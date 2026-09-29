---
name: domain-modeling
description: Sharpen domain terms and boundaries, maintain the glossary, and record consequential architectural decisions during design.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../../ATTRIBUTION.md
---

# Domain modeling

Use this when changing the model. Merely reading a glossary for vocabulary does not need this workflow. Read [decision authority](../../../shared/references/decision-authority.md) and the relevant existing `CONTEXT.md`, `CONTEXT-MAP.md`, and ADRs before proposing changes.

Challenge terms that conflict with the glossary. Separate overloaded concepts, propose a canonical name, and test boundaries with concrete edge cases. Check claims about current behavior against code. Use [how](../../../upstream/pstack/skills/how/SKILL.md) for nontrivial code facts; use [architect](../../../upstream/pstack/skills/architect/SKILL.md) through [bstack policy](../../../shared/skills/bstack-router/SKILL.md) when consequential alternatives need comparison. Do not rerun adequate grounding.

The user settles product meaning and ADR choices unless they delegated that scope. Describe code/document contradictions without silently choosing which is correct. Record agreed terms as they land using [the glossary format](CONTEXT-FORMAT.md). Keep the glossary free of implementation plans.

Use the shared [architecture decision process](../../../shared/references/architecture-decisions.md) for the rare choices that need an ADR. Most features produce none. Reuse an existing decision before proposing another; [the short format](ADR-FORMAT.md) preserves only the actual choice, reason, trade-off, and authority.

Follow the project's existing document locations. Keep useful glossary drafts in the owning private workspace's `artifacts/domain/` using [workspace access](../../../shared/references/workspace.md). ADR proposals can stay private; accepted ADRs default to a flat repository `docs/adr/` folder under the shared process. Create files lazily and preserve existing authoritative documents.
