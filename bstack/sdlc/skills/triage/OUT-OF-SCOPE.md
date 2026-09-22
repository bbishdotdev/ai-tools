# Rejected and deferred requests

Keep a rejection's reason and authority discoverable so the same idea is not treated as new intake. Search by domain concept, including synonyms, before creating another record. Surface a matching prior decision to its owner; do not silently reaffirm or overturn it.

The local default is the retained ticket with `triage:wontfix`, an explicit wait/reason, its decision authority, and links to related requests. Reuse a matching concept's record and relate new intake rather than copying a second rejection document. Preserve prior history when a decision is reconsidered.

If the project already maintains `.out-of-scope/` or another rejection index, consult it and follow that convention for accepted enhancement rejections. A useful entry states the concept, durable reason, authority, and prior requests. Keep one entry per concept. Do not create a repository-wide knowledge base just to triage one request.

Distinguish rejection from deferral. Temporary lack of time or a dependency is `triage:deferred`, with the condition for reconsideration in the wait. A feature already implemented elsewhere is not a rejected concept; point to its working behavior and evidence. Bug reports do not automatically become enhancement-policy entries.

Rejected, duplicate, already-implemented, and deferred intake stays in Backlog with its explicit disposition and wait. Done is reserved for this ticket's completed execution with evidence. Reconsidering a request follows the normal triage checks, preserves the old decision in history, and clears the wait only when the condition or decision changes.
