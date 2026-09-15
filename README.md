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

The first command previews the links. The second connects the shared skill through `~/.agents/skills/`, Claude, and Cursor, and links the Codex and Claude global instruction files to one policy router. It also generates a Cursor rule for projects beneath your home directory. It respects `CODEX_HOME` and `CLAUDE_CONFIG_DIR` and refuses to replace existing files. Keep this checkout in place because the links point to it.

Add the text from `rules/memory-policy.md` to Cursor's global User Rules through its UI. The rule only routes memory operations to the skill. Native memories remain in each product's native system.

Check the local installation with `python3 ~/.agents/skills/memory-policy/scripts/status.py`. Native sync and background approval enforcement have not passed compatibility checks across all three tools, so no sync writer, hook, or watcher is installed. See the skill's native-interface reference for measured limits. The installer never changes existing memories or generation settings.

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
