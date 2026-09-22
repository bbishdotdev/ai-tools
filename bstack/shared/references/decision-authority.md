# Decision authority

Product choices and ADRs belong to the user by default. Reuse an existing explicit approval or delegation within its scope. Automatic routing only selects workflows; it grants no authority to make decisions, publish, or start implementation.

An agent records human decisions with the actual decider and confirmation reference. Delegated decisions record the decider, scope and grant reference. Do not fabricate a human approval or widen a planning grant into implementation. Carry these limits into specs, tickets and [handoffs](../skills/handoff/SKILL.md).

## Autonomous grilling

Use this branch only when the user explicitly delegates the answers or asks for an autonomous run that needs grilling. Manual human grilling never requires model settings.

Before creating or changing planning records, run the [workflow helper](../workflow.py) with the selected project, `preflight --mode autonomous --area wayfinder`. For first-time setup, initialize the empty store using [workspace access](workspace.md) before adding configuration files. The helper reads the owning workspace's private `.bstack/workspace/roles.json`:

```json
{
  "version": 1,
  "grilling": {
    "interviewer": {"adapter": "native", "model": "explicit-model-id"},
    "respondent": {"adapter": "claude", "model": "different-explicit-model-id"}
  }
}
```

Use the user's actual model IDs, not these placeholders. Supported adapter labels are `native`, `codex`, `claude`, `cursor` and `grok`. Each role may include an explicitly configured `effort`. Missing, invalid or same-model bindings stop this autonomous branch before writes. Ask for the missing roles once; do not guess a cheaper model or substitute an interview with yourself.

A successful helper result validates configuration only. Use the host's supported capabilities to establish that each configured model can actually run, with the required permissions and requested effort. A CLI binary or a config entry alone is insufficient. Report an unavailable adapter/model before starting the exchange. External data disclosure still follows the user's authorization and host rules.

Run two distinct model participants with separate role briefs. The interviewer challenges the plan and the respondent answers within the user's delegated scope using code and accepted decisions. Preserve substantive objections, answers and unresolved points in the resulting record. The calling agent coordinates the exchange; it must not invent either participant's response. Same-family model variants provide a narrower difference in perspective than different families; report what actually ran.

Use grilling's shared-understanding stopping rule, plus any user budget or scope boundary. If no bound was supplied for an unattended run, set and report a finite round/time budget before starting. Disagreement or exhausted budget leaves the question unresolved or waiting. It does not justify fabricated consensus. An ADR outside the grant returns to the user.

## Phase changes

At prototype-to-implementation, use a fresh context with the durable handoff. Read [handoff](../skills/handoff/SKILL.md) when transferring a phase. Verify any requested session/model launch capability before promising an unattended run. If the host cannot launch the required receiver, preserve the handoff and identify the needed launch action. Do not silently continue in the old context and claim a fresh session.
