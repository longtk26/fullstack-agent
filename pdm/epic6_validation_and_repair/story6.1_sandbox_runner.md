# Story 6.1 — Isolated sandbox runner

**Epic:** [6 — Validation & repair](epic6_validation_and_repair.md) · **Requirements:** NFR 8.1, 8.3 · **Depends on:** 1.2, 4.4

## User story

As the security owner, I want generated (untrusted) code to run only inside a locked-down, per-job container,
so that it cannot touch the agent, the host, secrets or the internet.

## Acceptance criteria

- [ ] `docker/runner/Dockerfile` → `bga-runner:<version>` (python 3.12-slim, uv, make, ruff, pytest, non-root uid 10001).
      Built by `make up` (compose `build` profile) and pinned by tag.
- [ ] `ISandboxRunner` port, Docker SDK implementation:
  - `start(gen_id)`: create the internal network and the Postgres sidecar (tmpfs data, random creds), then wait until healthy.
  - `exec(gen_id, argv, timeout_s, env) → {exit_code, duration_ms, stdout_ref, stderr_ref, truncated}`.
    Each check is a `docker run --rm` on the job network (no long-lived exec shell).
  - `install_deps(gen_id)`: `uv venv /work/.venv && uv pip install -r requirements.txt -r requirements-dev.txt` on the
    egress network with a PyPI-only proxy allowlist. The venv is cached by a hash of the requirements files.
  - `stop(gen_id)`: remove containers, network and temp volumes. Idempotent.
- [ ] Limits from env: `SANDBOX_CPU` (1), `SANDBOX_MEMORY` (1g), `SANDBOX_PIDS` (256), per-command timeout (300 s),
      output byte cap. `--read-only` rootfs plus a tmpfs `/tmp`, `--cap-drop ALL`, `--security-opt no-new-privileges`.
- [ ] Only `/work` (that job's project dir) is mounted. Env passed is only `DB_URL` (the template's variable) for the
      sidecar, plus a generated `JWT_SECRET` and `CORS_ORIGINS`.
- [ ] Test: a sandbox command trying `curl https://example.com` fails. Reading `/var/run/docker.sock` fails.
      Writing outside `/work` and `/tmp` fails.
