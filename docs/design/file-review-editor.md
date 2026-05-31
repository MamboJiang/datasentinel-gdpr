# File Review Editor

## Problem Definition

Finding Detail currently shows redacted detector evidence but does not let a reviewer inspect where the evidence appears inside the source file. Reviewers need a file review surface that opens a file preview, lands on the relevant evidence, and shows why the finding was flagged without exposing raw sensitive values or changing the source file.

## Research Basis

- W3C Web Annotation Data Model defines selectors for resource fragments, text quotes, text positions, data positions, CSS, XPath, and SVG regions. This supports a format-neutral evidence target model before choosing a viewer implementation. Source: `https://www.w3.org/TR/annotation-model/`.
- ECMA-376 defines Office Open XML document representation for Word, Excel, and PowerPoint files. Office anchors should reference stable document structures such as paragraph, run, sheet, row, or cell locations rather than browser-only pixel coordinates. Source: `https://ecma-international.org/publications-and-standards/standards/ecma-376/`.
- OASIS OpenDocument Format 1.3 defines XML-based office documents for text, spreadsheets, and presentations. ODF anchors should reference `content.xml` paragraphs or spreadsheet cells without exposing raw table names or values. Source: `https://www.oasis-open.org/standard/odf-v1-3-cs01/`.
- IETF RFC 5322 and RFC 2045 define Internet message and MIME body structure. Email anchors should reference ordinal headers and body parts rather than raw header values, body text, or attachment names. Sources: `https://datatracker.ietf.org/doc/html/rfc5322`, `https://www.rfc-editor.org/rfc/rfc2045.html`.
- W3C CSV on the Web defines tabular data and metadata concepts for rows, columns, and cells. Spreadsheet and CSV anchors should use sheet/table coordinates plus optional text selectors. Source: `https://www.w3.org/TR/tabular-data-primer/`.

## Options

| Option | Description | Tradeoff | Decision |
| --- | --- | --- | --- |
| Viewer-specific coordinates only | Store PDF page coordinates or DOM positions directly. | Fast for one viewer, brittle across formats and renderer changes. | Rejected |
| Raw source text viewer | Render extracted text and highlight raw evidence. | Easy to implement, violates minimization requirements for sensitive values. | Rejected |
| Format-neutral evidence anchors | Normalize evidence to a small anchor model, then let each viewer resolve supported selectors. | Requires a translation layer, but keeps UI and review workflow stable. | Accepted |

## Anchor Model

The review editor should treat each sensitive signal as an evidence anchor with:

- `anchorId`: stable UI key.
- `format`: `pdf`, `zip`, `docx`, `xlsx`, `odt`, `ods`, `odp`, `eml`, `csv`, `txt`, or `unknown`.
- `label`: human-readable evidence type.
- `redactedText`: masked evidence text only.
- `selector`: one of the primitive selectors below.
- `fallback`: a redacted text quote or page/line label when precise positioning is unavailable.

Primitive selectors:

| Selector | Use |
| --- | --- |
| `pageRegion` | PDF/image-like pages. Use page number plus source-derived coordinates, such as estimated PDF user-space points or OCR pixel word boxes. |
| `textQuote` | Word, PDF text layer, HTML, plain text. Use masked quote plus surrounding redacted context. |
| `textPosition` | Plain text or extracted text stream. Use start/end offsets when stable. |
| `tableCell` | CSV/XLSX/ODS. Use sheet/table, row, column, and optional cell text selector. |
| `structurePath` | DOCX/PPTX/ODT/ODP/EML/HTML and supported ZIP child documents. Use paragraph, run, slide, shape, email part, XPath-like path, or semantic block ID. |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Detail visible | Open file requested | Finding has at least one signal | Editor open | Select first evidence anchor |
| Detail visible | Open file requested | Finding has no signal | Editor open empty | Show no-evidence state |
| Editor open | Evidence anchor selected | Anchor has supported selector | Evidence focused | Scroll preview and highlight matching redacted region |
| Editor open | Evidence anchor selected | Selector unsupported | Fallback focused | Show redacted fallback location |
| Editor open | Close requested | Always | Detail visible | Clear active editor state |
| Editor open | Review decision requested | Review action available | Review dialog open | Preserve selected evidence context visually |

## Format Mapping

