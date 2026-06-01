# Local Format Recognition and Difficulty Grading

## Problem Definition

Prelaunch scans need to recognize more real business documents without turning normal scans into paid AI work. Text-like files must handle common Unicode encodings such as UTF-8 and UTF-16 through BOM or declared charset metadata; PDF text layers, bounded local PDF OCR fallback, RFC 5322/MIME email messages, bounded ZIP archive containers, bounded legacy Office conversion, and bounded raw video frame OCR are supported, and users also bring Office documents such as DOCX, XLSX, PPTX, DOC, XLS, PPT, ODT, ODS, and ODP. The scanner needs a deterministic, fast extraction path and a public difficulty summary that explains which formats were easy, moderate, hard, or unsupported without exposing raw source text. Image/video-specific recognition boundaries are documented separately in `docs/design/image-video-recognition-boundary.md`, legacy Office conversion is documented in `docs/design/legacy-office-conversion-boundary.md`, and archive-container boundaries are documented in `docs/design/archive-container-extraction.md`.

## Research Basis

- ECMA-376 defines Office Open XML vocabularies, document representation, and packaging: https://ecma-international.org/publications-and-standards/standards/ecma-376/
- Microsoft documents DOCX, XLSX, and PPTX as XML-based Open XML formats that use ZIP compression: https://support.microsoft.com/en-us/office/open-xml-formats-and-file-name-extensions-5200d93c-3449-4380-8e11-31ef14555b18
- OASIS publishes OpenDocument Format 1.3 as an XML-based office document standard, with package and schema parts for text, spreadsheet, and presentation content: https://www.oasis-open.org/standard/odf-v1-3-cs01/
- IETF RFC 5322 defines the Internet Message Format used by email message files: https://datatracker.ietf.org/doc/html/rfc5322
- IETF RFC 2045 defines MIME message bodies and content types used by multipart email: https://www.rfc-editor.org/rfc/rfc2045.html
- Python `email.parser` supports parsing RFC-style email messages from bytes with configurable policies: https://docs.python.org/3/library/email.parser.html
- Python `zipfile` supports reading ZIP archives and documents decompression resource-limit pitfalls: https://docs.python.org/3.11/library/zipfile.html
- Python `xml.etree.ElementTree` provides stdlib XML parsing APIs and parse-error behavior: https://docs.python.org/3.12/library/xml.etree.elementtree.html
- Python `codecs` documents Unicode codec names and BOM constants used for local UTF-8/UTF-16 text decoding: https://docs.python.org/3.12/library/codecs.html

## Options Considered

| Option | Summary | Decision |
| --- | --- | --- |
| Keep Office files unsupported | Continue asking users to export Office content manually. | Rejected because common prelaunch documents would remain invisible even when text is deterministic to extract. |
| Add a broad parser service | Use Tika or a persistent worker process for all file coverage. | Rejected for this slice because it adds runtime dependencies, slower startup, larger deployment risk, and a broader privacy surface. |
| Use OpenRouter for file extraction | Send source content or file text to AI when local extraction is missing. | Rejected for default scans because the requirement is no AI unless necessary and raw source content must not leave the process. |
| Deterministic OOXML text extraction | Read selected XML parts from DOCX/XLSX/PPTX ZIP packages in memory, then run the existing redaction detectors. | Accepted because it is fast, reversible, dependency-light, and keeps raw content transient. |
| Deterministic OpenDocument extraction | Read bounded `content.xml` text, spreadsheet cells, and presentation paragraphs from ODT/ODS/ODP packages in memory. | Accepted because common Drive/business exports use ODF and the selector model can reuse `structurePath` and `tableCell`. |
| Deterministic RFC 5322/MIME email extraction | Read selected headers and text/plain or text/html body parts from EML files while skipping attachments. | Accepted because emails are common business records and can reuse public-safe `structurePath` anchors without raw body persistence. |
| BOM/charset-aware Unicode text decoding | Decode text-like byte streams with an explicit charset or UTF BOM before deterministic detection. | Accepted because real exports often use UTF-16 and multilingual labels must not be lost before detection. |
| Bounded suffixless Unicode text sniffing | Decode no-extension files only when the MIME type is empty or octet-stream-like and the decoded stream has a text-like replacement/control-character profile. | Accepted because Drive and enterprise sources often include `.env`, `.gitignore`, and extensionless config or log files, while binary no-extension files must remain unsupported. |
| Header-aware delimited and Markdown table extraction | Treat standard CSV/TSV/Markdown header rows as label context for each data cell and sniff common CSV delimiters. | Accepted because common business exports and Markdown docs store names, birth dates, addresses, and phone numbers in columns rather than `Label,Value` rows, and those values need source-cell anchors. |

## Selected Approach

The prelaunch document reader recognizes:

- Easy: BOM/charset-aware Unicode text-like formats such as TXT, CSV, TSV, JSON, Markdown, LOG, XML, HTML/HTM, and bounded suffixless Unicode text.
- Moderate: PDF text layers, RFC 5322/MIME email messages (`.eml`), bounded ZIP archive containers (`.zip`), Office Open XML packages (`.docx`, `.xlsx`, `.pptx`), and OpenDocument packages (`.odt`, `.ods`, `.odp`) because they need structured parsing but not OCR or AI.
- Hard: files that need OCR or richer parsing, such as bounded PDF OCR fallback, image OCR, bounded raw video frame OCR, and OCR-deferred media.
- Unsupported: unsafe, unknown, over-limit, unreadable, encrypted, or missing required host-converter/tooling formats.

