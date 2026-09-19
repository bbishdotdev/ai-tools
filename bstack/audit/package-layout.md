# Direct skills and package layout

Date: 2026-09-19. This replaces the consumer layout described in the [initial packaging report](packaging.md). Pinned source snapshots remain unchanged.

## Installed contract

bstack owns `.bstack/package/`. Public engineering skills sit directly under its `engineering/` bucket; writing and control skills sit under `shared/`. Each of the 29 public names has a small binding in `.agents/skills/`, with per-skill links for Claude Code, Cursor, and Grok. The [manifest](../release/bstack/manifest.json) is the catalog and file-integrity record.

Poteto Mode is an ordinary engineering entry. Invoking another skill loads that workflow and the bstack policy without automatically loading the upstream router. Principles and playbooks remain internal dependencies. Customized unslop remains active for prose; engineering routing stays manual unless auto mode is enabled.

The offline installer copies the canonical package. skills.sh transports one `install-bstack` skill carrying a deterministic archive of that same package. Its bootstrap installs the canonical package and public bindings. This extra bootstrap step is required because skills.sh copies skill folders but does not run setup. The archive stays distributor-owned and is not a runtime dependency.

The approved prototype, Matt Pocock workflows, shared memory, and GitHub assets remain pending runtime integration. Native plugin manifests with the previous skill-root layout were removed; this release makes no native plugin-manager or desktop compatibility claim.

## Installation and migration

Offline, skills.sh symlink, and skills.sh copy installation produced identical canonical manifests and all 29 public bindings for all four hosts. Tests used paths containing spaces and removed the staged source before bootstrap, doctor, and model execution. The skills.sh archive remained unchanged. The distributor was the cached `skills@1.7.0` CLI using local release files.

Migration also used the actual prior release from commit `20994ee`. Its offline install had auto enabled and all four hosts selected. The new installer moved it to `.bstack/package/`, preserved those settings, and passed doctor after both source copies were removed. Uninstall removed the owned package and bindings while preserving a private work file.

120 deterministic tests passed: 16 builder, 41 runtime, 7 archive transport, 21 installation evidence, and 35 existing layer, development-installer, and policy checks. They cover package closure and reproducibility, public/private skill boundaries, archive validation, ownership and collisions, rollback, updates, migration, removal, and evidence parsing. Source integrity checks confirm all PStack and Matt Pocock pins remain unchanged. One pre-existing unresolved Markdown link remains in the frozen PStack source.

## Live behavior

The offline-installed package was tested with Codex 0.153.2, Claude Code 2.1.261, Cursor 2026.09.18-9a7762b, and Grok 1.0.34. The probes classify tasks and read instructions and fixture values. They do not execute full engineering workflows.

Direct `how` and manual Poteto Mode probes passed across all four clients. Direct invocation observed successful packaged `how` and policy reads without reading the upstream router or delegating. Claude and Grok also emitted native skill lists containing all 29 public names. Codex and Cursor did not emit an equivalent registry in these traces; their evidence is direct invocation and observed reads, plus filesystem binding checks.

Codex's automatic routing and session continuity passed, but its fresh fixture's native project trust gate blocked hooks. The verifier reports that limit without granting trust. This is not a Codex hook-delivery pass.

During broader testing, Cursor attached a fresh after-tool context to both native tool events but the model returned an older lifecycle receipt on one turn and null on the other. Those runs remain failures of model acknowledgment. Grok also browsed the router during one fresh off-mode probe while investigating the requested receipt, despite manual-only instructions. Its auto setting and hooks were correctly off. Off-mode wording now explicitly prohibits searching files or configuration for receipts, and Cursor/Grok auto probes specify the exact after-tool receipt label.

The focused Cursor/Grok rerun passed both auto turns and fresh after-off behavior. Each auto turn echoed the exact new after-tool receipt and read its new fixture value; resumed session IDs matched. Combined results from the primary runs and focused rerun are:

| CLI | Direct skill and manual mode | Fresh default-off and after-off | Auto routing and resume | Reminder acknowledgment |
| --- | --- | --- | --- | --- |
| Codex | Passed | Passed | Passed | Blocked by native project trust |
| Claude Code | Passed | Passed | Passed | Both prompt receipts matched |
| Cursor | Passed | Passed | Passed on focused retry | Both after-tool receipts matched on retry |
| Grok | Passed | Passed after focused after-off retry | Passed | Both after-tool receipts matched |

## Verification corrections

Independent review and live traces led to three evidence-check corrections: any successful partial upstream-router read now fails the direct-entry exclusion check; negative search globs and filename-only listings no longer count as content reads; native search inputs and result paths are inspected so forbidden state-file searches cannot escape the check. Hook emission, native context attachment where observable, and model acknowledgment are reported separately. Model acknowledgment remains required for the reminder-delivery check.

Rechecking 34 saved traces with the stricter access checks found two additional failures in earlier Cursor probes: default-off in `dda340` searched runtime/controller source, and auto-1 in `09b8f6` searched the state file. Direct/manual traces and the focused rerun remained clean. The later default-off pass came from `09b8f6`; the later auto and after-off passes came from `f3c6e2`. Original reports are retained unchanged alongside the stricter recheck. Final evidence-parser corrections were applied to these saved traces without spending more model usage; the router and reminder adapter did not change.

The first live attempt failed because the outer sandbox prevented clients from writing their own local state. Authorized reruns used normal CLI access. All failures remain in private evidence alongside the later results.

## Evidence and limits

Private evidence is under `.bstack/verification/`:

- `20260919T214255Z-installation-dda340`: four-client direct and manual checks; includes the subsequently fixed Codex negative-glob false positive in default-off.
- `20260919T214625Z-installation-09b8f6`: default-off, auto, resumed auto, and after-off; includes Cursor acknowledgment and Grok off-mode failures.
- `20260919T215450Z-installation-f3c6e2`: focused Cursor/Grok auto, resumed auto, and after-off passes.
- `20260919T215808Z-installation-ae11fe`: final three-method installation and binding checks after evidence-parser corrections.
- `.bstack/work/package-layout/migration.json`: real previous-release migration and removal evidence.
- `.bstack/work/package-layout/access-evidence-recheck.json`: stricter replay of saved access traces without new model calls.

These are bounded CLI observations, not deterministic LLM compliance. Cursor and Grok's after-tool fallback cannot deliver before the first tool or on tool-free turns. Global installs, remote Git distribution, Windows, desktop applications, native plugin managers, full workflow execution, and installed-package context compaction remain unverified. See the [installation guide](../INSTALL.md) and [verification contract](../shared/skills/verify-bstack/features/installation.md).
