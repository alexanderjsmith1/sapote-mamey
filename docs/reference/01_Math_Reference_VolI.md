# The Mathematics of Sapote-Mamey

### Counting, scoring, and reconstruction formulae in the deterministic extraction engine

**Version of record:** Mamey engine v1.9.110 (the math tracks the engine, which is frozen at 1.9.110 through the current bundle) · constants last verified against engine source 2026-07-13 · bundle at that time v9.7.319
**Author:** Alexander J. Smith
**Status:** Methods reference. Every formula below is transcribed from the engine source and cited to its module; nothing here is reconstructed from memory.

---

## 0. How to read this document

Mamey is the deterministic half of the pipeline: it parses antiSMASH output and computes a fixed set of numbers — BGC counts, assembly tiers, three routing scores per cluster, reconstruction-confidence scores for fragmented clusters, and a battery of guard flags. Sapote, the LLM judgment layer, consumes those numbers; it never recomputes them. This document covers the Mamey math only.

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

Three points of nuance carried in the code:

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

The weights encode partial-evidence discounting: an Interior cluster counts whole (1.0); an Edge cluster, truncated at one boundary, counts half (0.5); a Full-contig cluster, presumed truncated at both ends, counts a quarter (0.25). The raw count `I + E + F` is always reported alongside the corrected count — the discount is transparent, never silent.

**Worked example.** A strain with 12 Interior, 6 Edge, and 4 Full-contig regions:

```
raw       = 12 + 6 + 4              = 22
corrected = 12 + 0.5·6 + 0.25·4     = 12 + 3 + 1 = 16.00
```

A parsing-control invariant follows directly: because every weight is ≤ 1, **corrected ≤ raw** always. A run where corrected exceeds raw signals a coordinate or edge-status bug (this is exactly the failure the circular-replicon fix in §1 addressed).

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

The reasoning: a genome where ≥70% of BGCs sit fully inside contigs is well-enough assembled that the corrected count is trustworthy; below 20% Interior, most clusters are truncated and any count is a floor, not an estimate.

### 3.1 Supporting assembly statistics

**N50** (`assembly.py:n50`) — the length-weighted median contig size. Sort contig lengths descending; accumulate; return the length at which the running total first reaches half the assembly:

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

The dispersion check needs no prior and always runs; the analyst judges, extraction is unaffected.

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

This is the project's recurring **substring-containment** guard applied to scoring: it keeps legitimate delimited subtypes (`t2pks` inside `hr-t2pks`, `azole` inside `azole-containing-ripp`, `siderophore` inside `ni-siderophore`) while rejecting glued false matches — the canonical one being `polyene` inside `arylpolyene`, which previously scored a pigment as an antifungal.

**Subsumption.** A specific subclass suppresses the generic it implies, so weight is not double-counted:

```
SUBCLASS_SUBSUMES = { hr-t2pks → t2pks,  transat-pks → t1pks }
```

If both the subtype and its generic match, only the subtype's weight is banked. **Pigment classes** (`arylpolyene`, `ladderane`) are excluded from scoring entirely.

The scorer also sees only the BGC's **own** class evidence — its `products`, `mibig_hits`, and a *resolved* MIBiG product line — never the raw `kcb_top` genome-description blob (`scoring.py:scoring_class_text`, P-7 fix). A genome self-hit's free-text description carries the *reference organism's* unrelated class tokens; folding those in once inflated a bare `saccharide` cluster by +34 AB from `nrps`/`t1pks`/`t2pks` that were not its own.

### 4.3 The diagnostic-marker bonus

**Source:** `scoring.py` (`DIAGNOSTIC_BONUS`, `AF_DIAGNOSTIC_TRIGGERS`, `AB_DIAGNOSTIC_TRIGGERS`)

A CCTT/cassette trigger that *proves* a bioactivity class — even when the product label and KCB anchor carry no matching word — adds a flat bonus:

```
DIAGNOSTIC_BONUS = 25
if a corroborated AF trigger fired:  base_AF += 25
if a corroborated AB trigger fired:  base_AB += 25
```

- **AF triggers:** `T43-NUC` (nucleoside chitin-synthase inhibitors), `T43-PTM` (HSAF/PTM macrolactams).
- **AB triggers:** `T43-LAN`, `T43-LASSO`, `T43-THA`, `T43-PHO`, `T43-AMC`, `T43-BLA` (lanthi/lasso/thioamide, phosphonate, aminoglycoside, β-lactam).

This fixes the failure mode where a KCB-dark cluster labelled only "nucleoside; other" but carrying the NikJ diagnostic is a definitive antifungal whose evidence was computed and then dropped before it reached the tier gate. Only **corroborated** triggers grant the bonus — see §6.1.

### 4.4 KCB and RiQ novelty adjustments

**Source:** `scoring.py:triage_bgcs`

After the keyword base, novelty is adjusted by reference-similarity and recognition signals:

