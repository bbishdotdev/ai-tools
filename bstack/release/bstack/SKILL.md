---
name: bstack
description: Install or upgrade the bundled bstack collection when the user asks to set up or update bstack in a project.
metadata:
  package: bstack
---

# Install bstack

This folder is the complete bstack 3.3.0 release. Keep its scripts, workflows, references, manifest, and license notices together. Bundled workflow bodies use `INSTRUCTIONS.md`, so only this installer appears before setup creates the project skills. It needs Python 3.11 or newer; no archive extraction or upstream download is required.

Target the Git repository containing the work. Resolve it with `git rev-parse --show-toplevel`, even if this installer lives elsewhere. Resolve [scripts/bstack.py](scripts/bstack.py) relative to this skill folder, choose an available Python 3.11+ interpreter, then run:

```sh
<python3.11-or-newer> <installed-bstack>/scripts/bstack.py install --project <project-root>
```

For a new installation, pass `--hosts` with the requested or available tools, including the current host: `codex`, `claude`, `cursor`, `grok`, `amp`, `copilot`, `opencode`. The default selects the first four. On upgrade, omit the flag to preserve the existing selection. New projects default to `--auto on` and `--verification ask`; upgrades preserve those settings unless explicitly changed.

Setup validates the complete manifest and selected interpreter before installing a private copy at `.bstack/package/`. It saves that interpreter for generated hooks. Keep the interpreter available; rerun setup with another supported interpreter to repair or change it. Respect ownership conflicts. Do not move or delete another installer's skills to force setup through. The installed package works after this distributor-owned folder is removed.

Run the installed controller's doctor with the same supported interpreter:

```sh
<python3.11-or-newer> <project-root>/.bstack/package/scripts/bstack.py doctor --project <project-root>
```

Doctor checks package integrity, owned bindings, and actual hook command startup. Native host loading, Codex trust, and delivery still need a fresh session in the target checkout. Follow the setup result's `fresh_session_required` and `notice`; a later status check does not clear that requirement. In Claude desktop, open a new Code chat rooted in the project. Installing in a parent repository does not configure a child repository.

Every developer runs setup in their own checkout. Commit portable `AGENTS.md`, `CLAUDE.md`, `.gitignore`, and a newly created PR template if desired. Generated skills, runtime state, and adapters belong to the checkout. The stable `.bstack/` block and shared generated-path policy have separate ownership. Shared visibility exceptions survive setup, and uninstall preserves that policy. Review `sharing` for policy maintenance and visible or tracked generated paths; preserve unrelated configuration in mixed host settings.

Report `auto`, `verification`, `pr_template`, and any `recovery_warning` from setup. Existing PR templates stay unchanged; only replace a chosen template when requested. Codex's explicit hooks-off setting blocks automatic setup; the user can enable hooks or choose `--auto off`, which leaves its native guard unavailable. After successful doctor, suggest `bstack-guide` in the fresh session. Optional user-wide memory setup remains separate and requires its own request. Use the installed [setup instructions](shared/setup-bstack/INSTRUCTIONS.md) for later configuration and optional setup.
