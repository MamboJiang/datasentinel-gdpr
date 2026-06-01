# Test Cases

## Current Initialization Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| INIT-001 | Review repository language | All tracked project files are written in English. |
| INIT-002 | Review repository scope | No implementation code or runtime dependency files are present. |
| INIT-003 | Review required documents | README, BRD, MRD, PRD, TRD, DesignSpec, TestCase, and ACCEPTANCE exist. |
| INIT-004 | Review GitHub visibility | The remote repository is public. |
| INIT-005 | Review collaborators | Requested teammates are invited or already present as collaborators. |

## Contract Readiness Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| CONTRACT-001 | Parse contract YAML files | `contracts/openapi.yaml` and files in `contracts/schemas/` parse as YAML. |
| CONTRACT-002 | Parse mock payloads | Every file in `contracts/mocks/` parses as JSON. |
| CONTRACT-003 | Compare contract docs and mocks | Mock payloads use the envelope, field names, and state values documented in `docs/API_CONTRACT.md`. |
| CONTRACT-004 | Review tolerant compatibility rules | Unknown fields, optional fields, empty arrays, partial data, and unknown enum-like values have documented behavior. |
| CONTRACT-005 | Review error contract | Errors are documented as `application/problem+json` with trace IDs. |
| CONTRACT-006 | Review AI instructions | `AGENTS.md` and `.github/copilot-instructions.md` tell AI tools to follow the contract and avoid unapproved implementation. |
| CONTRACT-007 | Review governance contract | Governance config, active policy pack, permissions, and review support endpoints are documented and mocked. |
| CONTRACT-008 | Review organizer sample source | The organizer sample repository is represented as a default demo source without vendoring PDFs. |

## User Documentation Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| USERDOC-001 | Install the Fumadocs docs app | `npm install` succeeds from `docs-site` and creates only docs-site dependency artifacts. |
| USERDOC-002 | Build the Fumadocs docs app | `npm run build` succeeds from `docs-site`. |
| USERDOC-003 | Review docs navigation | The sidebar contains quick start, accounts and Workspaces, sources, dashboard and scans, findings and review, audit and evaluation, governance, safety boundaries, and FAQ pages without duplicate top-level shortcuts to the same destinations. |
| USERDOC-004 | Review user-facing workflow coverage | The docs explain source registration, full scans, findings review, human decisions, audit, evaluation, governance, Workspace scoping, and permission boundaries in user language. |
| USERDOC-005 | Review safety copy | The docs state no legal advice, no full GDPR compliance claim, deletion simulated in P0, no raw-content exposure, and no provider-token persistence. |
| USERDOC-006 | Review scope discipline | The docs do not invent API fields, endpoints, production Microsoft Graph access, tenant integrations, real deletion behavior, legal conclusions, or hidden permission powers. |
| USERDOC-007 | Request `https://founder-force.uk/docs` | The response serves the Fumadocs user guide under the existing domain prefix. |
| USERDOC-008 | Open the console account menu and click Docs | The browser performs a document navigation to `/docs` and renders the deployed Fumadocs guide. |
| USERDOC-009 | Request `https://founder-force.uk/docs/api/search` | The response comes from the docs search route, while `https://founder-force.uk/api/health` still comes from the product API. |
| USERDOC-010 | Review `/docs` and `/docs/quick-start` visually | The homepage shows a prominent quick-start CTA, first-review workflow preview, task cards, and safety summary; Quick Start shows an eight-step path and readiness checks. |
| USERDOC-011 | Compare homepage and nested docs layouts | `/docs` renders as a standalone homepage without the Fumadocs sidebar, while `/docs/quick-start` keeps sidebar navigation. |
| USERDOC-012 | Review screenshot and data aids | Quick Start, Sources, Dashboard and Scans, Findings and Review, and Audit and Evaluation include cropped non-sensitive screenshots plus tables that explain fields, metrics, and next actions; screenshot URLs are served under `/docs/media/`. |

## Public Upload Analysis Planning Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| UPLOADPLAN-001 | Review the public upload-analysis design note | `docs/design/public-upload-analysis-preview.md` defines the problem, research basis, options, state machine, impact surface, rollback path, and primitive acceptance criteria. |
| UPLOADPLAN-002 | Review planned capacity limits | The planning docs state one active file per user/session, a 10 MB maximum file size, and at most 10 active user analyses globally. |
| UPLOADPLAN-003 | Review non-implementation scope | The planning docs state that no upload UI, endpoint, worker, queue, storage, parser, scanner, or deployment behavior is approved in the current task. |
| UPLOADPLAN-004 | Review safety boundaries | The planning docs keep raw sensitive values out of public output and prohibit legal advice, full GDPR-compliance claims, automatic deletion, and production tenant integration. |
| UPLOADPLAN-005 | Review future contract dependency | The planning docs require future updates to the OpenAPI contract, API docs, mock payloads, tests, security notes, deployment controls, and acceptance criteria before implementation. |

## Backend Planning Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| BEPLAN-001 | Review post-source execution plan | `docs/design/backend-post-source-execution-plan.md` and `docs/design/backend-post-source-stage-details.md` define the backend steps after sample source connection. |
| BEPLAN-002 | Review step boundaries | The planning documents separate scan orchestration, extraction, detection, classification, owner routing, review, audit, delta scan, metrics, and evaluation responsibilities. |
| BEPLAN-003 | Review state transitions | The planning documents define success, failure, permission-denial, partial-data, and rollback paths. |
| BEPLAN-004 | Review safety constraints | The planning documents keep raw sensitive text out of public responses and keep deletion simulated. |
| BEPLAN-005 | Review contract compatibility | The planning documents use existing P0 endpoints and mock payload shapes without requiring a contract version bump. |
| BEPLAN-006 | Review primitive acceptance | The planning documents define observable acceptance criteria for each backend workflow stage. |

## Backend API Server Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| BEAPI-001 | Call `GET /api/health` | The server returns `data.ok = true`, contract metadata, and `X-Contract-Version = 0.1.0`. |
| BEAPI-002 | Call `GET /api/sources` | The response returns the mock-compatible source list including `source_001`. |
| BEAPI-003 | Start a full scan for `source_001` | The server returns `202`, a running scan envelope, `meta.partial = true`, and no raw source content. |
| BEAPI-004 | Start a full scan for a not-ready source | The server returns `application/problem+json` and does not create a new audit event. |
| BEAPI-005 | Record a valid review decision | The server returns `201`, updates finding status, creates a review audit event, and keeps `deletionExecuted = false`. |
| BEAPI-006 | Load the frontend with API unavailable | The frontend renders a server-unavailable or explicit development fallback state without silently presenting fake prelaunch data. |

