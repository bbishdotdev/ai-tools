# Review standard

Apply the [baseline](../../../shared/references/baseline-agents.md), [architecture decision policy](../../../shared/references/architecture-decisions.md), shared [PR standards](../../../shared/references/pr-standards.md), and [unslop](../../../shared/skills/unslop/SKILL.md). Read applicable current project decisions from the pinned target tree, alongside the base/head snapshots. Missing ADRs do not require creating one.

Find the project's documented decision location, including application-wide decisions. If read-only model tools cannot run the trusted ADR catalog helper, inspect that location directly. An empty default `docs/adr/` directory does not establish that the project has no decisions elsewhere.

A rebuttal can warrant a focused reassessment without a code change. Verify the speaker's authority for product or architecture decisions. Human dismissal of a review changes GitHub's merge process, not the technical evidence; never dismiss another review yourself. A confirmed unnecessary change can be a blocker when its cost or harm warrants withholding merge. A disputed requirement is a human decision only when it materially affects whether the PR should merge.

Read the relevant principle leaves from the shared PR standards. Do not launch their implementation playbooks or delegate more agents. Review PR-introduced or PR-exposed issues only.

## Evidence and categories

A finding names a reachable trigger or material structural cost, the consequence, and precise source evidence. Trace callers and existing validation before claiming a path can fail. State the root problem instead of prescribing a guard, retry, fallback, or extra test as a substitute for fixing it. A test result is observed only when supplied or actually obtained; reading test code is not running it.

- `blocker`: substantiated issue requiring action before merge. Explain why it cannot safely wait.
- `human-decision`: a consequential product or architectural choice that needs the authorized human before merge. Explain the unresolved choice and its trade-off; do not fabricate approval.
- `moderate`: substantiated, useful improvement that can safely follow later.
- `low`: small but concrete benefit worth the author's attention. Omit cosmetic nits and theoretical risks.

An unresolved material coverage gap makes the review incomplete. It is not evidence of a bug, and does not erase valid findings elsewhere. Explain why uninspected content matters; a changed binary file alone does not establish a material gap. A failed mapped archive verification remains an unresolved integrity gap. Read-only review does not require rerunning tests. A missing live check makes coverage incomplete only when you can name the consequential behavior you cannot assess from the available code and evidence. No findings is valid; do not fill empty categories.

Write for a busy developer. Usually two short sentences per finding: what can happen and why it matters, then the useful next step. Link evidence instead of narrating the runner or repeating the same point in the title, explanation and action. Use plain language without softening real blockers to meet a length target.
