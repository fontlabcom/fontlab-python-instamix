#!/usr/bin/env bash
# this_file: build.post.sh
# Repo-specific step run by ./build.sh after uv build: ship the FontLab installer.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
cp install.vfpy dist/install.vfpy
