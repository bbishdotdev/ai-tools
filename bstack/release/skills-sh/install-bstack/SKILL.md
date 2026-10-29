---
name: install-bstack
description: Install or upgrade the bundled bstack collection when the user asks to set up or update bstack in a project.
metadata:
  package: bstack
---

# Install bstack

This skill transports the reviewed bstack release. Its [archive](assets/bstack.zip) contains the package, dependencies, customizations, source manifest, and license notices. Do not fetch upstream skills or modify this distributor-owned archive.

Target the Git repository containing the work, even when this installer skill or another bstack package lives in a parent folder or the user's home directory. Resolve the active repository with `git rev-parse --show-toplevel`; use that path for `--project`. If the session starts above several repositories and the intended one is unclear, identify it before installing. Resolve [install.py](install.py) to its absolute path, then run:

```sh
python3 <installed-install-bstack>/install.py --project <project-root>
```

For a new installation, select the requested hosts or detect available tools, including the current host, and pass `--hosts` with the relevant names: `codex`, `claude`, `cursor`, `grok`, `amp`, `copilot`, `opencode`. Without that flag, a new installation configures the first four; add the optional hosts explicitly when requested. For upgrades, omit `--hosts` to preserve the existing selection unless the user requests a change. Amp, Copilot, and OpenCode discover the shared skills and get native routing and PR-guard bindings: an Amp plugin, Copilot hook configuration, or an OpenCode plugin. Native folder trust and tool settings still apply. Verify Amp discovery with `amp skills list` in a fresh session, and check Copilot in its own client.

The installer validates and copies the package to `.bstack/package/`, creates direct skill entries under `.agents/skills/`, and connects the selected hosts. A new installation starts with automatic engineering routing on and project verification set to `ask`; upgrades preserve both choices. Auto routing picks relevant engineering workflows during ordinary prompts. Verification `ask` proposes changes to a project's verifier before editing it. The user can choose `--auto off` or `--verification off|ask|auto` during installation, or change either later with the installed controller. Respect ownership conflicts rather than overwriting them. The installed package is independent of this transport skill and the development checkout. Keep this skill intact so its distributor can update or remove it normally.

If Codex explicitly disables hooks, default setup stops. Explain the two simple options: enable hooks or install with `--auto off`. Do not silently change that host setting. Manual setup can complete, but the Codex PR guard cannot run until hooks are enabled.

A package installed only in a parent directory is not setup for a child repository. Parent `CLAUDE.md` instructions may appear in Claude Code while the child's skills and auto hook are absent. Install into the child repository, run its `doctor`, then enable auto there if requested. In Claude Code desktop, start a Code chat rooted in that repository and open a fresh chat after setup. Do not report parent `doctor` success as proof for the child.

Setup adds the seven-rule baseline inside managed blocks in `AGENTS.md` and, when Claude is selected, `CLAUDE.md`. It creates missing files, preserves surrounding project instructions, and follows existing links within the project without duplicating a shared block. The baseline applies with automatic routing off. Do not rewrite these blocks by hand or run a host's `/init` automatically.

New root instruction files are project files, not disposable installer state. Setup does not stage or commit them. Tell the user when they are untracked and suggest committing them if they want the guidance to survive a new checkout. On upgrade, if the result has `recreated_instruction_files`, report `recovery_warning` plainly: the installer rebuilt only its block and cannot recover missing project guidance outside it. An existing file with a changed or removed block still needs reconciliation; do not overwrite the whole file.

After successful setup, offer to add project-specific guidance outside the blocks if needed. This is optional; installation is already complete. If the user requests it, inspect the repository and preserve the baseline. A host's native init is optional too, not a portable setup step. Run the installed `doctor` afterward. If an init removed or changed a block, preserve the new project guidance and restore the exact managed block from `.bstack/config.json` before rerunning setup; do not overwrite the whole file.

The entrypoint runs the installed package's `doctor` after installation. Report its `doctor` result and preserve the install result's `fresh_session_required` and `notice` guidance. A later status check does not clear that reload requirement. When required, tell Claude desktop users to start a new Code chat so it discovers the installed skills. A successful filesystem check does not prove that a desktop app has discovered the skills or run its hooks.

Doctor also lists optional model launchers and workflow readiness. A missing Codex, Claude Code, Cursor or Grok CLI does not spoil a basic installation. When the user chooses a model-backed workflow, run `doctor --live --workflow review-pr|grilling|to-pr` for that workflow. A broken selected role must be fixed before that workflow starts. If the developer uses a wrapper, ask for its working terminal command and configure it with `shared/model_cli.py configure --cli <name> --command 'wrapper {args}'`; rerun the live check. Do not guess a wrapper or silently switch providers. The `to-pr` probe tests Codex text access, not image generation.

Report the install result's `pr_template` status. If setup created `.github/pull_request_template.md`, tell the user it is their editable project copy and should be committed to the default branch for GitHub to use it. If templates already existed, name every returned path, say setup left them unchanged, and point to `pr_template.bundled`. Offer: "Want me to compare your current PR template with BStack's and replace the one you choose?" If the user chooses to replace one, show the meaningful differences, save its current contents, and change only the file they selected. A multi-template directory needs a specific file choice; do not add a competing default template silently. Do not ask again when the user already requested that exact replacement.

Use a supported in-session refresh capability only if the host actually exposes one, and verify its result. Otherwise give the fresh-session instruction; do not simulate a refresh by running a separate CLI process or resetting the user's chat. Claude's `/reload-skills`, where available, refreshes the skill catalog only; it does not replace a required session change for routing instructions or hooks.

After `doctor` succeeds, report its `auto` and `verification` settings plainly. If auto is off, explain that engineering routing is manual and that `$bstack-auto on` in Codex or `/bstack-auto on` in slash-command hosts enables it. Do not override an existing off preference. For project verifier behavior, the installed controller accepts `verification off|ask|auto`; explain a choice only if the user asks to change it. Installation or `doctor` failures come first.

After a successful `doctor`, point the user to `bstack-guide` for a short walkthrough and help choosing a first workflow. If they asked to learn bstack during installation, read the installed `.bstack/package/shared/bstack-guide/SKILL.md` and give that walkthrough now. Otherwise recommend `$bstack-guide` in Codex or `/bstack-guide` in slash-command hosts. When a fresh session is required, say to invoke it in that new session; do not imply this chat's skill catalog has reloaded.

Shared memory is bundled but inactive. If the user also requests it, use the installed `setup-bstack` skill's optional memory setup. Do not change user-wide memory settings as part of ordinary project installation.

The PR creation guard is installed for every selected host even with auto routing off. It redirects raw PR creation and body replacement to `to-pr`. Binding checks do not prove a native denial; consult the recorded compatibility limits. Codex users still need to review hook trust in the terminal CLI; setup never grants it. If Codex hooks are explicitly disabled, a manual install can complete but the guard cannot run there. Automatic Codex routing requires hooks to be enabled.
