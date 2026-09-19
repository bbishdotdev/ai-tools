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

[Matt's grilling](../upstream/matt-pocock/sdlc/skills/grilling/SKILL.md) already stops when no unresolved decision branches remain and the user confirms shared understanding. Keep that default. There is no approved replacement stopping heuristic or fixed question limit.

The adaptation is explicit delegation with two agents using different models. In an authorized autonomous run, an interviewer and a responding agent must work through the questions in a real exchange, using evidence and the user's constraints. Record their decisions and unresolved assumptions as agent judgments, never as a fabricated conversation with the user. Different models provide an opportunity for different perspectives; they do not prove independence or correctness.

Autonomous grilling needs configurable role-to-model bindings. Before an autonomous workflow starts, validate the bindings and availability required for its grilling sessions. If a required role is missing or cannot run, resolve that setup first rather than silently substituting self-interview. Ordinary human-guided grilling and basic/manual workflows do not require those bindings and must remain usable without them. Automatic router activation alone does not delegate product or ADR decisions.

The exact role names, model-difference requirement, disagreement procedure, and execution limits remain design choices. The user's model/provider examples do not select defaults. This is a requirement for the future adapter, not an implemented cross-model harness or a reason to block the current human interview.

[Wayfinder](../upstream/matt-pocock/sdlc/skills/wayfinder/SKILL.md) currently requires human participation for grilling and prototype tickets and limits most resolution to one ticket per session. Its charting flow also stops after creating the map. Those rules need an explicit bstack override for an authorized autonomous effort to progress across tickets and phases. They remain in the pinned original for comparison.

The agreed planning record types are open questions, decisions, domain terminology, and ADRs. Research evidence should be linked to the decisions it supports. Prototype choices follow the temporary lifecycle below; they do not automatically create a decision record or ADR. Storage and export behavior remain part of the local app design.

## Workflow connections

| Connection | Agreed direction or remaining choice |
| --- | --- |
| Grilling and domain modeling to engineering | Use PStack `how` for code facts and `architect` for consequential technical alternatives. Return evidence to the owning planning workflow. Product and ADR decisions retain the authority rule above. |
| Prototype work | Human review has selected disposable workspaces, existing application context for enhancements, standalone scratchpads for new concepts, five distinct options by default, respect for the existing visual system, interactive comparison, iterative refinement, focused verification, and selective code reuse. See the lifecycle below. |
| Spec and tickets to implementation | A proposed `/implement` entry accepts existing specs or tickets and routes into the appropriate bstack/PStack engineering workflow. It reuses prior decisions and evidence rather than starting a second implementation process. Matt's original `implement` is not currently imported or activated. |
| Engineering back to planning | New evidence can identify a specific unresolved decision. Return that question and its evidence without restarting the full interview. |
| Handoff | Shared between SDLC and engineering, and within each. Preserve the goal, scope, current owner and phase, decision authority, artifact references, completed checks, and next action. |
| Triage | Retain intake and coordination for incoming human or agent findings. Check accepted decisions, existing work, ownership, and related PRs before creating or advancing work. It is not a required Wayfinder stage. |

The intended experience is one agent carrying the work forward. Organizing, research, planning, prototyping, specs, tickets, and implementation can form a continuous flow, with entry at whichever stage the task needs. Users should not need to switch source packages or re-explain the work. Commands can be explicit entry points without becoming mandatory steps between phases.

The local app should expose the same work operations to agents and its human UI. Its integration must support both interactive decisions and fully delegated runs. The next review should define how an agent finds current work, resolves blockers, records evidence, and resumes without duplicating completed phases. This document does not select a CLI or MCP implementation yet.

## Triage handles intake and coordination

[Triage](../upstream/matt-pocock/sdlc/skills/triage/SKILL.md) evaluates incoming requests: checks whether work already exists or was rejected, verifies claims, asks for missing information, and assigns readiness states. It creates an implementation brief for work ready to proceed.

Wayfinder does not invoke triage. They share `grilling`, `domain-modeling`, and tracker setup. Wayfinder's next-ticket selection uses open, unblocked, unclaimed child decisions. That is work scheduling, not the triage workflow. [To-spec](../upstream/matt-pocock/sdlc/skills/to-spec/SKILL.md) explicitly marks its result ready for an agent without additional triage.

PStack's [Benny triage](../upstream/pstack/automations/benny/skills/triage-issue-reports/SKILL.md) is a configured Slack-report automation. Its [Bugbot triage reference](../upstream/pstack/skills/poteto-mode/references/bugbot-triage.md) classifies review comments. Neither is a direct replacement for general local backlog intake or Wayfinder scheduling.

Agreed direction: retain triage for incoming work, including findings from agents already executing another task. Reuse PStack's bounded investigation and reproduction capabilities where useful. Do not route Wayfinder into a bug-fix workflow merely to choose its next decision ticket.

The bstack adaptation must check existing tickets, active work and ownership, related branches, and open PRs where that capability exists. Local records must support this coordination without requiring an external tracker or Git host. Missing access is unknown coverage, not proof that no related work exists.

For an overlap, distinguish a contribution to the same intended outcome from separate follow-up work. Coordinate an in-scope enhancement with the current owner; record a separate change as blocked on its predecessor when it should build on that work after integration. Do not expand a PR indefinitely or edit another agent's work without coordination. Recheck dependencies when resuming deferred work.

Read relevant ADRs and accepted decisions before classifying intentional behavior as a defect. A deviation from an accepted decision, a proposal to change that decision, and a defect supported by new evidence are different findings. An ADR explains intent; it does not rule out a real defect. Product and ADR changes retain the agreed decision authority.

These are adaptation requirements, not guarantees supplied by the imported triage skill. Preventing concurrent agents from claiming the same work also needs coordination in the future local work store; a prompt that checks existing work before writing is insufficient by itself.

## Prototype comparison for the manual review

The pinned sources are [PStack's Prototype playbook](../upstream/pstack/skills/poteto-mode/playbooks/prototype.md), [Matt's prototype entry](../upstream/matt-pocock/dependencies/skills/prototype/SKILL.md), and its [logic](../upstream/matt-pocock/dependencies/skills/prototype/LOGIC.md) and [UI](../upstream/matt-pocock/dependencies/skills/prototype/UI.md) guides.

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

### Agreed prototype behavior

Use the existing application for an enhancement to an existing feature, in an isolated disposable checkout. Use a standalone scratchpad for a brand-new concept. Scratchpad describes the disposable workspace and its lifecycle; an application-based prototype can still use the real framework and components.

Prototype work should be quick and mostly throwaway. Its purpose is to illustrate a question, inspire alternatives, and help the user choose or combine ideas into a final design target. Use the application's brand, design system, colors, and existing components. A new concept inside an established product still follows that visual system, even in a standalone scratchpad. Establish a new visual direction when starting from scratch without an existing system or when the user explicitly requests that change. Useful pieces may carry into implementation through the normal engineering process; application-based prototypes may have more reusable code because they already use those components. Producing a prototype does not complete production implementation.

For option generation, default to five meaningfully different variants. Respect an explicit requested count. Distinguish the concepts through layout, composition, information hierarchy, or behavior while keeping the established visual system. Cosmetic theme changes alone do not satisfy the request for unique options.

Multiple variants require interactive comparison. A single prototype also needs interaction when the requested behavior is inherently interactive. Keep a static or measured experiment simple when interaction would not help answer its question.

Before presenting work, run every variant, exercise the relevant interactions, and capture screenshots or measured output. Focus verification on whether the prototype demonstrates its question correctly. Production testing belongs to implementation. Verification artifacts can remain temporary alongside the prototype.

Prototyping is an iterative loop. Requests for more options, refinements, or combinations produce revised prototypes for review. Combining elements from variants one, three, and five should produce the requested combined variant, not a new default batch of five or an automatic production implementation. A favorite or requested combination is not necessarily a final choice. Interpret casual wording such as "implement that" in the active prototyping context; do not treat that word alone as an instruction to leave the prototype phase.

An explicit final selection settles the design direction. Production implementation also needs to be within the user's requested scope, including earlier authorization that still applies. Do not require a special command or repeated permission when the user has already made the final choice and authorized that work. If the conversation leaves a material ambiguity between another preview and the production build, resolve that specific ambiguity.

Keep prototypes while their decision remains open, including when a prototyping session ends without selecting a direction. Once the user makes a final decision and the work moves to implementation, clean up the disposable workspace by default. Ensure the implementing agent can use the selected design and any reusable pieces before removing its working reference. A user request to save prototypes overrides cleanup so they remain available as references. Saved-reference storage is an implementation detail still to be chosen; no remote host is required.

Do not automatically create a prototype decision document, ADR, rationale, screenshot archive, or permanent verification report. The user can simply choose an option or combine parts without explaining why. Carry the selected target through the active workflow and let the implementation and any resulting design-system changes express it. Preserve additional reference material only when requested. This does not remove independently required ADRs for consequential architecture decisions elsewhere in the workflow.

## Name and next review

The package remains `bstack`. "Super engineer" is a working description of the intended experience, not an approved rename.

The prototype grilling has produced the agreed defaults above. The [approved prototype workflow](../engineering/prototype/WORKFLOW.md) expresses them as one shared workflow, with a [source and structure review](../engineering/prototype/REVIEW.md). The user approved the design. Runtime activation awaits the shared handoff and execution-session contract.

The decision-delegation adapter, cross-model grilling harness, prototype routing and execution verification, `/implement` entry, triage coordination, local work operations, and shared handoff format remain implementation work. No consumer routing or new workflow behavior is claimed by this record.
