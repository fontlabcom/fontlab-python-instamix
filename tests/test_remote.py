# this_file: tests/test_remote.py
"""Remote transport is faked; filesystem placement uses the real installer."""

import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from fontlab_instamix import cli, env, packages, remote, uv, venv


@pytest.fixture
def bridge(data, monkeypatch):
    value = {
        "python": "3.12",
        "implementation": "3.12.9",
        "platform": sys.platform,
        "machine": "aarch64",
        "data_dir": str(data),
        "site_packages": str(data / "python/3.12/site-packages"),
    }
    state = SimpleNamespace(
        value=value,
        calls=[],
        command=None,
        error=None,
        nonce=True,
        refresh=True,
        active=False,
    )

    class Client:
        def __init__(self, command=None):
            state.command = command

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def run(self, code, **variables):
            state.active = True
            try:
                state.calls.append((code, json.loads(json.dumps(variables))))
                if state.error:
                    raise state.error
                if code == remote.PROBE:
                    return SimpleNamespace(value=state.value)
                if code == remote.READ_MARKER:
                    marker = Path(variables["marker"])
                    state.marker = marker
                    return SimpleNamespace(
                        value=marker.read_text() if state.nonce else "wrong"
                    )
                assert code == remote.REFRESH
                return SimpleNamespace(value=state.refresh)
            finally:
                state.active = False

    monkeypatch.setitem(sys.modules, "fontlab_remopy", SimpleNamespace(FontLab=Client))
    return state


def test_env_and_bridge_are_read_only(bridge, data, capsys):
    assert cli.main(["--remote", "--bridge", "/bridge with spaces", "env"]) == 0
    assert json.loads(capsys.readouterr().out)["python"] == "3.12"
    assert bridge.command == "/bridge with spaces"
    assert bridge.calls == [(remote.PROBE, {})]
    assert not list(data.iterdir())


def test_missing_optional_import_does_not_break_local_cli(monkeypatch, data, capsys):
    monkeypatch.setitem(sys.modules, "fontlab_remopy", None)
    assert cli.main(["--data-dir", str(data), "env"]) == 0
    assert cli.main(["--remote", "env"]) == 1
    assert "requires fontlab-remopy" in capsys.readouterr().err


@pytest.mark.parametrize(
    "changes",
    [
        {"python": None},
        {"python": "2.7"},
        {"machine": "unknown"},
        {"data_dir": "relative"},
        {"site_packages": "/wrong"},
        {"platform": "other"},
    ],
)
def test_malformed_facts_refuse_before_writes(bridge, data, changes):
    bridge.value.update(changes)
    assert cli.main(["--remote", "pkg", "install", "demo"]) == 1
    assert not list(data.iterdir())
    assert len(bridge.calls) == 1


def test_foreign_os_can_be_reported_but_not_used(bridge, data):
    bridge.value.update(
        platform="win32",
        data_dir="C:\\FontLab",
        site_packages="C:\\FontLab\\python\\3.12\\site-packages",
    )
    assert cli.main(["--remote", "env"]) == 0
    assert cli.main(["--remote", "pkg", "list"]) == 1
    assert not list(data.iterdir())


@pytest.mark.parametrize(
    "argv",
    [
        ["--data-dir", "/conflict", "--remote", "pkg", "list"],
        ["--remote", "ext", "install", "missing", "--run-hooks"],
        ["--remote", "wrap", "missing"],
        ["--bridge", "/bridge", "env"],
    ],
)
def test_invalid_combinations_refuse(bridge, data, argv):
    assert cli.main(argv) == 1
    assert not list(data.iterdir())


def test_nonce_mismatch_cleans_only_owned_marker(bridge, data):
    other = data / ".instamix-probe-other"
    other.write_text("keep")
    bridge.nonce = False
    assert cli.main(["--remote", "pkg", "install", "demo"]) == 1
    assert list(data.iterdir()) == [other]
    assert not bridge.marker.exists()


def test_probe_timeout_does_not_retry(bridge, data):
    bridge.error = TimeoutError("unknown")
    assert cli.main(["--remote", "pkg", "install", "demo"]) == 1
    assert len(bridge.calls) == 1
    assert not list(data.iterdir())


def test_shared_probe_timeout_cleans_marker(bridge, data):
    class TimedOut:
        def run(self, *args, **kwargs):
            raise TimeoutError("unknown")

    with pytest.raises(TimeoutError):
        remote.shared_path(TimedOut(), data)
    assert not list(data.iterdir())


def test_missing_data_root_is_not_created(bridge, data):
    data.rmdir()
    assert cli.main(["--remote", "pkg", "list"]) == 1
    assert not data.exists()


