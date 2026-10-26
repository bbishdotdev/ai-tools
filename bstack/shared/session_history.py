#!/usr/bin/env python3
import argparse
from collections import deque
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


HOSTS = ("codex", "claude", "cursor", "grok", "amp")
MAX_BYTES = 2_000_000


def project_slug(project):
    return str(project).lstrip("/").replace("/", "-")


def text_blocks(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (text_blocks(item) for item in value)))
    if isinstance(value, dict):
        if value.get("type") in ("text", "input_text", "output_text"):
            return str(value.get("text", ""))
        return text_blocks(value.get("content", ""))
    return ""


def codex_messages(path):
    for entry in json_lines(path):
        if entry.get("type") != "response_item":
            continue
        message = entry.get("payload", {})
        role = message.get("role")
        if message.get("type") == "message" and role in ("user", "assistant"):
            value = text_blocks(message.get("content", []))
            if value:
                yield {"role": role, "text": value}


def claude_messages(path):
    for entry in json_lines(path):
        role = entry.get("type")
        if role not in ("user", "assistant") or entry.get("isSidechain"):
            continue
        message = entry.get("message", {})
        value = text_blocks(message.get("content", ""))
        if value:
            yield {"role": role, "text": value}


def cursor_messages(path):
    for entry in json_lines(path):
        role = entry.get("role")
        if role not in ("user", "assistant"):
            continue
        value = text_blocks(entry.get("message", ""))
        if value:
            yield {"role": role, "text": value}


def grok_messages(path):
    for entry in json_lines(path):
        role = entry.get("type", "").lower()
        if role not in ("user", "assistant"):
            continue
        value = text_blocks(entry.get("content", ""))
        if value:
            yield {"role": role, "text": value}


READERS = {"codex": codex_messages, "claude": claude_messages,
           "cursor": cursor_messages, "grok": grok_messages}


def json_lines(path):
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                yield value


def session_project(path, host):
    if host == "codex":
        for entry in json_lines(path):
            if entry.get("type") == "session_meta":
                return entry.get("payload", {}).get("cwd")
            break
    if host == "claude":
        for index, entry in enumerate(json_lines(path)):
            if entry.get("cwd"):
                return entry["cwd"]
            if index > 30:
                break
    if host == "grok":
        context = path.parent / "prompt_context.json"
        if context.is_file():
            try:
                return json.loads(context.read_text()).get("working_directory")
            except (OSError, json.JSONDecodeError):
                return None
    return None


def local_candidates(project, host, home):
    slug = project_slug(project)
    if host == "codex":
        candidates = (home / ".codex/sessions").glob("*/*/*/*.jsonl")
    elif host == "claude":
        root = home / ".claude/projects"
        directories = (path for path in root.iterdir() if path.is_dir() and not path.is_symlink()) if root.is_dir() else ()
        candidates = (path for directory in directories for path in directory.glob("*.jsonl"))
    elif host == "cursor":
        candidates = (home / ".cursor/projects" / slug / "agent-transcripts").glob("**/*.jsonl")
    elif host == "grok":
        candidates = (home / ".grok/sessions").glob("*/*/chat_history.jsonl")
    else:
        return
    for path in candidates:
        if not path.is_file() or path.is_symlink() or "subagents" in path.parts:
            continue
        if host in ("codex", "claude", "grok") and session_project(path, host) != str(project):
            continue
        yield path


def amp_threads(limit):
    if not shutil.which("amp"):
        return [], "Amp CLI is unavailable"
    result = subprocess.run(["amp", "threads", "list"], capture_output=True, text=True, timeout=20)
    if result.returncode:
        return [], "Amp could not list threads; check login and CLI access"
    ids = list(dict.fromkeys(re.findall(r"\bT-[a-fA-F0-9-]{16,}\b", result.stdout)))[:limit]
    return ids, None if ids else "Amp returned no recognizable thread IDs"


def amp_markdown(thread_id, window):
    if not re.fullmatch(r"T-[a-fA-F0-9-]{16,}", thread_id):
        raise ValueError("Invalid Amp thread ID")
    result = subprocess.run(["amp", "threads", "markdown", thread_id], capture_output=True,
                            text=True, timeout=30)
    if result.returncode:
        raise ValueError("Amp could not export this thread")
    return result.stdout[:MAX_BYTES] if window == "start" else result.stdout[-MAX_BYTES:]


