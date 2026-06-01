# Acceptance Criteria

## Repository Initialization

The initialization is complete when:

- The GitHub repository is public.
- The local repository has a clean `main` branch after the initial commit is pushed.
- The repository contains English-language planning documents for BRD, MRD, PRD, TRD, DesignSpec, TestCase, and acceptance criteria.
- The repository does not contain implementation code, runtime dependencies, secrets, generated build artifacts, or copied source data from the challenge PDF.
- The project README clearly states the project thesis, current scope, and non-goals.
- The listed teammates are invited as GitHub collaborators.

## Project Readiness

The project is ready for implementation only when:

- The team approves the initial requirements and acceptance criteria.
- The first implementation task has a narrow, testable scope.
- Any new workflow, external API integration, permission model, or deletion mechanism has a design note with state transitions, failure paths, rollback paths, and primitive acceptance criteria.

## Parallel Delivery Contract Readiness

Frontend-backend parallel development may start when:

- `docs/API_CONTRACT.md` defines the P0 endpoints, envelope, tolerance rules, error format, and state machines.
- `contracts/openapi.yaml` and `contracts/schemas/` define the machine-readable contract.
- `contracts/mocks/` contains payloads for sources, scan status, findings list, finding detail, audit events, admin metrics, and latest evaluation.
- `docs/DELIVERY_WORKFLOW.md` defines frontend, backend, contract, and QA responsibilities.
- `AGENTS.md` and `.github/copilot-instructions.md` tell teammate AI tools how to follow the contract.
- No frontend or backend implementation code is introduced before the first scoped implementation task.
- `docs/GOVERNANCE_CONFIG.md` defines policy packs, organization model, permission boundaries, review support, and enterprise change scenarios.
- `docs/GDPR_SAMPLE_REFERENCES.md` records how the organizer sample repository is used without vendoring PDFs.

## Frontend Surface Contract Readiness

Frontend surface work is ready for final implementation and QA planning when:

- `docs/FRONTEND_CONSOLE_CONTRACT.md` defines the internal console functional contract across app shell, dashboard, sources, scan pipeline, findings, finding detail, file review, review support, human review, audit, evaluation, governance, permissions, states, privacy boundaries, and responsive/accessibility obligations.
- `docs/WEBSITE_HOMEPAGE_CONTRACT.md` defines the public homepage content contract across product thesis, workflow highlights, sample source, evidence/redaction, owner routing, human review, audit, evaluation, governance, safety boundaries, calls to action, reduced motion, and responsive/accessibility obligations.
- Both frontend surface contracts avoid prescribing visual design, component implementation, final art direction, framework internals, or unapproved dependencies.
- Both frontend surface contracts remain compatible with `docs/API_CONTRACT.md`, `contracts/openapi.yaml`, `contracts/mocks/`, `docs/DesignSpec.md`, and the current P0 acceptance criteria.
- Both frontend surface contracts keep developer-facing documentation and engineering instructions English-only, allow user-facing interface copy to be localized through reviewed frontend dictionaries, keep deletion simulated, avoid legal-advice or full-compliance claims, and avoid production Microsoft Graph, OAuth, tenant, AI, parser, OCR, database, queue, or deletion commitments.

## Public Upload Analysis Entry Acceptance

The public website upload-analysis entry is accepted when:

- `docs/design/public-upload-analysis-preview.md` defines the implemented problem, research basis, options, state machine, impact surface, rollback path, and primitive acceptance criteria.
- `contracts/openapi.yaml`, `docs/API_CONTRACT.md`, `contracts/schemas/public-analysis.yaml`, and `contracts/mocks/publicAnalysisCapacity.json` / `contracts/mocks/publicAnalysisResult.json` define the same public-analysis fields and states.
- The root homepage presents a prominent single-file analysis entry before requiring the full Workspace console, and the entry clearly explains its website boundary without sounding like prelaunch placeholder copy.
- The entry explains that owner assignment, Workspace cases, audit trails, and evaluation history live in the governed Workspace and links users to `/dashboard` from the analysis section.
- The entry displays real capacity data from `/api/public-analysis/capacity`, including active analyses, available slots, waiting-at-intake count, and the file-size limit.
- The entry accepts exactly one uploaded file per browser analysis session at a time, rejects files larger than 10 MB, and allows at most 10 active public analyses globally in the API process.
- Oversized, duplicate-active, capacity-full, unsupported, failed, completed, and start-over states are visible and non-destructive.
- Accepted analyses return a concise redacted summary with detected categories, risk level, redacted evidence snippets, warnings, review guidance, and accountable next steps.
- The frontend can render optional backend-provided processing stages, Workspace handoff readiness, next steps, and boundary notes without requiring a contract version bump.
- Entry output does not expose raw sensitive values, provide legal advice, claim full GDPR compliance, execute deletion, or imply production tenant or Microsoft Graph integration.
- The public entry remains separate from the full Workspace console and does not create Workspace sources, findings, audit events, or deletion actions.

## Fumadocs User Documentation Acceptance

The user-facing documentation surface is accepted when:

- `docs/design/fumadocs-user-documentation.md` defines problem, research basis, options, state machine, impact surface, rollback path, and primitive acceptance criteria.
- `docs-site/` contains a separate Fumadocs and Next.js documentation app rather than changing the existing Vite console framework.
- The documentation app can be installed and built from `docs-site` with npm scripts.
- The docs sidebar exposes task-oriented pages for quick start, accounts and Workspaces, sources, dashboard and scans, findings and review, audit and evaluation, governance, safety boundaries, and FAQ.
- The docs sidebar does not duplicate task pages with separate top-level shortcut links for the same destinations.
- The docs homepage presents a prominent quick-start CTA, visible first-review workflow, task cards, role-oriented paths, and safety boundary summary.
- The docs homepage renders without the Fumadocs sidebar, while nested docs pages keep sidebar navigation.
- The Quick Start page presents the first review loop as a scannable step path with readiness checks and next-page links.
- Key user-guide pages include cropped, non-sensitive product screenshots plus tables that explain visible fields, metrics, and next actions.
- Screenshot assets are served from the docs prefix and do not require a root-level static route that could collide with the product frontend.
- User-facing docs explain lawdit's source registration, full-scan, findings review, audit, evaluation, governance, Workspace, and permission-boundary workflows without requiring readers to understand API contracts.
- User-facing docs state that lawdit does not provide legal advice or claim full GDPR compliance.
- User-facing docs state that deletion is simulated in P0 and source-registration deletion does not delete external files.
- User-facing docs explain redacted evidence, no raw-content exposure, visible allowed and denied actions, account versus Workspace authorization, and optional AI boundaries.
- User-facing docs do not invent API fields, endpoints, production Microsoft Graph or tenant integrations, real deletion behavior, provider-token persistence, legal conclusions, or hidden permission powers.
- `https://founder-force.uk/docs` serves the Fumadocs user guide without changing the `founder-force.uk` prefix.
- The console account-menu Docs row navigates to the deployed Fumadocs guide instead of rendering an internal placeholder.
- Docs search uses `/docs/api/search` and does not intercept or replace the product `/api/*` backend route.
- Generated Fumadocs artifacts and build outputs remain ignored.

## Backend Post-Source Planning Readiness

Backend work after sample source connection is ready to break into scoped tasks when:

