---
name: no-comments
description: Review scoped code comments and replace them with clearer code or an ADR candidate when they carry a fundamental decision. Use before review or when comments obscure the implementation.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# No comments

Inspect the caller's files or diff. If no scope is given, use the current change. Do not expand into unrelated code.

Find code comments, commented-out code, and suppressions in that scope. Remove narration and dead code. Where a comment explains behavior, improve names, data shape, or function boundaries until the code is clear without it. Investigate a suppression before removing it; fix the underlying cause and keep type and lint checks valid. Do not delete required license or generated-file notices as a style cleanup.

If a comment records a fundamental architecture choice that the code cannot express, consult the [architecture decision process](../../shared/references/architecture-decisions.md). Most explanations do not meet the ADR threshold. Do not create an ADR just to move a comment somewhere else.

Use a fresh delegate for an independent pass only when the host supports one and the scope warrants it. Pass this skill and the exact files to the delegate; no named Cursor agent or model is required. Review its findings against the code before editing. Do not claim independent review if none ran.

Run the relevant check after changes. Report what was removed or clarified and any comment or suppression that remains for a specific reason. Do not widen the task merely because a comment hints at another problem.
