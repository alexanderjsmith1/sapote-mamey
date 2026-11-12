# The Mathematics of Sapote-Mamey

## Using this reference

Start with the saved value you want to explain: [counts](#2-the-corrected-bgc-count),
[AB/AF/novelty scores](#4-the-three-routing-scores-ab-af-novelty),
[a tier or guard](#6-floors-downgrades-and-guards), or
[a candidate fragment link](#7-rg-gmci-reconstructing-fragmented-clusters).
Read the matching section beside the package's source row and issue records.
Terms are defined in the [glossary](../GLOSSARY.md). Use [current source scope](06_CURRENT_SOURCE_SCOPE.md)
to interpret counts, tiers and raw pair scores.

These numbers are weighted diagnostics and routing labels. They are not a physically reconciled
cluster census or a calibrated probability. Keep raw counts and exact scope. A low or absent
KnownClusterBlast (KCB) match does not establish novelty, compound identity, production or activity.

### Counting, scoring, and reconstruction formulae in the deterministic extraction engine

**Version of record:** Mamey engine v1.9.181 · bundle v9.7.465
**Status:** Source-cited methods reference. A module citation locates an explanation; current behavior still needs the selected source and input state.

---

## 0. How to read this document

Mamey is the deterministic half of the pipeline. It parses antiSMASH output and computes a fixed set of numbers: BGC (biosynthetic gene cluster) counts, assembly tiers, three routing scores per cluster, reconstruction-confidence scores for fragmented clusters, and a set of guard flags. Sapote, the judgment layer, consumes those numbers. It never recomputes them. This document covers the Mamey math only.

Two principles govern every number here and should be read into all of them:

1. **The scores are routing priors, not biological proof.** AB/AF/novelty values order BGCs for human and judgment-layer attention. They are explicitly *not* WL/DAPR scores and must never be cited as evidence that a strain produces a compound. The claim-safe vocabulary ("biosynthetic capacity consistent with…") is mandatory downstream of every number in this document.

2. **KCB is similarity, not identity.** Every appearance of a known-cluster-blast (KCB) signal below is a sequence-similarity measure against a reference. It informs novelty and display; it never confirms a product.

Each section gives the formula, the constants as they appear in code, the rationale, and the source location (`module.py:symbol`).

---

## 1. BGC boundary classification

Everything counting-related rests on one upstream decision: is a detected region **Interior**, **Edge**, **Full-contig**, or **Unknown**? This *edge status* uses supplied coordinates, contig length and topology before scoring; it does not measure pathway completeness.

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

- **The 0.95 rule.** A region occupying ≥95% of its contig is "Full-contig" — this is a span label, not proof that both ends are truncated or that a pathway is complete.
- **Circular-replicon correction.** On a closed/circular chromosome the origin is not a truncation point — origin proximity alone does not prove that a BGC wraps. After the Full-contig check, the circular branch returns Interior; verify source coordinates and topology. Edge is assigned by the remaining linear/unknown-topology branch. Without this, a closed genome would get false Edge calls at the origin, and the corrected count would fall below the raw count.
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
N50 = L* at the first observed sorted contig length where cumulative length reaches total/2
```

**GC fraction** (`assembly.py:gc_pct_from_sequences`):

```
GC% = round( (#G + #C) / (#A + #C + #G + #T) · 100 , 3 )
```

### 3.2 Non-blocking contamination / sanity heuristic

**Source:** `assembly.py:assembly_sanity_check`

Some very poor drafts show clear pathology, such as bimodal GC or megabases of foreign content. This check flags — but never blocks — suspicious assemblies. It computes a **length-weighted per-contig GC standard deviation**:

```
mean = Σ(gᵢ·wᵢ) / Σwᵢ
var  = Σ(wᵢ·(gᵢ − mean)²) / Σwᵢ
gc_sd = √var
```

where `gᵢ` is contig *i*'s GC% and `wᵢ` its length. Flags fire as:

- `gc_sd ≥ 5.0` → **CONTAMINATION_SUSPECT** (a review threshold, not a source-bound estimate of clean-genome variation).
- `|overall_GC − expected_GC| ≥ 8.0` → **ASSEMBLY_SANITY** (only if a taxon GC prior is supplied).
- genome size outside an expected `[lo, hi]` range → **ASSEMBLY_SANITY** (only if a size prior is supplied).

GC dispersion is evaluated only with at least two contigs carrying valid GC measurements;
otherwise `per_contig_gc_sd` is None. The current default size checks also need no taxon prior:
positive total size below 3,000,000 bp or above 12,000,000 bp raises a suspect flag, and a
below-floor input with at most five contigs gets a partial-submission flag. Caller overrides can
change or disable those bounds. The flags are named `PARTIAL_ASSEMBLY_SUSPECT` and `PARTIAL_SUBMISSION_SUSPECT`; search the issue log for those names. These are non-blocking heuristics; inspect the recorded inputs
and flags rather than reading a missing dispersion value as a clean result.

---

## 4. The three routing scores: AB, AF, novelty

Each BGC receives three scores on a 0–100 scale: **AB** (antibacterial routing prior), **AF** (antifungal routing prior), and **novelty**. They sort clusters for the judgment layer. The full computation lives in `scoring.py:triage_bgcs`; the constants are module-level in `scoring.py`.

### 4.1 The base + keyword model

On the usual branch, the initial values are the following base-plus-keyword scores. An overmerge-suspect multi-product record uses the maximum per-protocluster keyword score instead. Compound-class credits, diagnostic subsumption, guards and other adjustments also apply; inspect the selected path and rationale for each score:

```
base_AB      = 25 + score_keywords(class_text, AB_KEYWORDS)
base_AF      = 20 + score_keywords(class_text, AF_KEYWORDS)
base_novelty = 30 + score_keywords(class_text, NOVELTY_KEYWORDS)
```

The values 25/20/30 are initial bases on the stated branches, not a universal final-score floor. The **keyword tables** as they appear in code:

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

These weights are routing priors set by workflow judgment not calibrated against a labelled set. Changing them changes batch ordering.

### 4.2 Delimited-word matching and subsumption

**Source:** `scoring.py:score_keywords`, `scoring.py:_key_present`

A class keyword scores **once**, at its most specific weight, and only on a delimiter-bounded token match — never a glued substring. The membership test:

```
_key_present(key, text)  =  regex (?<![a-z0-9]) key (?![a-z0-9]) matches text
```

This is the project's recurring **substring-containment** guard applied to scoring. It keeps legitimate delimited subtypes (`t2pks` inside `hr-t2pks`, `azole` inside `azole-containing-ripp`, `siderophore` inside `ni-siderophore`) while rejecting glued false matches — the canonical one being `polyene` inside `arylpolyene`, which would score a pigment as an antifungal.

**Subsumption.** A specific subclass suppresses the generic it implies, so weight is not double-counted:

```
SUBCLASS_SUBSUMES = { hr-t2pks → t2pks,  transat-pks → t1pks }
```

If both the subtype and its generic match, only the subtype's weight is banked. **Pigment classes** (`arylpolyene`, `ladderane`) are excluded from scoring entirely.

The scorer also sees only the BGC's **own** class evidence — its `products`, `mibig_hits`, and a *resolved* MIBiG product line — never the raw `kcb_top` genome-description blob (`scoring.py:scoring_class_text`). A genome self-hit's free-text description carries the *reference organism's* unrelated class tokens; folding those in would inflate a bare `saccharide` cluster with `nrps`, `t1pks` and `t2pks` weights that are not its own.

### 4.3 The diagnostic-marker bonus

**Source:** `scoring.py` (`DIAGNOSTIC_BONUS`, `AF_DIAGNOSTIC_TRIGGERS`, `AB_DIAGNOSTIC_TRIGGERS`)

A CCTT (Compound-Class Trigger Table) trigger that supports a bioactivity class — even when the product label and KCB anchor carry no matching word — adds a flat bonus.

```
DIAGNOSTIC_BONUS = 25
if a corroborated AF trigger fired:  base_AF += 25
if a corroborated AB trigger fired:  base_AB += 25
```

- **AF triggers:** `T43-NUC` (nucleoside chitin-synthase inhibitors), `T43-PTM` (HSAF/PTM macrolactams), `T43-PYE` (polyene macrolide antifungals).
- **AB triggers:** `T43-LAN`, `T43-LASSO`, `T43-THA`, `T43-PHO`, `T43-AMC`, `T43-BLA`, `T43-GPA` (glycopeptide), `T43-BLT` (betalactone).

The bonus keeps a KCB-dark cluster labelled only "nucleoside; other" from losing a diagnostic it carries, such as NikJ. Only **corroborated** triggers grant the bonus — see §6.1.

### 4.4 KCB and RiQ novelty adjustments

**Source:** `scoring.py:triage_bgcs`

After the keyword base, novelty is adjusted by reference-similarity and recognition signals:

```
if kcb_evidence_state != UNKNOWN_KCB and kcb_similarity_pct is not None and kcb_similarity_pct >= 70:
    novelty −= 15       # observed close comparator
# A missing percent, or an UNKNOWN_KCB state, moves nothing.
if riq_score is not None and riq_score < 0.5:
    novelty += 10       # supplied low-recognition metric; not proof of novelty
```

`kcb_similarity_pct` is antiSMASH's percent similarity to the closest known cluster (0–100). The package bands it at 70 and 40 (`precision.py:KCB_PCT_HIGH`, `KCB_PCT_MODERATE`). The cumulative KCB score is a summed BLAST score. It is not a percent and grows with cluster size, so no rule here reads it. `riq_score` is antiSMASH's region-to-region RiQ ratio (0–1).

A recognized KnownClusterBlast no-hit report can yield `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED`. Unsupported empty, missing, unreadable or unbound evidence can instead remain unavailable/UNKNOWN; no such label by itself proves a completed negative search. See [Reading your results](../READING_YOUR_RESULTS.md) for the states and bands.

### 4.5 The RG-GMCI rescue bonus

A BGC linked to other fragments by reconstruction evidence (§7) gets a routing-priority bonus — never a confidence bonus:

```
rescue_bonus = 8   if a HIGH_RG_GMCI_RESCUE link supports the BGC
             = 4   if a MODERATE_RG_GMCI_CANDIDATE link supports it
             (ACCESSORY_ONLY gives no bonus; an absent functional profile can remain eligible and is not demonstrated complementarity)
             = 0   otherwise  (and 0 for a primary-metabolism, pigment or mobile-element-flagged region)
```

### 4.6 The edge penalty (neutralized)

**Source:** `scoring.py:edge_penalty`

```
edge_penalty(edge_status) = 0.0    (for all statuses)
```

The boundary penalty is **deliberately zero**. An earlier development account reported comparable base scores across boundary states; its dataset is not bound here and does not establish a general absence of truncation effects. Truncation uncertainty is carried as a confidence signal through the architecture grade (§5) and the edge-status field, not as a score deduction. The function is kept, returning 0, so the multipliers below stay wired for a future calibrated penalty.

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

A structural routing heuristic, not a measured completeness or reliability estimate, derived from edge status, whether a core biosynthetic class is present, length, KCB support, and antiSMASH's chemical-hybrid flag. Let `has_core` be true if the product text contains any of {nrps, pks, ripp, lanthipeptide, terpene, saccharide, phosphonate, siderophore, metallophore, lassopeptide, thioamide, tomm, azole}; `distinct_core` the number of distinct normalized product families among the product labels that contain one of those terms (`product_family`; a label in the catch-all `other` family counts as its own class), not the number of matched terms; `high_kcb = (kcb_similarity_pct ≥ 70)`; and `hybrid_coherent = has_chemical_hybrid ∧ distinct_core ≥ 2`, where `has_chemical_hybrid` means antiSMASH flagged the region's candidate cluster `kind = chemical_hybrid`. Rules are applied in this order; the first that matches wins:

```
Interior ∧ has_core ∧ length ≥ 10 kb         →  A   (passes configured length/core conditions; completeness not established)
Interior ∧ high_kcb ∧ ¬has_core              →  B   (KCB-supported, limited core annotation)
Interior ∧ has_core ∧ hybrid_coherent        →  A   (compact but coherent: fused multi-class architecture)
Interior ∧ has_core                          →  B   (limited/compact)
Edge ∧ has_core                              →  C   (truncated but coherent; partial)
Edge ∧ ¬has_core                             →  D   (truncated, limited annotation)
Full-contig ∧ has_core                       →  D   (Full-contig/core label; physical truncation not established)
otherwise                                    →  E   (weak/ambiguous; inventory-level)
```

The hybrid promotion only lifts a compact Interior core region from B to A. It never promotes a truncation grade (C, D or E): the hybrid flag says nothing about edge or length truncation. Example: Interior, products `nrps; t1pks`, 5,000 bp, chemical-hybrid flag set → A (without the flag, B). One label that contains two listed terms counts once: Interior, product `nrp-metallophore`, 5,000 bp, flag set → B. So do two labels in one family: `lanthipeptide-class-i; ripp-like` → B. The grade is a structural routing heuristic, not measured completeness, production, novelty or activity.

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

### 6.1 Trigger corroboration (selected CCTT bonus and floor paths)

A CCTT class trigger only counts if it is **corroborated** — fired on a class-compatible locus. An uncorroborated trigger (e.g. `T43-PHO` on a T3PKS, or any gated trigger on a mobile-dominant region whose class-defining enzyme is absent and whose architecture-class confidence is LOW) is recorded for the judgment layer but grants **no** AB/AF bonus, no indicated corroboration-based guard exemption, and **no** tier floor:

```
corroborated_triggers = triggers − uncorroborated
(corroborated triggers feed the indicated bonus/floor paths; individual guards can use different inputs, including the raw-trigger hglE fallback)
```

This is an implemented CCTT-veto policy, not a measured reliability guarantee. The hglE fallback separately checks the raw trigger set.

### 6.2 The Tier-1 diagnostic floor

A Tier-1 diagnostic is a corroborated class-defining trigger, or class-concordant self-resistance. It must not be buried by a low text or KCB score.

```
if (a corroborated class-defining trigger fired  OR  class-concordant T1 self-resistance)
   AND tier in {Inventory, Low}:
        tier ← Medium        (floored = true)
```

**Exclusion:** a lone tailoring-enzyme marker — halogenase / fluorinase-chlorinase (`T43-HAL_*`, `T43-XHAL_*`) — is a *modification*, not a class call, and does **not** floor on its own. A class-defining marker that co-occurs still floors; the tailoring marker remains a recorded signal.

### 6.2a The glycopeptide machinery floor

**Source:** `scoring.py:736-749`

```
if architecture_capacity == "glycopeptide"
   AND architecture_class_confidence == "HIGH"
   AND tier in {Medium, Inventory, Low}:
        tier ← High          (floored = true, glyco_machinery_floored = true)
```

The configured glycopeptide capacity label tests at least six NRPS condensation domains, a halogenase and a glycosyltransferase (`class_architecture.py`). These signals do not independently establish crosslinking machinery or a confirmed glycopeptide. Verify source annotations and alternatives; the floor is a routing policy that can raise this label to High. It never raises a tier above High, and the downgrades in §6.6 and §6.7 are applied after it. It is a capacity statement, not a production claim.

### 6.3 Primary-metabolism / pigment suppression

**Source:** `scoring.py:triage_bgcs`

Fires only when **all** of: (a) a housekeeping/pigment core-gene marker is in the BGC's own CDS; (b) the BGC's own product class is *exclusively* weak/over-call labels (`WEAK_OVERCALL_CLASSES` = {nrps-like, terpene, terpene-precursor, saccharide, arylpolyene, other, t2pks, t3pks, pks-like, fatty_acid, redox-cofactor, quinone_isoprenoid_chain}); and (c) no Tier-1 diagnostic fired. Effect:

```
base_AB ← min(base_AB, 25)        # strip keyword credit to the floor
base_AF ← min(base_AF, 20)
```

This policy caps keyword credit for the matching records. A committed class label or qualifying diagnostic can exempt a record; exemptions and caps are routing rules, not proof that a cluster is genuine or false.

### 6.4 Mobile-element / ICE demotion

**Source:** `scoring.py:triage_bgcs`

A region dominated by mobility machinery (ICE/transposon) and mis-typed by antiSMASH as biosynthetic is not a biosynthesis lead.

```
if mobile_dominant AND no Tier-1 diagnostic:
        base_AB ← min(base_AB, 25)
        base_AF ← min(base_AF, 20)
```

A qualifying diagnostic can exempt it; the exemption does not establish that a region is a genuine cluster. The companion resistance-axis rule: a T1 self-protection tier on a mobile-dominant region is only genuine self-resistance if the resistance is *class-concordant* with the cluster's own product. A non-concordant resistance group on an ICE background does not establish a Tier-1 self-resistance diagnostic under this rule; its biological role remains to be reviewed.

### 6.5 KCB mis-anchor guards

**Source:** `scoring.py:triage_bgcs`

The recorded mis-anchor flags constrain comparator-derived credit. An aminoglycoside
mis-anchor clamps AB regardless of an unrelated Tier-1 trigger. A polyene mis-anchor clamps
AF unless a corroborated non-polyene AF diagnostic supplies independent credit; inspect the
rationale to see that exception. An unrelated Tier-1 marker is not a blanket exemption.

```
aminoglycoside anchor, no DOIS/2-deoxy-scyllo-inosose:   base_AB ← min(base_AB, 25)
polyene anchor, < 4 PKS-KS domains:                      base_AF ← min(base_AF, 20)
```

**Enediyne guard (§4.1 novelty table, independent of tier):** a flagged mis-anchor loses only the enediyne keyword contribution actually banked on the selected branch; it need not be 18. A genuine named-enediyne KCB anchor carries a neutral `[E-signal]` note — similarity, structure not confirmed — and *no* BSL-2/lab-safety warning (the enediyne BSL-2 doctrine was retired; selective biosafety flags give false reassurance, and chemical handling is governed by lab SOPs).

```
if enediyne mis-anchor: remove the difference between selected keyword scores with/without enediyne
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
state. Keep that implementation/policy discrepancy visible. NAPAA has no such fallback, but `compile_report.py` still filters a row carrying a NAPAA standing label. Read the selected artifact's actual row and standing state; do not assume every compiled report follows the neutral registry.

A resulting standing label sets `tier = bottom_tier(bgc)` (Low or Inventory by class policy),
clears the generic floor flag and excludes corrected lead rank, while preserving the numeric
axes. It does not certify a product, habitat-specificity or novelty claim. For the detailed
consumer boundary, use [current standing-rule scope](06_CURRENT_SOURCE_SCOPE.md#volume-i-section-66-standing-rule-selection-scope-and-policy-conflict).

### 6.7 RiPP-fragment completeness floor

**Source:** `scoring.py:triage_bgcs`

This cap uses RiPP-family labels, Edge/Full-contig state and positive span below 8 kb as proxies. It does not directly test precursor absence:

```
if RiPP-family AND edge_status ∈ {Edge, Full-contig}
   AND 0 < span_kb < 8.0 AND tier ∈ {Exceptional, High, Medium}:
        tier ← bottom_tier(bgc)  (ripp_floored = true; specialized RiPP normally Low)
```

Span uses the validated circular span when supplied; otherwise absolute coordinate difference when an end is present, otherwise contig length, divided by 1,000. This branch excludes Interior labels. Review source coverage independently; size/boundary proxies do not establish precursor absence or product completeness.

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
+ 2   if both counts are truthy and (a.nprot + b.nprot) ≥ 12

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

(`RGGMCI_SCORE_HIGH = 14`, `RGGMCI_SCORE_MODERATE = 9`). These component weights are engineering judgment, not calibrated against a labelled set — the downstream cascade applies specified guards and demotions, not a measured precision estimate or proof of linkage. The raw score is a coarse routing prior.

### 7.2 The gate cascade (specified demotions)

A HIGH score is necessary but not sufficient. Several gates can **demote** HIGH → MODERATE (`rggmci.py`):

- **Product-class compatibility:** the two fragments must share a specific compatible class, not just a generic umbrella token.
- **Three exclusion gates:** demote if both fragments drop their class after exclusions; if neither side has a strong reference; or on a noise-class signal on both sides.
- **Hub-degree guard:** a BGC confidently linked to more than `RGGMCI_MAX_HUB_DEGREE = 4` fragments is promiscuous (a 2-fragment split is degree 1); HIGH links beyond degree 4 are demoted (`DEMOTED_HUB_PROMISCUITY_degree_d_gt_4`).

### 7.3 Subject-tiling verdict (genuineness)

**Source:** `rggmci.py:_subject_tiling`, consumed by the cohort rollup (`tools/rggmci_cohort_rollup.py`)

Independently of the score, the two fragments' subject genes are compared to classify the *kind* of relationship.

- **COMPLEMENTARY_SPLIT** — the pair met the engine's aggregated disjoint-tiling, subject-count and geometry conditions; a candidate split interpretation.
- **TERMINUS_TRUNCATION_SPLIT** — a retained terminus/geometry condition changed or corroborated the tiling label; inspect the override and junction-evidence fields.
- **OVERLAPPING_PARALOG** — overlapping subject support triggered the engine's paralogy category; retained HIGH/MODERATE confidence is demoted to LOW by this gate.
- **MIXED_SUBJECT_SIGNAL** — mixed overlap/disjoint support; unresolved.
- **INSUFFICIENT_SUBJECT_DATA** — the split conditions were not established; not a completed rejection of linkage.

These labels do not independently establish physical adjacency, reject every alternative or
measure biological confidence.

The cohort rollup ranks the whole cohort's rescues by this verdict (genuineness), not raw score, because a raw-score ranking can put an OVERLAPPING_PARALOG pair first. It then layers a **CONFIRMABLE / LIKELY / NEEDS-REVIEW** confidence tier driven by disjoint-reference count, shared-subject overlap, the DISTANT_ON_REFERENCE caution, and core fraction.

### 7.4 RG-GMCI's effect on scoring

RG-GMCI changes routing priority, never claim confidence. Its only scoring effects are the `rescue_bonus` (§4.5) and the (currently dormant) penalty reduction (§4.7). An Interior split-anchor keeps its own architecture grade; only the pathway-unit label drops to Arch C.

---

## 8. The completeness invariant

**Source:** `scoring.py:scoring_coverage`, `scoring.py:assert_full_scoring_coverage`

Every BGC is assessed on AB/AF/novelty — not just lead-tier ones. The engine scores all BGCs by construction (`triage_bgcs` loops the full list; Edge/FC/small-contig fragments included, none skipped). This invariant exists to catch **downstream** loss, such as a merge or workbook build that carries scores for leads only:

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
| Score bases | 25 / 20 / 30 | `scoring.py:triage_bgcs` | AB / AF / novelty initial bases on stated branches; not final-score floors |
| Diagnostic bonus | 25 | `scoring.py` | corroborated CCTT trigger |
| KCB-strong novelty | −15 | `scoring.py:triage_bgcs` | non-UNKNOWN KCB state and `kcb_similarity_pct` ≥ 70 (`precision.py:KCB_PCT_HIGH`) |
| Missing/unknown KCB novelty | 0 | `scoring.py` | a missing percent or `UNKNOWN_KCB` adds no credit and no penalty |
| KCB percent bands | 70 / 40 | `precision.py:similarity_band` | high / moderate / low |
| Low-RiQ novelty | +10 | `scoring.py` | riq_score < 0.5 |
| Rescue bonus | 8 / 4 | `scoring.py` | HIGH / MODERATE RG-GMCI |
| Edge penalty | 0.0 | `scoring.py:edge_penalty` | neutralized |
| Penalty multipliers | 0.35 / 0.20 | `scoring.py:triage_bgcs` | AB·AF / novelty (dormant) |
| Lead tiers | 85 / 70 / 50 | `scoring.py:triage_bgcs` | Exceptional / High / Medium |
| Architecture grade | 10 kb, KCB percent ≥ 70 | `parsers.py:architecture_grade` | A–E thresholds (`precision.py:KCB_PCT_HIGH`) |
| RiQ labels | 0.85 / 0.50 | `antismash_evidence.py:riq_label` | known / variant / novel |
| RiPP-fragment floor | 8.0 kb | `scoring.py` | truncated RiPP cap |
| RG-GMCI tiers | 14 / 9 | `rggmci.py` | HIGH / MODERATE |
| Hub-degree max | 4 | `rggmci.py` | promiscuity demotion |
| Multibatch | 25 / 15 | `scoring.py:needs_multibatch` | raw / edge+FC |

---

*Source citations are navigation aids; verify each selected formula, code version and input scope. Scores are routing priors, not biological proof; KCB is similarity, not identity; capacity-level language is mandatory downstream.*
