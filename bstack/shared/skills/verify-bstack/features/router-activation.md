# Router activation

A developer can prompt normally while bstack keeps its router available and loads relevant instructions on demand.

## Sub-features

- First response loads the router from repository instructions.
- Codex and Claude Code receive a fresh short reminder on each user prompt.
- Cursor receives a session reminder and a standing rule; its prompt hook has no context output. Its after-tool fallback is a separate feature.
- Grok receives standing repository instructions and a native after-tool fallback; its prompt hook cannot add context in the tested version.
- Follow-up turns reuse loaded context when sufficient.
- Router and supporting files remain unchanged by verification.

## How to get to it (user POV)

Start an installed Codex, Claude Code, Cursor, or Grok CLI here. For the automated POC, run `python3 bstack/shared/skills/verify-bstack/scripts/verify.py live` to discover and test installed clients.

## Driving it with verify.py

Preconditions: repository adapters installed, CLI authenticated, and hook trust reviewed.

- Start one new session per selected tool. Ask for a read-only classification of a bug report without naming the router path. Observe a router read and the bug-fix route.
- Resume the same session with a performance request, then a read-only investigation. Capture receipts and route choices for all turns.
- Compare each response receipt to that turn's hook output. Preserve missing receipts as failures or unsupported results.
- Inspect file-read tool events independently of model claims. Report rereads rather than treating them as silent success.

## Gotchas

A synthetic routing probe establishes a controlled POC, not general task success. The prompt restricts execution to reading/classification. It must not cause code edits, PRs, or delegation. Hook logs show emission; only the matching model response proves the receipt was seen. Cursor's session receipt cannot prove delivery on subsequent prompts.
