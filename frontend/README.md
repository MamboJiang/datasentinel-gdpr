# DataSentinel Frontend

Contract-backed React frontend for the DataSentinel GDPR discovery prototype.

## Run Locally

```bash
npm install
npm run dev
```

## Validate

```bash
npm run lint
npm run build
```

## Data Boundary

The frontend imports the fixtures in `../contracts/mocks/` directly. It does not connect to production services, perform real deletion, or expose raw sensitive evidence.
