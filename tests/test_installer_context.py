# this_file: tests/test_installer_context.py
"""Installer entry admission uses fake providers and never deploys files."""
import ast
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
INSTALLERS = ("install.vfpy", "stub/install.vfpy", "src/fontlab_instamix/stub_install.vfpy")


@pytest.mark.parametrize("installer", INSTALLERS)
@pytest.mark.parametrize("context", ("missing", "explicit", "host", "import"))
def test_installer_entry_checks_context_before_ready_provider(tmp_path, monkeypatch, installer, context):
    calls = []

    def install_project(path):
        calls.append("deploy")
        if context in ("missing", "import"):
            raise AssertionError("blocked fake deployment; no filesystem installer exists")
        return []

    package = ModuleType("fontlab_instamix")
    monkeypatch.setitem(sys.modules, "fontlab_instamix", package)
    for name, attrs in {
        "legacy": {},
        "extension": {"preflight_plugin_migration": lambda: None},
        "bootstrap": {"_legacy_rollback": lambda: None, "install_project": install_project},
        "gui": {"message": lambda text: calls.append("message")},
    }.items():
        module = ModuleType("fontlab_instamix." + name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, module.__name__, module)
        monkeypatch.setattr(package, name, module, raising=False)
    # Block deployment before removing the inherited owned data-folder override.
    monkeypatch.setitem(sys.modules, "fontlab", None)
    monkeypatch.delenv("FONTLAB_DATA_DIR", raising=False)
    if context == "explicit":
        monkeypatch.setenv("FONTLAB_DATA_DIR", str(tmp_path / "data"))
    elif context == "host":
        host = ModuleType("fontlab")
        host.flPreferences = lambda: SimpleNamespace(dataPathDefault=str(tmp_path / "host-data"))
        monkeypatch.setitem(sys.modules, "fontlab", host)
    source = (ROOT / installer).read_text()
    ns = {"__name__": "install_vfpy_import", "__file__": str(tmp_path / "install.vfpy")}
    exec(compile(source, installer, "exec"), ns)
    assert calls == [], "import sentinel must not validate, bootstrap or deploy"
    if context == "import":
        assert list(tmp_path.iterdir()) == []
        return
    if ns["SELF_INSTALL"]:
        # Exercise the actual root entry without its forced wheel installation.
        def ready_provider(force=False):
            calls.append("ensure")
            return ns["required_api"]()
        ns["ensure"] = ready_provider
    entry = ast.Module(body=[ast.parse(source).body[-1]], type_ignores=[])
    ns["__name__"] = "external_installer_execution"
    if context == "missing":
        with pytest.raises(RuntimeError, match="run inside FontLab or set FONTLAB_DATA_DIR"):
            exec(compile(entry, installer, "exec"), ns)
        assert calls == [], "context refusal must precede provider reuse and deployment"
    else:
        exec(compile(entry, installer, "exec"), ns)
        assert "message" in calls
        assert ("deploy" in calls) == (not ns["SELF_INSTALL"])
    assert list(tmp_path.iterdir()) == [], "fake admission checks must not create data folders"
