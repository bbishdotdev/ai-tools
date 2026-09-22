#!/usr/bin/env python3
"""Read workflow configuration without creating or upgrading a workspace."""

import argparse
import json
from pathlib import Path
import re
import sys

# Importing the bundled workspace must not create bytecode beside installed files.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from wayfinder.core import DomainError, _git_location, _read_metadata, canonical


ADAPTERS = {"native", "codex", "claude", "cursor", "grok"}
AREAS = {"wayfinder", "tickets"}
MAX_CONFIG_BYTES = 65536


def fail(code, message, **details):
    raise DomainError(code, message, **details)


def present(path):
    return path.exists() or path.is_symlink()


def workspace_root(project):
    project = Path(project).resolve()
    if not project.is_dir():
        fail("workspace_missing", "Project directory does not exist")
    git = _git_location(project)
    root = git[0] if git else project
    binding = git[1] / "bstack-wayfinder.json" if git else root / ".bstack/workspace/metadata.json"
    if not present(binding):
        if git and present(root / ".bstack/workspace/metadata.json"):
            fail("workspace_missing", "Workspace metadata has no Git binding; explicit recovery is required")
        return root, None
    metadata = _read_metadata(binding)
    root = Path(metadata["root"])
    if root.resolve() != root or (not git and root != project):
        fail("workspace_missing", "Workspace root does not match its binding")
    if git:
        root_git = _git_location(root)
        if root_git is None or root_git[1] != git[1]:
            fail("workspace_missing", "Workspace root no longer belongs to this Git repository")
    if _read_metadata(root / ".bstack/workspace/metadata.json") != metadata:
        fail("workspace_missing", "Workspace metadata does not match its Git binding")
    return root, metadata["id"]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate field")
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError("Invalid JSON constant")


def config(path, required=False):
    if not present(path):
        if required:
            fail("config_missing", "Autonomous grilling requires roles.json with two explicit model bindings")
        return None
    try:
        with path.open("rb") as stream:
            content = stream.read(MAX_CONFIG_BYTES + 1)
        if len(content) > MAX_CONFIG_BYTES:
            raise ValueError("Configuration is too large")
        value = json.loads(content.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=invalid_constant)
    except (OSError, ValueError, RecursionError):
        fail("config_invalid", f"{path.name} must be readable, valid JSON within 64 KiB")
    if not isinstance(value, dict) or type(value.get("version")) is not int or value["version"] != 1:
        fail("config_invalid", f"{path.name} must be an object with version 1")
    return value


def fields(value, allowed, required, label):
    if not isinstance(value, dict) or set(value) - allowed or required - set(value):
        fail("config_invalid", f"{label} has missing or unsupported fields")


def nonempty(value, label):
    if (not isinstance(value, str) or not value.strip() or len(value) > 256
            or any(ord(character) < 32 for character in value)):
        fail("config_invalid", f"{label} must be nonempty text without control characters, at most 256 characters")
    return value.strip()


def grilling_roles(directory, mode):
    if mode == "manual":
        return {"status": "not-required", "runtimeChecked": False}
    value = config(directory / "roles.json", required=True)
    fields(value, {"version", "grilling"}, {"version", "grilling"}, "roles.json")
    roles = value["grilling"]
    fields(roles, {"interviewer", "respondent"}, {"interviewer", "respondent"}, "grilling")
    bindings = {}
    for role in ("interviewer", "respondent"):
        binding = roles[role]
        fields(binding, {"adapter", "model", "effort"}, {"adapter", "model"}, f"grilling.{role}")
        adapter = binding["adapter"]
        if not isinstance(adapter, str) or adapter not in ADAPTERS:
            fail("config_invalid", f"grilling.{role}.adapter must name a supported CLI or native host")
        bindings[role] = {"adapter": adapter, "model": nonempty(binding["model"], f"grilling.{role}.model")}
        if "effort" in binding:
            bindings[role]["effort"] = nonempty(binding["effort"], f"grilling.{role}.effort")
    if bindings["interviewer"]["model"].casefold() == bindings["respondent"]["model"].casefold():
        fail("config_invalid", "Autonomous grilling requires two distinct model identities, even across adapters")
    return {"status": "configured", "bindings": bindings, "runtimeChecked": False}


def work_adapters(directory, area):
    value = config(directory / "adapters.json")
    if value is not None:
        fields(value, {"version", *AREAS}, {"version"}, "adapters.json")
    result = {}
    for selected in sorted(AREAS if area == "both" else {area}):
        explicit = value is not None and selected in value
        binding = value[selected] if explicit else {"provider": "local"}
        fields(binding, {"provider"}, {"provider"}, f"adapters.{selected}")
        provider = binding["provider"]
        if not isinstance(provider, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", provider):
            fail("config_invalid", f"adapters.{selected}.provider must be a lowercase provider name")
        if provider != "local":
            fail("provider_unsupported", f"The selected {selected} provider is not implemented in this bundle",
                 area=selected, provider=provider)
        result[selected] = {"provider": provider, "source": "configured" if explicit else "default"}
    return result


def preflight(project, mode="manual", area="both"):
    if mode not in {"manual", "autonomous"} or area not in {*AREAS, "both"}:
        fail("validation", "Unsupported preflight mode or area")
    root, workspace_id = workspace_root(project)
    directory = root / ".bstack/workspace"
    return {"ok": True, "value": {
        "root": str(root), "workspaceId": workspace_id, "mode": mode, "area": area,
        "adapters": work_adapters(directory, area), "grilling": grilling_roles(directory, mode),
        "runtimeChecked": False,
    }}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        fail("validation", message)


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument("--project", type=Path, default=Path.cwd())
        commands = parser.add_subparsers(dest="command", required=True)
        check = commands.add_parser("preflight")
        check.add_argument("--mode", choices=("manual", "autonomous"), default="manual")
        check.add_argument("--area", choices=("wayfinder", "tickets", "both"), default="both")
        args = parser.parse_args(argv)
        print(canonical(preflight(args.project, args.mode, args.area)))
        return 0
    except DomainError as error:
        print(canonical(error.response()))
        return 1
    except OSError:
        print(canonical({"ok": False, "error": {"code": "io", "message": "Could not read workflow configuration"}}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
