# bstack

bstack combines engineering workflows, portable setup controls, and custom policies in one package. Version 0.1.0 includes the router, customized unslop, and selected engineering dependencies. The SDLC integrations and prototype workflow remain in the development repository and are not active in this release.

The exported skill is `poteto-mode`. Invoke it explicitly to load the [bstack router](content/shared/skills/bstack-router/WORKFLOW.md). Internal workflows stay private and are loaded through the [index](content/index.json). The active unslop is [Brenden's customization](content/shared/skills/unslop/WORKFLOW.md).

## Set up a consumer project

A reviewed clone or transferred release directory contains the complete selected instruction corpus and bstack changes. Installation uses those bundled files. It never fetches PStack, replaces them with upstream latest, or needs access to an upstream repository.

For an offline installation, run the bundled controller directly from the reviewed release. This copies the capsule into the consumer project and sets up its bindings using Python's standard library. Node, npm, and skills.sh are not required for this path.

```sh
python3 <reviewed-bstack-release>/skills/poteto-mode/scripts/bstack.py install --project <project-root> --hosts codex claude cursor grok
```

A skills.sh install copies this complete skill directory. It does not execute setup, register native plugins, grant hook trust, or configure project instructions. After installing the skill, use its actual installed path:

```sh
python3 <installed-poteto-mode>/scripts/bstack.py setup --project <project-root> --hosts codex claude cursor grok
python3 <installed-poteto-mode>/scripts/bstack.py doctor --project <project-root>
```

Setup installs the customized writing binding and local control entries. Routing is manual until explicitly enabled. Existing user configuration is preserved. Host trust and reload requirements are reported by the controller and remain subject to that host's controls.

```sh
python3 <installed-poteto-mode>/scripts/bstack.py auto on --project <project-root>
python3 <installed-poteto-mode>/scripts/bstack.py auto status --project <project-root>
python3 <installed-poteto-mode>/scripts/bstack.py auto off --project <project-root>
```

The generated `/bstack-auto` entry performs the same explicit operations. Off stops future automatic routing and preserves manual Poteto Mode and unslop. It cannot remove instructions already present in an active conversation. Start a fresh session when checking the manual default or an opt-out.

Before removing the capsule through skills.sh, remove its project bindings:

```sh
python3 <installed-poteto-mode>/scripts/bstack.py uninstall --project <project-root>
```

## Dependencies and scope

The controller and reminder use Python 3.11 or newer and its standard library. POSIX CLI setup is the current implementation. Optional imported helpers retain their own requirements, such as Bun, Node, or a configured forge CLI. Their package declarations and source are included; those runtimes, accounts, service credentials, and downloaded npm dependencies are not bundled or provisioned. Read the [capability contract](content/shared/skills/bstack-router/references/capabilities.md) before using them. An unavailable external destination remains unavailable.

The Claude and Cursor native manifests outside this capsule identify the plugin as `bstack`; they export the same skill. They do not enable hooks automatically. Their presence and successful skill copying do not establish native plugin installation or desktop behavior. A Codex native manifest is deliberately omitted because its current plugin validator rejects the shared manual-entry flag. Codex CLI installation through the offline controller or skills.sh remains a separate supported packaging path, with explicit invocation configured in `agents/openai.yaml`. The maintainer's live CLI verification is a separate check from `doctor`.

## Source and updates

[Credits and license notices](ATTRIBUTION.md) travel with the capsule. [manifest.json](manifest.json) records installed files, source hashes, and declared build transformations. Its paths are relative to this directory. The manifest excludes its own hash. The [layer summary](content/layers.json) names the active replacements. Source hashes establish integrity against the reviewed development inputs, not the authenticity of an arbitrary download.

This release is built offline from selected, pinned sources. Updates are reviewed and adopted selectively; installing bstack does not follow upstream changes automatically. Generated workflow files preserve the upstream instructions except for recorded packaging transformations and bstack's explicit policy precedence. Rebuild from the maintained source rather than editing generated release files. A local release build is not evidence that the same revision has been published to a remote branch or package registry.
