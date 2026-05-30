# Local SQLite Persistence

## Problem Definition

The agent-us API preview currently keeps source registrations, scan state, review decisions, audit events, metrics, evaluation context, governance config, permissions, and review support in process memory. That is useful for the first contract server, but it means demo state disappears after restart and can drift into ad hoc temporary registers or code fixtures. DataSentinel needs a lightweight, local, reversible persistence tool that can run on agent-us without approving a production storage platform.

## Research Basis

- Python's official `sqlite3` module provides a DB-API interface to SQLite and documents placeholder binding for SQL values: https://docs.python.org/3/library/sqlite3.html.
- SQLite's official "Appropriate Uses" guidance lists local application storage, server-side application-specific storage, testing, demos, and replacement of ad hoc disk files as appropriate uses: https://www.sqlite.org/whentouse.html.
- SQLite's official overview describes it as a self-contained, serverless, zero-configuration transactional SQL database stored in ordinary disk files: https://www.sqlite.org/about.html.

## Options

| Option | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| Keep in-memory only | Smallest runtime surface | Loses workflow state on restart and encourages ad hoc registers | Rejected |
| Add local SQLite JSON-document store | No runtime dependency, single local file, restart-safe demo state, easy rollback | Not a production multi-tenant storage model | Accepted |
| Add Postgres or managed database | More production-like durability and concurrency | Adds operations, credentials, network, backup, auth, and migration scope too early | Rejected |
| Store mutable state in project fixtures | Easy to inspect in git | Mixes runtime data with code/contracts and risks committing sensitive review notes | Rejected |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| API configured without db path | Server starts | No `--db-path` and no `DATASENTINEL_DB_PATH` | In-memory demo | Seed from contract mocks only in process memory |
| API configured with db path | Server starts | SQLite path is writable | Persistent demo | Create schema when needed, seed sources, load workflow document |
| Persistent demo | Source registered | Source contract validation passes | Source persisted | Upsert source JSON row in SQLite |
| Persistent demo | Scan or review command accepted | Existing command guards pass | Workflow persisted | Save workflow JSON document after mutation |
| Persistent demo | Server restarts | SQLite file exists | Persistent demo | Reload saved source rows and workflow state |
| Persistent demo | SQLite write fails | File or permission guard fails at boundary | Request failed | Return backend error; no source-file, deletion, Graph, OAuth, or tenant side effect |

## Impact Surface

- Backend local storage boundary under `backend/datasentinel/`.
- API server startup options and local environment variable handling.
- Agent-us deployment commands and service-manager guidance.
- Backend behavior tests for restart persistence.
- `ACCEPTANCE.md`, `docs/TRD.md`, `docs/DEPLOYMENT.md`, `docs/DELIVERY_WORKFLOW.md`, and `docs/TestCase.md`.

The OpenAPI contract, mock payload shape, frontend API client, production connector boundary, OAuth/Graph boundary, and deletion boundary are unchanged.

## Rollback Path

1. Stop the API process using `--db-path` or `DATASENTINEL_DB_PATH`.
2. Restart the server without a database path to return to the in-memory demo.
3. Keep or archive the SQLite file outside the repository for audit/debugging, or delete it if the demo state must be reset.
4. Revert the SQLite store modules and documentation if the project chooses a different persistence boundary later.

## Primitive Acceptance Criteria

- The default API server still starts without a database and uses in-memory fixture-backed state.
- Starting the API with `--db-path <file>` or `DATASENTINEL_DB_PATH=<file>` creates a local SQLite file without adding runtime dependencies.
- `python3 -m backend.datasentinel.db_tool init --db-path <file>` creates the schema and seeds contract-compatible demo data.
- `python3 -m backend.datasentinel.db_tool status --db-path <file>` reports schema version, source count, workflow-document count, and database path.
- Source registrations survive a server restart when the same SQLite file is reused.
- Accepted scan/review workflow mutations survive a server restart when the same SQLite file is reused.
- Rejected scan/review commands do not create source, audit, finding, metric, or workflow changes.
- The SQLite store does not store raw source file bodies, unredacted extracted content, production connector credentials, OAuth tokens, Microsoft Graph tenant data, deletion execution state, or legal conclusions.
