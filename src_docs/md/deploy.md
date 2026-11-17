---
this_file: src_docs/md/deploy.md
---

# Deploy

Deploying means placing a package in a FontLab data folder. Instamix does the same work from three places: a terminal, FontLab's Python panel and an `install.vfpy` that FontLab opens.

## The data folder

Instamix finds `<data>` in this order:

1. `--data-dir` on the command line
2. `$FONTLAB_DATA_DIR`
3. `fontlab.flPreferences().dataPathDefault`, inside FontLab
4. `~/Library/Application Support/FontLab/FontLab 9` on macOS, `Documents\FontLab\FontLab 9` on Windows

`fontlab-instamix env` prints the folder it chose, together with the Python version, platform and site-packages path.

## From a terminal

```sh
fontlab-instamix ext install dist/com.example.countglyphs.fontlabextz
fontlab-instamix ext install examples/com.example.hello.fontlabext --copy
fontlab-instamix bootstrap path/to/project
fontlab-instamix pkg install fonttools
```

`ext install` stores a copy of the extension in `Extensions/Library/` and links each file from that copy into place, so the source folder can be deleted afterwards. `--copy` copies the files instead of linking; Windows always copies. `bootstrap` links straight to the files in your checkout, so edits there take effect after a FontLab restart. `bootstrap` installs a project from its `[tool.fontlab-install]` table and prints, for example, `installed com.example.mytools (13 paths)`.

Restart FontLab after an install. FontLab reads Scripts, plugins and site-packages at launch.

## From FontLab's Python panel

```python
import fontlab_instamix as im
im.install("/path/to/com.example.countglyphs.fontlabextz")
im.install_project("/path/to/project")
im.installed()
im.uninstall("com.example.countglyphs")
```

Instamix must already be in FontLab's site-packages. Open `install.vfpy` from the instamix repository once, or let a project stub fetch it.

## With `install.vfpy`

Open a project's `install.vfpy` in FontLab with File > Open. The stub installs instamix if needed, installs the project and shows a message. This is the route for users who do not use a terminal.

## What gets written

For each install instamix writes:

- the package files in FontLab's folders: Scripts, Encoding, Codepage, Actions, Data, `Extensions/<kind>/` and `python/3.11/site-packages`
- `Extensions/Library/<id>.fontlabext`, holding the manifest
- `Extensions/.instamix/<id>.json`, a ledger of every placed path, and a line in `Extensions/.instamix/install.log`
- `Scripts/Instamix/List Extensions.py` and `Scripts/Instamix/Uninstall <id>.py`, so users can manage installs from the Scripts menu
- for a project, a `<name>-<version>.dist-info` folder whose `INSTALLER` reads `fontlab-instamix`

## Uninstall

```sh
fontlab-instamix ext uninstall com.example.mytools
```

Instamix removes the paths in the ledger. A file the user changed after the install stays in place and is reported. PyPI dependencies stay installed, because other packages may need them; remove them with `pkg uninstall`.

## Update

Install the new version over the old one. Instamix removes the files the old version placed, then places the new ones. If anything fails, it rolls back to the previous version.
