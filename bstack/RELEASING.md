# Releasing bstack

Each stable version has a GitHub Release with two assets: `bstack-<version>.zip` and `SHA256SUMS`. The ZIP is the complete offline installer. It uses the same pinned package as the skills.sh installer.

## Decide when to release

Commit and merge normal work to `main` as it becomes ready. A push to `main` does not publish a GitHub Release. Publish a version when a coherent set of changes is verified and worth asking users to install. One important bug fix can be a release; several related improvements can ship together. There is no fixed schedule or release per commit.

Changes to skills, routing instructions, templates shipped in the package, and dependencies count as package changes, just like code. README wording and maintainer documentation can land without a new package version. Prepare a new version whenever distributing changed package bytes; never replace an existing release's ZIP or move its tag.

The unpinned skills.sh command reads the committed installer on `main`, so it can expose a prepared package before the tag publishes. Use a [tagged source or release download](INSTALL.md#install-a-published-version) for a fixed published version. Existing installations update only when their installer runs again.

### Choose a version

- Increment the patch version for compatible fixes and small refinements, such as `0.4.2` to `0.4.3`.
- Increment the minor version for new capabilities or substantial workflow changes, such as `0.4.2` to `0.5.0`.
- While bstack is below 1.0, breaking changes require a minor version and explicit migration notes. From 1.0 onward, breaking changes require a major version.

Describe changes to saved data, settings, skill names, or supported tools prominently. A version number alone does not explain what a user needs to do.

## Keep the changelog

Add short, user-visible entries to [CHANGELOG.md](../CHANGELOG.md) under **Unreleased** with the change. Group related entries and link a PR when it adds useful context. Include installation or usage documentation changes when they affect the reader; skip housekeeping and commit-by-commit logs.

At release preparation, turn those entries into `release-notes/<version>.md` using [TEMPLATE.md](release-notes/TEMPLATE.md). Lead with the benefit, remove empty sections and placeholders, and include upgrade actions and actual verification. That versioned file is the single source for the GitHub Release description. The changelog links to it instead of duplicating the full notes.

Keep published notes tied to what shipped. Record later work under **Unreleased**. Release notes are authored and reviewed; the workflow checks that the file exists, but does not summarize commits or validate its claims.

## Prepare a version

1. Start a release-preparation branch from current `main`, choose its scope, and update `version` in [package/selection.json](package/selection.json).
2. Create `release-notes/<version>.md` from the template. Review it against the actual changes since the previous tag.
3. Add the version, release date, and notes link to the changelog. Remove only the Unreleased entries included in this release.
4. Rebuild the committed package and run the checks below from the repository root. Run any additional checks required by the changed workflows.

This stages a release in Git for review. It does not create or publish a GitHub Release. Use the chosen version in the output path; `0.4.3` below is an example.

```sh
python3 -B bstack/scripts/package.py build
python3 -B bstack/scripts/layers.py check
python3 -B bstack/scripts/package.py check
python3 -B bstack/scripts/test_layers.py
python3 -B bstack/package/test_runtime.py
python3 -B bstack/package/test_transport.py
python3 -B bstack/scripts/test_package.py
python3 -B -m unittest discover -s bstack/shared/tests
python3 -B bstack/scripts/package.py dist --output .bstack/dist/0.4.3
```

Check the ZIP against `SHA256SUMS` from the output folder with `sha256sum --check SHA256SUMS` on Linux or `shasum -a 256 --check SHA256SUMS` on macOS. Extract it outside the checkout and install into a disposable project. Confirm `doctor` succeeds and any existing host and automatic-routing preferences survive an upgrade.

Use the version being released in the output path. `dist` can be rerun for identical inputs, but refuses to replace different bytes in an existing archive or checksum file. Each version gets its own folder under the ignored `.bstack/dist/`. Run `package.py check` first to catch a stale committed package.

## Publish

After review and verification, commit and merge the source, generated package, and release notes into `main`. Tag that exact commit with `v<version>` and push the tag when ready to publish. For example, after preparing 0.4.3:

```sh
git tag -a v0.4.3 -m "bstack 0.4.3"
git push origin v0.4.3
```

The [release workflow](../.github/workflows/release.yml) checks the tag against the package version, requires release notes, and runs package checks and tests on Python 3.11. It creates a draft, uploads both assets, and publishes only after both uploads succeed. It doesn't replace an existing release or its assets.

The draft is a temporary upload step, not a second approval checkpoint. Pushing the tag starts publication automatically. Ordinary commits and `main` pushes do not trigger this workflow.

Check the Actions result and the release's two attached assets before announcing it. GitHub also shows automatic source archives. Link users to `bstack-<version>.zip` for installation.

## Publish without Actions

Use a clean checkout of the pushed release tag. Run the same checks and `dist` command above. Confirm the tag is exactly `v` plus the version in `package/selection.json`, then publish those two files with the GitHub CLI:

```sh
gh release create v0.4.3 \
  .bstack/dist/0.4.3/bstack-0.4.3.zip .bstack/dist/0.4.3/SHA256SUMS \
  --verify-tag --draft --title "bstack 0.4.3" \
  --notes-file bstack/release-notes/0.4.3.md
gh release edit v0.4.3 --draft=false
```

Replace 0.4.3 with the version being released. If an upload fails, leave the draft unpublished and inspect it before retrying. A rerun won't overwrite that draft. Resolve an incomplete draft deliberately; don't replace a published ZIP under the same version. Ship a new version for corrections.
