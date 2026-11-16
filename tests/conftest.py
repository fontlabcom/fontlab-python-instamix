# this_file: tests/conftest.py
"""Shared fixtures: a throwaway FontLab data folder and the example extension."""

import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "com.example.hello.fontlabext"


@pytest.fixture
def data(tmp_path, monkeypatch):
    folder = tmp_path / "FontLab 9"
    folder.mkdir()
    monkeypatch.setenv("FONTLAB_DATA_DIR", str(folder))
    return folder


@pytest.fixture
def example(tmp_path):
    target = tmp_path / "src" / EXAMPLE.name
    shutil.copytree(EXAMPLE, target)
    return target
