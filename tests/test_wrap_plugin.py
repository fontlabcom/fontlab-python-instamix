# this_file: tests/test_wrap_plugin.py
"""Plugin packaging validates data without executing draft code."""

import json
from pathlib import Path

import pytest

from fontlab_instamix import cli, extension, wrap

META = {
    "plugin_id": "Demo",
    "name": "Demo plugin",
    "kind": "reporter",
    "entry": "demo:Demo",
    "min_app_version": "1.0.0",
}
KINDS = {
    "reporter": "reporters",
    "filter": "filters",
    "tool": "tools",
    "palette": "palettes",
    "general": "general",
}


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("copy", [False, True])
def test_plugin_kind_roundtrip(tmp_path, kind, copy):
    source = tmp_path / "Demo.py"
    source.write_text("raise RuntimeError('never import drafts')\n")
    meta = dict(META, kind=kind, entry="Demo:Demo")
    folder = wrap.make_plugin(source, tmp_path / "out", "com.example.demo", **meta)
    relative = Path("Extensions") / KINDS[kind] / f"Demo.fontlab{kind}"
    inner = folder / relative
    assert (inner / source.name).read_bytes() == source.read_bytes()
    assert json.loads((inner / "plugin.json").read_text())["entry"] == "Demo:Demo"
    archive = wrap.make_zip([folder], folder.with_suffix(".fontlabextz"))
    data = tmp_path / "data"
    extension.install(archive, data, copy=copy)
    installed = data / relative
    assert (installed / source.name).read_bytes() == source.read_bytes()
    assert (installed / "plugin.json").resolve().parent.name == inner.name
    assert (installed / "plugin.json").resolve().parent.parent.name == KINDS[kind]
    extension.uninstall("com.example.demo", data)
    assert not (installed / "plugin.json").exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "bad"},
        {"plugin_id": "bad/id"},
        {"entry": "../demo:Demo"},
        {"entry": "demo:no.class"},
        {"entry": "absent:Demo"},
        {"name": " "},
        {"version": "1.0"},
        {"min_app_version": "01.0.0"},
        {"ext_id": "../bad"},
    ],
)
def test_invalid_plugin_preserves_output(tmp_path, changes):
    source = tmp_path / "demo.py"
    source.write_text("pass\n")
    out = tmp_path / "out"
    args = dict(META, ext_id="com.example.demo") | changes
    with pytest.raises((ValueError, FileNotFoundError)):
        wrap.make_plugin(source, out, **args)
    assert not out.exists()


def test_package_relative_entry_and_existing_manifest(tmp_path):
    source = tmp_path / "Draft.fontlabReporter"
    (source / "pkg").mkdir(parents=True)
    (source / "pkg" / "__init__.py").write_text("from .helper import Demo\n")
    (source / "pkg" / "helper.py").write_text("class Demo: pass\n")
    metadata = {
        "id": "Demo",
        "name": "Demo plugin",
        "kind": "reporter",
        "version": "0.1.0",
        "entry": "pkg:Demo",
        "min_app_version": "1.0.0",
    }
    raw = json.dumps(metadata)
    (source / "plugin.json").write_text(raw)
    (source / "LICENSE").write_text("owned fixture licence\n")
    folder = wrap.make_plugin(
        source, tmp_path / "out", "com.example.demo", **(META | {"entry": "pkg:Demo"})
    )
    inner = folder / "Extensions/reporters/Draft.fontlabreporter"
    assert (inner / "plugin.json").read_text() == raw
    assert (inner / "pkg/helper.py").read_bytes() == (
        source / "pkg/helper.py"
    ).read_bytes()
    assert (inner / "LICENSE").read_bytes() == (source / "LICENSE").read_bytes()
    with pytest.raises(ValueError, match="agree"):
        wrap.make_plugin(
            source,
            tmp_path / "other",
            "com.example.demo",
            **(META | {"entry": "pkg:Demo", "name": "conflict"}),
        )
    assert not (tmp_path / "other").exists()


def test_plugin_cli_and_missing_options(tmp_path, capsys):
    source = tmp_path / "demo.py"
    source.write_text("pass\n")
    base = [
        "wrap",
        str(source),
        "--id",
        "com.example.demo",
        "--out",
        str(tmp_path / "out"),
        "--kind",
        "reporter",
    ]
    assert cli.main(base) == 1
    assert not (tmp_path / "out").exists()
    assert (
        cli.main(
            base
            + [
                "--plugin-id",
                "Demo",
                "--name",
                "Demo plugin",
                "--entry",
                "demo:Demo",
                "--min-app-version",
                "1.0.0",
                "--zip",
            ]
        )
        == 0
    )
    assert (tmp_path / "out/com.example.demo.fontlabextz").is_file()


def test_plugin_existing_output_and_source_guards(tmp_path):
    source = tmp_path / "draft"
    source.mkdir()
    (source / "demo.py").write_text("pass\n")
    with pytest.raises(ValueError, match="outside"):
        wrap.make_plugin(source, source / "out", "com.example.demo", **META)
    assert not (source / "out").exists()
    folder = tmp_path / "out/com.example.demo.fontlabext"
    folder.mkdir(parents=True)
    (folder / "owner").write_text("keep")
    with pytest.raises(FileExistsError):
        wrap.make_plugin(source, folder.parent, "com.example.demo", **META)
    assert list(folder.iterdir()) == [folder / "owner"]
    assert (folder / "owner").read_text() == "keep"
    outside = tmp_path / "private.py"
    outside.write_text("private")
    (source / "leak.py").symlink_to(outside)
    with pytest.raises(ValueError, match="links"):
        wrap.make_plugin(source, tmp_path / "new", "com.example.demo", **META)
    assert not (tmp_path / "new").exists()


def test_plugin_copy_failure_leaves_no_published_bundle(tmp_path, monkeypatch):
    source = tmp_path / "demo.py"
    source.write_text("pass\n")

    def failed_copy(*args, **kwargs):
        raise OSError("copy failed")

    monkeypatch.setattr(wrap.shutil, "copy2", failed_copy)
    with pytest.raises(OSError, match="copy failed"):
        wrap.make_plugin(source, tmp_path / "out", "com.example.demo", **META)
    assert list((tmp_path / "out").iterdir()) == []
