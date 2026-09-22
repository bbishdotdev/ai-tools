# Agent brief

A brief states the accepted behavior, scope, and evidence a fresh implementer needs. For local tickets, the body and acceptance-criteria field own that contract. Update the existing ticket through its claim and revision checks; do not create a competing specification in a comment or file.

Use this structure when it helps:

```markdown
## Summary

The change and the problem it addresses.

## Current and desired behavior

What happens now, what should happen, and meaningful edge cases.

## Evidence and governing decisions

Observed reproduction or diff checks, accepted source decisions, and ADR links.
Distinguish confirmed findings from unresolved assumptions.

## Key interfaces

Domain concepts, types, behavioral contracts, or configuration shapes affected.

## Scope

What is included and what remains outside this change.
```

Put concrete, independently verifiable criteria in `acceptanceCriteria`. Preserve the decision authority and source references in their dedicated ticket fields. Keep paths and line numbers out of durable requirements; they may appear in dated evidence references when useful. Describe behavior rather than a fixed sequence of code edits.

For a proposed PR, describe what remains to finish or correct in that diff. Reuse its valid work rather than asking an implementer to recreate the feature. For `ready-for-human`, explain the judgment, access, or manual verification that requires a person. A brief is not proof that the implementation or its tests passed.
