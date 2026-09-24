# bstack

bstack combines engineering and SDLC workflows with shared agent configuration, context handling, and verification. The collection is designed for Codex, Claude Code, and Cursor, with CLI verification also covering Grok.

## Use the current bundle

[Install the complete bundle](INSTALL.md) from a local clone, a transferred release, or skills.sh. Installation uses the exact bundled source and customizations. It never fetches newer upstream skills.

Invoke engineering skills such as `how` and `architect` directly, or use Poteto Mode to select a complete workflow. Automatic routing is opt-in. The bundle also includes Wayfinder, grilling, specs, ticket breakdown, triage, research, prototype, implementation entry, PR preparation and shared handoff. Planning uses the same local records as the browser app. The development repository retains its previously authorized automatic routing.

## Work in the source tree

- [Engineering](engineering/README.md) holds bstack-owned research, prototype, implementation and PR entries.
- `github/` holds the PR template and executable publishing helper, including the final overlap check and visual fallback.
- [SDLC](sdlc/README.md) holds owned planning skills and integration decisions.
- [Workspace](workspace/README.md) provides Wayfinder, specs and Kanban, with shared SQLite operations for its browser UI and JSON CLI.
- `shared/` holds the router, adapters, maintainer verification, and [memory implementation](shared/memory.md).
- [Upstream](upstream/README.md) holds unchanged, pinned source inputs. Use the [catalog](audit/catalog.md) and [architectural audit](audit/pstack.md) when reviewing those inputs.
- `package/` and `scripts/` assemble and check `release/`, the complete consumer installation artifact.

Optional [shared memory setup](shared/memory.md) installs a separate user runtime from the bundle. It preserves existing notes and leaves legacy source-linked installations unchanged. External planning/ticket providers, autonomous cross-model execution, desktop apps and native plugin-manager installation remain separate implementation or verification work. Configuring a provider does not implement its operations or provision its services.

## Maintain and verify

Keep customizations separate from the frozen sources. Follow [upstream updates](UPSTREAM.md) to compare a new snapshot or adopt a selected improvement. [layers.json](layers.json) records the sources and active adaptations.

```sh
python3 bstack/scripts/layers.py check
python3 bstack/scripts/audit_pstack.py
python3 bstack/scripts/package.py build
python3 bstack/scripts/package.py check
```

The [verification skill](shared/skills/verify-bstack/SKILL.md) describes targeted source, package, installation, and live CLI checks. See the [current package results](audit/package-layout.md) for direct skill discovery and installation evidence. Historical [packaging results](audit/packaging.md), [router results](audit/router-poc.md), [fallback results](audit/router-fallback.md), and [policy-layer results](audit/bstack-layers.md) record earlier checks and their limits. New evidence goes in gitignored `.bstack/verification/`.

[Kanban and SDLC verification](audit/kanban-sdlc.md) records the local app, 42-entry release, independent reviews, installed planning-to-tickets flow and fresh handoff checks, with their current limits.

[Portable memory verification](audit/portable-memory.md) records optional user installation, offline runtime independence, preservation and recovery tests, and the remaining live-recall and review limits.

[Root attribution](../ATTRIBUTION.md) is the single maintained source for acknowledgments, ownership distinctions, and required notices. Generated releases carry that information with the installed bundle.
