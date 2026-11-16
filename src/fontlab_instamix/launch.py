# this_file: src/fontlab_instamix/launch.py
"""Entry points for the generated ``Scripts/Instamix`` menu launchers."""

from __future__ import annotations

from . import env, extension, gui


def list_extensions(data=None) -> str:
    """Show every installed extension with its version."""
    records = extension.installed(env.data_dir(data))
    lines = [f"{r.get('id')}  {r.get('version')}  {r.get('name', '')}" for r in records]
    text = "\n".join(lines) or "Nothing is installed with instamix."
    gui.message(text, "Installed extensions")
    return text


def uninstall(ext_id: str, data=None) -> list[str]:
    """Ask, then uninstall *ext_id*; show what was kept because it changed."""
    if not gui.confirm(f"Uninstall {ext_id}?", "Uninstall"):
        return []
    try:
        kept = extension.uninstall(ext_id, env.data_dir(data))
    except extension.InstallError as error:
        gui.message(str(error), "Uninstall", error=True)
        return []
    note = "\n\nKept (changed since install):\n" + "\n".join(kept) if kept else ""
    gui.message(f"Uninstalled {ext_id}. Restart FontLab.{note}", "Uninstall")
    return kept
