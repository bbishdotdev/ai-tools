# Portable memory verification

September 23, 2026. bstack 0.4.0 adds optional user-wide memory setup to the offline bundle. This report covers local installation and filesystem behavior on Linux.

## Delivered behavior

`memory setup` previews a reviewed installation plan. Applying its digest copies the component into `~/.local/share/bstack/memory/runtime/` and connects the canonical user skill, managed instruction pointers, native settings, and Cursor bridge hook. Ordinary project installation, automatic routing, project updates, and project removal leave this user installation alone.

The same synchronization engine handles approved notes. Codex and Claude retain native files; Cursor uses a labeled bridge. Existing native contents and unrelated settings survive setup. Recorded native roots remain consistent across invoking tools. Legacy Work-based installations are detected and left unchanged. No personal notes or real user configuration were changed during this work.

The runtime is staged before replacement. Caught failures, including interruption, attempt rollback only where files still match the installer writes. Concurrent edits are preserved and reported. There is no durable recovery journal for process kills or power loss, and setup is not a transaction across native background writers.

## Checks

| Check | Result |
| --- | --- |
| Memory engine and portable installer | 62 passed, including 44 existing tests |
| Offline memory lifecycle through the transport archive | 1 passed |
| Package assembly and private payload | 20 passed |
| Project runtime | 44 passed |
| Transport archive validation | 7 passed |
| Generated release and source layers | Clean |
| Offline installation driver | Passed for all four host bindings after staged-source removal |
| Memory and maintainer skill validation | Passed |

The lifecycle check creates, updates, and deletes synthetic notes in an isolated home. It removes the installing project and release, then invokes the copied helper and actual registered Cursor hook. Project reinstall and removal preserve the user files. Other cases exercise stale plans, runtime drift, path collisions, invalid overlapping stores, unrelated settings, custom native roots, failure rollback, and retry.

Independent review found two packaging/test issues and two runtime issues. The fixes isolate the test subprocess environment, route memory-only requests directly to setup, make failed installation recoverable, and reject native data inside the replaceable runtime. Regression checks pass. The final independent re-review and fresh-agent skill evaluation were blocked by provider usage limits; the parent reviewed the fixes and ran the final checks locally.

## Limits and evidence

These results do not establish current fresh-session native recall, desktop behavior, native background-writer approval enforcement, Windows support, or a Grok memory adapter. Legacy migration and user-level uninstall are not implemented. Historical native recall evidence remains in the component's compatibility reference.

Private design and review reports, the isolated skill fixture, and the offline installation report are under `.bstack/work/portable-memory/`. The reusable recipe is [portable memory verification](../shared/skills/verify-bstack/features/portable-memory.md).
