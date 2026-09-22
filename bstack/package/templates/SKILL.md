---
name: poteto-mode
description: Enter bstack's Poteto Mode for an explicitly requested engineering workflow.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  package: bstack
  attribution: ../../ATTRIBUTION.md
---

# Poteto Mode

Read [bstack's router](../../shared/router/WORKFLOW.md) in full and use it to select and continue the requested engineering workflow. Apply [bstack's customized unslop](../../shared/unslop/SKILL.md) to prose.

The [workflow index](../../index.json) resolves skill names to bundled instructions and replacements. Read only the playbooks, principles, and supporting files needed for the task. Use these reviewed files; do not fetch upstream latest. Resolve references against the actual packaged file and helpers to an absolute path before running them from the consumer project.

Other installed bstack skills can be invoked directly without entering Poteto Mode. Automatic routing is an explicit project preference controlled by [bstack-auto](../../shared/bstack-auto/SKILL.md). See [the package guide](../../README.md) for setup and host limits.
