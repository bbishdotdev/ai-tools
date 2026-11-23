# Minimal reviewer capabilities for static PR review

Status: accepted

Date: 2026-11-23

Decision owner: Brenden Bishop

Confirmation: Brenden asked for the Codex restrictions to return on 2026-11-23, after an enterprise merge review flagged their removal in 3.5.0.

Supersedes: [0002: Client read-only tools for static PR review](0002-client-read-only-review-tools.md)

Static PR review still starts each reviewer CLI in its own read-only mode inside the pinned snapshot, with no MCP server. BStack now also turns off every client capability a review does not need to read that snapshot. For Codex that means connected apps, plugins, browser and computer use, subagents, hooks, memories, goals, image tools, and skill discovery are off; its shell stays on because Codex has no read-only file tool. Commands Codex runs get a minimal environment, and each CLI starts without the other provider's credentials. The target check, pinned snapshot, tool-free preflight, and controller-only publication are unchanged.

The previous record said BStack removes no further client tools and leaves that boundary to the client. That went further than removing the MCP browser required. Leaving optional capabilities on gave a reviewer steered by a hostile PR more ways to reach data and services, including connected apps that the read-only sandbox does not cover. Turning them off costs one list of flags and does not depend on anything a managed installation blocks.

The cost of the previous record otherwise stands. BStack does not confine reads: a Codex reviewer can run read-only commands and read any file the user can read, and the preflight is the only check against a hostile PR. A passing live doctor shows a reviewer can read the snapshot, not that other reads are blocked. The feature list tracks Codex's flag names and needs review when Codex adds capabilities. Revisit if a client offers a way to confine reads to the snapshot that works under managed policy.
