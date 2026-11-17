# this_file: src/fontlab_instamix/remote.py
"""Short host probes; installation stays in the external CLI process."""

from __future__ import annotations

import json
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

from . import env

PROBE = """
import platform, sys
from pathlib import Path
import fontlab
_data = fontlab.flPreferences().dataPathDefault
_data = _data() if callable(_data) else _data
if not _data:
    raise ValueError('FontLab returned no data folder')
_version = str(sys.version_info.major) + '.' + str(sys.version_info.minor)
result = dict(python=_version, implementation=sys.version.split()[0],
              platform=sys.platform, machine=platform.machine(), data_dir=str(_data),
              site_packages=str(Path(str(_data)) / 'python' / _version / 'site-packages'),
              in_fontlab=True)
"""
READ_MARKER = (
    "from pathlib import Path\nresult = Path(marker).read_text(encoding='utf-8')"
)
REFRESH = "import importlib\nimportlib.invalidate_caches()\nresult = True"


def facts(value: object) -> tuple[dict, env.Target]:
    """Reject incomplete or inconsistent host facts before touching disk."""
    keys = (
        "python",
        "implementation",
        "platform",
        "machine",
        "data_dir",
        "site_packages",
    )
    if not isinstance(value, dict) or any(
        not isinstance(value.get(k), str) or not value[k] for k in keys
    ):
        raise ValueError("malformed FontLab environment facts")
    target = env.Target(value["python"], value["platform"], value["machine"])
    # Parse foreign host paths without applying this CLI's filesystem semantics.
    from pathlib import PurePosixPath, PureWindowsPath

    path_type = PureWindowsPath if target.platform == "win32" else PurePosixPath
    data = path_type(value["data_dir"])
    if (
        not data.is_absolute()
        or path_type(value["site_packages"])
        != data / "python" / target.version / "site-packages"
    ):
        raise ValueError("malformed FontLab data folder or canonical site-packages")
    return value, target


def shared_path(client, data: Path) -> None:
    """Prove the host sees one unique owned file; never create the data root."""
    token = secrets.token_hex(32)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix=".instamix-probe-", dir=data, delete=False
    ) as stream:
        marker = Path(stream.name)
        stream.write(token)
    try:
        if client.run(READ_MARKER, marker=str(marker)).value != token:
            raise ValueError(
                "FontLab shared-filesystem nonce mismatch; refusing local operation"
            )
    finally:
        marker.unlink()


def execute(args) -> int:
    """Route the supported CLI commands using validated host facts."""
    if args.command not in ("env", "pkg", "ext", "venv"):
        raise ValueError(f"--remote does not support {args.command}")
    if getattr(args, "run_hooks", False):
        raise ValueError(
            "--remote --run-hooks is unsupported: hooks need FontLab execution context; submit them inside FontLab separately"
        )
    try:
        from fontlab_remopy import FontLab
    except ImportError as error:
        raise RuntimeError(
            "Remote CLI requires fontlab-remopy in this external Python environment"
        ) from error
    try:
        with FontLab(command=args.bridge) as client:
            value, target = facts(client.run(PROBE).value)
            if args.data_dir and Path(args.data_dir).expanduser() != Path(
                value["data_dir"]
            ):
                raise ValueError(
                    "--data-dir conflicts with the running FontLab data folder"
                )
            if args.command == "env":
                print(json.dumps(value, indent=2))
                return 0
            if target.platform != sys.platform:
                raise ValueError(
                    "remote installation requires the same OS; Windows/CrossOver execution is not implemented"
                )
            data = Path(value["data_dir"])
            shared_path(client, data)
            args.data_dir, args.target = str(data), target
            # All provider work, including bounded uv subprocesses, runs here.
            status = args.func(args)
            if args.command == "venv" or getattr(args, "action", None) in (
                "install",
                "uninstall",
            ):
                try:
                    if client.run(REFRESH).value is not True:
                        raise RuntimeError("host did not confirm cache invalidation")
                except Exception as error:  # noqa: BLE001 - optional transport errors retain unknown outcomes
                    print(
                        f"fontlab-instamix: local operation completed; host cache refresh failed or is unknown: {error}. Do not reinstall; imported modules may require a later owner restart.",
                        file=sys.stderr,
                    )
                    return 1
            return status
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"external installer timed out; partial local changes may remain; no automatic retry. stderr: {error.stderr!r}"
        ) from error
    except (ValueError, OSError, RuntimeError):
        raise
    except Exception as error:
        raise RuntimeError(
            f"remote operation failed or has unknown outcome: {error}; no automatic retry; inspect any partial local changes"
        ) from error
