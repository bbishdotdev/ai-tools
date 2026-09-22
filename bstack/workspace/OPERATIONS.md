# Wayfinder operations

Development contract for the shared CLI and browser operations. Run commands from the [workspace README](README.md). The Python core owns validation and persistence.

Skills call the [shared request helper](../shared/references/workspace-requests.md) with operation input data and saved receipts. It builds these envelopes in code. `call` and HTTP still accept the full envelope for lower-level integrations.

## Operation envelope

Queries: `{op,input}`. Mutations: `{op,requestId,actor:{id,kind},input}`. Actor kind is `human` or `agent`. Actor/authority fields are local assertions, not authenticated identities. Successful response: `{ok:true,changeSeq,value}`. Failure: `{ok:false,error:{code,message,currentRev?,current?}}`. Codes include validation, not_found, conflict, cycle, not_ready, claimed, stale_claim, request_reused, workspace_missing.

All writes have a unique requestId. Persist the canonical request hash and result in the transaction. Matching replay returns the same result; altered input with the same ID fails. Updates require expectedRev; relationship mutations use expectedMapRev. Domain entry never trusts UI validation. Bound user text and collection sizes.

## Read shapes

- `workspace.read {}` -> `{workspace:{id,root},maps:[Map]}`.
- `map.read {mapId}` -> `{map:Map,questions:[Question],relationships:[Relationship]}`.
- `question.read {questionId}` -> `{question:Question,answers:[Answer]}`.
- `question.search {mapId?,text?,labels?,state?,owner?,ready?}` -> `{questions:[Question]}`.

`Map = {id,rev,title,destination,scope,unresolved,progress,counts:{total,resolved,ready,blocked,waiting,reviewing},...}`.
`Question = {id,mapId,rev,title,body,method,priority,state,progress,labels:[string],wait:string,claim:null|{owner,expiresAt,fence},answer:null|Answer,status,blockedBy:[id],...}`.
Methods are `grilling`, `research`, `prototype`, `prerequisite-task`.
States are `open`, `resolved`, `needs-review`, `out-of-scope`.
Status display values are `Ready`, `Blocked`, `Waiting`, `In progress`, `Resolved`, `Needs review`, `Out of scope`.
`Relationship = {kind,from,to}` where kind is blocks, parent, related.
`Answer = {id,revision,markdown,authority,references,acceptedAt,prerequisites,...}`.
`authority = {kind:'human',decider,confirmation}` or `{kind:'delegated',decider,scope,grantReference}`.

Question claim tokens are returned only to successful claim operations, not ordinary views. IDs are stable opaque strings. Server-side generated identities never use current array lengths.

## Mutations

- `map.create {title,destination,scope,unresolved?}` -> `{map}`. Scope may be a short explicit string, not an implied grant.
- `map.update {mapId,expectedRev,patch:{title?,destination?,scope?,unresolved?,progress?}}` -> `{map}`.
- `question.create {mapId,title,body?,method,priority?,labels?}` -> `{question}`.
- `question.update {questionId,expectedRev,patch:{title?,body?,method?,priority?,labels?,progress?},claimToken?,fence?}` -> `{question}`.
- `relationship.add/remove {mapId,expectedMapRev,kind,from,to}` -> `{map,relationships}`.
- `question.resolve {questionId,expectedRev,answer:{markdown,authority,references:[]},claimToken?,fence?}` -> `{question}`.
- `question.reopen/exclude/review {questionId,expectedRev,claimToken?,fence?}` -> `{question}`.
- `wait.set {questionId,expectedRev,reason,claimToken?,fence?}` and `wait.clear {questionId,expectedRev,claimToken?,fence?}` -> `{question}`.
- `claim.acquire {questionId,expectedRev}` -> `{question,claimToken,fence,expiresAt}`; `claim.renew/release {questionId,claimToken,fence}` -> `{question,...}`.

Agent updates to existing question content/lifecycle/waits require their current live claim; create/graph planning operations require revisions but don't pretend to claim the whole workspace. Human writes fail if another live claim owns the question. Explicit `claim.takeover {questionId,expectedRev}` by human revokes ownership; UI may explain the conflict before exposing takeover. Never infer takeover from an ordinary save.

Claim eligibility is separate from scheduling readiness. Explicit claim.acquire may acquire an unowned existing question in any lifecycle for maintenance, including review/reopen/wait handling. It does not make blocked or waiting work ready and cannot bypass resolution prerequisites. Automated next-work selection queries Ready questions first. Takeover only revokes the prior claim and advances its fence; it does not grant or fabricate an answer.

Reject self-links, duplicate typed links, missing endpoints, cross-map links, blocking cycles, and parent cycles independently; normalize related endpoints. Every invalidation advances affected question revisions and the map revision, even when the prior state was already needs-review. All question writes, including claims and waits, advance question and map revisions. Every graph write advances map.rev; affected question revisions advance on blocking changes. Map metadata writes advance map.rev. Create operations need requestId but no expectedRev. A review checks expectedRev, which acknowledges the current prerequisite snapshot because every prerequisite change advances dependent revisions.

