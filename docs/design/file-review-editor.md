# File Review Editor

## Problem Definition

Finding Detail currently shows redacted detector evidence but does not let a reviewer inspect where the evidence appears inside the source file. Reviewers need a file review surface that opens a file preview, lands on the relevant evidence, and shows why the finding was flagged without exposing raw sensitive values or changing the source file.

## Research Basis

- W3C Web Annotation Data Model defines selectors for resource fragments, text quotes, text positions, data positions, CSS, XPath, and SVG regions. This supports a format-neutral evidence target model before choosing a viewer implementation. Source: `https://www.w3.org/TR/annotation-model/`.
- ECMA-376 defines Office Open XML document representation for Word, Excel, and PowerPoint files. Office anchors should reference stable document structures such as paragraph, run, sheet, row, or cell locations rather than browser-only pixel coordinates. Source: `https://ecma-international.org/publications-and-standards/standards/ecma-376/`.
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
- `format`: `pdf`, `docx`, `xlsx`, `csv`, `txt`, or `unknown`.
- `label`: human-readable evidence type.
- `redactedText`: masked evidence text only.
- `selector`: one of the primitive selectors below.
- `fallback`: a redacted text quote or page/line label when precise positioning is unavailable.

Primitive selectors:

| Selector | Use |
| --- | --- |
| `pageRegion` | PDF/image-like pages. Use page number and normalized rectangle percentages. |
| `textQuote` | Word, PDF text layer, HTML, plain text. Use masked quote plus surrounding redacted context. |
| `textPosition` | Plain text or extracted text stream. Use start/end offsets when stable. |
| `tableCell` | CSV/XLSX. Use sheet/table, row, column, and optional cell text selector. |
| `structurePath` | DOCX/PPTX/HTML. Use paragraph, run, slide, shape, XPath-like path, or semantic block ID. |

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
| PDF | Page number plus normalized region, or text quote in PDF text layer. | Overlay highlight on rendered page. | Page number with redacted snippet. |
| DOCX | Paragraph/run path or text quote from extracted document model. | Highlight paragraph block in generated preview. | Section heading plus redacted quote. |
| XLSX/CSV | Sheet/table, row, column, cell range. | Highlight cell or row in grid preview. | Row/column label plus redacted quote. |
| TXT/Markdown | Text position or line number plus quote. | Highlight line and masked phrase. | Line number plus redacted quote. |
| Unknown | Redacted quote only. | Evidence list focus. | File metadata and signal card. |

## Impact Surface

- Frontend only for P0.
- Finding Detail adds an editor overlay using current mock finding signals.
- No contract field is required for the first UI slice; the UI derives fallback anchors from existing `signals.page` and `signals.snippet`.
- Future contract work may add explicit `evidenceAnchors` without breaking existing clients.

## Rollback Path

Remove the editor button, editor component, and CSS. Existing Finding Detail redacted evidence cards remain unchanged because the editor reads current mock fields without altering the response contract.

## Primitive Acceptance Criteria

- A reviewer can open a file review surface from Finding Detail.
- The editor selects the first sensitive signal by default.
- Selecting another redacted signal changes the highlighted preview region.
- The preview never displays raw sensitive values.
- Unsupported or missing precise anchors still show a redacted fallback location.
- Closing the editor returns the reviewer to Finding Detail without changing scan, finding, or review state.
