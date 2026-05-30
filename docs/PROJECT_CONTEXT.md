# Project Context

## One-Liner

DataSentinel is a Bosch-grade GDPR discovery and responsible cleanup workflow for distributed enterprise drives.

## Product Thesis

DataSentinel turns GDPR file cleanup from manual auditing into a measurable, owner-routed, human-reviewed, audit-ready workflow.

## Core Loop

Source connection -> full scan -> hybrid detection -> context classification -> owner routing -> human review -> audit trail -> delta scan -> evaluation metrics.

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
- The demo must not rely on live external APIs.

## P0 Demo Path

Run full scan -> show admin metrics -> open evidence card -> record user review action -> show audit event -> run delta scan -> show evaluation metrics.

## Architecture Principles

- Use a deterministic scanning core before any AI classifier.
- Use AI only for structured context assistance and explanations.
- Keep side effects in boundary layers.
- Keep sensitive evidence redacted by default.
- Treat metrics as product features, not internal logs.

## Deferred P0 Items

- Production Microsoft Graph OAuth.
- Real remote deletion.
- Multi-tenant SaaS controls.
- Billing, procurement, and compliance certification.
- Advanced vector search or customer-specific policy engines.
