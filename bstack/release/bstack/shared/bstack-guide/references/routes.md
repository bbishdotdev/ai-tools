# Common routes through bstack

These are examples, not a required sequence. Choose only the steps that help with the current request, and resolve the selected skill through the installed `index.json`.

| What the person wants | Useful starting point |
| --- | --- |
| Understand existing code | `how` for how it works; `why` for the reason behind behavior; `teach` for a fuller explanation; `bro` only to restate the last answer more plainly. |
| Fix a bug or build a clear feature | State the task normally with auto mode on, invoke `poteto-mode` for manual engineering routing, or use `implement` for an accepted plan. |
| Shape an idea | `grill-me` for questions, `grill-with-docs` when source material matters, or `wayfinder` when several decisions need a persistent map. |
| Compare a product or UI direction | `prototype` for disposable variants and iteration; a choice can then move through `handoff` to a clean implementation context. |
| Turn decisions into buildable work | `to-spec` for accepted scope; `to-tickets` when slices and a board help. Either can be skipped when the request is already clear. |
| Work on a PR | `to-pr` to prepare it, `review-pr` for independent review, and `resolve-pr` to assess feedback on the author's side. Each can be used on its own. |

The local workspace app and CLI share Wayfinder maps, specs, and tickets. They work offline by default. GitHub PR operations are separate; a local ticket is not silently posted to GitHub, Jira, or Linear. `review-pr` has additional CLI and authentication needs. Check its own instructions before promising a run.

Shared personal memory is optional and separate from project installation. `setup-bstack` previews it before changing user-wide settings. The project baseline in `AGENTS.md` and `CLAUDE.md` is not personal memory.

To teach a full journey, pick one realistic example and pause at each meaningful decision: what is known, what needs a person to decide, what artifact survives, and whether a fresh context would help. Don't portray planning as a gate before every bug fix, or a ticket as a prerequisite for implementation.
