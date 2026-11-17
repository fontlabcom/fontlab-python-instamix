# this_file: src/fontlab_instamix/uv.py
"""Find, download and run uv as its own binary.

Never runs ``sys.executable``: inside FontLab that is FontLab itself.
uv is downloaded from GitHub releases into ``<data>/python/uv/`` and its
SHA-256 is checked against the ``.sha256`` file published with the release.
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from . import env

RELEASES = "https://github.com/astral-sh/uv/releases"
CANDIDATES = (
    "~/.local/bin/uv",
    "~/.cargo/bin/uv",
    "/opt/homebrew/bin/uv",
    "/usr/local/bin/uv",
)


class UvError(RuntimeError):
    """uv is missing, failed to download, or a uv command failed."""


def exe_name() -> str:
    return "uv.exe" if sys.platform == "win32" else "uv"


def local_uv(data: Path) -> Path:
    """Where instamix keeps its own uv: ``<data>/python/uv/uv``."""
    return Path(data) / "python" / "uv" / exe_name()


def find(data: Path | None = None) -> Path | None:
    """Return a usable uv binary or ``None``."""
    candidates = []
    if data is not None:
        candidates.append(local_uv(data))
    if os.environ.get("UV"):
        candidates.append(Path(os.environ["UV"]))
    found = shutil.which("uv")
    if found:
        candidates.append(Path(found))
    candidates += [Path(c).expanduser() for c in CANDIDATES]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def asset_name(plat: str = sys.platform) -> str:
    triple = env.uv_platform(plat)
    return f"uv-{triple}.zip" if plat == "win32" else f"uv-{triple}.tar.gz"


def asset_url(version: str | None = None, plat: str = sys.platform) -> str:
    base = (
        f"{RELEASES}/download/{version}" if version else f"{RELEASES}/latest/download"
    )
    return f"{base}/{asset_name(plat)}"


def fetch_bytes(url: str) -> bytes:
    """Download ``url`` (kept small so tests can replace it)."""
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def extract_binary(archive: bytes, name: str, plat: str = sys.platform) -> bytes:
    """Return the bytes of the uv binary inside a release archive."""
    wanted = "uv.exe" if plat == "win32" else "uv"
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            for member in zipped.namelist():
                if member.rsplit("/", 1)[-1] == wanted:
                    return zipped.read(member)
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tarred:
            for member in tarred.getmembers():
                if member.isfile() and member.name.rsplit("/", 1)[-1] == wanted:
                    handle = tarred.extractfile(member)
                    if handle:
                        return handle.read()
    raise UvError(f"{name} does not contain {wanted}")


def download(data: Path, version: str | None = None, fetch=fetch_bytes) -> Path:
    """Download uv into ``<data>/python/uv/`` and return its path."""
    url = asset_url(version)
    name = asset_name()
    archive = fetch(url)
    expected = fetch(url + ".sha256").decode("ascii", "replace").split()[0].lower()
    actual = hashlib.sha256(archive).hexdigest()
    if expected != actual:
        raise UvError(
            f"uv checksum mismatch for {name}: expected {expected}, got {actual}"
        )
    target = local_uv(data)
    temp = target.with_name(target.name + ".tmp")
    env.require_inside(data, target)
    env.require_inside(data, temp)
    if target.is_symlink() or temp.is_symlink() or temp.exists():
        raise UvError(f"refusing linked uv destination or occupied temporary path: {target}, {temp}")
    payload = extract_binary(archive, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp.write_bytes(payload)
    temp.chmod(0o755)
    temp.replace(target)
    return target


def ensure(data: Path, *, allow_download: bool = True) -> Path:
    """Return uv, downloading it if needed and allowed."""
    found = find(data)
    if found:
        target = local_uv(data)
        env.require_inside(data, target)
        if found != target:
            if target.exists() or target.is_symlink():
                raise UvError(f"uv destination already exists: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(found, target)
        return target
    if not allow_download:
        raise UvError("uv not found; run: fontlab-instamix uv fetch")
    return download(data)


def run(
    uv: Path, args: list[str], runner=subprocess.run
) -> subprocess.CompletedProcess:
    """Run ``uv <args>``; raise :class:`UvError` on failure."""
    command = [str(uv), *args]
    extra = (
        {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        if sys.platform == "win32"
        else {}
    )
    try:
        result = runner(command, capture_output=True, text=True, timeout=300, **extra)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UvError(f"uv command could not complete: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise UvError(f"uv {' '.join(args)} failed ({result.returncode}): {detail}")
    return result
