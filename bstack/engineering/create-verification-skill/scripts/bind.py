#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys


HOST_DIRECTORIES = {"claude": ".claude", "cursor": ".cursor", "grok": ".grok"}
SKILL_NAME = re.compile(r"verify-[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def inside_project(project: Path, path: Path) -> bool:
    return path.resolve().is_relative_to(project)


def plan(project: Path, name: str) -> list[tuple[Path, Path, str]]:
    project = project.resolve()
    if not SKILL_NAME.fullmatch(name):
        raise ValueError("Name must look like verify-my-app and contain only lowercase letters, digits, and dashes")
    state_path = project / ".bstack/config.json"
    if not state_path.is_file() or not inside_project(project, state_path):
        raise ValueError("BStack is not set up in this project; run setup-bstack here before binding a verifier")
    state = json.loads(state_path.read_text())
    hosts = state.get("hosts")
    if not isinstance(hosts, list) or any(host not in ("codex", *HOST_DIRECTORIES) for host in hosts):
        raise ValueError("BStack host settings are missing or invalid in .bstack/config.json")
    source = project / ".agents/skills" / name
    if not (source / "SKILL.md").is_file() or not inside_project(project, source):
        raise ValueError(f"Create .agents/skills/{name}/SKILL.md before binding it")

    links = []
    for host in hosts:
        if host == "codex":
            continue
        destination_dir = project / HOST_DIRECTORIES[host] / "skills"
        if not inside_project(project, destination_dir):
            raise ValueError(f"{destination_dir} points outside this project")
        if destination_dir.resolve() == (project / ".agents/skills").resolve():
            continue
        destination = destination_dir / name
        target = Path("../../.agents/skills") / name
        if destination.is_symlink() and destination.readlink() == target and destination.resolve() == source.resolve():
            status = "bound"
        elif destination.exists() or destination.is_symlink():
            raise ValueError(f"{destination} already exists and is not this verifier's link; resolve it manually")
        else:
            status = "missing"
        links.append((destination, target, status))
    return links


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        links = plan(args.project, args.name)
        if args.apply:
            created = []
            try:
                for destination, target, status in links:
                    if status != "missing":
                        continue
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    os.symlink(target, destination)
                    created.append(destination)
            except OSError:
                for destination in created:
                    destination.unlink()
                raise
        for destination, _, status in links:
            outcome = "created" if args.apply and status == "missing" else status
            print(f"{outcome}: {destination}")
        if not links:
            print("No host links needed; Codex uses .agents/skills directly")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Binding stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
