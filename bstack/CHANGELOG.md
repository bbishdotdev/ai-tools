# bstack changelog

User-visible changes collect under **Unreleased** until a version is published. Each release has one notes file, also used as its GitHub Release description. See [release preparation](RELEASING.md) and the [notes template](release-notes/TEMPLATE.md).

## Unreleased

- Add native Amp, Copilot, and OpenCode routing and PR guards, plus direct playbook links and compaction reminders. See [PR #23](https://github.com/bbishdotdev/ai-tools/pull/23).
- Generate compatibility from real developer scenarios, track model quality separately, and record native PR-guard denials. Failed or quota-limited attempts remain visible instead of retaining an old green result.
- Keep generated-code grading and candidate Git commands in a credential-free, network-isolated maintainer worker. Consumer installation and static PR review need no new system packages.
- Refresh an owned PR description through `to-pr`, restoring draft status when its new assessment requires it. Truly small PRs, up to two files and 30 changed lines, can omit a visual.

## Published releases

| Version | Date | Notes |
| --- | --- | --- |
| [3.0.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v3.0.0) | 2026-10-26 | [Portable review tools and clearer feedback](release-notes/3.0.0.md) |
| [2.0.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v2.0.0) | 2026-10-23 | [Safer PR reviews and portable setup](release-notes/2.0.0.md) |
| [1.0.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v1.0.0) | 2026-10-19 | [Browsable guide, project PR policy, and clearer setup](release-notes/1.0.0.md) |
| [0.8.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.8.0) | 2026-10-10 | [Scoped PR feedback and safer upgrades](release-notes/0.8.0.md) |
| [0.7.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.7.0) | 2026-10-10 | [Independent PR review and clearer PR visuals](release-notes/0.7.0.md) |
| [0.6.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.6.0) | 2026-10-07 | [Seven-rule baseline for project agents](release-notes/0.6.0.md) |
| [0.5.1](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.5.1) | 2026-09-29 | [Module documentation and source credits](release-notes/0.5.1.md) |
| [0.5.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.5.0) | 2026-09-29 | [Shared architecture decisions and ADR discovery](release-notes/0.5.0.md) |
| [0.4.2](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.4.2) | 2026-09-29 | [Downloadable installers, setup guidance, and Atlas improvements](release-notes/0.4.2.md) |

0.4.2 is the first formal GitHub Release. Earlier development is recorded in Git history.
