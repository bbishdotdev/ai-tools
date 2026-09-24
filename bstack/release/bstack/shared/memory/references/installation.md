# Install optional shared memory

Ask the agent: "Use setup-bstack to enable shared personal memory on this machine."

Memory setup is separate from engineering auto mode. It configures Codex native memory, Claude's native memory directory, and Cursor's file bridge. It requires Python 3.11+ on POSIX. There is no Grok memory adapter.

## Preview and apply

From an installed project, preview the user-wide changes:

```sh
python3 .bstack/package/scripts/bstack.py memory setup
```

Review the returned file changes and plan digest. If setup is already authorized, apply that unchanged plan:

```sh
python3 .bstack/package/scripts/bstack.py memory setup --apply-plan <digest>
python3 .bstack/package/scripts/bstack.py memory status
```

The standalone [installer](../scripts/portable.py) accepts the same `setup`, `status`, and `--apply-plan` arguments. A changed configuration or payload invalidates the plan. Resolve reported conflicts before generating a new preview. Do not force replacement of another installation.

Setup enables Codex's memory feature and use of memory, and enables Claude auto memory. It preserves native generation settings and unrelated configuration. An existing fixed Claude directory is retained. Otherwise, setup selects a shared user directory; old project memories stay on disk but are no longer the default startup index. Their content is not migrated.

Setup does not create personal notes. Later additions, edits, deletions, and migrations require approval of the exact content. A plan digest checks file revisions; it does not prove human approval.

## Installed ownership

`~/.local/share/bstack/memory/runtime/` contains a copy of the reviewed code and policy. `state/` holds the Cursor bridge, default Claude directory, lock, and configuration backups. Codex keeps its configured native memory root. The stable skill at `~/.agents/skills/memory-policy` points to the copied runtime.

Setup records the selected `CODEX_HOME` and `CLAUDE_CONFIG_DIR` roots so other tools use the same destinations. A later conflicting environment override requires review; it does not silently switch stores.

Global instruction files receive a managed policy block. Existing instructions, hooks, and native memories are preserved. Unrecognized symlinks, conflicting skill paths, and edits to owned runtime files stop setup.

The downloaded release and installing project can be removed after setup. Project install, update, and uninstall do not change this user installation. To update the user runtime, explicitly run memory setup from a reviewed newer bundle. Personal data stays outside the replaceable runtime.

Existing source-linked `~/Work` installations are reported as legacy and left untouched. Migration and user-level uninstall are separate work. Do not delete a legacy source checkout on the assumption that it was copied.

## Verify the installation

Status reports file and configuration readiness without printing personal notes. It does not establish fresh-session recall or approval enforcement for native background writers. Start fresh sessions after setup and use the checks in [native interfaces](native-interfaces.md) when testing current product versions.

For isolated verification, append `--home <disposable-home>` to setup and status. It ignores production native-directory environment overrides. Run note operations with `sync.py --home <disposable-home>`. Use synthetic notes only.
