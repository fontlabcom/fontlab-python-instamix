# this_file: tests/test_parity.py
"""Parity with the legacy install.vfpy: markers, versions, dist-info, initScript,
launchers, legacy migration, bundles and the stub installer."""

import hashlib
import importlib.metadata
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from fontlab_instamix import (
    bootstrap,
    cli,
    dest,
    distinfo,
    extension,
    initscript,
    launchers,
    legacy,
    markers,
    stub,
    vcs,
)

ROOT = Path(__file__).resolve().parents[1]
NO_REQS = lambda d, specs: None


def _site(data):
    return data / "python" / "3.11" / "site-packages"


def _project(
    root,
    name="proj-a",
    ext_id="com.example.proja",
    extra_toml="",
    version='version = "2.0"',
):
    pkg = root / "src" / name.replace("-", "_")
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\n{version}\n'
        f'[tool.fontlab-install]\nid = "{ext_id}"\npackages = ["src/{name.replace("-", "_")}"]\n{extra_toml}'
    )
    (root / "Scripts").mkdir()
    (root / "Scripts" / "Tool.py").write_text("print(1)\n")
    (root / "install.vfpy").write_text("# installer\n")
    return root


# --- markers --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        ('python_version >= "3.10"', True),
        ("python_version < '3.11'", False),
        ('python_version == "3.11" and (os_name == "nt" or os_name != "nt")', True),
        ('"3.1" in python_full_version', True),
        ('extra == "gui"', False),
        ('python_version > "3.9.0" or extra == "x"', True),
    ],
)
def test_markers_evaluate_when_marker_then_fontlab_target(marker, expected):
    assert markers.evaluate(marker) is expected


def test_markers_evaluate_when_extra_given_then_matches():
    assert markers.evaluate('extra == "gui"', extra="gui")


def test_markers_evaluate_when_platform_then_host(monkeypatch):
    expected = sys.platform == "darwin"
    assert markers.evaluate('sys_platform == "darwin"') is expected
    assert markers.applies('pyobjc; sys_platform == "darwin"') is expected


def test_markers_evaluate_when_garbage_then_error():
    with pytest.raises(markers.MarkerError):
        markers.evaluate('python_version >= "3" and')


def test_markers_split_when_spec_then_requirement_and_marker():
    assert markers.split('fonttools>=4 ; python_version >= "3.8"') == (
        "fonttools>=4",
        'python_version >= "3.8"',
    )
    assert markers.split("fonttools") == ("fonttools", "")


# --- version --------------------------------------------------------------------


def test_project_version_when_static_then_used(tmp_path):
    assert vcs.project_version(tmp_path, {"project": {"version": "1.2"}}) == "1.2"


def test_project_version_when_dynamic_and_git_then_describe(tmp_path):
    def runner(args, **kwargs):
        return subprocess.CompletedProcess(
            args, 0, stdout="v1.4.0-3-gabc1234\n", stderr=""
        )

    version = vcs.project_version(
        tmp_path, {"project": {"dynamic": ["version"]}}, runner
    )
    assert version.startswith("1.4.")


def test_project_version_when_dynamic_without_git_then_fallback(tmp_path):
    def runner(args, **kwargs):
        raise FileNotFoundError("git")

    pyproject = {
        "project": {"dynamic": ["version"]},
        "tool": {"hatch": {"version": {"fallback-version": "0.9.1"}}},
    }
    assert vcs.project_version(tmp_path, pyproject, runner) == "0.9.1"
    pyproject = {
        "project": {"dynamic": ["version"]},
        "tool": {"hatch": {"version": {"raw-options": {"fallback_version": "0.8"}}}},
    }
    assert vcs.project_version(tmp_path, pyproject, runner) == "0.8"


def test_project_version_when_version_file_then_preferred(tmp_path):
    (tmp_path / "_v.py").write_text('__version__ = version = "3.1.4"\n')
    pyproject = {
        "project": {"dynamic": ["version"]},
        "tool": {"hatch": {"build": {"hooks": {"vcs": {"version-file": "_v.py"}}}}},
    }
    assert vcs.project_version(tmp_path, pyproject, lambda *a, **k: 1 / 0) == "3.1.4"


# --- dist-info ------------------------------------------------------------------


