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

The runner checks whether review work is needed before starting models. Closed PRs are skipped; confirmed merge conflicts defer review. Unchanged compatible assessments can be reused locally or from a trusted published review. Different models or `run --fresh` start an independent pass, with earlier public feedback available as evidence. Reusing someone else's assessment never submits an approval as the current developer.

A follow-up uses the last complete assessment, new changes and affected context. Each reviewer receives its own earlier report when available, not the other current reviewer's report. Human rebuttals can trigger reassessment without a code change. Evaluate them honestly: accept supported corrections or justified noncritical trade-offs, and defend findings that still hold. Follow the rubric for critical failures and decision authority.

## Read the result

Inspect the saved review and its coverage before reporting success. Findings need concrete evidence; model agreement alone is insufficient. The adjudicator accounts for candidates, prior findings, existing public feedback and artifact limitations. Valid partial assessments keep their findings and may publish useful feedback, but cannot approve or replace the complete follow-up baseline. Failed model calls or malformed results are not publishable assessments.

The [rubric](references/rubric.md) distinguishes blockers, consequential human decisions, and nonblocking moderate/low findings. No finding quota, mandatory test-per-fix rule, or code-size threshold. Don't invent uncertainty to justify another review round. Don't call an unavailable check a code defect.

## Publish when authorized

Preparing or running a review does not by itself authorize a GitHub write. An explicit request to review and post, or an existing publication grant for this PR, is sufficient; do not ask again. Apply [unslop](../../shared/unslop/SKILL.md) through the review prompts, not by rewriting validated run artifacts afterward.

```sh
python3 /absolute/skill-directory/scripts/review.py publish --project /path/to/project --run /absolute/run-directory
python3 /absolute/skill-directory/scripts/review.py publish --project /path/to/project --run /absolute/run-directory --write
```

Inspect the first command's read-only action plan. The second performs its reactions, replies and any new review. Agree with existing feedback in place; publish only useful additions, disagreements, resolutions and genuinely new findings. Existing-only blockers do not create another request-changes status. Approval still requires a complete assessment with no unresolved blocker or human decision. A stale result cannot publish.

Use concise, human wording, category icons and the actual model signature. GitHub may accept only a comment on the current user's own PR; distinguish that recommendation from a formal approval. Report the actual submitted actions and links.

Do not post rejected findings, raw model transcripts, or a second copy of the same review. Do not retry an uncertain publication blindly. Use the same run so the runner can reconcile an existing review first. For new commits, run the incremental review before publishing again.
