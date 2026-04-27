---
name: issue-orchestrator
description: Use when an AI coding agent needs to pull, triage, sequence, execute, verify, commit, and prepare PRs for a batch of GitHub issues. Triggers include requests to work through a milestone, assigned issues, TODO/project-status issues, explicit issue lists, labels, or other subsets; decide dependency order, parallelizable work, delegated-agent handoffs, git worktree strategy, acceptance-criteria validation, runbook/manual verification, commits, and PR readiness.
---

# Issue Orchestrator

Use this skill to turn a set of GitHub issues into an execution plan, then drive the work through implementation, verification, commits, and PR preparation.

This skill is for doing the work, not merely drafting issues. If the user is creating or refining issue text, use `github-issue` instead.

Challenge the issue set. Call out weak acceptance criteria, hidden dependencies, missing tests, and scope that should be split or merged. Do not start from assumptions. Fetch current issues, comments, labels, milestone/project metadata, and relevant code/docs.

Keep context bounded. Default to delegated agents for bounded exploration, dependency diagnosis, implementation slices, and verification passes when delegation is available and permitted. Delegation is useful for sequential handoffs too: a worker can explore or execute a focused task, then report only the relevant findings, changed files, tests, and risks back to the orchestrator.

Prefer one issue per PR, but optimize for coherent review units over rigid bookkeeping. Commit only coherent, verified slices. Do not create noisy commits for half-working acceptance-criteria fragments. Never mark an acceptance criterion as verified unless there is direct evidence: test output, code inspection, browser verification, runbook result, or explicit user confirmation.

Resolve the user's selector before planning:

- Explicit issue numbers: fetch exactly those issues.
- Milestone: fetch all open issues in that milestone.
- Assignment: fetch issues assigned to the target user, usually the authenticated GitHub user unless specified.
- Project/status such as TODO: fetch via available GitHub/project tooling; if project status is unavailable, explain the gap and use labels/milestones/issues as a fallback.
- Label or query: fetch matching open issues.

If the selector is ambiguous and the wrong set would cause real work on the wrong issues, ask one concise clarification. Otherwise make the most conservative reasonable assumption and state it.

Use worker agents, subagents, or equivalent delegation aggressively when available and permitted by the active instructions. Do not reserve delegation only for parallel implementation; also use it to conserve context during sequential work.

Default delegated handoffs include focused codebase exploration before planning or implementation, dependency/install/test failure diagnosis with concrete logs and suspected root cause, independent issue implementation with a clear write scope, verification pass for a completed issue or PR, and runbook/browser smoke on an already-running app.

Keep the task local when it is a tiny lookup, the immediate next step depends on nuanced orchestrator judgment, or delegation would add more coordination cost than context savings.

Good delegated tasks include independent issue implementation with a clear write scope, codebase exploration for a specific question, dependency failure investigation with exact commands/errors, verification pass for a completed issue or PR, and runbook/browser smoke on an already-running app.

Poor delegated tasks include immediate blockers needed for the next local step, vague "figure everything out" requests, and multiple agents touching the same files without worktrees or a clear merge plan.

When delegating code changes, tell each worker they are not alone in the codebase. Assign explicit ownership: issue number, branch/worktree, files/modules, tests. Ask workers to commit only verified coherent slices if commits are part of the workflow. Require final output with changed files, tests run, acceptance criteria covered, and residual risks.

When delegating sequential exploration or diagnosis, give the worker a narrow question and expected output shape. Ask for source references, commands run, key findings, and confidence. Have the worker omit broad summaries and unrelated code tour notes. Continue locally from the returned findings instead of re-reading everything unless the result is inconsistent or high risk.

Create an acceptance-criteria verification matrix for each issue:

```md
| AC | Evidence | Status |
| --- | --- | --- |
| A session page can load a test session | Playwright smoke `...` | Verified |
| Candidate can see polished UX | Not implemented; out of M0 scope | Not verified |
```

