"""Source configuration store for the local demo server."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MOCKS_DIR = PROJECT_ROOT / "contracts" / "mocks"


def load_mock(name: str) -> dict[str, Any]:
    with (MOCKS_DIR / name).open(encoding="utf-8") as file:
        return json.load(file)


def default_sources() -> list[dict[str, Any]]:
    if not demo_fixtures_enabled():
        return []

    return copy.deepcopy(load_mock("sources.json")["data"])


def demo_source_ids() -> set[str]:
    return {source["sourceId"] for source in load_mock("sources.json")["data"]}


def demo_fixtures_enabled() -> bool:
    return os.environ.get("DATASENTINEL_ENABLE_DEMO_FIXTURES", "true").lower() not in {"0", "false", "no", "off"}


class SourceStore:
    """In-memory source store seeded from contract mocks."""

    def __init__(
        self,
        sources: Iterable[dict[str, Any]] | None = None,
        *,
        allowed_roots: Iterable[Path | str] | None = None,
    ) -> None:
        self._sources = {source["sourceId"]: copy.deepcopy(source) for source in (sources or default_sources())}
        self.allowed_roots = tuple(Path(root).resolve() for root in (allowed_roots or ()))

    @classmethod
    def with_roots(
        cls,
        allowed_roots: Iterable[Path | str],
        sources: Iterable[dict[str, Any]] | None = None,
    ) -> "SourceStore":
        return cls(sources, allowed_roots=allowed_roots)

    def list_sources(self) -> list[dict[str, Any]]:
        return copy.deepcopy(list(self._sources.values()))

    def get(self, source_id: str) -> dict[str, Any] | None:
        source = self._sources.get(source_id)
        return copy.deepcopy(source) if source else None

    def add(self, source: dict[str, Any]) -> dict[str, Any]:
        stored = copy.deepcopy(source)
        self._sources[stored["sourceId"]] = stored
        return copy.deepcopy(stored)

    def delete(self, source_id: str) -> dict[str, Any] | None:
        source = self._sources.pop(source_id, None)
        return copy.deepcopy(source) if source else None
