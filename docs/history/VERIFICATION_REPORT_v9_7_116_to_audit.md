# VERIFICATION REPORT → audit chat — v9.7.116 consolidated handoff reconciliation

**From:** patch chat · **Re:** `PATCH_HANDOFF_v9_7_116_CONSOLIDATED.md` checked against the actual build tree
**Tree:** `/data/mamey-local/v116_build` (descends from frozen v9.7.115) · **Suite:** 1,706 passed, 96 skipped, 1 xfailed · version still 9.7.115 (bump at cut)
**Master fixture:** byte-identical to the shipped `Cohort_Master_24strain_v2_scored.xlsx` (SHA `5c434c05…`), so all numeric verification transfers.

This report confirms what's folded + independently verified, flags discrepancies, and lists what is NOT yet in the tree so the cut scope is honest.

---

## Per-item reconciliation

| Handoff item | Claim | Tree state | Independent verification |
|---|---|---|---|
| 1a findings staleness | populator didn't re-fire 18→24 | **FIXED differently** — see discrepancy #1 | hardcoded literals removed; audit passes on v2 |
| 1b denominator invariant | implemented + passes | **FOLDED ✓** `tools/cross_strain_denominator_audit.py` | catches all 3 stale /18 on v1; clean on v2; ignores 164/1131 |
| 1c stale About string | sweep on rebuild | not applicable to my tree (their master only) | n/a |
| 2 master fixture | verified scored master | **bundled to `private/`** (AS-bearing, leak-safe) | DAPR 200/200, findings /24, denominator audit clean |
| 3 Gap 2 card context | BUILT, 9 tests | **FOLDED ✓** `mamey/cross_strain_card_context.py` | reproduces 11/11 differentiating capacities exactly |
| 4 Gap 1 orchestrator | BUILT, 7 tests | **FOLDED ✓** `mamey/cohort_cards.py` | injection + regex-at-start + real-master flagging verified |
| 5 Gap 3 synthesis | BUILT, 10 tests, novelty_basis | **FOLDED ✓** `mamey/cohort_synthesis.py` | fully_dark=164 AND dark_or_unresolved=423 **exact** |
| 6 RG-GMCI rollup | spec only | **NOT folded** (spec acknowledged) | — |
| 7 singleton + pks | modules done, un-wired | **FOLDED + WIRED ✓** (singleton) — see discrepancy #2 | substring bug fixed; BGC045 artifact fixed |
| 8a locus-map scale fix | coded + verified | **FOLDED ✓** `mamey/locus_map.py` | contig-end BGC 8%→93% of panel |
| 8b/8c report layout | drop gene table + tight flow | **NOT folded** | — |

---

## Discrepancies the audit chat should know about

**#1 — Item 1a root cause was different than diagnosed (and the fix is more durable).**
The handoff says the `Cross_Strain_Findings` populator "did not re-fire" on cohort growth. The actual root cause in `tools/add_xstrain_sheets.py` is that rows 3–4 had **hardcoded string literals** `'universal classes (18/18)'` and `'17/18 / 15/18'` — they were never dynamic, frozen from when the cohort was 18. Every *other* findings row already computes from `N`. Fix: made rows 3–4 compute from `N` and `prev[...]` like the rest. So it wasn't a re-fire-trigger gap; it was two literal strings. The denominator invariant (1b) catches either cause, so the durable guard is the same — but the diagnosis differs and the "re-fire trigger" wiring the handoff implies isn't needed.

