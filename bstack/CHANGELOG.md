# bstack changelog

User-visible changes collect under **Unreleased** until a version is published. Each release has one notes file, also used as its GitHub Release description. See [release preparation](RELEASING.md) and the [notes template](release-notes/TEMPLATE.md).

## Unreleased

- `to-pr` now tries Codex CLI image generation for a grounded, readable PR illustration, then the current agent's image tool and plain visual fallbacks. The packaged workflow includes the brief, inspection, and attachment procedure.
- Draft `review-pr` workflow: two independent reviews, anonymous adversarial adjudication, PR-necessity checks, incremental follow-ups, and concise GitHub verdicts. Claude Code/Codex execution and GitHub publication have been exercised on a live draft PR.
- Review follow-ups now assess author rebuttals and existing public feedback, share compatible published assessments without duplicate approval, and save useful findings when noncritical artifacts limit coverage. Publication can react or reply to prior reviews, with a new request-changes event only for a unique blocker. A private live calibration exercised these decisions with real model calls.
- Resolved review replies now point to the earlier discussion and reviewed commit, with the detailed evidence kept in the private assessment rather than repeated in the public comment.

## Published releases

| Version | Date | Notes |
| --- | --- | --- |
| [0.6.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.6.0) | 2026-10-07 | [Seven-rule baseline for project agents](release-notes/0.6.0.md) |
| [0.5.1](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.5.1) | 2026-09-29 | [Module documentation and source credits](release-notes/0.5.1.md) |
| [0.5.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.5.0) | 2026-09-29 | [Shared architecture decisions and ADR discovery](release-notes/0.5.0.md) |
| [0.4.2](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.4.2) | 2026-09-29 | [Downloadable installers, setup guidance, and Atlas improvements](release-notes/0.4.2.md) |

0.4.2 is the first formal GitHub Release. Earlier development is recorded in Git history.
