# bstack credits

bstack is an integration project by Brenden Bishop. Its packaging, adapters, policy layer, verification work, and custom workflow changes are covered by the included [MIT license](LICENSE), copyright 2026 Brenden Bishop.

## Included upstream work

- Lauren "poteto" Tan created [PStack](https://github.com/cursor/plugins/tree/@PSTACK_COMMIT@/pstack), version 0.15.2. The engineering skills, principles, playbooks, agents, and helpers derive from that source. Preserve its [MIT notice](licenses/pstack.txt), copyright 2026 Lauren Tan.
- [Cursor Team Kit](https://github.com/cursor/plugins/tree/@PSTACK_COMMIT@/cursor-team-kit), version 1.2.0, supplies `deslop`, `control-cli`, and `control-ui`. Its manifest names Eric Zakariasson as author. Its [MIT notice](licenses/cursor-team-kit.txt) credits copyright 2026 Cursor.

Both upstream sources are pinned to `@PSTACK_COMMIT@`. These selected source files and bstack's customizations are bundled in the release. Installation never fetches upstream latest. File sources, original hashes, and packaging transformations are recorded in [manifest.json](manifest.json).

## Adaptations

- [bstack's router](content/shared/skills/bstack-router/WORKFLOW.md) layers Brenden's portable capability rules, scoped execution, design thresholds, and evidence reporting over PStack's workflows.
- [Customized unslop](content/shared/skills/unslop/WORKFLOW.md) adapts PStack's skill through [code-maverick](https://github.com/bbishdotdev/code-maverick/tree/d67cc653bee6290bf4261cd56d5b6ad745d8a369/.agents/skills/unslop), adding Brenden's voice and writing preferences. The upstream runtime version is replaced in this package.
- The bstack verification approach follows PStack's [create-verification-skill](content/engineering/skills/create-verification-skill/WORKFLOW.md) method. bstack's verification implementation is its own work.
- Generated dependencies use private `WORKFLOW.md` names, local package paths, and an explicit bstack policy reference. The source checkout remains unchanged. Local setup replaces the upstream host-specific setup workflow.

bstack names the collection. Poteto Mode retains the engineering workflow's upstream identity. These credits identify source relationships and do not imply that upstream authors maintain or endorse bstack.

## Planned work

[Matt Pocock's skills](https://github.com/mattpocock/skills) supply selected SDLC and handoff sources in the bstack development repository. No Matt Pocock skill is included in this release. Their future release integration must carry the pinned revision, authorship, license, and change records.
