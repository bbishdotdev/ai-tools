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
import shutil
import subprocess
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True
import verify
from codex_hooks import hooks_list, trust_limit
from fallback import tool_trace

HOST_NAMES = {"codex": "codex", "claude": "claude-code", "cursor": "cursor", "grok": "grok"}
SOURCE_ROOT = Path(__file__).resolve().parents[5]
PACKAGED = (SOURCE_ROOT / "manifest.json").is_file()


def run_command(argv, cwd, evidence, env=None):
    evidence.mkdir(parents=True, exist_ok=True)
    verify.save(evidence / "command.json", argv)
    with (evidence / "stdout.txt").open("w") as out, (evidence / "stderr.txt").open("w") as err:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=out, stderr=err, timeout=120)
    verify.save(evidence / "exit.json", {"code": result.returncode})
    return result.returncode, (evidence / "stdout.txt").read_text()


def inspect_capsule(capsule):
    manifest = json.loads((capsule / "manifest.json").read_text())
    failures = []
    for record in manifest["files"]:
        path = capsule / record["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            failures.append(record["path"])
    skills = sorted(str(p.relative_to(capsule)) for p in capsule.rglob("SKILL.md"))
    return {"name": manifest["name"], "version": manifest["version"],
            "manifest_sha256": hashlib.sha256((capsule / "manifest.json").read_bytes()).hexdigest(),
            "file_count": len(manifest["files"]), "hash_failures": failures,
            "discoverable_skills": skills, "entrypoints": manifest["entrypoints"]}


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
            if (item.get("exit_code") == 0 and re.search(r"\b(cat|sed|head|tail|read_text)\b", command)
                    and target.name in command and contains(item.get("aggregated_output", ""))):
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


def probe(host, binary, project, capsule, folder, phase, session=None, timeout=180):
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
        "This asks about the example task, not an audit of the installer or its settings. Return JSON only. "
    )
    if active:
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
    router = manifest_router(capsule)
    router_observed = successful_read(stream, router, project, ["## Select and continue", "inherit-parent",
                                                              "## Capabilities and authorization"])
    router_attempted = "bstack-router" in read_text and "WORKFLOW.md" in read_text
    forbidden = ("/runtime/", "/scripts/bstack.py", ".bstack/config.json", "/hooks/hook-",
                 ".bstack/verification", "turns.sqlite3")
    checks = {"exit_zero": code == 0, "structured_response": bool(response),
              "no_development_checkout_read": str(SOURCE_ROOT) not in read_text,
              "no_receipt_source_read": not any(path in read_text for path in forbidden)}
    if session:
        checks["same_session"] = session == new_session
    if active:
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
    if phase.startswith("auto"):
        event_name = {"codex": "UserPromptSubmit", "claude": "UserPromptSubmit",
                      "cursor": "postToolUse", "grok": "PostToolUse"}[host]
        eligible = [r for r in records if r.get("host") == host and r.get("session_id") == new_session
                    and r.get("event") == event_name and r.get("receipt")]
        latest = max(eligible, key=lambda r: r["observed_at_ns"], default=None)
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
              "hook_limit": hook_limit,
              "native_hook_status": native_hooks,
              "response": response, "answer": answer, "reads": reads, "tool_calls": trace,
              "hook_records": records}
    verify.save(folder / "report.json", report)
    return report


