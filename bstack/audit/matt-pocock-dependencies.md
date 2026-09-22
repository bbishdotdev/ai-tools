# Matt Pocock dependency import

This extends the [initial SDLC and handoff import](matt-pocock-import.md) with `research`, `prototype`, and `setup-matt-pocock-skills` at the same upstream commit, `c55ee46073ed923f86ce59a5eb3b6d895095d1b7`.

The [shared dependency sources](../upstream/README.md) contain 14 files: the three complete skill directories with reference files and agent metadata, plus Matt Pocock's MIT notice. [Dependency provenance](../matt-pocock-dependencies-provenance.json) records their original paths, hashes, and modes. All 13 selected Matt Pocock skills are now present across the three import boundaries.

## Dependency review

- Wayfinder calls `research` and `prototype` for the corresponding ticket types.
- Wayfinder, to-spec, to-tickets, and triage refer to `setup-matt-pocock-skills` for tracker configuration.
- Setup includes local Markdown, GitHub, and GitLab tracker templates, triage labels, and domain documentation rules.
- These dependencies introduce no further required named skills. The domain template mentions `improve-codebase-architecture` as another consumer of domain modeling, not as an instruction to invoke it.
- Project-supplied Wayfinder notes and handoff suggestions can still name other skills. Host delegation and skill lookup are capabilities to bind, not additional upstream skill imports.

An independent agent confirmed this dependency review and checked all 14 files against the pinned checkout. Bytes, hashes, modes, and selected directory contents match exactly. No findings required changes.

## Verification

`layers.py check` is clean for all four registered sources. `layers.py review-update` reports `unchanged` for all three Matt Pocock imports against the pinned checkout. The PStack audit confirms that its 162 imported files and inventory remain unchanged; its previously recorded unresolved upstream Markdown link remains.

All 21 existing layer tests pass. Release build and integrity checks pass, with the same 153-file consumer release and one public skill. The offline installation verifier reports `pass`, with package integrity and bindings passing for the existing Codex, Claude Code, Cursor, and Grok configuration. Its local report is `.bstack/verification/20260919T015540Z-installation-b15d4b/report.json`; live model probes were disabled.

This adds source dependencies for review. It does not run tracker setup or activate Matt's workflows in the consumer release. The generated release change records the updated layer registry hash; its runtime routing and workflow selection remain unchanged. No new CLI behavior or desktop support is claimed.
