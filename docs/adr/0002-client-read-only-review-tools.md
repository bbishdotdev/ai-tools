# Client read-only tools for static PR review

Status: superseded

Superseded by: [0003: Minimal reviewer capabilities for static PR review](0003-minimal-reviewer-capabilities.md)

Date: 2026-11-19

Decision owner: Brenden Bishop

Confirmation: Brenden chose this direction in the implementation discussion on 2026-11-19 and asked for this record to replace the earlier one.

Supersedes: [0001: Restricted tools for static PR review](0001-restricted-static-review-tools.md)

Static PR review starts each reviewer CLI in its own read-only mode inside a directory that holds the pinned trees, the PR context, and BStack's review policy. Claude Code gets its read-only file tools. Codex runs in its read-only sandbox. BStack no longer ships a repository browser, removes no further client tools, and does not audit what a reviewer read. It keeps the target check, the pinned snapshot, the tool-free preflight, and controller-only publication.

The earlier design gave reviewers a bundled browser as their only tool. That browser could reach a model only as a local MCP server, and a managed Claude Code installation refused to start any such server, so review could not run there at all. Each replacement we considered needed separate enforcement code per client. BStack cannot anticipate every client and organization policy, so the client and the person running the review now own that boundary.

The cost is real. A Codex reviewer can run read-only commands, including code from the PR, and read any file the user can read. A hostile PR opened against the project's repository, including one from a fork, could steer a reviewer into quoting local data in a finding that the controller then publishes. The preflight is the only check against that and can be fooled. Consumers decide which PRs are safe to review on a machine; an optional `worker` can add OS isolation. Fork PRs get no special handling yet. Revisit if BStack starts publishing reviews unattended for repositories that accept PRs from untrusted authors.
