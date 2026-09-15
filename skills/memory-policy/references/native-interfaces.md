# Native memory compatibility

Verified 2026-09-14 on Linux. Recheck after client updates. The installed package provides a shared policy, an installer, and a read-only status helper. No native sync adapter, approval hook, daemon, or watcher is installed. Policy links alone do not prove that background writers obey them.

| Product | Evidence | Qualification for automatic global sync |
| --- | --- | --- |
| Codex desktop 0.153.0-alpha.5 | Isolated native import, repeat, update, and source-file deletion succeeded for project resources. | Fails the required scope and selection criteria. The importer selects entire project collections and preserves project scope. Background consolidation and global recall were not proven. |
| Codex CLI 0.153.2 | Generated protocol exposes the same memory migration shape. | Runtime import was tested with the desktop executable only. No per-fact approval or general native memory CRUD interface was found. |
| Claude Code 2.1.261 | Isolated native Write succeeded with a non-denying hook and was blocked by explicit PreToolUse denial. | Foreground denial works. Background extraction/dream coverage and an approval-bound write helper remain unproven. |
| Cursor 3.19.7 | Runtime customization UI and command/settings search exposed no native Memories management surface. | No supported native memory read/write/update/delete interface verified for the current account. Do not substitute the User Rules UI. |

## Codex

Native files are generated under `$CODEX_HOME/memories` (normally `~/.codex/memories`). The background extractor is independent of ordinary conversational skill selection. The installed feature listing initially reported `memories = false` and `external_agent_memory_import = false`; this policy installation does not change those settings. Do not report that native memory was enabled by this installation.

The app-server protocol provides experimental `externalAgentConfig/detect` and `externalAgentConfig/import`. Select `migrationSource: "claude-code"`. A `MEMORY` item's `details.memory` contains project keys, not paths to individual memory files. Detection requires a reliable project working directory recovered from a source session.

The disposable probe demonstrated that a second memory file in the selected project was also imported, even though a single-fact approval would not cover it. Repeating import created no duplicate files. Re-import reflected a source update and removed a deleted source file. These are resource synchronization results only. No authenticated native consolidation or fresh-session recall was tested.

Import creates `memories/extensions/external_agent_import/resources/<project-key>/scope.json` plus the project files. Its consolidation instructions preserve scope and prohibit promoting project content into global user preferences. Changing Claude to a global `autoMemoryDirectory` also falls outside the importer's discovery of `projects/*/memory`. Do not fabricate a project or edit Codex's generated files to pretend that this is a global per-fact interface.

Sources: [Codex memories](https://learn.chatgpt.com/docs/customization/memories), [native importer](https://github.com/openai/codex/blob/main/codex-rs/external-agent-migration/src/memory_import.rs), [source discovery](https://github.com/openai/codex/blob/main/codex-rs/external-agent-migration/src/memory.rs), [hooks](https://learn.chatgpt.com/docs/hooks).

## Claude Code

Supported native Markdown normally lives in `~/.claude/projects/<scope>/memory/`, with a `MEMORY.md` index and topic files. `autoMemoryDirectory` can redirect future native memory to a user-wide directory. It does not migrate existing files. Persistent subagents have additional user, project, and local roots. This installation leaves all these settings and files intact.

The isolated foreground probe recorded a PreToolUse Write event. With explicit denial, no native file or PostToolUse event appeared; a non-denying control produced both the file and PostToolUse event. The account's background extraction/dream rollout settings prevented naturally exercising those writers. Their custom permission callbacks also mean ordinary interactive `ask` behavior cannot be assumed to cover them. No production hook is installed on the strength of the foreground test alone.

An `ask` hook also blocked the isolated noninteractive foreground run. This does not prove that the background callback will honor `ask`.

The control wrote to the native directory but serialized line breaks literally, so its frontmatter was not validated. This was a path-level permission test, not a proof of native indexing or recall.

Sources: [memory storage](https://code.claude.com/docs/en/memory#storage-location), [hooks](https://code.claude.com/docs/en/hooks#pretooluse-decision-control), [persistent subagent memory](https://code.claude.com/docs/en/sub-agents#enable-persistent-memory).

## Cursor

Current installed source distinguishes generated knowledge-base records from User Rules. Its private knowledge-base RPCs are not a supported native-memory integration. The current public API documentation does not provide a native-memory CRUD endpoint. Absence of a local memory directory says nothing about server-held state.

An isolated `--user-data-dir` UI probe unexpectedly connected to the existing account's Agents window. Only UI inspection was performed, and the probe process was closed. Do not assume that flag isolates Cursor Agents state. A future mutation probe needs stronger isolation or a separately authorized account session.

Use Cursor's global User Rules UI for the short router from `rules/memory-policy.md`. Installed source discovers `.cursor/rules` through workspace ancestors. The installer generates `~/.cursor/rules/memory-policy.mdc` from the canonical router for projects beneath the home directory. It does not establish coverage for projects elsewhere. Global skill links are separate from this always-applied router. A cloud or remote agent also needs access to the shared skill; local installation does not install it on other hosts.

The authorized attempt to add the global User Rule through the supported UI could not reach a save. Temporary windows repeatedly exited before the editor opened; the original Cursor instance was preserved. The global User Rule remains pending. Add the canonical router through Customize → Rules → User → New and verify its text. The local generated rule is already installed for home-directory workspaces.

Sources: [Cursor APIs](https://cursor.com/docs/api), [hooks](https://cursor.com/docs/hooks), [skills](https://cursor.com/docs/skills), [historical native memory release](https://cursor.com/changelog/1-2).

## Criteria before adding a writer

Require observable native create, readback, update, deletion, and recall from an unrelated project. Verify that repeated application does not duplicate content, that every imported fact is approved, and that native consolidation does not discard approved content or propagate unapproved content. Test foreground, background, and subagent writers separately. A hook failure or unavailable product must have an explicit outcome. Do not expand an approval when retrying a failed destination.
