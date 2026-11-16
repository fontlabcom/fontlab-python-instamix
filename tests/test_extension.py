# this_file: tests/test_extension.py
import os
import shutil
import sys
import zipfile

import pytest

from fontlab_instamix import extension, ledger, wrap
from fontlab_instamix.extension import InstallError


def _no_reqs(data, specs):
    raise AssertionError(f"unexpected requirements {specs}")


def test_check_member_when_unsafe_then_rejected():
    for bad in ["/abs/x", "../x", "a/../../x", "C:/x", "a\\b"]:
        with pytest.raises(InstallError):
            extension.check_member(bad)
    extension.check_member("com.example.a.fontlabext/manifest.fontlabextj")


def test_unpack_when_zip_has_dotdot_then_rejected(tmp_path):
    zpath = tmp_path / "bad.fontlabextz"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("com.example.a.fontlabext/manifest.fontlabextj", "{}")
        z.writestr("../evil.py", "x")
    with pytest.raises(InstallError):
        extension.unpack(zpath, tmp_path / "out")
    assert not (tmp_path / "evil.py").exists()


def test_install_when_example_then_files_linked_and_recorded(data, example):
    [_record] = extension.install(example, data, requirements=_no_reqs)
    script = data / "Scripts" / "com.example.hello" / "Hello.py"
    enc = data / "Encoding" / "com.example.hello" / "hello.enc"
    assert script.is_file() and enc.is_file()
    if sys.platform != "win32":
        assert script.is_symlink() and enc.is_symlink()
        assert "Extensions/Library" in os.readlink(script)
    assert (data / "Extensions" / "Library" / "com.example.hello.fontlabext").is_dir()
    assert ledger.read(data, "com.example.hello")["version"] == "1.0.0"
    assert [r["id"] for r in extension.installed(data)] == ["com.example.hello"]


def test_uninstall_when_installed_then_removes_exactly_ours(data, example):
    (data / "Scripts").mkdir()
    keep = data / "Scripts" / "mine.py"
    keep.write_text("x")
    extension.install(example, data, requirements=_no_reqs)
    assert extension.uninstall("com.example.hello", data) == []
    assert keep.read_text() == "x"
    assert (data / "Scripts").is_dir() and (data / "Encoding").is_dir()
    assert not (data / "Scripts" / "com.example.hello").exists()
    assert not (data / "Encoding" / "com.example.hello").exists()
    assert not (data / "Extensions" / "Library" / "com.example.hello.fontlabext").exists()
    assert ledger.read(data, "com.example.hello") is None


def test_uninstall_when_copied_file_changed_then_kept(data, example):
    extension.install(example, data, copy=True, requirements=_no_reqs)
    script = data / "Scripts" / "com.example.hello" / "Hello.py"
    assert not script.is_symlink()
    script.write_text("edited")
    kept = extension.uninstall("com.example.hello", data)
    assert script.read_text() == "edited"
    assert any("Hello.py" in k for k in kept)


def test_uninstall_when_unknown_then_error(data):
    with pytest.raises(InstallError):
        extension.uninstall("com.example.none", data)


def test_install_when_upgrade_then_old_files_gone(data, example):
    extension.install(example, data, requirements=_no_reqs)
    (example / "scripts" / "Hello.py").rename(example / "scripts" / "Hello2.py")
    text = (example / "manifest.fontlabextj").read_text().replace('"1.0.0"', '"1.1.0"')
    (example / "manifest.fontlabextj").write_text(text)
    extension.install(example, data, requirements=_no_reqs)
    folder = data / "Scripts" / "com.example.hello"
    assert sorted(p.name for p in folder.iterdir()) == ["Hello2.py"]
    assert ledger.read(data, "com.example.hello")["version"] == "1.1.0"


def test_install_when_reinstall_same_then_ok(data, example):
    extension.install(example, data, requirements=_no_reqs)
    extension.install(example, data, requirements=_no_reqs)
    assert (data / "Scripts" / "com.example.hello" / "Hello.py").is_file()


def test_install_when_foreign_file_in_way_then_error(data, example):
    target = data / "Encoding" / "com.example.hello"
    target.mkdir(parents=True)
    (target / "hello.enc").write_text("theirs")
    with pytest.raises(InstallError):
        extension.install(example, data, requirements=_no_reqs)
    assert (target / "hello.enc").read_text() == "theirs"


def test_install_when_zip_then_built_and_installed(data, example, tmp_path):
    zpath = wrap.make_zip([example], tmp_path / "Hello.FONTLABEXTZ")
    with zipfile.ZipFile(zpath) as z:
        assert "com.example.hello.fontlabext/manifest.fontlabextj" in z.namelist()
    [record] = extension.install(zpath, data, requirements=_no_reqs)
    assert record["id"] == "com.example.hello"
    assert (data / "Scripts" / "com.example.hello" / "Hello.py").is_file()


def test_install_when_case_insensitive_folder_suffix_then_ok(data, example):
    upper = example.with_name("com.example.hello.FontLabExt")
    example.rename(upper)
    [record] = extension.install(upper, data, requirements=_no_reqs)
    assert record["id"] == "com.example.hello"


