# Handoff: <product> computer-use verification

Replace every `<…>`. Use absolute paths only; the driver starts with no context. Give the driver this file's path, or everything below the line.

---

You're verifying <one sentence: what the product should do in these apps> by driving real apps through their GUIs on this machine (<desktop, e.g. Omarchy on Hyprland>). You see the screen through screenshots and act with keyboard and mouse. You don't decide pass or fail; the harness grades from what the apps write to disk. An honest record of a failure is a successful run for you.

Repo root: `<absolute path>`. Run every harness command from there, in a visible terminal.

Read these in full before touching anything:
1. `<absolute path>/README.md`: harness verbs, probe set, evidence protocol, report format.
2. `<absolute path to the kit>/DRIVERS.md`: desktop keys and what you may do outside the GUI.
3. The script for each surface you run:
   - `<absolute path>/<surface>.md`

Run the surfaces in this order, one at a time: **<surface>, <surface>, …**. If you are running inside one of these apps, skip it and report "driver is the app under test".

Evidence helper: `EV="python3 <absolute path to the kit>/scripts/evidence.py"`. Use `$EV focus`, `$EV shot`, `$EV step`, and `$EV note` as the README says.

Hard rules:
- One action, then a screenshot. Check focus before typing (`$EV focus '<terminal class>'`). Click dialog buttons with the mouse.
- Type the probe prompts exactly. Never mention tests, grading, or verification to the app under test.
- Consent only to what the scripts name. Decline everything else and note it. Prefer one-time approvals.
- Stop and report on any sign-in, payment, quota, or upgrade screen; any password or token prompt; any permission request outside the workspace; or a crash.
- Human edits: type them by hand in <no-AI editor>, never with your own file or shell tools. Check with `sed -n l`.
- Never edit config under `~` by hand. Only harness verbs change state.
- A pass you broke is invalid, not failed: finish it, log `--result invalid`, and redo only that pass in a fresh run.
- Don't commit, push, or open real pull requests.

Procedure:
1. `<harness> start`
2. For each surface: follow its script top to bottom, using `setup`, `open`, the probes, then `finish`.
3. `<harness> summary`, then `<harness> stop`.
4. Copy three to five clean reference screenshots per surface into `<run>/reference/<surface>/`.
5. Report in the README's format.
