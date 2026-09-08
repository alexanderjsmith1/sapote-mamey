# Sapote–Mamey v9.7.22 — build -l (2026-06-14)

Audit-debt batch on top of -k. **No engine scoring logic changed.**

## antiSMASH profile / comparability guard (audit 2.4 — the cross-habitat landmine)
- New `--antismash-profile {strict|relaxed|loose|unknown}` on `mamey_run.py run`; recorded in
  `manifest.json` and `commit_receipt.json` per strain (default `unknown` — not auto-detected; the
  standard region JSON does not carry strictness).
- New `tools/check_antismash_profile.py`: scans a packages root and exits non-zero if strains were
  run under different antiSMASH profiles, or any is `unknown` — fail-closed guard against pooling
  across profiles for comparative/ecological claims.
- `docs/ANTISMASH_PROFILE.md` documents the convention. The Run_Manifest **sheet** column is a
  deliberate schema-v1.1 change, staged so the frozen 25-sheet schema is not mutated ad hoc.

## Cheap-debt batch (read-through Worst-list tail)
- esmeraldin reference entry flagged `architecture_capacity: KNOWN_MISFIRE` (machine-visible, #14).
- `BUILD_STAMP.txt` is now the single canonical build identity; `test_build_stamp.py` asserts version
  agreement across BUILD_STAMP / pyproject / TAG + a well-formed `<date><letter>` stamp (#6).
- Glossary canonicalized: `docs/GLOSSARY.md` declared canonical, both addenda declare scope;
  `test_glossary_canonical.py` guards it (#15).
- `tests/README.md` documents which suites skip and why, so the ~80 skips read as designed (#13).

## Still staged (focused units — NOT in -l)
- RG-GMCI + reconstruction **acceptance** discriminators (overlap-fraction + coordinate-distance) with
  a fresh test matrix — scoring surgery, its own pass (v9.2 review's top hazard).
- Fragment-concordance scorer — net-new consumer of the panel.
- Task-based Start-Here/router + per-report ID-resolver table.
- Run_Manifest sheet `antismash_profile` column (schema v1.1).

## Per-tier verification (in-zip)
| Tier | pytest | AS-### | TIER_MANIFEST |
|---|---|---|---|
| CODE | 487 passed / 80 skip | 0 | yes |
| CODE-analysis-free | 485 passed / 82 skip | 0 | yes |
| SID-public | 487 passed / 80 skip | 0 | yes |
| MERGED-PRIVATE-scaffold | 486 passed / 81 skip | retained (expected) | yes |

Checksums regenerated last; verified in-zip. Supersedes -k (functional superset).
