# Sapote-Mamey Release Checklist — v9.4

Run this checklist before moving from `DEV_CANDIDATE` to `PUBLIC_RELEASE`.  
Each item must be ✅ (confirmed) or explicitly documented as a known limitation in `RELEASE_MANIFEST.md`.

---

## Gate 1 — Document synchronization

- [ ] Exactly one active parent controller exists: `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md`
- [ ] All prior monoliths moved to `docs/legacy/` with `HISTORICAL_DO_NOT_USE_AS_CONTROLLER` banner
- [ ] Stale-term scan passed: no occurrences of `v8.1`, the retired project codename (renamed to ``), `Davey`, `optional RG-GMCI`, `PENDING` (in required fields), `Full Coverage Mode`. *(Do NOT flag `Bert` — live literature-mode feature per BERT_MODE_PROTOCOL/§21; or `v8.4 candidate` — intentional backward-compat triggers in §0/§0.11. the retired project codename (renamed to ``)→`` and `Davey`→`Rapid Literature Deep Dive` were renamed out; flag any residual.)*
- [ ] Affiliation: 
- [ ] `docs/DELIVERABLE_CONTRACT.md` present and consistent with `CLAUDE_SYSTEM_PROMPT.md §4–§5`
- [ ] `docs/HOW_TO_USE.md` step sequence matches actual CLI behavior
- [ ] All derived prompts regenerated from v9.4 monolith (not copy-pasted from v8.x)

## Gate 2 — Prompt quality

- [ ] `prompts/CLAUDE_SYSTEM_PROMPT.md` mandates all §4 per-strain deliverables without asking the user
- [ ] `prompts/CLAUDE_SYSTEM_PROMPT.md` mandates all §5 project-bundle deliverables without asking
- [ ] `prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md` includes all all required scan names and completion rules
- [ ] All failure codes match across both prompts and DELIVERABLE_CONTRACT.md
- [ ] No ASPIRATIONAL behavior presented as available functionality

## Gate 3 — Schema verification

- [ ] `docs/WORKBOOK_SCHEMA.md` matches column names in `templates/master_workbook_template_v1.0.xlsx`
- [ ] `docs/WORKBOOK_SCHEMA.md` matches column names in a representative produced workbook
- [ ] `scan_states.json` schema in MAMEY_CHATGPT_EXECUTION_PROMPT.md §6 matches schema produced by `mamey_run.py`
- [ ] Checkpoint CSV schema in prompt §7 matches fields produced by `mamey_run.py`

## Gate 4 — CLI verification

- [ ] `mamey_run.py --help` output matches documented run modes in HOW_TO_USE.md
- [ ] `--mode` values `smoke`, `standard`, `gold` all documented and functional (default `standard`). Note: `project_merge` is the master-workbook merge **operation** (`update_master_workbook`), not a `--mode` value
- [ ] Accession support: either `--accession` is implemented and tested, or documented as unsupported with explicit antiSMASH ZIP requirement
- [ ] Failure codes emitted by `mamey_run.py` match codes listed in prompts

## Gate 5 — Test matrix

> **Note:** the six behavioral tests below are **target/Release-2 acceptance tests** — they are NOT yet implemented in `tests/`. The current suite (**818 passed / 80 skipped** as of v9.7.57) is predominantly a **contract / doc-presence + unit** suite (ID uniqueness, naming, absolute coordinates, RG-GMCI-rescue-without-claim-confidence-upgrade, etc.) rather than an end-to-end behavioral merge/extraction suite; the 80 skips are largely the reference-panel concordance tests that need committed antiSMASH ZIP fixtures (see CI_REFERENCE_FIXTURES_GUIDE.md). `schema_mismatch_stop` in particular tests inline pre-merge validation that is currently a **separate** `workbook_schema_check` step (not wired into the merge — Release-2). Treat this matrix as the behavioral-coverage goal, not a current gate.

- [ ] `smoke_parse_small_zip`: small antiSMASH ZIP → assembly stats, raw BGC count, manifest ✅ / ❌
- [ ] `gold_complete_one_zip`: representative antiSMASH ZIP → all scan statuses, sealed package, checksums ✅ / ❌
- [ ] `workbook_merge_append`: existing workbook + one complete package → new rows appended, no old rows deleted ✅ / ❌
- [ ] `failed_accession_boundary`: accession request without accession-enabled runner → `UNSUPPORTED_ACCESSION_MODE`, no fabricated rows ✅ / ❌
- [ ] `continue_checkpoint`: prior checkpoint with deferred item → next item processed, completed items not rerun ✅ / ❌
- [ ] `schema_mismatch_stop`: workbook missing required columns → merge stops with `WORKBOOK_SCHEMA_CONFLICT` ✅ / ❌

