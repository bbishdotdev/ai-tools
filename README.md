# bstack

bstack is Brenden Bishop's collection of engineering workflows, agent adapters, and custom skills. It builds on [PStack by Lauren "poteto" Tan](https://github.com/cursor/plugins/tree/main/pstack), with bstack's policy and customizations tracked separately from the pinned upstream source.

The current bundle supports project installation for Codex, Claude Code, Cursor, and Grok CLIs. Poteto Mode is the manual engineering entry; automatic routing is opt-in. [Selected Matt Pocock SDLC skills, handoff, and their dependencies](bstack/sdlc/README.md) are pinned in the source tree for review; their consumer release integration and local work planning remain pending.

## Install

From a local clone, install the exact reviewed bundle into your project:

```sh
python3 bstack/release/skills/poteto-mode/scripts/bstack.py install \
  --project /path/to/your/project --hosts codex claude cursor grok
```

This path requires Python 3.11+ on POSIX and works from a transferred release directory without npm or skills.sh. Installation uses the bundled PStack revision and bstack customizations; it never fetches upstream latest.

See [installation and optional skills.sh distribution](bstack/INSTALL.md), [current scope](bstack/README.md), and [verification results and limits](bstack/audit/packaging.md). Native plugin-manager installation and desktop behavior remain separate verification work.

## Repository layout

- `bstack/engineering/` contains pinned upstream PStack sources.
- `bstack/sdlc/` contains the selected Matt Pocock sources and their dependency review notes.
- `bstack/shared/` contains bstack's policy, custom skills, router adapters, the existing shared-memory source, Matt's pinned handoff skill, and the SDLC dependency sources.
- `bstack/package/` and `bstack/scripts/` assemble and verify the consumer bundle.
- `bstack/release/` is the complete generated installation artifact.
- `bstack/audit/` records source reviews and verification results.

Root `AGENTS.md`, `CLAUDE.md`, and hidden host configuration support development of bstack. Private work and runtime evidence stay in gitignored `.bstack/`.

The shared-memory source has moved under bstack; it is not yet part of the consumer release. See [shared memory setup](bstack/shared/memory.md) before changing an existing installation.

See [attribution](bstack/ATTRIBUTION.md) and [upstream updates](bstack/UPSTREAM.md) for authors, source pins, and ownership of adaptations.
