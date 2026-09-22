---
name: to-spec
description: Synthesize accepted conversation and planning decisions into a versioned specification without restarting the interview.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../../../ATTRIBUTION.md
---

# To spec

Synthesize what is already known. Do not restart the design interview. Read [workspace access](../../../shared/references/workspace.md), [work adapters](../../../shared/references/work-adapters.md), and [decision authority](../../../shared/references/decision-authority.md). Specs belong to the planning adapter; tickets can use a different provider later.

Read the referenced decisions and relevant glossary/ADRs. Reuse adequate code grounding. Identify the highest existing behavioral test seam that can verify the feature, preferring fewer seams. Confirm a new material testing choice with the decision owner unless it is already agreed or delegated. Missing product decisions remain explicit open points in a draft; do not invent them to obtain approval.

Write the spec with:

- The user's problem and proposed outcome.
- User stories covering the accepted behaviors and meaningful edge cases, without padding the list.
- Settled implementation decisions and contracts.
- Testing decisions, behavioral acceptance, and relevant test precedents.
- Scope exclusions and remaining notes or unresolved decisions.

Use domain concepts and interfaces instead of brittle file paths or line numbers. A small prototype state machine, schema, or type can stay inline when it expresses an accepted decision better than prose. Trim demo controls and link the runnable reference separately.

Store the authoritative Markdown with `spec.create` or `spec.update`, linking the exact planning questions and artifact references. Use the existing record when revising a spec. Do not create a parallel Markdown source of truth; export only when requested.

For acceptance, acquire the spec claim and read each declared question's current accepted answer. Use the [shared request helper](../../../shared/references/workspace-requests.md) to call `spec.approve` with the spec and question receipts as bases and actual decision authority as input. Code derives the exact `questionSources`; do not recreate that logic. Use prior explicit approval when it covers this body; otherwise present the draft for approval. A settled subset is sufficient and does not require finishing the whole map. Missing answers or stale sources keep the spec unapproved.

Return the spec reference and whether it is draft or approved. Approval preserves an immutable revision and may feed [to-tickets](../to-tickets/SKILL.md); it is not permission to implement.
