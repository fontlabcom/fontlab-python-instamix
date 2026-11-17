---
this_file: CHANGELOG.md
---

# Changelog

## 2026-11-17 — Windows FontLab 9 uv bootstrap (Issue 259)

Tested in FontLab 9.1.9813 for Windows (x64 on Windows 11 ARM, Parallels),
starting from an empty data folder:

- On Windows, uv venv requests now pin the host's exact Python patch version
  (`cpython-3.11.9-windows-x86_64-none`) inside FontLab; macOS keeps the
  minor-version request. A minor-only request
  made uv follow its `cpython-3.11-…` directory junction, which processes
  started from FontLab cannot cross (os error 448, untrusted mount point).
- On Windows, uv keeps its managed Python in `<data>/python/uv/python`
  (`UV_PYTHON_INSTALL_DIR`, unless the user set it), away from junctions
  in `%APPDATA%\uv\python`.
- The uv download falls back to the system `curl.exe` when FontLab's OpenSSL
  rejects GitHub's certificate chain; SHA-256 checking is unchanged.

Released as 1.0.12 on PyPI. In Windows FontLab, a package `install.vfpy`
with no sibling instamix checkout fetched the 1.0.12 wheel with the curl
fallback, and a blank 14-package install plus the uv/PyPI smoke passed on it.

Native evidence: uv downloaded (0.13.9), venv created, `humanize` and
`tabulate` installed from PyPI and imported, `fontlab-fly` installed through
`install.vfpy` with its sibling packages. Records are in the workspace
`WORK/issue259/results/`. macOS native behaviour was not retested.

Known limits: a Windows venv created before this change keeps its
`pyvenv.cfg` home on the old junction and must be removed by hand; the first
Windows run downloads CPython (about 24 MiB) into the data folder, so it
needs network access.

## 2026-11-17 — Remopy release qualification

Remopy 2.0.7 includes the Wine/CrossOver providers and CLI routing in its
reviewed GitHub release. Runtime execution, remote hooks and native Windows
bootstrap remain unverified. Remopy PyPI publication failed with
invalid-publisher; publisher administration and any admitted retry remain open.
No owner-recovery or consumer-execution hold is lifted.

## 2026-11-17 — Existing shared-package venvs

A compatible environment whose site-packages resolves exactly to the canonical
package directory can now be reused without creating a redundant managed path
file or directories. Runtime version, implementation, platform, architecture and
prefix checks remain mandatory. Other escaping paths and unrelated managed path
files are still refused. The read-only runtime probe disables bytecode writes.

Four canonical-layout regressions failed first; nine mismatch/preservation cases
already passed. All 425 arm64 Python 3.11 tests pass in 8.70 seconds, with 96.49%
statement coverage for the complete venv module. The controller subsequently
qualified 21 focused tests in 4.37 seconds with 94.52% combined statement/branch
coverage for the whole module (55/57 statements and 14/16 branches). An actual offline uv-created environment,
then linked to its canonical site-packages, preserves its files, links and path
files while probing and importing. Scoped lint and wheel/sdist builds pass. The locked strict docs build and
all 36 docs tests pass (10.603 seconds), preserving the exact installer asset.
This is source qualification on owned scratch data. Owner-folder recovery and
consumer execution remain held; no existing installation is converted or repaired.
Independent source review passed. Controller reindexing now includes probe,
create and the new tests: 16 changed symbols across 11 files, one affected
cmd_pkg_install flow, MEDIUM risk. This supersedes the earlier omitted-symbol
summary; index extraction caps and the initial metadata-census limit remain.
Task 20 integration, exact-SHA CI/release and native/Windows checks remain open.

## 2026-11-17 — Installer entry context

All three standalone installer copies check the existing read-only site context
before bootstrapping, including when a ready provider is reused. External entry
execution without FontLab or FONTLAB_DATA_DIR now refuses before deployment.
The import sentinel remains side-effect free; explicit data-folder and host
preference contexts retain their behavior. CLI and direct API defaults are unchanged.

Twelve fake-provider cases cover all copies, including blocked deployment before
removing the test data override. The three missing-context cases fail before the
fix. All 411 arm64 Python 3.11 tests pass in 7.70 seconds; compile, template
parity and scoped lint checks pass. No real provider, installer deployment or
native host is executed by these
new regressions. Independent release review qualifies the guard in published
1.0.10 at 5b875f0dc41ab404cfda92b127186f1896f540b3, with successful exact-SHA
release/docs/Pages runs and matching GitHub/PyPI artifacts.
Consumer execution and owner-folder recovery remain held pending their existing
incident review; this source guard does not repair or prove prior folder state.

