# Computer-use verification kit

Some product paths only exist in a GUI or an interactive terminal: editor agent panels, desktop apps, trust dialogs, approval cards, slash commands, interrupts, app-managed compaction. Headless drives can't reach them. This kit lets a project verifier hand those paths to a computer-use agent that drives the real app through screenshots, keyboard, and mouse. Code still decides the result.

Use it when a verifier's user path runs through a GUI or interactive surface and no headless driver can reach it. Keep headless drives for everything they can cover; they are cheaper and steadier.

## Roles

| Role | Who | Owns |
| --- | --- | --- |
| Orchestrator | the agent building or maintaining the verifier | harness, probe set, per-surface scripts, handoff, fixes after each report |
| Driver | a computer-use agent, see [DRIVERS.md](DRIVERS.md) | performing scripted steps exactly, evidence, the report |
| Harness | a script beside the verifier | all state: isolation, config snapshots, launch environment, collection, grading |
| Grader | code in the harness | pass or fail, from what the app wrote to disk and from external effects |

The driver never decides pass or fail from screenshots, and never edits config by hand. Screenshot judgment varies run to run; records on disk don't.

## Harness contract

Write one harness per verifier, saved beside it. It exposes these verbs. A batch harness may prepare every case up front and grade them all at the end; the guarantees stay the same.

| Verb | Does | Prints |
| --- | --- | --- |
| `start` | makes a run folder under a gitignored path, records the git revision, starts local services | the run folder |
| `setup <surface> [variant]` | refuses if state from an earlier pass remains; builds an isolated workspace; snapshots every user config the product or app may touch; installs what the case needs | `READY`, then `KEY=value` lines the scripts reference, such as `WORKSPACE=`, `SCREENS=` |
| `open <surface>` | launches the app on the workspace with the case environment and raw-payload recording | nothing the driver must parse |
| `finish <surface>` | collects the app's own records, runs the grader, restores state, diffs config against the snapshot | a short result block |
| `summary` | prints every finished surface in the run | the same blocks |
| `stop` | stops only what `start` launched | nothing |

Required behavior:

- **Isolation.** Each surface gets a fresh workspace outside the repo, so the app under test never sees the harness, the verifier, or the user's real projects.
- **Config cleanliness.** `finish` diffs every snapshotted config. "Byte-identical" is the cleanup bar; any difference is a failure to report, not to fix by hand.
- **Leftover state.** `setup` stops with a plain message when an earlier pass left state behind. The driver reports it; it never cleans up.
- **Running instances.** A desktop app that is already running ignores the launch environment. `open` checks for a running instance and refuses rather than attaching to it.
- **One surface at a time.** Heavy apps in parallel have exhausted memory on real machines. `setup` refuses while another surface is open.
- **Grading from records.** Read the transcripts, hook payloads, databases, or service state the app produces. A surface whose records can't be found grades as incomplete, never as a pass.
- **Fixtures.** Keep raw payloads per run. Sanitized copies become adapter regression tests; the live run then only needs repeating when the app changes.

Run folder layout, per surface:

```
<run>/<surface>[-<variant>]/
  steps.jsonl      driver: one line per action (evidence helper)
  notes.md         driver: surprises, fallbacks, script errors
  screens/         driver: NNN-<slug>.png
  model.txt        driver: model name as the app shows it, or "unknown"
  raw-payloads/    harness: what the app emitted
  records/         harness: what the product stored or the app wrote
  config-diff.txt  harness
  result.json      grader
```

## Probe set

Every surface runs the same probes with the same exact prompts, so results compare across tools and runs. Write them once with [templates/PROBES.md](templates/PROBES.md). A per-surface script says *how* to perform each probe in that app; it never rewrites the prompt.

Include probes for the behaviors GUI surfaces change: a plain agent edit, a shell-made edit, a subagent, slash commands and skills (research, no fixed expectation), an interrupted turn, compaction where the product depends on it, and human-only edits when the product attributes authorship. A probe the app can't perform is a recorded result, not a failure.

