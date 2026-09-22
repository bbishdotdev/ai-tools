# Workspace requests

All local skills use the bundled [CLI](../../workspace/cli.py). Run its `request` command instead of writing a Python client, shell wrapper, request envelope, or claim-handling loop. The [shared implementation](../../workspace/wayfinder/requests.py) builds requests and calls the existing core. No server, registry, or extra dependency is needed.

The agent supplies operation data: titles, Markdown, chosen IDs, relationships, decisions, and real authority. Code supplies request IDs, revision checks, claim credentials, and exact spec source identities. The core validates the operation and saves records. The browser reads that same database.

Use [workspace access](workspace.md) for project discovery and preflight. Read only the relevant fields in [operations](../../workspace/OPERATIONS.md); it remains the authoritative domain contract.

## Invoke an operation

Resolve the CLI relative to this file or the installed `index.json`. Paths below are placeholders for the package and consumer project. Store input files and receipts under the workspace's private artifacts directory, outside the installed package. Create the directory once after workspace initialization.

```bash
BSTACK_CLI='/absolute/package/workspace/cli.py'
BSTACK_PROJECT='/absolute/consumer/project'
BSTACK_REQUESTS='/absolute/workspace/root/.bstack/workspace/artifacts/requests/session-id'
mkdir -p "$BSTACK_REQUESTS"
python3 "$BSTACK_CLI" --project "$BSTACK_PROJECT" request workspace.read
python3 "$BSTACK_CLI" --project "$BSTACK_PROJECT" request map.create \
  --actor session-id --input-file "$BSTACK_REQUESTS/map-input.json" \
  --receipt "$BSTACK_REQUESTS/map-created.json"
```

`map-input.json` contains only the operation's input data:

```json
{
  "title": "Checkout flow",
  "destination": "Choose the checkout experience",
  "scope": "Plan the UI and dependencies"
}
```

Queries need no actor. Omit `--input-file` for an empty input. Use `--receipt` on a query when its result will be the basis for a later write. Every mutation requires a stable session `--actor` and a new `--receipt` path. The helper always records the actor as an agent, even when its input records a human's decision.

Both stdout and the receipt's `result` contain the core's response. Check `ok` and the exit status. Receipts are private files containing the workspace identity, exact request, and result; claim receipts include credentials. They are not handoff documents or proof of sound decisions.

## Edit from reviewed records

Use a successful receipt as `--basis`. The helper copies the target ID and revision from that snapshot. It never fetches a newer revision behind the agent's back. Select an explicit ID in the input when a receipt has multiple records of the same kind.

For a question created or read into `question.json`:

```bash
python3 "$BSTACK_CLI" --project "$BSTACK_PROJECT" request claim.acquire \
  --actor session-id --basis "$BSTACK_REQUESTS/question.json" \
  --receipt "$BSTACK_REQUESTS/question-claimed.json"
python3 "$BSTACK_CLI" --project "$BSTACK_PROJECT" request question.update \
  --actor session-id --basis "$BSTACK_REQUESTS/question-claimed.json" \
  --input-file "$BSTACK_REQUESTS/progress-input.json" \
  --receipt "$BSTACK_REQUESTS/question-updated.json"
```

`progress-input.json` can contain `{"patch":{"progress":"Compared the two storage options."}}`. Subsequent updates can use `question-updated.json` as their basis; credentials travel through successful receipts while the claim remains live. Use the same mechanism for `spec.claim.acquire`, `spec.update`, `ticket.claim.acquire`, and ticket operations.

When a fresh read provides the revision but an earlier receipt holds your claim, pass both `--basis fresh-read.json --claim claim-receipt.json`. The helper checks the workspace, actor, and target match. Expired or revoked claims still fail in the core. Acquire, renew, and release claims explicitly; a claim is not permission to execute or make a product decision. Never share ownership through a handoff.

## Planning, specs, and tickets

| Operation | Data the agent supplies | Receipts the helper needs |
| --- | --- | --- |
| `map.create`, `question.create`, `spec.create`, `ticket.create` | The operation's content and chosen source IDs | New output receipt; no basis |
| `relationship.add/remove` | `kind`, `from`, `to` | Current map as basis |
| `question.resolve` | `answer` with Markdown, actual authority, references | Claimed question as basis |
| `spec.approve` | Actual `authority` | Claimed spec plus a basis receipt for each reviewed accepted question |
| `ticket.relationship.add/remove` | `kind`, `from`, `to` | Both current ticket endpoints as bases |
| `ticket.transition` | `to` plus required reason or completion evidence | Claimed ticket as basis |
| `ticket.sources.acknowledge` | Reconciliation `note` and actual `authority` | Claimed ticket plus reviewed linked spec/questions as bases |
| Other updates and waits | Operation-specific content | Target as basis, claim when required |

Repeat `--basis` for multiple inputs. For spec approval and ticket source acknowledgement, code derives accepted source identities from those receipts. It does not invent approval, resolve missing answers, or substitute current unseen sources. A source change between reading and approval fails the core's checks. The agent must reconcile changed decisions before acknowledging them.

Do not put `expectedRev`, endpoint revisions, `claimToken`, or `fence` in input data. The helper derives those fields. Relationship changes and source invalidation can change multiple revisions, so read affected records again before continuing. Review/Done transitions and question resolution can release claims; acquire new ownership when the next phase requires it.

## Retry and reconcile

The helper saves the exact request before executing it. If execution is interrupted or its result is uncertain, replay that receipt:

```bash
python3 "$BSTACK_CLI" --project "$BSTACK_PROJECT" replay \
  --receipt "$BSTACK_REQUESTS/map-created.json"
```

Replay preserves the original request ID and input. The core deduplicates it, including when the write committed before the response was saved. A new request refuses to overwrite an existing receipt. Never edit receipts or create a new request to retry an uncertain create.

A known conflict, stale claim, or validation error requires inspection and reconciliation, then a new request with a new receipt. Replaying a recorded rejection returns that rejection. The helper does not loop, silently take over, change decision authority, or advance work through extra phases. `call` remains the lower-level exact-envelope interface for integrations that already manage those mechanics.
