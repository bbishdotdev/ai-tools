# Upstream sources and bstack adaptations

`upstream/pstack/` contains exact files from the pinned PStack source and its selected cursor-team-kit companions. [pstack-provenance.json](pstack-provenance.json) records their repository, commit, source paths, hashes, and file modes. Keep bstack-owned engineering workflows in `engineering/` and local adaptations outside every upstream boundary.

bstack adopts upstream changes selectively. A new upstream release does not require a bstack update. Keep the current pin until a reviewed change is worth adopting. [Credits and source relationships](../ATTRIBUTION.md) identifies the authors and notices to preserve for both complete updates and selected improvements.

[layers.json](layers.json) maps each adaptation to a source manifest and the upstream file versions used as its review bases. These hashes record the dependency versions the adaptation targets. They do not certify that upstream behavior is safe or that every indirect dependency has been reviewed.

The active [bstack router](shared/skills/bstack-router/SKILL.md) adds portable policy around the unchanged upstream router and playbooks. Its review bases cover that entry, the bundled playbooks, and direct workflow dependencies with their supporting files. The [shared unslop skill](shared/skills/unslop/SKILL.md) replaces the upstream unslop skill when bstack routes writing work. Its origin hashes describe the initial code-maverick import. Source relationships are maintained in [root attribution](../ATTRIBUTION.md); individual skills need only a pointer there.

The manifest describes the relationship. The active router and host adapters put that relationship into the agent's instruction flow. A file listed as an override does not automatically replace arbitrary explicit reads of its upstream counterpart. Model compliance still needs behavioral verification.

This split preserves the upstream diff and our edits. It does not eliminate maintenance. A policy overlay adds instructions and can conflict with a changed upstream workflow. A whole-skill replacement keeps our version intact, but new upstream improvements must be reviewed and ported deliberately. The current layer makes no claim of lower context cost or deterministic routing.

## Release assembly and installation

`package/selection.json` selects the reviewed workflows and helpers. `scripts/package.py` builds `release/` entirely from local pinned sources and bstack-owned files. It replaces concrete dependency paths, applies the bstack policy binding, selects customized unslop and setup, and records each file's source hash and transformations in the installed manifest. The generated files are Git-tracked, so a release diff shows exactly what consumers receive. Do not edit them directly.

Run `python3 bstack/scripts/package.py build` after changing owned sources or selecting an upstream update. Then run `python3 bstack/scripts/package.py check` and the installation verification. Build and install do not fetch upstream. Installing from a clone, transferred release, skills.sh, or an internal distributor uses the same reviewed bundle; selecting newer upstream content is a separate maintainer action.

## Check the current tree

From the repository root:

```bash
python3 bstack/scripts/layers.py check
python3 bstack/scripts/audit_pstack.py
python3 bstack/scripts/test_layers.py
```

The layer check rejects altered, missing, unrecorded, or symlinked imported files, changed permissions, missing active entrypoints, and review bases that disagree with the source lock. Editing an upstream file and leaving the lock unchanged fails. Updating the source lock without reviewing affected layer bases also fails.

## Review a candidate update

Obtain a separate checkout of the upstream repository at the candidate revision, then run:

```bash
python3 bstack/scripts/layers.py review-update --source pstack --candidate /path/to/cursor-plugins
```

Pass the repository root that contains both `pstack/` and `cursor-team-kit/`. The command reads the candidate and current files. It does not fetch, copy, replace, rewrite locks, or accept an update. It first requires a clean current import and valid layers.

The JSON report lists changed and removed imported files, new files under PStack and the selected companion skill directories, and affected layer review bases. Symlinks and unsafe paths within those compared trees are rejected. New files elsewhere in cursor-team-kit are outside the selected import and are not enumerated. A `review_required` report exits successfully because the comparison completed; `invalid` exits with status 1. Review the status and report contents before proceeding.

Record the candidate's Git commit while reviewing it. This file comparison does not authenticate its commit identity or certify a clean checkout. A change outside a layer's listed bases can still affect behavior through an indirect dependency. Review semantics even when there is no textual merge conflict and no directly affected base.

