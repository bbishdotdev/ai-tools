# Native after-tool fallback: verified 2026-09-18

Historical evidence predates the lowercase directory rename. Commands here use the current path; saved JSON evidence retains the original observed paths.

Cursor and Grok passed four resumed headless CLI turns each with the shared bstack reminder. Each tool-using turn received exactly one fresh reminder, verified by a random receipt echoed by the model. Later tool results in that turn emitted no additional reminder. Both CLIs read the full Poteto Mode router on turn one only, then retained the tested routing behavior through the remaining turns.

| Check | Cursor 2026.09.15-d2fe57e | Grok 1.0.34 |
|---|---|---|
| Correct routes and router-specific fact | 4/4 | 4/4 |
| Fresh after-tool receipt | Turns 1, 2, 4 | Turns 1, 2, 4 |
| Duplicate reminders suppressed | 2, 1, 1 across tool turns | 2, 1, 1 across tool turns |
| Tool-free third turn | 0 calls, 0 after-tool emissions | 0 calls, 0 after-tool emissions |
| Router disk reads | Turn 1 only | Turn 1 only |
| Boundary evidence | Session-end reset after each invocation | Prompt submission before each turn's tools |

The production reminder remains 323 characters in this checkout. Verification adds a receipt, making the tested after-tool context 390 characters. No full router text is injected by the hook. The existing Codex/Claude prompt adapters remain in place; this focused live run exercised Cursor/Grok only. Local protocol tests also cover the unchanged Codex/Claude delivery shapes.

## What the native-ID test uncovered

The first live run failed the suppression/delivery checks because installed CLIs differed from their documented common schemas:

- Cursor headless reused the conversation ID as `generation_id` across resumed turns. That would suppress every turn after the first. The installed bundle confirms that the headless path uses the conversation ID; its interactive path supplies a changing generation ID. Headless probes did not emit `beforeSubmitPrompt` or `stop`, but did emit `sessionEnd`.
- Grok omitted `promptId` from tool events. Its native `UserPromptSubmit` event did supply it, so the adapter retains that ID for the tool hooks in the same session. The prompt hook contributes no model context.

The final adapter bridges these observed lifecycle boundaries using a small temporary SQLite cache. It does not inspect transcript contents. Atomic claims suppress concurrent tool-result duplicates; nine local protocol tests cover the native shapes, compatibility guard, missing IDs, isolation, concurrency, and lifecycle bridging.

## Limits

This is an after-tool fallback. Standing instructions still cover the first tool call and all tool-free responses. Correct routing on the tool-free turn demonstrates retained instructions for this probe, not new hook delivery.

Cursor headless uses a temporary effective-turn token cleared on `sessionEnd`. A hard kill can skip that reset and leave a stale claim for the first resumed invocation. Concurrent invocations of the same conversation can race with lifecycle changes. Grok's retained prompt ID also assumes serial turns per session. These tests prove the normal serial path, not universal exactly-once delivery or recovery from every interruption.

Grok still warns while parsing Cursor's separate hook format, including global configuration outside bstack. The native `.grok/hooks/bstack.json` route delivered all three fresh after-tool receipts despite those warnings. No global configuration was changed to hide them.

Desktop apps, interactive CLI UIs, crash recovery, concurrent use of one conversation, and compaction under these new fallback paths were not exercised. The earlier Codex/Claude compaction results remain separate evidence. All imported PStack files remain unchanged.

## Reproduce and inspect

```bash
python3 bstack/shared/router/test_hook.py
python3 bstack/shared/skills/verify-bstack/scripts/verify.py doctor
python3 bstack/shared/skills/verify-bstack/scripts/fallback.py
```

- [Portable results summary](router-fallback-results.json)
- Passing raw evidence: `.bstack/verification/20260918T203500Z-fallback-b0da01/report.json`
- Preserved failing native-ID run: `.bstack/verification/20260918T202835Z-fallback-c9c645/report.json`
- Lifecycle discovery probe: `.bstack/verification/20260918-fallback-boundary-probe/`
- [Feature contract](../shared/skills/verify-bstack/features/after-tool-reminder.md)
- [Adapter design](../shared/router/README.md)

The native output contracts were checked against [Cursor's hook reference](https://cursor.com/docs/hooks) and [Grok's hook reference](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/10-hooks.md). Installed-version behavior above comes from retained live evidence and Cursor's local bundle, rather than assuming the documented fields are present or unique.
