# Reviewer-job security

The PR author controls code, descriptions, comments, and some linked material that the review models read. Treat all of it as untrusted data. The asset to protect is the machine running `review-pr`: its files, credentials, configured CLI sessions, network access, and GitHub review authority. An OWASP check of the contributor's code answers a different question.

The [agent-owasp-compliance skill](https://github.com/github/awesome-copilot/blob/main/skills/agent-owasp-compliance/SKILL.md) is a useful prompt for examining tool use, privilege, trust, and audit trails. Its keyword scan is not a runtime defense. Use the [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) for the actual risk names and definitions. The referenced skill's short labels do not all match that source.

## Review boundary

The controller captures complete Git trees without running project hooks or code. Review models browse those pinned files through BStack's bundled browser. It can list, search, read, and compare source, including unchanged callers. It rejects outside paths, symlinks, and unsupported operations. A repository string cannot become a shell command or URL fetch through this interface. Requests run automatically without developer approval.

The CLIs launch with general machine tools and unrelated integrations disabled at the model interface. BStack supplies its baseline, review principles, and writing policy through allowlisted `read_policy` paths. Project PR policy and source are explicit review context; they do not configure new tools. Codex may use pure V8 orchestration to call the browser, without host filesystem or network APIs. The browser uses stdio, opens no listening network service, and adds no global MCP configuration. Static review requires no OS worker or extra system packages.

These are application-level restrictions, not an OS sandbox. The model CLI still authenticates and contacts its provider. The installed CLI, wrapper command, BStack runtime, and administrator-managed policy are trusted local components. A modified CLI, a wrapper that drops restrictions, or policy that adds capabilities can invalidate the boundary. `doctor --live` checks a snapshot read and denied traversal through the configured launch; that alone cannot certify that a malicious wrapper exposes no other tools. Optional OS isolation may add protection. A script that merely forwards arguments does not.

## Safety preflight and publication

A tool-free preflight checks the pinned diff, PR description, and discussion before either independent reviewer runs. Every scanner match needs an explicit clear or hold decision. Legitimate quoted attack fixtures, explanatory security feedback, and unrelated open PRs do not automatically stop normal work. Missing dispositions fail closed. Direct reviewer instructions, agent-rule overrides, and changed opaque executables can pause review. The runner verifies reported locations against the diff; an unverified location produces a generic hold rather than a fabricated link.

A hold saves a partial result and prepares only a runner-written comment pointing a person to the affected locations. It never quotes the suspicious instruction into that comment. If preflight itself fails, reviewers do not proceed. A pass is evidence from one check, not a certification that the PR is safe or permission to execute it. Injection can evade a judge or distort a model's conclusion. The restricted browser limits available actions even when the model follows a malicious instruction; it does not establish immunity.

The target is checked against the selected project's origin or explicit target configuration before `gh` contacts it. `--project` determines that boundary, even when BStack is installed elsewhere. The controller keeps GitHub publication authority; the review models receive no GitHub tool. The publisher validates findings, escapes model prose, creates evidence links itself, and rechecks freshness. Public receipts contain reproducible hashes, not signatures or proof that another checkout's models ran. Other developers' reviews remain discussion evidence.

## Executing PR code

Running the app, tests, or verification skill is a separate optional capability. Its fixed command comes from trusted local configuration and runs against a disposable copy of the pinned head. Its separate runtime worker must deny access to host files and credentials, block network egress, and enforce CPU, memory, and process limits. A model worker is not automatically suitable for this job. Do not let PR content choose commands or destinations, and do not retry failed execution on the host.

Without a runtime worker, the result is a static review using source and existing CI evidence. Do not imply that the reviewer exercised the application.

## Maintainer checks

Run `doctor --live` through the actual configured launchers. Use these provider-backed evaluations from an installed package to check code navigation and synthetic escape attempts:

```sh
python3 -B engineering/review-pr/scripts/browsing_eval.py --project /path/to/project --cli codex claude --case cross-file
python3 -B engineering/review-pr/scripts/browsing_eval.py --project /path/to/project --cli codex claude --case escape
```

The first requires search, a read of an unchanged caller, and a grounded breakage finding. The second checks denied reads outside the snapshot, absence of a fake canary from the report, and no contact with a synthetic collector. Results and browser traces are saved under the project's private `.bstack/review-evals/`. These checks exercise selected CLI versions and models; they do not prove that every attack or future tool change is covered. Maintainer tests also check the tool inventory sent by Codex and browser path validation.

Exercise the live preflight judge separately with `python3 -B engineering/review-pr/scripts/security_eval.py --project /path/to/project`. Its fixtures include normal code and docs, source/discussion injections, and secret-egress attempts. This is a regression check of one configured model, not a measure of general attack-detection accuracy. End-to-end coverage also includes a held PR posting one sanitized comment and a hostile runtime command running only in a disposable sandbox.

The controller caps inputs and model-call volume and uses a local per-PR lock. A callback service must still authenticate GitHub webhook requests, restrict event types and target repositories, and deduplicate delivery IDs. BStack supplies neither a public webhook endpoint nor cross-machine rate limiting.
