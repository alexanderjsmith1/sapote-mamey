# Sapote–Mamey — Volume I — Plain-Language Companion
## Counting, Scoring, and Reconstruction in the Deterministic Extraction Engine
**Source document:** `docs/reference/01_Math_Reference_VolI.md` (re-grounded to Mamey engine v1.9.164 · bundle v9.7.429; originally compiled v1.9.110 / v9.7.319)
> **Start with the value you are reading.** Use §1–§3 for counts/boundaries, §4–§6 for scores
> and tier changes, and §7 for candidate fragment links. The [technical Volume I](../reference/01_Math_Reference_VolI.md)
> gives formula context; [current source scope](../reference/06_CURRENT_SOURCE_SCOPE.md) records
> known implementation boundaries. Resolve a conflict at the selected source owner, not by
> assuming either prose constants table has been fully reverified.
**Constants re-verified against:** bundle v9.7.429 · engine 1.9.164 · re-grounded 2026-09-14 (core formulas unchanged since v1.9.110; CCTT trigger roster expanded at v1.9.99)


*Volume I covers the engine's core quantitative pipeline: how BGCs are counted, how an assembly is graded, how the three routing scores are built, how the guards suppress them, and how fragmented clusters are reconstructed. Volume II covers the subsystems that feed and surround it (CCTT triggers, architecture-first assessment, KCB/RiQ extraction, compound-class annotation, rescue, enrichment, and — from v9.7.250 — Cluster G).*

---

> **Current formula use:** The grounding stamps above are historical. Use the installed Python,
> named configuration and admitted input state for current numerical behavior. Verify each scientific
> explanation and worked case against its own evidence; another historical reference does not
> override the installed source.

## 0. How to read this document

Two rules govern every number below. They are not caveats; they are the semantics.

1. **Scores are routing priors, not biological proof.** No value here — no count, no score, no tier, no rescue link — is evidence that a strain *produces* a compound. Capacity-level language ("biosynthetic capacity consistent with…") is mandatory downstream. Raising a lead's tier never raises its claim ceiling.

2. **KCB is similarity, not identity.** Every KnownClusterBlast signal is a sequence-similarity score against a reference. It informs novelty and display. It never confirms a product.

Every formula is transcribed from engine source with a `module.py:symbol` citation. Where a constant has drifted since the Vol I source was compiled, the **running module is authoritative** and the drift is noted.

---

## 1. BGC boundary classification

**Source:** `parsers.py:_edge_status`

Every antiSMASH region is assigned exactly one of three boundary states, from its coordinates relative to its contig.

```
EDGE_FLANK        = 5_000        # bp
FULL_CONTIG_FRAC  = 0.95         # region span / contig length

Unknown      ⇐  contig_length <= 0
Full-contig  ⇐  (end - start + 1) >= 0.95 * contig_length
Interior     ⇐  circular replicon (after the Full-contig check)
Edge         ⇐  start <= 5000  OR  (contig_length - end) <= 5000
Interior     ⇐  otherwise
```

Precedence: **Full-contig is tested first.** A region occupying ≥95% of its contig is Full-contig even though it also satisfies the Edge predicate — it is truncated at *both* ends, and the count weight must reflect that.

**Circular-replicon correction (v9.7.87).** On a closed chromosome the origin is not a truncation point: a region adjacent to the origin wraps and is **Interior**, not Edge. Without this correction every closed genome reported spurious Edge regions.

**Interpretation.** Edge status is a coordinate/topology classification under the supplied
contig length and bounds. It flags possible boundary truncation; it does not directly measure
missing sequence or pathway completeness. A–E architecture grading (§5.2) adds source-label,
length and hybrid evidence, but is also a heuristic. Read the fields together.

---

## 2. The corrected BGC count

**Source:** `assembly.py:corrected_bgc_count`

```python
corrected = round(I + 0.5 * E + 0.25 * F, 2)
```

where `I`, `E`, `F` are the Interior, Edge, and Full-contig counts.

The weights encode **partial evidence**, not partial existence:

| Class | Weight | Reasoning |
|---|---:|---|
| Interior | 1.00 | Fixed contribution for the Interior label; not proof of a complete pathway |
| Edge | 0.50 | Fixed contribution for the Edge label; does not measure half a locus |
| Full-contig | 0.25 | Fixed contribution for the Full-contig label; does not measure one-quarter recovery |

**Invariant:** `corrected ≤ raw` always. With the same nonnegative I/E/F denominator, a violation signals inconsistent counts/inputs or arithmetic. False boundary labels can depress the discounted count, as in the circular-replicon defect, while still satisfying this inequality.

**Corrected count is a boundary-weighted comparison heuristic, not the only meaningful counting scope or a proven biological count.** Retain raw region calls and exact denominators when reporting observed inventory; fragmentation can split one pathway across calls, while fused calls and false/missing predictions create other uncertainties. The raw count is always reported alongside, so the discount is visible rather than hidden.

**It is a pre-rescue weighted summary, not a guaranteed floor on biological pathway count.** RG-GMCI (§7) may later show that two Edge fragments are one cluster. The corrected count does not anticipate that; it is the defensible number before reconstruction.

**Worked example (teicoplanin calibration, this session).** `BGC0000440` is a single MIBiG reference cluster deposited as its own contig: `I=0, E=0, F=1` → `corrected = 0.25`, `interior_pct = 0.0`, tier `VERY_POOR`. Both are correct and both are artifacts of the input shape, not of the biology. A single-region reference deposit *is* a full-contig fragment.

---

## 3. Assembly quality tier

**Source:** `assembly.py:assembly_tier`

```python
interior_pct = round(100 * I / raw, 1) if raw else None  # raw includes Unknown-boundary records

interior_pct >= 70  ->  GOOD
interior_pct >= 45  ->  MODERATE
interior_pct >= 20  ->  POOR
interior_pct <  20  ->  VERY_POOR
None                ->  UNKNOWN
```

**The tier is decided by interior-BGC percentage alone.** Contig count and N50 are descriptive context, not part of the test. The 66/50/33 thresholds are **retired** — `tools/check_monolith_freshness.py` scans the parent design document for them as a marker of stale doctrine.

The tier summarizes the supplied boundary distribution. It is separate from contiguity
classification and per-locus architecture/claim fields; it does not impose a calibrated
strain-wide biological claim ceiling. Read the source/input scope before interpreting a low
count or a GOOD label.

### 3.1 Supporting statistics

`N50` — sort contigs descending by length, accumulate; N50 is the contig length at which the running total first reaches half the assembly. A contiguity proxy. It does not enter the interior-percentage `assembly_tier`; the separate `fragmentation_tier` does threshold N50 jointly with contig count (`assembly.py`).

### 3.2 Contamination / sanity heuristic (non-blocking)

**Source:** `assembly.py:assembly_sanity_check` (PC-A2, v9.7.101)

```python
GC_SD >= 5.0   ->  CONTAMINATION_SUSPECT
```

Length-weighted standard deviation of per-contig GC%. Clean genomes run 1–2%; contaminated drafts 7–12%.

**Genome-size and GC flags are assembly-sanity heuristics, not co-assembly diagnoses.** The current default upper bound is 12,000,000 bp; a positive size above that bound sets `INFLATED_ASSEMBLY_SUSPECT`. The lower 3,000,000-bp default can flag partial assemblies, with at most five contigs additionally setting `PARTIAL_SUBMISSION_SUSPECT`; caller overrides can change or disable these bounds. GC dispersion and any supplied GC/size priors are separate checks (`assembly.py`). Contig count and raw BGC count are affected differently by fragmentation and prediction; neither proves contamination or a two-strain assembly.

Non-blocking: extraction proceeds, the stats are recorded.

---

## 4. The three routing scores

**Source:** `scoring.py:triage_bgcs`

### 4.1 Base + keyword model