def test_distinfo_metadata_when_extras_then_marked_lines():
    text = distinfo.metadata(
        "Fontlab-App",
        "1.0",
        ["fonttools"],
        {"GUI": ['pyobjc; sys_platform == "darwin"', "rich"]},
    )
    assert "Name: Fontlab-App\nVersion: 1.0\n" in text
    assert "Requires-Dist: fonttools\n" in text
    assert "Provides-Extra: gui\n" in text
    assert (
        'Requires-Dist: pyobjc ; (sys_platform == "darwin") and extra == "gui"\n'
        in text
    )
    assert 'Requires-Dist: rich ; extra == "gui"\n' in text


def test_install_project_when_installed_then_metadata_version_found(data, tmp_path):
    root = _project(tmp_path / "proj-a", extra_toml='dependencies = ["fonttools>=4"]\n')
    bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    folder = _site(data) / "proj_a-2.0.dist-info"
    assert (folder / "INSTALLER").read_text() == "fontlab-instamix\n"
    assert "Requires-Dist: fonttools>=4" in (folder / "METADATA").read_text()
    assert (folder / "RECORD").read_text().splitlines()[0] == "proj_a,,"
    assert (folder / "WHEEL").is_file()
    [dist] = importlib.metadata.distributions(path=[str(_site(data))], name="proj-a")
    assert dist.version == "2.0"
    assert extension.uninstall("com.example.proja", data) == []
    assert not folder.exists()


def test_install_project_when_symlinked_package_uninstalled_then_checkout_kept(
    data, tmp_path
):
    root = _project(tmp_path / "proj-a")
    bootstrap.install_project(
        root / "install.vfpy", data, requirements=NO_REQS, copy=False
    )
    assert (_site(data) / "proj_a").is_symlink()
    extension.uninstall("com.example.proja", data)
    assert (root / "src" / "proj_a" / "__init__.py").is_file()
    assert (root / "Scripts" / "Tool.py").is_file()


def test_install_project_when_marker_excludes_then_dep_skipped(data, tmp_path):
    root = _project(
        tmp_path / "proj-a",
        extra_toml="dependencies = ['old; python_version < \"3.0\"', 'new']\n",
    )
    calls = []
    bootstrap.install_project(
        root / "install.vfpy", data, requirements=lambda d, s: calls.append(s)
    )
    assert calls == [["new"]]
    metadata = (_site(data) / "proj_a-2.0.dist-info" / "METADATA").read_text()
    assert (
        'Requires-Dist: old; python_version < "3.0"' in metadata
    )  # METADATA keeps every spec


# --- scripts mapping and bundles -------------------------------------------------


def test_install_project_when_listed_folder_then_scripts_subfolder(data, tmp_path):
    root = _project(tmp_path / "proj-a", extra_toml='scripts = ["tools/Extra"]\n')
    (root / "tools" / "Extra").mkdir(parents=True)
    (root / "tools" / "Extra" / "Run.py").write_text("print(2)\n")
    (root / "Scripts" / "__pycache__").mkdir()
    (root / "Scripts" / "__pycache__" / "Tool.cpython-311.pyc").write_bytes(b"x")
    (root / "Scripts" / ".DS_Store").write_bytes(b"x")
    bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    assert (data / "Scripts" / "Tool.py").is_file()
    assert (data / "Scripts" / "tools" / "Extra" / "Run.py").is_file()
    assert not (data / "Scripts" / "__pycache__").exists()
    assert not (data / "Scripts" / ".DS_Store").exists()


def test_install_project_when_bundle_then_extensions_kind(data, tmp_path):
    root = _project(tmp_path / "proj-a", extra_toml='extensions = "Extensions"\n')
    bundle = root / "Extensions" / "filters" / "Blur.fontlabFilter"
    bundle.mkdir(parents=True)
    (bundle / "plugin.json").write_text("{}")
    (bundle / "main.py").write_text("print(3)\n")
    bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    assert (
        data / "Extensions" / "filters" / "Blur.fontlabFilter" / "main.py"
    ).is_file()


@pytest.mark.parametrize(
    "rule", ["Extensions", "Extensions/Library", "Extensions/.instamix/x"]
)
def test_dest_resolve_when_reserved_extensions_folder_then_error(rule):
    with pytest.raises(dest.DestError):
        dest.resolve(rule, "x")


