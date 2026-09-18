#!/usr/bin/env python3
"""Verify native after-tool reminders in resumed Cursor and Grok CLI sessions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

from verify import ROOT, ROUTER, CASES, cli_command, discover, events, extract, process, save

HOSTS = ("cursor", "grok")
CONTRACT = (
    "This is a read-only BStack routing and hook probe, not permission to execute the classified task. "
    "Use repository standing guidance and reuse instructions already available. "
    "Do not edit, execute workflows, delegate, access network services, or read verification logs, "
    "hook source, or state databases. Do not invoke verify-bstack or read its files; this probe supplies its own procedure. "
    "Return a JSON object with playbook (filename stem), "
    "coding_delegate (the router's default coding-delegate model policy identifier only, no explanation), values (the two fixture values in order, "
    "or [] on the no-tool turn), and after_tool_receipt. The receipt must be the exact value "
    "labeled 'After-tool verification receipt' in hook context for THIS user turn, or null "
    "if none was delivered. Never substitute a lifecycle receipt or an earlier turn's receipt. "
)


def tool_trace(stream):
    """Count all tool calls, and retain ordering without copying tool result bodies."""
    calls, ends = {}, {}
    for index, event in enumerate(stream):
        if event.get("type") == "tool_call":
            call_id = event.get("call_id", f"unknown-{index}")
            call = event.get("tool_call", {})
            args = call.get("readToolCall", {}).get("args", {})
            entry = calls.setdefault(call_id, {"id": call_id, "start": index,
                                               "path": args.get("path"), "kind": list(call)})
            if event.get("subtype") == "completed":
                ends[call_id] = index
            if event.get("subtype") == "started":
                entry["start"] = index
        elif event.get("type") in ("assistant", "user"):
            for content in event.get("message", {}).get("content", []):
                if content.get("type") == "tool_use":
                    call_id = content.get("id", f"unknown-{index}")
                    args = content.get("input", {})
                    calls[call_id] = {"id": call_id, "start": index, "kind": content.get("name"),
                                      "path": args.get("target_file", args.get("file_path"))}
                elif content.get("type") == "tool_result":
                    ends[content.get("tool_use_id")] = index
    return [dict(call, end=ends.get(call_id)) for call_id, call in calls.items()]


def sequential_reads(trace, first, second):
    return any(a["path"] == str(first) and b["path"] == str(second)
               and a["end"] is not None and a["end"] < b["start"]
               for a in trace for b in trace)


def run_tool(host, binary, run, timeout):
    if not binary:
        return {"tool": host, "status": "blocked", "reason": "CLI executable missing"}
    folder = run / host
    folder.mkdir()
    before = hashlib.sha256(ROUTER.read_bytes()).hexdigest()
    session, turns, seen_receipts, seen_turns = None, [], set(), set()
    # Grok's read-only sandbox permits /tmp writes, but not repository evidence writes.
    # Keep hook state/evidence there during execution; the parent retains evidence below.
    with tempfile.TemporaryDirectory(prefix=f"bstack-{host}-fallback-") as scratch:
        temporary = Path(scratch)
        for number in range(1, 5):
            expected, request = CASES[(number - 1) % len(CASES)]
            no_tools = number == 3
            turn = folder / f"turn-{number}"
            hook_dir = temporary / f"hooks-{number}"
            hook_dir.mkdir()
            values = [] if no_tools else [uuid.uuid4().hex, uuid.uuid4().hex]
            first = temporary / f"first-{uuid.uuid4().hex}.json"
            second = temporary / f"second-{uuid.uuid4().hex}.json"
            if no_tools:
                task = "Use only retained context. Do not call ANY tools on this turn. Return values=[] and after_tool_receipt=null. "
            else:
                save(second, {"value": values[1]})
                save(first, {"value": values[0], "next_file": str(second)})
                task = (f"Read {first} using the native file-read tool. Its next_file field names a second "
                        "file; read that file in a subsequent tool call. Return both values in order. "
                        "Do not search for or list fixture files. Read instruction files only as needed. ")
            prompt = CONTRACT + "\n\n" + task + request
            env = dict(os.environ, BSTACK_VERIFY_DIR=str(hook_dir),
                       BSTACK_STATE_DIR=str(temporary / "state"))
            argv = cli_command(host, binary, session)
            argv.extend(["-p", prompt] if host == "grok" else [prompt])
            try:
                code, raw = process(argv, turn, env, timeout)
            finally:
                turn.mkdir(parents=True, exist_ok=True)
                shutil.copytree(hook_dir, turn / "hooks", dirs_exist_ok=True)
                (turn / "prompt.txt").write_text(prompt)
                save(turn / "fixtures.json", {"first": str(first) if values else None,
                                             "second": str(second) if values else None, "values": values})
            stream = events(raw)
            new_session, answer, parsed, reads = extract(stream)
            trace = tool_trace(stream)
            records = [json.loads(p.read_text()) for p in sorted((turn / "hooks").glob("hook-*.json"))]
            after = [r for r in records if r.get("delivery_kind") == "after_tool" and r["host"] == host]
            emitted = [r for r in after if r.get("receipt")]
            duplicates = [r for r in after if r.get("suppressed_reason") == "duplicate_turn"]
            turn_ids = {r.get("turn_id") for r in after}
            response = parsed or {}
            checks = {
                "exited_successfully": code == 0,
                "same_session": bool(new_session) and (not session or new_session == session),
                "expected_playbook": response.get("playbook") == expected,
                "retained_router_fact": response.get("coding_delegate") == "inherit-parent",
                "correct_fixture_values": response.get("values") == values,
            }
            if host == "grok":
                starts = [r for r in records if r["host"] == host and r["event"] == "UserPromptSubmit"]
                checks["prompt_boundary_observed"] = len(starts) == 1 and bool(starts[0].get("turn_id"))
                checks["prompt_boundary_precedes_tools"] = len(starts) == 1 and all(
                    r.get("turn_id") == starts[0]["turn_id"] and r["observed_at_ns"] > starts[0]["observed_at_ns"] for r in after)
            if host == "cursor":
                ends = [r for r in records if r["host"] == host and r["event"] == "sessionEnd"]
                checks["cli_end_boundary_observed"] = len(ends) == 1
                checks["cli_end_boundary_follows_tools"] = len(ends) == 1 and all(
                    r["observed_at_ns"] < ends[0]["observed_at_ns"] for r in after)
            if no_tools:
                checks.update(no_tool_calls=not trace, no_after_tool_events=not after,
                              no_current_receipt=response.get("after_tool_receipt", "missing") is None)
            else:
                checks.update(
                    dependent_reads_in_order=sequential_reads(trace, first, second),
                    exactly_one_emission=len(emitted) == 1,
                    duplicate_suppression_observed=len(duplicates) >= 1,
                    no_unexpected_suppression=all(r.get("suppressed_reason") in (None, "duplicate_turn") for r in after),
                    fresh_turn_identity=len(turn_ids) == 1 and None not in turn_ids and not (turn_ids & seen_turns),
                    same_hook_session=bool(after) and all(r.get("session_id") == new_session for r in after),
                    fresh_receipt_seen=len(emitted) == 1 and emitted[0]["receipt"] not in seen_receipts
                                       and response.get("after_tool_receipt") == emitted[0]["receipt"],
                )
            seen_turns.update(turn_ids)
            seen_receipts.update(r["receipt"] for r in emitted)
            diagnostic = re.sub(r"\x1b\[[0-9;]*m", "", (turn / "stderr.txt").read_text())
            result = {"turn": number, "kind": "no_tools" if no_tools else "dependent_reads", "checks": checks,
                      "session_id": new_session, "response": parsed, "tool_calls": trace,
                      "router_read_observed": any("bstack-router/SKILL.md" in r for r in reads),
                      "after_tool_events": after, "lifecycle_events": [r for r in records if r not in after],
                      "hook_warnings": [line for line in diagnostic.splitlines()
                                        if re.search(r"hook.*(fail|error)|failed.*hook|BStack.*(skipped|unavailable)", line, re.I)]}
            (turn / "answer.txt").write_text(answer if isinstance(answer, str) else json.dumps(answer))
            save(turn / "assessment.json", result)
            turns.append(result)
            session = new_session or session
            print(f"{host} turn {number}: {json.dumps(checks)}", flush=True)
            if code or not new_session:
                break
    unchanged = hashlib.sha256(ROUTER.read_bytes()).hexdigest() == before
    passed = len(turns) == 4 and unchanged and all(all(t["checks"].values()) for t in turns)
    result = {"tool": host, "status": "pass" if passed else "incomplete", "router_unchanged": unchanged,
              "turns": turns, "scope": "Native after-tool fallback, one resumed CLI conversation",
              "limits": "Standing instructions cover tool-free responses and the first tool call. Cursor headless relies on serial sessionEnd boundaries: hard kills or concurrent use of one conversation can defeat suppression. No per-prompt or desktop guarantee."}
    save(folder / "report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", nargs="+", choices=HOSTS)
    parser.add_argument("--cursor-bin")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    clients = discover(args.cursor_bin)
    selected = args.tools or [host for host in HOSTS if clients[host]["installed"]]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-fallback-" + uuid.uuid4().hex[:6]
    run = ROOT / ".bstack/verification" / stamp
    run.mkdir(parents=True)
    reports = []
    with ThreadPoolExecutor(max_workers=max(1, len(selected))) as pool:
        futures = [pool.submit(run_tool, host, clients[host]["binary"] if clients[host]["installed"] else None,
                               run, args.timeout) for host in selected]
        for host, future in zip(selected, futures):
            try:
                reports.append(future.result())
            except Exception as error:
                reports.append({"tool": host, "status": "error", "reason": str(error)})
    save(run / "report.json", {"run": str(run), "clients": clients, "tools": reports,
                              "skipped": [host for host in HOSTS if host not in selected],
                              "scope": "tool, tool, no-tools, tool; independent Cursor and Grok sessions"})
    print(run / "report.json", flush=True)
    return 0 if reports and all(r["status"] == "pass" for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
