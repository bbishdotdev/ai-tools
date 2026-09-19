---
name: poteto-mode
description: Enter bstack's adapted Poteto Mode for engineering work when explicitly requested. Loads bstack policies, customized writing rules, and selected workflows on demand.
disable-model-invocation: true
metadata:
  author: Brenden Bishop, integration and adaptation
  package: bstack
  upstream-author: Lauren "poteto" Tan
  upstream-source: https://github.com/cursor/plugins/tree/main/pstack
  attribution: ATTRIBUTION.md
---

# Poteto Mode in bstack

Read [bstack's router](content/shared/skills/bstack-router/WORKFLOW.md) in full before doing the requested engineering work. Apply that policy to every workflow, agent, reference, and helper selected from this package. Use [bstack's customized unslop](content/shared/skills/unslop/WORKFLOW.md) for prose.

The [workflow index](content/index.json) maps skill names to the reviewed instruction files bundled here. Use these files, including bstack's customizations. Do not fetch upstream latest to fill a workflow dependency. Internal skills use `WORKFLOW.md`; they are dependencies, not separately installed commands. Resolve every packaged path relative to its containing document. Resolve a helper's absolute path before running it from the consumer project. The package can be outside that project's checkout. Read the capability contract before using host-specific helpers or integrations.

This manual entry works without setup. To install the project-local writing binding and `/bstack-auto` control, run the following with the actual installed package path and requested project root:

```sh
python3 <installed-poteto-mode>/scripts/bstack.py setup --project <project-root> --hosts codex claude cursor grok
```

Setup defaults to manual routing. `/bstack-auto on`, `/bstack-auto off`, and `/bstack-auto status` control the project's optional automatic routing. Turning it off preserves manual entry and the customized writing binding. Host command prefixes can differ. Do not enable automatic mode unless the user asks for it.

For installation checks, run `python3 <installed-poteto-mode>/scripts/bstack.py doctor --project <project-root>`. These checks do not prove a model followed the workflow. Run `uninstall` with the same project before removing this skill, so its separately installed bindings are cleaned up.

See [package setup and limits](README.md) and [credits](ATTRIBUTION.md). This is bstack's integration of Poteto Mode; the upstream engineering workflows are Lauren Tan's PStack work.
