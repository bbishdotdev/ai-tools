# Context recovery

bstack remains available when a developer resumes work or the client compacts a long conversation.

## Sub-features

- Resume preserves the same session and previously selected workflow.
- Codex and Claude `SessionStart` with source `compact` restores the reminder before continuation.
- The agent rereads full instructions if compaction removed them.

## How to get to it (user POV)

Resume the test session in the appropriate CLI. For actual compaction, use the client's native compaction command or lifecycle API on that disposable session. Desktop compaction must be driven in the desktop surface itself.

## Driving it with verify.py

Preconditions: a completed live run and its saved session identifiers.

- The automated live suite resumes each session twice and captures evidence.
- For native compaction, run `python3 bstack/shared/skills/verify-bstack/scripts/compact.py --tool claude --report .bstack/verification/<run>/claude/report.json`, or substitute `codex` in both positions. Retain the actual compact event, `SessionStart` hook with source `compact`, and the next response. Compare its receipt and source reads with the pre-compaction run.
- Until that native path runs, report compaction as unverified. Unit tests of synthetic hook payloads are adapter tests only.

## Gotchas

Do not simulate compaction by asking the model to forget. Do not infer desktop behavior from CLI results. A summary that says a router was loaded does not contain the router's complete instructions.
