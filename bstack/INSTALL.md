# Install bstack

bstack installs one package and a set of directly invocable skills. Poteto Mode is an engineering entry within that collection. The package contains the exact reviewed dependencies and customizations; installation never fetches newer upstream sources.

The controller requires Python 3.11+ on POSIX. These instructions cover project-local CLI installation. Windows, global installation, desktop apps, and native plugin managers need separate integration and verification.

## From a clone or transferred release

From the ai-tools checkout:

```sh
python3 bstack/release/bstack/scripts/bstack.py install \
  --project /path/to/your/project --hosts codex claude cursor grok
```

Select the hosts you want configured. Installation copies `release/bstack/` into the project's `.bstack/package/` and creates the public skill bindings. You can transfer just that package directory to an offline machine and run its controller. No npm, skills.sh, Git, or network is needed, and the original source can be removed after installation.

## Through skills.sh or an internal distributor

skills.sh copies skill folders, so the release includes a dedicated `install-bstack` transport skill containing an archive of the complete package. The installer unpacks that archive into the same canonical layout as the offline route.

From the consumer project:

```sh
npx skills@1.7.0 add /path/to/ai-tools/bstack/release/skills-sh \
  --skill install-bstack --agent codex claude-code cursor grok
python3 .agents/skills/install-bstack/scripts/install.py \
  --project "$PWD" --hosts codex claude cursor grok
```

skills.sh supports its default host links and `--copy`; both transport the same archive. The second command is required because skills.sh does not execute setup. An internal distributor can copy the complete `install-bstack/` folder and run the same command. Keep the transport intact so its distributor retains ownership of it. The installed package operates independently of that archive.

Check for an existing `install-bstack` skill before using a third-party installer. The bstack controller cannot protect a file that another installer overwrites first. It refuses collisions while creating its own package and bindings.

## Installed layout

```text
your-project/
  .bstack/
    package/
      engineering/
        how/SKILL.md
        architect/SKILL.md
        poteto-mode/SKILL.md
        principles/              # Internal, loaded on demand
        ...
      shared/
        router/                  # Internal bstack policy
        unslop/SKILL.md
        setup-bstack/SKILL.md
        bstack-auto/SKILL.md
        verify-bstack/SKILL.md
      scripts/bstack.py
      manifest.json
      ATTRIBUTION.md
    config.json
    instructions.md
  .agents/skills/
    how/SKILL.md                  # Points to the packaged how skill
    architect/SKILL.md
    poteto-mode/SKILL.md
    ...                          # All 29 public entries
  .claude/skills/                 # Per-skill links to .agents/skills
  .cursor/skills/                 # Same shared entries
  .grok/skills/                   # Same shared entries
  AGENTS.md
  CLAUDE.md
```

Each public entry is a small binding to its exact packaged skill. Hosts can discover the individual names without loading all their instruction bodies. The full skills and supporting files live once in the package. Principles have no public skill entry; the active skill loads relevant principles and playbooks as needed.

The generated release groups skills into engineering and shared buckets. SDLC and GitHub content will join as their integrations are implemented. Frozen `upstream/` snapshots remain development inputs and are not installed as a second collection.

## Direct skills and automatic routing

Invoke `$how` in Codex or `/how` in slash-command hosts. This selects the how workflow and bstack's policy without first entering Poteto Mode. Other public skills work the same way. Invoke `poteto-mode` when you want its router to select a full engineering workflow.

Engineering entrypoints are manual by default. Customized unslop stays active for prose. Use `bstack-auto on`, `off`, or `status` for optional automatic routing, or use the controller directly:

```sh
python3 .bstack/package/scripts/bstack.py auto on --project "$PWD"
python3 .bstack/package/scripts/bstack.py auto status --project "$PWD"
python3 .bstack/package/scripts/bstack.py auto off --project "$PWD"
python3 .bstack/package/scripts/bstack.py doctor --project "$PWD"
```

Setup preserves other instructions and configuration. Mode and ownership state live in gitignored `.bstack/`. Start a fresh session after bindings change; disabling auto cannot remove instructions already in a conversation. Codex hook trust must be reviewed through its native `/hooks` UI. Setup does not grant trust. Cursor and Grok's after-tool reminders do not provide first-tool or tool-free prompt injection.

## Update, migrate, and remove

Rerun the installer from a reviewed newer release. It verifies the owned package, preserves auto preference and selected hosts, and rolls back on installation errors. Modified or unowned files stop the update.

Existing offline installs under `.agents/skills/poteto-mode/` migrate to `.bstack/package/` after their integrity and ownership checks pass. Existing third-party-distributed Poteto Mode folders are not adopted or deleted; resolve those conflicts through their distributor before installing the new package.

Run `python3 .bstack/package/scripts/bstack.py uninstall --project "$PWD"` to remove the verified owned package and bindings. Private work and independently distributed installer skills remain. Remove `install-bstack` through its distributor if desired.

Generated bindings contain local paths. Install per checkout rather than checking machine-specific bindings and ownership state into another project. Stable instruction pointer blocks can be committed. Reinstallation recreates the ignored package.

Optional helper programs still require their own runtimes or authorized external services. Installation does not provision them. See [maintainer verification](shared/skills/verify-bstack/SKILL.md) and [upstream ownership](UPSTREAM.md).
