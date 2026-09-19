# Install bstack

Install the reviewed bundle in `bstack/release/`. It contains bstack's policy, customized unslop, selected PStack workflows and helpers, project adapters, maintainer verification, and attribution. Installation never downloads PStack or substitutes a newer upstream revision. The bundle's `manifest.json` records its exact source pin, file hashes, and packaging changes.

The current controller requires Python 3.11 or newer on POSIX. Linux CLI installation is tested. Windows, desktop apps, and native plugin-manager installation are separate work.

## From a local clone or transferred folder

Copy the release directory to the destination machine, or check out a reviewed bstack commit. No npm, skills.sh, Git, or network access is needed to run this installer. From the ai-tools checkout:

```sh
python3 bstack/release/skills/poteto-mode/scripts/bstack.py install \
  --project /path/to/your/project --hosts codex claude cursor grok
```

Select only the hosts you want to configure. Installation copies the complete bundle into the project's `.agents/skills/poteto-mode/` and configures those hosts. The original clone or transferred folder can then be removed. Existing unowned skill files or conflicting configuration cause a clear failure; they are not overwritten.

## Through skills.sh or an internal distributor

The public skill is named `poteto-mode`; the complete package is bstack. That one directory contains all selected instructions and their supporting files. Private workflows use `WORKFLOW.md` so the installer does not discover the raw upstream skills as independent packages.

From the consumer project, using a reviewed local release:

```sh
npx skills@1.7.0 add /path/to/ai-tools/bstack/release \
  --skill poteto-mode --agent codex claude-code cursor grok
python3 .agents/skills/poteto-mode/scripts/bstack.py setup \
  --project "$PWD" --hosts codex claude cursor grok
```

The skills CLI requires Node and access to its own installation if it is not already available. bstack itself still comes from the specified release. `--copy` is also supported. An internal distributor can copy the complete `skills/poteto-mode/` directory and run its setup command. Keep all nested content and executable permissions intact.

Check for an existing `poteto-mode` skill before using a third-party installer. That name can also belong to PStack. The bstack controller cannot undo a third-party installer overwriting files before setup runs. The direct Python installer refuses that collision.

The skills.sh route makes manual Poteto Mode available before setup. Setup adds the customized writing binding, host instructions, `/bstack-auto`, and `/verify-bstack`. The offline route performs both steps together.

## Installed project layout

After an offline install with all four hosts selected, the project contains:

```text
your-project/
  .agents/skills/
    poteto-mode/
      SKILL.md                     # Public entry into bstack
      content/
        index.json                 # Names mapped to bundled workflows
        engineering/               # Selected PStack skills, playbooks, agents
        shared/                    # bstack router, unslop, verification
      scripts/bstack.py            # Setup, mode control, doctor, uninstall
      runtime/                     # Reminder hook implementation
      manifest.json
      ATTRIBUTION.md
      LICENSE
    unslop/SKILL.md                 # Writing binding
    bstack-auto/SKILL.md            # Explicit on/off/status control
    verify-bstack/SKILL.md          # Installed-package verification
  .claude/skills/                   # Links to the four .agents/skills entries
  .cursor/skills/                   # Same shared entries
  .grok/skills/                     # Same shared entries
  .cursor/rules/bstack.mdc          # Pointer to project instructions
  AGENTS.md                        # Managed bstack instruction block
  CLAUDE.md                        # Managed bstack instruction block
  .bstack/                         # Local configuration and instructions
```

This tree omits supporting files. Hosts discover the four public `SKILL.md` entries. Inside `poteto-mode`, engineering dependencies use `WORKFLOW.md`; the router reads the relevant instructions through the bundled index. They are not separate slash commands, and installing them does not load their full text into every conversation. Codex reads the canonical `.agents/skills` entries; the other selected hosts receive links to the same files.

The development repository's `bstack/upstream/` directory is a build input. It is not copied into the consumer project. The release builder selects those pinned sources, applies bstack's recorded packaging changes, and preserves the installed `content/engineering/` paths. An installed project does not need the development checkout.

Setup preserves existing project instructions and configuration. Automatic routing is off initially; opting in adds the selected hosts' hook bindings. See the next section for mode behavior and host limits.

## Manual entry and automatic routing

Routing starts in manual mode. Invoke `$poteto-mode` in Codex or `/poteto-mode` in hosts that use slash skills. The entry applies bstack's policy before loading its bundled PStack workflows. The customized unslop binding remains active after setup regardless of the router setting.

Use `/bstack-auto on`, `/bstack-auto off`, or `/bstack-auto status`, or run the same controller directly:

```sh
python3 .agents/skills/poteto-mode/scripts/bstack.py auto on --project "$PWD"
python3 .agents/skills/poteto-mode/scripts/bstack.py auto status --project "$PWD"
python3 .agents/skills/poteto-mode/scripts/bstack.py auto off --project "$PWD"
python3 .agents/skills/poteto-mode/scripts/bstack.py doctor --project "$PWD"
```

The controller owns only its generated files, marked instruction blocks, and hook entries. It preserves other project configuration. Mode and ownership state live in gitignored `.bstack/`. Repeating setup preserves the chosen mode. Start a fresh agent session after changing bindings; turning off auto mode cannot erase instructions already in a conversation.

Codex hook trust is separate from project trust. Review the installed commands in Codex's native `/hooks` interface. Setup does not grant that trust. Claude has prompt-hook context delivery. Cursor and Grok use the tested after-tool reminder because their prompt hooks do not provide equivalent context injection. The first tool call and tool-free turns rely on standing instructions.

## Update and remove

Updates are explicit. Transfer a reviewed newer bstack bundle and rerun its offline `install`, or update the whole skill through your distributor and rerun `setup`. Offline updates verify the existing owned files before replacing them, preserve auto preference, and roll back if configuration fails. A changed or unowned file stops the update.

Run the installed controller's `uninstall --project /path/to/project` before removing the capsule. It removes unchanged bstack bindings and preserves private work and verification evidence. The capsule itself remains available for manual use until you remove it through its distributor or explicitly remove `.agents/skills/poteto-mode/`. Keep any host entry installed by a third-party distributor under that distributor's ownership.

Do not copy machine-specific generated wrappers, hooks, and ownership state between unrelated projects. Install from the portable release on each machine. Stable instruction pointers can be checked in; runtime setup is per checkout.

## What offline installation includes

The instruction corpus, bstack customizations, helper source, notices, and Python adapter are bundled. Optional PStack helper programs can still require Bun, Node, npm dependencies, or an authorized external service. Installing bstack does not provision those runtimes or accounts. The capability contract requires the agent to check availability before choosing them. Live model verification also needs authenticated CLIs and provider access.

See [the verification skill](shared/skills/verify-bstack/SKILL.md) for maintainer checks and [upstream ownership](UPSTREAM.md) for selectively adopting upstream changes. Neither installation path follows upstream latest.
