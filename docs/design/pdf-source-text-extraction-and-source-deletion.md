# PDF Source Text Extraction and Source Deletion

## Problem Definition

Prelaunch source scans must handle real user documents that arrive as PDF tickets, reports, and exports. The prior document reader accepted only text-like files, so PDFs with embedded text were skipped even when deterministic rules could identify GDPR-relevant signals. Users also need to remove incorrect source registrations from DataSentinel without deleting files in Google Drive, direct-link locations, or host-mounted folders.

## Research Basis

- pypdf documents `PdfReader` and `page.extract_text()` for extracting text from PDF pages: https://pypdf.readthedocs.io/en/latest/user/extract-text.html
- pypdf states that text extraction is not OCR and cannot extract text from image-only pages: https://pypdf.readthedocs.io/en/latest/user/extract-text.html#ocr-vs-text-extraction
- Tesseract command-line documentation describes local image OCR and language-pack selection: https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html
- Poppler `pdftoppm` documentation describes rendering PDF pages into image files for bounded local OCR fallback: https://manpages.ubuntu.com/manpages/jammy/man1/pdftoppm.1.html

## Options Considered

| Option | Summary | Decision |
| --- | --- | --- |
| Keep PDFs unsupported | Continue skipping PDFs and require users to export text manually. | Rejected because common real files with text layers would remain invisible to deterministic scanning. |
| Text-layer PDF extraction | Extract embedded PDF text in memory during scan execution and pass it through the existing redaction and finding pipeline. | Accepted as the preferred prelaunch path because it is bounded, reversible, and does not require OCR. |
| OCR all PDFs | Render pages and run OCR before deterministic scanning. | Rejected because text-layer PDFs should not pay the OCR cost or expand failure surface. |
| Bounded PDF OCR fallback | Render a bounded page range only when no text layer is available, then use local Tesseract OCR. | Accepted as a recoverable fallback because it stays local, temporary, and warning-counted when tooling is missing. |
| Bounded OCR for blank pages inside text-layer PDFs | Keep extracted text-layer pages and OCR only blank/scanned pages within the existing OCR page budget. | Accepted because real PDFs can mix generated text pages with scanned appendices, and returning after the first text-layer match can hide sensitive image-page evidence. |
| Bounded OCR for image-bearing text-layer pages | OCR a bounded number of pages that have extractable text plus embedded images, then merge OCR text with the text layer. | Accepted because real PDFs can place sensitive labels in image overlays while keeping unrelated text in the text layer. |
| Delete source files | Use provider APIs or filesystem deletion when a user deletes a Source. | Rejected because automatic deletion is outside the approved prototype boundary. |
| Delete source registration only | Remove the DataSentinel source metadata row, clear DataSentinel workflow state derived from that registration, and leave external files untouched. | Accepted because it corrects wrong setup state without mutating user files. |

## Selected Approach

The prelaunch document reader treats `application/pdf` and `.pdf` as supported when the PDF has an extractable text layer or can use bounded host-local PDF OCR fallback. The reader loads bytes in memory, extracts page text with pypdf when possible, and then reuses the existing deterministic signal detection, redaction, finding, metric, and audit flow. Text-layer extraction can attach estimated PDF user-space page regions from scan-time text matrices so authorized review surfaces can later focus a redacted finding on the page. When a PDF has blank/scanned pages or text-layer pages that also contain embedded images, the scanner keeps the text-layer page records and OCRs the bounded target pages within the existing OCR page budget, returning `pdf_mixed` and `pdf_text_layer_with_page_ocr` when OCR adds text. If mixed-page OCR cannot run, the scanner preserves the usable text-layer result, marks the document hard, and reports a recoverable OCR-deferred warning instead of silently treating the visual layer as scanned. Text-layer-missing PDFs may be rasterized in a temporary directory and OCRed locally with Tesseract TSV output when `DATASENTINEL_OCR_MODE=local`, `pdftoppm`, and Tesseract are available; OCR word boxes can attach pixel page regions to redacted anchors. Local image OCR may run bounded color-overlay preprocessing variants and bounded multilingual language profiles to improve recall for high-contrast text over busy images. Raw source bytes, page images, raw OCR text, and raw extracted text remain transient.