def manifest_router(capsule):
    manifest = json.loads((capsule / "manifest.json").read_text())
    return capsule / manifest["entrypoints"]["router"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=SOURCE_ROOT if PACKAGED else SOURCE_ROOT / "bstack/release")
    parser.add_argument("--skills-cli", type=Path, help="Pinned skills@1.7.0 bin/cli.mjs; otherwise uses npx")
    parser.add_argument("--methods", nargs="+", choices=("offline", "symlink", "copy"), default=["offline"],
                        help="Default: offline Python install. skills.sh methods are explicitly optional.")
    parser.add_argument("--live-method", choices=("offline", "symlink", "copy"),
                        help="Installed project to exercise with models; defaults to first selected method")
    parser.add_argument("--live", action="store_true", help="Spend model usage on installed CLI sessions")
    parser.add_argument("--tools", nargs="+", choices=HOST_NAMES)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    methods = list(dict.fromkeys(args.methods))
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
    report = {"scope": "Project installation, setup, and optional installed CLI probes", "clients": clients,
              "selected": selected, "live": args.live, "live_method": live_method,
              "installs": [], "probes": []}
    try:
        with tempfile.TemporaryDirectory(prefix="bstack-consumer-") as scratch:
            root = Path(scratch)
            staged = root / "release"
            shutil.copytree(args.release.resolve(), staged)
            source_capsule = staged if (staged / "manifest.json").is_file() else staged / "skills/poteto-mode"
            source_manifest = hashlib.sha256((source_capsule / "manifest.json").read_bytes()).hexdigest()
            report["source_manifest_sha256"] = source_manifest
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
                    command = [sys.executable, str(source_capsule / "scripts/bstack.py"), "install",
                               "--project", str(project), "--hosts", *selected]
                else:
                    command = cli + ["add", str(staged), "--skill", "poteto-mode", "--agent",
                                     *[HOST_NAMES[n] for n in selected], "--yes", "--json"]
                    if method == "copy":
                        command.append("--copy")
                code, raw = run_command(command, project, output / method / "install", env)
                if code:
                    raise RuntimeError(f"{method} install failed; see saved stdout/stderr")
                rows = json.loads(raw)
                if method != "offline" and (not rows or any(row.get("name") != "poteto-mode" or row.get("status") != "installed" for row in rows)):
                    raise RuntimeError(f"Unexpected installed skills: {rows}")
                capsule = project / ".agents/skills/poteto-mode"
                if not capsule.exists():
                    capsule = project / (".claude" if "claude" in selected else ".grok") / "skills/poteto-mode"
                integrity = inspect_capsule(capsule)
                if integrity["hash_failures"] or integrity["discoverable_skills"] != ["SKILL.md"]:
                    raise RuntimeError(f"Invalid installed capsule: {integrity}")
                if integrity["manifest_sha256"] != source_manifest:
                    raise RuntimeError(f"{method} installed a different bundle manifest")
                report["installs"].append({"method": method, "project": str(project), "integrity": integrity,
                                           "installer_results": rows})
                projects[method] = (project, capsule)
            shutil.rmtree(staged)
            report["staged_source_removed_before_execution"] = True
            project, capsule = projects[live_method]
            verify.ROOT = project
            def phase(label, sessions=None):
                with ThreadPoolExecutor(max_workers=len(selected)) as pool:
                    futures = [pool.submit(probe, host, clients[host]["binary"], project, capsule,
                                           output / "live" / host / label, label,
                                           (sessions or {}).get(host), args.timeout) for host in selected]
                    results = [future.result() for future in futures]
                report["probes"].extend(results)
                verify.save(output / "report.json", report)
                print(label + ": " + ", ".join(f"{r['host']}={'pass' if r['passed'] else 'fail'}" for r in results), flush=True)
                return {r["host"]: r["session_id"] for r in results if r["session_id"]}

            if args.live:
                phase("manual")
            for method, (target, installed) in projects.items():
                controller = ["python3", str(installed / "scripts/bstack.py")]
                code, raw = run_command(controller + ["setup", "--project", str(target), "--hosts", *selected],
                                        target, output / method / "setup", env)
                if code:
                    raise RuntimeError(f"{method} setup failed: {raw}")
                code, raw = run_command(controller + ["doctor", "--project", str(target)], target,
                                        output / method / "doctor", env)
                if code:
                    raise RuntimeError(f"{method} installed doctor failed: {raw}")
                next(row for row in report["installs"] if row["method"] == method)["doctor"] = json.loads(raw)
            controller = ["python3", str(capsule / "scripts/bstack.py")]
            if args.live:
                phase("default-off")
            for mode in ("on", "on"):
                code, _ = run_command(controller + ["auto", mode, "--project", str(project)], project,
                                      output / "state" / (mode + "-" + uuid.uuid4().hex[:4]), env)
                if code:
                    raise RuntimeError("Enabling automatic mode failed")
            if args.live:
                sessions = phase("auto-1")
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
            report["status"] = "pass" if all(p["passed"] for p in report["probes"]) else "fail"
            if report["status"] == "pass" and any(p["hook_limit"] for p in report["probes"]):
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
