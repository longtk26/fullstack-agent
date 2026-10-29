"""Docker implementation of the per-job sandbox (Story 6.1).

Topology per job: an internal network `bga-sbx-<gen>` (no route out), a PostgreSQL sidecar on tmpfs with random
credentials, and one short-lived runner container per command with /work = the job's project directory.
Runner containers are read-only, run as a non-root uid, drop all capabilities and get CPU/memory/PID limits.
The worker drives the host Docker daemon, so bind-mount sources are host paths (HOST_WORKSPACE_ROOT is mounted
at the same path inside the worker).
"""

import asyncio
import hashlib
import json
import os
import secrets
import threading
import time
from pathlib import Path

import docker
from docker.errors import APIError, NotFound
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import ReadTimeout
from sqlalchemy.engine import make_url

from src.configs import config, get_logger

from .port import ExecResult, ISandbox, ISandboxProvider, SandboxError, SandboxKind

logger = get_logger(__name__)
LABEL = "bga.sandbox"
INSTANCE_LABEL = "bga.instance"
PART_LABEL = "bga.sandbox.part"
RUNNER_UID = 10001
DB_USER = "app"
DB_READY_TIMEOUT_S = 60
# Story 17.5: shared, read-only node_modules per dependency set. Vite and Vitest write into these folders (nothing
# else does: tsc, ESLint, next build and Playwright only read), so each gets a tmpfs.
MODULES_VOLUME = "bga-fe-modules-"
MODULES_LABEL = "bga.fe-modules"
MODULES_READY = ".bga-ready"
WRITABLE_DIRS = (".vite", ".vite-temp", ".vitest-cache")
DEPENDENCY_FIELDS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies", "pnpm")
_modules_lock = threading.Lock()
_modules_ready: dict[str, bool] = {}  # per worker process: key → filled (False: install per project instead)


def dependency_key(project: Path) -> str | None:
    """What decides a frontend's node_modules: the lock file, the pnpm workspace settings and the dependency fields
    of package.json (scripts and names may differ). None when there is no lock file."""
    lock = project / "pnpm-lock.yaml"
    try:
        manifest = json.loads((project / "package.json").read_text())
        digest = hashlib.sha256(lock.read_bytes())
    except (OSError, ValueError):
        return None
    workspace = project / "pnpm-workspace.yaml"
    if workspace.is_file():
        digest.update(workspace.read_bytes())
    digest.update(json.dumps({key: manifest.get(key) for key in DEPENDENCY_FIELDS}, sort_keys=True).encode())
    return digest.hexdigest()[:16]


def instance_id() -> str:
    """Identifies this agent deployment by its database, so a worker only ever cleans up its own sandboxes and
    previews when several deployments (e.g. the Docker stack and the test suite) share one Docker daemon.

    Only the database name counts, not the URL: the Docker worker (`postgres:5432`) and a host dev worker
    (`localhost:5442`) use the same database and must recognise each other's containers."""
    return hashlib.sha256((make_url(config.db_url).database or "").encode()).hexdigest()[:12]


def _labels(generation_id: str, part: str = "backend") -> dict[str, str]:
    return {LABEL: generation_id, INSTANCE_LABEL: instance_id(), PART_LABEL: part}


