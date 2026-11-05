"""The shared local object store (Story 10.5): one S3-compatible container (`bga-storage`, RustFS) for the sandboxes
and previews of generated apps with file fields, like MinIO in the story; MinIO's images are no longer published.

It joins a job's or preview's network as `storage` while that network exists; the generated app creates its bucket
(one per generation) and the bucket's CORS rule at startup. The API is published on 127.0.0.1 only, so a browser on
this machine can upload to a presigned URL and read a signed one. Buckets are removed with their preview or sandbox
by a one-shot runner container (it has boto3) on `bga-storage-net`.
"""

import hashlib
import hmac
import time

import docker
from docker.errors import APIError, NotFound
from docker.models.containers import Container

from src.configs import config, get_logger

logger = get_logger(__name__)
NAME = "bga-storage"
ALIAS = "storage"
NETWORK = "bga-storage-net"
VOLUME = "bga-storage-data"
PORT = 9000
REGION = "us-east-1"
LABEL = "bga.storage"
READY_TIMEOUT_S = 30
MARKER = "src/libs/storage/__init__.py"  # a project (or ZIP) that has file fields has the storage library


def _derived() -> tuple[str, str]:
    """New root credentials, derived from JWT_SECRET (stable across restarts, never stored by us)."""
    digest = hmac.new(config.jwt_secret.encode(), b"bga-storage", hashlib.sha256).hexdigest()
    return f"bga{digest[:17]}", digest[17:57]


def credentials(client: docker.DockerClient) -> tuple[str, str]:
    """The running store's root credentials: whichever process started it (the worker, a test run) set them."""
    try:
        env = dict(item.split("=", 1) for item in client.containers.get(NAME).attrs["Config"]["Env"] if "=" in item)
        return env["RUSTFS_ACCESS_KEY"], env["RUSTFS_SECRET_KEY"]
    except (NotFound, KeyError):
        return _derived()


def bucket(prefix: str, generation_id: str) -> str:
    """S3 bucket names: 3–63 lowercase letters, digits and hyphens."""
    return f"{prefix}-{generation_id.lower().replace('_', '-')}"[:63]


def app_env(client: docker.DockerClient, bucket_name: str, public_endpoint: str) -> dict[str, str]:
    access, secret = credentials(client)
    return {
        "STORAGE_ENDPOINT": f"http://{ALIAS}:{PORT}",
        "STORAGE_PUBLIC_ENDPOINT": public_endpoint,
        "STORAGE_BUCKET": bucket_name,
        "STORAGE_REGION": REGION,
        "STORAGE_ACCESS_KEY": access,
        "STORAGE_SECRET_KEY": secret,
    }


def public_endpoint() -> str:
    return f"http://{config.preview_public_host}:{config.storage_port}"


def ensure(client: docker.DockerClient) -> Container:
    """The running store, started (and its network created) on first use."""
    if not client.networks.list(names=[NETWORK]):
        client.networks.create(NETWORK, driver="bridge", labels={LABEL: "network"})
    try:
        container = client.containers.get(NAME)
        if container.status != "running":
            container.start()
    except NotFound:
        access, secret = _derived()
        container = client.containers.run(
            config.storage_image,
            name=NAME,
            detach=True,
            network=NETWORK,
            labels={LABEL: "server"},
            environment={"RUSTFS_ACCESS_KEY": access, "RUSTFS_SECRET_KEY": secret},
            volumes={VOLUME: {"bind": "/data", "mode": "rw"}},
            ports={f"{PORT}/tcp": (config.preview_bind_host, config.storage_port)},
            restart_policy={"Name": "unless-stopped"},
            mem_limit="512m",
        )
    deadline = time.monotonic() + READY_TIMEOUT_S
    while time.monotonic() < deadline:
        probe = container.exec_run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"http://127.0.0.1:{PORT}/"])
        if probe.exit_code == 0 and probe.output.decode().strip() not in ("", "000"):
            return container
        time.sleep(0.5)
    raise RuntimeError("the local object store did not become ready")


def attach(client: docker.DockerClient, network_name: str) -> None:
    """Joins the store to a job's or preview's network as `storage`."""
    container = ensure(client)
    network = client.networks.get(network_name)
    try:
        network.connect(container, aliases=[ALIAS])
    except APIError as exc:
        if "already exists" not in str(exc).lower() and "endpoint with name" not in str(exc).lower():
            raise


def detach(client: docker.DockerClient, network_name: str) -> None:
    """Leaves a network before it is removed (a network with a connected container cannot be)."""
    try:
        client.networks.get(network_name).disconnect(NAME, force=True)
    except (NotFound, APIError):
        pass


REMOVE_SCRIPT = """
import os, boto3
from botocore.config import Config
s3 = boto3.client("s3", endpoint_url=os.environ["ENDPOINT"], aws_access_key_id=os.environ["KEY"],
                  aws_secret_access_key=os.environ["SECRET"], region_name="us-east-1",
                  config=Config(s3={"addressing_style": "path"}))
name = os.environ["BUCKET"]
try:
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=name):
        keys = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if keys:
            s3.delete_objects(Bucket=name, Delete={"Objects": keys})
    if os.environ.get("DROP") == "1":
        s3.delete_bucket(Bucket=name)
except s3.exceptions.NoSuchBucket:
    pass
"""


def remove_bucket(client: docker.DockerClient, bucket_name: str, drop: bool = True) -> None:
    """Empties a bucket (and removes it, unless `drop` is false); nothing when the store is not running."""
    try:
        if client.containers.get(NAME).status != "running":
            return
    except NotFound:
        return
    access, secret = credentials(client)
    try:
        client.containers.run(
            config.sandbox_image,
            ["python", "-c", REMOVE_SCRIPT],
            network=NETWORK,
            environment={
                "ENDPOINT": f"http://{NAME}:{PORT}",
                "KEY": access,
                "SECRET": secret,
                "BUCKET": bucket_name,
                "DROP": "1" if drop else "0",
            },  # fmt: skip
            remove=True,
            mem_limit="256m",
        )
    except (APIError, docker.errors.ContainerError) as exc:
        logger.warning("bucket not removed", extra={"bucket": bucket_name, "error": str(exc)[:300]})
