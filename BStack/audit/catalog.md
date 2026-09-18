# PStack catalog

Generated from the pinned BStack import. Start with [the architectural audit](pstack.md).

This catalog describes unchanged upstream files. BStack's active [router policy](../shared/skills/bstack-router/SKILL.md) and [unslop override](../shared/skills/unslop/SKILL.md) live outside the import. See [the layer manifest](../layers.json).

Purpose text comes from each skill's description. Manual means the file declares `disable-model-invocation: true`; normal means it does not. This records metadata, not proof that any host loaded the skill. Character counts cover the complete SKILL.md, not its supporting files. Dormant Benny skills are outside the plugin manifest's discovery directory.

## Workflow and utility skills

| Skill | Purpose and trigger | Discovery | Characters |
| --- | --- | --- | ---: |
| [architect](../engineering/skills/architect/SKILL.md) | Sketch types, signatures, and module structure before code, then stay in the loop while implementation fills in. Use for /architect, 'architect this', 'design this', or non-trivial work where jumping to code would lock in the wrong shape. | Manual | 5,383 |
| [arena](../engineering/skills/arena/SKILL.md) | Spawn N parallel candidates at the same task, pick a base, graft the strongest parts of the losers into it. Use for /arena, 'arena this', 'throw it in the arena', or when one attempt at a non-trivial artifact would lock in the wrong shape. | Manual | 4,591 |
| [automate-me](../engineering/skills/automate-me/SKILL.md) | Use for "automate me", "create/update/refresh my -mode skill", "turn/capture my preferences or working style into a skill", or wanting agents to follow how the user works. Drafts or revises a personal -mode skill via create-skill + unslop, optionally pulling fresh evidence from recent transcripts. | Manual | 7,164 |
| [blast-radius](../engineering/skills/blast-radius/SKILL.md) | Find what a change could break somewhere else before it ships, beyond the diff, and prove the one fact it's safe because of by running real code instead of writing it up. Use for 'blast radius of X', 'what could this break', or reviewing a small diff you don't trust. | Manual | 4,016 |
| [bro](../engineering/skills/bro/SKILL.md) | Restate the last message in plain human language, with no jargon. | Manual | 267 |
| [create-verification-skill](../engineering/skills/create-verification-skill/SKILL.md) | Generate a project-local verification skill that drives your app the way a user does — any language, framework, or platform. Use for /create-verification-skill, "make a control skill for this repo", or when a project has no scripted way to prove UI/CLI/service behavior. | Manual | 5,869 |
| [figure-it-out](../engineering/skills/figure-it-out/SKILL.md) | Design an auditable playbook when no narrower one fits: a large migration, an ambitious multi-part change, or work a human reviews after stepping away. Scales rigor to the task, runs a hypothesis loop, and logs decisions via show-me-your-work. Use for /figure-it-out, 'figure it out', a large migration, or when no narrower playbook applies. | Manual | 4,384 |
| [how](../engineering/skills/how/SKILL.md) | Use for "how does X work", code walkthroughs before changing something, and placement / ownership / layering questions ("where should this live", "which package owns this", "is this the right layer"). Explains subsystem architecture, runtime flow, onboarding mental models. Use why for motivation. | Manual | 2,738 |
| [interrogate](../engineering/skills/interrogate/SKILL.md) | Use for "interrogate", "adversarial review", "multi-model review", "challenge this", "stress test this code", "find blind spots", or "tear this apart". Multiple LLM reviewers challenge changes from independent angles. | Manual | 4,943 |
| [maintain-verification-skill](../engineering/skills/maintain-verification-skill/SKILL.md) | Periodic pass that keeps a project's verification skill and feature map honest: parallel source readers per feature, one live session driving every feature, at most one PR of proven corrections. Use for /maintain-verification-skill or "audit the verify skill". | Manual | 4,890 |
| [make-bot-ui](../engineering/skills/make-bot-ui/SKILL.md) | Use when building a custom UI (page, dashboard, buttons) that should wake a Grok Bot over a webhook, when the user must provide a webhook sender key, or when exposing that UI on Tailscale. | Manual | 4,649 |
| [no-comments](../engineering/skills/no-comments/SKILL.md) | Spawn Comment Sicko, fix accepted findings, and offer encodings for claimed constraints. | Manual | 2,560 |
| [poteto-mode](../engineering/skills/poteto-mode/SKILL.md) | poteto's agent style for concise, detailed responses, deliberate subagents, unslopped prose, simple code, and verified work. Use for poteto, /poteto-mode, or requests to work in this style. | Manual | 18,677 |
| [recall](../engineering/skills/recall/SKILL.md) | Reconstruct your recent working context from your own chat history, live state, and the shared record (user reports, prior fixes, incidents), then hand back a tight current-state brief. Use for 'recall my work on X', 'catch me up', 'what have I been working on', 'where did I leave off', before starting or resuming work. | Manual | 5,212 |
| [reflect](../engineering/skills/reflect/SKILL.md) | Spawn three parallel review subagents over the active transcript, surface learnings, and route each to a concrete edit on an existing skill. Use when the user says reflect. | Manual | 4,588 |
| [setup-pstack](../engineering/skills/setup-pstack/SKILL.md) | Configure which models pstack uses per role and at what reasoning budget. Detects your available models and writes an always-applied rule that overrides the skill defaults. Use for /setup-pstack, "configure pstack models", "pstack budget", or changing pstack's model choices. | Normal | 5,681 |
| [show-me-your-work](../engineering/skills/show-me-your-work/SKILL.md) | Keep a reviewable decision trail for long-running or unattended work: a TSV log with one row per decision (what, why, evidence, result). Local by default; commit it when a reviewer needs the trail to trust the result. Use for /show-me-your-work, autonomous or multi-phase runs, or work a human reviews after stepping away. | Manual | 5,459 |
| [swarm](../engineering/skills/swarm/SKILL.md) | Fan out N parallel workers, drain them, and return one report. Use for /swarm, 'swarm this', or parallel coverage, races, gauntlets, and exploration. | Manual | 2,172 |
| [tdd](../engineering/skills/tdd/SKILL.md) | Use only when the user explicitly asks for TDD, a failing test, or a regression test, OR when the bug has an obvious cheap local test target. Skip when the test path is unclear, expensive, integration-heavy, or not requested. | Manual | 3,536 |
| [teach](../engineering/skills/teach/SKILL.md) | Explain a body of work plainly so a person actually understands it. Runs the `how` and `why` skills and weaves what they find into one clear explanation. Use for 'teach me this', 'help me really understand X', 'explain this change or subsystem to me'. | Manual | 5,623 |
| [technical-writing](../engineering/skills/technical-writing/SKILL.md) | Layered technical-writing standard: Diátaxis structure, Google developer style sentences, STE instruction rules, Global English syntax. Use for /technical-writing or when writing or reviewing docs, RFCs, readmes, PR descriptions, or commit messages. | Manual | 10,978 |
| [typescript-best-practices](../engineering/skills/typescript-best-practices/SKILL.md) | TypeScript best practices. Use when reading or editing any .ts or .tsx file. | Manual | 2,684 |
| [unslop](../engineering/skills/unslop/SKILL.md) | Cut AI tells from any writing. Must always apply. | Manual | 6,091 |
| [why](../engineering/skills/why/SKILL.md) | Use for 'why does X work this way', 'why we picked Y', design rationale, regressions, postmortems, or data-backed thresholds. Discovers available MCPs and queries each evidence category (source control, issue tracker, long-form docs, real-time chat, infrastructure observability, error tracking, product analytics warehouse) in parallel, then returns a cited read on decisions and tradeoffs. Use how for runtime behavior. | Manual | 9,999 |

