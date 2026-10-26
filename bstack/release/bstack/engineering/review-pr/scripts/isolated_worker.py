#!/usr/bin/env python3

import ipaddress
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time


PROVIDERS = frozenset({"api.anthropic.com", "platform.claude.com", "claude.ai", "api.openai.com", "chatgpt.com"})
PORT = 18080
ROOT = Path(__file__).resolve().parents[3]


def copy_stream(left, right):
    while True:
        readable, _, _ = select.select((left, right), (), (), 60)
        if not readable:
            return
        for source in readable:
            target = right if source is left else left
            data = source.recv(65536)
            if not data:
                return
            target.sendall(data)


def provider_socket(domain):
    for family, kind, protocol, _, address in socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM):
        ip = ipaddress.ip_address(address[0])
        if not ip.is_global:
            continue
        upstream = socket.socket(family, kind, protocol)
        upstream.settimeout(15)
        try:
            upstream.connect(address)
            return upstream
        except OSError:
            upstream.close()
    raise OSError("Provider has no reachable public address")


def proxy_client(client):
    with client:
        client.settimeout(15)
        request = b""
        while b"\r\n\r\n" not in request and len(request) < 8192:
            chunk = client.recv(4096)
            if not chunk:
                return
            request += chunk
        header, separator, extra = request.partition(b"\r\n\r\n")
        try:
            line = header.split(b"\r\n", 1)[0].decode("ascii")
            method, authority, version = line.split(" ")
            domain, port = authority.rsplit(":", 1)
        except (ValueError, UnicodeDecodeError):
            client.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            return
        if not separator or method != "CONNECT" or version != "HTTP/1.1" or domain not in PROVIDERS or port != "443":
            client.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            return
        try:
            upstream = provider_socket(domain)
        except OSError:
            client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            return
        with upstream:
            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            if extra:
                upstream.sendall(extra)
            client.settimeout(None)
            upstream.settimeout(None)
            copy_stream(client, upstream)


def proxy_loop(listener, stop):
    listener.settimeout(1)
    while not stop.is_set():
        try:
            client, _ = listener.accept()
        except socket.timeout:
            continue
        except OSError:
            return
        threading.Thread(target=proxy_client, args=(client,), daemon=True).start()


def dirs_for(path):
    return [parent for parent in reversed(path.parents) if parent != Path("/")]


def runtime_path(name, executable):
    version = executable.parents[1]
    if (name == "codex" and executable.parent.name == "bin" and version.parent.name == "codex"
            and re.fullmatch(r"\d+(?:\.\d+)+(?:[-+][A-Za-z0-9.-]+)?", version.name)
            and (version / "codex-package.json").is_file()):
        return version
    return executable


def codex_arguments(args, runtime):
    if args[:3] != ["exec", "--ignore-user-config", "--ignore-rules"]:
        raise ValueError("Built-in review worker only accepts BStack's restricted Codex invocation")
    flag = ["--sandbox", "read-only"]
    index = next((i for i in range(len(args) - 1) if args[i:i + 2] == flag), None)
    if index is None:
        raise ValueError("Codex review invocation is missing its sandbox flag")
    filesystem = '{":root"="deny",":minimal"="read",":workspace_roots"={"."="read"},' + \
        json.dumps(str(runtime)) + '="read",' + json.dumps(str(ROOT)) + '="read"}'
    return args[:index] + ["-c", 'default_permissions="bstack-review"', "-c", "permissions.bstack-review.filesystem=" + filesystem] + args[index + 2:]


