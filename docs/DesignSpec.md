# Design Specification

## Design Goal

The future product experience should make GDPR data cleanup feel like an accountable review workflow, not an automatic deletion tool.

## Conceptual Workflow State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Source selected | Full scan requested | Source is readable | Scanning | Record scan start |
| Scanning | File analyzed | File can be parsed | Finding classified | Store finding evidence |
| Scanning | File cannot be parsed | Error is recoverable | Needs review | Record extraction issue |
| Finding classified | Owner resolved | Owner confidence is sufficient | Assigned | Notify or queue owner |
| Finding classified | Owner unresolved | No reliable owner | Escalated | Queue for privacy team |
| Assigned | Reviewer decides delete | Reviewer is authorized | Delete approved | Record decision and reason |
| Assigned | Reviewer decides retain | Reviewer gives reason | Retain approved | Record exception |
| Assigned | Reviewer escalates | Escalation target exists | Escalated | Record escalation |
| Delete approved | Deletion executed | Deletion is supported | Closed | Record deletion result |
| Delete approved | Deletion fails | Failure is recoverable | Needs review | Record failure |
| Closed | Delta scan requested | Previous scan baseline exists | Scanning changes | Compare changed files only |

## Experience Principles

- Show evidence, not hidden model conclusions.
- Mask sensitive snippets by default.
- Keep every decision attributable to a human or system actor.
- Make deletion, retention, and escalation reasons visible in the audit trail.
- Separate risk explanation from legal conclusion.

## Deferred Design Decisions

- Visual design system.
- Information architecture.
- Interaction details.
- Framework-specific components.
- Data persistence model.

