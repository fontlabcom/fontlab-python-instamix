# this_file: tests/test_issue271.py
"""Owned filesystem cases for conflict reporting and local bootstrap wheels."""
import io
import json
import shutil
import zipfile
from pathlib import Path

import pytest
from test_parity import _project
from test_plugin_migration import setup_upgrade
from test_standalone_pack import namespace, wheel
from test_validation_before_writes import snapshot

from fontlab_instamix import bootstrap, cli, extension, ledger


def package_extension(root):
    folder = root / 'com.example.conflict.fontlabext'
    package = folder / 'fontlabapp'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('VALUE = 1\n')
    (folder / 'manifest.fontlabextj').write_text(json.dumps({
        'id': 'com.example.conflict', 'name': 'Conflict', 'version': '1.0.0',
        'python': {'packages': ['fontlabapp']},
    }))
    return folder


def test_install_when_recorded_link_is_directory_then_explains_and_preserves(tmp_path):
    folder, data = package_extension(tmp_path), tmp_path / 'data'
    extension.install_folder(folder, data, copy=False)
    target = data / 'python/3.11/site-packages/fontlabapp'
    target.unlink()
    shutil.copytree(folder / 'fontlabapp', target)
    (target / 'owner.txt').write_text('owner')
    before = snapshot(data)
    with pytest.raises(extension.InstallError, match='recorded link.*directory') as caught:
        extension.install_folder(folder, data, copy=False)
    assert 'move' in str(caught.value).lower()
    assert snapshot(data) == before


@pytest.mark.parametrize('change', ['edited', 'extra', 'directory'])
def test_install_when_copied_package_has_owner_content_then_no_writes(tmp_path, change):
    folder, data = package_extension(tmp_path), tmp_path / 'data'
    extension.install_folder(folder, data, copy=True)
    target = data / 'python/3.11/site-packages/fontlabapp'
    if change == 'edited':
        (target / '__init__.py').write_text('owner')
    elif change == 'extra':
        (target / 'owner.txt').write_text('owner')
    else:
        (target / 'owner').mkdir()
    before = snapshot(data)
    with pytest.raises(extension.InstallError, match='conflict'):
        extension.install_folder(folder, data, copy=True)
    assert snapshot(data) == before


def test_bootstrap_when_parent_conflicts_then_dependencies_not_installed(tmp_path):
    _project(tmp_path / 'dependency', name='dependency', ext_id='com.example.dependency')
    parent = _project(tmp_path / 'parent', name='parent', ext_id='com.example.parent')
    data = tmp_path / 'data'
    bootstrap.install_project(parent, data, requirements=lambda *args: None)
    target = data / 'python/3.11/site-packages/parent'
    target.unlink()
    target.mkdir()
    (target / 'owner').write_text('owner')
    (parent / 'pyproject.toml').write_text((parent / 'pyproject.toml').read_text().replace('[project]', '[project]\ndependencies = ["dependency"]'))
    before = snapshot(data)
    with pytest.raises(extension.InstallError):
        bootstrap.install_project(parent, data, requirements=lambda *args: None)
    assert snapshot(data) == before
    assert ledger.read(data, 'com.example.dependency') is None


def test_bootstrap_when_later_dependency_fails_then_retains_success_records(tmp_path, monkeypatch):
    first = _project(tmp_path / 'first', name='first', ext_id='com.example.first')
    second = _project(tmp_path / 'second', name='second', ext_id='com.example.second')
    parent = _project(tmp_path / 'parent', name='parent', ext_id='com.example.parent')
    original = bootstrap.sibling_dependencies
    monkeypatch.setattr(bootstrap, 'sibling_dependencies', lambda project: ([first, second], []) if project.root == parent else original(project))
    original_install = bootstrap._install_checkout
    def install(project, *args):
        if project.root == second:
            raise extension.InstallError('blocked fixture')
        return original_install(project, *args)
    monkeypatch.setattr(bootstrap, '_install_checkout', install)
    with pytest.raises(extension.InstallError) as caught:
        bootstrap.install_project(parent, tmp_path / 'data', requirements=lambda *args: None)
    assert [r['id'] for r in caught.value.installed_records] == ['com.example.first']


