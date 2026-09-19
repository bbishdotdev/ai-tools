# bstack

bstack is Brenden Bishop's integrated collection of engineering and SDLC workflows, agent adapters, and custom skills. It builds on open-source work, with source attribution and bstack's changes tracked separately.

The engineering foundation is [PStack by Lauren "poteto" Tan](https://github.com/cursor/plugins/tree/main/pstack). The planned SDLC foundation is a selection from [Matt Pocock's skills](https://github.com/mattpocock/skills). bstack connects these workflows and adds Brenden's operating preferences. See [credits and source relationships](ATTRIBUTION.md) for authors, licenses, and the distinction between imported, adapted, and original work.

bstack names the whole collection. **Poteto Mode** remains the name of its PStack-based engineering mode. The adapter command design keeps `/poteto-mode`; collection-wide automatic activation is a separate setting.

## Direction and current scope

The goal is one distributable plugin that connects engineering and SDLC workflows across Codex, Claude Code, and Cursor, with CLI verification also covering Grok. Planned additions include shared memory and context handling, local-first work planning, GitHub templates and CI jobs, and selected Matt Pocock skills. Those pieces will join the package in reviewed steps.

Today, bstack has a pinned PStack import, a separate policy layer, customized `unslop`, and a generated consumer bundle with project-local CLI adapters. [Install the complete bundle](INSTALL.md) from a local clone or transferred folder using Python, or through skills.sh. Both routes use the exact bundled revision. New installations default to manual Poteto Mode; automatic routing is an explicit opt-in. The development repository's earlier POC still uses its previously authorized automatic routing.

Matt Pocock's skills, shared memory integration, local work management, desktop verification, and native plugin-manager installation remain future work.

Start with [how PStack works and the simplification options](audit/pstack.md). Use the [catalog](audit/catalog.md) to review individual skills and playbooks.

`engineering/` contains unmodified PStack 0.15.2 from `cursor/plugins` at `e31650eea443aaea1e84cc15d88c13f40080b275`, plus its three direct Cursor Team Kit companion skills. PStack's README, guide, license, Cursor manifest, scripts, agents, and dormant Benny pack are preserved. bstack's customized `unslop` from `code-maverick` lives separately under `shared/skills/unslop/`.

The source import remains unchanged. The generated `release/` assembles bstack's policy and replacements with selected dependencies, portable paths, helper source, and notices. It does not run PStack model setup or enable its automations. The upstream instructions in `engineering/` still describe PStack's original environment. The active [bstack router](shared/skills/bstack-router/SKILL.md) applies scoped routing, capability-based tool choices, risk-based architecture, and evidence reporting over that source. This is an instruction policy, not an implementation of every provider adapter.

## Selective upstream updates

bstack keeps reviewed source pins and adopts upstream improvements deliberately. It does not automatically follow the latest upstream release. Maintainers can review a newer snapshot or port selected improvements into bstack-owned adaptations without replacing unrelated choices.

See [upstream updates and layer ownership](UPSTREAM.md) before changing an imported file. [layers.json](layers.json) records bstack-owned overlays and replacement skills separately from their pinned upstream review bases. The same arrangement can support selected Matt Pocock skills later.

## Verification and source records

The historical [raw-source skills.sh probe](audit/skills-install.md) found missing dependencies and notices, incorrect overrides, and absent setup. The generated release addresses those packaging gaps. Use `python3 bstack/scripts/package.py build` to assemble it and `python3 bstack/scripts/package.py check` to detect stale or altered output. [The installation guide](INSTALL.md) explains the current distribution and host boundaries.

The [consumer packaging report](audit/packaging.md) records matching offline/copy/symlink installs, 77 deterministic tests, and 20 live CLI routing/mode probes. Codex reminder delivery remains explicitly limited by native project trust in fresh fixtures; desktop and native plugin-manager installation are not claimed.

The [policy-layer report](audit/bstack-layers.md) describes the approved behavior changes, source separation, and CLI verification scope.

The historical [router POC results](audit/router-poc.md) record 12 passing routing checks against the original entry across Codex, Claude Code, Cursor, and Grok, with explicit hook-support gaps. The [router adapter](shared/router/README.md) now points its short reminder to bstack's entry. The [maintainer verification skill](shared/skills/verify-bstack/SKILL.md) discovers installed CLIs, drives resumed sessions, checks fresh hook receipts, and captures native compaction evidence. Its policy probes evaluate the new layer separately. Runtime transcripts live in gitignored `.bstack/verification/`.

The [after-tool fallback results](audit/router-fallback.md) add eight passing resumed CLI turns across Cursor and Grok, including fresh delivery, duplicate suppression, and tool-free behavior. This narrows the prompt-hook gap while preserving explicit limits around first-tool coverage and Cursor's headless lifecycle boundaries.

[pstack-provenance.json](pstack-provenance.json) records upstream sources, file hashes, and permissions. The approved `unslop` customization is recorded in the layer registry. [The static inventory](audit/pstack-inventory.json) records imported file sizes and textual dependencies with source locations.

Verify the import and audit inventory from the repository root:

```bash
python3 bstack/scripts/audit_pstack.py
python3 bstack/scripts/layers.py check
```

The checker uses the Python standard library and executes no imported workflow. `--write` regenerates the inventory after reviewed provenance changes. It does not silently accept changed vendor files.