```python
base_ab      = 25 + score_keywords(class_txt, AB_KEYWORDS)
base_af      = 20 + score_keywords(class_txt, AF_KEYWORDS)
base_novelty = 30 + score_keywords(class_txt, NOVELTY_KEYWORDS)
```

`class_txt = scoring_class_text(bgc)` = the BGC's **own** `products` + `mibig_hits` + `closest_candidate_kcb_product` (when resolved).

**It is NOT the raw `kcb_top` blob.** The v9.7.85 P-7 contamination fix: `kcb_top` contains the *reference organism's* entire genome-description vocabulary, which falsely credited those classes to this BGC. A BGC whose top hit sat in a *Streptomyces* chromosome inherited every class token in that chromosome's description.

**Keyword weights** (`scoring.py`):

*AB (18 keyword entries):* carbapenem 18 · phosphonate 15 · thioamide 14 · thiopeptide 14 · thiazolylpeptide 14 · hr-t2pks 14 · transat-pks 14 · aminoglycoside 14 · nrps 12 · t2pks 12 · lanthipeptide 12 · t1pks 10 · lassopeptide 10 · phenazine 10 · saccharide 8 · halogenated 8 · ripp 8 · azole 8

*AF (17 keyword entries):* hsaf 20 · nystatin 20 · nikkomycin 20 · polyoxin 20 · polyene 18 · candicidin 18 · nucleoside 18 · tetramate 16 · sgr ptm 14 · chitin 12 · ptm 12 · transat-pks 12 · t1pks 10 · nrps 8 · terpene 6 · siderophore 4 · metallophore 4

*Novelty (11 classes):* transat-pks 18 · enediyne 18 · azoxy 18 · thioamide 15 · phosphonate 15 · hgle 12 · ranthipeptide 12 · ripp 10 · nrps 8 · t1pks 8 · t2pks 8

**Compound-class scored consequence (v9.7.86).** If the BGC's `compound_class_annotation` carries a `scored_axis`, its `scored_weight` is added to that axis: `polyene_macrolide` → AF +22 (the largest single compound-class bonus), `ionophore` → AB +14, `anthracycline` → weight **0** (a routing flag for the cytotoxic board, not an AB/AF score).

### 4.2 Delimited matching and subsumption

```python
_key_present(key, text)  ⇐  re.search(rf"(?<![a-z0-9]){key}(?![a-z0-9])", text)
```

Delimiter-bounded, **not substring**. This is what stops `"polyene"` inside `"arylpolyene"` from claiming the AF polyene weight — arylpolyene is a flexirubin-type pigment, not an antifungal polyene macrolide.

**Subsumption** prevents double-counting a class and its subclass:

```python
SUBCLASS_SUBSUMES = {"hr-t2pks": "t2pks", "transat-pks": "t1pks"}
# if both matched, discard the generic
```

**`PIGMENT_NONLEAD_CLASSES = {arylpolyene, ladderane}`** are excluded from scoring entirely.

### 4.3 The diagnostic bonus

```python
DIAGNOSTIC_BONUS = 25
```

Added to the relevant axis when a **corroborated** class-defining CCTT trigger fires (corroboration: §6.1).

- **AF triggers:** `T43-NUC`, `T43-PTM`, `T43-PYE` (polyene macrolide; v1.9.99)
- **AB triggers:** `T43-LAN`, `T43-LASSO`, `T43-THA`, `T43-PHO`, `T43-AMC`, `T43-BLA`, `T43-GPA` (glycopeptide; v1.9.99), `T43-BLT` (betalactone; v1.9.99)
- **Excluded from the tier floor:** `TIER1_FLOOR_EXCLUDED_PREFIXES = ("T43-HAL_", "T43-XHAL_")` — halogenases are *tailoring* modifications, not class calls. A lone halogenase does not floor a tier.

### 4.4 KCB and RiQ novelty adjustments

```python
kcb_evidence_state != "UNKNOWN_KCB" and kcb_cumulative > 10_000 -> novelty -= 15
missing/unknown KCB evidence -> no novelty credit in either direction
riq_score      <  0.50   ->  novelty += 10    # region distant from its closest MIBiG reference
```

