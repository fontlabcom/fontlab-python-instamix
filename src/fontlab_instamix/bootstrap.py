# this_file: src/fontlab_instamix/bootstrap.py
"""Install a project checkout into FontLab from its ``install.vfpy``.

A project's ``install.vfpy`` needs two lines::

    import fontlab_instamix.bootstrap as b
    b.install_project(__file__)

It reads ``[tool.fontlab-install]`` from the project's ``pyproject.toml``
(keys: ``id``, ``name``, ``packages``, ``scripts``, ``extensions``,
``dependencies``) and turns it into a ``.fontlabext`` installed by
:mod:`fontlab_instamix.extension`, so the ledger and uninstall are shared.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import env, extension, manifest

DEFAULT_SCRIPTS = "Scripts"


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
    extra: dict = field(default_factory=dict)


def _list(value, key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return tuple(value)
    raise BootstrapError(f"[tool.fontlab-install] {key} must be a string or list of strings")


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
        raise BootstrapError(f"{root / 'pyproject.toml'} has no [tool.fontlab-install] table")
    ext_id = table.get("id")
    if not isinstance(ext_id, str) or not manifest.ID_PATTERN.match(ext_id):
        raise BootstrapError("[tool.fontlab-install] id must be a reverse-DNS id like com.example.tool")
    project = data.get("project", {})
    scripts = _list(table.get("scripts"), "scripts")
    if not scripts and (root / DEFAULT_SCRIPTS).is_dir():
        scripts = (DEFAULT_SCRIPTS,)
    extensions = table.get("extensions", "")
    if not isinstance(extensions, str):
        raise BootstrapError("[tool.fontlab-install] extensions must be a folder name")
    known = {"id", "name", "packages", "scripts", "extensions", "dependencies"}
    return Project(
        root=root,
        id=ext_id,
        name=str(table.get("name") or project.get("name") or ext_id),
        version=str(project.get("version") or "0"),
        packages=_list(table.get("packages"), "packages"),
        scripts=scripts,
        extensions=extensions,
        dependencies=_list(table.get("dependencies"), "dependencies"),
        extra={k: v for k, v in table.items() if k not in known},
    )


def manifest_data(project: Project) -> dict:
    """Manifest describing the project checkout as an extension."""
    rules = []
    for folder in project.scripts:
        to = "Scripts/{}" if folder == DEFAULT_SCRIPTS else f"Scripts/{Path(folder).name}"
        rules.append({"from": folder, "to": to})
    for package in project.packages:
        if not (project.root / package).is_dir():
            raise BootstrapError(f"package folder {package!r} not found in {project.root}")
    data = {
        "id": project.id,
        "name": project.name,
        "version": project.version,
        "python": {"packages": list(project.packages), "requires": []},
        "install": rules,
    }
    manifest.parse(data)
    return data


def sibling_dependencies(project: Project) -> tuple[list[Path], list[str]]:
    """Split dependencies into sibling checkouts (with install.vfpy) and uv specs."""
    siblings, specs = [], []
    for spec in project.dependencies:
        name = spec.split(";")[0].strip()
        for sep in "<>=!~[ ":
            name = name.split(sep)[0]
        sibling = project.root.parent / name
        if (sibling / "install.vfpy").is_file() and (sibling / "pyproject.toml").is_file():
            siblings.append(sibling)
        else:
            specs.append(spec)
    return siblings, specs


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
    linked into ``Scripts/<id>``, sibling dependency checkouts are installed
    first, other dependencies go through uv. Returns the ledger records.
    """
    data = env.data_dir(data)
    project = read_project(Path(start))
    seen = _seen if _seen is not None else set()
    if project.root in seen:
        return []
    seen.add(project.root)
    records: list[dict] = []
    siblings, specs = sibling_dependencies(project)
    for sibling in siblings:
        records += install_project(sibling, data, copy=copy, requirements=requirements, _seen=seen)
    data_manifest = manifest_data(project)
    data_manifest["python"]["requires"] = specs
    records.append(_install_checkout(project, data_manifest, data, copy, requirements))
    if project.extensions and (project.root / project.extensions).is_dir():
        for folder in sorted((project.root / project.extensions).rglob("*")):
            nested = any(extension.is_ext(part) for part in folder.relative_to(project.root).parts[:-1])
            if folder.is_dir() and extension.is_ext(folder.name) and not nested:
                records += extension.install(folder, data, copy=copy, requirements=requirements)
    return records


def _install_checkout(project: Project, data_manifest: dict, data: Path, copy, requirements) -> dict:
    """Install the checkout through a tiny generated ``.fontlabext`` of links."""
    with tempfile.TemporaryDirectory(prefix="instamix-project-") as temp:
        folder = Path(temp) / f"{project.id}.fontlabext"
        folder.mkdir()
        copied = False
        for rel in [r["from"] for r in data_manifest["install"]] + data_manifest["python"]["packages"]:
            target = folder / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            source = project.root / rel
            try:
                target.symlink_to(source, target_is_directory=source.is_dir())
            except OSError:  # Windows without symlink rights: copy (not live)
                copied = True
                if source.is_dir():
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
        (folder / manifest.MANIFEST).write_text(json.dumps(data_manifest), encoding="utf-8")
        # Files copied into the temp folder vanish afterwards, so never link to them.
        copy = True if copied else copy
        return extension.install_folder(folder, data, copy=copy, requirements=requirements, editable=True)
