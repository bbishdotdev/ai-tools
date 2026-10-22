# bstack changelog

User-visible changes collect under **Unreleased** until a version is published. Each release has one notes file, also used as its GitHub Release description. See [release preparation](RELEASING.md) and the [notes template](release-notes/TEMPLATE.md).

## Unreleased

- Make automatic engineering routing the new-install default. Existing projects keep their saved setting; `bstack-auto off` restores manual routing.
- Add `off`, `ask`, and `auto` project-verification settings. New installs use `ask`; feature work can now create or update only the affected `verify-<app>` path.
- Add a cross-host shell PR creation guard, a clearer first-use setup map, and an exact-block path for upgrading cloned v1 installs that lost local state.
- Replace Cursor-bound verifier and comment-cleanup skills, remove four host-specific skills from the consumer catalog, and quarantine seven unported playbooks. The pinned upstream snapshots remain available for selective updates.
- Clarify autonomous grilling's two-model requirement and distinguish saved role choices from a verified model run.
- Add one configurable headless CLI launcher for Codex, Claude Code, Cursor and Grok, with live doctor checks for selected review, grilling and PR-visual roles. PR review and autonomous grilling stop before full work when a chosen CLI model fails its short probe.

## Published releases

| Version | Date | Notes |
| --- | --- | --- |
| [1.0.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v1.0.0) | 2026-10-19 | [Browsable guide, project PR policy, and clearer setup](release-notes/1.0.0.md) |
| [0.8.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.8.0) | 2026-10-10 | [Scoped PR feedback and safer upgrades](release-notes/0.8.0.md) |
| [0.7.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.7.0) | 2026-10-10 | [Independent PR review and clearer PR visuals](release-notes/0.7.0.md) |
| [0.6.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.6.0) | 2026-10-07 | [Seven-rule baseline for project agents](release-notes/0.6.0.md) |
| [0.5.1](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.5.1) | 2026-09-29 | [Module documentation and source credits](release-notes/0.5.1.md) |
| [0.5.0](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.5.0) | 2026-09-29 | [Shared architecture decisions and ADR discovery](release-notes/0.5.0.md) |
| [0.4.2](https://github.com/bbishdotdev/ai-tools/releases/tag/v0.4.2) | 2026-09-29 | [Downloadable installers, setup guidance, and Atlas improvements](release-notes/0.4.2.md) |

0.4.2 is the first formal GitHub Release. Earlier development is recorded in Git history.
