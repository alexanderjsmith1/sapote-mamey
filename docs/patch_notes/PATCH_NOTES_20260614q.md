# Sapote–Mamey v9.7.22 — build -q (2026-06-14)

## BLOCKING FIX — `mamey run` was broken in every tier (caught by external -p audit)
`_write_package` referenced `antismash_profile` in its body (intake.json + manifest.json writes) but
never accepted it as a parameter → `NameError` at package-write on **every real single-strain run**,
all four tiers. The unit suite missed it because nothing exercised the run→package path.
- Fix: threaded `antismash_profile` into `_write_package` (signature + call site), per-tier (cli.py
  carries tier-specific redaction).
- Regression test `tests/test_write_package_profile.py`: asserts any run-scoped name used in the
  writer body is a parameter (introspection — no fixture needed).
- **Runtime-verified**: live `mamey run` on a real strain now completes `MAMEY_COMPLETE` and the
  manifest/intake carry `antismash_profile`. (Pre-fix this crashed.)

## #2 — 5 KS-diff reconciliation (overlay)
candicidin (54→21) and granaticin (0→2, type-II PKS) resolved to MIBiG with recorded basis and an
audit trail (`previous_curated_pks_ks`); lobophorin / ibomycin / nostophycin left **UNRESOLVED** and
flagged for literature check — not silently overridden.

## #3 — schema amendment: A3_Run_Manifest + `antismash_profile`
Column added at position 5 (after `mode`), populated from `run.context`; freeze-note in
`MASTER_SCHEMA_FROZEN_v1_1.md`; validator auto-requires it; `tests/test_run_manifest_profile.py`.

## #4 — fungal layer + scorer filters
`mamey/data/mibig/mibig_reference_index.fungal.json` (525 Eukaryota) bundled. Scorer gains
`--include-fungal` and `--mibig-status` (e.g. keep only `active`).

## #1 — cohort concordance summary
`tools/cohort_concordance_summary.py`: scores a multi-strain ledger against the adjudicated MIBiG
space, grouping nearest neighbours per strain with the CURATED-ADJUDICATED vs MIBIG-AUTO split.
Validated on real strains — it independently recovered known leads on a private Bombus strain (NODE_162 → polyoxin, a
peptidyl-nucleoside; NODE_182 → staurosporine, indolocarbazole).

## Marker bug fix (latent, found via #1)
`obs_signature` read the wrong ledger column and treated `none`/free-text as markers. Now reads
`cmp_t43_markers` and normalizes T43 tokens (`T43-HAL_halogenase` → `T43-HAL`); sentinels dropped.
Markers now discriminate correctly (scores drop where a fragment lacks a required marker — intended).

## Tests
+`test_write_package_profile`, `test_run_manifest_profile`, `test_cohort_summary`, scorer
status/normalization cases.

## Per-tier verification (in-zip)
| Tier | pytest | non-MIBiG AS-### |
|---|---|---|
| CODE | 526 / 80 skip | 0 |
| CODE-analysis-free | 524 / 82 skip | 0 |
| SID-public | 526 / 80 skip | 0 |
| MERGED-PRIVATE-scaffold | 525 / 81 skip | retained (expected) |

Out-of-tree (delivered separately, not bundled): the cohort demo CSVs (PRIVATE — AS strains) and the
refreshed `Technical_Report.md`. Carried-over audit items (boundary-audit token-matcher; ingest
first-merge friction; NAPAA/hglE standing-rule fork) remain open — see next steps. Supersedes -p.
