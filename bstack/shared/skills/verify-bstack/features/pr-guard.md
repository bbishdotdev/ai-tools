# PR creation guard

The installed host hook should redirect a direct shell `gh pr create` or body-replacing `gh pr edit` to `to-pr`, even when automatic routing is off. The message must name the next action briefly. Title-only edits, views, and ordinary shell commands should pass. A package doctor result proves only that the hook binding exists.

Run `bstack/scripts/test_pr_guard.py` for command forms and each host payload. In disposable installed projects, inspect the generated Codex, Claude Code, Cursor, and Grok bindings. Live host tests must attempt the command without publishing a real PR and observe an actual denial; local script tests alone do not prove that the host invokes or trusts the hook. This guard catches supported shell invocations, not arbitrary GitHub APIs, wrappers, or a user deliberately bypassing it.
