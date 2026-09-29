# Architecture decisions

ADRs preserve the few fundamental choices whose reasons a future maintainer needs. Most features produce no ADR. Planning questions, implementation notes, research, prototype selections, and routine trade-offs stay in their existing records.

## Decide whether a record earns its place

All three must hold:

- The choice establishes a lasting architectural constraint, ownership boundary, or implementation direction that would be costly to reverse.
- Its reason would be surprising or easy to lose by reading the code alone.
- Real competing approaches or constraints explain why this direction was chosen.

Before proposing a record, finish this sentence with a concrete risk: "Without this reason, a future maintainer could wrongly ..." If that only describes ordinary implementation work, skip the ADR and the capture prompt. Do not invent alternatives or rationale to pass the threshold.

Check existing decisions before creating anything. Reuse the record that already owns the choice. Keep inseparable consequences of one choice together; a new phase, ticket, implementation detail, or application of that choice does not earn another ADR. Split only independent fundamental decisions that could change separately. There is no target count, per-feature quota, or required ADR at a phase boundary.

If one feature appears to need a batch of ADRs, stop drafting and identify the fundamental choice driving those details. Put the implementation breakdown in the spec or tickets. Do not make routine choices sound architectural to justify more records.

When an unrecorded choice qualifies and the decision is confirmed within the authorized task, capture it without asking for the same approval again. Otherwise offer one short proposal at a natural decision checkpoint, naming the decision and why its reason needs preserving. Do not prompt repeatedly after the user declines. An agent may accept a decision only within the user's explicit delegation; automatic routing is not delegation. Follow [decision authority](decision-authority.md).

## Organize by decision

Honor an existing ADR convention, including a single file. Do not migrate it just to match bstack. For a new project, use a flat `docs/adr/` directory, created only for the first accepted decision:

```text
docs/adr/
  0001-local-planning-storage.md
  0002-independent-planning-and-ticket-providers.md
```

Each short file owns one fundamental decision. The stable ID and filename describe the choice, not a feature name, team, sprint, or task. Feature renames usually need only a terminology or link correction inside the existing record. Do not create feature subfolders or copy the same ADR into several areas. Follow existing numbering, never reuse an ID, and never overwrite another writer's record.

Private proposals stay under the owning workspace's `artifacts/adr/` when a durable draft is useful. A conversation can be enough until acceptance; do not create a draft file merely to prove the process ran. Accepted records go into repository Markdown by default. Keep existing authoritative documents in place. See [workspace access](workspace.md) for private paths.

Use [the short ADR format](../../sdlc/domain-modeling/ADR-FORMAT.md). Record the choice, actual reason and important trade-off, status, and real decision authority. Include scope or a revisit condition when it helps applicability. A few paragraphs are usually enough. Omit empty sections, meeting transcripts, research dumps, duplicate code descriptions, and a change-by-change journal.

## Consult and reconcile

Before nontrivial research, design, triage, implementation, or review, inspect the decision catalog and read the few records relevant to the problem. Include applicable decisions spanning the whole application. A filename search alone cannot establish relevance. Read unknown-status records before treating them as accepted. Reuse those bodies while still current in context; do not reload the whole corpus every turn.

Use the bundled [workflow helper](../workflow.py) for the catalog and mechanical checks. Follow the project's documented ADR location; the default scans only `docs/adr/`, not the whole repository. Resolve the helper relative to this file or through the installed `index.json` workflow entry:

```bash
python3 /absolute/package/shared/workflow.py --project /path/to/checkout adr
python3 /absolute/package/shared/workflow.py --project /path/to/checkout adr --path architecture/decisions
python3 /absolute/package/shared/workflow.py --project /path/to/checkout adr --path ADR.md
```

No workspace setup is needed. The catalog reads the active checkout, lists titles, paths, declared status and recognized replacement links, and reports mechanical findings. It creates no index or documents. Read selected bodies with the host's file tools. An empty scan only describes the selected location. Unknown conventions need manual inspection; a declared status or successful scan does not prove approval, relevance, or semantic consistency.

Pass the relevant stable IDs and paths through questions, specs, tickets, delegates, PRs, and handoffs. Link to the authoritative record instead of copying its prose. The receiving phase checks the current record and status before relying on a prior summary. Existing decisions inform the work even when the user never invokes domain modeling.

An already rejected alternative needs no repeat investigation unless there is concrete new evidence: changed requirements, constraints, operating scale, costs, dependencies, or an invalidated assumption. Name that evidence and compare it with the recorded reason. Age alone and an agent's preference are not reasons to reopen a choice. If no condition changed, continue under the current decision without another debate. Honor an explicit user request to reconsider; a comparison alone does not reverse the accepted decision.

Before accepting a new ADR, read potentially overlapping decisions and resolve contradictions explicitly. Do not leave two conflicting decisions accepted for the same scope. If their scopes differ, make that distinction clear. If the prior choice still holds, clarify its wording, scope, or links in place without changing its meaning. Routine clarification needs no successor ADR.

When an authorized decision actually reverses the old choice, write a short successor explaining what changed, link it to the old record, and mark the old one superseded with a reciprocal replacement link. Preserve the old rationale for readers of older work. Retire an obsolete decision when its scope no longer exists; do not invent a replacement. Superseded and retired records are historical context, not current constraints.

Reconcile affected open specs, tickets, and handoffs with the changed decision before continuing dependent work. Do not silently replace their sources or dismiss a change warning. Revisit ADRs when their area changes; no scheduled review ceremony or activity log is required.

The workspace still treats artifact references as links. Editing a linked ADR file does not automatically invalidate its approved specs or tickets. The agent must reread and reconcile those sources; the catalog is a read-only aid, not an approval gate or a background monitor.
