---
name: deslop
description: Remove AI-generated code slop and clean up code style
---

> This packaged dependency follows [bstack's policy](../../../shared/skills/bstack-router/WORKFLOW.md). Read or reuse that policy before following these instructions. Resolve skill names through the [workflow index](../../../index.json). Use bundled workflows and replacements; do not fetch upstream latest. Resolve packaged paths relative to this document; use resolved helper paths from the consumer project.

# Remove AI code slop

Check the diff against main and remove AI-generated slop introduced in the branch.

## Focus Areas

- Extra comments that are unnecessary or inconsistent with local style
- Defensive checks or try/catch blocks that are abnormal for trusted code paths
- Casts to `any` used only to bypass type issues
- Deeply nested code that should be simplified with early returns
- Other patterns inconsistent with the file and surrounding codebase

## Guardrails

- Keep behavior unchanged unless fixing a clear bug.
- Prefer minimal, focused edits over broad rewrites.
- Keep the final summary concise (1-3 sentences).
