# CLI discovery

The bstack maintainer can validate a change against whichever supported CLIs are installed.

## Sub-features

- Discover `codex`, `claude`, `cursor-agent` or `agent`, and `grok` on PATH.
- Record executable paths and versions before testing.
- Test all discovered clients by default, or a requested `--tools` subset.
- Report missing default clients as skipped and explicitly requested missing clients as blocked.
- Report unsupported prompt-context hooks separately from routing failures.

## How to get to it

Run `python3 bstack/shared/skills/verify-bstack/scripts/verify.py doctor` from the repository root. Then run the same command with `live` after authorizing provider calls. The default live run requires no client list.

## Verification

Check that the recorded `clients` match the installed executables. Each selected client should have three responses sharing a session ID. A missing client must never appear as passed. `pass_with_limits` preserves successful routing without claiming unavailable prompt-hook delivery. Authentication failures remain failures even when the executable exists.

## Gotchas

`doctor` does not make model calls or validate authentication. CLI validation does not establish app support. The suite covers bstack routing, not every installed skill or the developer's application.
