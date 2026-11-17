# this_file: src/fontlab_instamix/wrap.py
"""Wrap a script or folder of scripts into a ``.fontlabext`` and ``.fontlabextz``."""

from __future__ import annotations

import json
import keyword
import re
import shutil
import tempfile
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
    data = {
        "id": ext_id,
        "name": name or source.stem,
        "version": version,
        "install": [{"from": "scripts", "to": "Scripts/{}"}],
    }
    manifest.parse(data)
    folder = Path(out_dir) / f"{ext_id}.fontlabext"
    if folder.exists():
        raise FileExistsError(folder)
    scripts = folder / "scripts"
    scripts.mkdir(parents=True)
    if source.is_dir():
        shutil.copytree(source, scripts, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    else:
        shutil.copy2(source, scripts / source.name)
    (folder / manifest.MANIFEST).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return folder


def make_zip(folders: list[Path], zip_path: Path) -> Path:
    """Zip ``.fontlabext`` folders (the folders themselves, not their contents)."""
    folders = [Path(folder) for folder in folders]
    if not folders:
        raise ValueError("at least one extension folder is required")
    ids, roots = set(), set()
    for folder in folders:
        item = manifest.load(folder)
        root = folder.name.casefold()
        if folder.name[:-len(".fontlabext")] != item.id or folder.suffix.casefold() != ".fontlabext":
            raise ValueError("extension root must match its manifest id")
        if item.id.casefold() in ids or root in roots:
            raise ValueError("duplicate extension id or root")
        ids.add(item.id.casefold())
        roots.add(root)
    zip_path = Path(zip_path)
    with tempfile.TemporaryDirectory(prefix=".instamix-pack-", dir=zip_path.parent) as temporary:
        staged = Path(temporary) / "archive.zip"
        with zipfile.ZipFile(staged, "w", zipfile.ZIP_DEFLATED) as archive:
            for folder in folders:
                for path in sorted(folder.rglob("*")):
                    if "__pycache__" in path.parts or path.name == ".DS_Store" or path.is_dir():
                        continue
                    archive.write(path, (Path(folder.name) / path.relative_to(folder)).as_posix())
        staged.replace(zip_path)
    return zip_path


PLUGIN_KINDS = {
    "reporter": "reporters",
    "filter": "filters",
    "tool": "tools",
    "palette": "palettes",
    "general": "general",
}
_RELEASE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def _plugin_metadata(data: dict[str, str]) -> list[str]:
    """Check the App manifest contract without importing the entry module."""
    if any(not isinstance(value, str) or not value.strip() for value in data.values()):
        raise ValueError("plugin metadata requires nonempty strings")
    if data["kind"] not in PLUGIN_KINDS:
        raise ValueError("unsupported plugin kind")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", data["id"]):
        raise ValueError("plugin id must be a stable identifier")
    for field in ("version", "min_app_version"):
        if not _RELEASE.fullmatch(data[field]):
            raise ValueError(f"{field} must be a three-part release version")
    entry = data["entry"].split(":")
    if len(entry) != 2 or any(
        not part.isidentifier() or keyword.iskeyword(part)
        for part in entry[0].split(".") + entry[1:]
    ):
        raise ValueError("entry must be module:Class using Python identifiers")
    return entry[0].split(".")


def make_plugin(
    source: Path,
    out_dir: Path,
    ext_id: str,
    *,
    plugin_id: str,
    name: str,
    kind: str,
    entry: str,
    min_app_version: str,
    version: str = "0.1.0",
) -> Path:
    """Package an App-compatible draft, without executing or adapting its code.

    A directory supplies bundle contents; a file supplies one Python module.
    App checks inheritance and class metadata when loading the installed bundle.
    Existing plugin.json must agree with all six explicit metadata fields.
    """
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(source)
    if not source.is_dir() and (not source.is_file() or source.suffix != ".py"):
        raise ValueError("a plugin source must be a Python module or directory")
    metadata = {
        "id": plugin_id,
        "name": name,
        "kind": kind,
        "version": version,
        "entry": entry,
        "min_app_version": min_app_version,
    }
    parts = _plugin_metadata(metadata)
    root = source if source.is_dir() else source.parent
    module = root.joinpath(*parts)
    candidates = [module.with_suffix(".py"), module / "__init__.py"]
    if not any(
        path.is_file()
        and path.resolve().is_relative_to(root.resolve())
        and (source.is_dir() or path == source)
        for path in candidates
    ):
        raise ValueError("entry module must exist inside the supplied source")
    existing = source / "plugin.json" if source.is_dir() else None
    if existing is not None and existing.exists():
        previous = json.loads(existing.read_text(encoding="utf-8"))
        if not isinstance(previous, dict) or any(
            previous.get(key) != value for key, value in metadata.items()
        ):
            raise ValueError("existing plugin.json must agree with explicit metadata")
    if source.is_dir() and any(
        not path.resolve().is_relative_to(source.resolve())
        for path in source.rglob("*")
    ):
        raise ValueError("plugin source links must stay inside the supplied directory")
    stem = source.stem if source.is_file() else source.name
    for suffix_kind in PLUGIN_KINDS:
        for suffix in (".fontlab" + suffix_kind, ".fontlab" + suffix_kind.title()):
            stem = stem.removesuffix(suffix)
    if not stem or stem in (".", "..") or any(char in stem for char in ":\\"):
        raise ValueError("invalid plugin bundle stem")
    parent = "Extensions/" + PLUGIN_KINDS[kind]
    data = {
        "id": ext_id,
        "name": name,
        "version": version,
        "install": [{"from": parent, "to": parent}],
    }
    manifest.parse(data)
    folder = Path(out_dir) / f"{ext_id}.fontlabext"
    if folder.exists() or folder.is_symlink():
        raise FileExistsError(folder)
    if source.is_dir() and folder.resolve().is_relative_to(source.resolve()):
        raise ValueError("output must be outside the plugin source")
    # Stage before publishing so a failed copy never leaves an incomplete bundle.
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".instamix-plugin-", dir=folder.parent
    ) as temporary:
        staged = Path(temporary) / folder.name
        inner = staged / parent / f"{stem}.fontlab{kind}"
        inner.parent.mkdir(parents=True)
        if source.is_dir():
            shutil.copytree(
                source,
                inner,
                ignore=shutil.ignore_patterns("__pycache__", ".DS_Store", "*.pyc"),
            )
        else:
            inner.mkdir()
            shutil.copy2(source, inner / source.name)
        if existing is None or not existing.exists():
            (inner / "plugin.json").write_text(
                json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
            )
        (staged / manifest.MANIFEST).write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
        staged.rename(folder)
    return folder
