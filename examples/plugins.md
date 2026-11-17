---
this_file: examples/plugins.md
---
# Package a plugin draft

A draft must already follow the App plugin base-class contract. Instamix copies
its Python code unchanged; it never executes the draft or imports App to guess
its class. It validates the six metadata fields and entry-module location.
App separately verifies inheritance and matching class `name`, `title`, `kind`
when loading the installed plugin. Install a compatible App before using it;
Instamix does not install App as a packaging dependency.

```sh
fontlab-instamix wrap Demo.py --id com.example.demo --name 'Demo plugin' \
  --kind reporter --plugin-id Demo --entry Demo:Demo \
  --min-app-version 1.0.0 --version 1.0.0 --out dist --zip
```

The equivalent Python API is `fontlab_instamix.wrap.make_plugin(source, out_dir,
ext_id, plugin_id="Demo", name="Demo plugin", kind="reporter", entry="Demo:Demo",
min_app_version="1.0.0", version="1.0.0")`, with `Path` arguments. Extension ID is
lowercase reverse-DNS; plugin ID retains the class's stable identifier.

Kinds are reporter, filter, tool, palette and general. The generated layout is
`com.example.demo.fontlabext/Extensions/reporters/Demo.fontlabreporter/`, containing
`plugin.json` and `Demo.py`. Other kinds use filters/tools/palettes/general and
lowercase `.fontlabfilter`, `.fontlabtool`, `.fontlabpalette`, `.fontlabgeneral`.
The outer manifest targets the kind folder, preserving that same parent inside
the installed Library source. An existing bundle retains its stem, code and
licence; only its canonical suffix changes. Its existing plugin.json must agree
with all six explicit metadata values and is copied unchanged.

Supply a directory for multiple files or relative imports, using entries such as
`pkg.demo:Demo` or `pkg:Demo` for a package with `__init__.py`. Its contents become
the bundle contents. Source links must stay inside that directory. Outputs must
be outside it, and an existing output bundle is never replaced. This operation
does not adapt an arbitrary script into a plugin; use plain `wrap` for scripts.

# Select and install extensions inside FontLab

```python
from fontlab_instamix import gui
records = gui.install_selected()             # multiple ZIPs or root manifests
records = gui.install_selected(folder=True)  # one .fontlabext directory
```

`pick_files()` returns a list of paths; `pick_file()` and `pick_folder()` return
one path or an empty string. Cancellation installs nothing. Without PythonQt,
multiple selection reads one literal path per line, ending with a blank line.
Paths may contain spaces and commas; do not quote them or enter CSV.

`install_selected(["/path/one.fontlabextz", "/path/two/manifest.fontlabextj"],
data=Path("/scratch/FontLab 9"))` bypasses dialogs and uses the public extension
installer. A failure prints its path and error, then remaining selections
continue. Returned records contain successful installations only; status reports
always print. If a multi-extension archive fails partway through, successful
records from that archive are included too. Direct `extension.install` callers
still receive the original exception, with its `installed_records` attribute
listing earlier committed extensions. Native dialog behavior still needs
qualification in FontLab.