## Engineering principles

| Skill | Purpose and trigger | Discovery | Characters |
| --- | --- | --- | ---: |
| [principle-attack-the-premise](../engineering/skills/principle-attack-the-premise/SKILL.md) | Apply when two or more fixes that share one premise have failed the same gate. Take a census of which actors hold the imbalance before the next fix, then question the premise instead of writing another fix that assumes it. | Manual | 1,941 |
| [principle-boundary-discipline](../engineering/skills/principle-boundary-discipline/SKILL.md) | Apply when wiring validation, error handling, or framework adapters. Concentrate guards at system boundaries (CLI, config, network, external APIs); trust internal types and keep business logic in pure functions. | Manual | 1,883 |
| [principle-build-the-lever](../engineering/skills/principle-build-the-lever/SKILL.md) | Apply to any non-trivial work, not just bulk work: edits, migrations, analyses, checks. Build the tool that does it or proves it (codemod, script, generator, or a skill your subagents follow) instead of working by hand. The tool is the artifact a reviewer can rerun. | Manual | 2,458 |
| [principle-encode-lessons-in-structure](../engineering/skills/principle-encode-lessons-in-structure/SKILL.md) | Apply when you catch yourself writing the same instruction a second time, or notice a recurring correction. Encode the rule as a lint, metadata flag, runtime check, or script instead of more text. | Manual | 2,211 |
| [principle-exhaust-the-design-space](../engineering/skills/principle-exhaust-the-design-space/SKILL.md) | Apply when facing a novel UI interaction or architectural decision with no precedent in the codebase. Build 2-3 competing prototypes and compare side by side before committing. | Manual | 1,152 |
| [principle-experience-first](../engineering/skills/principle-experience-first/SKILL.md) | Apply when product, UX, or feature-scope tradeoffs come up. Choose user delight over implementation convenience; ship fewer polished features over more rough ones. | Manual | 1,184 |
| [principle-fix-root-causes](../engineering/skills/principle-fix-root-causes/SKILL.md) | Apply when debugging. Trace each symptom to its root cause and fix it there; reproduce first, ask why until you reach it, resist nil-check guards that silence crashes. | Manual | 1,246 |
| [principle-foundational-thinking](../engineering/skills/principle-foundational-thinking/SKILL.md) | Apply before writing logic: choosing core types and data structures, sequencing scaffold-vs-feature work, asking what concurrent actors share. Get the data structures right so downstream code becomes obvious. | Manual | 1,530 |
| [principle-guard-the-context-window](../engineering/skills/principle-guard-the-context-window/SKILL.md) | Apply when context is filling up: large outputs, long files, repeated reads, fan-out planning. Route bulk to subagents; keep summaries in the main thread, not raw payloads. | Manual | 1,067 |
| [principle-laziness-protocol](../engineering/skills/principle-laziness-protocol/SKILL.md) | Apply when refactoring, evaluating diff size, or tempted to add abstractions, layers, or signal threading. Bias toward deletion and the smallest change that solves the problem. | Manual | 1,371 |
| [principle-make-operations-idempotent](../engineering/skills/principle-make-operations-idempotent/SKILL.md) | Apply when designing commands, lifecycle steps, or processing loops that run amid crashes, restarts, and retries. Converge to the same end state regardless of partial prior runs. | Manual | 1,390 |
| [principle-migrate-callers-then-delete-legacy-apis](../engineering/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md) | Apply when introducing a new internal API while old callers still exist. Migrate callers and delete the old API in the same wave instead of preserving compatibility layers. | Manual | 1,146 |
| [principle-minimize-reader-load](../engineering/skills/principle-minimize-reader-load/SKILL.md) | Apply when reviewing or shaping code that's hard to trace. Count layers between question and answer, and hidden state in the reader's head; collapse one-caller wrappers and shrink mutable scope. | Manual | 2,095 |
| [principle-model-the-domain](../engineering/skills/principle-model-the-domain/SKILL.md) | Apply when writing stateful logic, or when code branches a lot or repeats a shape assumption across files. Encode the domain in a structure instead of scattered conditionals. | Manual | 2,082 |
| [principle-never-block-on-the-human](../engineering/skills/principle-never-block-on-the-human/SKILL.md) | Apply when tempted to ask 'should I do X?' on reversible work. Proceed, present the result, let the human course-correct after the fact; reserve confirmation for irreversible actions. | Manual | 1,343 |
| [principle-outcome-oriented-execution](../engineering/skills/principle-outcome-oriented-execution/SKILL.md) | Apply during planned rewrites and migrations with explicit phase boundaries. Converge on the target architecture; don't preserve smooth intermediate states with throwaway compatibility code. | Manual | 1,132 |
| [principle-prove-it-works](../engineering/skills/principle-prove-it-works/SKILL.md) | Apply after completing a task, before declaring done. Verify against the real artifact (run the feature, read the actual value, inspect the diff), not a proxy, self-report, or 'it compiles.' | Manual | 1,879 |
| [principle-redesign-from-first-principles](../engineering/skills/principle-redesign-from-first-principles/SKILL.md) | Apply when integrating a new requirement into an existing design. Redesign as if the requirement had been a foundational assumption from day one, instead of bolting it on. | Manual | 844 |
| [principle-separate-before-serializing-shared-state](../engineering/skills/principle-separate-before-serializing-shared-state/SKILL.md) | Apply when concurrent actors might write to the same file, branch, key, or state object. Eliminate the sharing first; serialize structurally only when one shared writer is a real invariant. | Manual | 1,565 |
| [principle-sequence-verifiable-units](../engineering/skills/principle-sequence-verifiable-units/SKILL.md) | Apply to multi-step work (sweeps, migrations, runs of similar edits) and to how you stack commits and PRs. Break work into small units that each end in a verifiable state, check each before the next, and order delivery so the sequence proves itself to a reviewer. | Manual | 2,029 |
| [principle-subtract-before-you-add](../engineering/skills/principle-subtract-before-you-add/SKILL.md) | Apply when sequencing an addition, refactor, or rewrite. Remove dead code, redundant validators, and stub references first, then build on the simpler base. | Manual | 1,094 |
| [principle-test-behavior-not-implementation](../engineering/skills/principle-test-behavior-not-implementation/SKILL.md) | Apply when you write, change, or keep a test. Call the code the way its users do and assert the result they observe against a literal expected value. If the test would still pass when every imported function returns undefined, rewrite the assertion or delete the test. | Manual | 2,575 |
| [principle-type-system-discipline](../engineering/skills/principle-type-system-discipline/SKILL.md) | Apply when designing types, reviewing a function signature, or writing code in any statically-typed language. Make illegal states unrepresentable, brand semantic primitives, parse external data at boundaries, refuse to lie to the compiler, exhaust variants, derive from authoritative schemas. | Manual | 4,922 |

