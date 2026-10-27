#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import shlex
import sys


HELPER = Path(__file__).resolve().parents[2] / "github/pr.py"
MESSAGE = (f"Use bstack's to-pr skill before creating a PR or replacing its body. Run its helper's scan, prepare, "
           f"then publish steps: python3 {HELPER}")


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


SHELL_TOOLS = ("Bash", "Shell", "bash", "shell", "run_terminal_command")


def shell_command(host, payload):
    if host == "cursor":
        return payload.get("command")
    tool = payload.get("tool_name", payload.get("toolName"))
    if tool not in SHELL_TOOLS:
        return None
    detail = payload.get("tool_input", payload.get("toolInput", payload.get("toolArgs", {})))
    return detail.get("command") if isinstance(detail, dict) else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True, choices=("codex", "claude", "cursor", "grok", "copilot", "opencode", "amp"))
    args = parser.parse_args()
    if os.environ.get("GROK_HOOK_EVENT") and args.host != "grok":
        print(json.dumps({"permission": "allow"} if args.host == "cursor" else {}))
        return 0
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    command = shell_command(args.host, payload) if isinstance(payload, dict) else None
    if isinstance(command, str) and bypasses_to_pr(command):
        if args.host in ("copilot", "opencode", "amp"):
            print(json.dumps({"permissionDecision": "deny", "permissionDecisionReason": MESSAGE}))
            return 0
        print(MESSAGE, file=sys.stderr)
        return 2
    print(json.dumps({"permission": "allow"} if args.host == "cursor" else {}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
