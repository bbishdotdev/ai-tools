import json
import os
from pathlib import Path
import subprocess


PYTHON = "/usr/bin/python3"
GIT = "/usr/bin/git"
RUNTIME = ("/usr/bin", "/usr/lib", "/usr/lib64", "/bin", "/lib", "/lib64")


def open_directory(path):
    current = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(os.path.abspath(path)).parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def run(argv, inputs=(), output=None, cwd="/work", timeout=300):
    command = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--cap-drop", "ALL",
               "--clearenv", "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/home/grader",
               "--setenv", "TMPDIR", "/tmp", "--setenv", "LC_ALL", "C.UTF-8",
               "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--setenv", "GIT_CONFIG_GLOBAL", "/dev/null",
               "--setenv", "GIT_CONFIG_NOSYSTEM", "1", "--setenv", "GIT_TERMINAL_PROMPT", "0",
               "--setenv", "GIT_OPTIONAL_LOCKS", "0"]
    command += [arg for path in RUNTIME if Path(path).is_dir() for arg in ("--ro-bind", path, path)]
    command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--dir", "/home/grader"]
    descriptors = []
    try:
        for source, target in inputs:
            descriptor = open_directory(source)
            descriptors.append(descriptor)
            command += ["--ro-bind", f"/proc/self/fd/{descriptor}", target]
        if output is None:
            command += ["--tmpfs", "/work"]
        else:
            descriptor = open_directory(output)
            descriptors.append(descriptor)
            command += ["--bind", f"/proc/self/fd/{descriptor}", "/work"]
        limits = ("import os, resource, sys; "
                  f"limits = ((resource.RLIMIT_CPU, {min(max(int(timeout), 1), 300)}), "
                  "(resource.RLIMIT_AS, 1024 ** 3), (resource.RLIMIT_FSIZE, 64 * 1024 ** 2), "
                  "(resource.RLIMIT_NOFILE, 256), (resource.RLIMIT_CORE, 0)); "
                  "[resource.setrlimit(kind, (value, value)) for kind, value in limits]; "
                  "os.execv(sys.argv[1], sys.argv[1:])")
        command += ["--chdir", cwd, "--", PYTHON, "-I", "-c", limits, *argv]
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, env={},
                              pass_fds=descriptors)
    finally:
        for descriptor in descriptors:
            os.close(descriptor)


def checked(result):
    if result.returncode:
        raise RuntimeError(f"isolated grading failed: {result.stderr.strip()[:2000]}")
    return result.stdout


def git(project, *args):
    return checked(run([GIT, *args], [(project, "/candidate")], cwd="/candidate")).strip()


def read_text(project, relative, default=None):
    script = ("import json, pathlib, sys; path = pathlib.Path('/candidate') / sys.argv[1]; "
              "print(json.dumps(path.read_text(errors='replace') if path.is_file() else None))")
    result = checked(run([PYTHON, "-I", "-c", script, relative], [(project, "/candidate")]))
    value = json.loads(result)
    return default if value is None else value


def record_files(project, patterns=("hook-*.json", "guard-*.json")):
    script = """
import json
from pathlib import Path
import sys

records = {}
total = 0
for pattern in sys.argv[1:]:
    for path in sorted(Path('/candidate').glob(pattern)):
        if not path.is_file():
            continue
        with path.open('rb') as handle:
            text = handle.read(1024 * 1024 + 1)
        total += len(text)
        if len(text) > 1024 * 1024 or total > 8 * 1024 * 1024 or len(records) >= 1024:
            raise ValueError('hook records exceed grading limits')
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError('hook record must be an object')
        records[path.name] = value
print(json.dumps(records))
"""
    return json.loads(checked(run([PYTHON, "-I", "-c", script, *patterns], [(project, "/candidate")])))


def records(project, pattern):
    return list(record_files(project, (pattern,)).values())


def copy_records(source, destination):
    files = record_files(source)
    destination.mkdir()
    for name, record in files.items():
        (destination / name).write_text(json.dumps(record) + "\n")


def added_lines(project, base_commit):
    script = """
import json
from pathlib import Path
import subprocess
import sys

def git(*args):
    return subprocess.run(['/usr/bin/git', *args], check=True, capture_output=True, text=True).stdout

diff = git('diff', '--no-ext-diff', sys.argv[1], '--', '.', ':(exclude).bstack')
lines = [line[1:] for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++')]
for name in git('ls-files', '-z', '--others', '--exclude-standard').split('\\0'):
    path = Path(name)
    if path.is_file() and path.suffix == '.py':
        lines += path.read_text(errors='replace').splitlines()
print(json.dumps(lines))
"""
    return json.loads(checked(run([PYTHON, "-I", "-c", script, base_commit],
                                 [(project, "/candidate")], cwd="/candidate")))


def clone(source, branch, destination):
    destination.mkdir()
    checked(run([GIT, "clone", "--no-hardlinks", "-q", "--branch", branch, "--", "/candidate", "/work"],
                [(source, "/candidate")], output=destination))


def tests(source, hidden, destination):
    destination.mkdir()
    script = """
import os
import shutil
import subprocess
import sys

shutil.copytree('/candidate', '/work', symlinks=True, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('.bstack', '.git'))
shutil.copy('/hidden/test_outcome.py', '/work/tests/test_zz_outcome.py')
os.chdir('/work')
raise SystemExit(subprocess.run([sys.executable, '-m', 'unittest']).returncode)
"""
    return run([PYTHON, "-I", "-c", script], [(source, "/candidate"), (hidden, "/hidden")], output=destination)
