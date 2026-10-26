# Story 6.1 — Isolated sandbox runner

**Epic:** [6 — Validation & repair](epic6_validation_and_repair.md) · **Requirements:** NFR 8.1, 8.3 · **Depends on:** 1.2, 4.4

## User story

As the security owner, I want generated (untrusted) code to run only inside a locked-down, per-job container,
so that it cannot touch the agent, the host, secrets or the internet.

## Acceptance criteria

- [x] `docker/runner/Dockerfile` → `bga-runner:<version>` (python 3.12-slim, uv, make, ruff, pytest, non-root uid 10001).
      Built by `make up` (compose `build` profile) and pinned by tag.
- [x] `ISandboxRunner` port, Docker SDK implementation:
  - `start(gen_id)`: create the internal network and the Postgres sidecar (tmpfs data, random creds), then wait until healthy.
  - `exec(gen_id, argv, timeout_s, env) → {exit_code, duration_ms, stdout_ref, stderr_ref, truncated}`.
    Each check is a `docker run --rm` on the job network (no long-lived exec shell).
  - `install_deps(gen_id)`: `uv venv /work/.venv && uv pip install -r requirements.txt -r requirements-dev.txt` on the
    egress network with a PyPI-only proxy allowlist. *(Partly: plain egress network, allowlist proxy deferred to 11.x.)* The venv is cached by a hash of the requirements files.
  - `stop(gen_id)`: remove containers, network and temp volumes. Idempotent.
- [x] Limits from env: `SANDBOX_CPU` (1), `SANDBOX_MEMORY` (1g), `SANDBOX_PIDS` (256), per-command timeout (300 s),
      output byte cap. `--read-only` rootfs plus a tmpfs `/tmp`, `--cap-drop ALL`, `--security-opt no-new-privileges`.
- [x] Only `/work` (that job's project dir) is mounted. Env passed is only `DB_URL` (the template's variable) for the
      sidecar, plus a generated `JWT_SECRET` and `CORS_ORIGINS`.
- [x] Test: a sandbox command trying `curl https://example.com` fails. Reading `/var/run/docker.sock` fails.
      Writing outside `/work` and `/tmp` fails.

**Status (2026-10-23):** done (`agent-api/src/sandbox/`, `docker/runner/`, `make runner`), except the PyPI-only
proxy: projects whose requirements differ from the runner's baked venv install into `/work/.venv` on a plain
egress bridge network (`bga-sbx-egress`); the allowlist proxy is left for hardening (11.x). Generated CRUD
projects need no extra packages, so the normal path never leaves the internal network. Sandboxes carry an
instance label (hash of the database name; was `DB_URL` until 2026-10-26) so deployments sharing a Docker daemon never clean up each other's sandboxes;
the worker removes orphans of finished generations. Isolation tests: `tests/sandbox/` (`BGA_SANDBOX_TESTS=1`).
