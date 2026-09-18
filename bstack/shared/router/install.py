#!/usr/bin/env python3
"""Install or check this POC's repository-local adapters without overwriting others."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def command(host):
    if host == "claude":
        return 'python3 "${CLAUDE_PROJECT_DIR}/bstack/shared/router/hook.py" --host claude'
    if host == "codex":
        return 'python3 "$(git rev-parse --show-toplevel)/bstack/shared/router/hook.py" --host codex'
    if host == "grok":
        return 'python3 "${GROK_WORKSPACE_ROOT}/bstack/shared/router/hook.py" --host grok'
    return "python3 bstack/shared/router/hook.py --host cursor"


def configurations():
    result = {}
    for host, path in (("codex", ".codex/hooks.json"), ("claude", ".claude/settings.json")):
        handler = {"type": "command", "command": command(host), "timeout": 5}
        events = {name: [{"hooks": [handler.copy()]}] for name in
                  ("SessionStart", "UserPromptSubmit", "SubagentStart")}
        result[path] = {"hooks": events}
    result[".cursor/hooks.json"] = {"version": 1, "hooks": {
        name: [{"command": command("cursor"), "timeout": 5}]
        for name in ("sessionStart", "sessionEnd", "beforeSubmitPrompt", "preCompact", "postToolUse")
    }}
    result[".grok/hooks/bstack.json"] = {"hooks": {name: [{"hooks": [
        {"type": "command", "command": command("grok"), "timeout": 5}
    ]}] for name in ("UserPromptSubmit", "PostToolUse")}}
    return result


def desired_rule(router_path="bstack/shared/skills/bstack-router/SKILL.md"):
    reminder = Path(__file__).with_name("reminder.txt").read_text().strip()
    return ('---\ndescription: bstack engineering router reminder\nalwaysApply: true\n---\n\n'
            + reminder.format(router_path=router_path) + "\n")


def install(apply=False):
    errors = []
    config = ROOT / ".codex/config.toml"
    if not config.exists():
        errors.append(".codex/config.toml")
        if apply:
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text("# Activate this project layer so Codex discovers sibling hooks.json.\n[features]\nhooks = true\n")
    for relative, wanted in configurations().items():
        path = ROOT / relative
        current = json.loads(path.read_text()) if path.exists() else {}
        for key, value in wanted.items():
            if key != "hooks":
                current.setdefault(key, value)
        hooks = current.setdefault("hooks", {})
        for event, groups in wanted["hooks"].items():
            existing = hooks.setdefault(event, [])
            if groups[0] not in existing:
                own = [g for g in existing if "bstack/shared/router/hook.py" in json.dumps(g)]
                if own:
                    raise ValueError(f"Review changed bstack hook instead of duplicating: {path}:{event}")
                existing.extend(groups)
        expected = json.dumps(current, indent=2) + "\n"
        if not path.exists() or json.loads(path.read_text()) != current:
            errors.append(relative)
            if apply:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(expected)
    rule = ROOT / ".cursor/rules/bstack-router.mdc"
    if not rule.exists() or rule.read_text() != desired_rule():
        errors.append(str(rule.relative_to(ROOT)))
        if apply:
            if rule.exists() and rule.read_text() != desired_rule("bstack/engineering/skills/poteto-mode/SKILL.md"):
                raise ValueError(f"Review changed rule before replacing: {rule}")
            rule.parent.mkdir(parents=True, exist_ok=True)
            rule.write_text(desired_rule())
    links = {"CLAUDE.md": "AGENTS.md"}
    for host in (".agents", ".claude", ".cursor"):
        for skill in ("bstack-router", "unslop", "verify-bstack"):
            links[f"{host}/skills/{skill}"] = f"../../bstack/shared/skills/{skill}"
    for relative, target in links.items():
        path = ROOT / relative
        if path.is_symlink() and path.readlink() == Path(target):
            continue
        if path.exists() or path.is_symlink():
            raise ValueError(f"Existing entry would be replaced: {path}")
        errors.append(relative)
        if apply:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changes = install(args.apply)
    print(json.dumps({"applied": args.apply, "changes": changes}, indent=2))
    raise SystemExit(0 if args.apply or not changes else 1)
