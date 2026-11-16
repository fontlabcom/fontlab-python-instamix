# this_file: src/fontlab_instamix/wrap.py
"""Wrap a script or folder of scripts into a ``.fontlabext`` and ``.fontlabextz``."""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from pathlib import Path

from . import manifest

SCRIPT_SUFFIXES = (".py", ".vfpy")


def slug(text: str) -> str:
    """Lowercase id part from free text."""
    value = re.sub(r"[^a-z0-9-]+", "-", text.lower()).strip("-")
    return value if value and value[0].isalpha() else f"x{value}" if value else "extension"


def make_folder(
    source: Path,
    out_dir: Path,
    ext_id: str,
    *,
    name: str | None = None,
    version: str = "0.1.0",
) -> Path:
    """Create ``<out_dir>/<ext_id>.fontlabext`` with ``source`` under ``scripts/``.

    The manifest installs the scripts into ``Scripts/<ext_id>/``.
    """
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(source)
    if source.is_file() and source.suffix.lower() not in SCRIPT_SUFFIXES:
        raise ValueError(f"not a FontLab script (.py or .vfpy): {source}")
    folder = Path(out_dir) / f"{ext_id}.fontlabext"
    if folder.exists():
        raise FileExistsError(folder)
    scripts = folder / "scripts"
    scripts.mkdir(parents=True)
    if source.is_dir():
        shutil.copytree(source, scripts, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    else:
        shutil.copy2(source, scripts / source.name)
    data = {
        "id": ext_id,
        "name": name or source.stem,
        "version": version,
        "install": [{"from": "scripts", "to": "Scripts/{}"}],
    }
    manifest.parse(data)
    (folder / manifest.MANIFEST).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return folder


def make_zip(folders: list[Path], zip_path: Path) -> Path:
    """Zip ``.fontlabext`` folders (the folders themselves, not their contents)."""
    zip_path = Path(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in folders:
            folder = Path(folder)
            manifest.load(folder)
            for path in sorted(folder.rglob("*")):
                if "__pycache__" in path.parts or path.name == ".DS_Store" or path.is_dir():
                    continue
                archive.write(path, (Path(folder.name) / path.relative_to(folder)).as_posix())
    return zip_path
