# BStack

BStack is being assembled one component at a time. The first step is a pinned PStack import and a source audit.

Start with [how PStack works and the simplification options](audit/pstack.md). Use the [catalog](audit/catalog.md) to review individual skills and playbooks.

`engineering/` contains PStack 0.15.2 from `cursor/plugins` at `e31650eea443aaea1e84cc15d88c13f40080b275`, plus its three direct Cursor Team Kit companion skills. The `unslop` directory is the exact customized version from `code-maverick`. PStack's README, guide, license, Cursor manifest, scripts, agents, and dormant Benny pack are preserved.

The import remains a source installation, not a distributable BStack plugin. The router POC now adds repository-local instructions and adapters for Codex, Claude Code, Cursor, and Grok. It does not run PStack model setup or enable its automations. The upstream instructions in `engineering/` still describe PStack's original environment.

The [router POC results](audit/router-poc.md) record 12 passing routing checks across Codex, Claude Code, Cursor, and Grok, with explicit hook-support gaps. The [router adapter](shared/router/README.md) uses one short reminder and leaves Poteto Mode unchanged. The [maintainer verification skill](shared/skills/verify-bstack/SKILL.md) discovers installed CLIs, drives resumed sessions, checks fresh hook receipts, and captures native compaction evidence. Runtime transcripts live in gitignored `.bstack/verification/`.

The [after-tool fallback results](audit/router-fallback.md) add eight passing resumed CLI turns across Cursor and Grok, including fresh delivery, duplicate suppression, and tool-free behavior. This narrows the prompt-hook gap while preserving explicit limits around first-tool coverage and Cursor's headless lifecycle boundaries.

[pstack-provenance.json](pstack-provenance.json) records the sources, file hashes, permissions, and the approved `unslop` override. [The static inventory](audit/pstack-inventory.json) records file sizes and textual dependencies with source locations.

Verify the import and audit inventory from the repository root:

```bash
python3 BStack/scripts/audit_pstack.py
```

The checker uses the Python standard library and executes no imported workflow. `--write` regenerates the inventory after reviewed provenance changes. It does not silently accept changed vendor files.
