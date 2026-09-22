# Pull requests

## Contract

The owned `to-pr` entry replaces Opening a PR in the generated package. It produces a short visual explanation from the actual diff and accepted decisions, preserves consumer template requirements, and checks open work immediately before publishing. Duplicate intent, contradictory contracts and demonstrated hard conflicts keep an authorized PR in draft with linked warnings. Shared files alone are not a conflict. Incomplete evidence stays explicit and draft.

The agent owns semantic review. The Python helper owns collection, coverage checks, immutable prepared files, freshness, publication state and media fallback. It uses authenticated `gh` for pushed same-repository branches. Other forges and fork publishing require separate supported tools. This is independent of planning and ticket provider selection.

## Local checks

```sh
python3 -m unittest discover -s bstack/github/tests -v
python3 bstack/scripts/test_package.py
python3 bstack/package/test_runtime.py
python3 bstack/scripts/layers.py check
python3 bstack/scripts/package.py check
```

Exercise paginated open work, missing or truncated patches, missing semantic reviews, conflicting findings, changed branch heads and new open PRs. A stale pre-publication review must not create a PR. Incomplete coverage may create only a draft. Verify dry-run makes no external mutations, uncertain creation is reconciled instead of retried blindly, unrelated same-head PRs are preserved, and partial upload failures leave a usable fallback. New work during publication must keep the PR draft. These fake-transport checks do not establish GitHub behavior.

Package checks must resolve public `to-pr` and internal `opening-a-pr` to the same owned entry, include its template and helper, preserve explicit invocation, and run the helper after removing the installer source. Keep upstream snapshots unchanged.

## Agent review

Give a fresh agent the installed skill and a bounded fixture with open PR bodies/diffs: compatible shared paths, duplicate intent across different files, opposite contract changes, an actual integration conflict, and an unrelated PR. Ask for the review record and prepared briefing without giving expected labels. Inspect supporting evidence and the resulting draft/ready plan separately. A filled JSON record is not proof of a sound review.

## Authorized live publication

Only use an already authorized repository and branch. Scan the final pushed revision, inspect all open work, prepare the body and media with a useful fallback, and inspect the read-only plan. Publish with `--write`. Read the resulting PR through GitHub and verify its base, head, status, notices, body and visual URLs. Retry the same bundle to check it resolves the same PR without duplicates. Attach the PR to the current task.

Record actual upload support and failures. Do not call an illustration a screenshot or a passed test. Do not create a competing PR, request reviewers, comment on another author's work, or merge just to test overlap. Use local fixtures for unsafe or disruptive cases. Keep evidence under gitignored `.bstack/verification/`; report unexercised providers, versions and failure paths.
