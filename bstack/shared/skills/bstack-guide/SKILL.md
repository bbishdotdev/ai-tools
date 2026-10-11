---
name: bstack-guide
description: Explain how to use bstack, choose a starting skill, or understand its setup, routing, workspace, and memory. Use when someone asks how bstack works or where to start.
metadata:
  author: Brenden Bishop
---

# bstack guide

Help the person use bstack for the work they actually have. This is a teaching skill: explain and demonstrate, but don't install, change modes, create work items, or start an engineering workflow just because the guide was selected.

For a general introduction, follow the short [walkthrough](references/walkthrough.md), then offer a few optional starting points. Use familiar developer journeys to show how planning, engineering, PR work, and continuity fit together. Explain that the seven-rule project baseline and `unslop` apply without auto mode; named skills work directly; `poteto-mode` chooses an engineering workflow when invoked; and `bstack-auto` opts ordinary engineering prompts into that routing. Planning, implementation, and PR work can start independently. Make clear that a guide request doesn't turn on auto mode.

For a specific question, answer that slice first. Read [common routes](references/routes.md) only when examples or a walkthrough would help. For exact setup, limits, or commands, read the installed package's `README.md` or relevant skill from its `index.json` rather than relying on this overview. Resolve those files from the package containing this skill, not from the generated discovery entry. Check the local `doctor` result only when the person asks about their installation; don't imply a documented capability is configured or working here.

Use a small diagram or concrete example if it clarifies the path. Keep the first answer short and let the person choose where to go deeper. If they ask to try a workflow, use its actual skill and honor its own scope and authorization. An explanation of `review-pr`, for example, does not publish a review.
