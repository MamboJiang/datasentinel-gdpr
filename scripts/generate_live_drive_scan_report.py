#!/usr/bin/env python3
"""Generate the redacted deployed Google Drive scan evidence report."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from lawdit.ai_config import load_local_env  # noqa: E402
from lawdit.source_http import build_sqlite_app  # noqa: E402


DEFAULT_FOLDER_ID = "1AmTxh7RhEyvgo400SAZHI8s_CawvAdQn"
DEFAULT_FOLDER_NAME = "GDPR-data-samples-main"
DEFAULT_OUTPUT = ROOT / "tests" / "fixtures" / "gdpr_data_samples_main" / "live_drive_scan_report_agent_us.json"
RAW_VALUE_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"https?://"),
    re.compile(r"/Users/[^\"\\s]+"),
    re.compile(r"/srv/lawdit/(?:sources|data)/[^\"\\s]+"),
    re.compile(r"\b(?:access_token|refresh_token|Bearer)\b"),
)


def main() -> int:
    args = _args()
    load_local_env()

    db_path = args.db_path or os.environ.get("LAWDIT_DB_PATH")
    if not db_path:
        raise SystemExit("LAWDIT_DB_PATH or --db-path is required.")

    user_id = args.user_id or os.environ.get("LAWDIT_LIVE_DRIVE_USER_ID")
    if not user_id:
        raise SystemExit("--user-id or LAWDIT_LIVE_DRIVE_USER_ID is required.")

    report = generate_report(
        db_path=db_path,
        user_id=user_id,
        folder_id=args.folder_id,
        folder_name=args.folder_name,
        timeout_seconds=args.timeout_seconds,
    )
    _assert_redacted(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


def generate_report(
    *,
    db_path: str,
    user_id: str,
    folder_id: str,
    folder_name: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    app = build_sqlite_app(db_path, [])
    session_id = app.auth_service.store.create_session(user_id, int(time.time()) + max(timeout_seconds, 900))
    headers = {"Cookie": f"lawdit_session={session_id}", "Content-Type": "application/json"}
    source_id = f"source_drive_live_gdpr_samples_{int(time.time())}"
    trace_id = "trace_live_drive_report"

    try:
        binding = _call(app, headers, "GET", "/api/integrations/google-drive/binding", trace_id)
        source_create = _call(app, headers, "POST", "/api/sources", trace_id, _source_payload(source_id, folder_id, folder_name))
        if source_create["status"] >= 400:
            raise RuntimeError(f"Source creation failed with HTTP {source_create['status']}: {_safe_error(source_create)}")

        scan_start = _call(app, headers, "POST", "/api/scans/full", trace_id, {"sourceId": source_id})
        if scan_start["status"] >= 400:
            raise RuntimeError(f"Scan start failed with HTTP {scan_start['status']}: {_safe_error(scan_start)}")

        scan_id = _data(scan_start)["scanId"]
        scan = _wait_for_scan(app, headers, scan_id, trace_id, timeout_seconds)
        findings_result = _call(app, headers, "GET", "/api/findings", trace_id)
        findings = _data(findings_result) or []
        preview_summary, mixed_pdf_summary, sampled = _preview_summaries(app, headers, findings, trace_id)

        return {
            "reportId": "live_drive_scan_agent_us_2026-06-01_after_mixed_pdf_ocr_fix",
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "folderId": folder_id,
            "bindingStatusCode": binding["status"],
            "bindingConnected": bool((_data(binding) or {}).get("connected")),
            "sourceCreateStatusCode": source_create["status"],
            "scanStartStatusCode": scan_start["status"],
            "scanId": scan_id,
            "sourceId": source_id,
            "scanStatus": scan.get("status"),
            "scanStage": scan.get("stage"),
            "fileInventory": scan.get("fileInventory"),
            "contentExtraction": scan.get("contentExtraction"),
            "signalDetection": scan.get("signalDetection"),
            "findingAssembly": scan.get("findingAssembly"),
            "findingsListStatusCode": findings_result["status"],
            "findingsVisibleCount": len(findings),
            "sourceReviewPreviewSampledFindings": sampled,
            "sourceReviewPreviewSample": preview_summary,
            "mixedPdfPreviewSample": mixed_pdf_summary,
            "privacyRule": (
                "Aggregate server-side Drive scan evidence only; no raw extracted text, raw detected values, "
                "source bodies, provider tokens, refresh tokens, Drive URLs, or private absolute paths."
            ),
            "safetyChecks": {
                "driveFilesMutated": False,
                "providerTokensPersisted": False,
                "refreshTokensPersistedInReport": False,
                "driveUrlsPersisted": False,
                "sourceBodiesPersisted": False,
                "rawTextPersisted": False,
                "rawDetectedValuesPersisted": False,
                "privateAbsolutePathsPersisted": False,
            },
        }
    finally:
        app.auth_service.store.delete_session(session_id)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default=None, help="SQLite DB path. Defaults to LAWDIT_DB_PATH.")
    parser.add_argument("--user-id", default=None, help="Account user ID with a connected Google Drive binding.")
    parser.add_argument("--folder-id", default=DEFAULT_FOLDER_ID)
    parser.add_argument("--folder-name", default=DEFAULT_FOLDER_NAME)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    return parser.parse_args()


def _call(app: Any, headers: dict[str, str], method: str, path: str, trace_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps(payload) if payload is not None else None
    return app.handle(method, path, trace_id, body, "application/json" if payload is not None else None, headers)


def _data(result: dict[str, Any]) -> Any:
    return result.get("body", {}).get("data")


def _source_payload(source_id: str, folder_id: str, folder_name: str) -> dict[str, Any]:
    return {
        "sourceId": source_id,
        "name": folder_name,
        "sourceType": "google_drive_selection",
        "rootLabel": folder_name,
        "sampleFamilies": ["Google_Drive"],
        "config": {
            "items": [{
                "id": folder_id,
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "url": f"https://drive.google.com/drive/folders/{folder_id}",
            }],
        },
    }


def _wait_for_scan(app: Any, headers: dict[str, str], scan_id: str, trace_id: str, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_scan: dict[str, Any] | None = None
    while time.time() < deadline:
        result = _call(app, headers, "GET", f"/api/scans/{scan_id}", trace_id)
        last_scan = _data(result)
        if isinstance(last_scan, dict) and last_scan.get("status") in {"completed", "failed"}:
            break
        time.sleep(2)

    if not isinstance(last_scan, dict):
        raise RuntimeError("Scan did not return a readable status.")
    if last_scan.get("status") != "completed":
        raise RuntimeError(f"Scan did not complete: {last_scan.get('status')} / {last_scan.get('stage')}")
    return last_scan


def _preview_summaries(app: Any, headers: dict[str, str], findings: list[dict[str, Any]], trace_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int]:
    first_preview: dict[str, Any] | None = None
    mixed_pdf_preview: dict[str, Any] | None = None
    sampled = 0
    for item in findings[:30]:
        finding_id = item.get("findingId")
        if not isinstance(finding_id, str):
            continue
        detail = _data(_call(app, headers, "GET", f"/api/findings/{finding_id}", trace_id)) or {}
        preview = detail.get("sourceReviewPreview") if isinstance(detail, dict) else None
        if not isinstance(preview, dict):
            continue
        sampled += 1
        summary = _preview_summary(preview)
        first_preview = first_preview or summary
        if preview.get("fileFormat") == "pdf_mixed":
            mixed_pdf_preview = summary
            break
    return first_preview, mixed_pdf_preview, sampled


def _preview_summary(preview: dict[str, Any]) -> dict[str, Any]:
    anchors = [item for item in (preview.get("anchors") or []) if isinstance(item, dict)]
    return {
        "fileFormat": preview.get("fileFormat"),
        "extractionMethod": preview.get("extractionMethod"),
        "recognitionDifficulty": preview.get("recognitionDifficulty"),
        "redactionMode": preview.get("redactionMode"),
        "rawContentExposed": preview.get("rawContentExposed"),
        "pageImagesExposed": preview.get("pageImagesExposed"),
        "anchorCount": len(anchors),
        "pageCount": len(preview.get("pages") or []),
        "textRangeCount": len(preview.get("textRanges") or []),
        "tableCellCount": len(preview.get("tableCells") or []),
        "structureBlockCount": len(preview.get("structureBlocks") or []),
        "anchorFormats": sorted({anchor.get("format") for anchor in anchors if anchor.get("format")}),
        "pageRegionAnchorCount": sum(1 for anchor in anchors if isinstance((anchor.get("selector") or {}).get("pageRegion"), dict)),
    }


def _safe_error(result: dict[str, Any]) -> str:
    body = result.get("body", {})
    return str(body.get("detail") or body.get("title") or "unknown error")[:240] if isinstance(body, dict) else "unknown error"


def _assert_redacted(report: dict[str, Any]) -> None:
    serialized = json.dumps(report, ensure_ascii=False)
    for pattern in RAW_VALUE_PATTERNS:
        if pattern.search(serialized):
            raise RuntimeError(f"Unsafe report content matched {pattern.pattern}")


if __name__ == "__main__":
    raise SystemExit(main())
