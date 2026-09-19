---
name: principle-redesign-from-first-principles
description: "Apply when integrating a new requirement into an existing design. Redesign as if the requirement had been a foundational assumption from day one, instead of bolting it on."
disable-model-invocation: true
---

> This packaged dependency follows [bstack's policy](../../../shared/skills/bstack-router/WORKFLOW.md). Read or reuse that policy before following these instructions. Resolve skill names through the [workflow index](../../../index.json). Use bundled workflows and replacements; do not fetch upstream latest. Resolve packaged paths relative to this document; use resolved helper paths from the consumer project.

# Redesign From First Principles

When integrating a change, don't bolt it onto the existing design. Redesign as if the requirement had been there from the start.

- Read all affected files and understand the current design
- Ask: "if we were writing this from scratch with this new requirement, what would we build?"
- Propagate the change through every reference: types, docs, examples, rationale sections
- Think about the whole redesign, then deliver it incrementally

This is the method for preserving option value when integrating changes into an existing design.
