# Product Requirements Document

## Product Goal

Provide a prototype workflow that shows how an organization can discover GDPR-relevant data, classify risk, assign ownership, support human review, and prove the outcome.

## Initial User Journey

1. A privacy or IT user starts with a controlled sample file source.
2. The system identifies candidate files that may contain personal or GDPR-relevant data.
3. The system explains why each finding matters.
4. The system suggests an accountable owner or escalation path.
5. A human reviewer decides whether to delete, retain, mask, archive, or escalate the finding.
6. The system records the decision in an audit trail.
7. A later delta scan focuses only on new or changed files.

## Required Capabilities

- Full-scan concept for initial discovery.
- Classification concept for personal-data findings and risk context.
- Owner-routing concept for review accountability.
- Human-review concept with decision reasons.
- Audit-log concept for evidence and outcomes.
- Delta-scan concept for ongoing governance.

## Explicitly Deferred

- Production Microsoft 365 integration.
- Real deletion of remote files.
- Authentication and authorization implementation.
- Persistent storage selection.
- AI model or vendor selection.
- User interface implementation.

## Product Constraints

- User-facing and repository text must be English.
- Deletion must be human-accountable.
- Sensitive snippets should be minimized or masked in any future UI.
- Requirements changes must update this document and `ACCEPTANCE.md`.

