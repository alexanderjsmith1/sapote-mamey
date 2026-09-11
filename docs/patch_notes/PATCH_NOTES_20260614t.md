# PATCH NOTES — build -t (2026-06-14)

**Bundle:** Sapote–Mamey v9.7.22 · **Engine:** Mamey 1.9.30 · **Build:** 20260614t
**Theme:** Single-pass record extraction (runtime), F1 bare-assembly fix, diagnostic-trigger SSOT, and the
package-write/pass-count test coverage that makes those regressions impossible to ship silently.

## Runtime — one record pass per run (was three)
- **tigrfam folded into the shared record pass.** `extract_tigrfam_hits` was a separate full-JSON parse
  in the cli; it is now a 5th handler in the single-pass `_run_record_extractors` driver, gated by a
  `want_tigrfam` flag so it runs only on the status path that consumes it (no wasted pass elsewhere, no
  off-mode regression). The cli reads tigrfam from the evidence dict and drops the redundant key so the
  persisted `AntiSMASH_Evidence_Parse.json` is byte-identical to before.
- **Double `parse_antismash_evidence` deduped.** The records were parsed twice per run — once for the
  status dict (cli) and once inside `parse_bgcs_from_zip` to apply evidence to BGCs. `parse_bgcs_from_zip`
  now accepts an optional pre-parsed `evidence=`; the cli passes the status evidence in, so the records are
  parsed once. Safe because `apply_evidence_to_bgcs` reads only `by_region` (independent of `want_tigrfam`).
  Standalone callers (tests) pass nothing and parse internally as before.
- Net: a bounded run makes ONE record pass (5 handlers) instead of three; off makes one (tigrfam only). A
  single streaming record pass over a 132 MB genome is ~24 s, so the run drops one such pass. Byte-parity
  with -s on the WWKJ control (only volatile files differ).

## Correctness — F1 bare-assembly guard (E6)
- The F1 guard failed any strain when the antiSMASH VERSION string was undetected, even with regions
  parsed (`raw == 0 or not antismash_ver`) — silently discarding real, region-bearing strains. A bare
  assembly is now defined by `raw == 0` alone; a missing version with regions present is recorded as an
  issue and the run proceeds.

## Correctness — diagnostic CCTT trigger counting (Patch A)
- `compat_v941` computed `diagnostic_count` from a hand-typed token subset that silently dropped
  T43-IDC / T43-NUC / T43-BLA / T43-AMC / T43-NN (under-tiering class-definitive BGCs to TIER_2) and only
  matched T43-PTM / T43-XHAL by substring accident. The diagnostic set is now derived from the active
  scanning backend (`source_scans.CCTT_PATTERNS`, all 15 T43 triggers) and matched on the full trigger
  name. An indolocarbazole-core BGC whose only trigger is T43-IDC now exports TIER_1_DIAGNOSTIC.

## Test coverage (the gap that let the above ship/regress)
- `test_package_write_smoke.py` — first end-to-end run_one_strain -> _write_package coverage; the streaming
  case is the regression guard for the v9.7.22 "Decimal is not JSON serializable" crash (verified: fails
  when use_float is reverted).
- `test_record_pass_count.py` — pins the one-record-pass invariant (bounded=1/5 handlers, off=1/1); catches
  a dedup regression or a re-introduced wasted pass that a package-write smoke test cannot see.
- `test_compat_diagnostic_triggers.py` — T43-IDC/NUC -> TIER_1_DIAGNOSTIC, full-set coverage, no-substring-
  -accident, and an SSOT drift guard tying the diagnostic set to source_scans.CCTT_PATTERNS.

## Verification (per tier, not assumed)
- Full suite green in every tier: CODE 536 | CODE-analysis-free 534 | SID-public 536 | MERGED 535 (+10 each from -s).
- Public tiers AS-### clean (mibig corpus exempt); MERGED retains AS refs (PRIVATE).
- cli.py per-tier sanitization preserved (edits applied in place, not blind-copied).

## Scope / unchanged
- **DO-FIRST kit: unaffected** (carries none of the changed files; no registry/policy change). Remains at build -r.
- No policy/registry change; standing rules, enediyne guard/gate, NAPAA/hglE policy unchanged.
- Version unchanged at 9.7.22 (build letter only). A publication release version bump can be done separately.
