---
name: setup-bstack
description: Configure or check bstack's local project bindings and selected agent tools.
disable-model-invocation: true
metadata:
  package: bstack
---

# Set up bstack

If the request is only to enable, update, or check personal memory, go directly to **Optional personal memory** below. Do not reconfigure project bindings or initialize or serve the workspace for that request.

Resolve the installed package from the [controller](../../scripts/bstack.py). Target the Git repository containing the work, even if this skill was discovered from a parent workspace. A parent-only setup does not bind a child repo's Claude skills or auto hook. Choose a Python 3.11+ interpreter and run the controller with the requested project. Setup validates and saves this exact interpreter for hooks; rerun setup to change or repair that selection:

```sh
python3.12 <absolute-package-path>/scripts/bstack.py setup --project <project-root>
```

For a new installation, add `--hosts` with the requested or detected tools, including the current host: `codex`, `claude`, `cursor`, `grok`, `amp`, `copilot`, `opencode`. On upgrade, omit `--hosts` to preserve the saved selection unless the user requests a change.

Setup creates direct public skill entries and project instructions. Run it separately in each checkout. Its `sharing` report lists mixed host settings and tracked generated files; ignores do not hide tracked edits. Claude uses local settings and private launch scripts, and only previously owned hooks migrate from shared settings. New projects start with automatic engineering routing on and project verification set to `ask`. Upgrades keep both choices. Use `--auto off` for manual routing or `--verification off|ask|auto` to choose how project verifiers are maintained. Explain these choices when changing them: auto routing picks relevant engineering workflows for ordinary prompts; verification `ask` proposes a verifier change before making it, while `auto` maintains affected verifier paths during feature or bug work. Run `doctor --project <project-root>` to check package integrity, owned bindings, and harmless startup probes of the generated commands. This check does not prove that a host loaded or trusted its hooks.

Generated-path ignore rules are shared repository policy, separate from the stable `.bstack/` ownership block. Setup merges that policy and preserves visibility exceptions; doctor reports needed policy maintenance without writing it. Uninstall keeps the shared policy for the team to revise. Report visible generated paths honestly when an exception or tracked file prevents ignoring them.

If Codex has `[features] hooks = false`, the default auto setup stops with a clear choice: enable hooks or pass `--auto off`. Manual setup can finish with that setting, but its Codex PR creation guard cannot run until hooks are enabled. Do not silently change an explicit host setting.

When the source controller belongs to a parent BStack install, `setup` copies that exact package into the child repo. Use the child's own `.bstack/package/scripts/bstack.py` for subsequent `auto` and `doctor` commands. Start a fresh Claude Code desktop Code chat rooted in the child after changing bindings.

When project setup and `doctor` succeed, recommend `bstack-guide` as a short introduction. If the user asked for a walkthrough as part of setup, read the installed `shared/bstack-guide/INSTRUCTIONS.md` and give it. If new bindings require a fresh session, recommend invoking the guide there. Skip this recommendation for a memory-only request.

The seven-rule [baseline](../references/baseline-agents.md) is written into a managed block in `AGENTS.md`. When Claude is selected and the project has no `CLAUDE.md`, setup creates one that only imports `AGENTS.md`, so the baseline lives in one place. An existing `CLAUDE.md`, and one from an earlier BStack install, gets the managed block. Existing project text and shared symlinks are preserved. Baseline rules apply independently of auto mode. Do not run a host's `/init` automatically. Offer optional project-specific guidance outside the blocks after setup; installation does not depend on it. If the user requests that guidance or a native init, preserve the blocks and run `doctor` afterward. A changed or missing block must be restored from its exact record in `.bstack/config.json` while preserving new project text; setup refuses to overwrite that conflict.

If the user wants project-specific PR priorities or human-review paths, offer [configure-pr](../configure-pr/INSTRUCTIONS.md). Its committed policy is optional. Setup does not create an empty policy file or copy one from the package without a request.

For local planning and tickets, initialize the project's workspace before creating optional role or adapter configuration:

```sh
python3 <absolute-package-path>/workspace/cli.py --project <project-root> init
python3 <absolute-package-path>/workspace/cli.py --project <project-root> serve
```

The workspace stores maps, specs and Kanban tickets privately under its owning project's `.bstack/workspace/`. Git worktrees share that owner's store. Read [workspace access](../references/workspace.md) before writing artifacts. Read existing domain documents and ADR conventions when work needs them; setup does not create a second documentation system.

