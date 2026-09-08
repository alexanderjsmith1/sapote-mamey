# Sapote–Mamey v9.7.22 — build -n (2026-06-14)

New consumer: the fragment-concordance scorer. **No existing engine logic changed.**

## fragment_concordance_scorer.py (the panel's consumer)
- Scores a strain's observed BGC fragments against the 73-signature reference panel: per fragment, the
  best-matching reference + a concordance tier (STRONG/MODERATE/WEAK/NONE) over four axes — region-token
  Jaccard (0.30), marker-set concordance (0.30), domain-count shape KS/NRPS-C/NRPS-A (0.25), size ratio (0.15).
- **Claim-safe by construction.** Concordance is architectural SIMILARITY, not identity or production;
  T43 markers [E-signal]; marker credit uses each reference's **adjudicated** `expected_marker_set`, so a
  reference whose scanned marker is PENDING (pekiskomycin, lipopeptide 8D1) earns no marker credit — the
  scorer never rewards matching an unconfirmed marker. Weights/thresholds are a documented heuristic rubric.
- Inputs: `--observed obs.json` (fragment signatures) or `--ledger ledger.csv` (reference_panel_ledger
  output). Output: per-fragment best-match + top-N as CSV with a claim-safe header.

## Test matrix (9) — the three adjudications are the fixtures
`tests/test_fragment_concordance.py`: component units; C-1027 uses the widened {T43-ENE, T43-HAL}
(full credit for both, half for ENE-only); pekiskomycin/8D1 PENDING -> no marker credit; piericidin
T43-negative; end-to-end best_match over the real panel (piericidin-like -> piericidin STRONG; C-1027-like
-> C-1027 surfaced).

## Still staged
- Task-based Start-Here/router + per-report ID-resolver table.
- Run_Manifest sheet `antismash_profile` column (schema v1.1).
- Refresh the three stale delivered docs.
- Corrected-BGC-count reframe for NAR-GB.

## Per-tier verification (in-zip)
| Tier | pytest | AS-### |
|---|---|---|
| CODE | 510 passed / 80 skip | 0 |
| CODE-analysis-free | 508 passed / 82 skip | 0 |
| SID-public | 510 passed / 80 skip | 0 |
| MERGED-PRIVATE-scaffold | 509 passed / 81 skip | retained (expected) |

Supersedes -m. Checksums regenerated last; verified in-zip.
