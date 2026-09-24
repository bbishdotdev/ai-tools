---
name: setup-bstack
description: Configure or check bstack's local project bindings and selected agent tools.
disable-model-invocation: true
metadata:
  package: bstack
---

# Set up bstack

If the request is only to enable, update, or check personal memory, go directly to **Optional personal memory** below. Do not reconfigure project bindings or initialize or serve the workspace for that request.

Resolve the installed package from the [controller](../../scripts/bstack.py). Run it with the requested project and hosts:

```sh
python3 <absolute-package-path>/scripts/bstack.py setup --project <project-root> --hosts codex claude cursor grok
```

Setup creates direct public skill entries and project instructions. It preserves an existing auto preference and defaults to manual routing for a new installation. Do not enable auto mode without the user's request. Run `doctor --project <project-root>` to check the resulting package and bindings.

For local planning and tickets, initialize the project's workspace before creating optional role or adapter configuration:

```sh
python3 <absolute-package-path>/workspace/cli.py --project <project-root> init
python3 <absolute-package-path>/workspace/cli.py --project <project-root> serve
```

The workspace stores maps, specs and Kanban tickets privately under its owning project's `.bstack/workspace/`. Git worktrees share that owner's store. Read [workspace access](../references/workspace.md) before writing artifacts. Read existing domain documents and ADR conventions when work needs them; setup does not create a second documentation system.

Ordinary manual work needs no model configuration. The default delegation policy remains `inherit-parent`. Before explicitly autonomous grilling, follow [decision authority](../references/decision-authority.md) and validate the configured participants before planning writes. Auto routing does not grant decision authority. Wayfinder and tickets have [independent adapter choices](../references/work-adapters.md), each defaulting to the implemented local adapter. External adapters remain unsupported until implemented and verified; a Git remote is not a provider selection.

## Optional personal memory

Only when the user requests shared memory, run `python3 <absolute-package-path>/scripts/bstack.py memory setup` to preview user-wide configuration. Read [portable memory setup](../memory/references/installation.md), review the changes, then apply the unchanged plan with `memory setup --apply-plan <digest>` within that authorization. Check `memory status` afterward. Engineering auto mode and ordinary project setup do not enable memory.

The bundle copies the memory runtime to a stable user directory. Existing legacy installations are reported and preserved. Notes still require approval of their exact content. Configuration checks do not prove recall in a fresh agent session.

This replaces the upstream setup dependencies. Do not write global model rules or select providers as part of setup. See [the package guide](../../README.md) for updates and removal.
