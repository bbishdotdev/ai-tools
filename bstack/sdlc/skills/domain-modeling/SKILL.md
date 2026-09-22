---
name: domain-modeling
description: Sharpen domain terms and boundaries, maintain the glossary, and record consequential architectural decisions during design.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../../../ATTRIBUTION.md
---

# Domain modeling

Use this when changing the model. Merely reading a glossary for vocabulary does not need this workflow. Read [decision authority](../../../shared/references/decision-authority.md) and the relevant existing `CONTEXT.md`, `CONTEXT-MAP.md`, and ADRs before proposing changes.

Challenge terms that conflict with the glossary. Separate overloaded concepts, propose a canonical name, and test boundaries with concrete edge cases. Check claims about current behavior against code. Use [how](../../../upstream/pstack/skills/how/SKILL.md) for nontrivial code facts; use [architect](../../../upstream/pstack/skills/architect/SKILL.md) through [bstack policy](../../../shared/skills/bstack-router/SKILL.md) when consequential alternatives need comparison. Do not rerun adequate grounding.

The user settles product meaning and ADR choices unless they delegated that scope. Describe code/document contradictions without silently choosing which is correct. Record agreed terms as they land using [the glossary format](CONTEXT-FORMAT.md). Keep the glossary free of implementation plans.

Offer an ADR only when the decision is costly to reverse, surprising without context, and the result of a real trade-off. All three must hold. Use [the ADR format](ADR-FORMAT.md); a prototype preference alone does not need an ADR. Preserve the authority and reasons actually given, without inventing a rationale.

Follow the project's existing document locations. If none exists, discover the owner root using [workspace access](../../../shared/references/workspace.md) and keep new drafts in `artifacts/domain/` or `artifacts/adr/` beneath its private workspace directory. Create files lazily. Promote accepted records to repository docs only when requested or established project conventions require it; do not move existing authoritative docs.