```
if kcb_cumulative > 10000:       novelty −= 15      # strong known-cluster similarity ⇒ less novel
elif kcb_cumulative is None:     novelty += 5       # no KCB signal at all ⇒ slightly more novel
if riq_score < 0.5:              novelty += 10      # low recognition ⇒ more likely novel
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

The boundary penalty is **deliberately zero**. Empirically (AS cohort + the selvamicin control), Edge/FC clusters show no truncation signature in their base score — mean base AB was Interior 34.7 vs Edge 35.7 vs FC 35.3 — so the former penalty was a flat pessimism prior with no measurement basis. At the Medium threshold it was decisive, flipping 83% of near-threshold Edge/FC leads to Inventory and burying exactly the overlooked fragments the tool exists to surface (selvamicin BGC0001773, a Full-contig attine antifungal polyene, sank partly on this penalty). Truncation uncertainty is now carried as a **confidence** signal via architecture grade (§5) and the edge-status field, not as a score deduction. The function is retained returning 0 so the multipliers below stay wired for a future calibrated penalty from one place.

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
best <  50   →  Inventory
```

The tier is then subject to floors and downgrades (§6).

### 5.2 Architecture confidence A–E

**Source:** `parsers.py:architecture_grade`

A *structural reliability* grade — how completely the cluster is captured — derived from edge status, whether a core biosynthetic class is present, length, and KCB support. Let `has_core` be true if the product text contains any of {nrps, pks, ripp, lanthipeptide, terpene, saccharide, phosphonate, siderophore, metallophore, lassopeptide, thioamide, tomm, azole}, and `high_kcb = (kcb_score ≥ 10000)`:

```
Interior ∧ has_core ∧ length ≥ 10 kb         →  A   (coherent, complete)
Interior ∧ (has_core ∨ high_kcb)             →  B   (limited/compact, or KCB-supported)
Edge ∧ has_core                              →  C   (truncated but coherent; partial)
Edge ∧ ¬has_core                             →  D   (truncated, limited annotation)
Full-contig ∧ has_core                       →  D   (likely truncated both ends)
otherwise                                    →  E   (weak/ambiguous; inventory-level)
```

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

A definitive class marker must not be buried by a low text/KCB score:

```
if (a corroborated class-defining trigger fired  OR  class-concordant T1 self-resistance)
   AND tier == Inventory:
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

A region dominated by mobility machinery (ICE/transposon) and mis-typed by antiSMASH as biosynthetic is not a biosynthesis lead:

```
if mobile_dominant AND no Tier-1 diagnostic:
        base_AB ← min(base_AB, 25)
        base_AF ← min(base_AF, 20)
```

A corroborated class signal exempts it, so genuine clusters with incidental flanking mobile genes are untouched. The companion resistance-axis rule (v9.7.37, PC-12): a T1 self-protection tier on a mobile-dominant region is only genuine self-resistance if the resistance is *class-concordant* with the cluster's own product; a non-concordant resistance group on an ICE background is horizontally-acquired cargo, not self-protection, and does not establish a Tier-1 diagnostic.

### 6.5 KCB mis-anchor guards

**Source:** `scoring.py:triage_bgcs` (v9.7.15)

A KCB product-name anchor lacking its committed class diagnostic is spurious for this locus; the anchor-derived axis credit is suppressed (exempt when a Tier-1 diagnostic independently fires):

```
aminoglycoside anchor, no DOIS/2-deoxy-scyllo-inosose:   base_AB ← min(base_AB, 25)
polyene anchor, < 4 PKS-KS domains:                      base_AF ← min(base_AF, 20)
```

**Enediyne guard (§4.3, independent of tier):** a PREV-001/hglE artifact loses its +18 enediyne novelty credit; a genuine named-enediyne KCB anchor carries a neutral `[E-signal]` note — similarity, structure not confirmed — and *no* BSL-2/lab-safety warning (the enediyne BSL-2 doctrine was retired; selective biosafety flags give false reassurance, and chemical handling is governed by lab SOPs):

```
if enediyne mis-anchor:   novelty −= 18
```

A class-level KCB mismatch (compound family incompatible with own product class) is flagged for the judgment layer regardless of tier.

### 6.6 Standing-rule permanent exclusions

**Source:** `scoring.py:standing_rule_for`, registry `mamey/data/rules_registry.json`

Three always-on downgrades cap the lead tier to Inventory while **preserving raw scores** (evidence trail intact):

- **saccharide** — read from own products only.
- **NAPAA** — the *Nosema* hypothesis was retired; annotation-domain flag.
- **hglE-KS-PREV-001 / hexacosalactone** — habitat-non-specific; for this rule the *structural novelty stays intact*, only the drug-lead/habitat-specificity claim is downgraded (novelty is deliberately not stripped).

The **committed-class guard** protects real leads: a standing-rule downgrade applies only when the BGC's own product classes are *exclusively* weak/over-call labels. A real NRPS/PKS/RiPP that merely carries a saccharide tailoring arm keeps its lead status. Exception — NAPAA and hglE-KS bypass this guard, because they are annotation-domain flags that fire even on committed-backbone clusters (a PKS cluster also carrying the hglE-KS domain is still a hexacosalactone-class downgrade). A CCTT co-occurrence on an hglE-KS region suppresses the downgrade (the biosynthetic content extends beyond the generic glycolipid machinery).

```
if a standing rule fires:   tier ← Inventory
```

### 6.7 RiPP-fragment completeness floor

**Source:** `scoring.py:triage_bgcs` (F2)

A RiPP-family cluster (`RIPP_FAMILY_CLASSES`) that is a truncated sub-8 kb fragment with no precursor captured cannot be evaluated as a product:

```
if RiPP-family AND edge_status ∈ {Edge, Full-contig}
   AND 0 < span_kb < 8.0 AND tier ∈ {Exceptional, High, Medium}:
        tier ← Inventory        (ripp_floored = true)
