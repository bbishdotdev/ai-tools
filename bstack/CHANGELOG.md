# bstack changelog

User-visible changes collect under **Unreleased** until a version is published. Each release has one notes file, also used as its GitHub Release description. See [release preparation](RELEASING.md) and the [notes template](release-notes/TEMPLATE.md).

## Unreleased

- VS Code with Copilot is now measured: skills and PR workflows are Supported, auto mode and hooks Partial.
- The router and its reminder say task size is no exemption: a one-line fix still opens its playbook.
- Copilot hooks now work in VS Code. VS Code runs the Copilot binding with its own event names and terminal tool, so the router reminder and PR guard were silently skipped there.
- The README opens with the supported tools and whether each has CLI or CLI and desktop bindings. `matrix.py` generates the strip with the compatibility matrix.
- Cursor desktop and Claude Code desktop are now measured: both prove skills and auto mode through computer-use runs. PR workflows and hooks stay Partial until the remaining desktop scenarios run.
- Desktop verification fixes: Claude Code desktop cases reach the fake `gh`, OpenCode desktop opens each case's own project, Cursor's post-compaction context no longer shifts graded turns, and blocked or unattempted cases are no longer recorded as failures. `interactive.py status` checks a case's launch, environment, and transcript before prompts are graded.

## Published releases

| Version | Date | Notes |
| --- | --- | --- |
| [3.1.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v3.1.0) | 2026-10-29 | [Measured CLI compatibility and native workflow guards](release-notes/3.1.0.md) |
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