Text-like extraction uses only stdlib codec decoding and keeps source bytes transient. Delimited and Markdown table extraction preserves existing label-value rows and also treats standard header rows as label context for each data cell, so values such as names, birth dates, and addresses can be detected even when the value itself has no regex signature. `.csv` inputs sniff comma, semicolon, tab, and pipe delimiters before falling back to the default comma delimiter. Markdown inputs preserve ordinary text-position anchors and convert standard pipe tables into source-derived `tableCell` anchors. DOCX, XLSX, PPTX, ODT, ODS, ODP, ZIP, and EML extraction uses only stdlib parsers, never writes extracted files to disk, and reads only bounded package members, archive members, or email parts that can contain visible text. DOC, XLS, and PPT extraction writes source bytes and converted text only to a temporary directory and invokes host-local LibreOffice headless conversion. The scan output adds optional `contentExtraction.recognitionDifficulty`, `contentExtraction.formatCounts`, `contentExtraction.aiAssistanceUsed`, and `contentExtraction.modelCalls` fields. Normal deterministic scans must keep `aiAssistanceUsed = false` and `modelCalls = 0`.

## State Machine

```text
source_registered -> scan_requested
scan_requested -> format_identified
format_identified -> easy_text_extraction
format_identified -> moderate_structured_extraction
format_identified -> hard_pdf_ocr
format_identified -> hard_ocr_deferred
format_identified -> unsupported_rejected
easy_text_extraction -> deterministic_signal_detection
moderate_structured_extraction -> deterministic_signal_detection
hard_pdf_ocr -> deterministic_signal_detection
hard_ocr_deferred -> completed_with_warning
unsupported_rejected -> completed_with_warning
deterministic_signal_detection -> completed
```

Guards:

- Source bytes must stay under the prelaunch document-size limit before extraction.
- Text decoding may use a declared `charset` or UTF BOM; unsupported or malformed encodings fall back to replacement decoding rather than dropping bytes silently.
- CSV delimiter sniffing and header-row label context must not add raw cell values to public payloads; only redacted findings and source-derived `tableCell` selectors are allowed.
- Markdown table header-row label context must not add raw table values to public payloads; only redacted findings and source-derived `tableCell` selectors are allowed.
- OOXML and OpenDocument package member reads must stay under bounded uncompressed XML limits, ZIP member extraction must stay under bounded member-count and member-size limits, and email part extraction must stay under bounded part-count and text-size limits.
- No raw source text, raw Office XML, file body, provider token, or OpenRouter key may appear in public payloads.
- OpenRouter is not called by the deterministic extraction path.

Side effects:

- Raw bytes and extracted text exist only in scan memory.
- Public payloads store counts, methods, difficulty tiers, warnings, and redacted evidence only.
- Unsupported and hard/OCR-deferred files are recoverable warnings, not hidden successes.

Failure paths:

- Malformed ZIP archives, malformed XML, malformed email messages, missing OpenDocument `content.xml`, encrypted or unreadable package/archive parts, over-limit package members, OCR-tooling-missing image-only PDFs, FFmpeg/OCR-tooling-missing raw videos, and LibreOffice-missing or conversion-failed legacy Office files become warning-counted files.
- A failed file does not stop the rest of a local folder or Drive folder scan.
- A single direct-link file that is unsupported completes as a warning-only scan batch rather than producing fake findings.

## Impact Surface

- Backend: source document reader, local/remote/Drive extraction metadata, scan `contentExtraction` payloads, tests.
- Frontend: Sources supported-format list and Dashboard recognition-difficulty summary.
- Contracts: optional `contentExtraction` fields for difficulty and format counts.
- Documentation: source-input acceptance, API contract, technical scope, test cases.
- Security/privacy: no raw-source persistence, no AI call by default, bounded ZIP decompression.

## Rollback Path

Remove BOM/charset-aware decoding from the text decoder, remove `.docx`, `.xlsx`, `.pptx`, `.odt`, `.ods`, `.odp`, `.eml`, and `.zip` from the supported suffix set, and remove the optional difficulty UI. Existing findings and source registrations remain valid; future scans report those formats as unsupported until the extractor is re-enabled.

## Primitive Acceptance Criteria

- DOCX, XLSX, PPTX, DOC, XLS, PPT, ODT, ODS, ODP, EML, and ZIP files under the prelaunch size limit can be scanned from local, direct-link, or Google Drive selected sources.
- Deterministic detectors can find email, phone, IBAN-like patterns, and multilingual labels in extracted Office/OpenDocument/email/archive member text and return only redacted snippets.
- Public scan payloads include difficulty counts and per-format counts without raw source content.
- UTF-16 text-like files with a BOM or declared charset can produce multilingual redacted findings and source-local anchors without leaking raw values.
- Suffixless Unicode text files can produce redacted text-position findings, while suffixless binary files remain unsupported.
- Standard header-row CSV files and semicolon-delimited CSV files can produce label-context detections with redacted table-cell anchors.
- Standard Markdown table files can produce multilingual label-context detections with redacted table-cell anchors while non-table Markdown content keeps text-position anchors.
- Image-only PDFs use bounded local OCR when tooling is available; otherwise they are counted as hard/OCR-deferred warnings.
- Normal full and delta scans report zero model calls and do not use OpenRouter for local extraction.
- The Sources page lists the newly supported Office Open XML, OpenDocument, EML, and ZIP formats.
- Automated tests cover deterministic UTF-16 text-like decoding, suffixless text sniffing with binary rejection, DOCX/XLSX/PPTX, DOC/XLS/PPT, ODT/ODS/ODP, EML, and ZIP extraction, redaction, difficulty counts, and zero AI usage.
