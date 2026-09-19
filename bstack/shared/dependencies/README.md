# Imported workflow dependencies

These support the selected [Matt Pocock SDLC workflows](../../sdlc/README.md). All three skills are pinned to the same upstream commit, `c55ee46073ed923f86ce59a5eb3b6d895095d1b7`, with their complete supporting files and [MIT notice](matt-pocock/LICENSE).

| Skill | Required by | Included support |
| --- | --- | --- |
| [research](matt-pocock/skills/research/SKILL.md) | Wayfinder research tickets | Primary-source research instructions and agent metadata. |
| [prototype](matt-pocock/skills/prototype/SKILL.md) | Wayfinder prototype tickets | Logic and UI prototype guides, plus agent metadata. |
| [setup-matt-pocock-skills](matt-pocock/skills/setup-matt-pocock-skills/SKILL.md) | Wayfinder, to-spec, to-tickets, and triage | Local Markdown, GitHub, and GitLab tracker templates; triage labels; domain documentation rules; agent metadata. |

`research` and `prototype` remain engineering capabilities in our classification. This directory holds their pinned dependency sources while we compare them with PStack. The existing `engineering/` directory is a strict PStack import boundary; adding unrelated sources there requires a separate relocation. Setup lives with these dependencies because it supplies configuration used across the SDLC selection.

All required, statically named Matt Pocock skill dependencies found in the selected entrypoints and supporting files are present in the source tree. `grilling`, `domain-modeling`, and `triage` were already included. Setup's domain template mentions `improve-codebase-architecture` as another caller of domain modeling; it does not invoke it. User-supplied Wayfinder notes and handoff suggestions can still name additional skills.

This import does not execute setup, configure a tracker, replace PStack workflows, or register new skills with a host. Consumer release assembly, Skill tool bindings, and behavior across CLIs still need review. Tracker templates describe integrations; importing them does not connect an account or validate those APIs.

Keep `matt-pocock/` unchanged. [Dependency provenance](../../matt-pocock-dependencies-provenance.json) records every upstream path, file hash, and mode. Future bstack adapters belong outside this import boundary. Follow [the selective update procedure](../../UPSTREAM.md).
