# Sapote–Mamey v9.7.22 — build -m (2026-06-14)

The v9.2 review's top structural hazard, fixed: geometry now **gates** RG-GMCI + reconstruction
acceptance (demote), instead of only feeding the score additively. No other engine logic changed.

## RG-GMCI acceptance discriminators (`mamey/rggmci.py`)
- **Overlap-fraction.** `_adjacency` classifies `OVERLAPPING_REFERENCE_SEGMENTS` only when the overlap
  covers >= 20% of the smaller segment (`OVERLAP_FRACTION_MIN`). A 1-bp nominal overlap is now
  `ADJACENT`, not overlapping — it no longer earns the full overlap score. `overlap_fraction` is
  surfaced per pair.
- **Geometry acceptance gate** (`_geometry_gate`). A pair reaching HIGH/MODERATE purely on convergence
  count (many shared references) with zero overlapping/adjacent reference geometry is **demoted** to
  `LOW_SHARED_REFERENCE_SIGNAL`, unless an independent cross-scaffold physical-split signal supports it
  (then capped at MODERATE). Convergence count can no longer manufacture a HIGH rescue without real
  geometry. The reason is recorded per pair in `acceptance_gate`.

## Reconstruction acceptance (`tools/build_reconstruction.py`)
- New `reconstruction_verdict`: overlap-fraction on shared reference-gene coverage gates the verdict.
  Complementary tiling (<= 15% overlap) -> `SUPPORTED`; partial -> `WEAK`; high overlap (> 50%, both
  fragments over the same reference region) -> `NOT_SUPPORTED` (likely duplication/mis-pairing, not a
  clean split). The tiling section emits the verdict + a caution instead of always reporting "complementary."

## Test matrix (these discriminators were previously untested)
- `tests/test_rggmci_acceptance.py` (10): overlap-fraction thresholds, distant classification, and the
  full demotion truth-table incl. the split-signal exception.
- `tests/test_reconstruction_overlap.py` (4): complementary / partial / high-overlap / unevaluable.

## Still staged
- Fragment-concordance scorer (net-new consumer of the panel).
- Task-based Start-Here/router + per-report ID-resolver table.
- Run_Manifest sheet `antismash_profile` column (schema v1.1).

## Per-tier verification (in-zip)
| Tier | pytest | AS-### |
|---|---|---|
| CODE | 501 passed / 80 skip | 0 |
| CODE-analysis-free | 499 passed / 82 skip | 0 |
| SID-public | 501 passed / 80 skip | 0 |
| MERGED-PRIVATE-scaffold | 500 passed / 81 skip | retained (expected) |

Supersedes -l. Checksums regenerated last; verified in-zip.