Every accepted answer records the current prerequisite answer revisions. Changes to a resolved question's title, body, method, or progress require reopening first. Labels and priority remain editable. Accepting an answer or reopening/excluding a question affects transitive blocking dependents; blocking-edge changes affect the edge target and its transitive blocking dependents. All affected in-scope questions advance revisions, clear current answers, and revoke claims atomically. Previously resolved, already-needs-review, previously reviewed, claimed, or nonempty-progress questions become needs-review. Untouched open questions remain open with readiness recomputed, so adding the first prerequisite to a new question does not invent a review ceremony. Reviewing returns a question to open, never silently restores an old answer. Out-of-scope never satisfies a blocker. Wait changes and expired claims never resolve an item. A resolved question must have an accepted answer. Empty readiness never implies map completion.

Waits can be set only on open or needs-review questions. Clear a wait explicitly; it is not an answer. Map completion also requires the unresolved-areas field to be empty.

The HTTP adapter accepts these same envelopes at `POST /api/operation`. The browser obtains a per-server token from `GET /api/bootstrap` and sends `X-Wayfinder-Token` with same-origin JSON requests. The CLI calls the core directly and does not require a running server.

## Specs and Kanban

Questions remain planning records. Specs preserve accepted planning snapshots. Tickets track execution in the workspace-wide Kanban board. A ticket may start without a map or spec when its scope and authority are explicit. Ticket changes never resolve questions or alter a map's question counts.

Queries require no actor:

- `board.read {mapId?,specId?,text?,labels?,state?,owner?,ready?}` returns `{tickets,relationships,counts:{backlog,ready,inProgress,review,done,blocked,needsSourceReview}}`. Counts follow the filters; dependencies are evaluated across the full workspace and relationships remain available outside the filters.
- `ticket.search` accepts the board filters and returns `{tickets}`.
- `ticket.read {ticketId}` returns `{ticket,history}`. Historical records retain prior content and completion evidence; no read exposes claim tokens or hashes.
- `spec.search {mapId?,text?,state?}` returns `{specs}`.
- `spec.read {specId}` returns `{spec,revisions}` with immutable approved snapshots.

A spec has `id,rev,mapId,title,markdown,questionIds,references,state,acceptedRevision,createdAt,updatedAt`. Its read view also has `claim,sourceIssues,usableApproval`. `state` is `draft` or `approved`. Each accepted revision stores `specId,revision,title,markdown,mapId,questionSources,references,authority,acceptedAt`. Each question source is `{questionId,answerId,revision}`. A claim renewal changes `rev` but never an accepted revision.

A ticket has `id,rev,mapId,title,body,acceptanceCriteria,labels,priority,state,progress,wait,references,authority,sources,needsSourceReview,sourceReview,completion,startedAt,createdAt,updatedAt`. `mapId` and authority may be null while drafting. `startedAt` is null until the first transition to In progress and is retained through reopening. Sources are `{spec:null|{specId,revision},questions:[{questionId,answerId,revision}]}`. A source's accepted identity may be null in Backlog. Read views add `claim,blockedBy,sourceIssues,ready,satisfiesDependency`. They omit the private lease and internal fence.

Ticket states are `backlog`, `ready`, `in-progress`, `review`, and `done`. Blocked, waiting, stale sources, and current ownership are separate facts. `ready` is a selection hint for an unclaimed Ready ticket whose content, authority, sources, and dependencies are usable and which has no wait or pending source review. Claim acquisition alone never starts execution.

`sourceIssues` entries contain `{kind,id,reason,expected,current}`. The source identity objects show exactly which accepted answer or spec revision changed. Artifact references are opaque strings. The application neither reads them nor claims that referenced files or test reports are current.

### Spec writes

- `spec.create {mapId?,title,markdown?,questionIds?,references?}` returns `{spec}`.
- `spec.update {specId,expectedRev,patch,claimToken?,fence?}` returns `{spec}`. Patch keys are `title,markdown,mapId,questionIds,references`.
- `spec.approve {specId,expectedRev,questionSources,authority,claimToken?,fence?}` returns `{spec,revision}`.

Approval requires nonempty title and Markdown and the exact current accepted identities for every declared question. It does not require the rest of a map to be settled. With a map association, every declared question must belong to that map. Without one, questions may come from any workspace map. Reapproval appends a new immutable snapshot. Substantive draft edits return the spec to Draft, preserve earlier accepted revisions, and invalidate linked tickets. A source answer change advances affected spec revisions and revokes their claims; metadata and claim renewals alone do not stale an accepted answer.

### Ticket writes

