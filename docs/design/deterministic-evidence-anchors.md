# Deterministic Evidence Anchors

## Problem Definition

Reviewers need to inspect where a deterministic signal came from without receiving raw sensitive values in list, detail, audit, or metric payloads. The same finding detail interaction should support text files, PDF text layers, OCR-derived text, tables, ZIP archive members, and future structured document renderers without creating format-specific user workflows.

The first P0 anchor primitive is a redacted `textPosition` selector over the normalized extracted text stream used by deterministic detection. It is not a claim that every source format is visually renderable yet. It is the minimal source-data-derived location record needed to make later one-click open-and-focus review behavior consistent.

## Research Basis

- The W3C Web Annotation Data Model defines text position selectors as zero-based character ranges with start included and end excluded, and warns that position selectors are brittle if the source representation changes. DataSentinel follows the same range semantics for `textPosition` but keeps a smaller internal JSON shape rather than adopting the full JSON-LD annotation model.
- Because position selectors can drift after source changes, DataSentinel anchors are tied to the scan-time extracted representation and include a redacted fallback label for unsupported or stale renderers.
- pypdf text extraction supports visitor callbacks that receive the text fragment, user matrix, text matrix, font dictionary, and font size. Its documentation recommends using transformation matrices for positions but warns that coordinates can be wrong in complicated PDFs, so DataSentinel marks scan-time PDF regions as estimated.
- Tesseract command-line OCR supports TSV output with page, block, paragraph, line, word, pixel bounding box, confidence, and text columns. DataSentinel uses the TSV geometry to derive redacted OCR word-box regions while keeping raw OCR text internal to scan-time detection.

References: <https://www.w3.org/TR/annotation-model/>, <https://pypdf.readthedocs.io/en/4.2.0/user/extract-text.html#using-a-visitor>, <https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html#tsv-output>

## Options Compared

| Option | Decision | Reason |
| --- | --- | --- |
| Raw quote or adjacent context | Rejected | It would expose matched personal data or nearby source content in public payloads. |
| Redacted text-position selector | Chosen for P0 | It gives deterministic review focus over extracted text while preserving the no-raw-content boundary. |
| Full W3C annotation JSON-LD | Deferred | The complete model is larger than the current contract needs and would add integration complexity before renderers exist. |
| Format-specific viewer URLs | Rejected for P0 | It would fragment the review interaction and can expose raw host paths or provider URLs. |
| PDF/image page-region selectors | Chosen incrementally | PDF text-layer coordinates and OCR TSV word boxes make source-data-derived visual focus possible while keeping raw content out of public payloads. |
| XML structure-path selectors | Chosen incrementally | XML element and attribute ordinals give reviewers a source-data-derived focus target for nested XML payloads without exposing raw XML values or raw element and attribute names in selector metadata. |
| JSON/JSONL/NDJSON structure-path selectors | Chosen incrementally | JSON record and field ordinals give reviewers a source-data-derived focus target for nested structured payloads without exposing raw JSON values or raw property names in selector metadata. |
| ZIP member wrapper selectors | Chosen incrementally | ZIP member ordinals preserve the source container context for child selectors without exposing raw archive member names or recursively expanding nested archives. |

## Anchor Shape

Finding signals may include:

```json
{
  "evidenceAnchor": {
    "anchorId": "anchor_0123abcd",
    "format": "text",
    "label": "Email",
    "redactedText": "Email: [REDACTED_EMAIL]",
    "selector": {
      "type": "textPosition",
      "start": 12,
      "end": 30,
      "page": 2,
      "sourceStart": 4,
      "sourceEnd": 22,
      "pageRegion": { "x": 72, "y": 640, "width": 120, "height": 12, "unit": "pt", "origin": "bottom_left", "confidence": "estimated" }
    },
    "fallback": { "label": "Page 2", "redactedText": "Email: [REDACTED_EMAIL]" },
    "rawContentExposed": false
  }
}
```

Rules:

