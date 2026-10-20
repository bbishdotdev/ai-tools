# Project PR policy

## Human review required

- `AGENTS.md`: Changes to the project's standing agent rules need a human reviewer.
- `CLAUDE.md`: Changes to the project's standing Claude rules need a human reviewer.
- `bstack/shared/references/baseline-agents.md`: Changes to the baseline shipped to other projects need a human reviewer.

## Critical behavior

- Installing or upgrading BStack must preserve existing project guidance and supported host bindings.
- A change must not make the same supported workflow silently behave differently across agent tools.

## Review focus

- Developer-facing skills need clear, concise usage docs and a simple path to the intended result.
- Check how a change affects Codex, Claude Code, Cursor, and Grok where those hosts are supported.
- Keep context loading scoped to what the task needs.

## Relevant standards

- `bstack/shared/references/pr-standards.md`: Shared BStack PR judgment.
