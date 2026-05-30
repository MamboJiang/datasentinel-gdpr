# Context and Risk Judgment

## Problem Definition

After content extraction and deterministic signal detection, DataSentinel needs a visible stage that turns redacted evidence candidates into context, risk, retention-review signals, and human-review guidance. The stage must help reviewers prioritize accountable work without becoming a legal-advice engine or an automatic deletion mechanism.

This P0 slice is a deterministic, fixture-backed workflow connected to the existing scan lifecycle. It follows the previous source-inventory and content-extraction slice and the local Atlas-derived requirements referenced by `docs/design/source-inventory-content-extraction.md`.

## Scope

In scope:

- A scan-level `contextRisk` summary exposed as an optional field on the existing scan payload.
- A pipeline stage after `detecting_signals` and before scan completion.
- Deterministic context and risk counts derived from redacted evidence candidates, sample-family metadata, and active policy-pack guidance.
- Policy-pack version, risk-rule fingerprint, retention-review counts, and human-review boundary status.
- Dashboard visibility for context/risk status without exposing raw source content.
- Evaluation linkage through a context-risk rules hash and zero paid-service cost.

Out of scope:

- Legal advice, legal conclusions, or claims of GDPR compliance.
- Automatic deletion, quarantine, or remote file mutation.
- Production Microsoft Graph, OAuth, tenant, source download, database, queue, parser, OCR, NER, or LLM integration.
- Public endpoints for internal classification stages.
- Hard-coded legal rules inside scanner logic.

## Research Basis

- GDPR Article 4 defines personal data and processing broadly enough that context must be explicit rather than reduced to one detector label.
- GDPR Articles 24, 25, 32, and 35 repeatedly require risk-aware technical and organisational measures that consider nature, scope, context, purposes, cost, likelihood, and severity.
- EDPB-endorsed DPIA guidance treats high-risk processing as a structured assessment topic, so this slice presents risk as review triage and not a legal conclusion.
- Microsoft Presidio is a credible future production candidate for PII detection and anonymization because its official documentation describes analyzers, anonymizers, operators, and extensible recognizers. It is not added in P0 because deterministic fixtures are cheaper, reproducible, and sufficient for this acceptance slice.

References:

- Regulation (EU) 2016/679 on EUR-Lex: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016R0679
- EDPB DPIA high-risk processing guidance page: https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/data-protection-impact-assessments-high-risk-processing_en
- Microsoft Presidio documentation: https://microsoft.github.io/presidio/

## Atlas-Derived Requirements

| ID | Requirement |
| --- | --- |
| CTXRISK-REQ-001 | Context/risk judgment must run only after evidence candidates exist; it cannot invent findings without detector evidence. |
| CTXRISK-REQ-002 | Context classification must use source family, redacted evidence candidates, and active policy-pack guidance rather than raw file bodies. |
| CTXRISK-REQ-003 | Risk output must include evidence and policy rationale but must not make a legal conclusion. |
| CTXRISK-REQ-004 | Retention status must be neutral or review-required when metadata is insufficient; automated deletion is not allowed. |
| CTXRISK-REQ-005 | The active policy-pack version must be attached to the judgment output for audit and reproducibility. |
| CTXRISK-REQ-006 | Unknown context categories and unknown risk guidance must stay renderable by tolerant clients. |
| CTXRISK-REQ-007 | The stage must keep model calls and estimated paid-service cost at zero in P0. |
| CTXRISK-REQ-008 | The stage must preserve continuity for owner routing, review support, audit events, metrics, and evaluation. |

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Add a production classifier or NER dependency now | Closer to pilot reality | Adds runtime, data handling, model quality, and cost risk before backend boundaries are approved | Rejected for P0 |
| Use an LLM for context/risk explanations | Strong language output | Harder to reproduce, requires privacy controls, and adds paid-service cost | Rejected for P0 |
| Use Microsoft Presidio now | Mature open-source PII tooling and extensibility | Still requires backend runtime, language model packages, tuning, and redaction validation | Future candidate |
| Use deterministic fixture-backed policy guidance | Free, reproducible, testable, and aligned with current mock workflow | Does not classify arbitrary real documents | Accepted for P0 |
| Add a new public classification endpoint | Debuggable stage boundary | Expands public contract and encourages coupling to internal workflow | Rejected |
| Add optional `contextRisk` on existing scan payload | Observable and compatible with tolerant clients | Requires schema, mock, UI, and tests to stay synchronized | Accepted |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Extracting content | Extraction summarized | Redacted evidence candidates are counted | Detecting signals | Detector stage receives only internal evidence candidates |
| Detecting signals | Signals detected | Snippets are redacted and fingerprinted | Judging context risk | Build context/risk input from counts, source family, and policy pack |
| Detecting signals | No signals found | File was scanned successfully | No finding | Count scanned file without risk output |
| Judging context risk | Policy pack active | Guidance can be applied | Context risk judged | Attach policy-pack version and risk-rule fingerprint |
| Judging context risk | Guidance incomplete | Tolerant fallback is allowed | Context risk judged with neutral values | Mark unknown context/risk as neutral, not fatal |
| Judging context risk | Retention metadata insufficient | No reliable retention rule exists | Context risk judged with unknown retention | Avoid deletion or legal conclusion |
| Judging context risk | Judgment completes | Metrics are available | Scan completed | Publish counts, review-required boundary, and evaluation hash |
| Judging context risk | Blocking configuration missing | No active policy pack exists | Scan partial or failed | Preserve prior findings and expose problem details in backend implementations |

