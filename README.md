# bstack

bstack is my collection of engineering and SDLC workflows, agent adapters, and custom skills. It connects planning, prototyping, implementation, and verification across agent tools.

The current bundle supports project installation for Codex, Claude Code, Cursor, and Grok CLIs. Engineering skills such as `how` and `architect` are available directly. Poteto Mode selects a complete engineering workflow; automatic routing is opt-in. [Owned SDLC adaptations](bstack/sdlc/README.md) connect Matt Pocock's planning approach to bstack's engineering workflows while preserving the pinned sources for selective updates.

The bundled [local workspace app](bstack/workspace/README.md) provides Wayfinder maps, approved specs, and a Kanban ticket board. Browser and agent CLI use the same SQLite store. Planning and tickets have separate adapter choices; local is currently implemented, with external providers left for later integration.

## Install

Choose either route. Both install the same bundled skills, dependencies, and customizations. Python 3.11+ on macOS or Linux is required.

### With skills.sh

From the project where you want to use bstack, run:

```sh
npx skills add bbishdotdev/ai-tools --skill install-bstack
```

Choose your agent and project scope if prompted. Then open your agent in that project and ask:

> Install bstack in this project.

Or invoke `$install-bstack` in Codex, `/install-bstack` in Claude Code or Cursor. If the skill does not appear, start a fresh session in the same project.

The command downloads the installer skill. Your agent then runs it to install the full bstack package and checks it with `doctor`.

To make the installer available across projects, add `-g` to the command above. Then invoke it from any target repo. Only the installer is global; each repo gets its own bstack package.

`bbishdotdev/ai-tools` identifies this repository; `--skill install-bstack` selects its installer. Keep both parts. You don't need to select all the skills in the development repository.

### From a download or clone

[Download bstack](https://github.com/bbishdotdev/ai-tools/releases/latest). Choose the `bstack-<version>.zip` asset and extract it. It contains one `bstack/` folder with the installer and the full package. GitHub's automatic source archives contain the development repository instead.

Ask your agent:

> Read SKILL.md in the extracted bstack folder and install bstack into my project at /path/to/my-project.

Or run this from the extracted folder:

```sh
python3 install.py --project /path/to/my-project
```

No Git, npm, skills.sh, or network access is needed during installation. A clone works too; use its bundled installer as described in [installation](bstack/INSTALL.md#from-a-download-or-clone).

After setup, start a fresh agent session to discover the skills. The agent offers automatic routing if it is off; enabling it is opt-in. Upgrades preserve your existing mode and selected tools. Neither route fetches upstream latest.

See [installation and updates](bstack/INSTALL.md), [current scope](bstack/README.md), and [verification results and limits](bstack/audit/package-layout.md). Native plugin-manager installation and desktop behavior remain separate verification work.

## Repository layout

- `bstack/engineering/` contains bstack-owned engineering workflows.
- `bstack/sdlc/` contains owned planning skills and their design history.
- `bstack/workspace/` contains the local planning app, SQLite operations, and agent CLI.
- `bstack/shared/` contains shared policy, custom skills, router adapters, and the existing memory implementation.
- `bstack/upstream/` contains frozen third-party source snapshots used for comparison and release assembly.
- `bstack/package/` and `bstack/scripts/` assemble and verify the consumer bundle.
- `bstack/release/` is the complete generated installation artifact.
- [Release preparation](bstack/RELEASING.md) covers building and publishing the downloadable package.
- `bstack/audit/` records source reviews and verification results.

Root `AGENTS.md`, `CLAUDE.md`, and hidden host configuration support development of bstack. Private work and runtime evidence stay in gitignored `.bstack/`.

Optional [shared memory setup](bstack/shared/memory.md) copies a user-wide runtime from the bundle for Codex, Claude, and Cursor's file bridge. Project installation leaves it inactive. Existing source-linked installations remain unchanged.

Original bstack contributions use the [MIT license](LICENSE). [Attribution](ATTRIBUTION.md) centralizes acknowledgments, the source map, and applicable third-party notices. [Upstream updates](bstack/UPSTREAM.md) describes how to adopt improvements without overwriting bstack's work.