## Prelaunch Account Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| AUTH-001 | Call `GET /api/auth/providers` | The response lists Google and GitHub with `configured` flags and no secrets. |
| AUTH-002 | Start login for an unconfigured provider | The server returns `application/problem+json` and creates no session. |
| AUTH-003 | Start GitHub login when configured | The server redirects to GitHub with state and PKCE challenge, and stores the verifier only in a signed HttpOnly transaction cookie. |
| AUTH-004 | Complete callback with mismatched state | The server rejects the callback before token exchange and creates no user or session. |
| AUTH-005 | Complete callback with validated provider identity | The server stores a local user profile, creates a first-party session, and redirects to the app. |
| AUTH-006 | Call `GET /api/auth/session` with a valid cookie | The response returns `authenticated = true`, safe user profile fields, and no provider tokens. |
| AUTH-007 | Call `POST /api/auth/logout` | The server revokes the local session, clears the cookie, and `/api/auth/session` returns unauthenticated. |
| AUTH-008 | Render unauthenticated console | The frontend shows a minimal centered sign-in page with DataSentinel branding, only Google and GitHub branded provider buttons, and no fixture findings. |
| AUTH-009 | Render authenticated console with no findings | The frontend shows operational empty states and source setup actions instead of fake examples. |
| AUTH-010 | Start server with `DATASENTINEL_ENABLE_DEMO_FIXTURES=false` | Sources, findings, audit, metrics, and evaluation start empty until a configured local source is scanned. |
| AUTH-011 | Restart a SQLite-backed preview after disabling demo fixtures | Historical seeded demo sources and workflow documents are removed while real registered local sources and account/session records remain. |
| AUTH-012 | Sign in as Account A and Account B against the same SQLite preview | Account B cannot list, delete, scan, connect-test, review, or open Account A's Sources or Findings. |
| AUTH-013 | Start a SQLite preview after legacy global rows exist | Legacy global source and workflow rows are hidden from authenticated account scopes. |

## Workspace Admin Permission Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| WORKSPACE-001 | Call `GET /api/workspaces` as a newly created account with no membership | The response has no current Workspace, no Workspace list, and `workspaceRequired = true`. |
| WORKSPACE-001A | Call `POST /api/workspaces` as a signed-in account | The response includes the new Workspace and the creator becomes an active `workspace_owner` and `workspace_admin` member. |
| WORKSPACE-001B | Create two Workspaces, register a Source in the first, then switch to the second | The second Workspace lists no Source or Finding state copied from the first Workspace. |
| WORKSPACE-001C | Call `POST /api/workspaces/current` for a Workspace where the account is a member | The response updates `currentWorkspaceId`, and subsequent operational API reads use the selected Workspace scope. |
| WORKSPACE-001D | Call `POST /api/workspaces/current` for an unknown or non-member Workspace | The server returns problem details and leaves the previous Workspace selection unchanged. |
| WORKSPACE-002 | Call `GET /api/workspaces/current/admin` as a Workspace admin | The response includes Workspace, current membership, members, groups, permission catalog, invitations, permission boundary, and chart data. |
| WORKSPACE-003 | Call `GET /api/workspaces/current/admin` as a non-admin or Workspace-less account | The response exposes denied admin actions and no mutation capability. |
| WORKSPACE-004 | Generate an invite link as a Workspace admin | The server returns a pending invitation with invite path, invited groups, inviter, expiry, and no provider secrets. |
| WORKSPACE-005 | Create an invitation as a non-admin | The server returns `application/problem+json` and no invitation or membership changes. |
| WORKSPACE-006 | Accept a pending invite link as a signed-in account | The invitation page shows concise Workspace name, introduction, owner, member count, and invited group context before acceptance, and the account becomes an active Workspace member exactly once. |
| WORKSPACE-007 | Accept an invitation twice, after expiry, after revocation, or as an existing member | The server returns problem details and does not create duplicate membership. |
| WORKSPACE-008 | Render the Workspace menu | The menu shows current Workspace and current membership groups for members, and pending/no-Workspace state for accounts without membership. |
| WORKSPACE-008A | Click the Workspace menu create action | A Workspace creation dialog opens with name, description, creator-role, and default-group settings before creation. |
| WORKSPACE-008B | Click a non-current Workspace in the Workspace menu | The menu switches current Workspace and reloads Workspace-scoped operational state. |
| WORKSPACE-008C | Render the sidebar as a non-admin Workspace member | Links requiring denied Workspace actions are hidden, and expandable links show a right-side chevron. |
| WORKSPACE-008D | Update the Workspace profile as an admin with `manage_workspace_settings` | The Workspace menu and Admin header show the new name and introduction, the profile editor does not expose a Sidebar label field, and membership group display remains in the compact Workspace menu pill without changing membership or operational scope. |
| WORKSPACE-009 | Render `/workspace/admin` | Admin charts and compact member/group summaries render without a charting dependency, explanatory helper paragraphs, or legal-compliance claim. |
| WORKSPACE-009A | Render `/workspace/admin`, `/workspace/admin/members`, and `/workspace/admin/groups` | The surfaces use concise operational labels without helper paragraphs or collapsed group-description text while retaining Workspace description data, denied-action reasons, and the external-source deletion warning. |
| WORKSPACE-010 | Create a Workspace group as an admin | The server returns the new group with a generated ID, visible name, description, explicit permissions, and zero initial members. |
| WORKSPACE-011 | Rename or re-permission a Workspace group as an admin | The group keeps its ID and permission boundaries use the updated permissions. |
| WORKSPACE-012 | Delete a non-admin Workspace group | The group disappears from admin summary, members lose that group reference, and pending invite links with no remaining groups are revoked. |
| WORKSPACE-013 | Open `/workspace/admin/groups` from sidebar or Admin Group controls panel | The new-group form and per-group permission editors are collapsed by default; only a new-group button and compact group cards are visible until the admin opens a form or card edit icon. |
| WORKSPACE-014 | Open `/workspace/admin/members` from sidebar or Admin Members panel | The Members page lists all Workspace members and supports search, group filtering, status filtering, grouping, and sorting by name, primary group, status, joined date, and last activity. |
| WORKSPACE-015 | Update a member's groups as an admin with `manage_workspace_members` | The member's permission boundary changes to the selected valid groups. |
| WORKSPACE-016 | Remove a Workspace member as an admin with `manage_workspace_members` | The member is no longer active in admin summary and their selected Workspace is cleared when needed. |
| WORKSPACE-017 | Update or remove members as a non-admin | The server returns problem details and no membership change is persisted. |
| WORKSPACE-018 | Remove self or remove/demote the last active `workspace_admin` member | The server returns problem details and no lockout-causing change is persisted. |
| WORKSPACE-019 | Delete `workspace_admin` or remove its required admin-management permissions | The server returns problem details and no lockout-causing change is persisted. |
| WORKSPACE-020 | Generate a pending invite and render the Invitations list | Pending invitations show a copy action; accepted, expired, or revoked invitations do not expose a pending-copy control. |
| WORKSPACE-021 | Create an invitation that includes `workspace_owner` | The server returns problem details and no invitation grants Owner authority. |
| WORKSPACE-022 | Type another active member's exact email in the Owner transfer control | The transfer button is disabled while the input is empty or unmatched, becomes enabled only for a matching active member email, and requires a second confirmation before submission. |
| WORKSPACE-022A | Transfer owner authority as a Workspace owner to another active member | The target member receives `workspace_owner` and `workspace_admin`, and the previous owner loses `workspace_owner`. |
| WORKSPACE-023 | Transfer owner authority as a non-owner or to a removed/unknown member | The server returns problem details and no membership changes. |
| WORKSPACE-024 | Delete `workspace_owner` or remove its required owner-management permissions | The server returns problem details and no lockout-causing change is persisted. |
| WORKSPACE-025 | Delete a Workspace with a non-matching confirmation name | The server returns problem details and leaves the Workspace, memberships, and invitations unchanged. |
| WORKSPACE-026 | Delete a Workspace with exact-name confirmation as a Workspace owner | A second confirmation is required, then the Workspace is removed from visible directories, active memberships are removed, pending invitations are revoked, affected current selections are cleared, and no external source files are deleted. |

