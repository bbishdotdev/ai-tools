#!/usr/bin/env python3
"""Install the bundled bstack release and verify the installed project."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--hosts", nargs="+",
                        help="Configure selected hosts; omit to preserve an existing installation")
    args = parser.parse_args(argv)
    project = args.project.expanduser().resolve()
    installer = Path(__file__).resolve().parent / "scripts/install.py"
    command = [sys.executable, "-B", str(installer), "--project", str(project)]
    if args.hosts is not None:
        command.extend(["--hosts", *args.hosts])
    try:
        installed = subprocess.run(command, text=True, capture_output=True, check=False)
        if installed.returncode:
            sys.stderr.write(installed.stdout + installed.stderr)
            return installed.returncode
        installation = json.loads(installed.stdout)
        controller = project / ".bstack/package/scripts/bstack.py"
        checked = subprocess.run([sys.executable, "-B", str(controller), "doctor", "--project", str(project)],
                                 text=True, capture_output=True, check=False)
        if checked.returncode:
            print("bstack installation completed, but verification failed.", file=sys.stderr)
            sys.stderr.write(checked.stdout + checked.stderr)
            return checked.returncode
        health = json.loads(checked.stdout)
        if not health.get("installed") or any(health.get(key) != "passed" for key in ("bindings", "package_integrity")):
            raise ValueError("doctor did not confirm the installed package and bindings")
        print(json.dumps({**installation, "status": "installed", "doctor": health}, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(f"bstack setup failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