- `ticket.create {mapId?,title,body?,acceptanceCriteria?,labels?,priority?,authority?,references?,specId?,questionIds?}` returns `{ticket}` in Backlog.
- `ticket.update {ticketId,expectedRev,patch,claimToken?,fence?}` returns `{ticket}`. Patch keys are `title,body,acceptanceCriteria,labels,priority,progress,references,authority`.
- `ticket.link {ticketId,expectedRev,specId:null|string,questionIds:[],reason?,claimToken?,fence?}` replaces declared sources and snapshots current accepted identities. In progress or Review requires a reason and a later source review. Done must first reopen.
- `ticket.sources.acknowledge {ticketId,expectedRev,sources,note,authority,claimToken?,fence?}` records review against exact current accepted identities. The source set must match the existing links and every source must be usable. All blocking predecessors must satisfy their dependencies. Acknowledgement clears only `needsSourceReview`; it keeps the execution column and wait.
- `ticket.transition {ticketId,expectedRev,to,reason?,completion?,claimToken?,fence?}` returns `{ticket}`.
- `ticket.wait.set {ticketId,expectedRev,reason,claimToken?,fence?}` and `ticket.wait.clear {ticketId,expectedRev,claimToken?,fence?}` return `{ticket}`.
- `ticket.relationship.add/remove {kind,from,to,expectedFromRev,expectedToRev}` returns `{from,to,relationships}`. Endpoints are tickets anywhere in this workspace. Blocks and parent graphs independently reject cycles; related endpoints are normalized.

Legal moves are Backlog to Ready; Ready to Backlog or In progress; In progress to Backlog or Review; Review to In progress or Done; Done to Backlog. Review to In progress and Done to Backlog require a nonempty reason. Forward moves require body, acceptance criteria, authority, current sources, satisfied prerequisites, no wait, and no pending source review. Done additionally requires `completion:{markdown,references}` with nonempty Markdown. The recorded completion also stores the actor and time. This is a local evidence record, not proof that a referenced test ran.

Substantive content changes in Ready return the ticket to Backlog. In progress or Review must explicitly return to Backlog before changing title, body, criteria, or authority. Progress, labels, priority, and evidence references remain editable during execution. Done permits only label and priority changes until reopened. Reopening clears current completion after its earlier value has been retained in immutable history. It retains progress and the fact that execution previously started.

A Done ticket satisfies a dependency only when it has completion evidence, current sources, no pending source review, and all its own prerequisites satisfy their dependencies. Evaluate the full graph, including hidden cards. Source changes, blocking edge changes, and reopening Done prerequisites advance affected ticket revisions and revoke claims atomically. Direct planning-source changes mark every directly affected ticket for review. Dependency changes require review for previously started work, nonempty progress, completion evidence, or prior source review. Untouched Backlog/Ready tickets retain their column and use computed blockers. Invalidation keeps content, progress, waits, completion evidence, and columns intact, even for Done work. Repeated changes always advance revisions and fences.

### Ticket and spec claims

`ticket.claim.acquire/takeover {ticketId,expectedRev}` and `spec.claim.acquire/takeover {specId,expectedRev}` use the existing 900-second claim rules. Acquire returns `{ticket|spec,claimToken,fence,expiresAt}`. Renew/release replace `expectedRev` with `claimToken,fence`; renewal returns `{ticket|spec,fence,expiresAt}` and release/takeover return `{ticket|spec}`. Takeover is human-only and revokes ownership without acquiring a replacement claim.

Agents need their live claim to edit existing tickets or specs, approve, acknowledge sources, change waits, or transition. Creation and relationship planning remain revision-checked planning operations. Maintenance claims can be acquired for blocked or stale records. Moving to Review or Done releases the implementation claim, and the next phase acquires its own. A source or dependency change between acquisition and transition makes the old revision and credentials unusable.

Titles are bounded to 300 characters. Ticket body, acceptance criteria, and progress are bounded to 30,000; spec Markdown and completion Markdown to 50,000. References contain at most 100 nonempty strings of at most 4,000 characters. Question-source lists contain at most 100 unique IDs. The workspace limits are 500 specs, 5,000 tickets, and 50,000 combined question and ticket relationships. Existing label, priority, authority, request size, and replay rules apply.

## Database schema 2 migration

Stop all schema-1 servers and CLI writers before upgrading, then restart them with the current CLI. A legacy process cannot invalidate source links introduced by schema 2. The new core checks `PRAGMA user_version` inside every operation transaction, including replay reads.

Discovery verifies both bindings, database identity, required tables, and SQLite integrity. Under the existing Git-common or standalone initialization lock, it backs up schema 1 with SQLite's connection backup API to `.bstack/workspace/wayfinder.schema-v1.sqlite3`. This includes committed WAL contents. Backup failure stops the upgrade before any schema write.

The migration creates specs, spec revisions, tickets, relationships, and indexes and sets `PRAGMA user_version=2` in one explicit transaction. Failure rolls back the complete upgrade. Discovery can retry before commit or reopen after commit. Repeated startup and concurrent worktree startup reuse the same upgraded store and backup. Missing, corrupt, or future-version stores are rejected rather than recreated.

Binding metadata still uses format 1. The legacy `schemaVersion:1` field in `metadata.json` and Git-common `bstack-wayfinder.json` identifies the binding format, not the SQLite schema. Migration preserves both files byte for byte and leaves all earlier domain rows, history, request results, revisions, and `changeSeq` unchanged. New workspaces also use binding format 1 and SQLite schema 2.