## 2026-11-17 — Public standalone installer download

The existing strict docs build now publishes the exact root install.vfpy as a
static download. The homepage and README link to its canonical public URL and
the homepage links the project licence. Only that exact root asset is allowed
through the source-download test; all other script and private-payload bans
remain intact. Reproducible builds now include the installer in their full-file
hash comparison.

The new missing-asset regression failed first, then 36 docs tests passed in
5.064 seconds. Full arm64 Python 3.11 source checks passed 399 tests in 11.51
seconds with an explicit owned scratch data root. Runtime modules and installer
bytes were unchanged in that increment. Independent 1.0.10 review now qualifies
the delivered download: HTTP 200, 7143 bytes, matching the released canonical
installer SHA256 5e7b64584ddfef9e276add3d465343c641b91c29840db34967735d4d00ab643e.
API/book guide delivery retains its own gates.

## 2026-11-17 — Failed legacy upgrade preservation

A legacy project upgrade now keeps a private snapshot of its affected targets,
shared tools, metadata and receipts until replacement succeeds. Installation,
requirements, ledger, startup or launcher failure restores the prior bytes,
links, modes and ownership state. Rollback failure retains recovery files and
adds their location to the exception. External package-manager effects remain
outside this file-deployment transaction; nonempty dependency folders are kept.
A rolled-back project is removed from partial-success reports, preserving other
completed records. Existing extension/ZIP partial-success behavior is unchanged.

The common bootstrap requires this private rollback capability before reusing
or accepting a provider. Published 1.0.8 lacks it and is replaced; failure to
obtain a safe replacement preserves the prior provider and prevents deployment.
The 1.0.8 release has a known legacy-upgrade defect: an unowned conflict can
leave other old files removed. Do not use that version for legacy migration.

Verified 399 arm64 Python 3.11 tests in 8.84 seconds; complete changed module
bootstrap.py has 91% combined coverage. Six real historical-installer scenarios
pass against an ordinary candidate-wheel prefix with whole-tree failure
oracles, preserving 234 Examples or 224 Scriptmix entries on refusal. Actual
published 1.0.8 rejection, failed-fetch preservation and candidate-wheel
replacement pass. Independent release review qualifies published 1.0.9 at
c676c7cad2f87556edacd98c6da6b000f9dfbfe0, its GitHub/PyPI artifact identity and
all six released-wheel legacy-preservation fixtures. Updated consumer-stub
readiness/delivery, native and Windows qualification remain separate.



## 2026-11-17 — Managed plugin migration safety

- Refuse distinct title-case plugin bundles with changed or unowned contents
  before installation writes; retain their files and ownership receipt. Unchanged
  owned copies/links and case-insensitive aliases continue to upgrade.
- Require the callable migration preflight in reused and replacement bootstrap
  providers; preserve previous packages/metadata/imports on replacement failure.
- Verified 378 tests on ordinary Python and actual arm64 Python 3.11.14, including
  the retained case-sensitive HFS+ fixture; complete changed modules exceed 80%.
  Genuine 1.0.7 refusal/recovery and current wheel replacement pass in scratch.

## Unreleased

- Package five plugin kinds from explicitly described Python drafts into canonical lowercase inner bundles; validate metadata before writes, preserve source/licence bytes and reuse agreeing plugin.json without executing drafts.
- Add plugin options to `wrap` and `wrap.make_plugin`; copied and linked archive installation retain the required kind-folder parent inside Library.
- Add lazy PythonQt multiple archive/manifest selection, folder selection and `gui.install_selected`, with cancellation and per-path partial-failure reports, including committed extensions in a partly failed ZIP. Archive exceptions retain their original identity and expose `installed_records`. Existing message reports remain print-only.

- Install and uninstall reports no longer open modal dialogs. `gui.message` now only prints, so inside FontLab the report goes to the Output panel. The uninstall Yes/No confirmation is unchanged.

- Documentation website at https://code.fontlab.com/fontlab-python-instamix/: a
  developer guide to developing, packaging, deploying and delivering FontLab 9
  scripts, Python packages and plugins with instamix, plus a command, manifest,
  project-table and plugin.json reference. Commands and output were checked
  against a scratch data folder. ProperDocs + MaterialX with the light fltheme26
  theme; sources in `src_docs/`, generated output in `docs/`;
  `.github/workflows/docs.yml` rebuilds and checks it on every main commit;
  `tests_docs/` holds 35 site tests.

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
