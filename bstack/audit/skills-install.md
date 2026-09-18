# skills.sh installation probe

The current source tree is not ready to ship as an integrated bstack installation through `skills.sh`. Skill file installation succeeds for all four CLI targets, but the installed router has missing dependencies. This probe establishes the packaging work needed before agent behavior tests can pass in a fresh consumer project.

## What ran

On 2026-09-18, `skills@1.7.0` installed a local snapshot of commit `e299ba16e16f5e4d454f084139f7a2163a932092` into two temporary projects. The snapshot matched the committed files. Both runs targeted Codex, Claude Code, Cursor, and Grok, used project scope and the default symlink method, and disabled telemetry.

The first run selected every discovered skill under `bstack/`. The second selected only `bstack/shared/skills/`. Each run exited zero. `skills list --agent <agent> --json` and direct file checks confirmed the following results:

| Target | Installed location | Whole source tree | Shared skills only |
| --- | --- | --- | --- |
| Codex | `.agents/skills/` | 55 skills | 3 skills |
| Claude Code | `.claude/skills/`, linked to `.agents/skills/` | 55 skills | 3 skills |
| Cursor | `.agents/skills/` | 55 skills | 3 skills |
| Grok | `.grok/skills/`, linked to `.agents/skills/` | 55 skills | 3 skills |

These are installer targets and readable files. No agent model session, native plugin installation, desktop test, remote Git install, or global install ran in this probe. The supported target directories come from the tested CLI; the native agents' actual discovery remains a later check.

## Observed packaging gaps

- Both installs copied the bstack router, including its capability reference. Its relative path to the upstream Poteto Mode router no longer resolved. The whole-tree install placed that skill elsewhere rather than preserving the source layout.
- The whole-tree install selected PStack's upstream `unslop` by name. Its hash matched the vendor copy, not bstack's customized replacement. Installing only shared skills selected the correct replacement but omitted its engineering dependencies.
- The whole-tree install included all three dormant Benny skills. Source discovery does not express bstack's intended release selection.
- Neither install included the package's license files or central attribution file. The adapted skills' attribution paths did not resolve.
- Neither install created bstack's standing instructions or host hook configuration. Automatic mode remains a separate, opt-in setup requirement for the eventual release.

The [skills CLI documentation](https://github.com/vercel-labs/skills#plugin-manifest-discovery) describes discovering skills declared by plugin manifests. Its [installer implementation](https://github.com/vercel-labs/skills/blob/v1.7.0/src/installer.ts) copies each selected skill directory. Recognizing a plugin manifest during skill discovery is not proof that a complete native plugin, hooks, agents, and files outside those skill directories were installed.

## Next packaging step

Define a consumer package layout that includes the router's dependencies, the intended skill replacements, and their license notices. Expose only the supported entrypoints. Keep upstream source pins and bstack's adaptations separate in the development tree, then assemble the release from those sources.

Test that release through `skills.sh` in a fresh project before building more workflows. First require correct file selection and working dependency paths. Then run the existing CLI routing and continuity probes against the installed package, without access to this development checkout. Test manual invocation before opting into automatic routing, including on, off, and status behavior once those controls exist.

A native plugin may also need host-specific manifests and setup. For example, [OpenAI's plugin packaging documentation](https://developers.openai.com/plugins/build/plugins) describes bundled hooks and their trust requirements. That installation path requires its own verification; this skill-copy probe does not establish it.

## Evidence and reproduction

[The recorded results](skills-install-results.json) include commands, source revision, installed target counts, hash comparisons, and missing-file checks. Raw command output is retained locally in `.bstack/verification/skills-install-20260918/`. The initial attempt to combine `--list` with `--json` was rejected by the CLI; discovery was rerun without `--json`. Large JSON output was captured to regular files to avoid truncated pipe output observed in the first whole-tree run.

The temporary source snapshot and consumer projects were removed after evidence capture. Paths in the recorded results describe those test locations.

Use [the installation verification procedure](../shared/skills/verify-bstack/features/installation.md) to repeat this probe. No consumer-ready install command is advertised yet.
