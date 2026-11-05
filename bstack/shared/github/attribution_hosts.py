from datetime import datetime
import json
import os
from pathlib import Path
import re
import time

from attribution import reported, unavailable


MAX_BYTES = 16 * 1024 * 1024
ID = re.compile(r"[A-Za-z0-9_-]{1,160}")


def records(path, tail=True, limit=MAX_BYTES):
    with Path(path).open("rb") as handle:
        handle.seek(0, 2)
        start = max(0, handle.tell() - limit) if tail else 0
        handle.seek(start)
        if start:
            handle.readline()
        data = handle.read(limit)
    for line in data.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except (ValueError, UnicodeError):
            continue
        if isinstance(value, dict):
            yield value


def field(payload, *names):
    return next((payload[name] for name in names if payload.get(name) is not None), None)


def identity(payload):
    session = field(payload, "session_id", "sessionId", "conversation_id", "sessionID", "threadId")
    call = field(payload, "tool_use_id", "toolUseId", "toolCallId", "callID", "toolUseID")
    return session, call


def unique(host, models, evidence="response-model"):
    models = set(models)
    if len(models) > 1:
        return unavailable(host, "ambiguous_model_evidence")
    return reported(host, next(iter(models), None), evidence)


def same_path(left, right):
    return isinstance(left, str) and isinstance(right, str) and Path(left).resolve() == Path(right).resolve()


def claude(payload):
    session, call = identity(payload)
    transcript = field(payload, "transcript_path", "transcriptPath")
    if not session or not call or not transcript:
        return unavailable("claude", "missing_tool_identity")
    path = Path(transcript)
    agent = field(payload, "agent_id", "agentId")
    if agent:
        if not isinstance(agent, str) or not ID.fullmatch(agent):
            return unavailable("claude", "invalid_agent_identity")
        if path.name != f"agent-{agent}.jsonl":
            path = path.with_suffix("") / "subagents" / f"agent-{agent}.jsonl"
    models = []
    for record in records(path):
        if record.get("type") != "assistant" or record.get("sessionId") != session:
            continue
        if record.get("agentId") not in (None, agent) or not same_path(record.get("cwd"), payload.get("cwd")):
            continue
        message = record.get("message", {})
        if any(block.get("type") == "tool_use" and block.get("id") == call for block in message.get("content", [])
               if isinstance(block, dict)):
            models.append(message.get("model"))
    return unique("claude", models)


def grok(payload):
    session, call = identity(payload)
    transcript = field(payload, "transcript_path", "transcriptPath")
    if not session or not call or not transcript:
        return unavailable("grok", "missing_tool_identity")
    path = Path(transcript)
    if path.parent.name != session:
        return unavailable("grok", "session_mismatch")
    linked = any(record.get("params", {}).get("sessionId") == session and
                 record.get("params", {}).get("update", {}).get("toolCallId") == call for record in records(path))
    if not linked:
        return unavailable("grok", "tool_call_not_persisted")
    models = [record.get("model_id") for record in records(path.with_name("chat_history.jsonl"))
              if record.get("type") == "assistant" and any(tool.get("id") == call for tool in record.get("tool_calls", []))]
    return unique("grok", models)


def milliseconds(value):
    if isinstance(value, (float, int)):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000
    return None


def arguments(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def copilot(payload):
    session, call = identity(payload)
    tool = field(payload, "tool_name", "toolName")
    if tool in ("run_in_terminal", "copilot_run_in_terminal"):
        model = field(payload, "model_id", "model")
        return reported("copilot", model, "selected-model") if model else unavailable(
            "copilot", "vscode_model_not_exposed_during_tool_call")
    if not isinstance(session, str) or not ID.fullmatch(session):
        return unavailable("copilot", "missing_session_identity")
    path = Path(os.environ.get("COPILOT_HOME", Path.home() / ".copilot")) / "session-state" / session / "events.jsonl"
    cutoff = milliseconds(payload.get("timestamp"))
    if cutoff is None:
        return unavailable("copilot", "missing_hook_timestamp")
    command = arguments(field(payload, "tool_input", "toolInput", "toolArgs")).get("command")
    agent = field(payload, "agent_id", "agentId")
    pending, started, complete = {}, set(), set()
    header = next(records(path, tail=False, limit=65536), {})
    session_data = header.get("data", {})
    scoped = (header.get("type") == "session.start" and session_data.get("sessionId") == session and
              same_path(session_data.get("context", {}).get("cwd"), payload.get("cwd")))
    for record in records(path):
        when = milliseconds(record.get("timestamp"))
        if when is None or when > cutoff:
            continue
        data, event = record.get("data", {}), record.get("type")
        if data.get("agentId") != agent:
            continue
        if event == "assistant.message":
            for request in data.get("toolRequests", []):
                request_id = request.get("toolCallId")
                if request_id and request.get("name") in (tool, "bash" if tool == "Bash" else tool):
                    if arguments(request.get("arguments")).get("command") == command:
                        pending[request_id] = data.get("model")
        elif event == "tool.execution_start":
            started.add(data.get("toolCallId"))
        elif event in ("tool.execution_complete", "tool.execution_error"):
            complete.add(data.get("toolCallId"))
    if not scoped:
        return unavailable("copilot", "session_mismatch")
    candidates = {key: value for key, value in pending.items() if key in started and key not in complete and (not call or key == call)}
    if len(candidates) != 1:
        return unavailable("copilot", "ambiguous_active_tool_call" if candidates else "tool_call_not_persisted")
    return unique("copilot", candidates.values())


def native_plugin(host, payload):
    session, call = identity(payload)
    if not session or not call:
        return unavailable(host, "missing_tool_identity")
    return reported(host, payload.get("response_model"), "selected-model" if host == "opencode" else "response-model")


READERS = {"claude": claude, "grok": grok, "copilot": copilot}


def capture(host, payload):
    session, call = identity(payload)
    if host in ("codex", "cursor"):
        if not session or not call:
            return unavailable(host, "missing_tool_identity")
        return reported(host, field(payload, "model_id", "model"), "selected-model")
    if host in ("amp", "opencode"):
        return native_plugin(host, payload)
    reader = READERS[host]
    result = unavailable(host, "model_not_exposed")
    for delay in (0, 0.1, 0.25):
        if delay:
            time.sleep(delay)
        try:
            result = reader(payload)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            result = unavailable(host, "native_evidence_unavailable")
        if result.model or result.reason not in ("model_not_exposed", "tool_call_not_persisted", "native_evidence_unavailable"):
            break
    return result
