# Reviewer-job security

The PR author controls code, descriptions, comments, and some linked material that the review models read. Treat all of it as untrusted data. The asset to protect is the machine running `review-pr`: its files, credentials, configured CLI sessions, network access, and GitHub review authority. An OWASP check of the contributor's code answers a different question.

The [agent-owasp-compliance skill](https://github.com/github/awesome-copilot/blob/main/skills/agent-owasp-compliance/SKILL.md) is a useful prompt for examining tool use, privilege, trust, and audit trails. Its keyword scan is not a runtime defense. Use the [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) for the actual risk names and definitions. The referenced skill's short labels do not all match that source.

## Review boundary

The controller captures complete Git trees without running project hooks or code, and skips symlinks. It copies those pinned files, the PR context, and BStack's review policy into a private temporary directory and starts each reviewer CLI there. Reviewers list, search, and read source with their own tools, including unchanged callers.

BStack asks each client for its read-only mode and adds nothing on top. Claude roles get `Read`, `Grep`, and `Glob` in `dontAsk` mode with hooks, memory, custom instructions, plugins, and MCP servers off; Claude Code denies reads outside the working directory. Codex roles run with `--sandbox read-only`, user config and project instructions ignored, and web search off. That sandbox blocks writes and network access. It does not stop Codex from running read-only commands, including code from the PR, or from reading any file your user can read.

This is not a sandbox built by BStack. The model CLI still authenticates and contacts its provider. The installed CLI, wrapper command, BStack runtime, Claude user settings, and administrator-managed policy are trusted local inputs. Claude loads user settings so its authentication and provider configuration remain available after a wrapper runs.

What BStack does guard is the target: it reviews only PRs opened against the selected project's origin or an explicitly configured repository. It does not check who wrote the PR, so a PR from a fork counts. A hostile PR can still try to steer a reviewer, for example into quoting a local file in its findings, which the controller would then post. The preflight below is the only check against that, and it can be fooled. Decide which PRs are safe to review on a given machine. For PRs from people you do not trust, use a machine without secrets or configure an isolating `worker`. `doctor --live` checks that each role can log in and read a snapshot file; it does not test any boundary.

## Safety preflight and publication

A tool-free preflight checks the pinned diff, PR description, and discussion before either independent reviewer runs. The runner supplies the restricted review boundary separately from that untrusted content. The model identifies instructions aimed at changing the review, accessing data outside it, or making the reviewer execute commands or reconfigure tools. Every claim needs a valid location and a bounded explanation of how the text directs this reviewer.

Hooks, package scripts, HTTP calls, and other application behavior are source to inspect. Their presence does not mean the reviewer executes them. Application security defects remain work for the full review. Legitimate attack fixtures, explanatory security feedback, and unrelated open PRs do not automatically stop it. The controller separately enforces the existing checks for direct instructions in agent files to override review rules and changed executable files that cannot be read as text. The model cannot classify an archive as executable; archive integrity and coverage use the [generated ZIP procedure](running.md#generated-zips).

A hold saves the explanations privately and prepares a comment using fixed descriptions of the attempted reviewer action and verified source links. It never publishes model-written reasons or quotes the suspicious instruction. Malformed output, missing explanations, and invalid locations stop as incomplete checks with a local error. They produce no publishable security finding, and reviewers do not proceed.

A pass grants no execution permission and does not certify the PR's safety. Injection can evade a judge or distort a model's conclusion.

The target is checked against the selected project's origin or explicit target configuration before `gh` contacts it. `--project` determines that boundary, even when BStack is installed elsewhere. The controller keeps GitHub publication authority; the review models receive no GitHub tool. The publisher validates findings, escapes model prose, creates evidence links itself, and rechecks freshness. Public receipts contain reproducible hashes, not signatures or proof that another checkout's models ran. Other developers' reviews remain discussion evidence.

## Executing PR code

Running the app, tests, or verification skill is a separate optional capability. Its fixed command comes from trusted local configuration and runs against a disposable copy of the pinned head. Its separate runtime worker must deny access to host files and credentials, block network egress, and enforce CPU, memory, and process limits. A model worker is not automatically suitable for this job. Do not let PR content choose commands or destinations, and do not retry failed execution on the host.

Without a runtime worker, the result is a static review using source and existing CI evidence. Do not imply that the reviewer exercised the application.

## Maintainer checks

Run `doctor --live` through the actual configured launchers to check an installed package. The fuller evaluations below are maintainer tools in the development repository and are not bundled with consumer releases. Run this one from the repository root to check that reviewers follow a change into unchanged code through the configured model providers:

```sh
python3 -B bstack/scripts/browsing_eval.py --project /path/to/project --cli codex claude
```

It passes when the reviewer reports the breakage and cites the unchanged caller. Results are saved under the project's private `.bstack/review-evals/`. This exercises the selected CLI versions and models on one synthetic repository; it does not measure review quality in general.

A native maintainer fixture inspects the tools Claude sends to a local fake provider. It was verified against Claude Code 2.1.322 and checks the exact advertised tools, authentication from synthetic user settings and an OAuth environment variable, and exclusion of the fixture's user and plugin customizations. Rerun it when changing CLI versions or launch flags.

Exercise the live preflight judge separately with `python3 -B bstack/scripts/security_eval.py --project /path/to/project`. Its fixtures pair ordinary hooks, scripts, network code, and archives with instructions that try to control the reviewer or expose data. They also cover source and discussion injections, inert attack fixtures, and direct agent-rule overrides. Lifecycle tests separately check the mandatory opaque-executable hold. This is a regression check of one configured model, not a measure of general attack-detection accuracy. End-to-end coverage also includes a held PR posting one sanitized comment and a hostile runtime command running only in a disposable sandbox.

The controller caps inputs and model-call volume and uses a local per-PR lock. A callback service must still authenticate GitHub webhook requests, restrict event types and target repositories, and deduplicate delivery IDs. BStack supplies neither a public webhook endpoint nor cross-machine rate limiting.
