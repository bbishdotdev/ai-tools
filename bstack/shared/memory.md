# Optional shared memory

The bstack bundle includes the memory runtime. Project installation leaves it inactive. Ask the agent: "Use setup-bstack to enable shared personal memory on this machine."

From an installed project, the agent previews and applies user-wide setup:

```sh
python3 .bstack/package/scripts/bstack.py memory setup
python3 .bstack/package/scripts/bstack.py memory setup --apply-plan <digest>
python3 .bstack/package/scripts/bstack.py memory status
```

See [portable setup](skills/memory-policy/references/installation.md) for the affected settings and review procedure. The first command is read-only. A plan digest binds the preview to current files; it does not supply user approval.

## Ownership and storage

Setup copies the reviewed code to `~/.local/share/bstack/memory/runtime/`, with private state beside it. Global skill links and the Cursor hook point to that stable runtime. Removing a project or downloaded release leaves the memory installation usable. Updating it is an explicit memory setup operation from a reviewed bundle.

Codex uses its configured native memory root. Claude keeps an existing fixed native directory or uses the new shared default. Cursor uses a file bridge, generated rule, and read-only prompt hook. Grok has no memory adapter. Configuration readiness, physical readback, and fresh-session recall are separate checks.

Setup preserves existing notes and unrelated settings. It does not merge old project memories, propagate native-only edits, or add new personal notes. The [memory policy](skills/memory-policy/SKILL.md) still requires approval of exact additions, changes, deletions, and migrations. Native background writers are outside that guarantee when they do not receive the policy.

## Existing source-linked installations

The earlier installation uses `~/Work/.agents/skills/memory-policy` and `~/Work/AGENTS.md` links into this checkout. Portable setup detects that layout and leaves it unchanged. It does not copy or migrate it automatically. Keep its permanent checkout until a separate migration is reviewed.

The legacy installation commands remain available from the source checkout:

```sh
python3 bstack/shared/skills/memory-policy/scripts/install.py --activate-sync
python3 -B ~/.agents/skills/memory-policy/scripts/status.py
```

The first command previews the legacy plan; `--apply` applies reviewed setup. It is not the portable consumer installer. The second reports local status without printing personal notes.

## Maintainer checks

Run the memory engine and installation tests in disposable homes:

```sh
python3 -B -m unittest discover -s bstack/shared/skills/memory-policy/tests
python3 -B bstack/scripts/test_memory_installation.py
python3 -B bstack/scripts/test_package.py
```

These tests establish filesystem behavior and offline portability. [Native interface evidence](skills/memory-policy/references/native-interfaces.md) records earlier version-specific live recall tests; rerun them before claiming current application recall.