## Required companion skills

| Skill | Purpose and trigger | Discovery | Characters |
| --- | --- | --- | ---: |
| [control-cli](../engineering/skills/control-cli/SKILL.md) | Build or adapt a local harness to drive, inspect, and profile an interactive CLI or TUI without external services. Use for CLI UX checks, startup regressions, memory leaks, hangs, prompt flows, or terminal demos. | Normal | 4,333 |
| [control-ui](../engineering/skills/control-ui/SKILL.md) | Build or adapt a local browser/CDP harness to drive and inspect a web, IDE, or Electron UI. Use for local UI verification, screenshots, accessibility snapshots, perf profiles, visual diffs, or reproducing UI bugs. | Normal | 4,802 |
| [deslop](../engineering/skills/deslop/SKILL.md) | Remove AI-generated code slop and clean up code style | Normal | 719 |

## Dormant automation skills

| Skill | Purpose and trigger | Discovery | Characters |
| --- | --- | --- | ---: |
| [reproduce-and-fix-issues](../engineering/automations/benny/skills/reproduce-and-fix-issues/SKILL.md) | Reproduce triaged Slack bugs through a configured app-control adapter, verify existing fixes, and open a bounded draft pull request only after before-and-after proof. Use only from the configured Benny repro automation. | Manual | 14,238 |
| [setup-benny](../engineering/automations/benny/skills/setup-benny/SKILL.md) | Configure Benny and prepare its triage and repro automations. Use when installing Benny or changing its Slack, tracker, repository, routing, control, model, or budget settings. | Manual | 13,992 |
| [triage-issue-reports](../engineering/automations/benny/skills/triage-issue-reports/SKILL.md) | Triage Slack issue reports with one thread-only verdict, evidence review, cause-aware routing, tracker dedupe, and fail-closed ticket creation. Use only from the configured Benny triage automation. | Manual | 10,320 |