## Local SQLite Persistence Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| DB-001 | Run `python3 -m backend.datasentinel.db_tool init --db-path <file>` | A local SQLite file is created with schema version, source rows, and one workflow document. |
| DB-002 | Run `python3 -m backend.datasentinel.db_tool status --db-path <file>` | The command reports the database path, schema version, source count, and workflow-document count without exposing secrets. |
| DB-003 | Register a source through a SQLite-backed API app and restart with the same file | The source remains listed after restart. |
| DB-004 | Record a review through a SQLite-backed API app and restart with the same file | Finding status and the review audit event remain visible after restart. |
| DB-005 | Start the API without `--db-path` | The server keeps the existing in-memory fixture-backed behavior. |

## Prelaunch Source Input Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| SRCIN-001 | Call `GET /api/integrations/google-drive/picker-config` with a valid first-party session cookie | The response reports `configured`, `clientId`, `apiKey`, `appId`, scopes, and missing browser setup fields without returning client secrets or provider tokens. |
| SRCIN-002 | Register a direct HTTPS file link | The source is created as `remote_file_link` with `config.url` and can become scan-ready when the URL passes policy checks. |
| SRCIN-002A | Register a source with an active Workspace member selected as direct owner | The Source response includes `assignedOwnerUserId` and an owner display snapshot from the current Workspace membership. |
| SRCIN-002B | Edit a Source owner as a Workspace admin | The Source owner changes to the selected active member or clears to fallback without mutating external source files. |
| SRCIN-003 | Scan a direct HTTPS text file with detectable personal-data patterns | The scan produces findings with redacted evidence and no raw source body or unredacted personal data in public payloads. |
| SRCIN-004 | Register a non-HTTPS, credential-bearing, Google Drive share-page, private-address, over-limit, or unsupported direct file link | The backend rejects the connection or scan before creating workflow output. |
| SRCIN-005 | Load an authenticated empty prelaunch project with no findings, then register a source | The frontend treats the API as available and does not request a blank finding detail before source registration. |
| SRCIN-005A | Open the Sources page | The page shows the current prelaunch supported file types below the source inventory surface. |
| SRCIN-006 | Select Google Drive files through Picker | The source stores selected item metadata, keeps the access token out of persisted source state, and shows connected in the Sources table while the browser session still holds the token. |
| SRCIN-006A | Connect Google Drive in Account settings | The binding status becomes connected and public payloads expose safe profile fields, scopes, and timestamps without access tokens, refresh tokens, client secrets, or OAuth transaction state. |
| SRCIN-006B | Refresh the browser after registering a Google Drive source with a connected binding | The source remains scan-ready through the account binding even though the source record stores no access token. |
| SRCIN-006C | Disconnect or change the Google Drive binding in Account settings | The local binding is removed or replaced, provider-token revocation is attempted, source registrations remain, and no Google Drive file is deleted or mutated. |
| SRCIN-006D | Choose Google Drive files or a folder in Add Source while the signed-in account has a connected Drive binding | The frontend requests a short-lived bound Picker token, passes it to Google Picker, and does not start browser-side Google authorization. |
| SRCIN-007 | Receive a non-terminal Google Picker callback before the final picked action | The Add Source dialog remains open and waits for the final picked or cancelled action. |
| SRCIN-008 | Select a Google Drive folder through Picker | The selected folder appears in the Add Source dialog, and the scan enumerates descendant files up to the prelaunch limit. |
| SRCIN-008A | Scan a local source above the prelaunch file-count limit | The scanner processes only the bounded file count, reports the total candidate files, and includes a visible limit warning. |
| SRCIN-009 | Start a Google Drive scan without a per-scan access token or connected account binding after previous findings exist | The backend returns `application/problem+json`, records a failed source-unavailable scan state, clears visible scan-derived findings, and does not delete external source files. |
| SRCIN-009A | Trigger a server-side scan rejection from the frontend | The frontend shows the project-server rejection reason and does not mark the server disconnected or run the local mock scan workflow. |
| SRCIN-010 | Review public payloads after remote-link or Drive scans | Payloads expose metadata, warnings, redacted snippets, findings, metrics, and audit events only; raw file bodies, raw source URLs, absolute host paths, provider tokens, refresh tokens, client secrets, legal conclusions, and deletion execution are absent. |
| SRCIN-011 | Scan a PDF that has an extractable text layer and detectable personal-data patterns | The scan produces findings with redacted evidence and does not expose raw extracted PDF text in public payloads. |
| SRCIN-012 | Review source references after local, direct-link, or Google Drive scans | Public findings and console views show a safe source reference or source name, not a raw external URL or absolute host file path. |
| SRCIN-012A | Delete a source from the Sources page or `DELETE /api/sources/{sourceId}` | The source registration is removed from DataSentinel state, derived scan/finding state for that deleted source is cleared, external source files are not deleted, and a repeated delete returns not found. |
| SRCIN-012B | Scan a Source assigned to one Workspace member, then list findings as another member | Only the assigned owner or fallback route sees the finding; unrelated Workspace members receive an empty list or not found. |
| SRCIN-013 | Scan DOCX, XLSX, PPTX, DOC, XLS, PPT, ODT, ODS, ODP, EML, and ZIP files with detectable personal-data patterns | The scan produces redacted findings from deterministic Office Open XML, host-local legacy Office conversion, OpenDocument, RFC 5322/MIME email, or bounded ZIP member extraction and reports the expected moderate or hard recognition difficulty. |
| SRCIN-014 | Inspect `contentExtraction` after a deterministic scan | The payload includes difficulty and format counts, `aiAssistanceUsed = false`, `modelCalls = 0`, and no raw source text. |
| SRCIN-015 | Scan an image file with host OCR available | The scanner extracts OCR text during scan execution, creates only redacted findings, reports `image_ocr` and hard difficulty, and keeps model calls at zero. |
| SRCIN-016 | Scan a VTT/SRT transcript and a bounded raw video file | The transcript can produce redacted findings, and the raw video can produce redacted findings through host-local FFmpeg frame extraction plus local Tesseract OCR. Missing tools, disabled OCR, over-limit video, or empty frame OCR remain hard/OCR-deferred. |
| SRCIN-017 | Scan legacy binary Office inputs through host-local conversion | A bounded DOC/XLS/PPT input is converted to UTF-8 text through host-local LibreOffice during scan execution only; missing converter, failed conversion, empty output, or over-limit input is recorded as hard unsupported without raw binary bytes, converted raw text, or fake findings in public payloads. |
| SRCIN-018 | Run deployed Google Drive binding scan on `agent-us` | A selected `GDPR-data-samples-main` Drive folder scan starts without a browser-memory Picker token, completes through the account binding, records `pdf_mixed` evidence for the V4 PDF, and stores only aggregate redacted evidence in `live_drive_scan_report_agent_us.json`. |
| SRCIN-019 | Scan Google Docs, Sheets, and Slides exports | The Drive reader uses explicit export MIME types, reports `google_docs_export`, `google_sheets_export`, and `google_slides_export` format/method counts, preserves redacted anchors, and does not mislabel unsupported Google Workspace MIME types as generic text. |

