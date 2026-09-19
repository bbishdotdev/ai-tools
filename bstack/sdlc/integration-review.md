# SDLC integration review

This records the user's direction from September 19, 2026, and the remaining integration choices. It is a design record, not an active router policy or a new skill implementation. The imported files and consumer release remain unchanged.

## Verified upstream baseline

`git ls-remote https://github.com/mattpocock/skills.git HEAD` returned `c55ee46073ed923f86ce59a5eb3b6d895095d1b7` during this review. All three Matt Pocock imports use that revision. Source integrity checks pass, and all three compare unchanged against its clean checkout. No upstream refresh was necessary.

## Agreed decision ownership

Product decisions and ADR decisions belong to the user by default. The agent can investigate facts, recommend an answer, and draft an ADR. An explicit request to decide autonomously delegates those decisions within the scope of that request.

Delegation must survive stage changes, subagents, and session handoffs. The receiving agent must know which decisions the user retained and which it may make. An agent-made decision must be recorded as delegated judgment, not represented as a human answer or approval.

Decision authority and execution scope are separate. Autonomous planning can resolve decisions without authorizing implementation. A request to carry an effort through implementation can cover the whole workflow. Existing authorization carries forward within its scope without repeated setup or confirmation.

The existing opt-in automatic router setting controls workflow activation. It is separate from permission to make product or ADR decisions autonomously.

## Grilling stays grounded in the current skill

[Matt's grilling](matt-pocock/skills/grilling/SKILL.md) already stops when no unresolved decision branches remain and the user confirms shared understanding. Keep that default. There is no approved replacement stopping heuristic or fixed question limit.

The adaptation is explicit delegation. In an authorized autonomous run, the agent must work through the same questions using evidence and the user's constraints, recording its choices and unresolved assumptions. It must not fabricate a conversation with the user. The details of this adaptation still need to be implemented and verified.

[Wayfinder](matt-pocock/skills/wayfinder/SKILL.md) currently requires human participation for grilling and prototype tickets and limits most resolution to one ticket per session. Its charting flow also stops after creating the map. Those rules need an explicit bstack override for an authorized autonomous effort to progress across tickets and phases. They remain in the pinned original for comparison.

The agreed record types are open questions, decisions, domain terminology, and ADRs. Research and prototype evidence should be linked to the decisions they support. Storage and export behavior remain part of the local app design.

## Workflow connections

| Connection | Agreed direction or remaining choice |
| --- | --- |
| Grilling and domain modeling to engineering | Use PStack `how` for code facts and `architect` for consequential technical alternatives. Return evidence to the owning planning workflow. Product and ADR decisions retain the authority rule above. |
| Prototype work | Explicit manual comparison before combining the two implementations. PStack execution and verification with Matt's detailed instructions is a candidate, not a settled design. |
| Spec and tickets to implementation | A proposed `/implement` entry accepts existing specs or tickets and routes into the appropriate bstack/PStack engineering workflow. It reuses prior decisions and evidence rather than starting a second implementation process. Matt's original `implement` is not currently imported or activated. |
| Engineering back to planning | New evidence can identify a specific unresolved decision. Return that question and its evidence without restarting the full interview. |
| Handoff | Shared between SDLC and engineering, and within each. Preserve the goal, scope, current owner and phase, decision authority, artifact references, completed checks, and next action. |
| Triage | Still under review. It is not a required Wayfinder stage. |

The intended experience is one agent carrying the work forward. Organizing, research, planning, prototyping, specs, tickets, and implementation can form a continuous flow, with entry at whichever stage the task needs. Users should not need to switch source packages or re-explain the work. Commands can be explicit entry points without becoming mandatory steps between phases.

The local app should expose the same work operations to agents and its human UI. Its integration must support both interactive decisions and fully delegated runs. The next review should define how an agent finds current work, resolves blockers, records evidence, and resumes without duplicating completed phases. This document does not select a CLI or MCP implementation yet.

## Triage is optional intake

[Triage](matt-pocock/skills/triage/SKILL.md) evaluates incoming requests: checks whether work already exists or was rejected, verifies claims, asks for missing information, and assigns readiness states. It creates an implementation brief for work ready to proceed.

Wayfinder does not invoke triage. They share `grilling`, `domain-modeling`, and tracker setup. Wayfinder's next-ticket selection uses open, unblocked, unclaimed child decisions. That is work scheduling, not the triage workflow. [To-spec](matt-pocock/skills/to-spec/SKILL.md) explicitly marks its result ready for an agent without additional triage.

PStack's [Benny triage](../engineering/automations/benny/skills/triage-issue-reports/SKILL.md) is a configured Slack-report automation. Its [Bugbot triage reference](../engineering/skills/poteto-mode/references/bugbot-triage.md) classifies review comments. Neither is a direct replacement for general local backlog intake or Wayfinder scheduling.

Recommendation pending review: retain triage for optional incoming work, outside the normal planned-work path. Reuse PStack's bounded investigation and reproduction capabilities where useful. Do not route Wayfinder into a bug-fix workflow merely to choose its next decision ticket.

## Prototype comparison for the manual review

The pinned sources are [PStack's Prototype playbook](../engineering/skills/poteto-mode/playbooks/prototype.md), [Matt's prototype entry](../shared/dependencies/matt-pocock/skills/prototype/SKILL.md), and its [logic](../shared/dependencies/matt-pocock/skills/prototype/LOGIC.md) and [UI](../shared/dependencies/matt-pocock/skills/prototype/UI.md) guides.

| Topic | PStack | Matt Pocock |
| --- | --- | --- |
| Purpose | Cheap experiment to settle a design or observable behavior question. | Concrete artifact to answer a logic, state, or UI design question. |
| Location | Isolated scratch directory, separate from production source. | Near the relevant code; UI variants preferably run in the existing page. |
| Tools | Light HTML, CSS, JavaScript, or a small behavior script; no production framework. | Standalone HTML for logic; existing framework and components for UI. |
| Variations | Labeled alternatives behind one switcher. | Usually three structurally distinct UI variants, URL selection, and a floating switcher. |
| Logic exploration | Smallest experiment that answers the question. | Pure logic module, visible state, free-play controls, and guided scenarios. |
| Verification | Agent drives the matching surface and captures screenshots or observed output. | Detailed interactive artifact for review; explicit agent-driven verification is less prescribed. |
| Artifact retention | Return the evidence, decision, and scratch path. | Preserve the prototype on a separate branch with links from the work item. |
| Production handoff | Separate Feature or architect workflow handles the real build. | Reuse validated decisions or logic, discard prototype UI machinery, and rewrite production code appropriately. |

The manual review needs to settle prototype placement, artifact retention, and the boundary between reusable logic and production implementation. These differences require decisions; concatenating both instruction sets would leave conflicting defaults.

## Name and next review

The package remains `bstack`. "Super engineer" is a working description of the intended experience, not an approved rename.

The next explicit review is the prototype comparison above. The decision-delegation adapter, `/implement` entry, optional triage role, local work operations, and shared handoff format remain implementation work. No consumer routing or new workflow behavior is claimed by this record.
