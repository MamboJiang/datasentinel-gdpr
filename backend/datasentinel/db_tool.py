"""Command-line utilities for local SQLite demo persistence."""

from __future__ import annotations

import json
import os
from argparse import ArgumentParser
from pathlib import Path

from .persistent_demo_state import PersistentDemoState
from .sqlite_store import SQLiteDocumentStore, SQLiteSourceStore, SQLiteWorkflowStore

DEFAULT_DB_PATH = Path("data/datasentinel.sqlite3")


def main() -> None:
    parser = ArgumentParser(description="Manage the DataSentinel local SQLite demo database.")
    parser.add_argument("command", choices=("init", "status"))
    parser.add_argument("--db-path", default=os.environ.get("DATASENTINEL_DB_PATH"))
    args = parser.parse_args()

    db_path = Path(args.db_path).expanduser() if args.db_path else DEFAULT_DB_PATH
    documents = SQLiteDocumentStore(db_path)

    if args.command == "init":
        source_store = SQLiteSourceStore(documents)
        workflow_store = SQLiteWorkflowStore(documents)
        PersistentDemoState(source_store, workflow_store)

    print(json.dumps(documents.status(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
