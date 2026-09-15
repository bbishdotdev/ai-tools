# ai-tools

My personal AI toolbox.

This repo is where I keep the agent prompts, skills, rules, GitHub workflows, and small bits of process that make AI coding tools behave more like useful teammates and less like autocomplete with confidence issues.

The goal is simple:

Make the default behavior better.

## What is in here

- `agents/`: full agent prompts or modes, like a development coach that teaches instead of silently doing the work.
- `skills/`: reusable skill folders with `SKILL.md`, references, and optional UI metadata.
- `rules/`: shared behavior and writing rules that can be copied into agents, skills, or project instructions.
- `github/`: GitHub issue templates, automation, and review agents.

## Current skills

- `memory-policy`: require approval for personal memories and coordinate verified native destinations.
- `refine`: stress-test a plan by asking hard questions until the decision tree is clear.
- `milestone`: turn a product idea into a PRD-like milestone.
- `github-issue`: turn vague work into clear GitHub issues with acceptance criteria, tests, and sequencing.
- `issue-orchestrator`: pull a batch of issues into a real execution plan, then drive implementation and verification.
- `development-coach`: help the user learn by building instead of doing the work for them.
- `write-like-me`: turn raw thoughts into clear, direct writing that sounds like me.
- `conventional-commit`: shape changes into a conventional commit message.

## Why this exists

AI tools are powerful, but the defaults are often weird.

They over-polish writing.
They rush into code.
They skip the boring product thinking.
They act like every task is isolated.
They say "done" without enough evidence.

I do not want that.

I want agents that challenge weak ideas, preserve context, write issues that can be executed, review work against the real goal, and help me get better while I build.

Some of this is prompts.
Some of it is workflow.
Some of it is refusing to let the tool turn every problem into a code generation slot machine.

## Using this repo

Copy the pieces you need into the tool you are using.

Use `skills/` anywhere Vercel-style skills are supported. Each skill follows the frontmatter plus `# Title`, `## When to Use`, and `## Steps` format.

Install a whole skills repo:

```bash
npx skills add bbishdotdev/ai-tools
```

Install the writing skill:

```bash
npx skills add bbishdotdev/ai-tools --skill write-like-me
```

Install the development coach skill:

```bash
npx skills add bbishdotdev/ai-tools --skill development-coach
```

Install from a local checkout:

```bash
npx skills add ./skills
```

Install the shared memory policy from a stable checkout:

```bash
python3 skills/memory-policy/scripts/install.py --activate-sync
python3 skills/memory-policy/scripts/install.py --activate-sync --apply
```

Use the permanent `~/Work/ai-tools` checkout as the versioned source. The first command previews installation and activation. The second applies them and creates these Work-level entrypoints:

- `~/Work/.agents/skills/memory-policy/` links to this repository's skill.
- `~/Work/AGENTS.md` links to `rules/memory-policy.md`.
- `~/Work/CLAUDE.md` links to `AGENTS.md`.

The home-level `~/.agents`, Codex, Claude, and Cursor entrypoints route to that shared Work setup. The installer also generates local Cursor user rules. It respects `CODEX_HOME` and `CLAUDE_CONFIG_DIR` and refuses to replace unrelated instruction files. Activation updates only the requested memory settings and the managed Cursor router, with backups. Keep the permanent checkout in place; runtime links must not target a task worktree. This installs local access on this machine, not remote or cloud filesystem access.

Cursor's installed local user rules route memory changes to the shared skill and supply approved memory text inline. No manual copying into the User Rules UI is needed for this local setup. An existing account User Rule can remain as an additional policy router; it does not copy local memories into cloud sessions. Codex and Claude read their native memories.

Check the local installation with `python3 ~/.agents/skills/memory-policy/scripts/status.py`. The shared `sync.py` helper previews and applies approved additions, updates, and deletions to all three destinations. It preserves unrelated content and checks the reviewed file revision before writing. Previewing does not save a memory or proposal.

Codex uses `$CODEX_HOME/memories`. Claude uses a fixed user-wide native directory, defaulting to `~/Work/.agents/memory-sync/claude`. Cursor's source copy is `~/Work/.agents/memory-sync/cursor/MEMORY.md`. Each approved sync also generates `~/.cursor/rules/personal-memories.mdc` with the managed notes inline and `alwaysApply: true`. Fresh chats receive those notes as rule context without fetching the bridge. Ordinary recall skips the policy and status workflow. Cursor's file bridge is deliberately labeled as a bridge; it does not pretend to be an unavailable native interface. Native features stay enabled.

Activation enables Codex memory use and Claude auto memory while preserving generation settings, unrelated configuration, and hooks. Existing Claude project memory files stay intact; future sessions use the configured global index. No existing memories are automatically migrated. Configuration/router changes are backed up locally under `~/Work/.agents/memory-sync/backups`, outside this repository. The installer is idempotent and the shared paths resolve to the permanent Work checkout.

The agent checks exact conversational approval before calling the shared helper. The helper binds writes to a reviewed plan and checks all three destinations before writing. The generated Cursor rule contains only managed bridge entries and is refreshed by approved sync operations. It is not a second manually edited source. A stale generated copy is reported by status and inspection. No watcher propagates arbitrary native edits, and no claim is made that internal background writers honor the conversational approval policy. See [compatibility and verification](skills/memory-policy/references/native-interfaces.md) for the tested scope.

To check natural policy discovery, start a fresh chat in each app with a project under `~/Work` and send:

> I’m considering remembering “Use short paragraphs.” What would you save? Don’t save it yet.

The agent should find the shared policy without being told its path, propose a personal preference, and save nothing. A fact such as “this app uses Convex” belongs in project instructions or documentation.

To test synchronization after activation, ask one app:

> Remember that my temporary memory verification phrase is amber-otter-42. I approve saving this exact temporary note across our configured destinations.

Start unrelated fresh chats in all three apps and ask “What is my temporary memory verification phrase?” Do not include the answer, policy path, or earlier conversation. Each reply should simply name the phrase. Cursor should answer from its generated rule context without searches, memory-policy invocation, or sync-status commands. Ask for provenance separately only when diagnosing a failure. Then approve a replacement phrase, repeat the fresh-chat check, and explicitly approve deletion. A destination that is pending or cannot recall the note has not passed. Creating three independent copies manually does not test synchronization.

Use `agents/` for custom agent modes. Copy them into `.claude/`, `.github/`, or wherever your tool supports custom agents.

Use `github/` as the source for your repo's `.github/` folder. Copy the issue templates, workflows, scripts, and GitHub-specific agents from there.

For project-wide behavior, start with `rules/AGENTS.md`.

For writing voice, use `rules/writing.md` or the bundled reference inside `skills/write-like-me/`.

## Design notes

These files are intentionally plain.

Markdown over magic.
Small folders over frameworks.
Explicit instructions over vibes.

If a skill needs to ship with reference material, it should keep that material in `references/` so the skill can move on its own.

If an agent is really a mode, it should live in `agents/`. A thin skill can point at it for tools that only support skills.

That is the pattern.