def test_read_project_when_no_packages_key_then_hatch_wheel_packages(tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "p"\nversion = "1"\ndependencies = ["fonttools"]\n'
        '[project.optional-dependencies]\ngui = ["rich"]\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["src/p"]\n'
        '[tool.fontlab-install]\nid = "com.example.p"\n'
    )
    info = bootstrap.read_project(root)
    assert info.packages == ("src/p",)
    assert info.dependencies == ("fonttools",)
    assert info.extras == {"gui": ["rich"]}
    assert info.scripts == ()
    assert not info.init_script


# --- initScript -----------------------------------------------------------------


def test_initscript_when_added_and_removed_then_other_lines_kept(tmp_path):
    (tmp_path / "initScript.py").write_bytes(b"print('mine')\r\n")
    assert initscript.update(tmp_path)
    text = (tmp_path / "initScript.py").read_bytes()
    assert (
        text.startswith(b"print('mine')\r\n")
        and initscript.BEGIN in text
        and b"\r\n# END" in text
    )
    assert not initscript.update(tmp_path)  # idempotent
    assert initscript.update(tmp_path, remove=True)
    assert (tmp_path / "initScript.py").read_bytes() == b"print('mine')\r\n"


def test_initscript_when_duplicate_markers_then_error():
    with pytest.raises(ValueError, match="Malformed"):
        initscript.updated(initscript.HOOK + initscript.HOOK, remove=False)


def test_initscript_when_symlink_then_refused(tmp_path):
    (tmp_path / "real.py").write_text("")
    (tmp_path / "initScript.py").symlink_to(tmp_path / "real.py")
    with pytest.raises(ValueError, match="symlink"):
        initscript.update(tmp_path)


def test_install_project_when_app_id_then_initscript_block_round_trip(data, tmp_path):
    root = _project(tmp_path / "app", "fontlab-fontlabapp", initscript.APP_ID)
    (data / "initScript.py").write_text("print('owner')\n")
    [record] = bootstrap.install_project(
        root / "install.vfpy", data, requirements=NO_REQS
    )
    assert record["init_script"] is True
    assert initscript.BEGIN in (data / "initScript.py").read_bytes()
    extension.uninstall(initscript.APP_ID, data)
    assert (data / "initScript.py").read_text() == "print('owner')\n"


# --- launchers ------------------------------------------------------------------


def test_install_project_when_installed_then_launchers_written_and_removed(
    data, tmp_path
):
    root = _project(tmp_path / "proj-a")
    bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    folder = data / launchers.FOLDER
    uninstaller = folder / "Uninstall com.example.proja.py"
    assert "from fontlab_instamix import launch" in uninstaller.read_text()
    assert "launch.uninstall('com.example.proja')" in uninstaller.read_text()
    assert "launch.list_extensions()" in (folder / launchers.LIST).read_text()
    compile(uninstaller.read_text(), str(uninstaller), "exec")
    extension.uninstall("com.example.proja", data)
    assert not folder.exists()


def test_launch_when_called_then_lists_and_uninstalls(data, tmp_path, monkeypatch):
    from fontlab_instamix import gui, launch

    shown = []
    monkeypatch.setattr(
        gui, "message", lambda text, title="", error=False: shown.append(text)
    )
    monkeypatch.setattr(gui, "confirm", lambda text, title="": True)
    root = _project(tmp_path / "proj-a")
    bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    assert "com.example.proja  2.0" in launch.list_extensions(data)
    assert launch.uninstall("com.example.proja", data) == []
    assert "Uninstalled com.example.proja" in shown[-1]


# --- legacy migration -----------------------------------------------------------


def _legacy(data, root, ext_id, *, hashed, edited=False):
    """Simulate a legacy install.vfpy install (remopy family or plugmix family)."""
    site, scripts = _site(data), data / "Scripts"
    site.mkdir(parents=True)
    menu = scripts / "Extensions"
    menu.mkdir(parents=True)
    tool = scripts / "Tool.py"
    tool.write_text("print(1)\n" if not edited else "print('edited')\n")
    package = site / "proj_a"
    package.symlink_to(root / "src" / "proj_a", target_is_directory=True)
    info = site / "proj_a-1.0.dist-info"
    info.mkdir()
    (info / "INSTALLER").write_text("install.vfpy\n")
    (info / "METADATA").write_text("Name: proj-a\nVersion: 1.0\n")
    (site / "fontlab_install.py").write_text('MODULE = "fontlab_install"\n')
    (menu / legacy.MARKER).write_text(json.dumps({"id": "fontlab_install"}) + "\n")
    (menu / "List Extensions.py").write_text(
        legacy.LAUNCHER % ("List Extensions", "list_extensions()")
    )
    uninstaller = menu / f"Uninstall {ext_id}.py"
    uninstaller.write_text(
        legacy.LAUNCHER % ("Uninstall " + ext_id, f"uninstall({ext_id!r})")
    )
    files = [str(package), str(info), str(tool), str(uninstaller)]
    record = {
        "action": "install",
        "id": ext_id,
        "version": "1.0",
        "files": files,
        "source": str(root),
    }
    if hashed:
        record["hashes"] = {str(tool): hashlib.sha256(b"print(1)\n").hexdigest()}
        record["links"] = {str(package): os.readlink(package)}
    log = legacy.log_path(data, ext_id)
    log.parent.mkdir(parents=True)
    log.write_text(json.dumps(record) + "\n")
    (scripts / "Mine.py").write_text("user file\n")
    return log


