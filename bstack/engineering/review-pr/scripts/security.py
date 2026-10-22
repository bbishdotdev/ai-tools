import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
from urllib.parse import urlparse

from contracts import ReviewError


def trusted_executable(name, project):
    found = shutil.which(name)
    if not found:
        raise ReviewError(f"Required executable not found: {name}")
    if Path(found).resolve().is_relative_to(Path(project).resolve()):
        raise ReviewError(f"Untrusted PR review cannot launch a project-local executable: {name}")
    return found


def remote_target(project):
    trusted_executable("git", project)
    result = subprocess.run(["git", "-C", str(project), "remote", "get-url", "origin"], capture_output=True, text=True)
    if result.returncode:
        raise ReviewError("This project has no origin remote. Configure review targets in .bstack/review.json before reviewing a PR")
    remote = result.stdout.strip()
    if remote.startswith("git@") and ":" in remote:
        host, repo = remote[4:].split(":", 1)
    elif remote.startswith("ssh://"):
        parts = urlparse(remote)
        host, repo = parts.hostname, parts.path.lstrip("/")
    else:
        parts = urlparse(remote)
        host, repo = parts.hostname, parts.path.lstrip("/")
        if parts.scheme != "https" or parts.username or parts.password or parts.port:
            raise ReviewError("The origin remote must use HTTPS or GitHub SSH, or review targets must be configured explicitly")
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not host or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ReviewError("The origin remote does not identify a GitHub repository")
    return f"{host.lower()}/{repo.lower()}"


def allowed_target(project, target, config):
    selected = f"{target['host'].lower()}/{target['repo'].lower()}"
    allowed = config.get("targets") or [remote_target(project)]
    if not config.get("targets") and target["host"].lower() != "github.com":
        raise ReviewError("Non-GitHub.com review targets require an explicit targets entry in .bstack/review.json")
    if selected not in {item.lower() for item in allowed}:
        raise ReviewError(f"PR target {selected} is not this project's origin or an explicitly configured review target")


def worker_argv(config, args):
    template = config.get("worker")
    if not template:
        raise ReviewError("Reviewing untrusted PRs requires an isolated model worker. Configure worker in .bstack/review.json, or use --trusted-pr for a PR you trust")
    result = []
    for part in template:
        result.extend(args if part == "{args}" else [part])
    return result


def worker_environment():
    keep = {"PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "TMPDIR", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "SSL_CERT_FILE", "SSL_CERT_DIR"}
    return {key: value for key, value in os.environ.items() if key in keep}


def verify_worker(config, work, project):
    if not config.get("worker"):
        raise ReviewError("No isolated model worker is configured")
    secret = Path(work).parent / (Path(work).name + "-outside-canary")
    secret.write_text("bstack-review-outside-snapshot")
    secret.chmod(0o600)
    private_root = Path(project) / ".bstack/reviews"
    if private_root.is_symlink() or private_root.parent.is_symlink():
        secret.unlink(missing_ok=True)
        raise ReviewError("Private review directories must not be symbolic links")
    private_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_root.chmod(0o700)
    with tempfile.NamedTemporaryFile(prefix=".review-outside-", dir=private_root, delete=False) as project_file:
        project_file.write(b"bstack-review-project-canary")
        project_secret = Path(project_file.name)
    home = Path.home()
    private = [secret, project_secret, home / ".config/gh/hosts.yml", home / ".ssh/id_rsa", home / ".ssh/id_ed25519", home / ".aws/credentials"]
    private = [str(path) for path in private if path.exists()]
    script = Path(work) / "worker-canary.py"
    shutil.copyfile(Path(__file__).with_name("worker_canary.py"), script)
    listener = None
    try:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
    except OSError:
        port = 0
    hosts = {"github.com", *(item.split("/", 1)[0] for item in config.get("targets", []))}
    probe = ["python3", str(script), str(port), ",".join(sorted(hosts)), *private]
    try:
        result = subprocess.run(worker_argv(config, probe), cwd=work, env=worker_environment(), capture_output=True, timeout=30)
        if result.returncode:
            raise ReviewError(f"The isolated worker failed its snapshot, outside-file, GitHub-credential, or local-network canary (exit {result.returncode})")
        return {"outside_files_blocked": True, "github_credentials_blocked": True, "local_network_checked": bool(port)}
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ReviewError(f"The isolated worker canary failed: {error}") from error
    finally:
        if listener is not None:
            listener.close()
        script.unlink(missing_ok=True)
        secret.unlink(missing_ok=True)
        project_secret.unlink(missing_ok=True)


def validate_public_text(value):
    if not isinstance(value, str):
        return
    prose = re.sub(r"(?s)(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)", "", value)
    if re.search(r"(?i)(?:https?://|www\.|(?<![\w])data:|<\s*/?\s*[a-z][^>]*>|\]\s*\(|!\s*\[)", prose):
        raise ReviewError("Model-written review text contains a link, image, or HTML. Publication needs a fresh, plain-text assessment")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ReviewError("Model-written review text contains control characters")


def validate_public_report(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in {"path", "id", "side", "kind", "relation", "category", "status", "disposition", "duplicate_of"}:
                validate_public_report(item)
    elif isinstance(value, list):
        for item in value:
            validate_public_report(item)
    else:
        validate_public_text(value)