def test_install_when_packages_and_requires_then_site_linked_and_uv_called(data, tmp_path):
    folder = tmp_path / "com.example.pkg.fontlabext"
    (folder / "src" / "mypkg").mkdir(parents=True)
    (folder / "src" / "mypkg" / "__init__.py").write_text("X = 1\n")
    (folder / "manifest.fontlabextj").write_text(
        '{"id": "com.example.pkg", "name": "P", "version": "1",'
        ' "python": {"packages": ["src/mypkg"], "requires": ["fonttools>=4"]}}'
    )
    calls = []
    extension.install(folder, data, requirements=lambda d, specs: calls.append(list(specs)))
    assert calls == [["fonttools>=4"]]
    assert (data / "python" / "3.11" / "site-packages" / "mypkg" / "__init__.py").is_file()
    extension.uninstall("com.example.pkg", data)
    assert not (data / "python" / "3.11" / "site-packages" / "mypkg").exists()


def test_ledger_when_installed_then_outside_library(data, example):
    extension.install(example, data, requirements=_no_reqs)
    record = ledger.record_path(data, "com.example.hello")
    assert record.is_file()
    library = (data / "Extensions" / "Library").resolve()
    assert library not in record.resolve().parents
    assert sorted(p.name for p in library.iterdir()) == ["com.example.hello.fontlabext"]


def test_install_when_reinstall_fails_then_old_state_restored(data, example):
    extension.install(example, data, requirements=_no_reqs)
    script = data / "Scripts" / "com.example.hello" / "Hello.py"
    library = data / "Extensions" / "Library" / "com.example.hello.fontlabext"
    old_manifest = (library / "manifest.fontlabextj").read_text()
    before = ledger.read(data, "com.example.hello")
    # The new version adds a file whose destination is already taken by a stranger.
    (example / "scripts" / "Extra.py").write_text("print(2)\n")
    text = (example / "manifest.fontlabextj").read_text().replace('"1.0.0"', '"2.0.0"')
    (example / "manifest.fontlabextj").write_text(text)
    (data / "Scripts" / "com.example.hello" / "Extra.py").write_text("theirs")
    with pytest.raises(InstallError):
        extension.install(example, data, requirements=_no_reqs)
    assert script.is_file()
    assert (library / "manifest.fontlabextj").read_text() == old_manifest
    assert not (library / "scripts" / "Extra.py").exists()
    assert ledger.read(data, "com.example.hello") == before
    assert (data / "Scripts" / "com.example.hello" / "Extra.py").read_text() == "theirs"
    assert not list((data / "Extensions" / "Library").glob("*.prev"))
    assert extension.uninstall("com.example.hello", data) == ["Scripts/com.example.hello"]
    assert not script.exists()


@pytest.mark.parametrize("bad", ["../../x", "a/b", "a\\b", "..", "", "c:x", "a..b"])
def test_uninstall_when_id_unsafe_then_error(data, bad):
    with pytest.raises((InstallError, ledger.LedgerError)):
        extension.uninstall(bad, data)


def test_uninstall_when_ledger_paths_escape_then_outside_untouched(data, tmp_path):
    outside = tmp_path / "outside"
    (outside / "keep").mkdir(parents=True)
    (outside / "keep" / "f.txt").write_text("x")
    folder = ledger.ledger_dir(data)
    folder.mkdir(parents=True)
    record = {
        "id": "com.example.evil",
        "library": "../outside",
        "entries": [
            {"path": "../outside/keep/f.txt", "kind": "copy", "sha256": ledger.sha256(outside / "keep" / "f.txt")},
            {"path": str(outside / "keep"), "kind": "dir"},
        ],
    }
    (folder / "com.example.evil.json").write_text(__import__("json").dumps(record))
    with pytest.raises(InstallError):
        extension.uninstall("com.example.evil", data)
    assert (outside / "keep" / "f.txt").read_text() == "x"


def test_uninstall_when_library_is_symlink_then_target_untouched(data, example, tmp_path):
    extension.install(example, data, copy=True, requirements=_no_reqs)
    library = data / "Extensions" / "Library" / "com.example.hello.fontlabext"
    elsewhere = tmp_path / "elsewhere"
    shutil.move(str(library), str(elsewhere))
    library.symlink_to(elsewhere, target_is_directory=True)
    extension.uninstall("com.example.hello", data)
    assert not library.is_symlink() and (elsewhere / "manifest.fontlabextj").is_file()


def test_installed_when_record_corrupt_then_skipped(data, example):
    extension.install(example, data, requirements=_no_reqs)
    (ledger.ledger_dir(data) / "com.example.bad.json").write_text("{not json")
    assert [r["id"] for r in extension.installed(data)] == ["com.example.hello"]


def test_install_when_requirements_fail_then_ledger_still_written(data, tmp_path):
    folder = tmp_path / "com.example.req.fontlabext"
    (folder / "scripts").mkdir(parents=True)
    (folder / "scripts" / "R.py").write_text("print(1)\n")
    (folder / "manifest.fontlabextj").write_text(
        '{"id": "com.example.req", "name": "R", "version": "1", "python": {"requires": ["x"]},'
        ' "install": [{"from": "scripts", "to": "Scripts/{}"}]}'
    )

    def boom(data, specs):
        raise RuntimeError("uv failed")

    with pytest.raises(RuntimeError):
        extension.install(folder, data, requirements=boom)
    assert ledger.read(data, "com.example.req")["requires_failed"] is True
    extension.uninstall("com.example.req", data)
    assert not (data / "Scripts" / "com.example.req").exists()
