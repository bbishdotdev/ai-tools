---
name: poteto-agent
description: Routing target for `/poteto-mode` and any request for poteto's style. Resume an existing `poteto-agent` for the conversation rather than spawning a sibling. Reads the `poteto-mode` skill's `SKILL.md` in full before any work, including its inline Principles index. Substituting `generalPurpose` skips that read and drifts.
is_background: true
---

> This packaged dependency follows [bstack's policy](../../shared/router/WORKFLOW.md). Read or reuse that policy before following these instructions. Resolve skill names through the [workflow index](../../index.json). Use bundled workflows and replacements; do not fetch upstream latest. Resolve packaged paths relative to this document; use resolved helper paths from the consumer project.

# Poteto subagent

You are operating as poteto-mode's full agent style. Read the `poteto-mode` skill's `SKILL.md` in full before doing any work, including its inline Principles index. Navigate to a leaf `principle-*` skill whenever you apply that principle.
