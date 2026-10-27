"""Headless drivers: each host runs in its own full-access mode inside one outer bubblewrap jail."""
from dataclasses import dataclass
import json
from pathlib import Path
import shlex
import shutil
import sys

sys.dont_write_bytecode = True
from codex_hooks import hooks_list

HOME = Path.home()
HIDDEN = (HOME / ".config/gh", HOME / ".ssh")
import glob
import os


def real_gh():
    candidates = [Path(entry) / "gh" for entry in os.environ.get("PATH", "").split(os.pathsep)]
    candidates += [Path(found) for pattern in (".local/share/mise/installs/gh/*/*/bin/gh", ".local/share/mise/shims/gh")
                   for found in glob.glob(str(HOME / pattern))]
    candidates += [Path("/usr/bin/gh"), Path("/usr/local/bin/gh")]
    resolved = {path.resolve() for path in candidates if path.is_file()}
    return sorted(str(path) for path in resolved if path.name == "gh" and "/work-" not in str(path))


REAL_GH = real_gh()


def jail(argv, base, state, files=(), cwd=None):
    for path in state:
        if not path.suffix:
            path.mkdir(parents=True, exist_ok=True)
    state = [path for path in state if path.exists()]
    return ["bwrap", "--die-with-parent", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
            "--tmpfs", "/tmp",
            *[arg for path in state for arg in ("--bind", str(path), str(path))],
            *[arg for source, target in files for arg in ("--bind", str(source), str(target))],
            *[arg for path in HIDDEN if path.exists() for arg in ("--tmpfs", str(path))],
            *[arg for path in REAL_GH if (base / "bin/gh").exists() for arg in ("--ro-bind", str(base / "bin/gh"), path)],
            "--bind", str(base), str(base), "--chdir", str(cwd or base), "--", *argv]


@dataclass
class Host:
    name: str
    binaries: tuple
    install: str
    skill_prefix: str
    reminder_events: tuple
    state: tuple
    model: str
    compacts: bool = True

    def binary(self):
        return next((found for command in self.binaries if (found := shutil.which(command))), None)

    def prepare(self, binary, base, project):
        return []

    def native(self, binary, base, project, session, prompt):
        raise NotImplementedError

    def command(self, binary, base, project, session, prompt, files=()):
        argv, stdin = self.native(binary, base, project, session, prompt)
        return jail(argv, base, [HOME / path for host in HOSTS.values() for path in host.state], files, project), stdin


class Codex(Host):
    def prepare(self, binary, base, project):
        config = base / "codex-config.toml"
        original = HOME / ".codex/config.toml"
        config.write_text((original.read_text() if original.exists() else "") +
                          f'\n[projects."{project}"]\ntrust_level = "trusted"\n')
        files = [(config, original)]
        launcher = base / "codex-jailed"
        launcher.write_text("#!/bin/sh\nexec " + shlex.join(jail([binary], base, [HOME / ".codex"], files, project)) + ' "$@"\n')
        launcher.chmod(0o755)
        status = hooks_list(project, str(launcher), timeout=60)
        with config.open("a") as handle:
            for entry in status.get("hooks_list", {}).get("data", []):
                for hook in entry.get("hooks", []):
                    if hook.get("sourcePath", "").startswith(str(project)):
                        handle.write(f'\n[hooks.state."{hook["key"]}"]\ntrusted_hash = "{hook["currentHash"]}"\n')
        return files

    def native(self, binary, base, project, session, prompt):
        args = [binary, "exec", "--json", "-c", f'model="{self.model}"', "-c", 'model_reasoning_effort="medium"',
                "-c", 'sandbox_mode="danger-full-access"', "-c", 'approval_policy="never"']
        return args + (["resume", session, "-"] if session else ["-"]), prompt


class Claude(Host):
    def native(self, binary, base, project, session, prompt):
        args = [binary, "-p", "--model", self.model, "--output-format", "stream-json", "--verbose",
                "--permission-mode", "bypassPermissions", "--strict-mcp-config",
                "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "project"]
        return args + (["--resume", session] if session else []), prompt


class Grok(Host):
    def native(self, binary, base, project, session, prompt):
        args = [binary, "-m", self.model, "--reasoning-effort", "low",
                "--output-format", "streaming-messages-json", "--cwd", str(project), "--trust",
                "--permission-mode", "bypassPermissions", "--disable-web-search"]
        return args + (["--resume", session] if session else []) + ["-p", prompt], None


class Cursor(Host):
    def native(self, binary, base, project, session, prompt):
        args = [binary, "--print", "--model", self.model, "--output-format", "stream-json", "--trust",
                "--workspace", str(project),
                "--sandbox", "disabled", "--force"]
        return args + (["--resume", session] if session else []) + [prompt], None


class Copilot(Host):
    def native(self, binary, base, project, session, prompt):
        args = ["env", "COPILOT_ALLOW_ALL=true", binary, "-p", prompt, "--model", self.model,
                "--output-format", "json", "--allow-all", "--disable-builtin-mcps"]
        return args + (["--resume", session] if session else []), None


class Amp(Host):
    def native(self, binary, base, project, session, prompt):
        settings = base / "amp-settings.json"
        settings.write_text(json.dumps({"amp.dangerouslyAllowAll": True}) + "\n")
        command = ([binary, "threads", "continue", session] if session else [binary]) + [
            "-x", "--stream-json", "--mode", self.model, "--plugin-ready-timeout", "10", "--no-ide",
            "--no-notifications", "--no-archive-after-execute",
            "--settings-file", str(settings)]
        return command, prompt


class OpenCode(Host):
    def native(self, binary, base, project, session, prompt):
        command = [binary, "run", "--format", "json", "--dir", str(project), "--auto", "-m", self.model]
        return command + (["-s", session] if session else []) + [prompt], None


HOSTS = {
    "codex": Codex("codex", ("codex",), "codex", "$", ("UserPromptSubmit",), (".codex",), "gpt-reserve"),
    "claude": Claude("claude", ("claude",), "claude", "/", ("UserPromptSubmit",), (".claude", ".claude.json"), "claude-sonnet-5-5"),
    "grok": Grok("grok", ("grok",), "grok", "/", ("PostToolUse",), (".grok",), "grok-4.7"),
    "cursor": Cursor("cursor", ("cursor-agent", "agent"), "cursor", "/", ("postToolUse", "sessionStart"),
                     (".cursor", ".config/cursor", ".local/share/cursor-agent"), "composer-2.5"),
    "copilot": Copilot("copilot", ("copilot",), "copilot", "/", ("userPromptSubmitted",), (".copilot",), "auto"),
    "amp": Amp("amp", ("amp",), "amp", "/", ("agent.start",), (".amp", ".local/share/amp", ".cache/amp", ".config/amp"), "low",
               compacts=False),
    "opencode": OpenCode("opencode", ("opencode",), "opencode", "/", ("chat.system.transform",),
                         (".config/opencode", ".local/share/opencode", ".cache/opencode", ".local/state/opencode"),
                         "opencode/claude-haiku-5-5"),
}