## Core Engine Corpus and Multilingual Detection Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| CORE-001 | Review the Google Drive corpus manifest | `tests/fixtures/gdpr_data_samples_main/drive_manifest.json` records the `GDPR-data-samples-main` folder ID, observed date, original file IDs, filenames, MIME types, and corpus roles. |
| CORE-001A | Verify raw corpus preservation | `tests/fixtures/gdpr_data_samples_main/raw_corpus_manifest.json` represents every Drive manifest file, and every tracked raw file exists with the expected byte size and SHA-256. |
| CORE-001B | Review local corpus scan evidence | `tests/fixtures/gdpr_data_samples_main/corpus_scan_report.json` records extraction methods, difficulty, OCR capability state, signal counts, and signal types only; it contains no raw extracted text or raw detected values. |
| CORE-002 | Scan multilingual deterministic cases | Chinese, French, Spanish, German, Italian, Portuguese, Dutch, Polish, Japanese, Korean, and Arabic form labels produce redacted signals for names, phone numbers, email, birth dates, IDs, tax IDs, addresses, bank accounts, compensation, health, and credentials. |
| CORE-002A | Scan inline and OCR-normalized multilingual labels | Static text and OCR output with multiple labels on one line, punctuation-missing CJK/Kana/Hangul/Arabic labels, or dash-delimited labels produce separate redacted findings with source-local text-position anchors and no same-type overlapping duplicate signals. |
| CORE-002B | Scan separatorless CJK OCR word output | Tesseract TSV output that splits Chinese labels and values into character-level words is normalized into detectable text, produces separate redacted person, phone, and address signals, and attaches pixel source regions without raw OCR text or raw values in public payloads. |
| CORE-003 | Review multilingual scan payloads | Public scan, finding, and detail payloads include redaction markers and signal counts but do not include the raw multilingual values. |
| CORE-004 | Scan a PDF without an extractable text layer when local PDF OCR tooling is available | The scanner uses bounded local PDF OCR, reports `pdf_ocr`/`pdf_page_image_ocr`, marks hard difficulty, and produces redacted findings only. |
| CORE-004A | Scan a mixed PDF with text-layer pages and blank/scanned pages | The scanner keeps extractable text-layer pages, OCRs bounded blank/scanned pages when host tooling is available, reports `pdf_mixed`/`pdf_text_layer_with_page_ocr`, and returns redacted page-region anchors for OCR-derived findings without exposing raw OCR text or page images. |
| CORE-004B | Scan a mixed PDF with text-layer pages and image text overlays | The scanner keeps text-layer content, OCRs bounded image-bearing pages when host tooling is available, merges OCR-derived signals into `pdf_mixed` findings, and exposes only redacted page-region anchors. |
| CORE-004C | Scan a mixed PDF when page OCR tooling is unavailable | The scanner preserves text-layer findings, marks the document hard, increments OCR-deferred warning metadata, and does not pretend the visual layer was scanned. |
| CORE-004D | Scan a bounded PDF larger than the text-stream limit | PDF and other complex document formats use the bounded document byte budget rather than the 1 MB text-stream budget, so a 6 MB PDF can enter extraction and signal detection. |
| CORE-005 | Scan a PDF without an extractable text layer when local PDF OCR tooling is missing | The scanner reports a recoverable hard/OCR-deferred warning and does not create fake findings. |
| CORE-006 | Configure local OCR languages | When `DATASENTINEL_OCR_LANGS` is set, the local Tesseract invocation uses the installed language-pack list directly when bounded and splits large lists into bounded multilingual profiles. |
| CORE-006A | Review OCR capability reporting | OCR capability output reports mode, configured language list, Tesseract availability, `pdftoppm` availability, image OCR availability, and PDF OCR availability without probing or storing source content. |
| CORE-006B | Scan colored text overlays in image OCR | Local OCR can run bounded color-overlay preprocessing variants before deterministic detection, producing redacted findings without public raw OCR text or page images. |
| CORE-006C | Handle one timed-out OCR profile | If one OCR language profile or preprocessing candidate times out, later bounded candidates can still run and produce redacted findings; only total OCR failure is counted as OCR-deferred. |
| CORE-007 | Open a source evidence anchor | PDF, text, table, and structure-based anchors resolve through the same review open-and-focus interaction or a redacted fallback without exposing raw values. |
| CORE-008 | Scan preserved raw PDF corpus | All preserved PDF corpus files with text layers extract through `pdf_text_layer`; completed example PDFs produce redacted findings and the serialized signal payloads do not contain raw email, employee ID, or tax ID values. |
| CORE-009 | Scan preserved image OCR challenge without local OCR tooling | The image challenge is reported as hard/OCR-deferred on hosts without Tesseract and does not create fake findings. |
| CORE-010 | Review deterministic text-position anchors | Detected label and regex signals include `evidenceAnchor.selector.type = textPosition`, stable start/end offsets, a redacted fallback label, and no raw matched value in serialized public payloads. |
| CORE-011 | Scan structured text-like files | CSV, XML, JSON, JSONL/NDJSON, HTML/HTM, and UTF-16 text-like files with multilingual labels produce redacted findings, easy difficulty counts, and source-data evidence anchors without leaking raw values. |
| CORE-011A | Review table-cell anchors | CSV/TSV, XLSX, and ODS label-value cells produce `tableCell` selectors with source-derived row, column, column label, and sheet metadata where available, while serialized public payloads keep raw cell values redacted. |
| CORE-011A1 | Scan standard header-row CSV files | Header-row CSV files such as `Name,Date of Birth,Address` create label-context fragments for each data cell, detect label-only values such as names, birth dates, and addresses, and attach redacted `tableCell` anchors to the data row and column. |
| CORE-011A2 | Scan semicolon-delimited CSV files | `.csv` files that use semicolon delimiters, including multilingual headers such as `Nombre;Teléfono`, are parsed as CSV tables and produce redacted findings with source-derived `tableCell` anchors. |
| CORE-011A3 | Scan Markdown files with standard tables | Markdown table headers such as `姓名, 电话, 地址` create label-context fragments for data cells, produce redacted multilingual findings, and attach source-derived `tableCell` anchors while ordinary Markdown text continues to use text-position anchors. |
| CORE-011B | Review structure-path anchors | DOCX, PPTX, ODT, ODP, EML, HTML/HTM, XML, JSON, JSONL, and NDJSON block-derived matches produce `structurePath` selectors with paragraph, slide/shape, OpenDocument paragraph, email header/body-part, HTML node, XML element/attribute ordinal, or JSON record/field ordinal metadata while serialized public payloads keep raw document text, raw email text/header values, raw XML values, and raw JSON values redacted. ZIP member anchors wrap child selectors with ordinal member metadata and do not expose raw member names. |
| CORE-011C | Scan RTF rich-text files | RTF Unicode and escaped text produce redacted findings with source-local text-position anchors, moderate difficulty, and no raw rich-text body or raw detected value in public payloads. |
| CORE-011D | Scan OpenDocument files | ODT, ODS, and ODP files with multilingual labels produce redacted findings, moderate difficulty, `structurePath` or `tableCell` anchors, and no raw OpenDocument body or raw detected value in public payloads. |
| CORE-011E | Scan EML email files | RFC 5322/MIME EML files with multilingual header or body labels produce redacted findings, moderate difficulty, `structurePath` anchors, and no raw email body, raw header value, attachment filename, or raw detected value in public payloads. |
| CORE-011F | Scan ZIP archive files | ZIP files with supported non-archive members produce redacted findings, moderate difficulty, child selectors wrapped with ZIP member ordinals, and no raw member filename or raw detected value in public payloads. |
| CORE-012 | Review PDF text-layer page anchors | PDF text-layer findings expose redacted anchors with `format = pdf_text_layer`, page number, page-local source offsets, and a page fallback label without leaking raw matched values. |
| CORE-013 | Assemble redacted source-review preview package | Finding details include `sourceReviewPreview` built from redacted evidence anchors only, with grouped page regions/text ranges/table cells/structure blocks and `rawContentExposed = false`, `pageImagesExposed = false`, no raw source body, no page image, no Drive URL, and no private absolute path. |
| CORE-013A | Review source-preview context windows | Finding details include redacted context windows for supported anchors, the context preserves safe nearby labels and offsets, masks target and neighboring detected values, and serializes without raw detected values, raw source body, Drive URL, or private absolute path. |
| CORE-014 | Scan bounded raw video media through local frame OCR | MP4/MOV/M4V/MKV/WEBM/AVI inputs under the video byte limit are sampled into temporary frames, OCR'd locally, and surfaced as `video_ocr` hard-difficulty findings with redacted frame-local anchors and no raw frame or media persistence. |
| CORE-014A | Scan legacy binary Office through local conversion | DOC/XLS/PPT inputs under the document byte limit are converted through host-local LibreOffice and surfaced as hard-difficulty redacted findings with source-local text anchors and no persisted binary input or converted raw text. |
| CORE-012A | Review PDF text-layer page-region anchors | When scan-time PDF text coordinates are available, the signal anchor includes an estimated `pageRegion` with PDF user-space coordinates and no raw matched value. |
| CORE-012B | Review OCR page-region anchors | When scan-time Tesseract TSV word boxes are available for image OCR or PDF OCR, the signal anchor includes a pixel `pageRegion` with top-left origin and no raw OCR value. |
| CORE-013 | Scan generated multiformat challenge cases | Generated CSV, HTML, XML, JSONL, UTF-16 text, RTF, DOCX, XLSX, PPTX, ODT, ODS, ODP, EML, ZIP, image OCR, PDF OCR, VTT, and runtime-generated legacy Office/video cases produce expected redacted signal types, recognition difficulty, format labels, and source-local offsets without leaking raw values. |
| CORE-014 | Scan large or noisy text streams | Signal detection stops at the configured scan-character window, caps public signal records per document, and does not leak raw values from skipped content. |

