import hashlib
import json
import os
from pathlib import Path
import secrets
import selectors
import shutil
import signal
import socket
import stat
import subprocess
import tempfile
import time

from contracts import ReviewError


MAX_SNAPSHOT_BYTES = 250 * 1024 * 1024
MAX_TIMEOUT_SECONDS = 600
MAX_TOTAL_OUTPUT_BYTES = 1024 * 1024
WORKER_TIMEOUT_SECONDS = 25

CANARY = """import json
import os
from pathlib import Path
import socket
import subprocess
import sys

nonce, port, marker, encoded = sys.argv[1:]
paths = json.loads(encoded)
if not Path(marker).is_file():
    raise SystemExit(2)
if any(Path(path).exists() for path in paths):
    raise SystemExit(3)
if any(key.startswith(('GH_', 'GITHUB_', 'AWS_', 'AZURE_', 'CODEX_', 'ANTHROPIC_')) or key in ('OPENAI_API_KEY', 'CURSOR_API_KEY') for key in os.environ):
    raise SystemExit(4)
try:
    connection = socket.create_connection(('127.0.0.1', int(port)), timeout=1)
except OSError:
    pass
else:
    connection.close()
    raise SystemExit(5)
try:
    token = subprocess.run(('gh', 'auth', 'token', '--hostname', 'github.com'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
except FileNotFoundError:
    pass
except subprocess.TimeoutExpired:
    raise SystemExit(7)
else:
    if token.returncode == 0:
        raise SystemExit(6)
print(nonce)
"""


def _argv(value, name, placeholder=False):
    if (not isinstance(value, list) or not value or len(value) > 40
            or any(not isinstance(part, str) or not part or len(part) > 512
                   or any(ord(char) < 32 for char in part) for part in value)):
        raise ReviewError(f"Runtime verification {name} must be a fixed argv list")
    if placeholder:
        if len(value) < 2 or value.count("{args}") != 1 or value[0] == "{args}" or any("{args}" in part and part != "{args}" for part in value):
            raise ReviewError("Runtime verification worker needs one standalone {args} placeholder")
    elif any("{args}" in part for part in value):
        raise ReviewError("Runtime verification command cannot contain worker placeholders")
    return list(value)


def validate_runtime_config(value, project):
    if not isinstance(value, dict) or set(value) - {"command", "worker", "timeout_seconds", "output_limit_bytes"}:
        raise ReviewError("Runtime verification needs a private command and worker configuration")
    command = _argv(value.get("command"), "command")
    worker = _argv(value.get("worker"), "worker", placeholder=True)
    timeout = value.get("timeout_seconds", 120)
    output_limit = value.get("output_limit_bytes", MAX_TOTAL_OUTPUT_BYTES)
    if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT_SECONDS:
        raise ReviewError("Runtime verification timeout_seconds must be 1 through 600")
    if type(output_limit) is not int or not 1024 <= output_limit <= MAX_TOTAL_OUTPUT_BYTES:
        raise ReviewError("Runtime verification output_limit_bytes must be 1024 through 1048576")
    executable = shutil.which(worker[0])
    if not executable:
        raise ReviewError("Runtime verification worker executable is unavailable")
    if Path(executable).resolve().is_relative_to(Path(project).resolve()):
        raise ReviewError("Runtime verification worker cannot be a project-local executable")
    return {"command": command, "worker": worker, "timeout_seconds": timeout, "output_limit_bytes": output_limit}


def _copy_snapshot(source, destination):
    source = Path(source).resolve(strict=True)
    if not source.is_dir():
        raise ReviewError("Pinned head snapshot is not a directory")
    total = 0
    for root, directories, files in os.walk(source, followlinks=False):
        parent = Path(root)
        relative = parent.relative_to(source)
        if ".git" in relative.parts:
            raise ReviewError("Pinned head snapshot contains Git metadata")
        (destination / relative).mkdir(parents=True, exist_ok=True)
        for name in directories:
            path = parent / name
            if name == ".git" or path.is_symlink():
                raise ReviewError("Pinned head snapshot contains a Git directory or symbolic link")
        for name in files:
            source_file = parent / name
            record = source_file.stat(follow_symlinks=False)
            if name == ".git" or not stat.S_ISREG(record.st_mode):
                raise ReviewError("Pinned head snapshot contains a nonregular file")
            total += record.st_size
            if total > MAX_SNAPSHOT_BYTES:
                raise ReviewError("Pinned head snapshot exceeds 250 MiB")
            target = destination / relative / name
            shutil.copyfile(source_file, target, follow_symlinks=False)
            target.chmod(0o700 if record.st_mode & 0o111 else 0o600)


