# Website Homepage Contract

## Purpose

This document defines the functional and content contract for the public lawdit project homepage. It describes what the homepage must communicate and what user paths it must support without prescribing visual design, art direction, page composition, component structure, animation style, or final marketing copy.

The homepage exists to explain lawdit before a user enters the internal product console. It must make the prototype understandable to evaluators, teammates, and reviewers while staying inside the project's safety and scope boundaries.

## Contract Sources

The homepage must stay aligned with:

- `ACCEPTANCE.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/BRD.md`
- `docs/MRD.md`
- `docs/PRD.md`
- `docs/DesignSpec.md`
- `docs/DEMO_SCRIPT.md`
- `docs/SECURITY_NOTES.md`
- `docs/EVALUATION.md`
- `docs/GOVERNANCE_CONFIG.md`
- `docs/GDPR_SAMPLE_REFERENCES.md`
- `docs/design/project-homepage-parallax.md`
- `docs/design/public-upload-analysis-preview.md`
- `docs/FRONTEND_CONSOLE_CONTRACT.md`

## Scope

In scope:

- Public route `/`.
- Homepage navigation and calls to action.
- Product thesis and highlights.
- Workflow explanation.
- Controlled sample source explanation.
- Safety, privacy, review, audit, governance, and evaluation positioning.
- Link into the internal console at `/dashboard`.
- Reduced-motion and responsive content requirements.
- A prominent single-file public analysis entry with real capacity data and redacted short results.

Out of scope:

- Internal console requirements, which are defined in `docs/FRONTEND_CONSOLE_CONTRACT.md`.
- Final visual identity.
- Exact layout, typography, color, imagery, illustrations, animation choreography, or interaction microcopy.
- SEO growth strategy, analytics, lead capture, billing, procurement, or customer onboarding.
- Production login or tenant connection.
- Durable public upload queues, retained public analysis history, multi-file upload, production tenant connection, or public deletion workflows.

## Non-Negotiable Homepage Boundaries

- Homepage content must be English.
- The homepage must not claim full GDPR compliance.
- The homepage must not provide legal advice.
- The homepage must not imply automatic deletion.
- The homepage must clearly position deletion as simulated in the prototype when deletion is mentioned.
- The homepage must not claim production Microsoft 365, Microsoft Graph, OAuth, tenant, AI, OCR, or deletion integration.
- The homepage must not show raw sensitive data.
- The homepage must not vendor or embed organizer sample PDFs.
- The homepage must not obscure that the P0 flow is mock-backed or controlled-sample-backed when that context is relevant.

## Primary Audience

The homepage must be understandable to:

- Hackathon judges or evaluators.
- Privacy and compliance stakeholders.
- IT administrators.
- Department data owners or Masters of Data.
- Product and engineering teammates.
- Auditors reviewing the prototype flow.

## Primary User Path

Required path:

1. User lands on `/`.
2. User understands what lawdit is.
3. User understands that it is an accountable GDPR-relevant data discovery and review workflow, not a generic PII scanner.
4. User understands the main loop: source connection, full scan, evidence, context/risk, owner routing, human review, audit, delta scan, evaluation.
5. User sees the prototype's safety boundaries.
6. User can enter the console at `/dashboard`.

The homepage must not require a login flow for P0.

## Route and Navigation Contract

Required route behavior:

- `/` shows the public homepage.
- `/dashboard` opens the internal console dashboard.
- Existing internal routes remain reachable through the console, not through homepage-only assumptions.

Required homepage navigation:

- Primary navigation to product explanation sections.
- Primary call to action that opens `/dashboard`.
- Secondary navigation or links to source, workflow, evaluation, or governance sections when present.
- Anchor navigation must focus or scroll to existing sections only.
- Route changes must clean up any homepage-only animation or scroll effects.

## Required Homepage Message

The homepage must communicate this product thesis:

lawdit turns GDPR-relevant data discovery from manual file auditing into a measurable, evidence-backed, owner-routed, human-reviewed, audit-ready workflow.

The homepage must make these points clear:

- lawdit is not a generic PII scanner.
- Detection is the beginning of a governed workflow, not the final answer.
- Every finding needs evidence.
- Sensitive evidence is redacted by default.
- Accountable owners or escalation paths receive findings.
- Human reviewers make the final review decision.
- Every review decision creates audit evidence.
- Delta scans support ongoing governance.
- Evaluation metrics show accuracy, reproducibility, speed, and resource intensity.
- Policy packs allow governance changes without hard-coding one legal snapshot.
- Permission boundaries show what users can and cannot do.

## Required Highlight Information

The homepage must include or clearly imply these product highlights:

