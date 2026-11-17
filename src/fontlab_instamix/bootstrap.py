# this_file: src/fontlab_instamix/bootstrap.py
"""Install a project checkout into FontLab from its ``install.vfpy``.

A project's ``install.vfpy`` needs two lines::

    import fontlab_instamix.bootstrap as b
    b.install_project(__file__)

It reads ``[tool.fontlab-install]`` from the project's ``pyproject.toml``
(keys: ``id``, ``name``, ``packages``, ``scripts``, ``extensions``,
``dependencies``, ``init-script``) and turns it into a ``.fontlabext``
installed by :mod:`fontlab_instamix.extension`, so the ledger and uninstall
are shared. Like the legacy ``install.vfpy`` it replaces, it removes an
earlier legacy install first, writes a ``.dist-info``, maps the top-level
``Scripts/`` onto FontLab's Scripts and ``Extensions/<kind>/`` bundles onto
FontLab's Extensions, and adds the FontApp startup block when asked.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import (
    distinfo,
    env,
    extension,
    initscript,
    launchers,
    ledger,
    legacy,
    manifest,
    markers,
    vcs,
)

DEFAULT_SCRIPTS = "Scripts"
DOCS_PREFIXES = (
    "readme",
    "license",
    "licence",
    "changelog",
)  # top-level Scripts docs stay out


class BootstrapError(RuntimeError):
    """The project has no usable ``[tool.fontlab-install]`` table."""


@dataclass(frozen=True)
class Project:
    root: Path
    id: str
    name: str
    version: str
    packages: tuple[str, ...] = ()
    scripts: tuple[str, ...] = ()
    extensions: str = ""
    dependencies: tuple[str, ...] = ()
    extras: dict = field(default_factory=dict)
    init_script: bool = False
    extra: dict = field(default_factory=dict)


def _list(value, key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return tuple(value)
    raise BootstrapError(
        f"[tool.fontlab-install] {key} must be a string or list of strings"
    )


def find_root(start: Path) -> Path:
    """Folder holding ``pyproject.toml`` at or above ``start``."""
    start = Path(start).resolve()
    for folder in (start, *start.parents) if start.is_dir() else start.parents:
        if (folder / "pyproject.toml").is_file():
            return folder
    raise BootstrapError(f"no pyproject.toml at or above {start}")


def read_project(start: Path) -> Project:
    """Parse ``[tool.fontlab-install]`` from the nearest ``pyproject.toml``."""
    root = find_root(start)
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    table = data.get("tool", {}).get("fontlab-install")
    if not isinstance(table, dict):
        raise BootstrapError(
            f"{root / 'pyproject.toml'} has no [tool.fontlab-install] table"
        )
    ext_id = table.get("id")
    if not isinstance(ext_id, str) or not manifest.ID_PATTERN.match(ext_id):
        raise BootstrapError(
            "[tool.fontlab-install] id must be a reverse-DNS id like com.example.tool"
        )
    project = data.get("project", {})
    extensions = table.get("extensions", "")
    if not isinstance(extensions, str):
        raise BootstrapError("[tool.fontlab-install] extensions must be a folder name")
    init = table.get("init-script", ext_id == initscript.APP_ID)
    if not isinstance(init, bool):
        raise BootstrapError("[tool.fontlab-install] init-script must be true or false")
    known = {
        "id",
        "name",
        "packages",
        "scripts",
        "extensions",
        "dependencies",
        "init-script",
    }
    return Project(
        root=root,
        id=ext_id,
        name=str(table.get("name") or project.get("name") or ext_id),
        version=vcs.project_version(root, data),
        packages=_packages(table, data),
        scripts=_scripts(root, table),
        extensions=extensions,
        dependencies=_list(
            table.get("dependencies", project.get("dependencies")), "dependencies"
        ),
        extras=_extras(project),
        init_script=init,
        extra={k: v for k, v in table.items() if k not in known},
    )


def _packages(table: dict, data: dict) -> tuple[str, ...]:
    """Listed packages, else the hatch wheel packages (as the legacy installer did)."""
    if "packages" in table:
        return _list(table["packages"], "packages")
    wheel = (
        data.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
    )
    return _list(wheel.get("packages"), "packages")


def _scripts(root: Path, table: dict) -> tuple[str, ...]:
    """The top-level ``Scripts`` folder (exact case) plus the listed folders."""
    listed = [
        s.replace("\\", "/").strip("/") for s in _list(table.get("scripts"), "scripts")
    ]
    top = (
        [DEFAULT_SCRIPTS]
        if DEFAULT_SCRIPTS in os.listdir(root) and (root / DEFAULT_SCRIPTS).is_dir()
        else []
    )
    return tuple(dict.fromkeys(top + listed))


def _extras(project: dict) -> dict[str, list[str]]:
    extras = project.get("optional-dependencies", {})
    if not isinstance(extras, dict):
        raise BootstrapError("[project.optional-dependencies] must be a table")
    return {
        key: list(_list(value, f"optional-dependencies.{key}"))
        for key, value in extras.items()
    }


def _script_rules(root: Path, folder: str) -> list[dict]:
    """Rules for one Scripts folder. The top-level ``Scripts`` maps child by
    child, skipping README/LICENSE/Markdown docs that would collide in
    FontLab's shared Scripts root; their subfolders still install whole."""
    if folder != DEFAULT_SCRIPTS:
        return [{"from": folder, "to": f"Scripts/{folder}"}]
    rules = []
    for child in sorted((root / folder).iterdir()):
        lowered = child.name.lower()
        if extension._junk(Path(child.name)) or (
            child.is_file() and lowered.startswith(DOCS_PREFIXES)
        ):
            continue
        if child.is_file() and lowered.endswith(".md"):
            continue
        to = f"Scripts/{child.name}" if child.is_dir() else "Scripts"
        rules.append({"from": f"{folder}/{child.name}", "to": to})
    return rules


