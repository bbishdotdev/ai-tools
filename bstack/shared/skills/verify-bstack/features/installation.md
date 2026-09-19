# Consumer installation

## Contract

Installation must deliver bstack's reviewed bundle, including its policy, customized unslop, selected workflows, helper source, notices, and controller. No install path fetches upstream latest. An installer exit proves file delivery; real CLI sessions provide separate discovery and routing evidence.

The [initial raw-source probe](../../../../audit/skills-install.md) remains the historical failure case. Test `bstack/release/`, not the source imports in `upstream/`.

## Drive

From the ai-tools checkout:

```sh
python3 bstack/scripts/package.py build
python3 bstack/scripts/package.py check
python3 bstack/shared/skills/verify-bstack/scripts/installation.py
```

The default method runs the bundled Python installer. It requires no skills.sh or network access. To compare distributor behavior:

```sh
python3 bstack/shared/skills/verify-bstack/scripts/installation.py \
  --methods offline symlink copy --skills-cli /path/to/skills/bin/cli.mjs
```

The supplied CLI must be skills@1.7.0. Without `--skills-cli`, explicitly selected skills.sh methods use `npx --yes skills@1.7.0`. Record installer output to regular files, not a pipe that can truncate JSON. The harness uses project scope and project paths containing spaces.

Each method must deliver the same capsule manifest and hashed files, one discoverable `SKILL.md`, the bstack replacement skills, complete local references, and notices. Delete the temporary source before setup, doctor, or model execution. This proves independence from that staged source. Separately reject model reads from the development checkout.

The packaged installation driver also runs from a transferred capsule. Suppress Python bytecode writes before importing its helpers so verification does not mutate the integrity-checked package.

## Live CLI behavior

Add `--live` only when model usage is authorized. The verifier discovers installed Codex, Claude Code, Cursor, and Grok CLIs. An explicit missing client is an error; otherwise unavailable clients are not selected. `--live-method offline` uses the offline-installed project; choose `symlink` or `copy` to drive another selected method.

The probes are read-only. They classify example tasks, read per-turn fixture values, and report a router-specific policy. They do not implement the examples or execute full engineering workflows.

1. Invoke manual Poteto Mode and observe a successful installed-router read. A skills.sh project has not run setup yet; an offline project is already configured with automatic routing off.
2. Run setup and doctor for every installed project. Check a fresh engineering prompt with manual-only guidance: no router read, no hook receipt, and persisted auto off.
3. Enable automatic mode twice. Run a fresh turn and a resumed turn with different routing cases and unique file values. Require session continuity, successful current fixture reads, the correct bstack policy, and a current native hook receipt when supported and trusted.
4. Disable twice and run another fresh engineering prompt. Check that automatic bindings and receipts are absent while normal advice remains available.

Correlate successful tool results with file reads. Attempted paths or a model assertion are insufficient. Match hook receipts to the actual host, event, session, and turn. Cursor/Grok delivery must be the once-per-turn after-tool fallback, not a stale receipt or another host's hook. Reading state, hook implementation, or receipt logs invalidates the probe.

Codex native hook trust is inspected separately without changing it. Untrusted or modified hooks are a visible verification limit, not a delivery pass. Missing receipts from trusted hooks are failures. Fixture workspace trust is supplied explicitly to headless CLIs; these probes do not verify interactive trust onboarding.

## Lifecycle and limits

Runtime tests cover collisions, preservation of unrelated configuration, exact safe block adoption after cloning, opt-in persistence, package upgrades, rollback, symlink boundaries, private-work retention, and removal of owned bindings. Builder tests cover deterministic files/modes, dependency rewrites, custom overrides, complete source records, and stale or altered release detection.

The current installer requires Python 3.11+ and POSIX. Global installation, remote Git distribution, Windows, native plugin managers, and desktop applications require their own evidence. A directory transfer does not provision external service accounts or optional helper runtimes. Current CLI tests do not establish context compaction behavior for the installed release.

Keep prompts, commands, native output, hook records, and reports under gitignored `.bstack/verification/`. Preserve failures alongside successful reruns and summarize exact evidence and limitations in the tracked audit report.
