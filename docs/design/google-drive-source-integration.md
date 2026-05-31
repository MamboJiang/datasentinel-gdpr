# Google Drive and Remote Link Source Integration

## Problem Definition

Prelaunch users need to scan real working files without uploading and storing raw files inside DataSentinel. The source setup flow must support two low-friction inputs:

- A user-selected Google Drive file or folder scope.
- A direct HTTPS link to one supported text-like file, PDF text layer, or Office Open XML file.

The implementation must read source content only during scan execution, produce redacted findings and audit evidence, and avoid long-term raw source-content storage.

## Research Basis

- Google Picker API is the official browser UI for selecting Drive files: https://developers.google.cn/workspace/drive/picker/guides/overview?hl=en
- Google Drive API documents file listing/search behavior for folder traversal and metadata filtering: https://developers.google.com/workspace/drive/api/guides/search-files
- Google Drive API documents binary download and Google Workspace document export behavior: https://developers.google.cn/workspace/drive/api/guides/manage-downloads?hl=en
- Google Drive API scope guidance distinguishes per-file access such as `drive.file` from broader read scopes such as `drive.readonly`: https://developers.google.com/workspace/drive/api/guides/api-specific-auth

## Options Considered

| Option | Summary | Decision |
| --- | --- | --- |
| Upload files into DataSentinel | User uploads files, backend stores them, scanner reads local copies. | Rejected for prelaunch because raw file storage increases privacy, retention, and deletion obligations. |
| Direct HTTPS file link | User registers one public HTTPS text-like or PDF text-layer file URL; backend fetches it only while scanning. | Accepted for single-file and export-link workflows with SSRF-style host checks and size/type limits. |
| Google Drive Picker plus per-scan token | Browser lets the user select files or a folder; backend receives selected metadata and a short-lived access token only when scan starts. | Accepted for Drive because it avoids storing provider tokens and raw content while supporting selected files and folders. |
| Server-side stored Drive refresh token | Backend stores refresh token and scans Drive later without user interaction. | Rejected for this slice because it expands credential storage, consent, revocation, and production connector scope. |

## Selected Approach

The frontend Source dialog exposes three registration modes:

- `remote_file_link`: stores `config.url` and scans one public HTTPS text-like file or PDF text layer.
- `google_drive_selection`: stores selected Drive item metadata in `config.items`; keeps the Google access token in browser memory and sends it only in `POST /api/scans/full` as `authorization.googleDriveAccessToken`.
- `local_repo`: keeps the existing allowed absolute path flow for controlled host-mounted sources.

The backend adds a temporary prelaunch document-reader boundary that converts supported source types into in-memory `SourceDocument` values. It does not persist raw file bodies or provider access tokens. Public payloads continue to expose only metadata, counts, redacted snippets, findings, metrics, and audit events.

## Source State Machine

```text
empty -> source_dialog_open
source_dialog_open -> source_registered
source_registered -> connection_checking
connection_checking -> connected
connection_checking -> rejected
connected -> scan_requested
scan_requested -> token_required
scan_requested -> inventorying_files
inventorying_files -> extracting_content
extracting_content -> detecting_signals
detecting_signals -> completed
detecting_signals -> failed
```

Guards:

- `remote_file_link` requires an HTTPS URL with no embedded credentials and a host that resolves to public addresses. Google Drive or Google Docs share pages are not direct file links and must use `google_drive_selection`.
- `google_drive_selection` requires configured Picker public credentials and selected Drive items before registration.
- Google Drive scan execution requires `authorization.googleDriveAccessToken`.
- Folder traversal stops at the prelaunch file limit.
- Text extraction accepts text-like MIME types, supported text-like file suffixes, PDF text layers, or exported Google Workspace documents.

Side effects:

- Source registration stores metadata and connector config only.
- Scan execution downloads or exports content into memory for the current process.
- Findings store redacted snippets and source metadata only.
- Audit events record scan/finding workflow events and do not include raw source content.

Failure paths:

- Missing Picker public config leaves Drive selection disabled and reports the missing host variables.
- Missing per-scan Drive token rejects scan start without changing scan, finding, audit, metric, or evaluation state.
- Unsupported file type, image-only or unreadable PDF, over-limit file size, download failure, or Drive API failure becomes a warning or command rejection before raw content is persisted.

Rollback path:

- Remove or unset `GOOGLE_PICKER_API_KEY` and `GOOGLE_CLOUD_PROJECT_NUMBER` to disable Drive selection without affecting existing account login.
- Remove the `remote_file_link` and `google_drive_selection` adapters from governance config to make those sources non-scan-ready.
- Revert the source dialog to local-path registration only; existing stored source rows remain metadata-only and can be ignored or deleted through normal state cleanup.

## Impact Surface

- Frontend: Source dialog, source scan readiness, runtime-only Drive access-token handoff.
- Backend: Source validation, source connection checks, prelaunch scan document reading, PDF text-layer extraction, Drive Picker public-config endpoint.
- Contracts: source config shapes, source-registration deletion route, per-scan authorization payload, Google Drive Picker config envelope.
- Deployment: host environment needs Google Picker public credentials for Drive selection and the PDF extraction dependency installed for the API runtime.
- Security/privacy: no raw source body storage, no provider token persistence, HTTPS/public-host guard for remote links, no real deletion.

## Primitive Acceptance Criteria

- A user can register a direct HTTPS file link and start a full scan that produces redacted findings when the file contains detectable signals.
- Direct-link scans reject non-HTTPS, credential-bearing, private-address, unreachable, over-limit, or unsupported files without storing raw content.
- PDF text-layer scans can produce redacted findings without storing raw PDF bodies or raw extracted text.
- DOCX, XLSX, and PPTX scans can produce redacted findings through the local deterministic extraction path documented in `docs/design/local-format-recognition-difficulty.md`.
- A user can select Google Drive files or one folder through Google Picker when host public credentials are configured.
- A Google Drive source stores selected item metadata but not the access token.
- A Google Drive full scan requires a short-lived access token in the scan request and rejects missing tokens without mutating workflow state.
- Google Drive folder scans enumerate descendant files up to the prelaunch limit and export Google Workspace documents to text-like content.
- A user can remove a source registration from DataSentinel state without deleting any external source file.
- Public API responses and UI surfaces show metadata, redacted evidence, findings, metrics, warnings, and audit state without raw file bodies, unredacted personal data, provider tokens, refresh tokens, client secrets, or deletion execution.