Missing KCB previously received +5 in the historical scorer; that credit was removed. A bounded
or failed parse cannot earn a novelty increase from its missing comparator. The observed-state
condition also prevents a stale contradictory score from applying the high-KCB penalty.
The RiQ branch shown above remains conditional on an actually supplied numeric RiQ value.

### 4.5 RG-GMCI rescue bonus

```python
eligible(pair) = pair.functional_rescue_class != "ACCESSORY_ONLY"
high_rg = any(eligible HIGH pair)
mod_rg  = any(eligible MODERATE pair)
rescue_bonus = 0 if (primary_metab_flag or mobile_element_flag) else (8 if high_rg else 4 if mod_rg else 0)
```

Never applied to a primary-metabolism-flagged or mobile-element-flagged BGC. **It is routing priority, not claim confidence** (§7.4).

### 4.6 The edge penalty (neutralized, v9.7.84)

```python
def edge_penalty(...): return 0.0
```

**Removed on evidence, not on principle.** Mean base AB across the cohort: Interior 34.7 · Edge 35.7 · Full-contig 35.3. **There is no truncation signature in the base scores.** The penalty was burying overlooked edge fragments at the tier threshold while measuring nothing.

Truncation uncertainty is now carried as **architecture confidence** (Edge/FC → grade C/D) and as `edge_status` in the rationale — not as a score deduction. The corrected-count weights (1 / 0.5 / 0.25) are a *separate* mechanism and are unchanged.

The function is retained returning `0.0` so call sites stay intact for a future calibrated penalty.

### 4.7 Final assembly

```python
effective_penalty = max(0, edge_penalty - rescue_offset)      # == 0, since edge_penalty == 0

ab      = clamp(0, 100, base_ab      + rescue_bonus - 0.35 * effective_penalty)
af      = clamp(0, 100, base_af      + rescue_bonus - 0.35 * effective_penalty)
novelty = clamp(0, 100, base_novelty + rescue_bonus - 0.20 * effective_penalty)
```

The `0.35 / 0.20` multipliers are **dormant** (they multiply zero). They are retained for the same reason `edge_penalty` is.

---

## 5. Lead tier and confidence

### 5.1 Lead tier from the best axis

**Source:** `scoring.py:triage_bgcs`

```python
best = max(ab, af, novelty)

best >= 85  ->  Exceptional
best >= 70  ->  High
best >= 50  ->  Medium
else        ->  bottom_tier(bgc)  # Inventory for housekeeping-only/unresolved; Low otherwise
```

**The tier is about where to spend lab effort. It is never a confidence statement.** Raising a lead's tier does not raise its claim ceiling.

### 5.2 Architecture confidence A–E

**Source:** `parsers.py:architecture_grade`

```python
has_core = any(t in products for t in
    {nrps, pks, ripp, lanthipeptide, terpene, saccharide, phosphonate,
     siderophore, metallophore, lassopeptide, thioamide, tomm, azole})

A  ⇐  Interior AND has_core AND span >= 10 kb
B  ⇐  Interior AND NOT has_core AND kcb_cumulative >= 10_000
A  ⇐  Interior AND has_core AND has_chemical_hybrid AND distinct_core >= 2
B  ⇐  Interior AND has_core
C  ⇐  Edge     AND has_core
D  ⇐  (Edge AND NOT has_core) OR (Full-contig AND has_core)
E  ⇐  otherwise
```

Apply these branches in order (first match wins). `distinct_core` counts distinct terms in the core-class set above; `has_chemical_hybrid` is antiSMASH candidate-cluster `kind = chemical_hybrid`. Synthetic example: Interior, `nrps; t1pks`, 5,000 bp, chemical-hybrid flag true → A; without the flag → B. The hybrid branch never promotes Edge or Full-contig truncations. See [the technical reference](../reference/01_Math_Reference_VolI.md); this is structural grading, not compound or activity evidence.

Display: A→High · B→Moderate-High · C→Moderate · D→Low-Moderate · E→Low.

