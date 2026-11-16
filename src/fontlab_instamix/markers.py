# this_file: src/fontlab_instamix/markers.py
"""Evaluate PEP 508 environment markers for FontLab's embedded Python.

Used by bootstrap to decide which dependencies apply. The environment is
FontLab's target (Python 3.11 on this machine's OS), not the interpreter
that runs instamix.
"""

from __future__ import annotations

import platform
import re
import sys

from . import env

VERSION_VARS = {"python_version", "python_full_version", "implementation_version", "platform_release"}
_TOKEN = re.compile(
    r"\s*(?:(?P<str>'[^']*'|\"[^\"]*\")|(?P<op>===|==|!=|<=|>=|~=|<|>|not\s+in\b|in\b)"
    r"|(?P<paren>[()])|(?P<word>[A-Za-z_][A-Za-z0-9_.]*))"
)


class MarkerError(ValueError):
    """A marker could not be parsed."""


def environment(extra: str = "") -> dict[str, str]:
    """Return the marker variables for FontLab's Python on this machine."""
    system = platform.system()
    return {
        "python_version": env.FONTLAB_PYTHON,
        "python_full_version": env.FONTLAB_PYTHON + ".0",
        "implementation_name": "cpython",
        "implementation_version": env.FONTLAB_PYTHON + ".0",
        "platform_python_implementation": "CPython",
        "sys_platform": sys.platform,
        "os_name": "nt" if sys.platform == "win32" else "posix",
        "platform_system": system,
        "platform_machine": env.machine(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "extra": extra,
    }


def _tokens(text: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    while pos < len(text.rstrip()):
        match = _TOKEN.match(text, pos)
        if not match or match.end() == pos:
            raise MarkerError(f"cannot parse marker {text!r} at {pos}")
        kind = match.lastgroup or ""
        out.append((kind, " ".join(match.group(kind).split())))
        pos = match.end()
    return out


_RELEASE = re.compile(r"\d+(?:\.\d+)*")
_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def _version(text: str) -> tuple[int, ...] | None:
    """Numeric release tuple of *text*, or None when it is not a plain version."""
    return tuple(int(part) for part in text.split(".")) if _RELEASE.fullmatch(text) else None


def _padded(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    size = max(len(a), len(b))
    return a + (0,) * (size - len(a)), b + (0,) * (size - len(b))


def _compare(left: str, op: str, right: str, versions: bool) -> bool:
    """Compare as versions when both sides are plain versions, else as strings (PEP 508)."""
    if op == "in":
        return left in right
    if op == "not in":
        return left not in right
    if op == "===":
        return left == right
    a, b = (_version(left), _version(right)) if versions else (None, None)
    if a is None or b is None:
        return left == right if op == "~=" else _OPS[op](left, right)
    if op == "~=":
        prefix = b[:-1]
        a, b = _padded(a, b)
        return a >= b and a[: len(prefix)] == prefix
    return _OPS[op](*_padded(a, b))


class _Parser:
    def __init__(self, text: str, variables: dict[str, str]):
        self.items, self.pos, self.vars = _tokens(text), 0, variables

    def peek(self) -> tuple[str, str]:
        return self.items[self.pos] if self.pos < len(self.items) else ("", "")

    def take(self) -> tuple[str, str]:
        item = self.peek()
        if not item[0]:
            raise MarkerError("marker ends too early")
        self.pos += 1
        return item

    def expr(self) -> bool:
        value = self.conj()
        while self.peek() == ("word", "or"):
            self.take()
            value = self.conj() or value
        return value

    def conj(self) -> bool:
        value = self.atom()
        while self.peek() == ("word", "and"):
            self.take()
            value = self.atom() and value
        return value

    def atom(self) -> bool:
        if self.peek() == ("paren", "("):
            self.take()
            value = self.expr()
            if self.take() != ("paren", ")"):
                raise MarkerError("missing ')'")
            return value
        left, (kind, op), right = self.operand(), self.take(), self.operand()
        if kind != "op":
            raise MarkerError(f"expected an operator, got {op!r}")
        versions = left[1] in VERSION_VARS or right[1] in VERSION_VARS
        if "extra" in (left[1], right[1]):
            left, right = (_extra(left), _extra(right))
        return _compare(left[0], op, right[0], versions and op not in ("in", "not in"))

    def operand(self) -> tuple[str, str]:
        kind, text = self.take()
        if kind == "str":
            return text[1:-1], ""
        if kind == "word" and text in self.vars:
            return self.vars[text], text
        raise MarkerError(f"unknown marker variable {text!r}")


def _extra(item: tuple[str, str]) -> tuple[str, str]:
    return re.sub(r"[-_.]+", "-", item[0]).lower(), item[1]


def evaluate(marker: str, extra: str = "") -> bool:
    """Return whether *marker* holds for FontLab's Python; an empty marker holds."""
    if not marker.strip():
        return True
    parser = _Parser(marker, environment(extra))
    value = parser.expr()
    if parser.peek()[0]:
        raise MarkerError(f"unexpected {parser.peek()[1]!r} in marker {marker!r}")
    return value


def split(spec: str) -> tuple[str, str]:
    """Split a requirement into (requirement, marker); URL requirements need ' ;'."""
    pattern = r"\s+;\s*" if "@" in spec.split(";", 1)[0] else r"\s*;\s*"
    parts = re.split(pattern, spec, maxsplit=1)
    return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")


def applies(spec: str, extra: str = "") -> bool:
    """Return whether requirement *spec* applies to FontLab's Python."""
    return evaluate(split(spec)[1], extra)