@pytest.mark.parametrize("hashed", [False, True])
def test_install_project_when_legacy_install_then_migrated(data, tmp_path, hashed):
    root = _project(tmp_path / "proj-a")
    log = _legacy(data, root, "com.example.proja", hashed=hashed)
    bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    site = _site(data)
    assert not (site / "proj_a-1.0.dist-info").exists()
    assert (
        site / "proj_a-2.0.dist-info" / "INSTALLER"
    ).read_text() == "fontlab-instamix\n"
    assert (data / "Scripts" / "Tool.py").is_file()
    assert (data / "Scripts" / "Mine.py").read_text() == "user file\n"  # not in the log
    assert not (site / "fontlab_install.py").exists()
    assert not (data / "Scripts" / "Extensions").exists()
    assert json.loads(log.read_text().splitlines()[-1])["action"] == "uninstall"
    assert (root / "src" / "proj_a" / "__init__.py").is_file()


def test_install_project_when_legacy_script_edited_then_refused_and_nothing_removed(
    data, tmp_path
):
    root = _project(tmp_path / "proj-a")
    _legacy(data, root, "com.example.proja", hashed=True, edited=True)
    with pytest.raises(legacy.MigrationError, match="Tool.py"):
        bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    assert (data / "Scripts" / "Tool.py").read_text() == "print('edited')\n"
    assert (_site(data) / "proj_a-1.0.dist-info").is_dir()
    assert legacy.installed(data, "com.example.proja")


def test_legacy_cleanup_when_other_legacy_active_then_shared_tools_kept(data, tmp_path):
    root = _project(tmp_path / "proj-a")
    _legacy(data, root, "com.example.proja", hashed=False)
    other = legacy.log_path(data, "com.example.other")
    other.parent.mkdir(parents=True)
    other.write_text(
        json.dumps({"action": "install", "id": "com.example.other", "files": []}) + "\n"
    )
    bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    assert (_site(data) / "fontlab_install.py").exists()
    assert (data / "Scripts" / "Extensions" / "List Extensions.py").exists()


def test_legacy_plan_when_path_outside_data_then_kept(data, tmp_path):
    outside = tmp_path / "elsewhere.py"
    outside.write_text("x")
    state = {"id": "com.example.x", "files": [str(outside)]}
    remove, kept = legacy.plan(data, state, set())
    assert remove == [] and kept[0][0] == str(outside)
    assert outside.exists()


# --- stub -----------------------------------------------------------------------


def test_stub_when_packaged_then_equals_root_copy_and_short():
    text = stub.text()
    assert text == (ROOT / "stub" / "install.vfpy").read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 40
    compile(text, "install.vfpy", "exec")


