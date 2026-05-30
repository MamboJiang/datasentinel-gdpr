# Finding Assembly and Evidence Card

## Problem Definition

After owner routing, DataSentinel needs a visible assembly stage that turns redacted detector signals, context/risk output, owner assignment, policy context, and audit history into contract-compatible finding rows and evidence-card detail views. The stage must prove continuity from earlier workflow steps without becoming a production scanner, legal-advice engine, or deletion mechanism.

The separate local Atlas markdown referenced by the user was not present in this repository or the searched parent document directory at implementation time. This design therefore applies the Atlas-derived continuity requirements already recorded in `docs/design/context-risk-judgment.md` and `docs/design/owner-routing-assignment.md`, plus the governance contract.

## Scope

In scope:

- A scan-level optional `findingAssembly` summary on the existing scan payload.
- A visible `assembling_findings` pipeline stage after `assigning_owner`.
- Deterministic fixture-backed finding rows and evidence-card details assembled from previous stage summaries.
- Policy-pack version, source snapshot, assembly fingerprint, evidence-card counts, missing-card count, denied-action count, redaction boundary, and no-legal-conclusion boundary.
- Frontend mock workflow continuity from scan completion to findings list, finding detail, file review, permission boundary display, audit, metrics, and evaluation.

Out of scope:

- New public endpoints.
- Production parsers, OCR, NER, embeddings, vector search, LLMs, storage, queues, directory sync, notifications, or Microsoft Graph.
- Automatic deletion, quarantine, source mutation, or permission changes.
- Legal advice, legal conclusions, or full GDPR compliance claims.
- Raw source content, file bodies, page images, unredacted personal data, salts, or detector secrets in public payloads.

## Research Basis

- GDPR Article 5 includes data minimisation, storage limitation, integrity/confidentiality, and accountability; the stage therefore keeps evidence redacted, preserves policy context, and records attributable audit events.
- GDPR Article 24 requires controller responsibility measures that consider nature, scope, context, purpose, risk, and implementation cost; the stage therefore remains deterministic and policy-pack driven in P0.
- GDPR Article 32 frames security measures around risk and implementation cost; the stage avoids raw-content exposure and paid model calls in P0.
- The EDPB DPIA guidance treats high-risk processing as a structured assessment topic; evidence cards present review triage and not legal conclusions.
- Microsoft Presidio remains a future production candidate for PII detection and anonymization because its official documentation describes analyzer and anonymizer components. It is not added here because this P0 slice only assembles already-redacted fixture signals.

References:

- Regulation (EU) 2016/679 on EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- EDPB DPIA high-risk processing guidance: https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/data-protection-impact-assessments-high-risk-processing_en
- Microsoft Presidio documentation: https://microsoft.github.io/presidio/

## Atlas-Derived Requirements

| ID | Requirement |
| --- | --- |
| FINDASM-REQ-001 | Finding assembly must run only after redacted signals, context/risk judgment, and owner assignment exist. |
| FINDASM-REQ-002 | Each assembled finding must have at least one redacted evidence signal and an evidence card. |
| FINDASM-REQ-003 | Evidence cards must show evidence, policy context, owner routing, retention status, action boundaries, and audit history without raw source content. |
| FINDASM-REQ-004 | Assembly output must preserve policy-pack version, source snapshot, and deterministic assembly fingerprint for audit and evaluation. |
| FINDASM-REQ-005 | Missing evidence, missing owner routing, or raw-content boundary failures must be visible as warnings, not hidden success. |
| FINDASM-REQ-006 | The stage must not make legal conclusions, claim full GDPR compliance, or execute deletion. |
| FINDASM-REQ-007 | Unknown optional fields and unknown enum-like values must remain renderable by tolerant clients. |
| FINDASM-REQ-008 | The stage must keep model calls and estimated paid-service cost at zero in P0. |

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Keep static finding fixtures disconnected from scan completion | Fast and low risk | Does not prove continuity from earlier stages | Rejected |
| Generate evidence cards directly in UI components | Quick visual result | Hides workflow logic in presentation and weakens tests | Rejected |
| Add a production PII dependency now | Closer to future backend reality | Adds runtime, privacy, tuning, and cost risk before backend boundaries exist | Rejected for P0 |
| Use deterministic fixture-backed assembly from previous summaries | Reproducible, testable, zero-cost, contract-compatible | Does not classify arbitrary documents | Accepted |
| Add a public assembly endpoint | Debuggable | Expands the contract before needed | Rejected |
| Add optional `findingAssembly` to scan payload | Observable with tolerant clients and no endpoint churn | Requires schema, mocks, docs, UI, and tests to stay synchronized | Accepted |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Assigning owner | Owner assignment pending | Context/risk is incomplete | Assembly pending | Preserve existing findings; expose pending summary |
| Assigning owner | Owner assignment completed | Assigned finding count is available | Assembling findings | Build assembly input from redacted signals, context/risk, owners, policy pack, and audit context |
| Assembling findings | Evidence signals available | Signal snippets are redacted | Evidence cards assembled | Publish finding rows and detail map |
| Assembling findings | Evidence missing | Missing-card count is nonzero | Assembly warning | Preserve warning and do not hide incomplete cards |
| Assembling findings | Raw-content boundary fails | `rawContentExposed = true` | Assembly warning or failure | Preserve warning; backend implementation may fail the scan |
| Assembling findings | Assembly completed | Every assigned finding has an evidence card | Scan completed | Publish `findingAssembly`, metrics, audit event, and evaluation hash |
| Evidence card visible | Reviewer opens file review | Actor can read assigned finding | Redacted review surface | Focus the selected redacted evidence anchor |
| Evidence card visible | Reviewer opens action boundary | Permission data exists | Boundary visible | Show allowed actions and denied actions before submit |

