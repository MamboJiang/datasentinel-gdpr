# GDPR Enterprise Expert Atlas

Repository edition derived from the local source file `/Users/y.h/Downloads/GDPR_Enterprise_Expert_Atlas.md`, generated on 2026-05-30. The source document was not copied verbatim because this repository must stay English-only.

## Core Thesis

GDPR data discovery is not a generic PII search problem. The enterprise product goal is a responsible deletion control tower that can discover GDPR-relevant data, explain evidence, route findings to accountable owners, support human review, record audit evidence, and measure quality and operating cost.

The product must help answer:

- What data exists and where it is.
- Why the data exists and which policy pack currently guides review.
- Who is accountable: direct owner, Master of Data fallback, or escalation target.
- Whether the next action is delete candidate, retain with reason, false-positive correction, transfer, escalation, or a future restricted-access action.
- Why the decision was made, who made it, when it happened, and which evidence and policy context were visible.
- How delta scans and policy-pack versions prevent the same risk from recurring.

## Non-Legal Boundary

The Atlas is a product and engineering reference for a prototype. It is not legal advice, does not claim full GDPR compliance, and does not authorize automatic deletion. Enterprise deployment would require DPO, legal, security, IT, and business-owner confirmation.

## Authoritative Basis

- Regulation (EU) 2016/679 on EUR-Lex: https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng
- European Commission GDPR principles overview: https://commission.europa.eu/law/law-topic/data-protection/data-protection-explained_en
- European Commission processing-principles guidance: https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr/overview-principles/what-data-can-we-process-and-under-which-conditions_en
- EDPB Guidelines 01/2022 on the right of access: https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-012022-data-subject-rights-right-access_en
- Microsoft Graph delta query overview, future connector reference only: https://learn.microsoft.com/en-us/graph/delta-query-overview

## Atlas Product Requirements

| Area | Requirement |
| --- | --- |
| Enterprise control tower | The system must connect discovery, classification, owner attribution, review, audit, delta scan, and evaluation instead of stopping at detection. |
| Evidence first | Every finding must be backed by deterministic or versioned evidence and must show redacted evidence, detector, confidence, location when available, and policy context. |
| Human accountability | AI or rules can support evidence and context, but high-risk review and deletion/retention decisions stay human-accountable. |
| Deletion boundary | P0 records `delete_candidate` only. It must not mutate source files, execute deletion, update retention labels, or imply proof of erasure. |
| Policy packs | Legal and retention guidance must live in versioned policy packs and organization models, not hard-coded scanner logic. |
| Owner attribution | Findings must route to a direct owner, Master of Data fallback, or escalation path. They must not become silent unowned work. |
| Permission boundary | Reviewers must see allowed actions, denied actions, denial reasons, checklist requirements, transfer options, and escalation options before acting. |
| Auditability | AuditEvent is a first-class object. Events must preserve actor, timestamp, action, object, previous/resulting state, reason, evidence references, policy context, and safety boundaries. |
| Delta governance | Full scans create a baseline; delta scans compare fingerprints and modified times and treat missing files as source inventory changes, not DataSentinel deletion. |
| Evaluation | Precision, recall, F1, reproducibility, throughput, resource intensity, scenario quality, review throughput, and risk-progress context are product features. |
| Privacy engineering | Public payloads must not expose raw extracted text, full file bodies, page images, credentials, unredacted personal data, hidden permission data, legal conclusions, or deletion execution. |

## 12-Stage Workflow Contract

| Stage | Atlas requirement summary |
| --- | --- |
| 1. Start full scan | Require `sourceId`, actor context, idempotency, readable or P0 `mock_ready` source, and current policy pack. Output scan ID, status, progress, counts, duration, and warnings. |
| 2. Inventory and extraction | Use file path, size, modified time, sample family, permissions snapshot, and file fingerprint internally. Output scannable inventory, unreadable-file warnings, and internal extraction results without exposing raw text. |
| 3. Deterministic signal detection | Use extracted text inside the internal boundary, detector rules version/hash, and policy evidence requirements. Output redacted evidence signals such as email, employee ID, IBAN-like values, signatures, access roles, and feedback comments. |
| 4. Context and risk judgment | Use signals, file type/family, modified time, and policy guidance. Output context category, risk level, risk score, retention status, and risk explanation without legal conclusions. |
| 5. Owner assignment | Use file-owner clues, source Master of Data, organization model, and escalation path. Output direct owner, fallback owner, or escalation target. |
| 6. Finding and evidence card assembly | Combine scan, file, signals, risk, owner, policy, and audit context into finding rows and evidence-card details for frontend display. |
| 7. Review support and permission boundary | Use current user, finding status, owner, policy pack, and organization rules. Output allowed actions, denied actions, checklist, required reason fields, and transfer/escalation options. |
| 8. Human review decision | Require actor, finding ID, decision, reason, idempotency key, and policy version. Output updated finding status, review record, audit event, and no-real-deletion boundary. |
| 9. Audit event recording | Record scan, assignment, view, review, escalation, and related lifecycle events with actor, timestamp, event type, reason, resulting status, and policy context. |
| 10. Incremental scan | Require full-scan baseline, file fingerprints, modified time, and current inventory. Output new, changed, modified, unchanged, and missing file results; missing does not mean deleted by DataSentinel. |
| 11. Admin metrics | Aggregate scan state, finding state, risk, backlog, retention, and duration into scanned files, flagged files, volume, progress, scan time, backlog, high-risk count, and overdue count. |
| 12. Evaluation metrics | Use dataset hash, scanner version, rules hash, config hash, policy version, and finding fingerprints. Output precision, recall, F1, reproducibility, throughput, and resource intensity. |

## Enterprise Data Model Minimum

The Atlas expects these concepts to remain visible in the product model:

- `Source`: ID, type, connector or fixture, scope, status, last full scan, and future delta token.
- `FileItem`: ID, path, owner, Master of Data, permissions, hash, created time, and modified time.
- `Finding`: ID, file ID, detector, entity type, confidence, snippet hash, context category, and risk severity.
- `RetentionDecision` or review record: decision, purpose or reason, lawful-basis or policy guidance reference when available, retention review date, exception reason, and reviewer.
- `ReviewTask`: assignee, status, due date or SLA, action, comments, and escalation target.
- `AuditEvent`: event ID, actor, action, object ID, timestamp, before/after state, reason, and evidence.
- `RuleVersion`: detector rule ID/version, model version when used, config hash, and test results.

## Repository Trace

This Atlas repository edition is traced by `docs/design/gdpr-enterprise-atlas-12-stage-audit.md` and the per-stage design notes in `docs/design/`.
