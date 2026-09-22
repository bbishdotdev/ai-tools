---
name: wayfinder
description: Chart and resolve a map of dependent planning questions across sessions, using local storage or the configured planning adapter.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# Wayfinder

Find the route to a destination too large or uncertain for one context. Maps organize planning questions; implementation tickets belong to the later execution phase. Read [workspace access](../../shared/references/workspace.md), [independent work adapters](../../shared/references/work-adapters.md), and [decision authority](../../shared/references/decision-authority.md). Resolve the Wayfinder adapter before planning writes. Local works without an external tracker or role configuration for human-guided work.

## Chart the map

Execute local operations through the [shared request helper](../../shared/references/workspace-requests.md). Supply content and decisions as data; let the helper assemble envelopes, revisions, and claim credentials.

1. Name the destination and scope using [grilling](../grilling/SKILL.md) and [domain modeling](../domain-modeling/SKILL.md) as needed. Reuse decisions already made. Planning is the default; only an explicit scoped grant permits execution or autonomous choices.
2. Explore the breadth of unknowns. A precise question can be recorded even when blocked. Keep areas too vague to phrase as questions in the map's `unresolved` field. If the route is already clear and fits one session, skip the map and continue only the authorized next step.
3. Use `map.create` and `question.create` for questions that can be named now. Put the destination and scope in their dedicated fields. Create IDs first, then connect `blocks`, `parent`, or `related` edges with `relationship.add`. Blocking and parent relationships serve different purposes.
4. Keep each question small enough for a fresh context. Start bounded research in parallel where useful and supported. Charting alone does not authorize resolving human decisions; return the map and ready questions. If the user already authorized continuation, follow that scope instead of imposing a new approval stop.

The database owns the map, question bodies, accepted answers, and graph. Use titles in human-facing links and narration; retain stable IDs for operations. Do not duplicate answers in a second map document. Query the overview and zoom into relevant questions on demand.

## Work through the map

Read the current map. If no question was named, query `question.search` with the map and `ready:true`; select a ready question, then acquire its claim before working. Re-read after a claim conflict and choose another eligible question. A maintenance claim on blocked or waiting work does not make it ready.

Dispatch by the question's `method`:

| Method | Work |
| --- | --- |
| `grilling` | Run [grilling](../grilling/SKILL.md) with [domain modeling](../domain-modeling/SKILL.md). Human answers are the default; autonomous exchange requires the configured distinct models and scoped authority. |
| `research` | Use [research](../../engineering/research/SKILL.md). The owning session accepts the findings against the question and records their sources. |
| `prototype` | Use [prototype](../../engineering/prototype/SKILL.md). Preserve the review loop and link the usable selected artifact. A favorite alone is not final acceptance. |
| `prerequisite-task` | Do only the authorized work needed to unblock a decision. Record observed facts. If access or human action is missing, set a specific wait and give the needed action. Never infer permission to provision or publish. |

Resolve with `question.resolve` only when the answer is accepted by its decision owner. Record Markdown, the actual human confirmation or scoped delegated authority, and references. Re-read prerequisites and pass the reviewed question receipt as the basis; the core captures the accepted dependency snapshot. Release unfinished claims when pausing. Never copy a claim into a handoff as ownership for the receiver.

After an answer, create newly precise questions and edges, remove their corresponding fog from `unresolved`, and check invalidated dependents. Preserve history through reopen/review operations. Use `question.exclude` for work outside this destination, recording the scope reason in the question before exclusion; exclusion does not satisfy a blocker. If the destination changes materially, chart a new effort rather than silently reopening a rejected scope.

An empty ready queue can mean blocked, waiting, claimed, or stale work. Report the actual condition. The map is settled only when all in-scope questions are resolved and `unresolved` is empty. Clear waits explicitly; passage of time is not an answer.

## Continue with a clean context

Default to one substantial non-research question per session. A broader authorized run may continue through fresh [handoffs](../../shared/handoff/SKILL.md), carrying authority and current IDs rather than the full conversation. Host support determines whether those sessions can launch automatically. Do not claim an unattended loop without a working runner.

Accepted decisions can feed [to-spec](../to-spec/SKILL.md), then [to-tickets](../to-tickets/SKILL.md). A settled subset may form a spec while other map questions remain open. Planning completion never starts implementation by itself. Newly discovered bug or feature intake may need [triage](../triage/SKILL.md); ordinary ready planning questions do not.
