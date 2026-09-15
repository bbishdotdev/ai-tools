---
name: memory-policy
description: Review, approve, and coordinate personal native memories across Codex, Claude Code, and Cursor. Use before remembering, updating, forgetting, migrating, or synchronizing durable user preferences. Project knowledge belongs in project instructions, docs, or skills.
---

# Memory policy

Keep each product's native memory system. This skill governs memory operations; it is not a replacement memory store.

## Before a memory change

1. Classify the proposed content. Memories may contain personal facts, agent behavior preferences, and general process or operating preferences. App architecture, repository commands, environment setup, debugging discoveries, and project decisions belong in the relevant project rules, `AGENTS.md`, skill, or documentation. Route them there under the ordinary task authorization.
2. Show the exact addition, old/new text for an update, or exact item for deletion. Name the intended native destinations: Codex, Claude Code, and Cursor. Obtain explicit approval from the user for that content and operation before writing anywhere. A direct request to remember or forget exact content can supply approval; do not ask twice when the scope is already clear. Approval to implement a task or this policy does not approve memories inferred from it. Examples of possible preferences are not instructions to save those preferences.
3. Keep an unapproved candidate in the current conversation. Do not save it in a native memory, proposal file, persistent queue, rule, or skill to work around approval. Ordinary session transcripts are outside this workflow.
4. Check the native interfaces before changing a destination. Read [native-interfaces.md](references/native-interfaces.md) and run `python3 ~/.agents/skills/memory-policy/scripts/status.py` for local configuration and installation status. Recheck compatibility after product updates. File presence does not prove native recall.

## Apply approved content

Use the shared `scripts/sync.py` command for the verified Codex and Claude native-file adapters. Run its help for the current command syntax. The default destination set is all three products; an unavailable destination stops preflight before any write. See the compatibility reference for the tested client versions and recall limits. Keep the same approved meaning across products; format differences must not add facts or broaden the preference.

Preflight all destinations. If one lacks a verified native interface, explain the specific gap and keep the operation pending in the conversation. Do not silently save a partial copy or substitute User Rules, `AGENTS.md`, a shared text file, or a private database/RPC. A user can explicitly authorize a partial save after seeing the missing destinations; report it as partial.

Preview the operation with the helper before applying it. Keep a stable note ID for later updates and deletion. Review the exact old/new content, destination paths, and plan digest against the user's approval, then apply that unchanged plan. A digest binds the operation and observed files; it is not evidence of human consent. A changed plan needs review before retrying. Never use an apply option to bypass the conversational approval requirement.

After writing, inspect every destination. Report physical file readback separately from fresh-session native recall. Retry only the unchanged approved meaning and destinations; inspect existing IDs and content first to avoid duplicates. Updates and deletions need the same approval and readback as additions. Never resurrect a deleted memory from a stale copy. If an operation partially fails, report the written copies and pending work; do not pretend separate native files commit atomically.

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

For an explicitly approved partial save, place `--destinations codex,claude` before the command. Never add that option merely to work around a failed all-three preflight. `--home` is for disposable test profiles. The helper manages only its own marked entries and topic files; it does not migrate or remove arbitrary preexisting memories.

## Background writers and limits

Apply this policy when extracting, consolidating, dreaming, or maintaining subagent memory whenever this instruction is available. A hook must check human approval for the exact operation; an agent-supplied `approved: true` is not evidence. Generic permission prompts are not a substitute for reviewing the memory content.

A skill cannot guarantee control over internal background writers that never receive it. A watcher observes writes after the fact. Report unapproved drift without propagating it or automatically deleting it. Do not claim pre-write enforcement without testing that specific writer and its failure paths.

Do not disable native memory or silently change generation settings to make enforcement appear complete. If enabled native generation and mandatory approval cannot both be enforced, disclose the product limitation. Installation of this policy alone is not evidence that native synchronization works.
