---
this_file: CHANGELOG.md
---
# Changelog

## Unreleased — standalone installer and ZIP packaging (2026-11-17)

- Install a validated wheel from one standalone file, retaining distribution metadata and licence; preserve prior package links and metadata on failure.
- Share the bootstrap template across root/project installers; support offline local or sibling built wheels and live Python version discovery.
- Generate a two-line extension installer when Instamix is already installed.
- Add multi-folder `pack`; enforce exact manifest namespace with case-insensitive suffixes, reject invalid/duplicate roots before touching output and preserve existing archives on staging failure.
- Validate the GUI/project entry APIs before committing a bootstrapped wheel or reusing an installed copy; restore prior installation if required APIs are incomplete.
- Verify 307 tests and actual wheel-from-sdist installation in a disposable data folder; native and Windows acceptance remain open.

## Unreleased — shared Python environment (2026-11-17)

- Resolve embedded Python version at runtime; accept explicit target facts for remote callers and reject unsupported architectures.
- Verify standalone venv version, platform, architecture and prefix; preserve incompatible environments. Share canonical site-packages through an owned venv `.pth` and install through its verified interpreter.
- Keep a local uv executable by copying an available binary; bound uv commands and interpreter probes.
- Expose lazy `install_packages(*specs, data=None)` without changing extension `install`; refresh import caches after installation and reject option-like package requirements.
- Resolve extension site-packages rules through the same live-version provider as Python packages; guard uv download destinations and temporary files against escaping links.
- Read wheel RECORD as CSV, including quoted commas and newlines. Explicit-version package listing and removal use the same target as installation.
- Offline arm64 CPython 3.11 wheel installation and both shared import routes pass in scratch directories. Native FontLab and Windows execution remain unverified.

## Unreleased

- Stage checkout metadata and uninstall launchers before changing the install. Restore installed copy bytes, links, tracked directory permissions, Library and ledger bytes/permissions after placement or ledger-write failure, including generated records without source paths. Preserve modified launchers and unrelated metadata; retain the explicit requires_failed partial-install contract. Fifteen focused offline regressions pass, including custom file/directory permissions; the preceding complete 268-test arm64 Python 3.11 suite passed.
- Cache the download test fixture's archive bytes so payload and checksum cannot differ across a gzip timestamp boundary.

- Refuse escaped destination directory links and linked Library staging or ledger files before changing installs. Preserve symlinked data roots, internal directory links and editable package links. Reject absolute/traversing source declarations while retaining bootstrap source links; offline rollback checks cover ordinary deployed files.

- Validate wrapper metadata before creating or copying output. Require extension folder basenames to match manifest IDs and validate install plans before creating data folders or replacing installs. Mixed-case extension suffixes and bootstrap checkout installs remain supported; 26 new offline regressions pass.

- Public `install(path)`, `installed()` and `uninstall(id)` resolve omitted data folders through the existing environment helper. Explicit positional data folders still take precedence. Four offline API regressions pass, including folder, manifest and archive entry points.

- Accept a root `manifest.fontlabextj` path when installing an extension, including case-insensitive filenames. Reuse the containing folder identity and existing deployment flow; reject unrelated files and manifests outside extension folders. Offline tests cover direct API and CLI use.

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

## 2026-11-17 — Remote CLI target routing

Added optional lazy Remopy routing for env, package/extension install/list/remove
and venv. Short host calls discover facts, verify an owned nonce and invalidate
caches; providers run locally with explicit target facts. Extension manifest
rules, package sources, requirements and standard folders share the host version.
Existing local defaults remain compatible. Conflicting data overrides, foreign OS,
malformed facts and remote hooks refuse; timeout is not retried, and refresh
failure reports the already completed operation separately.

Baseline 270 passed. Full coverage run: 295 passed in 7.37s; complete changed
modules CLI 89%, dest 100%, env 91%, extension 93%, remote 97%. Focused remote
transport/nonce/target/timeout cases use fake Remopy and scratch files, including
an external provider delayed beyond five seconds. Native/Windows, remote hooks
and released installation remain unverified. Task evidence:
.superpowers/sdd/PLAN/task-7-report.md. No native calls, install, commit or push.
