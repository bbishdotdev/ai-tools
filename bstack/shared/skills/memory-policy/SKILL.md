---
name: memory-policy
description: Approve and synchronize durable personal memory writes across Codex, Claude Code, and Cursor. Use for creating, updating, deleting, migrating, or synchronizing memories. Do not invoke for ordinary recall or questions about an already stored preference.
---

# Memory policy

Synchronize approved personal memories with one shared command. Codex and Claude use their native memory files. Cursor uses the explicitly authorized file bridge because its ordinary desktop native interface is unavailable in the tested setup. Keep each product's native features enabled. Do not reopen the bridge decision or ask for setup approval again.

## Recall

For a question about an already stored memory, answer directly from supplied context. Do not start the approval workflow, read compatibility references, or run sync status. If this skill was invoked for ordinary recall, return to answering the question. If the fact is missing from context, read the relevant native memory source or Cursor bridge once. Investigate sync only when the user asks for diagnosis or stored copies conflict. Do not narrate routine retrieval or explain storage provenance unless asked.

Cursor receives approved personal notes through `~/.cursor/rules/personal-memories.mdc` and a read-only `beforeSubmitPrompt` hook that supplies the current verified snapshot. The hook avoids cached rule discovery in already-open workspaces and supersedes older snapshots after updates or deletions. The bridge remains the source. Reading it with an agent tool is a fallback, not a startup requirement.

## Before a memory change

1. Classify the proposed content. Memories may contain personal facts, agent behavior preferences, and general process or operating preferences. App architecture, repository commands, environment setup, debugging discoveries, and project decisions belong in the relevant project rules, `AGENTS.md`, skill, or documentation. Route them there under the ordinary task authorization.
2. Show the exact addition, old/new text for an update, or exact item for deletion. Name the destinations: Codex native memory, Claude native memory, and Cursor's file bridge. Obtain explicit approval from the user for that content and operation before writing anywhere. A direct request to remember or forget exact content can supply approval; do not ask twice when the scope is already clear. Approval to implement a task or this policy does not approve memories inferred from it. Examples of possible preferences are not instructions to save those preferences.
3. Keep an unapproved candidate in the current conversation. Do not save it in a native memory, proposal file, persistent queue, rule, or skill to work around approval. Ordinary session transcripts are outside this workflow.
4. Check the native interfaces before changing a destination. Read [native-interfaces.md](references/native-interfaces.md) and run `python3 ~/.agents/skills/memory-policy/scripts/status.py` for local configuration and installation status. Recheck compatibility after product updates. File presence does not prove native recall.

## Apply approved content

Use `scripts/sync.py` for every approved create, update, or deletion. All three products are the default destinations. The installed adapters write Codex native files, a user-wide Claude native directory, and Cursor's bridge. The same reviewed operation refreshes Cursor's generated `personal-memories.mdc`, and the read-only context hook supplies that current approved text before each prompt. Keep the same approved meaning across products; format differences must not add facts or broaden the preference.

Preflight all destinations. If configuration has drifted or a destination is unavailable, repair the authorized installation when possible and retry the same approved operation. Do not silently save a partial copy or switch to private databases/RPCs. Cursor's configured bridge is an intentional installed destination, not a missing native adapter. A reduced destination set requires explicit approval of a partial save.

Preview the operation with the helper before applying it. Keep a stable note ID for later updates and deletion. Review the exact old/new content, destination paths, and plan digest against the user's approval, then apply that unchanged plan. A digest binds the operation and observed files; it is not evidence of human consent. A changed plan needs review before retrying. Never use an apply option to bypass the conversational approval requirement.

After writing, inspect every destination. Report physical file readback separately from fresh-session native or bridge recall. Retry only the unchanged approved meaning and destinations; inspect existing IDs and content first to avoid duplicates. Updates and deletions need the same approval and readback as additions. Never resurrect a deleted memory from a stale copy. If an operation partially fails, report the written copies and pending work; do not pretend separate native files commit atomically.

Leave existing memories intact until the user approves the concrete migration, correction, or removal. Finding a project-specific memory does not authorize deleting it.

## Shared command

Use the installed script, so Codex, Claude, and Cursor invoke the same implementation:

```bash
python3 ~/.agents/skills/memory-policy/scripts/sync.py status
python3 ~/.agents/skills/memory-policy/scripts/sync.py inspect NOTE_ID
python3 ~/.agents/skills/memory-policy/scripts/sync.py set NOTE_ID --text 'EXACT APPROVED TEXT'
python3 ~/.agents/skills/memory-policy/scripts/sync.py delete NOTE_ID
```

`set` and `delete` only preview. After checking the preview against the user's approval, repeat the unchanged command with `--apply-plan PLAN_SHA256` using the returned digest. Quote text safely or use a subprocess argument list. `set` creates or updates the same stable ID. The helper accepts up to 4096 UTF-8 bytes per note; this is a helper limit, not a product limit.

For an explicitly approved partial save, place `--destinations codex,claude` before the command. Never add that option merely to work around a failed all-three preflight. `--home` is for disposable test profiles. Do not edit `personal-memories.mdc` by hand. It is generated from the managed bridge entries; arbitrary text outside those entries is not copied into it. The helper manages only its own marked entries and topic files; it does not migrate or remove arbitrary preexisting memories. Run `scripts/install.py --activate-sync --apply` to repair the already-authorized installation if needed; preview first and preserve unrelated configuration. Native generation settings must remain unchanged.

## Background writers and limits

Apply this policy when extracting, consolidating, dreaming, or maintaining subagent memory whenever this instruction is available. A hook must check human approval for the exact operation; an agent-supplied `approved: true` is not evidence. Generic permission prompts are not a substitute for reviewing the memory content.

The Cursor context hook only reads approved synchronized content for recall. It does not write, approve, or propagate memories. A skill cannot guarantee control over internal background writers that never receive it. A watcher observes writes after the fact. Report unapproved drift without propagating it or automatically deleting it. Do not claim pre-write enforcement without testing that specific writer and its failure paths.

Do not disable native memory or silently change generation settings to make enforcement appear complete. If enabled native generation and mandatory approval cannot both be enforced, disclose the product limitation. Installation of this policy alone is not evidence that native synchronization works.
