# Sapote–Mamey v9.7.22 — build -j (2026-06-14)

## HARD-GUARD FIX (release blocker): unpublished strain IDs in public tiers

Builds -f … -i of the public tiers (CODE, CODE-analysis-free, SID-public) carried unpublished
AS-### strain identifiers in two places: a docs/ `bgc_uid` example block (four examples naming
three real unpublished bryophyte strains) and one mamey/master_workbook.py code comment.

**Root cause.** The public-cut scrub and its self-audit (make_public_tier.sh) both matched strain
IDs with a `\b` word-boundary anchor, which fails on underscore-wrapped IDs (`..._AS-###_BGC..`).
The scrub skipped them; the self-audit then reported "0 leaks." Every manual leak check this
session inherited the same anchored pattern, so the leak was repeatedly mis-certified as clean.

**Fix (three layers).**
1. Scrub: anchor-free, hyphen-discriminated pattern — preceding char must not be a letter
   (excludes CAS-/MCAS- cassette stable-IDs); hyphen required, so legitimate dashless public KCB
   strings (e.g. `AL-KSAMP_AS10_SC01`) are preserved, not over-scrubbed. All real strain
   references in public tiers are now `AS-XXX`.
2. Audit: make_public_tier.sh self-audit uses the same anchor-free pattern.
3. Invariant: `tests/test_no_unpublished_ids_in_public_tier.py` fails closed on any AS-### token
   in a public tier (skips on the MERGED-PRIVATE scaffold, which legitimately retains them).
   The guard is now a test invariant, not a script step you must remember to run with the right scope.

## Reference panel: +piericidin (75 entries)
- piericidin (BGC0000124, *Streptomyces piomogenus*): modular T1PKS, KS8, T43-negative, 49.4 kb
  full-contig — architecture reference + T43-negative control.
- Library now **75 entries**, architecture_signature **73/75** (A54145, deoxyhangtaimycin pending
  source antiSMASH outputs). All four tier libraries byte-identical.

## Per-tier verification
| Tier | pytest | AS-### (anchor-free scan) | tier |
|---|---|---|---|
| CODE | 479 passed / 80 skip | 0 | public |
| CODE-analysis-free | 477 passed / 82 skip | 0 | public |
| SID-public | 479 passed / 80 skip | 0 | public |
| MERGED-PRIVATE-scaffold | 478 passed / 81 skip | retained (expected) | private |

Checksums regenerated last over the final tree; verified in-zip. Supersedes -i (contaminated).
