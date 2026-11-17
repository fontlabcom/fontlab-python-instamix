---
this_file: src_docs/md/deliver.md
---

# Deliver

Delivery is how a user gets your package. Choose the channel by who your users are.

## A zip for anyone

Send a `.fontlabextz` file. A user with instamix installs it from the Python panel:

```python
import fontlab_instamix as im
im.install("/path/to/com.example.countglyphs.fontlabextz")
```

or from a terminal with `uvx fontlab-python-instamix ext install com.example.countglyphs.fontlabextz`. Attach the zip to a GitHub release so each version has a stable download.

## A Git repository

Commit `pyproject.toml` with its `[tool.fontlab-install]` table and the `install.vfpy` stub. Users download or clone the repository and open `install.vfpy` in FontLab. The stub fetches instamix from PyPI when it is missing, so the user needs nothing else.

Developers who clone the repository get links instead of copies, so a pull and a FontLab restart bring in the new code.

## PyPI

Publish the project as a normal Python distribution when other packages depend on it. Other projects then list it in `dependencies`, and instamix installs it with uv into FontLab's site-packages. Users can also install it directly:

```sh
uvx fontlab-python-instamix pkg install fontlab-my-tools
```

`pkg install` places only the Python distribution. Scripts and plugins are installed by `bootstrap` from a checkout or by the project's `install.vfpy`.

## Release checklist

1. Bump the version: tag the commit with hatch-vcs, or edit `[project].version` or the manifest `version`.
2. Install into a scratch folder with `--data-dir` and check the printed path count.
3. Install into your own FontLab, restart and run each script and plugin.
4. Uninstall and check that nothing is left behind except files you changed.
5. Build the deliverable: `wrap … --zip`, or `uv build` for PyPI.
6. Publish the zip on a GitHub release or the distribution on PyPI, and update the `install.vfpy` stub if instamix changed.

## Supporting users

Ask users for the output of `fontlab-instamix env` and the list from Scripts > Instamix > List Extensions. The install log in `<data>/Extensions/.instamix/install.log` records each install and uninstall with its time and version.
