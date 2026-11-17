---
this_file: src_docs/md/reference.md
---

# Reference

## Command line

Run `uvx fontlab-python-instamix`, `fontlab-instamix` after installing, or `python -m fontlab_instamix`. Every command takes `--data-dir`.

| Command | Does |
| --- | --- |
| `env` | print Python, platform and FontLab folders as JSON |
| `ext install PATH… [--copy] [--run-hooks]` | install `.fontlabext` folders or `.fontlabextz` zips |
| `ext list` | list installed extensions: id, version and name, tab-separated |
| `ext uninstall ID…` | uninstall extensions by id |
| `pkg install SPEC… [--upgrade]` | install PyPI or `git+` packages with uv |
| `pkg list` | list installed distributions |
| `pkg uninstall NAME…` | remove packages installed with `pkg install` |
| `wrap SOURCE --id ID [--name N] [--version V] [--out DIR] [--zip]` | wrap a script or folder into a `.fontlabext` |
| `bootstrap [PROJECT] [--copy]` | install a project checkout from its `[tool.fontlab-install]` |
| `uv fetch` | find uv or download it into `<data>/python/uv` |
| `venv` | create `<data>/.venv` for Python 3.11 |
| `stub FOLDER… [--force]` | write the `install.vfpy` stub into repository folders |

Instamix runs uv as a separate program. It never runs `sys.executable`, which inside FontLab is FontLab itself.

## Python API

```python
import fontlab_instamix as im
im.install(path)           # a .fontlabext folder or .fontlabextz zip
im.uninstall(ext_id)       # returns the paths kept because they changed
im.installed()
im.install_project(path)   # a project checkout or its install.vfpy
im.data_dir()
```

## Manifest keys (`manifest.fontlabextj`)

| Key | Meaning |
| --- | --- |
| `id` | reverse-DNS id, matching the folder name |
| `name` | display name |
| `version` | version string |
| `min_fontlab` | minimum FontLab version |
| `description` | short description |
| `python` | `requires` (PEP 508 list) and `packages` (folders) |
| `vars` | values for `{var}` in destinations |
| `install` | list of `{"from": …, "to": …}` entries |

## Project keys (`[tool.fontlab-install]`)

| Key | Meaning |
| --- | --- |
| `id` | required reverse-DNS id |
| `name` | distribution name, used for the dist-info folder |
| `packages` | package folders for site-packages |
| `scripts` | folder of Scripts menu folders |
| `extensions` | folder of plugin bundles |
| `dependencies` | PEP 508 requirements, from PyPI or sibling checkouts |
| `init-script` | add the `fontlabapp.plugins` startup block to `<data>/initScript.py`; on by default only for `com.fontlab.fontlabapp` |

## Plugin bundle (`plugin.json`)

| Key | Meaning |
| --- | --- |
| `id` | unique across kinds; matches the class `name` |
| `name` | title; matches the class `title` |
| `kind` | `reporter`, `filter`, `tool`, `palette` or `general` |
| `version` | three-part version |
| `entry` | `module:Class` inside the bundle |
| `min_app_version` | minimum fontlabapp version |
