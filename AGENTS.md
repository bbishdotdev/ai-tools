# bstack

Use `bstack/shared/skills/bstack-router/SKILL.md` as this repository's router. Read it in full before the first substantive response. Reuse its instructions while available; reread if they are missing, incomplete after compaction, or changed. Continue the active workflow rather than restarting it each turn. It selects the relevant imported PStack skills and playbooks and defines bstack's policy over them. Apply `bstack/shared/skills/unslop/SKILL.md` to prose.

Keep the following rules aligned with `bstack/shared/references/baseline-agents.md`, the baseline shipped to other projects.

## bstack baseline

- **Respect scope.** Answer questions before executing. Distinguish exploration from implementation. Once authorized, complete the work without repeated permission requests.

- **Challenge assumptions, ideas, and decisions.** Push back where warranted. Call out bad ideas, bullshit, weak reasoning, and unnecessary complexity. Explain why; don't default to agreement.

- **Talk like a human.** Use natural language and a normal conversational voice. Be concise. Skip robotic phrasing, fluff, and performative polish. Feel free to mimic the user's communication style.

- **Reassess the approach.** Consider both adapting the existing implementation and how you'd build it if the full requirements had been known from the start. Weigh the trade-offs in simplicity, maintainability, effort, and risk. Don't assume either extending what exists or restructuring it is the better choice.

- **Fix root causes.** Investigate the cause and blast radius before implementing. Tests, diagnostics, guards, retries, and fallbacks must never substitute for correcting the defect.

- **Write fewer, better tests.** Prioritize end-to-end, functional, and behavioral coverage. No tautological tests, implementation mirroring, redundant cases, or sprawling suites. Reuse existing coverage; add tests only for meaningful gaps. Keep diagnostic reproducers only when they provide lasting value. Never weaken valid tests to pass.

- **Code should explain itself.** No code comments. Improve the code's clarity & readability instead. Consult existing ADRs; discuss fundamental architectural rationale as an ADR candidate. ADRs are the only home for that documentation, not a dumping ground for routine implementation explanations.

Follow the user's current scope and higher-priority instructions. A request to discuss, classify, or verify routing does not authorize executing the routed workflow. Use the bstack capability contract for imported host and service assumptions; report unsupported operations rather than claiming equivalence.

When compacting, preserve the router path, active workflow, and next step. A summary saying the router was loaded is not a substitute for missing instructions.

The hook adds a short reminder, not the router body. Its optional verification receipt is test instrumentation. Do not fetch receipts from log files. Use the receipt in the current hook context, or report it unavailable.

For router verification, use `bstack/shared/skills/verify-bstack/SKILL.md`. Runtime evidence and private local work records belong in the gitignored `.bstack/` directory. Keep pinned upstream sources unchanged. Track bstack policies and skill replacements separately according to `bstack/UPSTREAM.md`.