- `docs/design/backend-post-source-execution-plan.md` and `docs/design/backend-post-source-stage-details.md` define the planned stages from full scan through evaluation metrics.
- The planning documents cover scan orchestration, inventory and extraction, deterministic signal detection, context and risk planning, owner routing, finding assembly, review support, human review, audit logging, delta scan planning, admin metrics, and evaluation.
- The planning documents define state transitions, guard conditions, side effects, failure paths, partial-data behavior, and rollback path.
- The planning documents map the organizer sample families to evidence, context, owner-routing, and review planning assumptions without making legal conclusions.
- The planning documents stay compatible with `docs/API_CONTRACT.md`, `contracts/openapi.yaml`, and existing mock fixtures without requiring a contract version bump.
- The planning documents keep raw sensitive text out of public responses and keep deletion simulated.
- `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, and `docs/TestCase.md` reference the post-source backend planning sequence.

## P0 Product Acceptance

The first implementation milestone is accepted when:

- The root route `/` shows a public project homepage that introduces lawdit and links to the internal dashboard route at `/dashboard`.
- The frontend app shell shows the current page title or route hierarchy plus notifications in the top bar, lets intermediate title levels show a hover underline and navigate back to their route, keeps workspace switching in the top-left sidebar control, exposes logged-in account controls from the bottom-left sidebar account menu, and lets users collapse or expand the sidebar.
- Light and dark themes keep the Workspace switcher, Workspace creation dialog, sidebar navigation and subnavigation, Workspace Admin controls, and account-menu language selector readable without light-only backgrounds or low-contrast text.
- The top-right notification button opens a session notification center; operation feedback is timestamped, newest-first, dismissible, and does not render as a bottom toast.
- New operation feedback appears in a small top-right notification preview, auto-dismisses after a few seconds, and does not open, close, clear, dismiss, or reorder the session notification center.
- Connected console sessions refresh Workspace-scoped read data in the background so scan, review, source, member, and group changes become visible on already-open pages without a manual browser refresh.
- Scan-completed notifications appear only after the same visible scan transitions from `running` to `completed`; a fixed timeout or still-running scan must not emit a completed notification.
- On desktop, the sidebar can be resized with a pointer or keyboard-accessible separator, collapses when dragged below the configured threshold, caps expansion at the configured maximum width, and keeps the content area aligned without overlap.
- Account menu actions open local utility routes or local UI states for account settings, theme, language preference, feedback, homepage, changelog, help, docs, platform status, prototype plan, and session boundary without adding production authentication, billing, support, monitoring, tenant, external translation service, or external feedback integration.
- The account menu platform status tile shows whether the frontend data provider is checking, connected to, or disconnected from the project API server; it must not show a static all-systems-normal message when the server is unavailable.
- The account menu language preference lists EU language options, persists the selected code locally, updates core user-facing UI copy through static frontend dictionaries, keeps developer-facing docs and code comments English-only, and does not call a backend or translation service.
- A full scan can be started on a controlled sample source or a prelaunch connected source.
- Source registration can optionally assign an active Workspace member as the direct Source owner, and Workspace admins can edit that owner without mutating external source files.
- Starting a full scan uses an explicit `sourceId`, is allowed only for the controlled `mock_ready` sample source or approved prelaunch source types, and records scan-start and scan-completion audit events in the workflow.
- The Dashboard groups scanned files, flagged files, scanned volume, progress, scan time, review backlog, high-risk count, retention review count, and owner routing into clear scan, review, and pipeline summaries.
- While a scan is running, the Dashboard latest-scan panel shows active loading and refreshes status/progress from the connected project server instead of staying stale until browser refresh.
- A responsible user can list assigned findings.
- A Workspace Admin membership alone does not grant business review-decision authority for findings not assigned to that actor.
- A finding detail view shows redacted evidence, signals, risk explanation, owner assignment, retention status, and audit timeline, and the top title hierarchy shows `Findings / Finding Detail` with `Findings` linking back to the findings list.
- Opening a finding detail route loads the requested finding detail by `findingId`, so non-primary findings show full redacted evidence, owner, policy, file, and audit context when the backend provides it.
- A reviewer with current finding review authority, or a workspace actor with `review_findings` authority, can open a redacted file review surface from a finding detail view and focus the relevant sensitive evidence location without exposing raw sensitive values.
- A view-only actor sees the file review and evidence navigation controls disabled with the current permission-boundary reason instead of receiving silent access or a hidden capability.
- The file review surface consumes optional `signal.evidenceAnchor` data, displays PDF page, page-local offset, CSV/XLSX/ODS table-cell context, ZIP member context, DOCX/PPTX/ODT/ODP/EML/HTML/XML/JSON/JSONL/NDJSON structure-path context, estimated PDF page-region context, OCR image-region context, redacted source-context windows, and a source-derived visual focus box when region geometry is provided; it falls back to redacted line/page labels when precise selectors are unavailable.
- Finding details may include a redacted `sourceReviewPreview` package that groups evidence anchors into page regions, redacted source-context windows, text ranges, table cells, and structure blocks for the same file-review interaction while keeping `rawContentExposed = false` and `pageImagesExposed = false`.
- A human reviewer can record delete candidate, keep with reason, false positive, reassign, or escalate decisions.
- The review decision dialog never renders an empty decision selector; it either lists allowed decisions or shows a disabled no-available-decisions state tied to the visible permission boundary.
- Every review decision creates an audit event with actor, timestamp, reason, and resulting status.
- A `keep_with_reason` review changes the finding status to `retained` and the displayed retention state to a retained review-date state, so retained findings do not continue to show `Needs Review` in the findings table.
- A delta scan can run as a changed-file-only workflow against a completed full-scan baseline.
- Evaluation metrics show precision, recall, F1, reproducibility, throughput, and resource intensity.
- Deletion remains simulated.

## Prelaunch Account Acceptance

The Google/GitHub account system is accepted when:

- The design notes `docs/design/prelaunch-account-system.md` and `docs/design/account-scoped-prelaunch-state.md` define problem, research basis, options, state machine, impact surface, rollback path, and primitive acceptance criteria.
- `contracts/openapi.yaml`, `contracts/schemas/common.yaml`, and `docs/API_CONTRACT.md` document provider list, login redirect, callback, session read, and logout endpoints.
- Runtime configuration uses ignored environment variables for Google client ID/secret, GitHub client ID/secret, redirect base URL, session secret, cookie security, and auth-required mode.
- Prelaunch deployments can set `LAWDIT_ENABLE_DEMO_FIXTURES=false` so the signed-in console starts from empty state and configured local sources instead of seeded demo findings.
- When a persistent SQLite host switches to `LAWDIT_ENABLE_DEMO_FIXTURES=false`, historical seeded demo source rows and demo workflow documents are removed while real registered local sources and account/session records remain.
- `GET /api/auth/providers` lists Google and GitHub setup state without exposing secrets.
- Google and GitHub login are initiated only from the backend and provider secrets never reach the frontend.
- GitHub login uses state plus PKCE challenge/verifier; callback state mismatch creates no session.
- Successful provider callback creates a first-party HttpOnly session cookie and a safe local user profile.
- `/api/auth/session` returns authenticated state and safe profile fields without provider tokens.
- `POST /api/auth/logout` revokes the local session and clears the session cookie.
- SQLite-backed prelaunch Sources, scans, findings, audit events, metrics, and evaluation state are scoped to the current session user.
- A different signed-in account cannot list, delete, scan, connect-test, review, or open another account's Source or Finding.
- Legacy global SQLite source and workflow rows are quarantined outside authenticated account scopes instead of being exposed to every signed-in user.
- The unauthenticated console shows a minimal, centered sign-in page with lawdit branding and only Google and GitHub branded provider buttons instead of seeded demo findings or explanatory onboarding copy.
- The authenticated console account menu uses the current session profile instead of a hard-coded demo actor.
- Authentication does not grant real deletion, Microsoft Graph access, tenant access, legal conclusions, or hidden permission powers.
- Automated backend tests cover provider setup, unconfigured rejection, state mismatch rejection, session read, logout, auth-required workflow protection, account-scoped Sources, and account-scoped findings.

## Workspace Admin Permission Acceptance

The Workspace administrator and user-group system is accepted when:

- `docs/design/workspace-admin-permission-system.md` defines problem, research basis, options, state machine, impact surface, rollback path, and primitive acceptance criteria.
- `contracts/openapi.yaml`, `contracts/schemas/workspace.yaml`, `contracts/mocks/workspaceDirectory.json`, `contracts/mocks/workspaceAdmin.json`, `contracts/mocks/workspaceGroup.json`, and `docs/API_CONTRACT.md` document workspace directory, admin summary, Workspace profile settings, owner transfer, Workspace deletion, group management, invitation creation, and invitation acceptance endpoints.
- A newly created signed-in account has no Workspace membership by default and sees an invitation-required state rather than seeded Workspace access.
- A signed-in account can open a Workspace creation dialog from the left Workspace menu or no-Workspace state, enter Workspace settings, create a Workspace, and automatically becomes an active `workspace_owner` and `workspace_admin` member of that Workspace.
- Creating or accepting a Workspace makes that Workspace current for the account, and a member can switch current Workspace from the left Workspace menu.
- Sources, scan state, findings, audit events, metrics, and evaluation are isolated by the current Workspace; creating or switching to a Workspace does not copy operational data from another Workspace.
- A seeded or invited Workspace admin can open `/workspace/admin` and inspect compact member and group summaries, pending invite links, permission boundaries, and workspace-level charts.
- A Workspace admin with `manage_workspace_settings` can customize the Workspace name and introduction near the bottom of `/workspace/admin`; this does not change Workspace membership or operational scope, and the Danger Zone remains the final page section.
- A Workspace admin can open `/workspace/admin/members` from the sidebar or the Admin page Members panel and search, filter, group, and sort Workspace members by member text, group, status, join date, and last activity.
- A Workspace admin can open `/workspace/admin/groups` from the sidebar or the Admin page Group controls panel and manage Workspace groups on a dedicated page.
- `/workspace/admin`, `/workspace/admin/members`, and `/workspace/admin/groups` use concise operational copy without explanatory helper paragraphs or collapsed group-description text, while still showing Workspace description data, denied-action reasons, and deletion safety boundaries.
- A Workspace admin with `manage_workspace_members` can change another active member's Workspace groups from `/workspace/admin/members`.
- A Workspace admin with `manage_workspace_members` can remove an active member from the Workspace, except their own active membership.
- Member group changes or removals that would leave the Workspace without an active `workspace_admin` member are rejected.
- Workspace groups carry explicit permissions for workspace ownership, workspace administration, privacy review, data stewardship, and audit read-only access.
- A Workspace admin can create new Workspace groups from `/workspace/admin/groups`, set their names and permissions from the exposed permission catalog, and immediately use them in invite links.
- Workspace group controls on `/workspace/admin/groups` render collapsed by default: the new-group form is hidden behind a single button, existing groups show compact summary cards, and permission editing expands only after the admin clicks a group's edit icon.
- A Workspace admin can rename groups and change group permissions from `/workspace/admin/groups`; permission boundaries use the updated definitions.
- A Workspace admin can delete non-admin groups from `/workspace/admin/groups`; member and pending invite references to the deleted group are removed or revoked when no groups remain.
- The `workspace_owner` group cannot be invited, deleted, or stripped of the minimum owner-management permissions required for owner transfer and Workspace deletion.
- The `workspace_admin` group cannot be deleted or stripped of the minimum admin-management permissions required to avoid locking out the Workspace.
- Permission boundaries expose both allowed and denied Workspace actions, including a visible denial for real deletion.
- The left workspace menu is backed by Workspace data, shows the current Workspace name and introduction, shows current membership groups only in the compact right-side pill when available, shows legacy pending invitations or no-Workspace state when unavailable, and opens the Workspace creation dialog from its create action.
- Sidebar links are hidden when the current Workspace permission boundary does not allow the destination, and expandable sidebar groups show a right-side chevron.
- A Workspace admin can generate a pending invite link with one or more non-owner Workspace groups and can copy each pending invite link from the invitations list.
- A signed-in account that opens the invite link sees a concise invitation page with Workspace name, introduction, owner, member count, and invited group before accepting, and becomes an active Workspace member exactly once after acceptance.
- Already-member, duplicate-acceptance, expired, revoked, or non-admin invitation actions do not create membership or privilege changes.
- A Workspace owner can transfer owner authority by typing another active member's exact email; the transfer button remains disabled until the email matches, then a second confirmation is required before the target receives `workspace_owner` and `workspace_admin` and the previous owner loses `workspace_owner`.
- Only a Workspace owner can delete a Workspace, and deletion requires typing the exact Workspace name plus a second confirmation before submission.
- Workspace deletion removes the Workspace from visible directories, removes active memberships, revokes pending invite links, clears affected current-Workspace selections, and never deletes external source files or production tenant resources.
- Admin charts render deterministic management data from existing metrics plus Workspace membership and invitation summaries without adding a chart dependency.
- Workspace permissions do not grant production tenant access, Microsoft Graph access, source-file deletion, legal advice, full GDPR-compliance claims, or hidden powers.
- Automated tests cover Workspace-less accounts, Workspace creation, admin summary access, Workspace profile customization, group customization, member management, invitation creation, invitation acceptance, owner transfer, and Workspace deletion confirmation.

## Prelaunch Source Input Acceptance

Google Drive and direct-link source input are accepted when:

- The design notes `docs/design/google-drive-source-integration.md`, `docs/design/google-drive-account-binding.md`, `docs/design/pdf-source-text-extraction-and-source-deletion.md`, `docs/design/local-format-recognition-difficulty.md`, `docs/design/archive-container-extraction.md`, `docs/design/image-video-recognition-boundary.md`, and `docs/design/final-engine-hardening-boundary-register.md` define problem, research basis, options, state machine, impact surface, rollback path, and primitive acceptance criteria for source input and final hardening boundaries.
- `contracts/openapi.yaml`, `contracts/schemas/common.yaml`, `contracts/schemas/source-scan.yaml`, and `docs/API_CONTRACT.md` document Google Drive Picker public config, account-level Drive binding status, remote-link source config, Drive selected-item config, per-scan short-lived authorization, server-side token refresh for bound accounts, and host-local conversion boundaries for legacy Office inputs.
- Runtime configuration uses ignored environment variables for Google Picker public credentials: `GOOGLE_PICKER_API_KEY` and `GOOGLE_CLOUD_PROJECT_NUMBER`.
- `/api/integrations/google-drive/picker-config` reports Picker setup state behind the prelaunch session boundary without exposing Google client secrets, provider tokens, refresh tokens, or GitHub credentials.
- `/api/integrations/google-drive/binding`, `/api/integrations/google-drive/bind/start`, `/api/integrations/google-drive/bind/callback`, and `DELETE /api/integrations/google-drive/binding` let a signed-in user connect, inspect, change, or disconnect a personal Google Drive binding without exposing access tokens, refresh tokens, client secrets, or OAuth transaction state.
- An authenticated empty prelaunch project can still register sources when there are no findings or finding detail records yet.
- The Sources page can register a `remote_file_link` with `config.url` and no fake prefilled source examples.
- The Sources page can select or clear a direct Source owner from active Workspace members during Source registration.
- The Sources page exposes an edit action for admins to change a Source owner after registration.
- The Sources page shows the current core scanner supported file types below the source inventory surface, including PDF image OCR, OCR-backed image formats, modern Office, OpenDocument, EML, ZIP, UTF-16 text, JSONL/NDJSON, transcripts, and Google export inputs.
- Remote file-link scans require HTTPS, no embedded credentials, a public-resolving host, supported BOM/charset-aware Unicode text-like content, bounded XML/JSON-like structure extraction, bounded RTF text extraction, RFC 5322/MIME email text extraction, bounded ZIP archive member extraction, a PDF text layer or bounded local PDF OCR candidate, Office Open XML or OpenDocument content, supported image files, supported transcript files, or bounded raw video media; extractable text-like files must stay within the prelaunch text-stream size limit, PDF/image/Office-like complex documents must stay within the bounded document size limit, and raw video media must stay within the bounded video size limit.
- Local and Google Drive source enumeration is bounded by the prelaunch file-count limit and reports a warning when scanning stops at that limit.
- Google Drive and Google Docs share-page URLs are rejected as direct links and must be added through Google Drive Picker.
- The Sources page can select Google Drive files or a folder through Google Picker when host credentials are configured.
- Google Picker intermediate callbacks do not close the source setup flow; picked files or folders remain visible in the Add Source dialog before registration.
- Google Drive source registration stores selected item metadata but not access tokens.
- A Google Drive source with a current in-memory Picker token or connected account-level Drive binding is presented as connected even though the source record itself stores no access token.
- Refreshing the browser after registering a Google Drive source keeps that source scan-ready when the signed-in account has a connected Drive binding.
- Add Source `Choose files` and `Choose folder` use a short-lived Picker token from the connected account-level Drive binding so Google Picker opens for the bound account without starting browser-side Google authorization.
- Account settings can disconnect or change the Google Drive binding; source registrations remain metadata-only, external Drive files are not deleted or mutated, and future scans require a new binding or per-scan Picker token after disconnect.
- Google Drive full scans require a short-lived per-scan access token or connected account-level binding; missing, expired, or refresh-failed authorization rejects the scan, puts the workflow into a failed source-unavailable state, clears visible scan-derived findings, and never falls back to local mock findings.
- PDF files with an extractable text layer can be scanned from local, direct-link, or Google Drive selected sources without storing raw PDF bodies or raw extracted text.
- XML, JSON/JSONL/NDJSON, HTML/HTM, RTF, EML, ZIP archives with supported members, DOCX, XLSX, PPTX, ODT, ODS, and ODP files can be scanned deterministically from local, direct-link, or Google Drive selected sources without storing raw structured source bodies, rich-text/email/archive source bodies, or raw extracted text.
- Bounded legacy `.doc`, `.xls`, and `.ppt` files can be scanned from local, direct-link, or Google Drive selected sources through host-local LibreOffice headless conversion without storing raw binary Office bodies or converted raw text.
- PNG, JPG/JPEG, TIFF, BMP, and WEBP image files can be scanned through host-local Tesseract OCR when `LAWDIT_OCR_MODE=local` and the host binary is available, without storing raw images or raw OCR text.
- VTT and SRT transcript files can be scanned as video transcript text, while bounded MP4, MOV, M4V, MKV, WEBM, and AVI media can be scanned through host-local FFmpeg frame extraction plus local Tesseract OCR. Missing FFmpeg, missing Tesseract, disabled local OCR, extraction failure, over-limit video, or empty frame OCR are counted as hard/OCR-deferred.
- Missing LibreOffice, conversion timeout, failed conversion, missing conversion output, empty converted text, or over-limit legacy Office files are counted as hard unsupported warnings rather than silent successes.
- Scan payloads expose recognition difficulty counts and per-format extraction counts while normal deterministic scans keep `aiAssistanceUsed = false` and `modelCalls = 0`.
- Image-only and mixed-layer PDFs use bounded local PDF OCR when `LAWDIT_OCR_MODE=local`, Tesseract, `pdftoppm`, and required language packs are available; missing tooling, empty OCR, OCR timeout, OCR failure, or unreadable PDFs are recoverable hard/OCR-deferred warnings rather than silent successes or fake findings.
- Local OCR can run bounded color-overlay preprocessing variants for difficult image/PDF pages with high-contrast text over images; public payloads still expose only redacted evidence, not raw OCR text or page images.
- The Sources page can delete a lawdit source registration, clears lawdit scan/finding state derived from that deleted registration, and the backend `DELETE /api/sources/{sourceId}` route does not delete external source files.
- Findings produced from an assigned Source are visible to the assigned owner or explicit fallback route, not every Workspace member.
- Finding review transfer options for an assigned Workspace finding come from active Workspace members exposed by current review support and must not fall back to static demo delegation targets.
- Source scanning reads file content only during scan execution and persists metadata, redacted evidence, findings, metrics, and audit events rather than raw source bodies.
- Prelaunch finding payloads and console views use safe source references or source names instead of raw external source URLs or absolute host paths.
- Automated tests cover Picker config redaction, Drive binding connect/status/disconnect token redaction, bound Picker token refresh without refresh-token exposure, persisted Drive binding scan authorization after refresh, Picker picked/cancel/pending callback handling, bound Picker launch without Google Identity Services, empty-project source registration readiness, remote-link redaction/no-raw-content behavior, Google Drive share-link rejection, safe source-reference display, PDF text-layer scanning without raw-text persistence, DOCX/XLSX/PPTX, ODT/ODS/ODP, legacy DOC/XLS/PPT conversion, EML, and ZIP deterministic extraction with difficulty counts, local image OCR with redaction, video transcript scanning, bounded raw video frame OCR with deferred fallback, source-registration deletion, Drive token failure clearing stale findings, frontend no-mock-fallback command rejection, Source owner assignment visibility, Source owner editing, review-transfer target scoping, and real findings pagination totals.

## Core Engine Corpus and Multilingual OCR Acceptance

The core business engine hardening slice is accepted when:

- `docs/design/deterministic-evidence-anchors.md` defines the evidence-anchor problem, options, state machine, impact surface, rollback path, and primitive acceptance criteria.
- `tests/fixtures/gdpr_data_samples_main/drive_manifest.json` preserves the `GDPR-data-samples-main` Google Drive folder ID, observed date, original file IDs, filenames, MIME types, and corpus roles.
- `tests/fixtures/gdpr_data_samples_main/core_multilingual_cases.json` preserves runnable multilingual source-text cases for deterministic scanner tests.
- `tests/fixtures/gdpr_data_samples_main/generated_format_challenges.json` preserves generated high-difficulty multilingual format cases, including UTF-16 text, XML, RTF, newline-delimited JSON, OpenDocument, EML email, and ZIP archive cases, without mutating Drive originals.
- `tests/fixtures/gdpr_data_samples_main/core_negative_cases.json` preserves runnable no-sensitive-info cases for clean enterprise budgets, SKUs, release configs, Markdown tables, CSV inventory rows, and operations logs so false positives are measured rather than assumed absent.
- `tests/fixtures/gdpr_data_samples_main/raw_corpus_manifest.json` locks local raw corpus copies with origin, role, byte size, SHA-256, and Drive file IDs for all files in the Drive manifest.
- `tests/fixtures/gdpr_data_samples_main/corpus_scan_report.json` records repeatable core-engine scan evidence as methods, difficulty, counts, and signal types only, without raw extracted text or raw detected values.
- `tests/fixtures/gdpr_data_samples_main/core_engine_quality_report.json` records repeatable type-level precision, recall, F1, false-positive counts, and false-negative counts across multilingual, generated-format, and no-sensitive-info oracle cases without raw source text or raw detected values.
- `tests/fixtures/gdpr_data_samples_main/engine_hardening_validation_report.json` records final-hardening validation evidence for local tests, supported-format UI proof, agent-us deployment, OCR runtime capability, and real OCR smoke tests without raw source values or provider tokens.
- `tests/fixtures/gdpr_data_samples_main/core_engine_performance_report.json` and `tests/fixtures/gdpr_data_samples_main/core_engine_performance_report_agent_us.json` record repeatable mixed-format performance evidence as aggregate throughput, peak RSS, format counts, signal-type counts, OCR-deferred counts, and signal-cap behavior without raw extracted text, raw detected values, source bodies, provider tokens, or private absolute paths.
- `tests/fixtures/gdpr_data_samples_main/live_drive_scan_report_agent_us.json` records a deployed `agent-us` Google Drive binding scan of `GDPR-data-samples-main` as aggregate extraction, `pdf_mixed` OCR, signal, finding, and source-preview counts without raw extracted text, raw detected values, source bodies, provider tokens, refresh tokens, Drive URLs, page images, or private absolute paths.
- The corpus scan report records the OCR mode, configured language list, Tesseract availability, `pdftoppm` availability, image OCR availability, and PDF OCR availability so deferred OCR cases are explainable.
- Deterministic signal detection recognizes common Chinese, EU-language, Japanese, Korean, and Arabic form labels for names, phone numbers, email, birth dates, national identifiers, tax IDs, passports, addresses, bank accounts, health data, compensation, and credentials.
- Deterministic signal detection splits inline static-text and OCR-normalized label/value sequences such as `姓名：... 电话：... 地址：...`, punctuation-missing CJK/Kana/Hangul/Arabic labels such as `姓名 ... 电话 ...`, separatorless CJK/Kana/Hangul OCR text such as `姓名王芳电话...`, and dash-delimited labels such as `Name - ...` into separate redacted signals with source-local `textPosition` anchors, while suppressing overlapping same-type regex duplicates, weaker overlapping regex classifications when stronger contextual labels already explain the value, and context-free corporate budget/SKU/numeric-log patterns that are not personal data.
- Multilingual scan output exposes only redacted snippets, signal types, counts, findings, metrics, and audit-safe metadata; raw matched values, raw extracted text, source file bodies, and page images remain outside public payloads.
- Deterministic signal detection uses bounded scan windows and per-document signal caps so large or adversarial extracted text streams cannot produce unbounded public signal payloads.
- A reproducible benchmark script measures generated challenge cases, raw corpus files, and an oversized text stream, and proves that the signal cap is enforced while normal deterministic scans keep `modelCalls = 0` and `estimatedCostUsd = 0`.
- A reproducible quality report script evaluates multilingual source-text, generated-format, and no-sensitive-info oracle cases, records aggregate type-level precision/recall/F1 plus per-case false-positive and false-negative signal types, and stores only signal-type metadata.
- A live deployed Google Drive scan can use the server-side account binding without a browser-memory Picker token, complete on `agent-us`, and record redacted aggregate scan evidence.
- Google Drive scans export Google Docs, Google Sheets, and Google Slides through explicit export profiles that preserve distinct format/method counts and redacted anchors; unsupported Google Workspace MIME types are warning-counted rather than mislabeled as generic text.
- PDF files with text layers still prefer deterministic text-layer extraction.
- The preserved PDF corpus can be scanned through the real PDF text-layer extraction path, and completed example PDFs produce redacted findings without leaking detected raw values.
- PDF files without extractable text layers can fall back to bounded host-local PDF OCR when `LAWDIT_OCR_MODE=local`, `pdftoppm`, and Tesseract are available.
- Mixed PDFs that contain extractable text-layer pages plus blank/scanned pages or image text overlays keep the text-layer pages and can OCR the bounded target pages through the host-local PDF OCR path, returning `pdf_mixed`/`pdf_text_layer_with_page_ocr` with redacted page anchors when tooling is available.
- Mixed PDFs whose target-page OCR cannot run still preserve text-layer findings, mark the document hard, increment OCR-deferred warning metadata, and do not silently claim the visual layer was scanned.
- PDF and other complex document formats use a bounded document byte budget separate from the 1 MB text-stream budget, so realistic multi-megabyte PDFs can enter extraction and signal detection.
- Local OCR can select installed Tesseract language packs through `LAWDIT_OCR_LANGS` for multilingual image and PDF OCR, and large configured language lists are split into bounded profiles so one slow/noisy all-language OCR invocation cannot suppress later candidates.
- If one OCR preprocessing candidate or language profile times out, later bounded candidates can still run; only total OCR failure is reported as OCR-deferred.
- Image OCR normalizes Tesseract TSV word joins for CJK/Kana/Hangul character-level output so labels split into single-character OCR words can still produce redacted findings and pixel `pageRegion` anchors without storing raw OCR text.
- Missing PDF OCR tooling, empty OCR, OCR timeout, or OCR failure is reported as a recoverable hard/OCR-deferred warning rather than a silent success or fake finding.
- Image OCR challenge files remain hard/OCR-deferred on hosts without Tesseract and must not be counted as successful scans or fake findings.
- Current deterministic signal payloads include redacted `textPosition` evidence anchors for normalized extracted text streams, and those anchors never expose raw matched values.
- PDF text-layer findings include page-aware anchor context with `format = pdf_text_layer`, page number, page-local source offsets, and a redacted page fallback label when scan-time page metadata is available.
- PDF text-layer findings can include estimated `pageRegion` coordinates derived from scan-time PDF text matrices without exposing raw PDF text or page images.
- Image OCR and PDF OCR findings can include `pageRegion` pixel coordinates derived from scan-time Tesseract TSV word boxes, with top-left origin and optional OCR confidence, without exposing raw OCR text or page images.
- Text-like, XML, JSON-like, RTF, EML, ZIP member, Office Open XML, legacy Office conversion, OpenDocument, image OCR, video transcript, and video frame OCR findings include source-local text offsets and format labels when scan-time extracted-text metadata is available; UTF-16 text-like inputs with a BOM or declared charset resolve to the same redacted anchor model as UTF-8 text.
- CSV extraction recognizes common comma, semicolon, tab, and pipe delimiters for `.csv` inputs, and standard header-row tables such as `Name,Date of Birth,Address` create label-context fragments with redacted `tableCell` anchors for the source row and column.
- Markdown extraction preserves ordinary text-position anchors and converts standard Markdown tables into label-context fragments with redacted `tableCell` anchors, so multilingual header rows such as `姓名 | 电话 | 地址` can detect non-regex values without exposing raw Markdown text.
- XML findings can include `structurePath` selectors with source-derived element and attribute ordinal metadata without exposing raw XML values or raw element/attribute names in selector metadata.
- JSON, JSONL, and NDJSON findings can include `structurePath` selectors with source-derived record and field ordinal metadata without exposing raw JSON values or raw property names in selector metadata.
- One-click evidence navigation uses source-data-derived anchors such as normalized PDF page regions, OCR image regions, ZIP member ordinals, text positions, CSV/XLSX/ODS table cells, DOCX/PPTX/ODT/ODP/EML/HTML/XML/JSON/JSONL/NDJSON structure paths, legacy Office text ranges, or fallback labels behind one consistent open-and-focus review interaction, with a redacted fallback when a renderer cannot resolve a precise selector.
- Scan-time finding assembly creates a `sourceReviewPreview` package from redacted evidence anchors only, including redacted source-context windows around detected spans, without raw extracted text, raw source bodies, page images, private host paths, Drive URLs, or unredacted personal data.
- Automated backend tests cover raw corpus checksum and Drive coverage, real PDF corpus text-layer extraction, mixed PDF text-layer-plus-OCR extraction, corpus fixture readability, OCR capability reporting, multilingual detection redaction, deterministic quality report freshness/privacy, inline/OCR-normalized label-sequence detection, separatorless CJK OCR word-join detection, bounded signal detection for large text streams, UTF-16 text-like decoding, generated multiformat challenge scanning, structured text-like file scanning, Markdown table header extraction, RTF rich-text scanning, OpenDocument text extraction, legacy Office conversion, EML email extraction, ZIP archive member extraction, source-data evidence-anchor redaction, source-review context-window redaction, CSV header-row and delimiter-sniffed table-cell anchor redaction, CSV/XLSX/ODS table-cell anchor redaction, DOCX/PPTX/ODT/ODP/EML/HTML/XML/JSONL/NDJSON structure-path anchor redaction, PDF text-layer page-region anchor redaction, image OCR region anchor redaction, PDF OCR page-image region anchor redaction, scan assembly from multilingual cases, PDF OCR fallback, and missing-tool OCR-deferred behavior.
- Automated frontend tests cover file review anchor mapping from contract `evidenceAnchor` fields to redacted location labels, PDF page-local offsets, estimated PDF page-region labels, OCR image-region labels, backend source-review preview package summaries, mock-data preservation of source-review preview packages, and normalized visual focus geometry for bottom-left PDF and top-left OCR coordinates.

## OpenRouter AI Assistive Processing Acceptance

The OpenRouter AI assistive-processing boundary is accepted when:

- The design note `docs/design/openrouter-ai-processing.md` defines problem, research basis, options, state transitions, failure paths, rollback path, impact surface, and primitive acceptance criteria.
- Runtime configuration uses ignored environment variables only; tracked files contain placeholders but no real API key.
- `/api/health` and optional `aiProcessing` metadata expose provider, model, budget limits, usage baseline, fail-closed status, OCR/grep/AI tier plan, model-call count, estimated cost, and safety boundaries without exposing the API key.
- AI runtime metadata exposes `atlasReference`, 12 Atlas alignment entries, and tier rows that map OCR, grep, AI context, owner/review boundaries, audit, delta governance, admin metrics, and evaluation back to `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md`.
- The default model is `google/gemini-3.1-flash-lite`; deprecated or near-expiring cheaper models are not selected as defaults.
- The project budget is represented as 25 EUR and a conservative 25 USD OpenRouter application cap, with `OPENROUTER_USAGE_BASELINE_USD` available for project-specific usage tracking.
- AI calls require assistive mode, a configured key, redacted deterministic evidence, active policy-pack context, and a passing budget preflight.
- Unredacted evidence, missing deterministic anchors, missing policy-pack context, missing usage checks in fail-closed mode, exhausted budget, or insufficient OpenRouter remaining limit reject before any external model call.
- Existing deterministic full-scan, delta-scan, review, audit, metrics, and evaluation flows continue to show `modelCalls = 0`, `estimatedCostUsd = 0`, no raw-content exposure, no legal conclusion, and no deletion execution unless an explicit assistive classification path is invoked.
- Automated backend tests cover env defaults, tier planning, unredacted rejection, budget blocking, fail-closed usage checks, health metadata, and secret redaction.

## Local SQLite Persistence Acceptance

The lightweight local database boundary is accepted when:

- The design note `docs/design/local-sqlite-persistence.md` defines problem, research basis, options, state transitions, impact surface, rollback path, and primitive acceptance criteria.
- The API server starts in the existing in-memory mode when no database path is configured.
- The API server starts in local SQLite mode when `--db-path` or `LAWDIT_DB_PATH` points to a writable file.
- `python3 -m backend.lawdit.db_tool init --db-path <file>` creates the schema and seeds contract-compatible demo state without adding runtime dependencies.
- `python3 -m backend.lawdit.db_tool status --db-path <file>` reports schema version, source count, workflow-document count, and database path.
- Source registrations survive API restart when the same SQLite file is reused.
- Accepted scan/review mutations survive API restart when the same SQLite file is reused.
- The local SQLite store does not introduce production Microsoft Graph, OAuth, tenant, production database, queue, production source connector, raw source-content storage, credential storage, legal conclusions, or deletion execution.
- Automated backend tests cover source persistence, review/audit persistence, and unchanged in-memory behavior.

## Full Scan Start Acceptance

The full-scan start stage is accepted when:

- The design note `docs/design/full-scan-start-workflow.md` defines scope, state transitions, failure paths, rollback path, and primitive acceptance criteria.
- Dashboard full-scan start targets the default organizer sample source by `sourceId`.
- Source-row full-scan start targets the selected source by `sourceId`.
- Not-ready sources cannot create a full-scan record or audit event.
- Running and completed scan states update visible admin metrics without exposing raw source content.
- Evaluation data remains deterministic and cost-free for P0, with no model calls required for this stage.
- Automated behavior tests cover the accepted and rejected start paths.

## Source Inventory and Content Extraction Acceptance

The source-inventory and content-extraction stage is accepted when:

- The design note `docs/design/source-inventory-content-extraction.md` defines scope, state transitions, failure paths, rollback path, research basis, and primitive acceptance criteria.
- Starting a full scan produces visible file-inventory and content-extraction summaries for the selected controlled source without adding a public extraction endpoint.
- Internal inventory records include file path, size, modified timestamp, sample family, readability status, and file fingerprint for each candidate file.
- Running scans mark partial data with recoverable warnings and do not expose raw extracted text, file bodies, page images, or unredacted personal data.
- Completed scans show candidate files, fingerprinted files, extracted files, redacted evidence candidates, warning counts, duration, throughput, and evaluation resource intensity.
- Unsupported or OCR-deferred files are counted as recoverable warnings instead of silently failing or blocking the scan.
- The implementation uses deterministic fixture-backed processing with zero model calls and zero estimated paid-service cost.
- Automated behavior tests cover running, completed, partial-warning, no-raw-content, unsupported-file warning, and not-ready-source paths.

## Deterministic Signal Detection Acceptance

The deterministic signal-detection stage is accepted when:

- The design note `docs/design/deterministic-signal-detection.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `detecting_signals` after `extracting_content` and before `judging_context_risk`.
- Running scans show signal detection as pending until extraction completes.
- Completed scans expose a `signalDetection` summary with detector rules version/hash, active evidence requirements, evaluated evidence candidates, detected signals, redacted signals, findings-with-signals, signal-type counts, warnings, and `rawContentExposed = false`.
- Finding details expose only redacted signal snippets with detector, confidence, and location when available; no raw extracted text, file bodies, page images, detector secrets, or unredacted personal data crosses public payloads.
- Completed labeled forms can produce findings from contact, identity, government ID, employment, education, financial, online/device, location, vehicle, health, biometric, genetic, special-category, family/minor, credential, incident, and access fields even when no email address is present; snippets expose only labels and redaction markers, not adjacent raw source context.
- Deterministic pattern rules cover email, phone, SSN/NINO, IP, MAC, UUID, personal-profile URL, account handle, coordinates, Luhn-valid payment cards, and IBAN-like values without emitting matched values.
- Admin metrics expose signal counts, and evaluation preserves a signal-detection rules hash plus deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, inventory, extraction, signal-detection, finding, audit, metric, or evaluation state changes.
- Automated behavior tests cover running, completed, sample form-field coverage, redaction boundary, rules hash, metrics, evaluation traceability, and not-ready-source paths.

