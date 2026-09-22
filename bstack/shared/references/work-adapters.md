# Planning and ticket adapters

Wayfinder planning and implementation tickets have independent destinations. Each defaults to `local`. Configuring one must not select the other. Same-provider and mixed-provider arrangements are valid targets for future adapters.

The current release implements the local adapter through [workspace operations](../../workspace/OPERATIONS.md). It does not implement Jira, GitHub or Linear synchronization. Resolve the intended area with the [workflow helper](../workflow.py):

```bash
python3 /absolute/package/shared/workflow.py --project /path/to/project preflight --mode manual --area wayfinder
python3 /absolute/package/shared/workflow.py --project /path/to/project preflight --mode manual --area tickets
```

`both` checks a workflow crossing the boundary. An unavailable ticket destination should not block an independent planning read or session. Preflight is read-only and runs before creating records for the selected area.

Optional private configuration lives at `<workspace.root>/.bstack/workspace/adapters.json`. Omitting either area selects local for that area:

```json
{
  "version": 1,
  "wayfinder": {"provider": "local"},
  "tickets": {"provider": "local"}
}
```

An explicit external selection is currently reported as unsupported. Do not silently redirect it into the local database, switch provider on failure, or claim that a saved draft was delivered remotely. A local draft can preserve progress when that fallback is authorized. Ordinary consumers who have configured nothing can work offline immediately.

## Contract for future providers

Provider implementations own credentials, external project/record IDs, links and version tokens. They must declare which operations they support: read/search, create/update, typed relationships, revision checks, claims, acceptance history and source freshness. Do not assume SQLite transactions or fencing exist remotely. A missing capability needs an explicit limitation or a tested substitute.

Cross-provider spec and ticket sources retain the planning provider, stable record identity, accepted version, and a resolvable reference. Local IDs are not remote IDs, and a URL alone is not an accepted revision. Creating an external ticket and linking its planning source cannot be treated as one atomic transaction across providers. Adapters must handle partial failures, uncertain retries and reconciliation before claiming delivery.

Provider configuration does not authorize messages, publishing or other external mutations. Preserve requested scope and the host's permission requirements. Local private artifacts remain available regardless of provider choice. Imports, exports, synchronization and conflict resolution need focused implementation and verification for each provider; configuration alone does not supply them.