Allowed statuses are `Verified`, `User verification needed`, `Blocked`, `Out of scope`, and `Not done`. Use `Verified` only when direct evidence exists. Use `User verification needed` when the agent cannot validate safely or realistically, `Blocked` when a dependency or environment issue prevents validation, `Out of scope` when the issue explicitly excludes it, and `Not done` when acceptance criteria remain unsatisfied.

If user verification is needed, ask for the smallest specific check, say exactly what the user should observe, and do not claim completion until the user confirms or the issue/PR clearly records the gap.

For PR strategy, default to one issue per PR. Combine issues only when they are inseparable, share one coherent review unit, or one PR naturally closes multiple issues. Ask the user before pushing branches or creating PRs. Draft PR bodies with linked issues, summary, acceptance-criteria verification matrix, tests run, manual/runbook validation requested from the user, and risks or intentional deferrals. Use closing keywords only when all required acceptance criteria are verified or explicitly accepted by the user.

Keep git hygiene tight. Keep commits small and meaningful. Use non-interactive git commands. Never reset or discard unrelated changes. If worktrees are used, name them predictably and remove them only after the user confirms branches/PRs are safely created or no longer needed. If multiple agents produce branches, integrate by PR or explicit merge steps, not by copying random diffs.

## When to Use

Use this skill when an AI coding agent needs to pull, triage, sequence, execute, verify, commit, and prepare PRs for a batch of GitHub issues. Use it for requests to work through a milestone, assigned issues, TODO/project-status issues, explicit issue lists, labels, or other issue subsets.

Do not use this skill when the user is only creating, drafting, or refining issue text. Use `github-issue` for that.

## Steps

1. Inventory the selected issues. Fetch issue title, body, acceptance criteria, test plan, labels, milestone/project state, assignees, comments, linked PRs, and URLs. Inspect repo status and avoid overwriting user changes. Read relevant docs and search code with `rg`.

2. Build the dependency graph. Identify foundational schema/contracts/scaffolding, issues blocked by missing APIs, shared types, migrations, or UX surfaces, independent slices with disjoint write scopes, and acceptance criteria that depend on manual/browser/runbook validation.

3. Create the execution plan. Order serial blockers first. Group parallel work only after shared contracts are stable enough. Name expected write scopes and verification gates for each issue. State where delegated agents will be used for both parallel work and sequential context-bounded handoffs. Keep work local only when the next step is tiny, urgent, tightly coupled, or blocked on immediate orchestrator judgment.

4. Decide the worktree strategy. Use git worktrees for parallel implementation when issues should have separate branches/commits or may otherwise collide in one working tree. Keep work serial in the main worktree for foundational/shared-contract changes where parallelism would create merge churn. Prefer branch names like `codex/issue-123-short-topic`. Before creating worktrees, check current branch/status and avoid dirty-worktree surprises.

5. Execute each issue or coherent issue group. Create or switch to the chosen branch/worktree, re-read the issue acceptance criteria before editing, implement the smallest coherent slice that satisfies one or more acceptance criteria, and add or update tests proportional to risk. Use unit tests for pure logic, validation, hashing, sequencing, path filtering, and reducers; integration/functional tests for CLI/backend/API behavior; Playwright tests for user-visible web flows once UI exists; and manual/runbook checks for local-dev, OS, watcher, or user-judgment behavior.

6. Verify before committing. Run relevant checks, create or update the acceptance-criteria verification matrix, and commit with a clear message referencing the issue when practical. Update the issue/PR/runbook evidence if needed. Do not leave long-running dev servers or agent sessions running at the end of the turn.

7. Perform final validation before proposing PRs. Run the full relevant test suite, including Playwright if web acceptance criteria exist. Run typecheck and lint if available. Re-run focused tests for touched areas. Verify browser/runbook flows when UI or local workflow acceptance criteria exist. Check `git status` in every worktree. Confirm no unrelated user changes were reverted or committed. Summarize acceptance-criteria verification and remaining manual checks.
