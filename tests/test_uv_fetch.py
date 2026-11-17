# this_file: tests/test_uv_fetch.py
"""fetch_bytes uses the system curl only on TLS verification failure."""

import ssl
import subprocess
import urllib.error

import pytest

from fontlab_instamix import uv


def failing_open(reason):
    def urlopen(url, timeout):
        raise urllib.error.URLError(reason)

    return urlopen


def ok_runner(command, **kwargs):
    assert command[1:] == ["-fsSL", "--proto", "=https", "--proto-redir", "=https", "--max-time", "300", "--", command[-1]], command
    return subprocess.CompletedProcess(command, 0, b"payload", b"")


def test_fetch_when_win32_cert_fails_then_uses_curl(monkeypatch, tmp_path):
    curl = tmp_path / "curl.exe"
    curl.write_bytes(b"")
    monkeypatch.setattr(uv, "system_curl", lambda: curl)
    got = uv.fetch_bytes(
        "https://x",
        plat="win32",
        urlopen=failing_open(ssl.SSLCertVerificationError("bad")),
        runner=ok_runner,
    )
    assert got == b"payload"


def test_fetch_when_mac_cert_fails_then_uses_system_curl(monkeypatch, tmp_path):
    curl = tmp_path / "curl"
    curl.write_bytes(b"")
    monkeypatch.setattr(uv, "MAC_CURL", curl)
    seen = []

    def runner(command, **kwargs):
        seen.append(command[0])
        return ok_runner(command, **kwargs)

    got = uv.fetch_bytes(
        "https://x",
        plat="darwin",
        urlopen=failing_open(ssl.SSLCertVerificationError("bad")),
        runner=runner,
    )
    assert got == b"payload"
    assert seen == [str(curl)]


def test_fetch_when_mac_has_no_curl_then_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(uv, "MAC_CURL", tmp_path / "absent")
    with pytest.raises(urllib.error.URLError):
        uv.fetch_bytes(
            "https://x",
            plat="darwin",
            urlopen=failing_open(ssl.SSLCertVerificationError("bad")),
            runner=ok_runner,
        )


def test_fetch_when_linux_cert_fails_then_raises():
    with pytest.raises(urllib.error.URLError):
        uv.fetch_bytes(
            "https://x",
            plat="linux",
            urlopen=failing_open(ssl.SSLCertVerificationError("bad")),
            runner=ok_runner,
        )


def test_fetch_when_win32_other_error_then_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(uv, "system_curl", lambda: tmp_path / "curl.exe")
    with pytest.raises(urllib.error.URLError):
        uv.fetch_bytes(
            "https://x",
            plat="win32",
            urlopen=failing_open(OSError("offline")),
            runner=ok_runner,
        )


def test_curl_bytes_when_curl_fails_then_uv_error(tmp_path):
    def bad(command, **kwargs):
        return subprocess.CompletedProcess(command, 22, b"", b"404")

    with pytest.raises(uv.UvError, match="404"):
        uv.curl_bytes("https://x", tmp_path / "curl.exe", bad)


def test_fetch_when_win32_without_curl_then_raises(monkeypatch):
    monkeypatch.setattr(uv, "system_curl", lambda: None)
    with pytest.raises(urllib.error.URLError):
        uv.fetch_bytes("https://x", plat="win32", urlopen=failing_open(ssl.SSLCertVerificationError("bad")), runner=ok_runner)


def test_curl_bytes_when_curl_cannot_start_then_uv_error(tmp_path):
    def missing(command, **kwargs):
        raise FileNotFoundError(command[0])
    with pytest.raises(uv.UvError, match="curl could not download"):
        uv.curl_bytes("https://x", tmp_path / "curl.exe", missing)


def test_download_when_curl_bytes_bad_hash_then_refuses(tmp_path):
    def fetch(url):
        return b"0" * 64 + b"  uv.zip" if url.endswith(".sha256") else b"tampered"
    with pytest.raises(uv.UvError):
        uv.download(tmp_path, "0.9.0", fetch=fetch)


def test_curl_bytes_when_cert_variables_set_then_not_passed_to_curl(monkeypatch, tmp_path):
    monkeypatch.setenv("SSL_CERT_FILE", "/nowhere.pem")
    monkeypatch.setenv("CURL_CA_BUNDLE", "/nowhere.pem")
    seen = {}

    def runner(command, **kwargs):
        seen.update(kwargs["env"])
        return subprocess.CompletedProcess(command, 0, b"payload", b"")

    assert uv.curl_bytes("https://x", tmp_path / "curl", runner) == b"payload"
    assert "SSL_CERT_FILE" not in seen and "CURL_CA_BUNDLE" not in seen, seen.keys()
    assert "PATH" in seen
