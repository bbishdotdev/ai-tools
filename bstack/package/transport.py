#!/usr/bin/env python3
"""Install the reviewed bstack archive carried by the install-bstack skill."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import zipfile

MAX_FILES = 4096
MAX_BYTES = 128 * 1024 * 1024
HOSTS = ("codex", "claude", "cursor", "grok")


class InvalidBundle(ValueError):
    pass


def checked_path(value):
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or "\x00" in value or value.startswith("/")
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise InvalidBundle(f"Unsafe bundle path: {value!r}")
    return PurePosixPath(value)


def checked_bundle(archive):
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        if len(members) > MAX_FILES or sum(member.file_size for member in members) > MAX_BYTES:
            raise InvalidBundle("Bundle exceeds installation size limits")
        contents, modes = {}, {}
        for member in members:
            name = str(checked_path(member.filename))
            if name in contents:
                raise InvalidBundle(f"Duplicate archive path: {name}")
            mode = member.external_attr >> 16
            if member.is_dir() or stat.S_IFMT(mode) != stat.S_IFREG or mode & 0o7000:
                raise InvalidBundle(f"Bundle entry must be a regular file: {name}")
            contents[name] = source.read(member)
            modes[name] = stat.S_IMODE(mode)
    try:
        manifest = json.loads(contents["manifest.json"])
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InvalidBundle("Bundle needs a valid manifest.json") from error
    if (not isinstance(manifest, dict) or manifest.get("schema_version") != 2
            or manifest.get("name") != "bstack" or not isinstance(manifest.get("public_skills"), dict)):
        raise InvalidBundle("Unsupported bstack bundle manifest")
    if modes["manifest.json"] != 0o644:
        raise InvalidBundle("Bundle manifest must use mode 0644")
    records = manifest.get("files")
    if not isinstance(records, list):
        raise InvalidBundle("Bundle manifest needs a files array")
    expected = {"manifest.json"}
    for record in records:
        if not isinstance(record, dict):
            raise InvalidBundle("Invalid bundle file record")
        name = str(checked_path(record.get("path")))
        if name in expected:
            raise InvalidBundle(f"Duplicate manifest path: {name}")
        expected.add(name)
        mode, checksum = record.get("mode"), record.get("sha256")
        if (type(mode) is not int or not 0 <= mode <= 0o777
                or not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum)):
            raise InvalidBundle(f"Invalid bundle file metadata: {name}")
        if name not in contents:
            raise InvalidBundle(f"Missing bundle file: {name}")
        if hashlib.sha256(contents[name]).hexdigest() != checksum or modes[name] != mode:
            raise InvalidBundle(f"Bundle content or mode changed: {name}")
    if expected != set(contents):
        raise InvalidBundle("Unlisted bundle files: " + ", ".join(sorted(set(contents) - expected)))
    entrypoints = manifest.get("entrypoints")
    if (not isinstance(entrypoints, dict) or entrypoints.get("controller") != "scripts/bstack.py"
            or "scripts/bstack.py" not in expected):
        raise InvalidBundle("Bundle controller must be the reviewed scripts/bstack.py")
    return manifest, contents, modes


def install(archive, project, hosts):
    manifest, contents, modes = checked_bundle(archive)
    with tempfile.TemporaryDirectory(prefix="bstack-transport-") as scratch:
        staged = Path(scratch)
        for name, data in contents.items():
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(modes[name])
        command = [sys.executable, str(staged / manifest["entrypoints"]["controller"]),
                   "install", "--project", str(project.resolve()), "--hosts", *hosts]
        return subprocess.run(command, check=False).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--hosts", nargs="+", choices=HOSTS, default=list(HOSTS))
    args = parser.parse_args(argv)
    archive = Path(__file__).resolve().parents[1] / "assets/bstack.zip"
    try:
        return install(archive, args.project, list(dict.fromkeys(args.hosts)))
    except (InvalidBundle, OSError, zipfile.BadZipFile, RuntimeError) as error:
        print(f"bstack installation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
