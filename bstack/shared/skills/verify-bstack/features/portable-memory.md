# Portable memory

The bundle carries a private memory payload. Explicit `memory setup` copies it into a stable user runtime; ordinary project installation and automatic routing leave user memory configuration alone. Codex and Claude use native files, Cursor uses a labeled file bridge, and Grok has no adapter.

## Run the focused checks

```sh
python3 -B -m unittest discover -s bstack/shared/skills/memory-policy/tests
python3 -B bstack/scripts/test_memory_installation.py
python3 -B bstack/scripts/test_package.py
python3 -B bstack/package/test_runtime.py
python3 -B bstack/scripts/package.py build
python3 -B bstack/scripts/package.py check
```

Use disposable `--home` profiles and synthetic notes. Never run setup or save a verification note in the real home merely to test packaging. No model credentials or network access are needed for these checks.

The installation test uses the actual transport archive and controller. It verifies a read-only preview, copies the user runtime, creates and updates a synthetic note, removes the project and distribution, then checks the copied runtime, Cursor snapshot, and deletion. Project reinstallation and removal must preserve all user files. Package checks confirm private payload discovery and dependency closure.

The component suite covers idempotence, existing settings and notes, runtime updates, reviewed plan freshness, ownership conflicts, redirected paths, legacy detection, and native destination identity. A recognized legacy setup is preserved, not migrated. Native generation settings and unrelated hooks remain intact.

## Interpret evidence

Status checks local files and configuration. Synthetic sync checks physical readback and bridge snapshot output. Neither proves fresh-session model recall, desktop discovery, background-writer approval, or a Grok memory integration.

For authorized live recall checks, follow the component's [native interface procedure](../../memory-policy/references/native-interfaces.md). Its historical source-linked results are version-specific. Save current commands and results under `.bstack/verification/`; report unsupported or untested surfaces explicitly.
