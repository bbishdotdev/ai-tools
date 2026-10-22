---
name: create-verification-skill
description: Build a project verifier for a substantial new product feature when no verifier exists, following the project's verification setting. The verifier drives real user behavior and records evidence.
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
disable-model-invocation: false
---

# Create a verification skill

Build one `verify-<app>` skill for the current Git repository. It teaches the next agent how to start the app, drive a real user path, and tell whether it worked. Put its source in `.agents/skills/verify-<app>/`. Do not put the only copy under `.cursor/`, `.claude/`, or another host directory.

Read the [project verification policy](../../shared/references/verification-policy.md) first. Follow its `off`, `ask`, or `auto` setting before creating a verifier as part of other work. A direct request to create one can proceed. A throwaway prototype or exploration does not need one.

## 1. Find the real user path

Read the repo's run commands and existing tests or control scripts. Identify the primary user surface: UI, CLI, API, mobile app, or library. Use the existing harness if it can drive that surface. If it cannot, make the smallest local driver that can. Do not add a browser or test framework dependency just for this skill when a working tool is already available.

Record what the driver needs: runtime, startup command, environment variables, test account or fixture, port or data directory, and the command that proves the app is ready. Explain each missing prerequisite in plain language before trying to run it. Never invent credentials or treat an unavailable external service as a passing check.

## 2. Write the shared skill

Create `.agents/skills/verify-<app>/SKILL.md` with valid `name` and `description` frontmatter. Use these short sections with commands and expected results from this repo, not placeholders:

- **Launch:** start an isolated instance; say how to stop only what this run started.
- **Doctor:** a read-only check of the instance, build, data location, and access needed for the drive.
- **Drive:** exact user actions or requests, using stable UI labels, CLI prompts, or public endpoints.
- **Evidence:** capture both the action and its visible result. Check persisted or external effects from a second view when relevant. Name a private, disposable artifact location.
- **Cleanup:** remove test state and stop the run's instance while retaining the proof artifacts.

If a helper script is needed, save it beside this skill and show its exact command in the skill. Do not ask an agent to rewrite the helper from prose each time.

Create `features/README.md` as the feature index. During ordinary feature work, start with the changed feature's user path and only the nearby smoke path needed to prove it. A full product feature map is a separate audit. Give each mapped feature a short file with `Sub-features`, `How to get to it (user POV)`, `Driving it with <harness>`, and `Gotchas`. Every path listed as verified needs an observed result; a different entry point cannot stand in for it.

## 3. Bind the hosts

The `.agents/skills/` directory is the common source. Codex reads it directly. Claude Code, Cursor, and Grok need links from their project skill directories unless those directories already resolve to `.agents/skills/`. Run the bundled binder from this skill's `scripts/` directory, resolving its absolute path first:

```sh
python3 <absolute-skill-directory>/scripts/bind.py --project <project-root> --name verify-<app>
python3 <absolute-skill-directory>/scripts/bind.py --project <project-root> --name verify-<app> --apply
```

The first command previews the links for hosts selected in `.bstack/config.json`. The second creates only missing links. A conflicting path stops the entire operation without replacing anything. If BStack is not installed in this repo, tell the user that binding cannot infer its hosts; leave the shared skill intact and give the exact missing step. After links change, start a fresh agent session. A Claude desktop Code chat may retain its old skill list until then.

## 4. Prove the verifier

Follow the generated skill once: launch, doctor, drive one mapped feature, save evidence, and clean up. Check that the evidence survives cleanup and that no test process or data was left behind. If the app cannot run, report the precise blocker and leave the generated skill marked as unverified. Do not claim a draft skill works.

Point the user to `maintain-verification-skill` when they want a full feature-map audit. During ordinary implementation, follow the project verification setting and update or run only the affected feature recipe.