**Four confidence-like fields sit side by side on the triage board and answer four different questions.** They can disagree without contradiction:

| Column | Measures | Values |
|---|---|---|
| `Arch` | Structural completeness of the locus | A–E |
| `Arch_Capacity` | The claim-safe class **name** (not a confidence) | e.g. `glycopeptide` |
| `Class_Conf` | Confidence in *that class call* | HIGH / MODERATE / LOW |
| `claim_confidence` | Overall lead-claim confidence | HIGH / MODERATE / LOW |

`Arch = A, Class_Conf = LOW` is **coherent**: a structurally clean locus whose product class is still uncertain. (Through v9.7.27 `Class_Conf` was mislabelled `Arch_Conf`, which read as architecture-grade confidence, which it is not.)

**Two-level split-pathway rule.** For a reconstructed pathway, the *pathway unit* is graded C for structural interpretation, while the individual fragments retain their standalone grades (A/B for the anchor, D/E for secondaries). **Finding a second fragment is confirmatory, not penalising.**

### 5.3 RiQ recognition label

**Source:** `antismash_evidence.py:riq_label`

```python
riq >= 0.85  ->  "Likely known"
riq >= 0.50  ->  "Possibly novel / structural variant"
else         ->  "Potentially novel"
```

---

## 6. Floors, downgrades, and guards

The scoring model is deliberately generous at the base. The guards are what make it defensible. Read them as the substance of the model, not as exceptions to it.

### 6.1 Trigger corroboration — the gate before every bonus

**Source:** `source_scans.py:cctt_trigger_corroborated`

A CCTT trigger grants its bonus, its floor, and its guard-exemptions **only if corroborated**: it fired on a class-compatible locus.

```python
if trigger in CCTT_PROMISCUOUS: return True     # HAL, XHAL, NN — tailoring, biologically promiscuous
compat = CCTT_CLASS_COMPAT.get(trigger)
if not compat: return True                       # ungated trigger
return any(k in " ".join(products).lower() for k in compat)
```

An **uncorroborated** trigger is *recorded and preserved* for the judgment layer, but grants: no diagnostic bonus, no tier floor, no exemption from the primary-metabolism or mis-anchor guards. **Evidence is conserved; credit is not.**

### 6.2 The Tier-1 diagnostic floor

```python
if tier in ("Inventory", "Low") and tier1_floor:      # corroborated class trigger OR class-concordant T1 resistance
    tier = "Medium"; floored = True
```

Stops definitive chemistry evidence from being buried by a low keyword score. **The canonical case:** a KCB-dark nucleoside cluster with chitin context (CGAD-positive) — the nikkomycin/polyoxin-style antifungal a KCB-only scorer misses entirely.

The floor sets a **minimum**. It does not promote to High. Lone `T43-HAL` / `T43-XHAL` do not floor.

### 6.3 Primary-metabolism / pigment suppression

Fires when **all three** hold:
1. A housekeeping/pigment core-gene marker is in the BGC's own CDS
2. The BGC's own product classes are drawn **exclusively** from `WEAK_OVERCALL_CLASSES` = {nrps-like, terpene, terpene-precursor, saccharide, arylpolyene, other, t2pks, t3pks, pks-like, fatty_acid, redox-cofactor, quinone_isoprenoid_chain}
3. No Tier-1 diagnostic fired

Effect: `base_ab → 25`, `base_af → 20` (the floors). A committed backbone class (full NRPS/PKS/RiPP) exempts it. Coupling uses **flank = 0** — only genes *inside* the region count, because the false positive it guards against is a mis-called region, not a flanking neighbour.

### 6.4 Mobile-element / ICE demotion

```python
MOBILE_ELEMENT_CORE = {"integrase", "recombinase", "transposase"}
mobile_dominant = (core_hit and len(mobile_fams) >= 2) or (len(mobile_fams) >= 3)
```

A **lone flanking IS element is not dominant.** A mobile-dominant region with no corroborated Tier-1 trigger is capped at the AB/AF floors.

