#!/bin/sh
# this_file: test.sh
# Run the test suite with a throwaway pytest; instamix has no runtime deps.
set -eu
cd "$(dirname "$0")"
uv run --with pytest pytest -q "$@"
