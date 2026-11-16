---
this_file: CHANGELOG.md
---
# Changelog

## 1.0.3 (2026-11-16)

- Legacy migration moves files the legacy log recorded (`hashes`, `kept`) at new install targets to `Extensions/.instamix/backup/<id>/<UTC>/` instead of refusing, restores them if the install fails, and still applies after an earlier `migrated_to` uninstall. Unrecorded collisions still refuse. Reruns never move instamix's own files, backup folders are never overwritten, and a rollback restore is logged as `restored`.

## 1.0.2 (2026-11-16)

- Sibling detection now follows legacy `fontlab-fly`: a neighbouring folder counts only if it has `install.vfpy` and a pyproject with a `[tool.fontlab-install]` table and valid `id`, matched by normalised table or project name. Read-only checkouts such as TypeRig no longer break installs; their specs go to uv.
- Uninstall removes empty folders that instamix created under `Scripts/` (never `Scripts/` itself) and deletes `initScript.py` when only instamix's block was in it.
- 147 offline pytest tests; an offline run installed and uninstalled all 13 workspace packages in one data folder.

## 1.0.1 (2026-11-16)

- Legacy `install.vfpy` parity in `bootstrap.install_project`: environment markers (`markers.py`), hatch-vcs versions (`vcs.py`), dist-info (`distinfo.py`), the fontlabapp `initScript.py` block (`initscript.py`), `Scripts/Instamix` launchers (`launchers.py`, `launch.py`), plugin bundles under `Extensions/<kind>`, Scripts mapping and junk filter, hatch/project fallbacks for packages and dependencies, and migration of legacy installs (`legacy.py`).
- `fontlab-instamix stub DIR [--force]` writes the standard 40-line `install.vfpy` (`stub/install.vfpy`). It finds instamix installed, in a sibling checkout or as a sha256-checked PyPI wheel.
- Breaking: top-level `Scripts/` now installs into FontLab's `Scripts/` (not `Scripts/<id>/`), as the legacy installers did.
- Top-level README, LICENSE, CHANGELOG and `.md` files in `Scripts/` are not installed into FontLab's Scripts root.
- The stub uses an installed instamix only if it has `fontlab_instamix.legacy`; otherwise it falls back to a sibling checkout or PyPI.
- 140 offline pytest tests; not yet tested inside FontLab.

## 1.0.0 (2026-11-16)

- New package `fontlab-python-instamix` (import `fontlab_instamix`), stdlib only, Python 3.11+.
- Data folder resolution (`--data-dir`, `FONTLAB_DATA_DIR`, `flPreferences().dataPathDefault`, platform fallback) with a vendored platformdirs subset.
- Strict `manifest.fontlabextj` parser and destination rules (`.`, `{}`, `{var}`, case-insensitive targets, `..` refused).
- Extension install from `.fontlabext` folders and `.fontlabextz` zips: safe unzip, staged copy into `Extensions/Library`, per-file links into Scripts/Encoding/Codepage/Actions/Data/site-packages, JSON ledger and JSONL log, exact uninstall that keeps changed files, upgrade by reinstall.
- uv locate/download (checksum verified), `<data>/.venv`, package install/list/uninstall into FontLab's site-packages via `uv pip install --target`.
- `wrap` (script to extension/zip), `bootstrap.install_project` for `[tool.fontlab-install]` projects, PythonQt dialogs with console fallback, `fontlab-instamix` CLI, `install.vfpy` self-installer, example `com.example.hello` extension.
- 68 offline pytest tests; not yet tested inside FontLab.
