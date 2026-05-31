# Bounded Archive Container Extraction

## Problem Definition

Prelaunch source scans increasingly receive bundled evidence rather than one flat file. A ZIP archive can contain CSV exports, text logs, PDFs, Office documents, OpenDocument files, or email messages that the deterministic engine already understands. Keeping generic ZIP files unsupported leaves common Drive and direct-link business bundles invisible, while unbounded archive expansion would create decompression, recursion, and raw-path exposure risks.

## Research Basis

- PKWARE publishes APPNOTE as the ZIP file format specification: https://support.pkware.com/pkzip/appnote
- Python `zipfile` documents ZIP archive reading and warns about decompression pitfalls such as decompression bombs: https://docs.python.org/3/library/zipfile.html

## Options Considered

| Option | Summary | Decision |
| --- | --- | --- |
| Keep ZIP unsupported | Ask users to unpack archives manually before scanning. | Rejected because bundled Drive/business exports are common and would reduce coverage for the core engine. |
| Extract archives to disk | Unpack ZIP files into a temporary directory and reuse local scanning. | Rejected because it broadens the raw-content surface and adds path traversal cleanup risk. |
| Recursive archive expansion | Scan nested ZIP files and every supported member. | Rejected for P0 because recursion makes resource bounds and source-location semantics harder to prove. |
| Bounded in-memory member extraction | Read a limited number of supported non-archive members in memory, reuse existing extractors, and wrap member evidence anchors with ordinal ZIP member metadata. | Accepted because it improves mixed-format coverage while keeping resource and public-selector boundaries small. |

## Selected Approach

The prelaunch document reader treats `.zip`, `application/zip`, and `application/x-zip-compressed` as moderate-difficulty container inputs. It validates member count and uncompressed member-size budgets before reading selected entries. It skips directories, nested archives, unsupported members, encrypted or unreadable members, and members beyond the configured count. It does not write archive contents to disk.

Each extracted member is passed through the same deterministic extraction path used for standalone files. Public evidence anchors use `format = zip` and source-data-derived ordinal member metadata such as `memberIndex` and `memberPath`. Child selectors may preserve table-cell, structure-path, text-position, OCR, or PDF page metadata where available, but selector metadata must not expose raw ZIP member names, raw source values, absolute paths, or external URLs.

## State Machine

```text
format_identified -> archive_manifest_validated
archive_manifest_validated -> member_selected
member_selected -> member_extraction
member_extraction -> member_anchor_wrapped
member_anchor_wrapped -> deterministic_signal_detection
member_selected -> member_skipped
member_skipped -> archive_complete
archive_manifest_validated -> archive_rejected
archive_rejected -> completed_with_warning
```

Guards:

- Archive body must stay under the prelaunch source file-size limit before ZIP parsing.
- Archive member count and total declared uncompressed bytes must stay under configured limits.
- Individual member reads must stop at the configured per-member byte limit.
- Nested archive members are skipped in P0.
- ZIP member names are not exposed in public selectors or redacted evidence payloads.
- Existing child extractors still enforce their own format-specific bounds.

Side effects:

- Raw archive bytes and member bytes exist only in scan memory.
- Public payloads store redacted evidence, counts, methods, difficulty tiers, and source-local ordinal anchors only.
- Unsupported or skipped archive members do not create fake findings.

Failure paths:

- Malformed ZIP, ZIP64 issues, encrypted-only archives, unreadable members, no extractable supported members, or over-limit archives become unsupported warning-counted files.
- A failed member does not fail the whole archive when another supported member extracts successfully.
- A direct-link ZIP with no extractable supported member completes as a warning-only batch rather than producing fake findings.

## Impact Surface

- Backend: source format recognition, ZIP member extraction, local/remote/Drive supported suffix and MIME checks, generated format challenge tests.
- Frontend: Sources supported-format list and file-review selector summaries.
- Contracts: evidence-anchor selector metadata remains optional/additive; archive-specific fields are public-safe optional selector fields.
- Documentation: source-input acceptance, API contract, technical scope, test cases, and security notes.
- Security/privacy: no disk extraction, no member-name exposure in selectors, no recursive archive expansion, bounded decompression.

## Rollback Path

Remove `.zip` and ZIP MIME types from the supported source set and remove archive-specific tests/docs. Existing findings remain valid because anchors are optional and clients must tolerate unknown selector fields; future scans report ZIP files as unsupported.

## Primitive Acceptance Criteria

- A ZIP file under the prelaunch file-size limit can scan supported non-archive members from local, direct-link, or Google Drive selected sources.
- Deterministic detectors can find multilingual sensitive labels inside ZIP member text and return only redacted snippets.
- ZIP member evidence anchors include ordinal member metadata and source-local offsets without raw member names or raw detected values.
- Unsupported, encrypted, nested archive, or over-limit members do not create fake findings.
- Normal deterministic archive scans keep `aiAssistanceUsed = false` and `modelCalls = 0`.
- Automated tests cover ZIP member extraction, redaction, generated challenge coverage, and local-source format counts.