def test_cli_when_partial_install_then_reports_success_and_exits_nonzero(monkeypatch, capsys):
    error = extension.InstallError('blocked fixture')
    error.installed_records = [{'id': 'com.example.first', 'version': '1'}]
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(bootstrap, 'install_project', fail)
    assert cli.main(['bootstrap', '.']) == 1
    captured = capsys.readouterr()
    assert 'installed com.example.first 1' in captured.out
    assert 'blocked fixture' in captured.err


def write_wheel(root, version, content=None):
    target = root / 'dist' / f'fontlab_python_instamix-{version}-py3-none-any.whl'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(wheel() if content is None else content)
    return target


def test_download_when_self_dist_is_searched_twice_then_installs_one_wheel(tmp_path, monkeypatch):
    root = tmp_path / 'fontlab-python-instamix'
    root.mkdir()
    ns = namespace(root, monkeypatch)
    write_wheel(root, '1.2.3')
    ns['download'](root / 'stage')
    assert (root / 'stage/fontlab_instamix/__init__.py').is_file()


def test_download_when_multiple_versions_then_selects_numeric_newest(tmp_path, monkeypatch):
    ns = namespace(tmp_path, monkeypatch)
    write_wheel(tmp_path, '1.0.9', b'old wheel must not be opened')
    write_wheel(tmp_path, '1.2.3')
    ns['download'](tmp_path / 'stage')
    assert (tmp_path / 'stage/fontlab_instamix/__init__.py').is_file()


def test_download_when_same_version_conflicts_then_refuses_before_extraction(tmp_path, monkeypatch):
    project = tmp_path / 'project'
    project.mkdir()
    ns = namespace(project, monkeypatch)
    write_wheel(project, '1.2.3')
    write_wheel(tmp_path / 'fontlab-python-instamix', '1.2.3', b'different bytes')
    with pytest.raises(RuntimeError, match='conflicting.*1.2.3'):
        ns['download'](project / 'stage')
    assert not (project / 'stage').exists()


def test_download_when_filename_metadata_disagree_then_refuses(tmp_path, monkeypatch):
    ns = namespace(tmp_path, monkeypatch)
    write_wheel(tmp_path, '9.0.0')
    with pytest.raises(RuntimeError, match='version.*metadata'):
        ns['download'](tmp_path / 'stage')


def test_download_when_only_old_wheels_then_refuses_without_network(tmp_path, monkeypatch):
    ns = namespace(tmp_path, monkeypatch)
    write_wheel(tmp_path, '1.0.9')
    with pytest.raises(RuntimeError, match='minimum'):
        ns['download'](tmp_path / 'stage')


@pytest.mark.parametrize("installer", ["install.vfpy", "stub/install.vfpy", "src/fontlab_instamix/stub_install.vfpy"])
@pytest.mark.parametrize("older,newer", [
    ("1.0.9", "1.0.17"), ("1.0.17.dev1", "1.0.17.dev2"),
    ("1.0.17.dev2", "1.0.17a1"), ("1.0.17a2", "1.0.17b1"),
    ("1.0.17b2", "1.0.17rc1"), ("1.0.17rc2", "1.0.17"),
    ("1.0.17", "1.0.17.post1"), ("1.0.17", "1.0.17+g123"),
    ("1.0.17+build.2", "1.0.17+build.10"),
])
def test_local_wheel_versions_when_supported_then_numeric_order(tmp_path, monkeypatch, installer, older, newer):
    source = Path(__file__).resolve().parents[1] / installer
    ns = {"__name__": "install_vfpy_import", "__file__": str(tmp_path / "install.vfpy")}
    exec(compile(source.read_text(), installer, "exec"), ns)  # noqa: S102 - owned installer import sentinel
    assert ns["wheel_version"](older) < ns["wheel_version"](newer)


