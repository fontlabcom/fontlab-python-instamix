# this_file: tests/test_manifest.py
import json

import pytest

from fontlab_instamix import manifest
from fontlab_instamix.manifest import ManifestError

GOOD = {
    "id": "com.example.myext",
    "name": "My Extension",
    "version": "1.0.0",
    "python": {"requires": ["fonttools>=4"], "packages": ["src/mypkg"]},
    "vars": {"family": "adamtrix"},
    "install": [{"from": "scripts", "to": "Scripts/{}"}],
}


def test_parse_when_good_then_manifest():
    info = manifest.parse(GOOD)
    assert info.id == "com.example.myext"
    assert info.requires == ("fonttools>=4",)
    assert info.install[0].to == "Scripts/{}"


@pytest.mark.parametrize(
    "change",
    [
        {"id": "MyExt"},
        {"id": "single"},
        {"name": ""},
        {"version": 1},
        {"extra": 1},
        {"python": {"other": []}},
        {"python": {"requires": "fonttools"}},
        {"vars": {"a": 1}},
        {"install": [{"from": "x"}]},
        {"install": [{"from": "x", "to": "y", "z": 1}]},
        {"install": {}},
    ],
)
def test_parse_when_invalid_then_error(change):
    with pytest.raises(ManifestError):
        manifest.parse({**GOOD, **change})


def test_parse_when_not_object_then_error():
    with pytest.raises(ManifestError):
        manifest.parse([])


def test_load_when_example_then_this_file_tolerated(example):
    assert manifest.load(example).id == "com.example.hello"


def test_find_when_manifest_name_has_other_case_then_found(tmp_path):
    folder = tmp_path / "com.example.a.fontlabext"
    folder.mkdir()
    (folder / "Manifest.FontLabExtJ").write_text(json.dumps({**GOOD, "id": "com.example.a"}))
    assert manifest.load(folder).id == "com.example.a"
