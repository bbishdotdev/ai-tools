# bstack release

Version 0.7.0-dev.1. The [bstack package](bstack/README.md) contains the engineering, SDLC and shared skills, local workspace app, internal references, controller, and notices.

## Quick start from GitHub

From your project, run:

```sh
npx skills add bbishdotdev/ai-tools --skill install-bstack
```

Choose your agent and project scope if prompted. Then open your agent in that project and ask:

> Install bstack in this project.

Or invoke `$install-bstack` in Codex, `/install-bstack` in Claude Code or Cursor. If the skill does not appear, start a fresh session in the same project.

skills.sh downloads the [installer skill](skills-sh/install-bstack/SKILL.md); your agent runs it to install the full bundled package. Keep both the repository name and `--skill install-bstack` in the command. After installation and `doctor` succeed, the agent offers automatic routing if it is off. Enabling it requires your opt-in; upgrades preserve your existing preference. Python 3.11+ on POSIX is required.

For reuse across projects, add `-g` to install only the installer skill at user scope. Invoke it from each target project; the full bstack package remains project-local.

## Install this release offline

Run `python3 bstack/scripts/bstack.py install --project <project-root> --hosts codex claude cursor grok`. Select the hosts you need. It creates `.bstack/package/` and direct public skill entries in `.agents/skills/`. This route needs no npm, skills.sh, Git, or network access.

Both methods install the reviewed bundled files without fetching upstream. Native plugin managers and desktop apps are not validated by these CLI installers.
