---
name: install-bstack
description: Install or upgrade the bundled bstack collection when the user asks to set up or update bstack in a project.
metadata:
  package: bstack
---

# Install bstack

This skill transports the reviewed bstack release. Its [archive](assets/bstack.zip) contains the package, dependencies, customizations, source manifest, and license notices. Do not fetch upstream skills or modify this distributor-owned archive.

Use the current project unless the user names another target. Resolve [install.py](install.py) to its absolute path, then run:

```sh
python3 <installed-install-bstack>/install.py --project <project-root>
```

For a new installation, select the requested hosts or detect available tools, including the current host, and pass `--hosts` with the relevant names: `codex`, `claude`, `cursor`, `grok`. Without that flag, a new installation configures all four. For upgrades, omit `--hosts` to preserve the existing selection unless the user requests a change.

The installer validates and copies the package to `.bstack/package/`, creates direct skill entries under `.agents/skills/`, and connects the selected hosts. It preserves the existing automatic routing preference; a new installation starts with routing off. Respect ownership conflicts rather than overwriting them. The installed package is independent of this transport skill and the development checkout. Keep this skill intact so its distributor can update or remove it normally.

Setup adds the seven-rule baseline inside managed blocks in `AGENTS.md` and, when Claude is selected, `CLAUDE.md`. It creates missing files, preserves surrounding project instructions, and follows existing links within the project without duplicating a shared block. The baseline applies with automatic routing off. Do not rewrite these blocks by hand or run a host's `/init` automatically.

New root instruction files are project files, not disposable installer state. Setup does not stage or commit them. Tell the user when they are untracked and suggest committing them if they want the guidance to survive a new checkout. On upgrade, if the result has `recreated_instruction_files`, report `recovery_warning` plainly: the installer rebuilt only its block and cannot recover missing project guidance outside it. An existing file with a changed or removed block still needs reconciliation; do not overwrite the whole file.

After successful setup, offer to add project-specific guidance outside the blocks if needed. This is optional; installation is already complete. If the user requests it, inspect the repository and preserve the baseline. A host's native init is optional too, not a portable setup step. Run the installed `doctor` afterward. If an init removed or changed a block, preserve the new project guidance and restore the exact managed block from `.bstack/config.json` before rerunning setup; do not overwrite the whole file.

The entrypoint runs the installed package's `doctor` after installation. Report its `doctor` result and preserve the install result's `fresh_session_required` and `notice` guidance. A later status check does not clear that reload requirement. When required, tell Claude desktop users to start a new Code chat so it discovers the installed skills. A successful filesystem check does not prove that a desktop app has discovered the skills or run its hooks.

Report the install result's `pr_template` status. If setup created `.github/pull_request_template.md`, tell the user it is their editable project copy and should be committed to the default branch for GitHub to use it. If templates already existed, name every returned path, say setup left them unchanged, and point to `pr_template.bundled`. Offer: "Want me to compare your current PR template with BStack's and replace the one you choose?" If the user chooses to replace one, show the meaningful differences, save its current contents, and change only the file they selected. A multi-template directory needs a specific file choice; do not add a competing default template silently. Do not ask again when the user already requested that exact replacement.

Use a supported in-session refresh capability only if the host actually exposes one, and verify its result. Otherwise give the fresh-session instruction; do not simulate a refresh by running a separate CLI process or resetting the user's chat. Claude's `/reload-skills`, where available, refreshes the skill catalog only; it does not replace a required session change for routing instructions or hooks.

After `doctor` succeeds, check its `auto` result. If routing is off, briefly offer to enable it so ordinary engineering prompts use bstack's workflows. Suggest `$bstack-auto on` in Codex or `/bstack-auto on` in slash-command hosts. Leave it off until the user opts in. If they already explicitly requested automatic routing as part of setup, follow the installed `.bstack/package/shared/bstack-auto/SKILL.md` with `on` and verify the result; do not ask again. If routing is already on, report that without another offer. If installation or `doctor` fails, address that failure before offering auto mode.

Shared memory is bundled but inactive. If the user also requests it, use the installed `setup-bstack` skill's optional memory setup. Do not change user-wide memory settings as part of ordinary project installation.