## OpenRouter AI Assistive Processing Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| AI-001 | Start backend without an OpenRouter key | `/api/health` reports `ai.status = disabled` or `missing_api_key`; no API key appears in the payload. |
| AI-002 | Start backend with assistive mode and a key | `/api/health` reports provider `openrouter`, the configured model, budget limits, fail-closed guard, and the metadata/text/OCR/grep/AI tier plan. |
| AI-003 | Plan a redacted ambiguous evidence candidate with deterministic anchors and policy-pack context | The tier plan runs source/policy context, metadata, text/OCR, grep, and policy-context/risk before marking `ai_context` ready. |
| AI-004 | Plan an unredacted evidence candidate | `ai_context` is blocked before any external request. |
| AI-005 | Preflight when usage plus estimated cost exceeds budget | The budget guard rejects the call and leaves scan, finding, audit, metrics, and evaluation state unchanged. |
| AI-006 | Preflight when OpenRouter usage cannot be checked | Fail-closed mode rejects the call before any prompt leaves the process. |
| AI-007 | Run normal full and delta scans | Existing deterministic paths still report `modelCalls = 0`, `estimatedCostUsd = 0`, no raw content exposure, no legal conclusion, and no deletion execution. |
| AI-008 | Review AI metadata against the Atlas | `/api/health` and `aiProcessing` include `atlasReference`, 12 `atlasAlignment` entries, and tier rows whose `atlasStages` cover source/policy, inventory/OCR, deterministic signal detection, context/risk, owner/review boundaries, audit, delta, admin metrics, and evaluation. |
| AI-009 | Attempt AI context support without deterministic anchors or policy-pack context | The request is rejected before any external model request. |

## Full Scan Start Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| FULLSCAN-001 | Start full scan from Dashboard | The workflow targets the default organizer sample source by `sourceId` and creates a running full scan. |
| FULLSCAN-002 | Start full scan from Sources row | The workflow targets the selected source by `sourceId`, not a hard-coded first source. |
| FULLSCAN-003 | Start full scan for not-ready source | No scan or audit event is created, and the user receives a neutral denial message. |
| FULLSCAN-004 | Observe running full scan metrics | Scan progress, scanned files, flagged files, scanned volume, and scan status update together. |
| FULLSCAN-005 | Complete simulated full scan | Scan progress reaches 100%, duration and throughput are set, metrics match the completed scan, and evaluation points to the completed scan. |
| FULLSCAN-006 | Review full scan audit events | Start and completion events include scan ID, actor/system attribution, timestamp, source summary, and no raw sensitive content. |
| FULLSCAN-007 | Verify P0 cost boundary | Full scan start uses deterministic fixture data with zero model calls and no paid external services. |

