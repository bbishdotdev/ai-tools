# PR reviews

## Contract

`review-pr` runs two independent model sessions, anonymizes structured findings, and starts a fresh adjudicator with the source needed to challenge them. Both reviewers question whether the PR is needed. Current ADRs and the bstack baseline govern the review. An empty, completed review can approve; an unavailable or incomplete review cannot.

Follow-ups use the last complete review, new changes and affected scope. Settled findings need explicit dispositions. Unchanged compatible inputs reuse assessments, including trusted shared public reviews; different models or `--fresh` still run independently. Human rebuttals receive evidence-based reassessment without automatic concession. Publication is separately authorized, tied to the reviewed commit and reconciled action by action.

## Draft checks

```sh
python3 -B -m unittest discover -s bstack/github/tests
python3 -B bstack/scripts/test_package.py
python3 -B bstack/scripts/layers.py check
python3 -B bstack/scripts/package.py check
```

Use temporary Git repositories and fake forge/model executables for lifecycle checks. Cover a clean result, disproved concern, incremental resolution across several follow-ups, human replies without code changes, unchanged-run reuse, missing or malformed model output, stale publication and retry reconciliation. These checks establish orchestration behavior, not review quality or live authentication.

Include stdout-only client failures and generated ZIP coverage. A configured ZIP must match its pinned source tree exactly, including after a follow-up reverts only the archive. A mismatch must leave the prior complete assessment intact.

Cover preserved partial findings, unchanged partial reuse, current target ADR context, closed/conflicting PR preflight and public receipt reuse from another checkout without creating an approval. Verify that changed models run and existing reviews remain in context. Exercise agreement-only reactions without another request-changes event, evidence-based replies, unique new blockers, and retries after a reply succeeds but the later review fails. Malformed, edited, dismissed or untrusted receipts must not skip review.

Install the generated bundle into a disposable consumer, remove the downloaded installer and run the installed review helper's help/doctor. Confirm its prompts and referenced principles resolve from the installed package. Doctor's runtime-unchecked result is not a successful model review.

## Live calibration, when requested

Start with a small known fixture or a user-selected PR. Ask the installed skill to perform the review without telling it the expected findings. Keep publication off until authorized. Include a real defect, a clean change, an ADR-backed intentional choice, a tempting false positive, and a mistaken root-cause claim. A single fixture can cover several behaviors; don't create a test per instruction sentence. Include both a valid scope rebuttal and an objection that tries to excuse a reachable critical defect, checking that the models can concede and push back for the right reasons.

Inspect raw reviewer reports, the anonymous adjudicator input, dispositions and final body. Verify source citations and the actual configured model identities. Repeat after a narrow fix; inspect what was reread and whether the review stayed within the delta's blast radius. Fresh prompts saying "incremental" do not prove scoped behavior.

For authorized publication, check the actual GitHub review body, commit and event. A self-review comment is not an approval. Confirm a retry does not duplicate the review. Never change another author's PR, create competing work, modify branch protection, or force a push solely for a test. Record remaining model, provider and operating-system limits in `.bstack/verification/`.
