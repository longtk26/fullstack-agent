"""Docker implementation of the per-job sandbox (Story 6.1).

Topology per job: an internal network `bga-sbx-<gen>` (no route out), a PostgreSQL sidecar on tmpfs with random
credentials, and one short-lived runner container per command with /work = the job's project directory.
Runner containers are read-only, run as a non-root uid, drop all capabilities and get CPU/memory/PID limits.
The worker drives the host Docker daemon, so bind-mount sources are host paths (HOST_WORKSPACE_ROOT is mounted
at the same path inside the worker).
"""

import asyncio
import hashlib
import os
import secrets
import time
from pathlib import Path

import docker
from docker.errors import APIError, NotFound
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ReadTimeout

from src.configs import config, get_logger

from .port import ExecResult, ISandbox, ISandboxProvider, SandboxError

logger = get_logger(__name__)
LABEL = "bga.sandbox"
INSTANCE_LABEL = "bga.instance"
RUNNER_UID = 10001
DB_USER = "app"
DB_READY_TIMEOUT_S = 60


def instance_id() -> str:
    """Identifies this agent deployment (its database), so a worker only ever cleans up its own sandboxes even
    when several deployments (e.g. the Docker stack and a dev worker or the test suite) share one Docker daemon."""
    return hashlib.sha256(config.db_url.encode()).hexdigest()[:12]


def _labels(generation_id: str) -> dict[str, str]:
    return {LABEL: generation_id, INSTANCE_LABEL: instance_id()}


def _slug(generation_id: str) -> str:
    return generation_id.lower()


def _memory_bytes(value: str) -> int:
    units = {"k": 1024, "m": 1024**2, "g": 1024**3}
    value = value.strip().lower()
    return int(float(value[:-1]) * units[value[-1]]) if value[-1] in units else int(value)


def _chown_tree(root: Path, uid: int, gid: int) -> None:
    for directory, dirnames, filenames in os.walk(root):
        if ".git" in dirnames:
            dirnames.remove(".git")  # stays with the worker; git runs with safe.directory
        for name in [*dirnames, *filenames]:
            path = os.path.join(directory, name)
            if os.lstat(path).st_uid != uid:
                os.lchown(path, uid, gid)
    os.chown(root, uid, gid)