## Source Inventory and Content Extraction Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| INVEXT-001 | Start full scan for the organizer sample source | The running scan includes file-inventory and content-extraction summaries for `source_001`. |
| INVEXT-002 | Observe running inventory and extraction | The workflow marks partial data, exposes recoverable warnings, and shows stage progress without raw content. |
| INVEXT-003 | Complete full scan extraction | Inventory and extraction stages become complete, final counts match the scan profile, and warnings remain countable. |
| INVEXT-004 | Verify raw-content boundary | `rawContentExposed` remains `false` and no public payload contains raw extracted text, full file bodies, or page images. |
| INVEXT-005 | Verify unsupported-file handling | Unsupported or OCR-deferred files are counted as recoverable warnings and do not block scan completion. |
| INVEXT-006 | Verify resource and cost boundary | Evaluation resource intensity keeps model calls and estimated paid-service cost at zero. |
| INVEXT-007 | Reject inventory for not-ready source | A not-ready source cannot create scan, inventory, extraction, or audit state changes. |

## Deterministic Signal Detection Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| SIGNAL-001 | Start a full scan | The running scan includes `signalDetection.status = pending` and the `detecting_signals` stage after `extracting_content`. |
| SIGNAL-002 | Complete a full scan | The completed scan includes detector rules version/hash, evidence requirements, evaluated evidence candidates, detected/redacted signal counts, findings-with-signals count, and signal-type counts. |
| SIGNAL-003 | Verify redaction boundary | Finding details expose only redacted signal snippets and no public payload contains raw extracted text, full file bodies, page images, or unredacted personal data. |
| SIGNAL-004 | Scan completed labeled sample forms without email addresses | Training, IT access, incident, expense, supplier, HR, identity, education, health, special-category, family/minor, credential, online/device, location, vehicle, and financial fields can produce findings while snippets expose only labels and redaction markers. |
| SIGNAL-004A | Scan deterministic regex-friendly identifiers | Email, phone, SSN/NINO, IP, MAC, UUID, personal-profile URL, account handle, coordinates, Luhn-valid payment cards, and IBAN-like values produce redacted signals without emitting matched values. |
| SIGNAL-004B | Sanitize persisted evidence anchors | When a restored signal includes stale raw anchor text, the public response keeps selector and fallback labels but replaces anchor text with the redacted snippet. |
| SIGNAL-005 | Verify policy evidence requirements | `signalDetection.evidenceRequirements` matches the active policy pack evidence requirements when available. |
| SIGNAL-006 | Verify evaluation traceability | Evaluation stores the signal-detection rules hash and includes `signal_detection:completed` in the quality-basis input stages. |
| SIGNAL-007 | Verify resource and cost boundary | Signal detection keeps model calls and estimated paid-service cost at zero. |
| SIGNAL-008 | Reject signal detection for not-ready source | A not-ready source cannot create scan, extraction, signal-detection, finding, audit, metric, or evaluation state changes. |

## Context and Risk Judgment Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| CTXRISK-001 | Start a full scan | The running scan includes `contextRisk.status = pending` and the `judging_context_risk` stage after `detecting_signals`. |
| CTXRISK-002 | Complete a full scan | The completed scan includes a completed `contextRisk` summary with assessed evidence, context, risk, retention-review, and human-review counts. |
| CTXRISK-003 | Verify policy-pack traceability | `contextRisk.policyPackVersion` matches the active governance policy pack and evaluation stores a context-risk rules hash. |
| CTXRISK-004 | Verify legal boundary | `legalConclusionProvided` remains `false`, and UI-facing copy does not present the automated judgment as legal advice. |
| CTXRISK-005 | Verify raw-content boundary | Context/risk warnings and summaries do not contain raw extracted text, file bodies, page images, or unredacted personal data. |
| CTXRISK-006 | Verify resource and cost boundary | Context/risk judgment keeps model calls and estimated paid-service cost at zero. |
| CTXRISK-007 | Reject context/risk for not-ready source | A not-ready source cannot create scan, inventory, extraction, signal-detection, context/risk, or audit state changes. |

## Owner Routing and Assignment Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| OWNROUTE-001 | Start a full scan | The running scan includes `ownerAssignment.status = pending` and the `assigning_owner` stage after `judging_context_risk`. |
| OWNROUTE-002 | Complete a full scan | The completed scan includes a completed `ownerAssignment` summary with assigned, direct-owner, Master of Data fallback, escalation, and unowned counts. |
| OWNROUTE-003 | Verify accountability traceability | `ownerAssignment.policyPackVersion` and `organizationModelVersion` match governance config, and evaluation stores an owner-assignment rules hash. |
| OWNROUTE-004 | Verify no silent unowned findings | Completed controlled fixtures expose `unownedFindings = 0`; missing owner metadata must degrade to fallback or escalation. |
| OWNROUTE-005 | Verify audit visibility | Owner routing completion creates an audit-visible event with actor, timestamp, routed counts, and policy-pack version. |
| OWNROUTE-006 | Verify raw-content boundary | Owner-routing warnings and summaries do not contain raw extracted text, file bodies, page images, directory secrets, or unredacted personal data. |
| OWNROUTE-007 | Verify resource and cost boundary | Owner routing keeps model calls and estimated paid-service cost at zero. |
| OWNROUTE-008 | Reject owner routing for not-ready source | A not-ready source cannot create scan, inventory, extraction, context/risk, owner-assignment, or audit state changes. |

## Finding Assembly and Evidence Card Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| FINDASM-001 | Start a full scan | The running scan includes `findingAssembly.status = pending` and the `assembling_findings` stage after `assigning_owner`. |
| FINDASM-002 | Complete a full scan | The completed scan includes a completed `findingAssembly` summary with assembled findings, evidence cards, redacted signals, missing-card count, denied-action count, and policy-pack version. |
| FINDASM-003 | Verify scan continuity | Completed finding rows and details use the completed scan ID and are generated from previous stage summaries instead of disconnected static rows. |
| FINDASM-004 | Verify evidence-card completeness | Every assembled finding detail has at least one redacted signal, policy context, owner assignment, retention status, action boundary, and audit timeline. |
| FINDASM-005 | Verify no legal conclusion | `legalConclusionProvided` remains `false`, and UI-facing copy presents evidence cards as human-review support. |
| FINDASM-006 | Verify raw-content boundary | Evidence snippets do not expose raw extracted text, file bodies, page images, unredacted personal data, or full financial identifiers. |
| FINDASM-007 | Verify ownerless fallback | Missing source owner metadata routes evidence cards to escalation instead of leaving findings unowned. |
| FINDASM-008 | Verify audit and evaluation traceability | Finding assembly creates an audit-visible event and evaluation stores a finding-assembly rules hash. |
| FINDASM-009 | Verify resource and cost boundary | Finding assembly keeps model calls and estimated paid-service cost at zero. |
| FINDASM-010 | Open a finding detail from the Findings list | The top title hierarchy reads `Findings / Finding Detail`; `Findings` is hover-underlined and navigates back to `/findings`, while `Finding Detail` is the non-clickable current level. |
| FINDASM-010 | Reject assembly for not-ready source | A not-ready source cannot create scan, inventory, extraction, context/risk, owner-assignment, finding-assembly, finding, evidence-card, or audit state changes. |

