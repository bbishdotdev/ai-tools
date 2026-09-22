# Glossary format

Read a root `CONTEXT-MAP.md` first when present; follow it to the context that owns the term. Otherwise use the project's existing `CONTEXT.md`. For new private drafts, follow the location policy in [domain modeling](SKILL.md). Do not create a new bounded context just to split a long glossary.

```markdown
# Ordering

The language used to describe orders and their fulfillment.

## Language

**Order**: A customer's request for specific goods under agreed terms.
_Avoid_: Purchase, transaction

**Invoice**: A request for payment after delivery.
_Avoid_: Bill, payment request
```

Pick a canonical term and list misleading alternatives under `_Avoid_`. Keep each definition to one or two sentences. Include concepts particular to this domain; generic programming vocabulary does not belong here. Group terms only when real clusters emerge. Keep implementation decisions, task lists, and exploratory notes elsewhere.

When the project has multiple contexts, its context map names each, links its glossary, and describes meaningful relationships. The same word may legitimately have different meanings across contexts; clarify the owning context instead of forcing a global definition.
