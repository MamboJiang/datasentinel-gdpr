# Legacy Office Conversion Boundary

## Problem Definition

Business corpora may still include binary Microsoft Office files (`.doc`, `.xls`, `.ppt`). Modern OOXML and OpenDocument files are parsed directly, but the legacy binary formats need a bounded converter because ad hoc byte parsing would be brittle and could create false confidence.

## Research Basis

- LibreOffice documents `--headless` for running without a user interface and `--convert-to` with `--outdir` for command-line file conversion.
- LibreOffice examples include converting Office documents to text with `--convert-to "txt:Text (encoded):UTF8"`.
- The project security boundary requires source bytes to be used only during scan execution and not persisted into public payloads.

Reference: [LibreOffice command-line parameters](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html?DbPAR=DRAW%2F1000&System=UNIX).

## Options

| Option | Summary | Decision |
| --- | --- | --- |
| Keep legacy Office unsupported | Simple, but leaves a real enterprise corpus gap. | Rejected for final hardening. |
| Parse binary Office formats in project code | Avoids host tools, but adds high-risk binary parser complexity. | Rejected. |
| Use host-local LibreOffice headless conversion | Bounded, reversible, and keeps conversion local to the scan host. | Selected. |
| Use external document conversion service | Could improve fidelity, but sends source files outside the trust boundary. | Rejected. |

## Selected Approach

- Recognize `.doc`, `.xls`, and `.ppt` by suffix or legacy Microsoft Office MIME type.
- For files within the existing prelaunch document size limit, write bytes to a temporary directory, invoke host-local `soffice` or `libreoffice` in headless mode, convert to UTF-8 text, read the converted text, and delete the temporary directory.
- Use an isolated temporary LibreOffice user profile for each conversion to avoid state leakage from a GUI profile or prior conversion.
- Treat converted text as scan-time extracted text with redacted source-local anchors only.
- Missing LibreOffice, conversion timeout, failed conversion, missing output, or empty output is a recoverable hard unsupported warning, not a silent success.
- Public payloads must not expose raw binary Office bytes, converted raw text, private host paths, or raw detected values.

## State Machine

| State | Event | Guard | Next state | Side effect |
| --- | --- | --- | --- | --- |
| Candidate file | Suffix or MIME recognized as legacy Office | File is within prelaunch document size limit | Conversion requested | Write bytes to a temporary input file and create an isolated LibreOffice profile. |
| Conversion requested | LibreOffice conversion succeeds | Output text is non-empty | Text extracted | Scan deterministic signals and discard temporary input/output/profile files. |
| Conversion requested | LibreOffice missing, timeout, failure, missing output, or empty output | Failure is recoverable | Completed with warning | Count file as unsupported with hard difficulty; do not create fake findings. |
| Candidate file | File exceeds limit | Recoverable | Completed with warning | Count file as unsupported before conversion. |

## Impact Surface

- Backend format recognition and local/direct-link/Drive source scans.
- Source extraction metrics, warning text, and recognition difficulty counts.
- Frontend supported-file list and host-local dependency note.
- Server deployment package requirements.
- Redacted validation reports and corpus maintenance docs.

## Rollback Path

Remove the legacy Office suffixes and MIME types from format recognition, remove the LibreOffice converter module, remove the UI support chip, and revert acceptance/report bullets. Existing findings remain valid; future legacy Office scans become explicit unsupported warnings again.

## Primitive Acceptance Criteria

- A bounded `.doc`, `.xls`, or `.ppt` input can produce redacted findings through host-local LibreOffice conversion when the converter is installed or mocked.
- Missing converter, conversion failure, timeout, missing output, empty output, or over-limit input is reported as hard unsupported rather than a fake success.
- Converted text anchors remain source-local and redacted in public payloads.
- Temporary binary input, converted text output, and LibreOffice profile data are not persisted after scan execution.
- Automated tests cover mocked legacy Office extraction and real server-side converter execution when LibreOffice is installed.
