# Sapote–Mamey v9.7.22 — build -k (2026-06-14)

Follow-on to -j (which fixed the public-tier strain-ID leak + added piericidin). -k lands the
audit-derived hardening that closes the leak *class* and pays down named debt. **No engine scoring
logic changed.**

## Leak-class closure (audit Awkward #1/#2/#10/#12)
- `tools/redact_public_tier.py` rewritten: redacts SID **and** AS-### strain IDs, walks the whole
  tree by default (not two hardcoded files), and is tokenize-aware for .py — rewrites only comment
  and string spans, never code identifiers or numeric literals, so a tree-wide scrub is safe by
  construction (closes the `--all-py` foot-gun). AS pattern is hyphen-discriminated + anchor-free:
  catches underscore-wrapped IDs, preserves dashless public KCB strings (e.g. `AL-KSAMP_AS10_SC01`),
  excludes CAS-/MCAS- cassette stable-IDs. CAS multiset guard retained.
- `make_public_tier.sh` now (a) emits a per-tier `TIER_MANIFEST.txt` (sorted membership list) so
  "right files in the right tier" is a one-line diff, and (b) runs the fail-closed leak invariant
  against the staged public tier before zipping (exit 5 on any AS-### token).

## Single-strain path (audit 2.1)
- `build_modeb_deepdive.py` no longer falls back to the built-in SID target list on incomplete
  input; it **errors** with guidance (pass `--targets` or run the verdict step) instead of emitting
  mismatched all-`?` placeholder cards. Targets absent from banked records are dropped with a warning.
- New `docs/SINGLE_STRAIN_QUICKSTART.md`: cohort-of-one workflow with real commands.

## Reference panel
- Three scan-vs-curator divergences adjudicated. **C-1027: RESOLVED** — `T43-HAL` confirmed (BGC
  encodes the sgcC3 halogenase that chlorinates the chromophore); `expected_marker_set` widened to
  {T43-ENE, T43-HAL}. **pekiskomycin / lipopeptide 8D1: PENDING** — `T43-HAL` held as candidate
  false-positive awaiting literature/wet confirmation; expected unchanged; not asserted negative.
- New `docs/CI_REFERENCE_FIXTURES_GUIDE.md`: how to commit 2–3 PUBLIC type-strain zips so a live
  panel-concordance slice runs in CI instead of 74 skips.

## Still staged (next focused unit — NOT in -k)
- `antismash_profile`/strictness field in the run manifest + cross-tier comparability guard.
- Wiring overlap/coordinate discriminators into RG-GMCI + reconstruction *acceptance* (scoring surgery).
- The fragment-concordance scorer (net-new consumer of the panel).

## Per-tier verification (in-zip)
| Tier | pytest | AS-### | TIER_MANIFEST |
|---|---|---|---|
| CODE | 479 passed / 80 skip | 0 | yes |
| CODE-analysis-free | 477 passed / 82 skip | 0 | yes |
| SID-public | 479 passed / 80 skip | 0 | yes |
| MERGED-PRIVATE-scaffold | 478 passed / 81 skip | retained (expected) | yes |

Checksums regenerated last over the final tree; verified in-zip. Supersedes -j (functional superset).
