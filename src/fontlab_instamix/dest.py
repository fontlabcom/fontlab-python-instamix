# this_file: src/fontlab_instamix/dest.py
"""Resolve manifest ``to`` rules into paths inside the FontLab data folder.

Rules (see PLAN.md): ``.`` and ``./`` mean the target root, ``{}`` is the
extension name without ``.fontlabext``, ``{var}`` comes from manifest
``vars``, any other text is a subfolder. Unknown variables, ``..`` and
``\\`` or ``:`` inside a part (after expansion, on every platform) are
errors. The first path part names the target, matched case-insensitively.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

TARGETS = ("Scripts", "Actions", "Codepage", "Data", "Encoding", "Extensions", "site-packages")
RESERVED = {"extensions": {".instamix", "library"}}  # instamix's own folders
SITE_PACKAGES = "python/3.11/site-packages"
_VAR = re.compile(r"\{([^{}]*)\}")


class DestError(ValueError):
    """A ``to`` rule that cannot be resolved safely."""


def target_name(name: str) -> str:
    """Return the canonical target for ``name`` (case-insensitive)."""
    for target in TARGETS:
        if target.lower() == name.lower():
            return target
    raise DestError(f"unknown target {name!r}; use one of {', '.join(TARGETS)}")


def target_root(target: str) -> str:
    """Return the data-folder-relative directory of a canonical target."""
    return SITE_PACKAGES if target == "site-packages" else target


def expand(text: str, basename: str, variables: dict[str, str]) -> str:
    """Replace ``{}`` and ``{var}`` placeholders in ``text``."""

    def sub(match: re.Match[str]) -> str:
        key = match.group(1)
        if key == "":
            return basename
        if key not in variables:
            raise DestError(f"unknown variable {{{key}}} in {text!r}")
        value = str(variables[key])
        if "\\" in value or ":" in value or ".." in PurePosixPath(value).parts:
            raise DestError(f"variable {{{key}}} may not contain '\\', ':' or '..': {value!r}")
        return value

    return _VAR.sub(sub, text)


def resolve(rule: str, basename: str, variables: dict[str, str] | None = None) -> str:
    """Resolve ``rule`` to a POSIX path relative to the data folder.

    The result is a directory: sources are placed inside it.
    """
    if not rule or rule.startswith(("/", "\\")) or ":" in rule.split("/")[0][1:2]:
        raise DestError(f"destination must be relative: {rule!r}")
    expanded = expand(rule.replace("\\", "/"), basename, variables or {})
    parts = [p for p in expanded.split("/") if p not in ("", ".")]
    if not parts:
        raise DestError(f"destination has no target: {rule!r}")
    if any(p == ".." for p in parts):
        raise DestError(f"destination escapes its target: {rule!r}")
    if any("\\" in p or ":" in p for p in parts):  # Windows separators or drives
        raise DestError(f"destination parts may not contain '\\' or ':': {expanded!r}")
    root = target_root(target_name(parts[0]))
    reserved = RESERVED.get(root.lower())
    if reserved is not None and (len(parts) < 2 or parts[1].lower() in reserved):
        raise DestError(f"{root} needs a subfolder other than {', '.join(sorted(reserved))}: {rule!r}")
    return str(PurePosixPath(root, *parts[1:]))
