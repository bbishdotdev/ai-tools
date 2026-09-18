# BStack

BStack is being assembled one component at a time. It currently has a pinned PStack import, a separate BStack policy layer, and repository-local CLI adapters.

Start with [how PStack works and the simplification options](audit/pstack.md). Use the [catalog](audit/catalog.md) to review individual skills and playbooks.

`engineering/` contains unmodified PStack 0.15.2 from `cursor/plugins` at `e31650eea443aaea1e84cc15d88c13f40080b275`, plus its three direct Cursor Team Kit companion skills. PStack's README, guide, license, Cursor manifest, scripts, agents, and dormant Benny pack are preserved. BStack's customized `unslop` from `code-maverick` lives separately under `shared/skills/unslop/`.

The import remains a source installation, not a distributable BStack plugin. The router POC adds repository-local instructions and adapters for Codex, Claude Code, Cursor, and Grok. It does not run PStack model setup or enable its automations. The upstream instructions in `engineering/` still describe PStack's original environment. The active [BStack router](shared/skills/bstack-router/SKILL.md) applies scoped routing, capability-based tool choices, risk-based architecture, and evidence reporting over that source. This is an instruction policy, not an implementation of every provider adapter.

See [upstream updates and layer ownership](UPSTREAM.md) before changing an imported file. [layers.json](layers.json) records BStack-owned overlays and replacement skills separately from their pinned upstream review bases. The same arrangement can support selected Matt Pocock skills later; none have been imported yet.

The [policy-layer report](audit/bstack-layers.md) describes the approved behavior changes, source separation, and CLI verification scope.

The historical [router POC results](audit/router-poc.md) record 12 passing routing checks against the original entry across Codex, Claude Code, Cursor, and Grok, with explicit hook-support gaps. The [router adapter](shared/router/README.md) now points its short reminder to BStack's entry. The [maintainer verification skill](shared/skills/verify-bstack/SKILL.md) discovers installed CLIs, drives resumed sessions, checks fresh hook receipts, and captures native compaction evidence. Its policy probes evaluate the new layer separately. Runtime transcripts live in gitignored `.bstack/verification/`.

The [after-tool fallback results](audit/router-fallback.md) add eight passing resumed CLI turns across Cursor and Grok, including fresh delivery, duplicate suppression, and tool-free behavior. This narrows the prompt-hook gap while preserving explicit limits around first-tool coverage and Cursor's headless lifecycle boundaries.

[pstack-provenance.json](pstack-provenance.json) records upstream sources, file hashes, and permissions. The approved `unslop` customization is recorded in the layer registry. [The static inventory](audit/pstack-inventory.json) records imported file sizes and textual dependencies with source locations.

Verify the import and audit inventory from the repository root:

```bash
python3 BStack/scripts/audit_pstack.py
python3 BStack/scripts/layers.py check
```

The checker uses the Python standard library and executes no imported workflow. `--write` regenerates the inventory after reviewed provenance changes. It does not silently accept changed vendor files.
