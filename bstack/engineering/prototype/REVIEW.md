# Prototype design

The user approved this bstack workflow after the prototype grilling and instruction review. [WORKFLOW.md](WORKFLOW.md) owns the shared lifecycle, with conditional [UI](references/ui.md) and [logic](references/logic.md) guides. Runtime activation awaits the shared handoff and execution-session contract; this file is not a discoverable `SKILL.md`.

## Structure and context

The workflow owns one prototype session from the question through refinement and cleanup. The two artifact guides describe how to build the selected kind of experiment. They do not repeat decision authority, variant counts, verification, or cleanup.

The normal instruction load is the shared entry and whichever guide the question needs. A measured experiment needs only the entry. A task involving both visual and domain behavior can need both guides. This review and the upstream sources are maintainer material, not runtime prerequisites.

PStack's principles shaped these choices:

- [Foundational thinking](../../upstream/pstack/skills/principle-foundational-thinking/SKILL.md): one owner for session state and lifecycle, with separate workspaces for concurrent experiments. No new persistent state schema is needed to draft this workflow.
- [Redesign from first principles](../../upstream/pstack/skills/principle-redesign-from-first-principles/SKILL.md): organize around the user's review loop. Neither upstream entry wraps or calls the other.
- [Guard the context window](../../upstream/pstack/skills/principle-guard-the-context-window/SKILL.md): keep rules needed on every invocation in the entry and load artifact-specific details only when relevant. No recurring reads of this rationale or the source comparison.

## Source comparison

| Concern | Adopted source behavior | bstack choice |
| --- | --- | --- |
| Purpose | PStack's bounded experiment; Matt's question determines the artifact | One shared lifecycle for SDLC and engineering callers |
| Workspace | PStack isolates experiments; Matt shows UI in its real application | Existing features in a disposable checkout; new concepts in a standalone scratchpad |
| UI | Matt's structural alternatives, existing components, and comparison controls | Five options by default; keep the established visual system; no universal web-only control requirement |
| Logic | Matt's visible state, pure model, free exploration, and repeatable scenarios | Use the smallest suitable demo; keep PStack's script path for empirical questions |
| Verification | PStack runs the experiment and captures direct observations | Verify each presented variant; evidence stays temporary |
| Feedback | Both support comparison; Matt describes combining alternatives | An explicit refinement loop before production handoff |
| Retention | Matt archives every prototype and its rationale on a branch | Retain unfinished or explicitly saved work; no mandatory archive, ticket, ADR, or rationale |
| Implementation | PStack hands off for the real build; Matt identifies reusable logic | Carry useful pieces through normal engineering review and tests; clean up after the reference has transferred |

The detailed product choices are in the [integration review](../../sdlc/integration-review.md). This maintainer record describes the reusable skill; consumer prototyping sessions do not create a copy of it.

## Integration boundary

[Root attribution](../../../ATTRIBUTION.md) owns source credits, revisions, and notices. Before activation, register the reviewed source bases in [layers.json](../../layers.json) and connect both workflow callers to this entry. Source update tooling does not yet flag this unregistered workflow. The source registry supports one upstream per record, so the two source relationships need separate records.

## Review and activation checks

Review the entry's behavior with these cases before wiring it into the runtime:

- An existing branded application gets five distinct options in an isolated copy, preserving its visual system.
- An explicit request for four options produces four; a request for one combined revision produces one revision.
- A single interactive flow works, while a timing question can use a small script.
- A completed measurement-only task can clean up after delivering its result, unless review, implementation, or a preservation request still needs its artifacts.
- Combination and refinement requests stay in prototyping and get verified again.
- Paused work and saved references remain available. A final selection without implementation scope remains available too.
- An authorized final build receives its reference before disposable resources are removed. Saved or unrelated work survives cleanup.
- A normal session requires no external tracker, model-role setup, permanent report, or justification from the user.

Structural checks and instruction review do not prove live execution. Cross-CLI runs and the full prototype-to-implementation sequence belong to the activation step. Cross-model autonomous grilling remains a separate adapter requirement; this draft only carries the caller's decision authority.

Draft validation completed on September 19, 2026. The skill frontmatter validator passed using a temporary `SKILL.md` copy. Local Markdown links resolve, source integrity passes `layers.py check`, and `package.py check` confirms the existing release remains current. An independent read-only review applied the instructions to nine scenarios. It found the missing measurement-only completion rule; a focused recheck of the correction found no remaining contradiction in those cases. This was an instruction review, not a live CLI or application test.
