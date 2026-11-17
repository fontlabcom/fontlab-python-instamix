# this_file: tests/test_validation_before_writes.py
import json
import os

import pytest

from fontlab_instamix import extension, manifest, wrap


def snapshot(root):
    return {
        str(path.relative_to(root)): (
            ("link", os.readlink(path)) if path.is_symlink()
            else ("file", path.read_bytes()) if path.is_file()
            else ("dir",)
        )
        for path in root.rglob("*")
    }


@pytest.mark.parametrize("entry", ["folder", "manifest"])
@pytest.mark.parametrize("existing", [False, True])
def test_install_when_identity_mismatches_then_no_writes(tmp_path, example, entry, existing):
    data = tmp_path / "fresh-data"
    if existing:
        extension.install(example, data, copy=True)
    renamed = example.with_name("com.example.other.fontlabext")
    example.rename(renamed)
    example = renamed
    info_path = example / manifest.MANIFEST
    before = snapshot(tmp_path)
    with pytest.raises(extension.InstallError, match="manifest id"):
        extension.install(example if entry == "folder" else info_path, data)
    assert snapshot(tmp_path) == before
    assert data.exists() == existing


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("rule", [
    {"from": "missing", "to": "Scripts/{}"},
    {"from": "scripts", "to": "Scripts/../escape"},
    {"from": "scripts", "to": "Scripts/{unknown}"},
])
def test_install_when_plan_invalid_then_no_writes(tmp_path, example, existing, rule):
    data = tmp_path / "fresh-data"
    if existing:
        extension.install(example, data, copy=True)
    info_path = example / manifest.MANIFEST
    info = json.loads(info_path.read_text())
    info["install"] = [rule]
    info_path.write_text(json.dumps(info))
    before = snapshot(tmp_path)
    with pytest.raises((extension.InstallError, ValueError)):
        extension.install(example, data)
    assert snapshot(tmp_path) == before
    assert data.exists() == existing


@pytest.mark.parametrize("ext_id,version", [
    ("absolute", "1"), ("../outside/escape", "1"),
    ("com.example/escape", "1"), ("Com.example.tool", "1"),
    ("tool", "1"), ("com.example.tool", ""),
    ("com.example.tool", None), ("com.example.tool", 42),
])
@pytest.mark.parametrize("existing", [False, True])
def test_make_folder_when_metadata_invalid_then_no_writes(tmp_path, ext_id, version, existing):
    source = tmp_path / "Hello.py"
    source.write_text("print('hello')\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "sentinel").write_bytes(b"keep\x00me")
    out = tmp_path / "output"
    if existing:
        out.mkdir()
        (out / "sentinel").write_bytes(b"keep output")
    if ext_id == "absolute":
        ext_id = str(outside / "escape")
    before = snapshot(tmp_path)
    with pytest.raises(manifest.ManifestError):
        wrap.make_folder(source, out, ext_id, version=version)
    assert snapshot(tmp_path) == before
