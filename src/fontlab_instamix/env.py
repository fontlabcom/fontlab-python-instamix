# this_file: src/fontlab_instamix/env.py
"""Facts about the running Python and the FontLab data folder.

The data folder is chosen in this order: an explicit argument, the
``FONTLAB_DATA_DIR`` environment variable, ``fontlab.flPreferences()
.dataPathDefault`` when running inside FontLab, then the platform default.
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

from . import platformdirs

DATA_ENV = "FONTLAB_DATA_DIR"
STANDARD_FOLDERS = ("Scripts", "Actions", "Codepage", "Data", "Encoding")
FONTLAB_PYTHON = "3.11"  # FontLab 9 embeds Python 3.11 whatever runs the CLI


def python_version() -> str:
    """``major.minor`` of the running Python, e.g. ``3.11``."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def machine() -> str:
    """Normalised CPU architecture: ``arm64`` or ``x86_64``."""
    name = platform.machine().lower()
    if name in ("arm64", "aarch64"):
        return "arm64"
    if name in ("amd64", "x86_64", "x64"):
        return "x86_64"
    return name


def uv_platform(plat: str = sys.platform, arch: str | None = None) -> str:
    """Target triple for ``uv pip install --python-platform``."""
    arch = arch or machine()
    cpu = "aarch64" if arch == "arm64" else "x86_64"
    if plat == "win32":
        return f"{cpu}-pc-windows-msvc"
    if plat == "darwin":
        return f"{cpu}-apple-darwin"
    return f"{cpu}-unknown-linux-gnu"


def fontlab_data_dir() -> Path | None:
    """Ask FontLab for its data folder; ``None`` outside FontLab."""
    try:
        import fontlab  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        # No-arg flPreferences() is in established use (fontlabapp plugins/boot.py).
        value = fontlab.flPreferences().dataPathDefault
        if callable(value):
            value = value()
    except Exception:  # noqa: BLE001 - any FontLab failure means "unknown"
        return None
    return Path(str(value)) if value else None


def data_dir(explicit: str | os.PathLike | None = None) -> Path:
    """Return the FontLab data folder (not created)."""
    if explicit:
        return Path(explicit).expanduser()
    if os.environ.get(DATA_ENV):
        return Path(os.environ[DATA_ENV]).expanduser()
    return fontlab_data_dir() or platformdirs.default_data_dir()


def site_packages(data: Path) -> Path:
    """``<data>/python/3.11/site-packages`` used by FontLab's sys.path."""
    return Path(data) / "python" / FONTLAB_PYTHON / "site-packages"


def ensure_folders(data: Path) -> None:
    """Create the standard data subfolders instamix links into."""
    for name in (*STANDARD_FOLDERS, "Extensions/Library"):
        (Path(data) / name).mkdir(parents=True, exist_ok=True)
    site_packages(data).mkdir(parents=True, exist_ok=True)


def describe(data: Path | None = None) -> dict:
    """Summary used by ``fontlab-instamix env``."""
    data = data or data_dir()
    return {
        "python": python_version(),
        "implementation": sys.version.split()[0],
        "platform": sys.platform,
        "machine": machine(),
        "uv_platform": uv_platform(),
        "data_dir": str(data),
        "site_packages": str(site_packages(data)),
        "in_fontlab": "fontlab" in sys.modules,
    }
