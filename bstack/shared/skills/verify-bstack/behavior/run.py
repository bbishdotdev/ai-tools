#!/usr/bin/env python3
"""Install bstack into disposable projects, let real CLIs do ordinary work, and grade the outcome."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import signal
import threading
import time
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
sys.dont_write_bytecode = True
import verify
from hosts import HOME, HOSTS, jail

ROOT = verify.ROOT
RELEASE = ROOT / "bstack/release/bstack"
SCENARIO_DIR = HERE / "scenarios"
RESULTS = ROOT / "bstack/audit/compatibility-results.json"
COMPACT = object()
PROJECT_NAMES = {"late-pr": "notes", "misleading-bug": "roster", "feature-verifier": "invoices",
                 "adr-rejected": "catalog", "compaction-resume": "meter"}
SLASH_COMPACT = {
    "claude": lambda stream: any(e.get("type") == "system" and e.get("subtype") == "compact_boundary" for e in stream),
    "grok": lambda stream: any(e.get("type") == "system" and e.get("subtype") == "compact_boundary" for e in stream),
}


def copilot_compacted(session):
    log = HOME / ".copilot/session-state" / str(session) / "events.jsonl"
    return log.is_file() and any('"type":"session.compaction_complete"' in line.replace(" ", "")
                                 for line in log.read_text(errors="replace").splitlines())
PROVIDER_LIMITS = re.compile(r"quota_exceeded|exceeded your monthly quota|insufficient[ _]credits|usage limit reached", re.I)
QUALITY_CHECKS = {"outcome", "rejected_option_avoided", "answer_explains_rules"}
ROUTER = ".bstack/package/shared/router/WORKFLOW.md"
CACHE = re.compile(r"lru_cache|functools\.cache|@cache\b|\bcache\s*=\s*\{|_cache\b|results_by_query|memo")

SCENARIOS = {
    "explicit-skill": {
        "project": "late-pr", "column": "skills",
        "turns": [lambda host: HOSTS[host].skill_prefix + "how How does `notes list` decide which notes to show, and in what order?"],
    },
    "misleading-bug": {
        "project": "misleading-bug", "column": "auto",
        "turns": ["Renaming a team member doesn't stick. After saving, they still show their old display name. "
                  "I'm pretty sure the store is caching the old record somewhere. Can you fix it?"],
    },
    "feature-verifier": {
        "project": "feature-verifier", "column": "auto", "verification": "auto",
        "turns": ["Add a --currency option to `invoices summary` so the total line shows the currency code, "
                  "like `Total: 123.45 EUR`. Default to USD."],
    },
    "adr-rejected": {
        "project": "adr-rejected", "column": "auto",
        "turns": ["Product search is getting slow now that the catalog has around 50k products, and the same "
                  "popular queries come in constantly. Can you make search fast?"],
    },
    "late-pr": {
        "project": "late-pr", "column": "pr", "forge": True,
        "turns": ["Add a --tag option to `notes list` that only shows notes with that tag.",
                  "Make the tag match case-insensitive too.",
                  "Looks good. Raise a PR for this."],
    },
    "direct-pr": {
        "project": "late-pr", "column": "pr", "forge": True,
        "turns": ["Add a --limit N option to `notes list` that shows at most N notes, then open a PR for it "
                  "with `gh pr create --fill`."],
    },
    "compaction-resume": {
        "project": "compaction-resume", "column": "hooks",
        "turns": ["Our monthly usage report double-counts events that land exactly at midnight UTC on the first "
                  "of the month. Figure out why. Don't change anything yet, just explain what's going on.",
                  COMPACT,
                  "Thanks, that makes sense. Go ahead and fix it."],
    },
}


def run(argv, cwd, check=True, env=None):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, env=env)
    if check and result.returncode:
        raise RuntimeError(f"{argv} failed: {result.stderr.strip()[:2000]}")
    return result


def git(cwd, *args, env=None):
    return run(["git", *args], cwd, env=env).stdout.strip()


def workspace(scenario, host):
    base = Path(tempfile.mkdtemp(prefix="work-")).resolve()
    project = base / PROJECT_NAMES[scenario["project"]]
    shutil.copytree(SCENARIO_DIR / scenario["project"] / "project", project, symlinks=True)
    gitconfig = base / "gitconfig"
    gitconfig.write_text("[user]\n\tname = Dev\n\temail = dev@example.com\n[init]\n\tdefaultBranch = main\n"
                         "[protocol \"ext\"]\n\tallow = always\n")
    env = dict(os.environ, GIT_CONFIG_GLOBAL=str(gitconfig), GIT_CONFIG_NOSYSTEM="1",
               GIT_EXEC_PATH=str(git_exec_path(base)))
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN"):
        env.pop(name, None)
    git(project, "init", "-q", env=env)
    git(project, "add", "-A", env=env)
    git(project, "commit", "-qm", "Initial commit", env=env)
    bare = base / "remote.git"
    forge = base / "forge"
    forge.mkdir()
    fakebin = base / "bin"
    fakebin.mkdir()
    (fakebin / "gh").write_text(f"#!{sys.executable}\n" + (HERE / "fake_gh.py").read_text().split("\n", 2)[2])
    (fakebin / "gh").chmod(0o755)
    repo = "acme/" + project.name
    env.update(PATH=f"{fakebin}{os.pathsep}{env['PATH']}", GH_CONFIG_DIR=str(base / "gh-config"),
               FAKE_FORGE_STATE=str(forge / "state.json"), FAKE_FORGE_GIT=str(bare), FAKE_FORGE_REPO=repo)
    git(base, "init", "-q", "--bare", str(bare), env=env)
    url = f"https://github.com/{repo}.git"
    git(project, "remote", "add", "origin", url, env=env)
    git(project, "push", "-q", "-u", "origin", "main", env=env)
    script = Path(os.environ.get("BSTACK_BEHAVIOR_RELEASE", RELEASE)) / "scripts/bstack.py"
    install = HOSTS[host].install if f'"{HOSTS[host].install}"' in script.read_text().split("HOSTS = ", 1)[1].split("\n", 1)[0] \
        else "codex"
    run([sys.executable, str(script), "install", "--project", str(project), "--hosts", install], project, env=env)
    installed = [sys.executable, str(project / ".bstack/package/scripts/bstack.py")]
    if scenario.get("verification"):
        run(installed + ["verification", scenario["verification"], "--project", str(project)], project, env=env)
    run(installed + ["doctor", "--project", str(project)], project, env=env)
    git(project, "add", "-A", env=env)
    git(project, "commit", "-qm", "Set up bstack", env=env)
    git(project, "push", "-q", "origin", "main", env=env)
    return base, project, env


def git_exec_path(base):
    real = Path(run(["git", "--exec-path"], base).stdout.strip())
    shim = base / "git-core"
    shim.mkdir()
    for entry in real.iterdir():
        if entry.name not in ("git-remote-https", "git-remote-http"):
            (shim / entry.name).symlink_to(entry)
    for name in ("git-remote-https", "git-remote-http"):
        (shim / name).write_text('#!/bin/sh\nexec git remote-ext "$1" "%S $FAKE_FORGE_GIT"\n')
        (shim / name).chmod(0o755)
    return shim


def codex_compact(binary, project, base, session, files, folder, env):
    folder.mkdir(parents=True, exist_ok=True)
    argv = jail([binary, "app-server", "--listen", "stdio://"], base, [HOME / ".codex"], files, project)
    verify.save(folder / "command.json", argv)
    incoming, messages = queue.Queue(), []
    with (folder / "stderr.txt").open("w") as err, (folder / "server.jsonl").open("w") as trace:
        child = subprocess.Popen(argv, cwd=project, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=err, text=True, bufsize=1)

        def read():
            for line in child.stdout:
                trace.write(line)
                try:
                    incoming.put(json.loads(line))
                except ValueError:
                    pass
            incoming.put(None)

        threading.Thread(target=read, daemon=True).start()

        def send(method, params, request_id=None):
            child.stdin.write(json.dumps({"method": method, "params": params,
                                          **({"id": request_id} if request_id is not None else {})}) + "\n")
            child.stdin.flush()

        def until(predicate, timeout):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                data = incoming.get(timeout=max(0.1, end - time.monotonic()))
                if data is None:
                    raise RuntimeError("Codex app-server exited during compaction")
                messages.append(data)
                if "error" in data:
                    raise RuntimeError(str(data["error"]))
                if predicate(data):
                    return data
            raise TimeoutError("Codex compaction timed out")

        try:
            send("initialize", {"clientInfo": {"name": "bstack_behavior", "version": "0.1"},
                                "capabilities": {"experimentalApi": True}}, 1)
            until(lambda m: m.get("id") == 1, 30)
            send("initialized", {})
            send("thread/resume", {"threadId": session, "cwd": str(project), "sandbox": "danger-full-access",
                                   "approvalPolicy": "never"}, 2)
            until(lambda m: m.get("id") == 2, 60)
            send("thread/compact/start", {"threadId": session}, 3)
            until(lambda m: m.get("id") == 3, 30)
            until(lambda m: m.get("method") == "turn/completed", 300)
        finally:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    return any(m.get("method") == "item/completed" and
               m.get("params", {}).get("item", {}).get("type") == "contextCompaction" for m in messages)


def opencode_compact(binary, base, project, session, files, folder, env, model):
    folder.mkdir(parents=True, exist_ok=True)
    port = 4100 + int(uuid.uuid4().hex[:4], 16) % 800
    argv = jail([binary, "serve", "--port", str(port), "--hostname", "127.0.0.1"], base,
                [HOME / path for host in HOSTS.values() for path in host.state], files, project)
    verify.save(folder / "command.json", argv)
    with (folder / "stdout.txt").open("w") as out, (folder / "stderr.txt").open("w") as err:
        server = subprocess.Popen(argv, cwd=project, env=env, stdout=out, stderr=err, start_new_session=True)
        try:
            url = f"http://127.0.0.1:{port}"
            for _ in range(60):
                try:
                    urllib.request.urlopen(url + "/session", timeout=2)
                    break
                except OSError:
                    time.sleep(1)
            provider, model_id = model.split("/", 1)
            request = urllib.request.Request(f"{url}/session/{session}/summarize", method="POST",
                                             data=json.dumps({"providerID": provider, "modelID": model_id}).encode(),
                                             headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=600) as response:
                body = response.read().decode()
            (folder / "summarize.json").write_text(body)
            return response.status == 200 and json.loads(body) is True
        except (OSError, ValueError) as error:
            (folder / "summarize-error.txt").write_text(str(error))
            return False
        finally:
            os.killpg(server.pid, signal.SIGTERM)
            server.wait(timeout=20)


def trace(stream, turn):
    entries = []
    for event in stream:
        item = event.get("item", {})
        if event.get("type") == "item.completed":
            if item.get("type") == "command_execution":
                entries.append({"turn": turn, "tool": "shell", "command": item.get("command", "")})
            elif item.get("type") == "file_change":
                entries += [{"turn": turn, "tool": "edit", "path": change.get("path")} for change in item.get("changes", [])]
            elif item.get("type") == "mcp_tool_call":
                entries.append({"turn": turn, "tool": "mcp", "command": json.dumps(item)[:500]})
        if event.get("type") == "tool_call" and event.get("subtype") == "started":
            for key, value in event.get("tool_call", {}).items():
                if not key.endswith("ToolCall"):
                    continue
                args = value.get("args", {}) if isinstance(value, dict) else {}
                kind = {"readToolCall": "read", "shellToolCall": "shell", "editToolCall": "edit",
                        "writeToolCall": "edit", "deleteToolCall": "edit", "grepToolCall": "search",
                        "globToolCall": "search", "lsToolCall": "search"}.get(key, key)
                entries.append({"turn": turn, "tool": kind,
                                "path": args.get("path") or args.get("targetFile") or args.get("filePath"),
                                "command": args.get("command") or args.get("pattern") or args.get("prompt")})
        if event.get("type") == "tool.execution_start":
            data = event.get("data", {})
            name, args = data.get("toolName"), data.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {"command": args}
            kind = {"view": "read", "read": "read", "bash": "shell", "shell": "shell", "edit": "edit",
                    "create": "edit", "str_replace": "edit", "grep": "search", "glob": "search",
                    "skill": "skill"}.get(name, name)
            entries.append({"turn": turn, "tool": kind, "path": args.get("path") or args.get("file_path"),
                            "command": args.get("command") or args.get("pattern") or args.get("prompt"),
                            "skill": args.get("skill") if name == "skill" else None})
        part = event.get("part", {})
        if event.get("type") == "tool_use" and part.get("type") == "tool":
            name, args = part.get("tool"), part.get("state", {}).get("input", {})
            kind = {"read": "read", "bash": "shell", "edit": "edit", "write": "edit", "patch": "edit",
                    "grep": "search", "glob": "search", "list": "search", "skill": "skill"}.get(name, name)
            entries.append({"turn": turn, "tool": kind, "path": args.get("filePath") or args.get("path"),
                            "command": args.get("command") or args.get("pattern"),
                            "skill": args.get("name") if name == "skill" else None})
        if event.get("type") == "assistant":
            for content in event.get("message", {}).get("content", []):
                if content.get("type") != "tool_use":
                    continue
                name, args = content.get("name"), content.get("input", {})
                kind = {"Read": "read", "Bash": "shell", "Edit": "edit", "Write": "edit", "MultiEdit": "edit",
                        "NotebookEdit": "edit", "Grep": "search", "Glob": "search", "Skill": "skill",
                        "read_file": "read", "run_terminal_command": "shell", "search_replace": "edit",
                        "write_file": "edit", "grep": "search", "list_dir": "search"}.get(name, name)
                entries.append({"turn": turn, "tool": kind,
                                "path": args.get("file_path") or args.get("target_file") or args.get("path")
                                or args.get("target_directory"),
                                "command": args.get("command") or args.get("pattern") or args.get("prompt"),
                                "skill": args.get("skill") or args.get("command") if name == "Skill" else None})
    return entries


def usage(stream):
    totals = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    for event in stream:
        if event.get("type") == "turn.completed":
            for key in ("input_tokens", "output_tokens"):
                totals[key] += event.get("usage", {}).get(key, 0)
        if event.get("type") == "step_finish":
            tokens = event.get("part", {}).get("tokens", {})
            totals["input_tokens"] += tokens.get("input", 0) + sum(tokens.get("cache", {}).values())
            totals["output_tokens"] += tokens.get("output", 0)
            totals["cost_usd"] += event.get("part", {}).get("cost") or 0.0
        if event.get("type") == "result":
            totals["input_tokens"] += sum(event.get("usage", {}).get(key, 0) for key in
                                          ("cache_read_input_tokens", "cache_creation_input_tokens"))
            for key in ("input_tokens", "output_tokens"):
                totals[key] += event.get("usage", {}).get(key, 0)
            totals["cost_usd"] += event.get("total_cost_usd") or 0.0
    return totals


def session_and_answer(stream):
    session, answer = None, ""
    for event in stream:
        session = (event.get("session_id") or event.get("thread_id") or event.get("sessionID")
                   or event.get("sessionId") or event.get("chatId") or session)
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            answer = item.get("text", "")
        if event.get("type") == "assistant":
            texts = [c.get("text", "") for c in event.get("message", {}).get("content", []) if c.get("type") == "text"]
            answer = "\n".join(texts) or answer
        if event.get("type") == "assistant.message" and event.get("data", {}).get("content"):
            answer = event["data"]["content"]
        if event.get("type") == "text" and event.get("part", {}).get("text"):
            answer = event["part"]["text"]
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            answer = event["result"] or answer
    return session, answer


def touched(entries, fragment, turn=None):
    return any(fragment in (entry.get(field) or "") for entry in entries
               if turn is None or entry["turn"] == turn for field in ("path", "command", "skill"))


def changed(project, env, since):
    status = [line for line in run(["git", "status", "--porcelain"], project, env=env).stdout.splitlines()
              if "__pycache__" not in line and not line.endswith(".pyc")]
    return bool(status) or git(project, "rev-parse", "HEAD", env=env) != since


def hidden_tests(source, scenario_name, scenario, folder):
    grading = folder / "grading"
    shutil.copytree(source, grading, symlinks=True, ignore=shutil.ignore_patterns(".bstack", ".git"))
    shutil.copy(SCENARIO_DIR / scenario["project"] / "hidden/test_outcome.py", grading / "tests/test_zz_outcome.py")
    result = subprocess.run([sys.executable, "-m", "unittest"], cwd=grading, capture_output=True, text=True, timeout=300)
    (folder / "grading.txt").write_text(result.stdout + result.stderr)
    return result.returncode == 0


def added_lines(project, env, base_commit):
    diff = run(["git", "diff", base_commit, "--", ".", ":(exclude).bstack"], project, env=env).stdout
    untracked = run(["git", "ls-files", "--others", "--exclude-standard"], project, env=env).stdout.split()
    lines = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    for name in untracked:
        path = project / name
        if path.is_file() and path.suffix == ".py":
            lines += path.read_text(errors="replace").splitlines()
    return lines


def grade(name, scenario, ctx):
    entries, project, env, folder = ctx["trace"], ctx["project"], ctx["env"], ctx["folder"]
    last = len(scenario["turns"])
    checks = {"exited_cleanly": all(code == 0 for code in ctx["exits"]),
              "stayed_in_project": not any(str(ROOT) in (entry.get(field) or "")
                                           for entry in entries for field in ("path", "command"))}
    if name == "explicit-skill":
        answer = ctx["answers"][-1].lower()
        checks.update(skill_policy_read=touched(entries, ROUTER),
                      no_changes=not changed(project, env, ctx["base_commit"]),
                      answer_explains_rules="archived" in answer and "updated" in answer)
    elif name == "misleading-bug":
        checks.update(workflow_loaded=touched(entries, ROUTER) and touched(entries, "playbooks/bug-fix.md"),
                      outcome=hidden_tests(project, name, scenario, folder))
    elif name == "feature-verifier":
        recipes = project / ".agents/skills/verify-invoices/recipes.json"
        evidence = project / ".verify/last-run.json"
        runs = json.loads(evidence.read_text()) if evidence.is_file() else []
        checks.update(workflow_loaded=touched(entries, ROUTER) and touched(entries, "playbooks/feature.md"),
                      outcome=hidden_tests(project, name, scenario, folder),
                      verifier_recipe_updated="--currency" in recipes.read_text(),
                      verifier_ran=any("--currency" in item["args"] and item["passed"] for item in runs)
                      and all(item["passed"] for item in runs))
    elif name == "adr-rejected":
        lines = added_lines(project, env, ctx["base_commit"])
        checks.update(workflow_loaded=touched(entries, ROUTER) and (touched(entries, "playbooks/feature.md")
                                                                     or touched(entries, "playbooks/perf-issue.md")),
                      adr_read=touched(entries, "docs/adr/0001"),
                      rejected_option_avoided=not any(CACHE.search(line) for line in lines),
                      outcome=hidden_tests(project, name, scenario, folder))
    elif name == "late-pr":
        state_path = Path(env["FAKE_FORGE_STATE"])
        state = json.loads(state_path.read_text()) if state_path.is_file() else {"pulls": {}}
        pulls = [pull for pull in state["pulls"].values() if pull["state"] == "open"]
        head = pulls[0]["head"]["ref"] if len(pulls) == 1 else None
        outcome = False
        if head:
            clone = folder / "head"
            run(["git", "clone", "-q", "--branch", head, env["FAKE_FORGE_GIT"], str(clone)], folder, env=env)
            outcome = hidden_tests(clone, name, scenario, folder)
        checks.update(to_pr_loaded=touched(entries, "to-pr", turn=last),
                      single_pr=len(pulls) == 1 and head not in (None, "main"),
                      published_by_workflow=bool(pulls) and all("<!-- bstack-pr:" in pull["body"] for pull in pulls),
                      outcome=outcome)
    elif name == "direct-pr":
        state_path = Path(env["FAKE_FORGE_STATE"])
        state = json.loads(state_path.read_text()) if state_path.is_file() else {"pulls": {}}
        pulls = list(state["pulls"].values())
        checks.update(no_unmanaged_pr=all("<!-- bstack-pr:" in pull["body"] for pull in pulls),
                      pr_created=bool(pulls))
    elif name == "compaction-resume":
        checks.update(compacted=ctx["compacted"],
                      first_turn_stayed_read_only=not ctx["changed_after_first"],
                      instructions_recovered=touched(entries, ROUTER, turn=last),
                      outcome=hidden_tests(project, name, scenario, folder))
    return checks


def forge_env(base, project):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=str(base / "gitconfig"), GIT_CONFIG_NOSYSTEM="1",
               GIT_EXEC_PATH=str(base / "git-core"), GH_CONFIG_DIR=str(base / "gh-config"),
               FAKE_FORGE_STATE=str(base / "forge/state.json"), FAKE_FORGE_GIT=str(base / "remote.git"),
               FAKE_FORGE_REPO="acme/" + project.name)
    env["PATH"] = f"{base / 'bin'}{os.pathsep}{env['PATH']}"
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN"):
        env.pop(name, None)
    return env


def execute(host, binary, name, repeat, folder, timeout):
    scenario = SCENARIOS[name]
    started = time.monotonic()
    base, project, env = workspace(scenario, host)
    driver = HOSTS[host]
    files = driver.prepare(binary, base, project)
    observed = {"host": host, "model": driver.model, "scenario": name, "repeat": repeat, "workspace": str(base),
                "project": str(project),
                "base_commit": git(project, "rev-parse", "HEAD", env=env), "exits": [], "compacted": None,
                "changed_after_first": None, "session": None}
    session = None
    for number, turn in enumerate(scenario["turns"], 1):
        turn_dir = folder / f"turn-{number}"
        hooks = base / "hooks" / str(number)
        hooks.mkdir(parents=True)
        turn_env = dict(env, BSTACK_VERIFY_DIR=str(hooks), BSTACK_STATE_DIR=str(base / "state"))
        code = 0
        if turn is COMPACT:
            if host == "codex":
                observed["compacted"] = codex_compact(binary, project, base, session, files, turn_dir, turn_env)
            elif host == "opencode":
                observed["compacted"] = opencode_compact(binary, base, project, session, files, turn_dir, turn_env,
                                                         driver.model)
            elif host == "copilot":
                argv, stdin = driver.command(binary, base, project, session, "/compact", files)
                code, _ = verify.process(argv, turn_dir, turn_env, timeout, stdin, cwd=project)
                observed["compacted"] = code == 0 and copilot_compacted(session)
            elif host in SLASH_COMPACT:
                argv, stdin = driver.command(binary, base, project, session, "/compact", files)
                code, raw = verify.process(argv, turn_dir, turn_env, timeout, stdin, cwd=project)
                observed["compacted"] = code == 0 and SLASH_COMPACT[host](verify.events(raw))
            else:
                observed["compacted"] = False
        else:
            prompt = turn(host) if callable(turn) else turn
            argv, stdin = driver.command(binary, base, project, session, prompt, files)
            code, raw = verify.process(argv, turn_dir, turn_env, timeout, stdin, cwd=project)
            (turn_dir / "prompt.txt").write_text(prompt)
            session = session_and_answer(verify.events(raw))[0] or session
        observed["exits"].append(code)
        shutil.copytree(hooks, turn_dir / "hooks", dirs_exist_ok=True)
        if number == 1:
            observed["changed_after_first"] = changed(project, env, observed["base_commit"])
        if turn is not COMPACT and (code or not session):
            break
    observed.update(session=session, seconds=round(time.monotonic() - started, 1))
    verify.save(folder / "observed.json", observed)


def assess(folder):
    observed = json.loads((folder / "observed.json").read_text())
    host, name = observed["host"], observed["scenario"]
    scenario = SCENARIOS[name]
    base, project = Path(observed["workspace"]), Path(observed["project"])
    ctx = {"host": host, "project": project, "env": forge_env(base, project), "folder": folder, "trace": [],
           "answers": [], "exits": observed["exits"], "prompt_hooks": {}, "prompt_turns": [],
           "compacted": copilot_compacted(observed["session"]) if host == "copilot" and observed["session"]
           else observed["compacted"], "changed_after_first": observed["changed_after_first"],
           "base_commit": observed["base_commit"], "usage": []}
    for number in range(1, len(observed["exits"]) + 1):
        turn_dir = folder / f"turn-{number}"
        records = [json.loads(path.read_text()) for path in sorted((turn_dir / "hooks").glob("hook-*.json"))]
        ctx["prompt_hooks"][number] = sum(1 for record in records
                                          if record.get("event") in HOSTS[host].reminder_events)
        if scenario["turns"][number - 1] is COMPACT:
            continue
        stream = verify.events((turn_dir / "stdout.jsonl").read_text()) if (turn_dir / "stdout.jsonl").exists() else []
        answer = session_and_answer(stream)[1]
        ctx["answers"].append(answer if isinstance(answer, str) else json.dumps(answer))
        ctx["trace"] += trace(stream, number)
        ctx["usage"].append(usage(stream))
        ctx["prompt_turns"].append(number)
        (turn_dir / "answer.txt").write_text(ctx["answers"][-1])
    limited = any(PROVIDER_LIMITS.search(path.read_text(errors="replace"))
                  for path in folder.glob("turn-*/std*") if path.is_file())
    if limited:
        result = {"host": host, "model": observed.get("model"), "scenario": name, "repeat": observed["repeat"],
                  "status": "error", "reason": "provider quota or credit limit", "workspace": str(base)}
        verify.save(folder / "result.json", result)
        print(f"{host} {name}#{observed['repeat']}: error provider limit", flush=True)
        return result
    completed = len(ctx["exits"]) == len(scenario["turns"])
    shutil.rmtree(folder / "grading", ignore_errors=True)
    shutil.rmtree(folder / "head", ignore_errors=True)
    checks = grade(name, scenario, ctx) if completed else {"completed_all_turns": False}
    if Path(ctx["env"]["FAKE_FORGE_STATE"]).exists():
        shutil.copy(ctx["env"]["FAKE_FORGE_STATE"], folder / "forge.json")
    verify.save(folder / "trace.json", ctx["trace"])
    status = "pass" if checks and all(checks.values()) else "fail"
    integration = all(value for key, value in checks.items() if key not in QUALITY_CHECKS)
    quality = all(value for key, value in checks.items() if key in QUALITY_CHECKS)
    prompt_hooks = (all(ctx["prompt_hooks"].get(turn, 0) > 0 for turn in ctx["prompt_turns"])
                    if HOSTS[host].reminder_events else None)
    result = {"host": host, "model": observed.get("model"), "scenario": name, "repeat": observed["repeat"],
              "status": status, "integration_pass": bool(checks) and integration,
              "quality_pass": bool(checks) and integration and quality, "checks": checks,
              "reminder_hook_every_turn": prompt_hooks, "seconds": observed.get("seconds"),
              "session": observed["session"], "workspace": str(base),
              "usage": {key: sum(item[key] for item in ctx["usage"]) for key in ("input_tokens", "output_tokens", "cost_usd")}}
    verify.save(folder / "result.json", result)
    print(f"{host} {name}#{observed['repeat']}: {status} {json.dumps(checks)}", flush=True)
    return result


def recover_observed(folder):
    result = json.loads((folder / "result.json").read_text())
    base = Path(result["workspace"])
    project = next(path for path in base.iterdir() if (path / ".bstack").is_dir())
    scenario = SCENARIOS[result["scenario"]]
    exits = []
    for number, turn in enumerate(scenario["turns"], 1):
        exit_file = folder / f"turn-{number}" / "exit.json"
        if exit_file.exists():
            exits.append(json.loads(exit_file.read_text())["code"])
        elif turn is COMPACT and (folder / f"turn-{number}").exists():
            exits.append(0)
    checks = result.get("checks", {})
    env = forge_env(base, project)
    base_commit = git(project, "log", "--format=%H", "--grep=^Set up bstack$", "-n", "1", env=env)
    observed = {"host": result["host"], "scenario": result["scenario"], "repeat": result["repeat"],
                "workspace": str(base), "project": str(project), "base_commit": base_commit, "exits": exits,
                "compacted": checks.get("compacted"), "session": result.get("session"),
                "changed_after_first": (not checks["first_turn_stayed_read_only"]
                                        if "first_turn_stayed_read_only" in checks else None),
                "seconds": result.get("seconds"), "recovered": True}
    verify.save(folder / "observed.json", observed)


def run_case(host, binary, name, repeat, out, timeout):
    folder = out / host / f"{name}-{repeat}"
    folder.mkdir(parents=True)
    try:
        execute(host, binary, name, repeat, folder, timeout)
    except Exception as error:
        result = {"host": host, "scenario": name, "repeat": repeat, "status": "error", "reason": str(error)}
        verify.save(folder / "result.json", result)
        print(f"{host} {name}#{repeat}: error {error}", flush=True)
        return result
    return assess(folder)


def summarize(results, clients):
    summary = {}
    for result in results:
        host = summary.setdefault(result["host"], {"version": clients[result["host"]].get("version"), "scenarios": {}})
        host["model"] = result.get("model") or host.get("model")
        row = host["scenarios"].setdefault(result["scenario"], {"column": SCENARIOS[result["scenario"]]["column"],
                                                                "passes": 0, "quality_passes": 0, "repeats": 0,
                                                                "failed_checks": [], "reminder_hook_runs": 0})
        row["repeats"] += 1
        row["passes"] += result.get("integration_pass", result["status"] == "pass")
        row["quality_passes"] += result.get("quality_pass", result["status"] == "pass")
        row["reminder_hook_runs"] += result.get("reminder_hook_every_turn") is True
        row["failed_checks"] += sorted({key for key, value in result.get("checks", {}).items() if not value}
                                       | ({"setup"} if result["status"] == "error" else set()))
        row["failed_checks"] = sorted(set(row["failed_checks"]))
    return summary


def record(summary, run_id):
    data = json.loads(RESULTS.read_text())
    for host, value in summary.items():
        entry = data["hosts"][host + "-cli"]
        entry["version"] = value["version"]
        entry["model"] = value.get("model")
        for scenario, row in value["scenarios"].items():
            entry.setdefault("scenarios", {})[scenario] = dict(row, run=run_id)
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    RESULTS.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", nargs="+", choices=HOSTS, default=["codex", "claude"])
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=list(SCENARIOS))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=1200, help="Seconds per turn")
    parser.add_argument("--record", action="store_true", help=f"Merge the summary into {RESULTS.relative_to(ROOT)}")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--release", type=Path, help="Install this release bundle instead of bstack/release/bstack")
    parser.add_argument("--resume", type=Path, help="Finish an interrupted run directory, skipping completed cases")
    parser.add_argument("--regrade", type=Path, help="Re-score a finished run directory from its saved evidence")
    args = parser.parse_args()
    if args.list:
        for name, scenario in SCENARIOS.items():
            print(f"{name} [{scenario['column']}]: {len([t for t in scenario['turns'] if t is not COMPACT])} turns")
        return 0
    if args.release:
        os.environ["BSTACK_BEHAVIOR_RELEASE"] = str(args.release.resolve())
    if args.regrade:
        folders = sorted(path.parent for path in args.regrade.glob("*/*/result.json"))
        for folder in folders:
            if not (folder / "result.original.json").exists():
                shutil.copy(folder / "result.json", folder / "result.original.json")
            if not (folder / "observed.json").exists():
                recover_observed(folder)
        results = [assess(folder) for folder in folders]
        clients = {name: {"version": None} for name in HOSTS}
        summary = summarize(results, clients)
        verify.save(args.regrade / "report.json", {"run": args.regrade.name, "results": results, "summary": summary,
                                                   "regraded": datetime.now(timezone.utc).isoformat()})
        if args.record:
            record(summary, args.regrade.name)
        return 0
    clients = {name: {"binary": host.binary()} for name, host in HOSTS.items()}
    for item in clients.values():
        if item["binary"]:
            version = subprocess.run([item["binary"], "--version"], capture_output=True, text=True, timeout=30)
            item["version"] = (version.stdout or version.stderr).strip().splitlines()[0] if (version.stdout or version.stderr).strip() else None
        item["installed"] = bool(item["binary"])
    missing = [tool for tool in args.tools if not clients[tool]["installed"]]
    if missing:
        parser.error("Missing CLI: " + ", ".join(missing))
    if args.resume:
        out = args.resume.resolve()
        run_id = out.name
    else:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-behavior-" + uuid.uuid4().hex[:6]
        out = ROOT / ".bstack/verification" / run_id
        out.mkdir(parents=True)
    jobs = []
    for repeat in range(1, args.repeats + 1):
        for name in args.scenarios:
            for tool in args.tools:
                if COMPACT in SCENARIOS[name]["turns"] and not HOSTS[tool].compacts:
                    continue
                folder = out / tool / f"{name}-{repeat}"
                if (folder / "result.json").exists() and json.loads((folder / "result.json").read_text())["status"] != "error":
                    continue
                if folder.exists():
                    folder.rename(folder.with_name(folder.name + ".interrupted-" + uuid.uuid4().hex[:4]))
                jobs.append((tool, name, repeat))
    print(f"{len(jobs)} cases to run in {out}", flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda job: run_case(job[0], clients[job[0]]["binary"], job[1], job[2], out,
                                                     args.timeout), jobs))
    results = [json.loads(path.read_text()) for path in sorted(out.glob("*/*/result.json"))]
    summary = summarize(results, clients)
    verify.save(out / "report.json", {"run": run_id, "results": results, "summary": summary})
    if args.record:
        record(summary, run_id)
    print(out / "report.json")
    return 0 if all(result["status"] == "pass" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
