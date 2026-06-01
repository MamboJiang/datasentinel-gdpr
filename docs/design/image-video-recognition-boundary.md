# Image and Video Recognition Boundary

## Problem Definition

Enterprise discovery sources include screenshots, scanned receipts, badge photos, access request screenshots, training screenshots, meeting captions, and recorded operational walkthroughs. Text-like files, email messages, ZIP archives, PDF text layers, Office Open XML extraction, and OpenDocument extraction do not cover those common media inputs. Prelaunch scanning needs a bounded image/video path that improves discovery without persisting raw media or silently sending sensitive source material to external AI services.

## Research Basis

- The Tesseract project documents an open-source OCR engine with a command-line `tesseract` program, so the prelaunch backend can invoke a local binary without adding a Python image-processing dependency or external OCR service.
- Tesseract command-line documentation describes direct image OCR, language selection, page segmentation modes, and TSV output with word bounding boxes for local OCR processing.
- Poppler `pdftoppm` documentation describes rendering PDF pages into image files, which provides a bounded local bridge from image-only PDFs to the existing Tesseract OCR path.
- FFmpeg official documentation covers command-line video processing, including bounded frame extraction with output image sequences. This supports a local raw-video frame OCR path without sending media to an external service.
- The WebVTT specification defines a standard text-track format for video captions, which makes subtitle files safe to treat as deterministic text inputs.
- The GDPR discovery strategy reference emphasizes company workflows such as expense, supplier, access, incident, and training material; those workflows commonly include screenshots, scans, captions, and recordings.

