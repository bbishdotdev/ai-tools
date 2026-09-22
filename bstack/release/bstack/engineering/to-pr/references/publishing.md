# Publish a reviewed briefing

Use the [GitHub helper](../../../github/pr.py) for GitHub. It needs Python 3 and an authenticated `gh` for the selected host. Inspect its help and available operations before use. Other forges follow the same review policy through supported tools. If those tools are unavailable, keep a local draft and name the missing delivery step. Do not claim GitHub commands support another forge.

Resolve paths from this skill's real installed location, including symlinks. `../../github/pr.py` and `../../github/pull_request_template.md` are relative to the directory containing `SKILL.md`. Do not assume the consumer has a maintainer checkout or a particular working directory. Keep private scans, notes, bodies, and prepared bundles in the consumer's gitignored `.bstack/` directory. These records can contain other PRs' source code.

## Prepare the branch and evidence

Confirm the selected remote, host, base, and head. The helper handles a pushed head branch in the same repository. Publishing a fork PR or an unpushed branch needs a supported alternative or a clear limitation. Commit and push only within the user's authorized scope. A dry-run publication does not authorize a push.

Use the final diff against the intended base, including the parent branch for a stacked PR. Check local and required CI results relevant to this revision. Resolve required review findings or keep the PR draft with the remaining work visible. Preserve the consumer's required template fields.

Create `body.md` using the [template](../../../github/pull_request_template.md). Keep the state comparison in Before and after and the implementation visual in For visual nerds. Use a body file so shell substitutions cannot alter prose or expose data. For an image managed by the helper, put `<!-- bstack-visual:flow -->` in the visual section and add a media manifest:

```json
[
  {
    "id": "flow",
    "file": "flow.svg",
    "alt": "Illustration of a ticket update passing through an ownership check",
    "fallback": "Update request → check the active claim → save when the token matches; otherwise reject the update."
  }
]
```

Media paths resolve relative to the media manifest. The example describes an illustration, not a test result. Use a real visual and labels supported by the actual diff. Keep the fallback useful by itself. Inspect the rendered image and verify screenshot provenance before publication. If upload is unsupported, retain the fallback and report the missing attachment. Do not add an external image service or commit evidence files just to obtain a URL without authorization.

## Read all open work

Set `PR_HELPER` to the resolved helper path. The repository and branch names below are illustrative; replace them with the verified values.

```bash
python3 "$PR_HELPER" scan --repo owner/repo --host github.com --base main --head codex/change --out .bstack/pr/scan.json
python3 "$PR_HELPER" show --scan .bstack/pr/scan.json
python3 "$PR_HELPER" show --scan .bstack/pr/scan.json --target
```

Default `show` returns compact inventory and coverage. `--target` returns the proposed change, and `--number N` returns one PR's details. Use `--full` only when the complete raw scan is needed; it can include every patch.

The scan supplies candidate evidence. Review the full open-PR inventory, including drafts. Search by intended outcome, ticket, feature, subsystem, public contracts, and accepted decisions, as well as changed files. Titles cannot establish that the remaining PRs are unrelated. Read the body and matching diff for each relevant PR. Follow decision links when they affect the classification.

Classify each open PR with the strongest supported finding:

| Disposition | Required basis |
| --- | --- |
| `clear` | The inspected scope has no meaningful overlap. |
| `related` | Work touches the same area or a dependency, but its intent and contracts remain compatible. |
| `duplicate` | Both PRs solve the same accepted problem or add the same capability, even through different files. |
| `contradiction` | The changes require incompatible behavior, ownership, interfaces, or accepted decisions. Name both sides. |
| `hard-conflict` | Evidence establishes an actual integration or merge conflict. Shared paths alone are insufficient. |

For each finding, identify the other PR and the specific behavior, diff location, or accepted ADR that supports it. Give an actionable reason, such as which duplicate to keep or which contract must be reconciled. Do not call an unknown mergeability result a hard conflict. If several categories apply, record the additional evidence in the reason. A same-branch existing PR is the publication target, not a competing PR.

Write a review record tied to the scan ID. This is a data shape, not a finding to copy:

```json
{
  "version": 1,
  "scanId": "ID_FROM_SCAN",
  "reviews": [
    {
      "number": 123,
      "disposition": "related",
      "reason": "Explain the inspected relationship and why the changes remain compatible.",
      "evidence": ["Link to the relevant diff or decision, with the concrete supporting fact."]
    }
  ]
}
```

Do not fill uninspected PRs with `clear` to satisfy coverage. Missing reviews, incomplete diffs, failed detail reads, and unresolved comparisons are coverage limits. State what the check covered and what remains unknown. A local scan is not proof that the forge stayed unchanged.

The helper saves a partial scan when comparison, detail, or final consistency reads fail after the initial snapshot. That scan can prepare an authorized draft with explicit coverage limits. If the initial branch identity or open-PR list cannot be read, the helper exits without a scan artifact. Keep the body locally and report the missing access. Do not fabricate an empty inventory or publish from an invented scan.

## Prepare, inspect, and publish

```bash
python3 "$PR_HELPER" prepare --scan .bstack/pr/scan.json --review .bstack/pr/review.json --title 'fix(workspace): preserve the current ticket owner' --body .bstack/pr/body.md --out .bstack/pr/bundle
python3 "$PR_HELPER" publish --bundle .bstack/pr/bundle
```

Add `--media .bstack/pr/media.json` when the body contains media markers. Add `--draft` to `prepare` for draft-only authorization, missing required checks, or unfinished work. Inspect the prepared body and the read-only publication plan. Confirm the helper's linked overlap notice describes the evidence accurately and that its Reviewer attention gives a concrete next step. Keep other genuine reviewer actions from the authored body.

The helper must complete its final freshness check immediately before creation. If the head, base, or open-PR evidence changed before creation, refresh the scan and affected substantive reviews, then prepare again. Do not reuse a stale classification to make a PR ready. Failed or incomplete coverage stays explicit and draft. When the user has already authorized publication to this destination, proceed without asking again:

```bash
python3 "$PR_HELPER" publish --bundle .bstack/pr/bundle --write
```

Publication creates a draft first. Only a complete, clear, fresh review and applicable ready-publication scope permit a ready PR. A flagged PR still gets created as a draft when publication is authorized. The helper inserts a linked warning above the briefing and specific actions below it. Preserve those warnings during edits until a fresh substantive review resolves them. Do not promote a prior draft merely because another PR closed or the current scan no longer flags it.

If a PR already exists and its review becomes stale, leave it draft for an explicit reviewed follow-up. A new bundle cannot adopt that PR, overwrite its body, or change its readiness. Recheck the current diff and all open PRs, then carry the refreshed evidence into a supported follow-up on the existing PR within the user's authorization. Never create a replacement PR to bypass this limit.

If a create or attachment response is uncertain, reconcile the same branch and bundle before retrying. Never create a second PR for the same branch to escape an uncertain response. Verify the final PR's content, visuals or fallbacks, base, head, and status through the forge. Report the URL and any limits. Use the host's PR attachment capability when available. Opening a PR does not authorize comments on other PRs, review requests, a merge, or ongoing monitoring.
