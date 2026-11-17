---
this_file: src_docs/md/develop.md
---

# Develop

FontLab 9 runs Python 3.11 inside the application. Your code reaches it through FontLab's data folder, which instamix calls `<data>`:

| Folder | What FontLab does with it |
| --- | --- |
| `<data>/Scripts/` | lists every `.py` and `.vfpy` file in the Scripts menu, by subfolder |
| `<data>/python/3.11/site-packages/` | adds it to `sys.path`, so `import mytools` works in scripts, plugins and the Python panel |
| `<data>/Extensions/<kind>/` | holds plugin bundles that `fontlabapp.plugins` loads at launch (see [Plugins](plugins.md)) |
| `<data>/Encoding/`, `<data>/Codepage/`, `<data>/Actions/`, `<data>/Data/` | encodings, codepages, actions and data files |

Run `fontlab-instamix env` to see the folder on your machine. Inside FontLab it reports `"in_fontlab": true`.

## Lay out a project

Keep scripts and the code they share in one repository:

```text
my-fontlab-tools/
  pyproject.toml
  install.vfpy              # instamix stub, written by `fontlab-instamix stub .`
  src/mytools/__init__.py   # importable package: shared code
  Scripts/MyTools/SayHello.py
  Extensions/reporters/NodeCount.fontlabReporter/   # optional plugin bundle
```

A script is a plain Python file. Start it with an `#FLM:` comment that names it, keep the logic in your package, and keep the script short:

```python
#FLM: Say Hello
import fontlab
from mytools import hello

package = fontlab.flWorkspace.instance().currentPackage
print(hello(), len(package.glyphs()) if package else "no font open")
```

## Install from the checkout

Add a `[tool.fontlab-install]` table to `pyproject.toml` (see [Package](package.md)) and install the checkout once:

```sh
uvx fontlab-python-instamix bootstrap .
```

Instamix links each file instead of copying it, so the installed script and package are your working files:

- **Scripts** read your current source every time you run them from the menu.
- **Package code** is cached once imported. Restart FontLab after you change it.
- **Plugin bundles** load at launch. Restart FontLab after you change them.

On Windows, or where a symlink fails, instamix copies. Run `bootstrap` again after each edit there. Use `--copy` to force copies on any system, for example to test what a user gets.

## Python dependencies

FontLab's Python has no `pip`. Do not run `pip` from `sys.executable`: inside FontLab that is the application, not a Python interpreter. Declare dependencies in `[project].dependencies` and let `bootstrap` install them, or install them by hand:

```sh
fontlab-instamix pkg install fonttools "git+https://github.com/owner/repo"
fontlab-instamix pkg list
```

Instamix fetches its own `uv` into `<data>/python/uv` when none is on `PATH` (`fontlab-instamix uv fetch`) and installs into `<data>/python/3.11/site-packages` for Python 3.11 on your platform. Environment markers in dependency strings are evaluated for Python 3.11 and the host system, not for the Python that runs instamix.

For an editor or a type checker, `fontlab-instamix venv` creates or verifies `<data>/.venv` for Python 3.11. New environments use a managed `.pth` to read the canonical package directory. An existing compatible environment with site-packages linked directly to that exact directory is reused without changing its files. Other escaping paths, mismatched runtimes and unrelated managed-path files are refused.

## Test without FontLab

Point every command at a scratch folder to see exactly which files an install places:

```sh
uvx fontlab-python-instamix --data-dir /tmp/fl bootstrap .
find /tmp/fl -type f
```

This proves the layout, not the behaviour. Run scripts and plugins in FontLab 9 before you release them: an offline check cannot show menus, drawing, Undo or the state of an open font.
