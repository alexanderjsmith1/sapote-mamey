# Engine Lineage and Compatibility
**Version history, scoring boundaries, and cross-version compatibility**

**v9.7.149a** | Source: `docs/ENGINE_LINEAGE.md`, `docs/COHORT_RESCORING_PLAN.md` | Last updated: 2026-06-29

---

## Why engine version matters

Every Mamey run stamps its output with the engine version. Cross-strain comparisons are only valid when all strains use the same engine. If strains were scored at different versions — which happens during active development — the comparative layer is blocked until re-scoring is complete.

The `cohort_scoring_version_gate.py` tool enforces this as a fail-closed gate.

---

## Current engine

**Engine:** 1.9.100 | **First bundle:** v9.7.142 | **Current bundle:** v9.7.149a

---

## Engine lineage (authoritative record)

### Engine 1.9.100 — current

**Bundle range:** v9.7.142 – v9.7.149a (current)
**Bump from:** 1.9.99
**Bump reason:** Evidence-handling and runtime-interface expansion
**Scoring/parser semantics changed:** No intentional AB/AF scoring overhaul; evidence ingestion and output interfaces expanded

**What entered the tree:**
- `mamey/bgc_blastp_panel.py` — BLASTP panel export for large modular PKS/NRPS proteins
- `mamey/blastp_followup.py` — BLASTP follow-up result parsing and ingestion
- `mamey/blastp_evidence_store.py` — durable per-BGC BLASTP evidence store
- `mamey/citation_compact.py` — citation compact output mode
- `mamey/validators/modeb_full20.py` — first Mode B §1–§20 validator (144a schema)
- Claim-safety gate infrastructure
- LLM handoff utilities
- Release QA tooling

**Tests run at bump:** focused pytest suite (82 tests passed at v9.7.142 baseline)

---

### Engine 1.9.99 — baseline (pre-v9.7.142)

**Bundle range:** up to v9.7.141
**What this covered:** core BGC extraction, scoring (AB/AF), KCB/MIBiG matching, architecture grading (A–E), RGGMCI split-cluster reconstruction, FLBR/LMPKS rescue, UMED/CGAD/EFLS/CCTT triggers, evidence conservation, four-tier release infrastructure.

---

## Compatibility matrix

| Mamey engine | Bundle version | Workbook schema | Backward compatible |
|-------------|---------------|-----------------|-------------------|
| 1.9.100 | v9.7.149a (current) | v1_1 | ✓ Current |
| 1.9.99 | v9.7.144a | v1_1 | ✓ Supported |
| 1.9.95 | v9.7.140 | v1_1 | ✓ Supported (with caveats) |
| 1.9.85 | v9.7.120 | v1_1 | ✓ Read-compatible |
| 1.9.50 | v9.7.100 | v1_0 | ~ Legacy; can read, not write |
| <1.9.50 | <v9.7.100 | v0_9 | ✗ Unsupported |

**Forward compatibility:** Older versions cannot read newer workbooks. Never attempt to open a v1_1 schema workbook with a v1_0 engine.

---

## What changes at a scoring boundary

A scoring boundary is an engine change that intentionally or unintentionally alters AB/AF scores. Strains scored before and after a boundary are not directly comparable for AB/AF ranking.

**Known boundary range:** 1.9.84 → 1.9.96 (multiple boundaries stacked; exact per-version CHANGELOG entries exist but are not reproduced here — see `docs/ENGINE_LINEAGE.md` for authoritative record).

**The implication:** If your cohort contains strains scored at engine 1.9.85 and 1.9.96, their AB/AF scores are from different rulebooks. Cross-strain rankings are invalid.

---

## Re-scoring protocol

When strains in a cohort were scored at different engine versions:

**Scope:** Every strain in the comparative cohort must be re-run at the target engine version.

**Per strain:**
1. Re-run deterministic Mamey extraction at the pinned engine version
2. Re-emit Sapote judgment layer under that version
3. Record engine version in the per-strain receipt

**After re-scoring, recompute from scratch:**
- Product-class prevalence matrices
- Pan-BGC-ome / BGC family groupings
- Cross-strain rankings

**What survives re-scoring unchanged:**
- Standing permanent exclusions (NAPAA, hglE-KS-PREV-001, saccharide)
- Claim-safety conventions
- Mechanism-level observations (e.g. HSAF/PTM recurrence as a mechanism observation, not a score ranking)

---

## Version gate enforcement

```bash
python tools/cohort_scoring_version_gate.py \
  --banked-dir cohort \
  --workbook master_workbook.xlsx
```

Exits non-zero if any strain was scored at a different engine version. A comparative build may only aggregate strains with matching scoring engine versions.

---

## Checking your package's engine version

```bash
# From the manifest
cat runs/[strain]/package/manifest.json | grep '"engine"'

# Or inspect the commit receipt
cat runs/[strain]/package/commit_receipt.json | grep '"mamey_engine"'
```

---

## Engine lineage maintenance rule

Every engine bump requires an entry in `docs/ENGINE_LINEAGE.md`. If `mamey.__engine__` changes between release baselines without an entry, `sync_version.py --check` exits non-zero with:

```
ERROR: engine changed X → Y but docs/ENGINE_LINEAGE.md has no entry for Y.
Add an entry before cutting a release.
```

Future engine bumps must include:
- Old engine version
- New engine version
- First bundle carrying new engine
- Reason for bump
- Whether scoring/parser semantics changed
- Tests run at bump

---

## Bundle version history (last 5)

| Bundle | Engine | Date | Status | Notes |
|--------|--------|------|--------|-------|
| v9.7.149a | 1.9.100 | 2026-06-29 | **Current** | Documentation audit + 28-batch docs |
| v9.7.148c | 1.9.100 | 2026-06-20 | Stable | Single-region accession support + SOP-07 |
| v9.7.144a | 1.9.100 | 2026-06-10 | Stable | Mode B validator (modeb_full20.py) + version-stamp fixes |
| v9.7.142 | 1.9.100 | 2026-05-15 | Stable | First 1.9.100 bundle; BLASTP utilities |
| v9.7.141 | 1.9.99 | 2026-04-01 | Legacy | Last 1.9.99 bundle |

---

## See also

- **Authoritative source:** `docs/ENGINE_LINEAGE.md`
- **Re-scoring plan:** `docs/COHORT_RESCORING_PLAN.md`
- **Version gate tool:** `tools/cohort_scoring_version_gate.py`
- **Schema check:** `python mamey/workbook_schema_check.py`
- **Sync version check:** `python tools/sync_version.py --check`
- **Multi-strain claims guide:** `batch22_multi_strain_comparative_claims.md`