def test_packages_run_outside_remote_and_propagate_target(bridge, data, monkeypatch):
    calls = []

    def install(folder, specs, **kwargs):
        assert not bridge.active
        assert not bridge.marker.exists()
        calls.append((folder, specs, kwargs))
        return SimpleNamespace(stdout="installed")

    monkeypatch.setattr(packages, "install", install)
    assert (
        cli.main(
            ["--remote", "--data-dir", str(data), "pkg", "install", "demo", "--upgrade"]
        )
        == 0
    )
    assert calls == [
        (
            data,
            ["demo"],
            {"upgrade": True, "target": env.Target("3.12", sys.platform, "arm64")},
        )
    ]
    assert [c[0] for c in bridge.calls] == [
        remote.PROBE,
        remote.READ_MARKER,
        remote.REFRESH,
    ]


def test_delayed_external_provider_is_not_a_host_call(bridge, monkeypatch):
    def install(*args, **kwargs):
        assert not bridge.active
        time.sleep(5.05)
        assert len(bridge.calls) == 2
        return SimpleNamespace(stdout="done")

    monkeypatch.setattr(packages, "install", install)
    assert cli.main(["--remote", "pkg", "install", "demo"]) == 0


def test_external_timeout_no_retry_or_refresh(bridge, monkeypatch):
    calls = []

    def install(*args, **kwargs):
        calls.append(1)
        raise subprocess.TimeoutExpired(["uv"], 300, stderr="partial")

    monkeypatch.setattr(packages, "install", install)
    assert cli.main(["--remote", "pkg", "install", "demo"]) == 1
    assert calls == [1]
    assert len(bridge.calls) == 2


def test_refresh_failure_reports_completed_install(bridge, monkeypatch, capsys):
    bridge.refresh = False
    calls = []
    monkeypatch.setattr(
        packages,
        "install",
        lambda *a, **kw: calls.append(1) or SimpleNamespace(stdout="done"),
    )
    assert cli.main(["--remote", "pkg", "install", "demo"]) == 1
    assert calls == [1]
    assert "local operation completed" in capsys.readouterr().err


def test_remote_package_list_and_uninstall_use_host_site(bridge, data, capsys):
    site = data / "python/3.12/site-packages"
    dist = site / "demo-1.0.dist-info"
    dist.mkdir(parents=True)
    (site / "demo.py").write_text("VALUE = 1")
    (dist / "RECORD").write_text("demo.py,,\ndemo-1.0.dist-info/RECORD,,\n")
    assert cli.main(["--remote", "pkg", "list"]) == 0
    assert "demo\t1.0" in capsys.readouterr().out
    assert cli.main(["--remote", "pkg", "uninstall", "demo"]) == 0
    assert not (site / "demo.py").exists()


def test_remote_venv_uses_target(bridge, data, monkeypatch):
    calls = []
    monkeypatch.setattr(uv, "ensure", lambda folder: folder / "uv")
    monkeypatch.setattr(
        venv,
        "create",
        lambda *args, **kwargs: calls.append((args, kwargs)) or data / ".venv",
    )
    assert cli.main(["--remote", "venv"]) == 0
    assert calls == [
        ((data, data / "uv"), {"target": env.Target("3.12", sys.platform, "arm64")})
    ]


def test_remote_extension_placements_and_requirements_share_target(
    bridge, data, example, monkeypatch
):
    manifest = example / "manifest.fontlabextj"
    value = json.loads(manifest.read_text())
    (example / "rule.py").write_text("RULE = 1")
    (example / "linked").mkdir()
    (example / "linked/__init__.py").write_text("LINKED = 1")
    value["install"] = [{"from": "rule.py", "to": "site-packages/."}]
    value["python"] = {"packages": ["linked"], "requires": ["demo"]}
    manifest.write_text(json.dumps(value))
    calls = []
    monkeypatch.setattr(packages, "install", lambda *a, **kw: calls.append((a, kw)))
    assert cli.main(["--remote", "ext", "install", str(example), "--copy"]) == 0
    site = data / "python/3.12/site-packages"
    assert (site / "rule.py").is_file()
    assert (site / "linked/__init__.py").is_file()
    assert not (data / "python/3.11").exists()
    assert calls == [
        ((data, ["demo"]), {"target": env.Target("3.12", sys.platform, "arm64")})
    ]
    assert cli.main(["--remote", "ext", "list"]) == 0
    assert cli.main(["--remote", "ext", "uninstall", value["id"]]) == 0
    assert not (site / "rule.py").exists()


def test_facts_reject_non_mapping():
    with pytest.raises(ValueError, match="malformed"):
        remote.facts(None)
