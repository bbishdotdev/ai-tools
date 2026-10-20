---
name: configure-pr
description: Set or revise this repository's PR review priorities, human-review paths, critical behavior, and linked standards. Use when a developer says what their team's PR process should care about.
metadata:
  author: Brenden Bishop
  attribution: ../../../ATTRIBUTION.md
---

# Configure project PR policy

Maintain one committed `bstack-pr-policy.md` at the Git repository root. In a monorepo, scope rules with repository-relative paths such as `apps/web/src/auth/**`. Do not create a separate file per package. The policy adds project concerns to [BStack's shared PR standards](../../references/pr-standards.md); it cannot relax them.

Read the existing policy and relevant project standards before editing. If no policy exists, start from the [empty template](../../references/pr-policy-template.md). Translate the developer's request into the smallest useful addition. Keep existing project rules unless the developer asks to revise them. Link established Markdown standards instead of copying their contents. Do not move this policy into `.bstack/`, `AGENTS.md`, or a forge-specific folder.

Use the four headings in the template. Under **Human review required**, write one-line bullets as `- \`path-or-glob\`: reason`. These rules are matched by code against changed paths, so name actual paths. A semantic concern such as "anything that affects authentication" may extend beyond a path rule; state that limit and add a focused review concern as needed. Human review withholds BStack's AI approval. Forge branch protection or owners rules are a separate way to enforce the merge.

Under **Critical behavior** and **Review focus**, use short one-line bullets. Critical behavior is a blocker when evidence shows a regression; an unverified concern is a coverage gap, not an invented defect. Under **Relevant standards**, write `- \`path/to/file.md\`: why it matters`. The file must be committed to the target branch for reviewers to rely on it.

Validate the result with `python3 <absolute-package-path>/shared/pr_policy.py validate --project <repo-root>`. For an open PR, check the applicable base revision with `check --project <repo-root> --base <target-ref>`. Show the developer the resulting policy and which changed paths require a human. Changes to `bstack-pr-policy.md` itself always require human review. Do not silently edit forge ownership or branch protection.