def _environment(work):
    home = Path(tempfile.mkdtemp(prefix=".bstack-runtime-home-", dir=work))
    temporary = Path(tempfile.mkdtemp(prefix=".bstack-runtime-tmp-", dir=work))
    return {"PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin", "HOME": str(home), "TMPDIR": str(temporary),
            "XDG_CONFIG_HOME": str(home / ".config"), "XDG_CACHE_HOME": str(home / ".cache"),
            "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}


def _worker_command(worker, args):
    command = []
    for part in worker:
        command.extend(args if part == "{args}" else [part])
    return command


def _terminate(process):
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        pass


def _run_bounded(command, work, environment, timeout, capture_limit, byte_limit):
    started = time.monotonic()
    try:
        process = subprocess.Popen(command, cwd=work, env=environment, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    except OSError as error:
        raise ReviewError(f"Runtime verification worker could not start: {error.strerror or type(error).__name__}") from error
    output_hash = hashlib.sha256()
    captured = bytearray()
    output_bytes = 0
    timed_out = False
    output_exceeded = False
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        os.set_blocking(process.stdout.fileno(), False)
        try:
            while selector.get_map() or process.poll() is None:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    timed_out = True
                    _terminate(process)
                    break
                for key, _ in selector.select(min(remaining, 0.2)):
                    try:
                        chunk = os.read(key.fileobj.fileno(), min(65536, byte_limit - output_bytes + 1))
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    output_hash.update(chunk)
                    output_bytes += len(chunk)
                    if len(captured) < capture_limit:
                        captured.extend(chunk[:capture_limit - len(captured)])
                    if output_bytes > byte_limit:
                        output_exceeded = True
                        _terminate(process)
                        break
                if output_exceeded:
                    break
        finally:
            if process.poll() is None:
                _terminate(process)
            process.stdout.close()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _terminate(process)
        process.wait(timeout=5)
    return {"exit_code": process.returncode, "timed_out": timed_out, "output_exceeded": output_exceeded,
            "output_bytes": output_bytes, "output_sha256": output_hash.hexdigest(),
            "output_digest_complete": not output_exceeded,
            "duration_seconds": round(time.monotonic() - started, 3), "_captured": bytes(captured)}


def _outside_paths(project, outside):
    home = Path.home()
    candidates = [outside, Path(project) / ".bstack/reviews", home / ".config/gh/hosts.yml", home / ".ssh/id_rsa",
                  home / ".ssh/id_ed25519", home / ".aws/credentials", home / ".codex/auth.json",
                  home / ".claude/.credentials.json", home / ".config/gcloud/application_default_credentials.json"]
    return [str(path) for path in candidates if path.exists()]


def _check_worker(config, work, project, outside, environment):
    nonce = secrets.token_hex(16)
    marker = work / (".bstack-runtime-marker-" + nonce)
    marker.write_text(json.dumps({"runtime_probe": nonce}))
    probe = work / (".bstack-runtime-canary-" + nonce + ".py")
    probe.write_text(CANARY)
    listener = None
    try:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        arguments = ["python3", str(probe), nonce, str(listener.getsockname()[1]), str(marker),
                     json.dumps(_outside_paths(project, outside))]
        result = _run_bounded(_worker_command(config["worker"], arguments), work, environment,
                              WORKER_TIMEOUT_SECONDS, 256, 4096)
        if result["timed_out"] or result["exit_code"] != 0 or result["_captured"] != (nonce + "\n").encode():
            raise ReviewError("Runtime verification worker failed its file, credential, environment, or host-network canary")
    except OSError as error:
        raise ReviewError("Runtime verification could not start its host-network canary") from error
    finally:
        if listener is not None:
            listener.close()
        probe.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)


def probe_runtime_worker(value, project):
    if value is None:
        return {"status": "not_configured"}
    config = validate_runtime_config(value, project)
    with tempfile.TemporaryDirectory(prefix="bstack-review-runtime-probe-") as temporary:
        root = Path(temporary)
        work = root / "head"
        work.mkdir(mode=0o700)
        outside = root / "outside-canary"
        outside.write_text("bstack-runtime-outside-canary")
        outside.chmod(0o600)
        _check_worker(config, work, project, outside, _environment(work))
    return {"status": "passed", "scope": "selected file, credential, environment, and host-loopback checks"}


def run_runtime_verification(value, project, pinned_head_dir):
    if value is None:
        return {"status": "skipped", "reason": "Runtime verification is not configured"}
    config = validate_runtime_config(value, project)
    with tempfile.TemporaryDirectory(prefix="bstack-review-runtime-") as temporary:
        root = Path(temporary)
        work = root / "head"
        work.mkdir(mode=0o700)
        _copy_snapshot(pinned_head_dir, work)
        outside = root / "outside-canary"
        outside.write_text("bstack-runtime-outside-canary")
        outside.chmod(0o600)
        environment = _environment(work)
        _check_worker(config, work, project, outside, environment)
        outcome = _run_bounded(_worker_command(config["worker"], config["command"]), work,
                               environment, config["timeout_seconds"], 0, config["output_limit_bytes"])
        return {"status": "timed_out" if outcome["timed_out"] else "output_limit" if outcome["output_exceeded"] else
                          "passed" if outcome["exit_code"] == 0 else "failed",
                "exit_code": outcome["exit_code"], "duration_seconds": outcome["duration_seconds"],
                "output_bytes": outcome["output_bytes"], "output_sha256": outcome["output_sha256"],
                "output_digest_complete": outcome["output_digest_complete"],
                "diagnostic": "Verification timed out" if outcome["timed_out"] else
                              "Verification exceeded the 1 MiB output limit" if outcome["output_exceeded"] else
                              "Verification passed" if outcome["exit_code"] == 0 else
                              f"Verification exited {outcome['exit_code']}; output is untrusted and was not passed to the review model",
                "isolation_canary": "passed; selected checks do not prove complete isolation",
                "network_limit": "Canary checks host loopback only; the worker must independently block outbound network access"}
