# this_file: tests/test_legacy_rollback.py
"""Failed legacy upgrades preserve the entire old installation and ownership state."""
import json
import shutil
from pathlib import Path

import pytest

from fontlab_instamix import bootstrap, extension, initscript, launchers, ledger, legacy
from test_parity import _legacy, _project
from test_upgrade_rollback import snapshot


@pytest.mark.parametrize('copy', [False, True])
@pytest.mark.parametrize('failure', ['unowned', 'placement', 'ledger', 'requirements', 'requirements_side_effect', 'legacy_log', 'shared_cleanup', 'init_script', 'list_launcher'])
def test_legacy_upgrade_when_failure_then_exact_previous_install(data, tmp_path, monkeypatch, copy, failure):
    root = _project(tmp_path / 'project', extra_toml='dependencies = ["dep"]\ninit-script = true\n')
    log = _legacy(data, root, 'com.example.proja', hashed=True)
    old = legacy.installed(data, 'com.example.proja')
    package = data / 'python/3.11/site-packages/proj_a'
    if copy:
        package.unlink()
        shutil.copytree(root / 'src/proj_a', package)
        (package / legacy.MARKER).write_text(json.dumps({'id': 'com.example.proja'}))
        old['links'] = {}
    retired = data / 'Scripts/Retired/Old.py'
    retired.parent.mkdir()
    retired.write_text('old installed tool\n')
    retired.chmod(0o640)
    retired.parent.chmod(0o700)
    old['files'].append(str(retired))
    old['hashes'][str(retired)] = ledger.sha256(retired)
    compiled = retired.with_suffix('.pyc')
    compiled.write_bytes(b'old cached bytes')
    log.write_text(json.dumps(old) + '\n')
    log.chmod(0o600)
    (data / 'python/3.11/site-packages/proj_a-1.0.dist-info').chmod(0o700)
    (data / 'initScript.py').write_text('# owner startup\n')
    if failure == 'unowned':
        (root / 'Scripts/Owner.py').write_text('new tool\n')
        (data / 'Scripts/Owner.py').write_text('owner bytes\n')
    before = snapshot(data)

    def fail(*args, **kwargs):
        error = RuntimeError('injected legacy failure')
        if failure.startswith('requirements'):
            error.installed_records = [{'id': 'com.example.dependency'}, {'id': 'com.example.proja'}]
        if failure == 'requirements_side_effect':
            (data / 'Data/dependency.txt').write_text('external dependency bytes')
        raise error

    requirements = fail if failure.startswith('requirements') else lambda *args: None
    if failure == 'placement':
        original = extension.Placement.place
        def place(self, source, target):
            original(self, source, target)
            if target.name == 'METADATA':
                fail()
        monkeypatch.setattr(extension.Placement, 'place', place)
    elif failure == 'legacy_log':
        original = legacy._log
        def log(*args):
            original(*args)
            fail()
        monkeypatch.setattr(legacy, '_log', log)
    elif failure == 'shared_cleanup':
        original = legacy.cleanup_shared
        def cleanup(*args):
            original(*args)
            fail()
        monkeypatch.setattr(legacy, 'cleanup_shared', cleanup)
    elif failure == 'list_launcher':
        original = launchers.write_list
        def write_list(*args):
            original(*args)
            fail()
        monkeypatch.setattr(launchers, 'write_list', write_list)
    elif failure == 'ledger':
        original = ledger.write
        def write(*args):
            original(*args)
            fail()
        monkeypatch.setattr(ledger, 'write', write)
    elif failure == 'init_script':
        original = initscript.update
        def update(*args, **kwargs):
            original(*args, **kwargs)
            fail()
        monkeypatch.setattr(initscript, 'update', update)

    with pytest.raises(RuntimeError, match='refusing to overwrite|injected legacy failure') as error:
        bootstrap.install_project(root, data, copy=copy, requirements=requirements)
    if failure.startswith('requirements'):
        assert error.value.installed_records == [{'id': 'com.example.dependency'}]
    after = snapshot(data)
    if failure == 'requirements_side_effect':
        assert (data / 'Data/dependency.txt').read_text() == 'external dependency bytes'
        after = {key: value for key, value in after.items() if key not in {'Data', 'Data/dependency.txt'}}
    assert after == before
    assert legacy.installed(data, 'com.example.proja') == old
    assert ledger.read(data, 'com.example.proja') is None


def test_legacy_upgrade_when_restore_fails_then_recovery_bytes_retained(data, tmp_path, monkeypatch):
    root = _project(tmp_path / 'project', extra_toml='dependencies = ["dep"]\n')
    _legacy(data, root, 'com.example.proja', hashed=True)
    old_script = (data / 'Scripts/Tool.py').read_bytes()
    info = data / 'python/3.11/site-packages/proj_a-1.0.dist-info'
    old_metadata = (info / 'METADATA').read_bytes()
    original = shutil.copy2
    def copy(source, target, **kwargs):
        if 'instamix-legacy-rollback-' in str(source):
            raise OSError('injected restore failure')
        return original(source, target, **kwargs)
    monkeypatch.setattr(shutil, 'copy2', copy)
    def fail(*args):
        raise RuntimeError('injected install failure')
    with pytest.raises(OSError, match='injected restore failure') as error:
        bootstrap.install_project(root, data, requirements=fail)
    note = next(note for note in error.value.__notes__ if note.startswith('Legacy recovery files retained at '))
    recovery = Path(note.removeprefix('Legacy recovery files retained at '))
    assert recovery.is_dir()
    manifest = json.loads((recovery / 'recovery.json').read_text())
    saved_script = Path(manifest['paths'][str(data / 'Scripts/Tool.py')])
    assert saved_script.read_bytes() == old_script
    info = data / 'python/3.11/site-packages/proj_a-1.0.dist-info'
    assert (Path(manifest['paths'][str(info)]) / 'METADATA').read_bytes() == old_metadata
    assert manifest['directory_modes'][str(data)] == data.stat().st_mode & 0o7777
