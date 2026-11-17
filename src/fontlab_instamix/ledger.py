# this_file: src/fontlab_instamix/ledger.py
"""Install records: ``Extensions/.instamix/<id>.json`` plus a JSONL log.

The ledger lives outside ``Extensions/Library``, which holds only installed
extension copies.

A record lists every path instamix created for one extension, with a kind
(``link``, ``copy`` or ``dir``) and, for copies, a SHA-256, so uninstall
removes exactly those and leaves anything the user changed.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

from . import env

LEDGER_DIR = "Extensions/.instamix"
SAFE_ID = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]*$")


class LedgerError(ValueError):
    """An extension id that cannot name a ledger record safely."""


def check_id(ext_id: str) -> str:
    """Return ``ext_id`` if it is a safe reverse-DNS-like name, else raise."""
    if not isinstance(ext_id, str) or not SAFE_ID.match(ext_id) or ".." in ext_id:
        raise LedgerError(f"invalid extension id: {ext_id!r}")
    return ext_id
LOG = "install.log"


def ledger_dir(data: Path) -> Path:
    return Path(data) / LEDGER_DIR


def record_path(data: Path, ext_id: str) -> Path:
    return ledger_dir(data) / f"{check_id(ext_id)}.json"


def check_paths(data: Path, ext_id: str) -> None:
    """Preflight record, temporary record and log before changing an install."""
    path = record_path(data, ext_id)
    for target in (path, path.with_suffix(".tmp"), ledger_dir(data) / LOG):
        _check_file(data, target)


def _check_file(data: Path, path: Path) -> None:
    env.require_inside(data, path)
    if path.is_symlink():
        raise LedgerError(f"refusing symlinked ledger file: {path}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(data: Path, ext_id: str) -> dict | None:
    """Return the install record for ``ext_id`` or ``None``."""
    path = record_path(data, ext_id)
    _check_file(data, path)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write(data: Path, record: dict) -> Path:
    """Write ``record`` atomically and append it to the log."""
    check_paths(data, record["id"])
    path = record_path(data, record["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    _check_file(data, temp)
    temp.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)
    log(data, {"action": "install", "id": record["id"], "version": record.get("version")})
    return path


def remove(data: Path, ext_id: str) -> None:
    check_paths(data, ext_id)
    path = record_path(data, ext_id)
    if path.exists():
        path.unlink()
    log(data, {"action": "uninstall", "id": ext_id})


def records(data: Path) -> list[dict]:
    """Return all install records, sorted by id."""
    folder = ledger_dir(data)
    env.require_inside(data, folder / ".instamix-check")
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.glob("*.json")):
        try:
            _check_file(data, path)
            record = json.loads(path.read_text(encoding="utf-8"))
            check_id(record["id"])
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"instamix: skipping unreadable ledger record {path}: {error}", file=sys.stderr)
            continue
        found.append(record)
    return sorted(found, key=lambda r: r["id"])


def log(data: Path, entry: dict) -> None:
    """Append one JSON line to the install log."""
    folder = ledger_dir(data)
    _check_file(data, folder / LOG)
    folder.mkdir(parents=True, exist_ok=True)
    entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry}
    with open(folder / LOG, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
