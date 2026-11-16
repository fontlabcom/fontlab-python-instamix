# this_file: src/fontlab_instamix/extension.py
"""Install and uninstall ``.fontlabext`` folders and ``.fontlabextz`` zips.

Flow: unpack (zip only) -> copy the folder to
``<data>/Extensions/Library/<id>.fontlabext`` -> link each file named by the
manifest ``install`` rules into its target (symlink, or copy on Windows or
when symlinking fails) -> record every created path in the ledger.
Uninstall removes exactly the recorded paths that are still ours.
"""

from __future__ import annotations

import fnmatch
import os
import runpy
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import dest, env, ledger, manifest

EXT = ".fontlabext"
ZIP = ".fontlabextz"
LIBRARY = "Extensions/Library"


class InstallError(RuntimeError):
    """An extension cannot be installed or uninstalled safely."""


def is_ext(path: Path | str) -> bool:
    return str(path).rstrip("/\\").lower().endswith(EXT)


def is_zip(path: Path | str) -> bool:
    return str(path).lower().endswith(ZIP)


def basename(path: Path | str) -> str:
    """Folder name without ``.fontlabext`` (the ``{}`` placeholder)."""
    name = Path(str(path).rstrip("/\\")).name
    return name[: -len(EXT)] if name.lower().endswith(EXT) else name


# --- zip safety --------------------------------------------------------------


def check_member(name: str) -> None:
    """Reject zip member names that could write outside the target folder."""
    if "\\" in name:
        raise InstallError(f"zip member uses backslashes: {name!r}")
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        raise InstallError(f"zip member is absolute: {name!r}")
    if ".." in PurePosixPath(name).parts:
        raise InstallError(f"zip member escapes the folder: {name!r}")


def unpack(zip_path: Path, into: Path) -> list[Path]:
    """Extract a ``.fontlabextz`` into ``into``; return its ``.fontlabext`` folders."""
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        for name in names:
            check_member(name)
        archive.extractall(into)
    folders = sorted(p for p in Path(into).iterdir() if p.is_dir() and is_ext(p.name))
    if not folders:
        raise InstallError(f"{zip_path} holds no {EXT} folder at its root")
    return folders


def hook_for(folder: Path) -> Path | None:
    """Optional installer hook next to an unpacked extension."""
    root = folder.parent
    for child in root.iterdir():
        lower = child.name.lower()
        if child.is_file() and lower in (f"install_{folder.name.lower()}.vfpy", "install.vfpy"):
            return child
    return None


# --- linking -----------------------------------------------------------------


@dataclass
class Placement:
    """Paths created while linking one extension (relative to data)."""

    data: Path
    copy: bool
    entries: list[dict] = field(default_factory=list)

    def rel(self, path: Path) -> str:
        return Path(path).relative_to(self.data).as_posix()

    def mkdirs(self, folder: Path) -> None:
        missing = []
        while not folder.exists():
            missing.append(folder)
            folder = folder.parent
        for item in reversed(missing):
            item.mkdir()
            self.entries.append({"path": self.rel(item), "kind": "dir"})

    def place(self, source: Path, target: Path) -> None:
        if target.exists() or target.is_symlink():
            raise InstallError(f"refusing to overwrite existing {target}")
        self.mkdirs(target.parent)
        if not self.copy:
            try:
                os.symlink(source, target, target_is_directory=source.is_dir())
                self.entries.append({"path": self.rel(target), "kind": "link", "target": str(source)})
                return
            except (OSError, NotImplementedError):
                pass
        if source.is_dir():
            self.mkdirs(target)
            for child in sorted(source.rglob("*")):
                if child.is_file() and "__pycache__" not in child.parts:
                    self.place(child, target / child.relative_to(source))
            return
        shutil.copy2(source, target)
        self.entries.append(
            {"path": self.rel(target), "kind": "copy", "sha256": ledger.sha256(target), "source": str(source)}
        )


def default_copy() -> bool:
    """Copy instead of symlinking on Windows."""
    return sys.platform == "win32"


JUNK = ("__pycache__", "*.pyc", "*.vfpyc", ".DS_Store")


def _junk(rel: Path) -> bool:
    """Byte-code and Finder files are never installed (legacy SCRIPT_JUNK)."""
    return any(fnmatch.fnmatch(part, pattern) for part in rel.parts for pattern in JUNK)


def sources(folder: Path, pattern: str) -> list[tuple[Path, str]]:
    """Files matched by a ``from`` pattern, with their path below the match root.

    A folder contributes all its files (its contents go into the destination);
    a file or glob contributes the files themselves.
    """
    pattern = pattern.replace("\\", "/").strip("/")
    if ".." in PurePosixPath(pattern).parts or pattern.startswith("/"):
        raise InstallError(f"'from' must stay inside the extension: {pattern!r}")
    matches = sorted(folder.glob(pattern)) if any(c in pattern for c in "*?[") else [folder / pattern]
    found = []
    for match in matches:
        if match.is_dir():
            for child in sorted(match.rglob("*")):
                if child.is_file() and not _junk(child.relative_to(match)):
                    found.append((child, child.relative_to(match).as_posix()))
        elif match.is_file():
            found.append((match, match.name))
    if not found:
        raise InstallError(f"'from' {pattern!r} matches nothing in {folder.name}")
    return [(path, rel) for path, rel in found if not fnmatch.fnmatch(path.name.lower(), manifest.MANIFEST)]


