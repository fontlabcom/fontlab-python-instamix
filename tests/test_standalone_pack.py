# this_file: tests/test_standalone_pack.py
"""Owned wheel/bootstrap and multi-extension packaging regressions."""
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from fontlab_instamix import cli, extension, stub, wrap

ROOT = Path(__file__).resolve().parents[1]
INFO = "fontlab_python_instamix-1.2.3.dist-info"


def wheel(gui="def message(text):\n    print('fixture GUI: ' + text)\n"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, value in {
            "fontlab_instamix/__init__.py": "VALUE = 123\n",
            "fontlab_instamix/legacy.py": "",
            "fontlab_instamix/gui.py": gui,
            INFO + "/METADATA": "Name: fontlab-python-instamix\nVersion: 1.2.3\n",
            INFO + "/WHEEL": "Wheel-Version: 1.0\n",
            INFO + "/RECORD": "",
            INFO + "/licenses/LICENSE": "Owned test fixture; no third party source.\n",
        }.items():
            archive.writestr(name, value)
    return buffer.getvalue()


def namespace(tmp_path, monkeypatch):
    monkeypatch.setenv("FONTLAB_DATA_DIR", str(tmp_path / "data"))
    ns = {"__name__": "install_vfpy_import", "__file__": str(tmp_path / "install.vfpy")}
    exec(compile((ROOT / "install.vfpy").read_text(), "install.vfpy", "exec"), ns)
    return ns


def local_wheel(tmp_path, gui="def message(text):\n    print('fixture GUI: ' + text)\n"):
    path = tmp_path / "dist" / "fontlab_python_instamix-1.2.3-py3-none-any.whl"
    path.parent.mkdir()
    path.write_bytes(wheel(gui))
    return path


def test_standalone_offline_wheel_preserves_metadata_and_imports(tmp_path, monkeypatch):
    ns = namespace(tmp_path, monkeypatch)
    local_wheel(tmp_path)
    # A separate Python proves the import comes from installed bytes, not pytest's src path.
    installer = tmp_path / "install.vfpy"
    installer.write_text((ROOT / "install.vfpy").read_text())
    script = """import runpy, sys, importlib.metadata
ns = runpy.run_path(sys.argv[1], run_name='install_vfpy_import')
m = ns['ensure'](force=True)
assert m.VALUE == 123
assert m.__file__.startswith(str(ns['site']()))
assert importlib.metadata.version('fontlab-python-instamix') == '1.2.3'
"""
    subprocess.run([sys.executable, "-I", "-c", script, str(installer)], check=True)
    assert (ns["site"]() / INFO / "licenses/LICENSE").read_text().startswith("Owned")


@pytest.mark.parametrize("failure", ["download", "digest", "replace"])
def test_bootstrap_failure_preserves_package_link_and_metadata(tmp_path, monkeypatch, failure):
    ns = namespace(tmp_path, monkeypatch)
    site = ns["site"]()
    site.mkdir(parents=True)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "owned").write_bytes(b"previous")
    (site / "fontlab_instamix").symlink_to(checkout, target_is_directory=True)
    oldinfo = site / "fontlab_python_instamix-0.1.dist-info"
    oldinfo.mkdir()
    (oldinfo / "METADATA").write_bytes(b"previous metadata")
    if failure == "replace":
        local_wheel(tmp_path)
        original = Path.rename
        def fail(self, target):
            if self.parent.name == "new" and self.name == "fontlab_instamix":
                raise OSError("replace failure")
            return original(self, target)
        monkeypatch.setattr(Path, "rename", fail)
    else:
        def response(url, timeout):
            if failure == "download":
                raise OSError("offline")
            if url == "wheel":
                return io.BytesIO(wheel())
            return io.BytesIO(json.dumps({"urls": [{"packagetype": "bdist_wheel", "filename": "x-py3-none-any.whl", "url": "wheel", "digests": {"sha256": "0" * 64}}]}).encode())
        monkeypatch.setattr(ns["urllib"].request, "urlopen", response)
    with pytest.raises((OSError, RuntimeError)):
        ns["ensure"](force=True)
    assert (site / "fontlab_instamix").is_symlink()
    assert (checkout / "owned").read_bytes() == b"previous"
    assert (oldinfo / "METADATA").read_bytes() == b"previous metadata"
    assert sorted(p.name for p in site.iterdir()) == ["fontlab_instamix", oldinfo.name]


def folders(tmp_path):
    source = tmp_path / "owned.py"
    source.write_text("# Owned test fixture\n")
    return [wrap.make_folder(source, tmp_path, "com.example." + name) for name in ("first", "second")]


def test_pack_two_extensions_install_and_uninstall_independently(tmp_path):
    roots = folders(tmp_path)
    output = tmp_path / "both.fontlabextz"
    assert cli.main(["pack", *(str(p) for p in roots), "--out", str(output)]) == 0
    data = tmp_path / "data"
    records = extension.install(output, data, copy=True)
    assert {r["id"] for r in records} == {"com.example.first", "com.example.second"}
    extension.uninstall("com.example.first", data)
    assert [r["id"] for r in extension.installed(data)] == ["com.example.second"]
    extension.uninstall("com.example.second", data)
    assert extension.installed(data) == []
    entry = stub.write(roots[0])
    assert len(entry.read_text().splitlines()) == 2


