# this_file: src/fontlab_instamix/gui.py
"""Small PythonQt dialogs for use inside FontLab.

PythonQt is imported only when a function is called, never at module import,
so this module is importable outside FontLab. Without PythonQt every helper
falls back to the console. ``message`` always prints and never opens a dialog.
"""

from __future__ import annotations


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
    return QtGui.QMessageBox.question(None, title, text, buttons) == QtGui.QMessageBox.Yes


def pick_file(title: str = "Choose an extension", pattern: str = "Extensions (*.fontlabextz *.fontlabext)") -> str:
    """Return a chosen path, or an empty string when cancelled."""
    QtGui = _qtgui()
    if QtGui is None:
        return input(f"{title}: ").strip()
    return str(QtGui.QFileDialog.getOpenFileName(None, title, "", pattern) or "")


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
