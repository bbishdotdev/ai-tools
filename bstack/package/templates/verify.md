---
name: verify-bstack
description: Verify the installed bstack package, public skill bindings, and optional live CLI behavior.
disable-model-invocation: true
metadata:
  package: bstack
---

# Verify bstack

Run the installed [controller](../../scripts/bstack.py) with `doctor --project <project-root>` to check package integrity and bindings. This maintainer entry does not activate engineering mode or authorize implementation work.

Resolve [scripts/installation.py](scripts/installation.py) to its absolute path and run it from the chosen project. It installs this reviewed package into isolated projects and records evidence under `.bstack/verification/`. Its default offline probe needs Python and no upstream download.

Use `--release <release-directory> --methods offline symlink copy` to also test the skills.sh transport artifact from a complete release. The installed canonical package alone does not contain that transport archive. Use `--help` for the available options.

Add `--live` only for user-authorized provider-backed checks. Those probes check direct skill invocation, manual mode, default-off behavior, automatic reminders, resumed turns, and opt-out. An installer exit, intact files, hook emission, observed model reads, and correct responses prove different things. Report unsupported or blocked checks accurately.

Other packaged verifier modules support this installation probe. Source pin and layer checks belong in the development repository.

For SDLC changes, use a disposable installed project and read [workspace access](../references/workspace.md). Give a fresh agent a human-approved planning-only brief and ask it to save accepted Wayfinder context, an approved spec, linked tickets and a durable handoff. Inspect actual stored identities, authority, source snapshots and dependencies, then reopen a source and verify a fresh receiver detects the change. No implementation or external delivery is part of that fixture.

In a separate empty fixture, request autonomous grilling without role configuration and verify it stops before planning writes. Check [independent adapter](../references/work-adapters.md) selections separately: local planning must remain usable when only the ticket provider is unsupported. A config check does not prove two models ran. Browser interactions, native discovery on each CLI, cross-model exchange and fresh-session launch need their own observed evidence.
