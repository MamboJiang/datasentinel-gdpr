# Google Drive and Remote Link Source Integration

## Problem Definition

Prelaunch users need to scan real working files without uploading and storing raw files inside lawdit. The source setup flow must support two low-friction inputs:

- A user-selected Google Drive file or folder scope.
- A direct HTTPS link to one supported text-like file, RFC 5322/MIME email file, bounded ZIP archive, PDF text layer or bounded local PDF OCR candidate, Office Open XML file, or OpenDocument file.

The implementation must read source content only during scan execution, produce redacted findings and audit evidence, and avoid long-term raw source-content storage.

## Research Basis

- Google Picker API is the official browser UI for selecting Drive files: https://developers.google.cn/workspace/drive/picker/guides/overview?hl=en
- Google Drive API documents file listing/search behavior for folder traversal and metadata filtering: https://developers.google.com/workspace/drive/api/guides/search-files
- Google Drive API documents binary download and Google Workspace document export behavior: https://developers.google.cn/workspace/drive/api/guides/manage-downloads?hl=en
- Google Drive API scope guidance distinguishes per-file access such as `drive.file` from broader read scopes such as `drive.readonly`: https://developers.google.com/workspace/drive/api/guides/api-specific-auth
- Google OAuth web-server applications can use `access_type=offline` to obtain refresh tokens for server-side access-token refresh: https://developers.google.com/identity/protocols/oauth2/web-server

## Options Considered

| Option | Summary | Decision |
| --- | --- | --- |
| Upload files into lawdit | User uploads files, backend stores them, scanner reads local copies. | Rejected for prelaunch because raw file storage increases privacy, retention, and deletion obligations. |
| Direct HTTPS file link | User registers one public HTTPS text-like, email, ZIP archive, PDF, Office Open XML, or OpenDocument file URL; backend fetches it only while scanning. | Accepted for single-file and export-link workflows with SSRF-style host checks, size/type limits, bounded archive parsing, and local OCR fallback when approved tooling exists. |
| Google Drive Picker plus per-scan token | Browser lets the user select files or a folder; backend receives selected metadata and a short-lived access token only when scan starts. | Still accepted as the lowest-persistence path for one-off scans. |
| Account-scoped server-side Drive binding | Backend stores a user-approved Drive refresh token in the local account store and refreshes short-lived access tokens only for selected-source scans. | Accepted for the requested Account settings binding; documented separately in `docs/design/google-drive-account-binding.md`. |
| Workspace-level Drive tenant connector | Admin grants broad tenant or shared-drive crawling. | Rejected for P0 because it expands into production tenant discovery and authorization. |

## Selected Approach

The frontend Source dialog exposes three registration modes:

- `remote_file_link`: stores `config.url` and scans one public HTTPS text-like file, RFC 5322/MIME email file, bounded ZIP archive, PDF text layer or bounded local PDF OCR candidate, Office Open XML file, or OpenDocument file.
- `google_drive_selection`: stores selected Drive item metadata in `config.items`; Add Source can open Picker with either browser OAuth or a short-lived Picker token minted from a connected account binding; scans run with either a short-lived Picker token sent in `POST /api/scans/full` as `authorization.googleDriveAccessToken` or a connected account-level Drive binding that refreshes a short-lived token server-side.
- `local_repo`: keeps the existing allowed absolute path flow for controlled host-mounted sources.

The backend adds a temporary prelaunch document-reader boundary that converts supported source types into in-memory `SourceDocument` values. It does not persist raw file bodies. Provider tokens are never exposed publicly; per-scan Picker access tokens are not stored, and account binding refresh tokens are stored only in the local account binding store documented in `docs/design/google-drive-account-binding.md`. Public payloads continue to expose only metadata, counts, redacted snippets, findings, metrics, and audit events.

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
- Google Drive scan execution requires `authorization.googleDriveAccessToken` or a connected account-level Drive binding for the signed-in user.
- Folder traversal stops at the prelaunch file limit.
- Text extraction accepts text-like MIME types and supported text-like file suffixes through BOM/charset-aware Unicode decoding, RFC 5322/MIME email messages, bounded ZIP archives, PDF text layers, bounded local PDF OCR candidates, Office Open XML packages, OpenDocument packages, or explicit Google Docs, Sheets, and Slides export profiles. Other Google Workspace MIME types are warning-counted as unsupported instead of being mislabeled as generic text.

