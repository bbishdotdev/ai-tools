#!/usr/bin/env python3
"""Install or check development discovery and hooks without overwriting user entries."""
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


def development_links():
    selection = json.loads((ROOT / "bstack/package/selection.json").read_text())
    skills = {name: "bstack/release/bstack/engineering/" + name for name in selection["skills"]
              if not name.startswith("principle-")}
    skills.update({name: "bstack/" + path for name, path in selection["owned_skills"].items()})
    skills.update({name: "bstack/shared/skills/" + name for name in ("bstack-router", "unslop", "verify-bstack")})
    skills.update({name: "bstack/release/bstack/shared/" + name for name in ("setup-bstack", "bstack-auto")})
    links = {"CLAUDE.md": "AGENTS.md"}
    for host in (".agents", ".claude", ".cursor", ".grok"):
        for name, source in skills.items():
            if not (ROOT / source / "SKILL.md").is_file():
                raise ValueError("Missing development skill; build the release first: " + source)
            links[f"{host}/skills/{name}"] = "../../" + source
    return links


def destination(relative, *, link=False):
    parts = relative.split("/")
    if Path(relative).is_absolute() or any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"Unsafe development destination: {relative}")
    if ROOT.is_symlink() or not ROOT.is_dir():
        raise ValueError(f"Development root must be a real directory: {ROOT}")
    path = ROOT
    for part in parts[:-1]:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"Symlink ancestor would redirect development writes: {path}")
        if path.exists() and not path.is_dir():
            raise ValueError(f"Development destination parent is not a directory: {path}")
    path = path / parts[-1]
    if not link:
        if path.is_symlink():
            raise ValueError(f"Symlink configuration would redirect development writes: {path}")
        if path.exists() and not path.is_file():
            raise ValueError(f"Development destination is not a regular file: {path}")
    return path


def install(apply=False):
    links = development_links()
    configs = configurations()
    for relative in (".codex/config.toml", *configs, ".cursor/rules/bstack-router.mdc"):
        destination(relative)
    for relative, target in links.items():
        path = destination(relative, link=True)
        if (path.exists() or path.is_symlink()) and not (path.is_symlink() and path.readlink() == Path(target)):
            raise ValueError(f"Existing entry would be replaced: {path}")

    writes = {}
    config = ROOT / ".codex/config.toml"
    if not config.exists():
        writes[".codex/config.toml"] = "# Activate this project layer so Codex discovers sibling hooks.json.\n[features]\nhooks = true\n"
    for relative, wanted in configs.items():
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
        if not path.exists() or json.loads(path.read_text()) != current:
            writes[relative] = json.dumps(current, indent=2) + "\n"
    rule = ROOT / ".cursor/rules/bstack-router.mdc"
    if not rule.exists() or rule.read_text() != desired_rule():
        if rule.exists() and rule.read_text() != desired_rule("bstack/engineering/skills/poteto-mode/SKILL.md"):
            raise ValueError(f"Review changed rule before replacing: {rule}")
        writes[".cursor/rules/bstack-router.mdc"] = desired_rule()
    missing_links = {relative: target for relative, target in links.items()
                     if not (ROOT / relative).is_symlink()}
    if apply:
        for relative, text in writes.items():
            path = destination(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        for relative, target in missing_links.items():
            path = destination(relative, link=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)
    return list(writes) + list(missing_links)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changes = install(args.apply)
    print(json.dumps({"applied": args.apply, "changes": changes}, indent=2))
    raise SystemExit(0 if args.apply or not changes else 1)
