#!/usr/bin/env python3
"""Install and configure the bstack package for one local project."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import sys
import tempfile
import tomllib

SCHEMA = 1
HOSTS = ("codex", "claude", "cursor", "grok")
STATE = ".bstack/config.json"
PACKAGE = ".bstack/package"
BEGIN = "<!-- bstack:begin -->"
END = "<!-- bstack:end -->"
RELOAD = "Start a fresh agent session after these bstack binding or package changes. Existing conversation context is not erased."


class Conflict(ValueError):
    pass


def session_guidance(auto, hosts, changed=False):
    codex_hooks = auto and "codex" in hosts
    notices = [RELOAD] if changed else []
    if codex_hooks:
        notices.append("Codex hook trust was not checked. To review it, open `codex` in a terminal in this project, "
                       "then run `/hooks` inside the Codex terminal CLI. `/hooks` in desktop chat is not the same command. "
                       "Setup does not grant trust, and configuration does not prove live hook delivery.")
    return {"fresh_session_required": changed,
            "native_hook_trust": "not_checked" if codex_hooks else "not_applicable",
            "notice": " ".join(notices)}


def capsule_root():
    return Path(__file__).resolve().parent.parent


def read_json(path):
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise Conflict(f"Cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise Conflict(f"Expected a JSON object: {path}")
    return value


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_check(capsule, legacy=False):
    manifest = read_json(capsule / "manifest.json")
    errors = []
    version = manifest.get("schema_version")
    if manifest.get("name") != "bstack" or version != 2 and not (legacy and version == 1):
        errors.append("Unsupported bstack package manifest")
    files = manifest.get("files")
    if not isinstance(files, list):
        raise Conflict("Package manifest needs a files array")
    seen = set()
    for entry in files:
        relative = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            errors.append(f"Invalid package path: {relative!r}")
            continue
        if relative in seen:
            errors.append(f"Duplicate package path: {relative}")
        seen.add(relative)
        path = capsule / relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(capsule.resolve()):
            errors.append(f"Missing or unsafe package file: {relative}")
        elif digest(path) != entry.get("sha256"):
            errors.append(f"Package content changed: {relative}")
        elif "mode" in entry:
            mode = entry["mode"]
            expected = int(mode, 8) if isinstance(mode, str) else mode
            if stat.S_IMODE(path.stat().st_mode) != expected:
                errors.append(f"Package file mode changed: {relative}")
    actual = {str(p.relative_to(capsule)) for p in capsule.rglob("*") if p.is_file() or p.is_symlink()}
    extras = actual - seen - {"manifest.json"}
    if extras:
        errors.append("Unlisted package files: " + ", ".join(sorted(extras)))
    entrypoints = manifest.get("entrypoints", {})
    if not isinstance(entrypoints, dict):
        entrypoints = {}
    required = ("router",) if version == 1 else ("router", "unslop", "mode", "controller", "reminder", "index", "setup", "verification")
    for name in required:
        relative = entrypoints.get(name)
        if not isinstance(relative, str) or relative not in seen:
            errors.append(f"Manifest {name} entrypoint must identify a hashed package file")
    if version == 2:
        public = manifest.get("public_skills")
        if not isinstance(public, dict) or not public:
            errors.append("Manifest needs a public_skills object")
        else:
            paths = set()
            for name, skill in public.items():
                if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
                    errors.append(f"Invalid public skill name: {name!r}")
                if not isinstance(skill, dict):
                    errors.append(f"Invalid public skill: {name!r}")
                    continue
                relative = skill.get("path")
                if not isinstance(relative, str) or relative not in seen or not relative.endswith("/SKILL.md"):
                    errors.append(f"Public skill must identify a hashed SKILL.md: {name}")
                elif relative in paths:
                    errors.append(f"Duplicate public skill path: {relative}")
                else:
                    paths.add(relative)
                if not isinstance(skill.get("description"), str) or not skill["description"].strip():
                    errors.append(f"Public skill needs a description: {name}")
                if not isinstance(skill.get("implicit"), bool) or skill["implicit"] != (name == "unslop"):
                    errors.append(f"Only unslop may be implicitly invoked: {name}")
            for name, entrypoint in (("poteto-mode", "mode"), ("unslop", "unslop"), ("setup-bstack", "setup"), ("verify-bstack", "verification")):
                if not isinstance(public.get(name), dict) or public[name].get("path") != entrypoints.get(entrypoint):
                    errors.append(f"Public skill does not match its entrypoint: {name}")
            if "bstack-auto" not in public:
                errors.append("Missing public skill: bstack-auto")
    if errors:
        raise Conflict("; ".join(errors))
    return manifest


def safe_path(project, relative, follow_leaf=False):
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise Conflict(f"Unsafe managed path: {relative}")
    path = project / relative
    resolved = path.resolve() if follow_leaf else path.parent.resolve() / path.name
    if not resolved.is_relative_to(project):
        raise Conflict(f"Refusing to write outside project through a symlink: {path}")
    return resolved if follow_leaf else path


def state_read(project):
    path = safe_path(project, STATE)
    if not path.exists():
        return None
    if path.is_symlink():
        raise Conflict(f"State file must not be a symlink: {path}")
    state = read_json(path)
    if state.get("schema") != SCHEMA or not isinstance(state.get("managed"), dict):
        raise Conflict(f"Unsupported or malformed bstack state: {path}")
    if not isinstance(state.get("auto"), bool) or not isinstance(state.get("hosts"), list) or any(h not in HOSTS for h in state["hosts"]):
        raise Conflict(f"Malformed bstack mode or host settings: {path}")
    return state


def snapshot(path):
    if path.is_symlink():
        return {"kind": "link", "target": os.readlink(path)}
    if path.exists():
        if not path.is_file():
            raise Conflict(f"Expected a file, found another object: {path}")
        return {"kind": "file", "data": path.read_bytes(), "mode": stat.S_IMODE(path.stat().st_mode)}
    return None


def text_snapshot(value, path):
    if value is None:
        return ""
    if value["kind"] != "file":
        raise Conflict(f"Refusing to replace unmanaged symlink: {path}")
    try:
        return value["data"].decode()
    except UnicodeDecodeError as error:
        raise Conflict(f"Expected a UTF-8 text file: {path}") from error


def marker_block(body, style="markdown"):
    begin, end = (BEGIN, END) if style == "markdown" else ("# bstack:begin", "# bstack:end")
    return f"{begin}\n{body.rstrip()}\n{end}\n"


def without_block(text, record, path):
    block = record["text"]
    if text.count(block) != 1:
        raise Conflict(f"Managed bstack block changed or disappeared: {path}")
    return text.replace(block, "", 1)


def insert_block(text, record, path):
    block = record["text"]
    if "bstack:begin" in text or "bstack:end" in text:
        raise Conflict(f"Unowned or malformed bstack block: {path}")
    anchor = record.get("anchor")
    if anchor:
        matches = list(re.finditer(r"^\s*" + re.escape(anchor) + r"\s*(?:#.*)?$", text, re.MULTILINE))
        if len(matches) != 1:
            raise Conflict(f"Cannot identify TOML section {anchor}: {path}")
        position = matches[0].end()
        suffix = text[position:]
        return text[:position] + "\n" + block + (suffix[1:] if suffix.startswith("\n") else suffix)
    if text and not text.endswith("\n"):
        record["text"] = "\n" + block
    return text + record["text"]


def wrapper(name, description, body, manual=True):
    return (f"---\nname: {name}\ndescription: {json.dumps(description)}\ndisable-model-invocation: {str(manual).lower()}\n"
            "metadata:\n  package: bstack\n---\n\n" + body.rstrip() + "\n")


def build_records(project, capsule, hosts, auto, old, manifest=None):
    manifest = manifest or package_check(capsule)
    router = capsule / manifest["entrypoints"]["router"]
    unslop = capsule / manifest["entrypoints"]["unslop"]
    script = capsule / manifest["entrypoints"]["controller"]
    invocation = f"python3 {shlex.quote(str(script))}"
    project_arg = f"--project {shlex.quote(str(project))}"
    records = {}

    def add(relative, value, instructions=False):
        path = safe_path(project, relative, follow_leaf=instructions)
        key = str(path.relative_to(project))
        if key in records and records[key] != value:
            raise Conflict(f"Conflicting generated bindings: {key}")
        records[key] = value

    for name, skill in manifest["public_skills"].items():
        source = capsule / skill["path"]
        body = (f"Read `{source}` in full and follow it. Resolve its bundled references from `{source.parent}`, "
                "not this generated entry directory.\n\n"
                f"This entry selects `{name}` and the dependencies needed for the user's requested deliverable. "
                "Keep that scope. Invoking a planning, explanation, or review skill does not authorize implementation.\n")
        text = wrapper(name, skill["description"], body, manual=not skill["implicit"])
        add(f".agents/skills/{name}/SKILL.md", {"kind": "file", "text": text})
        add(f".agents/skills/{name}/agents/openai.yaml", {"kind": "file", "text": f"policy:\n  allow_implicit_invocation: {str(skill['implicit']).lower()}\n"})
    for host in hosts:
        directory = {"claude": ".claude", "cursor": ".cursor", "grok": ".grok"}.get(host)
        if directory:
            for name in manifest["public_skills"]:
                if (project / directory / "skills").resolve() == (project / ".agents/skills").resolve():
                    continue
                add(f"{directory}/skills/{name}", {"kind": "link", "target": f"../../.agents/skills/{name}"})

    instruction = f"Apply `{unslop}` to prose. Read it when its instructions are unavailable.\n"
    if auto:
        instruction += (f"Use `{router}` as the engineering router. Read it in full before substantive engineering work, "
                        "reuse available instructions, and reread after compaction if missing. Continue the active workflow. "
                        "Preserve the router path, active workflow, and next step when compacting.\n")
    else:
        instruction += ("Engineering routing is manual. Load an engineering skill and its needed dependencies only "
                        "when the user explicitly invokes that bstack skill. Poteto Mode selects the engineering router; "
                        "other entries select their named workflow within the user's requested scope. Continue an "
                        "explicitly invoked workflow across turns. Otherwise follow ordinary project guidance without "
                        "activating bstack engineering workflows.\n")
    add(".bstack/instructions.md", {"kind": "file", "text": "# bstack project instructions\n\n" + instruction})
    pointer = "Read and follow `.bstack/instructions.md` for bstack project instructions. Resolve this path from the project root.\n"
    add("AGENTS.md", {"kind": "block", "text": marker_block(pointer), "adopt": True}, instructions=True)
    if "claude" in hosts:
        add("CLAUDE.md", {"kind": "block", "text": marker_block(pointer), "adopt": True}, instructions=True)
    if "cursor" in hosts:
        rule = "---\ndescription: bstack prose and optional engineering routing\nalwaysApply: true\n---\n\n" + pointer
        add(".cursor/rules/bstack.mdc", {"kind": "file", "text": rule})
    ignore_path = safe_path(project, ".gitignore", follow_leaf=True)
    ignore_key = str(ignore_path.relative_to(project))
    ignore_text = text_snapshot(snapshot(ignore_path), ignore_path)
    if ignore_key in old or "bstack:begin" in ignore_text or "bstack:end" in ignore_text or not re.search(r"(?m)^/?\.bstack/$", ignore_text):
        add(".gitignore", {"kind": "block", "text": marker_block(".bstack/", "shell"), "adopt": True}, instructions=True)

    if auto:
        for host in hosts:
            command = f"{invocation} hook --host {host} {project_arg}"
            if host in ("codex", "claude"):
                events = ("SessionStart", "UserPromptSubmit", "SubagentStart")
                handler = {"hooks": [{"type": "command", "command": command, "timeout": 5}]}
                target = ".codex/hooks.json" if host == "codex" else ".claude/settings.json"
                add(target, {"kind": "json", "entries": {e: [handler] for e in events}, "defaults": {}})
            elif host == "cursor":
                events = ("sessionStart", "sessionEnd", "beforeSubmitPrompt", "preCompact", "postToolUse")
                handler = {"command": command, "timeout": 5}
                add(".cursor/hooks.json", {"kind": "json", "entries": {e: [handler] for e in events}, "defaults": {"version": 1}})
            else:
                handler = {"hooks": [{"type": "command", "command": command, "timeout": 5}]}
                add(".grok/hooks/bstack.json", {"kind": "json", "entries": {e: [handler] for e in ("UserPromptSubmit", "PostToolUse")}, "defaults": {}})
        if "codex" in hosts:
            relative = ".codex/config.toml"
            path = safe_path(project, relative)
            content = text_snapshot(snapshot(path), path)
            previous = old.get(relative)
            if previous:
                content = without_block(content, previous, path)
            try:
                parsed = tomllib.loads(content)
            except tomllib.TOMLDecodeError as error:
                raise Conflict(f"Malformed Codex TOML: {error}") from error
            features = parsed.get("features", {})
            if not isinstance(features, dict):
                raise Conflict("Codex features must be a TOML table")
            if features.get("hooks") is False:
                raise Conflict("Codex configuration explicitly disables hooks; enable that setting before opting in")
            if features.get("hooks") is not True:
                if "features" in parsed:
                    add(relative, {"kind": "block", "text": marker_block("hooks = true", "shell"), "anchor": "[features]"})
                else:
                    add(relative, {"kind": "block", "text": marker_block("[features]\nhooks = true", "shell")})
    return records


def json_reconcile(content, previous, wanted, path):
    try:
        obj = json.loads(content) if content else {}
    except json.JSONDecodeError as error:
        raise Conflict(f"Malformed host JSON {path}: {error}") from error
    if not isinstance(obj, dict):
        raise Conflict(f"Host configuration must be an object: {path}")
    preserve_empty = previous.get("preserve_empty", False) if previous else bool(content)
    preserve_hooks = previous.get("preserve_hooks", False) if previous else "hooks" in obj
    hooks = obj.get("hooks", {})
    if not isinstance(hooks, dict) or any(not isinstance(v, list) for v in hooks.values()):
        raise Conflict(f"Host hooks must map events to arrays: {path}")
    if previous:
        for event, entries in previous["entries"].items():
            actual = hooks.get(event, [])
            for entry in entries:
                if actual.count(entry) != 1:
                    raise Conflict(f"Managed hook changed or disappeared: {path}:{event}")
                actual.remove(entry)
            if not actual:
                hooks.pop(event, None)
        for key, value in previous.get("owned_defaults", {}).items():
            if obj.get(key) != value:
                raise Conflict(f"Managed configuration key changed: {path}:{key}")
            if not (hooks and key == "version"):
                obj.pop(key)
    if wanted:
        wanted["preserve_empty"] = preserve_empty
        wanted["preserve_hooks"] = preserve_hooks
        owned_defaults = {}
        for key, value in wanted.get("defaults", {}).items():
            if key not in obj:
                obj[key] = value
                owned_defaults[key] = value
            elif obj[key] != value:
                raise Conflict(f"Unsupported host configuration version: {path}:{key}")
        wanted["owned_defaults"] = owned_defaults
        for event, entries in wanted["entries"].items():
            actual = hooks.setdefault(event, [])
            for entry in entries:
                if entry in actual:
                    raise Conflict(f"An unowned identical bstack hook exists: {path}:{event}")
                actual.append(entry)
    if hooks or preserve_hooks:
        obj["hooks"] = hooks
    else:
        obj.pop("hooks", None)
    return json.dumps(obj, indent=2, sort_keys=True) + "\n" if obj or preserve_empty else None


def reconcile(project, previous, desired):
    changes = {}
    for relative in sorted(set(previous) | set(desired)):
        path = safe_path(project, relative)
        before = snapshot(path)
        old, new = previous.get(relative), desired.get(relative)
        kind = (old or new)["kind"]
        if old and new and old["kind"] != new["kind"]:
            raise Conflict(f"Managed binding type changed: {relative}")
        if kind == "link":
            if old and before != {"kind": "link", "target": old["target"]}:
                raise Conflict(f"Managed skill link changed or disappeared: {path}")
            if not old and before is not None:
                raise Conflict(f"Existing skill entry would be replaced: {path}")
            after = {"kind": "link", "target": new["target"]} if new else None
        else:
            text = text_snapshot(before, path)
            if kind == "file":
                if old and text != old["text"]:
                    raise Conflict(f"Managed file changed or disappeared: {path}")
                if not old and before is not None:
                    raise Conflict(f"Existing file would be replaced: {path}. Restore this project's .bstack/config.json ownership state or explicitly resolve the collision before setup; copied machine-specific bindings are not adopted automatically")
                output = new["text"] if new else None
            elif kind == "block":
                if old:
                    text = without_block(text, old, path)
                elif new and new.get("adopt") and text.count(new["text"]) == 1:
                    text = without_block(text, new, path)
                output = insert_block(text, new, path) if new else (text or None)
            elif kind == "json":
                output = json_reconcile(text, old, new, path)
            else:
                raise Conflict(f"Unknown managed binding: {kind}")
            after = {"kind": "file", "data": output.encode(), "mode": before.get("mode", 0o644) if before else 0o644} if output is not None else None
        if before != after:
            changes[relative] = (before, after)
    return changes


def replace(path, value):
    if value is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".bstack-", dir=path.parent)
    temp = Path(temporary)
    try:
        if value["kind"] == "link":
            os.close(fd)
            temp.unlink()
            temp.symlink_to(value["target"])
        else:
            with os.fdopen(fd, "wb") as output:
                output.write(value["data"])
                output.flush()
                os.fsync(output.fileno())
            temp.chmod(value["mode"])
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def apply(project, changes):
    written = []
    try:
        for relative, (before, after) in changes.items():
            path = safe_path(project, relative)
            if snapshot(path) != before:
                raise Conflict(f"File changed during configuration: {path}")
            replace(path, after)
            written.append((path, before))
    except Exception:
        for path, before in reversed(written):
            replace(path, before)
        raise


@contextmanager
def project_lock(project):
    try:
        import fcntl
    except ImportError as error:
        raise Conflict("This runtime currently supports POSIX project configuration only") from error
    descriptor = os.open(project, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def configure(project, capsule, action, hosts=None, mode=None, installation=None, locked=False):
    with nullcontext() if locked else project_lock(project):
        current = state_read(project)
        if action != "setup" and not current:
            if action == "uninstall":
                return {"installed": False, "auto": False, "hosts": [], "changes": [],
                        **session_guidance(False, [])}
            raise Conflict("bstack is not configured in this project; run setup first")
        if action == "auto" and current["capsule"] != str(capsule):
            raise Conflict("Run auto from the configured installed package")
        old = current["managed"] if current else {}
        if action == "uninstall":
            desired = {}
            state = None
        else:
            manifest = package_check(capsule)
            chosen_hosts = list(dict.fromkeys(hosts if hosts is not None else current["hosts"] if current else HOSTS))
            enabled = mode if mode is not None else current["auto"] if current else False
            install_kind = installation or (current.get("installation", "external") if current else "external")
            desired = build_records(project, capsule, chosen_hosts, enabled, old, manifest=manifest)
            state = {"schema": SCHEMA, "capsule": str(capsule), "hosts": chosen_hosts, "auto": enabled, "managed": desired, "installation": install_kind}
        changes = reconcile(project, old, desired)
        bindings_changed = any(relative != ".gitignore" for relative in changes)
        if action == "uninstall":
            retained = [p for p in (project / ".bstack").rglob("*")
                        if (p.is_file() or p.is_symlink()) and p not in
                        (project / STATE, project / ".bstack/instructions.md")]
            if retained:
                ignore = safe_path(project, ".gitignore", follow_leaf=True)
                key = str(ignore.relative_to(project))
                before = snapshot(ignore)
                after = changes.get(key, (before, before))[1]
                text = text_snapshot(after, ignore)
                if not re.search(r"(?m)^/?\.bstack/$", text):
                    text += ("\n" if text and not text.endswith("\n") else "") + ".bstack/\n"
                    changes[key] = (before, {"kind": "file", "data": text.encode(), "mode": before.get("mode", 0o644) if before else 0o644})
        path = safe_path(project, STATE)
        before = snapshot(path)
        after = {"kind": "file", "data": (json.dumps(state, indent=2) + "\n").encode(), "mode": 0o600} if state else None
        if before != after:
            changes[STATE] = (before, after)
        apply(project, changes)
        return {"installed": state is not None, "auto": state["auto"] if state else False,
                "hosts": state["hosts"] if state else [], "changes": list(changes),
                **session_guidance(state["auto"] if state else False, state["hosts"] if state else [], bindings_changed)}


def install_offline(project, capsule, hosts=None):
    manifest = package_check(capsule)
    target = safe_path(project, PACKAGE)
    with project_lock(project):
        current = state_read(project)
        installed_manifest = None
        if target.is_symlink():
            raise Conflict(f"Install will not replace a package symlink: {target}")
        if target.exists():
            if not current or current.get("installation") != "offline" or current["capsule"] != str(target):
                raise Conflict(f"Install will not replace an unowned package: {target}")
            installed_manifest = package_check(target)
        package_changed = installed_manifest != manifest
        legacy = safe_path(project, ".agents/skills/poteto-mode")
        if current and current.get("installation") == "offline" and current["capsule"] == str(legacy):
            if legacy.is_symlink():
                raise Conflict(f"Owned legacy package became a symlink: {legacy}")
            package_check(legacy, legacy=True)
        else:
            if legacy.is_symlink() or (legacy / "manifest.json").exists():
                raise Conflict("Existing externally installed Poteto Mode is not owned by bstack. "
                               "Remove it using its distributor before setup; its files will not be adopted or deleted")
            legacy = None
        chosen_hosts = list(dict.fromkeys(hosts if hosts is not None else current["hosts"] if current else HOSTS))
        enabled = current["auto"] if current else False
        previous = current["managed"] if current else {}
        desired = build_records(project, target, chosen_hosts, enabled, previous, manifest=manifest)
        preflight = dict(previous)
        if legacy:
            for relative in desired:
                path = safe_path(project, relative)
                if path.is_relative_to(legacy):
                    before = snapshot(path)
                    if before is not None:
                        preflight[relative] = {"kind": "file", "text": text_snapshot(before, path)}
        reconcile(project, preflight, desired)
        if target == capsule:
            result = configure(project, target, "setup", hosts=chosen_hosts, installation="offline", locked=True)
            result["installation"] = "offline"
            result["package"] = str(target)
            return result
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".bstack-install-", dir=target.parent) as temporary:
            staging = Path(temporary) / "package"
            staging.mkdir()
            for entry in manifest["files"]:
                source = capsule / entry["path"]
                destination = staging / entry["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            shutil.copy2(capsule / "manifest.json", staging / "manifest.json")
            package_check(staging)
            backup = Path(temporary) / "previous"
            old_legacy = Path(temporary) / "legacy"
            try:
                if target.exists():
                    os.replace(target, backup)
                if legacy:
                    os.replace(legacy, old_legacy)
                os.replace(staging, target)
                result = configure(project, target, "setup", hosts=chosen_hosts, installation="offline", locked=True)
            except Exception:
                if not staging.exists() and target.exists():
                    shutil.rmtree(target)
                if backup.exists():
                    os.replace(backup, target)
                if old_legacy.exists():
                    if legacy.exists():
                        shutil.rmtree(legacy)
                    os.replace(old_legacy, legacy)
                raise
        result["installation"] = "offline"
        result["package"] = str(target)
        result["source"] = "bundled-files-only"
        result.update(session_guidance(result["auto"], result["hosts"], result["fresh_session_required"] or package_changed))
        return result


def uninstall_package(project, capsule):
    with project_lock(project):
        current = state_read(project)
        if not current or current.get("installation") != "offline":
            return configure(project, capsule, "uninstall", locked=True)
        owned = safe_path(project, PACKAGE)
        legacy = safe_path(project, ".agents/skills/poteto-mode")
        if current["capsule"] not in (str(owned), str(legacy)):
            raise Conflict("Owned package location is unsupported; no package files were removed")
        owned = owned if current["capsule"] == str(owned) else legacy
        if owned.is_symlink():
            raise Conflict(f"Owned package became a symlink: {owned}")
        package_check(owned, legacy=owned == legacy)
        reconcile(project, current["managed"], {})
        with tempfile.TemporaryDirectory(prefix=".bstack-uninstall-", dir=project) as temporary:
            backup = Path(temporary) / "package"
            os.replace(owned, backup)
            try:
                result = configure(project, capsule, "uninstall", locked=True)
            except Exception:
                os.replace(backup, owned)
                raise
        result["package_removed"] = True
        result.update(session_guidance(False, [], True))
        return result


def status(project, capsule, check=False):
    current = state_read(project)
    result = {"installed": current is not None, "auto": current["auto"] if current else False,
              "project": str(project), "hosts": current["hosts"] if current else [],
              "package": current["capsule"] if current else str(capsule),
              **session_guidance(current["auto"] if current else False, current["hosts"] if current else [])}
    if check:
        manifest = package_check(capsule)
        if current:
            if current["capsule"] != str(capsule):
                raise Conflict("This command is from another package location; run the installed package command")
            expected = build_records(project, capsule, current["hosts"], current["auto"], current["managed"], manifest=manifest)
            changes = reconcile(project, current["managed"], expected)
            if changes:
                raise Conflict("Bindings need setup reconciliation: " + ", ".join(changes))
        result["package_integrity"] = "passed"
        result["bindings"] = "passed" if current else "not_configured"
    return result


def run_hook(project, capsule, host):
    current = state_read(project)
    if not current or not current["auto"] or host not in current["hosts"]:
        print("{}")
        return 0
    if current["capsule"] != str(capsule):
        print("{}")
        print("bstack stale hook ignored; run setup from the installed package", file=sys.stderr)
        return 0
    manifest = package_check(capsule)
    path = capsule / manifest["entrypoints"]["reminder"]
    spec = importlib.util.spec_from_file_location("bstack_reminder", path)
    module = importlib.util.module_from_spec(spec)
    bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = bytecode
    module.ROOT = project
    module.ROUTER = capsule / manifest["entrypoints"]["router"]
    module.TEMPLATE = capsule / "runtime/reminder.txt"
    original = sys.argv
    try:
        sys.argv = [str(path), "--host", host]
        return module.main()
    finally:
        sys.argv = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("install", "setup"):
        setup = commands.add_parser(name)
        setup.add_argument("--hosts", nargs="+", choices=HOSTS)
    auto = commands.add_parser("auto")
    auto.add_argument("mode", choices=("on", "off", "status"))
    for name in ("doctor", "uninstall"):
        commands.add_parser(name)
    hook = commands.add_parser("hook")
    hook.add_argument("--host", required=True, choices=HOSTS)
    for command in commands.choices.values():
        command.add_argument("--project", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        project = args.project.expanduser().resolve()
        if not project.is_dir():
            raise Conflict(f"Project directory does not exist: {project}")
        capsule = capsule_root()
        if args.command == "hook":
            return run_hook(project, capsule, args.host)
        if args.command in ("install", "setup"):
            result = install_offline(project, capsule, hosts=args.hosts)
        elif args.command == "uninstall":
            result = uninstall_package(project, capsule)
        elif args.command == "doctor":
            result = status(project, capsule, check=True)
        elif args.mode == "status":
            result = status(project, capsule)
        else:
            result = configure(project, capsule, "auto", mode=args.mode == "on")
        print(json.dumps(result, indent=2))
        return 0
    except (Conflict, OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
