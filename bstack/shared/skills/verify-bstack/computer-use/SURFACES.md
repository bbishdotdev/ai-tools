# Surface notes

Per-app details for [the runbook](RUNBOOK.md). Items marked **(verify)** are expected but not yet confirmed on this machine. Check them on screen and record what you actually saw in the run's `SURFACE-NOTES.md`. Unmarked items have been confirmed.

## Shared conventions

- **Terminal:** Super+Return opens a new terminal on Omarchy. Ghostty pastes with **Shift+Insert**. A clipboard provider must stay alive until the paste lands; a short-lived clipboard command pastes nothing.
- **Small tiles:** new windows can open as a small tile, and the titlebar maximize button may do nothing. **Super+Alt+F** maximizes the focused window.
- **File dialogs:** many desktop apps open a GTK file chooser. Press **Ctrl+L** to show a location box and type the full project path from `CASE.md`. GTK appends a trailing slash; that is fine. Click **Select** (or **Open**) with the mouse rather than pressing Enter. The first click often only focuses the button, so screenshot and click again if the dialog is still open.
- **Exact paths:** every fixture project is named `notes`, `meter`, `roster`, and so on, and older workspaces with the same name exist under `/tmp`. Confirm the full `/tmp/work-…/<name>` path, never only the folder name.
- **Typing a slash prompt:** when you type `/how …` or `$how …`, a suggestion popup often appears. Keep typing the full prompt. If Enter picks a suggestion instead of sending, screenshot the result, make sure the input still holds the full prompt, and press Enter again. Log what happened.
- **Quitting Electron apps:** each desktop section below gives the exact quit flow. Helper processes can outlive the window by about twenty seconds. Before relaunching, `status` must not report a `STALE` instance (see the runbook).

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

Confirmed in run `20261029T125650Z-interactive-200a52`, with reference screenshots in that run's `reference/cursor-desktop/`.

- **Before launch:** `status` must say `launched: no` with no `STALE` line. A running Cursor ignores the case environment, so the case would be invalid.
- **Launch:** `setsid sh $C/launch.sh >/dev/null 2>&1 &`. It runs `cursor --new-window .` from the project folder. The title reads `<name> - Cursor` and the Agent composer is usually already open. No trust dialog appeared.
- **Project:** hover `README.md` in the Explorer; the tooltip shows the full path. Check that it matches `CASE.md`.
- **Window:** Super+Alt+F maximizes the tile. **Ctrl+Alt+E** expands the Agent chat. Agent mode was already selected.
- **Model:** the picker under the composer, for example `Grok 4.7 High Fast`. Do not change it.
- **Submit:** click the composer, type the prompt, check it, press Enter once. Full `/how …` prompts submitted without picking a suggestion.
- **Working:** `Planning next moves`, `Thinking`, or `Waiting for subagent`, a tab spinner, and a stop button. Subagent cards change label while they run. **Done:** empty composer, no stop button or spinner, subagent cards say `Completed`, and the answer header says `Worked for <time>`. Starting a new turn collapses the previous turn's tool details.
- **Approvals:** none appeared in fourteen cases, including `gh pr create`.
- **Compaction:** click the composer first (after scrolling it loses focus and `/` does nothing), type `/summ`, and click **Summarize** ("Summarize the conversation"). It runs immediately; no Enter. Wait for `Chat context summarized` and idle.
- **Quit:** Ctrl+Q opens `Quit Cursor?`. Leave `Don't ask again` unchecked and click **Quit** with the mouse.
- **Transcript (grader):** `~/.cursor/projects/<slug>/agent-transcripts/`, the same as the CLI. Cursor adds context messages (for example `<available_subagent_types>`) after compaction; the grader counts only `<user_query>` messages as turns.

## OpenCode desktop (`opencode-desktop`)

