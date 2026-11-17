# this_file: src/fontlab_instamix/gui.py
"""Small PythonQt dialogs for use inside FontLab.

PythonQt is imported only when a function is called, never at module import,
so this module is importable outside FontLab. Without PythonQt every helper
falls back to the console. ``message`` always prints and never opens a dialog.
"""

from __future__ import annotations

from pathlib import Path


def _qtgui():
    try:
        from PythonQt import QtGui  # type: ignore[import-not-found]
    except ImportError:
        return None
    return QtGui


def message(text: str, title: str = "Instamix", *, error: bool = False) -> None:
    """Print a status line; inside FontLab stdout goes to the Output panel.

    Never opens a modal dialog: install and uninstall reports must not
    interrupt the user's work.
    """
    prefix = f"{title} error" if error else title
    print(f"{prefix}: {text}", flush=True)


def confirm(text: str, title: str = "Instamix") -> bool:
    QtGui = _qtgui()
    if QtGui is None:
        return input(f"{title}: {text} [y/N] ").strip().lower() in ("y", "yes")
    buttons = QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
    return (
        QtGui.QMessageBox.question(None, title, text, buttons) == QtGui.QMessageBox.Yes
    )


FILE_PATTERN = "Extensions (*.fontlabextz manifest.fontlabextj)"


def pick_file(title: str = "Choose an extension", pattern: str = FILE_PATTERN) -> str:
    """Return PythonQt's QString path, or an empty string on cancellation."""
    QtGui = _qtgui()
    result = (
        input(f"{title}: ").strip()
        if QtGui is None
        else QtGui.QFileDialog.getOpenFileName(None, title, "", pattern)
    )
    if result is None:
        return ""
    if not isinstance(result, str):
        raise TypeError("PythonQt getOpenFileName must return a string")
    return result


def pick_files(
    title: str = "Choose extensions", pattern: str = FILE_PATTERN
) -> list[str]:
    """Choose archives/manifests; console fallback takes one literal path per line."""
    QtGui = _qtgui()
    if QtGui is None:
        paths = []
        while path := input(f"{title} (one path, blank to finish): ").strip():
            paths.append(path)
        return paths
    result = QtGui.QFileDialog.getOpenFileNames(None, title, "", pattern)
    if result is None:
        return []
    if not isinstance(result, (tuple, list)) or not all(
        isinstance(path, str) for path in result
    ):
        raise TypeError("PythonQt getOpenFileNames must return a sequence of strings")
    return [path for path in result if path]


def pick_folder(title: str = "Choose an extension folder") -> str:
    """Choose a .fontlabext directory without mixing folders into a file dialog."""
    QtGui = _qtgui()
    result = (
        input(f"{title}: ").strip()
        if QtGui is None
        else QtGui.QFileDialog.getExistingDirectory(None, title, "")
    )
    if result is None:
        return ""
    if not isinstance(result, str):
        raise TypeError("PythonQt getExistingDirectory must return a string")
    return result


def install_selected(
    paths: list[str | Path] | None = None,
    *,
    data: Path | None = None,
    folder: bool = False,
) -> list[dict]:
    """Install selected extensions; report each failure and continue other selections.

    Explicit paths bypass the picker. Returned records contain successful installs;
    failures print through message, including the path and original error.
    """
    from . import install

    if paths is None:
        paths = [pick_folder()] if folder else pick_files()
    records = []
    for path in paths:
        if not path:
            continue
        try:
            installed = install(Path(path), data)
        except (OSError, ValueError, RuntimeError) as error:
            message(f"{path}: {error}", error=True)
            installed = getattr(error, "installed_records", [])
        records.extend(installed)
        for item in installed:
            message(f"installed {item['id']} {item['version']}")
    return records


class Progress:
    """Context manager showing a busy progress dialog (or printing steps)."""

    def __init__(self, title: str = "Instamix", steps: int = 0):
        self.title = title
        self.steps = steps
        self.dialog = None

    def __enter__(self) -> Progress:
        QtGui = _qtgui()
        if QtGui is not None:
            self.dialog = QtGui.QProgressDialog(self.title, "", 0, self.steps)
            self.dialog.setCancelButton(None)
            self.dialog.show()
        return self

    def step(self, text: str, value: int | None = None) -> None:
        if self.dialog is None:
            print(f"{self.title}: {text}")
            return
        self.dialog.setLabelText(text)
        if value is not None:
            self.dialog.setValue(value)
        _qtgui().QApplication.processEvents()

    def __exit__(self, *exc) -> None:
        if self.dialog is not None:
            self.dialog.close()
