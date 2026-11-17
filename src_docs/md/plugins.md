---
this_file: src_docs/md/plugins.md
---

# Plugins

A plugin is a folder bundle that FontLab loads at launch through the `fontlabapp.plugins` framework of [fontlab-fontlabapp](https://github.com/fontlabcom/fontlab-fontlabapp). The bundle's name ends in its kind, and it lives in the matching `<data>/Extensions/` subfolder:

| Kind | Folder | Bundle suffix | Base class |
| --- | --- | --- | --- |
| `reporter` | `reporters` | `.fontlabReporter` | `Reporter` |
| `filter` | `filters` | `.fontlabFilter` | `Filter` |
| `tool` | `tools` | `.fontlabTool` | `Tool` |
| `palette` | `palettes` | `.fontlabPalette` | `Palette` |
| `general` | `general` | `.fontlabGeneral` | `General` |

[fontlab-python-plugmix](https://github.com/fontlabcom/fontlab-python-plugmix) holds working examples of each kind.

## A reporter bundle

```text
Extensions/reporters/NodeCount.fontlabReporter/
  plugin.json
  node_count.py
```

`plugin.json` declares the plugin:

```json
{
  "id": "node_count",
  "name": "Node Count",
  "kind": "reporter",
  "version": "1.0.0",
  "entry": "node_count:NodeCount",
  "min_app_version": "1.2.10"
}
```

- `id`, `name` and `kind` must match the class's `name`, `title` and kind. Ids are unique across all kinds.
- `version` has three parts.
- `entry` is `module:Class`; the module sits inside the bundle. The bundle needs no `__init__.py`.
- `min_app_version` is the lowest `fontlab-fontlabapp` version the plugin needs.

The class receives an immutable snapshot of the glyph and returns marks to draw:

```python
from fly.ap.plugins.reporter import Mark, Reporter
from fly.ap.plugins.snapshot import GlyphSnapshot


class NodeCount(Reporter):
    """Write the node count of each contour at its first node."""

    name = "node_count"
    title = "Node Count"

    def compute(self, snapshot: GlyphSnapshot) -> list[Mark]:
        marks = []
        for contour in snapshot.contours:
            if contour.nodes:
                first = contour.nodes[0]
                marks.append(Mark("text", ((first.x, first.y),), (56, 217, 137), text=str(len(contour.nodes))))
        return marks
```

## How bundles are installed and loaded

Point `extensions` in `[tool.fontlab-install]` at the folder that holds the kind subfolders, and declare the framework as a dependency:

```toml
[tool.fontlab-install]
id = "com.example.mytools"
name = "my-fontlab-tools"
extensions = "Extensions"
dependencies = ["fontlab-fontlabapp>=1.2.10", "fontlab-fly>=1.3.0"]
```

`bootstrap` links each bundle that holds a `plugin.json` to `<data>/Extensions/<kind>/<Name>.fontlab<Kind>`. At launch, `fontlabapp.plugins` discovers the bundles, imports their entry modules and registers them with FontLab's interface. A bundle with an invalid manifest or a failing import is logged and skipped; the other plugins still load.

Plugin code is trusted Python that runs in FontLab with full access. Restart FontLab to load a changed bundle.