**T1 self-protection cargo guard (v9.7.37).** A T1 resistance tier on a mobile-dominant region **without class-concordant groups** is demoted to `t1_self_protection = False`. Otherwise an ICE's cargo resistance gene would float an impostor BGC to Medium.

### 6.5 KCB mis-anchor guards

Read the recorded class-specific mis-anchor flags. An unrelated Tier-1 trigger is not a
blanket exemption: the aminoglycoside clamp remains, and the polyene clamp has a separate
exception for corroborated non-polyene AF evidence. The enediyne branch is independent of
Tier-1 status.

| Guard | Test | Effect |
|---|---|---|
| Aminoglycoside | anchor present, **no DOIS/BtrC** in own CDS | AB → 25 |
| Polyene macrolide | anchor present, `ks_domain_count < 4` | AF → 20 |
| Enediyne | anchor present, **no `ene_KS`** | strip the +18 novelty; emit neutral `[E-signal]` |

The enediyne guard is where **PREV-001** lives: the `hglE`/`hglD` glycolipid ketosynthase cross-reacts with `ene_KS`. Verdict matrix: named enediyne + real `ene_KS` → `GENUINE_E_SIGNAL`; named + no `ene_KS` → `ENEDIYNE_MISANCHOR`; generic + hglE → `PREV001_ARTIFACT`; generic alone → `E_SIGNAL_UNRESOLVED`.

**The per-BGC BSL-2 flag is retired.** A selective biosafety flag on one compound class gives false reassurance about every other class. Handling is governed by lab SOPs; the engine emits a neutral note.

### 6.6 Standing-rule permanent exclusions

**Source:** `scoring.py:standing_rule_for`, reading `mamey/data/rules_registry.json` (SSOT)

The scorer selects registry rules with `action=downgrade` and `lead_blocking=True`; a
resulting standing flag sets `bottom_tier(bgc)` (Low or Inventory), preserves numeric scores
and excludes corrected lead rank. NAPAA is neutral and is not in that selected subset.

