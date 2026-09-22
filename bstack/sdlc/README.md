# SDLC

These are bstack-owned adaptations of the selected Matt Pocock skills. They use the local Wayfinder/spec/ticket store and bstack's shared authority, provider and handoff contracts. The pinned originals remain unchanged under `upstream/matt-pocock/` for comparison and selective updates.

| Entry | Purpose |
| --- | --- |
| [grilling](skills/grilling/SKILL.md) | Work through the unresolved branches of a plan. |
| [grill-me](skills/grill-me/SKILL.md) | Start a human-guided grilling session. |
| [grill-with-docs](skills/grill-with-docs/SKILL.md) | Grill while maintaining domain terms and consequential ADRs. |
| [domain-modeling](skills/domain-modeling/SKILL.md) | Clarify domain language and document decisions. |
| [wayfinder](skills/wayfinder/SKILL.md) | Organize and resolve planning questions across sessions. |
| [to-spec](skills/to-spec/SKILL.md) | Synthesize accepted context into an approved specification. |
| [to-tickets](skills/to-tickets/SKILL.md) | Slice agreed scope into linked implementation tickets. |
| [triage](skills/triage/SKILL.md) | Assess intake, prior decisions, duplication and active work. |
| [to-questionnaire](skills/to-questionnaire/SKILL.md) | Draft questions for another person. |

The common flow is Wayfinder → to-spec → to-tickets → implement. It is not a mandatory sequence. A clear small task can enter through a standalone ticket; sufficient specs can enter implementation directly. Triage handles incoming work, not every planned ticket.

[Research](../engineering/research/SKILL.md), [prototype](../engineering/prototype/SKILL.md) and [implement](../engineering/implement/SKILL.md) connect planning to engineering. [Handoff](../shared/skills/handoff/SKILL.md) transfers either phase to a fresh context without copying the entire conversation. Matt's setup dependency is replaced by bstack setup. His implement, TDD, code-review and ask-matt skills remain excluded.

## Work and authority

The [local app](../workspace/README.md) and agent CLI share maps, accepted answers, specs, tickets, typed dependencies, claims and revision checks. Private files hold research, handoffs, questionnaires and prototype references. Specs stay in the database rather than a second Markdown backlog.

[Planning and ticket adapters](../shared/references/work-adapters.md) are independent. Each defaults to local; external provider implementations are future work. A configured but unsupported provider fails clearly instead of silently delivering somewhere else.

Product and ADR decisions belong to the user unless explicitly delegated. Automatic skill routing does not grant decision authority. Autonomous grilling requires two configured models and verified execution capability before planning writes; manual sessions need neither role config nor an external service. [Decision authority](../shared/references/decision-authority.md) owns those rules.

## Source and release

All entries are explicit-only, with opt-in automatic routing through the bstack router. Consumer installation includes the owned skills, shared references, operations CLI and compiled browser app. Installed paths use `sdlc/<name>/`, without the source tree's `skills/` grouping.

[layers.json](../layers.json) records exact reviewed upstream bases. [Attribution](../../ATTRIBUTION.md) holds the credits, source map and notices; [upstream updates](../UPSTREAM.md) explains selective adoption. Design history remains in [integration review](integration-review.md) and [Wayfinder design](wayfinder-design.md). Current executable behavior is defined by the owned skills and [operations](../workspace/OPERATIONS.md).
