#!/bin/sh
# Exit 0 if the baked /opt/venv matches the project's requirements, 3 if a project venv must be installed.
set -e
want=$(cat requirements.txt requirements-dev.txt | sha256sum | cut -d' ' -f1)
if [ "$want" = "$(cat /opt/venv/requirements.sha256)" ]; then echo "baked"; exit 0; fi
if [ -x /work/.venv/bin/python ] && [ "$want" = "$(cat /work/.venv/requirements.sha256 2>/dev/null)" ]; then echo "project"; exit 0; fi
echo "install-needed"; exit 3
