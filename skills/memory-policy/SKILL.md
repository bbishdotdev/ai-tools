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

Use only supported native interfaces that have passed create, readback, update, deletion, and global-scope checks. Keep the same approved meaning across all three products; format differences must not add facts or broaden the preference. Bind approval to the operation, exact revision, and destinations. A changed proposal needs renewed approval.

Preflight all destinations. If one lacks a verified native interface, explain the specific gap and keep the operation pending in the conversation. Do not silently save a partial copy or substitute User Rules, `AGENTS.md`, a shared text file, or a private database/RPC. A user can explicitly authorize a partial save after seeing the missing destinations; report it as partial.

After an authorized write, read it back through the native interface. Report each destination as verified, failed, or pending. Retry only the unchanged approved operation; inspect existing native IDs and content first to avoid duplicates. Updates and deletions need the same approval and readback as additions. Never resurrect a deleted memory from a stale copy. If an operation partially fails, report the written copies and pending work; do not pretend three separate products commit atomically.

Leave existing memories intact until the user approves the concrete migration, correction, or removal. Finding a project-specific memory does not authorize deleting it.

## Background writers and limits

Apply this policy when extracting, consolidating, dreaming, or maintaining subagent memory whenever this instruction is available. A hook must check human approval for the exact operation; an agent-supplied `approved: true` is not evidence. Generic permission prompts are not a substitute for reviewing the memory content.

A skill cannot guarantee control over internal background writers that never receive it. A watcher observes writes after the fact. Report unapproved drift without propagating it or automatically deleting it. Do not claim pre-write enforcement without testing that specific writer and its failure paths.

Do not disable native memory or silently change generation settings to make enforcement appear complete. If enabled native generation and mandatory approval cannot both be enforced, disclose the product limitation. Installation of this policy alone is not evidence that native synchronization works.
