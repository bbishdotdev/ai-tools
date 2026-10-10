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

The runner records the reviewed commits and context, keeps the last complete review as the incremental baseline, and gives each role a fresh session. It reuses an unchanged completed review. A changed head normally produces a delta review; changed base/history or review policy/configuration can require a full pass. Changed PR intent, discussion or competing work requires reassessing that context. The reviewing models still determine which unchanged callers or contracts a delta affects.

This draft also invalidates a review when CI status changes during or after it. A retry can refresh context without new code, but still costs another model pass. Other open PRs are supplied as titles, descriptions and commit identities. If that information cannot establish whether work overlaps, the models must report the gap rather than claim a duplicate is proven.

Reviewers inspect materialized source as data. The runner disables supported host customization paths and restricts model tools; it does not run repository tests or hooks to establish behavior. These controls are not a claim of universal OS isolation or immunity to prompt injection. Explicit model metadata is withheld from the judge; prose may still reveal stylistic clues.

The result schema is defined in [contracts.py](../scripts/contracts.py) and supplied to the model by the runner. Don't recreate the schema, anonymization, or GitHub calls in shell snippets. A valid schema proves structure, not that a finding is correct.

## Publication

`run` is local. `publish --run ...` previews the event and body; adding `--write` submits only within the user's existing authorization. The body includes the intended verdict and meaningful findings or resolutions. The runner checks freshness and reconciles repeat publication against the same run before writing again.

When GitHub disallows a review event for the acting account, report the supported comment and intended verdict separately. An incomplete result cannot approve. A review is tied to a commit; a later push needs a new review. Required CI and repository merge policy remain separate from the model's judgment. The runner never merges a PR or changes branch protection.

For an uncertain network result, retain the run and retry through its publication command so it can look for the existing review. Don't manually post the body again. If the runner reports that it cannot resolve the attempt, inspect GitHub before retrying a write.
