# Behavior scenarios

## Contract

The compatibility matrix claims what bstack does in a host, so each cell must come from a host doing ordinary work, not from a model describing what it would do. A scenario installs the current release into a disposable project, sends prompts a developer would actually type without naming skills, lets the real CLI work with its native hooks and session lifecycle, then grades the resulting repository and trace with code.

| Scenario | Column | What passes |
| --- | --- | --- |
| `explicit-skill` | Skills | `/how` or `$how` loads the packaged skill's bstack policy, explains the real code, and changes nothing. |
| `misleading-bug` | Auto mode | The reported symptom points at a cache; the real defect is a key mismatch with a second affected caller. Hidden tests cover both paths. The router and bug-fix playbook are loaded. |
| `feature-verifier` | Auto mode | With verification set to `auto`, the agent implements the flag, adds a recipe to the existing `verify-invoices` skill, and runs it. Evidence is the verifier's own output file. |
| `adr-rejected` | Auto mode | The obvious speedup is a result cache that the project's ADR rejected. The agent reads the ADR, avoids the rejected option, and meets a distinct-query latency budget that a cache cannot meet. |
| `late-pr` | PR workflows | After two feature turns, "Raise a PR" loads `to-pr`, pushes a branch, and publishes exactly one PR through the bundled helper. Hidden tests run on the pushed head. |
| `direct-pr` | PR workflows | The user asks for `gh pr create --fill` directly. A PR must still be created, and only through the bundled helper. |
| `guard-probe` | PR workflows | A dedicated hook test attempts the raw command once. A native guard record must show it was denied; no PR or project edit may result. Voluntary use of the helper cannot satisfy this check. |
| `compaction-resume` | Hooks | The first turn explains without editing. A real native compaction follows. The next turn rereads the router or the playbook it selected, then fixes the defect. |

The Hooks column also requires the host's delivering reminder hook on every user turn of the ordinary-work scenarios: `UserPromptSubmit` for Codex and Claude Code, the after-tool fallback for Grok, the session or after-tool hook for Cursor, `userPromptSubmitted` for Copilot, `agent.start` for Amp, and the system-prompt transform for OpenCode. The separate `guard-probe` verifies a pre-tool denial; it cannot require an after-tool reminder when its only tool was prevented from running. That is execution evidence, not a receipt-based delivery proof; `verify.py live` keeps that narrower claim.

Checks are split in two. Integration checks ask whether bstack's instructions, workflows, and hooks reached the model and were used: router and playbook reads, skill policy reads, ADR reads, verifier upkeep, `to-pr` and helper publication, first-turn scope, hook delivery, and compaction recovery. Quality checks ask whether the model then did the work well: hidden-test outcomes, avoiding the rejected alternative, and correct answers. The matrix uses integration checks from the most recent recorded run of each scenario. `matrix.py` writes one row per host and model to `bstack/audit/model-results.md`, with integration and quality passes in each cell, which is where model recommendations come from. Use `--model host=model` to measure another model on the same host.

A cell is Supported only when every mapped scenario passed its integration checks in every repeat of the recorded run. A binding without that proof is Partial. A host without a binding is Not supported. Matrix colors are never edited by hand.

## Isolation

Each CLI runs in its own full-access mode, because that is the behavior under test: Codex `danger-full-access`, Claude Code and Grok `bypassPermissions`, Cursor `--force` with its sandbox disabled, Copilot `--allow-all`, Amp `amp.dangerouslyAllowAll`, and OpenCode `--auto`. One outer bubblewrap jail contains the process instead. The root filesystem is read-only. Only the disposable workspace and the seven CLIs' own state paths are writable, so sign-ins and session resume work. `~/.ssh` and `~/.config/gh` are replaced with empty mounts. A host's native sandbox and approval prompts are therefore not exercised.

Codex loads project hooks only for a project trusted in `~/.codex/config.toml`. The jail mounts a copy of that file over the original with trust for the workspace and its hook hashes from `hooks/list`, so the user's file never changes.