| Highlight | Required Meaning |
| --- | --- |
| GDPR-relevant discovery | The product finds candidate files that may contain GDPR-relevant personal data. |
| Evidence-first findings | Findings are backed by redacted detector evidence, not hidden model conclusions. |
| Context and risk triage | The system helps prioritize context, risk, retention review, and human review without giving legal advice. |
| Owner routing | Findings are assigned to direct owners, Master of Data fallback, or escalation paths. |
| Human review | Reviewers decide delete candidate, keep with reason, false positive, reassign, or escalate. |
| Audit trail | Scan events, assignments, and human decisions are attributable and traceable. |
| Delta scan | Later scans focus on changed files after a full-scan baseline. |
| Evaluation metrics | Precision, recall, F1, reproducibility, throughput, and resource intensity are first-class product evidence. |
| Governance layer | Policy packs, organization model, permissions, review support, and change previews make the workflow adaptable. |
| Safe prototype boundary | Deletion is simulated, raw sensitive content is minimized, and production integrations are deferred. |

## Required Homepage Sections

The homepage may choose any visual order, but it must cover these content responsibilities.

### Hero or Opening Statement

Must include:

- Product name: lawdit.
- Plain statement of the category or offer.
- One concise explanation of the governed workflow.
- Primary call to action into `/dashboard`.
- No claim of full GDPR compliance.
- No legal-advice claim.

### Problem Section

Must explain:

- Personal data can be spread across distributed file stores.
- Manual review does not scale.
- Simple detection is not enough.
- Teams need evidence, ownership, review decisions, audit, and measurable quality.

### Workflow Section

Must show the loop:

1. Controlled source.
2. Full scan.
3. File inventory and extraction summary.
4. Deterministic evidence signals.
5. Context and risk triage.
6. Owner routing.
7. Review support and permission boundary.
8. Human review decision.
9. Audit trail.
10. Delta scan.
11. Evaluation metrics.

The workflow must not imply automatic deletion or legal conclusions.

### Evidence and Redaction Section

Must explain:

- Evidence snippets are redacted.
- Raw source content is not exposed through public UI payloads in P0.
- Unsupported or OCR-deferred files are recoverable warnings, not hidden failures.
- Evidence supports review decisions but does not replace human accountability.

### Owner Routing Section

Must explain:

- Findings are routed to accountable owners.
- Master of Data fallback prevents silently unowned findings.
- Escalation paths support DPO or Legal review.
- Ownership changes and task transfers are governance scenarios, not hard-coded exceptions.

### Human Review Section

Must explain:

- Reviewers see guidance before acting.
- Reviewers see allowed and denied actions.
- Decisions require reasons.
- Available decisions include delete candidate, keep with reason, false positive correction, reassign, and escalate.
- `delete_candidate` is simulated and does not execute source-file deletion in P0.

### Audit Section

Must explain:

- Scan, assignment, and review actions produce audit events.
- Audit events preserve actor, timestamp, reason, outcome, and policy context when available.
- Audit evidence does not reveal raw sensitive content.

### Evaluation Section

Must explain:

- Accuracy and operational quality are product features.
- Required metrics include precision, recall, F1, reproducibility, throughput, and resource intensity.
- P0 resource intensity includes zero model calls and zero estimated paid-service cost when using deterministic fixtures.
- Mock-backed values are prototype evidence, not production certification.

### Governance Section

Must explain:

- Policy packs represent policy guidance.
- Organization model supports ownership and fallback.
- Permission boundaries show allowed and denied actions.
- Change previews help represent policy or organization changes before activation.
- Governance configuration avoids hard-coding one legal snapshot into scanner logic.

### Controlled Sample Source Section

Must explain:

- The default demo source references the organizer sample repository `a-klumpp/GDPR-data-samples`.
- Sample families include `Expense_Report`, `IT_Access_Request`, `Incident_Report`, `Supplier_Onboarding`, and `Training_Evaluation`.
- The repository is referenced, not vendored into this project.
- The P0 demo uses controlled sample or mock-backed behavior rather than live enterprise data.

### Console Preview or Product Surfaces Section

Must list or preview the internal product areas:

- Dashboard.
- Sources.
- Findings.
- Finding detail and evidence card.
- File review editor.
- Review panel.
- Audit view.
- Evaluation.
- Governance settings.
- Permission boundary.

The homepage may link to `/dashboard` as the main way to inspect these surfaces.

### Safety and Scope Section

Must state or clearly communicate:

- Deletion is simulated in this prototype.
- The prototype does not connect to production Microsoft Graph or tenant systems.
- The prototype does not provide legal advice.
- The prototype does not claim full GDPR compliance.
- Raw sensitive content is minimized and redacted in UI-facing payloads.
- Production AI, durable queue, production authorization, database-backed public analysis history, and real deletion choices are deferred unless separately approved.

## Required Calls to Action

The homepage must provide:

- Primary CTA to open the console at `/dashboard`.
- A secondary CTA or link to learn how the workflow works, when page sections are long enough to justify it.
- Optional link to the controlled sample source reference, if presented safely and without embedding sample files.

