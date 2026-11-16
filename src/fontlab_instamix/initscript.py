# this_file: src/fontlab_instamix/initscript.py
"""Add or remove FontApp's startup block in ``<data>/initScript.py``.

The block is byte-identical to the one written by fontlabapp's
``plugins.startup`` module and the legacy installer, so either tool can
remove what the other added. Lines outside the block are never touched.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

FILE = "initScript.py"
APP_ID = "com.fontlab.fontlabapp"
BEGIN = b"# BEGIN fontlabapp.plugins (owned separator)"
END = b"# END fontlabapp.plugins"
HOOK = b"\n".join(
    [
        BEGIN,
        b"try:",
        b"    from fly.ap.plugins import install as _fontlab_plugins_install",
        b"    _fontlab_plugins_install()",
        b"except Exception as _fontlab_plugins_error:",
        b"    print('FontLab plugins startup:', _fontlab_plugins_error)",
        END,
        b"",
    ]
)
_BLOCK = re.compile(rb"\r?\n" + re.escape(BEGIN) + rb"\r?\n.*?(?m:^" + re.escape(END) + rb"\r?\n)", re.DOTALL)


def updated(contents: bytes, remove: bool) -> bytes:
    """Return *contents* with the block added or removed."""
    if BEGIN in contents or END in contents:
        match = _BLOCK.search(contents)
        if contents.count(BEGIN) != 1 or contents.count(END) != 1 or not match:
            raise ValueError("Malformed or duplicate fontlabapp.plugins startup markers")
        return contents[: match.start()] + contents[match.end() :] if remove else contents
    if remove:
        return contents
    newline = b"\r\n" if b"\r\n" in contents else b"\n"
    return contents + newline + HOOK.replace(b"\n", newline)


def update(data: Path, *, remove: bool = False) -> bool:
    """Add (or remove) the block in ``data/initScript.py``; return whether it changed."""
    path = Path(data) / FILE
    if path.is_symlink():
        raise ValueError(f"Refusing a symlink {FILE}")
    contents = path.read_bytes() if path.exists() else b""
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    new = updated(contents, remove)
    if new == contents:
        return False
    handle, temp = tempfile.mkstemp(prefix=".initScript-", dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(new)
        os.chmod(temp, mode)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise
    return True