## Adopt selected improvements

Use this path to take a useful upstream change while keeping the rest of bstack's reviewed source pin.

1. Review the candidate change and its dependencies. Decide which behavior to adopt and how it interacts with bstack's policy.
2. Port the selected change into a bstack-owned overlay or whole-skill replacement. Keep the pinned vendor files and their source manifest unchanged. Register a new replacement in `layers.json` when needed and connect it to the active routing policy.
3. Record the exact source bases in the layer registry and the selected change in Git. Update the central attribution map when the relationship changes. Keep design notes only when they explain a useful choice. Preserve required notices in central attribution and the original source snapshots; do not add repeated credit blocks to runtime instructions.
4. Run the source and layer checks, then verification for the affected behavior. Unchanged vendor review bases keep their existing hashes; they still identify the source underneath the adaptation.

Do not mix newer files into the vendor snapshot and label the whole snapshot with one newer commit. A selected improvement belongs in the adaptation history unless its source is imported and tracked as a separate, accurately recorded snapshot.

Candidate comparison is implemented. Selecting, porting, recording, and applying improvements are manual steps. The checker validates source integrity and layer references; it does not verify a backport's correctness or completeness.

## Adopt a newer source snapshot

Use this path when a newer baseline is worth adopting. Keep upstream changes and bstack changes in separate local commits on the working branch. No push or PR is part of these commands.

1. Import the approved upstream files and refresh their source manifest manually. Include removals, additions selected for import, file modes, source paths, commit, and version. Put only the upstream update and its lock in that commit.
2. Review the router policy and whole-skill overrides against the changed source. Adapt them as needed, then refresh their reviewed base hashes in `layers.json`. Put those adaptations and reviewed hashes in a second commit. The layer check is expected to fail between these commits when a recorded base changed.
3. Regenerate the source inventory with `python3 bstack/scripts/audit_pstack.py --write`. Run the layer checks and the authorized bstack CLI verification. Keep failures and unsupported behavior visible in the results.

Lock refresh is manual for now. The review command deliberately has no apply mode. Do not fix a failed check by changing hashes without examining the corresponding source and adaptation.

## Selected Matt Pocock imports

The layer registry includes `matt-pocock-sdlc`, `matt-pocock-handoff`, and `matt-pocock-dependencies`, all pinned to `c55ee46073ed923f86ce59a5eb3b6d895095d1b7`. Their manifests record the nine [SDLC skills](sdlc/README.md), shared handoff, and three [support dependencies](upstream/README.md) separately. No bstack adaptation or active release binding is registered for these skills yet.

Their `source_path` is the empty string, meaning the upstream repository root. Every file records its exact original `source_path`; this preserves provenance when bstack groups upstream engineering and productivity skills together. `review_paths` limits discovery of new candidate files to the selected skill directories and accompanying notices/docs. Unselected upstream skills do not become imports or update candidates implicitly. The integrity check still rejects every unrecorded file inside each local import boundary.

Compare a separate Matt Pocock checkout with all three sources:

```bash
python3 bstack/scripts/layers.py review-update --source matt-pocock-sdlc --candidate /path/to/matt-pocock-skills
python3 bstack/scripts/layers.py review-update --source matt-pocock-handoff --candidate /path/to/matt-pocock-skills
python3 bstack/scripts/layers.py review-update --source matt-pocock-dependencies --candidate /path/to/matt-pocock-skills
```

Keep `upstream/matt-pocock/sdlc/`, `upstream/matt-pocock/handoff/`, and `upstream/matt-pocock/dependencies/` unchanged. Put overlays and replacements outside those import boundaries. Register their source bases in `layers.json` and connect them explicitly to routing and release assembly when reviewed. The generated attribution file carries each source's MIT notice with a distribution that includes its material.

Use non-overlapping directories under `upstream/` for separate source snapshots. Their manifests own the destination paths. A relocation changes that destination and its callers, not the pinned file bytes or hashes. Do not relax the integrity check to admit bstack-owned files into an upstream snapshot.
