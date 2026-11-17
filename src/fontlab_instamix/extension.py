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
import stat
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
        env.require_inside(self.data, folder / ".instamix-check")
        missing = []
        while not folder.exists():
            missing.append(folder)
            folder = folder.parent
        for item in reversed(missing):
            env.require_inside(self.data, item / ".instamix-check")
            item.mkdir()
            self.entries.append({"path": self.rel(item), "kind": "dir"})

    def place(self, source: Path, target: Path) -> None:
        env.require_inside(self.data, target)
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
    pattern = pattern.replace("\\", "/")
    if ".." in PurePosixPath(pattern).parts or pattern.startswith("/") or ":" in pattern:
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


def plan(folder: Path, info: manifest.Manifest, name: str, data: Path, *, version: str | None = None) -> list[tuple[Path, Path]]:
    """Return ``(source, target)`` pairs for every file the manifest installs."""
    pairs = []
    for rule in info.install:
        target_dir = Path(data) / dest.resolve(rule.to, name, info.vars, version=version)
        for source, rel in sources(folder, rule.source):
            pairs.append((source, target_dir / rel))
    site = env.site_packages(data, version=version)
    for package in info.packages:
        check_member(package)
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


def _check_library(data: Path, library: Path) -> None:
    for suffix in ("", ".new", ".old", ".prev"):
        path = library.with_name(library.name + suffix)
        env.require_inside(data, path)
        if path.is_symlink():
            raise InstallError(f"refusing symlinked Library staging path: {path}")


def stage(folder: Path, target: Path, data: Path) -> None:
    """Copy ``folder`` to ``target``, replacing an older copy at the last moment."""
    _check_library(data, target)
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


def preflight_plugin_migration(data: Path, pairs: list[tuple[Path, Path]], previous: dict | None) -> None:
    """Refuse distinct legacy bundles that removal would retain before any writes."""
    kinds = {"reporters": "Reporter", "filters": "Filter", "tools": "Tool",
             "palettes": "Palette", "general": "General"}
    roots = set()
    for _, target in pairs:
        parts = target.relative_to(data).parts
        if len(parts) < 3 or parts[0] != "Extensions" or parts[1] not in kinds:
            continue
        suffix = ".fontlab" + kinds[parts[1]].lower()
        if parts[2].endswith(suffix):
            roots.add((data / Path(*parts[:3]), kinds[parts[1]]))
    entries = {p: entry for entry in (previous or {}).get("entries", [])
               if (p := _entry_path(data, entry)) is not None}
    for canonical, kind in roots:
        if not canonical.parent.is_dir():
            continue
        legacy_name = canonical.name[:-len(kind)] + kind
        # Actual directory entries distinguish separate roots from case-insensitive aliases.
        children = {p.name: p for p in canonical.parent.iterdir()}
        legacy = children.get(legacy_name)
        if legacy is None or (canonical.name not in children and canonical.exists() and legacy.samefile(canonical)):
            continue
        env.require_inside(data, legacy)
        paths = [legacy, *legacy.rglob("*")] if legacy.is_dir() and not legacy.is_symlink() else [legacy]
        for path in paths:
            entry = entries.get(path)
            if entry is None or entry.get("kind") not in {"dir", "link", "copy"} or not _ours(path, entry):
                raise InstallError(f"legacy plugin bundle would be retained: {legacy}; preserve or move its owner files before installing {canonical.name}")


