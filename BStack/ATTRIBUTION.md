# Credits and source relationships

BStack is an integration project by Brenden Bishop. Its engineering workflows build on Lauren "poteto" Tan's PStack. Selected SDLC workflows from Matt Pocock's skills are planned. BStack's packaging, adapters, policy changes, verification tools, and custom workflows have their own history alongside those upstream sources.

## Included upstream work

| Source | Credit | Included in BStack | License notice |
| --- | --- | --- | --- |
| [PStack](https://github.com/cursor/plugins/tree/e31650eea443aaea1e84cc15d88c13f40080b275/pstack) 0.15.2 | Lauren "poteto" Tan | Pinned engineering skills, principles, playbooks, agents, scripts, and supporting files under `engineering/` | [MIT, copyright 2026 Lauren Tan](engineering/LICENSE) |
| [Cursor Team Kit](https://github.com/cursor/plugins/tree/e31650eea443aaea1e84cc15d88c13f40080b275/cursor-team-kit) 1.2.0 | Eric Zakariasson, author named in the upstream manifest; Cursor, copyright holder | PStack's three companion skills: `deslop`, `control-cli`, and `control-ui` | [MIT, copyright 2026 Cursor](engineering/licenses/cursor-team-kit.txt) |

Both imports come from `cursor/plugins` at commit `e31650eea443aaea1e84cc15d88c13f40080b275`. [pstack-provenance.json](pstack-provenance.json) records the exact source paths, hashes, and file modes. Imported files retain their original content, metadata, and notices.

## BStack adaptations and original work

| Component | Relationship to upstream |
| --- | --- |
| [BStack router](shared/skills/bstack-router/SKILL.md) | Brenden's policy layer over PStack's Poteto Mode, playbooks, and skills. It adds portable capability rules, scoped execution, design thresholds, and evidence reporting. The upstream workflows remain credited to PStack. |
| [Customized unslop](shared/skills/unslop/SKILL.md) | Adaptation of PStack's `unslop`, customized in Brenden's `code-maverick` project before import into BStack. It adds his voice and agent writing preferences. [layers.json](layers.json) records the customization's source commit and original imported hashes. |
| [Verify BStack](shared/skills/verify-bstack/SKILL.md) | BStack-authored verification skill and CLI drivers. Its feature-based verification approach follows PStack's [create-verification-skill](engineering/skills/create-verification-skill/SKILL.md) workflow. This credits the method without attributing BStack's test implementation to PStack's authors. |
| [Router adapters](shared/router/README.md), layer tooling, and integration docs | BStack work that connects the imported workflows to supported hosts and records the package's behavior and source history. |

BStack's own work is covered by the repository's [MIT license, copyright 2026 Brenden Bishop](../LICENSE). The upstream license notices remain with the upstream work and its adaptations.

**BStack** names the collection. **Poteto Mode** retains the upstream identity for the engineering mode. The proposed `/poteto-mode` adapter is part of BStack's integration design; it does not rename the entire collection or imply that Lauren maintains BStack.

## Planned Matt Pocock integration

[Matt Pocock's skills](https://github.com/mattpocock/skills) are the intended source for selected SDLC workflows. Selection and import are still pending. No Matt Pocock skill is bundled in BStack today.

At import, record the selected revision and paths, copy that revision's license and notices, and credit Matt in the package docs and any adapted skill metadata. Keep his original files separate from BStack's changes. Review local work tracking and connections to PStack as adaptations with their own history.

## Attribution in packaged releases

Include this file, the relevant upstream license notices, and the source records in each BStack release. Preserve author credits and notices when distributing an adapted skill separately. A link back to this repository alone is not the complete attribution bundle.

Use skill frontmatter `metadata` for concise authorship, upstream source, and relationship fields on BStack-owned skills. Keep detailed source pins and changes in the source manifests, [layer registry](layers.json), and Git history. Do not edit pinned vendor files just to add BStack branding.

For each new import or selected upstream improvement, record who created it, its repository and revision, the relevant paths, and what BStack changed. Distinguish an unchanged import, an adaptation, and original work informed by an upstream method. Follow the [selective update procedure](UPSTREAM.md) when adopting changes.
