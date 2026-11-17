# this_file: tests/test_bootstrap_cli.py
import json
import sys

import pytest

from fontlab_instamix import bootstrap, cli, extension, wrap


def _project(root, name, ext_id, deps=()):
    root.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "2.0"\n'
        f'[tool.fontlab-install]\nid = "{ext_id}"\npackages = ["src/{name.replace("-", "_")}"]\n'
        f"dependencies = {json.dumps(list(deps))}\n"
    )
    pkg = root / "src" / name.replace("-", "_")
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (root / "Scripts").mkdir()
    (root / "Scripts" / f"{name}.py").write_text("print(1)\n")
    (root / "install.vfpy").write_text("# installer\n")
    return root


def test_read_project_when_table_then_parsed(tmp_path):
    root = _project(tmp_path / "proj-a", "proj-a", "com.example.proja")
    info = bootstrap.read_project(root / "install.vfpy")
    assert info.id == "com.example.proja"
    assert info.scripts == ("Scripts",)
    assert info.packages == ("src/proj_a",)


def test_read_project_when_no_table_then_error(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n')
    with pytest.raises(bootstrap.BootstrapError):
        bootstrap.read_project(tmp_path)


def test_install_project_when_sibling_dep_then_both_installed(data, tmp_path):
    _project(tmp_path / "proj-b", "proj-b", "com.example.projb")
    root = _project(tmp_path / "proj-a", "proj-a", "com.example.proja", ["proj-b>=1", "fonttools"])
    calls = []
    records = bootstrap.install_project(
        root / "install.vfpy", data, requirements=lambda d, specs: calls.append(list(specs))
    )
    assert [r["id"] for r in records] == ["com.example.projb", "com.example.proja"]
    assert calls == [["fonttools"]]
    site = data / "python" / "3.11" / "site-packages"
    assert (site / "proj_a" / "__init__.py").is_file()
    assert (data / "Scripts" / "proj-a.py").is_file()  # top-level Scripts/ maps onto FontLab Scripts
    if sys.platform != "win32":
        assert (site / "proj_a").resolve() == (root / "src" / "proj_a").resolve()
    extension.uninstall("com.example.proja", data)
    assert not (site / "proj_a").exists()
    assert (root / "src" / "proj_a" / "__init__.py").is_file()


def test_install_project_when_run_twice_then_reinstalls_and_uninstalls(data, tmp_path):
    root = _project(tmp_path / "proj-a", "proj-a", "com.example.proja")
    no_reqs = lambda d, specs: None
    bootstrap.install_project(root / "install.vfpy", data, requirements=no_reqs)
    bootstrap.install_project(root / "install.vfpy", data, requirements=no_reqs)
    site = data / "python" / "3.11" / "site-packages"
    script = data / "Scripts" / "proj-a.py"
    assert script.is_file() and (site / "proj_a").exists()
    assert extension.uninstall("com.example.proja", data) == []
    assert not script.exists() and not script.is_symlink()
    assert not (site / "proj_a").exists() and not (site / "proj_a").is_symlink()
    assert (root / "src" / "proj_a" / "__init__.py").is_file()
    assert (root / "Scripts" / "proj-a.py").is_file()


def test_wrap_when_script_then_installable(data, tmp_path):
    script = tmp_path / "Tool.py"
    script.write_text("print(1)\n")
    folder = wrap.make_folder(script, tmp_path / "out", "com.example.tool")
    zpath = wrap.make_zip([folder], tmp_path / "tool.fontlabextz")
    [record] = extension.install(zpath, data, requirements=lambda d, s: None)
    assert (data / "Scripts" / "com.example.tool" / "Tool.py").is_file()
    assert record["id"] == "com.example.tool"


def test_cli_when_ext_cycle_then_ok(data, example, capsys):
    assert cli.main(["--data-dir", str(data), "ext", "install", str(example)]) == 0
    assert cli.main(["--data-dir", str(data), "ext", "list"]) == 0
    assert "com.example.hello" in capsys.readouterr().out
    assert cli.main(["--data-dir", str(data), "ext", "uninstall", "com.example.hello"]) == 0
    assert cli.main(["--data-dir", str(data), "ext", "uninstall", "com.example.hello"]) == 1


def test_cli_when_env_then_json(data, capsys):
    assert cli.main(["env"]) == 0
    assert json.loads(capsys.readouterr().out)["data_dir"] == str(data)


def test_gui_when_no_pythonqt_then_console(capsys):
    from fontlab_instamix import gui

    gui.message("hi")
    assert "hi" in capsys.readouterr().out


def test_install_project_when_neighbour_has_no_install_table_then_left_to_uv(data, tmp_path):
    other = tmp_path / "typerig"
    other.mkdir()
    (other / "install.vfpy").write_text("")
    (other / "pyproject.toml").write_text('[project]\nname = "typerig"\nversion = "1"\n')
    bad = tmp_path / "broken"
    bad.mkdir()
    (bad / "install.vfpy").write_text("")
    (bad / "pyproject.toml").write_text("not [valid toml")
    root = _project(tmp_path / "proj-a", "proj-a", "com.example.proja", ["typerig>=1", "broken"])
    calls = []
    records = bootstrap.install_project(
        root / "install.vfpy", data, requirements=lambda d, specs: calls.append(list(specs))
    )
    assert [r["id"] for r in records] == ["com.example.proja"]
    assert calls == [["typerig>=1", "broken"]]
    assert sorted(p.name for p in other.iterdir()) == ["install.vfpy", "pyproject.toml"]


def test_sibling_when_folder_name_differs_then_matches_project_name(tmp_path):
    _project(tmp_path / "checkout-x", "Proj_X.lib", "com.example.projx")
    assert bootstrap._sibling(tmp_path, "proj-x-lib", skip=tmp_path / "proj-a") == tmp_path / "checkout-x"


def test_uninstall_when_scripts_subfolders_emptied_then_pruned(data, tmp_path):
    root = _project(tmp_path / "proj-a", "proj-a", "com.example.proja")
    (root / "Scripts" / "Features").mkdir()
    (root / "Scripts" / "Features" / "x.py").write_text("")
    bootstrap.install_project(root / "install.vfpy", data, requirements=lambda d, s: None)
    (data / "Scripts" / "Mine").mkdir()
    assert (data / "Scripts" / "Features").is_dir()
    extension.uninstall("com.example.proja", data)
    assert not (data / "Scripts" / "Features").exists()
    assert (data / "Scripts" / "Mine").is_dir() and (data / "Scripts").is_dir()


def test_uninstall_when_user_folder_preexisted_then_kept(data, tmp_path):
    root = _project(tmp_path / "proj-a", "proj-a", "com.example.proja")
    (root / "Scripts" / "Mine").mkdir()
    (root / "Scripts" / "Mine" / "x.py").write_text("")
    mine = data / "Scripts" / "Mine"
    mine.mkdir(parents=True)  # user's own empty folder, before install
    bootstrap.install_project(root / "install.vfpy", data, requirements=lambda d, s: None)
    assert (mine / "x.py").exists()
    extension.uninstall("com.example.proja", data)
    assert mine.is_dir() and not (mine / "x.py").exists()


def test_sibling_when_tables_malformed_then_skipped(tmp_path):
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "install.vfpy").write_text("")
    (bad / "pyproject.toml").write_text('tool = 1\nproject = "x"\n')
    badid = tmp_path / "badid"
    badid.mkdir()
    (badid / "install.vfpy").write_text("")
    (badid / "pyproject.toml").write_text('[project]\nname = "badid"\n[tool.fontlab-install]\nid = "nodots"\n')
    assert bootstrap._sibling(tmp_path, "bad") is None
    assert bootstrap._sibling(tmp_path, "badid") is None


def test_message_when_pythonqt_present_then_prints_without_dialog(capsys, monkeypatch):
    from fontlab_instamix import gui

    def boom():
        raise AssertionError("message must not touch Qt dialogs")

    monkeypatch.setattr(gui, "_qtgui", boom)
    gui.message("Installed x 1.0", "Instamix")
    gui.message("bad", "Uninstall", error=True)
    out = capsys.readouterr().out
    assert "Instamix: Installed x 1.0" in out
    assert "Uninstall error: bad" in out
