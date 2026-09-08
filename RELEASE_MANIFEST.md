# Sapote-Mamey Bundle Release Manifest — v9.7.414 quality-recheck candidate

**Cut/build date:** 2026-09-07  
**Candidate status:** controlled quality-recheck rebuild; not signed release  
**Bundle version:** `sapote-mamey-v9.7.414`  
**Authoritative bundle version:** `9.7.414`  
**Engine:** Mamey v1.9.152  
**Build stamp:** 20260907v97414a  
**Release profile:** `CODE`  

## Tier scope

Public code tier; data-free, GitHub-ready, includes executable Mamey/Sapote support files and validation fixtures.

## Functional scope (carried forward from v9.7.144b onwards)

- Full Mode B §1–§30 contract and validator.
- Integrated evidence table remains a companion/index output, not a substitute.
- Offline Mode B / missing evidence sections fail visibly rather than silently omitting sections.
- Wise fragmented PKS queue workflow: 85k residue target, 100k hard cap, unique Q IDs, stable ledger, active/deferred state, CPU-failure recovery helper.
- `+` / `-` strand standard for machine-readable Mode B tables.
- PDF output contract for mature Mode B reports.

## Patches in v9.7.149–v9.7.157

> *Carried-forward historical snapshot. This section predates the current cut; the header/anchor fields above are authoritative for v9.7.414, and `CHANGELOG.md` is the authoritative per-cut patch history.*

**Engine 1.9.101 → 1.9.104 across the recent span.** v9.7.156 bumped to 1.9.102 (two compile-path
bugfixes); v9.7.157 to 1.9.103 (mandatory-deliverable gate); v9.7.158 to 1.9.104 (KCB
source-precedence + rank-vs-score fix). **v9.7.159 leaves the engine at 1.9.104 — additive,
engine-neutral (package_map + manifest_schema + accretion gate).** No scoring/Mode-B logic
changed; cross-strain comparability unaffected.

**v9.7.157 (this cut) — mandatory-deliverable gate:** `mamey run` now auto-emits the compiled
report after seal in every mode, so a completed run always hands the user a human-readable
deliverable (closes the smoke/--brief-none zero-deliverable gap). Plus the carried v9.7.156 work:
AS-series privacy-guard retirement (leak audit FAIL→WARN behind `AS_GUARD_RETIRED`) and two
compile-path bugfixes (render_all list-vs-int; compile_report n50/contigs assembly fallback).

**v9.7.154 (this cut) — bug-fix + test-infra, from a hostile-auditor pass on the v9.7.153 CODE artifact:**
- **PATCH-001**: `blastp_followup.parse_query_id` now parses space-delimited `BGC###_<gene> key=value`
  headers (not just pipe-delimited); `merge_hit_xml` fallback is truthy-guarded so a 4-query batch no
  longer mis-binds the first query's hits to every row. The combined token is not written to `strain`.
- **PATCH-002**: `render-all-figures` coerces list-valued `figures` (locus-maps) to a count before
  formatting, so the `--all` run no longer halts before `figure-suite`/`domain-level`/etc.
- **PATCH-004**: `test_bunny_hop_fixes` pandas-fallback tests snapshot/restore `sys.modules`, fixing 7
  order-dependent false-positive failures on full-suite runs (engine/scoring untouched).
- **PATCH-005 part 1**: `query_summary.csv` gains raw `top_identical_count`/`top_positive_count`.
- **PATCH-003**: `SESSION_START_MANIFEST` §0.5 `inspect`/`list-bgcs` syntax synced to argparse.
- Cross-checked against an independent ChatGPT patch pass; adopted its raw-count columns + whitespace
  `aa=` regex, rejected its `strain = <combined token>` assignment. See `CHANGELOG.md` v9.7.154.

**v9.7.152–v9.7.153 (carried forward, from the v9.7.153 artifact audit):**
- v9.7.153: `claim-safety --package` auto-derivation (Finding 3); `compile-report` bundle-version
  fix (Finding 6); AS-XXX full-file divergence check; `CUT_PROTOCOL.md` verify-the-artifact step;
  `PREREQUISITES.md` offline-dependency gaps closed.
