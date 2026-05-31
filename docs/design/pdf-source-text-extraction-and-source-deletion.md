# PDF Source Text Extraction and Source Deletion

## Problem Definition

Prelaunch source scans must handle real user documents that arrive as PDF tickets, reports, and exports. The prior document reader accepted only text-like files, so PDFs with embedded text were skipped even when deterministic rules could identify GDPR-relevant signals. Users also need to remove incorrect source registrations from DataSentinel without deleting files in Google Drive, direct-link locations, or host-mounted folders.

## Research Basis

- pypdf documents `PdfReader` and `page.extract_text()` for extracting text from PDF pages: https://pypdf.readthedocs.io/en/latest/user/extract-text.html
- pypdf states that text extraction is not OCR and cannot extract text from image-only pages: https://pypdf.readthedocs.io/en/latest/user/extract-text.html#ocr-vs-text-extraction

## Options Considered

| Option | Summary | Decision |
| --- | --- | --- |
| Keep PDFs unsupported | Continue skipping PDFs and require users to export text manually. | Rejected because common real files with text layers would remain invisible to deterministic scanning. |
| Text-layer PDF extraction | Extract embedded PDF text in memory during scan execution and pass it through the existing redaction and finding pipeline. | Accepted for prelaunch because it is bounded, reversible, and does not add OCR or raw file storage. |
| OCR all PDFs | Render pages and run OCR before deterministic scanning. | Rejected for this slice because it adds heavier dependencies, more privacy surface, and broader failure modes. |
| Delete source files | Use provider APIs or filesystem deletion when a user deletes a Source. | Rejected because automatic deletion is outside the approved prototype boundary. |
| Delete source registration only | Remove the DataSentinel source metadata row, clear DataSentinel workflow state derived from that registration, and leave external files untouched. | Accepted because it corrects wrong setup state without mutating user files. |

## Selected Approach

The prelaunch document reader treats `application/pdf` and `.pdf` as supported only when the PDF has an extractable text layer. The reader loads bytes in memory, extracts page text with pypdf, and then reuses the existing deterministic signal detection, redaction, finding, metric, and audit flow. Raw source bytes and raw extracted text remain transient.

The source API exposes `DELETE /api/sources/{sourceId}`. The route deletes the DataSentinel source registration from the active store, clears scan/finding state derived from that source registration, and returns the deleted source envelope. Missing source ids return `application/problem+json` with `404`.

## State Machine

```text
source_registered -> connection_checking
connection_checking -> connected
connected -> scan_requested
scan_requested -> extracting_text
extracting_text -> detecting_signals
extracting_text -> unsupported_pdf
detecting_signals -> completed

source_registered -> delete_requested
connected -> delete_requested
delete_requested -> registration_deleted
delete_requested -> delete_rejected_not_found
```

Guards:

- PDF extraction is allowed only for files under the prelaunch byte limit.
- PDFs must have extractable text; image-only PDFs stay unsupported/OCR-deferred.
- Source deletion targets a single source id and does not call provider delete APIs or remove filesystem paths.

Side effects:

- PDF source bodies and extracted text exist only in scan process memory.
- Findings persist redacted evidence and metadata only.
- Source deletion removes the source registration row from DataSentinel state and clears derived scan/finding workflow state for that source.

Failure paths:

- Missing PDF extraction dependency reports an unsupported source warning.
- Unreadable PDFs report extraction failure without creating raw-content payloads.
- Repeated source deletion returns not found.

Rollback path:

- Remove `.pdf` and `application/pdf` from the supported document reader set.
- Remove the `DELETE /api/sources/{sourceId}` route and frontend delete action.
- Existing findings and audit records remain intact; deleted source registrations can be re-added by the user.

## Impact Surface

- Backend: prelaunch document reader, source store interfaces, SQLite source persistence, source HTTP routing, API behavior tests.
- Frontend: Sources row actions and source-state updates.
- Contracts: OpenAPI source deletion route and source config descriptions.
- Deployment: API runtime must install the PDF extraction dependency from `requirements.txt`.
- Security/privacy: no OCR, no raw PDF persistence, no provider token storage, no source-file deletion.

## Primitive Acceptance Criteria

- A PDF with an extractable text layer can be scanned from an approved source and produce redacted findings when deterministic rules match.
- Public API and UI payloads do not expose raw PDF text, raw PDF bytes, provider tokens, or source credentials.
- An image-only or unreadable PDF is reported as unsupported/OCR-deferred rather than silently succeeding.
- A source registration can be deleted from DataSentinel, is absent from the next source list, and no stale scan/finding state remains for that deleted registration.
- Deleting a source registration does not delete or mutate Google Drive files, direct-link files, or host-mounted files.
- Repeating deletion for the same source id returns a not-found problem response.
