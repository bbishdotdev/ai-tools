# Shared memory source

The existing shared-memory implementation lives in `skills/memory-policy/`, beside its policy in `rules/memory-policy.md`. It was moved from the repository's former root `skills/` and `rules/` directories. Runtime code and policy wording are unchanged.

This is source preservation and organization. The generated bstack consumer release does not yet include or install this component.

## Existing local installation

The canonical installed entrypoints stay under `~/Work`:

- `~/Work/.agents/skills/memory-policy` points to this directory's `skills/memory-policy/`.
- `~/Work/AGENTS.md` points to this directory's `rules/memory-policy.md`.
- Home-level Codex, Claude, and Cursor entries route through those stable Work paths.

The cleanup repoints only the two source links on this machine. Memory storage, configuration, approval policy, and Cursor's context hook stay in place. No memory synchronization or content migration is part of the move.

For another existing checkout, verify the old links before repointing them to the new source. The installer refuses unrelated existing paths rather than replacing them.

## Install and check

From the repository root, preview the optional installation and activation:

```sh
python3 bstack/shared/skills/memory-policy/scripts/install.py --activate-sync
```

Add `--apply` to apply a reviewed installation plan. Use a permanent checkout because installed source links depend on it. The helper preserves native memories and unrelated settings. See [memory policy](skills/memory-policy/SKILL.md) and [native interfaces](skills/memory-policy/references/native-interfaces.md) for approval requirements and supported destinations.

Inspect an existing installation without printing memory contents:

```sh
python3 -B ~/.agents/skills/memory-policy/scripts/status.py
```

Run its tests in isolated temporary homes:

```sh
python3 -B -m unittest discover -s bstack/shared/skills/memory-policy/tests
```

Moving this source does not establish portable consumer memory installation or fresh application recall. Those need their own integration and verification step.
