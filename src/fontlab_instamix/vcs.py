# this_file: src/fontlab_instamix/vcs.py
"""Work out a checkout's version the way hatch-vcs and the legacy installer did.

Order: static ``[project].version``; for dynamic versions the hatch-vcs
version file, then ``PKG-INFO``, then ``git describe``, then the configured
fallback version, then ``0.0.0``. Never runs ``sys.executable``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

GIT_TIMEOUT = 20
DEFAULT = "0.0.0"
_VERSION_LINE = re.compile(r"""^(?:__version__|version)\s*(?::\s*\w+\s*)?=\s*(?:\w+\s*=\s*)?['"]([^'"]+)['"]""", re.MULTILINE)


def _hatch(pyproject: dict) -> dict:
    return pyproject.get("tool", {}).get("hatch", {})


def version_file(root: Path, pyproject: dict) -> str | None:
    """Version written by the hatch-vcs build hook, if the file exists."""
    rel = _hatch(pyproject).get("build", {}).get("hooks", {}).get("vcs", {}).get("version-file")
    path = root / rel if isinstance(rel, str) else None
    if not path or not path.is_file():
        return None
    match = _VERSION_LINE.search(path.read_text(encoding="utf-8", errors="replace"))
    return match.group(1) if match else None


def pkg_info(root: Path) -> str | None:
    """Version in an sdist's PKG-INFO, if present."""
    path = root / "PKG-INFO"
    if not path.is_file():
        return None
    match = re.search(r"^Version:\s*(\S+)", path.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
    return match.group(1) if match else None


def git_describe(root: Path, runner: Callable = subprocess.run) -> str | None:
    """Version from the newest ``vX.Y.Z`` tag, as the legacy installer computed it."""
    args = ["git", "-C", str(root), "describe", "--tags", "--long", "--match", "v[0-9]*.[0-9]*.[0-9]*"]
    flags = {"creationflags": 0x08000000} if sys.platform == "win32" else {}
    try:
        done = runner(args, capture_output=True, text=True, timeout=GIT_TIMEOUT, **flags)
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.fullmatch(r"v(.+)-(\d+)-(g[0-9a-f]+)", (done.stdout or "").strip()) if done.returncode == 0 else None
    if not match:
        return None
    tag, distance, sha = match.groups()
    return tag if distance == "0" else f"{tag}+{distance}.{sha}"


def fallback(pyproject: dict) -> str | None:
    """The configured hatch-vcs fallback version, if any."""
    version = _hatch(pyproject).get("version", {})
    raw = version.get("raw-options", {}).get("fallback_version")
    value = raw or version.get("fallback-version") or version.get("fallback_version")
    return value if isinstance(value, str) and value else None


def project_version(root: Path, pyproject: dict, runner: Callable = subprocess.run) -> str:
    """Return the version to record for the checkout at *root*."""
    project = pyproject.get("project", {})
    static = project.get("version")
    if static and "version" not in project.get("dynamic", []):
        return str(static)
    probes = [lambda: version_file(root, pyproject), lambda: pkg_info(root)]
    git = lambda: git_describe(root, runner)
    probes = [git, *probes] if (root / ".git").exists() else [*probes, git]
    for probe in probes:
        if found := probe():
            return found
    return fallback(pyproject) or (str(static) if static else DEFAULT)