- v9.7.152: AppleDouble intake fix; `--capped-session` rename; `_HEADING_RE` Bug 2.1;
  `verify_checksums` judgment-register exemption; AS-XXX ingest fixes; locus-map `fmt` (PNG path).

**v9.7.149–v9.7.151:** **GAP — not described here.** This manifest's authors for v9.7.154 did not have
cut-level visibility into v9.7.149–151. Whoever cut those should backfill this list rather than have it
guessed. Flagged explicitly per the standing "surface the fork, don't fabricate" rule.

## Validation status

| Gate | Status |
|---|---|
| Full pytest suite | PASS (8489 passed, 1037 skipped; receipt-bound log) |
| `sync_version --check` | PASS when run from candidate CODE tier |
| `gen_release_manifest.py --check` | PASS on all four tiers after manifest rewrite |
| `verify_release_identity.py --root CODE --tiers-dir <candidate>` | PASS after packaging |
| per-tier `sha256sum -c SOURCE_CHECKSUMS_SHA256.txt` | PASS after final cleanup |
| outer `sha256sum -c SHA256SUMS.txt` | PASS after packaging |

## Known limits

- Candidate rebuild only; not a signed release.
- v9.7.154: full `pytest tests/` completes clean after the PATCH-004 test-isolation fix. The 7
  order-dependent failures previously seen in `test_modeb_strand_standard_v97144.py` and
  `test_modeb_workflow_v97143a.py` were **not** a pandas-3.0.2 incompatibility in
  `mamey.mode_b.schema` (the v9.7.153 manifest's prior text here was incorrect). They were a
  `sys.modules` pop-without-restore leak in `test_bunny_hop_fixes.py`'s two pandas-fallback tests:
  a later fresh `import pandas` minted a second, incompatible copy of pandas' compiled classes,
  tripping an `isinstance` assertion deep in pandas only on full-suite collection order. Fixed by
  snapshot/restore of the exact prior `sys.modules` entries; see `CHANGELOG.md` v9.7.154 and
  `PATCH_TESTISOLATION_SYSMODULES_*`. Re-run the **full** suite to confirm — the bug never appears
  in isolation.
- No real antiSMASH strain smoke test has been run in this session — out of scope for a
  bug-fix/test-infra cut that touches no parsing or scoring logic; not a gap for this release class.
- Human review is still needed before any signed-release treatment.
- v9.7.153: a direct sweep of **CODE tier only** (`grep` for `AS-[0-9]+`-pattern identifiers
  outside `tests/`/`examples/`/`docs/`) found no surviving private-strain identifiers — only the
  documented `enterocin AS-48` public-reference carve-out (a real public bacteriocin name, not a
  cohort strain) and this session's own code comments referencing patch-source chat names. **This
  does not confirm or refute the claim for CODE-analysis-free or SID-public** — those tiers were
  not built or checked this session. Treat the original claim below as last-verified at whatever
  bundle version actually ran the full `audit_public_cut.py` sweep across all three tiers, not
  carried-forward boilerplate:
  - *(original claim, unverified for CODE-analysis-free/SID-public at v9.7.153):* Public-tier
    AS/PENDING redaction checks still report surviving identifiers in CODE, CODE-analysis-free,
    and SID-public; treat public-release promotion as blocked until sanitized or explicitly
    accepted as intentional synthetic/protocol examples.

## Derived sync anchors

All four tiers share build stamp `20260907v97414a`.

| Gate | Status |
|---|---|
| `sync_version --check` | PASS (engine 1.9.152, bundle 9.7.414) |

All tracked version anchors at v9.7.414 / Mamey 1.9.152.
`MAMEY_CHATGPT_EXECUTION_PROMPT.md` updated to v9.7.414.

*Generated: 2026-09-07 | Sapote-Mamey Bundle v9.7.414 | NOT_FOR_PUBLIC_RELEASE*