def list_sessions(project, hosts, days, limit, home):
    after = datetime.now(timezone.utc) - timedelta(days=days)
    sessions, gaps = [], []
    for host in hosts:
        if host == "amp":
            ids, error = amp_threads(limit)
            if error:
                gaps.append({"host": host, "reason": error})
            else:
                for thread_id in ids:
                    sessions.append({"host": host, "id": thread_id, "source": "amp CLI",
                                     "project_match": "unverified", "time_match": "unverified"})
            continue
        root = home / {"codex": ".codex/sessions", "claude": ".claude/projects",
                       "cursor": ".cursor/projects", "grok": ".grok/sessions"}[host]
        if not root.exists():
            gaps.append({"host": host, "reason": "No local session directory"})
            continue
        for path in local_candidates(project, host, home):
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if modified < after:
                continue
            sessions.append({"host": host, "id": path.stem if host != "grok" else path.parent.name,
                             "source": str(path), "modified": modified.isoformat(),
                             "project_match": "verified"})
    sessions.sort(key=lambda item: item.get("modified", ""), reverse=True)
    return {"project": str(project), "sessions": sessions[:limit], "gaps": gaps,
            "scope": {"days": days, "limit": limit, "hosts": hosts,
                      "amp_project_and_time_filter": "unverified" if "amp" in hosts else "not_applicable"}}


def bounded_messages(items, max_chars, window):
    messages, size, truncated = deque(), 0, False
    for item in items:
        value = item["text"]
        if not value:
            continue
        if window == "start":
            remaining = max_chars - size
            if remaining <= 0:
                truncated = True
                break
            messages.append({"role": item["role"], "text": value[:remaining]})
            size += min(len(value), remaining)
            truncated = truncated or len(value) > remaining
            continue
        messages.append({"role": item["role"], "text": value})
        size += len(value)
        while size > max_chars:
            excess = size - max_chars
            first = messages[0]
            if len(first["text"]) <= excess:
                size -= len(first["text"])
                messages.popleft()
            else:
                first["text"] = first["text"][excess:]
                size -= excess
            truncated = True
    return list(messages), truncated


def read_session(project, host, session_id, home, max_chars, allow_unverified_amp=False, window="end"):
    if window not in {"start", "end"}:
        raise ValueError("Session window must be start or end")
    if host == "amp":
        if not allow_unverified_amp:
            raise ValueError("Amp thread project is unverified; confirm this ID belongs to the selected project and pass --allow-unverified-amp")
        transcript = amp_markdown(session_id, window)
        return {"host": host, "id": session_id, "source": "amp CLI",
                "project_match": "unverified", "text": transcript[:max_chars] if window == "start" else transcript[-max_chars:],
                "truncated": len(transcript) > max_chars}
    for path in local_candidates(project, host, home):
        identifier = path.stem if host != "grok" else path.parent.name
        if identifier != session_id:
            continue
        messages, truncated = bounded_messages(READERS[host](path), max_chars, window)
        return {"host": host, "id": session_id, "source": str(path), "messages": messages,
                "truncated": truncated, "window": window}
    raise ValueError("Session is unavailable in the selected project")


def main():
    parser = argparse.ArgumentParser(description="Read scoped agent sessions without copying transcripts")
    parser.add_argument("operation", choices=("list", "read"))
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--hosts", nargs="+", choices=HOSTS, default=list(HOSTS))
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--host", choices=HOSTS)
    parser.add_argument("--id")
    parser.add_argument("--max-chars", type=int, default=30000)
    parser.add_argument("--window", choices=("start", "end"), default="end")
    parser.add_argument("--allow-unverified-amp", action="store_true",
                        help="Read a confirmed Amp thread whose project the CLI cannot verify")
    args = parser.parse_args()
    if args.days < 1 or not 1 <= args.limit <= 500 or not 1 <= args.max_chars <= MAX_BYTES:
        parser.error("Invalid scope")
    project = args.project.resolve()
    if args.operation == "read" and (not args.host or not args.id):
        parser.error("read needs --host and --id")
    result = (list_sessions(project, args.hosts, args.days, args.limit, Path.home())
              if args.operation == "list" else read_session(project, args.host, args.id,
                                                                Path.home(), args.max_chars,
                                                                args.allow_unverified_amp, args.window))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