## Gate 6 — Examples and reference materials

- [ ] `examples/test_data/` contains at least one small antiSMASH ZIP for smoke testing
- [ ] `examples/layperson_guide_exemplar.md` populated with a real Layperson Guide example
- [ ] `CITATION.cff` updated with v9.4 version string and current date
- [ ] `CHANGELOG.md` has a v9.4 entry describing the restoration changes

## Gate 7 — Public readiness

- [ ] `README.md` introduction matches the two-layer architecture (Mamey deterministic, Sapote interpretive)
- [ ] `README.md` does not claim capabilities not yet implemented
- [ ] `RELEASE_MANIFEST.md` lists all known limitations honestly
- [ ] Zenodo DOI placeholder updated (if depositing to Zenodo)
- [ ] All files in the release ZIP are included in `RELEASE_MANIFEST.md`
- [ ] SHA-256 checksums computed for all release files

---

## Sign-off

| Item | Checked by | Date | Notes |
|---|---|---|---|
| All gates above | | | |
| Release profile changed to PUBLIC_RELEASE | | | |

---

*Sapote-Mamey Bundle v9.7.428 | Active controller: docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md*

## Gate — Master Schema Conformance (FROZEN v1.1, added 2026-06-09)
- [ ] Any artifact identifying as `workbook_type = MASTER_STRAIN_WORKBOOK` conforms to the frozen canonical schema (codes A1–A4, B1–B12, C1–C3, D1–D4, F1–F2, G1–G2, H1–H3; column names per `MASTER_SCHEMA_FROZEN_v1_1.md`). Per-strain (§57) and custom workbooks are EXEMPT.
- [ ] Any sheet carrying a parsed product/accession (canonical trigger fields) carries the full KCB/MIBiG provenance column set; validator passes (no `WORKBOOK_SCHEMA_CONFLICT` sub-reasons).
- [ ] No non-canonical product/accession column names (else `KCB_PRODUCT_FIELD_NONCANONICAL`).
- [ ] Schema changes since last release are append-only (codes + columns); any structural change is a v2 that still reads v1.
- [ ] Schema changes since last release are append-only (codes + columns); any structural change is a v2 that still reads v1.

## Deliverable-contract enforcement (added v9.7.6)
- [ ] Every full run emitted a filled `DELIVERABLE_MANIFEST_<strain>.md` (from `docs/DELIVERABLE_MANIFEST_TEMPLATE.md`).
- [ ] `python tools/check_deliverable_suite.py --manifest DELIVERABLE_MANIFEST_<strain>.md --mode <mode>` exits 0.
- [ ] `python tools/sapote_judgment_receipt.py --package <pkg> --manifest <manifest> --modeb <cards...> --mode gold` exits 0 (gold_completeness = COMPLETE, not asserted).
- [ ] Tier parity: cassette stable IDs, `bundle_support/registry_inventory_v1.9.4.json`, and the manifests are present in ALL four tiers (the v9.7.5 gap was CODE-analysis-free shipping placeholder IDs + missing registry).

## Release gates (added v9.7.6 — post external-validation hardening)
Run `tools/check_tier_parity.py --tiers-dir <dir>` and record this table; every tier must be green before tag/push:

| Tier | Registry | BUG-class checks | Build caches | pytest (in-tier) | Leak audit | Checksums |
|---|---|---|---|---|---|---|
| MERGED-PRIVATE-scaffold | present | — | 0 | 47/3/0 | n/a (private) | self-verify |
| SID-public | present | — | 0 | 47/3/0 | 0 AS | self-verify |
| CODE | present | — | 0 | 47/3/0 | 0 AS | self-verify |
| CODE-analysis-free | present | — | 0 | 46/4/0 | 0 AS | self-verify |

- [ ] **pytest-in-cut gate**: `make_public_tier.sh` runs the suite in each staged tier and refuses to zip on any failure.
- [ ] **Cache hygiene**: cut scrubs `__pycache__`/`*.pyc`/`.pytest_cache` before checksum+zip (0 cache files shipped).
- [ ] **Registry in all tiers**: `registry_inventory_v1.9.4.{json,csv}` ships in all four (0 strain IDs; parity tests run not skip).
- [ ] **Version provenance**: no hardcoded `v1.9.x` literals in `mamey/*.py` except `__init__.py`; workbook/validate derive from `__version__`.
- [ ] **Coverage**: v1.9.2 coordinate + KCB regression guards run in public tiers via `tests/fixtures/synthetic_single_contig_antismash.zip`.
- [ ] **Checksum self-verify**: each tier's `SOURCE_CHECKSUMS_SHA256.txt` verifies 100% on a pristine extract.
- [ ] **Multi-tier disclosure**: per-tier patch/verification status recorded at delivery (never assume a fix propagated).
