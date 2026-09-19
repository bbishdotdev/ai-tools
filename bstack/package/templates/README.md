# bstack

Version @VERSION@. bstack is the collection; Poteto Mode is one engineering skill within it. The package groups public engineering skills under `engineering/` and shared controls and writing skills under `shared/`. Principles and playbooks stay internal and load only when needed.

The selected Matt Pocock SDLC workflows, approved prototype, shared memory, and GitHub assets await runtime integration. They are not active in this release.

## Install

From a reviewed clone or transferred package, run:

```sh
python3 <package-path>/scripts/bstack.py install --project <project-root> --hosts codex claude cursor grok
```

This creates `.bstack/package/` and direct public entries in `.agents/skills/`, with links for the selected hosts. Python 3.11+ on POSIX is required. No network, skills.sh, Git, or upstream access is needed for installation. The original source can be removed afterward.

A skills.sh distributor uses the separate `install-bstack` transport skill, whose archive contains this same package. Run that skill's installer after distribution. skills.sh does not run setup automatically.

## Use skills directly

Invoke `how`, `architect`, `tdd`, or another public skill by its native host command prefix. Codex uses `$how`; slash-command hosts use `/how`. Use `poteto-mode` when you want the router to select a complete engineering workflow. The [index](index.json) resolves internal dependencies; the [manifest](manifest.json) lists public skills and exact installed files.

Engineering skills are explicit-only by default. The customized [unslop](shared/unslop/SKILL.md) remains active for prose. `/bstack-auto on`, `off`, and `status` control optional automatic routing. The same commands are available from the controller:

```sh
python3 <project-root>/.bstack/package/scripts/bstack.py auto on --project <project-root>
python3 <project-root>/.bstack/package/scripts/bstack.py doctor --project <project-root>
```

Start a fresh session after bindings change. Turning auto off cannot erase existing conversation context. Native hook trust is separate from installation; setup does not grant it. Cursor and Grok's after-tool reminders do not guarantee first-tool or tool-free delivery. CLI packaging does not establish desktop or native plugin-manager support.

## Update and remove

Rerun the installer from a reviewed release to update. It preserves the chosen mode, verifies owned files, and refuses unowned or changed content. Existing offline Poteto Mode bundles migrate to the package layout. Old third-party distributor entries must be resolved through their owner if they collide.

Run the canonical controller with `uninstall --project <project-root>` to remove its verified package and owned bindings. Private work and separately distributed installer skills are preserved. Install separately per checkout; generated absolute bindings are machine-specific.

## Dependencies and source

[Attribution and required notices](ATTRIBUTION.md) travel with the package. The manifest records source hashes and build transformations. [layers.json](layers.json) records the active replacements. Installation never follows upstream latest.

Optional helper programs still need their own runtimes or configured services. Read the [capability contract](shared/router/references/capabilities.md) before using them. Live CLI verification needs authenticated providers and consumes model usage. Hash checks establish integrity against the reviewed inputs, not the authenticity of an arbitrary download.
