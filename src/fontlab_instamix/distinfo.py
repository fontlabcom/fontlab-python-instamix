# this_file: src/fontlab_instamix/distinfo.py
"""Write a ``.dist-info`` folder for a project installed from a checkout.

With it, ``importlib.metadata.version(name)`` and ``uv pip check`` see the
project. The bytes match the legacy ``install.vfpy`` output except for
``INSTALLER``, which says ``fontlab-instamix``.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import env, markers

INSTALLER = "fontlab-instamix"
WHEEL = "Wheel-Version: 1.0\nGenerator: fontlab-instamix\nRoot-Is-Purelib: true\nTag: py3-none-any\n"


def normalize(name: str) -> str:
    """Name as used in dist-info folder names (PEP 503, then underscores)."""
    return re.sub(r"[-_.]+", "_", name).lower()


def folder_name(name: str, version: str) -> str:
    """Dist-info folder name for *name* and *version*."""
    return f"{normalize(name)}-{version}.dist-info"


def _extra_line(spec: str, extra: str) -> str:
    requirement, marker = markers.split(spec)
    clause = f'extra == "{extra}"'
    return f"{requirement} ; ({marker}) and {clause}" if marker else f"{requirement} ; {clause}"


def metadata(name: str, version: str, requires: list[str], extras: dict[str, list[str]]) -> str:
    """METADATA text with Requires-Dist and Provides-Extra lines."""
    lines = ["Metadata-Version: 2.1", f"Name: {name}", f"Version: {version}"]
    lines += [f"Requires-Dist: {spec}" for spec in requires]
    for extra, specs in extras.items():
        key = re.sub(r"[-_.]+", "-", extra).lower()
        lines.append(f"Provides-Extra: {key}")
        lines += [f"Requires-Dist: {_extra_line(spec, key)}" for spec in specs]
    return "\n".join(lines) + "\n"


def write(
    data: Path, name: str, version: str, requires: list[str], extras: dict[str, list[str]], packages=()
) -> list[Path]:
    """Create the dist-info folder in site-packages; return the files written.

    RECORD lists the package links by name first, as the legacy installer did.
    """
    folder = env.site_packages(data) / folder_name(name, version)
    folder.mkdir(parents=True, exist_ok=True)
    files = {
        "METADATA": metadata(name, version, requires, extras),
        "INSTALLER": INSTALLER + "\n",
        "WHEEL": WHEEL,
    }
    written = []
    for file, text in files.items():
        (folder / file).write_text(text, encoding="utf-8")
        written.append(folder / file)
    names = [str(package) for package in packages] + [f"{folder.name}/{path.name}" for path in written] + [f"{folder.name}/RECORD"]
    (folder / "RECORD").write_text("".join(f"{line},,\n" for line in names), encoding="utf-8")
    return [*written, folder / "RECORD"]


def stale(data: Path, name: str) -> list[Path]:
    """Dist-info folders of *name* written by instamix (any version)."""
    site = env.site_packages(data)
    found = site.glob(f"{normalize(name)}-*.dist-info") if site.is_dir() else []
    return [path for path in found if _ours(path)]


def _ours(folder: Path) -> bool:
    installer = folder / "INSTALLER"
    return installer.is_file() and installer.read_text(encoding="utf-8").strip() == INSTALLER
