# Upstream sources and BStack adaptations

`engineering/` contains exact files from the pinned PStack source and its selected cursor-team-kit companions. [pstack-provenance.json](pstack-provenance.json) records their repository, commit, source paths, hashes, and file modes. Keep local adaptations outside this directory.

BStack adopts upstream changes selectively. A new upstream release does not require a BStack update. Keep the current pin until a reviewed change is worth adopting. [Credits and source relationships](ATTRIBUTION.md) identifies the authors and notices to preserve for both complete updates and selected improvements.

[layers.json](layers.json) maps each adaptation to a source manifest and the upstream file versions used as its review bases. These hashes record the dependency versions the adaptation targets. They do not certify that upstream behavior is safe or that every indirect dependency has been reviewed.

The active [BStack router](shared/skills/bstack-router/SKILL.md) adds portable policy around the unchanged upstream router and playbooks. Its review bases cover that entry, the bundled playbooks, and direct workflow dependencies with their supporting files. The [shared unslop skill](shared/skills/unslop/SKILL.md) replaces the upstream unslop skill when BStack routes writing work. Its code-maverick origin is recorded in the layer manifest. The upstream unslop copy remains available for comparison. Both files from the customized skill were preserved when it moved to `shared/skills/unslop/`; attribution metadata was added afterward. The recorded origin hashes describe that initial import.

The manifest describes the relationship. The active router and host adapters put that relationship into the agent's instruction flow. A file listed as an override does not automatically replace arbitrary explicit reads of its upstream counterpart. Model compliance still needs behavioral verification.

This split preserves the upstream diff and our edits. It does not eliminate maintenance. A policy overlay adds instructions and can conflict with a changed upstream workflow. A whole-skill replacement keeps our version intact, but new upstream improvements must be reviewed and ported deliberately. The current layer makes no claim of lower context cost or deterministic routing.

## Check the current tree

From the repository root:

```bash
python3 BStack/scripts/layers.py check
python3 BStack/scripts/audit_pstack.py
python3 BStack/scripts/test_layers.py
```

The layer check rejects altered, missing, unrecorded, or symlinked imported files, changed permissions, missing active entrypoints, and review bases that disagree with the source lock. Editing an upstream file and leaving the lock unchanged fails. Updating the source lock without reviewing affected layer bases also fails.

## Review a candidate update

Obtain a separate checkout of the upstream repository at the candidate revision, then run:

```bash
python3 BStack/scripts/layers.py review-update --source pstack --candidate /path/to/cursor-plugins
```

Pass the repository root that contains both `pstack/` and `cursor-team-kit/`. The command reads the candidate and current files. It does not fetch, copy, replace, rewrite locks, or accept an update. It first requires a clean current import and valid layers.

The JSON report lists changed and removed imported files, new files under PStack and the selected companion skill directories, and affected layer review bases. Symlinks and unsafe paths within those compared trees are rejected. New files elsewhere in cursor-team-kit are outside the selected import and are not enumerated. A `review_required` report exits successfully because the comparison completed; `invalid` exits with status 1. Review the status and report contents before proceeding.

Record the candidate's Git commit while reviewing it. This file comparison does not authenticate its commit identity or certify a clean checkout. A change outside a layer's listed bases can still affect behavior through an indirect dependency. Review semantics even when there is no textual merge conflict and no directly affected base.

## Adopt selected improvements

Use this path to take a useful upstream change while keeping the rest of BStack's reviewed source pin.

1. Review the candidate change and its dependencies. Decide which behavior to adopt and how it interacts with BStack's policy.
2. Port the selected change into a BStack-owned overlay or whole-skill replacement. Keep the pinned vendor files and their source manifest unchanged. Register a new replacement in `layers.json` when needed and connect it to the active routing policy.
3. Record the upstream repository, exact commit, affected source paths, selected change, and BStack adjustments in the adaptation's reference documentation. Link that record from its skill. Preserve the upstream credit and license notice. Record the same adoption in the Git commit so the code and its lineage can be reviewed together.
4. Run the source and layer checks, then verification for the affected behavior. Unchanged vendor review bases keep their existing hashes; they still identify the source underneath the adaptation.

Do not mix newer files into the vendor snapshot and label the whole snapshot with one newer commit. A selected improvement belongs in the adaptation history unless its source is imported and tracked as a separate, accurately recorded snapshot.

Candidate comparison is implemented. Selecting, porting, recording, and applying improvements are manual steps. The checker validates source integrity and layer references; it does not verify a backport's correctness or completeness.

## Adopt a newer source snapshot

Use this path when a newer baseline is worth adopting. Keep upstream changes and BStack changes in separate local commits on the working branch. No push or PR is part of these commands.

1. Import the approved upstream files and refresh their source manifest manually. Include removals, additions selected for import, file modes, source paths, commit, and version. Put only the upstream update and its lock in that commit.
2. Review the router policy and whole-skill overrides against the changed source. Adapt them as needed, then refresh their reviewed base hashes in `layers.json`. Put those adaptations and reviewed hashes in a second commit. The layer check is expected to fail between these commits when a recorded base changed.
3. Regenerate the source inventory with `python3 BStack/scripts/audit_pstack.py --write`. Run the layer checks and the authorized BStack CLI verification. Keep failures and unsupported behavior visible in the results.

Lock refresh is manual for now. The review command deliberately has no apply mode. Do not fix a failed check by changing hashes without examining the corresponding source and adaptation.

A future Matt Pocock import can add another source-manifest entry and its own overlay records using the same structure. No Pocock source has been imported by this change.

Use non-overlapping vendor directories for separate sources. `engineering/` is currently the PStack-only import boundary. Before mixing another author's engineering files into that category, move the PStack boundary into its own child directory and update its path references in a separate relocation commit. An SDLC import can use its own directory immediately. Do not relax the integrity check to admit unrelated files into an upstream snapshot.
