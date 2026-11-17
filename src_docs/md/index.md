---
this_file: src_docs/md/index.md
---

# FontLab Instamix

Instamix is the installer that FontLab 9 scripts, Python packages and plugins use to reach a user's FontLab. It is a stdlib-only Python package, so it runs inside FontLab's embedded Python 3.11 as well as from a terminal, and it records every file it places, so an uninstall removes exactly what it installed.

This site is a guide for FontLab developers. It follows one piece of work from the first line of code to a user's Scripts menu:

1. [Develop](develop.md) a script or a Python package against a live FontLab, with edits that take effect without reinstalling.
2. Write a [plugin](plugins.md): a reporter, filter, tool, palette or general extension that FontLab loads at launch.
3. [Package](package.md) the work as a `.fontlabext` extension or as a project with a `[tool.fontlab-install]` table.
4. [Deploy](deploy.md) it into a FontLab data folder from the command line, from FontLab's Python panel or with `install.vfpy`.
5. [Deliver](deliver.md) it to users as a zip, a Git repository or a PyPI release, and ship updates.

The [reference](reference.md) lists every command, manifest key and project key.

## Install Instamix

[Download install.vfpy](https://code.fontlab.com/fontlab-python-instamix/install.vfpy)
and open it with **File > Open** in FontLab 9.
It bootstraps Instamix without another Python package installer. The script is
distributed under the [project licence](assets/LICENSE).

## Two routes

| Route | You ship | Best for |
| --- | --- | --- |
| Extension | a `.fontlabext` folder or a `.fontlabextz` zip with a `manifest.fontlabextj` | scripts, encodings, codepages, actions and data files; no Python packaging |
| Project | a repository with `pyproject.toml`, a `[tool.fontlab-install]` table and an `install.vfpy` stub | Python packages, scripts and plugin bundles, with dependencies on PyPI or on other FontLab projects |

Both routes end in the same place. Instamix writes an extension record under `<data>/Extensions/Library/`, places the files in FontLab's folders and adds an uninstaller to the Scripts menu.

## Try it in two minutes

Every command takes `--data-dir`, so you can try instamix on a scratch folder without touching your FontLab:

```sh
git clone https://github.com/fontlabcom/fontlab-python-instamix
cd fontlab-python-instamix
uvx fontlab-python-instamix --data-dir /tmp/fl ext install examples/com.example.hello.fontlabext
uvx fontlab-python-instamix --data-dir /tmp/fl ext list
uvx fontlab-python-instamix --data-dir /tmp/fl ext uninstall com.example.hello
```

The first command prints `installed com.example.hello 1.0.0 (4 paths)`. The extension's script lands in `/tmp/fl/Scripts/com.example.hello/` and its encoding in `/tmp/fl/Encoding/com.example.hello/`.