Ordinary manual work needs no model configuration. The default delegation policy remains `inherit-parent`. A basic installation does not need an optional-model picker. For a full setup, offer PR review, PR visuals, and preparing grilling models for later. Honor workflows already selected. Configuring or checking these choices does not start a review, create a PR, or run a grilling interview.

Use the installed controller's normal `doctor --project <project-root>` output before presenting model choices. It resolves defaults and project overrides without sending model prompts. For `review-pr`, show each role's CLI, exact model ID, and effort from `models.workflows.review-pr.roles`: reviewer A, reviewer B, and the fresh final checker. Put those values in the keep-defaults or keep-current-settings option, or immediately beside it, before offering customization. Do not ask the user to accept unnamed defaults. Do not use a hardcoded model list in place of the resolved settings. Preserve saved choices unless the user changes them.

`to-pr` visuals are a separate choice from creating or reviewing a PR. Explain that visuals prefer Codex for an explanatory image when the project permits Codex to see its code. The current host's image tool or a useful diagram can be used when Codex image generation is unavailable. The `to-pr` text probe uses the CLI's configured model; it does not select a PR author model.

For grilling, ask whether to configure the interviewer and respondent now for later use, independently of whether the user wants an autonomous interview. Show any saved choices; otherwise explain that one model challenges the plan and a different model answers, then obtain their model choices without inventing defaults. Follow [decision authority](../references/decision-authority.md) to save the roles and check the supported participants. Human-guided mode remains the default. Keeping it manual must not skip requested model configuration or erase saved choices. An autonomous interview still needs an explicit request or scoped delegation for that run; setup creates no persistent autonomy toggle.

Before the first live check for a selected workflow, reuse its saved launch commands or a working command already established in this session. Otherwise ask how the developer runs each required CLI headlessly in their terminal. Examples are `claude -p "say hi"`, `codex exec "say hi"`, and `launch claude -- -p "say hi"`. Ask for the command only, never credentials or a complete settings file. Explain that BStack supplies the prompt, model and output flags. Save the executable and any wrapper arguments around `{args}`, for example:

```sh
python3 <absolute-package-path>/shared/model_cli.py --project <project-root> configure --cli claude --command 'launch claude -- {args}'
```

The plain equivalent is `claude {args}`. The helper saves the command privately in `.bstack/model-clis.json` and inserts native arguments at `{args}` without a shell. Do not infer the launch command from the CLI being present on `PATH`.

Explain that live checks send small model requests and may incur usage, but do not begin the workflow. Run `python3 <absolute-package-path>/scripts/bstack.py doctor --project <project-root> --live --workflow <workflow>` for each chosen and permitted workflow: `review-pr`, `grilling`, or `to-pr`. Grilling checks can run while human-guided mode remains selected. Recheck after changing a launch command. A failed optional workflow does not block basic installation, but that workflow remains blocked until its check passes. Never silently retry the plain binary or replace a chosen model after a launcher or authentication failure.

If the normal terminal command works but BStack cannot authenticate, say that BStack could not use the working login and check its launch command and settings. Do not claim the user was logged out or tell them to change certificates, shell files or login settings based on an incidental warning. Report the actual failed step and the next check in plain language. Keep basic installation and each selected workflow separate in the result: passed, not checked, or blocked. The `to-pr` live check proves text access only; image generation still needs a real visual attempt.

For grilling, report the saved models, whether their checks passed or remain unchecked/blocked, and that human-guided mode remains the default. A passed check means the models are ready for a later requested interview, not that autonomous answers have been enabled.

Auto routing does not grant product or ADR decision authority. Wayfinder and tickets have [independent adapter choices](../references/work-adapters.md), each defaulting to the implemented local adapter. External adapters remain unsupported until implemented and verified; a Git remote is not a provider selection.

## Optional personal memory

Only when the user requests shared memory, run `python3 <absolute-package-path>/scripts/bstack.py memory setup` to preview user-wide configuration. Read [portable memory setup](../memory/references/installation.md), review the changes, then apply the unchanged plan with `memory setup --apply-plan <digest>` within that authorization. Check `memory status` afterward. Engineering auto mode and ordinary project setup do not enable memory.

The bundle copies the memory runtime to a stable user directory. Existing legacy installations are reported and preserved. Notes still require approval of their exact content. Configuration checks do not prove recall in a fresh agent session.

This replaces the upstream setup dependencies. Do not write global model rules or select external planning or ticket services as part of setup. Project-local model CLI choices above are separate. See [the package guide](../../README.md) for updates and removal.
