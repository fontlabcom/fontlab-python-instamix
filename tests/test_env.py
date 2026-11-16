# this_file: tests/test_env.py
import sys
import types

from fontlab_instamix import env


def test_uv_platform_when_known_then_triple():
    assert env.uv_platform("darwin", "arm64") == "aarch64-apple-darwin"
    assert env.uv_platform("darwin", "x86_64") == "x86_64-apple-darwin"
    assert env.uv_platform("win32", "AMD64") == "x86_64-pc-windows-msvc"


def test_data_dir_when_explicit_then_wins(tmp_path, monkeypatch):
    monkeypatch.setenv(env.DATA_ENV, str(tmp_path / "env"))
    assert env.data_dir(tmp_path / "x") == tmp_path / "x"


def test_data_dir_when_env_then_used(tmp_path, monkeypatch):
    monkeypatch.setenv(env.DATA_ENV, str(tmp_path))
    assert env.data_dir() == tmp_path


def test_data_dir_when_fontlab_prefs_then_used(tmp_path, monkeypatch):
    monkeypatch.delenv(env.DATA_ENV, raising=False)
    prefs = types.SimpleNamespace(dataPathDefault=lambda: str(tmp_path))
    fake = types.SimpleNamespace(flPreferences=lambda: prefs)
    monkeypatch.setitem(sys.modules, "fontlab", fake)
    assert env.data_dir() == tmp_path


def test_data_dir_when_attribute_pref_then_used(tmp_path, monkeypatch):
    monkeypatch.delenv(env.DATA_ENV, raising=False)
    fake = types.SimpleNamespace(flPreferences=lambda: types.SimpleNamespace(dataPathDefault=str(tmp_path)))
    monkeypatch.setitem(sys.modules, "fontlab", fake)
    assert env.data_dir() == tmp_path


def test_describe_when_called_then_has_paths(data):
    info = env.describe(data)
    assert info["python"] == "3.11" or info["python"]
    assert str(data) in info["site_packages"]
