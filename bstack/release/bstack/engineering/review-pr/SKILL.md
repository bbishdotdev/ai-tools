---
name: review-pr
description: Review a pull request with two independent headless models and a fresh adjudicator that challenges their findings. Recheck follow-up changes without repeating settled review, then prepare or publish a concise verdict.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# Review a PR

Find consequential problems and question whether the PR is needed. A completed review with no actionable findings is a successful result. This is a read-only engineering workflow; it does not fix code or merge the PR.

Apply [bstack's router](../../shared/router/WORKFLOW.md) within this review scope. Use the owned [review rubric](references/rubric.md), not the full Arena or Interrogate workflow. The runner supplies two independent reviewers, anonymizes their findings, and gives a fresh adjudicator the code and decisions needed to challenge them.

## Run

Resolve [the runner](scripts/review.py) from this skill's real location, including installed symlinks. Use its commands instead of assembling model prompts or publication calls yourself. Read [configuration and run details](references/running.md) when configuring roles or interpreting incomplete runs. When a generated ZIP needs coverage, use the runner's source-tree verification described there.

```sh
python3 /absolute/skill-directory/scripts/review.py doctor --project /path/to/project
python3 /absolute/skill-directory/scripts/review.py run --project /path/to/project --pr https://github.com/owner/repo/pull/123
```

Confirm the target PR and local project. The first draft uses authenticated GitHub CLI for the forge and Claude Code/Codex CLIs for model execution. The calling agent can run in any host with those dependencies. Missing clients, unsupported flags, unavailable models, and failed responses are incomplete reviews, never permission to substitute a model or approve.

The first run covers the PR. A follow-up uses the last complete assessment, the new diff and affected context. Retain settled decisions unless new evidence invalidates them. Broader review must name what changed: a base revision, rewritten history, policy, model configuration, or a shared contract. Each reviewer receives its own previous report and the prior consolidated findings, not the other reviewer's raw report. Failed runs must not become the next review baseline.

## Read the result

Inspect the saved review and its coverage before reporting success. Findings need concrete evidence; model agreement alone is insufficient. The adjudicator must account for candidates and prior findings, including those dismissed or resolved. Keep that detailed record private. The public review contains the verdict, meaningful resolutions, surviving findings, and material limits.

The [rubric](references/rubric.md) distinguishes blockers, consequential human decisions, and nonblocking moderate/low findings. No finding quota, mandatory test-per-fix rule, or code-size threshold. Don't invent uncertainty to justify another review round. Don't call an unavailable check a code defect.

## Publish when authorized

Preparing or running a review does not by itself authorize a GitHub write. An explicit request to review and post, or an existing publication grant for this PR, is sufficient; do not ask again. Apply [unslop](../../shared/unslop/SKILL.md) through the review prompts, not by rewriting validated run artifacts afterward.

```sh
python3 /absolute/skill-directory/scripts/review.py publish --project /path/to/project --run /absolute/run-directory
python3 /absolute/skill-directory/scripts/review.py publish --project /path/to/project --run /absolute/run-directory --write
```

Inspect the first command's read-only publication plan. The second posts one GitHub review with its body and supported verdict at the reviewed commit. A stale or incomplete review cannot approve. GitHub self-review restrictions may require a comment that states the intended verdict. Report the actual submitted status and URL, not just the intended status.

Do not post rejected findings, raw model transcripts, or a second copy of the same review. Do not retry an uncertain publication blindly. Use the same run so the runner can reconcile an existing review first. For new commits, run the incremental review before publishing again.
