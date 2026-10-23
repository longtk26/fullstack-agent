# bga-runner: executes generated (untrusted) projects for validation. Built with `make runner`.
# Build context: agent-api/templates/fastapi_overlay (the baked venv matches the generated requirements).
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.9.5

COPY files/requirements.txt files/requirements-dev.txt /opt/bga/
RUN uv venv /opt/venv \
    && uv pip install --no-cache --python /opt/venv/bin/python -r /opt/bga/requirements.txt -r /opt/bga/requirements-dev.txt \
    && cat /opt/bga/requirements.txt /opt/bga/requirements-dev.txt | sha256sum | cut -d' ' -f1 > /opt/venv/requirements.sha256

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
