# Upstream and bstack layers

Upstream updates must preserve bstack-owned policies and skill replacements. The ownership and manual adoption procedure live in [UPSTREAM.md](../../../../UPSTREAM.md).

Run these from the repository root:

```bash
python3 bstack/scripts/layers.py check
python3 bstack/scripts/audit_pstack.py
python3 bstack/scripts/test_layers.py
python3 bstack/scripts/layers.py review-update --source pstack --candidate /path/to/cursor-plugins
python3 bstack/scripts/layers.py review-update --source matt-pocock-sdlc --candidate /path/to/matt-pocock-skills
python3 bstack/scripts/layers.py review-update --source matt-pocock-handoff --candidate /path/to/matt-pocock-skills
```

The current-tree checks verify pinned bytes and modes, missing/unrecorded imports, active layer entrypoints, and reviewed upstream base hashes. The fixture tests exercise local drift, candidate changes and removals, affected overrides, stale review bases, and read-only behavior. Compare an unchanged pinned source checkout as a real-file control when available.

For selected Matt Pocock sources, candidate discovery is limited by each manifest's `review_paths`. Check that a new file in a selected skill is reported, while an unrelated upstream skill is excluded. Both imports must compare unchanged against their exact pinned checkout, including the root license. This is source verification; the imported SDLC workflows and handoff have not been activated or behaviorally verified across hosts.

Candidate review lists textual changes and affected recorded bases. It never applies an update. A successful comparison can report `review_required`; inspect that status instead of treating exit zero as compatibility approval. After an actual source upgrade, review semantic changes and run affected CLI policy and continuity probes. This check does not establish complete dependency coverage or automatically merge new upstream behavior into replacement skills.
