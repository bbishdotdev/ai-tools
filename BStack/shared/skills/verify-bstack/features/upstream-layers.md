# Upstream and BStack layers

Upstream updates must preserve BStack-owned policies and skill replacements. The ownership and manual adoption procedure live in [UPSTREAM.md](../../../../UPSTREAM.md).

Run these from the repository root:

```bash
python3 BStack/scripts/layers.py check
python3 BStack/scripts/audit_pstack.py
python3 BStack/scripts/test_layers.py
python3 BStack/scripts/layers.py review-update --source pstack --candidate /path/to/cursor-plugins
```

The current-tree checks verify pinned bytes and modes, missing/unrecorded imports, active layer entrypoints, and reviewed upstream base hashes. The fixture tests exercise local drift, candidate changes and removals, affected overrides, stale review bases, and read-only behavior. Compare an unchanged pinned source checkout as a real-file control when available.

Candidate review lists textual changes and affected recorded bases. It never applies an update. A successful comparison can report `review_required`; inspect that status instead of treating exit zero as compatibility approval. After an actual source upgrade, review semantic changes and run affected CLI policy and continuity probes. This check does not establish complete dependency coverage or automatically merge new upstream behavior into replacement skills.
