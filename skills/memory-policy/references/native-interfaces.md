# Memory sync compatibility

Verified on Linux on 2026-09-14. Native-file create, update, deletion, and fresh-session recall passed for Codex and Claude Code in isolated profiles. Cursor uses the user-authorized file bridge with an automatically applied startup rule. Its ordinary native interface remains unverified and is not used. The shared sync command checks every requested destination before writing. A local file readback and a fresh-session recall test are different checks.

| Product | Verified native path | Current qualification |
| --- | --- | --- |
| Codex desktop 0.153.0-alpha.5 | `$CODEX_HOME/memories/memory_summary.md` and `MEMORY.md` | A native-file adapter passed create, update, deletion, and recall in unrelated working directories. Version-sensitive; background consolidation durability is not proven. |
| Codex CLI 0.153.2 | Same configured memory root | The runtime recall probe used the desktop executable. Do not claim a separate CLI runtime test. |
| Claude Code 2.1.261 | A fixed user-level `autoMemoryDirectory`, with `MEMORY.md` and typed topic files | Native-file adapter passed create, update, deletion, and recall in two unrelated working directories. Already-open sessions and background writers were not tested. |
| Cursor 3.19.7 | `~/Work/.agents/memory-sync/cursor/MEMORY.md`, projected into `~/.cursor/rules/personal-memories.mdc` | Explicit file bridge. Config, the recall router, bridge content, generated rule, update, and deletion are checked by the shared helper. This is not native Cursor memory. |

## Codex

Codex normally generates native Markdown under `$CODEX_HOME/memories`, usually `~/.codex/memories`. The `memories` feature must be enabled and `use_memories` must not be false. The activation command enables the memory feature and use of memories. It preserves native generation settings and unrelated configuration.

The native-file probe used a disposable home with `[features] memories = true`. It placed the same synthetic preference in `memory_summary.md` and `MEMORY.md`. Three fresh sessions recalled the original phrase, recalled its replacement from an unrelated working directory, then answered `UNKNOWN` after deletion. The question contained no phrase or memory path. Tools were prohibited and none were called, so recall came from the native injected summary. Authentication was mounted read-only; real memories and configuration were untouched.

Codex's installed consolidation prompt treats edits since its previous memory baseline as authoritative input. This supports a file adapter, but does not prove that its managed entries survive every future consolidation. Official documentation discourages hand editing as the primary control. Recheck after upgrades and distinguish verified foreground recall from unverified background durability. A digest mismatch or missing managed entry requires inspection, not automatic recreation or propagation.

The native external-agent importer is a different interface. It selects entire Claude project collections and preserves their project scope. It is not suitable for synchronizing one approved global preference. No dedicated per-fact CRUD endpoint was found in the app-server protocol.

