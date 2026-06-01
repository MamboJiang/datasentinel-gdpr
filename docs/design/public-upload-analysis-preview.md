# Public Upload Analysis Entry

## Problem Definition

The public website needs a simple product entry before a visitor enters the full console: upload one file, run the same bounded extraction and deterministic signal detection concepts used by the Workspace flow, and return a short redacted result summary with live capacity data.

This implementation is intentionally narrow. It is not a durable queue, customer workspace, legal assessment, production tenant connector, or deletion workflow.

## Research Basis

- OWASP File Upload guidance recommends allowlisted file types, server-side validation, safe filenames, storage outside executable paths, malware/CDR consideration where applicable, and explicit upload size limits to reduce storage and processing risk: [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
- OWASP input-validation guidance requires server-side validation because browser checks can be bypassed and specifically calls out maximum file size and file type controls for upload features: [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html).
- MDN documents `FormData` as the browser primitive for submitting files with `multipart/form-data` and warns not to manually set the multipart `Content-Type` header when using `fetch`: [MDN Using FormData Objects](https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest_API/Using_FormData_Objects).
- MDN documents multipart media types as boundary-delimited HTTP payloads, which keeps the API shape compatible with standard browser file uploads: [MDN MIME types](https://developer.mozilla.org/docs/Web/HTTP/Guides/MIME_types).

## Goals

- Let a visitor experience lawdit's discover -> explain -> review-next-step loop with one uploaded file.
- Return concise categories, risk level, redacted evidence snippets, a review recommendation, accountable next steps, and optional processing-stage detail.
- Show live server capacity data instead of fake queue numbers.
- Keep raw uploaded content transient inside the request/analysis boundary.
- Preserve lawdit safety boundaries: no legal advice, no full GDPR-compliance claim, no automatic deletion, no raw sensitive values in public output.

## Non-Goals

- No multi-file batch upload.
- No durable queue, background worker, or retained public analysis history.
- No production Microsoft Graph, tenant, OAuth, source connector, or deletion integration.
- No malware scanning or content disarm service in this P0 entry.
- No promise that a clean result means a file has no personal data.
- No full Workspace review console in the public route.

## Options Considered

| Option | Summary | Tradeoff |
| --- | --- | --- |
| Reject when capacity is full | Accept work only when an active analysis slot is available; show real active and waiting-at-intake counts. | Most reversible and avoids durable queue infrastructure; users retry when a slot opens. |
| Queue beyond active capacity | Queue users after active slots are occupied. | Smoother UX, but requires cancellation, cleanup, polling, and durable worker semantics outside P0. |
| Require sign-in before analysis | Tie every upload to an authenticated account. | Stronger identity boundary, but weakens the simple public analysis path. |

Selected direction: capacity guard with transient waiting-at-intake counts. The public API records sessions that hit capacity for a short TTL, but it does not enqueue files for later processing.

## Implemented Limits

| Limit | Value | Boundary Behavior |
| --- | --- | --- |
| Active analyses | 10 active browser sessions globally | The next concurrent requester sees capacity full, `waitingUsers` increments transiently, and no file analysis starts. |
| Per-session active files | 1 file | A session with an active analysis receives a duplicate-active rejection until the current analysis reaches a terminal state. |
| File size | 10 MB maximum | Oversized files are rejected before extraction or signal detection starts. |
| Upload shape | One `multipart/form-data` field named `file` | Missing, malformed, empty, or multi-file uploads are rejected. |
| Format gate | Core-supported suffix or MIME, plus suffixless text sniff candidates | Supported MIME types such as `application/pdf` can reach extraction even when the filename has no extension; suffixless octet-stream files must pass bounded Unicode text sniffing before producing findings. |
| Risk priority | Shared deterministic signal-risk taxonomy | Identity documents, credentials, financial identifiers, special-category data, and other Workspace high-risk signal types are high priority in public summaries as well. |
| Result depth | Short summary plus optional stages | The result returns categories, risk level, redacted evidence snippets, warnings, review guidance, accountable next steps, and optional handoff detail, not a full evidence workspace. |
| Deletion | Not available | Trial output cannot request, schedule, or imply deletion execution. |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Idle | Capacity loaded | Public API reachable | Idle | Render real `maxActive`, `activeAnalyses`, `availableSlots`, `waitingUsers`, and file-size limit. |
| Idle | User selects file | File exists and no active file for session | File selected | Show filename, size, and local size-limit status. |
| File selected | User submits | Client file size > 10 MB | Rejected: file too large | Show size-limit message; no request is needed. |
| File selected | User submits | Client checks pass | Uploading | Submit exactly one `multipart/form-data` file field with the browser analysis session header. |
| Uploading | Server validates | Body is malformed, empty, unsupported, or over 10 MB | Rejected | Return `application/problem+json`; no slot is reserved for analysis. |
| Uploading | Server validates | Session already has active analysis | Rejected: one file active | Return 409 with live capacity state. |
| Uploading | Server validates | Active analyses >= 5 | Rejected: capacity full | Return 429 with live capacity state and transient waiting position. |
| Uploading | Slot reserved | Capacity slot available | Analyzing | Reserve one active slot for the session. |
| Analyzing | Extraction or detection completes | Redacted summary available | Result ready | Release slot; return result and fresh capacity state. |
| Analyzing | Extraction fails | Unsupported or unreadable content | Analysis failed | Release slot; return safe problem details and fresh capacity state. |
| Result ready | User starts over | No active analysis remains | Idle | Clear local selected file/result state only. |

## Guards

- Server-side size validation is authoritative; client-side checks are only UX assistance.
- Server must not trust filename, MIME type, or browser metadata alone.
- The public intake gate must not reject a core-supported MIME type solely because the filename lacks an extension.
- Suffixless octet-stream files are accepted only as bounded text-sniffing candidates; binary candidates fail before finding creation.
- Public risk summaries must stay aligned with Workspace finding risk taxonomy for high-risk signal types such as passports and driver licenses.
- Only one active analysis is permitted for the same public analysis session ID.
- Capacity is counted by active analysis, not by page view.
- Slot reservation and release must be protected by a lock inside the API process.
- Terminal states must release the active slot even on extraction or detection failure.
- The public endpoint must not require the signed-in Workspace session because it is a website analysis entry.

## Side Effects

- The API keeps transient in-memory capacity state: active session tokens and short-TTL waiting sessions.
- Raw uploaded bytes are processed in-memory for the request and are not written to a public analysis store.
- The response contains only metadata, counts, risk level, warnings, review recommendation, optional accountable next steps/stages, and redacted snippets.
- Public payloads must not contain raw extracted text, raw file body, provider tokens, legal conclusions, or deletion instructions.

## Failure Paths

- Oversized file: reject before extraction and signal detection.
- Capacity full: reject at intake, add the session to the transient waiting-at-intake set, and do not reserve an active slot.
- Same session already active: reject the second submission without replacing the first analysis.
- Unsupported file: reject unsupported suffix/MIME combinations before reserving a slot, or release any reserved slot when extractor probing rejects a suffixless candidate.
- Analysis crash: release the slot and return a neutral failure without raw-content output.

## Rollback Path

- Remove the homepage analysis component and route CTAs.
- Disable `/api/public-analysis/capacity` and `/api/public-analysis/analyze` or return a maintenance problem response.
- Remove `contracts/schemas/public-analysis.yaml` and public-analysis mocks in the same rollback patch.
- Keep existing homepage sections, `/dashboard`, Workspace data, source registrations, and audit state unchanged.
- Clearing the API process removes transient capacity state without deleting Workspace console data.

## Impact Surface

- Public homepage content and CTA strategy.
- `contracts/openapi.yaml`, `docs/API_CONTRACT.md`, and public-analysis mocks.
- Backend public intake boundary, multipart validation, capacity accounting, extraction, deterministic signal detection, and redacted response shaping.
- Frontend API client, homepage analysis component, and visible capacity/result states.
- Acceptance criteria, tests, deployment checks, and security notes.

## Primitive Acceptance Criteria

- A visitor can identify the entry as a single-file, short-result experience before uploading.
- The page displays real capacity data from `/api/public-analysis/capacity`.
- A file larger than 10 MB is rejected before extraction or signal detection starts.
- Core-supported MIME types such as PDFs can be analyzed even when the uploaded filename has no extension.
- Suffixless octet-stream text can be analyzed through bounded Unicode sniffing, while suffixless binary content remains unsupported and creates no finding.
- A session with an active analysis cannot start a second file analysis.
- The system never runs more than 10 active public analyses in the API process at the same time.
- Capacity-full users see a clear non-destructive state with live waiting-at-intake data and no analysis slot is consumed.
- Every accepted analysis reaches a terminal state that releases its active slot.
- Results show redacted, concise facts, accountable next steps, and optional handoff detail without raw sensitive values, legal advice, full GDPR-compliance claims, or deletion execution.
- The frontend renders optional backend-provided processing stages, Workspace handoff readiness, next steps, and boundary notes while remaining compatible with shorter responses.
- The full Workspace console remains separate from the public analysis entry.
