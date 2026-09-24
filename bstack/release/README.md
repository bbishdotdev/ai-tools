# bstack release

Version 0.4.0. The [bstack package](bstack/README.md) contains the engineering, SDLC and shared skills, local workspace app, internal references, controller, and notices.

## Quick start from GitHub

From your project, run:

```sh
npx skills add bbishdotdev/ai-tools --skill install-bstack
```

Choose your agent and project scope if prompted. Then open your agent in that project and ask:

> Use install-bstack to set up this project for my installed tools.

skills.sh downloads the [installer skill](skills-sh/install-bstack/SKILL.md); your agent runs it to install the full bundled package. Keep both the repository name and `--skill install-bstack` in the command. Automatic routing stays opt-in. Python 3.11+ on POSIX is required.

## Install this release offline

Run `python3 bstack/scripts/bstack.py install --project <project-root> --hosts codex claude cursor grok`. Select the hosts you need. It creates `.bstack/package/` and direct public skill entries in `.agents/skills/`. This route needs no npm, skills.sh, Git, or network access.

Both methods install the reviewed bundled files without fetching upstream. Native plugin managers and desktop apps are not validated by these CLI installers.
