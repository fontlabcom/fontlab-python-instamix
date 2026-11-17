---
this_file: README.md
---
# fontlab-python-instamix

Installs extensions, scripts and Python packages into FontLab 9. Stdlib only,
runs inside FontLab's embedded Python 3.11 and from an ordinary terminal.

Documentation: <https://code.fontlab.com/fontlab-python-instamix/>

- **Extensions**: `.fontlabext` folders (also selectable by their root
  `manifest.fontlabextj`) and `.fontlabextz` zips are copied to
  `<data>/Extensions/Library/<id>.fontlabext`, then their files are linked
  into `Scripts`, `Encoding`, `Codepage`, `Actions`, `Data` and
  `python/3.11/site-packages`. A ledger records every path, so uninstall
  removes exactly what was installed and keeps files you changed.
- **Packages**: PyPI and `git+` packages go into FontLab's site-packages
  through [uv](https://docs.astral.sh/uv/), run as its own binary (never
  through `sys.executable`, which is FontLab itself on Windows).
- **Projects**: a repository with `[tool.fontlab-install]` in its
  `pyproject.toml` installs itself with a two-line `install.vfpy`.

`<data>` is FontLab's data folder: `--data-dir`, else `$FONTLAB_DATA_DIR`,
else `fontlab.flPreferences().dataPathDefault`, else
`~/Library/Application Support/FontLab/FontLab 9` (macOS) or
`Documents\FontLab\FontLab 9` (Windows).

## Install inside FontLab

