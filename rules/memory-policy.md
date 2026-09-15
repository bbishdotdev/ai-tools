# Shared memory policy

Before creating, changing, deleting, extracting, or synchronizing durable memories, read and follow `~/.agents/skills/memory-policy/SKILL.md`.

Require the user's explicit approval of the exact memory change. Keep memories limited to personal facts, agent behavior, and general operating preferences. Use the shared sync command to apply each approved change across Codex native memory, Claude native memory, and Cursor's configured file bridge. Project or app knowledge belongs in project instructions, documentation, or skills.

Keep native memory enabled. Do not ask again for implementation or synchronization already authorized by the user. An explicit request to remember exact content supplies approval for that memory. This policy does not claim control over background writers that do not load it.
