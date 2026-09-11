# Sapote–Mamey v9.7.22 — build -p (2026-06-14)

MIBiG 4.0 integration: a broad, current reference base with the session's curation as a thin overlay.

## MIBiG bacterial base (bundled)
- `mamey/data/mibig/mibig_reference_index.bacterial.json` — **2,091 confirmed-bacterial BGCs** (21
  phyla, 0 retired), auto-extracted from MIBiG 4.0 JSON + antiSMASH GBK. KS/A/C from `aSDomain`, size
  from `LOCUS`, `provenance="MIBiG-4.0-auto"`, `markers:[]` (no curated T43). Validation: 65/70 curated
  KS match the auto counts; 5 flagged (candicidin, granaticin/type-II, lobophorin, ibomycin, nostophycin).
- `tools/build_mibig_index.py` — the extractor (JSON+GBK→index; emits bacterial/fungal/full cuts + taxid sidecar).

## Adjudication overlay
- `mamey/data/mibig/adjudications.json` — accession-keyed curated judgment (75 entries: 24 marker sets,
  53 verdicts, capacity flags) lifted from `reference_bgc_library.json`. **No BGC selection** — judgment only.
- `mamey/adjudication.py` — `adjudicate(entry, overlay)`: matched accession → `CURATED-ADJUDICATED`
  (marker credit from `expected_marker_set`, KS disagreement flagged); else `MIBIG-AUTO` (no marker credit).

## Scorer wiring
- `fragment_concordance_scorer.py --mibig-index` scores observed fragments against the adjudicated
  2,091-entry space (bare flag = bundled bacterial cut). Output adds `reference_tier` + `best_accession`.
  Smoke: a KS=8 / 49.4 kb fragment → piericidin A1 (BGC0000124), CURATED-ADJUDICATED, 0.917 STRONG.
- Default behavior unchanged when `--mibig-index` is absent (curated panel only).

## Leak guard
- `mamey/data/mibig/` exempt from the AS-### scan (public corpus; contains public bacteriocin BGC0000489).
  The guard caught two of my own AS-### slips during this build (RELEASE_NOTES example, exemption comment) — working as designed.

## Backlog landed
- `RELEASE_NOTES_v9.7.22.md` consolidating the -i … -p arc.

## Tests (7 new)
`test_adjudication.py` (4) + `test_scorer_mibig.py` (3).

## Per-tier verification (in-zip)
| Tier | pytest | non-MIBiG AS-### |
|---|---|---|
| CODE | 521 / 80 skip | 0 |
| CODE-analysis-free | 519 / 82 skip | 0 |
| SID-public | 521 / 80 skip | 0 |
| MERGED-PRIVATE-scaffold | 520 / 81 skip | retained (expected) |

Supersedes -o. MIBiG fungal (525) + full (3,013) cuts available out-of-tree, not bundled.
