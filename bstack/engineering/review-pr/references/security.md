# Reviewer-job security

The PR author controls code, descriptions, comments, and some linked material that the review models read. Treat all of it as untrusted data. The asset to protect is the machine running `review-pr`: its files, credentials, configured CLI sessions, network access, and GitHub review authority. An OWASP check of the contributor's code answers a different question.

The [agent-owasp-compliance skill](https://github.com/github/awesome-copilot/blob/main/skills/agent-owasp-compliance/SKILL.md) is a useful prompt for examining tool use, privilege, trust, and audit trails. Its keyword scan is not a runtime defense. Use the [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) for the actual risk names and definitions. The referenced skill's short labels do not all match that source.

## Current boundaries

- The runner pins the PR source and passes it as review data. It does not execute repository tests or hooks. It disables supported CLI customization and MCP paths, constrains Claude's tools, and validates model output before publication.
- A controlled canary test showed Codex's `--sandbox read-only` role could read a file outside the pinned snapshot. Read-only prevents writes; it does not confine reads to the PR. Claude's restricted role denied that particular read, which is useful evidence but not a universal isolation guarantee.
- An untrusted review requires a configured external worker. The runner supplies a reduced environment and checks policy-file, outside-file, and GitHub-credential canaries through that wrapper. The wrapper must enforce file and network boundaries; the runner cannot manufacture those boundaries with a prompt or CLI flag. `--trusted-pr` explicitly bypasses this requirement only for the current code and discussion. A later push or new PR comment needs a new manual grant.
- The runner checks the PR target before contacting it and caps the diff and model-call budget. The publisher escapes model prose as plain text, including reference-style links, images, HTML, and bare URLs. It creates evidence links itself. These controls reduce abuse but do not make model prose a trusted channel.
- Public review receipts contain reproducible hashes, not signatures. They can prevent duplicate publication by the same account, but no longer skip another checkout's model pass or provide its incremental baseline. Other reviews remain discussion context.

## Before unattended review of hostile PRs

Run the model CLIs in an OS-enforced environment whose readable files are limited to the review snapshot, the installed BStack package read-only, required runtime files, and narrowly scoped authentication. If the package is inside the project, expose `.bstack/package` without exposing `.bstack/reviews`. Restrict network egress and GitHub credentials separately from the models. Run `doctor --live` through each actual launcher and wrapper. The canary checks selected files, not every possible secret or route; verify the worker's mounts and network policy independently. Keep publication in the parent runner after it validates findings against the pinned diff and rechecks the PR head. The callback service must authenticate webhook requests, validate the repository and PR target, and deduplicate delivery IDs. Do not automate `--trusted-pr`.
