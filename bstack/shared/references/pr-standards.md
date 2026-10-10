# PR standards

Apply these standards when preparing a PR, reviewing it, or responding to feedback. The workflows differ; the judgment behind them should not.

## Purpose and scope

Confirm the problem or requirement exists, the claimed cause is sound, and the change earns its cost. Check current behavior, accepted decisions, and open work before adding a fix another PR already covers. Sometimes leaving the code alone is better. A PR description is a claim to verify, not proof.

A PR should have one purpose a reviewer can assess and a maintainer can revert as a unit. That purpose may affect many files, layers, or features. Size and blast radius alone are not reasons to split. Separate outcomes that solve independent problems and can land or revert independently. Keep connected changes together when splitting would break a migration or leave an unsafe intermediate state; explain that dependency.

Before opening a PR, split unrelated work when practical. If a materially mixed PR remains, call it out and leave it in draft for review. During review, raise one concise finding that names the distinct outcomes and the concrete review, release, or rollback cost. Block merge when that cost makes the PR unsafe as one unit; otherwise give a nonblocking warning. Do not repeat the same finding without changed scope or new reasoning.

## Evidence and decisions

Ground claims in the actual diff, affected behavior, applicable ADRs, and checks that ran. A proposed ADR edit is not accepted authority. Do not infer that tests passed from reading them, invent alternatives, or call a shared file proof of duplicate intent. Trace the root cause and affected callers before proposing a guard, test, or rewrite.

Weigh deadlines, prototype limits, and implementation cost against the real consequence. A justified noncritical trade-off can wait. Reachable critical failures, data loss, exposed private data, and applicable exploitable vulnerabilities cannot be waived by calling the change a POC or urgent.

Treat feedback and rebuttals as claims to check against code, contracts, and decision authority. Neither model agreement nor an author's insistence settles them. Change course when the evidence warrants it; push back when it does not. Keep comments short, specific, and useful. Skip cosmetic nits and theoretical risks without a credible path to harm.

## Engineering principles

Use the relevant PStack principles to assess the final diff. Read only the leaves that affect this change. They guide judgment for both PR creation and review; they do not require running another workflow.

| Change or concern | Relevant principles |
| --- | --- |
| Data model, ownership, or representation | [Foundational thinking](../../upstream/pstack/skills/principle-foundational-thinking/SKILL.md), [model the domain](../../upstream/pstack/skills/principle-model-the-domain/SKILL.md) |
| Extending existing behavior | [Redesign from first principles](../../upstream/pstack/skills/principle-redesign-from-first-principles/SKILL.md), balanced by the baseline's implementation trade-offs |
| Complexity, layers, or readability | [Laziness protocol](../../upstream/pstack/skills/principle-laziness-protocol/SKILL.md), [minimize reader load](../../upstream/pstack/skills/principle-minimize-reader-load/SKILL.md) |
| Defect, workaround, or disputed cause | [Fix root causes](../../upstream/pstack/skills/principle-fix-root-causes/SKILL.md), [attack the premise](../../upstream/pstack/skills/principle-attack-the-premise/SKILL.md) when proposed fixes share a failing premise |
| Shared state, retries, or partial updates | [Separate shared state](../../upstream/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md), [idempotent operations](../../upstream/pstack/skills/principle-make-operations-idempotent/SKILL.md) |
| Inputs, security, or contracts | [Boundary discipline](../../upstream/pstack/skills/principle-boundary-discipline/SKILL.md), [type discipline](../../upstream/pstack/skills/principle-type-system-discipline/SKILL.md) |
| Tests or verification claims | [Test behavior](../../upstream/pstack/skills/principle-test-behavior-not-implementation/SKILL.md), [prove it works](../../upstream/pstack/skills/principle-prove-it-works/SKILL.md) |
| User-facing behavior | [Experience first](../../upstream/pstack/skills/principle-experience-first/SKILL.md) |

File length, a missing abstraction, a preferred alternative, or absent new tests do not establish a defect. Existing behavioral coverage can be enough. Raise architectural concerns only when they have a concrete consequence and a worthwhile trade-off; leave unrelated cleanup out of this PR.
