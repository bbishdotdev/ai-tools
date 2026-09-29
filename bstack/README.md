# bstack

bstack is my opinionated suite of skills, agents, and tools for planning, building, and reviewing software. It's part of the [ai-tools collection](../README.md).

It builds on [Lauren "poteto" Tan's PStack](https://github.com/cursor/plugins/tree/main/pstack) and [Matt Pocock's skills](https://github.com/mattpocock/skills). Some workflows reuse their work directly, others adapt it, and others draw inspiration from it. Their work is a huge part of the foundation. bstack adds my own skills, preferences, and integrations to connect it all into one stack. [Attribution](ATTRIBUTION.md) records what comes from where.

## What bstack adds

- A connected [planning and engineering workflow](sdlc/README.md): questions, prototypes, specs, tickets, implementation, and PRs, with shared handoffs between phases.
- A shared [ADR process](shared/references/architecture-decisions.md) that carries fundamental decisions between phases and avoids reopening settled choices without new evidence. Most features need no ADR.
- A [local workspace app](workspace/README.md) for Wayfinder decision maps and a Kanban ticket board. You and your agent use the same saved work without needing an external tracker.
- One installer for Codex, Claude Code, Cursor, and Grok CLIs, with direct skill invocation and optional automatic routing through Poteto Mode.
- Optional [shared personal memory](shared/memory.md) across Codex, Claude, and Cursor's file bridge, with explicit approval for changes to personal notes.
- Custom [prototyping](engineering/prototype/SKILL.md), [writing rules](shared/skills/unslop/SKILL.md), and [visual PR briefings](engineering/to-pr/SKILL.md), shaped around how I work.
- A complete, pinned package that installs offline and preserves your selected tools and routing preferences when you upgrade.

Planning and ticket storage are local today. GitHub, Jira, and Linear tracker connections are future work; the [adapter contract](shared/references/work-adapters.md) allows planning and tickets to use different providers. GitHub PR publishing is already implemented. See [verification results and tool-specific limits](audit/package-layout.md) for tested coverage.

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

The command downloads the installer skill from `main`. Your agent then runs it to install the full bstack package and checks it with `doctor`. To stay on a published version, use a [tagged skills.sh source](INSTALL.md#install-a-published-version) or the release download below.

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

No Git, npm, skills.sh, or network access is needed during installation. A clone works too; use its bundled installer as described in [installation](INSTALL.md#from-a-download-or-clone).

After setup, start a fresh agent session to discover the skills. The agent offers automatic routing if it is off; enabling it is opt-in. Upgrades preserve your existing mode and selected tools. Neither route fetches upstream latest.

See [installation and updates](INSTALL.md) and [verification results and limits](audit/package-layout.md). Native plugin-manager installation and desktop behavior remain separate verification work.

## Use bstack

Invoke engineering skills such as `how` and `architect` directly, or use Poteto Mode to select a complete workflow. Automatic routing is opt-in. The bundle also includes Wayfinder, grilling, specs, ticket breakdown, triage, research, prototype, implementation entry, PR preparation, and shared handoff. Planning uses the same local records as the browser app.

Optional [shared memory setup](shared/memory.md) copies a user-wide runtime from the bundle for Codex, Claude, and Cursor's file bridge. Project installation leaves it inactive. It preserves existing notes and leaves legacy source-linked installations unchanged.

Autonomous cross-model execution remains separate implementation work. Configuring an external provider does not implement its operations or provision its services.

## Updates

[Changelog](CHANGELOG.md) collects unreleased changes and links to published release notes. Normal commits and pushes to `main` do not publish a release. A version tag starts the tested release workflow; [release preparation](RELEASING.md) covers when and how to do that.

## Work in the source tree

Paths below are relative to this `bstack/` folder:

- [Engineering](engineering/README.md) holds bstack-owned research, prototype, implementation and PR entries.
- `github/` holds the PR template and executable publishing helper, including the final overlap check and visual fallback.
- [SDLC](sdlc/README.md) holds owned planning skills and integration decisions.
- [Workspace](workspace/README.md) provides Wayfinder, specs and Kanban, with shared SQLite operations for its browser UI and JSON CLI.
- `shared/` holds the router, adapters, maintainer verification, and [memory implementation](shared/memory.md).
- [Upstream](upstream/README.md) holds unchanged, pinned source inputs. Use the [catalog](audit/catalog.md) and [architectural audit](audit/pstack.md) when reviewing those inputs.
- `package/` and `scripts/` assemble and check `release/`, the complete consumer installation artifact.
- `audit/` records source reviews and verification results.

The repository's root `AGENTS.md`, `CLAUDE.md`, and hidden host configuration support development of bstack. Private work and runtime evidence stay in the repository's gitignored `.bstack/` folder.

## Maintain and verify

Keep customizations separate from the frozen sources. Follow [upstream updates](UPSTREAM.md) to compare a new snapshot or adopt a selected improvement. [layers.json](layers.json) records the sources and active adaptations.

Run these commands from the **ai-tools repository root**:

```sh
python3 bstack/scripts/layers.py check
python3 bstack/scripts/audit_pstack.py
python3 bstack/scripts/package.py build
python3 bstack/scripts/package.py check
```

The [verification skill](shared/skills/verify-bstack/SKILL.md) describes targeted source, package, installation, and live CLI checks. See the [current package results](audit/package-layout.md) for direct skill discovery and installation evidence. Historical [packaging results](audit/packaging.md), [router results](audit/router-poc.md), [fallback results](audit/router-fallback.md), and [policy-layer results](audit/bstack-layers.md) record earlier checks and their limits. New evidence goes in gitignored `.bstack/verification/`.

[Kanban and SDLC verification](audit/kanban-sdlc.md) records the local app, 42-entry release, independent reviews, installed planning-to-tickets flow and fresh handoff checks, with their current limits.

[Portable memory verification](audit/portable-memory.md) records optional user installation, offline runtime independence, preservation and recovery tests, and the remaining live-recall and review limits.

Original bstack contributions use the shared [MIT license](../LICENSE). [bstack attribution](ATTRIBUTION.md) is the single maintained source for acknowledgments, ownership distinctions, and required notices. Generated releases carry that information with the installed bundle.