## Review Support and Permission Boundary Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| REVIEW-001 | Start a full scan | The running scan includes `reviewSupport.status = pending` and the `preparing_review_support` stage after `assembling_findings`. |
| REVIEW-002 | Complete a full scan | The completed scan includes a completed `reviewSupport` summary with supported finding count, decision count, reason count, checklist count, transfer count, escalation count, denied action count, and policy-pack version. |
| REVIEW-003 | Verify finding-specific support | Review support for an assembled finding includes allowed decisions, checklist items, transfer options, escalation options, and permission-boundary denial reasons derived from governance data. |
| REVIEW-004 | Verify all P0 decisions | Allowed reviewer support can show `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate`. |
| REVIEW-005 | Verify reason requirement | Every available review decision requires a human reason before submission. |
| REVIEW-006 | Verify permission denial | A denied actor receives no review decisions and a review attempt is rejected without state changes. |
| REVIEW-006A | Open review support for an assigned finding | Transfer options come from active Workspace members rather than static demo delegation rows. |
| REVIEW-007 | Verify target validation | Reassign and escalate decisions require a target owner or escalation queue. |
| REVIEW-008 | Verify no real deletion | `execute_real_deletion` remains a denied action with a visible reason. |
| REVIEW-009 | Verify audit and evaluation traceability | Review support exposes a rules hash that evaluation preserves while keeping model calls and estimated paid-service cost at zero. |
| REVIEW-010 | Verify raw-content boundary | Review support does not expose raw extracted text, file bodies, page images, credentials, hidden permission data, or unredacted personal data. |
| REVIEW-011 | Reject support for not-ready source | A not-ready source cannot create scan, inventory, extraction, context/risk, owner-assignment, finding-assembly, review-support, permission-boundary, finding, evidence-card, or audit state changes. |

## Human Review Decision Handling Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| HREV-001 | Submit allowed delete candidate decision | The finding status becomes `delete_candidate`, one review record and one audit event are created, and `deletionExecuted` remains `false`. |
| HREV-001A | Submit delete candidate without explicit deletion-candidate confirmation | The request is rejected and no finding, audit, metric, source, or deletion state changes. |
| HREV-002 | Submit allowed retain decision | The finding status becomes `retained`, the list and detail retention state becomes `retained_until_review`, the reason and retention review date are recorded, and no source file is changed. |
| HREV-003 | Submit false positive correction | The finding status becomes `false_positive`, the reason is preserved for audit and evaluation context, and detector rules are not changed. |
| HREV-004 | Submit owner reassignment | The finding status remains reviewable as `assigned`, the delegated owner is recorded, and the audit event names the transfer target. |
| HREV-005 | Submit escalation | The finding status becomes `escalated`, the escalation queue is recorded, and the audit event names the queue target. |
| HREV-006 | Reject denied actor or denied decision | No finding, source, audit, metric, or evaluation state changes. |
| HREV-007 | Reject missing reason or checklist acknowledgement | No finding, source, audit, metric, or evaluation state changes. |
| HREV-008 | Reject retain without retention review date | No finding, source, audit, metric, or evaluation state changes. |
| HREV-009 | Reject transfer or escalation without supported target | No finding, source, audit, metric, or evaluation state changes. |
| HREV-010 | Repeat command with same idempotency key | The command is treated as already accepted and does not create duplicate audit events or metric increments. |
| HREV-011 | Verify audit and metrics | Accepted decisions include actor, timestamp, decision, reason, resulting status, policy-pack version, permission-boundary fingerprint, review-support rules fingerprint, backlog movement, and outcome counters. |
| HREV-012 | Verify evaluation and cost boundary | Human-review decision handling preserves a rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost. |

## Audit Event Recording Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| AUDIT-001 | Complete a full scan | The scan pipeline ends with `recording_audit_events`, and the audit summary counts scan, finding, system, and human events without raw content exposure. |
| AUDIT-002 | Review global audit list after scan completion | Scan start, scan completion, owner assignment, finding assembly, finding assembled, and finding assigned events use the same structured audit-event shape. |
| AUDIT-003 | Submit an accepted review decision | The finding timeline, global audit list, scan audit summary, audit metrics, and evaluation traceability update together. |
| AUDIT-004 | Submit a review reason containing obvious sensitive values | Public audit reason text masks emails, IBAN-like values, long numbers, and control characters. |
| AUDIT-005 | Submit denied, incomplete, stale, unknown, or duplicate commands | No duplicate audit events or audit metric increments are created. |
| AUDIT-006 | Review deletion boundary | Audit events may record `delete_candidate`, but `deletionExecuted` remains `false` and no source-file, connector, retention-label, or access-control mutation occurs. |

## Incremental Delta Scan Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| DELTA-001 | Start delta scan from completed full-scan baseline | The selected scan-ready source creates a running delta scan with baseline ID, source snapshot, inventory fingerprint, changed counts, partial warnings, and a `delta_scan_started` audit event. |
| DELTA-002 | Start delta scan without completed baseline | No scan, audit, finding, metric, or evaluation state changes, and the user receives a neutral baseline-unavailable message. |
| DELTA-003 | Start delta scan with mismatched explicit baseline | The command is rejected without state changes. |
| DELTA-004 | Observe running delta pipeline | The pipeline exposes `comparing_delta_baseline` before changed-file inventory and extraction. |
| DELTA-005 | Complete delta scan | Only changed files are processed, changed findings use the delta scan ID, unchanged files are carried forward, and missing files are represented as inventory changes. |
| DELTA-006 | Verify no deletion boundary | `missingFilesTreatedAsDeleted` and `deletionExecuted` remain `false`, and no audit event executes real deletion. |
| DELTA-007 | Verify downstream continuity | Completed delta output updates context/risk, owner routing, finding assembly, review support, audit recording, metrics, and evaluation together. |
| DELTA-008 | Verify evaluation and cost boundary | Evaluation preserves a delta rules hash, deterministic reproducibility, throughput, zero model calls, and zero estimated paid-service cost. |

## Admin Metrics Aggregation Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| METRICS-001 | Start a full scan | Running metrics include `aggregation.status = partial`, upstream input-stage statuses, scan coverage, risk, owner, audit, safety, and zero-cost fields. |
| METRICS-002 | Complete a full scan | Completed metrics aggregate scan coverage, risk queue, owner backlog, review outcomes, audit evidence, evaluation linkage, and resource cost from prior stage summaries. |
| METRICS-003 | Complete a delta scan | Delta aggregate metrics include baseline, changed, processed, carried-forward, and missing counts while keeping `missingFilesTreatedAsDeleted = false` and `deletionExecuted = false`. |
| METRICS-004 | Submit an accepted review decision | Owner backlog, outcome counters, audit counts, throughput inputs, and evaluation-linked aggregation update exactly once. |
| METRICS-005 | Reject scan or review command | Metrics remain unchanged together with source, finding, audit, and evaluation state. |
| METRICS-006 | Verify safety and cost boundary | Aggregation keeps raw-content, legal-conclusion, deletion-execution, model-call, and estimated-cost boundaries visible and safe. |
| METRICS-007 | Verify reproducibility | Evaluation stores `adminMetricsRulesHash` matching the metrics aggregation fingerprint. |
| METRICS-008 | Review Dashboard management indicators | Dashboard displays owner completion, risk queue, audit evidence, metric basis, and cost without raw source content or legal conclusions. |