def test_download_when_same_major_minor_then_newest_metadata_installed(tmp_path, monkeypatch):
    ns = namespace(tmp_path, monkeypatch)
    original = io.BytesIO(wheel())
    output = io.BytesIO()
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(output, "w") as target:
        for name in source.namelist():
            target.writestr(name.replace("1.2.3", "1.0.17"), source.read(name).replace(b"1.2.3", b"1.0.17"))
    write_wheel(tmp_path, "1.0.9", b"old")
    write_wheel(tmp_path, "1.0.17", output.getvalue())
    ns["download"](tmp_path / "stage")
    assert (tmp_path / "stage/fontlab_python_instamix-1.0.17.dist-info/METADATA").is_file()


def test_requirements_when_failure_has_committed_records_then_preserves_both(tmp_path):
    folder, data = package_extension(tmp_path), tmp_path / 'data'
    manifest = folder / 'manifest.fontlabextj'
    info = json.loads(manifest.read_text())
    info['python']['requires'] = ['owned-fixture']
    manifest.write_text(json.dumps(info))
    error = RuntimeError('requirements fixture failed')
    error.installed_records = [{'id': 'com.example.dependency', 'version': '1'}]
    def fail(*args):
        raise error
    with pytest.raises(RuntimeError) as caught:
        extension.install_folder(folder, data, requirements=fail)
    assert [r['id'] for r in caught.value.installed_records] == ['com.example.dependency', 'com.example.conflict']
    assert caught.value.installed_records[-1]['requires_failed'] is True
    assert ledger.read(data, 'com.example.conflict')['requires_failed'] is True


@pytest.mark.parametrize('installer', ['install.vfpy', 'stub/install.vfpy', 'src/fontlab_instamix/stub_install.vfpy'])
def test_standalone_when_provider_lacks_conflict_preflight_then_replacement_required(tmp_path, monkeypatch, installer):
    from types import SimpleNamespace
    source = Path(__file__).resolve().parents[1] / installer
    ns = {'__name__': 'install_vfpy_import', '__file__': str(tmp_path / 'install.vfpy')}
    exec(compile(source.read_text(), installer, 'exec'), ns)  # noqa: S102 - owned installer import sentinel
    def imported(name):
        if name.endswith('.extension'):
            return SimpleNamespace(preflight_plugin_migration=lambda *args: None)
        return SimpleNamespace()
    ns['importlib'] = SimpleNamespace(import_module=imported)
    with pytest.raises(ImportError, match='preflight_destinations'):
        ns['required_api']()


def test_cli_when_requirements_failed_then_reports_incomplete(monkeypatch, capsys):
    error = extension.InstallError('blocked fixture')
    error.installed_records = [{'id': 'com.example.first', 'version': '1', 'requires_failed': True}]
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(bootstrap, 'install_project', fail)
    assert cli.main(['bootstrap', '.']) == 1
    assert 'incomplete requirements for com.example.first 1' in capsys.readouterr().out


def test_install_when_case_alias_has_owned_dangling_links_then_replaces(tmp_path):
    new, data, old = setup_upgrade(tmp_path, "unchanged", copy=False)
    for path in (tmp_path / "old/com.example.demo.fontlabext/Extensions/reporters/Demo.fontlabReporter").iterdir():
        path.unlink()
    assert (old / "plugin.py").is_symlink() and not (old / "plugin.py").exists()
    extension.install_folder(new, data, copy=False, editable=True)
    canonical = old.with_name("Demo.fontlabreporter")
    assert (canonical / "plugin.py").is_file()
    assert extension.uninstall("com.example.demo", data) == []


def test_bootstrap_when_postcommit_launcher_fails_then_reports_committed_package(tmp_path, monkeypatch):
    parent = _project(tmp_path / "parent", name="parent", ext_id="com.example.parent")
    data = tmp_path / "data"
    bootstrap.install_project(parent, data, requirements=lambda *args: None)
    error = RuntimeError("launcher fixture")
    error.installed_records = [{"id": "com.example.external", "version": "1"}]
    def fail(*args):
        raise error
    monkeypatch.setattr(bootstrap.launchers, "write_list", fail)
    with pytest.raises(RuntimeError) as caught:
        bootstrap.install_project(parent, data, requirements=lambda *args: None)
    assert [record["id"] for record in caught.value.installed_records] == ["com.example.external", "com.example.parent"]
    assert ledger.read(data, "com.example.parent") is not None
