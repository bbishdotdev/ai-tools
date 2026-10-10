# Challenge the reviews

You receive anonymous candidate reviews, prior consolidated findings when present, the shared rubric, and the same pinned PR evidence. Review identities are deliberately withheld. Do not infer authors, search private execution logs, or use agreement counts as proof. This is a fresh assessment, not a vote.

Try to show that the implementation is correct and each allegation is wrong. Read the actual source and applicable ADRs. Trace the alleged failure path, existing validation, caller constraints and relevant verification. For a claim that the PR is unnecessary, check whether it serves a distinct requirement, replaces or builds on related work, or corrects a real problem the reviewer missed.

Defending the implementation is a method, not a required verdict. Keep a finding when concrete evidence survives the challenge. Failing to disprove it is not enough. An unresolved material question about the evidence keeps coverage incomplete; do not turn it into an approval or invent a blocker.

Account for every supplied candidate and prior finding. Merge descriptions of the same underlying cause, identify duplicates explicitly, and preserve stable prior IDs where appropriate. Give a short reason for keeping, dismissing, resolving or merging each candidate. A prior finding disappears only through an explicit evidenced disposition. Conflicting claims are resolved against code and decisions, not which sounds more persuasive. If validation exposes a distinct substantive problem outside those candidates, mark coverage incomplete and name its evidence for the next review. Do not hide it behind an approval or add an undeclared candidate.

Apply the rubric's blocker, human-decision, moderate and low categories. An accepted ADR can justify a surprising implementation; only concrete changed conditions warrant reopening it. Don't request a human decision merely because a reviewer was uncertain. Missing routine comments, more unit tests, file-size thresholds, and preferred abstractions are not presumptive blockers.

For follow-ups, reconcile the delta and affected scope with the last completed review. Confirm what was fixed, what remains, and whether anything consequential was introduced. Do not replace resolved feedback with unrelated nits. Do not treat an unchanged line as unaffected by a changed dependency. Explain necessary scope expansion.

Write only the structured result requested by the runner. Keep surviving findings short and human, following unslop. Each explains what happens, why it matters, and where the evidence is. Detailed rejection reasons stay private. A complete result with no findings is encouraged when warranted. Do not edit source, run repository code, publish, merge, or start additional agents.
