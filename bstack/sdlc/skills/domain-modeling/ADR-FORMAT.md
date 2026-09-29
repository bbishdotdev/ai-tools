# ADR format

Use [the shared architecture decision process](../../../shared/references/architecture-decisions.md) for the capture threshold, storage, authority, and supersession. Honor existing formats. For a new project, use one short Markdown file per fundamental decision in `docs/adr/`, with a stable numeric ID and decision-oriented name.

```markdown
# 0001: Store work locally by default

Status: accepted
Decision owner: <actual person or delegated agent>
Confirmation: <actual approval or scoped grant reference>

Work must remain usable without access to a hosted tracker. We chose a local
store with optional adapters because requiring a service would block that use.
```

A short paragraph can be sufficient. It states the context, choice, and actual reason. Replace the example authority fields with real evidence; the example is not an approved record. A delegated decision names its scope and grant. Add scope, a consequential alternative, or a revisit condition only when it helps. Omit empty template sections and transcripts.

For a reversal, the successor adds a `Supersedes:` line with a relative Markdown link to its predecessor and explains the changed condition. The old record changes to `Status: superseded` with a `Superseded by:` link to the successor. Keep the old rationale. Use `Status: retired` when the scope disappears without a successor. Links must point to real records.
