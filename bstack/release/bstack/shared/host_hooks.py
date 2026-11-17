def configuration(host, reminder, guard, auto, events=None):
    if host in ("codex", "claude", "grok"):
        hooks = {"PreToolUse": [{"matcher": "Bash", "hooks": [
            {"type": "command", "command": guard, "timeout": 5}]}]}
        if auto:
            names = (("UserPromptSubmit", "PostToolUse") if host == "grok" else
                     ("SessionStart", "UserPromptSubmit", "SubagentStart"))
            hooks.update({name: [{"hooks": [{"type": "command", "command": reminder, "timeout": 5}]}]
                          for name in names})
        return {"hooks": hooks}
    if host == "cursor":
        hooks = {"beforeShellExecution": [{"command": guard, "timeout": 5}],
                 "preToolUse": [{"matcher": "Shell", "command": guard, "timeout": 5}]}
        if auto:
            hooks.update({name: [{"command": reminder, "timeout": 5}] for name in
                          ("sessionStart", "sessionEnd", "beforeSubmitPrompt", "preCompact", "postToolUse")})
        return {"version": 1, "hooks": hooks}
    if host == "copilot":
        hooks = {"preToolUse": [{"type": "command", "bash": guard, "timeoutSec": 5}]}
        if auto:
            hooks.update({event: [{"type": "command", "bash": command, "timeoutSec": 5}]
                          for event, command in (events or {}).items()})
        return {"version": 1, "hooks": hooks}
    raise ValueError(f"Unsupported hook host: {host}")
