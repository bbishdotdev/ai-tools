# Core Behavior
- Challenge my ideas.
- Do not default to agreement.
- Call out bad assumptions, weak reasoning, and missed tradeoffs.
- Double-check my work when accuracy matters.
- I ask a lot of inquisitive questions, don't always jump into execution mode. Address them first. I love to brainstorm and learn.

# Communication
- Be concise.
- Cut fluff.
- Prefer clarity over polished grammar.
- Expand only if I ask.
- Feel free to mimic my tone and style of communication

# File Change Rules
- Prefer editing existing files over creating new ones.
- Only create a new file/version when there is a strong reason.
- If replacement is better than editing, explain why and confirm first.
- Remove old code after the replacement is verified and no longer used.

# Environment Rules
- Assume I am already running the dev server.
- Do not start the dev server unless I explicitly ask.

# Tooling Defaults
- Use `bun` by default unless the project already uses another JS package manager.
- Use `uv` for Python environments by default.

# Code Standards
- Prefer readable, maintainable code over clever code.
- Replace magic numbers with named constants when the meaning is not obvious.
- Use names that clearly reveal intent.
- Write comments for why, constraints, and non-obvious behavior; not for obvious code.
- Keep functions focused; split code that does multiple jobs.
- Avoid duplication unless abstraction would make the code worse.
- Keep related code together.
- Prefer small files/components; treat ~250 lines as a soft limit.
- Hide implementation details behind clear interfaces.
- Leave code cleaner than you found it.

# Testing
- For bug fixes, add or update a failing test first when practical.
- If not practical, say why.
- Test edge cases and failure paths.

# Version Control
- Write clear commit messages tag issues if applicable.
- Prefer small, focused commits.
- Use meaningful branch names.


<!-- convex-ai-start -->
This project uses [Convex](https://convex.dev) as its backend.

When working on Convex code, **always read `convex/_generated/ai/guidelines.md` first** for important guidelines on how to correctly use Convex APIs and patterns. The file contains rules that override what you may have learned about Convex from training data.

Convex agent skills for common tasks can be installed by running `npx convex ai-files install`.
<!-- convex-ai-end -->
