---
name: implement
description: Execute authorized work from a sufficient ticket or specification through bstack’s existing PStack engineering workflow.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# Implement

This entry connects accepted planning to [bstack's engineering router](../../shared/router/WORKFLOW.md). It does not introduce a second implementation process. Read [workspace access](../../shared/references/workspace.md), [work adapters](../../shared/references/work-adapters.md), and [decision authority](../../shared/references/decision-authority.md).

Confirm implementation is within the user's existing scope. Spec approval, a Ready label, or completion of Wayfinder is not execution permission. Read the selected ticket/spec and current accepted sources, relevant ADRs, active ownership and prerequisites. A sufficient direct request can proceed without manufacturing a map or spec. Reuse settled decisions and adequate grounding; reopen only questions made uncertain by current evidence.

If arriving from prototype or a substantial planning phase that needs a clean context, use [handoff](../../shared/handoff/SKILL.md) before starting execution. Carry the current scope, selected reference, governing instructions, and configured role. The fresh receiver rereads records and acquires ownership itself. Missing role settings do not block ordinary manual implementation; use the host's normal inherited model unless a supported role is configured or requested.

Use the [shared request helper](../../shared/references/workspace-requests.md) for local reads, claims, updates, and transitions. Query Ready work when no ticket was named. Within an already authorized implementation set, also recheck its Backlog successors after predecessors finish: satisfied dependencies do not move their column automatically. Do not promote unrelated or deferred intake. Revalidate authority, content, sources, blockers and waits, then acquire the selected ticket's claim.

Follow its actual column. Eligible Backlog moves to Ready before In progress; Ready moves to In progress; an In-progress ticket resumes without repeating the transition. Review remains in review unless an authorized correction returns it to In progress with a reason. Done is complete unless explicitly reopened through Backlog with a reason. Use the revision returned by each mutation. A maintenance claim on stale or blocked work cannot bypass readiness. Source review requires reconciling changed decisions and explicit acknowledgement against current identities; do not clear it just to pass a gate. Preserve other actors' claims and scoped work.

When PR delivery is in scope and a before/after would help review, capture the relevant UI, output, or measurement before changing it. Preserve enough context for an honest comparison.

Follow the router's matching PStack engineering playbook and its implementation/review separation. Reuse established grounding. Use the accepted prototype as a reference; subject carried-over code to normal review and testing. Record meaningful progress and evidence, renewing a live claim for longer work. Re-read and reconcile if a write conflicts or the claim is revoked.

Move completed implementation to Review with actual validation evidence. That releases the implementation claim; a reviewing phase acquires its own. Move to Done only after the applicable review and acceptance requirements pass, with nonempty completion evidence and references. A stored completion note is not proof the checks ran. Failures, waits, or stale sources preserve unfinished work and its next action.

Deliver at the authorized destination. For PR delivery, use the owned [to-pr workflow](../to-pr/SKILL.md) with its final overlap review. Do not infer publishing a PR, merging, or deploying from implementation permission. If work stops or changes context, release ownership appropriately and leave a [handoff](../../shared/handoff/SKILL.md) with current revisions and evidence.
