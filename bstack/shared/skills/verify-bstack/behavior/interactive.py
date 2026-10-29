#!/usr/bin/env python3
"""Prepare behavior cases for a computer-use agent to drive in desktop apps or terminal UIs, then grade them."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import urllib.parse
import uuid

sys.dont_write_bytecode = True
import run
from hosts import HOME, HOSTS

SURFACES = {
    "codex-desktop": ("codex", "desktop"), "claude-desktop": ("claude", "desktop"),
    "cursor-desktop": ("cursor", "desktop"), "opencode-desktop": ("opencode", "desktop"),
    "codex-tui": ("codex", "tui"), "claude-tui": ("claude", "tui"), "cursor-tui": ("cursor", "tui"),
    "grok-tui": ("grok", "tui"), "amp-tui": ("amp", "tui"), "opencode-tui": ("opencode", "tui"),
}
LAUNCH = {
    "codex-desktop": "codex-desktop", "claude-desktop": "claude-desktop", "cursor-desktop": "cursor --new-window .",
    "opencode-desktop": "opencode-desktop", "codex-tui": "codex", "claude-tui": "claude", "cursor-tui": "cursor-agent",
    "grok-tui": "grok", "amp-tui": "amp", "opencode-tui": "opencode",
}
PROMPT_BOUNDARY = {"cursor": {"beforeSubmitPrompt"}, "grok": {"UserPromptSubmit"}}
CHANGING_TOOLS = {"Edit", "Write", "MultiEdit", "StrReplace", "edit", "write", "patch", "search_replace", "write_file",
                  "apply_patch"}


def steps_for(surface, scenario):
    host = SURFACES[surface][0]
    steps = []
    for turn in run.SCENARIOS[scenario]["turns"]:
        if turn is run.COMPACT:
            steps.append({"kind": "compact"})
        else:
            steps.append({"kind": "prompt", "text": turn(host) if callable(turn) else turn})
    return steps


def launch_script(env, project, command):
    exports = "\n".join(f"export {key}={shlex.quote(env[key])}" for key in (
        "PATH", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM", "GIT_EXEC_PATH", "GH_CONFIG_DIR", "FAKE_FORGE_STATE",
        "FAKE_FORGE_GIT", "FAKE_FORGE_REPO", "BSTACK_VERIFY_DIR", "BSTACK_STATE_DIR"))
    return (f"#!/bin/sh\nunset GH_TOKEN GITHUB_TOKEN GH_ENTERPRISE_TOKEN\n{exports}\ncd {shlex.quote(str(project))}\n"
            f"if [ \"$#\" -gt 0 ]; then exec \"$@\"; fi\nexec {command}\n")


def card(case):
    lines = [f"# {case['surface']} · {case['scenario']} #{case['repeat']}", "",
             f"Project: `{case['project']}`", "",
             f"Launch: `sh {case['folder']}/launch.sh`", "",
             "Steps, in order:", ""]
    for number, step in enumerate(case["steps"], 1):
        if step["kind"] == "compact":
            lines.append(f"{number}. Trigger this app's native compaction in the same session (see the surface notes).")
        else:
            lines.append(f"{number}. Send this prompt exactly, then wait until the agent finishes:")
            lines += ["", "```text", step["text"], "```", ""]
    lines += ["", f"Evidence: screenshots in `{case['folder']}/screens/`, one JSON line per action in "
              f"`{case['folder']}/steps.jsonl`, and anything unusual in `{case['folder']}/notes.md`.", ""]
    return "\n".join(lines)


def prepare(surfaces, scenarios, repeats):
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-interactive-" + uuid.uuid4().hex[:6]
    out = run.ROOT / ".bstack/verification" / run_id
    for surface in surfaces:
        host, kind = SURFACES[surface]
        for scenario in scenarios:
            if run.COMPACT in run.SCENARIOS[scenario]["turns"] and not HOSTS[host].compacts:
                continue
            for repeat in range(1, repeats + 1):
                folder = out / surface / f"{scenario}-{repeat}"
                (folder / "screens").mkdir(parents=True)
                base, project, env = run.workspace(run.SCENARIOS[scenario], host)
                env = dict(env, BSTACK_VERIFY_DIR=str(base / "hooks/interactive"), BSTACK_STATE_DIR=str(base / "state"))
                Path(env["BSTACK_VERIFY_DIR"]).mkdir(parents=True)
                case = {"surface": surface, "kind": kind, "host": host, "scenario": scenario, "repeat": repeat,
                        "folder": str(folder), "workspace": str(base), "project": str(project),
                        "base_commit": run.git(project, "rev-parse", "HEAD", env=env),
                        "prepared_at": datetime.now(timezone.utc).isoformat(), "prepared_epoch": datetime.now().timestamp(),
                        "steps": steps_for(surface, scenario)}
                (folder / "launch.sh").write_text(launch_script(env, project, LAUNCH[surface]))
                (folder / "launch.sh").chmod(0o755)
                run.verify.save(folder / "case.json", case)
                (folder / "CASE.md").write_text(card(case))
                (folder / "steps.jsonl").touch()
                print(folder)
    return out


def exported(argv):
    with tempfile.TemporaryFile("w+") as output:
        subprocess.run(argv, stdout=output, stderr=subprocess.DEVNULL, timeout=120)
        output.seek(0)
        text = output.read()
    return json.loads(text) if text.strip() else {}


def tool_event(name, args):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": args}]}}


def text_event(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def normalized(name, args):
    args = args if isinstance(args, dict) else {"command": str(args)}
    path = next((args[key] for key in ("file_path", "filePath", "path", "target_file") if isinstance(args.get(key), str)), None)
    command = next((args[key] for key in ("command", "cmd") if isinstance(args.get(key), str)), None)
    if name in CHANGING_TOOLS:
        return tool_event("Edit", {"file_path": path or command or ""})
    if path and not command:
        return tool_event("Read", {"file_path": path})
    return tool_event("Bash", {"command": command or json.dumps(args)[:4000]})


def claude_turns(case):
    slug = re.sub(r"[^A-Za-z0-9]", "-", case["project"])
    files = sorted((HOME / ".claude/projects" / slug).glob("*.jsonl"), key=lambda path: path.stat().st_mtime)
    turns, compacted = [], False
    for path in files:
        for line in path.read_text(errors="replace").splitlines():
            event = json.loads(line)
            if event.get("type") == "system" and event.get("subtype") == "compact_boundary":
                compacted = True
            content = (event.get("message") or {}).get("content")
            if event.get("type") == "user" and not event.get("isMeta") and not event.get("isCompactSummary") and (
                    isinstance(content, str) or any(isinstance(c, dict) and c.get("type") == "text" for c in content or [])):
                text = content if isinstance(content, str) else " ".join(c.get("text", "") for c in content if c.get("type") == "text")
                command = re.search(r"<command-name>(/[^<]+)</command-name>", text)
                if (command and command.group(1) != "/compact") or (not text.startswith("<") and text.strip() != "/compact"):
                    turns.append([])
            if event.get("type") == "assistant" and turns:
                turns[-1].append(event)
    return turns, compacted


def codex_turns(case):
    turns, compacted = [], False
    for path in sorted((HOME / ".codex/sessions").glob("*/*/*/*.jsonl"), key=lambda path: path.stat().st_mtime):
        if path.stat().st_mtime < case["prepared_epoch"]:
            continue
        lines = [json.loads(line) for line in path.read_text(errors="replace").splitlines()]
        meta = next((item["payload"] for item in lines if item.get("type") == "session_meta"), {})
        if meta.get("cwd") != case["project"]:
            continue
        for item in lines:
            payload = item.get("payload") or {}
            if item.get("type") == "compacted" or payload.get("type") == "context_compacted":
                compacted = True
            if item.get("type") == "event_msg" and payload.get("type") == "task_started":
                turns.append([])
            if item.get("type") == "response_item" and turns:
                if payload.get("type") in ("custom_tool_call", "function_call", "local_shell_call"):
                    turns[-1].append(tool_event("Bash", {"command": str(payload.get("input") or payload.get("arguments")
                                                                        or payload.get("action"))}))
                elif payload.get("type") == "message" and payload.get("role") == "assistant":
                    turns[-1].append(text_event(" ".join(c.get("text", "") for c in payload.get("content", []))))
    return [turn for turn in turns if turn], compacted


def opencode_turns(case):
    database = HOME / ".local/share/opencode/opencode.db"
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
        ids = [row[0] for row in connection.execute(
            "select id from session where directory = ? and parent_id is null order by time_created", (case["project"],))]
    turns, compacted = [], False
    for session in ids:
        export = exported(["opencode", "export", session])
        for message in export["messages"]:
            parts = message["parts"]
            if any(part["type"] == "compaction" for part in parts):
                compacted = True
                continue
            if message["info"].get("role") == "user" and any(part["type"] == "text" for part in parts):
                turns.append([])
            elif turns:
                for part in parts:
                    if part["type"] == "tool":
                        turns[-1].append(normalized(part["tool"], (part.get("state") or {}).get("input")))
                    elif part["type"] == "text":
                        turns[-1].append(text_event(part.get("text", "")))
    return turns, compacted


def cursor_turns(case):
    slug = re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9]", "-", case["project"])).strip("-")
    files = sorted((HOME / ".cursor/projects" / slug / "agent-transcripts").glob("*/*.jsonl"),
                   key=lambda path: path.stat().st_mtime)
    turns = []
    for path in files:
        for line in path.read_text(errors="replace").splitlines():
            event = json.loads(line)
            content = (event.get("message") or {}).get("content") or []
            if event.get("role") == "user" and any(c.get("type") == "text" for c in content if isinstance(c, dict)):
                turns.append([])
            elif event.get("role") == "assistant" and turns:
                for c in content:
                    if c.get("type") == "tool_use":
                        turns[-1].append(normalized(c.get("name"), c.get("input")))
                    elif c.get("type") == "text" and c.get("text") != "[REDACTED]":
                        turns[-1].append(text_event(c.get("text", "")))
    return turns, False


def grok_session(path):
    return [json.loads(line) for line in (path / "chat_history.jsonl").read_text(errors="replace").splitlines()]


def grok_turns(case):
    folder = HOME / ".grok/sessions" / urllib.parse.quote(case["project"], safe="")
    sessions = [grok_session(path) for path in sorted(folder.iterdir()) if (path / "chat_history.jsonl").is_file()]
    main = [items for items in sessions if not any(
        item.get("type") == "system" and str(item.get("content")).startswith("You are a Grok Build subagent")
        for item in items)]
    helpers = [items for items in sessions if items not in main]
    turns, compacted, spawned = [], False, []
    for items in main:
        for item in items:
            if item.get("type") == "user" and "prompt_index" in item:
                turns.append([])
            elif item.get("type") == "assistant" and turns:
                if isinstance(item.get("content"), str) and item["content"]:
                    turns[-1].append(text_event(item["content"]))
                for call in item.get("tool_calls") or []:
                    try:
                        arguments = json.loads(call.get("arguments") or "{}")
                    except ValueError:
                        arguments = {"command": call.get("arguments")}
                    turns[-1].append(normalized(call.get("name"), arguments))
                    if call.get("name") == "spawn_subagent":
                        spawned.append(len(turns) - 1)
            elif "compact" in str(item.get("type", "")):
                compacted = True
    for index, items in zip(spawned, helpers):
        for item in items:
            for call in item.get("tool_calls") or []:
                try:
                    arguments = json.loads(call.get("arguments") or "{}")
                except ValueError:
                    arguments = {"command": call.get("arguments")}
                turns[index].append(normalized(call.get("name"), arguments))
    return turns, compacted


def amp_turns(case):
    listing = subprocess.run(["amp", "threads", "list", "--limit", "40"], capture_output=True, text=True, timeout=120).stdout
    turns = []
    for thread in dict.fromkeys(re.findall(r"T-[0-9a-f-]{36}", listing)):
        export = exported(["amp", "threads", "export", thread])
        directory = export.get("env", {}).get("initial", {}).get("workingDirectory", "")
        if directory.removeprefix("file://") != case["project"]:
            continue
        for message in export.get("messages", []):
            content = [c for c in message.get("content", []) if isinstance(c, dict)]
            if message.get("role") == "user" and any(c.get("type") == "text" for c in content):
                turns.append([])
            elif message.get("role") == "assistant" and turns:
                for c in content:
                    if c.get("type") == "tool_use":
                        turns[-1].append(normalized(c.get("name"), c.get("input")))
                    elif c.get("type") == "text":
                        turns[-1].append(text_event(c.get("text", "")))
        break
    return turns, False


def hook_turns(case, records):
    host = case["host"]
    turns, compacted = [], False
    for record in records:
        if record.get("event") in PROMPT_BOUNDARY.get(host, set()) or (not turns and record.get("event") in (
                "sessionStart", "SessionStart")):
            turns.append([])
        if record.get("event") in ("preCompact", "PreCompact", "PostCompact"):
            compacted = True
        if record.get("tool") and turns:
            turns[-1].append(normalized(record["tool"], {"command": record.get("tool_target")} if not str(
                record.get("tool_target", "")).startswith("/") else {"file_path": record["tool_target"]}))
    return [turn for turn in turns if turn] or turns, compacted


TRANSCRIPTS = {"claude": claude_turns, "codex": codex_turns, "opencode": opencode_turns, "amp": amp_turns,
               "cursor": cursor_turns, "grok": grok_turns}


def grade(folder):
    case = json.loads((folder / "case.json").read_text())
    hooks = Path(case["workspace"]) / "hooks/interactive"
    records = sorted(run.grading.records(hooks, "hook-*.json"),
                     key=lambda record: record.get("observed_at_ns", 0))
    turns, compacted = TRANSCRIPTS[case["host"]](case) if case["host"] in TRANSCRIPTS else hook_turns(case, records)
    if case["host"] == "cursor" and any(record.get("event") == "preCompact" for record in records):
        compacted = True
    prompt_indexes = [index for index, step in enumerate(case["steps"], 1) if step["kind"] == "prompt"]
    exits = []
    for number, step in enumerate(case["steps"], 1):
        turn_dir = folder / f"turn-{number}"
        (turn_dir / "hooks").mkdir(parents=True, exist_ok=True)
        if step["kind"] == "prompt":
            position = prompt_indexes.index(number)
            if position >= len(turns):
                break
            (turn_dir / "stdout.jsonl").write_text("".join(json.dumps(event) + "\n" for event in turns[position]))
            (turn_dir / "prompt.txt").write_text(step["text"])
        exits.append(0)
    for record in records:
        target = folder / "turn-1/hooks" / f"hook-{record.get('receipt') or uuid.uuid4().hex}.json"
        target.write_text(json.dumps(record))
    first = turns[0] if turns else []
    model_file = folder / "model.txt"
    model = model_file.read_text().strip() if model_file.is_file() and model_file.read_text().strip() else "unreported"
    observed = {"host": case["host"], "surface": case["surface"], "model": model, "scenario": case["scenario"],
                "repeat": case["repeat"], "workspace": case["workspace"], "project": case["project"],
                "base_commit": case["base_commit"], "exits": exits, "compacted": compacted, "interactive": True,
                "changed_after_first": any(tool.get("name") == "Edit" for event in first
                                           for tool in event.get("message", {}).get("content", [])),
                "session": None, "transcript_turns": len(turns)}
    run.verify.save(folder / "observed.json", observed)
    return run.assess(folder)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "grade", "surfaces"))
    parser.add_argument("--surfaces", nargs="+", choices=SURFACES, default=[])
    parser.add_argument("--scenarios", nargs="+", choices=run.SCENARIOS, default=list(run.SCENARIOS))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--run", type=Path, help="Interactive run directory to grade")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    if args.action == "surfaces":
        for surface, (host, kind) in SURFACES.items():
            print(f"{surface:18} host={host:9} kind={kind:8} launch: {LAUNCH[surface]}")
        return 0
    if args.action == "prepare":
        if not args.surfaces:
            parser.error("--surfaces is required for prepare")
        print(prepare(args.surfaces, args.scenarios, args.repeats))
        return 0
    if not args.run:
        parser.error("--run is required for grade")
    results = [grade(path.parent) for path in sorted(args.run.glob("*/*/case.json"))]
    summary = run.summarize(results, {name: {"version": None} for name in HOSTS})
    run.verify.save(args.run / "report.json", {"run": args.run.name, "results": results, "summary": summary})
    if args.record:
        run.record(summary, args.run.name)
    print(args.run / "report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
