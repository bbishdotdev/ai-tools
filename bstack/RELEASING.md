# Releasing bstack

Each stable version has a GitHub Release with two assets: `bstack-<version>.zip` and `SHA256SUMS`. The ZIP is the complete offline installer. It uses the same pinned package as the skills.sh installer.

## Prepare a version

1. Update `version` in [package/selection.json](package/selection.json).
2. Add `release-notes/<version>.md` with the changes users will notice, install instructions, and any relevant limits.
3. Rebuild the committed package and run the checks below from the repository root.

```sh
python3 -B bstack/scripts/package.py build
python3 -B bstack/scripts/layers.py check
python3 -B bstack/scripts/package.py check
python3 -B bstack/scripts/test_layers.py
python3 -B bstack/package/test_runtime.py
python3 -B bstack/package/test_transport.py
python3 -B bstack/scripts/test_package.py
python3 -B bstack/scripts/package.py dist --output .bstack/dist/0.4.2
```

Check the ZIP against `SHA256SUMS` from the output folder with `sha256sum --check SHA256SUMS` on Linux or `shasum -a 256 --check SHA256SUMS` on macOS. Extract it outside the checkout and install into a disposable project. Confirm `doctor` succeeds and any existing host and automatic-routing preferences survive an upgrade.

Use the version being released in the output path. `dist` can be rerun for identical inputs, but refuses to replace different bytes in an existing archive or checksum file. Each version gets its own folder under the ignored `.bstack/dist/`. Run `package.py check` first to catch a stale committed package.

## Publish

Commit and push the reviewed source, generated package, and release notes. Tag that exact commit with `v<version>` and push the tag. For example, after preparing 0.4.2:

```sh
git tag -a v0.4.2 -m "bstack 0.4.2"
git push origin v0.4.2
```

The [release workflow](../.github/workflows/release.yml) checks the tag against the package version, requires release notes, and runs package checks and tests on Python 3.11. It creates a draft, uploads both assets, and publishes only after both uploads succeed. It doesn't replace an existing release or its assets.

Check the Actions result and the release's two attached assets before announcing it. GitHub also shows automatic source archives. Link users to `bstack-<version>.zip` for installation.

## Publish without Actions

Use a clean checkout of the pushed release tag. Run the same checks and `dist` command above. Confirm the tag is exactly `v` plus the version in `package/selection.json`, then publish those two files with the GitHub CLI:

```sh
gh release create v0.4.2 \
  .bstack/dist/0.4.2/bstack-0.4.2.zip .bstack/dist/0.4.2/SHA256SUMS \
  --verify-tag --draft --title "bstack 0.4.2" \
  --notes-file bstack/release-notes/0.4.2.md
gh release edit v0.4.2 --draft=false
```

Replace 0.4.2 with the version being released. If an upload fails, leave the draft unpublished and inspect it before retrying. A rerun won't overwrite that draft. Resolve an incomplete draft deliberately; don't replace a published ZIP under the same version. Ship a new version for corrections.
