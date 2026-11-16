# this_file: src/fontlab_instamix/venv.py
"""``<data>/.venv`` matching FontLab's Python version, created by uv."""

from __future__ import annotations

import sys
from pathlib import Path

from . import env, uv

VENV = ".venv"


def path(data: Path) -> Path:
    return Path(data) / VENV


def python(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def create(data: Path, uv_bin: Path, runner=None) -> Path:
    """Create ``<data>/.venv`` for Python 3.11 unless it exists."""
    venv = path(data)
    if python(venv).exists():
        return venv
    args = ["venv", "--python", env.FONTLAB_PYTHON, str(venv)]
    if runner is None:
        uv.run(uv_bin, args)
    else:
        uv.run(uv_bin, args, runner=runner)
    return venv
