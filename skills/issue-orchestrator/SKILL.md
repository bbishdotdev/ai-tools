---
name: issue-orchestrator
description: Use when an AI coding agent needs to pull, triage, sequence, execute, verify, commit, and prepare PRs for a batch of GitHub issues. Triggers include requests to work through a milestone, assigned issues, TODO/project-status issues, explicit issue lists, labels, or other subsets; decide dependency order, parallelizable work, delegated-agent handoffs, git worktree strategy, acceptance-criteria validation, runbook/manual verification, commits, and PR readiness.
---

# Issue Orchestrator

Use this skill to turn a set of GitHub issues into an execution plan, then drive the work through implementation, verification, commits, and PR preparation.

This skill is for doing the work, not merely drafting issues. If the user is creating/refining issue text, use `github-issue` instead.

## Core Principles

- Challenge the issue set. Call out weak AC, hidden dependencies, missing tests, and scope that should be split or merged.
- Do not start from assumptions. Fetch current issues, comments, labels, milestone/project metadata, and relevant code/docs.
- Keep context bounded. Default to delegated agents for bounded exploration, dependency diagnosis, implementation slices, and verification passes when delegation is available and permitted.
- Delegation is useful for sequential handoffs too: a worker can explore or execute a focused task, then report only the relevant findings, changed files, tests, and risks back to the orchestrator.
- Prefer one issue per PR, but optimize for coherent review units over rigid bookkeeping.
- Commit only coherent, verified slices. Do not create noisy commits for half-working AC fragments.
- Never mark an AC as verified unless there is direct evidence: test output, code inspection, browser verification, runbook result, or explicit user confirmation.

## Issue Selection

Resolve the user’s selector before planning:

- Explicit issue numbers: fetch exactly those issues.
- Milestone: fetch all open issues in that milestone.
- Assignment: fetch issues assigned to the target user, usually the authenticated GitHub user unless specified.
- Project/status such as TODO: fetch via available GitHub/project tooling; if project status is unavailable, explain the gap and use labels/milestones/issues as a fallback.
- Label or query: fetch matching open issues.

If the selector is ambiguous and the wrong set would cause real work on the wrong issues, ask one concise clarification. Otherwise make the most conservative reasonable assumption and state it.

## Planning Workflow

1. **Inventory**
   - Fetch issue title, body, AC, test plan, labels, milestone/project state, assignees, comments, linked PRs, and URLs.
   - Inspect repo status and avoid overwriting user changes.
   - Read relevant docs and search code with `rg`.

2. **Build the dependency graph**
   - Identify foundational schema/contracts/scaffolding.
   - Identify issues blocked by missing APIs, shared types, migrations, or UX surfaces.
   - Identify independent slices with disjoint write scopes.
   - Identify AC that depend on manual/browser/runbook validation.

3. **Create the execution plan**
   - Order serial blockers first.
   - Group parallel work only after shared contracts are stable enough.
   - Name expected write scopes and verification gates for each issue.
   - State where delegated agents will be used for both parallel work and sequential context-bounded handoffs.
   - Keep work local only when the next step is tiny, urgent, tightly coupled, or blocked on immediate orchestrator judgment.

4. **Decide worktree strategy**
   - Use git worktrees for parallel implementation when issues should have separate branches/commits or may otherwise collide in one working tree.
   - Keep work serial in the main worktree for foundational/shared-contract changes where parallelism would create merge churn.
   - Prefer branch names like `codex/issue-123-short-topic`.
   - Before creating worktrees, check current branch/status and avoid dirty-worktree surprises.

## Delegated Agent Strategy

Use worker agents, subagents, or equivalent delegation aggressively when available and permitted by the active instructions. Do not reserve delegation only for parallel implementation; also use it to conserve context during sequential work.

Default delegated handoffs:

- Focused codebase exploration before planning or implementation.
- Dependency/install/test failure diagnosis with concrete logs and suspected root cause.
- Independent issue implementation with a clear write scope.
- Verification pass for a completed issue or PR.
- Runbook/browser smoke on an already-running app.

