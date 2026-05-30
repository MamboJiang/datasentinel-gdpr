# OpenRouter AI Assistive Processing

## Problem Definition

DataSentinel needs an AI-assisted review boundary for cases where deterministic extraction, OCR, grep-style rules, and policy-pack context find evidence but cannot confidently describe operational context. The boundary must use OpenRouter, respect a 25 EUR project budget, avoid raw personal data leaving the system, and preserve the 12-stage GDPR Enterprise Expert Atlas control-tower workflow.

This is not a replacement for deterministic signal detection, policy packs, owner routing, human review, or legal judgment.

## Research Basis

- OpenRouter chat completions use `POST https://openrouter.ai/api/v1/chat/completions` with an `Authorization: Bearer` API key, JSON messages, model selection, and non-streaming responses when requested: https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request
- OpenRouter key status can be checked with `GET https://openrouter.ai/api/v1/key`, including usage and remaining key limit fields: https://openrouter.ai/docs/api/reference/limits
- OpenRouter authentication supports direct bearer-token calls and optional app attribution headers: https://openrouter.ai/docs/api/reference/authentication
- The Models API exposes model identifiers, context length, supported parameters, and per-token pricing: https://openrouter.ai/docs/guides/overview/models
- As checked on 2026-05-30 through the OpenRouter Models API, `google/gemini-3.1-flash-lite` is available with no expiration date, 1M context, and lower-cost high-volume extraction positioning. `google/gemini-2.0-flash-lite-001` is cheaper but has an expiration date of 2026-06-01, so it is not selected as the default.

## Requirements

| ID | Requirement |
| --- | --- |
| AI-REQ-001 | AI calls must be disabled unless `DATASENTINEL_AI_MODE=assistive` and `OPENROUTER_API_KEY` are present. |
| AI-REQ-002 | The application budget cap is 25 EUR and a conservative 25 USD OpenRouter credit cap by default. |
| AI-REQ-003 | Usage must be checked against OpenRouter key usage and `OPENROUTER_USAGE_BASELINE_USD` before calls when a baseline is configured. |
| AI-REQ-004 | If usage cannot be checked and fail-closed mode is enabled, no AI call may leave the process. |
| AI-REQ-005 | Source/policy context, OCR, and grep-style deterministic stages run before any AI escalation. |
| AI-REQ-006 | External AI input must be redacted, anchored to deterministic evidence, and tied to an active policy-pack context; raw extracted text, file bodies, page images, credentials, or unredacted personal data must not be sent. |
| AI-REQ-007 | AI output is context support inside Atlas stage 4 only; it must not provide legal advice, claim GDPR compliance, assign owners, decide permissions, create audit facts, or issue deletion instructions. |
| AI-REQ-008 | Existing P0 scans remain deterministic and show zero model calls unless an explicit assistive AI classification path is invoked. |
| AI-REQ-009 | Runtime metadata must show how the tier plan maps to all 12 Atlas stages so reviewers can verify that AI is bounded by owner routing, review support, audit, delta governance, and evaluation. |

## Options

| Option | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| Keep AI fully disabled | Cheapest and safest | Does not satisfy the requested AI configuration | Rejected |
| Add OpenRouter directly inside scan orchestration | Fast to call a model | Couples external side effects to core scan state and risks accidental spend | Rejected |
| Add an injected OpenRouter boundary plus budget guard | Keeps side effects at the edge, testable, reversible, and budgeted | Requires a small runtime configuration surface | Accepted |
| Use `google/gemini-2.0-flash-lite-001` by default | Lowest current listed price | Endpoint expires on 2026-06-01 | Rejected |
| Use `google/gemini-3.1-flash-lite` by default | Current, long-context, low-latency, suitable for simple extraction/classification | Higher price than deprecated Flash Lite 2.0 | Accepted |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| AI disabled | Runtime starts | `DATASENTINEL_AI_MODE != assistive` | Deterministic only | Report `ai.status = disabled` |
| Missing key | Runtime starts | Assistive mode enabled but no key exists | Deterministic only | Report `ai.status = missing_api_key` |
| Configured | Runtime starts | Assistive mode and key exist | Ready for preflight | Report provider, model, budget, and tier plan without exposing the key |
| Ready for preflight | Evidence candidate arrives | Candidate is redacted, deterministically anchored, policy-pack contextualized, and ambiguous | Usage checking | Estimate cost and request OpenRouter key usage |
| Ready for preflight | Evidence candidate arrives | Candidate is not redacted | Rejected | No external request |
| Ready for preflight | Evidence candidate arrives | Candidate has no deterministic anchor or policy-pack context | Rejected | No external request |
| Usage checking | Key usage returned | Estimated call stays within local budget and OpenRouter remaining limit | AI request allowed | Send redacted prompt to OpenRouter |
| Usage checking | Usage unavailable | Fail-closed is true | Rejected | No external request |
| Usage checking | Budget exceeded | Budget or key limit insufficient | Rejected | No external request |
| AI request allowed | Provider returns response | Response received | Review support available | Return model output to caller for human review support |
| AI request allowed | Provider error | HTTP or network error | Provider failed | Return controlled rejection; deterministic state remains unchanged |

## Impact Surface

- `backend/datasentinel/ai_config.py` loads ignored local AI runtime configuration.
- `backend/datasentinel/ai_gateway.py` owns OpenRouter HTTP calls and budget preflight.
- `backend/datasentinel/processing_pipeline.py` owns OCR/grep/AI tier planning and redacted AI classification entrypoints.
- `backend/datasentinel/demo_state.py` exposes AI runtime metadata in health, scan, metrics, and evaluation responses.
- `contracts/schemas/` documents optional `aiProcessing` metadata.
- `.env.example` documents safe local secret and budget variables.

No public endpoint is added. No production Microsoft Graph, OAuth, tenant, database, queue, deletion integration, or raw source-content export is added.

## Rollback Path

1. Set `DATASENTINEL_AI_MODE=off` or remove `OPENROUTER_API_KEY`.
2. Remove optional `aiProcessing` metadata from backend responses if the UI no longer needs visibility.
3. Remove `ai_config.py`, `ai_gateway.py`, `processing_pipeline.py`, and their tests.
4. Revert `.env.example` and documentation additions.

Existing deterministic mock scan, review, audit, metrics, and evaluation flows continue to work when AI is disabled.

## Primitive Acceptance Criteria

- Health, scan, metrics, and evaluation responses can show AI provider, model, budget, tier plan, safety boundaries, and zero model calls without exposing the API key.
- A redacted ambiguous evidence candidate can be planned for AI only after metadata, text/OCR, and grep-rule stages.
- A redacted ambiguous evidence candidate is eligible for AI only when deterministic anchors and active policy-pack context are present.
- Runtime metadata maps the tiers to the 12 Atlas stages: source/policy context, inventory/extraction, deterministic signal detection, context/risk, owner assignment, evidence cards, review permissions, human decision, audit, delta, admin metrics, and evaluation.
- An unredacted candidate is rejected before any external request.
- A configured budget baseline blocks a call when OpenRouter usage plus estimated call cost would exceed the 25 USD application cap.
- Fail-closed mode blocks a call when OpenRouter usage cannot be checked.
- Existing full-scan and delta-scan paths still run without paid AI calls unless an explicit assistive AI classification method is invoked.
