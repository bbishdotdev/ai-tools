# Project verification

A project verifier is a `verify-<app>` skill that starts the real app, follows a user path, and saves evidence of the result. It gives an agent a repeatable way to check its work. It is different from adding a unit test for every code change.

The project's verification setting is stored in `.bstack/config.json`. Check it before changing a verifier. The user can override it for a task.

| Setting | During feature or bug work |
| --- | --- |
| `off` | Do not create or edit a verification skill on your own. Still perform the task's normal checks. |
| `ask` | Identify the affected user path and propose the specific verifier change. Wait for the user's answer before changing the verifier. This is the default for a new install. |
| `auto` | Create or update the affected verifier recipe within the authorized task, then run it when the app is available. Do not ask again for that routine work. |

Use `python3 <project-root>/.bstack/package/scripts/bstack.py verification status --project <project-root>` to read the setting. Replace `status` with `off`, `ask`, or `auto` to change it. Setup can select the mode; upgrades keep the current choice.

For an existing verifier, first check whether the changed behavior is already covered. Update only the affected feature file and driver steps when the user-facing contract changed. A code-only refactor may need a verifier run but no map edit. A removed feature needs its obsolete recipe removed. Run the affected path and keep its evidence. Do not run a full feature-map audit for every change.

For a new product feature with no verifier, use [create-verification-skill](../../engineering/create-verification-skill/SKILL.md) when the setting is `auto`, or offer it when the setting is `ask`. A throwaway prototype, exploration, or tiny copy change does not trigger automatic creation. If the app cannot run or a required account is unavailable, record the exact limit and complete the checks that are possible. Do not call an unrun recipe verified.

Use [maintain-verification-skill](../../engineering/maintain-verification-skill/SKILL.md) for an explicit full audit of the verifier and every mapped feature. That is separate from routine implementation.
