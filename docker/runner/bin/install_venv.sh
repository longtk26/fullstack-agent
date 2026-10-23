#!/bin/sh
# Runs on the egress network: builds /work/.venv for projects whose requirements differ from the baked venv.
set -e
rm -rf /work/.venv
uv venv /work/.venv
uv pip install --python /work/.venv/bin/python -r requirements.txt -r requirements-dev.txt
cat requirements.txt requirements-dev.txt | sha256sum | cut -d' ' -f1 > /work/.venv/requirements.sha256