Sources: [Codex memories](https://learn.chatgpt.com/docs/customization/memories), [native importer](https://github.com/openai/codex/blob/main/codex-rs/external-agent-migration/src/memory_import.rs), [hooks](https://learn.chatgpt.com/docs/hooks).

## Claude Code

Claude supports direct editing and deletion of native Markdown. Its default storage is project-scoped. A fixed absolute user-level `autoMemoryDirectory` makes the native index available across working directories. Each synchronized note uses a topic file with `name`, `description`, and `type: user` frontmatter, linked from the native `MEMORY.md` index.

The isolated probe kept `autoMemoryEnabled: true` and used four fresh sessions. Create was recalled from two unrelated directories, an update returned the replacement phrase, and deletion returned unknown. Traces showed reads of only the native topic during retrieval. Neither the prompt nor global instructions contained the phrase. Production settings and memories were untouched.

Setting a new global directory changes which native index future sessions load. It does not migrate old project memories. Preserve existing files and disclose that they will no longer be the default startup index. Migrating their contents needs review and approval of the specific personal notes. Do not copy project or app facts into global memory.

A separate isolated hook probe verified that an explicit PreToolUse denial blocks a foreground native Write. Background extraction and dreaming could not be naturally exercised under the account's rollout settings. Their custom permission callbacks mean ordinary interactive `ask` prompts cannot be assumed to cover them. Subagent native memory has separate roots. No claim of universal pre-write approval enforcement follows from these tests.

Sources: [audit and edit memory](https://code.claude.com/docs/en/memory#audit-and-edit-your-memory), [storage location](https://code.claude.com/docs/en/memory#storage-location), [hooks](https://code.claude.com/docs/en/hooks#pretooluse-decision-control), [subagent memory](https://code.claude.com/docs/en/sub-agents#enable-persistent-memory).

## Cursor

The installed client has a native user filesystem store under `~/.local/state/cursor/agent-stores/cursor_agent_stores/<user>/files`. Its existence alone does not establish that chats mount, ingest, or recall it.

Read-only inspection found these cached evaluated rollout values: `agent_store_sync_client=false`, `agent_store_principal_local_mounts=false`, and `agent_store_local_user_mount=true`. Installed extension code starts the ordinary desktop store harness only when the sync-client gate passes. Without the harness, `getMountedAgentStores` returns no stores. This is an inference from a cached bootstrap plus installed code, not a live feature-gate query or a conclusion about every cloud session.

No public setting to enable that rollout or native memory CRUD tool was found. Do not modify private databases, invoke undocumented KnowledgeBase RPCs, or override rollout gates. The runtime's durable `MEMORIES.md` instructions belong to an automation principal mount, not ordinary global desktop memory. SDK-supplied local stores also do not establish ordinary desktop recall.

The installed Cursor 3.19.7 client explicitly supports user file rules: its rule service creates them under the local user home at `.cursor/rules`, and its Customize UI lists user file rules separately from account User Rules. This is local client support; it does not synchronize rule files to cloud sessions.

The user authorized finishing the file bridge. Approved notes are synchronized to `~/Work/.agents/memory-sync/cursor/MEMORY.md`. The shared helper renders managed bridge entries directly into `~/.cursor/rules/personal-memories.mdc` with `alwaysApply: true`. Fresh chats receive that approved text as rule context. The policy router sends ordinary recall directly to the loaded facts and retains a bridge read only for missing context. The bridge config and exact policy-router bytes participate in each reviewed write plan. The generated memory rule is an additional reviewed output and receives the same byte comparison and file readback as the source copies. Unrelated projection drift blocks a write; retrying the same approved target can complete a partially written projection. Native Cursor features are left intact. Label its results as bridge readback, never native memory verification.

Cursor's global User Rule routes memory operations to this skill. The user confirmed adding it through the UI. The installer also generates the local user rule `~/.cursor/rules/memory-policy.mdc`. The local setup includes an always-applied generated memory rule, a separate policy router, and a read-only `beforeSubmitPrompt` hook. These local user rules do not provide remote or cloud filesystem access. The saved global User Rule remains an additional policy router.

Sources: [Cursor rules and alwaysApply](https://cursor.com/docs/rules), [Cursor CLI parameters](https://cursor.com/docs/cli/reference/parameters), [Cursor SDK](https://cursor.com/docs/sdk/python), [Cursor APIs](https://cursor.com/docs/api), [hooks](https://cursor.com/docs/hooks), [skills](https://cursor.com/docs/skills).

## Shared helper verification

The actual Cursor Agents window was tested in a fresh local `family-chef` chat with only “What is my memory test phrase?” After a normal Reload Window, it returned the approved phrase in about one second with zero tool calls. A fresh chat before that reload still used the workspace's cached rule discovery and read the files. Installed code confirms ancestor rules are cached while the workspace watcher watches its own root. The context hook addresses that refresh gap before each prompt.

The three-destination helper passed disposable create, update, and deletion using its default destination set. All six files, including Cursor's generated rule, matched after each operation; inspection reported consistent copies followed by absence after deletion. Repeating create, delete, and activation made no changes. Unmanaged bridge text stayed intact and was excluded from the generated rule. Cursor's bridge config and recall router are checked and bound into each plan; its generated rule is a reviewed output with a source dependency checked before writing.

Production activation completed with all three backends ready, all nine shared links correct, and the generated Cursor startup rule correct. All 17 preexisting native memory files retained their hashes. Configuration comparisons confirmed only requested activation settings changed; native generation settings and Claude hooks were preserved. Changed configuration/router files have private local backups. A repeated activation preview reported no changes. No personal notes were added by activation.

The delivered helper was separately exercised through its CLI against disposable native profiles. It generated both Codex files and Claude's native topic and index, updated the same note ID, and deleted it. Six fresh native sessions passed: both apps returned the original synthetic phrase after create, the replacement phrase after update in an unrelated working directory, and `UNKNOWN` after deletion. All six used zero tools; the value came from native context. The prompts contained neither the phrase nor a file path. Hashes of 17 real configuration, routing, and native-memory files remained unchanged.

The focused local suite covers CLI behavior, exact byte preservation, idempotent retries, stale plans, invalid configuration, file collisions, index placement, cooperating locks, concurrent native/configuration edits, partial failures, and final readback. Run it from the source checkout with `python3 -B -m unittest discover -s skills/memory-policy/tests -v`. These deterministic tests complement the runtime probes; they do not substitute for native recall after a client update.

## Synchronization and approval limits

The shared command applies the exact approved operation to the two native adapters and the configured Cursor bridge. It cannot make three products commit atomically. Preflight all destinations, preserve unrelated content, compare against the reviewed file revision, then read each changed file back. Report any partial failure and inspect before retrying.

The Cursor context hook reads the current bridge and generated rule, verifies they agree, and returns approved facts as prompt context. It makes no memory writes and does not supply approval for any change. Missing or inconsistent copies produce no memory content; ordinary prompts remain allowed. Its JSON response stays within 9,000 UTF-8 bytes. Larger snapshots are not truncated; memory-specific questions use a direct bridge read as the fallback.

Conversational approval is still required. A plan digest binds exact input, destinations, and observed files; it is not proof that a human approved the operation. Native writers do not honor the synchronizer's lock. No watcher, background approval hook, or automatic propagation of native-only edits is installed. A watcher would observe an unapproved write only after it happened.

Fresh-session recall is the acceptance test after activation. Create one explicitly approved disposable personal note, ask for it in unrelated fresh chats without supplying the value or policy path, update it and repeat, then approve deletion and verify fresh chats no longer recall it. The verification value should appear only in the chosen stores, with Cursor using its labeled bridge. Clear provenance matters because a transcript or an instruction-file copy can otherwise make a failed native adapter look successful.
