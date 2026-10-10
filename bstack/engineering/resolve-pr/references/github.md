# GitHub feedback helper

The first adapter uses Python 3.11+, Git, and an authenticated `gh` CLI. Resolve `scripts/feedback.py` from the installed skill's real path. It never changes code, pushes a branch, resolves a thread, dismisses a review, requests reviewers, or merges a PR.

Capture feedback before assessing it. Save the snapshot and your response data under the project's ignored `.bstack/` directory:

```sh
python3 /absolute/resolve-pr/scripts/feedback.py snapshot --pr https://github.com/owner/repo/pull/123 --out /project/.bstack/resolve-pr/123/snapshot.json
```

The snapshot records the PR's base and head commits, public discussion, and available checks. Inspect the diff and the linked code in the target checkout. Confirm the local branch before editing; the helper does not check out or push it.

Write `responses.json` only after judging concerns and, for a claimed fix, pushing the verified change. Omit items that need no public reply. Each reply names a source kind (`inline`, `review`, or `comment`) and its numeric GitHub ID:

```json
{
  "version": 1,
  "snapshot_id": "SNAPSHOT_ID_FROM_CAPTURE",
  "head": "CURRENT_PR_HEAD_SHA",
  "replies": [
    {"kind": "inline", "id": 123, "body": "Fixed the failing path in commit abc123; the request now retains its original error."},
    {"kind": "review", "id": 456, "body": "I checked this against the accepted ADR. The proposed change would reintroduce the rejected behavior, so I'm keeping the current approach."}
  ]
}
```

Use the **new** snapshot head after pushing. Preview, inspect, then write when the task authorizes public replies:

```sh
python3 /absolute/resolve-pr/scripts/feedback.py respond --snapshot /project/.bstack/resolve-pr/123/snapshot.json --responses /project/.bstack/resolve-pr/123/responses.json --project /project
python3 /absolute/resolve-pr/scripts/feedback.py respond --snapshot /project/.bstack/resolve-pr/123/snapshot.json --responses /project/.bstack/resolve-pr/123/responses.json --project /project --write
```

Inline replies stay in their thread. Replies to review bodies and timeline comments become one linked timeline comment because GitHub has no nested reply there. The helper checks the PR, discussion, and checks again before each write. A changed PR or new feedback stops publication; capture a new snapshot and reassess only affected concerns. Each posted body has a stable marker, so retry the same response file after an uncertain error rather than manually reposting. If the response text changes, preview it again. The helper does not adjudicate feedback, prove a claimed fix, or clear an existing request-changes review.
