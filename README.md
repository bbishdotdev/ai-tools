# bstack

bstack is Brenden Bishop's collection of engineering and SDLC workflows, agent adapters, and custom skills. It connects planning, prototyping, implementation, and verification across agent tools.

The current bundle supports project installation for Codex, Claude Code, Cursor, and Grok CLIs. Engineering skills such as `how` and `architect` are available directly. Poteto Mode selects a complete engineering workflow; automatic routing is opt-in. [Owned SDLC adaptations](bstack/sdlc/README.md) connect Matt Pocock's planning approach to bstack's engineering workflows while preserving the pinned sources for selective updates.

The bundled [local workspace app](bstack/workspace/README.md) provides Wayfinder maps, approved specs, and a Kanban ticket board. Browser and agent CLI use the same SQLite store. Planning and tickets have separate adapter choices; local is currently implemented, with external providers left for later integration.

## Install

From a local clone, install the exact reviewed bundle into your project:

```sh
python3 bstack/release/bstack/scripts/bstack.py install \
  --project /path/to/your/project --hosts codex claude cursor grok
```

This path requires Python 3.11+ on POSIX and works from a transferred release directory without npm or skills.sh. Installation uses the bundled PStack revision and bstack customizations; it never fetches upstream latest.

See [installation and optional skills.sh distribution](bstack/INSTALL.md), [current scope](bstack/README.md), and [verification results and limits](bstack/audit/package-layout.md). Native plugin-manager installation and desktop behavior remain separate verification work.

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

The shared-memory source has moved under bstack; it is not yet part of the consumer release. See [shared memory setup](bstack/shared/memory.md) before changing an existing installation.

Original bstack contributions use the [MIT license](LICENSE). [Attribution](ATTRIBUTION.md) centralizes acknowledgments, the source map, and applicable third-party notices. [Upstream updates](bstack/UPSTREAM.md) describes how to adopt improvements without overwriting bstack's work.
