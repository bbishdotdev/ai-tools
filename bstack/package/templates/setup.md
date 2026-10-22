---
name: setup-bstack
description: Configure or check bstack's local project bindings and selected agent tools.
disable-model-invocation: true
metadata:
  package: bstack
---

# Set up bstack

If the request is only to enable, update, or check personal memory, go directly to **Optional personal memory** below. Do not reconfigure project bindings or initialize or serve the workspace for that request.

Resolve the installed package from the [controller](../../scripts/bstack.py). Target the Git repository containing the work, even if this skill was discovered from a parent workspace. A parent-only setup does not bind a child repo's Claude skills or auto hook. Run the controller with the requested project and hosts:

```sh
python3 <absolute-package-path>/scripts/bstack.py setup --project <project-root> --hosts codex claude cursor grok
```

Setup creates direct public skill entries and project instructions. New projects start with automatic engineering routing on and project verification set to `ask`. Upgrades keep both choices. Use `--auto off` for manual routing or `--verification off|ask|auto` to choose how project verifiers are maintained. Explain these choices when changing them: auto routing picks relevant engineering workflows for ordinary prompts; verification `ask` proposes a verifier change before making it, while `auto` maintains affected verifier paths during feature or bug work. Run `doctor --project <project-root>` to check package integrity and bindings. This check does not prove that a host loaded or trusted its hooks.

If Codex has `[features] hooks = false`, the default auto setup stops with a clear choice: enable hooks or pass `--auto off`. Manual setup can finish with that setting, but its Codex PR creation guard cannot run until hooks are enabled. Do not silently change an explicit host setting.

When the source controller belongs to a parent BStack install, `setup` copies that exact package into the child repo. Use the child's own `.bstack/package/scripts/bstack.py` for subsequent `auto` and `doctor` commands. Start a fresh Claude Code desktop Code chat rooted in the child after changing bindings.

When project setup and `doctor` succeed, recommend `bstack-guide` as a short introduction. If the user asked for a walkthrough as part of setup, read the installed `shared/bstack-guide/SKILL.md` and give it. If new bindings require a fresh session, recommend invoking the guide there. Skip this recommendation for a memory-only request.

The seven-rule [baseline](../references/baseline-agents.md) is written into managed blocks in `AGENTS.md` and, when Claude is selected, `CLAUDE.md`, including new files. Existing project text and shared symlinks are preserved. Baseline rules apply independently of auto mode. Do not run a host's `/init` automatically. Offer optional project-specific guidance outside the blocks after setup; installation does not depend on it. If the user requests that guidance or a native init, preserve the blocks and run `doctor` afterward. A changed or missing block must be restored from its exact record in `.bstack/config.json` while preserving new project text; setup refuses to overwrite that conflict.

If the user wants project-specific PR priorities or human-review paths, offer [configure-pr](../configure-pr/SKILL.md). Its committed policy is optional. Setup does not create an empty policy file or copy one from the package without a request.

For local planning and tickets, initialize the project's workspace before creating optional role or adapter configuration:

```sh
python3 <absolute-package-path>/workspace/cli.py --project <project-root> init
python3 <absolute-package-path>/workspace/cli.py --project <project-root> serve
```

The workspace stores maps, specs and Kanban tickets privately under its owning project's `.bstack/workspace/`. Git worktrees share that owner's store. Read [workspace access](../references/workspace.md) before writing artifacts. Read existing domain documents and ADR conventions when work needs them; setup does not create a second documentation system.

Ordinary manual work needs no model configuration. The default delegation policy remains `inherit-parent`. Do not ask every new installer to choose optional models. When someone first chooses a model-backed workflow, explain its roles and run that workflow's live doctor before it starts. `review-pr` has two independent reviewers and a third model that checks their findings; its defaults use Claude Code and Codex. Autonomous grilling has one model challenging the plan and another answering. `to-pr` prefers Codex for an explanatory image when the project permits Codex to see its code, but can use the current host's image tool or a useful diagram when that is unavailable. Run `python3 <absolute-package-path>/scripts/bstack.py doctor --project <project-root> --live --workflow review-pr|grilling|to-pr` for the chosen and permitted workflow. A failed optional workflow should not block ordinary setup.

If a developer's CLI requires a wrapper, ask for its actual terminal command. For example, run `python3 <absolute-package-path>/shared/model_cli.py --project <project-root> configure --cli claude --command 'launch claude -- {args}'`. The helper saves the argument prefix privately in `.bstack/model-clis.json`. It does not use a shell, so arguments after `{args}` are passed separately. Recheck the selected workflow live after changing it. Never silently try the plain binary again or replace the chosen model after a wrapper or login failure. Auto routing does not grant product or ADR decision authority. Wayfinder and tickets have [independent adapter choices](../references/work-adapters.md), each defaulting to the implemented local adapter. External adapters remain unsupported until implemented and verified; a Git remote is not a provider selection.

## Optional personal memory

Only when the user requests shared memory, run `python3 <absolute-package-path>/scripts/bstack.py memory setup` to preview user-wide configuration. Read [portable memory setup](../memory/references/installation.md), review the changes, then apply the unchanged plan with `memory setup --apply-plan <digest>` within that authorization. Check `memory status` afterward. Engineering auto mode and ordinary project setup do not enable memory.

The bundle copies the memory runtime to a stable user directory. Existing legacy installations are reported and preserved. Notes still require approval of their exact content. Configuration checks do not prove recall in a fresh agent session.

This replaces the upstream setup dependencies. Do not write global model rules or select providers as part of setup. See [the package guide](../../README.md) for updates and removal.
