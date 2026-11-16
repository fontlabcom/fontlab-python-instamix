# this_file: src/fontlab_instamix/platformdirs.py
"""Tiny subset of platformdirs: the two folders instamix needs.

Adapted from platformdirs (https://github.com/tox-dev/platformdirs).

MIT License

Copyright (c) 2010-202x The platformdirs developers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_DOCUMENTS_GUID = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"


def user_data_dir_macos() -> Path:
    """``~/Library/Application Support``."""
    return Path.home() / "Library" / "Application Support"


def _documents_via_ctypes() -> str:
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    guid = GUID()
    ole32 = ctypes.WinDLL("ole32")  # type: ignore[attr-defined]
    ole32.CLSIDFromString(ctypes.c_wchar_p(_DOCUMENTS_GUID), ctypes.byref(guid))
    path_ptr = ctypes.c_wchar_p()
    shell32 = ctypes.WinDLL("shell32")  # type: ignore[attr-defined]
    result = shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0x4000, None, ctypes.byref(path_ptr))
    try:
        if result != 0 or not path_ptr.value:
            raise OSError("SHGetKnownFolderPath failed for Documents")
        return path_ptr.value
    finally:
        ole32.CoTaskMemFree(path_ptr)


def _documents_via_registry() -> str:
    import winreg  # type: ignore[import-not-found]

    key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
        return str(winreg.QueryValueEx(handle, "Personal")[0])


def user_documents_dir_windows() -> Path:
    """Windows Documents folder: known-folder API, registry, then USERPROFILE."""
    for resolver in (_documents_via_ctypes, _documents_via_registry):
        try:
            return Path(os.path.normpath(resolver()))
        except Exception:  # noqa: BLE001 - fall through to the next resolver
            continue
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents"


def default_data_dir(platform: str = sys.platform) -> Path:
    """FontLab 9's default data folder when FontLab itself cannot tell us."""
    if platform == "win32":
        return user_documents_dir_windows() / "FontLab" / "FontLab 9"
    return user_data_dir_macos() / "FontLab" / "FontLab 9"