Grading uses a separate bubblewrap worker with no CLI state or host home directory. It mounts only system executables and libraries, the requested candidate inputs as read-only directories, and one grading output directory when needed. Its environment contains a fixed set of runtime and Git settings. It has its own network namespace, temporary directory, home directory, process namespace, and device mounts. Each process has CPU, address-space, file-size, open-file, and core-dump limits. Missing isolation support fails grading; there is no host execution fallback.

Candidate Git inspection, pushed-head cloning, candidate file reads, snapshot preparation, and hidden tests all run inside that worker. Bind roots are opened without following symlinks, including their parent paths. Symlinks inside candidate files resolve against the worker's filesystem, so they cannot read credentials or write through to paths outside the mounted grading output.

Projects live in fresh temporary directories with project-shaped names. Expected answers, hidden tests, and graders stay in this checkout; any candidate path or command that touches the checkout fails `stayed_in_project`. This directory is outside `verify-bstack/scripts/`, so the packager does not ship graders into installs.

`gh` is a copy of `fake_gh.py` inside each workspace, backed by a bare repository. A shimmed `git-remote-https` routes `https://github.com/acme/<project>.git` to that repository, so the remote looks real while nothing reaches GitHub. Global and system git config are replaced, and GitHub tokens are removed from the environment. Copilot therefore needs its own `/login`; it cannot borrow `gh` credentials.

User-level instructions still load from the real home directory, and Cursor and Grok also run the user's Claude Code hooks from `~/.claude/settings.json`. Hooks that only record or notify do not change agent context, but treat user-level instructions and hooks as a known confound.

## Drive

```sh
python3 bstack/shared/skills/verify-bstack/behavior/run.py --list
python3 bstack/shared/skills/verify-bstack/behavior/run.py --tools codex claude --repeats 3 --record
python3 bstack/shared/skills/verify-bstack/behavior/matrix.py
```

Live runs spend model usage and need authorization. Use `--scenarios` and `--tools` for an adapter change, and the full suite with `--repeats 3` before a release. The focused `guard-probe` is an explicit test of enforcement; the other prompts ask for ordinary developer work. `matrix.py --check` fails when the committed SVG no longer matches the recorded results.

Every attempted scenario is recorded, including setup errors and provider limits. Those attempts do not count as graded model-quality failures, but prevent a current Supported claim until a clean rerun. A quota failure never silently reuses an older passing result under a newer date. Guard records are opt-in test instrumentation and contain decisions and argument types, not commands or prompts.

Each case writes prompts, native streams, hook records, `observed.json`, the normalized trace, the forge state, grading output, and `result.json` under `.bstack/verification/<run>-behavior-<id>/`. Workspaces are kept for inspection. After changing a parser or check, rerun grading without model calls:

```sh
python3 bstack/shared/skills/verify-bstack/behavior/run.py --regrade .bstack/verification/<run> --record
```

The first verdict is kept as `result.original.json`.

## Limits

Compaction is native: Codex through its app-server, Claude Code and Grok through `/compact` with a `compact_boundary` event, Copilot through `/compact` confirmed by `session.compaction_complete` in its session log, and OpenCode through its server's summarize endpoint. Cursor's headless mode treats slash commands as ordinary prompts, so the harness drives its interactive `/compress` through a pty and requires bstack's `preCompact` hook record. Amp has no compaction; its per-turn `agent.start` reminder is the recovery path, so the compaction scenario does not apply to it.

Headless runs skip interactive trust: Claude Code `-p` treats the folder as trusted, Cursor receives its trust flag, Copilot gets `COPILOT_ALLOW_ALL=true`, and the jail supplies Codex trust. Interactive sessions can hold back every hook until the user trusts the folder, so a headless pass does not establish first-run interactive behavior. Desktop surfaces reuse the scenarios and graders but need a person to submit the prompts. The local forge proves workflow behavior, not GitHub upload or permissions. One pass per scenario is weak evidence; record at least three repeats.
