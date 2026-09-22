# Attribution

bstack is Brenden Bishop's collection of workflows, tools, and agent integrations. Thanks to Lauren "poteto" Tan and Matt Pocock for their skills and engineering ideas, and to the Cursor Team Kit contributors for the companion tools included here.

bstack's original contributions use the [root MIT license](LICENSE). The notices below apply to the identified third-party material. They do not attribute the whole project to its upstream contributors or imply their endorsement.

## Source map

| Material | Relationship | Source and scope |
| --- | --- | --- |
| [PStack snapshot](https://github.com/cursor/plugins/blob/e31650eea443aaea1e84cc15d88c13f40080b275/pstack/README.md) | Imported unchanged | Lauren "poteto" Tan's PStack 0.15.2. Its skills, playbooks, agents, and support files are pinned with exact paths and hashes in PStack provenance (`bstack/pstack-provenance.json`, source repository only). The release includes the subset selected by package selection (`bstack/package/selection.json`, source repository only), with packaging transformations recorded in its installed manifest. |
| Cursor Team Kit companions | Imported unchanged | `deslop`, `control-cli`, and `control-ui`, included with the PStack snapshot. The upstream manifest names Eric Zakariasson as author; its license names Cursor as copyright holder. The same provenance file records these files. |
| Matt Pocock snapshots (`bstack/upstream/README.md`, source repository only) | Imported unchanged; source repository only | Nine SDLC skills, `handoff`, and the supporting `research`, `prototype`, and `setup-matt-pocock-skills` sources. Exact files are mapped in the SDLC (`bstack/matt-pocock-sdlc-provenance.json`, source repository only), handoff (`bstack/matt-pocock-handoff-provenance.json`, source repository only), and dependency (`bstack/matt-pocock-dependencies-provenance.json`, source repository only) manifests. The release uses bstack-owned adaptations; the pinned originals remain here for review. |
| [bstack router](shared/router/WORKFLOW.md) and [unslop](shared/unslop/SKILL.md) | Adapted | bstack's policy over PStack and a customized writing skill, respectively. Their reviewed source bases and the unslop customization's code-maverick origin are tracked in [layers.json](layers.json). |
| SDLC adapters (`bstack/sdlc/README.md`, source repository only), [handoff](shared/handoff/SKILL.md), and [research](engineering/research/SKILL.md) | Adapted | Owned workflows based on the selected Matt Pocock sources, with local workspace operations, decision authority, and portable handoffs. Exact review bases are recorded in the layer registry. |
| [Prototype workflow](engineering/prototype/WORKFLOW.md) | bstack-authored workflow incorporating upstream guidance | Combines selected PStack and Matt Pocock prototype guidance with bstack's lifecycle and product decisions. The active entry calls this shared lifecycle. Its design notes (`bstack/engineering/prototype/REVIEW.md`, source repository only) describe the composition. Both source notices are retained for the incorporated material. |
| [PR workflow](engineering/to-pr/SKILL.md) | bstack-authored workflow incorporating PStack guidance | Retains relevant PStack opening-PR and writing guidance. The visual/evidence approach also draws inspiration from [Matt Pocock's experimental PR skill](https://github.com/mattpocock/skills/blob/main/skills/in-progress/pr/SKILL.md), which credits Dex Horthy's Humanlayer `show-me`. That experimental skill is not copied or bundled. |
| Packaging, adapters, verification code, and original integration work | bstack-authored | PStack's `create-verification-skill` informed the verification method. That acknowledgment does not attribute bstack's implementation to PStack. |

PStack and Cursor Team Kit are pinned to [cursor/plugins at e31650e](https://github.com/cursor/plugins/tree/e31650eea443aaea1e84cc15d88c13f40080b275). Matt's sources are pinned to [mattpocock/skills at c55ee46](https://github.com/mattpocock/skills/tree/c55ee46073ed923f86ce59a5eb3b6d895095d1b7). The provenance files are the complete file map; this table describes their relationships without duplicating that inventory.

The prototype's source guidance is PStack's `skills/poteto-mode/playbooks/prototype.md` and its foundational-thinking, redesign-from-first-principles, and guard-the-context-window principles, plus Matt's `skills/engineering/prototype/SKILL.md`, `UI.md`, and `LOGIC.md` at those revisions.

## Distribution

This is the canonical attribution file. The release builder includes a copy with links adjusted for the installed bundle. Required notices travel with each distribution containing the corresponding material. Original notices inside frozen upstream snapshots remain intact for source integrity; individual bstack skills do not need duplicate acknowledgments or full license blocks.

Keep relationships accurate as workflows change. An independently written workflow can acknowledge ideas as inspiration. Copied or adapted material retains its applicable notices. Detailed update history belongs in provenance, layer records, and Git rather than runtime instructions.

## Third-party notices

The following notices cover the material identified above. Some sources are present only in the development repository, as marked in the source map.

### PStack

MIT License

Copyright (c) 2026 Lauren Tan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### Cursor Team Kit

MIT License

Copyright (c) 2026 Cursor

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### Matt Pocock skills

MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