## Evaluation Metrics Generation Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| EVALGEN-001 | Complete a full scan | Evaluation computes precision, recall, F1, reproducibility, throughput, resource intensity, confusion-matrix counts, scenario-level metrics, review-throughput context, risk-progress fields, and an evaluation-rules fingerprint. |
| EVALGEN-002 | Verify upstream traceability | Evaluation preserves dataset hash, scanner version, detector rules, config hash, policy-pack version, context/risk, owner, finding, review-support, audit, admin-metrics, and finding fingerprints. |
| EVALGEN-003 | Verify scenario-level quality | Scenario metrics expose per-family precision, recall, F1, false positives, false negatives, unsupported-file context, and OCR-deferred context where available. |
| EVALGEN-004 | Complete a delta scan | Evaluation computes changed-file quality context and preserves baseline, carried-forward, missing-file, and no-deletion boundaries. |
| EVALGEN-005 | Submit an accepted review decision | Review-throughput and risk-progress evaluation fields refresh exactly once while scan-quality precision, recall, and F1 remain stable. |
| EVALGEN-006 | Reject scan or review command | Evaluation remains unchanged together with metric, audit, source, and finding state. |
| EVALGEN-007 | Verify safety and cost boundary | Evaluation keeps raw-content, legal-conclusion, deletion-execution, model-call, estimated-cost, and paid-service boundaries visible and safe. |
| EVALGEN-008 | Review Evaluation page | The page renders scan quality, confusion matrix, scenario metrics, resource intensity, reproducibility, and safety boundaries without raw source content or legal conclusions. |

## File Review Editor Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| FILEREVIEW-001 | Open file review from Finding Detail | The editor opens for the finding file and focuses the first available redacted evidence anchor. |
| FILEREVIEW-002 | Open file review from an evidence card | The editor opens with that evidence anchor selected. |
| FILEREVIEW-003 | Select another evidence anchor | The active redacted preview highlight changes to the selected anchor. |
| FILEREVIEW-004 | Review redaction boundary | The editor shows masked snippets and fallback location labels without raw sensitive values or file bodies. |
| FILEREVIEW-005 | Close file review | The user returns to Finding Detail without changing scan, finding, source-file, or review state. |
| FILEREVIEW-006 | Review a contract evidence anchor | The editor uses `signal.evidenceAnchor` redacted text, selector type, PDF page, page-local offsets, estimated PDF page-region labels, and OCR image-region labels before falling back to legacy page/snippet data. |
| FILEREVIEW-007 | Review source-region focus | The editor maps PDF bottom-left page regions and OCR top-left image regions into one scalable redacted focus box without exposing raw source values. |
| FILEREVIEW-008 | Open Finding Detail as a view-only actor | File review and Open at evidence controls are disabled and the current permission-boundary reason is visible. |
| FILEREVIEW-009 | Open Finding Detail as a workspace reviewer | A workspace actor with `review_findings` authority can open file review even when the finding-level review-support actor is different. |
| FILEREVIEW-010 | Review source-preview package summary | The editor consumes `sourceReviewPreview`, shows the redaction and raw-boundary state, and uses backend page-region data for the same visual focus geometry without raw source values. |
| FILEREVIEW-010A | Review redacted source-context windows | The editor shows the active anchor's redacted source-context window, highlights the redacted marker, and does not display raw source values. |
| FILEREVIEW-011 | Load local mock findings after scan assembly | The assembled mock finding detail preserves the contract source-review preview package so browser QA can exercise the same redacted preview summary as the server payload. |

## Public Homepage Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| HOME-001 | Visit `/` | The public project homepage renders without the internal app shell. |
| HOME-002 | Open dashboard from homepage | The user navigates to `/dashboard`, and the internal app shell dashboard renders. |
| HOME-003 | Scroll homepage | Parallax layers move when reduced motion is not requested, while content remains readable. |
| HOME-004 | Review homepage claims | The page explains discovery, evidence, routing, review, audit, governance, and evaluation without claiming full legal compliance. |

## Remote Preview Deployment Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| DEPLOY-001 | Build frontend for remote preview | `npm run build` completes successfully before upload. |
| DEPLOY-002 | Visit `https://founder-force.uk/` | Caddy returns the DataSentinel frontend HTML from the active release after DNS points to `agent-us`. |
| DEPLOY-003 | Visit `https://founder-force.uk/dashboard` directly | Caddy falls back to `index.html`, and the frontend can render the dashboard route after DNS points to `agent-us`. |
| DEPLOY-004 | Call `https://founder-force.uk/api/health` | Caddy proxies to the loopback P0 API server and returns a contract health envelope. |
| DEPLOY-005 | Review remote service boundary | The preview exposes only static frontend assets plus the P0 API, may use the approved local SQLite state file, and does not start OAuth, Microsoft Graph, tenant, production database, queue, production connector, or deletion services. |
| DEPLOY-006 | Review rollback path | A saved Caddyfile backup, release symlink, and removable API service make rollback possible without changing product code. |

## Future Behavior Test Themes

These are not implementation tests yet. They define the areas that future tests should cover:

- App shell behavior for page-title-focused top bar, top-right timestamped notification center, auto-dismissing latest-message preview that does not mutate the notification center, dismiss/clear notification actions, no bottom toast overlay, top-left workspace menu visibility, bottom-left account menu visibility, sidebar collapse, menu open, keyboard close, and account-menu server connection display.
- Dark-theme visual behavior for Workspace switcher rows, Workspace creation dialog fields/actions, Workspace Admin KPI/form controls, sidebar subnavigation, and account-menu language selector readability.
- Public homepage behavior for root-route rendering, dashboard navigation, scroll-linked parallax, and reduced-motion fallback.
- File review behavior for format-specific anchors, renderer fallback, keyboard navigation, and redacted preview highlighting.
- Full-scan behavior with controlled sample files.
- Classification behavior for GDPR-relevant evidence.
- Owner-routing behavior when owner metadata is present or missing.
- Human-review decisions for delete, retain, mask, archive, and escalate.
- Audit-event behavior for every visible state transition.
- Delta-scan behavior for unchanged, changed, new, and deleted files.
- Evaluation behavior for precision, recall, F1, reproducibility, throughput, and resource intensity.
- Governance behavior for policy-pack changes, org model changes, task transfers, and permission boundaries.
