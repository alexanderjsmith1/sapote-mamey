# B2 — Registry-Backed Detector Wiring Spec, PHASE 2 (HMM/DIAMOND/BLASTP expansion)
**For execution in the ChatGPT/local runtime where HMMER + profile DBs exist.**
**Author handoff:** Claude (Sapote layer) · **Date:** 2026-06-10 · **Bundle:** v9.4.1-RUNNABLE (post-B2-Phase-1)
**Prereq:** Phase 1 (registry-driven regex/motif parity) is DONE and proven — see
`docs/patch_notes/B2_REGISTRY_WIRING_PHASE1_2026-06-10.md`. Do not start Phase 2 until
`tests/test_b2_registry_parity.py` is green on the target machine.

---

## 0. What Phase 2 is and is NOT

Phase 2 activates the registry's **non-regex detector backends** so markers can fire from
HMM/protein evidence rather than only annotation-text regex. This EXPANDS detection — which
is the whole point, and also the whole risk. The runner produces hour-long, ground-truth-validated
runs; a careless backend swap can silently change a validated call. Phase 2 is therefore done
**one backend family at a time, each diffed against AJS-XXX ground truth and the regex baseline.**

NOT in scope: changing scoring weights, claim ceilings, or workbook schema. New-backend hits
inherit the existing claim-ceiling machinery; they never auto-promote to product claims.

### The expansion set is smaller than it looks
Of the 16 HMM-bearing registry entries, **15 already carry a regex target** and therefore already
fire in Phase 1. For those, the HMM backend is a **precision/confirmation upgrade** (replace a
loose annotation-text match with a thresholded profile hit), not brand-new detection. Only
**`MMK-CCTT-015` (T43-TOMM, TIGR03604×2) is HMM-only** — genuinely new detection. Treat these two
situations differently (see §4).

| Entry | Library | Profile(s) | Has regex now? | Phase-2 effect |
|---|---|---|---|---|
| MMK-DOM-001 | domain_class | PF00501 (AMP-binding) | Y | precision upgrade |
| MMK-DOM-002 | domain_class | PF00668 (Condensation) | Y | precision upgrade |
| MMK-DOM-003/011 | domain_class | PF00550 (PP-binding/ACP) | Y | precision upgrade |
| MMK-DOM-005 | domain_class | PF00975 (thioesterase) | Y | precision upgrade |
| MMK-DOM-006 | domain_class | PF00109 (KS N) | Y | precision upgrade |
| MMK-DOM-007 | domain_class | PF00698 (AT) | Y | precision upgrade |
| MMK-DOM-013 | domain_class | PF02624 (YcaO) | Y | precision upgrade |
| MMK-CGAD-001 | chitin_glycan | PF00704 (GH18) | Y | precision upgrade |
| MMK-CGAD-002 | chitin_glycan | PF00182 (GH19) | Y | precision upgrade |
| MMK-CGAD-003 | chitin_glycan | PF03067 (AA10/LPMO) | Y | precision upgrade |
| SMK-NUC-001 | marker_addenda | NikJ/PolH radical-SAM | Y | precision upgrade |
| SMK-PHO-001 | marker_addenda | PF13714 (PepM) | Y | precision upgrade |
| SMK-ENE-001 | marker_addenda | ene_KS curated | Y | precision upgrade |
| SMK-UMED-004 | sapote_umed | PF00675/PF05193 (M16) | Y | precision upgrade |
| **MMK-CCTT-015** | mamey_cctt | **TIGR03604 ×2** | **N** | **NEW detection** |

`min_bitscore`/`max_evalue` are `None` in the inventory; the real thresholds live in the v8.11
source library (`release2_source_library/sapote_v8_11_registry/sapote_markers.py`). Carry them over
in step 2 — do not invent thresholds.

---

## 1. Environment — stand up the tools and DBs

Run on the machine that does real antiSMASH runs (has CPU + disk; can reach the internet once to
fetch DBs). The Claude sandbox cannot do this (no network, no binaries) — that is why this is a
ChatGPT/local spec.

