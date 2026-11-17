# this_file: tests/test_gui_selection.py
"""Lazy PythonQt selection and partial installation reports."""

from types import SimpleNamespace

import pytest

import fontlab_instamix
from fontlab_instamix import gui


@pytest.mark.parametrize(
    "result, expected",
    [
        (
            ("a.fontlabextz", "manifest.fontlabextj"),
            ["a.fontlabextz", "manifest.fontlabextj"],
        ),
        (["x"], ["x"]),
        ((), []),
        (None, []),
    ],
)
def test_pick_files_pythonqt_flat_sequence(monkeypatch, result, expected):
    dialog = SimpleNamespace(getOpenFileNames=lambda *args: result)
    monkeypatch.setattr(gui, "_qtgui", lambda: SimpleNamespace(QFileDialog=dialog))
    assert gui.pick_files() == expected


def test_pick_files_rejects_nested_or_string_results(monkeypatch):
    for result in [("x", ("filter",)), "x"]:
        monkeypatch.setattr(
            gui,
            "_qtgui",
            lambda selected=result: SimpleNamespace(
                QFileDialog=SimpleNamespace(getOpenFileNames=lambda *args: selected)
            ),
        )
        with pytest.raises(TypeError):
            gui.pick_files()


def test_console_selection_and_folder_cancel(monkeypatch):
    monkeypatch.setattr(gui, "_qtgui", lambda: None)
    responses = iter(["a path,with commas.fontlabextz", "manifest.fontlabextj", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))
    assert gui.pick_files() == [
        "a path,with commas.fontlabextz",
        "manifest.fontlabextj",
    ]
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    assert gui.pick_folder() == ""
    assert gui.pick_file() == ""


def test_pick_single_and_folder_native_contract(monkeypatch):
    dialog = SimpleNamespace(
        getOpenFileName=lambda *args: "manifest.fontlabextj",
        getExistingDirectory=lambda *args: "Demo.fontlabext",
    )
    monkeypatch.setattr(gui, "_qtgui", lambda: SimpleNamespace(QFileDialog=dialog))
    assert gui.pick_file() == "manifest.fontlabextj"
    assert gui.pick_folder() == "Demo.fontlabext"
    dialog.getOpenFileName = lambda *args: ("bad", "tuple")
    with pytest.raises(TypeError):
        gui.pick_file()


def test_install_selected_uses_public_api_and_reports_partial_failure(
    monkeypatch, tmp_path, capsys
):
    calls = []

    def install(path, data):
        calls.append((str(path), data))
        if str(path) == "bad":
            raise ValueError("invalid manifest")
        return [{"id": "com.example.good", "version": "1.0.0"}]

    monkeypatch.setattr(fontlab_instamix, "install", install)
    monkeypatch.setattr(gui, "pick_files", lambda: ["bad", "good"])
    assert gui.install_selected(data=tmp_path) == [
        {"id": "com.example.good", "version": "1.0.0"}
    ]
    assert calls == [("bad", tmp_path), ("good", tmp_path)]
    output = capsys.readouterr().out
    assert "error: bad: invalid manifest" in output
    assert "installed com.example.good" in output
    monkeypatch.setattr(gui, "pick_folder", lambda: "")
    assert gui.install_selected(folder=True) == []
    monkeypatch.setattr(gui, "pick_folder", lambda: "good")
    assert len(gui.install_selected(folder=True)) == 1
    assert len(gui.install_selected(["good"], data=tmp_path)) == 1


def test_lazy_qt_provider_console_confirmation_and_progress(monkeypatch, capsys):
    import sys

    monkeypatch.setitem(sys.modules, "PythonQt", None)
    assert gui._qtgui() is None
    monkeypatch.setattr("builtins.input", lambda prompt: "yes")
    assert gui.confirm("Proceed?")
    with gui.Progress("Installing", 1) as progress:
        progress.step("Selected archive", 1)
    assert "Installing: Selected archive" in capsys.readouterr().out
    events = []

    class Dialog:
        def __init__(self, *args):
            events.append("created")

        def setCancelButton(self, button):
            assert button is None

        def show(self):
            events.append("shown")

        def setLabelText(self, text):
            events.append(text)

        def setValue(self, value):
            events.append(value)

        def close(self):
            events.append("closed")

    qt = SimpleNamespace(
        QProgressDialog=Dialog,
        QApplication=SimpleNamespace(processEvents=lambda: events.append("processed")),
    )
    monkeypatch.setitem(sys.modules, "PythonQt", SimpleNamespace(QtGui=qt))
    assert gui._qtgui() is qt
    with gui.Progress("Installing", 1) as progress:
        progress.step("archive", 1)
    assert events == ["created", "shown", "archive", 1, "processed", "closed"]


def test_archive_partial_failure_keeps_original_error_and_reports_installed_records(
    tmp_path, monkeypatch, capsys
):
    from fontlab_instamix import extension, wrap

    folders = []
    for name in ("first", "second"):
        source = tmp_path / (name + ".py")
        source.write_text("pass\n")
        folders.append(wrap.make_folder(source, tmp_path, "com.example." + name))
    archive = wrap.make_zip(folders, tmp_path / "both.fontlabextz")
    data = tmp_path / "data"
    blocked = data / "Scripts/com.example.second/second.py"
    blocked.parent.mkdir(parents=True)
    blocked.write_text("owner bytes\n")
    with pytest.raises(extension.InstallError) as caught:
        extension.install(archive, data, copy=True)
    assert [record["id"] for record in caught.value.installed_records] == [
        "com.example.first"
    ]
    assert "second.py" in str(caught.value)
    extension.uninstall("com.example.first", data)
    records = gui.install_selected([archive], data=data)
    assert [record["id"] for record in records] == ["com.example.first"]
    assert [record["id"] for record in extension.installed(data)] == [
        "com.example.first"
    ]
    assert blocked.read_text() == "owner bytes\n"
    output = capsys.readouterr().out
    assert "error:" in output and "second.py" in output
    assert "installed com.example.first" in output
