# bga-runner: executes generated (untrusted) projects for validation. Built with `make runner`.
# Build context: agent-api/templates/fastapi_overlay (the baked venv matches the generated requirements).
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.9.5

COPY files/requirements.txt files/requirements-dev.txt /opt/bga/
# Story 10.2: every plugin's requirements too (agent-api/templates/plugins/*/plugin.json)
COPY --from=plugins . /opt/bga/plugins/
RUN python -c "import glob, json; print('\n'.join(r for f in sorted(glob.glob('/opt/bga/plugins/*/plugin.json')) for r in json.load(open(f)).get('requirements', [])))" > /opt/bga/plugin-requirements.txt \
    && uv venv /opt/venv \
    && uv pip install --no-cache --python /opt/venv/bin/python -r /opt/bga/requirements.txt -r /opt/bga/requirements-dev.txt -r /opt/bga/plugin-requirements.txt \
    && cat /opt/bga/requirements.txt /opt/bga/requirements-dev.txt /opt/bga/plugin-requirements.txt | grep -v '^[[:space:]]*$' | sort -u > /opt/venv/requirements.baked

COPY --from=runner_bin . /opt/bga/bin/

RUN useradd --uid 10001 --no-create-home runner
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPYCACHEPREFIX=/tmp/pycache \
    PYTHONPATH=/work \
    RUFF_CACHE_DIR=/tmp/ruff \
    UV_CACHE_DIR=/tmp/uv \
    HOME=/tmp
USER 10001
WORKDIR /work
