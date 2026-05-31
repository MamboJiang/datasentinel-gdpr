# Deterministic Signal Detection

## Problem Definition

After inventory and extraction, DataSentinel needs an explicit deterministic signal-detection stage before context/risk judgment. The Atlas requires evidence-first discovery: rules should detect concrete evidence such as email addresses, employee IDs, government identifiers, online identifiers, location data, financial data, special-category indicators, signatures, access roles, reimbursement data, and feedback comments before risk, owner routing, or review guidance is shown.

This P0 slice stays fixture-backed and deterministic. It does not add runtime parsers, OCR, NER, LLMs, production storage, Microsoft Graph, OAuth, tenant access, deletion, or a new public endpoint.

## Scope

In scope:

- A scan-level optional `signalDetection` summary on the existing scan payload.
- A visible `detecting_signals` pipeline stage after `extracting_content` and before `judging_context_risk`.
- Detector rules version/hash, active policy evidence requirements, evaluated evidence-candidate count, redacted signal count, findings-with-signals count, signal-type counts, warnings, and `rawContentExposed = false`.
- Finding evidence cards continue to expose redacted signal details through existing finding payloads.
- Prelaunch rules cover labeled names, dates of birth, employee/student/government identifiers, passport and driver-license fields, payment and bank data, online and device identifiers, location data, vehicle plates, access context, incident descriptions, supplier tax IDs/addresses, health, biometric, genetic, race/ethnicity, political, religious, trade-union, sexual-orientation, criminal-record, family/minor, compensation, credential-secret, and feedback-comment fields in addition to email, phone, URL, handle, SSN/NINO, IP, MAC, UUID, coordinate, payment-card, and IBAN-like patterns.
- Evaluation and admin metrics preserve signal-detection rules traceability.

Out of scope:

- Public raw extraction endpoint or raw detector payload.
- Production PII/NER/OCR dependencies.
- Hidden legal conclusions, automatic deletion, retention-label writes, access changes, or source mutation.

## Research Basis

- `docs/reference/GDPR_ENTERPRISE_EXPERT_ATLAS.md` requires deterministic evidence before AI/context judgment and human-accountable decisions.
- GDPR Article 4 identifies names, identification numbers, location data, online identifiers, and physical, physiological, genetic, mental, economic, cultural, or social identity factors as personal-data identifiers.
- GDPR Article 9 identifies special categories including racial or ethnic origin, political opinions, religious or philosophical beliefs, trade-union membership, genetic data, biometric data, health data, sex life, and sexual orientation.
- GDPR Article 5 principles on data minimisation, integrity/confidentiality, and accountability support exposing only redacted evidence and rule fingerprints.
- European Commission GDPR principles guidance identifies minimisation, storage limitation, integrity/confidentiality, and accountability as processing constraints.
- EDPB right-of-access guidance reinforces that data-subject workflows require prepared procedures and evidence handling, not ad hoc search output.

References:

- Regulation (EU) 2016/679 on EUR-Lex: https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng
- European Commission GDPR principles overview: https://commission.europa.eu/law/law-topic/data-protection/data-protection-explained_en
- EDPB Guidelines 01/2022 on right of access: https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-012022-data-subject-rights-right-access_en

## Atlas-Derived Requirements

