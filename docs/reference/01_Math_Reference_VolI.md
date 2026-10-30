# The Mathematics of Sapote-Mamey

## Using current source behavior

Start with the saved value you want to explain: [counts](#2-the-corrected-bgc-count),
[AB/AF/novelty scores](#4-the-three-routing-scores-ab-af-novelty),
[a tier or guard](#6-floors-downgrades-and-guards), or
[a candidate fragment link](#7-rg-gmci-reconstructing-fragmented-clusters).
Read the matching section beside the package's source row and issue records.

Use [current source scope](06_CURRENT_SOURCE_SCOPE.md) to interpret counts, tiers and raw pair scores.
Check scoring guards, calibration and scientific interpretation separately. The discounted count is
round(Interior +0.5 Edge +0.25 Full-contig,2), and assembly tiers use 70/45/20 with unknown when missing
(`mamey/assembly.py`). These are weighted diagnostics and routing labels, not a physically reconciled
cluster census or calibrated probability that a count is trustworthy. Preserve raw counts and exact scope.

The original §6.6 three-permanent-downgrades statement is superseded by the actual current registry:
NAPAA is neutral/action-none/nonblocking; HGLE-KS-PREV-001 is noted/flag/informational/nonblocking;
saccharide is excluded/downgrade for lead prioritization. Those are registry states (`mamey/data/rules_registry.json`), not a complete
description of downstream scoring. The scorer retains a direct hglE own-product fallback: absent another
standing rule, an `hgle-ks`/`hgle` product with no CCTT trigger acquires an hglE standing label and
class-gated bottom tier (`scoring.py`), excluding its corrected lead rank. NAPAA has no matching
retired fallback. Preserve actual labels, trigger state and per-consumer behavior rather than inferring
universal inclusion from registry nonblocking status. Scoring's retired branch comments
are not stronger authority than the loaded registry. This is a registry/scoring boundary, not a universal
claim about every downstream consumer: `compile_report.py` still filters a row
carrying a NAPAA standing label. Preserve the selected artifact's actual row/standing state and flag
that conditional consumer divergence; do not assume every compiled report follows the neutral registry. No low/no KCB match or preserved novelty-score field
establishes scientific novelty, compound identity, production or activity.

Selected §7.1 component weights and 14/9 raw thresholds agree with `_pair_score`
(`mamey/rggmci.py`), but final aggregation and gate cascade may change the saved confidence;
raw score is not the final verdict or nucleotide joining proof. Coordinate and LOCUS_PROXY adjacency carry
different units. Preserve full strain/node-or-contig/region/BGC identity, exact denominators, current profile,
source paths/hashes and actual receipts. Verify actual pair results and source provenance before drawing biological conclusions.



### Counting, scoring, and reconstruction formulae in the deterministic extraction engine

**Version of record:** Mamey engine v1.9.177 · bundle v9.7.461
**Author:** Alexander J. Smith
**Status:** Source-cited methods reference with historical compilation notes and scoped corrections. A module citation locates an explanation; current behavior still needs the selected source and input state.

---

## 0. How to read this document

Mamey is the deterministic half of the pipeline. It parses antiSMASH output and computes a fixed set of numbers — BGC counts, assembly tiers, three routing scores per cluster, reconstruction-confidence scores for fragmented clusters, and a battery of guard flags. Sapote, the LLM judgment layer, consumes those numbers; it never recomputes them. This document covers the Mamey math only.

Two principles govern every number here and should be read into all of them:

1. **The scores are routing priors, not biological proof.** AB/AF/novelty values order BGCs for human and judgment-layer attention. They are explicitly *not* WL/DAPR scores and must never be cited as evidence that a strain produces a compound. The claim-safe vocabulary ("biosynthetic capacity consistent with…") is mandatory downstream of every number in this document.

2. **KCB is similarity, not identity.** Every appearance of a known-cluster-blast (KCB) signal below is a sequence-similarity measure against a reference. It informs novelty and display; it never confirms a product.

Each section gives the formula, the constants as they appear in code, the rationale, and the source location (`module.py:symbol`).

---

## 1. BGC boundary classification

Everything counting-related rests on one upstream decision: is a detected region **Interior**, **Edge**, or **Full-contig**? This is the *edge status*, and it is computed from coordinates alone, before any scoring.

**Source:** `parsers.py:_edge_status`

Let a region span absolute source-record coordinates `[start, end]` on a contig of length `L`, with a flank tolerance `f = 5000 bp`. Define the region length:

```
length = end − start + 1
```

The classification:

```
if L ≤ 0:                            edge_status = Unknown
elif length ≥ 0.95 · L:              edge_status = Full-contig
elif contig is circular:             edge_status = Interior
elif start ≤ f  or  (L − end) ≤ f:   edge_status = Edge
else:                                edge_status = Interior
```

Three points of nuance carried in the code.

- **The 0.95 rule.** A region occupying ≥95% of its contig is "Full-contig" — the cluster *is* essentially the whole contig, so both ends are presumed truncated and linkage is unknown.
- **Circular-replicon correction (v9.7.87, P0-a).** On a closed/circular chromosome the origin is not a truncation point — a BGC adjacent to the origin wraps around, it is not truncated. So Edge is only assigned near a contig boundary when topology is linear or unknown. Without this, closed genomes produced false Edge calls at the origin and the corrected count fell below the raw count (a parsing-control failure; e.g. *Nocardia nova* NZ_CP006850).
- **Absolute coordinates.** antiSMASH region GBKs are clipped records whose feature coordinates restart at 1. Edge classification must use the absolute `Orig. start`/`Orig. end` from the record comment plus the true contig length, or a closed chromosome with many clipped region GBKs is falsely labelled Edge/Full-contig (`parsers.py:_region_orig_bounds_from_zip`).

---

## 2. The corrected BGC count

The headline count a strain reports is not the raw number of antiSMASH regions. Edge and Full-contig regions are fractionally discounted, because a truncated cluster is partial evidence of a biosynthetic capacity, not whole evidence.

**Source:** `assembly.py:corrected_bgc_count`

Let `I`, `E`, `F` be the counts of Interior, Edge, and Full-contig regions. Then:

```
corrected = round( I + 0.5·E + 0.25·F , 2 )
```

The weights are fixed contributions to a boundary-based statistic: Interior contributes 1.0,
Edge 0.5 and Full-contig 0.25. They do not measure the fraction of a locus recovered.
`bgc_count_summary` reports raw as the number of supplied BGC records, including records with
Unknown boundary; only the I/E/F groups contribute to the weighted statistic. Retain raw,
Unknown and I/E/F counts together rather than treating an unclassified boundary as absence.

**Worked example.** A strain with 12 Interior, 6 Edge, and 4 Full-contig regions:

```
raw       = 12 + 6 + 4              = 22
corrected = 12 + 0.5·6 + 0.25·4     = 12 + 3 + 1 = 16.00
```

A parsing-control invariant follows directly: because every weight is ≤ 1, **corrected ≤ raw** always. With a shared nonnegative I/E/F denominator, a result above raw signals inconsistent counts/inputs or arithmetic; changing boundary labels alone cannot violate the inequality. The circular-replicon correction in §1 addresses a different failure: false Edge/Full-contig labels can depress the discounted count while the inequality still holds.

---

## 3. Assembly quality tier

The corrected count is only interpretable against assembly quality: a low count on a fragmented draft means something different than a low count on a closed genome. The tier is computed from the **interior fraction** — the share of regions that are Interior.

**Source:** `assembly.py:assembly_tier`, `scoring.py:bgc_count_summary`

```
interior_pct = round( I / raw · 100 , 1 )          (None if raw = 0)
```

The tier:

```
interior_pct ≥ 70   →  GOOD
interior_pct ≥ 45   →  MODERATE
interior_pct ≥ 20   →  POOR
interior_pct <  20   →  VERY_POOR
None                →  UNKNOWN
```

These thresholds label the supplied region-boundary distribution. They are not calibrated
trustworthiness probabilities or biological lower-bound guarantees. Read contig count/N50 and
the separate contiguity classification alongside them; a high Interior fraction does not by
itself establish a complete genome or a reconciled pathway census.

### 3.1 Supporting assembly statistics

**N50** (`assembly.py:n50`) — the length-weighted median contig size. Sort contig lengths descending; accumulate; return the length at which the running total first reaches half the assembly.

```
N50 = the contig length L* such that Σ(lengths ≥ L*) ≥ total/2
```

**GC fraction** (`assembly.py:gc_pct_from_sequences`):

```
GC% = round( (#G + #C) / (#A + #C + #G + #T) · 100 , 3 )
```

### 3.2 Non-blocking contamination / sanity heuristic

**Source:** `assembly.py:assembly_sanity_check` (v9.7.101, PC-A2)

Two VERY_POOR drafts once passed as complete despite clear pathology (bimodal GC, megabases of foreign content). This check flags — but never blocks — suspicious assemblies. It computes a **length-weighted per-contig GC standard deviation**:

```
mean = Σ(gᵢ·wᵢ) / Σwᵢ
var  = Σ(wᵢ·(gᵢ − mean)²) / Σwᵢ
gc_sd = √var
```

where `gᵢ` is contig *i*'s GC% and `wᵢ` its length. Flags fire as:

- `gc_sd ≥ 5.0` → **CONTAMINATION_SUSPECT** (clean genomes run ~1–2%; the contaminated drafts ran 7–12%).
- `|overall_GC − expected_GC| ≥ 8.0` → **ASSEMBLY_SANITY** (only if a taxon GC prior is supplied).
- genome size outside an expected `[lo, hi]` range → **ASSEMBLY_SANITY** (only if a size prior is supplied).

GC dispersion is evaluated only with at least two contigs carrying valid GC measurements;
otherwise `per_contig_gc_sd` is None. The current default size checks also need no taxon prior:
positive total size below 3,000,000 bp or above 12,000,000 bp raises a suspect flag, and a
below-floor input with at most five contigs gets a partial-submission flag. Caller overrides can
change or disable those bounds. These are non-blocking heuristics; inspect the recorded inputs
and flags rather than reading a missing dispersion value as a clean result.

---

## 4. The three routing scores: AB, AF, novelty

Each BGC receives three scores on a 0–100 scale: **AB** (antibacterial routing prior), **AF** (antifungal routing prior), and **novelty**. They sort clusters for the judgment layer. The full computation lives in `scoring.py:triage_bgcs`; the constants are module-level in `scoring.py`.

### 4.1 The base + keyword model

Each axis starts from a base and adds class-keyword weights:

```
base_AB      = 25 + score_keywords(class_text, AB_KEYWORDS)
base_AF      = 20 + score_keywords(class_text, AF_KEYWORDS)
base_novelty = 30 + score_keywords(class_text, NOVELTY_KEYWORDS)
```

The bases (25, 20, 30) are the floor any non-excluded BGC carries before class evidence. The **keyword tables** as they appear in code:

**AB_KEYWORDS** — classes enriched for antibacterial leads:

| class | wt | class | wt | class | wt |
|---|---|---|---|---|---|
| carbapenem | 18 | phosphonate | 15 | thioamide | 14 |
| thiopeptide | 14 | thiazolylpeptide | 14 | hr-t2pks | 14 |
| transat-pks | 14 | aminoglycoside | 14 | nrps | 12 |
| t2pks | 12 | lanthipeptide | 12 | t1pks | 10 |
| lassopeptide | 10 | phenazine | 10 | saccharide | 8 |
| halogenated | 8 | ripp | 8 | azole | 8 |

**AF_KEYWORDS** — classes with antifungal-search relevance:

| class | wt | class | wt | class | wt |
|---|---|---|---|---|---|
| hsaf | 20 | nystatin | 20 | nikkomycin | 20 |
| polyoxin | 20 | polyene | 18 | candicidin | 18 |
| nucleoside | 18 | tetramate | 16 | sgr ptm | 14 |
| chitin | 12 | ptm | 12 | t1pks | 10 |
| transat-pks | 12 | nrps | 8 | terpene | 6 |
| siderophore | 4 | metallophore | 4 | | |

**NOVELTY_KEYWORDS** — rare/fragile/cryptic classes that must not be buried in fragmented assemblies:

| class | wt | class | wt | class | wt |
|---|---|---|---|---|---|
| transat-pks | 18 | enediyne | 18 | azoxy | 18 |
| thioamide | 15 | phosphonate | 15 | hgle | 12 |
| ranthipeptide | 12 | ripp | 10 | nrps | 8 |
| t1pks | 8 | t2pks | 8 | | |

These weights are routing priors set by workflow judgment (Mamey v1.1/v1.2), not calibrated against a labelled set. Reviewers may tune them, but changes must be changelogged because batch ordering depends on them.

### 4.2 Delimited-word matching and subsumption

**Source:** `scoring.py:score_keywords`, `scoring.py:_key_present`

A class keyword scores **once**, at its most specific weight, and only on a delimiter-bounded token match — never a glued substring. The membership test:

```
_key_present(key, text)  =  regex (?<![a-z0-9]) key (?![a-z0-9]) matches text
```

This is the project's recurring **substring-containment** guard applied to scoring. It keeps legitimate delimited subtypes (`t2pks` inside `hr-t2pks`, `azole` inside `azole-containing-ripp`, `siderophore` inside `ni-siderophore`) while rejecting glued false matches — the canonical one being `polyene` inside `arylpolyene`, which previously scored a pigment as an antifungal.

**Subsumption.** A specific subclass suppresses the generic it implies, so weight is not double-counted:

```
SUBCLASS_SUBSUMES = { hr-t2pks → t2pks,  transat-pks → t1pks }
```

If both the subtype and its generic match, only the subtype's weight is banked. **Pigment classes** (`arylpolyene`, `ladderane`) are excluded from scoring entirely.

The scorer also sees only the BGC's **own** class evidence — its `products`, `mibig_hits`, and a *resolved* MIBiG product line — never the raw `kcb_top` genome-description blob (`scoring.py:scoring_class_text`, P-7 fix). A genome self-hit's free-text description carries the *reference organism's* unrelated class tokens; folding those in once inflated a bare `saccharide` cluster by +34 AB from `nrps`/`t1pks`/`t2pks` that were not its own.

### 4.3 The diagnostic-marker bonus

**Source:** `scoring.py` (`DIAGNOSTIC_BONUS`, `AF_DIAGNOSTIC_TRIGGERS`, `AB_DIAGNOSTIC_TRIGGERS`)

A CCTT/cassette trigger that *proves* a bioactivity class — even when the product label and KCB anchor carry no matching word — adds a flat bonus.

```
DIAGNOSTIC_BONUS = 25
if a corroborated AF trigger fired:  base_AF += 25
if a corroborated AB trigger fired:  base_AB += 25
```

- **AF triggers:** `T43-NUC` (nucleoside chitin-synthase inhibitors), `T43-PTM` (HSAF/PTM macrolactams), `T43-PYE` (polyene macrolide antifungals; v1.9.99).
- **AB triggers:** `T43-LAN`, `T43-LASSO`, `T43-THA`, `T43-PHO`, `T43-AMC`, `T43-BLA`, `T43-GPA` (glycopeptide; v1.9.99), `T43-BLT` (betalactone; v1.9.99).

This fixes the failure mode where a KCB-dark cluster labelled only "nucleoside; other" but carrying the NikJ diagnostic is a definitive antifungal whose evidence was computed and then dropped before it reached the tier gate. Only **corroborated** triggers grant the bonus — see §6.1.

### 4.4 KCB and RiQ novelty adjustments

**Source:** `scoring.py:triage_bgcs`

After the keyword base, novelty is adjusted by reference-similarity and recognition signals:

```
if kcb_evidence_state != UNKNOWN_KCB and kcb_cumulative is not None and kcb_cumulative > 10000:
    novelty −= 15       # observed strong comparator signal
# Missing/unknown KCB adds no credit; explicit UNKNOWN also suppresses the penalty above.
if riq_score is not None and riq_score < 0.5:
    novelty += 10       # supplied low-recognition metric; not proof of novelty
```

`kcb_cumulative` is the summed knownclusterblast hit strength; `riq_score` is antiSMASH's region-to-region RiQ ratio (0–1).

### 4.5 The RG-GMCI rescue bonus

A BGC linked to other fragments by reconstruction evidence (§7) gets a routing-priority bonus — never a confidence bonus:

```
rescue_bonus = 8   if a HIGH_RG_GMCI_RESCUE link supports the BGC
             = 4   if a MODERATE_RG_GMCI_CANDIDATE link supports it
             = 0   otherwise  (and 0 for any primary-metab/pigment-flagged region)
```

### 4.6 The edge penalty (neutralized)

**Source:** `scoring.py:edge_penalty` (v9.7.84)

```
edge_penalty(edge_status) = 0.0    (for all statuses)
```

The boundary penalty is **deliberately zero**. Empirically (AS cohort + the selvamicin control), Edge/FC clusters show no truncation signature in their base score. Mean base AB was Interior 34.7 vs Edge 35.7 vs FC 35.3. So the former penalty was a flat pessimism prior with no measurement basis. At the Medium threshold it was decisive, flipping 83% of near-threshold Edge/FC leads to Inventory and burying exactly the overlooked fragments the tool exists to surface (selvamicin BGC0001773, a Full-contig attine antifungal polyene, sank partly on this penalty). Truncation uncertainty is now carried as a **confidence** signal via architecture grade (§5) and the edge-status field, not as a score deduction. The function is retained returning 0 so the multipliers below stay wired for a future calibrated penalty from one place.

### 4.7 Final score assembly

**Source:** `scoring.py:triage_bgcs`

With `penalty = edge_penalty(...) = 0` and the RG-GMCI reduction folded in:

```
effective_penalty = max(0, penalty − (8 if high_rg else 4 if mod_rg else 0))

AB      = clamp₀,₁₀₀( base_AB      + rescue_bonus − 0.35·effective_penalty )
AF      = clamp₀,₁₀₀( base_AF      + rescue_bonus − 0.35·effective_penalty )
novelty = clamp₀,₁₀₀( base_novelty + rescue_bonus − 0.20·effective_penalty )
```

where `clamp₀,₁₀₀(x) = max(0, min(100, x))`. The 0.35 / 0.20 multipliers are the (currently dormant) penalty couplings, retained for a future calibrated penalty. Each final score is rounded to one decimal.

---

## 5. Lead tier and architecture confidence

Two independent gradings sit on top of the scores: the **lead tier** (priority) and the **architecture confidence** (structural reliability). They answer different questions and must not be conflated.

### 5.1 Lead tier from the best axis

**Source:** `scoring.py:triage_bgcs`

```
best = max(AB, AF, novelty)

best ≥ 85   →  Exceptional
best ≥ 70   →  High
best ≥ 50   →  Medium
best <  50   →  bottom_tier(bgc)  # Inventory for housekeeping-only/unresolved; Low otherwise
```

The tier is then subject to floors and downgrades (§6).

### 5.2 Architecture confidence A–E

**Source:** `parsers.py:architecture_grade`

A *structural reliability* grade — how completely the cluster is captured — derived from edge status, whether a core biosynthetic class is present, length, KCB support, and antiSMASH's chemical-hybrid flag. Let `has_core` be true if the product text contains any of {nrps, pks, ripp, lanthipeptide, terpene, saccharide, phosphonate, siderophore, metallophore, lassopeptide, thioamide, tomm, azole}; `distinct_core` the number of those terms present; `high_kcb = (kcb_score ≥ 10000)`; and `hybrid_coherent = has_chemical_hybrid ∧ distinct_core ≥ 2`, where `has_chemical_hybrid` means antiSMASH flagged the region's candidate cluster `kind = chemical_hybrid`. Rules are applied in this order; the first that matches wins:

```
Interior ∧ has_core ∧ length ≥ 10 kb         →  A   (coherent, complete)
Interior ∧ high_kcb ∧ ¬has_core              →  B   (KCB-supported, limited core annotation)
Interior ∧ has_core ∧ hybrid_coherent        →  A   (compact but coherent: fused multi-class architecture)
Interior ∧ has_core                          →  B   (limited/compact)
Edge ∧ has_core                              →  C   (truncated but coherent; partial)
Edge ∧ ¬has_core                             →  D   (truncated, limited annotation)
Full-contig ∧ has_core                       →  D   (likely truncated both ends)
otherwise                                    →  E   (weak/ambiguous; inventory-level)
```

The hybrid promotion only lifts a compact Interior core region from B to A. It never promotes a truncation grade (C, D or E): the hybrid flag says nothing about edge or length truncation. Example: Interior, products `nrps; t1pks`, 5,000 bp, chemical-hybrid flag set → A (without the flag, B). The grade is structural reliability, not production, novelty or activity. Section reviewed against `parsers.py:architecture_grade` in v9.7.447.

The judgment-layer display maps A–E to words: A→High, B→Moderate-High, C→Moderate, D→Low-Moderate, E→Low (`scoring.py:triage_bgcs`).

### 5.3 RiQ recognition label

**Source:** `antismash_evidence.py:riq_label`

The RiQ ratio is bucketed for display:

```
RiQ ≥ 0.85   →  "Likely known"
RiQ ≥ 0.50   →  "Possibly novel / structural variant"
RiQ <  0.50   →  "Potentially novel"
```

---

## 6. Floors, downgrades, and guards

Most of the engine's actual judgment is here: the logic that prevents a high keyword score from over-claiming, and prevents a real-but-dark lead from being buried. These apply *after* §4–§5 and modify the tier (and sometimes the scores). Source throughout: `scoring.py:triage_bgcs`.

### 6.1 Trigger corroboration (the gate before every bonus)

A CCTT class trigger only counts if it is **corroborated** — fired on a class-compatible locus. An uncorroborated trigger (e.g. `T43-PHO` on a T3PKS, or any gated trigger on a mobile-dominant region whose class-defining enzyme is absent and whose architecture-class confidence is LOW) is recorded for the judgment layer but grants **no** AB/AF bonus, **no** guard exemption, and **no** tier floor:

```
corroborated_triggers = triggers − uncorroborated
(only corroborated triggers feed §4.3, §6.2, and the guard exemptions)
```

This is the CCTT-veto discipline; it is what makes the diagnostic bonus trustworthy.

### 6.2 The Tier-1 diagnostic floor

A definitive class marker must not be buried by a low text/KCB score.

```
if (a corroborated class-defining trigger fired  OR  class-concordant T1 self-resistance)
   AND tier in {Inventory, Low}:
        tier ← Medium        (floored = true)
```

**Exclusion (v9.7.19):** a lone tailoring-enzyme marker — halogenase / fluorinase-chlorinase (`T43-HAL_*`, `T43-XHAL_*`) — is a *modification*, not a class call, and does **not** floor on its own (it accounted for ~half of all floored BGCs). A class-defining marker that co-occurs still floors; the tailoring marker remains a recorded signal.

### 6.3 Primary-metabolism / pigment suppression

**Source:** `scoring.py:triage_bgcs` (v9.7.7, P0)

Fires only when **all** of: (a) a housekeeping/pigment core-gene marker is in the BGC's own CDS; (b) the BGC's own product class is *exclusively* weak/over-call labels (`WEAK_OVERCALL_CLASSES` = {nrps-like, terpene, terpene-precursor, saccharide, arylpolyene, other, t2pks, t3pks, pks-like, fatty_acid, redox-cofactor, quinone_isoprenoid_chain}); and (c) no Tier-1 diagnostic fired. Effect:

```
base_AB ← min(base_AB, 25)        # strip keyword credit to the floor
base_AF ← min(base_AF, 20)
```

This de-ranks the topoisomerase-"NRPS-like" false antibacterial and the carotenoid-"terpene" false antifungal without touching real clusters — a committed class label or a CCTT diagnostic exempts the region.

### 6.4 Mobile-element / ICE demotion

**Source:** `scoring.py:triage_bgcs` (v9.7.33, #28)

A region dominated by mobility machinery (ICE/transposon) and mis-typed by antiSMASH as biosynthetic is not a biosynthesis lead.

```
if mobile_dominant AND no Tier-1 diagnostic:
        base_AB ← min(base_AB, 25)
        base_AF ← min(base_AF, 20)
```

A corroborated class signal exempts it, so genuine clusters with incidental flanking mobile genes are untouched. The companion resistance-axis rule (v9.7.37, PC-12): a T1 self-protection tier on a mobile-dominant region is only genuine self-resistance if the resistance is *class-concordant* with the cluster's own product. A non-concordant resistance group on an ICE background is horizontally-acquired cargo, not self-protection, and does not establish a Tier-1 diagnostic.

### 6.5 KCB mis-anchor guards

**Source:** `scoring.py:triage_bgcs` (v9.7.15)

The recorded mis-anchor flags constrain comparator-derived credit. An aminoglycoside
mis-anchor clamps AB regardless of an unrelated Tier-1 trigger. A polyene mis-anchor clamps
AF unless a corroborated non-polyene AF diagnostic supplies independent credit; inspect the
rationale to see that exception. An unrelated Tier-1 marker is not a blanket exemption.

```
aminoglycoside anchor, no DOIS/2-deoxy-scyllo-inosose:   base_AB ← min(base_AB, 25)
polyene anchor, < 4 PKS-KS domains:                      base_AF ← min(base_AF, 20)
```

**Enediyne guard (§4.3, independent of tier):** a PREV-001/hglE artifact loses its +18 enediyne novelty credit. A genuine named-enediyne KCB anchor carries a neutral `[E-signal]` note — similarity, structure not confirmed — and *no* BSL-2/lab-safety warning (the enediyne BSL-2 doctrine was retired; selective biosafety flags give false reassurance, and chemical handling is governed by lab SOPs).

```
if enediyne mis-anchor:   novelty −= 18
```

A class-level KCB mismatch (compound family incompatible with own product class) is flagged for the judgment layer regardless of tier.

### 6.6 Standing-rule permanent exclusions

**Source:** `scoring.py:_downgrade_rules`, `standing_rule_for`, `triage_bgcs`;
`mamey/data/rules_registry.json`.

Read the row's actual standing label and own-product text. The scorer selects registry rules
with `action=downgrade` and `lead_blocking=True`, then applies their match/committed-class
policy. NAPAA is neutral and is not in that selected subset. The current selected rules include
SACCHARIDE, NI-SIDEROPHORE and NRP-METALLOPHORE.

The separate hglE own-product fallback can still create `hglE-KS-PREV-001` when no standing
rule exists and no raw CCTT trigger is present, despite the registry's informational/nonblocking
state. Keep that implementation/policy discrepancy visible.

A resulting standing label sets `tier = bottom_tier(bgc)` (Low or Inventory by class policy),
clears the generic floor flag and excludes corrected lead rank, while preserving the numeric
axes. It does not certify a product, habitat-specificity or novelty claim. For the detailed
consumer boundary, use [current standing-rule scope](06_CURRENT_SOURCE_SCOPE.md#volume-i-section-66-standing-rule-selection-scope-and-policy-conflict).

### 6.7 RiPP-fragment completeness floor

**Source:** `scoring.py:triage_bgcs` (F2)

A RiPP-family cluster (`RIPP_FAMILY_CLASSES`) that is a truncated sub-8 kb fragment with no precursor captured cannot be evaluated as a product:

```
if RiPP-family AND edge_status ∈ {Edge, Full-contig}
   AND 0 < span_kb < 8.0 AND tier ∈ {Exceptional, High, Medium}:
        tier ← bottom_tier(bgc)  (ripp_floored = true; specialized RiPP normally Low)
```

`span_kb = (end − start)/1000`, falling back to contig length. Never touches Interior clusters. Size + edge are conservative precursor proxies; a lone LanM synthetase beside a gas-vesicle operon should not float above a complete cluster.

### 6.8 Corrected lead rank

**Source:** `scoring.py:triage_bgcs`

After all scoring, records are sorted by `max(AB, AF, novelty)` descending. The **corrected rank** is a sequential lead rank assigned only to rows that are **not** standing-rule-downgraded, **not** primary-metabolism/pigment-flagged, and **not** mobile-element-flagged. Downgraded rows keep their raw scores but receive `corrected_rank = None` — they are visible but out of the lead order.

---

## 7. RG-GMCI: reconstructing fragmented clusters

RG-GMCI (**Reference-Guided Genome Mining Candidate Inference**) evaluates shared-reference
support for candidate relationships between fragmented regions. Read the raw score, saved
effective confidence, subject-tiling label and gate reasons together. These are computational
categories supporting a linkage hypothesis, not proof that the regions form one physical
pathway or an asserted nucleotide-level join. Retain both complete endpoint identities from
their bound records.

### 7.1 The pairwise score

**Source:** `rggmci.py:_pair_score`

For two ClusterBlast references `a`, `b` (one per BGC fragment), the additive score:

```
score = 0

# adjacency on the shared reference
+ 8   if OVERLAPPING_REFERENCE_SEGMENTS
+ 7   if ADJACENT_OR_NEARBY_REFERENCE_SEGMENTS
+ 3   if DISTANT_ON_REFERENCE_CAUTION
+ 2   if SHARED_REFERENCE_NO_INTERVAL
+ 1   otherwise

# protein support
+ 3   if min(a.nprot, b.nprot) ≥ 3   else +1     (when both have protein counts)
+ 2   if (a.nprot + b.nprot) ≥ 12

# reference rank quality
+ 3   if a.rank ≤ 5  and b.rank ≤ 5
+ 1   elif a.rank ≤ 10 and b.rank ≤ 10

# identity
+ 2   if min(a.mean_identity, b.mean_identity) ≥ 65
+ 1   elif ≥ 50

# token overlap
+ min(3, |shared reference-type tokens|)
+ min(2, |shared product tokens|)

# fragmentation / topology
+ 2   if either fragment is not Interior
+ 1   if the two fragments are on different contigs
```

The confidence tier from the raw score:

```
score ≥ 14   →  HIGH_RG_GMCI_RESCUE
score ≥  9   →  MODERATE_RG_GMCI_CANDIDATE
otherwise   →  LOW_SHARED_REFERENCE_SIGNAL
```

(`RGGMCI_SCORE_HIGH = 14`, `RGGMCI_SCORE_MODERATE = 9`). These component weights are engineering judgment, not calibrated against a labelled set — precision is enforced by the downstream gate cascade below, not by the weights. The raw score is a coarse routing prior.

### 7.2 The gate cascade (precision enforcement)

A HIGH score is necessary but not sufficient. Several gates can **demote** HIGH → MODERATE (`rggmci.py`):

- **P-2 product-class compatibility:** the two fragments must share a specific compatible class, not just a generic umbrella token.
- **R1 / R2 / R3:** demote if both fragments drop their class after exclusions (R1); if neither side has a strong reference (R2); or on a noise-class signal on both sides (R3).
- **Hub-degree guard:** a BGC confidently linked to more than `RGGMCI_MAX_HUB_DEGREE = 4` fragments is promiscuous (a 2-fragment split is degree 1); HIGH links beyond degree 4 are demoted (`DEMOTED_HUB_PROMISCUITY_degree_d_gt_4`).

### 7.3 Subject-tiling verdict (genuineness)

**Source:** `rggmci.py:_subject_tiling`, consumed by the cohort rollup (`tools/rggmci_cohort_rollup.py`, v9.7.117)

Independently of the score, the two fragments' subject genes are compared to classify the *kind* of relationship.

- **COMPLEMENTARY_SPLIT** — the pair met the engine's aggregated disjoint-tiling, subject-count and geometry conditions; a candidate split interpretation.
- **TERMINUS_TRUNCATION_SPLIT** — a retained terminus/geometry condition changed or corroborated the tiling label; inspect the override and junction-evidence fields.
- **OVERLAPPING_PARALOG** — overlapping subject support triggered the engine's paralogy category; retained HIGH/MODERATE confidence is demoted to LOW by this gate.
- **MIXED_SUBJECT_SIGNAL** — mixed overlap/disjoint support; unresolved.
- **INSUFFICIENT_SUBJECT_DATA** — the split conditions were not established; not a completed rejection of linkage.

These labels do not independently establish physical adjacency, reject every alternative or
measure biological confidence.

The cohort rollup ranks the whole cohort's rescues by this verdict (genuineness), not raw score — because raw-score ranking once put an OVERLAPPING_PARALOG pair at #1. It then layers a **CONFIRMABLE / LIKELY / NEEDS-REVIEW** confidence tier driven by disjoint-reference count, shared-subject overlap, the DISTANT_ON_REFERENCE caution, and core fraction.

### 7.4 RG-GMCI's effect on scoring

RG-GMCI changes routing priority, never claim confidence. Its only scoring effects are the `rescue_bonus` (§4.5) and the (currently dormant) penalty reduction (§4.7). The two-level rule (slim kernel Module 3) governs the rest: an Interior split-anchor keeps its standalone architecture grade; only the *pathway-unit* label is downgraded to Arch C.

---

## 8. The completeness invariant

**Source:** `scoring.py:scoring_coverage`, `scoring.py:assert_full_scoring_coverage` (v9.7.20)

Every BGC is assessed on AB/AF/novelty — not just lead-tier ones. The engine scores all BGCs by construction (`triage_bgcs` loops the full list; Edge/FC/small-contig fragments included, none skipped). This invariant exists to catch **downstream** loss — a merge or workbook build that carries scores for leads only, as one cohort merge did at ~9% coverage:

```
coverage = (#BGCs with ab, af, novelty all populated) / (#BGCs total)
```

`assert_full_scoring_coverage` raises by default, but its `raise_on_fail=False` option returns
a warning instead. The native gold-path writer uses that option and can continue to export
after a WARN or ERROR receipt. The helper checks matched non-None score fields on the supplied
objects, not the saved CSV/workbook or finite numeric validity. Keep its warning state and
expected roster alongside a separate check of the saved output.

---

## 9. Multibatch trigger

**Source:** `scoring.py:needs_multibatch`

The helper returns a batching recommendation and its first applicable reason:

```
needs_multibatch  =  raw > 25
                  ∨  (edge + full_contig) > 15
                  ∨  fragmented-cluster rescue review was triggered
```

---

## 10. Constants quick-reference

| Constant | Value | Source | Role |
|---|---|---|---|
| Edge flank | 5000 bp | `parsers.py:_edge_status` | Edge boundary tolerance |
| Full-contig threshold | 0.95·L | `parsers.py:_edge_status` | region ≥95% of contig |
| Corrected-count weights | 1 / 0.5 / 0.25 | `assembly.py:corrected_bgc_count` | Interior / Edge / FC |
| Assembly tiers | 70 / 45 / 20 | `assembly.py:assembly_tier` | GOOD / MOD / POOR / V_POOR |
| GC dispersion flag | ≥ 5.0 | `assembly.py:assembly_sanity_check` | contamination suspect |
| Score bases | 25 / 20 / 30 | `scoring.py:triage_bgcs` | AB / AF / novelty floor |
| Diagnostic bonus | 25 | `scoring.py` | corroborated CCTT trigger |
| KCB-strong novelty | −15 | `scoring.py` | kcb_cumulative > 10000 |
| Missing/unknown KCB novelty | 0 | `scoring.py` | unavailable comparator adds no credit; explicit UNKNOWN also suppresses high-KCB penalty |
| Low-RiQ novelty | +10 | `scoring.py` | riq_score < 0.5 |
| Rescue bonus | 8 / 4 | `scoring.py` | HIGH / MODERATE RG-GMCI |
| Edge penalty | 0.0 | `scoring.py:edge_penalty` | neutralized (v9.7.84) |
| Penalty multipliers | 0.35 / 0.20 | `scoring.py:triage_bgcs` | AB·AF / novelty (dormant) |
| Lead tiers | 85 / 70 / 50 | `scoring.py:triage_bgcs` | Exceptional / High / Medium |
| Architecture grade | 10 kb, KCB 10000 | `parsers.py:architecture_grade` | A–E thresholds |
| RiQ labels | 0.85 / 0.50 | `antismash_evidence.py:riq_label` | known / variant / novel |
| RiPP-fragment floor | 8.0 kb | `scoring.py` | truncated RiPP cap |
| RG-GMCI tiers | 14 / 9 | `rggmci.py` | HIGH / MODERATE |
| Hub-degree max | 4 | `rggmci.py` | promiscuity demotion |
| Multibatch | 25 / 15 | `scoring.py:needs_multibatch` | raw / edge+FC |

---

*Every formula transcribed from engine source. Scores are routing priors, not biological proof; KCB is similarity, not identity; capacity-level language is mandatory downstream.*
