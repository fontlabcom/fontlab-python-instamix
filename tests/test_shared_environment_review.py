# this_file: tests/test_shared_environment_review.py
import hashlib
import io
import json
import sys
import tarfile
import types
from functools import cache

import pytest

from fontlab_instamix import dest, env, extension, packages, uv


@cache
def archive_bytes():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        member = tarfile.TarInfo('uv/uv')
        payload = b'#!/bin/sh\n'
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    return buffer.getvalue()


def archive_fetch(url):
    content = archive_bytes()
    return hashlib.sha256(content).hexdigest().encode() if url.endswith('.sha256') else content


def snapshot(root):
    return {str(p.relative_to(root)): (('link', str(p.readlink())) if p.is_symlink()
            else ('dir',) if p.is_dir() else ('file', p.read_bytes())) for p in root.rglob('*')}


@pytest.mark.parametrize('escape', ['python', 'uv', 'uv.tmp'])
def test_download_refuses_escaping_parent_or_temp_without_mutation(data, tmp_path, escape):
    outside = tmp_path / 'outside'
    outside.mkdir()
    sentinel = outside / 'sentinel'
    sentinel.write_bytes(b'unchanged')
    leaf = data / 'python' if escape == 'python' else data / 'python/uv'
    if escape == 'uv.tmp':
        leaf = leaf / 'uv.tmp'
    leaf.parent.mkdir(parents=True, exist_ok=True)
    leaf.symlink_to(sentinel if escape == 'uv.tmp' else outside)
    before = snapshot(tmp_path)
    with pytest.raises((ValueError, uv.UvError)):
        uv.download(data, fetch=archive_fetch)
    assert snapshot(tmp_path) == before


def test_download_supports_symlinked_data_root(data, tmp_path):
    alias = tmp_path / 'alias'
    alias.symlink_to(data, target_is_directory=True)
    binary = uv.download(alias, fetch=archive_fetch)
    assert binary.read_bytes() == b'#!/bin/sh\n'
    assert (data / 'python/uv/uv').is_file()


def test_manifest_package_routes_use_live_host_version(data, example, monkeypatch):
    monkeypatch.setitem(sys.modules, 'fontlab', types.SimpleNamespace())
    monkeypatch.setattr(env, 'python_version', lambda: '3.12')
    manifest = example / 'manifest.fontlabextj'
    value = json.loads(manifest.read_text())
    (example / 'rule_module.py').write_text('RULE = 1\n')
    (example / 'linked_module').mkdir()
    (example / 'linked_module/__init__.py').write_text('LINKED = 1\n')
    value['install'] = [{'from': 'rule_module.py', 'to': 'site-packages/.'}]
    value['python'] = {'packages': ['linked_module'], 'requires': ['demo>=1']}
    manifest.write_text(json.dumps(value))
    requirements = []
    def capture_requirements(folder, specs):
        args = packages.install_args(folder, specs)
        requirements.append(args[args.index('--target') + 1])
    extension.install(example, data, requirements=capture_requirements)
    site = env.site_packages(data)
    assert site.parent.name == '3.12'
    assert (site / 'rule_module.py').is_file()
    assert (site / 'linked_module/__init__.py').is_file()
    assert requirements == [str(site)]
    assert not (data / 'python/3.11').exists()


def test_destination_fallback_remains_fontlab9(monkeypatch):
    monkeypatch.delitem(sys.modules, 'fontlab', raising=False)
    assert dest.resolve('site-packages/.', 'demo') == 'python/3.11/site-packages'


@pytest.fixture
def shared_runtime(data):
    import subprocess

    from fontlab_instamix import venv

    site = env.site_packages(data)
    site.mkdir(parents=True)
    purelib = venv.path(data) / "lib/python3.11/site-packages"
    purelib.parent.mkdir(parents=True)
    purelib.symlink_to(site, target_is_directory=True)
    facts = {
        "version": "3.11",
        "platform": "darwin",
        "arch": "arm64",
        "prefix": str(venv.path(data)),
        "purelib": str(purelib),
        "implementation": "CPython",
    }

    def runner(argv, **kwargs):
        assert argv[1:4] == ["-I", "-B", "-c"]
        assert kwargs["timeout"] == 30
        return subprocess.CompletedProcess(argv, 0, json.dumps(facts), "")

    return site, purelib, facts, runner


@pytest.mark.parametrize("pth", [None, "managed", "foreign", "link"])
def test_canonical_shared_venv_reused_without_writes(data, shared_runtime, pth):
    from fontlab_instamix import venv

    site, purelib, _facts, runner = shared_runtime
    marker = site / "keep.py"
    marker.write_text("VALUE = 256\n")
    pathfile = site / venv.PTH
    if pth == "managed":
        pathfile.write_text(f"# Managed by fontlab_instamix\n{site.resolve()}\n")
    elif pth == "foreign":
        pathfile.write_text("unrelated\n")
    elif pth == "link":
        pathfile.symlink_to(marker)
    before = snapshot(data)
    target = env.Target("3.11", "darwin", "arm64")
    if pth in ("foreign", "link"):
        with pytest.raises(uv.UvError, match="Unrelated"):
            venv.create(data, data / "uv", runner=runner, target=target)
    else:
        assert venv.probe(venv.path(data), target, runner) == purelib
        assert venv.create(
            data, data / "uv", runner=runner, target=target
        ) == venv.path(data)
    assert snapshot(data) == before


@pytest.mark.parametrize(
    "mismatch",
    [
        "version",
        "platform",
        "arch",
        "prefix",
        "implementation",
        "other-site",
        "other-version",
        "outside-data",
        "canonical-escape",
    ],
)
def test_shared_venv_mismatch_refused_without_writes(
    data, tmp_path, shared_runtime, mismatch
):
    from fontlab_instamix import venv

    site, purelib, facts, runner = shared_runtime
    overrides = {
        "version": "3.12",
        "platform": "linux",
        "arch": "x86_64",
        "prefix": str(data),
        "implementation": "PyPy",
    }
    if mismatch in overrides:
        facts[mismatch] = overrides[mismatch]
    else:
        other = {
            "other-site": data / "other/site-packages",
            "other-version": env.site_packages(data, version="3.12"),
            "outside-data": tmp_path / "outside/site-packages",
            "canonical-escape": tmp_path / "outside/site-packages",
        }[mismatch]
        other.mkdir(parents=True)
        if mismatch == "canonical-escape":
            site.rmdir()
            site.symlink_to(other, target_is_directory=True)
        else:
            purelib.unlink()
            purelib.symlink_to(other, target_is_directory=True)
    before = snapshot(tmp_path)
    with pytest.raises(uv.UvError):
        venv.probe(venv.path(data), env.Target("3.11", "darwin", "arm64"), runner)
    with pytest.raises((ValueError, uv.UvError)):
        venv.create(
            data,
            data / "uv",
            runner=runner,
            target=env.Target("3.11", "darwin", "arm64"),
        )
    assert snapshot(tmp_path) == before