| ID | Requirement |
| --- | --- |
| SIGNAL-REQ-001 | Signal detection must run after content extraction and before context/risk judgment. |
| SIGNAL-REQ-002 | Detector input may use extracted text only inside the internal processing boundary. |
| SIGNAL-REQ-003 | Detector output crossing the public contract must be redacted, counted, and traceable by rules version/hash. |
| SIGNAL-REQ-004 | Evidence requirements from the active policy pack must be preserved with the signal-detection summary. |
| SIGNAL-REQ-005 | Findings may be assembled only from redacted signals; raw snippets must not cross the API boundary. |
| SIGNAL-REQ-006 | Unsupported, unreadable, or OCR-deferred extraction inputs produce warnings rather than hidden detector success. |
| SIGNAL-REQ-007 | Signal detection must remain deterministic, reproducible, zero-model-call, and zero-paid-service in P0. |
| SIGNAL-REQ-008 | Evaluation must preserve the detector rules hash and signal-detection stage status. |

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Keep signal detection only as a pipeline label | Minimal change | Fails Atlas traceability because rule hash, counts, and evidence requirements are invisible | Rejected |
| Add optional `signalDetection` to the existing scan payload | Observable, reversible, tolerant-client compatible | Requires docs, schema, mocks, types, tests, and metrics to stay synchronized | Accepted |
| Add a public detection endpoint | Easy debugging | Expands the public API and increases raw-content leakage risk | Rejected |
| Add production NER/OCR/LLM detection now | Closer to future backend | Adds privacy, dependency, reproducibility, and cost risks outside P0 | Rejected |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Extracting content | Extraction running | Extraction is incomplete | Signal detection pending | Return pending summary and no public signal details |
| Extracting content | Extraction completed | Raw text remains internal and evidence candidates exist | Detecting signals | Apply deterministic P0 detector rules |
| Detecting signals | Signal matched | Snippet can be redacted | Redacted signal available | Count type, detector, confidence, and redacted signal |
| Detecting signals | Candidate has no match | Candidate was evaluated | No signal | Count evaluated candidate without creating a finding |
| Detecting signals | Unsupported/OCR-deferred input exists | Failure is recoverable | Detection completed with warnings | Keep warning visible for metrics/evaluation |
| Detecting signals | Raw-content boundary fails | `rawContentExposed = true` | Detection failed or unsafe | Backend implementations must stop public publication |
| Detection completed | Signal summary ready | Rules hash and policy evidence requirements are attached | Judging context risk | Context/risk can consume redacted signal counts and references |

## Public Contract Strategy

The public contract does not gain a new endpoint. `GET /api/scans/{scanId}` may include optional `signalDetection`:

- `status`
- `detectorRulesVersion`
- `detectorRulesHash`
- `evidenceRequirements`
- `evaluatedEvidenceCandidates`
- `detectedSignals`
- `redactedSignals`
- `findingsWithSignals`
- `rawContentExposed`
- `signalTypeCounts`
- `warnings`

Finding details continue to expose redacted `signals` with detector, confidence, snippet, and location when available. Clients must ignore unknown fields and render missing optional signal summaries neutrally.

## Privacy and Security Boundaries

- Raw extracted text, full source content, page images, credentials, detector secrets, and unredacted personal data must not cross the public API boundary.
- Signal snippets must be redacted before they are assembled into evidence cards and must not include adjacent raw source context around the match.
- Human-entered reasons remain handled by the audit sanitization boundary, not by detector output.
- Signal detection is evidence generation, not legal advice and not deletion execution.

## Impact Surface

- `contracts/schemas/source-scan.yaml`, `contracts/schemas/metrics.yaml`, and `contracts/mocks/` gain optional signal-detection fields only.
- `frontend/src/types/`, `frontend/src/data/`, and Dashboard presentation gain a small deterministic signal summary.
- `docs/API_CONTRACT.md`, `docs/PRD.md`, `docs/TRD.md`, `docs/DesignSpec.md`, `docs/TestCase.md`, `docs/EVALUATION.md`, and `ACCEPTANCE.md` gain the explicit stage requirements.

## Rollback Path

Remove optional `scan.signalDetection`, optional signal counters, `signalDetectionRulesHash`, and Dashboard signal text. Keep the `detecting_signals` pipeline label and existing finding `signals` shape. Required endpoints and required fields remain unchanged, so rollback does not require a contract version bump.

## Primitive Acceptance Criteria

- Running scans expose `signalDetection.status = pending` while extraction is incomplete.
- Completed scans expose `detecting_signals` between `extracting_content` and `judging_context_risk`.
- Completed scans expose detector rules version/hash, policy evidence requirements, evaluated evidence candidates, detected/redacted signal counts, findings-with-signals count, signal-type counts, warnings, and `rawContentExposed = false`.
- Finding details expose only redacted signal snippets; no raw extracted text, full file bodies, page images, adjacent raw match context, source URLs, absolute source paths, or unredacted personal data appear in public payloads or UI surfaces.
- Labeled forms with completed identifiers, contact, employment, financial, location, online/device, health, biometric, genetic, special-category, family/minor, credential, and incident/access fields produce findings even when the file contains no email address.
- Admin metrics expose signal counts, and evaluation preserves the signal-detection rules hash.
- Not-ready sources cannot create extraction, signal-detection, finding, audit, metric, or evaluation state.
- Automated behavior tests cover running pending state, completed signal counts, redaction boundary, rules hash, metrics, evaluation traceability, and not-ready-source continuity.
