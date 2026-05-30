# Test Cases

## Current Initialization Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| INIT-001 | Review repository language | All tracked project files are written in English. |
| INIT-002 | Review repository scope | No implementation code or runtime dependency files are present. |
| INIT-003 | Review required documents | README, BRD, MRD, PRD, TRD, DesignSpec, TestCase, and ACCEPTANCE exist. |
| INIT-004 | Review GitHub visibility | The remote repository is public. |
| INIT-005 | Review collaborators | Requested teammates are invited or already present as collaborators. |

## Contract Readiness Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| CONTRACT-001 | Parse contract YAML files | `contracts/openapi.yaml` and files in `contracts/schemas/` parse as YAML. |
| CONTRACT-002 | Parse mock payloads | Every file in `contracts/mocks/` parses as JSON. |
| CONTRACT-003 | Compare contract docs and mocks | Mock payloads use the envelope, field names, and state values documented in `docs/API_CONTRACT.md`. |
| CONTRACT-004 | Review tolerant compatibility rules | Unknown fields, optional fields, empty arrays, partial data, and unknown enum-like values have documented behavior. |
| CONTRACT-005 | Review error contract | Errors are documented as `application/problem+json` with trace IDs. |
| CONTRACT-006 | Review AI instructions | `AGENTS.md` and `.github/copilot-instructions.md` tell AI tools to follow the contract and avoid unapproved implementation. |
| CONTRACT-007 | Review governance contract | Governance config, active policy pack, permissions, and review support endpoints are documented and mocked. |
| CONTRACT-008 | Review organizer sample source | The organizer sample repository is represented as a default demo source without vendoring PDFs. |

## Future Behavior Test Themes

These are not implementation tests yet. They define the areas that future tests should cover:

- Full-scan behavior with controlled sample files.
- Classification behavior for GDPR-relevant evidence.
- Owner-routing behavior when owner metadata is present or missing.
- Human-review decisions for delete, retain, mask, archive, and escalate.
- Audit-event behavior for every visible state transition.
- Delta-scan behavior for unchanged, changed, new, and deleted files.
- Evaluation behavior for precision, recall, F1, reproducibility, throughput, and resource intensity.
- Governance behavior for policy-pack changes, org model changes, task transfers, and permission boundaries.