def inside(args):
    socket_path = os.environ["BSTACK_PROVIDER_SOCKET"]
    bridge = subprocess.Popen([os.environ["BSTACK_SOCAT"], f"TCP-LISTEN:{PORT},bind=127.0.0.1,reuseaddr,fork", f"UNIX-CONNECT:{socket_path}"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            if bridge.poll() is not None:
                raise OSError("Provider bridge stopped before the model started")
            try:
                with socket.create_connection(("127.0.0.1", PORT), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.02)
        else:
            raise OSError("Provider bridge did not start")
        return subprocess.run(args).returncode
    finally:
        bridge.terminate()
        try:
            bridge.wait(timeout=2)
        except subprocess.TimeoutExpired:
            bridge.kill()


def run(args):
    socat = shutil.which("socat")
    if sys.platform != "linux" or not shutil.which("bwrap") or not socat:
        raise ValueError("Built-in review isolation needs Linux, bubblewrap and socat")
    socat = Path(socat).resolve()
    if not args:
        raise ValueError("Missing model command")
    found = shutil.which(args[0])
    if not found:
        raise ValueError("Model executable was not found")
    executable = Path(found).resolve()
    name = Path(args[0]).name
    if name not in {"codex", "claude", "python3", "python3.11", "python3.12", "python3.13", "python3.14"}:
        raise ValueError("Built-in isolation supports direct Codex and Claude CLIs; configure a separate worker for a launcher wrapper")
    if name in {"codex", "claude"}:
        with executable.open("rb") as binary:
            if binary.read(4) != b"\x7fELF":
                raise ValueError("The bundled worker supports native Codex and Claude binaries. A script-based installation needs a separately isolated worker")
    runtime = runtime_path(name, executable)
    work = Path.cwd().resolve()
    if name == "codex":
        args = codex_arguments(args[1:], runtime)
    else:
        args = args[1:]
    home = Path.home()
    paths = {home, work, ROOT}
    if not runtime.is_relative_to(Path("/usr")):
        paths.add(runtime)
    if not socat.is_relative_to(Path("/usr")):
        paths.add(socat)
    dirs = set()
    for path in paths:
        dirs.update(dirs_for(path))
    dirs.update((home / ".codex", home / ".claude"))
    bind = []
    for directory in sorted(dirs, key=lambda path: (len(path.parts), str(path))):
        if directory not in {Path("/usr"), Path("/lib"), Path("/lib64"), Path("/etc")}:
            bind.extend(("--dir", str(directory)))
    for source in ("/usr", "/lib", "/lib64", "/etc/ssl", "/etc/ca-certificates", "/etc/passwd", "/etc/group"):
        if Path(source).exists():
            bind.extend(("--ro-bind", source, source))
    for path in sorted(paths - {home, work, ROOT}):
        bind.extend(("--ro-bind", str(path), str(path)))
    bind.extend(("--ro-bind", str(ROOT), str(ROOT), "--bind", str(work), str(work)))
    credentials = home / (".codex/auth.json" if name == "codex" else ".claude/.credentials.json")
    if name in {"codex", "claude"} and credentials.is_file():
        bind.extend(("--ro-bind", str(credentials), str(credentials)))
    args = [str(executable), *args]
    with tempfile.TemporaryDirectory(prefix="bstack-provider-") as directory:
        socket_path = str(Path(directory) / "bridge.sock")
        listener = socket.socket(socket.AF_UNIX)
        listener.bind(socket_path)
        listener.listen(8)
        stop = threading.Event()
        thread = threading.Thread(target=proxy_loop, args=(listener, stop), daemon=True)
        thread.start()
        proxy = f"http://127.0.0.1:{PORT}"
        environment = {"HOME": str(home), "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HTTPS_PROXY": proxy,
                       "HTTP_PROXY": proxy, "ALL_PROXY": proxy, "NO_PROXY": "", "BSTACK_PROVIDER_SOCKET": socket_path,
                       "BSTACK_SOCAT": str(socat)}
        if name == "codex":
            environment["CODEX_HOME"] = str(home / ".codex")
        command = ["bwrap", "--die-with-parent", "--unshare-user", "--unshare-net", "--unshare-pid", "--unshare-ipc",
                   "--unshare-uts", "--clearenv", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", *bind,
                   "--ro-bind", directory, directory, "--chdir", str(work)]
        for key, value in environment.items():
            command.extend(("--setenv", key, value))
        command.extend(("--", "/usr/bin/python3", str(Path(__file__).resolve()), "--inside", *args))
        try:
            return subprocess.run(command).returncode
        finally:
            stop.set()
            listener.close()
            thread.join(timeout=2)


def main():
    try:
        return inside(sys.argv[2:]) if sys.argv[1:2] == ["--inside"] else run(sys.argv[1:])
    except (OSError, ValueError) as error:
        print(f"BStack review isolation failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
