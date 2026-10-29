# Search uses a token index, not a result cache

Status: accepted

## Context

Search latency grows with catalog size, and popular queries repeat. Product names and availability change throughout the day through `Catalog.update`, and each worker process holds its own `Catalog`.

## Decision

Keep search results derived directly from current catalog state. When search needs to be faster, maintain an inverted token index inside `Catalog` and keep it current on every update.

## Rejected alternatives

- **Memoizing search results** (`functools.lru_cache`, `functools.cache`, or a query-to-results dictionary). Rejected because cached results go stale after updates, invalidation has caused incorrect results before, memory grows with the long tail of queries, and it does nothing for distinct queries.
