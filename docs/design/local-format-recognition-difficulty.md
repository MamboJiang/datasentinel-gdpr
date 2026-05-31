# Local Format Recognition and Difficulty Grading

## Problem Definition

Prelaunch scans need to recognize more real business documents without turning normal scans into paid AI work. Text-like files and PDF text layers are already supported, but users also bring Office documents such as DOCX, XLSX, and PPTX. The scanner needs a deterministic, fast extraction path and a public difficulty summary that explains which formats were easy, moderate, hard, or unsupported without exposing raw source text. Image and video-specific recognition boundaries are documented separately in `docs/design/image-video-recognition-boundary.md`.

## Research Basis

- ECMA-376 defines Office Open XML vocabularies, document representation, and packaging: https://ecma-international.org/publications-and-standards/standards/ecma-376/
- Microsoft documents DOCX, XLSX, and PPTX as XML-based Open XML formats that use ZIP compression: https://support.microsoft.com/en-us/office/open-xml-formats-and-file-name-extensions-5200d93c-3449-4380-8e11-31ef14555b18
- Python `zipfile` supports reading ZIP archives and documents decompression resource-limit pitfalls: https://docs.python.org/3.11/library/zipfile.html
- Python `xml.etree.ElementTree` provides stdlib XML parsing APIs and parse-error behavior: https://docs.python.org/3.12/library/xml.etree.elementtree.html

## Options Considered

| Option | Summary | Decision |
| --- | --- | --- |
| Keep Office files unsupported | Continue asking users to export Office content manually. | Rejected because common prelaunch documents would remain invisible even when text is deterministic to extract. |
| Add a heavy parser service | Use Tika, LibreOffice, or a worker process for broad file coverage. | Rejected for this slice because it adds runtime dependencies, slower startup, larger deployment risk, and a broader privacy surface. |
| Use OpenRouter for file extraction | Send source content or file text to AI when local extraction is missing. | Rejected for default scans because the requirement is no AI unless necessary and raw source content must not leave the process. |
| Deterministic OOXML text extraction | Read selected XML parts from DOCX/XLSX/PPTX ZIP packages in memory, then run the existing redaction detectors. | Accepted because it is fast, reversible, dependency-light, and keeps raw content transient. |

## Selected Approach

The prelaunch document reader recognizes:

- Easy: UTF-8 text-like formats such as TXT, CSV, TSV, JSON, Markdown, LOG, XML, and HTML.
- Moderate: PDF text layers and Office Open XML packages (`.docx`, `.xlsx`, `.pptx`) because they need structured parsing but not OCR or AI.
- Hard: files that appear to need OCR or richer parsing, such as image-only PDFs and raw video media.
- Unsupported: unsafe, unknown, over-limit, unreadable, encrypted, or legacy binary formats.

DOCX, XLSX, and PPTX extraction uses only stdlib ZIP and XML readers, never writes extracted files to disk, and reads only bounded package members that can contain visible text. The scan output adds optional `contentExtraction.recognitionDifficulty`, `contentExtraction.formatCounts`, `contentExtraction.aiAssistanceUsed`, and `contentExtraction.modelCalls` fields. Normal deterministic scans must keep `aiAssistanceUsed = false` and `modelCalls = 0`.

## State Machine

```text
source_registered -> scan_requested
scan_requested -> format_identified
format_identified -> easy_text_extraction
format_identified -> moderate_structured_extraction
format_identified -> hard_ocr_deferred
format_identified -> unsupported_rejected
easy_text_extraction -> deterministic_signal_detection
moderate_structured_extraction -> deterministic_signal_detection
hard_ocr_deferred -> completed_with_warning
unsupported_rejected -> completed_with_warning
deterministic_signal_detection -> completed
```

Guards:

- Source bytes must stay under the prelaunch document-size limit before extraction.
- OOXML package member reads must stay under bounded uncompressed XML limits.
- No raw source text, raw Office XML, file body, provider token, or OpenRouter key may appear in public payloads.
- OpenRouter is not called by the deterministic extraction path.

Side effects:

- Raw bytes and extracted text exist only in scan memory.
- Public payloads store counts, methods, difficulty tiers, warnings, and redacted evidence only.
- Unsupported and hard/OCR-deferred files are recoverable warnings, not hidden successes.

Failure paths:

- Invalid ZIP, malformed XML, encrypted or unreadable package parts, over-limit package members, image-only PDFs, and legacy binary Office files become warning-counted files.
- A failed file does not stop the rest of a local folder or Drive folder scan.
- A single direct-link file that is unsupported completes as a warning-only scan batch rather than producing fake findings.

## Impact Surface

- Backend: source document reader, local/remote/Drive extraction metadata, scan `contentExtraction` payloads, tests.
- Frontend: Sources supported-format list and Dashboard recognition-difficulty summary.
- Contracts: optional `contentExtraction` fields for difficulty and format counts.
- Documentation: source-input acceptance, API contract, technical scope, test cases.
- Security/privacy: no raw-source persistence, no AI call by default, bounded ZIP decompression.

## Rollback Path

Remove `.docx`, `.xlsx`, and `.pptx` from the supported suffix set and remove the optional difficulty UI. Existing findings and source registrations remain valid; future scans report those formats as unsupported until the extractor is re-enabled.

## Primitive Acceptance Criteria

- DOCX, XLSX, and PPTX files under the prelaunch size limit can be scanned from local, direct-link, or Google Drive selected sources.
- Deterministic detectors can find email, phone, and IBAN-like patterns in extracted Office text and return only redacted snippets.
- Public scan payloads include difficulty counts and per-format counts without raw source content.
- Image-only PDFs and unsupported formats are counted as hard/OCR-deferred or unsupported warnings.
- Normal full and delta scans report zero model calls and do not use OpenRouter for local extraction.
- The Sources page lists the newly supported Office Open XML formats.
- Automated tests cover deterministic DOCX/XLSX/PPTX extraction, redaction, difficulty counts, and zero AI usage.
