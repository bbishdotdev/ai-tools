# ADR format

Use the project's established ADR location and numbering. If none exists, use the private draft location from [domain modeling](SKILL.md). Read nearby decisions before allocating an identifier; do not overwrite a concurrent or existing record.

```markdown
# Store work locally by default

Work must remain usable without access to a hosted tracker. We chose a local
store with optional adapters because requiring a service would block that use.
```

A short paragraph can be sufficient. It states the context, choice, and actual reason. Record the decision owner and confirmation or delegated grant in the available record conventions; distinguish proposed from accepted work. Add alternatives, consequences, or a superseded-by link only when they help a future reader understand the trade-off. Preserve historical decisions when revisiting them.

Create an ADR only when the choice is hard to reverse, surprising without context, and based on real alternatives. Architectural boundaries, durable integration choices, hidden constraints, and costly technology commitments may qualify. Routine implementation details and prototype preferences generally do not. Never invent a rationale because a template appears to demand one.
