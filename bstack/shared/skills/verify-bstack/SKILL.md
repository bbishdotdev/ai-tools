---
name: verify-bstack
description: Maintainer verification for bstack changes. Discover installed Codex, Claude Code, Cursor, and Grok CLIs, then test router loading, routing, reminders, and continuity with saved evidence. Use when asked to validate bstack or after changing its router adapters.
metadata:
  author: Brenden Bishop
  attribution: ../../../../ATTRIBUTION.md
---

# Verify bstack

This skill is for bstack maintainers and contributors validating changes. Ordinary consumers do not need to run it. The first verification feature is the layered router reminder. Read [the feature map](features/README.md), then test the installed CLIs. Desktop apps are deferred.

## Launch

From the ai-tools repository root, run `python3 bstack/shared/router/install.py` to check the adapters. `--apply` installs the repository-local configuration and links; it preserves other hooks and refuses conflicting links. Codex requires project and hook trust; review the commands through `/hooks` for normal interactive use.

## Doctor

Run `python3 bstack/shared/skills/verify-bstack/scripts/verify.py doctor`. This discovers Codex, Claude Code, Cursor, and Grok on PATH and checks executable versions and configuration without starting a model. Authentication is checked by live probes. Missing tools are skipped by automatic discovery; an explicitly requested missing tool is blocked. Cursor can be supplied with `--cursor-bin /path/to/cursor-agent`.

## Drive

Run `python3 bstack/shared/skills/verify-bstack/scripts/verify.py live`. It selects every installed supported CLI and starts independent read-only sessions, resuming each session for two follow-up prompts. This sends test prompts and the instruction files the agent reads to each signed-in provider and spends model usage. The caller must have authorized live verification. Use `--tools claude` or another subset for focused retesting. Codex honors native hook trust; review the three hooks through `/hooks` before testing. Keep normal Codex config discovery. Grok uses its read-only sandbox and only read/search tools, with subagents and web search disabled. Cursor and Grok receive their documented project-trust option for this repository.

For changes to the Cursor/Grok after-tool fallback, run `python3 bstack/shared/skills/verify-bstack/scripts/fallback.py`. It discovers those two clients and tests dependent reads, once-per-turn emission, resumed turns, and a tool-free response. Use `--tools cursor` or `--tools grok` for a focused retest. Read [the after-tool feature contract](features/after-tool-reminder.md) before interpreting its results.

For bstack policy changes, run `python3 bstack/shared/skills/verify-bstack/scripts/policy.py`. It tests routing, design thresholds, scoped execution, local delivery, authorization reuse, and evidence claims in fresh read-only sessions. Use `--cases` for affected cases and `--tools` for focused retesting. Read [the policy feature contract](features/router-policy.md). These are classification probes, not proof that full workflows or external adapters executed correctly.

For imported source or layer changes, run `python3 bstack/scripts/layers.py check` and `python3 bstack/scripts/audit_pstack.py`. Review a candidate upstream checkout according to [the update procedure](../../../UPSTREAM.md) before changing a pin. Preserve bstack-owned skill replacements and review changed policy dependencies; passing hash checks alone cannot establish semantic compatibility.

For packaging changes, build with `python3 bstack/scripts/package.py build`, check with `python3 bstack/scripts/package.py check`, and run `python3 bstack/shared/skills/verify-bstack/scripts/installation.py`. The installation verifier defaults to the bundled Python installer and requires no skills.sh download. Add `--methods offline symlink copy` to compare all three paths; `--skills-cli /path/to/skills/bin/cli.mjs` uses an already available skills@1.7.0 CLI. Otherwise the explicitly selected skills.sh methods invoke pinned `npx skills@1.7.0`.

Add `--live` for authorized provider-backed checks. The verifier installs into isolated projects, compares exact manifests, deletes its staged source, and drives direct skills, manual Poteto Mode, fresh default-off, automatic routing across resumed turns, and fresh opt-out. `--phases` limits a retest; `--live-method` selects which installed project to drive. Native discovery metadata is reported when a CLI emits it. Native plugin registration, desktop behavior, and native compaction of this installed bundle are not covered by this test. Read [the consumer installation contract](features/installation.md).

## Evidence

Each run writes `.bstack/verification/<run-id>/`: prompts, command arguments, stdout/stderr, exit status, hook receipts, final responses, and `report.json`. A hook execution is not delivery. A fresh receipt echoed by the model establishes delivery; the response's routing choices and actual file reads establish separate behavioral evidence. A retained earlier receipt is not proof of the current prompt hook. An answer asserting that it read a file is not a read trace.

Cursor's native prompt hook is observational in this POC. Its session hook, always-applied rule, and after-tool fallback are separate paths; do not claim a native per-prompt injection pass for Cursor. Compaction requires a real host compaction event and subsequent evidence, not a prompt telling the model to pretend it compacted.

Grok reads `AGENTS.md`; its current `UserPromptSubmit` implementation discards added context. Test its routing and resume behavior, and mark per-prompt hook injection unsupported. `pass_with_limits` means supported routing checks passed while this hook guarantee remains unavailable. It is not full hook parity. Discovery itself does not prove authentication or behavior.

Native after-tool delivery is a narrower claim. Require a fresh echoed **after-tool** receipt on each tool turn and explicit duplicate suppression after subsequent reads. The no-tool turn must contain zero tool calls of any type and zero after-tool emissions; retaining an older receipt does not prove new delivery. Standing instructions cover that turn and the first tool call. The hook uses temporary SQLite state; verification receipts are also collected in a temporary directory, then retained in the report, so Grok's read-only sandbox can run the hook.

## Cleanup

Each CLI invocation is bounded by a timeout. The harness terminates only its own process group on timeout. Completed sessions and evidence remain available for inspection. Do not delete evidence or other users' sessions. Downloaded CLI binaries are disposable; credentials are never copied into evidence.

## Helpers

- `python3 bstack/shared/skills/verify-bstack/scripts/verify.py doctor`
- `python3 bstack/shared/skills/verify-bstack/scripts/verify.py live`
- `python3 bstack/shared/skills/verify-bstack/scripts/fallback.py`
- `python3 bstack/shared/skills/verify-bstack/scripts/policy.py`
- `python3 bstack/shared/router/test_hook.py`
- `python3 bstack/shared/router/test_install.py`
- `python3 bstack/scripts/audit_pstack.py`
- `python3 bstack/scripts/layers.py check`
- `python3 bstack/shared/skills/verify-bstack/scripts/compact.py --tool claude --report .bstack/verification/<run>/claude/report.json` exercises native compaction on an existing test session. Substitute `codex` in both positions for the Codex app-server compaction path. Use a report produced by the live command, not an unrelated user session.

Use the imported `maintain-verification-skill` workflow when expanding the feature map. Preserve explicit unverified results for desktop surfaces and compaction until those exact paths have run.
