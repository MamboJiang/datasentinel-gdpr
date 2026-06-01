"""Private baseline helpers for prelaunch delta scans."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .source_documents import SourceDocument


@dataclass(frozen=True)
class DeltaComparison:
    new_keys: set[str]
    modified_keys: set[str]
    unchanged_keys: set[str]
    missing_keys: set[str]

    @property
    def changed_keys(self) -> set[str]:
        return self.new_keys | self.modified_keys


def file_key(document: SourceDocument) -> str:
    return hashlib.sha256(document.source_path.encode("utf-8")).hexdigest()[:24]


def fingerprint_documents(documents: list[SourceDocument]) -> list[dict[str, Any]]:
    records = []
    for document in documents:
        content_hash = hashlib.sha256()
        content_hash.update(document.text.encode("utf-8", errors="replace"))
        content_hash.update(b"\0")
        content_hash.update(str(document.size_bytes).encode("ascii"))
        records.append({
            "fileKey": file_key(document),
            "contentFingerprint": "sha256:" + content_hash.hexdigest()[:32],
            "sizeBytes": document.size_bytes,
            "fileFormat": document.file_format,
            "recognitionDifficulty": document.recognition_difficulty,
        })
    return sorted(records, key=lambda item: item["fileKey"])


def inventory_fingerprint(records: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(str(record["fileKey"]).encode("ascii"))
        digest.update(b":")
        digest.update(str(record["contentFingerprint"]).encode("ascii"))
        digest.update(b";")
    return "sha256:" + digest.hexdigest()[:32]


def build_source_baseline(
    *,
    source_id: str,
    scan: dict[str, Any],
    findings: list[dict[str, Any]],
    file_fingerprints: list[dict[str, Any]],
    previous_baseline: dict[str, Any] | None = None,
    delta_comparison: DeltaComparison | None = None,
) -> dict[str, Any]:
    file_inventory = scan.get("fileInventory") if isinstance(scan.get("fileInventory"), dict) else {}
    finding_file_keys = _updated_finding_file_keys(findings, previous_baseline, delta_comparison)
    return {
        "sourceId": source_id,
        "baselineScanId": scan.get("scanId"),
        "baselineSourceSnapshotId": file_inventory.get("sourceSnapshotId"),
        "baselineInventoryFingerprint": inventory_fingerprint(file_fingerprints),
        "baselineTotalFiles": scan.get("totalFiles", len(file_fingerprints)),
        "baselineFindingCount": len(finding_file_keys),
        "findingFileKeys": finding_file_keys,
        "fileFingerprints": file_fingerprints,
    }


def compare_to_baseline(baseline: dict[str, Any], current_records: list[dict[str, Any]]) -> DeltaComparison:
    baseline_by_key = _records_by_key(baseline.get("fileFingerprints"))
    current_by_key = _records_by_key(current_records)
    baseline_keys = set(baseline_by_key)
    current_keys = set(current_by_key)

    shared_keys = baseline_keys & current_keys
    modified = {
        key
        for key in shared_keys
        if baseline_by_key[key].get("contentFingerprint") != current_by_key[key].get("contentFingerprint")
    }
    return DeltaComparison(
        new_keys=current_keys - baseline_keys,
        modified_keys=modified,
        unchanged_keys=shared_keys - modified,
        missing_keys=baseline_keys - current_keys,
    )


def changed_documents(documents: list[SourceDocument], comparison: DeltaComparison) -> list[SourceDocument]:
    changed = comparison.changed_keys
    return [document for document in documents if file_key(document) in changed]


def running_delta_summary(baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        **_baseline_fields(baseline),
        "status": "running",
        "deltaFingerprint": _delta_fingerprint(baseline, "running", "pending"),
        "changedFiles": 0,
        "newFiles": 0,
        "modifiedFiles": 0,
        "unchangedFiles": 0,
        "missingFiles": 0,
        "processedChangedFiles": 0,
        "carriedForwardFiles": int(baseline.get("baselineTotalFiles") or 0),
        "unchangedFindingsCarriedForward": int(baseline.get("baselineFindingCount") or 0),
        "reopenedFindings": 0,
        "missingFilesTreatedAsDeleted": False,
        "rawContentExposed": False,
        "legalConclusionProvided": False,
        "deletionExecuted": False,
        "warnings": ["Delta comparison is pending while the changed-file scan starts."],
    }


def completed_delta_summary(
    baseline: dict[str, Any],
    comparison: DeltaComparison,
    *,
    processed_changed_files: int,
    reopened_findings: int,
) -> dict[str, Any]:
    changed_files = len(comparison.changed_keys)
    unchanged_files = len(comparison.unchanged_keys)
    return {
        **_baseline_fields(baseline),
        "status": "completed",
        "deltaFingerprint": _delta_fingerprint(baseline, "completed", f"{changed_files}:{len(comparison.missing_keys)}"),
        "changedFiles": changed_files,
        "newFiles": len(comparison.new_keys),
        "modifiedFiles": len(comparison.modified_keys),
        "unchangedFiles": unchanged_files,
        "missingFiles": len(comparison.missing_keys),
        "processedChangedFiles": processed_changed_files,
        "carriedForwardFiles": unchanged_files,
        "unchangedFindingsCarriedForward": _carried_forward_findings(baseline, comparison),
        "reopenedFindings": reopened_findings,
        "missingFilesTreatedAsDeleted": False,
        "rawContentExposed": False,
        "legalConclusionProvided": False,
        "deletionExecuted": False,
        "warnings": _completed_warnings(comparison),
    }


def _baseline_fields(baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "baselineScanId": baseline.get("baselineScanId"),
        "baselineSourceSnapshotId": baseline.get("baselineSourceSnapshotId"),
        "baselineInventoryFingerprint": baseline.get("baselineInventoryFingerprint"),
        "baselineTotalFiles": int(baseline.get("baselineTotalFiles") or 0),
        "baselineFindingCount": int(baseline.get("baselineFindingCount") or 0),
    }


def _delta_fingerprint(baseline: dict[str, Any], status: str, suffix: str) -> str:
    digest = hashlib.sha256()
    digest.update(str(baseline.get("baselineInventoryFingerprint") or "").encode("ascii", errors="ignore"))
    digest.update(b":")
    digest.update(status.encode("ascii"))
    digest.update(b":")
    digest.update(suffix.encode("ascii"))
    return "sha256:" + digest.hexdigest()[:32]


def _completed_warnings(comparison: DeltaComparison) -> list[str]:
    warnings = []
    if comparison.unchanged_keys:
        warnings.append(f"{len(comparison.unchanged_keys)} unchanged baseline files were carried forward without new findings.")
    if comparison.missing_keys:
        warnings.append(f"{len(comparison.missing_keys)} missing baseline files are source inventory changes, not lawdit deletion.")
    return warnings


def _carried_forward_findings(baseline: dict[str, Any], comparison: DeltaComparison) -> int:
    finding_keys = baseline.get("findingFileKeys")
    if not isinstance(finding_keys, list):
        return 0
    return len({str(key) for key in finding_keys} & comparison.unchanged_keys)


def _updated_finding_file_keys(
    findings: list[dict[str, Any]],
    previous_baseline: dict[str, Any] | None,
    delta_comparison: DeltaComparison | None,
) -> list[str]:
    current_finding_keys = {str(item["fileKey"]) for item in findings if isinstance(item.get("fileKey"), str)}
    if not previous_baseline or not delta_comparison:
        return sorted(current_finding_keys)

    previous_keys = previous_baseline.get("findingFileKeys")
    if not isinstance(previous_keys, list):
        return sorted(current_finding_keys)

    carried_forward_keys = {str(key) for key in previous_keys} & delta_comparison.unchanged_keys
    return sorted(carried_forward_keys | current_finding_keys)


def _records_by_key(records: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(records, list):
        return {}
    return {
        str(record["fileKey"]): record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("fileKey"), str)
    }
