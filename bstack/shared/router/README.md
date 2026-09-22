# Router reminder POC

`AGENTS.md` points to the [bstack policy entry](../skills/bstack-router/SKILL.md), which selects PStack workflows and governs their host/service assumptions. `CLAUDE.md` links to that same instruction file. The shared [reminder](reminder.txt) supplies the bstack entry's path and tells the agent to reuse available instructions or reread missing/incomplete instructions. It never contains the full router body and does not inspect conversation transcripts. The pinned Poteto Mode source remains unchanged.

## Repository adapters

- Codex: `.codex/config.toml` activates the project layer; `.codex/hooks.json` subscribes to `SessionStart`, `UserPromptSubmit`, and `SubagentStart`.
- Claude Code: `.claude/settings.json` subscribes to the same events. `SessionStart` also handles source `compact`.
- Cursor: `.cursor/rules/bstack-router.mdc` always applies. `.cursor/hooks.json` injects at `sessionStart` and uses `postToolUse` for the fallback. `sessionEnd` clears headless suppression state; prompt/compaction events are observational. The prompt hook returns only `continue`; it does not pretend that Cursor accepts context there.
- Grok: `AGENTS.md` supplies standing instructions. `.grok/hooks/bstack.json` records the turn ID at `UserPromptSubmit` and injects the reminder once per observed user turn at native `PostToolUse`. The prompt event itself adds no context.
- The bstack router, customized unslop, and verification skill are canonical under `bstack/shared/skills/`, with individual links in each host's skill directory. Imported leaves remain on demand.

Check or install from the repository root:

```bash
python3 bstack/shared/router/install.py
python3 bstack/shared/router/install.py --apply
```

Installation preserves unrelated JSON hooks and refuses conflicting links. It migrates the exact former generated Cursor rule to the bstack entry, but refuses to replace a user-modified rule. No global instructions, personal memories, auth settings, or upstream PStack files are changed by the installer. Commands currently target POSIX shells with `python3` and Git; Windows installation is not verified by this Linux POC.

Codex project trust and hook trust are separate. Review these three commands through `/hooks` before use, including live verification. The harness honors native hook trust and does not bypass it. The local POC's three hooks were reviewed and approved through that UI. Ignoring normal user config prevented project-hook discovery in our initial Codex probe, even though `AGENTS.md` still loaded.

## Verification

```bash
python3 bstack/shared/router/test_hook.py
python3 bstack/shared/skills/verify-bstack/scripts/verify.py doctor
python3 bstack/shared/skills/verify-bstack/scripts/verify.py live
python3 bstack/shared/skills/verify-bstack/scripts/fallback.py
python3 bstack/shared/skills/verify-bstack/scripts/policy.py
python3 bstack/scripts/audit_pstack.py
python3 bstack/scripts/layers.py check
```

The maintainer verifier discovers Codex, Claude Code, Cursor, and Grok on PATH and tests all installed clients by default. Missing clients are listed as skipped. Use `--tools codex grok` for a subset; an explicitly requested missing client is blocked. Supply `--cursor-bin /path/to/cursor-agent` when needed. `doctor` checks discovery and versions. The live command sends test prompts and read instruction content to signed-in providers and spends model usage. Codex probes use `gpt-6-astra` at medium effort; the other clients retain their default models. The probes restrict execution to reading and classification.

Reports separate routing from hook delivery. `pass_with_limits` means routing passed on a client without native per-prompt context injection. An exit code of zero can include that result; inspect the capability fields before asserting full portability. Desktop apps remain outside this iteration.

Grok also scans Claude and Cursor hook configuration. The shared hook recognizes Grok's documented `GROK_HOOK_EVENT` runner marker and ignores invocations of another host's adapter; the native `--host grok` adapter remains active. Grok 1.0.34 emitted parser warnings for the otherwise valid Cursor hook format during testing; diagnostics remain in the evidence. Native after-tool delivery is tested separately from these compatibility warnings.

The hook writes no logs during normal use. With `BSTACK_VERIFY_DIR` set by the harness, it records event/session IDs, source hash, output size, and a random receipt. It never records the incoming prompt or full transcript. The model must echo the current receipt without opening those evidence files. Saved CLI output and observed read calls provide separate evidence of delivery and loading. Hook emission alone is not proof that the client delivered context.

