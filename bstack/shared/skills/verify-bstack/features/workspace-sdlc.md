# Local workspace and SDLC

## Contract

The browser and bundled CLI share one workspace for maps, questions, accepted answers, approved specs and implementation tickets. Wayfinder → to-spec → to-tickets is a useful sequence, not a mandatory ceremony. Planning is distinct from execution authority. The owned skills must work after installation without reading the maintainer checkout or raw upstream files.

Wayfinder and ticket providers resolve independently. Each defaults to local. External selections currently fail as unsupported; no provider synchronization or universal model launcher is claimed. Manual planning needs no model configuration. Explicit autonomous grilling needs two configured distinct models and actual execution capability before planning writes.

## Deterministic checks

From the source checkout:

```sh
python3 -m unittest discover -s bstack/workspace/tests -v
node bstack/workspace/web/test/recovery.test.mjs
python3 -m unittest discover -s bstack/shared/tests -v
python3 bstack/scripts/test_package.py
python3 bstack/package/test_runtime.py
```

Workspace tests create disposable Git projects and local HTTP servers. They exercise restart, the schema-1 migration and backup, worktree binding, claims, revision conflicts, replay, typed graph cycles, source invalidation, and cross-interface operations. The browser recovery suite checks unresolved requests and unsaved drafts. Package tests execute the installed CLI and preflight, then check integrity; running them must not create bytecode in the package.

The shared `request`/`replay` caller also has a focused suite: `python3 -m unittest discover -s bstack/workspace/tests -p test_requests.py -v`. It checks receipt-based planning through Done, interrupted-write replay, selection from saved search results, stale revisions, actor/workspace separation, source reconciliation, and malformed input. Agents should invoke this bundled code, supplying domain data and reviewed receipts rather than generating their own request/claim/retry client.

Check that an approved spec retains its exact accepted answer snapshots, tickets retain the approved spec revision, and changed sources revoke stale claims and require review without erasing progress or completion evidence. Filtered-out predecessors still block work. Done requires evidence and current prerequisites; a stale Done ticket cannot satisfy dependents.

## Browser drive

Use one disposable project, initialize with the current bundled CLI, and start its loopback server. Seed two maps, an approved spec, and tickets across all five states, including a cross-map dependency. Health-check the printed URL before driving. Preserve evidence before resetting a failed state.

Create and edit a ticket with Markdown preview, criteria and authority. Move it through the board by select and pointer drag. A blocked move must leave it unchanged with a readable reason. Open its hidden predecessor, resize and expand details, filter and search. Create and approve a spec. Edit the same record from CLI while a browser draft is open; verify deliberate reconciliation preserves the draft. Complete a ticket from CLI while a progress draft is open; hidden fields must not be silently discarded by a metadata save. Restart and check the saved records.

Record screenshots, observed states and console errors. Stop only the test server and close temporary tabs when finished. UI tests are separate from core tests; passing Python does not prove dragging or draft recovery.

## Installed skill forward test

Install into an isolated Git project using the [installation driver](installation.md), or the bundled offline controller. Remove its staging source. Give a fresh agent only the installed package, project and a bounded fixture brief. The agent must execute the requested workflow; do not feed it expected operations or answers beyond the fixture's approved product facts.

1. Human-approved fixture: private offline notes, SQLite, Markdown editing/preview, one user, no sharing. Planning only. Ask for saved accepted planning, one approved spec, two vertical tickets with a dependency, and a durable handoff. Verify the actual database, revisions, authority, criteria and references, no implementation changes, and no model-role setup requirement. Reload through a separate CLI process.
2. Start an autonomous planning-only request in a separate project without role configuration. Verify it reports the missing bindings before any map/question/spec/ticket write. Same-model and malformed bindings are also covered by deterministic preflight tests. Configuration success is not evidence that either model ran.
3. Reopen an accepted source from the first fixture, then give a fresh receiver its handoff. Verify it rereads current state, detects changed inputs and preserves the original authority boundary before attempting execution. It must not use the sender's claim token.
4. Configure Wayfinder local and tickets to an unsupported provider. Wayfinder-only preflight must succeed; ticket/both preflight must fail without writing local replacement tickets. Reverse the selections to exercise independent resolution.

Inspect persisted outcomes and tool evidence, including actual use of the shared request caller and its saved receipts. Distinguish observed file reads from agent-reported skill usage. Native same-model agents can verify these local effects; they do not prove cross-model grilling, every CLI's native discovery, desktop support, or automatic session launch. Retain those as unverified until separately exercised with authorization.