class DockerSandbox(ISandbox):
    def __init__(self, client: docker.DockerClient, generation_id: str, project: Path):
        self.client = client
        self.generation_id = generation_id
        self.project = project.resolve()
        self.network_name = f"bga-sbx-{_slug(generation_id)}"
        self.db_name = f"bga-sbx-db-{_slug(generation_id)}"
        self.password = secrets.token_hex(16)
        self.db_url = f"postgresql://{DB_USER}:{self.password}@{self.db_name}:5432/app"
        self.test_db_url = f"postgresql://{DB_USER}:{self.password}@{self.db_name}:5432/app_test"
        self._started = False
        self._env: dict[str, str] = {}

    # -- lifecycle ---------------------------------------------------------------------------------------------

    async def start(self) -> None:
        if self._started:
            return
        await asyncio.to_thread(self._start)
        self._started = True

    def _start(self) -> None:
        self._remove_all()
        labels = _labels(self.generation_id)
        self.client.networks.create(self.network_name, driver="bridge", internal=True, labels=labels)
        self.client.containers.run(
            config.sandbox_db_image,
            name=self.db_name,
            detach=True,
            network=self.network_name,
            labels=labels,
            environment={"POSTGRES_USER": DB_USER, "POSTGRES_PASSWORD": self.password, "POSTGRES_DB": "app"},
            tmpfs={"/var/lib/postgresql": "rw,size=512m"},
            mem_limit="512m",
            pids_limit=256,
        )
        deadline = time.monotonic() + DB_READY_TIMEOUT_S
        container = self.client.containers.get(self.db_name)
        while time.monotonic() < deadline:
            # -h 127.0.0.1: the image's init-time server only listens on the unix socket.
            if container.exec_run(["pg_isready", "-h", "127.0.0.1", "-U", DB_USER, "-d", "app"]).exit_code == 0:
                break
            time.sleep(0.5)
        else:
            raise SandboxError("sandbox PostgreSQL did not become ready")
        self._psql("CREATE DATABASE app_test")
        logger.info("sandbox started", extra={"generation_id": self.generation_id})

    async def stop(self) -> None:
        await asyncio.to_thread(self._remove_all)
        self._started = False

    def _remove_all(self) -> None:
        remove_job_resources(self.client, {self.generation_id})

    # -- database -----------------------------------------------------------------------------------------------

    def _psql(self, sql: str) -> None:
        container = self.client.containers.get(self.db_name)
        result = container.exec_run(["psql", "-v", "ON_ERROR_STOP=1", "-U", DB_USER, "-d", "postgres", "-c", sql])
        if result.exit_code != 0:
            raise SandboxError(f"psql failed: {result.output.decode(errors='replace')[:500]}")

    async def reset_database(self, name: str) -> None:
        await self.start()
        await asyncio.to_thread(self._psql, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await asyncio.to_thread(self._psql, f'CREATE DATABASE "{name}"')

    # -- commands -----------------------------------------------------------------------------------------------

    def _user(self) -> str:
        stat = self.project.stat()
        if stat.st_uid != 0:
            return f"{stat.st_uid}:{stat.st_gid}"
        # Worker runs as root (Docker deployment): hand the project to the runner uid before every command.
        _chown_tree(self.project, RUNNER_UID, RUNNER_UID)
        return f"{RUNNER_UID}:{RUNNER_UID}"

    async def exec(
        self, command: str, timeout_s: int | None = None, env: dict[str, str] | None = None, egress: bool = False
    ) -> ExecResult:
        await self.start()
        return await asyncio.to_thread(
            self._exec, command, timeout_s or config.sandbox_command_timeout_seconds, env, egress
        )

    def _exec(self, command: str, timeout_s: int, env: dict[str, str] | None, egress: bool) -> ExecResult:
        if egress:
            ensure_egress_network(self.client)
        environment = {
            "DB_URL": self.db_url,
            "TEST_DB_URL": self.test_db_url,
            "CORS_ORIGINS": "*",
            "JWT_SECRET": secrets.token_hex(32),
            **(env or {}),
        }
        if (self.project / ".venv" / "bin" / "python").exists():
            environment["PATH"] = "/work/.venv/bin:/opt/venv/bin:/usr/local/bin:/usr/bin:/bin"
        started = time.monotonic()
        container = self.client.containers.run(
            config.sandbox_image,
            ["sh", "-c", command],
            detach=True,
            user=self._user(),
            network=config.sandbox_egress_network if egress else self.network_name,
            labels=_labels(self.generation_id),
            volumes={str(self.project): {"bind": "/work", "mode": "rw"}},
            working_dir="/work",
            environment=environment,
            read_only=True,
            tmpfs={"/tmp": "rw,exec,size=512m"},
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            nano_cpus=int(config.sandbox_cpus * 1e9),
            mem_limit=_memory_bytes(config.sandbox_memory),
            pids_limit=config.sandbox_pids,
        )
        timed_out = False
        try:
            exit_code = container.wait(timeout=timeout_s).get("StatusCode", 1)
        except (ReadTimeout, RequestsConnectionError):
            timed_out = True
            exit_code = 124
            try:
                container.kill()
            except APIError:
                pass
        cap = config.sandbox_output_bytes
        stdout = container.logs(stdout=True, stderr=False)
        stderr = container.logs(stdout=False, stderr=True)
        try:
            container.remove(force=True)
        except APIError:
            pass
        truncated = len(stdout) > cap or len(stderr) > cap
        return ExecResult(
            exit_code=exit_code,
            duration_ms=int((time.monotonic() - started) * 1000),
            stdout=stdout[-cap:].decode(errors="replace"),
            stderr=stderr[-cap:].decode(errors="replace"),
            truncated=truncated,
            timed_out=timed_out,
        )


def ensure_egress_network(client: docker.DockerClient) -> None:
    try:
        client.networks.get(config.sandbox_egress_network)
    except NotFound:
        client.networks.create(config.sandbox_egress_network, driver="bridge", labels={LABEL: "egress"})


def remove_job_resources(client: docker.DockerClient, generation_ids: set[str]) -> int:
    removed = 0
    for generation_id in generation_ids:
        selector = {"label": [f"{LABEL}={generation_id}", f"{INSTANCE_LABEL}={instance_id()}"]}
        for container in client.containers.list(all=True, sparse=True, filters=selector):
            try:
                container.remove(force=True)
                removed += 1
            except (NotFound, APIError):  # already gone, or removal already in progress
                pass
        for network in client.networks.list(filters=selector):
            try:
                network.remove()
                removed += 1
            except (NotFound, APIError):
                pass
    return removed


class DockerSandboxProvider(ISandboxProvider):
    def __init__(self, client: docker.DockerClient | None = None):
        self.client = client or docker.from_env()

    def for_job(self, generation_id: str, project: Path) -> DockerSandbox:
        return DockerSandbox(self.client, generation_id, project)

    async def job_ids(self) -> set[str]:
        def run() -> set[str]:
            selector = {"label": f"{INSTANCE_LABEL}={instance_id()}"}
            labels = [
                (c.attrs.get("Labels") or {})
                for c in self.client.containers.list(all=True, sparse=True, filters=selector)
            ]
            labels += [(n.attrs.get("Labels") or {}) for n in self.client.networks.list(filters=selector)]
            return {label[LABEL] for label in labels if label.get(LABEL)}

        return await asyncio.to_thread(run)

    async def remove(self, generation_ids: set[str]) -> int:
        return await asyncio.to_thread(remove_job_resources, self.client, generation_ids)
