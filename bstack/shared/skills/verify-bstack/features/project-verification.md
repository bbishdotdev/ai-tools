# Project verifier lifecycle

New installs save `verification: ask`; upgrades keep their prior choice. `verification off`, `ask`, and `auto` must change only the project-verifier policy, not normal tests or automatic engineering routing. The installed project's `.bstack/instructions.md` points at the packaged verification policy. A requested override for one task takes precedence.

Use a disposable project with one existing `verify-<app>` skill and a feature change. In `off`, the agent should run appropriate checks but leave the verifier unchanged. In `ask`, it should identify the affected user path and propose an exact change before editing. In `auto`, it should update only that path, drive it when the app is available, and keep evidence. A behavior-preserving refactor may need a run but no map edit. A removed feature must not leave a stale recipe. A new substantive feature with no verifier should create a focused one in `auto`; a throwaway prototype should not.

The full `maintain-verification-skill` audit is an explicit task. Ordinary feature work must not re-audit every mapped feature or create a PR unless delivery is authorized. Package/runtime tests can prove setting persistence and binding. Only live feature work can prove that an agent noticed the setting and acted on the right path.
