# bstack VERSION

[One sentence describing the main benefit of this release. Replace VERSION and all bracketed prompts, and remove unused sections before publishing.]

## Breaking changes

- [Who is affected, what changes, and what they must do before upgrading. Remove this section if there are none.]

## Changes

### Added

- [New capability and what it lets the user do.]

### Changed

- [Changed behavior and why it helps.]

### Fixed

- [The problem users experienced and the corrected behavior.]

## Upgrade

[Required migration, restart, configuration, or other action. If no special steps are needed, say so and link to the installation guide. Describe preservation of existing settings only where verified.]

## Verification

[Name the checks that passed and the tools or platforms actually exercised. Include material known limitations. Link detailed evidence instead of pasting logs.]

## Install

Download **bstack-VERSION.zip** and **SHA256SUMS** from this release. Extract the ZIP and ask your agent to read its `SKILL.md` and install into your project, or run from the extracted folder:

```sh
python3 install.py --project /path/to/my-project
```

Use the same installer to upgrade. Requires Python 3.11+ on macOS or Linux. See [installation](https://github.com/bbishdotdev/ai-tools/blob/vVERSION/bstack/INSTALL.md) for skills.sh and other options.
