# Sapote–Mamey v9.7.22 — build -o (2026-06-14)

UX layer (audit + ChatGPT priorities). **No engine scoring logic changed.**

## Task router
- `docs/START_HERE.md`: task-based entry — run / merge / audit / publish / figures / concordance /
  cross-reference an ID / literature — each pointing straight to the tier + tool, with the standing
  hard guards inline. Complements the capability menu in `docs/BUNDLE_CAPABILITIES.md`.

## ID resolver (`BGC_ID | bgc_uid | contig/NODE | region | antiSMASH file | workbook row`)
- `mamey/id_resolver.py` (shared): `resolver_rows` + `resolver_md`. bgc_uid is composed in the
  workbook, not stored in the bank — pass `--workbook` for the authoritative value + row, else a
  derived uid (marked "(derived)") is used and the row column is an honest blank.
- `tools/build_id_resolver.py`: CLI emitting the resolver CSV for a banked cohort.
- Wired into `build_modeb_deepdive.py`: every Mode B report now carries the resolver table in its head
  (verified end-to-end). The same `resolver_md` can be dropped into other report builders.

## Tests (4)
`tests/test_id_resolver.py`: column contract, derived-uid + honest-blank row, authoritative workbook
map override, six-column markdown render.

## Still staged
- Run_Manifest sheet `antismash_profile` column (schema v1.1).
- Wire `build_id_resolver` / `fragment_concordance_scorer` into the remaining report builders + a
  per-strain concordance sheet.
- Refresh the three stale delivered docs.
- Corrected-BGC-count reframe for NAR-GB.

## Per-tier verification (in-zip)
| Tier | pytest | AS-### |
|---|---|---|
| CODE | 514 passed / 80 skip | 0 |
| CODE-analysis-free | 512 passed / 82 skip | 0 |
| SID-public | 514 passed / 80 skip | 0 |
| MERGED-PRIVATE-scaffold | 513 passed / 81 skip | retained (expected) |

Supersedes -n. Checksums regenerated last; verified in-zip.
