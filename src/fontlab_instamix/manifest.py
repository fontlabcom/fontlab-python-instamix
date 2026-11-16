# this_file: src/fontlab_instamix/manifest.py
"""Read and validate ``manifest.fontlabextj`` (strict JSON)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST = "manifest.fontlabextj"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z0-9][a-z0-9-]*)+$")
_KEYS = {"id", "name", "version", "description", "min_fontlab", "python", "vars", "install", "this_file"}
_PYTHON_KEYS = {"requires", "packages"}
_RULE_KEYS = {"from", "to"}


class ManifestError(ValueError):
    """The manifest is missing, malformed or has unknown keys."""


@dataclass(frozen=True)
class Rule:
    source: str
    to: str


@dataclass(frozen=True)
class Manifest:
    id: str
    name: str
    version: str
    description: str = ""
    min_fontlab: str = ""
    requires: tuple[str, ...] = ()
    packages: tuple[str, ...] = ()
    vars: dict[str, str] = field(default_factory=dict)
    install: tuple[Rule, ...] = ()


def _strings(value, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise ManifestError(f"{where} must be a list of non-empty strings")
    return tuple(value)


def _unknown(data: dict, allowed: set[str], where: str) -> None:
    extra = sorted(set(data) - allowed)
    if extra:
        raise ManifestError(f"unknown key(s) in {where}: {', '.join(extra)}")


def parse(data: object) -> Manifest:
    """Validate decoded JSON and return a :class:`Manifest`."""
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    _unknown(data, _KEYS, "manifest")
    for key in ("id", "name", "version"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ManifestError(f"manifest needs a non-empty string {key!r}")
    if not ID_PATTERN.match(data["id"]):
        raise ManifestError(f"id must be lowercase reverse-DNS like com.example.tool: {data['id']!r}")
    for key in ("description", "min_fontlab"):
        if not isinstance(data.get(key, ""), str):
            raise ManifestError(f"{key} must be a string")
    python = data.get("python", {})
    if not isinstance(python, dict):
        raise ManifestError("python must be an object")
    _unknown(python, _PYTHON_KEYS, "python")
    variables = data.get("vars", {})
    if not isinstance(variables, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in variables.items()
    ):
        raise ManifestError("vars must map strings to strings")
    rules = data.get("install", [])
    if not isinstance(rules, list):
        raise ManifestError("install must be a list")
    parsed = []
    for index, rule in enumerate(rules):
        where = f"install[{index}]"
        if not isinstance(rule, dict):
            raise ManifestError(f"{where} must be an object")
        _unknown(rule, _RULE_KEYS, where)
        if not all(isinstance(rule.get(k), str) and rule[k] for k in _RULE_KEYS):
            raise ManifestError(f"{where} needs string 'from' and 'to'")
        parsed.append(Rule(rule["from"], rule["to"]))
    return Manifest(
        id=data["id"],
        name=data["name"],
        version=data["version"],
        description=data.get("description", ""),
        min_fontlab=data.get("min_fontlab", ""),
        requires=_strings(python.get("requires", []), "python.requires"),
        packages=_strings(python.get("packages", []), "python.packages"),
        vars=dict(variables),
        install=tuple(parsed),
    )


def find(folder: Path) -> Path:
    """Return the manifest path inside ``folder`` (name matched case-insensitively)."""
    for child in Path(folder).iterdir():
        if child.is_file() and child.name.lower() == MANIFEST:
            return child
    raise ManifestError(f"no {MANIFEST} in {folder}")


def load(folder: Path) -> Manifest:
    """Read and validate the manifest of a ``.fontlabext`` folder."""
    path = find(folder)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"{path}: invalid JSON: {exc}") from exc
    return parse(data)