## Public Analysis Entry

The homepage must include a public "try analysis" entrypoint backed by `/api/public-analysis/capacity` and `/api/public-analysis/analyze`. The design contract is `docs/design/public-upload-analysis-preview.md`.

Constraints:

- The entry accepts one uploaded file per user/session at a time.
- Each file must be 10 MB or smaller.
- The system may process at most 10 active public analyses globally at the same time in the API process.
- Capacity data must show real active analyses, available slots, waiting-at-intake count, and the file-size limit.
- The result is a short redacted analysis summary, not the full Workspace review console, and should lead with a plain-language explanation generated from the actual detected categories, counts, risk level, file format, and redacted evidence locations.
- The entry must state its website analysis boundary in production-quality copy rather than using prelaunch placeholder language.
- The entry must explain that governed source setup, owners, review decisions, audit trails, and evaluation live in the Workspace.
- The entry must render optional backend-provided plain-language summary, processing stages, next steps, Workspace handoff readiness, and boundary notes when present.
- The entry section must link to `/dashboard` for users who want the governed Workspace path.
- The entry must not claim legal advice, full GDPR compliance, automatic deletion, production tenant access, or production Microsoft Graph integration.
- The OpenAPI contract, mock payloads, backend intake boundary, validation tests, and deployment controls must stay aligned with the implemented UI.

Calls to action must not imply:

- Production tenant connection.
- Real deletion.
- Legal certification.
- Purchase, billing, or enterprise deployment readiness.

## Allowed Claims

The homepage may claim:

- The prototype demonstrates GDPR-relevant discovery workflow concepts.
- The workflow is evidence-backed.
- Sensitive evidence is redacted by default.
- Review decisions are human-accountable.
- Audit events record visible workflow changes.
- Evaluation metrics are shown as product evidence.
- Governance can be represented through versioned policy packs.
- The P0 demo is controlled-sample-backed or mock-backed.

## Prohibited Claims

The homepage must not claim:

- Full GDPR compliance.
- Legal advice or legal determination.
- Automatic deletion.
- Production Microsoft 365 integration.
- Production OAuth or tenant onboarding.
- Production authorization.
- Certified scan accuracy.
- Certified privacy compliance.
- Real enterprise deployment readiness.
- That mock evaluation values prove production quality.

## Motion and Progressive Enhancement Contract

If homepage parallax or scroll animation is implemented:

- Motion must be progressive enhancement.
- Reduced-motion users must receive the same readable content without required animation.
- Route changes must clean up scroll triggers, timers, observers, and inline transforms.
- Animation must not be required to understand the workflow.
- Animation must not hide safety boundaries or deferred-scope disclosures.

## Accessibility Contract

The homepage must support:

- Keyboard navigation.
- Focusable calls to action.
- Semantic headings.
- Meaningful link labels.
- Reduced-motion preference.
- Sufficient text readability.
- Content that remains available without animation.
- No information conveyed only by color, motion, or decorative imagery.

## Responsive Contract

The homepage must remain readable on mobile and desktop.

Required responsive behavior:

- Primary CTA remains visible and usable.
- Product thesis remains readable.
- Workflow steps remain understandable.
- Long terms such as `resource intensity`, `permission boundary`, and policy-pack versions do not overflow.
- Homepage content does not overlap.
- Any product preview remains inspectable or degrades to text summaries.

## Content Quality Contract

Homepage copy must be:

- English.
- Direct and product-specific.
- Clear about prototype boundaries.
- Clear about human accountability.
- Clear about redaction and data minimization.
- Clear about evaluation metrics.
- Clear about governance adaptability.

Homepage copy must avoid:

- Legal advice wording.
- Fear-based compliance promises.
- Empty marketing claims.
- Claims that the product deletes data.
- Claims that the prototype connects to production enterprise systems.

## Acceptance Checklist

The homepage satisfies this contract when:

- `/` shows a public lawdit homepage instead of the internal console shell.
- The page explains the product thesis, workflow, safety boundaries, controlled sample source, governance layer, audit trail, and evaluation metrics.
- The page links to `/dashboard`.
- The page does not expose raw sensitive values.
- The page does not claim legal advice or full GDPR compliance.
- The page does not imply real deletion or production Microsoft integration.
- The page remains readable with reduced motion.
- The page remains usable on mobile and desktop.
- Any animation is optional and cleaned up on route changes.
- Homepage content stays consistent with the internal console contract and current acceptance criteria.
- The public upload-analysis entry shows live capacity data and a real redacted analysis result while remaining separate from the Workspace console.
- The public upload-analysis entry explains its website analysis boundary and provides a nearby link into the governed Workspace.

## Deferred

- Final brand identity.
- Final visual design system.
- SEO strategy.
- Analytics.
- Lead capture.
- Pricing or procurement flow.
- Production login.
- Production tenant connection.
- Customer onboarding.
