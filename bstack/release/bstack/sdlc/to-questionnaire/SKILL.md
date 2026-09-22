---
name: to-questionnaire
description: Draft an asynchronous questionnaire for someone who holds facts or decisions the current discussion lacks.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# To questionnaire

Ask about the recipient and the required result, not questions only that recipient can answer. Reuse known context. In one exchange establish the recipient's role, expertise, and relationship to the user. In another, establish the facts or decisions the user needs back. Combine or skip exchanges when the answers are already clear.

Draft a Markdown questionnaire with its purpose, sender/recipient, how answers will be used, and a short context paragraph. Include the agreed deadline and effort if known; do not invent them. Say partial answers and explicit uncertainty are useful.

Order questions by importance and group them by theme when useful. Each question covers one idea with an answer space. Add a brief reason only where the intent might otherwise be missed. End with a place for missing context the recipient thinks matters. Check that every requested fact or decision is covered.

Use [workspace access](../../shared/references/workspace.md) to save the artifact at `artifacts/questionnaires/<topic>.md` under the owning private workspace, or the user's explicit destination. Return the path and, when relevant, link it from the waiting planning question. Drafting does not authorize sending it. Resume from the answers through the caller's decision workflow; a returned document is not automatic approval of every suggestion.
