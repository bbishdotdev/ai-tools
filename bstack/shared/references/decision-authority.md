# Decision authority

Product choices and ADRs belong to the user by default. Reuse an existing explicit approval or delegation within its scope. Automatic routing only selects workflows; it grants no authority to make decisions, publish, or start implementation.

An agent records human decisions with the actual decider and confirmation reference. Delegated decisions record the decider, scope and grant reference. Do not fabricate a human approval or widen a planning grant into implementation. Carry these limits into specs, tickets and [handoffs](../skills/handoff/SKILL.md).

For nontrivial planning or engineering choices, follow the shared [architecture decision process](architecture-decisions.md). Consult applicable current ADRs before exploring alternatives. Apply its high capture threshold and reconcile actual reversals; ordinary answers and prototype preferences need no ADR.

## Autonomous grilling

Use this branch only when the user explicitly delegates the answers or asks for an autonomous run that needs grilling. Manual human grilling never requires model settings.

At first use, explain the roles plainly: one model challenges the plan, and a different model answers using the user's constraints and evidence. They can keep the human-guided interview instead. Do not turn ordinary auto routing into an autonomous decision grant.

First check whether the host supports launching two independent participants and passing the needed context to each. If it does, ask for two exact model choices only when the user has not already supplied or delegated them. Then try a small bounded request with each selected model and inspect the responses and model identities. A CLI binary, a model name, or a saved role file does not prove either can run. If one cannot, stop this branch before any planning write and name the gap. Do not ask the user to configure models for a workflow this host cannot execute.

For CLI roles, run `python3 /absolute/package/scripts/bstack.py doctor --project /path/to/project --live --workflow grilling` after saving the choices below. This makes the same bounded check for both configured roles. If the environment uses a wrapper, configure it once through `/absolute/package/shared/model_cli.py configure --cli <name> --command 'actual wrapper {args}'` and rerun doctor. A native host role needs its own observed host-level launch; the CLI doctor reports it as unverified.

For a supported run, initialize the private store through [workspace access](workspace.md) if it is new, then use the bundled [workflow helper](../workflow.py) to save role choices. Resolve the helper relative to this file and pass the consumer project explicitly:

```bash
python3 /absolute/package/workspace/cli.py --project /path/to/project init
python3 /absolute/package/shared/workflow.py --project /path/to/project configure-grilling \
  --interviewer-adapter codex --interviewer-model 'YOUR_INTERVIEWER_MODEL_ID' \
  --respondent-adapter claude --respondent-model 'YOUR_RESPONDENT_MODEL_ID'
python3 /absolute/package/shared/workflow.py --project /path/to/project preflight --mode autonomous --area wayfinder
```

The `init` command is needed only for a new workspace. The model IDs are placeholders; use choices the user supplied or explicitly delegated. Supported adapter labels are `native`, `codex`, `claude`, `cursor` and `grok`; add `--interviewer-effort` or `--respondent-effort` only when supported. The helper saves private `.bstack/workspace/roles.json` for the owning workspace, including linked worktrees. To change existing choices, rerun `configure-grilling` with `--replace`. Missing, invalid or same-model bindings stop preflight. Manual work ignores this file.

The default autonomous preflight sends a short prompt to each CLI role and stops if either fails. It reports `runtimeChecked: true` only for that live check. A native host role cannot be tested by this CLI helper. After observing a separate host-level launch for each native role, use `preflight --structural` to check the saved choices; its `runtimeChecked: false` remains honest. Run the two-role exchange with the scoped decision authority only when both requested models actually responded. If the host cannot do that, report the gap and offer human-guided grilling instead. Do not invent either side of the exchange. External data disclosure still follows the user's authorization and host rules.

Run two distinct model participants with separate role briefs. The interviewer challenges the plan and the respondent answers within the user's delegated scope using code and accepted decisions. Preserve substantive objections, answers and unresolved points in the resulting record. The calling agent coordinates the exchange; it must not invent either participant's response. Same-family model variants provide a narrower difference in perspective than different families; report what actually ran.

Use grilling's shared-understanding stopping rule, plus any user budget or scope boundary. If no bound was supplied for an unattended run, set and report a finite round/time budget before starting. Disagreement or exhausted budget leaves the question unresolved or waiting. It does not justify fabricated consensus. An ADR outside the grant returns to the user.

## Phase changes

At prototype-to-implementation, use a fresh context with the durable handoff. Read [handoff](../skills/handoff/SKILL.md) when transferring a phase. Verify any requested session/model launch capability before promising an unattended run. If the host cannot launch the required receiver, preserve the handoff and identify the needed launch action. Do not silently continue in the old context and claim a fresh session.
