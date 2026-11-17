#!/usr/bin/env python3
"""Install or check development discovery and hooks without overwriting user entries."""
import argparse
import json
from pathlib import Path
import shlex
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from host_hooks import configuration

ROOT = Path(__file__).resolve().parents[3]


def command(host):
    if host == "claude":
        return 'python3 "${CLAUDE_PROJECT_DIR}/bstack/shared/router/hook.py" --host claude'
    if host == "codex":
        return 'python3 "$(git rev-parse --show-toplevel)/bstack/shared/router/hook.py" --host codex'
    if host == "grok":
        return 'python3 "${GROK_WORKSPACE_ROOT}/bstack/shared/router/hook.py" --host grok'
    return f"python3 bstack/shared/router/hook.py --host {host}"


def guard_command(host):
    return command(host).replace("bstack/shared/router/hook.py", "bstack/shared/github/pr_guard.py")


def configurations():
    paths = {"codex": ".codex/hooks.json", "claude": ".claude/settings.json",
             "cursor": ".cursor/hooks.json", "grok": ".grok/hooks/bstack.json",
             "copilot": ".github/hooks/bstack.json"}
    return {path: configuration(host, command(host), guard_command(host), True) for host, path in paths.items()}


def plugin_files():
    result = {}
    for host, target, template in (
        ("amp", ".amp/plugins/bstack.ts", "amp-plugin.ts"),
        ("opencode", ".opencode/plugins/bstack.js", "opencode-plugin.js"),
        ("opencode", ".opencode/plugins/bstack/index.js", "opencode-plugin-v2.js"),
    ):
        hook = f"python3 {shlex.quote(str(ROOT / 'bstack/shared/router/hook.py'))} --host {host}"
        guard = f"python3 {shlex.quote(str(ROOT / 'bstack/shared/github/pr_guard.py'))} --host {host}"
        result[target] = (Path(__file__).with_name(template).read_text()
                          .replace("__BSTACK_HOOK__", json.dumps(hook))
                          .replace("__BSTACK_GUARD__", json.dumps(guard))
                          .replace("__BSTACK_AUTO__", "true"))
    return result


def desired_rule(router_path="bstack/shared/skills/bstack-router/SKILL.md"):
    reminder = Path(__file__).with_name("reminder.txt").read_text().strip()
    return ('---\ndescription: bstack engineering router reminder\nalwaysApply: true\n---\n\n'
            + reminder.format(router_path=router_path) + "\n")


def development_skills():
    selection = json.loads((ROOT / "bstack/package/selection.json").read_text())
    skills = {name: "bstack/release/bstack/engineering/" + name for name in selection["skills"]
              if not name.startswith("principle-")}
    skills.update({name: "bstack/" + path for name, path in selection["owned_skills"].items()})
    skills.update({name: "bstack/shared/skills/" + name for name in ("bstack-router", "unslop", "verify-bstack")})
    skills.update({name: "bstack/release/bstack/shared/" + name for name in ("setup-bstack", "bstack-auto")})
    return skills, selection["implicit_skills"]


def development_bindings():
    skills, implicit = development_skills()
    links = {"CLAUDE.md": "AGENTS.md"}
    files, legacy = {}, {}
    for name, source in skills.items():
        body = ROOT / source / "INSTRUCTIONS.md"
        target = source
        if source.startswith("bstack/release/") and body.is_file():
            target = f".bstack/development/skills/{name}"
            text = (f"---\nname: {name}\ndescription: Use bstack's {name} workflow.\n"
                    f"disable-model-invocation: {str(name not in implicit).lower()}\n---\n\n"
                    f"Read `{ROOT / 'bstack/shared/skills/bstack-router/SKILL.md'}` and `{body}` in full. "
                    f"Follow the workflow under bstack's policy, resolving its references from `{body.parent}`.\n")
            files[target + "/SKILL.md"] = text
            files[target + "/agents/openai.yaml"] = f"policy:\n  allow_implicit_invocation: {str(name in implicit).lower()}\n"
        elif not (ROOT / source / "SKILL.md").is_file():
            raise ValueError("Missing development skill; build the release first: " + source)
        for host in (".agents", ".claude", ".cursor", ".grok"):
            relative = f"{host}/skills/{name}"
            links[relative] = "../../" + target
            if target != source:
                legacy[relative] = "../../" + source
    return links, files, legacy


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


def install(apply=False, configs_only=False):
    links, wrappers, legacy = ({}, {}, {}) if configs_only else development_bindings()
    configs = configurations()
    plugins = {} if configs_only else plugin_files()
    rules = () if configs_only else (".cursor/rules/bstack-router.mdc",)
    for relative in (".codex/config.toml", *configs, *plugins, *wrappers, *rules):
        destination(relative)
    for relative, target in links.items():
        path = destination(relative, link=True)
        if (path.exists() or path.is_symlink()) and not (path.is_symlink() and str(path.readlink()) in (target, legacy.get(relative))):
            raise ValueError(f"Existing entry would be replaced: {path}")

    writes = {}
    for relative, source in {**plugins, **wrappers}.items():
        path = destination(relative)
        if path.exists() and path.read_text() != source:
            raise ValueError(f"Review changed plugin before replacing: {path}")
        if not path.exists():
            writes[relative] = source
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
                own = [g for g in existing if any(name in json.dumps(g) for name in
                       ("bstack/shared/router/hook.py", "bstack/shared/github/pr_guard.py"))]
                if own:
                    raise ValueError(f"Review changed bstack hook instead of duplicating: {path}:{event}")
                existing.extend(groups)
        if not path.exists() or json.loads(path.read_text()) != current:
            writes[relative] = json.dumps(current, indent=2) + "\n"
    for relative in rules:
        rule = ROOT / relative
        if not rule.exists() or rule.read_text() != desired_rule():
            if rule.exists() and rule.read_text() != desired_rule("bstack/engineering/skills/poteto-mode/SKILL.md"):
                raise ValueError(f"Review changed rule before replacing: {rule}")
            writes[relative] = desired_rule()
    missing_links = {relative: target for relative, target in links.items()
                     if not (ROOT / relative).is_symlink() or (ROOT / relative).readlink() != Path(target)}
    if apply:
        for relative, text in writes.items():
            path = destination(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        for relative, target in missing_links.items():
            path = destination(relative, link=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                path.unlink()
            path.symlink_to(target)
    return list(writes) + list(missing_links)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--configs-only", action="store_true", help="Check or repair portable host configuration without skill or plugin changes")
    args = parser.parse_args()
    changes = install(args.apply, args.configs_only)
    print(json.dumps({"applied": args.apply, "changes": changes}, indent=2))
    raise SystemExit(0 if args.apply or not changes else 1)
