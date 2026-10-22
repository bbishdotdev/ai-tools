---
name: to-pr
description: Prepare a short visual PR briefing, check open work for overlap, and publish to the authorized destination. Use for an explicit PR request or an authorized PR delivery step.
disable-model-invocation: false
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# PR

Give the reviewer enough context to judge the change in five minutes or less. Aim for 300–500 words for substantial work; small changes need much less. The helper counts authored prose, including visual fallbacks but excluding generated overlap notices, and stops above 650 words unless a required project template or material risk justifies a recorded exception. A larger diff needs a tighter briefing and links to detail, not a longer narration.

Read [bstack's router](../../shared/router/WORKFLOW.md) and apply [bstack's unslop](../../shared/unslop/SKILL.md) to the title, body, captions, and commit prose. This entry replaces PStack's Opening a PR workflow. Do not run both.

## Establish the change

Use the accepted ticket or spec, relevant ADRs, prior review, and the final diff against the actual PR base. Confirm the repository, forge, branch, destination, and existing publication scope. An implementation request alone does not authorize publication. Reuse adequate grounding and settled decisions. Do not rerun teach, how, or why just to fill a PR template. Investigate only gaps that affect the explanation or review.

Read and apply the shared [PR standards](../../shared/references/pr-standards.md) to the full diff before writing the briefing. Check need, scope, evidence, decisions, and material risk. If a materially mixed PR remains, call it out and keep it draft for review.

Run the [project PR policy checker](../../shared/pr_policy.py) against the actual target ref before publishing. Include any human-review requirement in Reviewer attention and use applicable critical behavior, focus areas, and committed standards when assessing the diff. A human-review rule does not by itself require a draft PR. Do not let a policy change on this PR set its own review rules.

When this workflow starts before implementation, capture a useful baseline early. Use a real screenshot, command output, or measurement with enough context to compare it later. If the earlier state is gone, say that. A reconstruction or a generated illustration cannot count as observed baseline evidence.

Keep unrelated work intact. Use an isolated checkout if needed. Inspect the final diff for unintended changes and sensitive data. Run [deslop](../deslop/SKILL.md) before committing and [no-comments](../no-comments/SKILL.md) before review. Complete the selected workflow's required tests and independent review. Reuse review of unchanged code; refresh checks affected by later edits. If a delegate opens the PR, retain the [interrogate](../interrogate/SKILL.md) step through the router's capability contract. Record missing checks honestly.

Keep commits coherent and ordered when commit preparation is in scope. Never discard unrelated changes, reset a worktree, or rewrite shared history to tidy a PR. For a stack, compare each child with its intended parent branch and explain the dependency.

## Write the briefing

Honor the consumer repository's required PR-template sections. Use the [bstack template](../../github/pull_request_template.md) where compatible. Do not replace the consumer's `.github` template automatically. Remove empty optional sections and drafting instructions.

Use these four sections in order. Each answers one reviewer question. Keep paragraphs short, usually two to five sentences; no walls of text. The only visual exception is a self-explanatory micro change in one file and one diff hunk, such as a typo or copy edit. Complex code or multiple files or hunks do not qualify.

1. **What changes and why.** State the change and the problem it solves. Give a concrete trigger and result.
2. **Before and after.** Show the few state changes that explain the outcome. Use short prose, a compact table, example input/output, measurements, or real screenshots. Use comparable conditions for measured results. Put a before/after visual here when it helps.
3. **How it works and why.** Give the reviewer the core logic and the reason for this implementation in plain language. Place each useful visual next to the point it explains. Show the actual result with a real screenshot when the change is visible in the product; use a generated illustration, annotated state view, authored SVG, sequence diagram, or ERD when the important behavior is hidden. Do not default to process flows, arrows, or human characters. Let distinct reviewer questions determine how many visuals earn a place; do not generate a picture for every paragraph. A text flow with arrows or a table is not a visual. Link directly to the few defining PR file diffs or symbols so a reviewer can jump from the explanation into the code. Link an ADR or alternative only when it explains a consequential choice. Do not inventory every module, retell the ADR, or invent rationale.
4. **Verification.** Say what ran, what passed, and the one or two material limits. Link the detailed test evidence instead of narrating test cases or pasting logs.

