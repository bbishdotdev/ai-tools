# Computer-use verification

## Contract

Headless runs prove bstack works when a CLI is scripted. Developers use desktop apps and interactive terminal UIs, where trust dialogs, approval prompts, slash commands, and app-managed compaction behave differently. This feature runs the same behavior scenarios through those surfaces with a computer-use agent driving the screen, and grades them with the same code as the headless suite.

The roles are split on purpose:

- **The harness prepares.** `behavior/interactive.py prepare` builds each case: a disposable project with bstack installed, the fake GitHub forge, and a `launch.sh` that starts the app or terminal UI with the case environment. Each case also gets a `CASE.md` with the exact prompts.
- **The agent drives.** It follows [the runbook](../computer-use/RUNBOOK.md) and [surface notes](../computer-use/SURFACES.md). It performs the steps, applies a fixed approval rule, and records screenshots and a step log with the [computer-use kit](../../../../engineering/create-verification-skill/computer-use/README.md)'s evidence helper.
- **The harness grades.** `behavior/interactive.py grade` reads the transcript each app writes to disk, plus the hook records, forge state, and project files, then runs the headless checks. The agent never judges pass or fail from screenshots.

Transcript sources, confirmed for the terminal UIs:

| Host | Source |
| --- | --- |
| Claude Code | `~/.claude/projects/<slug>/*.jsonl` |
| Codex | `~/.codex/sessions/**/rollout-*.jsonl` matched by cwd |
| Cursor | `~/.cursor/projects/<slug>/agent-transcripts/` |
| Grok | `~/.grok/sessions/<encoded path>/*/chat_history.jsonl` |
| Amp | `amp threads export`, matched by working directory |
| OpenCode | `opencode export`, found through OpenCode's session database |

Desktop apps are expected to write to the same stores. A case without a readable transcript grades as incomplete, never as a pass.

Results record under surface keys: `<host>-tui` rows render as an "Interactive CLI" group once recorded, and `<host>-desktop` rows fill the desktop group. Each case records the model the agent read from the app in `model.txt`.

## Evidence

Every case folder keeps `steps.jsonl`, with one line per action giving intent, action, observation, result, and screenshot. It also keeps active-window screenshots in `screens/`, the agent's `notes.md`, the graded `result.json`, and the normalized transcript in `turn-*/`. Each run ends with `SURFACE-NOTES.md`, recording what the agent actually saw, and a `reference/` folder of up to five screenshots per surface.

Maintainers fold `SURFACE-NOTES.md` back into SURFACES.md, replacing **(verify)** markers with confirmed steps. They curate reference screenshots into the guide only after checking them for personal data. Evidence stays under gitignored `.bstack/verification/` until curated.

## Limits

These runs are not jailed. The approval rule and the fake forge keep them inside `/tmp/work-…` and away from GitHub, so supervise the first run on a new machine. Each desktop app must start fresh from `launch.sh`, because a running instance ignores the case environment. That means the Claude desktop app, which may be hosting the user's own session, must be quit with the user's consent. A Codex agent cannot test the Codex desktop app it runs inside. The interactive grader counts reminder hooks per case rather than per turn. First-turn read-only checks rely on transcript edit calls, so a shell-based write in that turn is not caught. VS Code and Copilot are out of scope until a paid Copilot plan is available.

This feature is an instance of the general [computer-use kit](../../../../engineering/create-verification-skill/computer-use/README.md), which any project verifier can use.