```bash
# 1a. Tools (conda is the least-friction route on a lab box)
conda create -n mamey-hmm -y python=3.11 hmmer=3.4 diamond=2.1 blast=2.15
conda activate mamey-hmm
pip install -r requirements.txt           # bundle deps
python -c "import shutil; print(shutil.which('hmmsearch'), shutil.which('diamond'), shutil.which('blastp'))"
# all three must be non-None

# 1b. Profile databases (pin versions; record them in the run manifest)
mkdir -p ~/mamey_db && cd ~/mamey_db
# Pfam-A (used by all PF##### markers)
wget https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz
gunzip Pfam-A.hmm.gz && hmmpress Pfam-A.hmm
# TIGRFAM (used by TIGR03604 etc.)  — JCVI/NCBI mirror
wget https://ftp.ncbi.nlm.nih.gov/hmm/TIGRFAMs/release_15.0/TIGRFAMs_15.0_HMM.LIB.gz
gunzip TIGRFAMs_15.0_HMM.LIB.gz && mv TIGRFAMs_15.0_HMM.LIB TIGRFAM.hmm && hmmpress TIGRFAM.hmm
```

Record the exact DB releases (Pfam release number, TIGRFAM 15.0) in the run manifest. A marker's
hit is only reproducible against a pinned DB version. Two custom profiles
(`NikJ/PolH-like radical SAM PN`, `ene_KS curated`) are NOT in Pfam/TIGRFAM — defer those two
markers to a later sub-phase (see §6) or supply curated `.hmm` files first.

---

## 2. Make the registry carry detector payloads + thresholds

The inventory currently records the accession but not the threshold. Backfill from v8.11 so each
HMM target is self-describing. This is a data edit to `bundle_support/registry_inventory_v1.9.4.json`, not code.

For each of the 16 entries, set on the HMM target:
- `min_bitscore`, `max_evalue` — copied verbatim from the matching v8.11 `MarkerDefinition`
  (match by accession). Verified mappings present in v8.11:
  PF13714 → `pepm` bit=150.0 eval=1e-30 (full_proteome); PF00109 → `t2pks_ks`/`mod_ks` bit=100.0
  eval=1e-15 (bgc_local); PF00975 → `te_domain` bit=80.0 eval=1e-10; PF02624 → `yca_o` bit=100.0
  eval=1e-20; TIGR04186 → `nikj` bit=300.0 eval=1e-60 (full_proteome).
- **GAP — `TIGR03604` (MMK-CCTT-015) is NOT in v8.11**, so there is no inherited threshold. Set a
  conservative TIGRFAM trusted-cutoff: use the model's own GA (gathering) threshold from the
  TIGRFAM `.hmm` (`hmmsearch --cut_ga`) rather than a numeric floor. Document this choice; it is
  the only marker without a v8.11-inherited threshold.
- **`ene_ks` (TIGR03828) has bit=None/eval=None in v8.11** — same `--cut_ga` approach; do not
  invent a numeric floor.
- `search_scope` — `bgc_local` | `contig_15kb` | `full_proteome`, from v8.11.
- `db` — `Pfam-A` | `TIGRFAM` | `custom` so the dispatcher knows which DB to search.