## Context and Risk Judgment Acceptance

The context-and-risk judgment stage is accepted when:

- The design note `docs/design/context-risk-judgment.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `judging_context_risk` after `detecting_signals` and before completion.
- Running scans show context/risk judgment as pending until extraction and signal detection complete.
- Completed scans expose a `contextRisk` summary with policy-pack version, risk-rule fingerprint, assessed evidence count, context and risk counts, retention-review count, human-review count, and `legalConclusionProvided = false`.
- The stage consumes redacted signal/evidence candidates, sample-family metadata, modified-time context, and active policy-pack guidance without exposing raw source content or unredacted personal data.
- The Dashboard shows context/risk status, policy version, high-risk count, retention-review count, and human-review count without presenting legal conclusions.
- Evaluation preserves a context-risk rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, inventory, extraction, context/risk, or audit state changes.
- Automated behavior tests cover running, completed, policy-pack version, no-legal-conclusion, no-raw-content, cost boundary, and not-ready-source paths.

## Owner Routing and Assignment Acceptance

The owner-routing and assignment stage is accepted when:

- The design note `docs/design/owner-routing-assignment.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived continuity requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `assigning_owner` after `judging_context_risk` and before completion.
- Running scans show owner assignment as pending until context/risk judgment completes.
- Completed scans expose an `ownerAssignment` summary with policy-pack version, organization-model version, owner-resolution strategy, assignment-rule fingerprint, assigned count, direct-owner count, Master of Data fallback count, escalation count, and `unownedFindings = 0`.
- The stage consumes context/risk human-review counts, source Master of Data metadata, organization model, and active policy-pack escalation paths without exposing raw source content or unredacted personal data.
- The Dashboard shows owner-routing status, assigned findings, fallback assignments, escalation assignments, and unowned count without presenting legal conclusions.
- Owner routing creates an audit-visible event when review-required findings are routed.
- Evaluation preserves an owner-assignment rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, inventory, extraction, context/risk, owner-assignment, or audit state changes.
- Automated behavior tests cover running, completed, fallback, escalation, no-unowned, audit, no-raw-content, cost boundary, and not-ready-source paths.