## Public Contract Strategy

The public contract does not gain a new endpoint. The scan payload may include optional `contextRisk` data:

- `status`
- `policyPackVersion`
- `riskRulesFingerprint`
- `assessedEvidenceCandidates`
- `contextClassifiedFindings`
- `riskAssessedFindings`
- `highRiskFindings`, `mediumRiskFindings`, and `lowRiskFindings`
- `retentionReviewFiles`
- `humanReviewRequiredFindings`
- `legalConclusionProvided`
- `contextCategories`
- `warnings`

Admin metrics may include optional context/risk counters. Evaluation may include `contextRiskRulesHash`. Clients must continue to ignore unknown fields and render missing optional values neutrally.

## Privacy and Security Boundaries

- The stage receives redacted evidence candidate counts and detector output references, not raw source content.
- Public payloads must not expose raw extracted text, file bodies, page images, unredacted personal data, salts, or secret classifier configuration.
- Risk explanation is operational review guidance, not legal advice.
- `legalConclusionProvided` must remain `false` in P0.
- Deletion remains represented only as a human-review decision candidate; no source file can be changed by this stage.
- Policy-pack version and risk-rule fingerprint must be visible for audit and rollback.

## Economic Affordability

P0 uses deterministic fixture-backed rules with zero model calls and zero estimated paid-service cost. A future production path should preserve this cost order:

1. Deterministic redacted evidence and policy-pack mapping.
2. Open-source PII tooling such as Microsoft Presidio when backend isolation exists.
3. OCR only for suspicious or sampled files after parser hardening.
4. AI-assisted explanation only for low-confidence or ambiguous contexts, with policy approval and evaluation.

## Rollback Path

If this slice creates UI or contract noise, remove the optional `contextRisk` field, optional metrics fields, Dashboard context/risk panel rows, and `contextRiskRulesHash`. The scan endpoint set and required fields remain unchanged, so rollback does not require a contract version bump.

## Primitive Acceptance Criteria

- A completed full scan exposes a `judging_context_risk` pipeline stage after `detecting_signals`.
- A running scan shows context/risk judgment as pending until extraction and signal detection complete.
- The completed scan exposes a `contextRisk` summary with policy-pack version, risk-rule fingerprint, assessed evidence count, context/risk counts, retention-review count, human-review count, and `legalConclusionProvided = false`.
- The Dashboard shows context/risk judgment status and policy version without exposing raw source content.
- Context/risk output remains deterministic, reproducible, and zero-cost in P0.
- Unknown or missing policy guidance remains neutral instead of blocking rendering.
- Not-ready sources cannot create context/risk state.
- Behavior tests cover running, completed, policy-pack version, no-legal-conclusion, no-raw-content, cost boundary, and not-ready-source paths.
