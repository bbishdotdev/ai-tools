# Reviewer-job security

The PR author controls code, descriptions, comments, and some linked material that the review models read. Treat all of it as untrusted data. The asset to protect is the machine running `review-pr`: its files, credentials, configured CLI sessions, network access, and GitHub review authority. An OWASP check of the contributor's code answers a different question.

The [agent-owasp-compliance skill](https://github.com/github/awesome-copilot/blob/main/skills/agent-owasp-compliance/SKILL.md) is a useful prompt for examining tool use, privilege, trust, and audit trails. Its keyword scan is not a runtime defense. Use the [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) for the actual risk names and definitions. The referenced skill's short labels do not all match that source.

## Review boundary

The controller captures complete Git trees without running project hooks or code. Review models browse those pinned files through BStack's bundled browser. It can list, search, read, and compare source, including unchanged callers. It rejects outside paths, symlinks, and unsupported operations. A repository string cannot become a shell command or URL fetch through this interface. Requests run automatically without developer approval.

The CLIs launch with general machine tools and unrelated integrations disabled at the model interface. BStack supplies its baseline, review principles, and writing policy through allowlisted `read_policy` paths. Project PR policy and source are explicit review context; they do not configure new tools. Codex may use pure V8 orchestration to call the browser, without host filesystem or network APIs. The browser uses stdio, opens no listening network service, and adds no global MCP configuration. Static review requires no OS worker or extra system packages.

These are application-level restrictions, not an OS sandbox. The model CLI still authenticates and contacts its provider. The installed CLI, wrapper command, BStack runtime, Claude user settings, and administrator-managed policy are trusted local inputs. Claude loads user settings so its authentication and provider configuration remain available after a wrapper runs. BStack excludes project settings and separately overrides model tools, unrelated integrations, hooks, memory, custom instructions, the selected agent, and output style. This does not disable every installed plugin; the restrictions apply to what the review session can load and use.

A modified CLI, a wrapper that drops restrictions, or policy that adds capabilities can invalidate the boundary. `doctor --live` checks a snapshot read and denied traversal through the configured launch. It does not inspect the full advertised tool inventory or certify that a wrapper exposes no other tools. Optional OS isolation may add protection. A script that merely forwards arguments does not.

## Safety preflight and publication

A tool-free preflight checks the pinned diff, PR description, and discussion before either independent reviewer runs. The runner supplies the restricted review boundary separately from that untrusted content. The model identifies instructions aimed at changing the review, accessing data outside it, or making the reviewer execute commands or reconfigure tools. Every claim needs a valid location and a bounded explanation of how the text directs this reviewer.

Hooks, package scripts, HTTP calls, and other application behavior are source to inspect. Their presence does not mean the reviewer executes them. Application security defects remain work for the full review. Legitimate attack fixtures, explanatory security feedback, and unrelated open PRs do not automatically stop it. The controller separately enforces the existing checks for direct instructions in agent files to override review rules and changed executable files that cannot be read as text. The model cannot classify an archive as executable; archive integrity and coverage use the [generated ZIP procedure](running.md#generated-zips).

A hold saves the explanations privately and prepares a comment using fixed descriptions of the attempted reviewer action and verified source links. It never publishes model-written reasons or quotes the suspicious instruction. Malformed output, missing explanations, and invalid locations stop as incomplete checks with a local error. They produce no publishable security finding, and reviewers do not proceed.

A pass grants no execution permission and does not certify the PR's safety. Injection can evade a judge or distort a model's conclusion. The restricted browser limits available actions even when the model follows a malicious instruction; it does not establish immunity.

The target is checked against the selected project's origin or explicit target configuration before `gh` contacts it. `--project` determines that boundary, even when BStack is installed elsewhere. The controller keeps GitHub publication authority; the review models receive no GitHub tool. The publisher validates findings, escapes model prose, creates evidence links itself, and rechecks freshness. Public receipts contain reproducible hashes, not signatures or proof that another checkout's models ran. Other developers' reviews remain discussion evidence.

## Executing PR code

Running the app, tests, or verification skill is a separate optional capability. Its fixed command comes from trusted local configuration and runs against a disposable copy of the pinned head. Its separate runtime worker must deny access to host files and credentials, block network egress, and enforce CPU, memory, and process limits. A model worker is not automatically suitable for this job. Do not let PR content choose commands or destinations, and do not retry failed execution on the host.

Without a runtime worker, the result is a static review using source and existing CI evidence. Do not imply that the reviewer exercised the application.

## Maintainer checks

Run `doctor --live` through the actual configured launchers to check an installed package. The fuller evaluations below are maintainer tools in the development repository and are not bundled with consumer releases. Run them from the repository root to check code navigation and synthetic escape attempts through the configured model providers:

```sh
python3 -B bstack/scripts/browsing_eval.py --project /path/to/project --cli codex claude --case cross-file
python3 -B bstack/scripts/browsing_eval.py --project /path/to/project --cli codex claude --case escape
```

The first requires search, a read of an unchanged caller, and a grounded breakage finding. The second checks denied reads outside the snapshot, absence of a fake canary from the report, and no contact with a synthetic collector. Results and browser traces are saved under the project's private `.bstack/review-evals/`. These checks exercise selected CLI versions and models; they do not prove that every attack or future tool change is covered.

Native maintainer fixtures inspect the tool inventory sent by Codex and Claude to a local fake provider. The Claude fixture was verified against Claude Code 2.1.322. It checks the exact advertised tools, authentication from synthetic user settings and an OAuth environment variable, and exclusion of the fixture's user and plugin customizations. These version-specific checks are broader than the browser behavior checked by `doctor --live`; rerun them when changing CLI versions or launch controls. Browser path validation has separate coverage.

Exercise the live preflight judge separately with `python3 -B bstack/scripts/security_eval.py --project /path/to/project`. Its fixtures pair ordinary hooks, scripts, network code, and archives with instructions that try to control the reviewer or expose data. They also cover source and discussion injections, inert attack fixtures, and direct agent-rule overrides. Lifecycle tests separately check the mandatory opaque-executable hold. This is a regression check of one configured model, not a measure of general attack-detection accuracy. End-to-end coverage also includes a held PR posting one sanitized comment and a hostile runtime command running only in a disposable sandbox.

The controller caps inputs and model-call volume and uses a local per-PR lock. A callback service must still authenticate GitHub webhook requests, restrict event types and target repositories, and deduplicate delivery IDs. BStack supplies neither a public webhook endpoint nor cross-machine rate limiting.
