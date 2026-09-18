# bstack verification map

The POC verifies real CLI sessions against bstack's policy entry and its pinned PStack dependencies. Earlier reports using Poteto Mode directly are historical baseline evidence. Local desktop apps are separate surfaces and require their own evidence.

- [Router activation](router-activation.md): initial discovery, prompt reminders, selected dependency reads, and reuse.
- [Router policy](router-policy.md): fresh-session classification, design risk, local/provider delivery, authorization, and audit claims.
- [Upstream layers](upstream-layers.md): pinned-source integrity, separate owned adaptations, and read-only candidate review.
- [After-tool reminder](after-tool-reminder.md): Cursor/Grok native fallback, once-per-turn emission, and tool-free limits.
- [Context recovery](context-recovery.md): resume and actual compaction recovery.
- [CLI discovery](cli-discovery.md): installed clients, versions, selection, missing tools, and capability gaps.

Run doctor first. Capture commands, exit codes, model responses, and hook output receipts in `.bstack/verification/`. A missing client, missing authentication, unsupported hook, or unexercised surface must remain visible in the report. Test receipts exist only during verification; they do not turn the production reminder into a transcript analyzer.
