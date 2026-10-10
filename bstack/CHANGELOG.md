# bstack changelog

User-visible changes collect under **Unreleased** until a version is published. Each release has one notes file, also used as its GitHub Release description. See [release preparation](RELEASING.md) and the [notes template](release-notes/TEMPLATE.md).

## Unreleased

- Upgrades recreate a missing BStack-owned `AGENTS.md` or `CLAUDE.md` block and warn that project guidance outside the block cannot be recovered from BStack. Existing files with changed blocks still stop for reconciliation. Setup now calls out newly created, untracked root instruction files.
- Setup now gives projects without a PR template a starter `.github/pull_request_template.md`. It reports existing template locations and how to choose a replacement without overwriting them. Edits to the starter copy remain project-owned across upgrades and uninstall.
- PR review now rechecks changes made during review or before publication, with a three-pass limit and a clear stale warning if the PR keeps moving. `to-pr` and `review-pr` now share standards for need, scope, evidence, decisions, and material risk.
- `to-pr` now requires a real image or diagram for non-micro changes. A self-explanatory one-file, one-hunk edit may omit the visual section; text arrows no longer count as a visual, and uploaded images need a Mermaid fallback.

## Published releases

| Version | Date | Notes |
| --- | --- | --- |
| [0.7.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.7.0) | 2026-10-10 | [Independent PR review and clearer PR visuals](release-notes/0.7.0.md) |
| [0.6.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.6.0) | 2026-10-07 | [Seven-rule baseline for project agents](release-notes/0.6.0.md) |
| [0.5.1](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.5.1) | 2026-09-29 | [Module documentation and source credits](release-notes/0.5.1.md) |
| [0.5.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.5.0) | 2026-09-29 | [Shared architecture decisions and ADR discovery](release-notes/0.5.0.md) |
| [0.4.2](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.4.2) | 2026-09-29 | [Downloadable installers, setup guidance, and Atlas improvements](release-notes/0.4.2.md) |

0.4.2 is the first formal GitHub Release. Earlier development is recorded in Git history.
