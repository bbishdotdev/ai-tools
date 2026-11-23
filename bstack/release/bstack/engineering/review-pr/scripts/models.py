import json
from pathlib import Path
import re
import shutil
import secrets
import subprocess
import sys
import tempfile

from contracts import ReviewError, canonical
from artifacts import validate_zip_trees
from host import command, read_json, write_json
from reviewer_cli import READ_ONLY_PROMPT, build_command, prepare_files
from runtime_verification import probe_runtime_worker, validate_runtime_config
from security import trusted_executable, verify_worker, worker_argv, worker_environment

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared"))
import model_cli

DEFAULTS = model_cli.REVIEW_DEFAULTS
REQUIRED = {
    "codex": ["--ignore-user-config", "--ignore-rules", "--ephemeral", "--output-schema", "--output-last-message", "--sandbox", "--strict-config"],
    "claude": ["--safe-mode", "--tools", "--json-schema", "--effort", "--no-session-persistence", "--strict-mcp-config",
               "--setting-sources", "--disable-slash-commands", "--settings", "--permission-mode", "--permission-prompts", "--no-chrome"],
}


def launcher_argv(project, cli, args):
    try:
        return model_cli.argv(project, cli, args)
    except model_cli.ModelCLIError as exc:
        raise ReviewError(f"{cli} launcher configuration: {exc}") from exc


def launcher_availability(project, cli):
    try:
        return model_cli.availability(project, cli)
    except model_cli.ModelCLIError as exc:
        raise ReviewError(f"{cli} launcher configuration: {exc}") from exc


