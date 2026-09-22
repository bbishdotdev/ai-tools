---
name: triage
description: Evaluate incoming bugs, enhancements, or proposed changes for duplication, accepted intent, evidence, and a usable implementation brief.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../../../ATTRIBUTION.md
---

# Triage

Triage intake, not every planned ticket. Read [workspace access](../../../shared/references/workspace.md), [work adapters](../../../shared/references/work-adapters.md), and [decision authority](../../../shared/references/decision-authority.md). Use the selected ticket provider; planning sources may live elsewhere. External PRs are intake only when the user or project includes them. Reading a PR does not authorize comments, edits, or merge.

## Inspect before creating work

Read the complete request, history, and existing triage notes. For an attached change, inspect the diff too. Search tickets, accepted decisions/ADRs, implementation by domain concept, prior rejections, active claims, and relevant local branches. Read available PR coverage when configured. Report unavailable coverage honestly; lack of tracker access is not proof that no work exists.

Separate these outcomes:

- Already implemented: point to the working behavior and evidence.
- Duplicate or overlapping work: link the existing ticket/change. Prefer an authorized scoped addition to that effort or a waiting follow-up after it lands. Preserve current ownership and avoid expanding a focused change without direction.
- Intentional behavior: surface the governing ADR or accepted decision. A deviation from your preference is not a bug.
- New defect or enhancement: verify the claim before refining the design. Reproduce a bug where possible; for a proposed diff, run relevant checks. Record confirmed, failed to reproduce, or insufficient detail with evidence.

Recommend a category and disposition with reasons. Human product/scope decisions remain with the user unless delegated. Trust an explicit disposition override within its authority; skip unnecessary grilling, while retaining actual evidence and required readiness checks. Use [grilling](../grilling/SKILL.md) and [domain modeling](../domain-modeling/SKILL.md) only for unresolved decisions.

## Record the outcome

Keep one `category:bug` or `category:enhancement` label and one `triage:` disposition on a triaged local ticket. Dispositions are `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`, or `deferred`. Preserve unrelated labels. Conflicting dispositions require resolving the intended state, not applying another label.

| Disposition | Local record |
| --- | --- |
| Needs triage | Backlog with the evidence gathered so far. |
| Needs info | Backlog with a wait that names the missing facts or decision. Preserve established answers in the body/progress. |
| Ready for agent or human | Write the [brief](AGENT-BRIEF.md), criteria, authority, and source links. Clear an obsolete wait explicitly. Move to Ready only when the backend permits it; otherwise report the blocker. For human work, say which judgment, access, or manual step is needed. |
| Wontfix or deferred | Preserve as Backlog with the disposition label and explicit wait/reason. Never use Done to mean rejected, duplicate, already built elsewhere, or postponed. See [rejection records](OUT-OF-SCOPE.md). |

Do not move another actor's active work, alter Done history, or take over a claim implicitly. A request to triage existing execution may require a recommendation or follow-up instead of changing its column. Claims, lifecycle transitions, and provider capabilities still apply.

For an attention list, show unclassified intake, needs-triage, and needs-info with new relevant evidence, oldest first. Without an activity feed, do not claim to detect reporter replies automatically. Resume from stored notes and ask only unresolved questions. Local actor/history records identify agent work; if authorized external comments are supported later, identify generated triage notes according to that project's policy.
