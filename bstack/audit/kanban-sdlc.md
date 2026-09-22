# Kanban and SDLC integration

September 21, 2026. Local implementation and owned skill activation for bstack 0.3.0. This report covers the source checkout and its offline consumer bundle on Linux. It does not establish native desktop support or external provider execution.

## Delivered behavior

The local workspace now stores approved specs and implementation tickets beside Wayfinder maps and accepted questions. Its browser board has Backlog, Ready, In progress, Review and Done columns, pointer dragging and select-based movement, search/filtering, Markdown editing/preview, ticket dependencies, waits, source review, claims, expanded/resizable details, and retained history. UI and CLI use the same revision-checked operations.

Specs capture immutable approved bodies and exact accepted answer identities. Changed planning sources invalidate stale claims and mark dependent work for review without erasing progress or completion evidence. A Done ticket with stale sources stops satisfying its dependents. Schema 1 is backed up and upgraded transactionally; earlier rows and binding metadata remain unchanged. Legacy writers must be stopped before upgrading.

Thirteen owned entries join the release: nine SDLC skills, shared handoff, and engineering research/prototype/implement. The bundle exposes 42 public skills; only unslop is implicit. Pinned imports remain unchanged. The layer registry records each adaptation's reviewed source bases, including both prototype sources. The approved prototype lifecycle has one owner.

Wayfinder and tickets resolve providers independently, defaulting to local. Unsupported external selections fail before writes for that area; independent local planning can still proceed. This is configuration and an adapter contract, not Jira/GitHub/Linear synchronization. Autonomous grilling preflight requires two distinct model bindings and reports runtime availability as unchecked. Human-guided work requires no role configuration.

## Verification

| Check | Result |
| --- | --- |
| Workspace Python suite | 60 passed; includes migration, HTTP/CLI, restart, claims, conflicts, source invalidation and dependency rules |
| Browser recovery suite | 21 passed; includes preserving unfinished progress after external completion |
| Read-only workflow preflight | 13 passed; independent providers, manual/autonomous roles, worktree identity and no filesystem writes |
| Package assembly | 18 passed; 42 entries, deterministic archive, relative link closure, relocated runtime execution and integrity |
| Consumer runtime | 42 passed; all four host bindings, update/removal preservation and collision handling |
| Source layers | 22 passed; pinned source and reviewed adaptation bases |
| Development discovery | 7 passed; safe idempotent additions, conflicting entry refusal and redirected-path rejection |
| Offline installation driver | Passed for Codex, Claude Code, Cursor and Grok bindings; staged distribution removed before installed checks |

HTTP tests required permission to bind temporary loopback ports. The package includes compiled browser assets and standard-library Python runtime; installation and runtime tests needed no package registry or upstream fetch. Running workspace commands must not create bytecode inside the integrity-checked package.

Browser driving used a disposable two-map fixture. Observed create/edit/preview, spec approval, all ticket columns, completion evidence, valid pointer movement, rejected blocked movement, hidden cross-map blockers, detail expansion/resizing, CLI/browser conflicts, draft reconciliation, and source-review warnings after a planning answer changed. The final console check had no errors. A fresh server/page retained saved fixture records. The user's empty workspace was upgraded separately with a backup, byte-for-byte comparison of earlier table rows, and no fixture data inserted.

Independent backend and UI reviews found source invalidation and draft-loss edge cases; those were corrected and rechecked. The SDLC review found that newly unblocked Backlog successors and resumed tickets needed distinct implementation entry paths. The corrected instructions were exercised against real claim/transition operations. The final packaging review also found a redirected development skill-directory write. The installer now rejects symlinked destination parents before any writes; independent snapshots confirmed both dry-run and apply leave the checkout and external directory unchanged. No open P1/P2 findings remain in these scoped reviews.

## Fresh installed workflow

A fresh native agent received only an isolated installed package and human-approved planning fixture. It saved an accepted question/map, an approved spec, two vertical tickets with a blocking relationship, and a durable handoff. The first ticket was Ready, the successor remained Backlog, no implementation started, and claims were released. A separate process checked stored authority, acceptance criteria, exact sources, dependency edge and immutable spec body. The fixture had no model configuration.

Reopening the accepted question then made both tickets require source review. The earlier approved spec body and answer snapshot stayed intact while its current approval became unusable. Updating the installed bundle preserved those private records and the handoff. A fresh receiver reread the handoff and current records, identified the stale accepted scope, and returned reconciliation as the next step. It changed no records or claims and did not start implementation under planning-only authority.

A separate fresh autonomous fixture reported missing model bindings and stopped. Inspection confirmed no workspace or planning records were created, and no model roles were guessed. Skill reads are agent-reported where native read traces are unavailable; persisted records and operation results are checked separately. These tests do not establish every skill's full live execution on every CLI.

## Evidence and limits

Private evidence is under `.bstack/work/kanban-sdlc/`: test logs in `evidence/`, independent review reports, browser screenshots, before/after stored-record snapshots, fixture handoffs and execution records. The maintainer recipe is [local workspace and SDLC verification](../shared/skills/verify-bstack/features/workspace-sdlc.md).

The four CLI versions were discovered, and their filesystem installation bindings passed. Provider-backed sessions were not rerun for this feature. Cross-model grilling, automatic host session launch, native app/plugin-manager behavior, Windows, and Python 3.11 runtime execution remain unverified. Python 3.14.7 was used here. External provider adapters and shared-memory consumer integration remain separate work.