def test_stub_cli_when_folder_then_written_and_force_needed(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    assert cli.main(["stub", str(tmp_path)]) == 0
    assert (tmp_path / "install.vfpy").read_text() == stub.text()
    with pytest.raises(FileExistsError):
        stub.write(tmp_path)
    assert cli.main(["stub", "--force", str(tmp_path)]) == 0


def _stub_namespace(tmp_path, monkeypatch, data):
    """Load the stub's functions without running its install block."""
    monkeypatch.setenv("FONTLAB_DATA_DIR", str(data))
    namespace = {
        "__name__": "install_vfpy_import",
        "__file__": str(tmp_path / "repo" / "install.vfpy"),
    }
    exec(compile(stub.text(), "install.vfpy", "exec"), namespace)  # noqa: S102
    return namespace


def _wheel(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return buffer.getvalue()


def _fake_pypi(monkeypatch, blob, digest):
    import urllib.request

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    info = {
        "urls": [
            {"packagetype": "sdist"},
            {
                "packagetype": "bdist_wheel",
                "url": "wheel",
                "digests": {"sha256": digest},
            },
        ]
    }
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda url, timeout=0: Response(
            blob if url == "wheel" else json.dumps(info).encode()
        ),
    )


def test_stub_download_when_sha_matches_then_only_package_extracted(
    tmp_path, monkeypatch, data
):
    ns = _stub_namespace(tmp_path, monkeypatch, data)
    blob = _wheel(
        {
            "fontlab_instamix/__init__.py": "X = 1\n",
            "evil/x.py": "",
            "fontlab_python_instamix-1.dist-info/RECORD": "",
        }
    )
    _fake_pypi(monkeypatch, blob, hashlib.sha256(blob).hexdigest())
    target = tmp_path / "site"
    target.mkdir()
    ns["download"](target)
    assert (target / "fontlab_instamix" / "__init__.py").read_text() == "X = 1\n"
    assert sorted(p.name for p in target.iterdir()) == ["fontlab_instamix"]


def test_stub_download_when_sha_differs_then_refused(tmp_path, monkeypatch, data):
    ns = _stub_namespace(tmp_path, monkeypatch, data)
    blob = _wheel({"fontlab_instamix/__init__.py": ""})
    _fake_pypi(monkeypatch, blob, "0" * 64)
    target = tmp_path / "site"
    target.mkdir()
    with pytest.raises(RuntimeError, match="sha256"):
        ns["download"](target)
    assert not (target / "fontlab_instamix").exists()


def test_stub_ensure_when_sibling_checkout_then_copied_into_site(
    tmp_path, monkeypatch, data
):
    ns = _stub_namespace(tmp_path, monkeypatch, data)
    sibling = tmp_path / "fontlab-python-instamix" / "src" / "fontlab_instamix"
    sibling.mkdir(parents=True)
    (sibling / "__init__.py").write_text("SIBLING = True\n")
    import importlib as real_importlib

    calls = []

    def fake_import(name):
        calls.append(name)
        if len(calls) == 1:
            raise ImportError(name)
        return name

    saved = {k: v for k, v in sys.modules.items() if k.startswith("fontlab_instamix")}
    monkeypatch.setattr(real_importlib, "import_module", fake_import)
    monkeypatch.setitem(ns, "importlib", real_importlib)
    try:
        assert ns["ensure"]() == "fontlab_instamix"
    finally:
        sys.modules.update(
            saved
        )  # the stub purges fontlab_instamix* before re-importing
    assert (
        _site(data) / "fontlab_instamix" / "__init__.py"
    ).read_text() == "SIBLING = True\n"
    assert calls == ["fontlab_instamix.legacy", "fontlab_instamix"]


# --- fix round 1 ----------------------------------------------------------------


def test_install_project_when_two_projects_ship_scripts_readme_then_both_install(
    data, tmp_path
):
    for name, ext_id in (
        ("proj-a", "com.example.proja"),
        ("proj-b", "com.example.projb"),
    ):
        root = _project(tmp_path / name, name, ext_id)
        (root / "Scripts" / "README.md").write_text(f"{name} docs\n")
        (root / "Scripts" / "LICENSE").write_text("MIT\n")
        (root / "Scripts" / "Contours").mkdir()
        (root / "Scripts" / "Contours" / f"{name}.py").write_text("print(4)\n")
        (root / "Scripts" / "Contours" / f"README-{name}.md").write_text("kept\n")
        (root / "Scripts" / "Tool.py").rename(root / "Scripts" / f"{name}-tool.py")
        bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    scripts = data / "Scripts"
    assert not (scripts / "README.md").exists() and not (scripts / "LICENSE").exists()
    assert (scripts / "Contours" / "proj-a.py").is_file() and (
        scripts / "Contours" / "proj-b.py"
    ).is_file()
    assert (
        scripts / "Contours" / "README-proj-a.md"
    ).is_file()  # docs inside subfolders still install
    assert (scripts / "proj-a-tool.py").is_file() and (
        scripts / "proj-b-tool.py"
    ).is_file()


def test_install_project_when_scripts_only_docs_then_no_scripts_rule(data, tmp_path):
    root = _project(tmp_path / "proj-a")
    (root / "Scripts" / "Tool.py").unlink()
    (root / "Scripts" / "README.md").write_text("docs\n")
    bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    assert not (data / "Scripts" / "README.md").exists()


@pytest.mark.parametrize(
    ("marker", "expected"),
    [
        ('platform_release >= "6.8.0-45-generic"', "platform_release"),
        ('python_version == "3.11.0"', True),
        ('python_version ~= "3.10"', True),
        ('python_version != "3.11"', False),
    ],
)
def test_markers_evaluate_when_mixed_version_text_then_consistent_types(
    marker, expected, monkeypatch
):
    if (
        expected == "platform_release"
    ):  # not a plain version: compared as strings, no TypeError
        env = markers.environment() | {"platform_release": "7.0-custom"}
        monkeypatch.setattr(markers, "environment", lambda *args: env)
        expected = True  # "7" > "6" as text
    assert markers.evaluate(marker) is expected


def test_stub_ensure_when_old_instamix_installed_then_replaced(
    tmp_path, monkeypatch, data
):
    ns = _stub_namespace(tmp_path, monkeypatch, data)
    old = _site(data) / "fontlab_instamix"
    old.mkdir(parents=True)
    (old / "__init__.py").write_text("OLD = True\n")
    sibling = tmp_path / "fontlab-python-instamix" / "src" / "fontlab_instamix"
    sibling.mkdir(parents=True)
    (sibling / "__init__.py").write_text("NEW = True\n")
    (sibling / "legacy.py").write_text("")
    import importlib as real_importlib

    seen = []

    def fake_import(name):
        seen.append(name)
        if (old / "legacy.py").exists():
            return name
        raise ImportError(name)  # 1.0.0 has no fontlab_instamix.legacy

    saved = {k: v for k, v in sys.modules.items() if k.startswith("fontlab_instamix")}
    monkeypatch.setattr(real_importlib, "import_module", fake_import)
    try:
        assert ns["ensure"]() == "fontlab_instamix"
    finally:
        sys.modules.update(saved)
    assert (old / "__init__.py").read_text() == "NEW = True\n"
    assert str(_site(data)) in sys.path
    sys.path.remove(str(_site(data)))


def test_project_version_when_git_checkout_then_describe_before_version_file(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "_v.py").write_text('version = "0.0.1"\n')
    pyproject = {
        "project": {"dynamic": ["version"]},
        "tool": {"hatch": {"build": {"hooks": {"vcs": {"version-file": "_v.py"}}}}},
    }

    def runner(args, **kwargs):
        return subprocess.CompletedProcess(
            args, 0, stdout="v2.0.0-0-gabc1234\n", stderr=""
        )

    assert vcs.project_version(tmp_path, pyproject, runner) == "2.0.0"


def test_stub_download_when_no_wheel_then_clear_error(tmp_path, monkeypatch, data):
    import urllib.request

    ns = _stub_namespace(tmp_path, monkeypatch, data)
    body = json.dumps({"urls": [{"packagetype": "sdist"}]}).encode()
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda url, timeout=0: io.BytesIO(body)
    )
    with pytest.raises(RuntimeError, match="no fontlab-instamix wheel"):
        ns["download"](tmp_path)