Keep the task local when it is a tiny lookup, the immediate next step depends on nuanced orchestrator judgment, or delegation would add more coordination cost than context savings.

Good delegated tasks:

- Independent issue implementation with a clear write scope.
- Codebase exploration for a specific question.
- Dependency failure investigation with exact commands/errors.
- Verification pass for a completed issue or PR.
- Runbook/browser smoke on an already-running app.

Poor delegated tasks:

- Immediate blocker needed for the next local step.
- Vague “figure everything out” requests.
- Multiple agents touching the same files without worktrees or a clear merge plan.

When delegating code changes:

- Tell each worker they are not alone in the codebase.
- Assign explicit ownership: issue number, branch/worktree, files/modules, tests.
- Ask workers to commit only verified coherent slices if commits are part of the workflow.
- Require final output with changed files, tests run, AC covered, and residual risks.

When delegating sequential exploration or diagnosis:

- Give the worker a narrow question and expected output shape.
- Ask for source references, commands run, key findings, and confidence.
- Have the worker omit broad summaries and unrelated code tour notes.
- Continue locally from the returned findings instead of re-reading everything unless the result is inconsistent or high risk.

## Execution Workflow

For each issue or coherent issue group:

1. Create/switch to the branch/worktree chosen in the plan.
2. Re-read the issue AC before editing.
3. Implement the smallest coherent slice that satisfies one or more AC.
4. Add or update tests proportional to risk:
   - unit tests for pure logic, validation, hashing, sequencing, path filtering, reducers;
   - integration/functional tests for CLI/backend/API behavior;
   - Playwright tests for user-visible web flows once UI exists;
   - manual/runbook checks for local-dev, OS, watcher, or user-judgment behavior.
5. Run relevant checks before committing.
6. Commit with a clear message referencing the issue when practical.
7. Update the issue/PR/runbook evidence if needed.

Do not leave long-running dev servers or agent sessions running at the end of the turn.

## Acceptance Criteria Verification

Create an AC verification matrix for each issue:

```md
| AC | Evidence | Status |
| --- | --- | --- |
| A session page can load a test session | Playwright smoke `...` | Verified |
| Candidate can see polished UX | Not implemented; out of M0 scope | Not verified |
```

Allowed statuses:

- `Verified`: direct evidence exists.
- `User verification needed`: the agent cannot validate it safely or realistically.
- `Blocked`: dependency or environment issue prevents validation.
- `Out of scope`: the issue explicitly excludes it.
- `Not done`: AC remains unsatisfied.

If user verification is needed:

- Ask for the smallest specific check.
- Say exactly what the user should observe.
- Do not claim completion until the user confirms or the issue/PR clearly records the gap.

## Final Validation

Before proposing PRs:

- Run the full relevant test suite, including Playwright if web AC exists.
- Run typecheck and lint if available.
- Re-run focused tests for touched areas.
- Verify browser/runbook flows when UI or local workflow AC exists.
- Check `git status` in every worktree.
- Confirm no unrelated user changes were reverted or committed.
- Summarize AC verification and remaining manual checks.

## PR Strategy

- Default to one issue per PR.
- Combine issues only when they are inseparable, share one coherent review unit, or one PR naturally closes multiple issues.
- Ask the user before pushing branches or creating PRs.
- Draft PR bodies with:
  - linked issue(s),
  - summary,
  - AC verification matrix,
  - tests run,
  - manual/runbook validation requested from the user,
  - risks or intentional deferrals.
- Use closing keywords only when all required AC are verified or explicitly accepted by the user.

## Git Hygiene

- Keep commits small and meaningful.
- Use non-interactive git commands.
- Never reset or discard unrelated changes.
- If worktrees are used, name them predictably and remove them only after the user confirms branches/PRs are safely created or no longer needed.
- If multiple agents produce branches, integrate by PR or explicit merge steps, not by copying random diffs.
