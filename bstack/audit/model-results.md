# Model results

How each model did with bstack on each host. Each cell is `integration · quality of repeats`. Integration means the model loaded and followed bstack's routing, workflows, and hooks. Quality means it then did the work well: hidden tests, avoiding rejected alternatives, verifier coverage, and correct answers. The compatibility matrix uses the most recent integration result per host.

Last recorded: 2026-10-27.

| Tool | Model | misleading-bug | feature-verifier | adr-rejected | late-pr | direct-pr | compaction-resume |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Codex CLI | `gpt-reserve` | 3 · 2 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 |
| Claude Code CLI | `claude-sonnet-5-5` | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 |
| Cursor CLI | `claude-sonnet-5-thinking-high` | - | 3 · 3 of 3 | - | - | - | 3 · 3 of 3 |
| Cursor CLI | `composer-2.5` | 3 · 1 of 3 | 2 · 0 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 2 · 3 of 3 |
| Grok CLI | `grok-4.7` | 3 · 1 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 |
| Amp CLI | `low` | 3 · 1 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | - |
| GitHub Copilot CLI | `auto` | 3 · 1 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 2 · 2 of 2 | 2 · 2 of 2 | 2 · 2 of 2 |
| OpenCode CLI | `opencode/claude-haiku-5-5` | 3 · 3 of 3 | 1 · 3 of 3 | 2 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | 3 · 3 of 3 |
| OpenCode CLI | `opencode/claude-sonnet-5-5` | 3 · 2 of 3 | 3 · 3 of 3 | 3 · 3 of 3 | - | - | - |