## Finding Assembly and Evidence Card Acceptance

The finding-assembly and evidence-card stage is accepted when:

- The design note `docs/design/finding-assembly-evidence-card.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `assembling_findings` after `assigning_owner` and before completion.
- Running scans show finding assembly as pending until owner assignment and redacted signals are complete.
- Completed scans expose a `findingAssembly` summary with policy-pack version, source snapshot, assembly fingerprint, assembled finding count, evidence-card count, redacted signal count, missing-card count, denied-action count, `rawContentExposed = false`, and `legalConclusionProvided = false`.
- Completed scan findings and evidence-card details are assembled from the completed scan ID and previous stage summaries instead of disconnected static rows.
- Each assembled evidence card shows redacted signals, policy context, owner assignment, retention status, action boundary, and audit timeline without exposing raw source content or unredacted personal data.
- Finding assembly creates an audit-visible event and evaluation preserves a finding-assembly rules hash.
- The stage keeps deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, inventory, extraction, context/risk, owner-assignment, finding-assembly, finding, evidence-card, or audit state changes.
- Automated behavior tests cover running, completed, scan continuity, redaction, no-legal-conclusion, action-boundary, ownerless escalation, audit, evaluation hash, cost boundary, and not-ready-source paths.

## Review Support and Permission Boundary Acceptance

The review-support and permission-boundary stage is accepted when:

- The design note `docs/design/review-support-permission-boundary.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `preparing_review_support` after `assembling_findings`.
- Running scans show review support as pending until finding assembly and permission-boundary calculation can complete.
- Completed scans expose a `reviewSupport` summary with policy-pack version, organization-model version, support rules fingerprint, supported finding count, allowed action count, denied action count, available decision count, required reason count, checklist count, transfer count, escalation count, `rawContentExposed = false`, and `legalConclusionProvided = false`.
- Finding-specific review support is derived from assembled evidence cards, owner assignment, active policy pack, organization model, and actor permission boundary instead of disconnected static rows.
- A reviewer can see delete candidate, keep with reason, false positive correction, reassign, and escalate options when those actions are inside the permission boundary.
- Every available review decision requires a human reason before submission.
- Denied actors, missing reasons, missing transfer targets, and missing escalation targets are rejected without changing finding, audit, source, or metric state.
- Real deletion remains denied and visible as a permission-boundary reason.
- Evaluation preserves a review-support rules hash, deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Not-ready sources cannot create scan, inventory, extraction, context/risk, owner-assignment, finding-assembly, review-support, permission-boundary, finding, evidence-card, or audit state changes.
- Automated behavior tests cover running, completed, finding-specific support, permission denial, reason validation, target validation, no-raw-content, no-legal-conclusion, evaluation hash, cost boundary, and not-ready-source paths.

