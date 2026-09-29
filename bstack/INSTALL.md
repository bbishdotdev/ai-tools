# Install bstack

bstack installs one package and a set of directly invocable skills. Poteto Mode is an engineering entry within that collection. The package contains the exact reviewed dependencies and customizations; installation never fetches newer upstream sources.

The controller requires Python 3.11+ on POSIX. These instructions cover project-local CLI installation and optional user-wide memory setup. Windows, global installation of the full skill collection, desktop apps, and native plugin managers need separate integration and verification.

## With skills.sh

From the project where you want to use bstack, run:

```sh
npx skills add bbishdotdev/ai-tools --skill install-bstack
```

Choose your agent and project scope if prompted. Open your agent in that project, or start a fresh session if it was already running, and ask:

> Install bstack in this project.

Or invoke `$install-bstack` in Codex, `/install-bstack` in Claude Code or Cursor. The installer supports agent selection when you ask to install or upgrade bstack; you don't need to name a script or provide its flags.

Your agent runs the bundled installer, connects the selected tools, and checks the installation with `doctor`. After a successful check, it offers automatic routing if it is off. It only enables routing when you opt in, including when you already requested it alongside installation. Upgrades preserve your existing mode and selected tools.

There are two steps: skills.sh downloads `install-bstack`; asking your agent to use it installs the full bstack package. skills.sh does not run setup automatically.

`bbishdotdev/ai-tools` is the source repository, and `install-bstack` is the skill selected from it. `npx skills add install-bstack` alone does not identify this repository. Keep `--skill install-bstack` so you don't have to choose from the development repository's individual skills. A broad install from `bbishdotdev/ai-tools/bstack` can list upstream and internal skills too; don't select all of those.

### Install the installer once

To reuse `install-bstack` across projects, install just that skill at user scope:

```sh
npx skills add bbishdotdev/ai-tools --skill install-bstack -g
```

Select your agent tools when prompted. Then open an agent in any target repo and invoke `install-bstack` or ask it to install bstack. Start a fresh agent session if the newly installed skill isn't visible. The full bstack package still installs per repo. Global availability of the installer does not enable routing or install the full collection in every project.

### Claude desktop discovery

After installation or an upgrade that changes skill bindings, start a **new Code chat** in Claude desktop. An existing chat can retain its earlier skill list. Then type `/` to find the installed skills.

Claude also documents [`/reload-skills`](https://code.claude.com/docs/en/skills#edit-a-skill-during-a-session) to rescan skills in a running session. Use it inside the affected chat if that command is available; availability in the desktop build must be checked there. It refreshes the skill catalog, not bstack's routing instructions or hooks. Setup still reports when a fresh session is needed and does not reset the current chat automatically. Running another `claude` process cannot refresh the desktop chat you already have open.

Claude's [Code tab supports project skills and slash invocation](https://code.claude.com/docs/en/desktop#use-skills). If skills are still missing, check that the session runs in the same checkout where bstack was installed, with `claude` included in its configured hosts. The installer creates `.claude/skills/<name>` links to the project's shared skill entries. `doctor` validates those files; it does not verify the desktop command menu.

A separate worktree, cloud session, or SSH host can have a different filesystem. Install bstack in that session's checkout. Copying `.bstack/config.json` from another checkout is not a substitute: ownership records and generated bindings contain paths to their original project. Regular Chat and Cowork are separate environments and are not covered by this project installer.

## From a download or clone

[Download bstack](https://github.com/bbishdotdev/ai-tools/releases/latest) and choose the `bstack-<version>.zip` asset. Extract it to get one `bstack/` folder. The automatic source ZIP and tarball on that page contain the development repository; the named bstack ZIP contains the ready-to-use installer.

Ask your agent:

> Read SKILL.md in the extracted bstack folder and install bstack into my project at /path/to/my-project.

Or, from that extracted folder, run:

```sh
python3 install.py --project /path/to/my-project
```

The project directory must already exist. Add `--hosts codex claude cursor grok`, with only the tools you want, to choose hosts. Without this flag, a new install configures all four; an upgrade preserves its existing selection.

The installer checks the bundled files, copies the package into `.bstack/package/`, creates the skill bindings, and runs `doctor`. Setup needs Python 3.11+ but no npm, skills.sh, Git, or network. You can remove the downloaded folder afterward. Start a fresh agent session when the result requests it. Automatic routing and shared memory remain optional.

To check a download before extracting it, save `SHA256SUMS` beside the ZIP and run `sha256sum -c SHA256SUMS` on Linux, or `shasum -a 256 -c SHA256SUMS` on macOS. Both assets come from the same release.

### Use a clone or source archive

The repository includes the same installer. From the ai-tools folder, run:

```sh
python3 bstack/release/skills-sh/install-bstack/install.py --project /path/to/my-project
```

Or ask your agent to read `bstack/release/skills-sh/install-bstack/SKILL.md` and install into the target project. Despite the directory name, this is a local Python installer; it does not call skills.sh. You can also transfer just the complete `install-bstack/` folder. Keep its `assets/` and `scripts/` alongside `install.py`.

### Local skills.sh sources

skills.sh copies skill folders, so the release includes a dedicated `install-bstack` transport skill containing an archive of the complete package. The installer unpacks that archive into the same canonical layout as the offline route.

For a local checkout, the following explicit commands use the skills.sh version tested by the verification harness. Run them from the consumer project and select the hosts you need:

```sh
npx skills@1.7.0 add /path/to/ai-tools/bstack/release/skills-sh \
  --skill install-bstack --agent codex claude-code cursor grok
python3 .agents/skills/install-bstack/install.py \
  --project "$PWD" --hosts codex claude cursor grok
```

skills.sh supports its default host links and `--copy`; both transport the same archive. The second command is required because skills.sh does not execute setup. Keep the installer folder intact so skills.sh can update or remove it normally. The installed package operates independently of that archive.

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
