# <Surface name> run

Proves <product> works in <surface> across the probe set (link your verifier's probe table here): <probes covered>. Skipped: <probe>, because <reason>.

Surface id for the harness: `<surface>`. Layout: <where the conversation and input box are>. Key facts:
- **Submit:** <key>.
- **Interrupt:** <key, and any precondition such as "input box must be empty">.
- **Compaction:** <command>, or "none".
- **Quit:** <command or key; how to confirm the process is gone>.
- **Records the grader reads:** <path or command>.

Mark anything not yet seen on screen **(verify)**.

## 0. Before you start

- <Close running instances; `pgrep -fa <name>` must print nothing.>
- A run must already be started (`<harness> start`).

## 1. Set up

In a terminal, from the repo root, run `<harness> setup <surface>`. Answer `<exact consent questions>` with `<answer>`. Wait for `READY` and note the `KEY=` lines. 📸 `setup-ready`

## 2. Open

<Which terminal, which command.> 📸 `open`. A sign-in screen means stop and report.

## 3. First-run dialogs

- <Dialog wording> → <exact choice, key or click>. 📸 before choosing.
- <What to do if it doesn't appear.>

To send a prompt: <focus the input, type exactly, submit>. A turn is done when <visible signal>. Approval cards look like <wording>; approve per the probe set's rule with <key or button>.

## 4. Probes

One subsection per probe, in order:

### P1

Send P1. <Surface-specific handling.> 📸 `p1-done`

### P5

<Exact interrupt key and timing. What to do if it finished first: note "too late to interrupt" and retry once.> 📸 `p5-interrupted`

## 5. Finish

Quit the app (<how>), confirm it's gone, then `<harness> finish <surface>` from a focused terminal. 📸 `finish-summary`

## Expected results

One line per graded expectation, so the driver can mark PASS or FAIL:
- P1: <…>
- <…>

## Questions for the driver

- <Things the orchestrator doesn't know yet: exact wording, whether a feature exists, where a menu lives.>