After editing, **Phase-1 parity must still pass** (these fields don't touch regex). Re-run
`tests/test_b2_registry_parity.py` — green confirms you only added inactive-target metadata.

---

## 3. Detector backend code (new, behind the frozen switch)

Add `mamey/hmm_backend.py`. It must be import-safe on a machine WITHOUT the tools (the Claude
sandbox imports the package for Phase-1 tests): all tool calls lazy, guarded, and only reached
when a backend is actually activated.

```
hmm_backend.py
  detect_tools() -> {"hmmsearch": bool, "diamond": bool, "blastp": bool}
  run_hmmsearch(faa_path, hmm_db, accessions) -> list[HmmHit]
      # HmmHit: accession, locus_tag, bitscore, evalue, target_len, ali_coords
      # one hmmsearch over the proteome, then filter to the requested accessions
  hits_to_marker_calls(hits, registry_entries) -> list[MarkerHit]
      # apply per-marker min_bitscore/max_evalue from §2; map locus->BGC by coords;
      # enforce search_scope; for MMK-CCTT-015 enforce the "TIGR03604 x2 within
      # one region +/- 3kb" required_context rule
```

Wire into `source_scans.py` via the EXISTING extension point: `extract_domain_features()` already
produces `DomainFeature(... bitscore, evalue ...)` and `scan_domain_architecture()` already
consumes `PFAM_domain`/`aSDomain` features. The cleanest path is to **feed HMM hits in as
synthetic `DomainFeature`s / `MarkerHit`s through that same channel**, so downstream scoring,
EFLS, and provenance treat them identically to antiSMASH-supplied domains. Do not add a parallel
scoring path.

Activation switch: `registry_detector.ACTIVE_DETECTORS`. It is frozen to `{"regex","motif"}`.
Widen it ONE family at a time (§4). Gate every widening behind a tool-availability check —
if the tool is absent, fall back to regex for that family and log it, never crash.

---

## 4. Activation order — one family at a time, each gated by a diff

For each step: widen `ACTIVE_DETECTORS`, run the FULL pipeline on the AJS-XXX antiSMASH input,
diff against the locked baseline (§5), inspect, decide, lock the new baseline only if clean.

**Step 4a — Pfam domain-class precision upgrade (MMK-DOM-*, MMK-CGAD-*).**
These already fire by regex. Activating `pfam` should *narrow* matches (thresholded profile vs
loose text). Expected diff: same BGCs detected, possibly FEWER spurious domain-class tags on
mis-annotated CDS. ANY BGC that LOSES a previously-correct domain call is a regression — review,
do not accept. Net new BGCs here = suspicious (a precision upgrade shouldn't add BGCs); investigate.

**Step 4b — Diagnostic single-accession markers (SMK-PHO-001/PF13714, SMK-NUC, SMK-ENE).**
These are DIAGNOSTIC-tier. A new HMM hit here can legitimately rescue a BGC the regex missed
(annotation-text absent but profile present). Expect possible NET NEW diagnostic calls. Each new
call must be spot-checked: pull the locus, confirm the hit bitscore clears the v8.11 threshold,
confirm it sits in/near a plausible BGC.

**Step 4c — MMK-CCTT-015 (TIGR03604 ×2), the only HMM-only marker.**
This is the one genuinely new detector. Activate `hmm`/`tigrfam` last. Enforce the
required_context rule exactly (two TIGR03604 hits within one region ±3 kb; a single hit must NOT
fire). Verify on a known TOMM/thiopeptide-positive control before trusting it on AJS-XXX.

Never widen two families in one diff — you lose attribution of which backend caused a change.

---

## 5. The AJS-XXX ground-truth diff (the acceptance gate)

AJS-XXX = marine sponge-associated *Streptomyces*-family actinomycete; **five published compound
families are the ground truth** (monolith §-validation summary, line ~5523):

| Family | Class | Detection anchor | Must-hold after each Phase-2 step |
|---|---|---|---|
| **Photopiperazine** | DKP / dehydro-DKP | CDPS ctg1_80 + oxidase ctg1_78 = DKP-**A** by AlbA/AlbC homology | DKP-A call UNCHANGED |
| **Ionostatin** | linear polyether ionophore | *ion* region (NZ_SKBR01000002.1 r8; 7 PKS; KCB 16 hits) | polyether/LMPKS-PE call UNCHANGED |
| **Marinoterpin A–C** | meroterpenoid | KnownClusterBlast BGC0002372 (no marker logic) | KCB anchor UNCHANGED |
| **Tetrachlorizine** | (ClusterBlast literature control) | KCB/ClusterBlast | UNCHANGED |
| **Marinolide** | (bundled example) | — | UNCHANGED |

Plus the runner-level fact from memory: AJS-XXX/AJS-XXX-equivalent run = **43 BGCs confirmed genuine**,
**BGC001 → DKP-A**. (Note: bundle memory also references AJS-XXX as the validated DKP-A strain; if
your local copy uses the AJS327 genomic extraction run with 43 BGCs, that exact count is the
top-line regression number — it must not change under a precision upgrade.)

**Procedure:**
```bash
# Baseline (Phase 1, regex-only) — lock it ONCE before any widening
MAMEY_DISABLE_REGISTRY_DETECTOR=0 python mamey_run.py <AJS-XXX antismash zip> -o ajs327_baseline.xlsx
python tools/dump_scan_state.py ajs327_baseline.xlsx > ajs327_baseline.json   # see §5 note   # PLANNED — not implemented in v9.7.319 (phase-2 spec; no such script ships yet)

# After each 4x step:
python mamey_run.py <AJS-XXX antismash zip> -o ajs327_4x.xlsx
python tools/dump_scan_state.py ajs327_4x.xlsx > ajs327_4x.json   # PLANNED — not implemented in v9.7.319 (phase-2 spec; no such script ships yet)
diff <(jq -S . ajs327_baseline.json) <(jq -S . ajs327_4x.json)
```
Diff columns that matter: per-BGC marker calls, domain-class tags, CCTT triggers, DKP rank,
edge/EFLS status, KCB anchors, BGC count. (`tools/dump_scan_state.py` does not exist yet — write a   # PLANNED — not implemented in v9.7.319 (phase-2 spec; no such script ships yet)
~30-line dumper that serializes the scan-state dict deterministically, or reuse the serializer in
`tests/test_b2_registry_parity.py`.)

**Decision rule per diff:**
- Zero diff → backend is inert on AJS-XXX; safe, but verify it fires SOMEWHERE (a positive control)
  before claiming the family works.
- Diff is only NEW hits, each spot-checked legitimate, and all five ground-truth families + the
  43-BGC count + BGC001→DKP-A hold → ACCEPT, lock new baseline.
- Any LOST or CHANGED previously-validated call → REJECT, flag for human review (§7). Never
  silently accept a changed validated result.

---

## 6. Deferred sub-phase — custom profiles

`SMK-NUC-001` (NikJ/PolH radical-SAM PN) and `SMK-ENE-001` (ene_KS curated) reference profiles
described as "curated" in the inventory, but v8.11 maps both to STOCK TIGRFAM accessions that need
no custom build:
1. **Preferred — use the stock accession.** v8.11 `nikj` carries TIGR04186 (NUC); v8.11 `ene_ks`
   carries TIGR03828 (ENE). Both are in the TIGRFAM DB fetched in §1. Set the HMM target's
   `value` to the TIGRFAM accession and `db: TIGRFAM`. This keeps DBs standard and avoids a custom
   build entirely. Use `--cut_ga` for thresholds (neither has a v8.11 numeric floor).
2. **Fallback — only if the stock model is too broad in practice:** build a curated `.hmm` from a
   seed alignment of known family members (`hmmbuild` + `hmmpress`), store under
   `~/mamey_db/custom/`, set `db: custom`. Document the seed set.
Verify each fires on a positive control (a known nucleoside-antibiotic / enediyne BGC) before
trusting it on AJS-XXX.

---

## 7. Regression discipline (non-negotiable, carried from the Phase-1 spec)

- Before enabling any new-backend marker, parity (Phase 1) must hold: zero diff on the regex
  baseline for the non-activated families.
- Enable backends one family at a time; diff every scan column against expectation + AJS-XXX
  ground truth.
- Any marker that changes a previously-validated call is FLAGGED and human-reviewed, never
  silently accepted.
- New-backend hits get claim ceilings; never auto-promote to product claims.
- Record DB versions (Pfam release, TIGRFAM 15.0) in the run manifest; a hit is only reproducible
  against a pinned DB.
- Claude verifies parity + expansion against ground truth on the returned scan-state + diff.

## 8. Acceptance (Phase 2 complete)
1. `tests/test_b2_registry_parity.py` still green (Phase-1 parity intact for non-activated families).
2. Each activated family diffed on AJS-XXX; all five published families + 43-BGC count +
   BGC001→DKP-A hold; every new hit spot-checked.
3. `MMK-CCTT-015` fires only on the 2×-TIGR03604-within-region rule, verified on a TOMM-positive
   control.
4. New-backend hits carry claim ceilings; no product-claim auto-promotion.
5. Run manifest records tool versions + pinned DB releases.
6. Claude has verified the returned diff against ground truth.

## 9. Handback to Claude
Return: (a) the AJS-XXX baseline + post-activation scan-state JSONs, (b) the per-step diffs,
(c) the list of new hits with bitscores/loci, (d) the run manifest (tool + DB versions),
(e) updated `bundle_support/registry_inventory_v1.9.4.json`. Claude will re-verify parity, vet each new call
against the five-family ground truth, and confirm no validated call was lost before this is
merged toward a release tag.
