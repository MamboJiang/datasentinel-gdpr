# Image and Video Recognition Boundary

## Problem Definition

Enterprise discovery sources include screenshots, scanned receipts, badge photos, access request screenshots, training screenshots, meeting captions, and recorded operational walkthroughs. Text-like files, PDF text layers, and Office Open XML extraction do not cover those common inputs. Prelaunch scanning needs a bounded image/video path that improves discovery without persisting raw media or silently sending sensitive source material to external AI services.

## Research Basis

- The Tesseract project documents an open-source OCR engine with a command-line `tesseract` program, so the prelaunch backend can invoke a local binary without adding a Python image-processing dependency or external OCR service.
- FFmpeg official documentation covers command-line video processing and is the future candidate for approved local key-frame extraction or audio-track extraction. Raw video decoding is not enabled in this slice.
- The WebVTT specification defines a standard text-track format for video captions, which makes subtitle files safe to treat as deterministic text inputs.
- The GDPR discovery strategy reference emphasizes company workflows such as expense, supplier, access, incident, and training material; those workflows commonly include screenshots, scans, captions, and recordings.

References: [Tesseract User Manual](https://tesseract-ocr.github.io/tessdoc/), [FFmpeg Documentation](https://ffmpeg.org/documentation.html), [WebVTT specification](https://w3c.github.io/webvtt/).

## Options

| Option | Summary | Decision |
| --- | --- | --- |
| Keep images and videos unsupported | Users must transcribe or export media manually. | Rejected because screenshots and scans are common company records. |
| Local image OCR through Tesseract | Invoke a host-installed Tesseract CLI for image files during scan execution only. | Selected for prelaunch because it is local, deterministic, reversible, and avoids raw-media persistence. |
| External cloud vision or multimodal AI | Send images or video frames to a third-party model. | Rejected for default prelaunch because it would expose raw source media and expand privacy/security scope. |
| Full local video processing now | Decode frames and audio from raw video and run OCR/transcription. | Deferred because it needs media budgets, sampling rules, error isolation, and larger test fixtures. |
| Transcript-first video handling | Accept VTT/SRT transcript files, mark raw video media as hard/deferred. | Selected because it gives immediate value for captions while preserving a clear media boundary. |

## Selected Approach

- Image files (`PNG`, `JPG/JPEG`, `TIFF`, `BMP`, `WEBP`) are scanned through local Tesseract when `DATASENTINEL_OCR_MODE=local` and the host binary is available.
- Image OCR output is treated as extracted text only inside scan execution. Public payloads keep redacted evidence and metadata, not raw OCR text or raw images.
- Subtitle files (`VTT`, `SRT`) are cleaned into deterministic text and scanned as video transcript inputs.
- Raw video files (`MP4`, `MOV`, `M4V`, `MKV`, `WEBM`, `AVI`) are recognized as company-relevant media but reported as hard/OCR-deferred until an approved video processor exists.
- Normal deterministic scans still report `aiAssistanceUsed = false` and `modelCalls = 0`.

## State Machine

| State | Event | Guard | Next state | Side effect |
| --- | --- | --- | --- | --- |
| Candidate file | Suffix or MIME recognized as image | File is within prelaunch size limit and local OCR is enabled | OCR requested | Write bytes to a temporary local file and invoke Tesseract. |
| OCR requested | OCR succeeds with text | Text is non-empty | Text extracted | Scan redacted text candidates; discard temporary file. |
| OCR requested | OCR missing, timeout, failure, or empty text | Failure is recoverable | Completed with warning | Count file as hard/OCR-deferred and do not create fake findings. |
| Candidate file | Suffix or MIME recognized as VTT/SRT | UTF-8 text can be read | Transcript extracted | Strip timing/cue markers and scan transcript text. |
| Candidate file | Suffix or MIME recognized as raw video | No approved media processor | Completed with warning | Count file as hard/OCR-deferred. |
| Candidate file | Unsupported or unsafe format | Recoverable | Completed with warning | Count file as unsupported. |

## Impact Surface

- Backend: format recognition, local/Drive/direct-link source scanning, OCR mode setting, extraction counts, warning counts, difficulty counts, and no-raw-content boundary.
- Frontend: Sources supported-file list and user-facing limitation text.
- Contracts and docs: prelaunch source input acceptance, difficulty definitions, security notes, and test cases.
- Deployment: hosts that should scan images need the `tesseract` binary installed. Future video media processing would require explicit FFmpeg enablement.

## Rollback Path

Remove the media suffixes from `SUPPORTED_SUFFIXES`, remove the Tesseract invocation module, remove the transcript cleaner, and remove the Sources page/media acceptance bullets. Existing findings remain valid; future scans report those inputs as unsupported or OCR-deferred.

## Primitive Acceptance Criteria

- A supported image file can produce redacted findings through local OCR when OCR mode is local and Tesseract is installed or mocked in tests.
- OCR failures, missing Tesseract, empty OCR, and OCR timeouts are recoverable hard/OCR-deferred warnings.
- A VTT or SRT transcript file can produce redacted findings without treating timing markers as evidence.
- A raw video media file is recognized as hard/OCR-deferred, not a silent success and not a fake finding.
- Public scan payloads expose counts, methods, formats, warnings, and redacted evidence only.
- Normal image/transcript scans keep `aiAssistanceUsed = false` and `modelCalls = 0`.
