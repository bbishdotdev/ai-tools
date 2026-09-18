#!/usr/bin/env python3
"""Emit a small host-native reminder; never inject the router body."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
ROUTER = ROOT / "BStack/shared/skills/bstack-router/SKILL.md"
TEMPLATE = Path(__file__).with_name("reminder.txt")
INJECT_EVENTS = {
    "codex": {"SessionStart", "UserPromptSubmit", "SubagentStart"},
    "claude": {"SessionStart", "UserPromptSubmit", "SubagentStart"},
    "cursor": {"sessionStart", "postToolUse"},
    "grok": {"PostToolUse"},
}
AFTER_TOOL = {"cursor": "postToolUse", "grok": "PostToolUse"}


def identity(host, payload):
    if host == "grok":
        return payload.get("sessionId"), payload.get("promptId")
    return (payload.get("session_id", payload.get("conversation_id")),
            payload.get("turn_id", payload.get("generation_id")))


def event_name(payload, host):
    event = payload.get("hook_event_name", payload.get("hookEventName", ""))
    aliases = {"post_tool_use": "PostToolUse", "user_prompt_submit": "UserPromptSubmit"} if host == "grok" else {}
    return aliases.get(event, event)


def state_connection():
    default = Path(tempfile.gettempdir()) / f"bstack-router-{os.getuid()}"
    directory = Path(os.environ.get("BSTACK_STATE_DIR", default))
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return sqlite3.connect(directory / "turns.sqlite3", timeout=1)


def state_key(*parts):
    return hashlib.sha256(json.dumps([str(ROOT), *parts]).encode()).hexdigest()


def resolve_turn(host, payload):
    session, native = identity(host, payload)
    event = event_name(payload, host)
    if not isinstance(session, str) or not session:
        return session, native, "native"
    grok_boundary = host == "grok" and (event == "UserPromptSubmit" or (event == "PostToolUse" and not native))
    cursor_boundary = host == "cursor" and (event == "sessionEnd" or
                                            (event == "postToolUse" and native == session))
    if not (grok_boundary or cursor_boundary):
        return session, native, "native"
    key = state_key(host, session)
    with state_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE IF NOT EXISTS boundaries (key TEXT PRIMARY KEY, turn TEXT NOT NULL, created REAL NOT NULL)")
        connection.execute("DELETE FROM boundaries WHERE created < ?", (time.time() - 7 * 86400,))
        if host == "cursor" and event == "sessionEnd":
            connection.execute("DELETE FROM boundaries WHERE key = ?", (key,))
            return session, None, "cli_session_end"
        if host == "grok" and event == "UserPromptSubmit":
            if isinstance(native, str) and native:
                connection.execute("INSERT OR REPLACE INTO boundaries VALUES (?, ?, ?)", (key, native, time.time()))
            else:
                # Never retain a previous prompt's identity when a new start lacks it.
                connection.execute("DELETE FROM boundaries WHERE key = ?", (key,))
        if cursor_boundary:
            connection.execute("INSERT OR IGNORE INTO boundaries VALUES (?, ?, ?)", (key, uuid.uuid4().hex, time.time()))
        row = connection.execute("SELECT turn FROM boundaries WHERE key = ?", (key,)).fetchone()
        source = "prompt_submission" if host == "grok" else "cli_session_boundary"
        return session, row[0] if row else None, source


def claim_turn(host, session, turn):
    if not all(isinstance(value, str) and value for value in (session, turn)):
        return "missing_turn_identity"
    key = state_key(host, session, turn)
    with state_connection() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS delivered (key TEXT PRIMARY KEY, created REAL NOT NULL)")
        connection.execute("DELETE FROM delivered WHERE created < ?", (time.time() - 7 * 86400,))
        inserted = connection.execute("INSERT OR IGNORE INTO delivered VALUES (?, ?)", (key, time.time()))
        return None if inserted.rowcount else "duplicate_turn"


def build_output(host, payload, receipt=None):
    event = event_name(payload, host)
    text = TEMPLATE.read_text().strip().format(router_path=ROUTER)
    if receipt:
        label = "After-tool verification receipt" if event == AFTER_TOOL.get(host) else "Verification receipt for this event"
        text += f" {label}: {receipt}."
    if event not in INJECT_EVENTS[host]:
        # Cursor's prompt hook cannot inject context. Its standing rule is the fallback.
        return ({"continue": True} if event == "beforeSubmitPrompt" else {}), None
    if host == "cursor":
        return {"additional_context": text}, text
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}, text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, choices=INJECT_EVENTS)
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("Hook input must be an object")
        if os.environ.get("GROK_HOOK_EVENT") and args.host != "grok":
            # Grok invokes compatible hooks but discards context for these events.
            print("{}")
            return 0
        if not ROUTER.is_file():
            raise ValueError(f"Router missing: {ROUTER}")
        evidence = os.environ.get("BSTACK_VERIFY_DIR")
        observed_at_ns = time.time_ns()
        receipt = uuid.uuid4().hex if evidence else None
        event = event_name(payload, args.host)
        session, turn, turn_source = resolve_turn(args.host, payload)
        after_tool = event == AFTER_TOOL.get(args.host)
        suppressed = claim_turn(args.host, session, turn) if after_tool else None
        output, context = build_output(args.host, payload, receipt)
        if suppressed:
            output, context = {}, None
            if suppressed == "missing_turn_identity":
                print("BStack after-tool reminder skipped: missing session or turn ID", file=sys.stderr)
        if context is None and args.host not in ("cursor", "grok"):
            # Compatible hosts may invoke this file with an unsupported event format.
            print(json.dumps(output))
            return 0
        if evidence:
            destination = Path(evidence)
            destination.mkdir(parents=True, exist_ok=True)
            record = {
                "host": args.host,
                "observed_at_ns": observed_at_ns,
                "event": event,
                "source": payload.get("source"),
                "session_id": session,
                "turn_id": turn,
                "native_turn_id": identity(args.host, payload)[1],
                "turn_source": turn_source,
                "tool_use_id": payload.get("tool_use_id", payload.get("toolUseId")),
                "delivery_kind": "after_tool" if after_tool else "lifecycle",
                "suppressed_reason": suppressed,
                "receipt": receipt if context else None,
                "injection_supported": context is not None,
                "context_chars": len(context or ""),
                "router_sha256": hashlib.sha256(ROUTER.read_bytes()).hexdigest(),
            }
            # One file per event avoids interleaving from concurrent host hooks.
            (destination / f"hook-{receipt}.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(output))
    except (ValueError, OSError, sqlite3.Error) as error:
        print(f"BStack reminder unavailable: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
