#!/usr/bin/env python3
"""Read workflow configuration and ADRs without creating or upgrading a workspace."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

# Importing the bundled workspace must not create bytecode beside installed files.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from wayfinder.core import DomainError, canonical, workspace_binding
import model_cli


ADAPTERS = {"native", "codex", "claude", "cursor", "grok"}
AREAS = {"wayfinder", "tickets"}
MAX_CONFIG_BYTES = 65536
ROLE_NEXT_STEP = "Run autonomous preflight to test both CLI models before any planning write. Native roles need a separate host-level check."


def fail(code, message, **details):
    raise DomainError(code, message, **details)


def present(path):
    return path.exists() or path.is_symlink()


def workspace_root(project):
    root, metadata = workspace_binding(project)
    return root, metadata["id"] if metadata else None


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
            fail("config_missing", "Autonomous grilling needs two models this host can run: one to challenge the plan and one to answer. Verify both, then save them with configure-grilling. Human-guided grilling needs no model setup")
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


def validate_grilling_roles(value):
    fields(value, {"version", "grilling"}, {"version", "grilling"}, "roles.json")
    if type(value["version"]) is not int or value["version"] != 1:
        fail("config_invalid", "roles.json must use version 1")
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
    return bindings


def grilling_roles(directory, mode, root, structural=False):
    if mode == "manual":
        return {"status": "not-required", "runtimeChecked": False}
    value = config(directory / "roles.json", required=True)
    bindings = validate_grilling_roles(value)
    if structural:
        return {"status": "configured", "bindings": bindings, "runtimeChecked": False, "nextStep": ROLE_NEXT_STEP}
    try:
        result = model_cli.diagnose(root, "grilling", live=True)
    except model_cli.ModelCLIError as error:
        fail("model_config_invalid", str(error))
    if result["status"] != "passed":
        failed = [role for role, check in result["workflows"]["grilling"].get("roles", {}).items()
                  if check["status"] != "passed"]
        fail("model_unavailable", "Autonomous grilling cannot start because these roles did not pass a live check: "
             + ", ".join(failed) + ". Check login, model access, or the private wrapper command. Native roles need an observed host-level check and --structural preflight.")
    return {"status": "ready", "bindings": bindings, "runtimeChecked": True,
            "checks": result["workflows"]["grilling"]["roles"]}


def configure_grilling(project, args):
    root, workspace_id = workspace_root(project)
    if workspace_id is None:
        fail("workspace_missing", "Initialize the local workspace before configuring autonomous grilling")
    directory = root / ".bstack/workspace"
    bindings = {}
    for role in ("interviewer", "respondent"):
        binding = {"adapter": getattr(args, f"{role}_adapter"), "model": getattr(args, f"{role}_model")}
        effort = getattr(args, f"{role}_effort")
        if effort is not None:
            binding["effort"] = effort
        bindings[role] = binding
    value = {"version": 1, "grilling": bindings}
    validated = validate_grilling_roles(value)
    value["grilling"] = validated
    target = directory / "roles.json"
    if target.is_symlink():
        fail("config_invalid", "roles.json cannot be a symbolic link")
    if target.exists() and not args.replace:
        fail("config_exists", "Grilling roles already exist. Use --replace only when changing the selected models")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".roles-", suffix=".json", dir=directory)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        if args.replace:
            os.replace(temporary, target)
        else:
            try:
                os.link(temporary, target)
            except FileExistsError:
                fail("config_exists", "Grilling roles already exist. Use --replace only when changing the selected models")
    finally:
        temporary.unlink(missing_ok=True)
    return {"ok": True, "value": {"root": str(root), "workspaceId": workspace_id,
                                  "grilling": {"status": "configured", "bindings": validated, "runtimeChecked": False,
                                                "nextStep": ROLE_NEXT_STEP}}}


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


def preflight(project, mode="manual", area="both", structural=False):
    if mode not in {"manual", "autonomous"} or area not in {*AREAS, "both"}:
        fail("validation", "Unsupported preflight mode or area")
    root, workspace_id = workspace_root(project)
    directory = root / ".bstack/workspace"
    return {"ok": True, "value": {
        "root": str(root), "workspaceId": workspace_id, "mode": mode, "area": area,
        "adapters": work_adapters(directory, area), "grilling": grilling_roles(directory, mode, root, structural),
        "runtimeChecked": mode == "autonomous" and not structural,
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
        check.add_argument("--structural", action="store_true", help="Only inspect saved roles; use after a separate observed native-host check")
        configure = commands.add_parser("configure-grilling", help="Save the two model roles for autonomous grilling")
        for role in ("interviewer", "respondent"):
            configure.add_argument(f"--{role}-adapter", choices=sorted(ADAPTERS), required=True)
            configure.add_argument(f"--{role}-model", required=True)
            configure.add_argument(f"--{role}-effort")
        configure.add_argument("--replace", action="store_true")
        adr = commands.add_parser("adr", help="Inspect only the selected ADR file or directory")
        adr.add_argument("--path", default="docs/adr", help="Checkout-relative Markdown file or directory (default: docs/adr)")
        args = parser.parse_args(argv)
        if args.command == "configure-grilling":
            result = configure_grilling(args.project, args)
        elif args.command == "adr":
            from adr import inspect_adrs
            result = {"ok": True, "value": inspect_adrs(args.project, args.path).value()}
        else:
            result = preflight(args.project, args.mode, args.area, args.structural)
        print(canonical(result))
        return 0
    except DomainError as error:
        print(canonical(error.response()))
        return 1
    except OSError:
        print(canonical({"ok": False, "error": {"code": "io", "message": "Could not read or write workflow configuration"}}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