def install_folder(
    folder: Path,
    data: Path,
    *,
    copy: bool | None = None,
    requirements=None,
    target: env.Target | None = None,
    editable: bool = False,
    generated: list[tuple[Path, Path]] | None = None,
    fields: dict | None = None,
) -> dict:
    """Install one unpacked ``.fontlabext`` folder; return its ledger record.

    ``generated`` supplies prebuilt (source, target) file pairs copied into
    the same transaction. ``fields`` adds keys to the ledger record.

    ``requirements`` is called as ``requirements(data, list_of_specs)`` when
    the manifest lists ``python.requires`` (``packages.install`` by default).
    ``editable`` links files straight to their real (symlink-resolved)
    sources, e.g. a project checkout, and keeps only the manifest in Library.
    """
    folder = Path(folder)
    data = Path(data)
    info = manifest.load(folder)
    name = basename(folder)
    if name != info.id:
        raise InstallError(f"extension folder basename {name!r} must match manifest id {info.id!r}")
    version = target.version if target else None
    pairs = plan(folder, info, name, data, version=version)
    generated = generated or []
    env.check_folders(data, version=version)
    ledger.check_paths(data, info.id)
    library = library_path(data, info.id)
    _check_library(data, library)
    for _, destination in [*pairs, *generated]:
        env.require_inside(data, destination)
    previous = ledger.read(data, info.id)
    preflight_plugin_migration(data, pairs, previous)
    env.ensure_folders(data, version=version)
    backup = library.with_name(library.name + ".prev")
    if backup.exists() or backup.is_symlink():
        _remove_tree(data, backup)
    placement = Placement(data, default_copy() if copy is None else copy)
    generated_placement = Placement(data, True)
    generated_dirs = [target for source, target in generated if source.is_dir()]
    record_path = ledger.record_path(data, info.id)
    ledger_paths = (record_path, record_path.with_suffix(".tmp"), ledger.ledger_dir(data) / ledger.LOG)
    ledger_before = {
        path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode)) if path.exists() else None
        for path in ledger_paths
    }
    requirement_error = None
    with tempfile.TemporaryDirectory(prefix="instamix-rollback-") as temp:
        removed = []
        directory_modes = {}
        # Snapshot actual installed bytes: generated records may have no source.
        for entry in previous.get("entries", []) if previous else []:
            path = _entry_path(data, entry)
            if path is None or not _ours(path, entry):
                continue
            saved = dict(entry)
            if entry["kind"] == "dir":
                directory_modes[path] = stat.S_IMODE(path.stat().st_mode)
            if entry["kind"] == "copy":
                snapshot = Path(temp) / str(len(removed))
                shutil.copy2(path, snapshot)
                saved["source"] = str(snapshot)
            removed.append(saved)
        library_changed = False
        ledger_attempted = False
        try:
            if previous:
                _remove_tracked(data, previous.get("entries", []))
            if library.exists():
                library.rename(backup)
            library_changed = True
            if editable:
                with tempfile.TemporaryDirectory(prefix="instamix-stage-") as staging:
                    shutil.copy2(manifest.find(folder), Path(staging) / manifest.MANIFEST)
                    stage(Path(staging), library, data)
            else:
                stage(folder, library, data)
            for source, destination in pairs:
                origin = source.resolve() if editable else library / source.relative_to(folder)
                placement.place(origin, destination)
            for source, destination in generated:
                generated_placement.place(source, destination)
            record = {
                "id": info.id,
                "name": info.name,
                "version": info.version,
                "basename": name,
                "library": placement.rel(library),
                "requires": list(info.requires),
                # Intermediate generated parents (e.g. the shared launcher folder) are not owned.
                "entries": placement.entries + [
                    entry for entry in generated_placement.entries
                    if entry["kind"] != "dir" or any(
                        (data / entry["path"]).is_relative_to(folder) for folder in generated_dirs
                    )
                ],
                **(fields or {}),
            }
            if info.requires:
                if requirements is None:
                    from functools import partial

                    from . import packages

                    requirements = partial(packages.install, target=target) if target else packages.install
                try:
                    requirements(data, list(info.requires))
                except Exception as error:  # noqa: BLE001 - commit partial install before re-raising
                    record["requires_failed"] = True
                    requirement_error = error
            ledger_attempted = True
            ledger.write(data, record)
        except Exception:
            remove_entries(data, placement.entries + generated_placement.entries)
            if library_changed:
                if library.exists() or library.is_symlink():
                    _remove_tree(data, library)
                if backup.exists():
                    backup.rename(library)
            restore_modes = {path: mode for path, mode in directory_modes.items() if not path.exists()}
            restore_entries(data, list(reversed(removed)))
            # Restore restrictive directory permissions only after all descendants exist.
            for path, mode in reversed(restore_modes.items()):
                path.chmod(mode)
            if ledger_attempted:
                for path, content in ledger_before.items():
                    ledger._check_file(data, path)
                    if content is None:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_bytes(content[0])
                        path.chmod(content[1])
            raise
        if backup.exists():
            _remove_tree(data, backup)
    if requirement_error is not None:
        raise requirement_error
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
    data: Path | None = None,
    *,
    copy: bool | None = None,
    run_hooks: bool = False,
    requirements=None,
    target: env.Target | None = None,
) -> list[dict]:
    """Install an extension folder, its manifest, or all folders in an archive.

    Archive failures retain the original exception and attach installed_records
    for the extensions already committed before the failure.
    """
    if data is None:
        data = env.data_dir()
    path = Path(path)
    if path.is_file() and path.name.lower() == manifest.MANIFEST:
        path = path.parent
    if is_zip(path) and path.is_file():
        with tempfile.TemporaryDirectory(prefix="instamix-") as temp:
            records, hooks = [], []
            try:
                for folder in unpack(path, Path(temp)):
                    records.append(install_folder(folder, data, copy=copy, requirements=requirements, target=target))
                    hook = hook_for(folder)
                    if hook and hook not in hooks:
                        hooks.append(hook)
            except Exception as error:
                error.installed_records = records.copy()
                raise
            for hook in hooks if run_hooks else []:
                try:
                    runpy.run_path(str(hook), run_name="__main__")
                except Exception as error:  # noqa: BLE001 - the install itself succeeded
                    print(f"instamix: hook {hook.name} failed: {error}", file=sys.stderr)
            return records
    if path.is_dir() and is_ext(path):
        return [install_folder(path, data, copy=copy, requirements=requirements, target=target)]
    raise InstallError(f"not a {EXT} folder, its {manifest.MANIFEST}, or {ZIP} file: {path}")


