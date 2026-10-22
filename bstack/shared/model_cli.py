#!/usr/bin/env python3
"""Configure and check headless model commands for a BStack project."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from wayfinder.core import DomainError, workspace_binding


CLIENTS = {"codex": "codex", "claude": "claude", "cursor": "cursor-agent", "grok": "grok"}
REVIEW_DEFAULTS = {
    "reviewer_a": {"cli": "claude", "model": "claude-opus-5-5", "effort": "medium"},
    "reviewer_b": {"cli": "codex", "model": "gpt-6-astra", "effort": "medium"},
    "adjudicator": {"cli": "claude", "model": "claude-opus-5-5", "effort": "high"},
}
READY = "BSTACK_MODEL_READY"
CONFIG = ".bstack/model-clis.json"
MAX_CONFIG = 65536


class ModelCLIError(ValueError):
    pass


def config_root(project):
    try:
        root, _ = workspace_binding(project)
        return root
    except DomainError as error:
        raise ModelCLIError(str(error)) from error


def config_path(project):
    return config_root(project) / CONFIG


def validate_template(parts):
    if (not isinstance(parts, list) or not 2 <= len(parts) <= 32
            or parts.count("{args}") != 1 or parts[0] == "{args}"):
        raise ModelCLIError("Command must be an argv list with one {args} placeholder, for example: launch claude -- {args}")
    for part in parts:
        if not isinstance(part, str) or not part or len(part) > 512 or any(ord(char) < 32 for char in part):
            raise ModelCLIError("Command arguments must be short, nonempty strings without control characters")
        if "{args}" in part and part != "{args}":
            raise ModelCLIError("{args} must be its own argument")
    if Path(parts[0]).name.casefold() in {"sh", "bash", "zsh", "fish", "dash", "pwsh", "powershell"}:
        raise ModelCLIError("Use the launcher executable directly; shell -c commands are not accepted")
    return parts


def load(project):
    path = config_path(project)
    if path.is_symlink():
        raise ModelCLIError("model-clis.json cannot be a symbolic link")
    if not path.exists():
        return {}
    if path.stat().st_size > MAX_CONFIG:
        raise ModelCLIError("model-clis.json must be a regular JSON file under 64 KiB")
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise ModelCLIError("model-clis.json is not valid JSON") from error
    if not isinstance(value, dict) or set(value) != {"version", "commands"} or value["version"] != 1:
        raise ModelCLIError("model-clis.json needs version 1 and a commands object")
    commands = value["commands"]
    if not isinstance(commands, dict) or set(commands) - set(CLIENTS):
        raise ModelCLIError("model-clis.json contains an unsupported CLI")
    return {client: validate_template(parts) for client, parts in commands.items()}


def template(project, client):
    if client not in CLIENTS:
        raise ModelCLIError(f"Unsupported model CLI: {client}")
    configured = load(project).get(client)
    if configured:
        return configured
    if client == "cursor" and shutil.which("cursor-agent") is None and shutil.which("agent") is not None:
        return ["agent", "{args}"]
    return [CLIENTS[client], "{args}"]


def argv(project, client, arguments):
    result = []
    for part in template(project, client):
        result.extend(arguments if part == "{args}" else [part])
    if "/" in result[0] and not Path(result[0]).is_absolute():
        result[0] = str((config_root(project) / result[0]).resolve())
    return result


def configure(project, client, command):
    if client not in CLIENTS:
        raise ModelCLIError(f"Unsupported model CLI: {client}")
    try:
        parts = validate_template(shlex.split(command))
    except ValueError as error:
        raise ModelCLIError(f"Invalid command: {error}") from error
    current = load(project)
    current[client] = parts
    path = config_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ModelCLIError("model-clis.json cannot be a symbolic link")
    descriptor, temporary = tempfile.mkstemp(prefix=".model-clis-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump({"version": 1, "commands": current}, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"cli": client, "status": "saved", "path": str(path), "next": "Run doctor --live for the workflow that uses this CLI."}


def availability(project, client):
    command = argv(project, client, ["--version"])
    executable = shutil.which(command[0])
    if executable is None:
        return {"status": "missing", "command": command[0], "hint": f"Install {client}, or configure its launcher with model_cli.py configure --cli {client} --command '...'"}
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=7, cwd=project)
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "version_unavailable", "command": command[0], "hint": "The launcher did not return a version. A live prompt can still prove it works."}
    if result.returncode:
        return {"status": "version_unavailable", "command": command[0], "hint": "The launcher rejected --version. A live prompt can still prove it works."}
    lines = (result.stdout or result.stderr).strip().splitlines()
    return {"status": "available", "command": command[0], "version": lines[0][:160] if lines else "unknown"}


def failure_hint(client, output, error, exit_code):
    detail = (error + "\n" + output).casefold()
    if any(word in detail for word in ("authentication", "not authenticated", "not logged in", "session expired", "oauth", "unauthorized", "401")):
        return f"{client} could not authenticate. Sign in through that CLI, then rerun the live doctor."
    if any(word in detail for word in ("model not found", "unknown model", "model unavailable", "not available", "model is not supported")):
        return f"The selected model is unavailable to {client}. Choose an exact model this account can run, then retry."
    if any(word in detail for word in ("unknown option", "unexpected argument", "unrecognized option", "unknown flag")):
        return f"{client} rejected a CLI argument. Check its --help output and the configured wrapper's {{args}} position."
    if exit_code == 0:
        return f"{client} answered without the expected probe text. Check whether the wrapper changes output or prompt arguments."
    return f"{client} exited {exit_code}. Check CLI login, model access and the configured wrapper's argument pass-through."


def probe_arguments(client, model, effort, work):
    prompt = f"Reply with exactly {READY}. Do not call tools or inspect files."
    model_arg = ["--model", model] if model else []
    if client == "codex":
        args = ["exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", *model_arg,
                "-c", "mcp_servers={}", "--output-last-message", str(work / "answer.txt")]
        if effort:
            args.extend(["-c", f'model_reasoning_effort="{effort}"'])
        args.append("-")
        return args, prompt
    if client == "claude":
        args = ["--print", "--safe-mode", "--restricted", "--tools", "", "--setting-sources", "",
                "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--no-session-persistence",
                *model_arg, "--output-format", "json"]
        if effort:
            args.extend(["--effort", effort])
        args.append(prompt)
        return args, None
    if client == "cursor":
        return ["--print", "--mode", "ask", "--trust", *model_arg, "--output-format", "text", prompt], None
    args = ["--single", prompt, "--permission-mode", "plan", "--no-subagents", "--disable-web-search",
            *model_arg, "--output-format", "plain"]
    if effort:
        args.extend(["--reasoning-effort", effort])
    return args, None


def probe(project, client, model=None, effort=None, timeout=90):
    if client not in CLIENTS or (model is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", model)):
        raise ModelCLIError("Choose a supported CLI and an exact model ID")
    if effort is not None and effort not in {"low", "medium", "high", "xhigh", "max"}:
        raise ModelCLIError("Choose a supported effort value")
    if client == "cursor" and effort is not None:
        return {"status": "failed", "cli": client, "model": model,
                "reason": "Cursor has no separate effort flag in this adapter. Choose a model variant that includes effort, or omit effort."}
    if not 5 <= timeout <= 300:
        raise ModelCLIError("Probe timeout must be between 5 and 300 seconds")
    ready = availability(project, client)
    if ready["status"] == "missing":
        return {"status": "failed", "cli": client, "model": model, "reason": ready["hint"]}
    with tempfile.TemporaryDirectory(prefix="bstack-model-probe-") as directory:
        work = Path(directory)
        arguments, data = probe_arguments(client, model, effort, work)
        command = argv(project, client, arguments)
        try:
            result = subprocess.run(command, input=data, capture_output=True, text=True, timeout=timeout, cwd=work)
        except subprocess.TimeoutExpired:
            return {"status": "failed", "cli": client, "model": model, "reason": f"The model did not answer within {timeout} seconds"}
        except OSError:
            return {"status": "failed", "cli": client, "model": model, "reason": "The configured command could not start"}
        output = (work / "answer.txt").read_text() if client == "codex" and (work / "answer.txt").exists() else result.stdout
        observed = None
        if client == "claude" and result.returncode == 0:
            try:
                envelope = json.loads(output)
                observed = list(envelope.get("modelUsage", {}))
                output = envelope.get("result", "")
            except (TypeError, ValueError):
                pass
        if result.returncode or READY not in output:
            return {"status": "failed", "cli": client, "model": model,
                    "reason": failure_hint(client, output, result.stderr, result.returncode), "exit_code": result.returncode}
        if observed and model and model not in observed:
            return {"status": "failed", "cli": client, "model": model, "reason": f"The CLI used {observed}, not the requested model"}
        return {"status": "passed", "cli": client, "model": model, "effort": effort,
                "model_confirmed": bool(observed and model in observed), "image_generation_checked": False}


def workflow_roles(project, workflow):
    project = Path(project).resolve()
    if workflow == "review-pr":
        roles = {name: dict(value) for name, value in REVIEW_DEFAULTS.items()}
        path = project / ".bstack/review.json"
        if path.exists():
            try:
                supplied = json.loads(path.read_text())
                for name, value in supplied.get("roles", {}).items():
                    if name not in roles or not isinstance(value, dict):
                        raise ValueError()
                    roles[name].update(value)
            except (OSError, ValueError, AttributeError) as error:
                raise ModelCLIError("Cannot read review roles from .bstack/review.json") from error
        return roles
    if workflow == "grilling":
        path = config_root(project) / ".bstack/workspace/roles.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())["grilling"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ModelCLIError("Cannot read autonomous grilling roles") from error
    if workflow == "to-pr":
        return {"visual": {"cli": "codex", "model": None, "effort": None}}
    raise ModelCLIError(f"Unknown workflow: {workflow}")


def diagnose(project, workflow=None, live=False):
    if live and workflow is None:
        raise ModelCLIError("Choose --workflow review-pr, grilling, or to-pr for a live check")
    project = Path(project).resolve()
    configured = load(project)
    requested = [workflow] if workflow else ["review-pr", "grilling", "to-pr"]
    definitions = {name: workflow_roles(project, name) for name in requested}
    selected = set(CLIENTS) if workflow is None else {
        binding.get("cli", binding.get("adapter")) for roles in definitions.values()
        for binding in roles.values() if isinstance(binding, dict)
    } & set(CLIENTS)
    clients = {client: availability(project, client) if client in selected else {"status": "not_checked"}
               for client in CLIENTS}
    workflows = {}
    for name in requested:
        roles = definitions[name]
        if not roles:
            workflows[name] = {"status": "not_configured", "hint": "Configure two roles before autonomous grilling; human-guided grilling needs none."}
            continue
        checks = {}
        for role, binding in roles.items():
            client = binding.get("cli", binding.get("adapter"))
            model = binding.get("model")
            effort = binding.get("effort")
            if name == "review-pr" and client not in {"codex", "claude"}:
                checks[role] = {"status": "invalid", "hint": "This review runner currently supports Codex and Claude Code roles."}
            elif client == "native":
                checks[role] = {"status": "host_check_needed", "hint": "The native host cannot be tested by this CLI doctor. Use a CLI binding for a repeatable headless check."}
            elif client not in CLIENTS:
                checks[role] = {"status": "invalid", "hint": f"Unsupported CLI: {client}"}
            elif live:
                checks[role] = probe(project, client, model, effort)
            else:
                launch_status = clients[client]["status"]
                hint = "Run doctor --live --workflow " + name
                if launch_status == "version_unavailable":
                    hint = clients[client]["hint"] + " " + hint
                elif launch_status == "missing":
                    hint = clients[client]["hint"]
                checks[role] = {"status": "ready_for_live_check" if launch_status in {"available", "version_unavailable"} else "launcher_failed",
                                "cli": client, "model": model, "hint": hint}
        good = all(item["status"] == "passed" for item in checks.values()) if live else all(item["status"] == "ready_for_live_check" for item in checks.values())
        workflows[name] = {"status": "passed" if good and live else "ready_for_live_check" if good else "needs_setup", "roles": checks}
        if name == "to-pr":
            workflows[name]["limit"] = "A text prompt can be checked here. Image-generation tool access and image quality require an actual visual attempt."
    return {"status": "passed" if live and all(value["status"] == "passed" for value in workflows.values()) else "needs_setup" if live else "inspected",
            "configured_commands": sorted(configured), "clients": clients, "workflows": workflows,
            "live": live}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="action", required=True)
    setting = commands.add_parser("configure")
    setting.add_argument("--cli", required=True, choices=CLIENTS)
    setting.add_argument("--command", required=True, help="Quoted command ending in a standalone {args} placeholder")
    check = commands.add_parser("probe")
    check.add_argument("--cli", required=True, choices=CLIENTS)
    check.add_argument("--model")
    check.add_argument("--effort")
    check.add_argument("--timeout", type=int, default=90)
    run = commands.add_parser("run", help="Run a configured CLI with the supplied arguments")
    run.add_argument("--cli", required=True, choices=CLIENTS)
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    for item in commands.choices.values():
        item.add_argument("--project", type=Path, default=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        project = args.project.expanduser().resolve()
        if args.action == "configure":
            result = configure(project, args.cli, args.command)
        elif args.action == "run":
            arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
            if not arguments:
                raise ModelCLIError("Pass CLI arguments after --")
            return subprocess.run(argv(project, args.cli, arguments), cwd=project, check=False).returncode
        else:
            result = probe(project, args.cli, args.model, args.effort, args.timeout)
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") != "failed" else 1
    except (ModelCLIError, OSError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
