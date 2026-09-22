---
name: to-pr
description: Prepare a short visual PR briefing, check open work for overlap, and publish to the authorized destination. Use for an explicit PR request or an authorized PR delivery step.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# PR

Give the reviewer enough context to understand the change in three minutes or less. Aim for 250–400 words at most for substantial work. Small changes need much less. Use a concrete before/after and a useful visual before adding explanation.

Read [bstack's router](../../shared/router/WORKFLOW.md) and apply [bstack's unslop](../../shared/unslop/SKILL.md) to the title, body, captions, and commit prose. This entry replaces PStack's Opening a PR workflow. Do not run both.

## Establish the change

Use the accepted ticket or spec, relevant ADRs, prior review, and the final diff against the actual PR base. Confirm the repository, forge, branch, destination, and existing publication scope. An implementation request alone does not authorize publication. Reuse adequate grounding and settled decisions. Do not rerun teach, how, or why just to fill a PR template. Investigate only gaps that affect the explanation or review.

When this workflow starts before implementation, capture a useful baseline early. Use a real screenshot, command output, or measurement with enough context to compare it later. If the earlier state is gone, say that. A reconstruction or a generated illustration cannot count as observed baseline evidence.

Keep unrelated work intact. Use an isolated checkout if needed. Inspect the final diff for unintended changes and sensitive data. Run [deslop](../deslop/SKILL.md) before committing and [no-comments](../no-comments/SKILL.md) before review. Complete the selected workflow's required tests and independent review. Reuse review of unchanged code; refresh checks affected by later edits. If a delegate opens the PR, retain the [interrogate](../interrogate/SKILL.md) step through the router's capability contract. Record missing checks honestly.

Keep commits coherent and ordered when commit preparation is in scope. Never discard unrelated changes, reset a worktree, or rewrite shared history to tidy a PR. For a stack, compare each child with its intended parent branch and explain the dependency.

## Write the briefing

Honor the consumer repository's required PR-template sections. Use the [bstack template](../../github/pull_request_template.md) where compatible. Do not replace the consumer's `.github` template automatically. Remove empty optional sections and drafting instructions.

Use these five sections in order. Give each a distinct purpose without repeating the same explanation or visual:

1. **What changes and why.** State the change and the problem it solves. Give a concrete trigger and result.
2. **Before and after.** Compare the previous and resulting states using whatever makes that change clearest: short prose, a table, example input/output, measurements, or screenshots. An image is not required. Use comparable conditions for measured results.
3. **For visual nerds.** Show what was implemented or how it works. Choose the representation that fits: a UI screenshot, data flow, user flow, architecture SVG, sequence diagram, ERD, or another useful visual. Keep it focused on the important relationships.
4. **How it works and why.** Explain the mechanism and why this solution was chosen so a ten-year-old could follow the idea, without talking down to the reviewer. Link the key files or symbols and explain their roles. Use forge links at the reviewed revision for published PRs, not local filesystem paths. Include relevant ADRs, tradeoffs, and alternatives actually explored when they explain the choice. Distinguish documented reasoning from inference; do not invent alternatives or rationale.
5. **Verification.** Name the tests, checks, and observations that actually verified the change, their outcomes, and material limits. Link detailed evidence instead of pasting logs.

Keep technical terms that carry meaning and explain unfamiliar ones. Do not force an analogy or simplify away a constraint. Add Reviewer attention after these sections only for an unresolved risk, decision, missing required check, or concrete reviewer action.

Draw explanations with authored SVGs or the available image-generation tool when that helps. Match every label, arrow, and state to the code. Label generated visuals as illustrations. Inspect the rendered result. Keep screenshots separate as evidence of an observed run, with its state and relevant viewport or environment. Never generate a screenshot to imply a test passed.

Keep the visual small enough to understand at a glance. If image generation, rendering, or upload is unavailable, use Mermaid, a compact table, or a text flow under For visual nerds. A trivial change needs only a small representation. No cloud image service is required. Use short captions and alt text. A local file path is not a usable image link in a published PR.

Use the repository's title convention. Otherwise use `type(scope): short imperative subject`, with a real changed area as the scope. Keep the briefing focused on the final change; include explored alternatives only to explain the chosen solution. Apply the sentence-level guidance from [technical-writing](../technical-writing/SKILL.md), then unslop. Its shorter PR-body target does not override this workflow's three-minute limit.

## Check overlap and deliver

Read [publishing](references/publishing.md) before scanning or publishing. Inspect all open PRs, including drafts, for duplicate intent, contradictory decisions or contracts, and actual hard conflicts. Different files and branches can still implement the same thing. Shared files alone do not prove a conflict. Read matching diffs and accepted decisions before classifying them.

The final check must be fresh immediately before creation. The [GitHub helper](../../github/pr.py) records coverage, requires explicit review, checks freshness again, and reconciles retries. Flagged or incomplete checks with a valid initial scan still permit an authorized draft PR. If branch identity or the open-PR list cannot be read, keep a local draft and report that publication is blocked. The helper adds a concise linked warning at the top and actionable Reviewer attention at the bottom. Do not add a duplicate manual notice or treat the scan as a review verdict.

Prepare the body, evidence, and publication plan before asking about any unresolved publication boundary. Preserve permission already granted for that destination and status. Use `--draft` when the user requested a draft or unresolved checks require one. Do not make a previously flagged PR ready just because the flag disappeared. Refresh the substantive review first and preserve the authorized status. A new helper bundle cannot adopt an existing PR. Keep a stale published PR draft for an explicit reviewed follow-up.

After publication, verify the URL, body, attachments or fallbacks, base, head, and actual draft status. Attach the PR to the current task when the host supports it. Return the link, verification result, and any material coverage limit. Do not comment on other PRs, request reviewers, merge, or start monitoring as part of this workflow.
