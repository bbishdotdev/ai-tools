# PR reviews

## Contract

`review-pr` runs two independent model sessions, anonymizes structured findings, and starts a fresh adjudicator with the source needed to challenge them. Both reviewers question whether the PR is needed. Current ADRs and the bstack baseline govern the review. An empty, completed review can approve; an unavailable or incomplete review cannot.

Follow-ups use the last complete review, new changes and affected scope. Settled findings need explicit dispositions, and unchanged inputs should not cause fresh inference. Changed base/history, review configuration or policy requires a broader assessment. Publication is separate, explicitly authorized, tied to the reviewed commit and reconciled on retries.

## Draft checks

```sh
python3 -B -m unittest discover -s bstack/github/tests
python3 -B bstack/scripts/test_package.py
python3 -B bstack/scripts/layers.py check
python3 -B bstack/scripts/package.py check
```

Use temporary Git repositories and fake forge/model executables for lifecycle checks. Cover a clean result, disproved concern, incremental resolution across several follow-ups, human replies without code changes, unchanged-run reuse, missing or malformed model output, stale publication and retry reconciliation. These checks establish orchestration behavior, not review quality or live authentication.

Install the generated bundle into a disposable consumer, remove the downloaded installer and run the installed review helper's help/doctor. Confirm its prompts and referenced principles resolve from the installed package. Doctor's runtime-unchecked result is not a successful model review.

## Live calibration, when requested

Start with a small known fixture or a user-selected PR. Ask the installed skill to perform the review without telling it the expected findings. Keep publication off until authorized. Include a real defect, a clean change, an ADR-backed intentional choice, a tempting false positive, and a PR whose proposed fix addresses the wrong cause. A single fixture can cover several of these behaviors; don't create a test per instruction sentence.

Inspect raw reviewer reports, the anonymous adjudicator input, dispositions and final body. Verify source citations and the actual configured model identities. Repeat after a narrow fix; inspect what was reread and whether the review stayed within the delta's blast radius. Fresh prompts saying "incremental" do not prove scoped behavior.

For authorized publication, check the actual GitHub review body, commit and event. A self-review comment is not an approval. Confirm a retry does not duplicate the review. Never change another author's PR, create competing work, modify branch protection, or force a push solely for a test. Record remaining model, provider and operating-system limits in `.bstack/verification/`.
