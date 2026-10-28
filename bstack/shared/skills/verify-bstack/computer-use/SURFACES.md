# Surface notes

Per-app details for [the runbook](RUNBOOK.md). Items marked **(verify)** are expected but not yet confirmed on this machine. Check them on screen and record what you actually saw in the run's `SURFACE-NOTES.md`. Unmarked items have been confirmed.

## Shared conventions

- **Terminal:** Super+Return opens a new terminal on Omarchy.
- **File dialogs:** many desktop apps open a GTK file chooser. Press **Ctrl+L** to show a location box, type the full project path, then press Enter. Use the path from `CASE.md`, which is under `/tmp/work-…/`.
- **Typing a slash prompt:** when you type `/how …` or `$how …`, a suggestion popup often appears. Keep typing the full prompt. If Enter picks a suggestion instead of sending, screenshot the result, make sure the input still holds the full prompt, and press Enter again. Log what happened.
- **Quitting Electron apps:** **Ctrl+Q** usually quits fully **(verify)**. Closing the window may leave the app in the tray. After quitting, run the `pgrep` check below. It must print nothing before you relaunch.

## Claude Code terminal UI (`claude-tui`)

- **Launch:** `sh $C/launch.sh` in a new terminal; it runs `claude`.
- **First run:** a folder trust question such as "Do you trust the files in this folder?". Choose the yes/proceed option with the arrow keys and Enter.
- **Submit:** type in the input box at the bottom, then press Enter. Shift+Enter or a trailing `\` adds a newline **(verify)**; prompts here are single-line.
- **Working:** a spinner with an interrupt hint such as "esc to interrupt". **Done:** the hint disappears and the input box is empty and ready.
- **Approvals:** a numbered prompt such as "Do you want to proceed?". Press the number for the one-time "Yes" option, or the "No" option, per the approval rule. Avoid "don't ask again".
- **Model:** shown in the status line, or run `/status` **(verify)**.
- **Compaction:** type `/compact`, press Enter, and wait for a compaction confirmation in the transcript.
- **Quit:** `/exit`, or Ctrl+C twice.
- **Transcript (grader):** `~/.claude/projects/<project path with non-alphanumerics as dashes>/*.jsonl`.

## Codex terminal UI (`codex-tui`)

- **Launch:** `sh $C/launch.sh`; it runs `codex`.
- **First run:** a prompt asking whether to trust this folder. Choose the trust/yes option.
- **Hooks (required before the first prompt):** bstack installs project hooks that Codex keeps disabled until you trust them. Type `/hooks`, press Enter, and approve each hook whose source is this project's `.codex/hooks.json`, for the session start, user prompt submit, subagent start, and pre-tool-use events. Screenshot the hook list before and after. Leave any other hooks as they are. Press Esc to return to the prompt **(verify navigation keys)**.
- **Submit:** type, then press Enter. **Working:** a status line with an interrupt hint such as "Esc to interrupt" **(verify)**.
- **Approvals:** options such as "Yes", "Yes, always", and "No" with key shortcuts **(verify)**. Use the one-time yes.
- **Model:** shown in the header or via `/status` **(verify)**.
- **Compaction:** `/compact`, then wait for a "compacted" confirmation **(verify)**.
- **Quit:** `/quit` or Ctrl+C **(verify)**.
- **Transcript (grader):** `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`, matched by the project path.

## Cursor terminal UI (`cursor-tui`)

- **Launch:** `sh $C/launch.sh`; it runs `cursor-agent`.
- **First run:** a workspace trust prompt. Accept it.
- **Submit:** type, then press Enter.
- **Model:** shown in the footer, for example `Composer 2.5 · 6.6%`.
- **Approvals:** a run/skip style prompt for commands **(verify wording)**. Use the one-time run option per the approval rule.
- **Compaction:** type `/compress`, then press Enter. This is a real native compaction; it fires bstack's `preCompact` hook. Wait for the summary to finish.
- **Quit:** Ctrl+C **(verify; may need twice)**.
- **Transcript (grader):** `~/.cursor/projects/<slug>/agent-transcripts/<id>/<id>.jsonl`.

## Grok terminal UI (`grok-tui`)

- **Launch:** `sh $C/launch.sh`; it runs `grok`.
- **First run:** a folder trust prompt **(verify)**. Accept it.
- **Submit:** type, then press Enter.
- **Approvals:** a permission prompt for shell commands **(verify wording)**. Use the one-time allow.
- **Compaction:** `/compact` (documented in Grok's own `~/.grok/docs/user-guide/04-slash-commands.md`).
- **Model:** shown in the header or status line **(verify)**.
- **Quit:** Ctrl+C or `/exit` **(verify)**.
- **Transcript (grader):** `~/.grok/sessions/<url-encoded project path>/<session>/chat_history.jsonl`.

## Amp terminal UI (`amp-tui`)

- **Launch:** `sh $C/launch.sh`; it runs `amp`. Wait about 10 seconds after the UI appears before the first prompt so bstack's project plugin loads. bstack's reminder is attached on each turn start.
- **Submit:** type, then press Enter **(verify)**.
- **Approvals:** a prompt to allow or deny commands **(verify wording)**. Use the one-time allow.
- **Compaction:** Amp has none. There is no `compaction-resume` case for Amp.
- **Model:** Amp shows a mode such as `smart` or `rush` **(verify)**. Record what it shows.
- **Quit:** Ctrl+C, possibly twice **(verify)**.
- **Transcript (grader):** read with `amp threads export`, matched by working directory.

## OpenCode terminal UI (`opencode-tui`)

- **Launch:** `sh $C/launch.sh`; it runs `opencode`.
- **Submit:** type, then press Enter.
- **Approvals:** a permission dialog with options such as "Allow once", "Always", and "Reject" **(verify)**. Choose "Allow once".
- **Compaction:** `/compact` **(verify)**. If it is not listed, type `/` and look for "compact" or "summarize". Wait for a summary message.
- **Model:** shown in the footer or header **(verify)**.
- **Quit:** `/exit` or Ctrl+C **(verify)**.
- **Transcript (grader):** read with `opencode export <session>`, matched by directory in OpenCode's local database.

## Cursor desktop (`cursor-desktop`)

- **Before launch:** quit Cursor fully with Ctrl+Q **(verify)**, then confirm `pgrep -fa '/cursor' | grep -v cursor-agent` prints nothing. A running Cursor ignores the case environment, so the case would be invalid.
- **Launch:** `setsid sh $C/launch.sh >/dev/null 2>&1 &`. It runs `cursor --new-window .` from the project folder. The window title should show the project folder name.
- **First run:** a workspace trust dialog ("Do you trust the authors of the files in this folder?") **(verify)**. Choose the trust option.
- **Open the agent chat:** **Ctrl+L** **(verify)**, or the chat or agent icon in the top right. Make sure the mode selector says **Agent**.
- **Submit:** type in the chat box, then press Enter.
- **Approvals:** command cards with "Run" and "Skip" style buttons **(verify)**. Click the one-time run option per the approval rule.
- **Model:** the model picker under the chat box **(verify)**.
- **Compaction:** type `/` in the chat box and look for a command named summarize, compress, or compact **(verify)**. Run it, or record that none exists. The grader detects real compaction through bstack's `preCompact` hook.
- **Quit:** Ctrl+Q **(verify)**.
- **Transcript (grader):** expected in the same `agent-transcripts` folder as the CLI **(verify)**. After the first desktop case, run `ls ~/.cursor/projects/*/agent-transcripts | tail` and note whether a new folder appeared for this project.

## OpenCode desktop (`opencode-desktop`)

- **Before launch:** quit it fully, then confirm `pgrep -fa opencode-desktop` prints nothing.
- **Launch:** `setsid sh $C/launch.sh >/dev/null 2>&1 &`.
- **Project:** if it shows a project picker, choose open project or folder and enter the case project path (Ctrl+L in a GTK dialog) **(verify)**. Confirm the project name before sending prompts.
- **Submit, approvals, compaction:** expected to match the OpenCode terminal UI **(verify)**.
- **Transcript (grader):** the same OpenCode database as the terminal UI.

## Codex desktop (`codex-desktop`)

- **Before launch:** if you are Codex driving from inside the Codex desktop app, do not quit your own app. Record `codex-desktop` as blocked with the reason "driver is the app under test", and the user will run it from another computer-use agent. Otherwise quit fully and confirm `pgrep -fa codex-desktop` prints nothing.
- **Launch:** `setsid sh $C/launch.sh >/dev/null 2>&1 &`.
- **Project:** open the case project folder as the workspace for a new thread **(verify)**.
- **Hooks and trust:** expect the same trust and hook approvals as the terminal UI. If the app offers a hooks review, approve only this project's bstack hooks **(verify)**.
- **Submit:** type in the composer, then press Enter. **Compaction:** `/compact` in the composer **(verify)**.
- **Transcript (grader):** the same `~/.codex/sessions` rollouts as the terminal UI.

## Claude desktop, Code tab (`claude-desktop`)

- **Before launch:** this may be the app the user is talking to Claude in. Ask the user first. Then quit fully (File, then Quit, or Ctrl+Q **(verify)**) and confirm `pgrep -fa claude-desktop` prints nothing.
- **Launch:** `setsid sh $C/launch.sh >/dev/null 2>&1 &`.
- **Project:** open the **Code** tab, start a new session, and choose the case project folder as its working folder (folder picker; Ctrl+L to type the path) **(verify)**.
- **Submit:** type in the composer, then press Enter. Approval cards appear inline; choose the one-time allow per the approval rule.
- **Compaction:** `/compact` in the composer.
- **Transcript (grader):** the same `~/.claude/projects` files as the terminal UI.
