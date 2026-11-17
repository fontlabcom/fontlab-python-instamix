# this_file: tests/test_plugin_migration.py
"""Case-only bundle upgrades preserve owner files and managed receipts."""
import json
import shutil

import pytest

from fontlab_instamix import bootstrap, cli, extension, gui, ledger, wrap
from test_upgrade_rollback import snapshot


def bundle(root, suffix="Reporter"):
    folder = root / "com.example.demo.fontlabext"
    files = folder / f"Extensions/reporters/Demo.fontlab{suffix}"
    files.mkdir(parents=True)
    (files / "plugin.json").write_text('{"id":"demo"}')
    (files / "plugin.py").write_text("# owned plugin\n")
    (folder / "manifest.fontlabextj").write_text(json.dumps({
        "id": "com.example.demo", "name": "Demo", "version": "1.0",
        "install": [{"from": "Extensions/reporters", "to": "Extensions/reporters"}],
    }))
    return folder


def setup_upgrade(tmp_path, state, copy=True):
    old = bundle(tmp_path / "old")
    new = bundle(tmp_path / "new", "reporter")
    data = tmp_path / "data"
    if state == "unowned":
        shutil.copytree(old / "Extensions", data / "Extensions")
    else:
        extension.install_folder(old, data, copy=copy, editable=not copy)
    legacy = data / "Extensions/reporters/Demo.fontlabReporter"
    if state in ("plugin.json", "plugin.py"):
        path = legacy / state
        path.unlink()
        path.write_text("owner edit")
    elif state == "extra":
        (legacy / "extra").mkdir()
        (legacy / "extra/owned.txt").write_text("owner extra")
    elif state == "unknown":
        record = ledger.read(data, "com.example.demo")
        record["entries"] = []
        ledger.write(data, record)
    return new, data, legacy


@pytest.mark.parametrize("state", ["plugin.json", "plugin.py", "extra", "unowned", "unknown"])
@pytest.mark.parametrize("route", ["api", "cli", "gui", "bootstrap"])
def test_retained_legacy_bundle_refuses_before_mutation(tmp_path, monkeypatch, capsys, state, route):
    new, data, old = setup_upgrade(tmp_path, state)
    before = snapshot(data)
    canonical = old.with_name("Demo.fontlabreporter")
    if canonical.exists() and old.samefile(canonical):
        info = extension.manifest.load(new)
        extension.preflight_plugin_migration(data, extension.plan(new, info, info.id, data), ledger.read(data, info.id))
        assert snapshot(data) == before
        return
    monkeypatch.setenv("FONTLAB_DATA_DIR", str(data))
    if route == "gui":
        assert gui.install_selected([new], data=data) == []
        assert "error:" in capsys.readouterr().out
    elif route == "cli":
        assert cli.main(["--data-dir", str(data), "ext", "install", str(new)]) == 1
    elif route == "bootstrap":
        (new / "pyproject.toml").write_text('[project]\nname="demo"\nversion="2.0"\n[tool.fontlab-install]\nid="com.example.demo"\npackages=[]\nextensions="Extensions"\ndependencies=[]\n')
        with pytest.raises(extension.InstallError):
            bootstrap.install_project(new, data)
    else:
        with pytest.raises(extension.InstallError):
            extension.install(new, data)
    assert snapshot(data) == before
    assert old.is_dir()


@pytest.mark.parametrize("copy", [True, False])
def test_unchanged_owned_migration_and_uninstall(tmp_path, copy):
    new, data, old = setup_upgrade(tmp_path, "unchanged", copy)
    extension.install_folder(new, data, copy=copy, editable=not copy)
    canonical = old.with_name("Demo.fontlabreporter")
    assert [p.name for p in old.parent.iterdir()] == [canonical.name]
    assert extension.uninstall("com.example.demo", data) == []
    assert not canonical.exists()


def test_archive_refusal_preserves_partial_records_and_original_type(tmp_path):
    new, data, _ = setup_upgrade(tmp_path, "plugin.py")
    first = bundle(tmp_path / "first", "reporter")
    first.rename(first.with_name("com.example.aaa.fontlabext"))
    first = first.with_name("com.example.aaa.fontlabext")
    manifest = first / "manifest.fontlabextj"
    manifest.write_text(manifest.read_text().replace("com.example.demo", "com.example.aaa").replace("Extensions/reporters", "Scripts/First"))
    # Give the first archive member its own source and target.
    (first / "Scripts/First").mkdir(parents=True)
    (first / "Scripts/First/run.py").write_text("pass")
    archive = wrap.make_zip([first, new], tmp_path / "plugins.fontlabextz")
    receipt = ledger.record_path(data, "com.example.demo").read_bytes()
    with pytest.raises(extension.InstallError) as caught:
        extension.install(archive, data)
    assert [r["id"] for r in caught.value.installed_records] == ["com.example.aaa"]
    assert ledger.record_path(data, "com.example.demo").read_bytes() == receipt


def test_actual_filesystem_alias_is_not_a_distinct_legacy_bundle(tmp_path):
    new, data, old = setup_upgrade(tmp_path, "unchanged")
    canonical = old.with_name("Demo.fontlabreporter")
    # The test exercises the filesystem we actually run on, without mocked exists.
    alias = canonical.exists() and old.samefile(canonical)
    if alias:
        assert old.stat().st_ino == canonical.stat().st_ino
    extension.install_folder(new, data, copy=True)
    assert canonical.is_dir()
    assert [p.name for p in old.parent.iterdir()] == [canonical.name]
    assert old.exists() == alias


@pytest.mark.parametrize("kind,title", [("reporters", "Reporter"), ("filters", "Filter"), ("tools", "Tool"), ("palettes", "Palette"), ("general", "General")])
def test_each_kind_preflight_preserves_distinct_unowned_counterpart(tmp_path, kind, title):
    data = tmp_path / "data"
    old = data / "Extensions" / kind / ("Demo.fontlab" + title)
    old.mkdir(parents=True)
    (old / "owner.py").write_text("owner")
    canonical = old.with_name("Demo.fontlab" + title.lower())
    pairs = [(tmp_path / "source", canonical / "plugin.py")]
    before = snapshot(data)
    if canonical.exists() and old.samefile(canonical):
        extension.preflight_plugin_migration(data, pairs, None)
    else:
        with pytest.raises(extension.InstallError, match="legacy plugin bundle would be retained"):
            extension.preflight_plugin_migration(data, pairs, None)
    assert snapshot(data) == before


def test_project_refusal_precedes_dependency_and_legacy_mutations(tmp_path, monkeypatch):
    new, data, old = setup_upgrade(tmp_path, "plugin.py")
    canonical = old.with_name("Demo.fontlabreporter")
    if canonical.exists() and old.samefile(canonical):
        # Alias behavior is covered above; this invariant concerns distinct roots.
        extension.preflight_plugin_migration(data, [(new, canonical / "plugin.py")], ledger.read(data, "com.example.demo"))
        return
    (new / "pyproject.toml").write_text('[project]\nname="demo"\nversion="2.0"\n[tool.fontlab-install]\nid="com.example.demo"\npackages=[]\nextensions="Extensions"\ndependencies=[]\n')
    def forbidden(*args):
        pytest.fail("dependency or legacy mutation reached before preflight refusal")
    monkeypatch.setattr(bootstrap, "sibling_dependencies", forbidden)
    monkeypatch.setattr(bootstrap, "migrate_legacy", forbidden)
    before = snapshot(data)
    with pytest.raises(extension.InstallError, match="legacy plugin bundle would be retained"):
        bootstrap.install_project(new, data)
    assert snapshot(data) == before
