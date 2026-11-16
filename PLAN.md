---
this_file: fontlab-python-instamix/PLAN.md
---
# fontlab-python-instamix plan (issue 256)

Instamix installs Python packages and FontLab extensions into the FontLab 9
user data folder. It runs inside FontLab (stdlib + PythonQt + vendored code
only) and from a terminal through `fontlab-remopy`.

## Facts from the FontLab 9 C++ source (read, not run)

- Data folder (`flPreferences::dataPathDefault()`): macOS
  `~/Library/Application Support/FontLab/FontLab 9`; Windows
  `Documents\FontLab\FontLab 9`. Scripts menu and `sys.path` ignore the
  Developer > DataPath override.
- `sys.path` gets `<data>/python/3.11/site-packages` via `addSysPath`; no
  `site.addsitedir`, so `.pth` files there are probably ignored. Instamix
  must link package directories, not rely on `.pth`.
- Scripts menu scans `<data>/Scripts` recursively for `*.py`/`*.vfpy` and
  follows symlinks. Encoding/Codepage load recursively but probably do not
  follow symlinked directories on POSIX: link files, not directories.
- Opening a `.vfpy` runs it; `.py` only loads into the panel.
- Windows `sys.executable` is probably the FontLab executable: never run it
  as a subprocess.
- No native Extensions folder exists; `Extensions/` is ours.

## Package layout

```
src/fontlab_instamix/
  __init__.py        version, public API (lazy)
  env.py             FontLab environment: version, arch, data folder, paths
  platformdirs.py    vendored subset (from _private/platformdirs-unified.py)
  uv.py              locate/download uv into <data>/python/uv, run uv
  venv.py            <data>/.venv matching FontLab Python version and arch
  packages.py        pip install/uninstall/list into FontLab site-packages
  manifest.py        manifest.fontlabextj parsing (dataclasses, strict)
  dest.py            destination rule resolver (".", "{}", "dir/{}/sub", vars)
  extension.py       install/uninstall/list .fontlabext and .fontlabextz
  ledger.py          JSON install records + JSONL log
  wrap.py            wrap a script or plugin draft into a .fontlabext/.fontlabextz
  bootstrap.py       two-line installer support and self-install
  gui.py             small PythonQt helpers (message, confirm, progress, pick file)
  cli.py             argparse CLI: env, pip, ext, wrap, bootstrap
install.vfpy         self-extracting installer of instamix itself
```

## Manifest (`manifest.fontlabextj`, JSON, at extension root)

```json
{
  "id": "com.example.myext",
  "name": "My Extension",
  "version": "1.0.0",
  "description": "...",
  "min_fontlab": "9.0",
  "python": {"requires": ["fonttools>=4"], "packages": ["src/mypkg"]},
  "vars": {"family": "adamtrix"},
  "install": [
    {"from": "scripts", "to": "Scripts/{}"},
    {"from": "encoding/*.enc", "to": "Encoding/{}"},
    {"from": "actions/*.json", "to": "Actions/."},
    {"from": "data", "to": "Data/{family}/"}
  ]
}
```

Destination rules: `.`/`./` = target root; `{}` = extension basename without
`.fontlabext`; `dir`, `./dir/` = subfolder; `{var}` = manifest `vars` value.
Unknown `{var}` or `..` escape is an error. Targets: `Scripts`, `Actions`,
`Codepage`, `Data`, `Encoding`, `site-packages` (case-insensitive names).

## Install flow

1. `.fontlabextz`: validate member names, unzip to temp, run optional
   `install.vfpy` or `install_<name>.fontlabext.vfpy` hook only on request.
2. Copy each `.fontlabext` to `<data>/Extensions/Library/<id>.fontlabext`
   (staged, replaced atomically).
3. Link files from Library into targets (symlink on macOS; copy on Windows
   and when symlinks fail). `python.packages` are linked into site-packages;
   `python.requires` go through uv into site-packages.
4. Write `<data>/Extensions/.instamix/<id>.json` record outside Library, which is only a source (every created
   path and its hash), so uninstall removes exactly what was created.

## Python packages

- `uv` fetched once from GitHub releases (stdlib urllib + zip/tar, sha256 from
  release file) into `<data>/python/uv/`.
- `<data>/.venv` created with `uv venv --python <FontLab version>`; installs
  use `uv pip install --target <data>/python/3.11/site-packages --python-version
  3.11 --python-platform <platform>` so no separate interpreter needs to match.

## CLI via remopy

`fontlab-instamix` runs standalone (outside FontLab) for env/pip/ext/wrap on
a given data folder, and `fontlab-remopy` forwards `instamix` commands into
the running FontLab when a live answer is needed.

## Changes in other repositories

- fontlab-remopy: `platforms/windows.py` and CrossOver launcher
  (`wine`/`cxstart` with bottle `fontlab`), data-folder resolution for the
  bottle, `instamix` subcommand passthrough.
- fontlab-fontlabapp: `core/application/paths.py` and `versions.py` delegate
  to `fontlab_instamix.env` when importable (keep fallbacks; no import cycle:
  instamix never imports fontlabapp).
- fontlab-python-plugmix, scriptmix, examples, pens, grablab, glyport,
  fontport, echopy, fly, remopy, aidus-agentus: replace their copies of
  `install.vfpy` logic with the two-line bootstrap when instamix is present,
  keeping the standalone path. Root `install.sh` gains an instamix-first step.
- python-docs and python-book: user guide page for instamix and the manifest.

## Milestones

1. Core: env, platformdirs subset, dest resolver, manifest, ledger — tests.
2. Extensions: install/uninstall/list .fontlabext/.fontlabextz — tests with
   fixtures in a temp data folder.
3. Packages: uv fetch, venv, pip install/uninstall/list — tests with a fake
   uv plus one real offline-safe smoke run.
4. CLI, GUI helpers, wrap, bootstrap, self-installing `install.vfpy`.
5. remopy Windows/CrossOver support and instamix passthrough.
6. fontlabapp env delegation and other-repo installer updates.
7. Live tests: macOS FontLab 9 and Windows FontLab 9 in CrossOver.
8. Docs, CHANGELOG, final review, integration to main.

## Known limits

- `.pth`, symlinked-directory and `.vfpy`-from-argv behaviour are source
  inferences until the live tests confirm them.
