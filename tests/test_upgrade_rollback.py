# this_file: tests/test_upgrade_rollback.py
"""Failed upgrades preserve the installed bytes, links and ownership record."""
import os

import pytest

from fontlab_instamix import bootstrap, env, extension, launchers, ledger


def snapshot(root):
    return {
        p.relative_to(root).as_posix():
        ('link', os.readlink(p)) if p.is_symlink() else
        ('dir', p.stat().st_mode) if p.is_dir() else ('file', p.read_bytes(), p.stat().st_mode)
        for p in root.rglob('*')
    }


def project(root):
    (root / 'src/demo').mkdir(parents=True)
    (root / 'src/demo/__init__.py').write_text('VALUE = 1\n')
    (root / 'pyproject.toml').write_text(
        '[project]\nname="demo"\nversion="1.0"\n'
        '[tool.fontlab-install]\nid="com.example.demo"\npackages=["src/demo"]\n'
    )
    return root


@pytest.mark.parametrize('copy', [False, True])
@pytest.mark.parametrize('failure', ['finish', 'placement', 'ledger', 'ledger_temp', 'log'])
def test_upgrade_when_failure_then_exact_old_install(tmp_path, monkeypatch, copy, failure):
    root = project(tmp_path / 'project')
    data = tmp_path / 'data'
    bootstrap.install_project(root, data, copy=copy)
    # Earlier generated entries had no source; copy rollback must use installed bytes.
    record = ledger.read(data, 'com.example.demo')
    for entry in record['entries']:
        if entry['kind'] == 'copy':
            entry.pop('source', None)
    ledger.write(data, record)
    (env.site_packages(data) / 'demo-1.0.dist-info').chmod(0o700)
    if failure in ('ledger', 'log'):
        record_file = ledger.record_path(data, record['id'])
        record_file.chmod(0o600)
        temporary = record_file.with_suffix('.tmp')
        temporary.write_bytes(b'previous temporary bytes')
        temporary.chmod(0o640)
        (ledger.ledger_dir(data) / ledger.LOG).chmod(0o600)
    before = snapshot(data)
    config = root / 'pyproject.toml'
    config.write_text(config.read_text().replace('version="1.0"', 'version="2.0"'))
    if failure == 'finish':
        original = bootstrap._finish
        def fail(*args):
            original(*args)
            raise RuntimeError('injected failure')
        monkeypatch.setattr(bootstrap, '_finish', fail)
    elif failure == 'placement':
        original = extension.Placement.place
        def fail(self, source, target):
            original(self, source, target)
            if target.name == 'METADATA':
                raise RuntimeError('injected failure')
        monkeypatch.setattr(extension.Placement, 'place', fail)
    elif failure == 'ledger_temp':
        def fail(data, record):
            ledger.record_path(data, record['id']).with_suffix('.tmp').write_text('partial')
            raise RuntimeError('injected failure')
        monkeypatch.setattr(ledger, 'write', fail)
    else:
        original = getattr(ledger, 'write' if failure == 'ledger' else 'log')
        def fail(*args):
            original(*args)
            raise RuntimeError('injected failure')
        monkeypatch.setattr(ledger, 'write' if failure == 'ledger' else 'log', fail)
    with pytest.raises(RuntimeError, match='injected failure'):
        bootstrap.install_project(root, data, copy=copy)
    assert snapshot(data) == before
    site = env.site_packages(data)
    assert (site / 'demo-1.0.dist-info/METADATA').is_file()
    assert not (site / 'demo-2.0.dist-info').exists()


@pytest.mark.parametrize('copy', [False, True])
def test_upgrade_when_user_modified_launcher_then_refuses_and_preserves(tmp_path, copy):
    root = project(tmp_path / 'project')
    data = tmp_path / 'data'
    bootstrap.install_project(root, data, copy=copy)
    launchers.uninstaller_path(data, 'com.example.demo').write_text('# user changes\n')
    before = snapshot(data)
    with pytest.raises(extension.InstallError, match='overwrite'):
        bootstrap.install_project(root, data, copy=copy)
    assert snapshot(data) == before


def test_upgrade_when_untracked_stale_metadata_then_preserved(tmp_path):
    root = project(tmp_path / 'project')
    data = tmp_path / 'data'
    bootstrap.install_project(root, data)
    stale = env.site_packages(data) / 'demo-0.5.dist-info'
    stale.mkdir()
    (stale / 'INSTALLER').write_text('fontlab-instamix\n')
    (stale / 'METADATA').write_text('untracked bytes\n')
    before = snapshot(stale)
    bootstrap.install_project(root, data)
    assert snapshot(stale) == before


@pytest.mark.parametrize('copy', [False, True])
def test_upgrade_when_old_directory_survives_then_mode_not_reapplied(tmp_path, monkeypatch, copy):
    root = project(tmp_path / 'project')
    data = tmp_path / 'data'
    bootstrap.install_project(root, data, copy=copy)
    metadata = env.site_packages(data) / 'demo-1.0.dist-info'
    metadata.chmod(0o700)
    (metadata / 'user.txt').write_text('user file keeps directory alive')
    before = snapshot(data)
    config = root / 'pyproject.toml'
    config.write_text(config.read_text().replace('version="1.0"', 'version="2.0"'))
    original_write = ledger.write
    def fail(*args):
        original_write(*args)
        raise RuntimeError('injected failure')
    monkeypatch.setattr(ledger, 'write', fail)
    changed_modes = []
    original_chmod = type(metadata).chmod
    def chmod(path, mode, **kwargs):
        changed_modes.append(path)
        return original_chmod(path, mode, **kwargs)
    monkeypatch.setattr(type(metadata), 'chmod', chmod)
    with pytest.raises(RuntimeError, match='injected failure'):
        bootstrap.install_project(root, data, copy=copy)
    assert snapshot(data) == before
    assert metadata not in changed_modes