def test_initscript_when_only_block_removed_then_file_deleted(tmp_path):
    initscript.update(tmp_path)
    assert (tmp_path / "initScript.py").is_file()
    assert initscript.update(tmp_path, remove=True)
    assert not (tmp_path / "initScript.py").exists()


def test_initscript_when_user_content_then_file_kept(tmp_path):
    (tmp_path / "initScript.py").write_text("print('mine')\n")
    initscript.update(tmp_path)
    initscript.update(tmp_path, remove=True)
    assert "mine" in (tmp_path / "initScript.py").read_text()


def _stale_copy(data, root, ext_id):
    """Add an old-version copy of Tool.py that the log lists only under hashes."""
    old = data / "Scripts" / "Old Tool.py"
    old.write_text("print('old version')\n")
    log = legacy.log_path(data, ext_id)
    record = json.loads(log.read_text().splitlines()[0])
    record["hashes"] = {**record.get("hashes", {}), str(old): "0" * 64}
    log.write_text(json.dumps(record) + "\n")
    return old


def _project_with_old_tool(tmp_path):
    root = _project(tmp_path / "proj-a")
    (root / "Scripts").mkdir(exist_ok=True)
    (root / "Scripts" / "Old Tool.py").write_text("print('new')\n")
    return root


def test_install_project_when_recorded_stale_copy_then_moved_aside(data, tmp_path):
    root = _project_with_old_tool(tmp_path)
    _legacy(data, root, "com.example.proja", hashed=True)
    old = _stale_copy(data, root, "com.example.proja")
    bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    assert old.exists()  # the new file now sits there
    backups = list((data / "Extensions" / ".instamix" / "backup" / "com.example.proja").rglob("Old Tool.py"))
    assert [b.read_text() for b in backups] == ["print('old version')\n"]
    assert backups[0].as_posix().endswith("/Scripts/Old Tool.py")
    log = legacy.log_path(data, "com.example.proja").read_text().splitlines()
    assert json.loads(log[-1])["moved"]