def configuration(project, path=None):
    source = Path(path) if path else project / ".bstack/review.json"
    config = {"roles": {key: dict(value) for key, value in DEFAULTS.items()}, "timeout_seconds": 900, "zip_trees": {}, "targets": [], "worker": None, "runtime_verification": None,
              "max_model_calls_24h": 60}
    if path or source.exists():
        supplied = read_json(source)
        if not isinstance(supplied, dict) or set(supplied) - {"roles", "timeout_seconds", "zip_trees", "targets", "worker", "runtime_verification", "max_model_calls_24h"}:
            raise ReviewError("Review config accepts only roles, timeout_seconds, zip_trees, targets, worker, runtime_verification and max_model_calls_24h")
        if not isinstance(supplied.get("roles", {}), dict) or set(supplied.get("roles", {})) - set(DEFAULTS):
            raise ReviewError("Unknown review role")
        for role, values in supplied.get("roles", {}).items():
            if not isinstance(values, dict) or set(values) - {"cli", "model", "effort"}:
                raise ReviewError(f"Invalid role configuration: {role}")
            config["roles"][role].update(values)
        config["timeout_seconds"] = supplied.get("timeout_seconds", config["timeout_seconds"])
        config["zip_trees"] = validate_zip_trees(supplied.get("zip_trees", {}))
        config["targets"] = supplied.get("targets", [])
        config["worker"] = supplied.get("worker")
        runtime = supplied.get("runtime_verification")
        config["runtime_verification"] = validate_runtime_config(runtime, project) if runtime is not None else None
        config["max_model_calls_24h"] = supplied.get("max_model_calls_24h", config["max_model_calls_24h"])
    if type(config["timeout_seconds"]) is not int or not 30 <= config["timeout_seconds"] <= 3600:
        raise ReviewError("timeout_seconds must be an integer between 30 and 3600")
    if type(config["max_model_calls_24h"]) is not int or not 7 <= config["max_model_calls_24h"] <= 1000:
        raise ReviewError("max_model_calls_24h must be an integer between 7 and 1000")
    if not isinstance(config["targets"], list) or len(config["targets"]) > 20 or any(
            not isinstance(item, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", item)
            for item in config["targets"]):
        raise ReviewError("targets must be a short list of host/owner/repo entries")
    worker = config["worker"]
    if worker is not None and (not isinstance(worker, list) or len(worker) < 2 or len(worker) > 40 or worker.count("{args}") != 1
                               or worker[0] == "{args}" or any(not isinstance(part, str) or not part or len(part) > 512 or
                               any(ord(char) < 32 for char in part) or ("{args}" in part and part != "{args}") for part in worker)):
        raise ReviewError("worker must be an argv list with one {args} placeholder")
    for role, item in config["roles"].items():
        if item["cli"] not in REQUIRED or item["effort"] not in {"low", "medium", "high"}:
            raise ReviewError(f"Unsupported CLI or effort for {role}")
        if not isinstance(item["model"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", item["model"]):
            raise ReviewError(f"Invalid exact model ID for {role}")
    reviewers = [config["roles"][role] for role in ("reviewer_a", "reviewer_b")]
    if reviewers[0]["model"].casefold() == reviewers[1]["model"].casefold():
        raise ReviewError("The two reviewers must use different model identities")
    return config


def complete_output(args):
    with tempfile.TemporaryFile() as captured:
        try:
            subprocess.run(args, stdin=subprocess.DEVNULL, stdout=captured, stderr=subprocess.DEVNULL, timeout=15, check=True)
        except (OSError, subprocess.SubprocessError):
            return ""
        captured.seek(0)
        return captured.read().decode(errors="replace")


def doctor(config, project=None, live=False):
    project = Path(project or Path.cwd()).resolve()
    results = {}
    for cli in sorted({item["cli"] for item in config["roles"].values()} | {"git", "gh"}):
        if cli in REQUIRED:
            if config.get("worker"):
                trusted_executable(launcher_argv(project, cli, ["--version"])[0], project)
            ready = launcher_availability(project, cli)
            if ready["status"] == "missing":
                raise ReviewError(ready["hint"])
            help_args = launcher_argv(project, cli, ["exec", "--help"] if cli == "codex" else ["--help"])
            help_text = complete_output(help_args)
            if help_text:
                missing = [flag for flag in REQUIRED[cli] if flag not in help_text]
                if missing:
                    raise ReviewError(f"{cli} is missing required flags: {', '.join(missing)}")
            results[cli] = {"path": shutil.which(launcher_argv(project, cli, ["--version"])[0]),
                            "version": ready.get("version", "unavailable"), "help_checked": bool(help_text)}
        else:
            if config.get("worker"):
                trusted_executable(cli, project)
            lines = command([cli, "--version"]).decode().strip().splitlines()
            results[cli] = {"path": shutil.which(cli), "version": lines[0] if lines else "unknown"}
    checks = {}
    worker_checks = {}
    limits = []
    runtime_check = {"status": "configured_not_checked" if config.get("runtime_verification") else "not_configured"}
    if live:
        if config.get("worker"):
            with tempfile.TemporaryDirectory(prefix="bstack-review-worker-check-") as directory:
                work = Path(directory)
                write_json(work / "context.json", {})
                worker_checks = verify_worker(config, work, project)
        runtime_check = probe_runtime_worker(config.get("runtime_verification"), project)
        for name, role in config["roles"].items():
            checks[name] = probe_review_role(role, project, config)
            if checks[name]["status"] != "passed":
                raise ReviewError(f"{name} is not ready: {checks[name]['reason']}")
    status = "ready" if live else "ready_for_runtime_check"
    limits.extend(["No provider substitution will be attempted."] if live else
                  ["Authentication, model availability and effective effort have not been tested.", "No provider substitution will be attempted."])
    return {"status": status, "executables": results, "config": config,
            "runtime_checked": live, "model_checks": checks,
            "worker_checks": worker_checks,
            "runtime_verification_check": runtime_check,
            "isolation": "client_read_only_tools",
            "additional_worker": bool(config.get("worker")),
            "limits": limits}


def rendered(path):
    path = path.resolve()
    value = path.read_text()
    def replace(match):
        target = match[2]
        if "://" in target or target.startswith("#"):
            return match[0]
        candidate = (path.parent / target.split("#", 1)[0]).resolve()
        if candidate.exists():
            package = Path(__file__).resolve().parents[3]
            if candidate.is_relative_to(package):
                return f"[{match[1]}](policy/{candidate.relative_to(package).as_posix()})"
        return match[0]
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace, value)


def trusted_policy():
    package = Path(__file__).resolve().parents[3]
    pending = [Path(__file__).parent.parent / "references" / (name + ".md")
               for name in ("rubric", "reviewer", "adjudicator")]
    pending.append(package / "shared/references/pr-standards.md")
    files = {}
    while pending:
        path = pending.pop().resolve()
        if path in files or not path.is_relative_to(package) or not path.is_file() or path.suffix != ".md":
            continue
        body = path.read_text()
        files[path] = rendered(path)
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", body):
            if "://" not in link and not link.startswith("#"):
                pending.append(path.parent / link.split("#", 1)[0])
    return {path.relative_to(package).as_posix(): body for path, body in files.items()}


def run_model(role, schema, work, project, config, data, timeout, capture=None):
    args = build_command(role, schema, work, project, launcher_argv)
    trusted_executable(args[0], project)
    if config.get("worker"):
        trusted_executable(config["worker"][0], project)
        verify_worker(config, work, project)
        args = worker_argv(config, args)
    try:
        return command(args, cwd=work, data=data, timeout=timeout,
                       env=worker_environment(role["cli"]), inherit_env=False)
    except ReviewError as error:
        reason = model_cli.failure_hint(role["cli"], "", str(error))
        raise ReviewError(f"{role['cli'].capitalize()} review command failed: {reason}") from error


def model_report(role, raw, work):
    if role["cli"] == "codex":
        return read_json(work / "answer.json"), []
    envelope = json.loads(raw)
    if not isinstance(envelope, dict):
        raise ReviewError("Claude returned an unexpected reply. Confirm the saved headless command returns JSON.")
    if envelope.get("is_error"):
        raise ReviewError(model_cli.failure_hint("claude", raw.decode(), "", 0))
    return envelope.get("structured_output"), list(envelope.get("modelUsage", {}))


def probe_review_role(role, project, config=None):
    schema = {"type": "object", "properties": {"ready": {"type": "string", "enum": [model_cli.READY]},
              "probe": {"type": "string"}}, "required": ["ready", "probe"], "additionalProperties": False}
    with tempfile.TemporaryDirectory(prefix="bstack-review-probe-") as directory:
        work = Path(directory)
        nonce = secrets.token_hex(16)
        (work / "head").mkdir()
        (work / "head/probe.txt").write_text(nonce)
        prepare_files(work, schema, {}, {})
        try:
            raw = run_model(role, schema, work, project, config or {},
                            "Read the file head/probe.txt in the current directory with your read-only tools. Return ready=BSTACK_MODEL_READY and probe=the exact file contents.", 90)
            report, observed = model_report(role, raw, work)
            if report != {"ready": model_cli.READY, "probe": nonce}:
                raise ReviewError("The CLI did not read the expected snapshot file. Confirm this CLI can read files in its working directory when launched headless")
            if observed and role["model"] not in observed:
                raise ReviewError(f"The CLI used {observed}, not the requested model")
        except (ReviewError, ValueError, OSError) as error:
            return {"status": "failed", "model": role["model"], "reason": str(error)}
    return {"status": "passed", "model": role["model"], "effort": role["effort"],
            "model_confirmed": role["model"] in observed, "snapshot_read": True}


def invoke(role, schema, prompt, context, snapshots, config, output, project):
    with tempfile.TemporaryDirectory(prefix="bstack-review-agent-") as temporary:
        work = Path(temporary)
        for name, source in snapshots.items():
            shutil.copytree(source, work / name)
        prepare_files(work, schema, context, trusted_policy())
        write_json(output.with_suffix(".request.json"), {"role": role, "context": context})
        try:
            raw = run_model(role, schema, work, project, config, prompt + "\n\n" + READ_ONLY_PROMPT, config["timeout_seconds"], capture=output)
            report, observed = model_report(role, raw, work)
            if observed and role["model"] not in observed:
                raise ReviewError(f"Claude reported different models: {observed}; requested {role['model']}")
            if report is None:
                raise ReviewError("Claude did not return structured_output")
            return report
        except (ValueError, OSError) as exc:
            raise ReviewError(f"Invalid {role['cli']} result: {exc}") from exc
