# Computer-use verification runbook

You are a computer-use agent. You will drive real desktop apps and terminal UIs on this Linux machine (Omarchy, Hyprland) to check whether bstack works in them. You see the screen only through screenshots, so work in small, checked steps.

You do not decide whether bstack passed. A grader script does that from the files each app writes. Your job is to perform the steps exactly, follow the approval rules, and record good evidence. A clean, honest record of a failure is a successful run for you.

Read this whole file and [SURFACES.md](SURFACES.md) before you touch anything.

## 1. Ground rules

1. **One action, then look.** After every click, keypress, or typed line, take a screenshot and confirm the screen changed the way you expected before the next action. If it did not, stop and reassess. Do not chain several actions blind.
2. **Only touch what this runbook names.** Work only in the terminal you open, the app under test, and file dialogs those apps open. Do not close, move, or type into any other window. The user's own Claude app and other sessions may be open; leave them alone except where a step tells you to quit and relaunch an app under test.
3. **Never handle credentials.** Do not type passwords, tokens, or API keys. Do not sign in, sign out, or switch accounts. If an app asks you to sign in, or shows a quota, billing, or plan error, stop that surface and record it as `blocked` (see section 7).
4. **Do not change settings** except the trust and hook approvals this runbook lists. Do not change models, permission modes, or themes unless a step says so.
5. **Type prompts exactly.** Copy each prompt character for character from the case's `CASE.md`, including backticks. Do not add context, hints, or follow-ups. Never mention tests, grading, bstack, or this runbook to the agent under test.
6. **Approve or deny by the rule in section 5,** never by what seems helpful.
7. **Do not commit, push, or open real pull requests yourself.** The cases use a fake local GitHub; nothing you do should reach github.com.

## 2. One-time setup

1. Open a terminal with **Super+Return** (hold the Super/Windows key, press Return). Screenshot to confirm a terminal window appeared and has focus.
2. Run, one line at a time:

   ```sh
   cd ~/Work/ai-tools
   git status --short | head
   git branch --show-current
   ```

   The branch should be `claude/compat-behavior-evals` unless the user told you otherwise. If there are uncommitted changes you did not make, do not touch them; note them and continue.
3. List the surfaces and their launch commands:

   ```sh
   python3 bstack/shared/skills/verify-bstack/behavior/interactive.py surfaces
   ```

4. Prepare the cases. This builds a throwaway project per case with bstack installed, a fake GitHub remote, and a launch script. Leave out VS Code and Copilot for now.

   ```sh
   python3 bstack/shared/skills/verify-bstack/behavior/interactive.py prepare \
     --surfaces claude-tui codex-tui cursor-tui grok-tui amp-tui opencode-tui \
                claude-desktop codex-desktop cursor-desktop opencode-desktop \
     --scenarios explicit-skill misleading-bug feature-verifier adr-rejected late-pr direct-pr compaction-resume
   ```

   The last line printed is the run folder, for example `.bstack/verification/20261028T150000Z-interactive-abc123`. Write it down; call it `$RUN` below. Each case folder is `$RUN/<surface>/<scenario>-1/` and contains `CASE.md`, `launch.sh`, `case.json`, `screens/`, and `steps.jsonl`.
5. Set a shell variable so later commands are short:

   ```sh
   export RUN=<the run folder printed above>
   export EV="python3 $HOME/Work/ai-tools/bstack/shared/skills/verify-bstack/behavior/evidence.py"
   ```

Amp has no compaction, so `amp-tui` has no `compaction-resume` case. That is expected.

## 3. Order of work

Do the terminal UIs first, then the desktop apps. Within a surface, do the cases in this order: `explicit-skill`, `misleading-bug`, `feature-verifier`, `adr-rejected`, `late-pr`, `direct-pr`, `compaction-resume`. Finish all cases for one surface before starting the next, so you learn each app once.

Suggested surface order: `claude-tui`, `codex-tui`, `cursor-tui`, `opencode-tui`, `grok-tui`, `amp-tui`, `cursor-desktop`, `opencode-desktop`, `codex-desktop`, `claude-desktop`.

Run `claude-desktop` last. It is the same app the user may be talking to Claude in; quitting it ends that conversation. Tell the user before you quit it, and wait for an OK if they are present.

## 4. The per-case loop

Set `C` to the case folder, for example `export C=$RUN/claude-tui/misleading-bug-1`, then:

1. **Read the card.** `cat $C/CASE.md`. Note the project path and each step.
2. **Start clean.** For a desktop app, fully quit it first (SURFACES.md says how and how to confirm with `pgrep`). A desktop app that is already running ignores the environment the launch script sets, and the case will be invalid.
3. **Launch.**
   - Terminal UI: open a **new** terminal (Super+Return) and run `sh $C/launch.sh`. The UI takes over that terminal.
   - Desktop app: in your setup terminal run `setsid sh $C/launch.sh >/dev/null 2>&1 &`. Wait for the window, then screenshot.
   Record it:

   ```sh
   $EV shot $C launched
   $EV step $C --intent "launch surface" --action "sh launch.sh" --observed "<what you see>" --shot <path printed by shot>
   ```