## Human Review Decision Handling Acceptance

The human-review decision-handling stage is accepted when:

- The design note `docs/design/human-review-decision-handling.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A review decision is accepted only when current finding-specific review support exposes the decision inside the actor permission boundary.
- A reviewer can submit `delete_candidate`, `keep_with_reason`, `correct_false_positive`, `reassign_owner`, and `escalate` decisions with required human context.
- A `delete_candidate` review requires an explicit confirmation checklist acknowledgement and still records `deletionExecuted = false`.
- Every accepted decision creates exactly one review record and one audit event with actor, timestamp, decision, reason, resulting status, policy-pack version, permission-boundary fingerprint, and review-support rules fingerprint when available.
- `delete_candidate` changes finding review status only; no source file, connector, deletion service, or real deletion state is changed.
- `keep_with_reason` requires and records a retention review date.
- `keep_with_reason` updates both detail and list payload retention state to `retained_until_review` so the UI does not show an unresolved retention review after a retained decision.
- `reassign_owner` requires and records a supported transfer target.
- `escalate` requires and records a supported escalation queue.
- Denied decisions, denied actors, actor mismatch, missing reasons, missing checklist acknowledgements, missing retention review dates, missing transfer targets, missing escalation queues, and unknown findings are rejected without changing finding, audit, source, metric, or evaluation state.
- Duplicate review submissions with the same idempotency key do not create duplicate audit events or metric increments.
- Admin metrics can expose review decision totals, outcome counts, backlog movement, and review throughput inputs.
- Evaluation can preserve a human-review decision rules hash while keeping deterministic reproducibility, zero model calls, and zero estimated paid-service cost.
- Automated behavior tests cover accepted decisions, audit creation, status/owner updates, retain-date validation, checklist validation, denial paths, idempotency, no-real-deletion, metrics, evaluation, and no-state-change failures.

## Audit Event Recording Acceptance

The audit-event recording stage is accepted when:

- The design note `docs/design/audit-event-recording.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A full scan pipeline exposes `recording_audit_events` after `preparing_review_support`.
- Audit events for scan start, scan completion, owner assignment, finding assembly, finding assembled, finding assigned, and accepted review decisions share a structured event shape with actor, action, object, timestamp, state transition, outcome, and evidence references.
- Completed scan state exposes an `auditRecording` summary with policy-pack version, audit rules fingerprint, recorded event count, linked scan count, linked finding count, review decision count, human/system counts, `rawContentExposed = false`, `legalConclusionProvided = false`, and `deletionExecuted = false`.
- Accepted review decisions update the finding audit timeline, global audit list, audit summary, audit metrics, and evaluation traceability together.
- Denied, incomplete, stale, unknown, or duplicate review commands do not create duplicate audit events or metric increments.
- Human-entered audit text is sanitized for obvious emails, IBAN-like values, long numbers, and control characters before it appears in public audit payloads.
- The implementation keeps deterministic reproducibility, zero model calls, zero estimated paid-service cost, and no production storage, connector, authorization, SIEM, or deletion integration.
- Automated behavior tests cover lifecycle event recording, finding timeline inclusion, structured audit metadata, text sanitization, audit metrics, evaluation hash, no-raw-content boundary, and no-real-deletion boundary.

