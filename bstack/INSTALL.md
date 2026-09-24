# Install bstack

bstack installs one package and a set of directly invocable skills. Poteto Mode is an engineering entry within that collection. The package contains the exact reviewed dependencies and customizations; installation never fetches newer upstream sources.

The controller requires Python 3.11+ on POSIX. These instructions cover project-local CLI installation and optional user-wide memory setup. Windows, global installation of the full skill collection, desktop apps, and native plugin managers need separate integration and verification.

## Quick start

From the project where you want to use bstack, run:

```sh
npx skills add bbishdotdev/ai-tools --skill install-bstack
```

Choose your agent and project scope if prompted. Open your agent in that project, or start a fresh session if it was already running, and ask:

> Use install-bstack to set up this project for my installed tools.

Your agent runs the bundled installer, connects the selected tools, and checks the installation with `doctor`. It handles the script paths and host flags. Automatic routing stays off until you opt in.

There are two steps: skills.sh downloads `install-bstack`; asking your agent to use it installs the full bstack package. skills.sh does not run setup automatically.

`bbishdotdev/ai-tools` is the source repository, and `install-bstack` is the skill selected from it. `npx skills add install-bstack` alone does not identify this repository. Keep `--skill install-bstack` so you don't have to choose from the development repository's individual skills. A broad install from `bbishdotdev/ai-tools/bstack` can list upstream and internal skills too; don't select all of those.

## Offline or manual install

From the ai-tools checkout:

```sh
python3 bstack/release/bstack/scripts/bstack.py install \
  --project /path/to/your/project --hosts codex claude cursor grok
```

Select the hosts you want configured. Installation copies `release/bstack/` into the project's `.bstack/package/` and creates the public skill bindings. You can transfer just that package directory to an offline machine and run its controller. No npm, skills.sh, Git, or network is needed, and the original source can be removed after installation.

## Local skills.sh sources and internal distributors

skills.sh copies skill folders, so the release includes a dedicated `install-bstack` transport skill containing an archive of the complete package. The installer unpacks that archive into the same canonical layout as the offline route.

For a local checkout, the following explicit commands use the skills.sh version tested by the verification harness. Run them from the consumer project and select the hosts you need:

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
      sdlc/
        wayfinder/SKILL.md
        to-spec/SKILL.md
        to-tickets/SKILL.md
        ...
      shared/
        router/                  # Internal bstack policy
        unslop/SKILL.md
        setup-bstack/SKILL.md
        bstack-auto/SKILL.md
        verify-bstack/SKILL.md
        handoff/SKILL.md
        memory/                  # Optional user-runtime payload, not a project skill
        workflow.py
        references/
      workspace/                 # CLI, Python core and compiled app
      scripts/bstack.py
      manifest.json
      ATTRIBUTION.md
    config.json
    instructions.md
    workspace/                   # Private work, separate from package
  .agents/skills/
    how/SKILL.md                  # Points to the packaged how skill
    architect/SKILL.md
    poteto-mode/SKILL.md
    ...                          # All 43 public entries
  .claude/skills/                 # Per-skill links to .agents/skills
  .cursor/skills/                 # Same shared entries
  .grok/skills/                   # Same shared entries
  AGENTS.md
  CLAUDE.md
```

Each public entry is a small binding to its exact packaged skill. Hosts can discover the individual names without loading all their instruction bodies. The full skills and supporting files live once in the package. Principles have no public skill entry; the active skill loads relevant principles and playbooks as needed.

The generated release groups skills into engineering, SDLC and shared buckets and includes the GitHub PR template and publishing helper. Its private memory payload installs separately when requested. Frozen `upstream/` snapshots remain development inputs and are not installed as a second collection.

## Optional shared memory

After installing bstack, ask:

> Use setup-bstack to enable shared personal memory on this machine.

The agent previews user-wide configuration, then applies the unchanged plan within your setup authorization. To inspect the plan yourself, run `python3 .bstack/package/scripts/bstack.py memory setup`. Apply it with `memory setup --apply-plan <digest>` and check `memory status`.

The runtime is copied to `~/.local/share/bstack/memory/runtime/`. It survives removing the source, installer, or project. Codex and Claude use native files; Cursor uses a labeled file bridge. Grok has no memory adapter. Existing notes and unrelated settings are preserved, and setup adds no personal notes.

Memory setup is independent of auto routing. It can enable native memory use and select a shared Claude directory, so review those changes. Existing source-linked `~/Work` installs are detected and left unchanged; migration is not automatic. See [memory setup and limits](shared/memory.md).

## Direct skills and automatic routing

Invoke `$how` in Codex or `/how` in slash-command hosts. This selects the how workflow and bstack's policy without first entering Poteto Mode. Other public skills work the same way. Invoke `poteto-mode` when you want its router to select a full engineering workflow.

Engineering and SDLC entrypoints are manual by default. Customized unslop stays active for prose. Use `bstack-auto on`, `off`, or `status` for optional automatic routing. Invoking `bstack-auto` without an argument shows those choices without running a command. You can also use the controller directly:

```sh
python3 .bstack/package/scripts/bstack.py auto on --project "$PWD"
python3 .bstack/package/scripts/bstack.py auto status --project "$PWD"
python3 .bstack/package/scripts/bstack.py auto off --project "$PWD"
python3 .bstack/package/scripts/bstack.py doctor --project "$PWD"
```

Setup preserves other instructions and configuration. Mode and ownership state live in gitignored `.bstack/`. Start a fresh session after bindings change; disabling auto cannot remove instructions already in a conversation. Checking status or repeating an unchanged mode does not require a fresh session.

When automatic routing is enabled for Codex, review its hooks by opening `codex` in a terminal in the project directory, then entering `/hooks` inside that CLI. `/hooks` is not a desktop chat command. Setup does not grant or inspect hook trust. `auto status` confirms the saved mode, not live hook execution or router delivery. With auto off, bstack has no automatic routing hooks to review. See [Codex hook review](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks).

Cursor and Grok's after-tool reminders do not provide first-tool or tool-free prompt injection.

## Update, migrate, and remove

The [workspace app](workspace/README.md) runs from `.bstack/package/workspace/cli.py`. Initialize it once with `--project <project-root> init`, then use `serve` for the browser or `call` for agent operations. Private work survives package updates and removal. Stop old workspace servers and writers before upgrading the runtime; the new core backs up and migrates existing stores on discovery.

Planning and tickets each default to local and have [independent provider settings](shared/references/work-adapters.md). External providers are not yet implemented. Manual work needs no role configuration; autonomous grilling follows the [decision-authority preflight](shared/references/decision-authority.md).

Rerun the installer from a reviewed newer release. It verifies the owned package, preserves auto preference and selected hosts, and rolls back on installation errors. Modified or unowned files stop the update.

Existing offline installs under `.agents/skills/poteto-mode/` migrate to `.bstack/package/` after their integrity and ownership checks pass. Existing third-party-distributed Poteto Mode folders are not adopted or deleted; resolve those conflicts through their distributor before installing the new package.

Run `python3 .bstack/package/scripts/bstack.py uninstall --project "$PWD"` to remove the verified owned package and bindings. Private work and independently distributed installer skills remain. Remove `install-bstack` through its distributor if desired.

Generated bindings contain local paths. Install per checkout rather than checking machine-specific bindings and ownership state into another project. Stable instruction pointer blocks can be committed. Reinstallation recreates the ignored package.

Optional helper programs still require their own runtimes or authorized external services. Installation does not provision them. See [maintainer verification](shared/skills/verify-bstack/SKILL.md) and [upstream ownership](UPSTREAM.md).
