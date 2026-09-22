---
name: research
description: Investigate a bounded question against primary sources and return a cited finding artifact for a planning or engineering decision.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# Research

Define the question and what evidence would answer it. Use supported background delegation for independent reading so the caller can continue other work. Pass a bounded scope, the relevant source pointers, and [bstack policy](../../shared/router/WORKFLOW.md). If delegation is unavailable, perform the bounded research directly and state that limit; do not claim a background agent ran.

Follow claims to primary sources: official documentation, source code, standards, first-party APIs, or the local records that own the fact. Distinguish observed behavior, documented guarantees, and inference. Include relevant versions or dates for changing facts, conflicting evidence, and unanswered parts. A search snippet is a lead, not the source of record.

Use [workspace access](../../shared/references/workspace.md) to write one concise Markdown finding at `artifacts/research/<question>-<unique-id>.md` beneath the owning private workspace unless the project has an explicit research convention. Cite each substantive claim and include the question, answer, evidence, and remaining uncertainty. A research result does not settle an undelegated product choice.

Return the finding path to the caller. For Wayfinder, the owning session verifies the result and resolves its claimed question with the artifact reference and valid decision authority. Delegating reading does not transfer the caller's claim or authorize external writes. Use [handoff](../../shared/handoff/SKILL.md) when research must continue in another context.