[Download the single install.vfpy](https://code.fontlab.com/fontlab-python-instamix/install.vfpy)
and open it in FontLab 9 (File > Open). It installs the
compatible PyPI wheel with SHA-256 verification, including distribution metadata
and its licence. An adjacent `dist/` wheel or a sibling
`../fontlab-python-instamix/dist/` wheel works offline; keep only the intended
wheel there. Source-only sibling copies now require `uv build` first. This avoids
inventing release metadata or dropping its licence. Download, validation or
replacement failures restore the previous package and metadata, including links.

Standalone `.vfpy` entry points require FontLab or an explicit
`FONTLAB_DATA_DIR`, including when Instamix is already installed. Importing with
the `install_vfpy_import` sentinel has no installation side effects. CLI and
direct API data-folder defaults remain as described above.

The installer uses the running FontLab Python version (3.11 outside the host).
For editable checkouts use `fontlab-instamix bootstrap DIR` with Instamix already
installed; the standalone installer consistently installs wheel bytes.
Then in FontLab's Python panel:

```python
import fontlab_instamix as im
im.install("/path/to/com.example.hello.fontlabextz")
im.install_packages("fonttools>=4")  # distribution requirements for scripts
im.installed()  # installation records
im.uninstall("com.example.hello")
```

These calls use the data folder resolved above. Pass `data=Path("/scratch/FontLab 9")`
to any of them to use an explicit folder (import `Path` from `pathlib`).

## Legacy project upgrades

Use the current shared installer before upgrading an old `install.vfpy`
installation. Instamix 1.0.8 can remove other legacy-installed files after an
unowned target blocks the replacement. The corrected bootstrap refuses that
provider and obtains a replacement before deployment; if replacement fails,
it keeps the previous provider and stops.

The corrected project installer restores affected legacy files and receipts
when replacement fails. If restoration itself fails, its error gives the
retained recovery folder. Dependency installation has its own external effects;
this guarantee concerns the project's deployed files and ownership records.

## Shared Python packages

`install_packages(*specs, data=None)` installs distribution requirements, then
refreshes import caches. It does not infer distribution names from import names
or reload modules already imported. `im.install` continues to install extensions.

Package installation creates or verifies `<data>/.venv`, using the embedded
Python version and architecture inside FontLab. Standalone commands default to
FontLab 9's Python 3.11 and the current OS/architecture; they do not discover a
remote FontLab yet. A qualified uv Python request prevents accidental Intel
selection on Apple Silicon. uv is kept in `<data>/python/uv/`.

New venvs read `<data>/python/<version>/site-packages` through a managed
`.pth` file. An existing compatible venv whose site-packages resolves to that
exact canonical directory is reused without adding or changing files. Packages install directly into that canonical directory, which
FontLab already adds to its import path. FontLab need not process `.pth` files.
An incompatible existing venv or unrelated `.pth` file is refused without
replacement: inspect it and move it aside explicitly before retrying.

Remote callers can pass `env.Target(version, platform, arch)` to
`packages.install`, `packages.listed`, `packages.uninstall` and `venv.create`.
These provider APIs do not themselves contact FontLab.

## Command line

```sh
uvx fontlab-python-instamix --help        # or: python -m fontlab_instamix
fontlab-instamix env                       # Python, platform, FontLab folders
fontlab-instamix ext install Hello.fontlabextz some.fontlabext [--copy]
fontlab-instamix ext list
fontlab-instamix ext uninstall com.example.hello
fontlab-instamix pkg install fonttools "git+https://github.com/o/r"
fontlab-instamix pkg list | pkg uninstall fonttools
fontlab-instamix wrap MyScript.py --id com.me.myscript --zip
fontlab-instamix bootstrap path/to/project
fontlab-instamix uv fetch                  # find uv or download it to <data>/python/uv
fontlab-instamix venv                      # <data>/.venv for Python 3.11
```

Every command takes `--data-dir`, so you can try it on a scratch folder.

## Extension format

A `com.example.hello.fontlabext` folder (reverse-DNS name) holds
`manifest.fontlabextj` at its root:

```json
{"id": "com.example.hello", "name": "Hello", "version": "1.0.0",
 "min_fontlab": "9.0",
 "python": {"requires": ["fonttools>=4"], "packages": ["src/hello"]},
 "vars": {"family": "adamtrix"},
 "install": [{"from": "scripts", "to": "Scripts/{}"},
             {"from": "encoding/*.enc", "to": "Encoding/{}"},
             {"from": "data", "to": "Data/{family}/"}]}
```

Destinations start with a target (`Scripts`, `Actions`, `Codepage`, `Data`,
`Encoding`, `site-packages`, any case). `.` is the target root, `{}` the
extension name without `.fontlabext`, `{var}` a value from `vars`. Unknown
variables, unknown targets and `..` are errors. Files are linked one by one
(copied on Windows or when a symlink fails). A `.fontlabextz` is a zip holding
one or more `.fontlabext` folders; absolute, drive-letter and `..` members are
refused. Optional `install.vfpy` hooks in a zip run only with `--run-hooks`.
Unknown manifest keys are errors, except `this_file`.

See `examples/com.example.hello.fontlabext`.

## Plugin drafts and selection helpers

`wrap --kind reporter --plugin-id Demo --name Demo --entry demo:Demo
--min-app-version 1.0.0` packages an existing App-compatible draft.
`gui.install_selected()` selects multiple archives/manifests; `folder=True`
chooses one extension directory. See [examples and API](examples/plugins.md).

## Stub install.vfpy for other projects

`fontlab-instamix stub DIR` writes `install.vfpy` (`--force` replaces an
existing file). In a checkout with `pyproject.toml`, the bootstrap uses an installed
Instamix with callable `extension.preflight_plugin_migration`, otherwise the same
validated wheel installer as the standalone file. Older providers such as 1.0.7
are replaced; a failed replacement restores their package, metadata and imports.
It then calls `bootstrap.install_project(__file__)`. The canonical resource is
`src/fontlab_instamix/stub_install.vfpy`; generated copies are checked for parity.

For a `.fontlabext` folder, `stub DIR` writes a two-line entry that calls
`extension.install` on that folder. This short entry requires Instamix installed;
use the standalone installer once first. To distribute multiple extensions:

```sh
fontlab-instamix pack com.example.first.fontlabext com.example.second.fontlabext --out tools.fontlabextz
```

Every manifest and root identity is checked before creating a temporary archive;
case-insensitive duplicate identities are refused. A failed pack preserves the
previous output archive. Install/uninstall still tracks each extension separately.

`install_project` reads `[tool.fontlab-install]`:

```toml
[tool.fontlab-install]
id = "com.example.tool"           # required, reverse-DNS
name = "Tool"
packages = ["src/tool"]           # default: [tool.hatch.build.targets.wheel] packages
scripts = ["tools/Extra"]         # top-level Scripts/ is always included
extensions = "Extensions"         # .fontlabext folders and <kind>/<Name>.fontlab<Kind> bundles
dependencies = ["fontlab-fly>=1"] # default: [project] dependencies
init-script = false               # default: true only for com.fontlab.fontlabapp
```

It matches the legacy `install.vfpy`:

- Top-level `Scripts/` maps onto FontLab's `Scripts/`; other listed folders map to `Scripts/<path>`. `__pycache__`, `*.pyc`, `*.vfpyc` and `.DS_Store` are skipped.
- Bundles go to `Extensions/<kind>/<Name>.fontlab<Kind>`.
- Dependency markers are evaluated for FontLab's Python 3.11 on the host OS. Specs that do not apply are skipped; `METADATA` keeps all of them.
- The version comes from the static `[project].version`, then the hatch-vcs version file, `PKG-INFO`, `git describe` and the fallback version.
- `<dist>-<version>.dist-info` (INSTALLER `fontlab-instamix`) is written so `importlib.metadata` finds the package. Uninstall removes it and never follows the editable package link.
- `Scripts/Instamix/` holds `List Extensions.py` and `Uninstall <id>.py`.
- For fontlabapp, the `fontlabapp.plugins` block is added to `initScript.py`, and removed again on uninstall; `initScript.py` is deleted if nothing else is in it. Empty folders under `Scripts/` that instamix created are pruned too (never `Scripts/` itself, never a folder that existed before install).
- Dependencies uv installed from PyPI (for example fonttools) stay after uninstall: other extensions may share them, and the legacy installer also kept them. Sibling checkouts are detected only if their pyproject has a `[tool.fontlab-install]` table with a valid `id`; anything else (such as TypeRig) goes to uv.
- Case-sensitive plugin suffix upgrades refuse before writes when a distinct
  title-case bundle contains modified or unowned files, preserving its receipt.
  Unchanged managed bundles migrate normally; filesystem aliases remain supported.
- A legacy `install.vfpy` install of the same id is migrated first. Files it logged are removed; changed files are kept. If a kept file would collide with the new install, the install stops before it changes anything. Shared legacy tools (`fontlab_install.py`, `Scripts/Extensions/`) are removed once no legacy install remains.

## Development

```sh
./test.sh        # requires uv and preinstalled matching CPython 3.11 for offline venv test
./build.sh       # wheel + sdist into dist/
./publish.sh     # tagged, clean tree only
```

Apache-2.0. `platformdirs.py` vendors part of platformdirs (MIT, notice kept).

## Target the running FontLab from a terminal

Install optional `fontlab-remopy` in the external CLI Python environment, then use
`fontlab-instamix --remote env`, `--remote pkg install uharfbuzz`,
`--remote pkg list`, `--remote pkg uninstall NAME`, `--remote ext install PATH`,
`--remote ext list`, `--remote ext uninstall ID`, or `--remote venv`.
`--remote --bridge /path/to/executable` selects one Remopy bridge executable.
The host supplies its Python version, architecture and data folder. A conflicting
`--data-dir` is refused; `FONTLAB_DATA_DIR` does not override the discovered host.

Each filesystem operation proves shared access with an owned temporary nonce file.
Long uv operations run externally in the qualified target interpreter, outside
FontLab's short remote deadline. Terminal and host architectures may differ;
the provider verifies the actual standalone interpreter. Same OS is required.
A timeout is never retried automatically and may leave partial installation data.
Cache-refresh failure reports completed installation separately; already imported
modules may need a later owner restart. The command does not restart FontLab.
Remote `--run-hooks` is refused because hooks need FontLab's execution context.
Windows/CrossOver routing and live native acceptance remain separate pending work.
