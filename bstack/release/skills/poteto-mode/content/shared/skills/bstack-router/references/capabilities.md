# Capability contract

Apply this contract transitively to imported instructions and their supporting files. A provider-specific reference or executable remains provider-specific even when the surrounding workflow is portable. Inspect a helper's operations before running it. Use it only when its provider, inputs, permissions, and requested destination match the current environment; otherwise use a supported equivalent or report the unavailable step.

| Workflow needs | Resolve in this environment |
| --- | --- |
| Delegate implementation, exploration, synthesis, or review | Use the host's supported delegation API and permissions. Preserve the role, bounded scope, relevant source pointers, and separation of responsibilities. A named `poteto-agent`, Cursor `Task` field, or Grok Bot is not a portable API. Load bstack's router in delegates. |
| Select models | Use a supported user/project role setting; otherwise `inherit-parent`. Verify availability before selecting a named model. Different-role agents on the same model do not establish cross-model-family review. |
| Inspect a running CLI or UI | Select available terminal, browser, or native control tooling for that surface. Capture actual behavior. A browser substitute does not prove a desktop-only path. |
| Author or verify a skill | Use available skill-authoring tooling and the project's verification driver. Do not depend on Cursor's built-in skill names existing on other hosts. |
| Plan work, create a ticket, track decisions | Use the project's local artifact convention when no external destination is requested. In this repository, private working records go in gitignored `.bstack/work/`. A local file is sufficient for a generic work item; a board or database is not required. |
| Use a named issue tracker, forge, CI system, document store, or messaging service | Resolve the requested destination through its configured adapter. GitHub, Jira, Linear, Slack, and every other external service are optional integrations. If the user explicitly requests an unavailable service, report that gap. A local draft may preserve progress, but does not satisfy or prove delivery to that service. |
| Inspect PR status, CI, reviews, or automated review comments | Use the configured forge/CI/review provider, preserve the upstream review criteria, and distinguish reading status from authorized mutations. Judge automated comments on evidence regardless of bot vendor. Do not run a GitHub-specific helper against another provider. |
| Recover context or audit decisions | Use the current host's available task transcript, tool traces, and local decision artifacts. Do not assume Cursor's transcript directories or cloud URLs. Log entries and agent summaries are claims to check against primary evidence. |
| Run background work or resume a program | Use a supported host lifecycle or an explicitly configured local runner. Never claim an unattended loop, persisted coordinator, or delivery after the process exits unless that mechanism exists and was exercised. |

If no equivalent exists, preserve the step and explain the capability gap. Continue independent authorized work. Where a required independent reviewer or cross-model audit cannot run, report that exact limit; a useful local check can still run but does not satisfy the missing guarantee. Do not install accounts, provision services, or invent credentials as a hidden workflow prerequisite.

Available integration and authorized action are separate facts. Read-only access can establish availability. External messages require the user's applicable authorization. Do not repeat a permission question already answered for the same action, content, and destination. Local fallback never turns an unavailable explicit external delivery into success.