def manifest_data(project: Project) -> dict:
    """Manifest describing the project checkout as an extension.

    The top-level ``Scripts`` folder maps onto FontLab's Scripts; any other
    listed folder maps onto ``Scripts/<folder>``. Plugin bundles below
    ``<extensions>/<kind>/`` map onto FontLab's ``Extensions/<kind>/``.
    """
    rules = [rule for f in project.scripts for rule in _script_rules(project.root, f)]
    rules += [
        {"from": rel, "to": "Extensions/" + "/".join(PurePosixPath(rel).parts[-2:])}
        for rel in bundles(project)
    ]
    for package in project.packages:
        if not (project.root / package).is_dir():
            raise BootstrapError(
                f"package folder {package!r} not found in {project.root}"
            )
    data = {
        "id": project.id,
        "name": project.name,
        "version": project.version,
        "python": {"packages": list(project.packages), "requires": []},
        "install": rules,
    }
    manifest.parse(data)
    return data


def bundles(project: Project) -> list[str]:
    """``<extensions>/<kind>/<Name>.fontlab<Kind>`` folders that hold a ``plugin.json``."""
    if not project.extensions or not (project.root / project.extensions).is_dir():
        return []
    found = []
    for kind in sorted((project.root / project.extensions).iterdir()):
        for bundle in sorted(kind.iterdir()) if kind.is_dir() else []:
            if (
                bundle.is_dir()
                and ".fontlab" in bundle.suffix
                and (bundle / "plugin.json").is_file()
            ):
                found.append(bundle.relative_to(project.root).as_posix())
    return found


def sibling_dependencies(project: Project) -> tuple[list[Path], list[str]]:
    """Split dependencies into sibling checkouts (with install.vfpy) and uv specs.

    Dependencies whose environment marker does not apply to FontLab's
    Python are skipped.
    """
    siblings, specs = [], []
    for spec in project.dependencies:
        if not markers.applies(spec):
            continue
        name = markers.split(spec)[0]
        for sep in "<>=!~[ (@":
            name = name.split(sep)[0]
        sibling = _sibling(project.root.parent, name.strip(), skip=project.root)
        if sibling:
            siblings.append(sibling)
        else:
            specs.append(spec)
    return siblings, specs


