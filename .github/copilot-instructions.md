# lawdit Coding Instructions

Read these files before generating project code:

1. `AGENTS.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/API_CONTRACT.md`
4. `contracts/openapi.yaml`
5. `ACCEPTANCE.md`
6. `docs/GOVERNANCE_CONFIG.md`
7. `docs/GDPR_SAMPLE_REFERENCES.md`

Follow the API contract exactly. Use `contracts/mocks/` for frontend mock data and endpoint behavior before a backend is available.

Do not add real deletion, production OAuth, live Microsoft Graph access, or external service credentials in P0.

Use policy-pack and permission-boundary concepts for governance behavior. Do not hard-code legal rules or hide denied user actions without a reason.
