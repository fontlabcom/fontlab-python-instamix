# this_file: tests/test_packages.py
import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from fontlab_instamix import env, packages, uv, venv


class Recorder:
    def __init__(self, returncode=0):
        self.calls = []
        self.returncode = returncode

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        if "venv" in argv and not self.returncode:
            (Path(argv[-1]) / "lib/site-packages").mkdir(parents=True)
        if "-c" in argv:
            folder = Path(argv[0]).parent.parent
            facts = {
                "version": "3.11",
                "platform": sys.platform,
                "arch": env.machine(),
                "prefix": str(folder),
                "purelib": str(folder / "lib/site-packages"),
                "implementation": "CPython",
            }
            return subprocess.CompletedProcess(
                argv, self.returncode, json.dumps(facts), "boom"
            )
        return subprocess.CompletedProcess(argv, self.returncode, "ok", "boom")


def test_install_when_specs_then_uv_targets_site_packages(data, tmp_path):
    fake_uv = tmp_path / "uv"
    run = Recorder()
    packages.install(
        data, ["fonttools>=4", "git+https://github.com/x/y"], uv_bin=fake_uv, runner=run
    )
    argv = run.calls[-1]
    assert argv[0] == str(fake_uv)
    assert sys.executable not in argv
    assert argv[1:3] == ["pip", "install"]
    assert argv[argv.index("--target") + 1] == str(
        data / "python" / "3.11" / "site-packages"
    )
    assert argv[argv.index("--python-version") + 1] == "3.11"
    assert argv[argv.index("--python-platform") + 1].endswith(
        ("apple-darwin", "windows-msvc", "linux-gnu")
    )
    assert argv[-2:] == ["fonttools>=4", "git+https://github.com/x/y"]


def test_install_when_uv_fails_then_error(data, tmp_path):
    with pytest.raises(uv.UvError):
        packages.install(data, ["x"], uv_bin=tmp_path / "uv", runner=Recorder(1))


def test_venv_create_when_called_then_uv_venv(data, tmp_path):
    run = Recorder()
    venv.create(data, tmp_path / "uv", runner=run)
    argv = run.calls[0]
    assert argv[0] == str(tmp_path / "uv") and argv[1] == "venv"
    assert any("cpython-3.11-" in a for a in argv) and str(data / ".venv") in argv
    assert sys.executable not in argv


def test_listed_and_uninstall_when_dist_info_then_removed(data):
    site = data / "python" / "3.11" / "site-packages"
    (site / "demo").mkdir(parents=True)
    (site / "demo" / "__init__.py").write_text("")
    info = site / "demo-1.2.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Name: demo\nVersion: 1.2\n")
    (info / "RECORD").write_text(
        "demo/__init__.py,,\ndemo-1.2.dist-info/METADATA,,\ndemo-1.2.dist-info/RECORD,,\n"
    )
    assert ("demo", "1.2") in packages.listed(data)
    packages.uninstall(data, "Demo")
    assert not (site / "demo").exists() and not info.exists()


def test_uv_download_when_checksum_ok_then_installed(data, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        payload = b"#!/bin/sh\necho uv\n"
        member = tarfile.TarInfo("uv-aarch64-apple-darwin/uv")
        member.size = len(payload)
        tar.addfile(member, io.BytesIO(payload))
    archive = buf.getvalue()
    digest = hashlib.sha256(archive).hexdigest()

    def fetch(url):
        assert url.startswith("https://")
        return f"{digest}  uv.tar.gz\n".encode() if url.endswith(".sha256") else archive

    path = uv.download(data, "0.9.0", fetch=fetch)
    assert path == data / "python" / "uv" / "uv"
    assert path.read_bytes() == payload


def test_uv_download_when_checksum_bad_then_error(data, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")

    def fetch(url):
        return b"0" * 64 if url.endswith(".sha256") else b"archive"

    with pytest.raises(uv.UvError):
        uv.download(data, fetch=fetch)
    assert not uv.local_uv(data).exists()


def test_uninstall_when_other_dirs_and_linked_checkout_then_untouched(data, tmp_path):
    site = data / "python" / "3.11" / "site-packages"
    (site / "demo" / "sub").mkdir(parents=True)
    (site / "demo" / "sub" / "m.py").write_text("")
    (site / "other_empty").mkdir()
    (site / "other" / "__pycache__").mkdir(parents=True)
    (site / "other" / "__pycache__" / "x.cpython-311.pyc").write_text("")
    checkout = tmp_path / "checkout" / "proj"
    (checkout / "empty").mkdir(parents=True)
    (site / "proj").symlink_to(checkout, target_is_directory=True)
    info = site / "demo-1.0.dist-info"
    info.mkdir()
    (info / "RECORD").write_text("demo/sub/m.py,,\n../outside.py,,\nproj/x.py,,\n")
    (tmp_path / "checkout" / "proj" / "x.py").write_text("mine")
    packages.uninstall(data, "demo")
    assert not (site / "demo").exists() and not info.exists()
    assert (site / "other_empty").is_dir()
    assert (site / "other" / "__pycache__" / "x.cpython-311.pyc").exists()
    assert (checkout / "empty").is_dir() and (checkout / "x.py").read_text() == "mine"


def test_uninstall_when_record_entry_is_symlink_then_link_removed_not_target(
    data, tmp_path
):
    site = data / "python" / "3.11" / "site-packages"
    site.mkdir(parents=True)
    real = tmp_path / "real.py"
    real.write_text("keep")
    (site / "linked.py").symlink_to(real)
    info = site / "lk-1.0.dist-info"
    info.mkdir()
    (info / "RECORD").write_text("linked.py,,\n")
    packages.uninstall(data, "lk")
    assert not (site / "linked.py").is_symlink() and real.read_text() == "keep"


class EnvRecorder(Recorder):
    def __init__(self):
        super().__init__()
        self.envs = []

    def __call__(self, argv, **kwargs):
        self.envs.append(kwargs.get("env"))
        return super().__call__(argv, **kwargs)


def test_uv_run_when_windows_then_private_python_install_dir(
    data, tmp_path, monkeypatch
):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("UV_PYTHON_INSTALL_DIR", raising=False)
    run = EnvRecorder()
    packages.install(data, ["x"], uv_bin=tmp_path / "uv", runner=run)
    expected = str(data / "python" / "uv" / "python")
    assert run.envs, "uv was not called"
    for argv, environment in zip(run.calls, run.envs):
        if argv[0] != str(tmp_path / "uv"):
            continue
        assert environment is not None, (
            f"uv {argv[1:3]} ran without a private install dir"
        )
        assert environment["UV_PYTHON_INSTALL_DIR"] == expected


def test_uv_run_when_user_sets_install_dir_then_kept(data, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("UV_PYTHON_INSTALL_DIR", str(tmp_path / "mine"))
    assert uv.run_env(data) is None


def test_uv_run_when_macos_then_environment_inherited(data, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert uv.run_env(data) is None
