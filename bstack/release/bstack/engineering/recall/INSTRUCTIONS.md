---
name: recall
description: Reconstruct recent work on a named project or topic from scoped agent sessions and current project evidence. Use for catch-me-up and where-did-I-leave-off requests.
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
disable-model-invocation: false
---

# Recall

Give the user a current, compact account of their work. Start with the project and topic they named. Default to the active project and the last seven days if they gave no scope. Use the [session reader](../../shared/session_history.py) to list recent sessions, then open only relevant ones. Do not search unrelated projects. For Amp, confirm the thread belongs to this project and time window before reading it and pass `--allow-unverified-amp`; its list output does not establish either match.

Combine session findings with live Git, PR, ticket, or workspace state when available. A transcript records what an agent reported then; it does not prove what is true now. Cite a session ID or artifact for consequential facts. If the request is to resume one identified chat or handoff, use session-pickup or handoff instead of mining a wider history. If the user already supplied enough context, skip the crawl.

Reply with where things stand, what remains unresolved, and the most useful next move. Name coverage gaps briefly. Recall is read-only and does not create durable memory.
