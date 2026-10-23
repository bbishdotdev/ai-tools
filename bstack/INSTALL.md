# Install bstack

bstack installs one package and a set of directly invocable skills. Poteto Mode is an engineering entry within that collection. The package contains the exact reviewed dependencies and customizations; installation never fetches newer upstream sources.

The controller requires Python 3.11+ on macOS or Linux. It installs the full collection per project. The installer skill alone can live at user scope. Windows and native plugin-manager installation are not supported by this package; desktop skill discovery needs a separate check after setup.

| If you have... | Use... |
| --- | --- |
| Access to skills.sh | [Install the installer skill](#with-skillssh), then ask your agent to install bstack |
| A release ZIP or a clone | [Run the bundled installer](#from-a-download-or-clone) without skills.sh |
| An existing installation | [Update with a newer installer](#update-migrate-and-remove) |

## With skills.sh

From the project where you want to use bstack, run:

```sh
npx skills add bbishdotdev/ai-tools --skill install-bstack
```

Choose your agent and project scope if prompted. Open your agent in that project, or start a fresh session if it was already running, and ask:

> Install bstack in this project.

Or invoke `$install-bstack` in Codex, `/install-bstack` in Claude Code or Cursor. The installer supports agent selection when you ask to install or upgrade bstack; you don't need to name a script or provide its flags.

Your agent runs the bundled installer, connects the selected tools, and checks the installation with `doctor`. New installs turn automatic engineering routing on and set project verification to `ask`. Use `--auto off` for manual routing, or `--verification off|ask|auto` to choose how verifiers are maintained. Upgrades preserve both settings and selected tools.

Ask "How do I use bstack?" or invoke `$bstack-guide` in Codex or `/bstack-guide` in slash-command hosts for a short walkthrough. It is also available while automatic engineering routing is off. If setup says a fresh session is required, use the guide there.

There are two steps: skills.sh downloads `install-bstack`; asking your agent to use it installs the full bstack package. skills.sh does not run setup automatically.

`bbishdotdev/ai-tools` is the source repository, and `install-bstack` is the skill selected from it. `npx skills add install-bstack` alone does not identify this repository. Keep `--skill install-bstack` so you don't have to choose from the development repository's individual skills. A broad install from `bbishdotdev/ai-tools/bstack` can list upstream and internal skills too; don't select all of those.

### Install a published version

The short command above reads the committed installer on `main`. It can include a prepared package before that version is published. To install a specific release through skills.sh, pin its tag. For example, to install 2.0.0:

```sh
npx skills add 'bbishdotdev/ai-tools#v2.0.0' --skill install-bstack
```

Then ask your agent to install bstack as usual. Use the tag of the release you want when upgrading, and review its [release notes](CHANGELOG.md). The release ZIP below provides the same versioned package without skills.sh. Neither route updates an installed project just because `main` changes.

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

If BStack is installed in a home folder or parent workspace, that does not configure every Git repo beneath it. Claude can read a parent `CLAUDE.md` while the child repo has no BStack skills or auto hook, which looks like partial routing. Run the installer for the **child Git repo root** and check that repo's `doctor`. A globally installed `install-bstack` skill can do this from a Code chat opened in the repo; it copies its bundled package there. From an already installed parent package, the equivalent commands are:

```sh
python3 /path/to/parent/.bstack/package/scripts/bstack.py setup --project /path/to/repo --hosts claude
python3 /path/to/repo/.bstack/package/scripts/bstack.py doctor --project /path/to/repo
```

Start a fresh Code chat rooted in that repo afterward. The parent can serve as a package source, but the child keeps its own copy and bindings. This is also the supported path when several repos share one parent workspace.

A separate worktree, cloud session, or SSH host can have a different filesystem. Install bstack in that session's checkout. Copying `.bstack/config.json` from another checkout is not a substitute: ownership records and generated bindings contain paths to their original project. Regular Chat and Cowork are separate environments and are not covered by this project installer.

## From a download or clone

[Download bstack](https://github.com/bbishdotdev/ai-tools/releases/latest) and choose the `bstack-<version>.zip` asset. Extract it to get one `bstack/` folder. The automatic source ZIP and tarball on that page contain the development repository; the named bstack ZIP contains the ready-to-use installer.

Ask your agent:

> Read SKILL.md in the extracted bstack folder and install bstack into my project at /path/to/my-project.

Or, from that extracted folder, run:

```sh
python3 install.py --project /path/to/my-project
```

The project directory must already exist. Add `--hosts codex claude cursor grok`, with only the tools you want, to choose hosts. Without this flag, a new install configures all four; an upgrade preserves its existing selection. You can pass `--auto off` and `--verification off|ask|auto` at install time.

The installer checks the bundled files, copies the package into `.bstack/package/`, creates the skill bindings, and runs `doctor`. Setup needs Python 3.11+ but no npm, skills.sh, Git, or network. You can remove the downloaded folder afterward. Start a fresh agent session when the result requests it. Automatic routing is on for a new install and can be turned off; shared memory remains optional.

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

## Project instructions

Setup writes the seven-rule [bstack baseline](shared/references/baseline-agents.md) directly into a managed block in `AGENTS.md`. When Claude is selected, it also adds the block to `CLAUDE.md`. Missing files are created; existing project instructions stay intact. A `CLAUDE.md` link to `AGENTS.md` keeps one shared block. Baseline rules apply even when automatic routing is off.

Keep project-specific guidance outside `<!-- bstack:begin -->` and `<!-- bstack:end -->`. Updates replace only the owned block; uninstall removes it and preserves your guidance. A repository with only `CLAUDE.md` also gets `AGENTS.md` so the other tools have a shared entry. Setup does not stage or commit these project files. Review new root instruction files and commit them if they should travel with the repository; until then, Git lists them as untracked.

If an owned `AGENTS.md` or `CLAUDE.md` is missing on upgrade, the installer recreates its managed block and reports which file was rebuilt. Bstack does not keep the surrounding project text, so recover any lost guidance from Git or a backup. An existing file with a changed or removed managed block remains a conflict; setup will not overwrite it.

Setup does not run any tool's native init. The baseline is enough to finish installation. You can then ask your agent to inspect the repository and add project-specific guidance outside the block, or use your tool's init if available. Preserve the block and check afterward:

```sh
python3 .bstack/package/scripts/bstack.py doctor --project "$PWD"
```

If another tool changes or removes a managed block, `doctor` reports it and setup refuses to overwrite the conflict. Ask your agent to preserve the new project text, restore the exact block recorded in `.bstack/config.json`, and rerun setup. This checks the file contents; it cannot prevent another tool from editing them or prove that an agent followed the instructions.

## Check optional model workflows

Normal `doctor` checks the package and bindings, then lists which CLI launchers it can find. It doesn't spend model calls or block basic BStack use when an optional CLI is missing. Before a model-backed workflow, check the one you plan to use:

```sh
python3 .bstack/package/scripts/bstack.py doctor --project "$PWD" --live --workflow review-pr
python3 .bstack/package/scripts/bstack.py doctor --project "$PWD" --live --workflow grilling
python3 .bstack/package/scripts/bstack.py doctor --project "$PWD" --live --workflow to-pr
```

The live check sends a short prompt to the configured model for each role. A failed role stops that workflow and tells you whether to fix login, choose another model, or correct the launcher. The PR review runner also checks its roles before a new full review. Autonomous grilling's normal preflight checks its CLI roles before planning writes. The `to-pr` check proves Codex can answer a text prompt; its image tool and the final picture still need a real visual attempt.

`review-pr` needs an isolated model worker for every PR. Its tool-free safety preflight checks the pinned diff and discussion first, but a pass does not give reviewers host access. The general model doctor checks model access; the review runner's own `doctor --live` checks its worker canary. Optional app or test execution needs a separate credential-free runtime worker. See [review setup](engineering/review-pr/references/running.md) before automating reviews.

If a tool is launched through a local wrapper, tell your agent the working terminal command. For example, a wrapper that runs `launch claude -- <arguments>` can be saved once:

```sh
python3 .bstack/package/shared/model_cli.py --project "$PWD" configure \
  --cli claude --command 'launch claude -- {args}'
python3 .bstack/package/scripts/bstack.py doctor --project "$PWD" --live --workflow review-pr
```

`{args}` is one argument slot. BStack passes the normal CLI flags there as separate arguments; it never evaluates this setting as shell code. The private `.bstack/model-clis.json` file stays out of Git. You can configure Codex, Claude, Cursor, and Grok separately. Only the workflows that use a CLI need its launcher. If a first check fails, fix that launcher's command and rerun the live check. A project with no extra model workflow needs none of this setup.

Keep credentials in the CLI's normal login or environment, not in the saved command template.
If the wrapper executable lives in the project, a relative executable path is resolved from the project root. Use absolute paths for any separate script files passed to that executable.

The current launcher adapters cover Codex, Claude Code, Cursor and Grok. AMP has not been added or verified yet.

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
    ...                          # One entry per public skill in manifest.json
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

New installs enable automatic engineering routing. You can still invoke a named skill directly to load its instructions and relevant dependencies. Poteto Mode selects a full engineering workflow. Customized unslop stays active for prose. Use `bstack-auto on`, `off`, or `status` to control automatic routing. Invoking `bstack-auto` without an argument shows those choices without running a command. You can also use the controller directly:

```sh
python3 .bstack/package/scripts/bstack.py auto on --project "$PWD"
python3 .bstack/package/scripts/bstack.py auto status --project "$PWD"
python3 .bstack/package/scripts/bstack.py auto off --project "$PWD"
python3 .bstack/package/scripts/bstack.py doctor --project "$PWD"
```

Setup preserves other instructions and configuration. Mode and ownership state live in gitignored `.bstack/`. Auto hooks send a short router reminder; they do not add the full engineering corpus to every turn. Start a fresh session after bindings change; disabling auto cannot remove instructions already in a conversation. Checking status or repeating an unchanged mode does not require a fresh session.

When automatic routing is enabled for Codex, review its hooks by opening `codex` in a terminal in the project directory, then entering `/hooks` inside that CLI. `/hooks` is not a desktop chat command. Setup does not grant or inspect hook trust. `auto status` confirms the saved mode, not live hook execution or router delivery. With auto off, bstack keeps its PR creation guard for selected hosts, so Codex hook trust may still need review. See [Codex hook review](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks).

Cursor and Grok's after-tool reminders do not provide first-tool or tool-free prompt injection.

## Update, migrate, and remove

Refresh the installer first, then run it again for the target project. If you used skills.sh, repeat the same `npx skills add ... --skill install-bstack` command from [above](#with-skillssh), with the new tag if you pin releases. Use `-g` again if your installer is user-scoped. Then ask your agent: "Use install-bstack to upgrade this project." If you installed from a release ZIP or clone, get the newer bundle and run its `install.py --project <project-root>`. Updating the installer skill alone does not update the project package.

The [workspace app](workspace/README.md) runs from `.bstack/package/workspace/cli.py`. Initialize it once with `--project <project-root> init`, then use `serve` for the browser or `call` for agent operations. Private work survives package updates and removal. Stop old workspace servers and writers before upgrading the runtime; the new core backs up and migrates existing stores on discovery.

Planning and tickets each default to local and have [independent provider settings](shared/references/work-adapters.md). External providers are not yet implemented. Manual work needs no role configuration; autonomous grilling follows the [decision-authority preflight](shared/references/decision-authority.md).

Project verification has its own setting. `ask` proposes the affected `verify-<app>` change during feature or bug work, `auto` maintains that path as part of authorized work, and `off` leaves the verifier alone unless requested. New installs default to `ask`; upgrades preserve the prior choice. These settings do not change normal test expectations. Use `python3 .bstack/package/scripts/bstack.py verification status --project "$PWD"` to inspect it. The [verification policy](shared/references/verification-policy.md) describes when to create, update, or skip a verifier. The [setup map](shared/references/setup-requirements.md) explains optional tools only when a workflow needs them.

The installer checks the owned package, preserves auto preference and selected hosts, runs `doctor`, and rolls back on installation errors. Modified or unowned files stop the update. Read the result before starting a new agent session; `doctor` checks files and bindings, not live skill selection or hook delivery. The installed version is in `.bstack/package/manifest.json`.

Existing offline installs under `.agents/skills/poteto-mode/` migrate to `.bstack/package/` after their integrity and ownership checks pass. Existing third-party-distributed Poteto Mode folders are not adopted or deleted; resolve those conflicts through their distributor before installing the new package.

Run `python3 .bstack/package/scripts/bstack.py uninstall --project "$PWD"` to remove the verified owned package and bindings. Private work and independently distributed installer skills remain. Remove `install-bstack` through its distributor if desired.

Generated bindings contain local paths. Install per checkout rather than checking machine-specific bindings and ownership state into another project. Stable instruction pointer blocks can be committed. Reinstallation recreates the ignored package.

Optional helper programs still require their own runtimes or authorized external services. Installation does not provision them. See [maintainer verification](shared/skills/verify-bstack/SKILL.md) and [upstream ownership](UPSTREAM.md).
