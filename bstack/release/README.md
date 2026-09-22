# bstack release

Version 0.3.0. The [bstack package](bstack/README.md) contains the engineering, SDLC and shared skills, local workspace app, internal references, controller, and notices.

Install with `python3 bstack/scripts/bstack.py install --project <project-root> --hosts codex claude cursor grok`. It creates `.bstack/package/` and direct public skill entries in `.agents/skills/`.

The [skills.sh installer](skills-sh/install-bstack/SKILL.md) transports the same bundle as an archive. Use `npx skills@1.7.0 add <release>/skills-sh --skill install-bstack --agent codex claude-code cursor grok`, then run its `scripts/install.py --project <project-root> --hosts codex claude cursor grok`. Both methods install the reviewed bundled files without fetching upstream. Native plugin managers and desktop apps are not validated by these CLI installers.
