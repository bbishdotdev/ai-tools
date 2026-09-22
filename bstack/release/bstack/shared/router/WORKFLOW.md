---
name: bstack-router
description: Route engineering work through bstack's pinned PStack workflows with portable capabilities, scoped execution, and visible evidence. Use for bstack engineering tasks or when the repository's standing instructions load this router.
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# bstack router

This is bstack's policy layer over [PStack's router](../../engineering/poteto-mode/WORKFLOW.md). Keep the imported files unchanged. Apply this policy to every imported playbook, skill, agent, reference, and helper they select. User scope and host instructions take precedence; this layer resolves differences with the imported defaults.

## Select and continue

When the user explicitly invokes a named skill such as `how` or `architect`, apply this policy and follow that skill within the requested scope. Load only its needed dependencies. Do not also load the upstream router or select a playbook unless that skill calls for it or the user requests Poteto Mode.

For Poteto Mode or automatic engineering routing, read the upstream router in full, then the selected playbook and relevant skill leaves. Preserve its principles and workflow steps except for the adjustments below. Reuse full instructions while they remain available. After compaction, reread any missing instructions; retain the active workflow, completed work, and next step instead of restarting.

- Use a matching playbook for ordinary engineering tasks. A reported defect routes to Bug fix, measured slowness to Perf issue, and a cited read-only explanation to Investigation. New behavior routes to Feature.
- Use **figure-it-out** for engineering work needing a bespoke execution plan, including large or cross-cutting work whose coordination exceeds a narrower playbook. A one-time migration can need it. Repetition and creation of a reusable skill are not prerequisites. A standing multi-day coordinated program can instead need Orchestrate, as defined upstream.
- Ordinary writing, casual conversation, and other requests with no engineering workflow need a normal response. Select no engineering playbook. Apply [bstack's unslop](../unslop/SKILL.md) to prose without loading the upstream engineering corpus.
- Respect explicit skill requests and the requested deliverable. Planning, discussing, classifying, or verifying a route does not authorize executing the described work. A plan-only figure-it-out request stops at the plan.
- Within that scope, honor the selected playbook's explicit exceptions and skip conditions before generic defaults. Investigation stays read-only; it does not inherit a mandatory PR or prototype step.

## Planning and phase changes

Use bstack's owned entries for selected SDLC workflows, including references from imported instructions. Read only the selected entry and the dependencies it needs:

| Task | Entry |
| --- | --- |
| Explore a plan through questions | [grilling](../../sdlc/grilling/SKILL.md), [grill-me](../../sdlc/grill-me/SKILL.md), or [grill-with-docs](../../sdlc/grill-with-docs/SKILL.md) |
| Establish terminology or an ADR | [domain-modeling](../../sdlc/domain-modeling/SKILL.md) |
| Organize unresolved decisions across sessions | [wayfinder](../../sdlc/wayfinder/SKILL.md) |
| Synthesize accepted scope or slice implementation work | [to-spec](../../sdlc/to-spec/SKILL.md), then [to-tickets](../../sdlc/to-tickets/SKILL.md) when needed |
| Assess incoming work and overlap | [triage](../../sdlc/triage/SKILL.md) |
| Draft questions for another person | [to-questionnaire](../../sdlc/to-questionnaire/SKILL.md) |
| Research, prototype, or implement | [research](../../engineering/research/SKILL.md), [prototype](../../engineering/prototype/SKILL.md), [implement](../../engineering/implement/SKILL.md) |
| Prepare or publish an authorized PR | [to-pr](../../engineering/to-pr/SKILL.md) |
| Transfer work to a fresh context | [handoff](../handoff/SKILL.md) |

Named invocation selects that entry. Within opted-in automatic routing, propose or select the matching phase from the user's task. A sufficient spec or small known task can skip Wayfinder. Planning completion does not authorize implementation. Triage is intake coordination, not a mandatory step between planning and tickets.

Read [decision authority](../references/decision-authority.md) when deciding who can settle product choices, ADRs, or autonomous grilling. Human decisions remain the default; automatic routing and autonomous decision authority are separate. Use [workspace access](../references/workspace.md) for saved work and [independent work adapters](../references/work-adapters.md) for planning and ticket destinations. Local operation requires no external tracker or model-role setup.

Resolve imported Opening a PR instructions to the owned [to-pr entry](../../engineering/to-pr/SKILL.md), including transitive calls from other playbooks. Use its final overlap check and draft policy instead of upstream's unconditional ready-PR instruction. Resolve imported prototype instructions to the owned prototype entry, Matt's selected SDLC/research/handoff names to the entries above, and Matt's setup dependency to bstack setup. Preserve the approved prototype review loop. At the prototype-to-implementation boundary, write the shared handoff and start a fresh context through a supported host capability. Carry accepted decisions and evidence forward instead of repeating the interview or grounding automatically.

## Grounding and design

Retain **how** for nontrivial changes, architecture decisions, and uncertainty about how the system works. Reuse adequate grounding already established for the same code and question. Refresh when evidence, scope, or assumptions change. Architect should consume that grounding rather than automatically running the same exploration twice.

Use **architect** when consequential design uncertainty or risk warrants competing approaches: unclear ownership or interfaces, shared state and concurrency, competing data models, or changes with broad or costly consequences. Merely crossing a function boundary is not a trigger. A routine change following a known pattern with unchanged contracts can skip architecture with a brief reason.

Keep PStack's implementation and review separation, delegated steps, adversarial review, and relevant principle leaves. Adapt their tools through the capability contract below; this layer does not quietly turn mandatory independent review into self-review.

## Capabilities and authorization

The default delegation model policy is **inherit-parent**, including the coding delegate. Omit an explicit model unless a supported role override is configured or the user requests one. Imported provider names, model identifiers, agent types, transcript paths, and external destinations are examples of upstream bindings, not requirements or authorization.

Before an imported instruction needs delegation, a service, a host-specific tool, or a helper script, read [the capability contract](references/capabilities.md). Resolve the operation against capabilities actually available in this environment. Pass this router's path and relevant policy to delegates. They must apply bstack's layer before following imported instructions.

Proceed with authorized work without repeated permission requests. Earlier authorization persists for the same action and destination. Availability of an integration alone grants no permission to send messages, publish, deploy, or change external state. Follow host requirements and clarify only a material unresolved boundary.

Deliver at the user's requested or configured destination. Local changes, a patch, a work item, or a draft PR can each be valid outcomes. Run Opening a PR only when PR delivery is in scope and supported; no default requirement to publish a ready GitHub PR. A broken imported skill is a maintainer issue to record and address within scope, not an automatic extra PR in a consumer's task.

## Visible execution and evidence

For substantive engineering work, give a compact initial note naming the chosen workflow and relevant skills. Maintain the workflow's steps and meaningful skips in the available plan facility or a short local checklist. Do not copy every upstream step verbatim into each reply. Report a route change or consequential skip when it happens. End with what actually ran, the resulting artifact, checks performed, and material limits. Ordinary prose does not need a workflow preamble.

Use these distinctions when reporting execution:

- **Reported:** an agent says it selected or ran something.
- **Observed:** a trace or artifact shows a read, tool call, change, or reviewer response.
- **Checked:** evidence was compared against the task's acceptance criteria.

A skill name in chat, a file read, or a checked box is not proof of correct execution. Keep the deeper **show-me-your-work** audit for its upstream triggers and preserve Eval's examination of actual behavior. Match claims to real traces, artifacts, independent review outputs, and verification results. If the required transcript or independent model family is unavailable, state the missing evidence and narrower check performed. Do not label a self-review as an independent audit.

Always resolve imported **unslop** references to [bstack's customized skill](../unslop/SKILL.md), including explicit paths in upstream instructions. [The layer registry](../../layers.json) records this replacement and the policy's upstream review dependencies. Other imported skills remain on demand. The reminder hook carries this entry's path, not its body; it cannot itself prove that these instructions were followed.
