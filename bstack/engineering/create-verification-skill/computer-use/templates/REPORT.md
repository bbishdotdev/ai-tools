# Report: <product> computer-use run <run id>

Send this as your final message. Keep sections in this order and don't summarize away failures.

## 1. Run

- Run folder: `<absolute path>`
- Git revision: `<from the run folder>`
- Driver: <app and model>
- Surfaces run, in order: <…>

## 2. Harness summary

The `summary` output, verbatim, in a code block.

## 3. Expected results

Per surface, each "Expected results" line from its script:

| Surface | Probe | Expected | PASS / FAIL / INVALID / BLOCKED | What you saw (on anything but PASS) |
| --- | --- | --- | --- | --- |

## 4. Answers

Per surface, the answers to its script's "Questions for the driver".

## 5. Script corrections

Every place a script was wrong, vague, or needed a fallback: the step, what it said, what was actually on screen, and the screenshot name.

## 6. Blocked and invalid passes

Each with the reason and the last screenshot. Say which passes need a fresh run.

## 7. Reference screenshots

`<run>/reference/<surface>/` contents with a one-line caption each.
