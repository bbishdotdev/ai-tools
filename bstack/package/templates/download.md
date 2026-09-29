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

Automatic routing starts off. After a successful install, ask your agent to enable it if you want bstack workflows applied to ordinary engineering prompts. Shared memory setup is also optional and separate.

## Update

Download a newer release and run its installer against the same project. It preserves your selected tools and automatic routing preference, and stops on ownership conflicts. The installed project works independently of this download; you can remove this extracted folder afterward.

`SHA256SUMS`, distributed alongside the ZIP, records its checksum so you can verify the downloaded file before extracting it.