## Playbooks

These are selected files within poteto-mode, not separately registered skills.

| Playbook | Purpose | Characters |
| --- | --- | ---: |
| [authoring-a-skill](../engineering/skills/poteto-mode/playbooks/authoring-a-skill.md) | Author through Cursor create-skill, validate, and prepare a PR. | 829 |
| [autonomous-run](../engineering/skills/poteto-mode/playbooks/autonomous-run.md) | Drive one task until an explicit completion condition is met. | 1,878 |
| [autopilot-full](../engineering/skills/poteto-mode/playbooks/autopilot-full.md) | Run independent PR owners through verification and authorized merging. | 5,923 |
| [autopilot-stack](../engineering/skills/poteto-mode/playbooks/autopilot-stack.md) | Build one verified PR chain for the operator to land. | 5,288 |
| [babysit](../engineering/skills/poteto-mode/playbooks/babysit.md) | Check or drive PR conflicts, review comments, and CI toward merge readiness. | 8,010 |
| [bug-fix](../engineering/skills/poteto-mode/playbooks/bug-fix.md) | Reproduce, find the mechanism, fix, and prove the original symptom is gone. | 2,412 |
| [eval](../engineering/skills/poteto-mode/playbooks/eval.md) | Compare skill or prompt variants with blinded candidates and a judge. | 2,524 |
| [feature](../engineering/skills/poteto-mode/playbooks/feature.md) | Understand, design, delegate implementation, verify, and prepare delivery. | 3,022 |
| [hillclimb](../engineering/skills/poteto-mode/playbooks/hillclimb.md) | Improve one measured target through controlled, recorded experiments. | 4,081 |
| [investigation](../engineering/skills/poteto-mode/playbooks/investigation.md) | Return a cited explanation or recommendation without changing code. | 928 |
| [multi-phase-plan](../engineering/skills/poteto-mode/playbooks/multi-phase-plan.md) | Create a detailed PR program with explicit dependencies and verification lanes. | 12,274 |
| [opening-a-pr](../engineering/skills/poteto-mode/playbooks/opening-a-pr.md) | Prepare the worktree, commits, cleanup, writing, and forge submission. | 4,920 |
| [orchestrate](../engineering/skills/poteto-mode/playbooks/orchestrate.md) | Coordinate a multi-day program with owners, briefs, state records, and verifiers. | 16,779 |
| [pause-safely](../engineering/skills/poteto-mode/playbooks/pause-safely.md) | Stop work at a recoverable boundary and leave a resume note. | 1,180 |
| [perf-issue](../engineering/skills/poteto-mode/playbooks/perf-issue.md) | Measure a baseline, fix a demonstrated bottleneck, and compare traces. | 3,074 |
| [prototype](../engineering/skills/poteto-mode/playbooks/prototype.md) | Build a disposable experiment to settle a design or behavior question. | 2,161 |
| [refactoring](../engineering/skills/poteto-mode/playbooks/refactoring.md) | Change structure in small steps while preserving observed behavior. | 3,316 |
| [runtime-forensics](../engineering/skills/poteto-mode/playbooks/runtime-forensics.md) | Capture and diagnose a live runtime symptom without automatically fixing it. | 1,210 |
| [session-pickup](../engineering/skills/poteto-mode/playbooks/session-pickup.md) | Reconstruct a prior session and route the remaining work. | 1,678 |
| [shipping](../engineering/skills/poteto-mode/playbooks/shipping.md) | Independently verify and land only the contiguous safe part of a PR stack. | 4,849 |
| [trace-forensics](../engineering/skills/poteto-mode/playbooks/trace-forensics.md) | Query a captured profile or trace and attribute its strongest finding to source. | 1,865 |
| [visual-parity](../engineering/skills/poteto-mode/playbooks/visual-parity.md) | Compare against a fixed visual baseline while migrating one component at a time. | 1,197 |
| [worktree-cleanup](../engineering/skills/poteto-mode/playbooks/worktree-cleanup.md) | Audit worktrees and simulator state before reclaiming confirmed-unused storage. | 2,932 |

