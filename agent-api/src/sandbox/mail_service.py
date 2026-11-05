"""The shared local mail catcher (Story 10.7): one Mailpit container (`bga-mailpit`) for the sandboxes and previews of
generated apps that send email. It joins a job's or preview's network as `mailpit` while that network exists; apps
send to it by SMTP and tag each message with their generation id (`X-Tags`), so the agent UI links to one
generation's emails. SMTP and the web UI are published on 127.0.0.1 only. Mailpit keeps the newest messages and
prunes the rest itself.
"""

import time

import docker
from docker.errors import APIError, NotFound
from docker.models.containers import Container

from src.configs import config

NAME = "bga-mailpit"
ALIAS = "mailpit"
SMTP_PORT = 1025
UI_PORT = 8025
LABEL = "bga.mail"
READY_TIMEOUT_S = 30
MARKER = "src/libs/email/__init__.py"  # a project (or ZIP) that sends email has the email library


def app_env(tag: str) -> dict[str, str]:
    """A preview tags its messages with the generation id (what the agent UI's inbox link shows); a sandbox with
    `sandbox-<id>`, so validation mail stays out of the preview's inbox."""
    return {
        "EMAIL_BACKEND": "smtp",
        "SMTP_HOST": ALIAS,
        "SMTP_PORT": str(SMTP_PORT),
        "SMTP_TLS": "false",
        "EMAIL_TAG": tag,
    }


def inbox_url(generation_id: str) -> str:
    """The generation's emails in the web UI (the agent UI links here)."""
    return f"http://{config.preview_public_host}:{config.mail_ui_port}/search?q=tag%3A{generation_id}"


def ensure(client: docker.DockerClient) -> Container:
    try:
        container = client.containers.get(NAME)
        if container.status != "running":
            container.start()
    except NotFound:
        container = client.containers.run(
            config.mail_image,
            name=NAME,
            detach=True,
            labels={LABEL: "server"},
            environment={
                "MP_MAX_MESSAGES": "2000",
                "MP_SMTP_AUTH_ACCEPT_ANY": "true",
                "MP_SMTP_AUTH_ALLOW_INSECURE": "true",
            },  # fmt: skip
            ports={
                f"{UI_PORT}/tcp": (config.preview_bind_host, config.mail_ui_port),
                f"{SMTP_PORT}/tcp": (config.preview_bind_host, config.mail_smtp_port),
            },
            restart_policy={"Name": "unless-stopped"},
            mem_limit="256m",
        )
    deadline = time.monotonic() + READY_TIMEOUT_S
    while time.monotonic() < deadline:
        container.reload()
        if container.status == "running":
            probe = container.exec_run(["/mailpit", "readyz"])
            if probe.exit_code == 0:
                return container
        time.sleep(0.5)
    raise RuntimeError("the local mail catcher did not become ready")


def attach(client: docker.DockerClient, network_name: str) -> None:
    container = ensure(client)
    try:
        client.networks.get(network_name).connect(container, aliases=[ALIAS])
    except APIError as exc:
        if "already exists" not in str(exc).lower() and "endpoint with name" not in str(exc).lower():
            raise


def detach(client: docker.DockerClient, network_name: str) -> None:
    try:
        client.networks.get(network_name).disconnect(NAME, force=True)
    except (NotFound, APIError):
        pass
