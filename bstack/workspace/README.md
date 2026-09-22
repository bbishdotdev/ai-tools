# Local planning and work

Use Wayfinder to work through planning questions in Focus or inspect their connections in Atlas. Use Kanban to organize implementation tickets. Maps, accepted answers, specs, tickets, dependencies, labels, and waits live in one SQLite workspace shared by the browser and agent CLI.

The app has no AI chat or required external tracker. Agents use its local operations; the browser provides another way to inspect and edit the same work.

## Run the app

From an installed consumer project:

```sh
python3 .bstack/package/workspace/cli.py --project . init
python3 .bstack/package/workspace/cli.py --project . serve --port 4174
```

From an ai-tools checkout, initialize the repository you want to plan work for:

```sh
python3 bstack/workspace/cli.py --project /path/to/your/project init
python3 bstack/workspace/cli.py --project /path/to/your/project serve --port 4174
```

Open the URL printed by `serve`. Stop it with Ctrl+C. Starting it again opens the same workspace. The workspace starts empty; create a map with its destination and scope, then add questions and their connections.

Python 3.11 or newer on POSIX is the runtime target. This build was tested on Linux with Python 3.14.7. Windows and the minimum Python version have not been verified. Compiled browser assets are included, so running the app does not require Node, npm, an account, or a package registry. Node and the locked frontend dependencies are needed only when changing browser source.

The server listens on `127.0.0.1`. It serves the compiled app and its local operations, not arbitrary repository files. This server is for local use; it is not an externally hosted service.

## Use the same work from an agent

Use `request` to pass operation data to the bundled caller. It builds envelopes, derives revisions and claim credentials from saved receipts, and saves the exact request before executing a mutation. `replay` retries that saved request without duplicating an uncertain write. Both print the core's JSON response and exit nonzero for rejected operations.

The example below uses the source checkout. In an installed project, use `.bstack/package/workspace/cli.py` instead. [Workspace access](../shared/references/workspace.md) connects the bundled skills to these operations. The [shared request guide](../shared/references/workspace-requests.md) covers input files, claims, approval, and retry commands.

```sh
python3 bstack/workspace/cli.py --project /path/to/your/project request workspace.read
python3 bstack/workspace/cli.py request --help
```

A successful response has `ok`, `changeSeq`, and `value`. A failure has `ok: false` and an error code/message. A conflict requires inspection and a new reconciled request. The helper does not fetch unseen revisions or claim another actor's work. `call` remains available for integrations supplying a complete JSON envelope on stdin or through `--file`.

Use `workspace.read`, `map.read`, `question.search`, `spec.read`, and `board.read` to retrieve the current slice. Mutations cover planning, spec approval, tickets, typed relationships, transitions, waits, and claims. Read current records before updating them. [OPERATIONS.md](OPERATIONS.md) lists the exact request and response shapes.

Agent edits to existing questions, specs, and tickets require their live claim token and fence. A maintenance claim does not make blocked work ready. Actor and decision-authority fields record local assertions. They do not authenticate a person or replace the calling agent's approval rules.

## From planning to implementation

A spec can use accepted answers from a settled part of a map. Approval saves an immutable version of its body and the exact accepted answers it used. Tickets link to that approved version, carry acceptance criteria, and can depend on other tickets across the workspace. Small, clear work can start as a standalone ticket without a map or spec.

Tickets move through Backlog, Ready, In progress, Review, and Done. Blockers, waits, ownership, and changed planning inputs appear separately from the column. Forward moves check those conditions in the core. Done requires a completion note and can include evidence references; storing a note does not prove that its claimed checks ran.

Changing an accepted decision or spec flags affected work for source review and invalidates old agent claims. A completed ticket keeps its Done column and evidence, but stops satisfying dependents until it is explicitly reopened and reconciled. File references such as ADRs and prototypes are links; their contents are not automatically watched for changes.

## Keep work across sessions

Planning and tickets have [independent adapter settings](../shared/references/work-adapters.md). Both default to local. This release implements local operations only; configured Jira, GitHub, Linear or other external destinations are reported as unsupported. Their provider implementations can be added separately without making either workflow depend on the other provider.

The private store is under the selected project's `.bstack/workspace/`, outside the installed package and installer configuration. Git worktrees follow a binding in their common Git directory to that shared store. Separate clones have separate workspaces. Missing or mismatched bindings fail instead of silently creating a second backlog.

Committed answers retain their history. Changing a prerequisite can require affected work to be reviewed. Parent/child and related links organize work; only blocking links determine readiness. Ready next excludes active claims and explicit waits. An empty ready list does not mean planning is complete.

The browser preserves local drafts separately from saved records. A conflict keeps the draft visible for deliberate reconciliation. Saved work persists in SQLite; browser draft storage is not a substitute for saving an answer. The app refreshes externally saved changes while keeping an open draft intact.

## Upgrade the workspace

Stop old app servers and agent writers before starting an updated runtime. Schema 2 adds specs and tickets without rewriting existing map, question, answer, history, or replay records. It creates a SQLite backup before migrating and upgrades within one database transaction. Discovery never replaces a missing or corrupt store with an empty one.

The `schemaVersion: 1` field in workspace metadata identifies the binding format. The database schema version is stored separately in SQLite's `PRAGMA user_version`. A version-1 server already running in memory cannot enforce the new ticket source rules; restart it after upgrading.

## Rebuild and verify

These maintainer commands require the source checkout. The consumer bundle contains compiled assets and runtime Python, not the frontend source or tests.

```sh
cd bstack/workspace/web
npm ci
npm run build
```

The build writes the offline app to `../assets/` and includes its dependency notices. `npm ci` needs a package registry or a populated cache.

From the repository root:

```sh
python3 -m unittest discover -s bstack/workspace/tests -v
node bstack/workspace/web/test/recovery.test.mjs
```

The suite uses temporary workspaces. HTTP checks bind a local test port. Tests cover persistence, graph rules, revision conflicts, request replay, claims, and the HTTP boundary. Browser interaction checks are recorded separately in ignored `.bstack/work/wayfinder-implementation/` evidence during development.

Original app code uses the repository's MIT license. The compiled browser dependencies retain their notices in `assets/THIRD_PARTY_NOTICES.txt` and `assets/app.js.LEGAL.txt`.