**#2 — Item 7 singleton_filter shipped with the substring-containment bug; fixed on intake.**
The shipped `singleton_filter.py` matched housekeeping stems as bare substrings (`stem in domain`). Confirmed real false drops: `Trans_AT_S1`, `PKS_Docking_S1`, `Peptidase_S1` (all caught by bare `s1`), `NADHpyr_redox` (`nadh`), `GtrA_like` (`gtra`), `ABC1_kinase` (`abc1`) — genuine biosynthetic domains silently classified housekeeping, which *deflates* novelty counts (the opposite of the module's purpose). Replaced with three-tier token-bounded matching (prefix / exact-token / whole-name). **All the shipped module's real-data assertions still pass; the false drops are now fixed.** 7 regression tests added. This is the same bug class as the v9.7.115 marker/evidence-gate fixes.

**#3 — pks_investigation.py was never in any bundle.**
Item 7 references "43 pks tests" and a `pks_investigation` module, but it is not in `Archive_4.zip` nor the consolidated bundle — only the handoff text describes it. Cannot fold or verify what isn't shipped. **However**, the tree already has overlapping mis-anchor machinery (`source_scans.py` KCB class-mismatch guard), so the core protection isn't missing. I *did* fold the one actionable divergence the pks handoff flagged: Cy/`Heterocyclization` domains now classify as assembly-line core in `s3_census_generator` (+2 tests).

**#4 — Gap 3: I initially reproduced the SAME bug the handoff says was fixed, then adopted the shipped fix.**
My own first Gap 3 attempt got `dark_or_unresolved` wrong (concluded 423 "not derivable from the master"). The shipped module is correct — the resolution signal IS in `KCB_Top_Hit` (`BGC\d{7}` = MIBiG-resolved vs bare genome-ref = unresolved). I adopted the shipped novelty engine and **grafted in CSV-sourced genus/host** (the shipped version left genus as "not" / host as "Other" because the master registry taxonomy is unpopulated and the metadata JSON it expects wasn't bundled). Merged result reproduces 164/423 exactly AND populates the genus signatures (Actinophytocola PKS-dominated, etc.). See discrepancy #5.

**#5 — The master registry has NO populated genus/host; genus/host is sourced from the differentiating CSV (9 of 24 strains).**
`A2_Strain_Registry.Genus` is uniformly `'not'` and `Host_Source` is `'—'` in the scored master. The validated genus signatures and host gradient depend on taxonomy that lives only in the per-strain manifests / the differentiating CSV. My Gap 3 sources them from the CSV (covers 9 strains) and **states the partial coverage honestly** rather than emitting a misleading full-cohort claim. The genus-signature section suppresses the unresolved bucket and notes "provide genus for all 24 strains to complete." **For a clean cut, please bundle full strain genus/host** (registry columns or a metadata file) so these sections cover all 24.

---

## Test-count reconciliation (minor, explainable)

| Module | Handoff | Tree | Why |
|---|---|---|---|
| Gap 2 | 9 | 9 | match |
| Gap 1 | 7 | 6 | dropped 4 package-dependent (no `cohort_runs/` here), added 3 logic + real-master tests |
| Gap 3 | 10 | 13 | added 3 genus-from-CSV tests (the graft in #4/#5) |

The handoff's "+72 from item 7" (43 pks + 29 singleton) won't materialize: pks isn't shipped (#3), and the singleton test file is 36 in-tree (29 theirs + 7 false-drop regressions). Net new cohort+hardening tests in tree: ~78.

---

## NOT yet folded (must be scoped in or deferred to v9.7.117)

1. **Item 6 — RG-GMCI cohort rollup** (`tools/rggmci_cohort_rollup.py`). Spec only in both handoff and tree. D2_RGGMCI_Top_Pairs (158 rows) is populated, so it's buildable. Target result to reproduce: 158 HIGH → 43 complementary + 16 terminus = 59 genuine, 24 paralog excluded, 75 mixed; 2 CONFIRMABLE / 31 LIKELY / 26 REVIEW.
2. **Item 8b/8c — report layout** (drop redundant gene table; tight card flow). Not folded.
3. **Gap 2 nearest-pair sub-feature** — needs `E2_Comparative_Pairs` populated (still the one absent sheet; `update_e2_comparative_pairs()` exists but wasn't run on the cohort bank). The *class-ubiquity* feature (the 11 capacities) is fully done; only the nearest-pair line is pending.

---

## Recommendation

Items 1, 2, 3, 4, 5, 7(singleton), 8a are **folded and independently verified** against the byte-identical master. A clean v9.7.116 cut could ship these now as the "cross-strain cohort analysis + verification hardening" release, with items 6, 8b/8c as v9.7.117. Before the cut I need two things from the audit/analysis side: (a) confirmation that the deterministic DAPR provenance flag travels in the master's About/provenance (per item 2), and (b) full strain genus/host so the Gap 3 genus/host sections cover all 24 (per #5). Awaiting go/no-go on scope.
