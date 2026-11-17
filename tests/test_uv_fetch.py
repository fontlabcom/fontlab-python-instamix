# this_file: tests/test_uv_fetch.py
"""fetch_bytes falls back to Windows curl.exe only on TLS verification failure."""

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
    assert command[1:4] == ["-fsSL", "--max-time", "300"]
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


def test_fetch_when_mac_cert_fails_then_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(uv, "system_curl", lambda: tmp_path / "curl.exe")
    with pytest.raises(urllib.error.URLError):
        uv.fetch_bytes(
            "https://x",
            plat="darwin",
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