The source API exposes `DELETE /api/sources/{sourceId}`. The route deletes the DataSentinel source registration from the active store, clears scan/finding state derived from that source registration, and returns the deleted source envelope. Missing source ids return `application/problem+json` with `404`.

## State Machine

```text
source_registered -> connection_checking
connection_checking -> connected
connected -> scan_requested
scan_requested -> extracting_text
extracting_text -> detecting_signals
extracting_text -> pdf_ocr_requested
extracting_text -> mixed_pdf_page_ocr_requested
pdf_ocr_requested -> detecting_signals
mixed_pdf_page_ocr_requested -> detecting_signals
mixed_pdf_page_ocr_requested -> detecting_signals_without_blank_page_ocr
pdf_ocr_requested -> ocr_deferred
detecting_signals -> completed

source_registered -> delete_requested
connected -> delete_requested
delete_requested -> registration_deleted
delete_requested -> delete_rejected_not_found
```

Guards:

- PDF extraction is allowed only for files under the prelaunch bounded document byte limit.
- PDFs prefer extractable text; blank/scanned pages and image-bearing pages inside an otherwise text-layer PDF may use bounded local page OCR when host tooling is available. If mixed-page OCR is unavailable, the scanner still returns the extractable text-layer result and records a hard/OCR-deferred warning rather than failing the whole PDF or hiding the skipped visual layer.
- Image-only PDFs may use bounded local OCR when host tooling is available, otherwise they stay OCR-deferred.
- Source deletion targets a single source id and does not call provider delete APIs or remove filesystem paths.

Side effects:

- PDF source bodies and extracted text exist only in scan process memory.
- PDF text-layer and PDF OCR region metadata may be attached to redacted evidence anchors, but raw text, raw OCR text, and page images are not persisted.
- Mixed PDF page OCR may attach text-layer and OCR page metadata in the same extracted document, with per-page formats preserved in redacted anchors.
- Findings persist redacted evidence and metadata only.
- Source deletion removes the source registration row from DataSentinel state and clears derived scan/finding workflow state for that source.

Failure paths:

- Missing PDF extraction or local OCR tooling reports an unsupported or OCR-deferred warning.
- Mixed PDFs with usable text layers but unavailable page OCR report an OCR-deferred warning while preserving the text-layer findings.
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
- Deployment: API runtime must install the PDF extraction dependency from `requirements.txt`; hosts that need image-only PDF OCR also need `pdftoppm`, Tesseract, and matching language packs.
- Security/privacy: no external OCR, no raw PDF persistence, no page-image persistence, no provider token storage, no source-file deletion.

## Primitive Acceptance Criteria

- A PDF with an extractable text layer can be scanned from an approved source and produce redacted findings when deterministic rules match.
- PDF text-layer findings can include estimated page-region coordinates without exposing raw PDF text or page images.
- A mixed PDF can combine text-layer pages with OCR-derived blank/scanned or image-bearing pages and produce `pdf_mixed` redacted findings with per-page anchors when host tooling is available.
- A mixed PDF whose page OCR is unavailable still returns text-layer evidence, increments OCR-deferred warning metadata, and does not create fake OCR findings.
- A PDF or image with colored text overlays can use local OCR preprocessing variants and still expose only redacted evidence, not raw OCR text or page images.
- A PDF without an extractable text layer can produce redacted findings through bounded local OCR when host tooling is available.
- PDF OCR findings can include OCR pixel page-region coordinates from Tesseract TSV word boxes without exposing raw OCR text or page images.
- Public API and UI payloads do not expose raw PDF text, raw PDF bytes, provider tokens, or source credentials.
- An image-only, unreadable, or OCR-tooling-missing PDF is reported as unsupported/OCR-deferred rather than silently succeeding.
- A source registration can be deleted from DataSentinel, is absent from the next source list, and no stale scan/finding state remains for that deleted registration.
- Deleting a source registration does not delete or mutate Google Drive files, direct-link files, or host-mounted files.
- Repeating deletion for the same source id returns a not-found problem response.
