# bstack

bstack is Brenden Bishop's collection of engineering and SDLC workflows, agent adapters, and custom skills. It connects planning, prototyping, implementation, and verification across agent tools.

The current bundle supports project installation for Codex, Claude Code, Cursor, and Grok CLIs. Engineering skills such as `how` and `architect` are available directly. Poteto Mode selects a complete engineering workflow; automatic routing is opt-in. [Selected Matt Pocock SDLC skills, handoff, and their dependencies](bstack/sdlc/README.md) are pinned in the source tree for review; their consumer release integration and local work planning remain pending.

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
- `bstack/sdlc/` contains SDLC selection and integration decisions.
- `bstack/shared/` contains shared policy, custom skills, router adapters, and the existing memory implementation.
- `bstack/upstream/` contains frozen third-party source snapshots used for comparison and release assembly.
- `bstack/package/` and `bstack/scripts/` assemble and verify the consumer bundle.
- `bstack/release/` is the complete generated installation artifact.
- `bstack/audit/` records source reviews and verification results.

Root `AGENTS.md`, `CLAUDE.md`, and hidden host configuration support development of bstack. Private work and runtime evidence stay in gitignored `.bstack/`.

The shared-memory source has moved under bstack; it is not yet part of the consumer release. See [shared memory setup](bstack/shared/memory.md) before changing an existing installation.

Original bstack contributions use the [MIT license](LICENSE). [Attribution](ATTRIBUTION.md) centralizes acknowledgments, the source map, and applicable third-party notices. [Upstream updates](bstack/UPSTREAM.md) describes how to adopt improvements without overwriting bstack's work.