## After-tool fallback

Cursor and Grok use the same reminder text and an atomic SQLite claim keyed by repository, host, conversation, and effective turn. The first eligible tool result emits the reminder; later results in that turn emit nothing. A missing identity produces an explicit diagnostic and no reminder. Native turn fields alone did not work in the tested CLIs:

- Grok 1.0.34 supplies `promptId` at `UserPromptSubmit`, but omitted it from `PostToolUse`. The adapter retains the submitted ID by session and uses it for subsequent tool hooks. A new prompt replaces it, even on a tool-free turn.
- Cursor 2026.09.15-d2fe57e supplies the conversation ID as `generation_id` in headless mode and omits `beforeSubmitPrompt`/`stop` events in our probes. When those two IDs match, the adapter creates a temporary boundary token and clears it on native `sessionEnd`. Sequential resumed CLI invocations then receive fresh tokens. Distinct native generation IDs use the direct path, as expected by Cursor's documented schema; interactive CLI behavior has not been independently verified here.

The small state cache lives at `${TMPDIR:-/tmp}/bstack-router-<uid>/turns.sqlite3` with seven-day expiry. It stores hashed repository/session keys, opaque turn IDs, and timestamps only. `BSTACK_STATE_DIR` overrides its directory for isolated verification. This permits hook execution inside Grok's read-only sandbox without writing project files. Deleting this disposable cache can permit a reminder to repeat. The claim guarantees at-most-once emission for a retained effective turn; it cannot guarantee delivery if a hook fails after claiming or a client drops its output.

Cursor's headless boundary assumes one serial invocation at a time per conversation. A hard kill before `sessionEnd` can leave a stale suppression claim for the first resumed invocation. Concurrent invocations of the same conversation can race with a reset. Grok's retained prompt identity also assumes serial turns per session. These are explicit POC limits, not universal once-per-user-turn guarantees. Separate conversations remain isolated.

This is an **after-tool** reminder: the first tool call and every tool-free response still depend on standing instructions. It does not inspect context, inject the router body, or make routing deterministic. The agent decides whether to reuse or reread the router.

`fallback.py` discovers installed Cursor/Grok CLIs and runs four turns in one conversation per client: two turns with dependent file reads, a tool-free turn, then another turn with dependent reads. It checks fresh echoed after-tool receipts, suppression within each tool turn, new turn identities, zero tool calls on the tool-free turn, and retained routing behavior. Temporary hook evidence is copied into `.bstack/verification/` by the parent verifier. See [the feature contract](../skills/verify-bstack/features/after-tool-reminder.md).

The [2026-09-18 live results](../../audit/router-fallback.md) passed all eight turns, with the router read on turn one only in both conversations. The failed native-ID attempt is retained alongside the passing lifecycle-based run.

Native compaction uses a completed tool-specific live report:

```bash
python3 bstack/shared/skills/verify-bstack/scripts/compact.py --tool claude --report .bstack/verification/<run>/claude/report.json
python3 bstack/shared/skills/verify-bstack/scripts/compact.py --tool codex --report .bstack/verification/<run>/codex/report.json
```

The Claude driver sends native `/compact`; the Codex driver calls local app-server `thread/compact/start`. Both continue the same session afterward. The Codex driver keeps the app-server alive through that next model request because the compact hook runs at that point. A CLI pass is not a desktop UI pass, and synthetic compaction payload tests do not prove native compaction. See the [feature map](../skills/verify-bstack/features/README.md).

## Sources checked

- [Codex lifecycle hooks](https://developers.openai.com/codex/hooks)
- [Codex app-server compaction](https://developers.openai.com/codex/app-server#trigger-thread-compaction)
- [Claude Code hook reference](https://code.claude.com/docs/en/hooks)
- [Cursor hook reference](https://cursor.com/docs/hooks)
- [Cursor CLI parameters](https://cursor.com/docs/cli/reference/parameters)
- [Grok hook reference](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/10-hooks.md)

This POC tests instruction availability and a few routing choices. It does not validate every imported skill, model mapping, delegation tool, full workflow, or plugin distribution format.
