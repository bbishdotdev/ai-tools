---
name: to-tickets
description: Turn approved scope into verifiable vertical implementation slices with source references and real blocking relationships.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../../../ATTRIBUTION.md
---

# To tickets

Read [workspace access](../../../shared/references/workspace.md), [work adapters](../../../shared/references/work-adapters.md), and [decision authority](../../../shared/references/decision-authority.md). Resolve planning and ticket providers independently. Read the referenced spec revision, accepted questions, or conversation scope; a small known change does not require a map or spec.

Use the project's glossary and relevant ADRs. Reuse code grounding and look for a small prefactor that makes the change easier. Break the work into narrow end-to-end slices: each delivers behavior through the needed layers, can be demonstrated or verified, and fits a fresh context. Dependencies express actual prerequisites, not a preferred narrative order.

For a wide mechanical refactor that cannot land as vertical slices, use expand, migrate in bounded batches, then contract. Keep batches independently green where possible. If that is impossible, explicitly name the shared integration branch and final integrate-and-verify ticket instead of promising each batch is independently releasable.

Present titles, delivered behavior, and blocking edges for the proposed breakdown. Ask about granularity, merges, and actual prerequisites only when the breakdown needs a decision. Reuse an already approved breakdown or scoped delegation; do not repeat approval theater.

Create each ticket in Backlog with its body, testable `acceptanceCriteria`, scope boundaries, authority, and references. Link its approved `specId` and relevant `questionIds` when present. Local storage snapshots their accepted identities. Use exact provider-qualified source identities and versions across adapters; a remote ID is not a local database ID. Current unsupported external providers must be reported before writing there.

Create all tickets first, then use the [shared request helper](../../../shared/references/workspace-requests.md) for `ticket.relationship.add` with current endpoint receipts as bases. Code supplies their revisions. Parent and related links do not create blockers. Do not close the source question, parent ticket, or map as a side effect. Reuse existing matching work instead of duplicating it on retries.

Move eligible tickets to Ready with the normal claim and transition operations. Blocked successors remain Backlog until their predecessors satisfy their dependencies; do not bypass the core's readiness checks or relabel them to imply readiness. No extra triage is required for an approved breakdown. Creation and Ready state do not start implementation.

Keep descriptions behavioral. Avoid brittle paths and snippets except small accepted prototype logic that carries a decision. Return created/reused ticket references and dependency order. [Implement](../../../engineering/implement/SKILL.md) consumes the selected ready ticket when execution is authorized.
