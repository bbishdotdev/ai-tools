---
name: grilling
description: Stress-test a plan or decision through dependency-ordered question rounds until the decision owner confirms shared understanding.
disable-model-invocation: true
metadata:
  author: Brenden Bishop
  attribution: ../../ATTRIBUTION.md
---

# Grilling

Interview until the design is understood. Model the discussion as a tree of decisions and their prerequisites. Read [decision authority](../../shared/references/decision-authority.md) before starting; human answers are the default. Automatic routing does not authorize answering for the user.

Work in rounds. The frontier contains every decision whose prerequisites are already settled. Ask the whole frontier together, numbering each question and giving a concrete recommended answer. Wait for the answers, update the tree, then ask the next frontier. Questions that depend on another unanswered question belong in a later round. Keep the tree scoped to the requested decision, not every possible future feature.

Find facts yourself. Dispatch bounded exploration when supported, or inspect the relevant code and sources directly. An unfinished investigation blocks its dependent questions only; continue the rest of the frontier. Present evidence separately from recommendations. The decision owner settles trade-offs.

For explicitly delegated autonomous grilling, complete the shared preflight before creating planning records. Run the real exchange between the configured, distinct interviewer and respondent models. Pass the scoped authority and evidence to both. Keep their objections and unresolved points visible; a role label alone does not establish a second model. Respect the agreed scope and run limits. Return unanswered decisions when authority, execution capability, or the limit prevents resolution.

Stop when the in-scope frontier is empty. Summarize the resulting understanding and get confirmation from the decision owner before acting on it. Reuse an explicit confirmation already given for that understanding. In autonomous mode the authorized respondent confirms within its delegated scope. Unresolved disagreement stays unresolved.

The caller owns persistence. For a Wayfinder question, return the accepted answer, authority, and artifact references to [Wayfinder](../wayfinder/SKILL.md). For glossary or durable architectural decisions, use [domain modeling](../domain-modeling/SKILL.md). Finishing the interview does not itself authorize implementation.
