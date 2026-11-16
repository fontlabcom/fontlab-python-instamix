# this_file: src/fontlab_instamix/packages.py
"""Install PyPI or ``git+`` packages into FontLab's site-packages with uv.

Uses ``uv pip install --target <site-packages> --python-version 3.11
--python-platform <triple>`` so packages match FontLab's embedded Python,
whatever Python runs instamix.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path, PurePosixPath

from . import env, uv


def install_args(data: Path, specs: list[str], *, upgrade: bool = False) -> list[str]:
    """uv arguments (without the uv binary) for installing ``specs``."""
    if not specs:
        raise ValueError("no packages to install")
    args = [
        "pip",
        "install",
        "--target",
        str(env.site_packages(data)),
        "--python-version",
        env.FONTLAB_PYTHON,
        "--python-platform",
        env.uv_platform(),
    ]
    if upgrade:
        args.append("--upgrade")
    return args + list(specs)


def install(
    data: Path,
    specs: list[str],
    *,
    upgrade: bool = False,
    uv_bin: Path | None = None,
    runner=subprocess.run,
) -> subprocess.CompletedProcess:
    """Install ``specs`` into ``<data>/python/3.11/site-packages``."""
    env.site_packages(data).mkdir(parents=True, exist_ok=True)
    uv_bin = uv_bin or uv.ensure(data)
    return uv.run(uv_bin, install_args(data, specs, upgrade=upgrade), runner=runner)


def dist_name(folder: str) -> str:
    """Distribution name from a ``*.dist-info`` folder name."""
    return folder[: -len(".dist-info")].rsplit("-", 1)[0]


def listed(data: Path) -> list[tuple[str, str]]:
    """``(name, version)`` of every distribution in site-packages."""
    site = env.site_packages(data)
    if not site.is_dir():
        return []
    found = []
    for info in sorted(site.glob("*.dist-info")):
        stem = info.name[: -len(".dist-info")]
        name, _, version = stem.rpartition("-")
        found.append((name or stem, version))
    return found


def _normal(name: str) -> str:
    return name.lower().replace("-", "_").replace(".", "_")


def uninstall(data: Path, name: str) -> list[str]:
    """Remove a distribution installed with ``--target`` using its RECORD.

    ``uv pip uninstall`` cannot address a ``--target`` folder, so this reads
    the RECORD file directly. Returns the removed relative paths.
    """
    site = env.site_packages(data)
    infos = [i for i in site.glob("*.dist-info") if _normal(dist_name(i.name)) == _normal(name)]
    if not infos:
        raise ValueError(f"{name} is not installed in {site}")
    removed = []
    root = Path(os.path.realpath(site))
    for info in infos:
        record = info / "RECORD"
        lines = record.read_text(encoding="utf-8").splitlines() if record.is_file() else []
        parents: set[Path] = set()
        for line in lines:
            rel = line.split(",", 1)[0]
            if not rel or "\\" in rel or PurePosixPath(rel).is_absolute() or ".." in PurePosixPath(rel).parts:
                continue
            target = site / rel
            # Check the folder holding the entry, never following the entry itself.
            parent = Path(os.path.realpath(target.parent))
            if parent != root and root not in parent.parents:
                continue
            if target.is_symlink() or target.is_file():
                target.unlink()
                removed.append(rel)
                parents.add(target.parent)
        _prune(site, info, parents)
    return removed


def _prune(site: Path, info: Path, parents: set[Path]) -> None:
    """Delete ``info`` and the now-empty folders above removed files, up to ``site``."""
    import shutil

    if info.is_dir() and not info.is_symlink():
        shutil.rmtree(info)
    for folder in sorted(parents, key=lambda p: -len(p.parts)):
        while folder != site and site in folder.parents:
            if folder.is_symlink() or not folder.is_dir():
                break
            cache = folder / "__pycache__"
            if cache.is_dir() and not cache.is_symlink() and all(c.suffix == ".pyc" for c in cache.iterdir()):
                shutil.rmtree(cache)
            if any(folder.iterdir()):
                break
            folder.rmdir()
            folder = folder.parent
