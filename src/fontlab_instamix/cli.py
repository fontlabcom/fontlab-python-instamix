# this_file: src/fontlab_instamix/cli.py
"""``fontlab-instamix`` command line (also ``python -m fontlab_instamix``)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, bootstrap, env, extension, packages, stub, uv, venv, wrap


def _data(args) -> Path:
    return env.data_dir(args.data_dir)


def _target(args) -> dict:
    return {"target": args.target} if getattr(args, "target", None) else {}


def cmd_env(args) -> int:
    print(json.dumps(env.describe(_data(args)), indent=2))
    return 0


def cmd_ext_install(args) -> int:
    data = _data(args)
    for path in args.paths:
        for record in extension.install(Path(path), data, copy=args.copy or None, run_hooks=args.run_hooks, **_target(args)):
            print(f"installed {record['id']} {record['version']} ({len(record['entries'])} paths)")
    return 0


def cmd_ext_uninstall(args) -> int:
    data = _data(args)
    for ext_id in args.ids:
        kept = extension.uninstall(ext_id, data)
        print(f"uninstalled {ext_id}")
        for path in kept:
            print(f"  kept changed path: {path}")
    return 0


def cmd_ext_list(args) -> int:
    for record in extension.installed(_data(args)):
        print(f"{record['id']}\t{record['version']}\t{record['name']}")
    return 0


def cmd_pkg_install(args) -> int:
    data = _data(args)
    result = packages.install(data, args.specs, upgrade=args.upgrade, **_target(args))
    print((result.stdout or "").strip() or "done")
    return 0


def cmd_pkg_uninstall(args) -> int:
    data = _data(args)
    for name in args.names:
        removed = packages.uninstall(data, name, **_target(args))
        print(f"removed {name} ({len(removed)} files)")
    return 0


def cmd_pkg_list(args) -> int:
    for name, version in packages.listed(_data(args), **_target(args)):
        print(f"{name}\t{version}")
    return 0


def cmd_wrap(args) -> int:
    source = Path(args.source)
    ext_id = args.id or f"com.example.{wrap.slug(source.stem)}"
    plugin_options = (args.plugin_id, args.entry, args.min_app_version)
    if args.kind:
        if not all(plugin_options) or not args.name:
            raise ValueError(
                "plugin wrapping requires --plugin-id, --name, --entry and --min-app-version"
            )
        folder = wrap.make_plugin(
            source,
            Path(args.out),
            ext_id,
            name=args.name,
            version=args.version,
            kind=args.kind,
            plugin_id=args.plugin_id,
            entry=args.entry,
            min_app_version=args.min_app_version,
        )
    else:
        if any(plugin_options):
            raise ValueError("plugin metadata requires --kind")
        folder = wrap.make_folder(
            source, Path(args.out), ext_id, name=args.name, version=args.version
        )
    print(folder)
    if args.zip:
        print(wrap.make_zip([folder], folder.with_suffix(".fontlabextz")))
    return 0


def cmd_pack(args) -> int:
    print(wrap.make_zip([Path(folder) for folder in args.folders], Path(args.out)))
    return 0


def cmd_bootstrap(args) -> int:
    for record in bootstrap.install_project(Path(args.project), args.data_dir, copy=args.copy or None):
        print(f"installed {record['id']} ({len(record['entries'])} paths)")
    return 0


def cmd_uv_fetch(args) -> int:
    data = _data(args)
    print(uv.download(data, args.version) if args.force else uv.ensure(data))
    return 0


def cmd_venv(args) -> int:
    data = _data(args)
    print(venv.create(data, uv.ensure(data), **_target(args)))
    return 0


def cmd_stub(args) -> int:
    for folder in args.folders:
        print(f"wrote {stub.write(Path(folder), force=args.force)}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fontlab-instamix", description="Install extensions and packages into FontLab 9.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--data-dir", help=f"FontLab data folder (default: ${env.DATA_ENV} or FontLab's own)")
    p.add_argument("--remote", action="store_true", help="target the running FontLab through optional Remopy")
    p.add_argument("--bridge", help="Remopy bridge executable (requires --remote)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("env", help="show Python, platform and FontLab folders").set_defaults(func=cmd_env)

    ext = sub.add_parser("ext", help="manage .fontlabext extensions").add_subparsers(dest="action", required=True)
    s = ext.add_parser("install", help="install .fontlabext folders or .fontlabextz zips")
    s.add_argument("paths", nargs="+")
    s.add_argument("--copy", action="store_true", help="copy files instead of symlinking")
    s.add_argument("--run-hooks", action="store_true", help="run install*.vfpy hooks found in zips")
    s.set_defaults(func=cmd_ext_install)
    s = ext.add_parser("uninstall", help="uninstall extensions by id")
    s.add_argument("ids", nargs="+")
    s.set_defaults(func=cmd_ext_uninstall)
    ext.add_parser("list", help="list installed extensions").set_defaults(func=cmd_ext_list)

    pkg = sub.add_parser("pkg", help="manage Python packages in FontLab's site-packages").add_subparsers(
        dest="action", required=True
    )
    s = pkg.add_parser("install", help="install PyPI or git+ packages with uv")
    s.add_argument("specs", nargs="+")
    s.add_argument("--upgrade", action="store_true")
    s.set_defaults(func=cmd_pkg_install)
    s = pkg.add_parser("uninstall", help="remove packages installed with pkg install")
    s.add_argument("names", nargs="+")
    s.set_defaults(func=cmd_pkg_uninstall)
    pkg.add_parser("list", help="list installed distributions").set_defaults(func=cmd_pkg_list)

    s = sub.add_parser("wrap", help="wrap a script or folder into a .fontlabext")
    s.add_argument("source")
    s.add_argument("--id")
    s.add_argument("--name")
    s.add_argument("--version", default="0.1.0")
    s.add_argument("--out", default=".")
    s.add_argument("--zip", action="store_true", help="also write a .fontlabextz")
    s.add_argument(
        "--kind",
        choices=wrap.PLUGIN_KINDS,
        help="package an App-compatible plugin draft",
    )
    s.add_argument(
        "--plugin-id",
        help="stable plugin class identifier, separate from extension --id",
    )
    s.add_argument("--entry", help="plugin module:Class")
    s.add_argument("--min-app-version", help="minimum App three-part release version")
    s.set_defaults(func=cmd_wrap)

    s = sub.add_parser("pack", help="pack extension folders into one .fontlabextz")
    s.add_argument("folders", nargs="+")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_pack)

    s = sub.add_parser("bootstrap", help="install a project checkout using its [tool.fontlab-install]")
    s.add_argument("project", nargs="?", default=".")
    s.add_argument("--copy", action="store_true")
    s.set_defaults(func=cmd_bootstrap)

    uvp = sub.add_parser("uv", help="manage instamix's uv").add_subparsers(dest="action", required=True)
    s = uvp.add_parser("fetch", help="find uv or download it into <data>/python/uv")
    s.add_argument("--version", help="uv release tag, e.g. 0.9.0 (default: latest)")
    s.add_argument("--force", action="store_true", help="download even if uv is found")
    s.set_defaults(func=cmd_uv_fetch)

    sub.add_parser("venv", help="create <data>/.venv for Python 3.11").set_defaults(func=cmd_venv)

    s = sub.add_parser("stub", help="write the instamix install.vfpy stub into repo folders")
    s.add_argument("folders", nargs="+")
    s.add_argument("--force", action="store_true", help="replace an existing install.vfpy")
    s.set_defaults(func=cmd_stub)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.remote:
            from . import remote

            return remote.execute(args)
        if args.bridge:
            raise ValueError("--bridge requires --remote")
        return args.func(args)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"fontlab-instamix: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