## Per-surface scripts

One script per surface, from [templates/TOOL-SCRIPT.md](templates/TOOL-SCRIPT.md). Each holds what a first-time driver needs and nothing it must guess: launch, first-run dialogs with their wording, how to submit, what working and done look like, approval cards, interrupt keys, compaction, quitting, and where the app writes its records. Mark anything not yet seen on screen **(verify)**; the driver confirms or corrects it in `notes.md`, and the orchestrator folds that back in.

## Handoff and report

The driver gets one file, built from [templates/HANDOFF.md](templates/HANDOFF.md), passed by absolute path. It reports in [templates/REPORT.md](templates/REPORT.md)'s fixed format. The orchestrator turns the report into fixes and reruns only the failed or invalid passes.

## Driver rules every script inherits

1. **One action, then look.** Screenshot after each click, keypress, or typed line and confirm the expected change before the next.
2. **Check focus before typing.** Run `evidence.py focus '<class>'` or take a screenshot. A stray Return once sent a harness command into an editor's agent composer and started a turn.
3. **Click dialog buttons with the mouse,** especially right before typing a harness command.
4. **After choosing from a pop-up menu,** wait a second and check the input text; menus can swallow a keystroke.
5. **Type prompts exactly** as the probe set gives them. Never mention tests, grading, or the verifier to the app under test.
6. **Consent only to what the script names:** listed installs, trust for the workspace folder, the app's own writes inside it, and commands the probe names. Decline everything else and note it. Choose one-time approvals over "always".
7. **Stop and report** on sign-in, payment, quota, or upgrade screens, password or token prompts, permission requests outside the workspace, unknown OS dialogs, or crashes. Never work around them.
8. **Human edits are typed by hand** in an editor with no AI features, then checked with `sed -n l <file>`. Never write them with the driver's own file, shell, or patch tools: a driver with capture hooks makes its own writes AI edits.
9. **Never edit user config by hand.** Only harness verbs change state.
10. **A pass the driver broke is invalid, not failed.** Finish it so the harness restores state, log `--result invalid`, then redo only that pass in a fresh run.
11. **Never drive the app you are running inside.** Mark that surface blocked with the reason "driver is the app under test".

## Evidence helper

[`../scripts/evidence.py`](../scripts/evidence.py) writes the driver's evidence into a surface folder. Resolve its absolute path into the handoff.

```sh
python3 <kit>/scripts/evidence.py focus 'ghostty|kitty|alacritty'
python3 <kit>/scripts/evidence.py shot <surface-folder> trust-prompt
python3 <kit>/scripts/evidence.py step <surface-folder> --intent "trust folder" --action "click Trust" --observed "dialog closed" --shot <path>
python3 <kit>/scripts/evidence.py note <surface-folder> "Trust button reads 'Yes, I trust the authors'"
```

`shot` captures the focused window with `grim` on Hyprland. Use `--full` only when a dialog sits outside the app window. `step --result` accepts `ok`, `retry`, `blocked`, `failed`, or `invalid`.

## Durable guide

After a clean run, the driver copies three to five screenshots per surface into `<run>/reference/<surface>/`: trust prompt, approval card, working state, finished answer, and compaction or interrupt marker. Pick only frames showing the app under test, with no notifications, account details, or personal data. The maintainer reviews them, replaces **(verify)** markers in the scripts with what was seen, and commits the curated set beside the scripts.

## Where it fits

| Layer | Covers | Runs |
| --- | --- | --- |
| Unit and fixture tests | adapters and parsers, from saved raw payloads | every commit |
| Headless drives | scriptable CLIs | before release or nightly |
| Computer-use runs | GUI and interactive surfaces | before release, or when an app changes |

CI can run the harness with a hosted computer-use driver once one is available. The handoff, scripts, and grader don't change; only the driver does.
