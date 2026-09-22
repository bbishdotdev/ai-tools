# bstack

Version 0.3.0. bstack is the collection; Poteto Mode is one engineering skill within it. The package groups public engineering skills under `engineering/`, planning skills under `sdlc/`, and shared controls and writing skills under `shared/`. Principles and playbooks stay internal and load only when needed.

The local workspace app supports Wayfinder maps, accepted decisions, specs and Kanban tickets. The PR workflow provides a visual briefing, final overlap review, and optional GitHub publishing. Shared memory awaits runtime integration.

## Install

From the project where you want to use bstack, run:

```sh
npx skills add bbishdotdev/ai-tools --skill install-bstack
```

Choose your agent and project scope if prompted. Then open your agent in that project and ask:

> Use install-bstack to set up this project for my installed tools.

skills.sh downloads the installer skill; your agent runs it to install the full bundled package and check the result. Keep both the repository name and `--skill install-bstack` in the command. You don't need to select individual engineering or SDLC skills. Automatic routing stays opt-in. Python 3.11+ on POSIX is required.

### Offline or manual install

To install this exact package from a reviewed clone or transferred release, run:

```sh
python3 <package-path>/scripts/bstack.py install --project <project-root> --hosts codex claude cursor grok
```

Select the hosts you need. This creates `.bstack/package/` and direct public entries in `.agents/skills/`, with links for the selected hosts. No network, skills.sh, Git, or upstream access is needed for this route. The original source can be removed afterward.

A skills.sh distributor uses the separate `install-bstack` transport skill, whose archive contains this same package. Run that skill's installer after distribution. skills.sh does not run setup automatically.

## Use skills directly

Invoke `how`, `architect`, `tdd`, or another public skill by its native host command prefix. Codex uses `$how`; slash-command hosts use `/how`. Use `poteto-mode` when you want the router to select a complete engineering workflow. The [index](index.json) resolves internal dependencies; the [manifest](manifest.json) lists public skills and exact installed files.

Engineering and SDLC skills are explicit-only by default. The customized [unslop](shared/unslop/SKILL.md) remains active for prose. `bstack-auto on`, `off`, and `status` control optional automatic routing with the host's skill prefix. A bare invocation shows these choices without running a command. The same commands are available from the controller:

```sh
python3 <project-root>/.bstack/package/scripts/bstack.py auto on --project <project-root>
python3 <project-root>/.bstack/package/scripts/bstack.py doctor --project <project-root>
```

Start a fresh session after bindings change. Checking status or repeating an unchanged mode does not require a new session. Turning auto off cannot erase existing conversation context.

With automatic routing enabled for Codex, open `codex` in a terminal in the project directory and enter `/hooks` there to review hook trust. `/hooks` is not a desktop chat command. Setup does not grant or inspect trust, and `auto status` confirms configuration only. With auto off, no bstack routing hook review is needed. Cursor and Grok's after-tool reminders do not guarantee first-tool or tool-free delivery. CLI packaging does not establish desktop or native plugin-manager support.

## Local planning and tickets

```sh
python3 <package-path>/workspace/cli.py --project <project-root> init
python3 <package-path>/workspace/cli.py --project <project-root> serve
```

Open the printed local URL. Work stays in the owning Git project's ignored `.bstack/workspace/`; linked worktrees share the same store. The browser and agent CLI use the same records. See [workspace use](workspace/README.md) and [operations](workspace/OPERATIONS.md). Python and Git are required for the workspace; Node and network access are not required to run the compiled app.

Use `wayfinder` to organize unknowns, `to-spec` for accepted scope, and `to-tickets` for implementation slices. Known small work can start with a ticket. Planning does not start implementation. The `implement` entry revalidates approved work before entering the engineering process. `handoff` preserves current record revisions, authority and artifacts for a fresh session, including prototype-to-implementation transitions.

Manual planning needs no model setup. Explicit autonomous grilling requires two configured models and evidence that the host can run them; see [decision authority](shared/references/decision-authority.md). Wayfinder and tickets have [independent provider selections](shared/references/work-adapters.md). Both default to local. Jira, GitHub and Linear adapters remain future work; unsupported configured providers are reported without silent fallback.

## Pull requests

Use [to-pr](engineering/to-pr/SKILL.md) for authorized PR delivery. It reuses the completed implementation and review, produces a short visual briefing, and checks all open work for duplicate or conflicting intent. Flagged or incomplete reviews publish as drafts with linked notices.

The [template](github/pull_request_template.md) and [Python helper](github/pr.py) ship here. The helper uses authenticated `gh` for pushed branches within the same GitHub repository. It prepares locally, checks freshness, and writes only with explicit `publish --write`. Media upload falls back to the authored Mermaid, table, or text explanation. Other forges need a supported adapter; GitHub PR publishing does not implement the planning or ticket tracker adapters.

## Update and remove

Rerun the installer from a reviewed release to update. It preserves the chosen mode, verifies owned files, and refuses unowned or changed content. Existing offline Poteto Mode bundles migrate to the package layout. Old third-party distributor entries must be resolved through their owner if they collide.

Run the canonical controller with `uninstall --project <project-root>` to remove its verified package and owned bindings. Private work, workspace databases, role and adapter configuration, artifacts, and separately distributed installer skills are preserved. Install separately per checkout; generated absolute bindings are machine-specific.

## Dependencies and source

[Attribution and required notices](ATTRIBUTION.md) travel with the package. The manifest records source hashes and build transformations. [layers.json](layers.json) records the active replacements. Installation never follows upstream latest.

Optional helper programs still need their own runtimes or configured services. Read the [capability contract](shared/router/references/capabilities.md) before using them. Live CLI verification needs authenticated providers and consumes model usage. Hash checks establish integrity against the reviewed inputs, not the authenticity of an arbitrary download.
