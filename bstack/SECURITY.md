# Package security overview

This overview covers the complete `bstack/` consumer folder produced by release packaging. The same files travel inside the installer archive. The development repository also contains maintainer tests and evaluations that are not part of this package.

`manifest.json` records each packaged file's SHA-256, source path, source hash, and packaging transformations. `ATTRIBUTION.md` records upstream notices. Package checks detect changes against the manifest; they do not establish who published a copy or replace a security review.

## Installation and hooks

The bundled Python installer validates and copies the package into the target project's `.bstack/package/`. Installation itself needs no package download or provider connection. It writes the selected hosts' skill entries and adapters, managed instruction blocks, and ignore rules. It adds a PR template only when the project has none. Existing unrelated settings and project instructions are preserved.

Hooks run local bundled commands through the saved Python interpreter. They provide routing reminders and the PR creation guard; their files and launch paths are part of the installation. `doctor` checks package integrity, owned bindings, and command startup. Native host trust and live model behavior are separate checks.

Optional shared memory requires a separate preview and approval. Activation installs a user runtime and updates supported user-wide host configuration. Ordinary project installation does not enable it.

## Browser files in the package

| Files | Purpose and behavior |
| --- | --- |
| `shared/bstack-guide/assets/overview.html` | Offline guide with an inert JSON catalog and JavaScript for search and navigation. It loads no external scripts. Its external documentation links open when selected. |
| `workspace/assets/index.html`, `app.js`, `style.css` | Local workspace UI. The JavaScript bundle includes React and calls the workspace server's same-origin `/api/bootstrap` and `/api/operation` endpoints. These files are required to use the app. |
| `engineering/show-me-your-work/references/decision-log-template.tsv` | Text template for recording engineering decisions. |

The workspace server starts only when invoked. It binds to `127.0.0.1`, serves bundled assets, and keeps project records in the owning Git project's ignored `.bstack/workspace/`. It checks the request host and origin; changes also require the server's workspace token. The [workspace documentation](workspace/README.md) explains how to start and stop it.

## External tools and services

Model workflows and live checks launch configured model CLIs, which authenticate and contact their providers. PR workflows use authenticated `gh` for GitHub reads and authorized publication. Content supplied to those workflows can therefore leave the machine. The installed CLIs, launch wrappers, authentication settings, and administrator policy are trusted parts of that configuration.

PR review models read a pinned snapshot with their own CLI's read-only tools: Claude Code's file tools, and Codex in its read-only sandbox, where it can run read-only commands and read files your user account can read. BStack starts no MCP server or listening service for review and does not confine those reads itself. Optional execution of project code requires a separately configured runtime worker. Read the [review security boundary](engineering/review-pr/references/security.md) for the restrictions and their limits.

Maintainer model evaluations and policy tests stay in the development repository. The consumer package retains installation verification and the runtime checks used by `doctor`. Their presence does not make the full package network-free: live verification and model workflows still use their configured providers.
