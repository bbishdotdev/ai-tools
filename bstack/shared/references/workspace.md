# Workspace access

Use the bundled [workspace CLI](../../workspace/cli.py) for local planning and tickets. It uses the same operations and store as the browser; no running server or third-party account is required. Read [work adapters](work-adapters.md) before choosing where records belong.

Resolve the CLI and [workflow helper](../workflow.py) relative to this file, then pass the consumer project explicitly. In an installed package, `index.json` also names both entrypoints. Never assume the maintainer checkout exists or that the shell is in the package directory.

```bash
python3 /absolute/package/shared/workflow.py --project /path/to/project preflight --area both --mode manual
python3 /absolute/package/workspace/cli.py --project /path/to/project init
python3 /absolute/package/workspace/cli.py --project /path/to/project request workspace.read
```

Ordinary manual work needs no role configuration. Initialize once if the workspace is missing; an invalid, corrupt, or future-version workspace requires repair, not replacement. Initialize the empty store before adding optional configuration files to its directory. Autonomous preflight must pass before creating or changing planning records. For an existing workspace, `request` discovers it. Use the [shared executable request helper](workspace-requests.md) for all local skill operations instead of generating client code or envelopes. Read [operations](../../workspace/OPERATIONS.md) only for the input fields and lifecycle rules needed by the current phase.

Start with `workspace.read`. Its `workspace.root` owns the durable store across linked Git worktrees. Query the relevant map, question, spec or ticket by stable ID before writing. Use an agent actor for agent writes, even when recording a human's decision. The separate authority record names the actual human confirmation or scoped delegation.

The helper saves replayable receipts and derives revisions and claim credentials from explicit snapshots. Acquire a claim before editing an existing question, spec or ticket. Use the latest successful receipt as the next basis; reread records after external changes. A conflict requires rereading and reconciling the intended change. Do not blindly overwrite, take over another agent, or treat a claim as readiness or decision authority. Release ownership when handing work to the next phase.

## Records and files

The database owns maps, questions, accepted answers, spec bodies and revisions, tickets, relationships, progress and history. Do not create Markdown shadow backlogs or a second authoritative spec. Export only when requested or required by a configured destination.

Keep private artifacts beneath `<workspace.root>/.bstack/workspace/artifacts/`:

| Artifact | Folder |
| --- | --- |
| Cited investigation findings | `research/` |
| Session transfer | `handoffs/` |
| Draft questionnaires | `questionnaires/` |
| Isolated prototype session | `prototypes/<session>/` |
| New domain/ADR drafts | `domain/`, `adr/` |

Preserve existing project `CONTEXT.md`, `CONTEXT-MAP.md` and ADR conventions. A private draft does not supersede an accepted repository decision. Promote drafts to repository documents when the user or project convention calls for it. Keep prototype targets usable through handoff; unfinished or explicitly saved experiments survive session changes.

Store artifact references with the relevant answer, spec, ticket or handoff. The core treats references as opaque strings. It does not read files, verify freshness, authenticate decision makers, or prove that a cited check ran. The agent must inspect the relevant evidence before relying on it.