## Incremental Delta Scan Acceptance

The incremental delta-scan stage is accepted when:

- The design note `docs/design/incremental-delta-scan-workflow.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- A delta scan can start only for a selected scan-ready source with a completed baseline; missing, running, not-ready, or mismatched baselines reject without scan, audit, finding, metric, or evaluation state changes.
- Running delta scans expose `comparing_delta_baseline`, baseline identity, changed/new/modified/unchanged/missing counts, partial warnings, and `rawContentExposed = false`, `legalConclusionProvided = false`, and `deletionExecuted = false`.
- Completed delta scans process only changed files, carry unchanged baseline files forward, and represent missing files as source inventory changes rather than lawdit deletion.
- Completed delta findings use the delta scan ID and pass through context/risk, owner routing, finding assembly, review support, audit recording, metrics, and evaluation instead of using disconnected static rows.
- Dashboard and Sources expose delta readiness from the selected source and show baseline/change counts when available.
- Evaluation preserves a delta rules hash, deterministic reproducibility, throughput, zero model calls, and zero estimated paid-service cost.
- Automated behavior tests cover accepted delta start, rejected baseline paths, completed changed-file processing, carried-forward counts, no-real-deletion boundary, audit, metrics, evaluation, and full-scan continuity.

## Admin Metrics Aggregation Acceptance

The aggregate admin-metrics stage is accepted when:

- The design note `docs/design/admin-metrics-aggregation.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- Running scans expose partial aggregate metrics that identify upstream stage status across inventory, extraction, context/risk, owner assignment, finding assembly, review support, audit recording, and delta when present.
- Completed scans expose aggregate management metrics for scan coverage, deterministic signal counts, risk queue, owner backlog, review throughput, review outcomes, audit evidence, evaluation linkage, and resource cost from prior stage summaries instead of disconnected constants.
- Completed delta scans preserve changed-file, carried-forward, missing-file, no-raw-content, no-legal-conclusion, and no-deletion boundaries in the aggregate metrics.
- Accepted review decisions update owner backlog, outcome counters, audit counts, throughput inputs, and evaluation-linked aggregation exactly once.
- Rejected scan or review attempts leave metric, audit, source, finding, and evaluation state unchanged.
- Aggregated metrics keep `rawContentExposed = false`, `legalConclusionProvided = false`, `deletionExecuted = false`, `modelCalls = 0`, and `estimatedCostUsd = 0` in P0.
- Evaluation preserves an admin-metrics rules hash for deterministic reproducibility.
- Dashboard shows management indicators for owner completion, risk queue, audit evidence, metric basis, and cost without exposing raw source content or legal conclusions.
- Automated behavior tests cover running aggregation, completed aggregation, delta aggregation, accepted review metric updates, rejected path identity, safety boundaries, and cost boundaries.