| Format | Primary locator | Highlight strategy | Fallback |
| --- | --- | --- | --- |
| PDF | Page number plus estimated page region, OCR page-image region, or text position in PDF text layer. | Overlay highlight on rendered page when a renderer supports the selector. | Page number with redacted snippet. |
| Image OCR | OCR pixel region or source-local OCR text position. | Overlay highlight on rendered image when a renderer supports the selector. | Image OCR label with redacted snippet. |
| DOCX | Paragraph/run path or text quote from extracted document model. | Highlight paragraph block in generated preview. | Section heading plus redacted quote. |
| ODT/ODP | `content.xml` paragraph path or text quote from the extracted OpenDocument model. | Highlight paragraph block in generated preview. | Paragraph label plus redacted quote. |
| XLSX/CSV | Sheet/table, row, column, cell range. | Highlight cell or row in grid preview. | Row/column label plus redacted quote. |
| ODS | Sheet/table, row, column, cell range. | Highlight cell or row in grid preview. | Row/column label plus redacted quote. |
| EML | Header/body-part ordinal path plus optional redacted text position in the extracted email view. | Highlight the email header or body part in generated preview. | Header or body-part label plus redacted quote. |
| ZIP | Ordinal member metadata plus the child selector for supported member content. | Show archive member context and then focus the child selector when supported. | Member ordinal plus redacted quote. |
| TXT/Markdown | Text position or line number plus quote. | Highlight line and masked phrase. | Line number plus redacted quote. |
| Unknown | Redacted quote only. | Evidence list focus. | File metadata and signal card. |

## Source-Data Anchor Contract

Backend signal payloads may include explicit `evidenceAnchor` objects. Each anchor should depend only on stable data derived from the source file, not on a particular browser viewer implementation.

- PDF text-layer sources currently use page number plus page-local text offsets and may include estimated PDF user-space page regions derived from scan-time text matrices. Image OCR and bounded PDF OCR may include pixel regions derived from scan-time Tesseract TSV word boxes. The editor normalizes bottom-left PDF regions and top-left OCR regions into one redacted focus box. Future renderer-backed sources may add normalized region percentages that the UI can scale to any viewer size.
- Plain text, Markdown, logs, and extracted text streams use text-position offsets plus optional redacted text quotes.
- CSV, XLSX, and ODS sources use table, sheet, row, column, and optional cell text selectors.
- ZIP archives use ordinal member metadata and then delegate to the child member selector; public selectors must not show raw member names.
- DOCX, PPTX, ODT, ODP, EML, and HTML sources use structure paths plus optional redacted text quotes.
- Source review previews may include redacted context windows around each signal span. The backend redacts the target span and overlapping known signal spans before the preview is persisted; the UI highlights only the redacted marker inside that context window.
- Unsupported precise selectors fall back to the same evidence list and redacted location label, so the reviewer interaction remains one open-and-focus flow across formats.
- File review entry points depend on current finding review authority from review-support permission-boundary data or workspace-level `review_findings` authority. View-only actors see disabled entry points and the boundary reason instead of a hidden control or silent access.

## Impact Surface

- Finding Detail adds an editor overlay using current finding signals and optional `signal.evidenceAnchor` data.
- The contract keeps anchors optional so existing clients and mock consumers can continue to render redacted snippets only.
- Unsupported selector types resolve to the same redacted fallback interaction.
- Future renderer work may add more selector types without changing the user-facing open-and-focus workflow.

## Rollback Path

Remove the editor button, editor component, and CSS. Existing Finding Detail redacted evidence cards remain unchanged because the editor reads current mock fields without altering the response contract.

## Primitive Acceptance Criteria

- A reviewer with finding review authority, or a workspace actor with `review_findings` authority, can open a file review surface from Finding Detail.
- A view-only actor cannot open file review and sees the current permission-boundary reason.
- The editor selects the first sensitive signal by default.
- Selecting another redacted signal changes the highlighted preview region.
- PDF and OCR page regions render through one scalable redacted focus box without exposing source content.
- TXT/PDF/CSV/image OCR anchors can show a redacted source-context window that preserves nearby labels and masks detected values without exposing raw source text.
- ZIP member anchors show public-safe member context before resolving supported child selectors and do not expose raw member names.
- The preview never displays raw sensitive values.
- Unsupported or missing precise anchors still show a redacted fallback location.
- Closing the editor returns the reviewer to Finding Detail without changing scan, finding, or review state.
