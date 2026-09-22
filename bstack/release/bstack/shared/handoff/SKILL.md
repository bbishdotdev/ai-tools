---
name: handoff
description: Prepare a durable, concise transfer to a fresh context with current records, decision authority, evidence, and the next action.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# Handoff

Prepare the next session to continue the work, using the user's stated next phase when supplied. Read [workspace access](../references/workspace.md) and [decision authority](../references/decision-authority.md). Write `artifacts/handoffs/<topic>-<unique-session>.md` beneath the owning private workspace. Do not rely on an OS temporary directory for a resumable handoff.

Include only what the receiver needs:

- Goal, active phase, next action, and explicit exclusions.
- Decision owner and exact scope of any delegation, with its grant/confirmation reference. Separate planning permission from implementation or external-delivery permission.
- Owning workspace, project/worktree and branch, relevant commit or dirty-work description, record IDs and read revisions, and accepted spec/answer versions. Identify planning and ticket providers separately.
- Usable selected prototype, launch command, preservation requests, and other artifact references. Keep the selected target available until the receiver can use it.
- Checked evidence, unresolved risks, waits, blockers, and what was only reported or remains unverified.
- The governing router and needed skill paths, plus the proposed model role if configured. Paths and record IDs are the durable pointers; native session IDs are optional locators.

Reference specs, ADRs, commits, diffs, and research instead of repeating their bodies. Exclude credentials, claim tokens, secrets, and unnecessary personal data. Finish with a short startup instruction naming the immediate action and source records to reread.

A prototype-to-production transition requires a fresh context. Other substantial phase changes benefit from one; avoid restarting a small ongoing step merely because the skill name changes. Write the handoff before launching or relinquishing the current context. Release the current claim when pausing or transferring ownership; the receiver must acquire its own.

Use native fresh-session and model selection only when supported and authorized. Verify configured model availability; do not guess a substitute. If launch is unavailable, return the handoff path and the exact action the user must take to start a fresh session and read it. That is a prepared handoff, not a completed transfer. Explicit unattended work requiring automatic launch must report that capability gap in preflight, before starting the dependent workflow.

The receiver reads the governing skills and current records, compares revisions/sources and authority, checks blockers, then acquires its own claim. Stale records trigger reconciliation before work resumes. A handoff is a guide to authoritative records, not permission to ignore newer decisions.
