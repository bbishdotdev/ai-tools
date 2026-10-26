---
name: reflect
description: Review an agent session for recurring workflow lessons and propose focused improvements to existing skills or checks. Use when the user asks to reflect on how the work went.
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
disable-model-invocation: false
---

# Reflect

Review the current session or the sessions the user names. Use the [session reader](../../shared/session_history.py) only when that history is available and in scope. For Amp, confirm the thread belongs to the selected project before passing `--allow-unverified-amp`. An in-context conversation summary is a valid narrower source when a transcript is unavailable. Keep raw transcripts out of the resulting skill and repository.

Separate evidence-backed recurring lessons from one-off mistakes. For each accepted candidate, ask whether an existing check, script, project instruction, or skill should change. Prefer a structural check when prose repeatedly fails. Multiple independent reviewers are useful when the host can actually provide them; inherit the host's supported agents and model choices rather than assuming Cursor `Task` or fixed model names. Say when the review used one model or incomplete history.

Show proposed edits and rejected ideas. If the user already authorized the project change, make the smallest edit, validate it, and report what changed. Use the installed memory policy for any personal-memory proposal and get approval for its exact content. Do not file external tickets automatically.
