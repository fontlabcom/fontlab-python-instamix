---
this_file: README.md
---
# fontlab-python-instamix

Installs extensions, scripts and Python packages into FontLab 9. Stdlib only,
runs inside FontLab's embedded Python 3.11 and from an ordinary terminal.

Documentation: <https://code.fontlab.com/fontlab-python-instamix/>

- **Extensions**: `.fontlabext` folders and `.fontlabextz` zips are copied to
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

Open `install.vfpy` from this repository in FontLab 9 (File > Open). From a
git checkout it symlinks `src/fontlab_instamix` into
`<data>/python/3.11/site-packages` (edits are live after a restart); otherwise
it copies the package. Then in FontLab's Python panel:

```python
import fontlab_instamix as im
im.install("/path/to/com.example.hello.fontlabextz")
im.uninstall("com.example.hello")
```

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

## Stub install.vfpy for other projects

`fontlab-instamix stub DIR` writes the standard 40-line `install.vfpy` into a
project folder (`--force` replaces an existing one; the template is
`stub/install.vfpy`). When opened in FontLab it gets instamix in this order:
an installed copy, a sibling `../fontlab-python-instamix` checkout copied into
site-packages, or the PyPI wheel (sha256 checked, only `fontlab_instamix/`
extracted). Then it calls `bootstrap.install_project(__file__)`.

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
- A legacy `install.vfpy` install of the same id is migrated first. Files it logged are removed; changed files are kept. If a kept file would collide with the new install, the install stops before it changes anything. Shared legacy tools (`fontlab_install.py`, `Scripts/Extensions/`) are removed once no legacy install remains.

## Development

```sh
./test.sh        # uv run --with pytest pytest -q
./build.sh       # wheel + sdist into dist/
./publish.sh     # tagged, clean tree only
```

Apache-2.0. `platformdirs.py` vendors part of platformdirs (MIT, notice kept).