## Public Contract Strategy

The public contract does not gain a new endpoint. The scan payload may include optional `findingAssembly` data:

- `status`
- `policyPackVersion`
- `sourceSnapshotId`
- `assemblyRulesFingerprint`
- `assembledFindings`
- `evidenceCards`
- `evidenceSignals`
- `redactedEvidenceSnippets`
- `missingEvidenceCards`
- `deniedActionCount`
- `rawContentExposed`
- `legalConclusionProvided`
- `warnings`

Finding rows may include optional `evidenceSignalCount` and `policyPackVersion`. Finding details continue to use the existing evidence-card shape with `signals`, `riskExplanation`, `policyContext`, `owner`, `availableActions`, `deniedActions`, and `auditTimeline`.

## Impact Surface

- `contracts/schemas/source-scan.yaml`, `contracts/schemas/finding-review.yaml`, and `contracts/schemas/metrics.yaml` gain optional fields only.
- `contracts/mocks/` gain synchronized assembly, evidence-card, audit, metrics, and evaluation data.
- `frontend/src/data/` gains an assembly boundary and connects scan completion to findings and detail maps.
- Findings and Finding Detail UI show evidence count and action boundary data already provided by the contract.
- Tests verify running, completed, redaction, no-legal-conclusion, zero-cost, ownerless escalation, audit, and evaluation continuity.

## Privacy and Security Boundaries

- Public payloads must never include raw extracted text, full file content, page images, unredacted personal data, salts, detector secrets, directory tokens, or hidden permission data.
- Evidence-card snippets must be pre-redacted before they reach UI components.
- Denied actions must be visible when the contract provides them.
- `legalConclusionProvided` remains `false`.
- Real deletion remains disabled and visible as a denied action or simulated review decision.

## Economic Affordability

P0 uses deterministic fixture-backed assembly with zero model calls, zero estimated paid-service cost, and no new runtime dependency. Future production work should preserve this order:

1. Deterministic redacted evidence assembly from backend-reviewed signals.
2. Open-source detection and anonymization tools such as Microsoft Presidio after backend isolation exists.
3. OCR only for selected unsupported or high-value files after parser hardening.
4. AI-assisted explanations only for low-confidence contexts after privacy, cost, and evaluation controls are approved.

## Rollback Path

Remove optional `findingAssembly`, the `assembling_findings` pipeline stage, optional finding row fields, optional metrics, the evaluation hash, and the assembly mock workflow. Existing required endpoints and required fields remain unchanged, so rollback does not require a contract version bump.

## Primitive Acceptance Criteria

- A running full scan exposes `findingAssembly.status = pending` and `assembling_findings` after `assigning_owner`.
- A completed scan exposes `findingAssembly` with policy-pack version, source snapshot, assembly fingerprint, assembled finding count, evidence-card count, evidence signal count, missing-card count, denied-action count, `rawContentExposed = false`, and `legalConclusionProvided = false`.
- Completed scan findings are assembled from the completed scan ID and previous stage summaries, not from disconnected static rows.
- Every assembled finding detail has at least one redacted signal, policy context, owner assignment, retention status, allowed or denied action boundary, and audit timeline.
- Missing owner metadata routes assembled findings to escalation instead of leaving them unowned.
- The Findings table and Finding Detail evidence card remain renderable with tolerant optional fields.
- Finding assembly creates an audit-visible event and evaluation preserves an assembly rules hash.
- The stage remains deterministic with zero model calls and zero estimated paid-service cost.
- Not-ready sources cannot create scan, assembly, finding, evidence-card, or audit state changes.
