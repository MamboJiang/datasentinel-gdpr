# Test Cases

## Current Initialization Checks

| ID | Scenario | Expected Result |
| --- | --- | --- |
| INIT-001 | Review repository language | All tracked project files are written in English. |
| INIT-002 | Review repository scope | No implementation code or runtime dependency files are present. |
| INIT-003 | Review required documents | README, BRD, MRD, PRD, TRD, DesignSpec, TestCase, and ACCEPTANCE exist. |
| INIT-004 | Review GitHub visibility | The remote repository is public. |
| INIT-005 | Review collaborators | Requested teammates are invited or already present as collaborators. |

## Future Behavior Test Themes

These are not implementation tests yet. They define the areas that future tests should cover:

- Full-scan behavior with controlled sample files.
- Classification behavior for GDPR-relevant evidence.
- Owner-routing behavior when owner metadata is present or missing.
- Human-review decisions for delete, retain, mask, archive, and escalate.
- Audit-event behavior for every visible state transition.
- Delta-scan behavior for unchanged, changed, new, and deleted files.