Keep technical terms that carry meaning and explain unfamiliar ones for a new developer. Do not force an analogy or simplify away a constraint. Add Reviewer attention after these sections only for an unresolved risk, decision, missing required check, or concrete reviewer action. Keep each item to the action and why it matters; related work with no action stays out.

The helper adds a small AI signature after the briefing. Pass the exact model ID only when the host exposes it; otherwise it says the model was not reported. Do not guess a model, put the signature in the authored body, or claim that the signature proves who wrote the text.

For a generated explanation, prefer a headless Codex CLI session with image generation when Codex use is allowed for this project. Check its configured launcher with the live `to-pr` doctor before the attempt; a text probe does not prove the image tool works. Give it a brief grounded in the final diff and the idea each visual should explain; follow [the visual procedure](references/visuals.md). Inspect the result for accuracy and legibility before using it. If Codex is not authorized, available, or able to generate an image, use the current agent's image-generation capability. Use a real screenshot for visible results and an authored SVG or Mermaid diagram when exact relationships matter more than generated art. Do not jump to a weak fallback merely because a change is easy to summarize in text. If a non-micro PR still lacks a useful visual, keep it draft and report the missing step rather than publish arrow text.

Match every label, arrow, and state to the code. Label generated visuals as illustrations. Keep screenshots separate as evidence of an observed run, with its state and relevant viewport or environment. Never generate a screenshot to imply a test passed. Use short captions and alt text. A local file path is not a usable image link in a published PR.

Keep PR-only visuals in the ignored `.bstack/pr/` directory. For every PR-only image on GitHub, try `gh pr edit --attach` first through the [publishing procedure](references/publishing.md). Do not commit the image to host it before that attempt. Check the published body because an upload can append the image instead of placing it beside its explanation. If attachment fails, use the diagram fallback. If displaying the image would require committing it to the repository, ask the user first. Commit a visual without that extra check only when the project itself needs the file, independent of this PR description.

Use the repository's title convention. Otherwise use `type(scope): short imperative subject`, with a real changed area as the scope. Keep the briefing focused on the final change; include explored alternatives only to explain the chosen solution. Apply the sentence-level guidance from [technical-writing](../technical-writing/SKILL.md), then unslop. Its shorter PR-body target does not override this workflow's five-minute limit.

## Check overlap and deliver

Read [publishing](references/publishing.md) before scanning or publishing. Inspect all open PRs, including drafts, for duplicate intent, contradictory decisions or contracts, and actual hard conflicts. Different files and branches can still implement the same thing. Shared files alone do not prove a conflict. Read matching diffs and accepted decisions before classifying them.

The final check must be fresh immediately before creation. The [GitHub helper](../../github/pr.py) records coverage, requires explicit review, checks freshness again, and reconciles retries. Flagged or incomplete checks with a valid initial scan still permit an authorized draft PR. If branch identity or the open-PR list cannot be read, keep a local draft and report that publication is blocked. The helper adds a concise linked warning at the top and actionable Reviewer attention at the bottom. Do not add a duplicate manual notice or treat the scan as a review verdict.

Prepare the body, evidence, and publication plan before asking about any unresolved publication boundary. Preserve permission already granted for that destination and status. Use `--draft` when the user requested a draft or unresolved checks require one. Do not make a previously flagged PR ready just because the flag disappeared. Refresh the substantive review first and preserve the authorized status. A new helper bundle cannot adopt an existing PR. Keep a stale published PR draft for an explicit reviewed follow-up.

After publication, verify the URL, body, attachments or fallbacks, base, head, and actual draft status. Attach the PR to the current task when the host supports it. Return the link, verification result, and any material coverage limit. Do not comment on other PRs, request reviewers, merge, or start monitoring as part of this workflow.