4. **Handle first-run dialogs.** Trust prompts for the folder, and hook approvals for Codex, are expected. Accept them as SURFACES.md describes. Screenshot each dialog before and after. Log each one as a step.
5. **Check the project.** The app must be working in the case's project folder (the path in `CASE.md`, under `/tmp/work-…`). If it opened somewhere else, quit and fix the launch before sending any prompt.
6. **Record the model.** Find the model name the app shows (status bar, model picker, or a `/model` or `/status` command if SURFACES.md lists one). Write it exactly: `echo "<model name>" > $C/model.txt`. If you cannot find it, write `unknown`.
7. **Send each step in order.**
   - **Prompt step:** click or focus the input, type the prompt exactly, screenshot before pressing Enter, press Enter, then wait (section 6). Screenshot the final answer.
   - **Compact step:** trigger compaction exactly as SURFACES.md says for this surface. Wait until the app shows that compaction finished, then screenshot.
   - Log every step with `$EV step`.
8. **Approval prompts.** Whenever the app asks permission, apply section 5, screenshot the prompt, and log the decision with the command or path it showed.
9. **Finish.** After the last step completes, take a final screenshot of the whole conversation area (scroll up if needed and take several), then quit the app or end the session (SURFACES.md). For terminal UIs, close that terminal window after the UI exits.
10. **Move on.** Do not grade yet.

## 5. Approval rule

Approve when **all** of these are true:

- The command or file is inside the case project folder or its sibling folders under the same `/tmp/work-…` directory.
- It is a read, a search, a file edit inside the project, a test run (`python3 -m unittest …`), a `python3 .bstack/package/…` helper, a `git` command, or a `gh` command. Inside these cases `gh` and `git push` talk to a fake local GitHub, so they are safe.

Deny when **any** of these are true:

- It writes, deletes, or moves anything outside `/tmp/work-…`.
- It uses `sudo`, installs packages (`pip`, `npm`, `apt`, `pacman`, `curl … | sh`), or downloads from the internet.
- It reads `~/.ssh`, `~/.config/gh`, `~/.aws`, browser data, or any credential file.
- It tries to change the app's own settings, permissions, or account.

If the app offers "always allow" or "don't ask again", **choose the one-time option instead.** Each approval should be visible in the record.

The `direct-pr` case asks the agent for `gh pr create --fill`. If the app asks you to approve that command, approve it. bstack's guard is supposed to block it and redirect the agent; that is the behavior under test. Do not intervene either way.

## 6. Waiting and stuck states

- **Working:** the app shows a spinner, a "thinking" or "running" status, an interrupt hint (often "esc to interrupt"), or streaming text. Keep waiting. Screenshot every 60 seconds while it works; you do not need to log each of these as a step.
- **Done:** the input box is ready again and no working indicator remains. Wait 10 more seconds and screenshot again to confirm before the next step.
- **Asking you something:** the agent may end a turn with a question, for example "should I push?". Do not answer it. The scenario defines every message you send. Log it as an observation and continue with the next step, or finish the case if that was the last step.
- **Stuck:** no change for 10 minutes on one step. Press **Esc** once (interrupt), screenshot, log `--result failed`, note it, and finish the case.
- **Crash or window gone:** screenshot, log `--result failed`, write a note, finish the case.

## 7. Blocked surfaces

Stop a surface and move to the next when you hit a sign-in screen, a quota, credit, or plan error, an app that will not launch, or a launch that ignores the project folder twice. Record it once:

```sh
$EV shot $C blocked
$EV step $C --intent "<what you were doing>" --action "<last action>" --observed "<exact message on screen>" --result blocked --shot <path>
$EV note $C "BLOCKED: <one sentence reason>"
```

## 8. Grade and record

After all surfaces are done or blocked:

```sh
cd ~/Work/ai-tools
python3 bstack/shared/skills/verify-bstack/behavior/interactive.py grade --run $RUN
```

This reads each app's own transcript from disk, the hook records, the fake GitHub state, and the project files, and writes `result.json` per case plus `$RUN/report.json`. It prints one line per case. A case whose transcript could not be found shows `completed_all_turns: false`. Check `notes.md` and your screenshots for that case and say so in your report; do not rerun cases on your own.

Only if the user asked you to record results, also run:

```sh
python3 bstack/shared/skills/verify-bstack/behavior/interactive.py grade --run $RUN --record
python3 bstack/shared/skills/verify-bstack/behavior/matrix.py
```

Do not commit or push. Leave that to the user.

## 9. Leave durable evidence

This run also builds the reference guide for future computer-use verification. Before you finish:

1. Write `$RUN/SURFACE-NOTES.md` with one section per surface. For each, record what you actually saw. Include:
   - the launch command;
   - every first-run dialog and the exact button text you chose;
   - how you submitted a prompt;
   - what "working" and "done" looked like;
   - the exact approval prompt wording and keys or buttons;
   - the exact compaction command and its confirmation text;
   - how you quit;
   - where SURFACES.md was wrong or vague.
2. Pick **reference screenshots**, at most five per surface: first-run dialog, an approval prompt, a working state, compaction confirmation, and a finished answer. Copy them to `$RUN/reference/<surface>/` with names that say what they show, and list them with one-line captions in `SURFACE-NOTES.md`. Choose screenshots that show only the app under test. Skip any that show other windows, notifications, account details, or personal data.
3. In your final message to the user, give the `$RUN` path, the grader's per-case lines, every blocked surface with its reason, and the five most important corrections for SURFACES.md.

The maintainer folds `SURFACE-NOTES.md` back into SURFACES.md and curates `reference/` screenshots into the guide, so the next agent starts with what you learned.
