# this_file: src/fontlab_instamix/stub.py
"""Write the short ``install.vfpy`` stub that installs a repo with instamix."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

NAME = "install.vfpy"


def text() -> str:
    """The stub source shipped inside the package."""
    return resources.files(__package__).joinpath("stub_install.vfpy").read_text(encoding="utf-8")


def write(folder: Path, *, force: bool = False) -> Path:
    """Write ``install.vfpy`` into *folder* (a repo with ``[tool.fontlab-install]``)."""
    folder = Path(folder)
    if not (folder / "pyproject.toml").is_file():
        raise FileNotFoundError(f"{folder} has no pyproject.toml")
    path = folder / NAME
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; use --force to replace it")
    path.write_text(text(), encoding="utf-8")
    return path