```

`span_kb = (end − start)/1000`, falling back to contig length. Never touches Interior clusters. Size + edge are conservative precursor proxies; a lone LanM synthetase beside a gas-vesicle operon should not float above a complete cluster.

### 6.8 Corrected lead rank

**Source:** `scoring.py:triage_bgcs`

After all scoring, records are sorted by `max(AB, AF, novelty)` descending. The **corrected rank** is a sequential lead rank assigned only to rows that are **not** standing-rule-downgraded, **not** primary-metabolism/pigment-flagged, and **not** mobile-element-flagged. Downgraded rows keep their raw scores but receive `corrected_rank = None` — they are visible but out of the lead order.

---

## 7. RG-GMCI: reconstructing fragmented clusters

When a biosynthetic cluster is split across contigs by assembly fragmentation, RG-GMCI (Reference-Guided Genomic Module Co-Identification) scores whether two BGC fragments are arms of one original cluster, by shared-reference geometry. **This is homology-guided linkage, never an asserted nucleotide-level contig join.**

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

(`RGGMCI_SCORE_HIGH = 14`, `RGGMCI_SCORE_MODERATE = 9`.) These component weights are engineering judgment, not calibrated against a labelled set — precision is enforced by the downstream gate cascade below, not by the weights. The raw score is a coarse routing prior.

### 7.2 The gate cascade (precision enforcement)

A HIGH score is necessary but not sufficient. Several gates can **demote** HIGH → MODERATE (`rggmci.py`):

- **P-2 product-class compatibility:** the two fragments must share a specific compatible class, not just a generic umbrella token.
- **R1 / R2 / R3:** demote if both fragments drop their class after exclusions (R1); if neither side has a strong reference (R2); or on a noise-class signal on both sides (R3).
- **Hub-degree guard:** a BGC confidently linked to more than `RGGMCI_MAX_HUB_DEGREE = 4` fragments is promiscuous (a 2-fragment split is degree 1); HIGH links beyond degree 4 are demoted (`DEMOTED_HUB_PROMISCUITY_degree_d_gt_4`).

### 7.3 Subject-tiling verdict (genuineness)

**Source:** `rggmci.py:_subject_tiling`, consumed by the cohort rollup (`tools/rggmci_cohort_rollup.py`, v9.7.117)

Independently of the score, the two fragments' subject genes are compared to classify the *kind* of relationship:

- **COMPLEMENTARY_SPLIT** — disjoint subject tiling: the two arms cover different parts of the reference. *Genuine split.*
- **TERMINUS_TRUNCATION_SPLIT** — a severed arm at a contig terminus. *Genuine split* (may be promoted from INSUFFICIENT/MIXED by a `terminus_override_note` of `severed_arm` or `CORROBORATED_terminus_truncation`).
- **OVERLAPPING_PARALOG** — the arms cover the *same* reference region: shared paralogous machinery, **not** a split. *Excluded.*
- **MIXED_SUBJECT_SIGNAL** — ambiguous. *Manual-review queue.*
- **INSUFFICIENT_SUBJECT_DATA** — no subject tiling to judge. *Not rankable.*

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

`assert_full_scoring_coverage` **fails loudly** (raises) on any unscored BGC. Opting out is a deliberate source edit, not a default — a user is always confronted with incomplete coverage rather than shipping it silently.

---

## 9. Multibatch trigger

**Source:** `scoring.py:needs_multibatch`

A run is split into multiple judgment batches when it is too large to assess coherently in one pass:

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
| No-KCB novelty | +5 | `scoring.py` | kcb_cumulative is None |
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

*Sapote–Mamey · Mamey engine v1.9.110 (frozen; the math tracks the engine, not the rolling bundle version) · constants last verified against engine source 2026-07-13. Every formula transcribed from engine source. Scores are routing priors, not biological proof; KCB is similarity, not identity; capacity-level language is mandatory downstream.*