class SandboxProfile:
    """What a sandbox kind runs with: image, database sidecar, limits and extra volumes."""

    def __init__(self, kind: SandboxKind):
        frontend = kind == "frontend"
        self.kind = kind
        self.image = config.frontend_sandbox_image if frontend else config.sandbox_image
        self.database = not frontend
        self.cpus = config.frontend_sandbox_cpus if frontend else config.sandbox_cpus
        self.memory = config.frontend_sandbox_memory if frontend else config.sandbox_memory
        self.pids = config.frontend_sandbox_pids if frontend else config.sandbox_pids
        self.tmp = config.frontend_sandbox_tmp if frontend else "512m"
        self.volumes = {config.frontend_store_volume: {"bind": "/pnpm-store", "mode": "rw"}} if frontend else {}


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
    def __init__(self, client: docker.DockerClient, generation_id: str, project: Path, kind: SandboxKind = "backend"):
        self.client = client
        self.generation_id = generation_id
        self.project = project.resolve()
        self.profile = SandboxProfile(kind)
        suffix = "" if kind == "backend" else "-fe"
        self.network_name = f"bga-sbx-{_slug(generation_id)}{suffix}"
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
        labels = _labels(self.generation_id, self.profile.kind)
        self.client.networks.create(self.network_name, driver="bridge", internal=True, labels=labels)
        if not self.profile.database:
            logger.info("sandbox started", extra={"generation_id": self.generation_id, "kind": self.profile.kind})
            return
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
        remove_job_resources(self.client, {self.generation_id}, part=self.profile.kind)

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

    async def shared_dependencies(self) -> str | None:
        await self.start()
        return await asyncio.to_thread(self._shared_modules)

    # -- shared node_modules (Story 17.5) ------------------------------------------------------------------------

    def _shared_modules(self) -> str | None:
        """The ready volume for this project's dependencies, filled on first use; None when the project must install
        its own (backend sandbox, switched off, no lock file, or packages the store does not have)."""
        if self.profile.kind != "frontend" or not config.frontend_shared_modules:
            return None
        key = dependency_key(self.project)
        if key is None:
            return None
        volume = f"{MODULES_VOLUME}{key}"
        with _modules_lock:
            if key not in _modules_ready:
                _modules_ready[key] = self._fill_modules(volume)
        return volume if _modules_ready[key] else None

    def _fill_modules(self, volume: str) -> bool:
        """An offline install into the volume (the job network has no route out), marked ready only when it
        succeeded, so an interrupted fill is simply repeated."""
        try:
            self.client.volumes.get(volume)
        except NotFound:
            self.client.volumes.create(volume, labels={MODULES_LABEL: "true"})
        (self.project / "node_modules").mkdir(exist_ok=True)  # the mount point, owned by us rather than by Docker
        user = self._user()
        mount = {volume: {"bind": "/modules", "mode": "rw"}}
        # The volume root goes to this worker's runner uid (a new volume belongs to root; the host and the Docker
        # worker use different uids). Only this step runs as root, with CHOWN only.
        if self._run_helper(f"chown {user} /modules", "0:0", mount, cap_add=["CHOWN"]) != 0:
            return False
        writable = " ".join(f"node_modules/{name}" for name in WRITABLE_DIRS)
        fill = (
            f"{{ [ -f node_modules/{MODULES_READY} ] || {{ pnpm install --frozen-lockfile --offline && "
            f"touch node_modules/{MODULES_READY}; }}; }} && mkdir -p {writable}"
        )
        volumes = {
            str(self.project): {"bind": "/work", "mode": "rw"},
            volume: {"bind": "/work/node_modules", "mode": "rw"},
            **self.profile.volumes,
        }
        started = time.monotonic()
        ok = self._run_helper(fill, user, volumes) == 0
        logger.info(
            "shared node_modules " + ("ready" if ok else "not possible, the project installs its own"),
            extra={"volume": volume, "duration_ms": int((time.monotonic() - started) * 1000)},
        )
        return ok

    def _run_helper(self, command: str, user: str, volumes: dict, cap_add: list[str] | None = None) -> int:
        container = self.client.containers.run(
            self.profile.image,
            ["sh", "-c", command],
            detach=True,
            user=user,
            network=self.network_name,
            labels=_labels(self.generation_id, self.profile.kind),
            volumes=volumes,
            working_dir="/work",
            environment={"HOME": "/tmp", "CI": "1"},
            read_only=True,
            tmpfs={"/tmp": f"rw,exec,size={self.profile.tmp}"},
            cap_drop=["ALL"],
            cap_add=cap_add,
            security_opt=["no-new-privileges"],
            nano_cpus=int(self.profile.cpus * 1e9),
            mem_limit=_memory_bytes(self.profile.memory),
            pids_limit=self.profile.pids,
        )
        try:
            return container.wait(timeout=600).get("StatusCode", 1)
        except (ReadTimeout, RequestsConnectionError):
            return 124
        finally:
            try:
                container.remove(force=True)
            except APIError:
                pass

    def _exec(self, command: str, timeout_s: int, env: dict[str, str] | None, egress: bool) -> ExecResult:
        if egress:
            ensure_egress_network(self.client)
        environment = (
            {
                "DB_URL": self.db_url,
                "TEST_DB_URL": self.test_db_url,
                "CORS_ORIGINS": "*",
                "JWT_SECRET": secrets.token_hex(32),
            }
            if self.profile.database
            else {"HOME": "/tmp", "CI": "1", "NEXT_TELEMETRY_DISABLED": "1"}
        )
        environment |= env or {}
        if (self.project / ".venv" / "bin" / "python").exists():
            environment["PATH"] = "/work/.venv/bin:/opt/venv/bin:/usr/local/bin:/usr/bin:/bin"
        started = time.monotonic()  # includes a first fill of the shared node_modules
        user = self._user()
        volumes = {str(self.project): {"bind": "/work", "mode": "rw"}, **self.profile.volumes}
        tmpfs = {"/tmp": f"rw,exec,size={self.profile.tmp}"}
        modules = self._shared_modules()
        if modules is not None:
            volumes[modules] = {"bind": "/work/node_modules", "mode": "ro"}
            uid, _, gid = user.partition(":")
            for name in WRITABLE_DIRS:
                tmpfs[f"/work/node_modules/{name}"] = f"rw,exec,size=256m,uid={uid},gid={gid or uid}"
        container = self.client.containers.run(
            self.profile.image,
            ["sh", "-c", command],
            detach=True,
            user=user,
            network=config.sandbox_egress_network if egress else self.network_name,
            labels=_labels(self.generation_id, self.profile.kind),
            volumes=volumes,
            working_dir="/work",
            environment=environment,
            read_only=True,
            tmpfs=tmpfs,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            nano_cpus=int(self.profile.cpus * 1e9),
            mem_limit=_memory_bytes(self.profile.memory),
            pids_limit=self.profile.pids,
            ipc_mode="private",
            shm_size="256m" if self.profile.kind == "frontend" else None,
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


def remove_job_resources(client: docker.DockerClient, generation_ids: set[str], part: str | None = None) -> int:
    """Containers and networks of those generations' sandboxes; only one part (backend / frontend) when given.
    Resources from before parts existed carry no part label and count as `backend`."""
    removed = 0
    for generation_id in generation_ids:
        selector = {"label": [f"{LABEL}={generation_id}", f"{INSTANCE_LABEL}={instance_id()}"]}
        for container in client.containers.list(all=True, sparse=True, filters=selector):
            if part is not None and (container.attrs.get("Labels") or {}).get(PART_LABEL, "backend") != part:
                continue
            if not (container.attrs.get("Labels") or {}).get(LABEL):
                logger.warning("refusing to remove a non-sandbox container", extra={"container": container.id[:12]})
                continue
            try:
                container.remove(force=True)
                removed += 1
            except (NotFound, APIError):  # already gone, or removal already in progress
                pass
        for network in client.networks.list(filters=selector):
            if part is not None and (network.attrs.get("Labels") or {}).get(PART_LABEL, "backend") != part:
                continue
            try:
                network.remove()
                removed += 1
            except (NotFound, APIError):
                pass
    return removed


class DockerSandboxProvider(ISandboxProvider):
    def __init__(self, client: docker.DockerClient | None = None):
        self.client = client or docker.from_env()

    def for_job(self, generation_id: str, project: Path, kind: SandboxKind = "backend") -> DockerSandbox:
        return DockerSandbox(self.client, generation_id, project, kind)

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
