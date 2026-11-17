# this_file: tests/test_shared_environment_real.py
"""Offline integration: requires uv and a preinstalled matching CPython 3.11."""

import json
import subprocess
import zipfile

from fontlab_instamix import env, packages, uv, venv


def test_offline_wheel_imported_by_venv_and_canonical_path(data, tmp_path, monkeypatch):
    target = env.Target("3.11", env.sys.platform, env.machine())
    binary = uv.ensure(data, allow_download=False)
    wheel = tmp_path / "instamix_probe-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("instamix_probe.py", "VALUE = 256\n")
        archive.writestr(
            "instamix_probe-1.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: instamix-probe\nVersion: 1.0\n",
        )
        archive.writestr(
            "instamix_probe-1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr("instamix_probe-1.0.dist-info/RECORD", "")
    calls = []

    def offline(argv, **kwargs):
        if argv[0] == str(binary):
            argv = [argv[0], "--offline", *argv[1:]]
        calls.append(argv)
        return subprocess.run(argv, check=False, **kwargs)

    refreshed = []
    monkeypatch.setattr(
        packages.importlib, "invalidate_caches", lambda: refreshed.append(True)
    )
    packages.install(data, [str(wheel)], uv_bin=binary, runner=offline, target=target)
    assert refreshed == [True]
    executable = venv.python(venv.path(data), target.platform)
    site = env.site_packages(data, version=target.version).resolve()
    # Normal isolated venv startup processes its owned .pth file.
    code = "import instamix_probe as p; import json; print(json.dumps([p.VALUE,p.__file__]))"
    shared = subprocess.run(
        [str(executable), "-I", "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    # -S disables site/.pth: direct canonical path mirrors the host addSysPath route.
    direct = subprocess.run(
        [
            str(executable),
            "-I",
            "-S",
            "-c",
            f"import sys; sys.path.insert(0,{str(site)!r}); {code}",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    expected = [256, str(site / "instamix_probe.py")]
    assert json.loads(shared.stdout) == expected == json.loads(direct.stdout)
    facts = subprocess.run(
        [str(executable), "-I", "-c", venv.PROBE],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    actual = json.loads(facts.stdout)
    assert env.Target(actual["version"], actual["platform"], actual["arch"]) == target
    keep = site / "keep.py"
    keep.write_text("VALUE = 1\n")
    before = len(calls)
    venv.create(data, binary, runner=offline, target=target)
    assert len(calls) == before + 1  # existing environment is probed, never recreated
    assert keep.read_text() == "VALUE = 1\n"
    assert packages.listed(data, target=target) == [("instamix_probe", "1.0")]
    packages.uninstall(data, "instamix-probe", target=target)
    assert not (site / "instamix_probe.py").exists()
    assert keep.is_file()


def test_existing_canonical_site_symlink_reused_without_writes(data):
    import shutil

    from test_shared_environment_review import snapshot

    target = env.Target("3.11", env.sys.platform, env.machine())
    binary = uv.find(data)
    assert binary is not None, "the offline fixture requires installed uv"
    folder = venv.path(data)
    subprocess.run(
        [
            str(binary),
            "--offline",
            "venv",
            "--python",
            venv.request(target),
            str(folder),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    purelib = venv.probe(folder, target)
    site = env.site_packages(data, version=target.version)
    site.parent.mkdir(parents=True)
    shutil.move(str(purelib), site)
    purelib.symlink_to(site, target_is_directory=True)
    (site / "readonly_probe.py").write_text("VALUE = 256\n")
    # Startup imports prove -B also prevents cache writes from existing .pth files.
    (site / "existing.pth").write_text("import readonly_probe\n")
    before = snapshot(data)
    assert venv.create(data, binary, target=target) == folder
    imported = subprocess.run(
        [
            str(venv.python(folder)),
            "-I",
            "-B",
            "-c",
            "import readonly_probe as p; print(p.VALUE)",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert imported.stdout.strip() == "256"
    assert snapshot(data) == before
    assert purelib.is_symlink() and purelib.resolve() == site.resolve()
    assert not (site / venv.PTH).exists()