The hglE own-product fallback is separate: without an existing standing rule or any raw CCTT
trigger, it can still synthesize an hglE standing label despite the informational/nonblocking
registry entry. Inspect actual labels and source products instead of transferring a historical
habitat or novelty claim. See [the current standing-rule scope](../reference/06_CURRENT_SOURCE_SCOPE.md#volume-i-section-66-standing-rule-selection-scope-and-policy-conflict).

### 6.7 RiPP-fragment completeness floor

```python
RIPP_FRAGMENT_MAX_KB = 8.0

if class in RIPP_FAMILY_CLASSES and edge_status in {Edge, Full-contig} \
   and 0 < span_kb < 8.0 and tier in {Exceptional, High, Medium}:
       tier = bottom_tier(bgc); ripp_floored = True  # specialized RiPP normally becomes Low
```

A truncated sub-8 kb RiPP fragment with no precursor captured cannot be evaluated as a product. A lone LanM synthetase on a tiny contig must not float to High.

### 6.8 Corrected lead rank

`corrected_rank` is assigned sequentially over rows **not** carrying `standing_rule_flag`, `primary_metabolism_flag`, or `mobile_element_flag`. Downgraded rows keep their raw scores and receive `corrected_rank = None` — **visible, but not occupying a lead position.**

---

## 7. RG-GMCI — reconstructing fragmented clusters

**Source:** `rggmci.py`

Homology-guided linkage proposing that two BGC fragments on different contigs are one split pathway, because they map to the same reference producer cluster.

> **It does not join contigs at the nucleotide level.** It raises a linkage hypothesis. Physical confirmation requires long-read resequencing or PCR across the contig boundary.

All weights below are **engineering judgment, not calibration against a labelled set.** They are stated so they can be argued with.

### 7.1 The pairwise score

```
reference adjacency        +8  overlapping
                           +7  adjacent / nearby
                           +3  distant (caution)
                           +2  shared reference, no interval
                           +1  otherwise

protein support            +3  if min(a.nprot, b.nprot) >= 3   else +1
                           +2  additional, if total nprot >= 12

reference rank quality     +3  if both ranks <= 5
                           +1  if both ranks <= 10

identity                   +2  if min(mean_identity) >= 65%
                           +1  if >= 50%

token overlap              + min(3, shared reference-type tokens)
                           + min(2, shared product tokens)

fragmentation / topology   +2  if either fragment is non-Interior
                           +1  if on different contigs
```

### 7.2 Tiers and the gate cascade

```
score >= 14  ->  HIGH_RG_GMCI_RESCUE
score >=  9  ->  MODERATE_RG_GMCI_CANDIDATE
else         ->  LOW_SHARED_REFERENCE_SIGNAL
```

Precision gates, applied after scoring:

- **P-2 class compatibility** — the fragments must share a compatible class
- **R1** — demote if both drop class after exclusions
- **R2** — demote if neither fragment has a strong reference
- **R3** — demote on noise-class signal on both sides
- **Hub-degree guard** — a fragment linked to **more than 4** partners is *promiscuous*; HIGH links beyond degree 4 are demoted to `MODERATE_DEMOTED_HUB_PROMISCUITY`

### 7.3 Subject-tiling verdict (genuineness)

Reads which genes of the shared reference each fragment hits:

| Verdict | Meaning |
|---|---|
| `COMPLEMENTARY_SPLIT` | Aggregated tiling/count/geometry conditions support a candidate split interpretation |
| `TERMINUS_TRUNCATION_SPLIT` | Terminus/geometry evidence changed or corroborated the engine label; inspect the override |
| `OVERLAPPING_PARALOG` | Overlapping subject support triggers the engine category and demotes HIGH/MODERATE confidence |
| `MIXED_SUBJECT_SIGNAL` | ambiguous; manual review |
| `INSUFFICIENT_SUBJECT_DATA` | no tiling data |

`TERMINUS_TRUNCATION_SPLIT` **overrides** an `OVERLAPPING_PARALOG` verdict that rests on a gene class which is legitimately multi-copy *within one* cluster (e.g. the bottromycin RRE/methyltransferase). The paralog call is preserved for genuine paralogs.

### 7.4 Effect on scoring

`HIGH → +8`, `MODERATE → +4`, added to all three axes. Never applied to primary-metabolism or mobile-element flagged BGCs.

**The bonus is routing priority, not claim confidence.** A rescued pair is a lead to chase, not a proven join.

---

## 8. The completeness invariant

**Source:** `scoring.py:scoring_coverage`, `scoring.py:assert_full_scoring_coverage` (v9.7.20)

**Every BGC is scored on AB/AF/novelty — not just lead-tier ones.** `triage_bgcs` loops the full list; Edge, Full-contig, and small-contig fragments are all included, none skipped.

```
coverage = (#BGCs with ab, af, novelty all populated) / (#BGCs total)
```

`assert_full_scoring_coverage` **raises** on any unscored BGC.

The helper checks score-field presence for the supplied object roster. Its default raises,
but the native gold writer uses `raise_on_fail=False`, records warnings/errors and can continue
to export. It does not reread the saved workbook/CSV, validate finite numeric scores or detect
later merge loss. Check the serialized output separately. The earlier ~9% cohort example is a
historical report, not a current measurement.

---

## 9. Multibatch trigger

**Source:** `scoring.py:needs_multibatch`

```
needs_multibatch  =  raw > 25
                  ∨  (edge + full_contig) > 15
                  ∨  a fragmented-cluster rescue review was triggered
```

A true result recommends batching; the helper does not partition rows, dispatch judgment work or establish that later batches ran.

---

## 10. Constants quick-reference

*Re-verified against the running modules at bundle v9.7.250 / engine 1.9.110.*

| Constant | Value | Source | Role |
|---|---|---|---|
| Edge flank | 5,000 bp | `parsers.py:_edge_status` | Edge boundary tolerance |
| Full-contig threshold | 0.95 · L | `parsers.py:_edge_status` | region ≥95% of contig |
| Corrected-count weights | 1 / 0.5 / 0.25 | `assembly.py:corrected_bgc_count` | Interior / Edge / FC |
| Assembly tiers | 70 / 45 / 20 | `assembly.py:assembly_tier` | GOOD / MOD / POOR / V_POOR |
| GC dispersion flag | ≥ 5.0 | `assembly.py:assembly_sanity_check` | contamination suspect |
| Score bases | 25 / 20 / 30 | `scoring.py:triage_bgcs` | AB / AF / novelty floor |
| Diagnostic bonus | 25 | `scoring.py` | corroborated CCTT trigger |
| KCB-strong novelty | −15 | `scoring.py` | `kcb_cumulative > 10000` |
| Missing/unknown KCB novelty | 0 | `scoring.py` | unavailable comparator adds no novelty credit; explicit UNKNOWN also suppresses the high-KCB penalty |
| Low-RiQ novelty | +10 | `scoring.py` | `riq_score < 0.5` |
| Rescue bonus | 8 / 4 | `scoring.py` | HIGH / MODERATE RG-GMCI |
| Edge penalty | **0.0** | `scoring.py:edge_penalty` | neutralized v9.7.84 |
| Penalty multipliers | 0.35 / 0.20 | `scoring.py:triage_bgcs` | AB·AF / novelty (dormant) |
| Lead tiers | 85 / 70 / 50 | `scoring.py:triage_bgcs` | Exceptional / High / Medium |
| Architecture grade | 10 kb, KCB 10,000 | `parsers.py:architecture_grade` | A–E thresholds |
| RiQ labels | 0.85 / 0.50 | `antismash_evidence.py:riq_label` | known / variant / novel |
| RiPP-fragment floor | 8.0 kb | `scoring.py` | truncated RiPP cap |
| RG-GMCI tiers | 14 / 9 | `rggmci.py` | HIGH / MODERATE |
| Hub-degree max | 4 | `rggmci.py` | promiscuity demotion |
| Multibatch | 25 / 15 | `scoring.py:needs_multibatch` | raw / edge+FC |
| Backbone min | 45.0 kb | `dedup_and_guard.py:BACKBONE_MIN_KB` | fragment claim ceiling |

---

## 11. Where Volume I ends and Volume II begins

| Question | Volume |
|---|---|
| How many BGCs does this genome have? | **I** §1–§2 |
| How good is this assembly, and what may it claim? | **I** §3 |
| Why does this BGC score 62 on the AB axis? | **I** §4 |
| Why was it capped at Inventory despite scoring 71? | **I** §6 |
| Are these two fragments one cluster? | **I** §7 |
| Which CCTT trigger fired, and was it corroborated? | **II** Part A |
| What class is this, ignoring the KCB hit? | **II** Part B |
| Where did `kcb_cumulative` come from? | **II** Part C |
| Why is this chemotype worth +22 on AF? | **II** Part D |
| Is this rescue pair complementary or paralogous? | **II** Part E |
| Why does §11–§20 need 2,000 characters? | **II** Part G |
| Which locator does this BGC cite? | **II** Part G |

---

## 12. Drift notice

The Vol I source was compiled at **engine v1.9.98 / bundle v9.7.119** (2026-06-23). Every constant in §10 was re-read from the running modules at **v9.7.250 / engine 1.9.110** during this compilation and **all agree**.

This is not true of every reference document. `mode_b_quality_gate.py`'s floors have drifted materially from the Vol II source's account of them (Vol II Part G.4.6). **A constants table in a reference document is a claim, and claims rot.** Verify against the module before citing a number in a manuscript.

---

*Volume I compiled 2026-07-09 · sourced from `docs/reference/01_Math_Reference_VolI.md` (engine v1.9.98) · every constant re-verified against the running modules at bundle v9.7.250 / engine 1.9.110*

*Scores are routing priors, not biological proof. KCB is similarity, not identity. Capacity-level language is mandatory downstream.*
