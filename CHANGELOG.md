---
this_file: CHANGELOG.md
---
# Changelog

## Unreleased

- New package `fontlab-python-instamix` (import `fontlab_instamix`), stdlib only, Python 3.11+.
- Data folder resolution (`--data-dir`, `FONTLAB_DATA_DIR`, `flPreferences().dataPathDefault`, platform fallback) with a vendored platformdirs subset.
- Strict `manifest.fontlabextj` parser and destination rules (`.`, `{}`, `{var}`, case-insensitive targets, `..` refused).
- Extension install from `.fontlabext` folders and `.fontlabextz` zips: safe unzip, staged copy into `Extensions/Library`, per-file links into Scripts/Encoding/Codepage/Actions/Data/site-packages, JSON ledger and JSONL log, exact uninstall that keeps changed files, upgrade by reinstall.
- uv locate/download (checksum verified), `<data>/.venv`, package install/list/uninstall into FontLab's site-packages via `uv pip install --target`.
- `wrap` (script to extension/zip), `bootstrap.install_project` for `[tool.fontlab-install]` projects, PythonQt dialogs with console fallback, `fontlab-instamix` CLI, `install.vfpy` self-installer, example `com.example.hello` extension.
- 68 offline pytest tests; not yet tested inside FontLab.
