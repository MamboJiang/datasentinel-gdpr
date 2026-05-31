# Project Context

## One-Liner

DataSentinel is a Bosch-grade GDPR discovery and responsible cleanup workflow for distributed enterprise drives.

## Product Thesis

DataSentinel turns GDPR file cleanup from manual auditing into a measurable, owner-routed, human-reviewed, audit-ready workflow.

## Core Loop

Source connection -> full scan -> inventory/extraction -> deterministic signal detection -> optional redacted AI context support -> owner routing -> human review -> audit trail -> delta scan -> evaluation metrics.

## Target Users

- Employee or file owner.
- Master of Data or department data steward.
- Data Protection Officer or legal reviewer.
- IT administrator.
- Auditor or compliance reviewer.

## Non-Negotiable Requirements

- Scan logic is Priority 1.
- Every finding must have evidence.
- Users have the last word for review decisions.
- Admin reporting must show scanned files, flagged files, data volume, scan progress, scan time, review backlog, and risk distribution.
- Evaluation must include accuracy, reproducibility, speed, and resource intensity.
- Deletion is simulated in the hackathon prototype.
- The demo must not rely on live external APIs except approved prelaunch boundaries: Google/GitHub sign-in, Google Drive Picker/Drive reads for user-selected sources, direct HTTPS text-like/PDF/Office Open XML file reads, and optional OpenRouter assistive AI that is disabled unless configured, budget-guarded, and redacted-evidence-only.
- Legal and policy details must be configurable through versioned policy packs rather than hard-coded into scanner structure.
- Users must see permission boundaries and action scope before making decisions.
- The default demo source should reference the organizer sample repository.

## P0 Demo Path

Run full scan -> show admin metrics -> open evidence card -> record user review action -> show audit event -> run delta scan -> show evaluation metrics.

## Architecture Principles

- Use a deterministic scanning core before any AI classifier.
- Use AI only for structured context assistance and explanations.
- Keep side effects in boundary layers.
- Keep sensitive evidence redacted by default.
- Treat metrics as product features, not internal logs.
- Treat governance configuration as an admin-operable layer.
- Preserve policy-pack version and actor context in review and audit flows.

## Deferred P0 Items

- Production Microsoft Graph OAuth.
- Real remote deletion.
- Multi-tenant SaaS controls.
- Billing, procurement, and compliance certification.
- Advanced vector search or customer-specific policy engines.

## Organizer Sample Source

Default demo source: `https://github.com/a-klumpp/GDPR-data-samples`.

Sample families: `Expense_Report`, `IT_Access_Request`, `Incident_Report`, `Supplier_Onboarding`, and `Training_Evaluation`.
