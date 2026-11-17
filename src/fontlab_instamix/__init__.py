# this_file: src/fontlab_instamix/__init__.py
"""Stdlib-only installer toolkit for FontLab 9's embedded Python 3.11.

Submodules load lazily: ``fontlab_instamix.install(...)`` imports
:mod:`fontlab_instamix.extension` on first use.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bootstrap import install_project
    from .env import data_dir
    from .extension import install, installed, uninstall
    from .packages import install_packages

try:
    from .__version__ import __version__
except ImportError:  # running from a checkout: hatch-vcs writes this file on build
    __version__ = "0.0.0+checkout"

_LAZY = {
    "install": ("extension", "install"),
    "uninstall": ("extension", "uninstall"),
    "installed": ("extension", "installed"),
    "install_packages": ("packages", "install_packages"),
    "install_project": ("bootstrap", "install_project"),
    "data_dir": ("env", "data_dir"),
}

__all__ = [
    "__version__",
    "data_dir",
    "install",
    "install_packages",
    "install_project",
    "installed",
    "uninstall",
]


def __getattr__(name: str):
    if name in _LAZY:
        module, attr = _LAZY[name]
        return getattr(importlib.import_module(f"{__name__}.{module}"), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
