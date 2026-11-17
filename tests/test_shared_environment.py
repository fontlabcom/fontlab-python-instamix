# this_file: tests/test_shared_environment.py
import csv
import sys
import types

import pytest

from fontlab_instamix import env, packages, uv, venv


def test_host_version_and_explicit_target(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "fontlab", types.SimpleNamespace())
    assert env.site_packages(tmp_path).parent.name == env.python_version()
    assert env.site_packages(tmp_path, version="3.12").parent.name == "3.12"


def test_unknown_architecture_refused():
    with pytest.raises(ValueError, match="architecture"):
        env.uv_platform("darwin", "sparc")


def test_record_csv_quoted_names(data):
    site = env.site_packages(data)
    site.mkdir(parents=True)
    names = ["comma,name.py", "line\nname.py"]
    for name in names:
        (site / name).write_text("")
    info = site / "demo-1.0.dist-info"
    info.mkdir()
    with (info / "RECORD").open("w", newline="") as handle:
        csv.writer(handle).writerows((name, "", "") for name in names)
    assert packages.uninstall(data, "demo") == names
    assert all(not (site / name).exists() for name in names)


def test_ensure_copies_existing_uv(data, tmp_path, monkeypatch):
    source = tmp_path / "existing-uv"
    source.write_bytes(b"uv")
    source.chmod(0o755)
    monkeypatch.setattr(uv, "find", lambda data: source)
    target = uv.ensure(data, allow_download=False)
    assert target == uv.local_uv(data)
    assert target.read_bytes() == b"uv"


def test_windows_request_and_paths(tmp_path):
    target = env.Target("3.11", "win32", "AMD64")
    assert venv.request(target) == "cpython-3.11-windows-x86_64-none"
    assert venv.python(tmp_path, target.platform) == tmp_path / "Scripts/python.exe"
    args = packages.install_args(tmp_path, ["demo"], target=target)
    assert args[args.index("--python") + 1].endswith(".venv/Scripts/python.exe")
    assert args[args.index("--python-platform") + 1] == "x86_64-pc-windows-msvc"


def test_public_install_packages_delegates_and_propagates(data, monkeypatch):
    from fontlab_instamix import extension, install, install_packages

    assert install is extension.install
    calls = []
    monkeypatch.setattr(packages, "install", lambda d, specs: calls.append((d, specs)))
    monkeypatch.setattr(env, "data_dir", lambda value: value or data)
    install_packages("fonttools>=4")
    install_packages("demo", data=data / "explicit")
    assert calls == [(data, ["fonttools>=4"]), (data / "explicit", ["demo"])]

    def fail(*args):
        raise uv.UvError("failed install")

    monkeypatch.setattr(packages, "install", fail)
    with pytest.raises(uv.UvError, match="failed install"):
        install_packages("demo")


def test_empty_specs_leave_data_absent(data):
    with pytest.raises(ValueError, match="no packages"):
        packages.install_packages(data=data)
    assert not list(data.iterdir())


def test_probe_failure_preserves_existing_venv(data):
    import subprocess

    folder = venv.path(data)
    folder.mkdir(parents=True)
    marker = folder / "keep"
    marker.write_text("mine")

    def broken(*args, **kwargs):
        assert kwargs["timeout"] == 30
        return subprocess.CompletedProcess(args, 0, "{}", "")

    with pytest.raises(uv.UvError, match="Move it aside"):
        venv.create(data, data / "uv", runner=broken)
    assert marker.read_text() == "mine"
    assert not env.site_packages(data).exists()


@pytest.mark.parametrize("kind", ["version", "arch", "platform", "prefix", "purelib"])
def test_mismatched_probe_refused(data, kind):
    import json
    import subprocess

    folder = venv.path(data)
    purelib = folder / "lib/site-packages"
    purelib.mkdir(parents=True)
    facts = {
        "version": "3.11",
        "platform": "darwin",
        "arch": "arm64",
        "prefix": str(folder),
        "purelib": str(purelib),
        "implementation": "CPython",
    }
    facts[kind] = {
        "version": "3.12",
        "arch": "x86_64",
        "platform": "win32",
        "prefix": str(data),
        "purelib": str(data),
    }[kind]

    def runner(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, json.dumps(facts), "")

    with pytest.raises(uv.UvError):
        venv.create(
            data,
            data / "uv",
            runner=runner,
            target=env.Target("3.11", "darwin", "arm64"),
        )
    assert not env.site_packages(data).exists()


def test_pth_collision_preserved(data, monkeypatch):
    folder = venv.path(data)
    purelib = folder / "lib/site-packages"
    purelib.mkdir(parents=True)
    pth = purelib / venv.PTH
    pth.write_text("unrelated\n")
    monkeypatch.setattr(venv, "probe", lambda *args: purelib)
    with pytest.raises(uv.UvError, match="Unrelated"):
        venv.create(data, data / "uv")
    assert pth.read_text() == "unrelated\n"
    assert not env.site_packages(data).exists()


def test_timeout_and_os_error_reported():
    import subprocess
    from pathlib import Path

    for error in (subprocess.TimeoutExpired("uv", 300), OSError("missing uv")):

        def fail(*args, error=error, **kwargs):
            assert kwargs["timeout"] == 300
            raise error

        with pytest.raises(uv.UvError, match="could not complete"):
            uv.run(Path("uv"), [], runner=fail)


@pytest.mark.parametrize(
    "spec", ["", "  ", "--target=/outside", "--python=other", " --upgrade"]
)
def test_option_specs_refused_before_writes(data, spec):
    with pytest.raises(ValueError, match="cannot be uv options"):
        packages.install(data, [spec])
    assert not list(data.iterdir())


def test_explicit_version_list_and_remove(data):
    target = env.Target("3.12", "darwin", "arm64")
    site = env.site_packages(data, version=target.version)
    info = site / "demo-1.0.dist-info"
    info.mkdir(parents=True)
    (site / "demo.py").write_text("")
    (info / "RECORD").write_text("demo.py,,\n")
    assert packages.listed(data, target=target) == [("demo", "1.0")]
    assert packages.listed(data) == []
    assert packages.uninstall(data, "demo", target=target) == ["demo.py"]
