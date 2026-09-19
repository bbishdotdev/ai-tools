# bstack consumer packaging

The generated release installs the complete reviewed bstack bundle through a direct offline Python command or skills.sh. Installation never fetches PStack or selects its latest version. PStack remains pinned to `e31650eea443aaea1e84cc15d88c13f40080b275`; all 162 imported source files retain their original hashes and modes.

Use [the installation guide](../INSTALL.md). The [recorded results](packaging-results.json) contain exact bundle hashes, CLI versions, checks, and evidence locations.

## What ships

The release contains 153 files, with one public `poteto-mode` skill. That entry loads bstack's policy and customized unslop before the selected PStack workflows. Supporting workflows, agents, helpers, verification scripts, licenses, and attribution live inside the same copied directory. Private instructions use `WORKFLOW.md` and an index; they are not dozens of independently installed commands.

The builder records source hashes and declared transformations per file. It rewrites concrete dependencies and planning templates to installed paths, preserves the vendor snapshot, and rejects stale output or unresolved dependencies. PStack's setup and unslop entries resolve to bstack's replacements. Dormant Benny automations are excluded from the consumer bundle.

The controller configures project-local bindings with manual routing by default. Explicit auto on/off operations preserve unslop, unrelated configuration, and private work. Failed configuration updates roll back. Runtime state is gitignored. Fresh clones can adopt exact generated instruction pointers; arbitrary copied wrappers or hook files without their ownership state remain conflicts.

## Installation and deterministic checks

All three installation paths passed: bundled Python, skills.sh symlinks, and skills.sh copies. They delivered identical manifests and passed integrity and binding checks after the staged source was deleted. Tests used project paths containing spaces. The skills CLI was the cached `skills@1.7.0` implementation, installing local release files.

A separate install ran with only Python on PATH and an otherwise empty inherited environment. It succeeded without Git, npm, skills.sh, or any agent CLI available to the installer. After removing the transferred source, the installed doctor and packaged verification driver both ran successfully. Verification left the installed capsule unchanged. This is not a network-isolation test; code inspection confirms the installer has no fetch operation.

77 deterministic tests passed: 29 runtime lifecycle cases, 11 builder cases, 6 evidence-parser cases, and 31 existing adapter/layer/policy cases. The runtime cases include safe collisions, existing configuration preservation, cloned instruction pointers, repeat operations, opt-in persistence, upgrade rollback, symlink boundaries, and private-work retention.

Whitespace checking passes for owned changes. The packaged `automate-me` workflow retains one blank line at EOF from its pinned upstream source; the full staged whitespace check reports that inherited formatting.

After the live run, the generated verification wrapper's help text was corrected to describe its offline default. Routing and hook logic did not change. Runtime tests and all three static installation checks were repeated against the final release. The recorded results preserve both manifest hashes.

## Live CLI results

The offline-installed bundle passed 20 routing/mode probes. Each client completed manual invocation, a fresh default-off engineering prompt, automatic routing, a resumed automatic turn, and a fresh after-off prompt. Auto turns used different tasks and unique file values. Traces showed successful installed-router and fixture reads; no development-checkout reads were observed.

| CLI | Version | Manual and off behavior | Automatic routing and resume | Fresh reminder delivery |
| --- | --- | --- | --- | --- |
| Codex | 0.153.2 | Passed | Passed | Blocked by native project trust in the fresh fixture |
| Claude Code | 2.1.261 | Passed | Passed | 2/2 prompt receipts matched |
| Cursor | 2026.09.15-d2fe57e | Passed | Passed | 2/2 after-tool receipts matched |
| Grok | 1.0.34 | Passed | Passed | 2/2 after-tool receipts matched |

Codex's read-only native `hooks/list` and `config/read` queries identified the disabled project configuration layer. The session trust override used by the headless command did not satisfy that native gate. Neither installer nor verifier changed global trust or granted hook approval. The result is `pass_with_hook_limits`, not a Codex reminder-delivery pass. A missing receipt without explicit native trust evidence remains a failure.

Cursor and Grok still use an after-tool fallback. This does not create native prompt-hook parity: first-tool and tool-free behavior depend on standing instructions. The tests are scoped classification and activation checks, not proof of full engineering workflow execution or deterministic LLM compliance.

## Findings fixed during this pass

The first installed run found that absent router bindings alone did not keep Cursor/Grok from browsing into workflow files. Manual-off instructions now explicitly reserve the engineering router for user invocation. The probe now includes a small application fixture and explicitly forbids auditing installer state or invoking the verifier; earlier attempts that inspected state remain in the evidence as failures.

Independent source review also caught absolute standing-instruction pointers that broke new clones, upstream Git placeholders in generated plans, and verifier imports that could create bytecode caches inside the immutable package. Those issues were fixed and tested. The final delegated review found no remaining high-impact blocker. It used the same model family and did not independently rerun the live sessions.

## Limits

The controller currently requires Python 3.11+ and POSIX; this run used Linux and Python 3.14.7. Optional imported helper programs retain their runtime and authorized-service requirements. They are included as source, not provisioned accounts or downloaded npm dependencies.

Native plugin-manager installation, desktop apps, global installs, remote Git distribution, Windows, and native compaction of this installed release were not tested. Claude/Cursor native descriptors are metadata only. The Codex native descriptor was omitted because its bundled plugin validator rejects the shared manual-entry flag; Codex project skill installation remains verified separately.

The release and its source changes are local Git work. No remote publication or registry release ran.

Raw evidence is retained in `.bstack/verification/packaging-final-live/`, `packaging-release-static/`, and `packaging-python-only/`. Earlier failed runs remain in `packaging-live-first/` and `packaging-live-offline/`. Disposable consumer projects were removed after capture.
