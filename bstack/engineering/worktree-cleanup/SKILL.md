---
name: worktree-cleanup
description: Audit Git worktrees and reclaim confirmed-unused checkouts without losing local work. Use when asked to clean stale worktrees or recover disk space.
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# Worktree cleanup

Run the bundled [read-only audit](scripts/audit.py) for the repository. It lists Git worktrees and checks branch, local changes, ignored files, and unpushed commits. It does not declare a checkout safe to delete. Compare candidates with active agent sessions, pinned chats, running processes, and any worktree attachments the host exposes. A missing transcript is unknown usage, not proof that nobody needs the worktree.

Show the exact paths proposed for removal and why. Keep the primary checkout, active sessions, dirty worktrees, unpushed commits, and uncertain candidates. Before deletion, obtain approval for the exact paths. Use `git worktree remove` without `--force` on confirmed clean paths; verify Git's list afterward. Never use `rm -rf` as a fallback for a failed worktree removal. Do not delete simulators, caches, or unrelated directories as part of this skill.
