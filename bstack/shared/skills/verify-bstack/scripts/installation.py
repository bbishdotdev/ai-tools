#!/usr/bin/env python3
"""Install the bstack release in isolated projects and optionally drive real CLIs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True
import verify
from codex_hooks import hooks_list, trust_limit
from fallback import tool_trace

HOST_NAMES = {"codex": "codex", "claude": "claude-code", "cursor": "cursor", "grok": "grok"}
SOURCE_ROOT = next((parent for parent in Path(__file__).resolve().parents
                    if (parent / "manifest.json").is_file()), Path(__file__).resolve().parents[5])
PACKAGED = (SOURCE_ROOT / "manifest.json").is_file()
PHASES = ("direct", "manual", "default-off", "auto-1", "auto-2", "after-off")


def run_command(argv, cwd, evidence, env=None):
    evidence.mkdir(parents=True, exist_ok=True)
    verify.save(evidence / "command.json", argv)
    with (evidence / "stdout.txt").open("w") as out, (evidence / "stderr.txt").open("w") as err:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=out, stderr=err, timeout=120)
    verify.save(evidence / "exit.json", {"code": result.returncode})
    return result.returncode, (evidence / "stdout.txt").read_text()


def inspect_bundle(bundle):
    manifest = json.loads((bundle / "manifest.json").read_text())
    failures = []
    if manifest.get("schema_version") != 2 or manifest.get("name") != "bstack":
        failures.append("unsupported manifest")
    seen = set()
    for record in manifest["files"]:
        relative = record["path"]
        if (not isinstance(relative, str) or not relative or Path(relative).is_absolute()
                or any(part in ("", ".", "..") for part in relative.split("/"))):
            failures.append(f"unsafe path: {relative!r}")
            continue
        if relative in seen:
            failures.append(f"duplicate path: {relative}")
        seen.add(relative)
        path = bundle / relative
        if (path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(bundle.resolve())
                or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]
                or stat.S_IMODE(path.stat().st_mode) != record["mode"]):
            failures.append(relative)
    actual = {str(path.relative_to(bundle)) for path in bundle.rglob("*") if path.is_file() or path.is_symlink()}
    failures.extend("unlisted: " + path for path in sorted(actual - seen - {"manifest.json"}))
    public = manifest.get("public_skills", {})
    skills = sorted(str(path.relative_to(bundle)) for path in bundle.rglob("SKILL.md"))
    if not isinstance(public, dict) or skills != sorted(entry["path"] for entry in public.values()):
        failures.append("public skill paths do not match manifest")
    if any(name.startswith("principle-") for name in public):
        failures.append("internal principles exposed as public skills")
    return {"name": manifest["name"], "version": manifest["version"],
            "manifest_sha256": hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest(),
            "file_count": len(manifest["files"]), "hash_failures": failures,
            "packaged_public_skills": skills, "public_skills": public, "entrypoints": manifest["entrypoints"]}


def inspect_bindings(project, bundle, hosts):
    manifest = json.loads((bundle / "manifest.json").read_text())
    failures, entries, links = [], {}, {}
    for name, entry in manifest["public_skills"].items():
        wrapper = project / ".agents/skills" / name / "SKILL.md"
        policy = wrapper.parent / "agents/openai.yaml"
        text = wrapper.read_text() if wrapper.is_file() else ""
        implicit = entry["implicit"]
        valid = (f"name: {name}\n" in text and str(bundle / entry["path"]) in text
                 and f"disable-model-invocation: {str(not implicit).lower()}" in text
                 and policy.is_file()
                 and f"allow_implicit_invocation: {str(implicit).lower()}" in policy.read_text())
        entries[name] = {"path": str(wrapper), "target": str(bundle / entry["path"]), "valid": valid,
                         "implicit": implicit}
        if not valid or implicit != (name == "unslop"):
            failures.append(f"invalid public binding: {name}")
        for host in hosts:
            folder = {"claude": ".claude", "cursor": ".cursor", "grok": ".grok"}.get(host)
            if not folder:
                continue
            target = project / folder / "skills" / name
            valid = target.resolve() == wrapper.parent.resolve()
            links[f"{host}/{name}"] = {"path": str(target), "target": str(target.resolve()), "valid": valid}
            if not valid:
                failures.append(f"invalid host binding: {host}/{name}")
    discovered = sorted(path.parent.name for path in (project / ".agents/skills").glob("*/SKILL.md"))
    expected = set(manifest["public_skills"])
    if (project / ".agents/skills/install-bstack/SKILL.md").is_file():
        expected.add("install-bstack")
    if set(discovered) != expected:
        failures.append("installed public skill names differ from manifest")
    return {"scope": "filesystem bindings, not native CLI registration", "public_entries": entries,
            "filesystem_skill_names": discovered, "host_links": links, "failures": failures}


def command_reads_target(command, target, project):
    if not re.search(r"\b(cat|sed|head|tail|read_text)\b", command):
        return False
    pending = [command]
    for _ in range(3):
        candidates = []
        for text in pending:
            try:
                tokens = shlex.split(text)
            except ValueError:
                continue
            for token in tokens:
                path = Path(token.rstrip(";"))
                if (path if path.is_absolute() else project / path).resolve() == target.resolve():
                    return True
                if " " in token:
                    candidates.append(token)
        pending = candidates
    return False


def native_discovery(stream):
    observations = []
    for event in stream:
        if event.get("type") not in ("system", "session", "session.init"):
            continue
        for field in ("skills", "slash_commands"):
            if isinstance(event.get(field), list):
                observations.append({"event": event.get("type"), "subtype": event.get("subtype"),
                                     "field": field, "value": event[field]})
    return {"status": "observed" if observations else "not_observed", "observations": observations,
            "scope": "native CLI session metadata; file bindings are reported separately"}


def delegation_observed(stream):
    names = {"task", "spawn_agent", "delegate", "launch_agent", "subagent"}
    for event in stream:
        item = event.get("item", {})
        if item.get("type", "").startswith("collab_"):
            return True
        for content in event.get("message", {}).get("content", []):
            if (isinstance(content, dict) and content.get("type") == "tool_use"
                    and content.get("name", "").lower().split(".")[-1] in names):
                return True
        if any(name.lower() in names for name in event.get("tool_call", {})):
            return True
    return False


def without_exclusion_globs(value, depth=0):
    if isinstance(value, list):
        return [without_exclusion_globs(item, depth) for item in value]
    if isinstance(value, dict):
        return {key: without_exclusion_globs(item, depth) for key, item in value.items()
                if not (key in ("glob", "iglob") and isinstance(item, str) and item.startswith("!"))}
    if not isinstance(value, str) or depth == 3:
        return value
    try:
        tokens = shlex.split(value)
    except ValueError:
        return value
    retained = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in ("-g", "--glob", "--iglob") and index + 1 < len(tokens) and tokens[index + 1].startswith("!"):
            index += 2
            continue
        retained.append(without_exclusion_globs(token, depth + 1) if any(flag in token for flag in (" -g ", " --glob ", " --iglob ")) else token)
        index += 1
    return " ".join(retained)


def search_result_paths(value):
    if isinstance(value, list):
        return [path for item in value for path in search_result_paths(item)]
    if not isinstance(value, dict):
        return []
    paths = []
    for key, item in value.items():
        if key in ("file", "path", "filename") and isinstance(item, str):
            paths.append(item)
        elif key in ("files", "filenames") and isinstance(item, list):
            paths.extend(path for path in item if isinstance(path, str))
        if isinstance(item, (dict, list)):
            paths.extend(search_result_paths(item))
    return paths


def tool_accesses(stream):
    accesses, searches = [], set()
    for event in stream:
        item = event.get("item", {})
        if item.get("type") == "command_execution":
            accesses.append({"tool": "command_execution", "input": item.get("command", "")})
        for content in event.get("message", {}).get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") == "tool_use":
                name = content.get("name", "")
                accesses.append({"tool": name, "input": content.get("input", {})})
                if name.lower() in ("grep", "search", "search_files"):
                    searches.add(content.get("id"))
            elif (content.get("type") == "tool_result" and content.get("tool_use_id") in searches
                  and not content.get("is_error")):
                result = content.get("content", "")
                texts = [result] if isinstance(result, str) else [
                    block.get("text", "") for block in result if isinstance(block, dict)]
                paths = []
                for text in texts:
                    try:
                        structured = json.loads(text)
                    except json.JSONDecodeError:
                        paths.extend(line.split(":", 1)[0] for line in text.splitlines())
                    else:
                        paths.extend(search_result_paths(structured))
                accesses.append({"search_result_paths": paths})
        if event.get("type") == "tool_call":
            for name, call in event.get("tool_call", {}).items():
                if not name.endswith("ToolCall") or not isinstance(call, dict):
                    continue
                accesses.append({"tool": name, "input": call.get("args", {})})
                if event.get("subtype") == "completed" and name == "grepToolCall":
                    result = call.get("result", {}).get("success")
                    if result is not None:
                        accesses.append({"search_result_paths": search_result_paths(result)})
    return without_exclusion_globs(accesses)


def cursor_hook_context_attached(stream, session, receipt):
    if not receipt:
        return False
    marker = re.compile(r"(?<![A-Za-z0-9])" + re.escape(receipt) + r"(?![A-Za-z0-9])")
    return any(marker.search(context.get("content", ""))
               for event in stream if event.get("type") == "tool_call" and event.get("subtype") == "completed"
               and event.get("session_id") == session
               for context in event.get("tool_call", {}).get("hookAdditionalContexts", [])
               if isinstance(context, dict) and context.get("hookEventName") == "postToolUse")


def successful_read(stream, target, project, fragments):
    calls = set()

    def matches(value):
        if not isinstance(value, str):
            return False
        path = Path(value)
        return (path if path.is_absolute() else project / path).resolve() == target.resolve()

    def contains(value):
        text = value if isinstance(value, str) else json.dumps(value)
        return all(fragment in text for fragment in fragments)

    for event in stream:
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "command_execution":
            command = item.get("command", "")
            if (item.get("exit_code") == 0 and command_reads_target(command, target, project)
                    and contains(item.get("aggregated_output", ""))):
                return True
        for content in event.get("message", {}).get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") == "tool_use":
                args = content.get("input", {})
                if matches(args.get("file_path", args.get("target_file", args.get("path")))):
                    calls.add(content.get("id"))
            if (content.get("type") == "tool_result" and content.get("tool_use_id") in calls
                    and not content.get("is_error") and contains(content.get("content", ""))):
                return True
        if event.get("type") == "tool_call" and event.get("subtype") == "completed":
            read = event.get("tool_call", {}).get("readToolCall", {})
            success = read.get("result", {}).get("success")
            if matches(read.get("args", {}).get("path")) and success is not None and contains(success):
                return True
    return False


def probe(host, binary, project, bundle, folder, phase, session=None, timeout=180):
    folder.mkdir(parents=True, exist_ok=True)
    fixture = project / f"fixture-{host}-{phase}.txt"
    value = uuid.uuid4().hex
    fixture.write_text(value + "\n")
    active = phase in ("manual", "auto-1", "auto-2")
    contract = (
        "This is a read-only installation probe. Do not implement the example, delegate, edit files, "
        "or use network services. Only read files in this consumer project. Do not read verification "
        "logs, runtime source, state files (.bstack/config.json), or the development checkout. "
        "Do not invoke verify-bstack or bstack-auto or read their instruction files. "
        "Use only receipts supplied directly in this turn's hook context; do not search files or "
        "configuration for a receipt. "
        "This asks about the example task, not an audit of the installer or its settings. Return JSON only. "
    )
    if phase == "direct":
        prefix = "$how\n" if host == "codex" else "/how\n"
        prompt = (prefix + contract + "Explain what the invoked how skill is for and state bstack's default "
                  "delegation model policy. Read its instructions and any required bstack policy, but do not "
                  "execute its exploration or delegation workflow. Return JSON keys skill (the invoked "
                  "skill name), purpose (one sentence), and coding_delegate (policy identifier).")
    elif active:
        prefix = ("$poteto-mode\n" if host == "codex" else "/poteto-mode\n") if phase == "manual" else ""
        task = (
            "Classify this example using the configured workflow: "
            + ("Measured endpoint p95 rose from 120ms to 900ms." if phase == "auto-2"
               else "Saving a user profile silently discards the display name.")
            + " Read " + str(fixture) + " and include its value. "
            "Return keys playbook (filename stem), coding_delegate (default model policy identifier), "
            "value, receipt (latest current-turn verification receipt supplied in hook context, or null), "
            "and reason. Reuse instructions already available. Do not fetch a receipt from a file."
        )
        if phase.startswith("auto") and host in ("cursor", "grok"):
            task += (" The receipt must be labeled 'After-tool verification receipt' for THIS user turn. "
                     "Never substitute a lifecycle receipt or an earlier turn's receipt.")
        prompt = prefix + contract + task
    else:
        prompt = (contract + "Saving a profile drops the display name. Give three likely places to inspect, "
                  "using your ordinary project guidance. Do not implement a fix. "
                  'Return exactly one JSON object with keys "advice" and "receipt". '
                  'Include "receipt": null when no current-turn hook receipt is available; do not omit the key.')
    argv = verify.cli_command(host, binary, session)
    native_hooks = None
    if host == "codex" and phase.startswith("auto"):
        try:
            native_hooks = hooks_list(project, binary)
        except Exception as error:
            native_hooks = {"error": str(error)}
        verify.save(folder / "native-hook-status.json", native_hooks)
    if host == "claude":
        for flag in ("--tools", "--allowedTools"):
            argv[argv.index(flag) + 1] = "Read,Glob,Grep,Skill"
    if host in ("cursor", "grok"):
        argv.extend(["-p", prompt] if host == "grok" else [prompt])
        stdin = None
    else:
        stdin = prompt
    with tempfile.TemporaryDirectory(prefix=f"bstack-installed-{host}-") as scratch:
        hook_dir = Path(scratch) / "hooks"
        hook_dir.mkdir()
        env = dict(os.environ, BSTACK_VERIFY_DIR=str(hook_dir), BSTACK_STATE_DIR=str(Path(scratch) / "state"))
        code, raw = verify.process(argv, folder, env, timeout, stdin)
        shutil.copytree(hook_dir, folder / "hooks", dirs_exist_ok=True)
    (folder / "prompt.txt").write_text(prompt)
    stream = verify.events(raw)
    new_session, answer, response, reads = verify.extract(stream)
    trace = tool_trace(stream)
    records = [json.loads(p.read_text()) for p in (folder / "hooks").glob("*.json")]
    response = response or {}
    read_text = json.dumps(reads) + json.dumps(trace)
    accesses = tool_accesses(stream)
    access_text = json.dumps(accesses)
    router = manifest_router(bundle)
    router_observed = successful_read(stream, router, project, ["## Select and continue", "inherit-parent",
                                                              "## Capabilities and authorization"])
    router_attempted = str(router) in read_text or "shared/router/WORKFLOW.md" in read_text
    forbidden = ("/runtime/", "/scripts/bstack.py", ".bstack/config.json", "/hooks/hook-",
                 ".bstack/verification", "turns.sqlite3")
    checks = {"exit_zero": code == 0, "structured_response": bool(response),
              "no_delegation": not delegation_observed(stream),
              "no_development_checkout_read": str(SOURCE_ROOT) not in access_text,
              "no_receipt_source_read": not any(path in access_text for path in forbidden)}
    if session:
        checks["same_session"] = session == new_session
    if phase == "direct":
        manifest = json.loads((bundle / "manifest.json").read_text())
        how = bundle / manifest["public_skills"]["how"]["path"]
        index = json.loads((bundle / manifest["entrypoints"]["index"]).read_text())
        upstream = bundle / index["upstream_router"]
        checks.update(invoked_skill=response.get("skill") == "how",
                      meaningful_purpose=isinstance(response.get("purpose"), str) and bool(response["purpose"].strip()),
                      custom_model_policy=response.get("coding_delegate") == "inherit-parent",
                      installed_router_read=router_observed,
                      no_upstream_router_read=not successful_read(stream, upstream, project, []),
                      installed_how_read=successful_read(stream, how, project,
                          ["# How", "## Step 1. Assess Complexity", "## Output Format"]))
    elif active:
        checks.update(playbook=response.get("playbook") == ("perf-issue" if phase == "auto-2" else "bug-fix"),
                      custom_model_policy=response.get("coding_delegate") == "inherit-parent",
                      fixture=response.get("value") == value,
                      fresh_fixture_read=successful_read(stream, fixture, project, [value]))
        if phase in ("manual", "auto-1"):
            checks["installed_router_read"] = router_observed
    else:
        state = json.loads((project / ".bstack/config.json").read_text())
        instructions = (project / ".bstack/instructions.md").read_text()
        checks.update(no_router_read=not router_attempted, no_hook_receipts=not any(r.get("receipt") for r in records),
                      persisted_auto_off=state["auto"] is False, no_router_binding=str(router) not in instructions,
                      no_reported_receipt=response.get("receipt", "missing") is None)
    delivery = None
    hook_limit = None
    hook_emitted = False
    hook_attached = False if host == "cursor" else None
    if phase.startswith("auto"):
        event_name = {"codex": "UserPromptSubmit", "claude": "UserPromptSubmit",
                      "cursor": "postToolUse", "grok": "PostToolUse"}[host]
        eligible = [r for r in records if r.get("host") == host and r.get("session_id") == new_session
                    and r.get("event") == event_name and r.get("receipt")]
        latest = max(eligible, key=lambda r: r["observed_at_ns"], default=None)
        hook_emitted = bool(latest)
        if host == "cursor":
            hook_attached = cursor_hook_context_attached(stream, new_session, latest["receipt"] if latest else None)
        delivery = bool(latest and response.get("receipt") == latest["receipt"])
        if host in ("cursor", "grok"):
            delivery = delivery and len(eligible) == 1 and bool(latest.get("turn_id"))
        if host == "grok":
            starts = [r for r in records if r.get("host") == host and r.get("event") == "UserPromptSubmit"]
            delivery = delivery and len(starts) == 1 and starts[0].get("turn_id") == latest["turn_id"]
        if not delivery and native_hooks:
            hook_limit = trust_limit(native_hooks, project)
        if not hook_limit:
            checks["current_turn_hook_delivery"] = delivery
    report = {"host": host, "phase": phase, "session_id": new_session,
              "checks": checks, "passed": all(checks.values()), "fresh_hook_receipt_delivered": delivery,
              "hook_emitted": hook_emitted, "native_hook_context_attached": hook_attached,
              "hook_limit": hook_limit,
              "native_hook_status": native_hooks, "native_skill_discovery": native_discovery(stream),
              "response": response, "answer": answer, "reads": reads, "tool_calls": trace, "tool_accesses": accesses,
              "hook_records": records}
    verify.save(folder / "report.json", report)
    return report


def manifest_router(bundle):
    manifest = json.loads((bundle / "manifest.json").read_text())
    return bundle / manifest["entrypoints"]["router"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=SOURCE_ROOT if PACKAGED else SOURCE_ROOT / "bstack/release")
    parser.add_argument("--skills-cli", type=Path, help="Pinned skills@1.7.0 bin/cli.mjs; otherwise uses npx")
    parser.add_argument("--methods", nargs="+", choices=("offline", "symlink", "copy"), default=["offline"],
                        help="Default: offline Python install. skills.sh methods are explicitly optional.")
    parser.add_argument("--live-method", choices=("offline", "symlink", "copy"),
                        help="Installed project to exercise with models; defaults to first selected method")
    parser.add_argument("--live", action="store_true", help="Spend model usage on installed CLI sessions")
    parser.add_argument("--phases", nargs="+", choices=PHASES,
                        help="Bound live verification to selected phases; auto-2 requires auto-1")
    parser.add_argument("--tools", nargs="+", choices=HOST_NAMES)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    methods = list(dict.fromkeys(args.methods))
    phases = list(dict.fromkeys(args.phases or PHASES))
    if args.phases and not args.live:
        parser.error("--phases requires --live")
    if "auto-2" in phases and "auto-1" not in phases:
        parser.error("auto-2 requires auto-1 to establish a resumed session")
    live_method = args.live_method or methods[0]
    if live_method not in methods:
        parser.error("--live-method must be included in --methods")
    clients = verify.discover()
    selected = args.tools or [name for name, info in clients.items() if info["installed"]]
    missing = [name for name in selected if not clients[name]["installed"]] if args.live else []
    if missing:
        parser.error("Explicitly selected CLIs are missing: " + ", ".join(missing))
    if not selected and args.live:
        parser.error("No supported CLI installed")
    if not selected:
        selected = list(HOST_NAMES)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-installation-" + uuid.uuid4().hex[:6]
    evidence_root = Path.cwd() if PACKAGED else SOURCE_ROOT
    output = (args.output or evidence_root / ".bstack/verification" / stamp).resolve()
    output.mkdir(parents=True, exist_ok=True)
    cli = ["node", str(args.skills_cli.resolve())] if args.skills_cli else ["npx", "--yes", "skills@1.7.0"]
    env = dict(os.environ, DISABLE_TELEMETRY="1", DO_NOT_TRACK="1", NO_COLOR="1")
    report = {"scope": "Canonical package installation, public skill bindings, and optional installed CLI probes",
              "clients": clients, "selected": selected, "live": args.live, "live_method": live_method,
              "live_phases": phases if args.live else [], "installs": [], "probes": []}
    try:
        with tempfile.TemporaryDirectory(prefix="bstack-consumer-") as scratch:
            root = Path(scratch)
            staged = root / "release"
            release = args.release.resolve()
            shutil.copytree(release, staged / "bstack" if (release / "manifest.json").is_file() else staged)
            source_bundle = staged / "bstack"
            source_manifest = hashlib.sha256((source_bundle / "manifest.json").read_bytes()).hexdigest()
            report["source_manifest_sha256"] = source_manifest
            if any(method != "offline" for method in methods) and not (staged / "skills-sh").is_dir():
                raise RuntimeError("skills.sh verification needs --release pointing to the full release with skills-sh/")
            projects = {}
            for method in methods:
                project = root / (method + " project")
                project.mkdir()
                subprocess.run(["git", "init", "--quiet", str(project)], check=True, capture_output=True)
                (project / "src").mkdir()
                (project / "README.md").write_text(
                    "# Profile example\n\nA small read-only fixture for installation checks. "
                    "Application code lives in src/profile.py.\n")
                (project / "src/profile.py").write_text(
                    'def form_payload(display_name):\n    return {"display_name": display_name}\n\n'
                    'def save_profile(database, user_id, payload):\n    database[user_id] = dict(payload)\n\n'
                    'def load_profile(database, user_id):\n    return database[user_id]\n')
                if method == "offline":
                    command = [sys.executable, str(source_bundle / "scripts/bstack.py"), "install",
                               "--project", str(project), "--hosts", *selected]
                else:
                    command = cli + ["add", str(staged / "skills-sh"), "--skill", "install-bstack", "--agent",
                                     *[HOST_NAMES[name] for name in selected], "--yes", "--json"]
                    if method == "copy":
                        command.append("--copy")
                code, raw = run_command(command, project, output / method / "install", env)
                if code:
                    raise RuntimeError(f"{method} install failed; see saved stdout/stderr")
                rows = json.loads(raw)
                if method != "offline" and (not rows or any(row.get("name") != "install-bstack" or row.get("status") != "installed" for row in rows)):
                    raise RuntimeError(f"Unexpected installed transport skills: {rows}")
                report["installs"].append({"method": method, "project": str(project), "installer_results": rows})
                projects[method] = (project, project / ".bstack/package")
            shutil.rmtree(staged)
            report["staged_source_removed_before_execution"] = True
            for method, (target, installed) in projects.items():
                row = next(item for item in report["installs"] if item["method"] == method)
                if method != "offline":
                    locations = [target / ".agents/skills/install-bstack", target / ".claude/skills/install-bstack",
                                 target / ".grok/skills/install-bstack", target / ".cursor/skills/install-bstack"]
                    bootstrap = next((path for path in locations if (path / "scripts/install.py").is_file()), None)
                    if bootstrap is None:
                        raise RuntimeError(f"{method} did not transport install-bstack")
                    archive = bootstrap / "assets/bstack.zip"
                    before = hashlib.sha256(archive.read_bytes()).hexdigest()
                    code, raw = run_command([sys.executable, str(bootstrap / "scripts/install.py"), "--project",
                                             str(target), "--hosts", *selected], target, output / method / "bootstrap", env)
                    if code:
                        raise RuntimeError(f"{method} bootstrap failed: {raw}")
                    row["transport_archive_preserved"] = before == hashlib.sha256(archive.read_bytes()).hexdigest()
                    if not row["transport_archive_preserved"]:
                        raise RuntimeError("Bootstrap changed the distributor-owned archive")
                    row["bootstrap_results"] = json.loads(raw)
                integrity = inspect_bundle(installed)
                if integrity["hash_failures"] or integrity["manifest_sha256"] != source_manifest:
                    raise RuntimeError(f"{method} installed a different or invalid canonical bundle: {integrity}")
                controller = [sys.executable, str(installed / "scripts/bstack.py")]
                code, raw = run_command(controller + ["setup", "--project", str(target), "--hosts", *selected],
                                        target, output / method / "setup", env)
                if code:
                    raise RuntimeError(f"{method} setup failed: {raw}")
                bindings = inspect_bindings(target, installed, selected)
                if bindings["failures"]:
                    raise RuntimeError(f"{method} public binding failure: {bindings['failures']}")
                code, raw = run_command(controller + ["doctor", "--project", str(target)], target,
                                        output / method / "doctor", env)
                if code:
                    raise RuntimeError(f"{method} installed doctor failed: {raw}")
                row.update(integrity=integrity, bindings=bindings, doctor=json.loads(raw))
            report["canonical_bundles_identical"] = len({item["integrity"]["manifest_sha256"] for item in report["installs"]}) == 1
            project, bundle = projects[live_method]
            verify.ROOT = project

            def phase(label, sessions=None):
                if label not in phases:
                    return {}
                with ThreadPoolExecutor(max_workers=len(selected)) as pool:
                    futures = [pool.submit(probe, host, clients[host]["binary"], project, bundle,
                                           output / "live" / host / label, label,
                                           (sessions or {}).get(host), args.timeout) for host in selected]
                    results = [future.result() for future in futures]
                report["probes"].extend(results)
                verify.save(output / "report.json", report)
                print(label + ": " + ", ".join(f"{result['host']}={'pass' if result['passed'] else 'fail'}" for result in results), flush=True)
                return {result["host"]: result["session_id"] for result in results if result["session_id"]}

            controller = [sys.executable, str(bundle / "scripts/bstack.py")]
            if args.live:
                for label in ("direct", "manual", "default-off"):
                    phase(label)
            for mode in ("on", "on"):
                code, _ = run_command(controller + ["auto", mode, "--project", str(project)], project,
                                      output / "state" / (mode + "-" + uuid.uuid4().hex[:4]), env)
                if code:
                    raise RuntimeError("Enabling automatic mode failed")
            if args.live:
                sessions = phase("auto-1")
                if "auto-2" in phases:
                    if len(sessions) != len(selected):
                        raise RuntimeError("Cannot prove resumed turns: a CLI did not return a session ID")
                    phase("auto-2", sessions)
            for mode in ("off", "off"):
                code, _ = run_command(controller + ["auto", mode, "--project", str(project)], project,
                                      output / "state" / (mode + "-" + uuid.uuid4().hex[:4]), env)
                if code:
                    raise RuntimeError("Disabling automatic mode failed")
            if args.live:
                phase("after-off")
            report["status"] = "pass" if all(probe["passed"] for probe in report["probes"]) else "fail"
            if report["status"] == "pass" and any(probe["hook_limit"] for probe in report["probes"]):
                report["status"] = "pass_with_hook_limits"
    except Exception as error:
        report.update(status="error", error=str(error))
    finally:
        verify.ROOT = SOURCE_ROOT
        report["temporary_projects_removed"] = True
        verify.save(output / "report.json", report)
    print(str(output / "report.json"), flush=True)
    return 0 if report["status"] in ("pass", "pass_with_hook_limits") else 1


if __name__ == "__main__":
    raise SystemExit(main())
