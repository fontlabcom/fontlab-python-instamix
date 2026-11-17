# this_file: src/fontlab_instamix/venv.py
"""Verified standalone Python sharing FontLab's canonical package directory."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from . import env, uv

VENV = ".venv"
PTH = "_fontlab_instamix.pth"
PROBE = (
    "import json,sys,sysconfig,platform; print(json.dumps(dict("
    "version='%d.%d'%sys.version_info[:2],platform=sys.platform,"
    "arch=platform.machine(),prefix=sys.prefix,purelib=sysconfig.get_path('purelib'),"
    "implementation=platform.python_implementation())))"
)


def path(data: Path) -> Path:
    return Path(data) / VENV


def python(venv: Path, plat: str | None = None) -> Path:
    return venv / (
        "Scripts/python.exe" if (plat or sys.platform) == "win32" else "bin/python"
    )


def request(target: env.Target) -> str:
    os_name = {"darwin": "macos", "win32": "windows", "linux": "linux"}[target.platform]
    arch = "aarch64" if target.arch == "arm64" else "x86_64"
    libc = "gnu" if target.platform == "linux" else "none"
    return f"cpython-{target.version}-{os_name}-{arch}-{libc}"


def probe(folder: Path, target: env.Target, runner=subprocess.run) -> Path:
    """Refuse a mismatched interpreter before modifying an existing environment."""
    try:
        executable = python(folder, target.platform)
        if (
            "fontlab" in sys.modules
            and executable.resolve() == Path(sys.executable).resolve()
        ):
            raise ValueError("refusing to execute the FontLab host executable")
        result = runner(
            [str(python(folder, target.platform)), "-I", "-B", "-c", PROBE],
            capture_output=True,
            text=True,
            timeout=30,
        )
        facts = json.loads(result.stdout)
        matches = (
            result.returncode == 0
            and facts["implementation"] == "CPython"
            and env.Target(facts["version"], facts["platform"], facts["arch"]) == target
            and Path(facts["prefix"]).resolve() == folder.resolve()
        )
        purelib = Path(facts["purelib"])
        if not matches or not purelib.is_dir():
            raise ValueError("runtime facts do not match")
        site = env.site_packages(folder.parent, version=target.version).resolve()
        if purelib.resolve() == site:
            env.require_inside(folder.parent, site / PTH)
        else:
            env.require_inside(folder, purelib / PTH)
        return purelib
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        raise uv.UvError(
            f"Incompatible environment {folder}: {exc}. Move it aside explicitly and retry."
        ) from exc


def create(
    data: Path, uv_bin: Path, runner=subprocess.run, *, target: env.Target | None = None
) -> Path:
    """Create or verify the environment, preserving existing packages and files."""
    target = target or env.target()
    folder = path(data)
    env.require_inside(data, folder / ".instamix-check")
    site = env.site_packages(data, version=target.version).resolve()
    env.require_inside(data, site / ".instamix-check")
    if any(c in str(site) for c in "\r\n"):
        raise ValueError("site-packages path cannot contain a newline")
    if not folder.exists():
        uv.run(
            uv_bin, ["venv", "--python", request(target), str(folder)], runner=runner
        )
    purelib = probe(folder, target, runner)
    pth = purelib / PTH
    content = f"# Managed by fontlab_instamix\n{site}\n"
    if pth.is_symlink() or (
        pth.exists() and pth.read_text(encoding="utf-8") != content
    ):
        raise uv.UvError(f"Unrelated shared-package path file exists: {pth}")
    if purelib.resolve() == site:
        return folder
    site.mkdir(parents=True, exist_ok=True)
    if not pth.exists():
        pth.write_text(content, encoding="utf-8")
    return folder
