---
this_file: README.md
---
# fontlab-python-instamix

Installs extensions, scripts and Python packages into FontLab 9. Stdlib only,
runs inside FontLab's embedded Python 3.11 and from an ordinary terminal.

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

## Two-line install.vfpy for other projects

```python
#FLM: Install this project into FontLab
import fontlab_instamix.bootstrap as b  # missing? open fontlab-python-instamix/install.vfpy in FontLab first
b.install_project(__file__)
```

If instamix is not installed yet, FontLab raises `ModuleNotFoundError:
fontlab_instamix`. Get it by opening `fontlab-python-instamix/install.vfpy` in
FontLab once. To also work from a sibling checkout, replace the first line with:

```python
try: import fontlab_instamix.bootstrap as b
except ImportError:
    import sys, pathlib; sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "fontlab-python-instamix" / "src"))
    try: import fontlab_instamix.bootstrap as b
    except ImportError: raise SystemExit("fontlab-instamix missing: open fontlab-python-instamix/install.vfpy in FontLab first")
```

`install_project` reads `[tool.fontlab-install]`:

```toml
[tool.fontlab-install]
id = "com.example.tool"           # required, reverse-DNS
name = "Tool"
packages = ["src/tool"]           # linked into site-packages (editable)
scripts = ["Scripts"]             # default: Scripts/ if present
extensions = "Extensions"         # .fontlabext folders inside are installed too
dependencies = ["fontlab-fly>=1"] # sibling checkouts with install.vfpy first, else uv
```

## Development

```sh
./test.sh        # uv run --with pytest pytest -q
./build.sh       # wheel + sdist into dist/
./publish.sh     # tagged, clean tree only
```

Apache-2.0. `platformdirs.py` vendors part of platformdirs (MIT, notice kept).
