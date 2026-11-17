# this_file: tests/test_destination_containment.py
import json
import os

import pytest

from fontlab_instamix import env, extension, ledger


def snapshot(root):
    return {str(p.relative_to(root)): ('link', os.readlink(p)) if p.is_symlink()
            else ('dir',) if p.is_dir() else ('file', p.read_bytes())
            for p in root.rglob('*')}


@pytest.mark.parametrize('relative', ['Scripts/com.example.hello', 'python',
    'Extensions/Library', 'Extensions/.instamix',
    'Extensions/.instamix/install.log', 'Extensions/.instamix/com.example.hello.tmp',
    'Extensions/.instamix/com.example.hello.json'])
def test_install_when_destination_link_escapes_then_no_writes(data, example, tmp_path, relative):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'sentinel').write_text('untouched')
    link = data / relative
    link.parent.mkdir(parents=True, exist_ok=True)
    target = outside
    if link.suffix in ('.log', '.tmp', '.json'):
        target = outside / 'sentinel'
    link.symlink_to(target, target_is_directory=target.is_dir())
    before, external = snapshot(data), snapshot(outside)
    with pytest.raises((ValueError, extension.InstallError)):
        extension.install(example, data)
    assert snapshot(data) == before
    assert snapshot(outside) == external


@pytest.mark.parametrize('leaf', ['install.log', 'com.example.hello.tmp'])
def test_upgrade_when_ledger_leaf_is_link_then_old_install_unchanged(data, example, tmp_path, leaf):
    extension.install(example, data)
    outside = tmp_path / 'outside'
    outside.write_text('sentinel')
    link = ledger.ledger_dir(data) / leaf
    if link.exists():
        link.unlink()
    link.symlink_to(outside)
    before = snapshot(data)
    with pytest.raises((ValueError, extension.InstallError)):
        extension.install(example, data)
    assert snapshot(data) == before
    assert outside.read_text() == 'sentinel'


@pytest.mark.parametrize('copy', [False, True])
def test_install_when_data_and_internal_directory_are_links_then_supported(data, example, tmp_path, copy):
    alias = tmp_path / 'alias'
    alias.symlink_to(data, target_is_directory=True)
    (data / 'actual-scripts').mkdir()
    (data / 'Scripts').symlink_to(data / 'actual-scripts', target_is_directory=True)
    extension.install(example, alias, copy=copy)
    extension.install(example, alias, copy=copy)
    assert (alias / 'Scripts/com.example.hello/Hello.py').is_file()
    extension.uninstall('com.example.hello', alias)


@pytest.mark.parametrize('kind', ['package', 'rule'])
@pytest.mark.parametrize('bad', ['/absolute', 'C:/absolute', '../outside', r'..\outside'])
def test_install_when_source_not_relative_then_refused_before_writes(data, example, kind, bad):
    path = example / 'manifest.fontlabextj'
    info = json.loads(path.read_text())
    if kind == 'package':
        info['python'] = {'packages': [bad]}
    else:
        info['install'][0]['from'] = bad
    path.write_text(json.dumps(info))
    before = snapshot(data)
    with pytest.raises((ValueError, extension.InstallError)):
        extension.install(example, data)
    assert snapshot(data) == before


def test_plan_when_absolute_package_exists_then_refused(data, example, tmp_path):
    package = tmp_path / 'package'
    package.mkdir()
    path = example / 'manifest.fontlabextj'
    info = json.loads(path.read_text())
    info['python'] = {'packages': [str(package)]}
    path.write_text(json.dumps(info))
    with pytest.raises((ValueError, extension.InstallError)):
        extension.install(example, data)
    assert not (data / 'Extensions').exists()


