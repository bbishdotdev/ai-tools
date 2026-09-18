# Router policy decisions

The BStack entry layer changes when a workflow applies, when architecture exploration earns its cost, how external capabilities are selected, and how execution is reported. The pinned upstream router remains separately auditable.

## Contract

- Standalone prose does not select an engineering playbook.
- Complex one-time engineering work can use `figure-it-out` without creating a reusable skill. Planning authorization does not authorize implementing the plan.
- Touching two functions alone does not require architecture exploration. Unresolved ownership, interfaces, shared-state races, and consequential design risks can require it.
- Existing bug-fix, feature, and read-only investigation routes remain available.
- The default delegation model policy is `inherit-parent`. Host tooling and configured roles select available delegation capabilities.
- Generic work items can be local when no external provider is configured. A local artifact does not count as delivery to an explicitly requested unavailable service.
- Authorization for an unchanged action persists. A request to explain the next step still stays within that explanation scope.
- Selecting a workflow, executing it, and proving its results are distinct claims. A prior agent's sentence does not establish execution, successful verification, or independent review.

## Drive

Run `python3 BStack/shared/skills/verify-bstack/scripts/verify.py doctor` first. After live provider calls are authorized, run `python3 BStack/shared/skills/verify-bstack/scripts/policy.py` from the repository root. It discovers installed Codex, Claude Code, Cursor, and Grok CLIs. Each selected host receives ten independent fresh sessions. Hosts run concurrently; cases run serially within a host. Each case has a bounded timeout.

Use `--tools codex claude` or another subset to focus a run. Use `--cases ordinary-prose one-off-plan` to isolate a policy change. `--list-cases` prints fixture descriptions and expected answers without contacting providers. Explicitly requested missing clients are blocked. Automatic discovery skips missing clients.

The ten fixtures cover ordinary writing, one-time planning, a routine cross-function feature, risky shared state, a reported defect, read-only investigation, a generic local ticket, an unavailable named tracker, already-authorized action planning, and unsupported audit claims. Prompts include the fixture and response-field definitions. Expected values remain in the driver and retained assessment evidence, outside the model prompt.

## Evidence

Each case must show a tool read of the active `bstack-router/SKILL.md` entry. A statement that the agent read it does not satisfy this check. Responses must match literal per-case expectations and the default model policy. Trace checks permit instruction reads, scoped searches, and host-local tool schema discovery. Cursor's `getMcpToolsToolCall` is permitted only for its `cursor` server. Discovering a schema does not authorize invoking that operation; unknown MCP operations remain rejected. Codex commands and Cursor native shell calls use the same small read-command grammar, which fails closed on unrecognized execution. Inspect the raw trace when it rejects an alternate read mechanism.

Bare command names assume the normal host PATH. Explicit executables and shell wrappers must be under `/usr/bin` or `/bin`; a similarly named executable elsewhere does not count as a known read command.

The candidate must not read this verification skill, its feature maps, driver source, audit reports, or saved evidence. These files disclose expectations and would contaminate the result. The probe supplies its own procedure. The gate inspects native tool arguments, shell commands, and file reads, including the skill's symlink paths. Content searches must stay inside the named instruction directories or individual standing-instruction files. Content globs containing parent-directory traversal are rejected. Searching the whole checkout can expose answers without a separate file-read event and fails the gate. Ordinary prose also fails if the candidate accesses the imported engineering instructions. Directory listings and file-name globs may discover instruction paths, but explicitly targeting verification or evidence files still fails. These are bounded evidence checks, not a replacement for the host sandbox.

The run retains versions, exact prompts and commands, complete output streams, exit status, read and tool traces, assessments, and hashes of the active entry's Markdown files and the upstream router. Hook records and suppression state use temporary directories compatible with Grok's read-only sandbox. The parent copies hook evidence into `.bstack/verification/<run>-policy-<id>/` before cleaning the temporary directory.

Fresh session IDs are checked per host. Instruction hashes must remain unchanged throughout each probe. Missing JSON fields, wrong types, absent read evidence, unexpected tool calls, changed instructions, and incorrect policy choices remain incomplete results.

## Limits

These are classification and next-action probes. They do not execute the hypothetical work, create a local ticket, contact an external provider, delegate a real review, or establish that an implementation followed an entire playbook. They also do not prove hook delivery, compaction recovery, or desktop behavior. Use the separate reminder and compaction tests for those claims. Preserve `show-me-your-work`, Eval, and feature-specific verification when the actual workflow calls for deeper evidence.
