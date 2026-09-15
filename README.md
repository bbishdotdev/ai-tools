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
python3 skills/memory-policy/scripts/install.py
python3 skills/memory-policy/scripts/install.py --apply
```

Use the permanent `~/Work/ai-tools` checkout as the versioned source. The first command previews the links. The second creates these Work-level entrypoints:

- `~/Work/.agents/skills/memory-policy/` links to this repository's skill.
- `~/Work/AGENTS.md` links to `rules/memory-policy.md`.
- `~/Work/CLAUDE.md` links to `AGENTS.md`.

The home-level `~/.agents`, Codex, Claude, and Cursor entrypoints route to that shared Work setup. The installer also generates a Cursor rule for projects beneath your home directory. It respects `CODEX_HOME` and `CLAUDE_CONFIG_DIR` and refuses to replace existing files. Keep the permanent checkout in place; runtime links must not target a task worktree. This installs local access on this machine, not remote or cloud filesystem access.

Add the text from `rules/memory-policy.md` to Cursor's global User Rules through its UI. The rule only routes memory operations to the skill. Native memories remain in each product's native system.

Check the local installation with `python3 ~/.agents/skills/memory-policy/scripts/status.py`. The shared `sync.py` helper previews and applies approved additions, updates, and deletions to Codex and Claude native files. It preserves unrelated content and checks the reviewed file revision before writing. Run `python3 ~/.agents/skills/memory-policy/scripts/sync.py --help` for its interface. Previewing does not save a memory or proposal.

All three products are the default destinations. Cursor's ordinary desktop native interface remains unavailable in the tested setup, so the default operation refuses to write anywhere. A reduced destination set requires the user's explicit approval of a partial save. A Cursor file bridge also requires an explicit choice because it would not be native recall. The installer and sync helper leave native memory settings unchanged. Codex needs its memory feature enabled; Claude needs a fixed absolute user-level `autoMemoryDirectory`. Changing Claude's directory does not migrate its old project memories. See [native compatibility](skills/memory-policy/references/native-interfaces.md) for evidence and limitations.

No watcher or background approval hook is installed. The skill governs agents that read it; it does not prove approval enforcement for internal background writers. A successful helper result proves local file readback. Fresh-session native recall is a separate test.

To check natural policy discovery, start a fresh chat in each app with a project under `~/Work` and send:

> I’m considering remembering “Use short paragraphs.” What would you save? Don’t save it yet.

The agent should find the shared policy without being told its path, propose a personal preference, and save nothing. A fact such as “this app uses Convex” belongs in project instructions or documentation.

After every chosen destination is configured and available, test actual synchronization by asking one app:

> Remember that my temporary memory verification phrase is amber-otter-42. I approve saving this exact temporary note across our configured destinations.

Start unrelated fresh chats in all three apps and ask “What is my temporary memory verification phrase?” Do not include the answer, policy path, or earlier conversation. Each reply should name the phrase and identify its native source, or its bridge source if explicitly configured. Then approve a replacement phrase, repeat the fresh-chat check, and explicitly approve deletion. A destination that is pending or cannot recall the note has not passed. Creating three independent copies manually does not test synchronization.

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
