# GDPR Data Samples Main Fixtures

This directory preserves the project-facing test-corpus contract for the Google Drive folder `GDPR-data-samples-main`.

- `drive_manifest.json` records the Drive folder ID, observed timestamp, filenames, MIME types, and file IDs. It is the maintenance index for the external corpus.
- `core_multilingual_cases.json` contains synthetic multilingual source-text cases used by automated deterministic scanner tests.
- `generated_format_challenges.json` contains synthetic multilingual CSV, HTML, Office, image OCR, PDF OCR, and transcript cases generated for high-difficulty format tests without mutating Drive originals. Raw video frame OCR and legacy Office conversion use temporary files generated during runtime tests; the video, legacy Office bytes, converted text, and OCR text are not persisted here.
- `raw/` contains immutable local copies needed for repeatable core-engine verification. Organizer sample PDFs are mirrored from the public `a-klumpp/GDPR-data-samples` commit recorded in `raw/organizer_samples/SOURCE_COMMIT.txt`; Drive-only files are stored in `raw/drive_only/` with stable local filenames and their original Drive names recorded in the manifests.
- `raw_corpus_manifest.json` locks every raw corpus file with byte size, SHA-256, origin, role, and Drive file ID when applicable.
- `corpus_scan_report.json` records the latest local scan evidence as counts, extraction methods, OCR capability state, recognition difficulty, and signal types only. It must not contain raw extracted text or raw detected values.
- `core_engine_quality_report.json` records deterministic oracle quality for multilingual and generated-format cases as type precision, recall, F1, false-positive type counts, and false-negative type counts only. It must not contain raw source text or raw detected values.
- `engine_hardening_validation_report.json` records the latest final-hardening validation evidence for local tests, static-format CSV/Markdown/PDF deepening, redacted source-review context windows, supported-format UI proof, agent-us deployment, OCR/runtime converter capability, and real OCR/image/PDF/video-frame/legacy-Office smoke tests without raw values or provider tokens.
- `core_engine_performance_report.json` records the latest local mixed-format benchmark evidence as counts, throughput, peak RSS, format counts, signal-type counts, OCR-deferred counts, and signal-cap behavior without raw values, source bodies, provider tokens, or private absolute paths.
- `core_engine_performance_report_agent_us.json` records the same benchmark from the deployed `agent-us` runtime with host-local OCR packages available.
- `live_drive_scan_report_agent_us.json` records a server-side Google Drive scan of the `GDPR-data-samples-main` folder through the deployed `agent-us` account binding as aggregate counts, mixed PDF OCR evidence, and redaction-boundary evidence only. Regenerate it with `scripts/generate_live_drive_scan_report.py` on the deployed host.

The core engine tests read the local multilingual cases and the raw corpus manifest without requiring a live Google Drive token.

Refresh rule:

1. Update `drive_manifest.json` from the Drive folder.
2. Replace raw files only when the source file intentionally changes.
3. Regenerate `raw_corpus_manifest.json`, `corpus_scan_report.json`, `core_engine_quality_report.json`, `engine_hardening_validation_report.json`, `core_engine_performance_report.json`, `core_engine_performance_report_agent_us.json`, and `live_drive_scan_report_agent_us.json` when final-hardening validation evidence changes.
4. Run `python3 -m unittest tests.test_gdpr_data_samples_corpus tests.test_core_engine_detection tests.test_generated_format_challenges tests.test_core_engine_quality_report tests.test_core_engine_performance_report tests.test_live_drive_scan_report`.
5. Update `ACCEPTANCE.md` and `docs/TestCase.md` if corpus coverage, behavior, states, or acceptance criteria change.