## Agents

| Agent | Purpose | Dependency |
| --- | --- | --- |
| [poteto-agent](../engineering/agents/poteto-agent.md) | Give delegates the same operating instructions as the parent | Reads the full poteto-mode wrapper and relevant principle leaves |
| [Comment Sicko](../engineering/agents/comment-sicko.md) | Delete comments and flag code that needs a clearer structure | May investigate disputed claims through how and why; no application-code changes in this agent |

## Mechanical support

| Entry | Purpose |
| --- | --- |
| [check-plan.mjs](../engineering/skills/poteto-mode/scripts/check-plan.mjs) | Validate a specific multi-phase plan format, including fixed verification lane wording |
| [orch.ts](../engineering/skills/poteto-mode/scripts/orch/orch.ts) and [store.ts](../engineering/skills/poteto-mode/scripts/orch/store.ts) | CLI and file storage for orchestration units, verification ledger, inbox, gates, and frontier; do not spawn agents |
| [watch-pr](../engineering/skills/poteto-mode/scripts/watch-pr/watch-pr) | GitHub PR watcher with CLI, GitHub adapter, readiness policy, rendering, types, and bundled tests |
| [bootstrap.ts](../engineering/skills/poteto-mode/scripts/bootstrap.ts) | Install locked Bun dependencies next to the script when needed |
| [worktree-audit.sh](../engineering/skills/poteto-mode/scripts/worktree-audit.sh) | Inspect worktree size, age, Git/PR state, and Cursor transcripts for cleanup decisions |
| [log.sh](../engineering/skills/show-me-your-work/scripts/log.sh) | Append sanitized rows to the decision TSV |

The [guide](../engineering/docs/guide/README.md) explains upstream use. The [Benny pack](../engineering/automations/benny/README.md) includes configuration and automation templates. Images and license files are preserved. See [the inventory](pstack-inventory.json) for every file and explicit textual-reference edge with source locations.
