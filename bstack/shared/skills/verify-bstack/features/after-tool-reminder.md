# After-tool reminder

Cursor and Grok can reinforce standing router instructions after a tool result without requiring a wrapper command or loading the full router every turn.

## Contract

- Native `postToolUse` (Cursor) and `PostToolUse` (Grok) return the shared short reminder.
- At most one reminder is emitted per repository, host, conversation, and effective turn while the temporary state claim remains available.
- Subsequent tool results in that turn produce no context. A new user turn can emit a new reminder.
- Missing session/turn IDs produce an explicit skip diagnostic. They never become a session-wide suppression key.
- Grok's prompt-submission event supplies the turn ID when tool events omit it. Cursor headless uses a synthetic token reset by `sessionEnd` because its tool events reuse the conversation ID as the generation ID. Distinct native generation IDs use the direct path.
- Tool-free responses and the first tool call still rely on standing instructions.
- Grok's compatible invocation of another host's adapter is a no-op; its native adapter remains active.

## Drive

Run doctor, then `python3 bstack/shared/skills/verify-bstack/scripts/fallback.py` from the repository root after live provider calls are authorized. This discovers installed Cursor/Grok CLIs. Use `--tools grok` or `--tools cursor` to focus the run; explicitly requested missing clients are blocked.

In each host, the harness starts one session and resumes it through four user turns:

1. Read a fixture containing a random value and the path to a second fixture. Read the second fixture afterward and echo both values plus the current after-tool receipt.
2. Repeat with new fixtures in the same conversation. Require a new turn ID and receipt.
3. Classify a request using retained instructions without calling any tools. Require zero tool calls, zero after-tool events, and no current receipt.
4. Read another dependent fixture pair. Require the reminder to return with a fresh receipt after the tool-free turn.

Each turn also checks a routing choice and a router-specific fact. The tool traces must show the first fixture read completed before the second starts. Each tool turn must have exactly one emission and at least one duplicate suppression. Grok's prompt boundary must precede its tool events; Cursor's session-end reset must follow them. A lifecycle/session receipt cannot satisfy the after-tool receipt assertion. Hook metadata includes effective/native turn IDs and the boundary source. It is collected under a temporary directory and copied to the durable evidence folder; it does not include incoming prompts or tool bodies.

## Evidence and limits

Keep command arguments, prompts, raw CLI streams, diagnostics, expected fixture values, hook records, per-turn assessments, and the aggregate report under `.bstack/verification/`. Inspect every failed assertion; an unsupported native event remains incomplete, not a routing pass. Raw transcripts can contain instruction content read by the CLI and stay gitignored.

Run `python3 bstack/shared/router/test_hook.py` for protocol, missing-ID, host/session/turn isolation, lifecycle bridging, and concurrent-process checks. Concurrency verifies the atomic claim, while real echoed receipts establish delivery. A crash after claiming can prevent delivery; deleting or expiring state can permit another emission. Cursor hard kills can skip the reset and suppress the first resumed invocation. Concurrent use of one conversation can race with boundary changes. The live contract covers normal serial headless invocations; it does not establish prompt-level parity, desktop or interactive UI support, compaction recovery, crash recovery, or universal compliance with the router.
