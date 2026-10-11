# Engineering

This directory contains bstack-owned engineering entries. [Research](research/SKILL.md) produces bounded findings for planning, [prototype](prototype/SKILL.md) activates the approved disposable experiment lifecycle, and [implement](implement/SKILL.md) hands accepted work to the existing PStack engineering process. The [to-pr workflow](to-pr/SKILL.md) turns authorized delivery into a short visual briefing, checks open PRs for duplicate or conflicting work, and keeps flagged work in draft. Its [helper](../github/pr.py) and [template](../github/pull_request_template.md) ship in the same offline package.

Prototype's [design notes](prototype/REVIEW.md) preserve the source comparison and instruction review.

The [review-pr draft](review-pr/SKILL.md) uses two independent headless reviews followed by a fresh adjudicator that tries to disprove their findings. It checks whether a change is needed, consults ADRs, and reviews follow-up deltas against the last completed assessment. The bundled Python runner handles pinned snapshots, private history, existing public feedback, and authorized GitHub review publication. Claude Code and Codex are the first execution adapters. A live calibration checked that the reviewers upheld a reproduced privacy defect despite an author rebuttal and rejected an unsupported architecture demand.

[Resolve PR](resolve-pr/SKILL.md) is the author-side follow-up. It checks feedback against code and the PR's purpose, fixes only valid in-scope concerns, and explains rejections or separate work in the original discussion. Its GitHub helper pins feedback before assessment, checks freshness before replies, and reconciles retries without clearing another person's review state.

The current consumer release uses the [bstack router](../shared/skills/bstack-router/SKILL.md) with selected pinned engineering dependencies. Browse the [packaged engineering skills](../release/bstack/engineering/) for the consumer layout, or the [PStack source catalog](../audit/catalog.md) or the [source skills](../upstream/pstack/skills/). Those source snapshots live under [upstream](../upstream/README.md). Keep custom workflows here and source snapshots there so each can evolve without overwriting the other.

See [SDLC integration](../sdlc/integration-review.md) for how planning and engineering connect, and [central attribution](../ATTRIBUTION.md) for source relationships and notices.
