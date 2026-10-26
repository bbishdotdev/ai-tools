---
name: automate-me
description: Turn recurring working preferences in scoped agent sessions into a small, portable skill or project rule. Use when someone asks to capture how they work or update their personal mode.
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# Automate me

Turn repeated corrections and preferences into something an agent can follow. Start with the user's stated preferences. Ask which project and time window to inspect before reading other sessions. Use the bundled [session reader](../../shared/session_history.py) to list and selectively read Codex, Claude Code, Cursor, Grok, and available Amp sessions. Local readers constrain results to the selected project. Amp's thread list cannot yet prove a project or time match, so confirm selected thread IDs before opening them and pass `--allow-unverified-amp` when reading. Report missing providers rather than claiming a complete history.

Look for patterns across sessions, not one-off requests. Show the proposed rules and the evidence for each. Choose the smallest durable home: an existing project instruction for project behavior, a task skill for a repeated procedure, or personal memory for a stable personal preference. Don't create a new `-mode` skill when a short addition to an existing one suffices. Do not copy raw transcripts into the repository or generated skill.

When personal memory is the destination, read the installed memory policy and obtain approval for the exact change before writing. For a project skill, use the host's skill authoring capability or BStack's authoring playbook. Put portable skill files under `.agents/skills`, then use BStack setup to bind selected hosts. Keep the resulting skill short, test discovery in the selected host, and present the draft before landing it.

The output is a proposed change with its destination and evidence. Reading sessions does not itself authorize publishing or writing personal memory.
