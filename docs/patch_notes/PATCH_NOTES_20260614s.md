# PATCH NOTES — build -s (2026-06-14)

**Bundle:** Sapote–Mamey v9.7.22 · **Engine:** Mamey 1.9.30 · **Build:** 20260614s
**Theme:** E2 runtime — large-JSON streaming done right (memory-safe, byte-identical, faster) + determinism fix.

## E2 — `--json-evidence bounded` truly streams large JSONs (antismash_evidence.py)
- **Decimal-serialize crash fixed.** ijson yields JSON numbers as `Decimal` by default, which are not
  `json.dumps`-serializable; a streamed run crashed in `_write_package` (cli.py:661). The ijson record
  reader now passes `use_float=True`, so streamed records carry `float` — byte-identical to the
  `json.loads` full-load path.
- **Hidden env gate removed -> size-adaptive default.** Record streaming was gated behind an
  undocumented `MAMEY_STREAM_JSON=1`, so the banner said "streaming on" while the default full-loaded the
  whole document (~1 GB peak on a 132 MB JSON; each record-level extractor `json.loads`-ed it
  independently). The decision is now size-adaptive: JSONs >= 20 MB stream (flat memory), smaller ones
  full-load (`json.loads` is faster on small inputs, esp. under the cffi/python ijson backends).
  `MAMEY_STREAM_JSON` survives only as an explicit override (1/always, 0/never).

## Single-pass record extraction (antismash_evidence.py)
- The four record-level extractors (nrps_pks consensus, active-site pairings, product-class predictions,
  RiPP cores) each re-opened the ZIP and re-parsed the full JSON. They now share ONE pass via
  `_run_record_extractors` (per-handler error isolation; the public `extract_*` functions remain as thin
  wrappers). Four full-JSON parses -> one. WWKJ00000000 (114 BGCs, 132 MB JSON) streaming wall time:
  ~206 s -> ~91 s (~2.3x). `extract_tigrfam_hits` remains a separate cli pass (folding it in is a follow-up).

## Determinism (source_scans.py)
- Tier-1 domain hit lists were emitted from an unsorted `set`, so `manifest.json` and the
  `Project_Memory_Snapshot` were non-reproducible run-to-run (two identical runs disagreed on domain
  ordering). `sorted()` added — order is cosmetic (the score is presence-only), so this only adds
  determinism. Package output is now byte-stable across unseeded runs.

## Verification (per tier, not assumed)
- Full suite green in every tier: CODE 526 | CODE-analysis-free 524 | SID-public 526 | MERGED 525 (unchanged from -r).
- Byte-parity with the -r full-load path on WWKJ00000000: every substantive evidence file identical; diffs
  confined to volatile fields (xlsx timestamp, package_dir path, transitive checksums). Proven under
  natural conditions (no PYTHONHASHSEED pin) after the determinism fix.
- Streaming, force-stream, and force-full-load all produce identical evidence output.
- Public tiers AS-### clean (mibig corpus exempt); MERGED retains AS refs (PRIVATE).

## Scope / unchanged
- **DO-FIRST kit: unaffected by this batch** (carries neither changed file; no registry/policy change). Remains at build -r.
- No policy/registry change; standing rules, enediyne guard/gate, NAPAA/hglE policy unchanged from -r.

## Carried forward (not in this build)
- Fold `extract_tigrfam_hits` into the single pass (5th extractor; separate cli call site).
- B2 SSOT dedup; C1 saccharide-hybrid boundary FP; E1 smoke fixture / E6 F1 guard; E3 heartbeats.
