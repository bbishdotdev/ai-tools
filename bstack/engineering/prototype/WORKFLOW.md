---
name: prototype
description: Build and iterate on disposable prototypes to explore UI alternatives, experience behavior, or answer a technical question before production implementation.
metadata:
  author: Brenden Bishop
  status: approved-pending-integration
  attribution: ../../../ATTRIBUTION.md
---

# Prototype

Build the smallest runnable artifact that lets the decision owner judge the question. Keep the experiment disposable and the review loop open until the direction is settled.

## Frame the experiment

Use the conversation and relevant code to identify the question, existing constraints, and who can settle it. Reuse prior exploration. Ask only for a missing decision that materially changes the prototype. Product choices belong to the user unless explicitly delegated; carry the caller's scope and decision authority forward.

Choose the artifact by the question. Read only the applicable guide:

- UI options or interaction design: [UI guide](references/ui.md).
- Business rules or state transitions someone needs to experience: [logic guide](references/logic.md).
- Behavior or timing that observation can settle: the smallest runnable experiment with visible output. No extra guide or UI is required.

## Build in isolation

For an existing feature, run the actual application in a disposable local checkout. For a new concept, use an ignored scratch directory and the lightest suitable tools. Give each prototype session its own workspace. Keep unfinished and saved work out of automatically purged temporary storage.

Follow the application's brand, colors, typography, components, and design system, including in standalone sketches for that product. Establish a new visual direction only when none exists or the user requests it.

For open option generation, default to five structurally distinct variants. An explicit count wins. A focused measurement needs only the experiment that answers it. Provide labeled interactive comparison for multiple options. Build the relevant interactions whenever the concept itself is interactive.

Keep state in memory and mutations simulated. Use scratch persistence when persistence is the question. Add only what makes the experiment runnable and useful. Avoid production hardening, a new test suite, and speculative abstractions.

## Verify and present

Run every variant and exercise the relevant interactions before presenting it. Capture screenshots for visual comparisons or observed output for behavioral experiments. If the required control capability is unavailable, identify what remains unverified.

Present the artifact or launch command, stable variant labels, meaningful differences, and a recommendation. Keep evidence with the temporary workspace. Do not require a rationale from the user or create a decision document, ADR, or permanent evidence archive by default.

## Continue the review loop

Interpret feedback in the current conversation:

| Feedback | Next action |
| --- | --- |
| More options, a refinement, or a combination | Build the requested revision, verify it, and present it again. Combining parts of 1, 3, and 5 produces that combined variant, not another default batch. |
| A favorite without a final selection | Keep exploring or wait for the next direction. Preserve the alternatives. |
| Pause or no decision yet | Keep the workspace and its launch instructions available for resumption. |
| Save these | Preserve the requested runnable references locally and report their location. No remote service is required. |
| Final selection | Carry that target to implementation when implementation is within the authorized scope. Otherwise retain it for later. |

During refinement, the word "implement" alone does not end prototyping. Clear instructions to build the final selection do. Honor existing authorization without requiring a special command or repeated approval. Clarify only when another preview versus a production build remains ambiguous.

## Hand off and clean up

Pass the selected target and usable pieces to the caller's engineering workflow. Most prototype code is disposable; reusable logic or existing components still need normal production review and testing. Do not ship prototype controls or losing variants.

Once implementation has taken over the needed reference and reusable pieces, remove only this session's disposable files and resources. Preserve anything explicitly saved. Never clean up unfinished exploration or another session's work.

For a completed measurement-only task with no pending review or implementation, return the observed result and remove its unsaved scratch resources.

On a handoff or context compaction, retain only the question, workspace and launch command, current variants or selection, preservation request, decision authority, and next action in the existing task context. Resume the current phase.
