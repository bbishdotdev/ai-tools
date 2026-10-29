# Computer-use drivers

A driver is any agent that sees the screen through screenshots and acts with keyboard and mouse. The harness, scripts, and grader don't depend on which one. This file covers what changes per driver and per desktop.

## Choosing a driver

| Driver | Runs from | Can't drive | Notes |
| --- | --- | --- | --- |
| Codex desktop with computer use | the Codex desktop app | Codex desktop itself | Give it the handoff path. It may run harness commands in its own shell as well as in visible terminals. |
| Claude computer use | the Claude desktop app, or a cloud session linked to the machine | Claude desktop itself | App access is granted per app. Terminals and the apps under test must be allowed. |
| A hosted driver in CI | a VM with a desktop session | anything needing the user's sign-in | Pre-sign-in the VM's apps with test accounts. Never sign in during a run. |

Run the driver from an app that isn't under test. When every candidate driver is an app under test, split the run: one driver covers the others, a second covers the first.

## What a driver may do outside the GUI

- Run harness verbs and the evidence helper. Prefer a visible terminal for harness verbs, so the step log matches the screen.
- Read the handoff, scripts, and run-folder files.
- Take screenshots with `grim`.

It must not write workspace files, edit config, or run the product's own commands outside the scripted steps. For a driver that has its own capture or hook layer, any file it writes counts as its own AI edit.

## Desktop specifics: Omarchy on Hyprland

- **Super+Return** opens a terminal. When a synthetic Super+Return opens a menu instead, run `omarchy-launch-terminal`.
- Windows tile automatically; click a window to focus it. `hyprctl activewindow` shows the focused window's `class:` and title.
- **Super+W** closes the focused window. Electron apps usually quit fully with **Ctrl+Q**; closing the window can leave them running. Check with `pgrep -fa <name>`.
- In GTK file dialogs, **Ctrl+L** opens a path box.
- A no-AI editor for human edits: `omawrite <file>`, then save with **Ctrl+S** and close with **Super+W**. It saves without a final newline, so check with `sed -n l`. Fallback: `nvim`.

Add a section like this one for each new desktop (GNOME, macOS, Windows) the first time a run happens there, from the driver's notes.
