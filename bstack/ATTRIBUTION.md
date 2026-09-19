# Credits and source relationships

bstack is an integration project by Brenden Bishop. Its engineering workflows build on Lauren "poteto" Tan's PStack. Selected SDLC workflows and handoff are imported from Matt Pocock's skills. bstack's packaging, adapters, policy changes, verification tools, and custom workflows have their own history alongside those upstream sources.

## Included upstream work

| Source | Credit | Included in bstack | License notice |
| --- | --- | --- | --- |
| [PStack](https://github.com/cursor/plugins/tree/e31650eea443aaea1e84cc15d88c13f40080b275/pstack) 0.15.2 | Lauren "poteto" Tan | Pinned engineering skills, principles, playbooks, agents, scripts, and supporting files under `engineering/` | [MIT, copyright 2026 Lauren Tan](engineering/LICENSE) |
| [Cursor Team Kit](https://github.com/cursor/plugins/tree/e31650eea443aaea1e84cc15d88c13f40080b275/cursor-team-kit) 1.2.0 | Eric Zakariasson, author named in the upstream manifest; Cursor, copyright holder | PStack's three companion skills: `deslop`, `control-cli`, and `control-ui` | [MIT, copyright 2026 Cursor](engineering/licenses/cursor-team-kit.txt) |
| [Matt Pocock's skills](https://github.com/mattpocock/skills/tree/c55ee46073ed923f86ce59a5eb3b6d895095d1b7) | Matt Pocock | Nine selected SDLC skills under `sdlc/matt-pocock/` and handoff under `shared/matt-pocock/skills/handoff/`; source import only, not yet in the consumer release | [SDLC MIT notice](sdlc/matt-pocock/LICENSE), [handoff MIT notice](shared/matt-pocock/LICENSE), copyright 2026 Matt Pocock |

PStack and Cursor Team Kit come from `cursor/plugins` at commit `e31650eea443aaea1e84cc15d88c13f40080b275`. [pstack-provenance.json](pstack-provenance.json) records the exact source paths, hashes, and file modes. Imported files retain their original content, metadata, and notices.

## bstack adaptations and original work

| Component | Relationship to upstream |
| --- | --- |
| [bstack router](shared/skills/bstack-router/SKILL.md) | Brenden's policy layer over PStack's Poteto Mode, playbooks, and skills. It adds portable capability rules, scoped execution, design thresholds, and evidence reporting. The upstream workflows remain credited to PStack. |
| [Customized unslop](shared/skills/unslop/SKILL.md) | Adaptation of PStack's `unslop`, customized in Brenden's `code-maverick` project before import into bstack. It adds his voice and agent writing preferences. [layers.json](layers.json) records the customization's source commit and original imported hashes. |
| [Verify bstack](shared/skills/verify-bstack/SKILL.md) | bstack-authored verification skill and CLI drivers. Its feature-based verification approach follows PStack's [create-verification-skill](engineering/skills/create-verification-skill/SKILL.md) workflow. This credits the method without attributing bstack's test implementation to PStack's authors. |
| [Router adapters](shared/router/README.md), layer tooling, and integration docs | bstack work that connects the imported workflows to supported hosts and records the package's behavior and source history. |

bstack's own work is covered by the repository's [MIT license, copyright 2026 Brenden Bishop](../LICENSE). The upstream license notices remain with the upstream work and its adaptations.

**bstack** names the collection. **Poteto Mode** retains the upstream identity for the engineering mode. The proposed `/poteto-mode` adapter is part of bstack's integration design; it does not rename the entire collection or imply that Lauren maintains bstack.

## Matt Pocock selection

[Matt Pocock's skills](https://github.com/mattpocock/skills/tree/c55ee46073ed923f86ce59a5eb3b6d895095d1b7) supply `grilling`, `grill-me`, `grill-with-docs`, `domain-modeling`, `wayfinder`, `to-spec`, `to-tickets`, `triage`, `to-questionnaire`, and `handoff`. These are unchanged imports, including their reference files and agent metadata. They are present in the source repository but are not yet selected for the generated consumer release or active routing.

[SDLC provenance](matt-pocock-sdlc-provenance.json) and [handoff provenance](matt-pocock-handoff-provenance.json) pin commit `c55ee46073ed923f86ce59a5eb3b6d895095d1b7` and record original paths, SHA-256 hashes, and modes. [The selection notes](sdlc/README.md) identify deferred dependencies. Future local work tracking and connections to PStack belong in bstack-owned adaptations with their own history and attribution metadata; do not modify the pinned originals.

## Attribution in packaged releases

Include this file, the relevant upstream license notices, and the source records in each bstack release. Preserve author credits and notices when distributing an adapted skill separately. A link back to this repository alone is not the complete attribution bundle.

Use skill frontmatter `metadata` for concise authorship, upstream source, and relationship fields on bstack-owned skills. Keep detailed source pins and changes in the source manifests, [layer registry](layers.json), and Git history. Do not edit pinned vendor files just to add bstack branding.

For each new import or selected upstream improvement, record who created it, its repository and revision, the relevant paths, and what bstack changed. Distinguish an unchanged import, an adaptation, and original work informed by an upstream method. Follow the [selective update procedure](UPSTREAM.md) when adopting changes.