- `selector.start` and `selector.end` are offsets in the normalized extracted text stream for the scan, with `start` inclusive and `end` exclusive.
- `selector.sourceStart` and `selector.sourceEnd` are optional source-local refinements for the extracted representation segment that contained the match. Text-like, XML, RTF, EML, Office Open XML, OpenDocument, image OCR, video transcript, video frame OCR, PDF text-layer, and bounded PDF OCR extraction can use them while preserving the global text-position selector.
- OpenDocument extraction reuses existing public-safe selector shapes: ODS cells use `tableCell`, while ODT and ODP paragraphs use `structurePath` over `content.xml` ordinal metadata.
- EML extraction reuses `structurePath` selectors over ordinal header and body-part metadata and does not expose raw header values, raw body text, or attachment filenames.
- ZIP extraction wraps child selectors with `containerType = "zip"`, `memberIndex`, and ordinal `memberPath` metadata. It does not expose raw member names, raw archive paths, or nested archive contents in public selectors.
- XML structure-path selectors may include `elementIndex` and `attributeIndex`. Their `path` uses ordinal segments such as `/element[1]/element[2]/attribute[1]` rather than raw tag or attribute names so the selector remains public-safe.
- JSON, JSONL, and NDJSON structure-path selectors may include `recordIndex`, `lineNumber`, and `fieldIndex`. Their `path` uses ordinal segments such as `/record[1]/field[2]` rather than raw property names so the selector remains public-safe.
- `selector.page` is an optional PDF page refinement when scan-time page metadata is available.
- `selector.pageRegion` is an optional page-like region refinement. PDF text-layer regions use PDF user-space points with bottom-left origin and estimated confidence. OCR image and PDF-raster regions use image pixels with top-left origin and OCR confidence when available. Both are source-data-derived and keep the redacted fallback path.
- `redactedText` and `fallback.redactedText` must be derived from the public redacted snippet, not from raw source text.
- `anchorId` is stable for the signal type, detector, and source offsets within one extracted representation.
- Clients must treat `evidenceAnchor` as optional and use `fallback` when the selector type is unsupported.

## State Machine

| State | Event | Guard | Transition | Side Effects |
| --- | --- | --- | --- | --- |
| `no_anchor_candidate` | Detector emits a match | Match has source offsets in the extracted text stream | `anchor_building` | Capture signal type, detector, start, end, and fallback line number in memory. |
| `anchor_building` | Anchor is created | Start and end are non-negative and end is not before start | `anchor_sanitized` | Generate stable `anchorId`; write only redacted text into anchor fields. |
| `anchor_sanitized` | Scan-time source text metadata is available | Match range is contained in one source text segment | `anchor_sanitized` | Add source-local offsets and a fallback label without adding raw text. |
| `anchor_sanitized` | Scan-time XML structure metadata is available | Match range is contained in one parsed XML scalar value | `anchor_sanitized` | Add XML element/attribute ordinal metadata without adding raw XML values or raw tag/attribute names. |
| `anchor_sanitized` | Scan-time JSON structure metadata is available | Match range is contained in one parsed scalar value | `anchor_sanitized` | Add JSON record/field ordinal metadata without adding raw JSON values or raw property names. |
| `anchor_sanitized` | Scan-time page metadata is available | Match range is contained in one page text segment | `anchor_sanitized` | Add page number, page-local source offsets, and page fallback label without adding raw text. |
| `anchor_sanitized` | Scan-time PDF text coordinates are available | Match range overlaps one or more text-layer fragments | `anchor_sanitized` | Add an estimated page-region union without adding raw PDF text or page images. |
| `anchor_sanitized` | Scan-time OCR word boxes are available | Match range overlaps one or more OCR words | `anchor_sanitized` | Add an OCR page-region union without adding raw OCR text or page images. |
| `anchor_building` | Anchor cannot be created | Offset data is missing or invalid | `fallback_only` | Emit the redacted signal without a selector, or with only safe fallback metadata when available. |
| `anchor_sanitized` | Public payload is serialized | Anchor text contains no raw matched value | `anchor_exposed` | Return optional `evidenceAnchor` on the signal. |
| `anchor_sanitized` | Persisted signal has stale raw anchor text | Public sanitizer runs | `anchor_exposed` | Replace anchor text fields with the sanitized redacted snippet while preserving selector and fallback labels. |
| `anchor_exposed` | Authorized reviewer opens evidence | Renderer supports selector type for the scan representation | `focus_resolved` | Focus the matched location without changing source files or review state. |
| `anchor_exposed` | Authorized reviewer opens evidence | Renderer does not support selector type | `fallback_displayed` | Show fallback label and redacted text only. |
| `focus_resolved` or `fallback_displayed` | Reviewer closes preview | Always | `anchor_exposed` | No scan, finding, source, or audit mutation. |