- **Before launch:** `status` must say `launched: no` with no `STALE` line. Ctrl+Q quits with no dialog.
- **Launch:** `setsid sh $C/launch.sh >/dev/null 2>&1 &`. The app ignores the launch folder and opens its last project, often `~/Documents/Default Project`.
- **Project:** click the project selector below the composer, then **Add project**. In the GTK `Open project` dialog press Ctrl+L, type the exact path, and click **Select** (twice if the first click only focuses it). The footer then shows the project path; it must match `CASE.md` exactly.
- **Project identity:** OpenCode treats repositories with the same `origin` URL as one project and reopens the first path it saw. Cases prepared before the fix in `run.py` all used `acme/notes`, so every `notes` case collapsed into one old project. Newly prepared cases use a unique `acme-<id>/<name>` remote. If the footer still shows another `/tmp/work-…` path, block the surface and note the path.
- **Model:** shown under the composer, for example `OpenCode / Flint 40B Free`. It may differ between projects. Do not change it.
- **Submit, approvals, compaction:** expected to match the OpenCode terminal UI **(verify)**.
- **Transcript (grader):** the same OpenCode database as the terminal UI.

## Codex desktop (`codex-desktop`)

- **Before launch:** if you are Codex driving from inside the Codex desktop app, do not quit your own app. Record `codex-desktop` as blocked with the reason "driver is the app under test", and the user will run it from another computer-use agent. Otherwise quit fully and confirm `status` shows no `STALE` line.
- **Launch:** `setsid sh $C/launch.sh >/dev/null 2>&1 &`.
- **Project:** open the case project folder as the workspace for a new thread **(verify)**.
- **Hooks and trust:** expect the same trust and hook approvals as the terminal UI. If the app offers a hooks review, approve only this project's bstack hooks **(verify)**.
- **Submit:** type in the composer, then press Enter. **Compaction:** `/compact` in the composer **(verify)**.
- **Transcript (grader):** the same `~/.codex/sessions` rollouts as the terminal UI.

## Claude desktop, Code tab (`claude-desktop`)

Confirmed in run `20261029T125650Z-interactive-200a52`, with reference screenshots in that run's `reference/claude-desktop/`.

- **Before launch:** this may be the app the user is talking to Claude in. Ask the user first. Ctrl+Q quits at once when idle. While a session is working it shows `Claude is still working` with **Quit anyway**, **Wait for Claude**, and **Cancel**; click **Quit anyway** only with the user's OK (the first click may only focus it). Helpers take about twenty seconds to exit; wait until `status` shows no `STALE` line.
- **Launch:** `setsid sh $C/launch.sh >/dev/null 2>&1 &`. It opens at `New session` and remembers the previous folder, so always select the case folder.
- **Window:** maximize with Super+Alt+F and collapse the sidebar so unrelated chats stay out of screenshots.
- **Project:** click the folder selector below the composer, then **Open folder...**. In GTK `Select folder` press Ctrl+L, type the exact path, and click **Select** (twice if needed). A `Trust this workspace?` dialog shows the full path and `Execution allowed by: .claude/settings.json`; check the path and click **Trust workspace**.
- **Environment:** Claude Desktop puts your login shell's `PATH` ahead of the launch `PATH`. The launch script sets `CLAUDE_ENV_FILE`, which Claude sources before each command, to put the fake `gh` first again. After trusting the workspace, `status` must print `gh: fake forge`.
- **Model and mode:** for example `Opus 5.5 Medium`, with `Auto` permissions and `Worktree`. Leave them unchanged.
- **Submit:** click the composer, paste the prompt, check it, press Enter once.
- **Working:** orange dots, elapsed seconds, a token count, and a square stop button. **Done:** `Type / for commands`, the microphone icon, and no stop button. The parent composer can look idle while a subagent still runs; wait for `Message from subagent` and the parent's final answer.
- **Approvals:** none appeared in five cases. End-of-turn buttons such as **Commit changes**, **Leave uncommitted**, or **Commit and PR** are agent offers, not approvals; do not click them.
- **Sign-in requests:** if the agent asks you to run `gh auth login` or shows a **Logged in** button, the fake `gh` was not reached. Do not sign in. Run `status`, log the case `invalid` with its `gh:` line, and stop the surface.
- **Compaction:** `/compact` in the composer **(verify)**.
- **Transcript (grader):** the same `~/.claude/projects` files as the terminal UI.
