---
name: github-issue
description: Use when the user asks to create, draft, flesh out, plan, or refine one GitHub issue, or asks to break a milestone/PRD/user-story list into one or more executable GitHub issues. The skill turns vague ideas or milestone outcomes into well-scoped product/engineering issues by pushing back, researching the code/docs, asking clarifying questions, defining acceptance criteria, and choosing appropriate unit/integration/Playwright/manual test expectations before creating issues.
---

# GitHub Issue

Use this skill when the user asks to create or draft GitHub issues, especially from a vague prompt like "create an issue for X" or from a milestone/PRD created by `/milestone`.

The default behavior is **do not immediately create issues**. First build enough shared understanding that each issue is executable. Use the `/refine` subagent when the user's ask is vague or the product decision is still unsettled.

Except, if the user provides enough information to create the issue immediately, do so. In many flows the user already did `/refine` and `/milestone`; in that case, use those artifacts as source material and only ask about gaps that block issue quality.

## Invocation Modes

Choose one mode early and say which one you are using when it affects the workflow:

1. **Single issue mode**
   - Use when the user asks for an issue for a specific task, bug, feature, or improvement.
   - If the task is already clear, draft or create one issue.
   - If the task is vague, clarify the product outcome, constraints, and verification path before drafting.

2. **Milestone decomposition mode**
   - Use when the user asks for issues that fulfill a milestone, PRD, feature plan, or list of user stories.
   - Treat the milestone as the product contract: every issue should map back to one or more user stories, implementation decisions, or testing decisions.
   - Produce a coherent issue set, not a pile of tasks. Split by independently verifiable outcomes, user-visible flow boundaries, risk boundaries, or deep modules.
   - Call out missing milestone detail before creating issues if decomposition would otherwise encode bad assumptions.
   - Prefer fewer, stronger issues over many tiny tickets that only make sense in aggregate.

Common product flow:

```text
/refine -> /milestone -> /github-issue
```

`/refine` sharpens the idea. `/milestone` creates the PRD-like milestone with high-level user stories. `/github-issue` converts that milestone into executable GitHub issues.

## Core Workflow

1. **Clarify intent and mode**
   - Identify whether this is single issue mode or milestone decomposition mode.
   - Identify the product outcome, user value, current milestone, and source artifact.
   - If the request is vague, ask targeted questions before creating anything. Leverage the `/refine` subagent for this.
   - Push back on scope creep, weak assumptions, missing edge cases, or issues that mix unrelated work.

2. **Research context**
   - Read relevant docs first: `README.md`, `PRD.md`, `POC.md`, `TDD.md`, `GTM.md`, `TRANSPARENCY.md`, and user-flow docs as needed.
   - Search the codebase with `rg` before defining technical requirements.
   - Check existing GitHub issues if duplication is likely.
   - Use subagents for researching the codebase where possible.

3. **Shape the issue or issue set**
   - Prefer one clear outcome per issue.
   - Split issues when the work crosses unrelated surfaces, hides sequencing risk, or would be hard to verify.
   - In milestone decomposition mode, create a coverage map from user stories to proposed issues before finalizing.
   - Tie requirements back to the milestone and product thesis when relevant.

4. **Define tests proportionally**
   - Every issue should include a `Test Plan`.
   - Do not force every test type on every issue.
   - Use `Not applicable` or `Covered by follow-up` when appropriate.

5. **Preview before creating**
   - If the user has not explicitly authorized creation after seeing the final issue body or issue set, show the draft and ask for confirmation.
   - If the user already asked to create issues and the requirements are clear, create them after drafting internally.
   - For milestone decomposition, preview the proposed issue list unless the user explicitly asked for immediate creation and the milestone is already complete.

## Issue Format

Use the repo issue template in `.github/ISSUE_TEMPLATE/product_task.md`:

```md
## Goal

What user or product outcome does this issue unlock?

## Product Context

Why does this matter to the current milestone, product bet, or session-record-as-evidence primitive?

## Scope

What should be built or changed in this issue?

## Requirements

-

## Acceptance Criteria

- [ ]

## Test Plan

- Unit:
- Integration / functional:
- Playwright:
- Manual:

## Out of Scope

-
```

## Test Guidance

Use the lightest test layer that protects the behavior:

- **Unit tests**: deterministic logic such as ignore rules, path filtering, hashing, event normalization, state transitions, and validation helpers.
- **Integration / functional tests**: CLI-to-backend behavior, session creation, heartbeat, file update/delete sync, write rejection after end, reconnect/rescan.
- **Playwright tests**: user-visible web flows such as creating a session, seeing join instructions, viewing connection status, inspecting events/files, ending a session.
- **Manual checks**: early CLI behavior, OS/file watcher quirks, rapid saves, `Ctrl+C`, ignored secret files, and local setup friction.

For Code Maverick M1, minimum done usually means:

- unit coverage for security-sensitive or trust-sensitive rules,
- functional coverage for the capture/sync spine,
- light Playwright coverage for the raw interviewer view once UI exists,
- manual CLI checklist for real local folder behavior.

## Product Pushback Checklist

Before creating an issue, check:

- Is this issue proving the current milestone, or is it premature polish?
- Is the session record treated as the product primitive, not incidental telemetry?
- Are candidate capture boundaries and trust implications explicit?
- Are secrets and ignored files handled?
- Is the issue small enough to finish and verify?
- Are acceptance criteria observable?
- Does the test plan match the risk?
- Is anything important explicitly out of scope?

## GitHub Creation

When creating the issue:

- Use the detected repo remote unless the user specifies another repo.
- Attach the relevant milestone if known and supported by the available GitHub tool.
- Use labels only if they already exist or the user asks for them.
- After creation, report the issue title and URL/number.

If milestone assignment is not possible through the available tool, create the issue without it only after telling the user, or ask them to assign it manually.
