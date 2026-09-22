---
name: prototype
description: Build and iterate on disposable prototypes for design or behavior questions, preserving the chosen reference for a clean implementation handoff.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# Prototype

Read and follow the approved [prototype workflow](WORKFLOW.md). It owns framing, construction, verification, iteration, selection, and cleanup. Load only its applicable UI or logic guide.

Use [decision authority](../../shared/references/decision-authority.md) for the caller's scope and who selects the result. Use [workspace access](../../shared/references/workspace.md) for a persistent session directory at `artifacts/prototypes/<session>/` beneath the owning private workspace. An isolated application worktree may hold runnable code; keep its path and launch instructions with that session.

When a planning question called this workflow, return its accepted answer and usable artifact references to [Wayfinder](../../sdlc/wayfinder/SKILL.md). Do not silently resolve the question or create an ADR because a variant was preferred.

Before authorized production implementation, prepare a [handoff](../../shared/handoff/SKILL.md) and transfer to a fresh context running [implement](../implement/SKILL.md). Preserve the selected target until the receiver has the needed reference and reusable pieces. If the host cannot launch that context, leave a usable handoff and report the needed launch step. Never substitute an in-place continuation for an explicitly required unattended fresh-session transfer.
