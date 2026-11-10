---
name: maintain-verification-skill
description: Audit a project verification skill against source and live user behavior, then repair only proven drift. Use for an explicit verifier or feature-map maintenance pass.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# Maintain a verification skill

Use this for a requested full audit of a project's verifier. For a normal feature or bug fix, follow the [project verification policy](../../shared/references/verification-policy.md) and update or run only the affected recipe.

## Find the verifier

Look first under `.agents/skills/verify-*/` for a skill with Launch, Doctor, Drive, Evidence, Cleanup, and a `features/` index. Also check existing project skill locations so a verifier created before BStack is not ignored. If several match, ask which one to audit. If none match, use `create-verification-skill` when creating one is in scope.

The shared location for a new BStack verifier is `.agents/skills/verify-<app>/`. For an existing verifier elsewhere, keep its files in place until the user requests a move. Do not make a second copy that can drift. To bind a shared verifier to the hosts selected for this repo, use the binder in the installed `create-verification-skill/scripts/` directory. Preview before `--apply`; stop on a collision. A new agent session may be needed to discover changed links.

## Audit

1. Read the feature index and every listed feature file. Fix dead, duplicate, missing, or inaccurate entries only when source or live behavior proves the change.
2. Check each feature against source. Parallel read-only agents can divide independent features; every feature needs a source result. Reconcile overlaps into as few live app states as practical.
3. Follow the verifier's launch and doctor steps, then exercise every mapped feature through its user-facing entry point. Save the action and result. If a path is unreachable, name the attempted route and its unmet prerequisite; do not mark it passed.
4. When a drive fails, check the instance again and reset to known state before retrying. Keep earlier proof. Clean up processes and test data after the final drive.
5. Classify each result: stale map, broken driver, product defect, or missing prerequisite. Repair only the verifier's skill, map, and owned helper scripts. A product defect belongs in a separate implementation task.

Report one outcome: `clean`, `changed`, or `blocked`, with the features covered and evidence location. If changes were made, rerun the corrected path. Use `to-pr` when PR delivery is requested or already authorized; this maintenance pass does not create a PR by default.
