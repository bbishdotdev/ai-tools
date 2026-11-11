#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import shlex
import sys
import uuid

sys.dont_write_bytecode = True
from attribution import ExistingContext, attach, helper_positions
from attribution_hosts import arguments, capture


HELPER = Path(__file__).resolve().parents[2] / "github/pr.py"
MESSAGE = (f"Use bstack's to-pr skill before creating a PR or replacing its body. Run its helper's scan, prepare, "
           f"then publish steps: {shlex.join([os.path.abspath(sys.executable), str(HELPER)])}")


def commands(source):
    lexer = shlex.shlex(source, posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace_split = True
    lexer.whitespace = " \t\r"
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    groups = [[]]
    for token in tokens:
        if token and all(character in ";&|()\n" for character in token):
            groups.append([])
        else:
            groups[-1].append(token)
    return groups


def command_start(tokens):
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in ("if", "then", "do", "command", "exec", "time") or "=" in token and token.split("=", 1)[0].isidentifier():
            index += 1
            continue
        if token == "env":
            index += 1
            while index < len(tokens) and "=" in tokens[index] and tokens[index].split("=", 1)[0].isidentifier():
                index += 1
            continue
        return index
    return index


def bypasses_to_pr(source):
    for tokens in commands(source):
        start = command_start(tokens)
        if len(tokens) < start + 3 or Path(tokens[start]).name != "gh":
            continue
        position = start + 1
        while position < len(tokens) and tokens[position].startswith("-"):
            position += 2 if tokens[position] in ("-R", "--repo", "--hostname") else 1
        if len(tokens) < position + 2 or tokens[position] != "pr":
            continue
        action = tokens[position + 1]
        if action == "create":
            return True
        if action == "edit" and any(
            argument in ("-b", "--body", "-F", "--body-file") or
            argument.startswith(("--body=", "--body-file="))
            for argument in tokens[position + 2:]
        ):
            return True
    return False


SHELL_TOOLS = ("Bash", "Shell", "bash", "shell", "run_terminal_command", "run_in_terminal")


def shell_command(host, payload):
    if host == "cursor" and "command" in payload:
        return payload.get("command")
    tool = payload.get("tool_name", payload.get("toolName"))
    if tool not in SHELL_TOOLS:
        return None
    detail = payload.get("tool_input", payload.get("toolInput", payload.get("toolArgs", {})))
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except ValueError:
            return None
    return detail.get("command") if isinstance(detail, dict) else None


def attributed_input(host, payload, command):
    if not isinstance(command, str) or host == "cursor" and payload.get("hook_event_name") != "preToolUse":
        return None
    cwd = payload.get("cwd") or next(iter(payload.get("workspace_roots") or []), str(Path.cwd()))
    positions = helper_positions(command, HELPER, cwd)
    if not positions:
        return None
    attribution = capture(host, payload)
    detail = arguments(payload.get("tool_input", payload.get("toolInput", payload.get("toolArgs"))))
    updated = {**detail, "command": attach(command, positions, attribution)}
    if host == "cursor":
        return {"updated_input": updated}
    if host in ("opencode", "amp") or host == "copilot" and payload.get("tool_name") != "run_in_terminal":
        return {"modifiedArgs": updated}
    decision = {"hookEventName": "PreToolUse", "updatedInput": updated}
    if host == "codex":
        decision["permissionDecision"] = "allow"
    return {"hookSpecificOutput": decision}


def record_decision(host, payload, command, denied):
    directory = os.environ.get("BSTACK_VERIFY_DIR")
    if directory:
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        detail = payload.get("tool_input", payload.get("toolInput", payload.get("toolArgs")))
        record = {"host": host, "event": "pr_guard", "blocked": denied,
                  "command_available": isinstance(command, str),
                  "tool": payload.get("tool_name", payload.get("toolName")),
                  "arguments_type": type(detail).__name__}
        (destination / f"guard-{uuid.uuid4().hex}.json").write_text(json.dumps(record) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True, choices=("codex", "claude", "cursor", "grok", "copilot", "opencode", "amp"))
    parser.add_argument("--probe", action="store_true", help="Check startup without processing a tool call")
    args = parser.parse_args()
    if args.probe:
        print(json.dumps({"host": args.host, "purpose": "guard", "python": os.path.abspath(sys.executable)}))
        return 0
    if os.environ.get("GROK_HOOK_EVENT") and args.host != "grok":
        print(json.dumps({"permission": "allow"} if args.host == "cursor" else {}))
        return 0
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    command = shell_command(args.host, payload) if isinstance(payload, dict) else None
    denied = isinstance(command, str) and bypasses_to_pr(command)
    message, rewritten = MESSAGE, None
    if not denied and isinstance(payload, dict):
        try:
            rewritten = attributed_input(args.host, payload, command)
        except ExistingContext as error:
            denied, message = True, str(error)
    if isinstance(payload, dict):
        record_decision(args.host, payload, command, denied)
    if denied:
        decision = {"permissionDecision": "deny", "permissionDecisionReason": message}
        if payload.get("hook_event_name") == "PreToolUse" and args.host == "copilot":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", **decision}}))
            return 0
        if args.host in ("copilot", "opencode", "amp"):
            print(json.dumps(decision))
            return 0
        print(message, file=sys.stderr)
        return 2
    ordinary = {"permission": "allow"} if args.host == "cursor" and isinstance(command, str) else {}
    print(json.dumps(rewritten if rewritten is not None else ordinary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
