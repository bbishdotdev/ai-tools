#!/usr/bin/env python3
"""Run controlled router probes through real, resumed CLI sessions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[5]
ROUTER = ROOT / "BStack/shared/skills/bstack-router/SKILL.md"
CLIENTS = {"codex": ("codex",), "claude": ("claude",),
           "cursor": ("cursor-agent", "agent"), "grok": ("grok",)}
PROMPT_CONTEXT = {"codex": True, "claude": True, "cursor": False, "grok": False}
CASES = [
    ("bug-fix", "Users report that saving a profile silently discards the display name. Classify this reported defect."),
    ("perf-issue", "An endpoint's p95 latency increased from 120ms to 900ms in our measurements. Classify this performance request."),
    ("investigation", "I only want to understand why our cache exists and how it works, with a cited answer. Classify this read-only request."),
]
CONTRACT = (
    "This is a read-only routing probe, not permission to execute the classified task. "
    "Use this repository's standing guidance; read relevant instruction files as needed. "
    "Do not edit files, run workflows, delegate, call network services, or read verification logs. "
    "Do not invoke verify-bstack or read its files; this probe supplies its own procedure. "
    "Return one JSON object with keys playbook (filename stem), principle (one applicable full skill name), "
    "coding_delegate (the router's default coding-delegate model policy identifier only, no explanation), receipt (the latest verification receipt "
    "visible in hook context, or null), and explanation (one sentence). "
    "Reuse instruction content already available instead of rereading solely for this probe. "
)


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def discover(cursor_bin=None):
    clients = {}
    for name, commands in CLIENTS.items():
        binary = (cursor_bin if name == "cursor" else None) or next(
            (found for command in commands if (found := shutil.which(command))), None)
        entry = {"binary": binary, "installed": bool(binary)}
        if binary:
            try:
                result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15)
                entry.update(version=result.stdout.strip(), version_exit=result.returncode)
            except (OSError, subprocess.TimeoutExpired) as error:
                entry.update(installed=False, error=str(error))
        clients[name] = entry
    return clients


def process(argv, directory, env=None, timeout=180, prompt=None):
    directory.mkdir(parents=True, exist_ok=True)
    save(directory / "command.json", argv)
    if prompt is not None:
        (directory / "prompt.txt").write_text(prompt)
    started = time.monotonic()
    with (directory / "stdout.jsonl").open("w") as out, (directory / "stderr.txt").open("w") as err:
        proc = subprocess.Popen(argv, cwd=ROOT, env=env, stdin=subprocess.PIPE,
                                stdout=out, stderr=err, text=True, start_new_session=True)
        try:
            proc.communicate(prompt, timeout=timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            code = 124
    save(directory / "exit.json", {"code": code, "seconds": round(time.monotonic() - started, 2)})
    return code, (directory / "stdout.jsonl").read_text()


def events(text):
    result = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                result.append(value)
        except ValueError:
            pass
    return result


def extract(stream):
    session, answer, reads = None, "", []
    for event in stream:
        session = event.get("session_id") or event.get("thread_id") or session
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            answer = item.get("text", "")
        if event.get("type") == "item.completed" and item.get("type") == "command_execution":
            if re.search(r"\b(cat|sed|head|tail|read_text)\b", item.get("command", "")):
                reads.append(item.get("command", ""))
        if event.get("type") == "assistant":
            for content in event.get("message", {}).get("content", []):
                if content.get("type") == "text":
                    answer = content.get("text", "")
                if content.get("type") == "tool_use" and content.get("name") in ("Read", "read_file"):
                    reads.append(json.dumps(content.get("input", {})))
        if event.get("type") == "result":
            answer = event.get("result", answer)
        if event.get("type") == "tool_call" and event.get("subtype") == "completed":
            call = event.get("tool_call", {})
            if "readToolCall" in call:
                reads.append(json.dumps(call["readToolCall"].get("args", {})))
    parsed = None
    if isinstance(answer, str):
        start, end = answer.find("{"), answer.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(answer[start:end + 1])
            except ValueError:
                pass
    return session, answer, parsed, reads


def cli_command(tool, binary, session):
    if tool == "codex":
        args = [binary, "exec",
                "-c", f'projects."{ROOT}".trust_level="trusted"',
                "-c", 'model="gpt-6-astra"', "-c", 'model_reasoning_effort="medium"',
                "-c", 'sandbox_mode="read-only"', "--json"]
        return args + (["resume", session, "-"] if session else ["-"])
    if tool == "claude":
        args = [binary, "-p", "--output-format", "stream-json", "--verbose",
                "--permission-mode", "dontAsk", "--tools", "Read,Glob,Grep",
                "--allowedTools", "Read,Glob,Grep", "--strict-mcp-config",
                "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "project"]
        return args + (["--resume", session] if session else [])
    if tool == "grok":
        args = [binary, "--output-format", "streaming-messages-json", "--cwd", str(ROOT),
                "--trust", "--sandbox", "read-only", "--permission-mode", "dontAsk",
                "--tools", "read_file,grep,list_dir", "--no-subagents", "--disable-web-search",
                "--max-turns", "12"]
        return args + (["--resume", session] if session else [])
    args = [binary, "--print", "--output-format", "stream-json", "--mode", "ask",
            "--trust", "--workspace", str(ROOT)]
    return args + (["--resume", session] if session else [])


def run_tool(tool, binary, run, timeout):
    if not binary:
        return {"tool": tool, "status": "blocked", "reason": "CLI executable missing"}
    folder = run / tool
    folder.mkdir()
    session, turns = None, []
    before = hashlib.sha256(ROUTER.read_bytes()).hexdigest()
    for number, (expected, request) in enumerate(CASES, 1):
        turn = folder / f"turn-{number}"
        hook_dir = turn / "hooks"
        argv = cli_command(tool, binary, session)
        prompt = CONTRACT + "\n\n" + request
        if tool in ("cursor", "grok"):
            argv.extend(["-p", prompt] if tool == "grok" else [prompt])
            stdin = None
        else:
            stdin = prompt
        # Native Grok hooks inherit its read-only sandbox. Collect hook output in
        # its writable temporary area, then preserve it with the parent process.
        with tempfile.TemporaryDirectory(prefix=f"bstack-{tool}-probe-") as scratch:
            temporary_hooks = Path(scratch) / "hooks"
            temporary_hooks.mkdir()
            env = dict(os.environ, BSTACK_VERIFY_DIR=str(temporary_hooks),
                       BSTACK_STATE_DIR=str(Path(scratch) / "state"))
            try:
                code, raw = process(argv, turn, env, timeout, stdin)
            finally:
                shutil.copytree(temporary_hooks, hook_dir, dirs_exist_ok=True)
        diagnostic = re.sub(r"\x1b\[[0-9;]*m", "", (turn / "stderr.txt").read_text())
        hook_warnings = [line for line in diagnostic.splitlines()
                         if re.search(r"hook.*(fail|error)|failed.*hook", line, re.I)]
        if tool in ("cursor", "grok"):
            (turn / "prompt.txt").write_text(prompt)
        prior_session = session
        new_session, answer, parsed, reads = extract(events(raw))
        session = new_session or session
        (turn / "answer.txt").write_text(answer if isinstance(answer, str) else json.dumps(answer))
        hook_records = [json.loads(p.read_text()) for p in sorted(hook_dir.glob("hook-*.json"))]
        prompt_records = [r for r in hook_records if r["event"] == "UserPromptSubmit"]
        receipts = [r["receipt"] for r in prompt_records if r["injection_supported"]]
        response = parsed or {}
        checks = {
            "exited_successfully": code == 0,
            "same_session_available": bool(new_session) and (not prior_session or new_session == prior_session),
            "expected_playbook": response.get("playbook") == expected,
            "router_specific_fact": response.get("coding_delegate") == "inherit-parent",
            "fresh_prompt_receipt": response.get("receipt") in receipts if receipts else False,
        }
        turn_result = {"turn": number, "checks": checks, "session_id": session,
                       "expected_playbook": expected, "response": parsed,
                       "read_calls": reads, "hook_records": hook_records,
                       "hook_warnings": hook_warnings,
                       "router_read_observed": any("bstack-router/SKILL.md" in r for r in reads)}
        turns.append(turn_result)
        save(turn / "assessment.json", turn_result)
        print(f"{tool} turn {number}: {json.dumps(checks)}", flush=True)
        if code or not session:
            break
    unchanged = hashlib.sha256(ROUTER.read_bytes()).hexdigest() == before
    all_behavior = len(turns) == len(CASES) and all(
        all(value for key, value in t["checks"].items() if key != "fresh_prompt_receipt") for t in turns)
    delivery = len(turns) == len(CASES) and all(t["checks"]["fresh_prompt_receipt"] for t in turns)
    initial_read = bool(turns and turns[0]["router_read_observed"])
    supported = PROMPT_CONTEXT[tool]
    behavior_pass = all_behavior and unchanged and initial_read
    status = ("pass" if delivery else "incomplete") if supported else "pass_with_limits"
    result = {"tool": tool, "status": status if behavior_pass else "incomplete",
              "routing_pass": all_behavior, "per_prompt_delivery_pass": delivery,
              "per_prompt_delivery_supported": supported,
              "initial_router_read_pass": initial_read,
              "router_unchanged": unchanged, "turns": turns,
              "compaction": "not exercised", "desktop": "not exercised"}
    if tool == "cursor":
        result["note"] = "Cursor prompt hook is observational; session, standing rule, and after-tool fallback are separate paths. Verify the fallback with fallback.py."
    if tool == "grok":
        result["note"] = "Grok uses AGENTS.md; UserPromptSubmit discards additionalContext. Verify its separate native after-tool fallback with fallback.py."
    if not supported:
        result["per_prompt_delivery_pass"] = None
    starts = [r["receipt"] for t in turns for r in t["hook_records"]
              if r.get("event") in ("SessionStart", "sessionStart") and r.get("receipt")]
    result["session_receipt_seen"] = any((t.get("response") or {}).get("receipt") in starts for t in turns)
    save(folder / "report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("doctor", "live"))
    parser.add_argument("--tools", nargs="+", choices=CLIENTS,
                        help="Test these clients; default discovers all installed supported CLIs")
    parser.add_argument("--cursor-bin")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    clients = discover(args.cursor_bin)
    selected = args.tools or [name for name, item in clients.items() if item["installed"]]
    binaries = {name: item["binary"] if item["installed"] else None for name, item in clients.items()}
    if args.action == "doctor":
        report = {"root": str(ROOT), "router_exists": ROUTER.is_file(), "clients": clients,
                  "selected": selected, "authentication": "checked only by live probes"}
        check = subprocess.run(["python3", str(ROOT / "BStack/shared/router/install.py")], capture_output=True, text=True)
        report["adapters_ok"] = check.returncode == 0
        print(json.dumps(report, indent=2))
        return 0 if report["adapters_ok"] and report["router_exists"] else 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    run = ROOT / ".bstack/verification" / stamp
    run.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=max(1, len(selected))) as pool:
        futures = [pool.submit(run_tool, tool, binaries[tool], run, args.timeout) for tool in selected]
        reports = []
        for tool, future in zip(selected, futures):
            try:
                reports.append(future.result())
            except Exception as error:
                reports.append({"tool": tool, "status": "error", "reason": str(error)})
    skipped = [{"tool": name, "status": "skipped", "reason": "CLI not installed"}
               for name, item in clients.items() if not item["installed"] and name not in selected]
    save(run / "report.json", {"run": str(run), "clients": clients, "tools": reports, "skipped": skipped,
                              "scope": "Controlled CLI probes; no desktop or general workflow claim"})
    print(str(run / "report.json"), flush=True)
    return 0 if reports and all(r["status"] in ("pass", "pass_with_limits") for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
