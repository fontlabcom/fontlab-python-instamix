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