## Evaluation Metrics Generation Acceptance

The evaluation-metrics generation stage is accepted when:

- The design note `docs/design/evaluation-metrics-generation.md` defines scope, state transitions, failure paths, rollback path, Atlas-derived requirements, research basis, and primitive acceptance criteria.
- Completed full scans generate precision, recall, F1, reproducibility, throughput, resource intensity, confusion-matrix counts, scenario-level metrics, review-throughput context, and risk-progress fields from prior workflow summaries and a controlled golden dataset definition.
- Completed delta scans generate changed-file evaluation while preserving baseline, carried-forward, missing-file, no-raw-content, no-legal-conclusion, no-deletion, zero-model-call, and zero-cost boundaries.
- Evaluation exposes an evaluation-rules fingerprint plus dataset, detector/signal-detection, config, policy-pack, context/risk, owner-assignment, finding-assembly, review-support, audit-recording, admin-metrics, delta, and finding fingerprints for deterministic reproduction.
- Accepted human-review decisions refresh review-throughput and risk-progress fields exactly once without changing scan-quality precision, recall, or F1.
- Rejected scan or review commands leave evaluation, metric, audit, source, and finding state unchanged.
- The Evaluation page renders scan quality, confusion matrix, scenario metrics, resource intensity, reproducibility, and safety boundaries without raw source content or legal conclusions.
- Automated behavior tests cover full-scan generation, delta generation, review refresh, rejected-path identity, metric formula bounds, safety boundaries, and cost boundaries.

