# Organizer Sample References

## Source

The organizer sample repository is `a-klumpp/GDPR-data-samples`:

https://github.com/a-klumpp/GDPR-data-samples

The repository is public and contains PDF sample families for:

- `Expense_Report`
- `IT_Access_Request`
- `Incident_Report`
- `Supplier_Onboarding`
- `Training_Evaluation`

These names were verified from the public GitHub repository listing on 2026-05-30.

## Contract Usage

The sample repository is represented as a mock source in `contracts/mocks/sources.json` with `sourceType = organizer_sample_repo`.

## Google Drive Corpus Index

The working Google Drive corpus requested for core-engine testing is indexed locally at:

- `tests/fixtures/gdpr_data_samples_main/drive_manifest.json`
- `tests/fixtures/gdpr_data_samples_main/core_multilingual_cases.json`
- `tests/fixtures/gdpr_data_samples_main/generated_format_challenges.json`
- `tests/fixtures/gdpr_data_samples_main/raw_corpus_manifest.json`
- `tests/fixtures/gdpr_data_samples_main/corpus_scan_report.json`

The Drive folder is `GDPR-data-samples-main` with folder ID `1AmTxh7RhEyvgo400SAZHI8s_CawvAdQn`. The local manifest records original Drive file IDs, filenames, MIME types, and corpus roles observed on 2026-05-31. It includes the organizer PDF families plus a non-English PDF and image OCR challenge file.

`core_multilingual_cases.json` is the deterministic local test companion for the core engine. It preserves multilingual source-text cases for Chinese, French, Spanish, German, Italian, Portuguese, Dutch, Polish, Japanese, Korean, and Arabic labels so automated tests can run without a live Google Drive token.

`generated_format_challenges.json` is the generated high-difficulty companion corpus. It covers multilingual CSV, HTML, XML, JSONL, UTF-16 text, RTF, DOCX, XLSX, PPTX, ODT, ODS, ODP, EML, ZIP, image OCR, PDF OCR, and VTT transcript inputs without modifying Drive originals. Raw video frame OCR and legacy Office conversion coverage are generated at test runtime as temporary files and recorded only through redacted validation evidence.

`engine_hardening_validation_report.json` is the redacted final-hardening evidence record. It records the read-only live Drive folder check, local and agent-us validation commands, static-format deepening for header-row CSV, Markdown tables, source-review context windows, and mixed PDFs, supported-format UI proof, deployed release identifiers, OCR/converter runtime capability, and real OCR/image/PDF/video-frame/legacy-Office smoke-test summaries without raw source values or provider tokens.

`core_engine_performance_report.json` and `core_engine_performance_report_agent_us.json` are the redacted mixed-format benchmark records. They record parser/detector throughput, peak RSS, format counts, signal-type counts, OCR-deferred counts, and signal-cap behavior for generated challenges, raw corpus files, and an oversized text stream without raw source values or private paths. The `agent_us` report is the deployed-runtime proof with host-local Tesseract and `pdftoppm` available.

`live_drive_scan_report_agent_us.json` is the redacted live server-scan record. It proves the deployed `agent-us` runtime can scan the `GDPR-data-samples-main` folder through an account-level Google Drive binding, record aggregate extraction/finding/source-preview metrics, and keep provider tokens, Drive URLs, raw source bodies, raw detected values, page images, and private absolute paths out of the report.

`raw_corpus_manifest.json` locks the vendored local corpus files with source origin, role, byte size, SHA-256, and Drive file ID coverage. `corpus_scan_report.json` records the latest local verification outcome as extraction methods, recognition difficulty, OCR capability state, counts, and signal types only. Neither file may include raw extracted text or raw detected values.

Frontend use:

- Show it as the default demo source.
- Let users start a full scan from this source in mock mode.
- Show sample families as source metadata.

Backend use:

- Start with metadata-only source registration.
- Keep the Google Drive corpus manifest in `tests/fixtures/gdpr_data_samples_main/`.
- Do not modify raw Google Drive samples in place.
- Treat local raw corpus files as immutable test inputs.
- When refreshing or converting raw binary samples for local tests, preserve source identity through original Drive filenames and IDs in the manifests, regenerate checksums, and keep raw source bodies out of public payloads.

Evaluation use:

- Use sample families as controlled categories for scanner behavior.
- Store labels separately from downloaded files.
- Keep policy-pack version and dataset hash in evaluation output.

## Boundary

This repository stores the corpus manifests, focused local deterministic test cases, and scoped raw local copies needed for repeatable core-engine verification. Raw corpus files are test inputs only; production source registration remains metadata-first and must not expose raw source bodies in API payloads or UI surfaces.
