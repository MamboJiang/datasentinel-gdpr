# lawdit GDPR

**Turn scattered personal-data evidence into accountable GDPR review work.**

lawdit is a contract-first prototype for GDPR-relevant data discovery. It scans selected sources, explains redacted evidence, routes findings to accountable owners, supports human review, records audit events, and reports measurable evaluation metrics. It is built to show the governance loop around sensitive data, not just another one-time PII scan.

- Live demo: https://founder-force.uk/
- User guide: https://founder-force.uk/docs
- API contract: [contracts/openapi.yaml](contracts/openapi.yaml)
- Product docs: [docs](docs)

## Why It Matters

Organizations often know personal data is spread across documents, exports, shared drives, and ad hoc review folders. The hard part is proving what was found, who owns the decision, what action was allowed, and whether the workflow improved. lawdit makes that chain visible.

## What The Prototype Does

- Detects GDPR-relevant evidence across PDFs, Office-style documents, text, tables, archives, email exports, images, and selected Google Drive sources.
- Keeps sensitive source values redacted while preserving reviewable evidence locations such as page, table cell, structure path, OCR region, or text offset.
- Routes findings to responsible owners and exposes permission boundaries instead of hiding denied actions.
- Lets humans record keep, delete-candidate, false-positive, reassign, or escalation decisions with reasons.
- Records audit events for scan and review activity.
- Shows evaluation metrics including precision, recall, F1, reproducibility, throughput, and resource intensity.
- Uses governance policy-pack concepts so review rules can change without hard-coding one legal snapshot into the scanner.

## Demo Walkthrough

1. Open the live demo at https://founder-force.uk/.
2. Start with the public analysis entry for a single-file redacted preview, or open `/dashboard` for the governed Workspace flow.
3. Check source readiness, then start a full scan against the controlled demo source or an approved selected source.
4. Open a high-risk finding and inspect redacted evidence, signal labels, owner routing, retention status, and review support.
5. Record a human decision with a reason.
6. Confirm the matching audit event and review the evaluation dashboard.
7. Open https://founder-force.uk/docs for the task-oriented guide.

Deletion is simulated in this prototype. lawdit does not provide legal advice, does not claim full GDPR compliance, and does not implement production tenant-wide Microsoft Graph or deletion integrations.

## Local Development

### Backend API

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m backend.lawdit.db_tool init --db-path .lawdit.sqlite3
python -m backend.lawdit.source_server --host 127.0.0.1 --port 8000 --db-path .lawdit.sqlite3
```

### Frontend Console

```bash
cd frontend
npm ci
npm run dev
```

### User Documentation

```bash
cd docs-site
npm ci
npm run dev
```

## Repository Map

- `backend/lawdit/` - Python API server, scanner pipeline, persistence, evidence assembly, audit, and evaluation support.
- `frontend/` - Vite/React product console and public homepage.
- `docs-site/` - Fumadocs user guide served at `/docs`.
- `contracts/` - OpenAPI contract, schemas, and mock payloads shared by frontend and backend.
- `docs/` - product, technical, deployment, governance, security, demo, and test documentation.
- `tests/` - backend and contract behavior tests plus GDPR sample fixtures.

## Validation

```bash
python -m pytest
cd frontend && npm run test && npm run build
cd ../docs-site && npm run typecheck && npm run build
```

## Project Boundaries

- No automatic deletion.
- No legal advice or full-compliance claim.
- No production Microsoft 365 tenant inventory, production OAuth tenant access, or production deletion connector in P0.
- No raw sensitive values in public analysis output, audit events, or review payloads.
- Clients must tolerate optional fields and unknown enum-like values according to the API contract.

All repository documentation, issues, pull requests, commit messages, contracts, mocks, and developer-facing comments should be written in English. User-facing interface copy may be localized through reviewed frontend dictionaries.
