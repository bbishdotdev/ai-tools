from pathlib import Path
import os
import socket
import subprocess
import sys


def main():
    if not Path("context.json").is_file():
        return 2
    if any(Path(path).exists() for path in sys.argv[3:]):
        return 3
    if any(key.startswith(("GH_", "GITHUB_", "AWS_")) or key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") for key in os.environ):
        return 4
    if int(sys.argv[1]):
        try:
            connection = socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=1)
        except OSError:
            pass
        else:
            connection.close()
            return 5
    for host in sys.argv[2].split(","):
        try:
            check = subprocess.run(("gh", "auth", "token", "--hostname", host), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except FileNotFoundError:
            break
        except subprocess.TimeoutExpired:
            return 7
        if check.returncode == 0:
            return 6
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