@pytest.mark.parametrize("invalid", ["duplicate", "mismatch", "manifest", "empty", "write"])
def test_invalid_pack_preserves_previous_output(tmp_path, monkeypatch, invalid):
    roots = folders(tmp_path)
    output = tmp_path / "both.fontlabextz"
    output.write_bytes(b"previous archive")
    if invalid == "duplicate":
        roots.append(roots[0])
    elif invalid == "mismatch":
        new = tmp_path / "wrong.fontlabext"
        roots[1].rename(new)
        roots[1] = new
    elif invalid == "manifest":
        (roots[1] / "manifest.fontlabextj").write_text("{}")
    elif invalid == "empty":
        roots = []
    else:
        def fail(*args, **kwargs):
            raise OSError("write failure")
        monkeypatch.setattr(zipfile.ZipFile, "write", fail)
    with pytest.raises((ValueError, OSError)):
        wrap.make_zip(roots, output)
    assert output.read_bytes() == b"previous archive"


def test_templates_are_generated_from_one_source():
    source = (ROOT / "src/fontlab_instamix/stub_install.vfpy").read_text()
    assert stub.text() == source.replace("this_file: src/fontlab_instamix/stub_install.vfpy", "this_file: stub/install.vfpy")
    assert (ROOT / "install.vfpy").read_text() == source.replace("this_file: src/fontlab_instamix/stub_install.vfpy", "this_file: install.vfpy").replace("SELF_INSTALL = False", "SELF_INSTALL = True")


def test_site_uses_live_python_version_and_rejects_escape(tmp_path, monkeypatch):
    import types
    ns = namespace(tmp_path, monkeypatch)
    monkeypatch.setitem(sys.modules, "fontlab", types.SimpleNamespace())
    site = ns["site"]()
    assert site.parts[-2] == f"{sys.version_info.major}.{sys.version_info.minor}"
    root = Path(ns["os"].environ["FONTLAB_DATA_DIR"])
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "python").symlink_to(outside, target_is_directory=True)
    with pytest.raises(RuntimeError, match="escapes"):
        ns["ensure"](force=True)
    assert list(outside.iterdir()) == []


def test_two_line_entry_runs_with_installed_instamix(tmp_path, monkeypatch):
    root = folders(tmp_path)[0]
    entry = stub.write(root)
    data = tmp_path / "data"
    monkeypatch.setenv("FONTLAB_DATA_DIR", str(data))
    exec(compile(entry.read_text(), str(entry), "exec"), {"__file__": str(entry)})
    assert [r["id"] for r in extension.installed(data)] == ["com.example.first"]


def test_pack_namespace_case_refused_and_suffix_case_supported(tmp_path):
    root = folders(tmp_path)[0]
    output = tmp_path / "archive.fontlabextz"
    output.write_bytes(b"prior")
    wrong = root.with_name("Com.example.first.fontlabext")
    root.rename(wrong)
    with pytest.raises(ValueError, match="manifest id"):
        wrap.make_zip([wrong], output)
    assert output.read_bytes() == b"prior"
    supported = wrong.with_name("com.example.first.FONTLABEXT")
    wrong.rename(supported)
    wrap.make_zip([supported], output)
    assert extension.install(output, tmp_path / "data", copy=True)[0]["id"] == "com.example.first"


def test_incomplete_runtime_wheel_restores_prior_installation(tmp_path, monkeypatch):
    ns = namespace(tmp_path, monkeypatch)
    site = ns["site"]()
    package = site / "fontlab_instamix"
    package.mkdir(parents=True)
    (package / "__init__.py").write_bytes(b"PREVIOUS = True\n")
    old = site / "fontlab_python_instamix-0.1.dist-info"
    old.mkdir()
    (old / "METADATA").write_bytes(b"prior metadata")
    local_wheel(tmp_path, gui="message = None\n")
    saved = {k: v for k, v in sys.modules.items() if k == "fontlab_instamix" or k.startswith("fontlab_instamix.")}
    try:
        with pytest.raises(ImportError, match="gui.message"):
            ns["ensure"](force=True)
        assert all(sys.modules[k] is v for k, v in saved.items())
    finally:
        sys.modules.update(saved)
    assert (package / "__init__.py").read_bytes() == b"PREVIOUS = True\n"
    assert (old / "METADATA").read_bytes() == b"prior metadata"


def test_actual_standalone_entry_executes_complete_wheel(tmp_path, monkeypatch):
    installer = tmp_path / "install.vfpy"
    installer.write_text((ROOT / "install.vfpy").read_text())
    local_wheel(tmp_path)
    monkeypatch.setenv("FONTLAB_DATA_DIR", str(tmp_path / "data"))
    result = subprocess.run([sys.executable, "-I", "-c", "import runpy,sys;runpy.run_path(sys.argv[1])", str(installer)], check=True, text=True, capture_output=True)
    assert "fixture GUI: Installed fontlab-instamix" in result.stdout


def test_reused_project_copy_requires_callable_install_project(tmp_path, monkeypatch):
    from types import SimpleNamespace
    ns = namespace(tmp_path, monkeypatch)
    ns["SELF_INSTALL"] = False
    def imported(name):
        if name == "fontlab":
            raise ImportError(name)
        if name.endswith(".gui"):
            return SimpleNamespace(message=lambda text: None)
        if name.endswith(".bootstrap"):
            return SimpleNamespace(install_project=None)
        return SimpleNamespace()
    ns["importlib"] = SimpleNamespace(import_module=imported, invalidate_caches=lambda: None)
    def refused(target):
        raise OSError("fallback attempted")
    ns["download"] = refused
    with pytest.raises(OSError, match="fallback attempted"):
        ns["ensure"]()
