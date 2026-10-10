# Run a review

Requires Python 3.11+, Git, authenticated `gh` for the PR's host, and the selected model CLIs on macOS or Linux. The first draft implements Claude Code and Codex runners; its process and file locking require a POSIX host. It can be invoked from another agent host, but Cursor and Grok are not yet review execution adapters. No Wayfinder workspace, tracker, or skills.sh connection is required.

## Roles

Defaults are Opus 5.5 at medium effort, Codex Astra at medium effort, and a fresh Opus 5.5 adjudicator at high effort. Override only the roles you want in the project's private `.bstack/review.json`, or pass `--config /path/to/config.json` to the runner:

```json
{
  "roles": {
    "reviewer_a": {"cli": "claude", "model": "claude-opus-5-5", "effort": "medium"},
    "reviewer_b": {"cli": "codex", "model": "gpt-6-astra", "effort": "medium"},
    "adjudicator": {"cli": "claude", "model": "claude-opus-5-5", "effort": "high"}
  },
  "timeout_seconds": 900
}
```

Two reviewers must use distinct model identities. Prefer different families for independent perspectives. The adjudicator may use either family in a fresh session. Supported effort values are `low`, `medium`, and `high`; the configured model must support the requested value. Model IDs depend on the authenticated deployment. The runner does not substitute another model when one fails.

`doctor` checks configuration, executable availability, versions, and required CLI options. It does not make inference calls or certify model entitlement, authentication, or effective reasoning effort. `run` exposes execution failures as incomplete reviews. Don't interpret an installed binary as a working model.

The roles are separate from autonomous grilling configuration. Changing review roles does not enable automatic routing or grant product/ADR decision authority.

## State and follow-ups

Run from the consumer's project and use its `.bstack/` directory for private review data. Run records include pinned source metadata, diffs, model responses, prior decisions, and publication state. Temporary source trees are removed when the run ends. Records can still contain private source code. Keep `.bstack/` gitignored.

Failed model processes also retain private standard output, standard error and exit status. Authentication errors should name the failed login instead of appearing as an empty CLI failure. Reauthenticate the named client before retrying; the runner never replaces a failed reviewer with another model.

The runner pins the comparison tree, proposed head and current target tip. Reviewers can consult current target ADRs even when they landed after the PR forked. Only complete assessments become incremental baselines. A changed head normally produces a delta review; changed base/history or review policy/configuration can require a full pass. A rebuttal or requirement change without new code produces a context reassessment. Reviewers decide which callers or contracts are affected.

Closed or merged PRs are skipped before models run. Confirmed merge conflicts defer review; unknown mergeability is not a confirmed conflict. Draft status and failing CI alone do not skip an explicitly requested review.

Unchanged assessments are reused, including saved partial assessments so the same missing evidence does not repeatedly spend model calls. Use `run --fresh` to request a new independent pass. Different role models or efforts also require a new pass. Timeout changes alone do not change the assessment.

Published reviews carry a bounded receipt containing their public assessment and compatibility information. Another checkout can reuse a complete matching assessment from the same authenticated user or a reviewer with verified repository write access. Unknown, edited, dismissed or incompatible receipts remain discussion evidence. Receipt checks establish consistency and source identity, not proof that a collaborator actually ran the named models. Shared reuse links their result without posting a new approval. A shared baseline contains public findings, never another developer's private model reports.

Changed CI results or public discussion can require a context refresh. Reactions and timestamps alone do not. Existing reviews remain visible to the models; only an assessment's own verified publication batch is excluded from its freshness comparison. Arbitrary new prose is conservatively reassessed rather than discarded by a keyword filter. Other open PRs are supplied as titles, descriptions and commit identities; titles alone cannot prove duplication.

Reviewers inspect materialized source as data. The runner disables supported host customization paths and restricts model tools; it does not run repository tests or hooks to establish behavior. These controls are not a claim of universal OS isolation or immunity to prompt injection. Explicit model metadata is withheld from the judge; prose may still reveal stylistic clues.

The result schema is defined in [contracts.py](../scripts/contracts.py) and supplied to the model by the runner. Don't recreate the schema, anonymization, or GitHub calls in shell snippets. A valid schema proves structure, not that a finding is correct.

## Generated ZIPs

A generated ZIP can be covered through its reviewed source files when the runner proves that those files reproduce the exact archive. Configure the corresponding repository-relative paths in the private review configuration:

```json
{
  "zip_trees": {
    "dist/package.zip": "dist/package"
  }
}
```

The runner checks each existing base/head version against its own pinned source tree. Supported archives contain sorted regular UTF-8 files, Unix file modes, a fixed 1980 timestamp and deflate compression. It reconstructs bytes from that tree without extracting the supplied archive or executing project code. Exact matches produce source-equivalence evidence for the reviewers; they must still assess the source changes.

Unknown formats and non-text changes are assessed for material relevance. A changed image need not block unrelated code findings. A failed mapped archive verification remains an integrity gap; different compression-library output can prevent an exact match. Valid partial results retain findings and limits, but cannot approve or become the next complete baseline.

## Publication

`run` collects evidence and invokes models without posting. `publish --run ...` previews the actions; `--write` performs them within the user's authorization. Agreement adds a thumbs-up, useful additions and disagreements reply in an existing inline thread, and responses to overall reviews use a short linked timeline comment. New findings appear in a concise review with category icons and the models that performed it.

Only unique new blockers cause a new request-changes event. Agreement with an existing blocker does not mean approval; it leaves the formal state alone. Complete assessments without blockers or unresolved human decisions may approve. Partial assessments can publish supported blockers or a comment explaining their limits. The runner never dismisses someone else's review or resolves their thread automatically.

When GitHub disallows a review event for the acting account, report the supported comment and intended verdict separately. An incomplete result cannot approve. A review is tied to a commit; a later push needs a new review. Required CI and repository merge policy remain separate from the model's judgment. The runner never merges a PR or changes branch protection.

Writes are recorded action by action. After an uncertain response, retry the same run so the runner can reconcile already-posted reactions, replies and reviews. Don't manually post the body again. Fresh discussion can require reassessment before the remaining actions proceed. A final freshness check reduces concurrent duplicates, but there is no cross-machine lock or guarantee of exactly-once model execution or publication.