## Adaptive Governance Acceptance

The design points are accepted when:

- Legal or policy details can be represented as a versioned policy pack instead of hard-coded scanner logic.
- A reviewer can see plain-language support, required checklist items, available decisions, transfer options, escalation options, and required reason fields.
- A user can see allowed actions, denied actions, denial reasons, and visible scopes before attempting an action.
- Ownership transfer, personnel change, organization model change, policy version change, and regulatory update scenarios are represented in docs and contract mocks.
- Audit and evaluation payloads can preserve the policy-pack version used for a finding or decision.
- The organizer sample repository is represented as a default demo source with sample families.

## Remote Preview Deployment Acceptance

The remote preview deployment is accepted when:

- The design note `docs/design/remote-preview-deployment.md` defines problem, options, state machine, impact surface, rollback path, and primitive acceptance criteria.
- `docs/design/agent-us-api-server-integration.md` defines the P0 API server integration, state machine, impact surface, rollback path, and primitive acceptance criteria.
- `docs/DEPLOYMENT.md` records the `agent-us` frontend layout, API route, Caddy route, validation commands, and rollback steps.
- `npm run test` and `npm run build` pass before deployment.
- The remote host serves the frontend through Caddy on port 80 from `/srv/lawdit/frontend/current`.
- The remote host proxies `/api/*` through Caddy to a loopback P0 API server.
- Direct requests for `https://founder-force.uk/` and `https://founder-force.uk/dashboard` return lawdit frontend HTML after DNS points to `agent-us`.
- Direct requests for `https://founder-force.uk/docs` return the Fumadocs user guide after DNS points to `agent-us` and the docs service is running.
- Direct requests for `https://founder-force.uk/api/health` return a contract health envelope after DNS points to `agent-us` and the API service is running.
- The preview remains mock-compatible, in-memory, or local-SQLite-backed and adds no production Microsoft Graph, OAuth, tenant, production database, queue, production source connector, or deletion service.
- The previous Caddyfile is saved before modification, the release symlink allows asset rollback, and the API service can be stopped independently.

## Agent-us API Server Integration Acceptance

The frontend-backend integration is accepted when:

- The backend source package exposes `GET /api/health`, `GET /api/sources`, scan, finding, review, audit, metrics, evaluation, governance, permissions, and review-support paths from the existing P0 contract.
- Successful backend responses use the standard envelope and rejected commands use `application/problem+json`.
- The frontend requests `/api` first and falls back to the local mock workflow when the backend is unavailable.
- Vite development mode proxies `/api` to the local Python API server without hard-coding a public host.
- `POST /api/scans/full` accepts the controlled `mock_ready` source and rejects not-ready sources without adding audit events.
- Accepted prelaunch scan starts return `202` with `status = running` immediately after backend command validation, without waiting for source document reading or signal detection to finish.
- `POST /api/findings/{findingId}/review` records a review, updates finding state, adds an audit event, updates metrics, and keeps `deletionExecuted = false`.
- No raw source content, legal conclusion, production connector, OAuth, Microsoft Graph, production database, queue, unapproved AI service, or deletion execution is introduced.
- Python backend unit tests, frontend tests, frontend lint, and frontend build pass for the touched surfaces.
