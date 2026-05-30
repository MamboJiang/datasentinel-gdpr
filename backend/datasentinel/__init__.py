"""DataSentinel demo backend API."""

from .source_api import SourceApi, problem_from_issue
from .source_connection import ConnectionIssue, ConnectionPolicy, SourceConnectionService
from .source_http import SourceHttpApp, build_default_app
from .source_store import SourceStore, default_sources


def make_handler(*args, **kwargs):
    from .source_server import make_handler as build_handler

    return build_handler(*args, **kwargs)

__all__ = [
    "ConnectionIssue",
    "ConnectionPolicy",
    "SourceApi",
    "SourceConnectionService",
    "SourceHttpApp",
    "SourceStore",
    "build_default_app",
    "default_sources",
    "make_handler",
    "problem_from_issue",
]
