---
this_file: src_docs/md/package.md
---

# Package

Instamix accepts two kinds of package. Pick the extension format for plain files and the project format for anything that ships a Python package or depends on one.

## Extension: `.fontlabext`

An extension is a folder named with a reverse-DNS id, such as `com.example.hello.fontlabext`. It holds a `manifest.fontlabextj` at its root and the files the manifest names:

```text
com.example.hello.fontlabext/
├── manifest.fontlabextj
├── scripts/
│   └── Hello.py
└── encoding/
    └── hello.enc
```

```json
{"id": "com.example.hello", "name": "Hello", "version": "1.0.0",
 "min_fontlab": "9.0",
 "install": [{"from": "scripts", "to": "Scripts/{}"},
             {"from": "encoding/*.enc", "to": "Encoding/{}"}]}
```

Each `install` entry copies or links the files under `from` into `to`. A destination starts with a target: `Scripts`, `Actions`, `Codepage`, `Data`, `Encoding` or `site-packages`, in any case. `.` is the target root, `{}` is the extension name without `.fontlabext`, and `{var}` is a value from the manifest's `vars`. Unknown variables, unknown targets, `..` and unknown manifest keys (other than `this_file`) are errors, so a typo fails the install instead of placing files in the wrong folder.

A manifest can also name Python packages and requirements:

```json
"python": {"requires": ["fonttools>=4"], "packages": ["src/hello"]}
```

### Wrap a single script

You do not need to write the manifest by hand for a script:

```sh
fontlab-instamix wrap CountGlyphs.py --id com.example.countglyphs \
    --name "Count Glyphs" --version 1.0.0 --out dist --zip
```

This writes `dist/com.example.countglyphs.fontlabext` with the script under `scripts/` and a manifest that installs it into `Scripts/com.example.countglyphs/`. `--zip` also writes `dist/com.example.countglyphs.fontlabextz`. `wrap` accepts `.py` and `.vfpy` files, or a folder of them.

### Zip: `.fontlabextz`

A `.fontlabextz` is a zip that holds one or more `.fontlabext` folders. Use it to send extensions as one file. Instamix refuses members with absolute paths, drive letters or `..`. An `install.vfpy` hook inside a zip runs only when the user passes `--run-hooks`.

## Project: `[tool.fontlab-install]`

A project is an ordinary Python repository. Add a table to `pyproject.toml`:

```toml
[project]
name = "fontlab-my-tools"
version = "0.2.0"

[tool.fontlab-install]
id = "com.example.mytools"
name = "fontlab-my-tools"
packages = ["src/mytools"]
scripts = "Scripts"
extensions = "Extensions"
dependencies = ["fonttools>=4.50"]
```

- `id` is required and must be reverse-DNS. It names the extension record and the uninstaller.
- `name` should be the distribution name from `[project].name`. Instamix uses it for the `<name>-<version>.dist-info` folder it writes into site-packages.
- `packages` lists package folders to place in `<data>/python/3.11/site-packages`.
- `scripts` is a folder whose subfolders become FontLab Scripts menu folders. `Scripts/MyTools/SayHello.py` installs as `Scripts/MyTools/SayHello.py`.
- `extensions` is a folder of [plugin bundles](plugins.md) (`<kind>/<Name>.fontlab<Kind>`).
- `dependencies` are PEP 508 requirements. Instamix installs them with uv, evaluating markers for Python 3.11 on the host system. A dependency on another FontLab project that is checked out beside yours is installed from that checkout.

Instamix skips `__pycache__`, `*.pyc`, `*.vfpyc` and `.DS_Store`. It reads the version from `[project].version`, a hatch-vcs version file, `PKG-INFO` or `git describe`, in that order.

### The `install.vfpy` stub

Users install a project by opening `install.vfpy` in FontLab. Write the stub with:

```sh
fontlab-instamix stub .
```

The stub is about 40 lines. It imports an installed instamix; if there is none, it uses a sibling `fontlab-python-instamix` checkout, or downloads the instamix wheel from PyPI and checks its SHA-256. Then it installs the project and shows a message with the id and version. Commit the stub; rerun `stub --force` to update it.

## Which to choose

| Need | Format |
| --- | --- |
| One script or a few | `wrap` → `.fontlabextz` |
| Encodings, codepages, actions, data files | extension with a manifest |
| A Python package for other scripts to import | project |
| Plugins (reporters, filters, tools, palettes) | project with `extensions` |
| Dependencies from PyPI or other FontLab projects | project |
