# Claude Code parent-workspace setup

19 October 2026. This investigation covers a BStack package installed above a child Git repository, plus the released package installed into an isolated child repo on Linux. It does not inspect the user's MacBook or a Claude Code desktop conversation.

## Finding

BStack's installer binds skills, project instructions, and auto hooks to the exact `--project` directory. A parent install with auto mode on leaves a child Git repo `not_configured`. Claude may still see ancestor `CLAUDE.md` text, creating a partial setup: instructions without the child's own skill links or prompt hook. The supported path is to install the exact bundle into each working repo, optionally using a global installer skill or a parent package as the source. Auto mode must be enabled for that repo and the Code chat restarted there.

The package test `test_shared_parent_package_needs_child_bindings_for_claude_auto` now covers parent-only status, child setup, child auto mode, Claude's skill link, and the child hook's package path. It does not claim model compliance.

## Live CLI check

The isolated Claude Code CLI probe passed both fresh and resumed auto-routing turns: the installed router was read, the current hook receipt reached the model, the expected playbook and BStack policy were selected, and the fixture was read on each turn. Evidence: `.bstack/verification/20261020T024013Z-installation-c4bea5/report.json` (private, gitignored).

An earlier attempt failed before a useful model result because the sandbox blocked Claude's session directory and API access. That failure remains at `.bstack/verification/20261020T023632Z-installation-ef725d/report.json`. The successful rerun used Claude's normal filesystem and network access.

These results narrow the likely cause of the reported desktop behavior but do not prove it. [Claude's desktop docs](https://code.claude.com/docs/en/desktop) describe the Code tab's project folder and shared Claude Code configuration; [skill discovery](https://code.claude.com/docs/en/skills) and [project memory loading](https://code.claude.com/docs/en/memory) have different scope rules. The next direct check is a fresh Claude Code desktop Code chat rooted in the child repo, followed by child `doctor`, `auto status`, a simple engineering prompt, and confirmation that the current hook and router are actually read. A Mac-only failure after those checks needs the desktop session's own evidence.
