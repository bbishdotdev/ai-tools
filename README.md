# bstack

bstack is my opinionated suite of skills, agents, and tools for planning, building, and reviewing software.

It builds on [Lauren "poteto" Tan's PStack](https://github.com/cursor/plugins/tree/main/pstack) and [Matt Pocock's skills](https://github.com/mattpocock/skills). Some workflows reuse their work directly, others adapt it, and others draw inspiration from it. Their work is a huge part of the foundation. bstack adds my own skills, preferences, and integrations to connect it all into one stack. [Attribution](ATTRIBUTION.md) records what comes from where.

## What bstack adds

- A connected [planning and engineering workflow](bstack/sdlc/README.md): questions, prototypes, specs, tickets, implementation, and PRs, with shared handoffs between phases.
- A [local workspace app](bstack/workspace/README.md) for Wayfinder decision maps and a Kanban ticket board. You and your agent use the same saved work without needing an external tracker.
- One installer for Codex, Claude Code, Cursor, and Grok CLIs, with direct skill invocation and optional automatic routing through Poteto Mode.
- Optional [shared personal memory](bstack/shared/memory.md) across Codex, Claude, and Cursor's file bridge, with explicit approval for changes to personal notes.
- Custom [prototyping](bstack/engineering/prototype/SKILL.md), [writing rules](bstack/shared/skills/unslop/SKILL.md), and [visual PR briefings](bstack/engineering/to-pr/SKILL.md), shaped around how I work.
- A complete, pinned package that installs offline and preserves your selected tools and routing preferences when you upgrade.

Planning and ticket storage are local today. GitHub, Jira, and Linear tracker connections are future work; the [adapter contract](bstack/shared/references/work-adapters.md) allows planning and tickets to use different providers. GitHub PR publishing is already implemented. See [verification results and tool-specific limits](bstack/audit/package-layout.md) for tested coverage.

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

The command downloads the installer skill from `main`. Your agent then runs it to install the full bstack package and checks it with `doctor`. To stay on a published version, use a [tagged skills.sh source](bstack/INSTALL.md#install-a-published-version) or the release download below.

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

## Updates

[Changelog](CHANGELOG.md) collects unreleased changes and links to published release notes. Normal commits and pushes to `main` do not publish a release. A version tag starts the tested release workflow; [release preparation](bstack/RELEASING.md) covers when and how to do that.

## Repository layout

- `bstack/engineering/` contains bstack-owned engineering workflows.
- `bstack/sdlc/` contains owned planning skills and their design history.
- `bstack/workspace/` contains the local planning app, SQLite operations, and agent CLI.
- `bstack/shared/` contains shared policy, custom skills, router adapters, and the existing memory implementation.
- `bstack/upstream/` contains frozen third-party source snapshots used for comparison and release assembly.
- `bstack/package/` and `bstack/scripts/` assemble and verify the consumer bundle.
- `bstack/release/` is the complete generated installation artifact.
- `bstack/audit/` records source reviews and verification results.

Root `AGENTS.md`, `CLAUDE.md`, and hidden host configuration support development of bstack. Private work and runtime evidence stay in gitignored `.bstack/`.

Optional [shared memory setup](bstack/shared/memory.md) copies a user-wide runtime from the bundle for Codex, Claude, and Cursor's file bridge. Project installation leaves it inactive. Existing source-linked installations remain unchanged.

Original bstack contributions use the [MIT license](LICENSE). [Attribution](ATTRIBUTION.md) centralizes acknowledgments, the source map, and applicable third-party notices. [Upstream updates](bstack/UPSTREAM.md) describes how to adopt improvements without overwriting bstack's work.
