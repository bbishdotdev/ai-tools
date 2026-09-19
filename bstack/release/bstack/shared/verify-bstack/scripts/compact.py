#!/usr/bin/env python3
"""Exercise native compaction on an existing disposable verification session."""
import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
import uuid

import verify


def codex_compact(session, folder, env, prompt):
    argv = [shutil.which("codex"), "app-server", "--listen", "stdio://"]
    verify.save(folder / "command.json", argv)
    incoming = queue.Queue()
    messages = []
    with (folder / "stderr.txt").open("w") as err, (folder / "server.jsonl").open("w") as trace:
        child = subprocess.Popen(argv, cwd=verify.ROOT, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=err, text=True, bufsize=1)

        def read():
            for line in child.stdout:
                trace.write(line)
                trace.flush()
                try:
                    incoming.put(json.loads(line))
                except ValueError:
                    pass
            incoming.put(None)

        reader = threading.Thread(target=read, daemon=True)
        reader.start()

        def send(method, params, request_id=None):
            data = {"method": method, "params": params}
            if request_id is not None:
                data["id"] = request_id
            child.stdin.write(json.dumps(data) + "\n")
            child.stdin.flush()

        def until(predicate, timeout=120):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                data = incoming.get(timeout=max(0.1, end - time.monotonic()))
                if data is None:
                    raise RuntimeError("App-server exited before completing the request")
                messages.append(data)
                if "error" in data:
                    raise RuntimeError(str(data["error"]))
                if predicate(data):
                    return data
            raise TimeoutError("Compaction timed out")

        try:
            send("initialize", {"clientInfo": {"name": "bstack_verification", "version": "0.1"},
                                "capabilities": {"experimentalApi": True}}, 1)
            until(lambda m: m.get("id") == 1, 20)
            send("initialized", {})
            send("thread/resume", {"threadId": session, "cwd": str(verify.ROOT),
                                   "sandbox": "read-only", "approvalPolicy": "never"}, 2)
            until(lambda m: m.get("id") == 2, 30)
            send("thread/compact/start", {"threadId": session}, 3)
            until(lambda m: m.get("id") == 3, 20)
            until(lambda m: m.get("method") == "turn/completed", 150)
            # Compact hooks run before the next model request in this process.
            (folder / "prompt.txt").write_text(prompt)
            send("turn/start", {"threadId": session, "input": [{"type": "text", "text": prompt}],
                                "model": "gpt-6-astra", "effort": "medium"}, 4)
            started = until(lambda m: m.get("id") == 4, 30)
            turn_id = started["result"]["turn"]["id"]
            completed = until(lambda m: m.get("method") == "turn/completed" and
                              m.get("params", {}).get("turn", {}).get("id") == turn_id, 180)
        finally:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            reader.join(timeout=3)
    native = any(m.get("method") == "item/completed" and
                 m.get("params", {}).get("item", {}).get("type") == "contextCompaction" for m in messages)
    normalized = [{"thread_id": completed["params"]["threadId"]}]
    for message in messages:
        params = message.get("params", {})
        if message.get("method") != "item/completed" or params.get("turnId") != turn_id:
            continue
        item = dict(params["item"])
        item["type"] = {"agentMessage": "agent_message", "commandExecution": "command_execution"}.get(
            item["type"], item["type"])
        normalized.append({"type": "item.completed", "item": item})
    code = 0 if completed["params"]["turn"]["status"] == "completed" else 1
    return native, code, normalized


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", choices=("codex", "claude"), required=True)
    parser.add_argument("--report", type=Path, required=True, help="The tool-specific report.json from a live run")
    args = parser.parse_args()
    original = json.loads(args.report.read_text())
    session = original["turns"][-1]["session_id"]
    folder = args.report.parent / ("native-compaction-" + uuid.uuid4().hex[:6])
    folder.mkdir()
    env = dict(os.environ, BSTACK_VERIFY_DIR=str(folder / "hooks"))
    binary = shutil.which(args.tool)
    native = False
    prompt = verify.CONTRACT + "\n\n" + verify.CASES[1][1]
    followup = folder / "followup"
    followup.mkdir()
    if args.tool == "codex":
        prompt += " Also include visible_receipts, an array of verification receipts visible in current hook context."
        try:
            native, code, stream = codex_compact(session, folder, env, prompt)
        except Exception as error:
            failure = {"tool": args.tool, "session": session, "status": "error", "reason": str(error)}
            verify.save(folder / "report.json", failure)
            print(json.dumps(failure, indent=2))
            return 1
    else:
        command = verify.cli_command("claude", binary, session)
        code, raw = verify.process(command, folder / "compact-command", env, 180, "/compact")
        native = code == 0 and any(e.get("subtype") == "compact_boundary" for e in verify.events(raw))
        follow_env = dict(os.environ, BSTACK_VERIFY_DIR=str(followup / "hooks"))
        code, raw = verify.process(verify.cli_command(args.tool, binary, session), followup, follow_env, 180, prompt)
        stream = verify.events(raw)
    records = [json.loads(p.read_text()) for p in (folder / "hooks").glob("hook-*.json")]
    compact_records = [r for r in records if r.get("source") == "compact"]
    new_session, answer, parsed, reads = verify.extract(stream)
    (followup / "answer.txt").write_text(answer)
    following = records if args.tool == "codex" else [json.loads(p.read_text()) for p in (followup / "hooks").glob("hook-*.json")]
    receipts = [r["receipt"] for r in following if r["event"] == "UserPromptSubmit"]
    response = parsed or {}
    seen = [response.get("receipt"), *response.get("visible_receipts", [])]
    checks = {"native_compaction_observed": native,
              "compact_reminder_emitted": bool(compact_records),
              "same_session": new_session == session,
              "next_prompt_receipt": any(r in seen for r in receipts),
              "routing_after_compaction": response.get("playbook") == "perf-issue",
              "router_fact_after_compaction": response.get("coding_delegate") == "inherit-parent",
              "exit_success": code == 0}
    if args.tool == "codex":
        checks["compact_receipt_seen"] = any(r["receipt"] in seen for r in compact_records)
    report = {"tool": args.tool, "session": session, "checks": checks,
              "status": "pass" if all(checks.values()) else "incomplete",
              "response": parsed, "read_calls": reads, "compact_hooks": compact_records,
              "note": "Compaction emission and next-turn delivery are separate checks; desktop UI is not exercised."}
    verify.save(folder / "report.json", report)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
