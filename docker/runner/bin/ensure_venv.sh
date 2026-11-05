#!/bin/sh
# Exit 0 if the baked /opt/venv holds every requirement of the project, 3 if a project venv must be installed.
# The baked venv has the overlay's requirements and every plugin's (Story 10.2), so a line it lacks needs an install.
set -e
missing=$(cat requirements.txt requirements-dev.txt | grep -v '^[[:space:]]*$' | grep -v '^#' | grep -vxFf /opt/venv/requirements.baked || true)
if [ -z "$missing" ]; then echo "baked"; exit 0; fi
want=$(cat requirements.txt requirements-dev.txt | sha256sum | cut -d' ' -f1)
if [ -x /work/.venv/bin/python ] && [ "$want" = "$(cat /work/.venv/requirements.sha256 2>/dev/null)" ]; then echo "project"; exit 0; fi
echo "install-needed"; exit 3