def _ours(path: Path, entry: dict) -> bool:
    if entry["kind"] == "link":
        return path.is_symlink() and os.readlink(path) == entry["target"]
    if entry["kind"] == "copy":
        return path.is_file() and not path.is_symlink() and ledger.sha256(path) == entry["sha256"]
    return path.is_dir() and not path.is_symlink()


def inside(data: Path, path: Path) -> bool:
    """True if ``path`` lies inside ``data``; the last part is not followed."""
    return env.inside(data, path)


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


def _created_dirs(data: Path, entries: list[dict]) -> set[Path]:
    """Folders instamix created: ``dir`` entries of *entries* and of every ledger record."""
    owned = list(entries)
    for record in ledger.records(data):
        owned += record.get("entries", [])
    paths = (_entry_path(data, e) for e in owned if e.get("kind") == "dir")
    return {p for p in paths if p is not None}


def _prune_empty(data: Path, path: Path | None, created: set[Path]) -> None:
    """Remove now-empty folders above *path* that instamix created, never ``Scripts/``."""
    scripts = Path(data) / "Scripts"
    if path is None:
        return
    folder = path.parent
    while folder != scripts and scripts in folder.parents and folder in created:
        try:
            folder.rmdir()
        except OSError:
            return
        folder = folder.parent


def remove_entries(data: Path, entries: list[dict]) -> list[str]:
    """Remove recorded paths that are still ours; return the ones left behind."""
    done = _remove_tracked(data, entries)
    created = _created_dirs(data, entries) if done else set()
    for entry in done:
        _prune_empty(data, _entry_path(data, entry), created)
    removed = {id(e) for e in done}
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


def uninstall(ext_id: str, data: Path | None = None) -> list[str]:
    """Uninstall ``ext_id``; return paths left in place because they changed."""
    if data is None:
        data = env.data_dir()
    try:
        ledger.check_paths(data, ext_id)
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


def installed(data: Path | None = None) -> list[dict]:
    if data is None:
        data = env.data_dir()
    return ledger.records(data)