def test_placement_when_parent_link_escapes_then_refused(data, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (data / 'Scripts').symlink_to(outside, target_is_directory=True)
    source = tmp_path / 'source.py'
    source.write_text('source')
    with pytest.raises((ValueError, extension.InstallError)):
        extension.Placement(data, True).place(source, data / 'Scripts/nested/file.py')
    assert list(outside.iterdir()) == []


def test_ensure_folders_when_python_escapes_then_no_other_folders_created(data, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (data / 'python').symlink_to(outside, target_is_directory=True)
    before = snapshot(data)
    with pytest.raises(ValueError):
        env.ensure_folders(data)
    assert snapshot(data) == before
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize('leaf', ['install.log', 'com.example.hello.tmp', 'com.example.hello.json'])
def test_ledger_write_when_leaf_is_link_then_external_file_unchanged(data, tmp_path, leaf):
    outside = tmp_path / 'outside'
    outside.write_text('untouched')
    folder = ledger.ledger_dir(data)
    folder.mkdir(parents=True)
    (folder / leaf).symlink_to(outside)
    before = snapshot(data)
    with pytest.raises(ValueError):
        ledger.write(data, {'id': 'com.example.hello', 'version': '1'})
    assert snapshot(data) == before
    assert outside.read_text() == 'untouched'


@pytest.mark.parametrize('suffix', ['', '.new', '.old', '.prev'])
def test_install_when_library_staging_leaf_is_link_then_no_mutation(data, example, tmp_path, suffix):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'sentinel').write_text('untouched')
    path = extension.library_path(data, 'com.example.hello')
    path.parent.mkdir(parents=True)
    path.with_name(path.name + suffix).symlink_to(outside, target_is_directory=True)
    before, external = snapshot(data), snapshot(outside)
    with pytest.raises(extension.InstallError):
        extension.install(example, data)
    assert snapshot(data) == before
    assert snapshot(outside) == external


@pytest.mark.parametrize('copy', [False, True])
def test_editable_package_when_source_and_final_links_exist_then_upgrade_supported(data, example, tmp_path, copy):
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    (checkout / '__init__.py').write_text('VALUE = 1')
    (example / 'mypkg').symlink_to(checkout, target_is_directory=True)
    path = example / 'manifest.fontlabextj'
    info = json.loads(path.read_text())
    info['python'] = {'packages': ['mypkg']}
    path.write_text(json.dumps(info))
    extension.install_folder(example, data, editable=True, copy=copy)
    package = env.site_packages(data) / 'mypkg'
    assert package.is_symlink() is (not copy)
    extension.install_folder(example, data, editable=True, copy=copy)
    assert (package / '__init__.py').read_text() == 'VALUE = 1'
    extension.uninstall(info['id'], data)
    assert (checkout / '__init__.py').read_text() == 'VALUE = 1'


@pytest.mark.parametrize('copy', [False, True])
def test_upgrade_when_later_placement_fails_then_old_files_restored(data, example, monkeypatch, copy):
    extension.install(example, data, copy=copy)
    before = snapshot(data)
    original = extension.Placement.place
    calls = []

    def fail_later(self, source, target):
        calls.append(target)
        if len(calls) == 2:
            raise RuntimeError('placement failure')
        return original(self, source, target)

    monkeypatch.setattr(extension.Placement, 'place', fail_later)
    with pytest.raises(RuntimeError, match='placement failure'):
        extension.install(example, data, copy=copy)
    assert snapshot(data) == before


def test_install_when_absolute_rule_would_match_after_stripping_then_refused(data, example):
    path = example / 'manifest.fontlabextj'
    info = json.loads(path.read_text())
    info['install'][0]['from'] = '/scripts'
    path.write_text(json.dumps(info))
    with pytest.raises(extension.InstallError):
        extension.install(example, data)
    assert not (data / 'Extensions').exists()


@pytest.mark.parametrize('leaf', ['install.log', 'com.example.hello.tmp'])
def test_uninstall_when_ledger_leaf_is_link_then_install_preserved(data, example, tmp_path, leaf):
    extension.install(example, data)
    outside = tmp_path / 'outside'
    outside.write_text('sentinel')
    link = ledger.ledger_dir(data) / leaf
    if link.exists():
        link.unlink()
    link.symlink_to(outside)
    before = snapshot(data)
    with pytest.raises((extension.InstallError, ledger.LedgerError)):
        extension.uninstall('com.example.hello', data)
    assert snapshot(data) == before
    assert outside.read_text() == 'sentinel'