Side effects:

- Source registration stores metadata and connector config only.
- Scan execution downloads or exports content into memory for the current process.
- Findings store redacted snippets and source metadata only.
- Audit events record scan/finding workflow events and do not include raw source content.

Failure paths:

- Missing Picker public config leaves Drive selection disabled and reports the missing host variables.
- Missing Drive authorization rejects scan start or records a failed source-unavailable scan state without preserving stale findings.
- Unsupported file type, unreadable PDF, missing OCR tooling for text-layer-missing PDFs, over-limit file size, download failure, or Drive API failure becomes a warning or command rejection before raw content is persisted.

Rollback path:

- Remove or unset `GOOGLE_PICKER_API_KEY` and `GOOGLE_CLOUD_PROJECT_NUMBER` to disable Drive Picker selection without affecting existing account login.
- Remove Google OAuth client credentials or delete local `google_drive_bindings` rows to disable persistent account binding.
- Remove the `remote_file_link` and `google_drive_selection` adapters from governance config to make those sources non-scan-ready.
- Revert the source dialog to local-path registration only; existing stored source rows remain metadata-only and can be ignored or deleted through normal state cleanup.

## Impact Surface

- Frontend: Source dialog, Account settings Drive binding panel, source scan readiness, runtime-only Drive access-token handoff.
- Backend: Source validation, source connection checks, prelaunch scan document reading, PDF text-layer extraction and local OCR fallback, Drive Picker public-config endpoint, account binding routes, server-side access-token refresh.
- Contracts: source config shapes, source-registration deletion route, per-scan authorization payload, Google Drive Picker config envelope, Google Drive binding envelope.
- Deployment: host environment needs Google Picker public credentials for Drive selection and the PDF extraction dependency installed for the API runtime; image-only PDF OCR also needs host `pdftoppm`, Tesseract, and selected language packs.
- Security/privacy: no raw source body storage, no frontend provider-token exposure, account binding refresh tokens stored only server-side in the local prelaunch store, HTTPS/public-host guard for remote links, no real deletion.

## Primitive Acceptance Criteria

- A user can register a direct HTTPS file link and start a full scan that produces redacted findings when the file contains detectable signals.
- Direct-link scans reject non-HTTPS, credential-bearing, private-address, unreachable, over-limit, or unsupported files without storing raw content.
- PDF text-layer and bounded local PDF OCR scans can produce redacted findings without storing raw PDF bodies, page images, or raw extracted text.
- DOCX, XLSX, PPTX, ODT, ODS, ODP, EML, and ZIP scans can produce redacted findings through the local deterministic extraction path documented in `docs/design/local-format-recognition-difficulty.md` and `docs/design/archive-container-extraction.md`.
- A user can select Google Drive files or one folder through Google Picker when host public credentials are configured; if their lawdit account has a connected Drive binding, Picker opens with that bound account token instead of starting browser-side Google authorization.
- A Google Drive source stores selected item metadata but not the access token.
- A Google Drive full scan requires a short-lived access token in the scan request or a connected account-level Drive binding; missing authorization does not preserve stale scan-derived findings.
- A user can connect, change, or disconnect the account-level Drive binding from Account settings without deleting source registrations or external Drive files.
- Google Drive folder scans enumerate descendant files up to the prelaunch limit and export Google Docs, Google Sheets, and Google Slides through explicit export profiles that preserve distinct format/method counts and redacted anchors.
- A user can remove a source registration from lawdit state without deleting any external source file.
- Public API responses and UI surfaces show metadata, redacted evidence, findings, metrics, warnings, and audit state without raw file bodies, unredacted personal data, provider tokens, refresh tokens, client secrets, or deletion execution.
