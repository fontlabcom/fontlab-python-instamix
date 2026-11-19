# this_file: tests/test_remote.py
"""Remote transport is faked; filesystem placement uses the real installer."""

import json
import subprocess
import sys
import time
from importlib import metadata
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
        "in_fontlab": True,
    }
    state = SimpleNamespace(
        value=value,
        calls=[],
        events=[],
        default_bridge="/bridge from PATH",
        app=None,
        command=None,
        error=None,
        setup_error=None,
        version="2.0.13",
        nonce=True,
        refresh=True,
        active=False,
    )

    def find_bridge(command):
        state.events.append(("find", command))
        return state.default_bridge if command is None else command

    def ensure_ready(*, app=None, command):
        state.app = app
        state.events.append(("setup", command))
        if state.setup_error:
            raise state.setup_error

    class Client:
        def __init__(self, command=None):
            state.command = command
            state.events.append(("client", command))

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
                    state.events.append(("probe", None))
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

    version = metadata.version

    def installed_version(name):
        return state.version if name == "fontlab-remopy" else version(name)

    monkeypatch.setattr(metadata, "version", installed_version)
    monkeypatch.setitem(
        sys.modules,
        "fontlab_remopy",
        SimpleNamespace(
            FontLab=Client, ensure_ready=ensure_ready, find_bridge=find_bridge
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "fontlab_remopy.platforms",
        SimpleNamespace(DEFAULT_APP=data.parent / "System Apps" / "FontLab 9.app"),
    )
    return state


def test_env_runs_setup_before_client_and_preserves_bridge(bridge, data, capsys):
    assert cli.main(["--remote", "--bridge", "/bridge with spaces", "env"]) == 0
    assert json.loads(capsys.readouterr().out)["python"] == "3.12"
    assert bridge.command == "/bridge with spaces"
    assert bridge.events == [
        ("find", "/bridge with spaces"),
        ("setup", "/bridge with spaces"),
        ("client", "/bridge with spaces"),
        ("probe", None),
    ]
    assert bridge.calls == [(remote.PROBE, {})]
    assert not list(data.iterdir())


@pytest.mark.parametrize("version", ["2.0.13", "2.1.0", "2.0.13+local"])
def test_default_bridge_discovery_feeds_setup_and_client(bridge, capsys, version):
    bridge.version = version
    assert cli.main(["--remote", "env"]) == 0
    assert bridge.events == [
        ("find", None),
        ("setup", bridge.default_bridge),
        ("client", bridge.default_bridge),
        ("probe", None),
    ]
    assert json.loads(capsys.readouterr().out)["in_fontlab"]


@pytest.mark.parametrize("layout", ["home", "custom", "symlink"])
def test_macos_readiness_uses_the_selected_bridge_bundle(
    bridge, tmp_path, monkeypatch, layout
):
    monkeypatch.setattr(remote, "sys", SimpleNamespace(platform="darwin"))
    default = sys.modules["fontlab_remopy.platforms"].DEFAULT_APP
    app = tmp_path / "Home" / "Applications" / default.name
    if layout != "home":
        default.mkdir(parents=True)
        app = tmp_path / "Custom" / "FontLab Beta.app"
    executable = app / "Contents" / "MacOS" / "fontlab-mcp"
    executable.parent.mkdir(parents=True)
    executable.touch()
    if layout == "symlink":
        command = tmp_path / "bridge alias"
        command.symlink_to(executable)
    else:
        command = executable
    if layout == "home":
        bridge.default_bridge = str(command)
        args = ["--remote", "env"]
    else:
        args = ["--remote", "--bridge", str(command), "env"]
    assert cli.main(args) == 0
    assert bridge.app == app.resolve()
    assert bridge.events[-3:] == [
        ("setup", str(command)),
        ("client", str(command)),
        ("probe", None),
    ]


@pytest.mark.parametrize("default_present", [True, False])
def test_macos_wrapper_uses_default_or_user_installed_app(
    bridge, tmp_path, monkeypatch, default_present
):
    monkeypatch.setattr(remote, "sys", SimpleNamespace(platform="darwin"))
    home = tmp_path / "Home"
    monkeypatch.setattr(Path, "home", lambda: home)
    default = sys.modules["fontlab_remopy.platforms"].DEFAULT_APP
    user_app = home / "Applications" / default.name
    user_app.mkdir(parents=True)
    if default_present:
        default.mkdir(parents=True)
    wrapper = tmp_path / "bridge wrapper"
    wrapper.touch()
    assert cli.main(["--remote", "--bridge", str(wrapper), "env"]) == 0
    assert bridge.app == (default if default_present else user_app)
    assert bridge.command == str(wrapper)


@pytest.mark.parametrize("adjacent_present", [True, False])
def test_windows_bridge_prefers_adjacent_fontlab_executable(
    bridge, tmp_path, monkeypatch, adjacent_present
):
    monkeypatch.setattr(remote, "sys", SimpleNamespace(platform="win32"))
    default = tmp_path / "Program Files" / "FontLab 9.exe"
    sys.modules["fontlab_remopy.platforms"].DEFAULT_APP = default
    default.parent.mkdir()
    default.touch()
    executable = tmp_path / "Custom" / "fontlab-mcp.exe"
    executable.parent.mkdir()
    executable.touch()
    adjacent = executable.with_name(default.name)
    if adjacent_present:
        adjacent.touch()
    assert cli.main(["--remote", "--bridge", str(executable), "env"]) == 0
    assert bridge.app == (adjacent.resolve() if adjacent_present else default)
    assert bridge.command == str(executable)


def test_missing_bridge_stops_before_setup_and_client(bridge, capsys):
    bridge.default_bridge = None
    assert cli.main(["--remote", "env"]) == 1
    assert bridge.events == [("find", None)]
    assert "No executable FontLab MCP bridge found" in capsys.readouterr().err


def test_missing_optional_import_does_not_break_local_cli(monkeypatch, data, capsys):
    monkeypatch.setitem(sys.modules, "fontlab_remopy", None)
    assert cli.main(["--data-dir", str(data), "env"]) == 0
    assert cli.main(["--remote", "env"]) == 1
    assert "requires fontlab-remopy>=2.0.13" in capsys.readouterr().err


@pytest.mark.parametrize(
    "version", ["2.0.12", "2.0.13rc1", "2.0.13.dev0", None, "unknown"]
)
def test_unsupported_remopy_version_requires_upgrade(bridge, version, capsys):
    bridge.version = version
    assert cli.main(["--remote", "env"]) == 1
    assert "fontlab-python-instamix[remote]" in capsys.readouterr().err
    assert not bridge.events


def test_missing_readiness_helper_requires_upgrade(bridge, monkeypatch, capsys):
    monkeypatch.delattr(sys.modules["fontlab_remopy"], "ensure_ready")
    assert cli.main(["--remote", "env"]) == 1
    assert "fontlab-python-instamix[remote]" in capsys.readouterr().err
    assert not bridge.events


@pytest.mark.parametrize(
    "error", [TimeoutError(), subprocess.TimeoutExpired(["open"], 30)]
)
def test_setup_failure_stops_before_client_and_install(
    bridge, data, monkeypatch, capsys, error
):
    error.add_note("Setup outcome may be unknown; inspect setup/example")
    bridge.setup_error = error
    installs = []
    monkeypatch.setattr(packages, "install", lambda *args, **kwargs: installs.append(1))
    assert cli.main(["--remote", "pkg", "install", "demo"]) == 1
    assert bridge.events == [("find", None), ("setup", bridge.default_bridge)]
    assert not bridge.calls and not installs and not list(data.iterdir())
    diagnostic = capsys.readouterr().err
    assert "no automatic retry" in diagnostic
    assert "inspect setup/example" in diagnostic
    assert "partial local changes" not in diagnostic


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
    ("argv", "needs_host"),
    [
        (["--data-dir", "/conflict", "--remote", "pkg", "list"], True),
        (["--remote", "ext", "install", "missing", "--run-hooks"], False),
        (["--remote", "wrap", "missing"], False),
        (["--bridge", "/bridge", "env"], False),
    ],
)
def test_invalid_combinations_refuse(bridge, data, argv, needs_host):
    assert cli.main(argv) == 1
    assert not list(data.iterdir())
    if needs_host:
        assert bridge.events == [
            ("find", None),
            ("setup", bridge.default_bridge),
            ("client", bridge.default_bridge),
            ("probe", None),
        ]
    else:
        assert not bridge.events


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
    assert bridge.events.count(("setup", bridge.default_bridge)) == 1
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
