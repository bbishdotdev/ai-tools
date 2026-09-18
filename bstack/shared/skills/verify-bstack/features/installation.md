# Consumer installation

## Sub-features

Verify package discovery, selected skill versions, complete dependencies and notices, and host configuration. A successful installer exit is only a file-install result. Native skill discovery and workflow execution require separate agent sessions in the installed project.

The [initial skills.sh probe](../../../../audit/skills-install.md) found that the raw source layout does not produce a complete installation. Keep that result visible until a release layout passes this procedure.

## How to get to it (user POV)

The intended user installs bstack into a project and invokes Poteto Mode manually. Automatic routing is an optional next step. The current repository adapter POC is not that consumer installer.

## Driving it with the skills CLI

Run the candidate install in an empty temporary project. From the ai-tools repository root, the current source probe is:

```bash
bstack_source="$PWD/bstack"
bstack_probe="$(mktemp -d)"
cd "$bstack_probe"
DISABLE_TELEMETRY=1 npx --yes skills@1.7.0 add "$bstack_source" \
  --skill '*' --agent codex claude-code cursor grok --yes --json \
  > install-result.json 2> install-stderr.txt
```

Repeat in a separate empty project with `bstack/shared/skills` as the source to compare only bstack-owned skills. When a release artifact exists, test that artifact instead of treating this source probe as the distribution command. Record the exact source revision, CLI version, command, exit code, and output.

For each target, run `npx --yes skills@1.7.0 list --agent <agent> --json` and inspect the installed files. Confirm all of these conditions before reporting a complete package install:

- The selected skills match the release list. Dormant source examples and automations are not installed accidentally.
- `unslop` matches bstack's customized skill. Duplicate upstream names do not silently select the wrong version.
- Router, playbook, helper, and attribution references resolve inside the installed package. Nothing depends on an absolute path to the development checkout.
- The distribution includes applicable license notices and source records.
- Manual invocation is available without enabling automatic routing. Enabling automatic routing installs supported host configuration, and disabling it stops future reminders.

After file checks pass, run fresh native CLI sessions in the consumer project, then resumed turns. Adapt the existing driver to that project's paths explicitly; its current repository-root assumptions cannot validate an arbitrary installed package. Keep the development checkout unavailable to the probes so fallback reads cannot hide missing dependencies.

Retain command output and file-check evidence in `.bstack/verification/` in the maintainer checkout. Preserve failures and untested targets in the report.

## Gotchas

- `skills.sh` installing skill directories does not prove native plugin registration, hook setup, or agent execution.
- The tested CLI exposes Codex and Cursor through `.agents/skills/`; Claude Code and Grok have links to that canonical copy. Do not infer discovery from directory names alone.
- Capture JSON output to a regular file. The initial whole-tree probe observed truncated output through a pipe. `--list --json` is rejected by version 1.7.0.
- This procedure uses project scope. Global installs, remote Git installation, copy mode, upgrades, uninstall, and desktop applications need separate tests before claiming support.
