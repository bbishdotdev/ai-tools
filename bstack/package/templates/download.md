# bstack

This download includes the complete reviewed bstack package. Installation uses the bundled files and requires Python 3.11+ on macOS or Linux. It needs no Git, npm, skills.sh, or network access.

## Install

Ask your agent:

> Read SKILL.md in this folder and install bstack into my project at /path/to/my-project.

Or run:

```sh
python3 install.py --project /path/to/my-project
```

The target project must already exist. Add `--hosts codex claude cursor grok` to choose tools; include only the names you need. Without this option, a new installation configures all four and an upgrade preserves its current tools.

The installer verifies the package, installs it into your project's `.bstack/package/`, registers its skills, and runs `doctor`. Follow the resulting fresh-session guidance. In Claude desktop, start a new Code chat so the skills appear.

Automatic engineering routing starts on for a new installation. Add `--auto off` if you prefer to invoke engineering skills manually. The project verifier setting starts at `ask`: BStack proposes a verifier change and waits for your answer before editing it. Add `--verification off` or `--verification auto` to choose another mode. Upgrades keep your existing choices. Shared memory setup is optional and separate.

## Update

Download a newer release and run its installer against the same project. It preserves your selected tools and automatic routing preference, and stops on ownership conflicts. The installed project works independently of this download; you can remove this extracted folder afterward.

`SHA256SUMS`, distributed alongside the ZIP, records its checksum so you can verify the downloaded file before extracting it.