def _norm(name: str) -> str:
    """PEP 503 name normalisation (``Foo_Bar.baz`` -> ``foo-bar-baz``)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _sibling(parent: Path, name: str, skip: Path | None = None) -> Path | None:
    """Find the checkout beside *skip* that installs the dependency *name*.

    Only folders with install.vfpy and a pyproject.toml holding a
    ``[tool.fontlab-install]`` table with a valid ``id`` count, matched by that
    table's ``name`` or ``[project].name`` (never by folder name alone), so
    unrelated checkouts such as TypeRig are left to uv. First sorted folder wins.
    """
    wanted = _norm(name)
    if not wanted or not parent.is_dir():
        return None
    for folder in sorted(parent.iterdir()):
        if folder == skip or not (folder / "install.vfpy").is_file():
            continue
        try:
            doc = tomllib.loads((folder / "pyproject.toml").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        tool, project = doc.get("tool"), doc.get("project")
        table = tool.get("fontlab-install") if isinstance(tool, dict) else None
        if not isinstance(table, dict) or not manifest.ID_PATTERN.match(str(table.get("id", ""))):
            continue
        names = {table.get("name"), project.get("name") if isinstance(project, dict) else None}
        if wanted in {_norm(n) for n in names if isinstance(n, str)}:
            return folder
    return None


def install_project(
    start,
    data: Path | None = None,
    *,
    copy: bool | None = None,
    requirements=None,
    _seen: set | None = None,
) -> list[dict]:
    """Install the project around ``start`` (usually ``__file__``).

    Packages are linked from the checkout (an editable install), scripts are
    linked into FontLab's Scripts, sibling dependency checkouts are installed
    first, other dependencies go through uv. A legacy ``install.vfpy``
    install of the same id is removed first. Returns the ledger records.
    """
    data = env.data_dir(data)
    project = read_project(Path(start))
    seen = _seen if _seen is not None else set()
    if project.root in seen:
        return []
    seen.add(project.root)
    data_manifest = manifest_data(project)
    info = manifest.parse(data_manifest)
    pairs = extension.plan(project.root, info, project.id, data)
    extension.preflight_plugin_migration(data, pairs, ledger.read(data, project.id))
    records: list[dict] = []
    siblings, specs = sibling_dependencies(project)
    for sibling in siblings:
        records += install_project(
            sibling, data, copy=copy, requirements=requirements, _seen=seen
        )
    data_manifest["python"]["requires"] = specs
    records.append(_install_checkout(project, data_manifest, data, copy, requirements))
    launchers.write_list(data)
    if project.extensions and (project.root / project.extensions).is_dir():
        for folder in sorted((project.root / project.extensions).rglob("*")):
            nested = any(
                extension.is_ext(part)
                for part in folder.relative_to(project.root).parts[:-1]
            )
            if folder.is_dir() and extension.is_ext(folder.name) and not nested:
                records += extension.install(
                    folder, data, copy=copy, requirements=requirements
                )
    return records


def _install_checkout(
    project: Project, data_manifest: dict, data: Path, copy, requirements
) -> dict:
    """Install the checkout through a tiny generated ``.fontlabext`` of links."""
    with tempfile.TemporaryDirectory(prefix="instamix-project-") as temp:
        folder = Path(temp) / f"{project.id}.fontlabext"
        folder.mkdir()
        copied = False
        for rel in [r["from"] for r in data_manifest["install"]] + data_manifest[
            "python"
        ]["packages"]:
            copied = _mirror(project.root / rel, folder / rel) or copied
        (folder / manifest.MANIFEST).write_text(
            json.dumps(data_manifest), encoding="utf-8"
        )
        generated_root = Path(temp) / "generated"
        written = _finish(project, data_manifest, generated_root)
        generated = [
            (path, data / path.relative_to(generated_root))
            for path in written
            if path.parent not in written
        ]
        migrated = migrate_legacy(project, folder, data)
        # Files copied into the temp folder vanish afterwards, so never link to them.
        copy = True if copied else copy
        record = _install_after_migration(
            migrated,
            project.id,
            lambda: extension.install_folder(
                folder,
                data,
                copy=copy,
                requirements=requirements,
                editable=True,
                generated=generated,
                fields={"init_script": True} if project.init_script else None,
            ),
            data,
        )
    if project.init_script:
        initscript.update(data)
    return record


def _install_after_migration(migrated, ext_id: str, install, data: Path | None = None):
    """Run *install*; after a legacy migration, say how to recover from a failure."""
    try:
        return install()
    except Exception as exc:
        if not migrated:
            raise
        legacy.restore(migrated.get("moved") or [], data, ext_id)
        if migrated.get("backup_only"):
            raise BootstrapError(
                f"The new install of {ext_id} failed: {exc}. Files moved aside from a legacy install were put back. Fix the cause and run install.vfpy again."
            ) from exc
        raise BootstrapError(
            f"The legacy install of {ext_id} was removed, but the new install failed: {exc}. Fix the cause and run install.vfpy again."
        ) from exc


def _mirror(source: Path, target: Path) -> bool:
    """Link *source* at *target*; copy when links fail. Return True if copied."""
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.symlink_to(source, target_is_directory=source.is_dir())
        return False
    except OSError:  # Windows without symlink rights: copy (not live)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        return True


def migrate_legacy(project: Project, folder: Path, data: Path) -> dict | None:
    """Remove a legacy ``install.vfpy`` install of this project, if one is active."""
    info = manifest.load(folder)
    pairs = extension.plan(folder, info, extension.basename(folder), data)
    files = [source for source, _ in pairs if source.is_file()]
    known = {ledger.sha256(source.resolve()) for source in files}
    targets = {target.relative_to(data).as_posix() for _, target in pairs}
    site = env.site_packages(data).relative_to(data).as_posix()
    targets |= {f"{site}/{distinfo.folder_name(project.name, project.version)}"}
    return legacy.migrate(data, project.id, known, targets)


def _finish(project: Project, data_manifest: dict, data: Path) -> list[Path]:
    """Write the dist-info and the uninstall launcher; return them, folders first."""
    requires = list(project.dependencies)
    packages = [Path(package).name for package in project.packages]
    written = distinfo.write(
        data, project.name, project.version, requires, project.extras, packages
    )
    return [written[0].parent, *written, *launchers.write_uninstaller(data, project.id)]