def test_install_project_when_already_migrated_then_stale_copy_moved_aside(data, tmp_path):
    root = _project_with_old_tool(tmp_path)
    _legacy(data, root, "com.example.proja", hashed=True)
    old = _stale_copy(data, root, "com.example.proja")
    log = legacy.log_path(data, "com.example.proja")
    with log.open("a") as stream:
        stream.write(json.dumps({"action": "uninstall", "id": "com.example.proja", "migrated_to": "fontlab-instamix"}) + "\n")
    assert legacy.installed(data, "com.example.proja") is None
    bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    assert old.read_text() == "print('new')\n"
    assert list((data / "Extensions" / ".instamix" / "backup").rglob("Old Tool.py"))


def test_install_project_when_unrecorded_collision_then_refused(data, tmp_path):
    root = _project_with_old_tool(tmp_path)
    _legacy(data, root, "com.example.proja", hashed=True)
    (data / "Scripts" / "Old Tool.py").write_text("mine\n")
    with pytest.raises(Exception, match="refusing to overwrite"):
        bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    assert (data / "Scripts" / "Old Tool.py").read_text() == "mine\n"


def test_legacy_restore_when_moved_then_files_back(data):
    state = {"files": ["Scripts/a.py"]}
    (data / "Scripts").mkdir(parents=True)
    (data / "Scripts" / "a.py").write_text("x")
    moved = legacy.move_aside(data, "com.example.x", state, {"Scripts/a.py"})
    assert not (data / "Scripts" / "a.py").exists()
    legacy.restore(moved)
    assert (data / "Scripts" / "a.py").read_text() == "x"


def _migrated_state(data, root):
    _legacy(data, root, "com.example.proja", hashed=True)
    old = _stale_copy(data, root, "com.example.proja")
    log = legacy.log_path(data, "com.example.proja")
    with log.open("a") as stream:
        stream.write(json.dumps({"action": "uninstall", "id": "com.example.proja", "migrated_to": "fontlab-instamix"}) + "\n")
    return old


def test_install_project_when_rerun_from_migrated_state_then_one_backup_only(data, tmp_path):
    root = _project_with_old_tool(tmp_path)
    old = _migrated_state(data, root)
    backups = data / "Extensions" / ".instamix" / "backup"
    for _ in range(3):
        bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
        assert old.read_text() == "print('new')\n"
    found = list(backups.rglob("Old Tool.py"))
    assert [b.read_text() for b in found] == ["print('old version')\n"]


def test_move_aside_when_same_second_then_backups_not_overwritten(data):
    (data / "Scripts").mkdir(parents=True)
    state = {"files": ["Scripts/a.py"]}
    for text in ("one", "two"):
        (data / "Scripts" / "a.py").write_text(text)
        legacy.move_aside(data, "com.example.x", state, {"Scripts/a.py"})
    found = sorted(b.read_text() for b in (data / "Extensions").rglob("a.py"))
    assert found == ["one", "two"]


def test_install_project_when_install_fails_after_move_then_files_restored(data, tmp_path, monkeypatch):
    root = _project_with_old_tool(tmp_path)
    old = _migrated_state(data, root)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(extension, "install_folder", boom)
    with pytest.raises(bootstrap.BootstrapError, match="put back"):
        bootstrap.install_project(root / "install.vfpy", data, requirements=NO_REQS)
    assert old.read_text() == "print('old version')\n"
    last = json.loads(legacy.log_path(data, "com.example.proja").read_text().splitlines()[-1])
    assert last["action"] == "restored"
