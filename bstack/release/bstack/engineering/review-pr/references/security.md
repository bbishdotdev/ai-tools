# Reviewer-job security

The PR author controls code, descriptions, comments, and some linked material that the review models read. Treat all of it as untrusted data. The asset to protect is the machine running `review-pr`: its files, credentials, configured CLI sessions, network access, and GitHub review authority. An OWASP check of the contributor's code answers a different question.

The [agent-owasp-compliance skill](https://github.com/github/awesome-copilot/blob/main/skills/agent-owasp-compliance/SKILL.md) is a useful prompt for examining tool use, privilege, trust, and audit trails. Its keyword scan is not a runtime defense. Use the [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) for the actual risk names and definitions. The referenced skill's short labels do not all match that source.

## Current boundaries

- The runner pins the PR source and passes it as review data. It does not execute repository tests or hooks. It disables supported CLI customization and MCP paths, constrains Claude's tools, and validates model output before publication.
- A controlled canary test showed Codex's `--sandbox read-only` role could read a file outside the pinned snapshot. Read-only prevents writes; it does not confine reads to the PR. Claude's restricted role denied that particular read, which is useful evidence but not a universal isolation guarantee.
- Model subprocesses inherit the runner's environment, and the CLIs use the reviewer's local authentication. A hostile PR can try to redirect a model into reading host data and leaking it through its response or eventual review. Output schemas and prose instructions do not close that boundary.
- Public review receipts contain reproducible hashes, not signatures. The runner now reuses them only for the same authenticated GitHub account. Other developers' reviews remain untrusted discussion context and cannot skip this developer's model pass.

## Before unattended review of hostile PRs

Run the model CLIs in an OS-enforced environment whose readable files are limited to the review snapshot, required runtime files, and narrowly scoped authentication. Restrict network egress and GitHub credentials separately from the models. Test an outside-snapshot canary through each actual CLI launcher, including wrappers, and fail closed if it is readable. Keep publication in the parent runner after it validates findings against the pinned diff and rechecks the PR head. These controls need a portable implementation and live tests before this workflow can claim to safely review adversarial PRs from a normal developer workstation.