Failure and rollback paths:

- If a renderer cannot resolve an anchor, it must show the redacted fallback rather than hiding the finding.
- If a future anchor type leaks raw source content, remove that optional field and continue rendering redacted snippets; compatibility rules require clients to tolerate missing optional fields.
- If offset generation becomes unreliable for a format, that extractor can emit fallback-only signals until the renderer-specific anchor is repaired.

## Impact Surface

- Backend deterministic detection adds optional `evidenceAnchor` objects to signal payloads.
- Text-like, XML, JSON-like, RTF, EML, ZIP, Office Open XML, OpenDocument, image OCR, video transcript, and video frame OCR extraction attach source text segments so signal anchors can gain source-local fallback context.
- PDF text-layer and bounded PDF OCR extraction attach page text segments so signal anchors can gain page-aware fallback context.
- PDF text-layer extraction can attach estimated text-fragment regions derived from scan-time PDF matrices; image OCR and bounded PDF OCR can attach pixel word-box regions derived from scan-time Tesseract TSV output.
- Public sanitization redacts persisted or restored anchor text before exposure.
- The finding-review schema and finding detail mock document the optional anchor field.
- File review UI remains a single open-and-focus interaction. It can render source-derived PDF and OCR regions as a redacted normalized focus box, while richer format-native renderers remain future work.
- No source body, raw extracted text, page image, provider token, file mutation, review mutation, or deletion path is introduced.

## Primitive Acceptance Criteria

- A detected label signal has a `textPosition` selector whose start/end offsets point to the raw matched value in the normalized extracted text stream.
- A detected regex signal has a `textPosition` selector whose start/end offsets point to the regex match.
- A PDF text-layer signal whose match is contained in one scan-time page segment includes `format = pdf_text_layer`, page number, page-local source offsets, and a redacted page fallback label.
- A PDF text-layer signal whose match overlaps scan-time text-fragment coordinates may include `pageRegion` with PDF user-space coordinates, unit, origin, and estimated confidence, without exposing raw text.
- An image OCR or PDF OCR signal whose match overlaps scan-time OCR word boxes may include `pageRegion` with pixel coordinates, top-left origin, OCR confidence when available, and no raw OCR text.
- A reviewer opening a signal with `pageRegion` sees one normalized visual focus box whether the source region came from PDF bottom-left coordinates or OCR top-left pixels.
- A CSV, TSV, XLSX, or ODS signal whose match is contained in one parsed cell includes a `tableCell` selector with source-derived row, column, column label, sheet metadata when available, source-local offsets, and no raw cell value.
- An XML signal whose match is contained in one parsed element text or attribute value includes a `structurePath` selector with source-derived element and attribute ordinal metadata, source-local offsets, and no raw XML value, element name, or attribute name.
- A JSON, JSONL, or NDJSON signal whose match is contained in one parsed scalar value includes a `structurePath` selector with source-derived record and field ordinal metadata, source-local offsets, and no raw JSON value or raw property name.
- A DOCX, PPTX, ODT, ODP, EML, or HTML signal whose match is contained in one parsed block includes a `structurePath` selector with source-derived paragraph, slide/shape, OpenDocument paragraph, email header/body-part, or HTML node metadata, source-local offsets, and no raw document text.
- A ZIP member signal wraps the child selector with ordinal member metadata and does not expose raw archive member names or raw member paths.
- A text-like, XML, JSON-like, RTF, EML, ZIP, Office Open XML, OpenDocument, image OCR, video transcript, or video frame OCR signal whose match is contained in one scan-time extracted text segment includes the segment format, source-local offsets, and a redacted fallback label.
- Serialized public signal payloads contain redaction markers and selector metadata but not raw matched values.
- Restored persisted signals with stale raw anchor text are sanitized before public response.
- Evidence cards continue to render when `evidenceAnchor` is absent, unsupported, or fallback-only.
- Closing or opening evidence focus does not mutate source files, scan state, finding state, review state, or audit state.
