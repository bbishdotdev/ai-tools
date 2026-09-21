# SDLC sources

Nine selected SDLC skills are pinned under `upstream/matt-pocock/sdlc/`. This directory holds bstack's selection and integration work. [Central attribution](../../ATTRIBUTION.md) records the source relationship and notices; [the source map](../upstream/README.md) identifies the frozen inputs.

This is a source import for review. These workflows are not yet selected for `bstack/release/`, registered in the development host skill directories, or connected to the bstack router. Importing their files does not establish portable execution or complete their dependency setup.

[The integration review](integration-review.md) records agreed decision ownership, autonomous-run requirements, the proposed implementation entry, triage's separate role, and the prototype decisions. The [approved prototype workflow](../engineering/prototype/WORKFLOW.md) has [design notes](../engineering/prototype/REVIEW.md) and awaits the shared handoff contract before activation.

[The Wayfinder local-app draft](wayfinder-design.md) proposes the first map-to-decision-to-resume flow, the shared local records, and the agent operations. It is a design for review; no app or active skill integration is implemented by that document.

## Selection

| Skill | Purpose | Upstream category |
| --- | --- | --- |
| [grilling](../upstream/matt-pocock/sdlc/skills/grilling/SKILL.md) | Resolve a plan's open decisions through structured interview rounds. | productivity |
| [grill-me](../upstream/matt-pocock/sdlc/skills/grill-me/SKILL.md) | Manual entry point for grilling. | productivity |
| [grill-with-docs](../upstream/matt-pocock/sdlc/skills/grill-with-docs/SKILL.md) | Combine grilling with domain terminology and ADRs. | engineering |
| [domain-modeling](../upstream/matt-pocock/sdlc/skills/domain-modeling/SKILL.md) | Develop a domain glossary and record consequential decisions. | engineering |
| [wayfinder](../upstream/matt-pocock/sdlc/skills/wayfinder/SKILL.md) | Plan work across sessions using a map of decision tickets. | engineering |
| [to-spec](../upstream/matt-pocock/sdlc/skills/to-spec/SKILL.md) | Synthesize an existing discussion into a specification. | engineering |
| [to-tickets](../upstream/matt-pocock/sdlc/skills/to-tickets/SKILL.md) | Break agreed work into implementation tickets with blocking relationships. | engineering |
| [triage](../upstream/matt-pocock/sdlc/skills/triage/SKILL.md) | Evaluate incoming work and prepare implementation briefs. | engineering |
| [to-questionnaire](../upstream/matt-pocock/sdlc/skills/to-questionnaire/SKILL.md) | Collect information needed from another person. | productivity |

[Handoff](../upstream/matt-pocock/handoff/skills/handoff/SKILL.md) is imported separately under `upstream/matt-pocock/handoff/skills/handoff/` because session continuity spans the collection. The upstream behavior writes a handoff to the OS temporary directory and references existing artifacts; it does not synchronize durable memory.

The required `research`, `prototype`, and `setup-matt-pocock-skills` sources are now included under [upstream dependencies](../upstream/README.md), with their complete supporting files. Comparing the engineering workflows with PStack is a separate step. Matt's `implement`, `tdd`, `code-review`, and `ask-matt` remain excluded because this selection does not require them.

## Dependencies to review before activation

| Consumer | Dependency | Current state |
| --- | --- | --- |
| `grill-me` | `grilling` | Included. |
| `grill-with-docs` | `grilling`, `domain-modeling` | Included. |
| `wayfinder`, `triage` | `grilling`, `domain-modeling` | Included. |
| `wayfinder` research and prototype tickets | `research`, `prototype` | Source directories included under upstream dependencies. No PStack substitution or active routing is configured. |
| `wayfinder`, `to-spec`, `to-tickets`, `triage` | Issue-tracker configuration from `setup-matt-pocock-skills`; applicable triage labels and Wayfinding operations | Setup skill and all tracker, triage-label, and domain templates are included. Setup has not been executed; bstack has not configured these operations. |
| Imported workflows using the Skill tool or subagents | Host skill lookup and delegation | Upstream calls remain intact; portable bstack bindings need review. |
| `wayfinder` notes and `handoff` suggestions | Skills named by the project or current conversation | Resolve when used; these are open-ended references, not bundled dependencies. |

Domain and triage reference files are included with their skills. All required, statically named skill dependencies found in this selection and its supporting files are imported. Paths such as `CONTEXT.md`, `docs/adr/`, `.scratch/`, and `.out-of-scope/` describe consumer artifacts, not missing vendored files. Some supporting prose still assumes GitHub; local-first adaptation remains to be reviewed. No SQLite store or Kanban UI is introduced here.

## Ownership and updates

`upstream/matt-pocock/sdlc/` is an immutable import boundary. Put future bstack adapters or replacements outside it, and register their reviewed source bases in [layers.json](../layers.json). Do not edit imported frontmatter to add bstack branding.

[SDLC provenance](../matt-pocock-sdlc-provenance.json), [handoff provenance](../matt-pocock-handoff-provenance.json), and [dependency provenance](../matt-pocock-dependencies-provenance.json) record each original path, exact commit, SHA-256, and file mode. The SDLC skills are grouped in their snapshot by their role in bstack; their original engineering/productivity paths remain in those manifests. Handoff and the support dependencies have their own import boundaries, so checking them does not treat bstack's other shared skills as upstream files.

Follow [the update procedure](../UPSTREAM.md) to compare a candidate checkout. Review only the selected source trees and notices. Installation does not fetch upstream updates.
