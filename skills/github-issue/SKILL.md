---
name: github-issue
description: Use when the user asks to create, draft, flesh out, plan, or refine one GitHub issue, or asks to break a milestone/PRD/user-story list into one or more executable GitHub issues. The skill turns vague ideas or milestone outcomes into well-scoped product/engineering issues by pushing back, researching the code/docs, asking clarifying questions, defining acceptance criteria, and choosing appropriate unit/integration/Playwright/manual test expectations before creating issues.
---

# GitHub Issue

Use this skill to create or draft GitHub issues, especially from a vague prompt like "create an issue for X" or from a milestone/PRD created by `/milestone`.

The default behavior is to avoid immediately creating issues. First build enough shared understanding that each issue is executable. Use the `/refine` subagent when the user's ask is vague or the product decision is still unsettled.

If the user provides enough information to create the issue immediately, do so. In many flows the user already did `/refine` and `/milestone`; in that case, use those artifacts as source material and only ask about gaps that block issue quality.

Choose one invocation mode early and say which one you are using when it affects the workflow:

- Single issue mode: use when the user asks for an issue for a specific task, bug, feature, or improvement. If the task is clear, draft or create one issue. If it is vague, clarify the product outcome, constraints, and verification path before drafting.
- Milestone decomposition mode: use when the user asks for issues that fulfill a milestone, PRD, feature plan, or list of user stories. Treat the milestone as the product contract. Every issue should map back to one or more user stories, implementation decisions, or testing decisions. Include explicit dependency callouts in each issue body so later implementation can be sequenced or parallelized without relying on labels.

In milestone decomposition mode, produce a coherent issue set, not a pile of tasks. Split by independently verifiable outcomes, user-visible flow boundaries, risk boundaries, or deep modules. Call out missing milestone detail before creating issues if decomposition would otherwise encode bad assumptions. Prefer fewer, stronger issues over many tiny tickets that only make sense in aggregate.

Common product flow:

```text
/refine -> /milestone -> /github-issue
```

`/refine` sharpens the idea. `/milestone` creates the PRD-like milestone with high-level user stories. `/github-issue` converts that milestone into executable GitHub issues.

Use the repo issue template in `.github/ISSUE_TEMPLATE/product_task.md`:

    ## Goal

    What user or product outcome does this issue unlock?

    ## Product Context

    Why does this matter to the current milestone, product bet, or session-record-as-evidence primitive?

    ## Sequencing

    Depends on:
    - None

    Execution: Sequential | Parallel-ready

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

Use the lightest test layer that protects the behavior:

- Unit tests: deterministic logic such as ignore rules, path filtering, hashing, event normalization, state transitions, and validation helpers.
- Integration / functional tests: CLI-to-backend behavior, session creation, heartbeat, file update/delete sync, write rejection after end, reconnect/rescan.
- Playwright tests: user-visible web flows such as creating a session, seeing join instructions, viewing connection status, inspecting events/files, ending a session.
- Manual checks: early CLI behavior, OS/file watcher quirks, rapid saves, `Ctrl+C`, ignored secret files, and local setup friction.

For Code Maverick M1, minimum done usually means unit coverage for security-sensitive or trust-sensitive rules, functional coverage for the capture/sync spine, light Playwright coverage for the raw interviewer view once UI exists, and a manual CLI checklist for real local folder behavior.

Sequencing guidance for milestone decomposition:

- Each issue should include a `Sequencing` section.
- `Depends on` should be `None` or a checklist of issue numbers/titles that must land first. If issue numbers are not known yet, use stable draft titles and update to issue numbers after creation.
- `Execution` should be `Sequential` when the issue is blocked by another issue or must establish a contract before dependent work begins.
- `Execution` should be `Parallel-ready` when the issue can be worked independently after its listed dependencies are satisfied.
- Do not use labels as the dependency source of truth. Labels may drift and cannot express concrete prerequisites.
- Avoid vague values like `Type: Parallel`; use `Execution` so the field is clearly about implementation planning, not issue category.

When creating the issue, use the detected repo remote unless the user specifies another repo. Attach the relevant milestone if known and supported by the available GitHub tool. Use labels only if they already exist or the user asks for them. After creation, report the issue title and URL/number. If milestone assignment is not possible through the available tool, create the issue without it only after telling the user, or ask them to assign it manually.

## When to Use

Use this skill when the user asks to create, draft, plan, refine, or flesh out GitHub issues. Use it for one specific task, bug, feature, or improvement, or for decomposing a milestone, PRD, feature plan, or user-story list into executable issues.

Do not use it when the user wants to execute the issues. Use `issue-orchestrator` for pulling, sequencing, implementing, verifying, committing, and preparing PRs for a batch of GitHub issues.

## Steps

1. Clarify intent and mode. Identify whether this is single issue mode or milestone decomposition mode. Identify the product outcome, user value, current milestone, and source artifact. If the request is vague, ask targeted questions before creating anything and leverage the `/refine` subagent. Push back on scope creep, weak assumptions, missing edge cases, or issues that mix unrelated work.

2. Research context. Read relevant docs first: `README.md`, `PRD.md`, `POC.md`, `TDD.md`, `GTM.md`, `TRANSPARENCY.md`, and user-flow docs as needed. Search the codebase with `rg` before defining technical requirements. Check existing GitHub issues if duplication is likely. Use subagents for researching the codebase where possible.

3. Shape the issue or issue set. Prefer one clear outcome per issue. Split issues when the work crosses unrelated surfaces, hides sequencing risk, or would be hard to verify. In milestone decomposition mode, create a coverage map from user stories to proposed issues before finalizing and include explicit `Sequencing` callouts in each issue body. Tie requirements back to the milestone and product thesis when relevant.

4. Define tests proportionally. Every issue should include a `Test Plan`. Do not force every test type on every issue. Use `Not applicable` or `Covered by follow-up` when appropriate.

5. Check the product assumptions before creating an issue. Confirm the issue proves the current milestone rather than premature polish, treats the session record as the product primitive rather than incidental telemetry, makes candidate capture boundaries and trust implications explicit, handles secrets and ignored files, is small enough to finish and verify, has observable acceptance criteria, has a test plan matching the risk, and explicitly names important out-of-scope work.

6. Preview before creating. If the user has not explicitly authorized creation after seeing the final issue body or issue set, show the draft and ask for confirmation. If the user already asked to create issues and the requirements are clear, create them after drafting internally. For milestone decomposition, preview the proposed issue list unless the user explicitly asked for immediate creation and the milestone is already complete.