References: [Tesseract User Manual](https://tesseract-ocr.github.io/tessdoc/), [Tesseract Command-Line Usage](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [pdftoppm manpage](https://manpages.ubuntu.com/manpages/jammy/man1/pdftoppm.1.html), [FFmpeg Documentation](https://ffmpeg.org/documentation.html), [WebVTT specification](https://w3c.github.io/webvtt/).

## Options

| Option | Summary | Decision |
| --- | --- | --- |
| Keep images and videos unsupported | Users must transcribe or export media manually. | Rejected because screenshots and scans are common company records. |
| Local image OCR through Tesseract | Invoke a host-installed Tesseract CLI for image files during scan execution only. | Selected for prelaunch because it is local, deterministic, reversible, and avoids raw-media persistence. |
| Local PDF OCR fallback | Render image-only PDF pages locally and OCR the page images. | Selected as a bounded fallback after PDF text-layer extraction fails. |
| External cloud vision or multimodal AI | Send images or video frames to a third-party model. | Rejected for default prelaunch because it would expose raw source media and expand privacy/security scope. |
| Full local video processing now | Decode all frames and audio from raw video and run OCR/transcription. | Rejected for prelaunch because it is too expensive and expands raw-media handling. |
| Transcript-first video handling | Accept VTT/SRT transcript files, mark raw video media as hard/deferred. | Superseded by bounded frame OCR for raw video while keeping transcript support. |
| Bounded local video frame OCR | Extract at most four temporary frames through FFmpeg and OCR those frames through local Tesseract. | Selected because it closes the raw-video discovery gap while keeping cost, privacy, and runtime failure boundaries explicit. |

## Selected Approach

- Image files (`PNG`, `JPG/JPEG`, `TIFF`, `BMP`, `WEBP`) are scanned through local Tesseract when `LAWDIT_OCR_MODE=local` and the host binary is available. `LAWDIT_OCR_LANGS` may select installed Tesseract language packs for multilingual OCR; large configured language lists are split into bounded profiles so one slow/noisy all-language invocation cannot hide OCR output.
- PDF files are scanned through the text layer first. If no text layer is available, the scanner may rasterize a bounded page range through host-local `pdftoppm` and run the same local Tesseract OCR path. If a PDF has both text-layer pages and blank/scanned or image-bearing pages, bounded page OCR is attempted and the resulting document is reported as `pdf_mixed` when OCR adds text.
- OCR capability reporting records mode, configured languages, Tesseract availability, `pdftoppm` availability, image OCR availability, and PDF OCR availability so deferred cases are explainable without reading source content.
- Image OCR output is treated as extracted text only inside scan execution. Public payloads keep redacted evidence, source-local offsets, and optional pixel word-box metadata, not raw OCR text or raw images.
- Image OCR normalizes Tesseract TSV word joins for CJK/Kana/Hangul character-level output, so words split as single characters can still feed deterministic multilingual label detection while retaining word-box regions for redacted anchors.
- OCR timeouts for one candidate or language profile do not stop other bounded OCR candidates from running. Missing PDF rasterization or mixed-page OCR tooling is a recoverable hard/OCR-deferred warning, not a silent success.
- Subtitle files (`VTT`, `SRT`) are cleaned into deterministic text and scanned as video transcript inputs.
- Raw video files (`MP4`, `MOV`, `M4V`, `MKV`, `WEBM`, `AVI`) under the bounded video size limit are sampled into temporary PNG frames through host-local FFmpeg and OCR'd through the same local Tesseract path.
- Video frame OCR output is treated as scan-time extracted text only. Public payloads can include redacted frame-local labels, source offsets, and pixel word-box metadata, not raw frames, raw video, raw OCR text, or audio.
- Missing FFmpeg, missing Tesseract, disabled local OCR, FFmpeg failure, OCR timeout, empty OCR output, or over-limit video is a recoverable hard/OCR-deferred warning, not a silent success.
- Normal deterministic scans still report `aiAssistanceUsed = false` and `modelCalls = 0`.

## State Machine

| State | Event | Guard | Next state | Side effect |
| --- | --- | --- | --- | --- |
| Candidate file | Suffix or MIME recognized as image | File is within prelaunch size limit and local OCR is enabled | OCR requested | Write bytes to a temporary local file and invoke Tesseract. |
| OCR requested | OCR succeeds with text | Text is non-empty | Text extracted | Scan redacted text candidates; discard temporary file. |
| OCR requested | OCR succeeds with TSV word boxes | Boxes overlap a redacted signal range | Anchor region available | Attach pixel `pageRegion` metadata to the redacted anchor without storing raw OCR text. |
| OCR requested | OCR succeeds with CJK/Kana/Hangul character-level TSV words | Known labels can be reconstructed in scan memory | Text extracted | Join compatible OCR tokens without synthetic spaces and scan the normalized text without storing raw OCR text. |
| OCR requested | One candidate or language profile times out | Another bounded candidate can still run | OCR requested | Record the failed candidate in process memory and continue without exposing raw OCR text. |
| OCR requested | OCR missing, timeout, failure, or empty text | Failure is recoverable | Completed with warning | Count file as hard/OCR-deferred and do not create fake findings. |
| Candidate PDF | Text layer missing | Local PDF rasterizer and OCR are available | PDF OCR requested | Render page images in a temporary directory and OCR them locally. |
| Candidate PDF | Some pages have text and some pages are blank/scanned | Local PDF rasterizer and OCR are available | Mixed PDF page OCR requested | Render only bounded blank/scanned pages in a temporary directory and merge OCR text with text-layer page records. |
| PDF OCR requested | Rasterization or OCR fails | Failure is recoverable | Completed with warning | Count file as hard/OCR-deferred and discard temporary files. |
| Mixed PDF page OCR requested | Rasterization or OCR fails | Existing text layer is usable | Text extracted with warning | Return the text-layer pages, record hard/OCR-deferred warning metadata, avoid fake OCR findings, and discard temporary files. |
| Candidate file | Suffix or MIME recognized as VTT/SRT | UTF-8 text can be read | Transcript extracted | Strip timing/cue markers and scan transcript text. |
| Candidate file | Suffix or MIME recognized as raw video | File is within the bounded video size limit and FFmpeg plus local OCR are available | Video frame OCR requested | Write bytes to a temporary local file and extract up to four temporary frames. |
| Video frame OCR requested | FFmpeg succeeds and at least one frame OCR produces text | Text is non-empty | Text extracted | Scan redacted text candidates with frame-local labels and pixel regions; discard temporary video and frame files. |
| Video frame OCR requested | FFmpeg missing, OCR missing, timeout, failure, or empty text | Failure is recoverable | Completed with warning | Count file as hard/OCR-deferred and do not create fake findings. |
| Candidate file | Unsupported or unsafe format | Recoverable | Completed with warning | Count file as unsupported. |

## Impact Surface

- Backend: format recognition, local/Drive/direct-link source scanning, OCR mode setting, extraction counts, warning counts, difficulty counts, and no-raw-content boundary.
- Test corpus: scan reports may record OCR capability state, but must not include raw images, page images, OCR text, or detected raw values.
- Frontend: Sources supported-file list and user-facing limitation text.
- Contracts and docs: prelaunch source input acceptance, difficulty definitions, security notes, and test cases.
- Deployment: hosts that should scan images need the `tesseract` binary installed. Hosts that should scan image-only PDFs need both `pdftoppm` and Tesseract installed with appropriate language data. Hosts that should scan raw video media need FFmpeg plus Tesseract. `LAWDIT_OCR_LANGS` should match installed Tesseract language packs.

## Rollback Path

Remove the media suffixes from `SUPPORTED_SUFFIXES`, remove the Tesseract and FFmpeg invocation modules, remove the transcript cleaner, and remove the Sources page/media acceptance bullets. Existing findings remain valid; future scans report those inputs as unsupported or OCR-deferred.

## Primitive Acceptance Criteria

- A supported image file can produce redacted findings through local OCR when OCR mode is local and Tesseract is installed or mocked in tests.
- A PDF with no extractable text layer can produce redacted findings through local PDF OCR when OCR mode is local and the host PDF rasterizer and Tesseract are available or mocked in tests.
- A mixed PDF with extractable text pages and blank/scanned pages can produce `pdf_mixed` redacted findings from bounded page OCR while preserving per-page text-layer and OCR anchors.
- Image OCR and PDF OCR findings can include pixel region anchors from Tesseract TSV word boxes without exposing raw OCR text or page images.
- CJK/Kana/Hangul image OCR labels split into character-level TSV words can still produce redacted findings and pixel region anchors.
- Large configured OCR language lists are split into bounded Tesseract profiles, and a timed-out profile does not prevent later profiles or preprocessing candidates from producing redacted findings.
- OCR failures, missing Tesseract, empty OCR, and OCR timeouts are recoverable hard/OCR-deferred warnings.
- Missing PDF rasterization tooling is a recoverable hard/OCR-deferred warning.
- A VTT or SRT transcript file can produce redacted findings without treating timing markers as evidence.
- A bounded raw video media file can produce redacted findings through host-local FFmpeg frame extraction and local Tesseract OCR.
- Missing FFmpeg, missing Tesseract, disabled local OCR, failed frame extraction, empty frame OCR, or over-limit video is a hard/OCR-deferred warning, not a silent success and not a fake finding.
- Public scan payloads expose counts, methods, formats, warnings, and redacted evidence only.
- Normal image/transcript scans keep `aiAssistanceUsed = false` and `modelCalls = 0`.