def plan(folder: Path, info: manifest.Manifest, name: str, data: Path) -> list[tuple[Path, Path]]:
    """Return ``(source, target)`` pairs for every file the manifest installs."""
    pairs = []
    for rule in info.install:
        target_dir = Path(data) / dest.resolve(rule.to, name, info.vars)
        for source, rel in sources(folder, rule.source):
            pairs.append((source, target_dir / rel))
    site = env.site_packages(data)
    for package in info.packages:
        source = folder / package
        if not source.is_dir() or ".." in PurePosixPath(package).parts:
            raise InstallError(f"python package {package!r} is not a folder in {folder.name}")
        pairs.append((source, site / source.name))
    targets = [t for _, t in pairs]
    if len(set(targets)) != len(targets):
        raise InstallError("two install rules write the same destination")
    return pairs


# --- install / uninstall -----------------------------------------------------


def library_path(data: Path, ext_id: str) -> Path:
    return Path(data) / LIBRARY / f"{ledger.check_id(ext_id)}{EXT}"


def stage(folder: Path, target: Path) -> None:
    """Copy ``folder`` to ``target``, replacing an older copy at the last moment."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fresh = target.with_name(target.name + ".new")
    old = target.with_name(target.name + ".old")
    for leftover in (fresh, old):
        if leftover.exists():
            shutil.rmtree(leftover)
    shutil.copytree(folder, fresh, symlinks=False, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    if target.exists():
        target.rename(old)
    fresh.rename(target)
    if old.exists():
        shutil.rmtree(old)


def install_folder(
    folder: Path,
    data: Path,
    *,
    copy: bool | None = None,
    requirements=None,
    editable: bool = False,
    finish=None,
    fields: dict | None = None,
) -> dict:
    """Install one unpacked ``.fontlabext`` folder; return its ledger record.

    ``finish(data)`` may create more files after placement (dist-info,
    launchers) and returns them in creation order, folders first; they are
    recorded as owned entries. ``fields`` adds keys to the ledger record.

    ``requirements`` is called as ``requirements(data, list_of_specs)`` when
    the manifest lists ``python.requires`` (``packages.install`` by default).
    ``editable`` links files straight to their real (symlink-resolved)
    sources, e.g. a project checkout, and keeps only the manifest in Library.
    """
    folder = Path(folder)
    data = Path(data)
    info = manifest.load(folder)
    name = basename(folder)
    env.ensure_folders(data)
    library = library_path(data, info.id)
    pairs = plan(folder, info, name, data)  # validate before touching anything
    previous = ledger.read(data, info.id)
    backup = library.with_name(library.name + ".prev")
    if backup.exists() or backup.is_symlink():
        _remove_tree(data, backup)
    placement = Placement(data, default_copy() if copy is None else copy)
    removed: list[dict] = []
    try:
        if previous:
            removed = _remove_tracked(data, previous.get("entries", []))
        if library.exists():
            library.rename(backup)  # kept until the new version is fully placed
        if editable:
            with tempfile.TemporaryDirectory(prefix="instamix-stage-") as temp:
                shutil.copy2(manifest.find(folder), Path(temp) / manifest.MANIFEST)
                stage(Path(temp), library)
        else:
            stage(folder, library)
        for source, target in pairs:
            origin = source.resolve() if editable else library / source.relative_to(folder)
            placement.place(origin, target)
        if finish:
            placement.entries += generated_entries(data, finish(data))
    except Exception:
        # Roll back: drop the new files, bring back the old Library copy and links.
        remove_entries(data, placement.entries)
        if library.exists() or library.is_symlink():
            _remove_tree(data, library)
        if backup.exists():
            backup.rename(library)
        restore_entries(data, removed)
        raise
    if backup.exists():
        _remove_tree(data, backup)
    record = {
        "id": info.id,
        "name": info.name,
        "version": info.version,
        "basename": name,
        "library": placement.rel(library),
        "requires": list(info.requires),
        "entries": placement.entries,
        **(fields or {}),
    }
    if info.requires:
        if requirements is None:
            from . import packages

            requirements = packages.install
        try:
            requirements(data, list(info.requires))
        except Exception:
            record["requires_failed"] = True
            ledger.write(data, record)  # files are in place; uninstall must still find them
            raise
    ledger.write(data, record)
    return record


def generated_entries(data: Path, paths: list[Path]) -> list[dict]:
    """Ledger entries for files and folders that instamix wrote itself."""
    entries = []
    for path in paths:
        rel = Path(path).relative_to(data).as_posix()
        if Path(path).is_dir():
            entries.append({"path": rel, "kind": "dir"})
        else:
            entries.append({"path": rel, "kind": "copy", "sha256": ledger.sha256(Path(path))})
    return entries


def install(
    path: Path,
    data: Path,
    *,
    copy: bool | None = None,
    run_hooks: bool = False,
    requirements=None,
) -> list[dict]:
    """Install a ``.fontlabext`` folder or every folder in a ``.fontlabextz``."""
    path = Path(path)
    if is_zip(path) and path.is_file():
        with tempfile.TemporaryDirectory(prefix="instamix-") as temp:
            records, hooks = [], []
            for folder in unpack(path, Path(temp)):
                records.append(install_folder(folder, data, copy=copy, requirements=requirements))
                hook = hook_for(folder)
                if hook and hook not in hooks:
                    hooks.append(hook)
            for hook in hooks if run_hooks else []:
                try:
                    runpy.run_path(str(hook), run_name="__main__")
                except Exception as error:  # noqa: BLE001 - the install itself succeeded
                    print(f"instamix: hook {hook.name} failed: {error}", file=sys.stderr)
            return records
    if path.is_dir() and is_ext(path):
        return [install_folder(path, data, copy=copy, requirements=requirements)]
    raise InstallError(f"not a {EXT} folder or {ZIP} file: {path}")


def _ours(path: Path, entry: dict) -> bool:
    if entry["kind"] == "link":
        return path.is_symlink() and os.readlink(path) == entry["target"]
    if entry["kind"] == "copy":
        return path.is_file() and not path.is_symlink() and ledger.sha256(path) == entry["sha256"]
    return path.is_dir() and not path.is_symlink()


def inside(data: Path, path: Path) -> bool:
    """True if ``path`` lies inside ``data``; the last part is not followed."""
    root = Path(os.path.realpath(data))
    parent = Path(os.path.realpath(Path(path).parent))
    return (parent == root or root in parent.parents) and Path(path).name not in ("", ".", "..")


def _entry_path(data: Path, entry: dict) -> Path | None:
    rel = str(entry.get("path", ""))
    if not rel or PurePosixPath(rel).is_absolute() or ".." in PurePosixPath(rel).parts or ":" in rel or "\\" in rel:
        return None
    path = Path(data) / rel
    return path if inside(data, path) else None


def _remove_tracked(data: Path, entries: list[dict]) -> list[dict]:
    """Remove recorded paths that are still ours; return the removed entries."""
    removed = []
    for entry in reversed(entries):
        path = _entry_path(data, entry)
        if path is None or not (path.exists() or path.is_symlink()) or not _ours(path, entry):
            continue
        if entry["kind"] == "dir":
            try:
                path.rmdir()
            except OSError:
                continue  # holds files we did not create
        else:
            path.unlink()
        removed.append(entry)
    return removed


def remove_entries(data: Path, entries: list[dict]) -> list[str]:
    """Remove recorded paths that are still ours; return the ones left behind."""
    removed = {id(e) for e in _remove_tracked(data, entries)}
    kept = []
    for entry in entries:
        path = _entry_path(data, entry)
        if id(entry) not in removed and (path is None or path.exists() or path.is_symlink()):
            kept.append(str(entry.get("path")))
    return kept


def restore_entries(data: Path, entries: list[dict]) -> None:
    """Re-create entries removed by :func:`_remove_tracked` (rollback)."""
    for entry in reversed(entries):  # removal ran children first
        path = _entry_path(data, entry)
        if path is None or path.exists() or path.is_symlink():
            continue
        try:
            if entry["kind"] == "dir":
                path.mkdir()
            elif entry["kind"] == "link":
                os.symlink(entry["target"], path, target_is_directory=Path(entry["target"]).is_dir())
            elif entry.get("source") and Path(entry["source"]).is_file():
                shutil.copy2(entry["source"], path)
        except OSError as error:
            print(f"instamix: could not restore {path}: {error}", file=sys.stderr)


def _remove_tree(data: Path, path: Path) -> None:
    """Delete ``path`` (inside ``data``) without following a symlinked folder."""
    if not inside(data, path):
        raise InstallError(f"refusing to delete outside the data folder: {path}")
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)  # rmtree unlinks nested symlinks, never follows them


def uninstall_links(data: Path, record: dict) -> list[str]:
    return remove_entries(data, record.get("entries", []))


def uninstall(ext_id: str, data: Path) -> list[str]:
    """Uninstall ``ext_id``; return paths left in place because they changed."""
    try:
        record = ledger.read(data, ext_id)
    except ledger.LedgerError as error:
        raise InstallError(str(error)) from error
    if record is None:
        raise InstallError(f"{ext_id} is not installed")
    if record.get("init_script"):
        from . import initscript

        initscript.update(data, remove=True)  # before files go, so the hook never dangles
    kept = uninstall_links(data, record)
    library = library_path(data, ext_id)
    if record.get("library") not in (None, Path(library).relative_to(data).as_posix()):
        raise InstallError(f"ledger for {ext_id} names an unexpected Library path: {record.get('library')!r}")
    if library.exists() or library.is_symlink():
        _remove_tree(data, library)
    ledger.remove(data, ext_id)
    if not ledger.records(data):
        from . import launchers

        launchers.remove_list(data)
    return kept


def installed(data: Path) -> list[dict]:
    return ledger.records(data)
