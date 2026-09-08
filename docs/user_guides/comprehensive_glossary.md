<!-- SUPERSEDED GLOSSARY SOURCE — NOT CANONICAL -->
> **SUPERSEDED SNAPSHOT.** Retained for provenance and drift review only. It contains version-bound formulas, module descriptions, commands, and cohort-specific statements that may be stale or conflicting. Do not extend it and do not use it as term authority. Current reader-facing definitions live in the canonical [`docs/GLOSSARY.md`](../GLOSSARY.md); current formulas, enumerations, commands, and schemas live in their named code or schema sources.

# Superseded Sapote–Mamey Comprehensive Program Glossary Snapshot
**Bundle v9.7.414 · Engine 1.9.152 · build 20260907v97414a**
*Every entry derived from direct source inspection: module docstrings, formula transcription from `docs/reference/01_Math_Reference_VolI.md`, pattern tables from `docs/MARKER_CATALOG.generated.md`, schema from `docs/WORKBOOK_SCHEMA.md`, and contract docs. No entries inferred from general knowledge.*

---

## Section 1: Architecture and Layer Design

**Sapote–Mamey** — The complete pipeline system. A two-layer design: Mamey (deterministic extraction) and Sapote (LLM judgment). The name convention: Sapote is a tropical fruit with a soft, sweet interior; Mamey is the harder outer shell that protects and structures it. The analogy maps: Mamey provides the deterministic numerical structure; Sapote provides the interpretive judgment inside it.

**Mamey (extraction engine)** — The deterministic Python layer. Reads raw antiSMASH output ZIPs, runs fixed computations in fixed order, and writes a sealed package of structured data to disk. No LLM, no judgment, no prose. Same input + same engine version = same output, byte-for-byte. Current version: 1.9.111. Module: `mamey/` directory. Entry point: `python -m mamey`.

**Sapote (judgment layer)** — The LLM interpretation layer. Reads sealed Mamey packages and produces Mode B analysis cards, ecological synthesis, DAPR boards, layperson guides, and fermentation recommendations. Inherently non-deterministic. Constrained by the gate stack, claim-safety rules, the Execution Slice, and the Sapote Workflow Contract. Not a separate program — it is the operating contract under which the LLM runs.

**Deterministic** — Producing identical output for identical input, independent of when it runs or who runs it. Mamey is deterministic; Sapote is not. The distinction matters for methods reproducibility: a methods paper can cite Mamey outputs as reproducible numbers; Sapote outputs are human-reviewed judgment.

**Sealed package** — A Mamey output directory that has passed `mamey validate`. Contains `manifest.json`, all CSV and XLSX outputs, `checksums_sha256.txt`, and `gate_validation.json`. Status is `MAMEY_COMPLETE`, `MAMEY_COMPLETE_WITH_ISSUES`, or `VALIDATION_FAIL`. Sapote only operates on the first two.

**Four-tier release system** — The four publication tiers for any bundle or package: MERGED-PRIVATE-scaffold (all content), CODE (engine + docs, no private strain data), CODE-analysis-free (engine only), SID-public (public-safe redacted version). Each cut is produced by `tools/make_public_tier.sh` and verified by `tools/verify_tier_derivation.py`.

---

## Section 2: Core Abbreviations and Codes

**AB** — Antibacterial routing prior. A score 0–100 computed by Mamey for each BGC. Base 25 + keyword weights + CCTT diagnostic bonus − penalty. Clamp 0–100. Not a bioactivity claim; a routing signal for the judgment layer. Source: `scoring.py:triage_bgcs`.

**AF** — Antifungal routing prior. A score 0–100. Base 20 + keyword weights + CCTT diagnostic bonus. Source: `scoring.py:triage_bgcs`.

**Novelty** — Novelty routing prior. A score 0–100. Base 30 + keyword weights − KCB adjustment + RiQ adjustment. Source: `scoring.py:triage_bgcs`.

**BGC** — Biosynthetic Gene Cluster. A genomic locus encoding the complete pathway for a natural product: core biosynthetic enzymes + tailoring enzymes + regulatory genes + resistance genes + transporters. Detected by antiSMASH from genome sequences.

**KCB / KnownClusterBlast** — antiSMASH's reference-database comparison tool. Aligns BGC proteins against MIBiG curated clusters and reports a similarity percentage. KCB similarity is not product identity — it identifies the most similar known cluster by protein homology. A 70% KCB score means 70% of query proteins have homologs in the reference, not that the compound is 70% identical to the reference compound.

**KCB-dark** — A BGC with no meaningful KCB similarity to any MIBiG entry. Signals a candidate for novel chemistry. Not the same as "no value" — architecture-based class assignment still applies. A KCB-dark BGC with real biosynthetic architecture and a corroborating CCTT trigger is a novelty candidate, not a null result.

**CCTT** — Compound Class Trigger Table. A set of 18 families of text-pattern triggers that fire when annotation tokens in a BGC's CDS features match class-defining words. Each trigger is named `T43-XXX`. Source: `mamey/source_scans.py`, patterns documented in `docs/MARKER_CATALOG.generated.md`.

**RGGMCI / RG-GMCI** — Reference-Guided Genome Mining Candidate Inference. Homology-guided linkage of BGC fragments from different contigs that likely belong to the same biosynthetic pathway. Uses shared reference cluster geometry from ClusterBlast output. NOT a physical contig join — it raises a linkage hypothesis, not an assembly claim.

**FLBR** — Fragmented-megasynthase census. Detects modular PKS/NRPS genes distributed across multiple contigs. FLBR = STRONG means at least one megasynthase pathway is fragmented. Triggers the LMPKS rescue workflow.

**CGAD** — Chitinase Genome Architecture Detection. Scans the full proteome for chitin-degradation machinery: GH18 chitinases, LPMOs (AA10), GlcNAc utilization genes, DasR regulon markers.

**UMED** — Unusual Maturation Enzyme Detection. Finds RiPP/lanthipeptide maturation enzyme families that antiSMASH does not specifically annotate: RiPP RRE domains, C39 peptidase transporters, FlaP/AplP S9 proteases, YcaO/TfuA thioamide enzymes. Feeds §21–§22 triggering in Mode B.

**EFLS** — Edge-Flank Linkage Scoring. Detects split-pathway candidate pairs across contig boundaries using shared flanking gene signatures.

**DAPR** — Dual-Axis Priority Ranking. The antibacterial (C1) and antifungal (C2) lead boards, each ranking BGCs by their activity-axis score. Source: `docs/DAPR_CLASS_FRAMEWORK.md`, `tools/build_dapr_rescue_sheets.py`.

**WL score** — Wet-Lab Decision Score. A composite priority score combining AB, AF, and LMPKS bonuses. Ranks BGCs for isolation experiments. Source: `docs/modules/DELIVERABLE_WetLabMatrix.md`.

**RiQ** — Region-to-iQ (region recognition quotient). antiSMASH's own metric for how well-recognized a BGC region is relative to its reference database. RiQ < 0.50 → "Potentially novel" label; RiQ ≥ 0.85 → "Likely known."

**NAPAA** — A deprecated ecological hypothesis (the Nosema-Apis-Pathogen-Actinobacteria hypothesis) that proposed bee-associated actinomycetes target *Nosema* specifically. Excluded from all cross-habitat and within-habitat comparative claims because it is ecologically over-specific and convergent. Any BGC dominated by this annotation flag is capped at Inventory tier.

**hglE-KS-PREV-001** — The prevalent glycolipid KS domain finding. The hglE (heterocyst glycolipid synthase) KS domain is habitat-non-specific, appearing across bee, wasp, moss, and ant isolates from multiple genera. Cited as PREV-001 (prevalence finding 001). BGCs dominated by this signal are downgraded from lead status because the domain is ubiquitous across the cohort and therefore non-informative for habitat-specificity claims. The structural novelty of such BGCs is preserved; only the habitat-specificity claim is downgraded.

**HSAF / PTM** — Heat-Stable Antifungal Factor (HSAF), also called dihydromaltophilin, and the broader PTM (polyene tetramate macrolactam) family. A class of hybrid PKS-NRPS antifungals that inhibit sphingolipid biosynthesis. Detected by T43-PTM_hsaf_tetramate trigger. Confirmed in 5 bee-associated strains across 4 genera in the AS-series cohort.

**TTA codon / bldA tiering** — TTA is the rarest leucine codon in actinomycetes; its translation requires tRNA^Leu (encoded by *bldA*). Genes containing TTA codons may be developmentally regulated: T1 = developmentally active bldA present + TTA in BGC core genes; T2 = bldA present; T3 = TTA found but bldA absent or unclear; T4 = no TTA.

**LMPKS** — Large Modular PKS. Megasynthase pathways producing polyketides. Fragmented assemblies (POOR/VERY_POOR tier) frequently split LMPKS pathways across contigs. The LMPKS rescue workflow reconstructs fragmented pathways using RG-GMCI and EFLS evidence.

---

## Section 3: Assembly and BGC Counting

**Edge status** — The boundary classification for each detected BGC region. Three values: Interior (both ends on a contig, away from the contig edge), Edge (one end within 5,000 bp of a contig terminus), Full-contig (the region occupies ≥95% of its contig). Source formula: `parsers.py:_edge_status`.

**Corrected BGC count** — The fractionally-discounted BGC count that accounts for truncation. Formula: `corrected = round(I + 0.5×E + 0.25×F, 2)` where I = Interior count, E = Edge count, F = Full-contig count. The weights reflect partial evidence: a whole Interior cluster counts 1.0; an Edge cluster truncated at one end counts 0.5; a Full-contig cluster (truncated at both ends) counts 0.25. Corrected count ≤ raw count always (invariant). Source: `assembly.py:corrected_bgc_count`.

**Interior fraction** — `interior_pct = round(I / raw × 100, 1)`. The fraction of all detected BGC regions that are fully Interior. Drives the assembly tier classification.

**Assembly tiers** — Four quality categories based on interior fraction:
- GOOD: interior_pct ≥ 70%
- MODERATE: interior_pct ≥ 45%
- POOR: interior_pct ≥ 20%
- VERY_POOR: interior_pct < 20%
The 66/50/33 thresholds from earlier versions are permanently retired. Source: `assembly.py:assembly_tier`.

**N50** — The length-weighted median contig size. Sort contigs by length descending; accumulate lengths; N50 is the contig length at which the running total first reaches half the total assembly size. A proxy for assembly contiguity.

**Full-contig** — Edge status where the BGC region occupies ≥95% of its contig. Presumed truncated at both ends because the contig itself is likely a fragment. Weighted 0.25 in corrected count.

**Circular replicon correction** — On a closed/circular chromosome, the genome origin is not a truncation point — a BGC adjacent to the origin wraps around and is Interior, not Edge. `parsers.py` applies this correction at v9.7.87 to avoid false Edge calls on closed assemblies.

**GC dispersion flag** — A contamination detection heuristic. Computes the length-weighted standard deviation of per-contig GC%. A GC_SD ≥ 5.0 flags CONTAMINATION_SUSPECT. Clean genomes run 1–2% SD; contaminated assemblies run 7–12%. Non-blocking. Source: `assembly.py:assembly_sanity_check`.

---

## Section 4: Scoring System (Full Formulas)

All scores are computed by `mamey/scoring.py:triage_bgcs`. All are routing priors, not biological claims.

**Base scores:** AB base = 25; AF base = 20; novelty base = 30. These floors apply to every non-excluded BGC before any class evidence.

**Keyword scoring:** `score_keywords(class_text, keyword_table)` adds class-specific weights to the base. Each keyword matches once on a delimiter-bounded token (regex `(?<![a-z0-9]) key (?![a-z0-9])`) — no substring containment. Subsumption prevents double-counting: `hr-t2pks` subsumes `t2pks`; `transat-pks` subsumes `t1pks`.

**AB keywords and weights:** carbapenem+18, phosphonate+15, thioamide+14, thiopeptide+14, thiazolylpeptide+14, hr-t2pks+14, transat-pks+14, aminoglycoside+14, nrps+12, t2pks+12, lanthipeptide+12, t1pks+10, lassopeptide+10, phenazine+10, saccharide+8, halogenated+8, ripp+8, azole+8.

**AF keywords and weights:** hsaf+20, nystatin+20, nikkomycin+20, polyoxin+20, polyene+18, candicidin+18, nucleoside+18, tetramate+16, sgr ptm+14, chitin+12, ptm+12, t1pks+10, transat-pks+12, nrps+8, terpene+6, siderophore+4, metallophore+4.

**Novelty keywords and weights:** transat-pks+18, enediyne+18, azoxy+18, thioamide+15, phosphonate+15, hgle+12, ranthipeptide+12, ripp+10, nrps+8, t1pks+8, t2pks+8.

**Diagnostic bonus:** +25 to AB or AF when a corroborated CCTT class-defining trigger fires. AF triggers: T43-NUC (nucleoside), T43-PTM (HSAF). AB triggers: T43-LAN, T43-LASSO, T43-THA, T43-PHO, T43-AMC, T43-BLA. Requires corroboration (see below). Tailoring-enzyme-only triggers (T43-HAL, T43-XHAL) do NOT grant this bonus.

**KCB novelty adjustment:** if kcb_cumulative > 10,000 → novelty −15 (strong similarity to known cluster); if kcb_cumulative is None → novelty +5 (no reference hit at all); if riq_score < 0.50 → novelty +10 (low recognition).

**RG-GMCI rescue bonus:** +8 if a HIGH_RG_GMCI_RESCUE link exists; +4 if MODERATE_RG_GMCI_CANDIDATE. Zero for primary-metabolism or pigment-flagged regions.

**Edge penalty:** Currently 0.0. The penalty was neutralized at v9.7.84 after empirical measurement on the AS cohort showed no truncation signature in base scores (mean AB: Interior 34.7, Edge 35.7, FC 35.3). Truncation uncertainty is now carried as architecture grade, not a score deduction. The penalty function is retained returning 0 for a future calibrated penalty.

**Final score formula:**
```
effective_penalty = max(0, penalty − (8 if high_rg else 4 if mod_rg else 0))
AB      = clamp(0,100, base_AB      + rescue_bonus − 0.35×effective_penalty)
AF      = clamp(0,100, base_AF      + rescue_bonus − 0.35×effective_penalty)
novelty = clamp(0,100, base_novelty + rescue_bonus − 0.20×effective_penalty)
```

**Lead-tier routing:** best = max(AB, AF, novelty). Exceptional ≥ 85; High ≥ 70; Medium ≥ 50. Below 50, a region with at least one resolved class outside the governed Inventory allow-list is **Low**; an allow-listed-only or unresolved region is **Inventory**. These are routing-prior labels over annotations, not evidence of production, activity, novelty, or biological housekeeping.

---

## Section 5: Score Guards and Downgrades

**Trigger corroboration** — A CCTT trigger only grants its bonus or exemptions if it is corroborated: it fired on a class-compatible locus with a matching architecture-class confidence. An uncorroborated trigger (e.g., T43-PHO on a T3PKS, or a trigger on a mobile-element-dominated region with no class-defining enzyme) is recorded for the judgment layer but grants no scoring effect.

**Tier-1 diagnostic floor** — If a corroborated class-defining trigger OR a class-concordant T1 self-resistance marker is present, and the lead tier would otherwise be Low or Inventory, the tier is floored to Medium. This prevents strong class-capacity evidence from being buried by a low keyword score; it does not establish activity. Tailoring-enzyme triggers alone (T43-HAL, T43-XHAL) do not trigger this floor.

**Primary-metabolism / pigment suppression** — Fires when ALL of: (a) a housekeeping/pigment core-gene marker is present in the BGC's own CDS; (b) the BGC's own product class is exclusively from {nrps-like, terpene, terpene-precursor, saccharide, arylpolyene, other, t2pks, t3pks, pks-like, fatty_acid, redox-cofactor, quinone_isoprenoid_chain}; (c) no Tier-1 diagnostic fired. Effect: caps base_AB to 25, base_AF to 20.

**Mobile-element demotion** — A region dominated by ICE/transposon mobility machinery and mis-typed as biosynthetic is capped at base AB=25, AF=20. A corroborated class signal exempts it. A resistance marker on a mobile-dominant region is only treated as self-resistance if class-concordant with the cluster's own product.

**KCB mis-anchor guards:** (a) aminoglycoside KCB anchor without a DOIS biosynthesis gene → strip aminoglycoside credit; (b) polyene KCB anchor with fewer than 4 PKS-KS domains → strip polyene AF credit. These prevent a similarity label from inflating a score when the architecture doesn't support the class.

**Enediyne guard** — The T43-ENE trigger fires on real enediyne domains AND on the hglE/hglD glycolipid KS false positive (PREV-001). Real enediyne: emit neutral [E-signal] note, no BSL-2 flag, no scoring change. hglE artifact: strip the +18 novelty credit. The BSL-2 per-BGC flagging doctrine is retired; handling of potentially hazardous chemistry is governed by lab SOPs.

**Standing-rule exclusions** — Three permanent exclusions cap tier to Inventory while preserving raw scores: (1) saccharide (pure sugar clusters, not sugar-tailored NRP/PK); (2) NAPAA (convergent, not habitat-informative); (3) hglE-KS-PREV-001 (habitat-non-specific glycolipid). The committed-class guard protects clusters that are primarily non-saccharide but carry a saccharide tailoring arm. NAPAA and hglE-KS bypass this guard.

**RiPP-fragment completeness floor** — A RiPP cluster that is Edge/Full-contig, <8 kb, and has no precursor captured is capped at Inventory, regardless of its base score. Prevents a lone LanM synthetase on a tiny contig fragment from floating to High priority.

**Corrected rank** — Assigned sequentially to BGCs NOT subject to standing-rule downgrade, NOT primary-metabolism/pigment-flagged, and NOT mobile-element-flagged. Downgraded rows keep scores but receive corrected_rank = None, keeping them visible without occupying lead positions.

---

## Section 6: Architecture Confidence (A–E)

Source: `parsers.py:architecture_grade`. A structural reliability grade independent of the routing score.

**Grade A** — Interior, has a committed biosynthetic core class, region ≥10 kb. "Coherent and complete." Highest confidence for structural interpretation.

**Grade B** — Interior AND (has core class OR strong KCB ≥10,000). "Limited/compact, or KCB-supported."

**Grade C** — Edge AND has core class. "Truncated but coherent; partial."

**Grade D** — Edge without core class; OR Full-contig with core class. "Truncated, limited annotation."

**Grade E** — All others. "Weak/ambiguous; inventory-level."

Display labels: A→High, B→Moderate-High, C→Moderate, D→Low-Moderate, E→Low.

**has_core** — True if the BGC's product text contains any of: {nrps, pks, ripp, lanthipeptide, terpene, saccharide, phosphonate, siderophore, metallophore, lassopeptide, thioamide, tomm, azole}.

**Two-level split-pathway rule** — For fragmented pathways: the pathway unit (the combined multi-BGC pathway) is assigned Grade C for structural interpretation. Individual fragments retain their standalone grades (A or B for the anchor fragment; D or E for secondary fragments). Finding a second fragment is confirmatory, not penalizing.

---

## Section 7: The Ten Genome-Wide Scans

All ten run on every `mamey run` inside `run_source_scans`. They consume the cached parse — no re-run of antiSMASH. Source: `mamey/source_scans.py`.

**1. KCB sweep** — Extracts the top KnownClusterBlast hit per BGC from the antiSMASH JSON and computes `kcb_top`, `kcb_score`, `kcb_proteins`. Also assigns `kcb_cumulative` for novelty scoring. Source: `mamey/antismash_evidence.py`.

**2. Hallucination-trap / claim-calibration** — Checks that reported scores match re-derived scores from the manifest evidence. Catches downstream transformations (merges, workbook builds) that silently drop evidence. Coverage gate: `assert_full_scoring_coverage` fails loudly if any BGC is unscored.

**3. FLBR megasynthase census** — Detects KS/C/A/T/E domains and docking domains across the genome; computes megasynthase module count and assigns STRONG/WEAK fragmentation flag. Very-Poor assemblies automatically demote FLBR results because fragmentation is expected.

**4. UMED maturation-enzyme detection** — Scans all CDS annotations for seven families of unusual maturation enzymes (see Section 9 patterns). Records in-cluster vs. GAP (out-of-cluster) presence. Feeds CCTT triggers for RiPP classes.

**5. CCTT trigger scan** — Applies all 18 T43-XXX trigger families plus 3 veto families to every BGC's CDS annotation tokens. Bitscore floor 150. Bonus ≤+2 per trigger, non-stacking. Source patterns: see Section 9.

**6. CGAD chitin/GH18/LPMO** — Scans full proteome for GH18, GH19, AA10, chitin-binding CBM, and GlcNAc tokens. Proteome-scope gated: must record scope (full genome vs. BGC-only) before issuing verdict. Not isolation-source gated: a positive call on a moss strain counts equally to one on a bee strain.

**7. Resistance scan** — Detects APH/Van/Erm resistance gene families with an HGT guard. Distinguishes genuine self-resistance (class-concordant with BGC product) from HGT cargo (resistance not matching BGC class). Three resistance tiers: T1 = class-concordant resistance (VanHAX for glycopeptide, APH for aminoglycoside); T2 = general resistance; T3 = transporter-only.

**8. bldA/TTA tiering** — Scans all BGC CDS for TTA (leucine-TTA) codons; locates *bldA* across the genome. Assigns T1–T4 tier (see bldA above). Note: non-actinomycetes often get spurious T4 calls because TTA is common in other phyla — this is a known and documented limitation.

**9. TFBS motifs** — Searches BGC flanking regions for 12 families of transcription-factor binding-site motifs (DasR, DmdR1, BldD, FuR, Zur, LexA, PhoP, ANR, GBL/AdpA, SARP/BTAD, PAS/LuxR, IolR). Recorded in `F2_Regulatory_TFBS` workbook sheet and `B4_Cross_Strain_Scans`.

**10. RGGMCI pairs** — Computes pairwise reconstruction scores for all BGC fragment pairs. See Section 8.

---

## Section 8: RGGMCI Pairwise Scoring

Source: `mamey/rggmci.py`. All weights are engineering judgment, not calibrated against a labelled set.

**Pairwise score components:**
- Reference adjacency: +8 (overlapping) / +7 (adjacent-nearby) / +3 (distant, caution) / +2 (shared ref, no interval) / +1 (otherwise)
- Protein support: +3 if min(a.nprot, b.nprot) ≥ 3, else +1; additional +2 if total ≥ 12
- Reference rank quality: +3 if both ranks ≤5; +1 if both ≤10
- Identity: +2 if min(mean_identity) ≥65%; +1 if ≥50%
- Token overlap: +min(3, shared reference-type tokens) + min(2, shared product tokens)
- Fragmentation context: +2 if either fragment is non-Interior; +1 if on different contigs

**Score tiers:** HIGH_RG_GMCI_RESCUE ≥ 14; MODERATE_RG_GMCI_CANDIDATE ≥ 9; LOW_SHARED_REFERENCE_SIGNAL < 9.

**Gate cascade (precision enforcement):**
- P-2 class compatibility: fragments must share a compatible class
- R1: demote if both drop class after exclusions
- R2: demote if neither fragment has strong reference
- R3: demote on noise-class signal on both sides
- Hub-degree guard: BGC linked to >4 other fragments is "promiscuous"; HIGH links beyond degree 4 are demoted to MODERATE_DEMOTED_HUB_PROMISCUITY

**Subject-tiling verdict:**
- COMPLEMENTARY_SPLIT — arms cover different reference regions → genuine split
- TERMINUS_TRUNCATION_SPLIT — arm severed at contig terminus → genuine split
- OVERLAPPING_PARALOG — arms cover same reference region → NOT a split (excluded)
- MIXED_SUBJECT_SIGNAL — ambiguous → manual review
- INSUFFICIENT_SUBJECT_DATA — no tiling data available

---

## Section 9: Scan Pattern Catalogs

Source: `docs/MARKER_CATALOG.generated.md`. Generated from `mamey/source_scans.py`; must not drift.

### CCTT Triggers (T43-XXX family, 18 families / 121 patterns)

| Code | Name | Key diagnostic genes/words |
|---|---|---|
| T43-HAL | Halogenase | halogenase, flavin-dependent halogenase, tryptophan halogenase |
| T43-XHAL | Fluorinase/chlorinase | fluorinase, chlorinase, salL, fla, SAM-dependent halogenase |
| T43-PHO | Phosphonate | phosphonate, pep mutase, phosphoenolpyruvate mutase |
| T43-NUC | Nucleoside (antifungal) | nikkomycin, polyoxin, nikJ, nikD, nikC, chitin synthase inhibit |
| T43-BLA | Beta-lactam | nocardicin, isopenicillin N synthase, pcbAB, pcbC, ACV synthetase, beta-lactam synthetase, bls, clavaminate synthase |
| T43-AMC | Aminocyclitol | aminocyclitol, DOIS, btrc, 2-deoxy-scyllo-inosose |
| T43-ENE | Enediyne | enediyne |
| T43-LAN | Lanthipeptide | lanthipeptide, lantibiotic, lanC, lanM |
| T43-LASSO | Lassopeptide | lassopeptide, lasso peptide |
| T43-THA | Thioamide | thioamide, ycaO |
| T43-DKP | CDPS/diketopiperazine | cyclodipeptide synthase, CDPS, diketopiperazine |
| T43-IDC | Indolocarbazole | indolocarbazole, rebeccamycin, staurosporine, indsynth |
| T43-PTM | HSAF/PTM tetramate macrolactam | HSAF, maltophilin, dihydromaltophilin, heat-stable antifungal, tetramate, xanthobaccin, frontalamide |
| T43-TET | Tetronate/spirotetronate | tetronate, spirotetronate, fkbH |
| T43-NN | N-N bond | N-N bond, diazo, creE, creD, azoxy, hydrazine |
| T43-PYE | Polyene macrolide (antifungal) | polyene macrolide, natamycin, pimaricin, candicidin, amphotericin, nystatin, filipin, linearmycin, mediomycin (25 patterns total) |
| T43-GPA | Glycopeptide | oxyB, oxyA, oxyC, dpgS, 3,5-dihydroxyphenylglycine, 4-hydroxyphenylglycine, glycopeptide (15 patterns total) |
| T43-BLT | Beta-lactone | betalactone, beta-lactone, salinosporamide, platensimycin, platencin, lactacystin |

**CCTT vetoes** (patterns that suppress false triggers):
- T43-NUC suppressed by: glycogen/trehalose context, nucleoside phosphorylase, sugar-kinase context (APH misreads)
- T43-ENE suppressed by: hglE/hglD context (glycolipid KS false positive — PREV-001)
- T43-DKP suppressed by: copalyl diphosphate synthase context (ent-CDPS, a terpene cyclase, collides with CDPS)

### UMED Patterns (7 families / 23 patterns)
LanP S8 protease · LanT C39 transporter-peptidase · FlaP/AplP S9 protease · M16B metalloprotease · YcaO/TfuA thioamide · RiPP RRE domain · nucleoside maturation enzymes

### CHITINASE Patterns (5 families / 15 patterns)
GH18 (chitinase, glycoside hydrolase family 18) · GH19 (gh19, glycoside hydrolase family 19) · AA10/LPMO (lytic polysaccharide monooxygenase) · CBM_CHITIN (chitin-binding, CBM) · GlcNAc (N-acetylglucosamine, nagABCD, DasR)

### RESISTANCE Patterns (6 families / 21 patterns)
Beta-lactamase fold · Erm methylase (23S rRNA methyltransferase, erythromycin resistance) · VanHAX-like (vanH, vanA, vanX, D-Ala-D-Lac) · APH/AAC (aminoglycoside phosphotransferase, acetyltransferase) · Fosfomycin (fomA, fomB) · Self-resistance general

### REGULATOR Patterns (14 families / 31 patterns)
DasR/GntR · LuxR · TetR · LysR · SARP (Streptomyces Antibiotic Regulatory Protein) · MarR · LacI · AraC · Two-component (response regulator, histidine kinase) · Fur/Zur (iron/zinc uptake regulator) · IolR · PhoP/PhoR · OsdR · GBL/AdpA (gamma-butyrolactone receptors, ArpA, ArpB, ScbR, BarA)

### TFBS Motifs (12 families / 14 patterns)
DasR-like palindrome · DmdR1 iron-box-like · LexA SOS-like · BldD-like · FuR-like · Zur-like · IolR-like · PhoP box-like · ANR/FNR-like · GBL/AdpA-like · SARP/BTAD-like · PAS/LuxR-like

### DOMAIN CLASS Patterns (20 families / 52 patterns)
NRPS: A (adenylation), C (condensation), T/PCP, E (epimerization), TE (thioesterase)
PKS: KS (ketosynthase), AT (acyltransferase), DH (dehydratase), ER (enoylreductase), KR (ketoreductase), ACP (acyl carrier)
RiPP: precursor peptide, YcaO/TOMM, halogenase
Tailoring: glycosyltransferase, methyltransferase, oxidoreductase, aminotransferase, transporter, regulator

### FLBR Patterns (4 families / 10 patterns)
mod_KS (modular ketosynthase) · hyb_KS (hybrid PKS-NRPS) · tra_KS (trans-AT PKS) · mega_NRPS (nonribosomal peptide synthetase)

### MOBILE ELEMENT Patterns (6 families / 30 patterns)
Integrase · Recombinase · Transposase · Conjugation elements · Tox/repeat (RHS, WXG) · Replication initiator

---

## Section 10: Output Package Structure

A sealed Mamey package directory contains the following files. All paths relative to `runs_<date>/<STRAIN_ID>/package/`.

| File | Content |
|---|---|
| `manifest.json` | Authoritative handoff JSON. All computed values, scan results, BGC metadata. The single source of truth for Sapote. |
| `OPEN_ME_FIRST.html` | Browser-readable package entry point. Links to all outputs with context. |
| `<ID>_2_inventory.csv` | Full BGC inventory: one row per BGC with coordinates, products, boundary, KCB, scores. |
| `<ID>_3_scan_states.json` | All ten scan states and their outputs. |
| `<ID>_4_triage_board.csv` | Ranked BGC board: Corrected_rank, AB, AF, novelty, CCTT_triggers, lead_tier. |
| `<ID>_4A_RGGMCI_ranked_pairs.csv` | Ranked split-pathway reconstruction pairs. |
| `<ID>_4c_AB_lead_board.csv` | Antibacterial lead board (DAPR AB). |
| `<ID>_4c_AF_lead_board.csv` | Antifungal lead board (DAPR AF). |
| `<ID>_5_workbook.xlsx` | Master per-strain workbook with all schema sheets. |
| `<ID>_8_strain_brief.pdf` | Auto-generated strain brief PDF. |
| `_8a…_8m_fig_*.png` | Figure suite: 13 figure types + companion `_data.csv` files. |
| `locus_maps/<BGC>_locus_map.svg` | Per-BGC gene-arrow diagrams. |
| `gold_figures/` | Gold-mode figure set (F01–F15): domain heatmap, class composition, etc. |
| `checksums_sha256.txt` | SHA256 for every file in the package. |
| `gate_validation.json` | Per-gate PASS/FAIL from `mamey validate`. |
| `run_phase_receipts.jsonl` | Per-phase START/DONE timing receipts. |
| `issue_log.md` | Non-fatal issues logged during the run. |
| `mode_b_templates/` | §1–§30 skeletons from `emit-modeb-template --batch`. |
| `judgment/` | Authored Mode B cards from `ingest-receipts`. |
| `<ID>_judgment_register.json` | Register of Mode B card completion status. |
| `blastp_online/` | BLASTp evidence store: per-BGC overlay CSVs. |
| `gene_context.jsonl` | Normalized per-CDS gene context (domains, annotations). |
| `Literature_Search_WorkOrder.md/json` | Literature search handoff for a separate session. |

---

## Section 11: Workbook Schema (All Sheets)

Source: `docs/WORKBOOK_SCHEMA.md`. Sheet codes are stable identifiers; names are display labels.

### Section A — Project Administration
| Code | Sheet | Owner | Content |
|---|---|---|---|
| A1 | A1_Dashboard | Auto | Project summary stats, version, strain count |
| A2 | A2_Strain_Registry | Both | One row per strain: taxonomy, assembly, scores, status |
| A3 | A3_Run_Manifest | Runner | One row per Mamey run |
| A4 | A4_Completeness_Audit | Auto | Per-strain sheet/field population status |

### Section B — BGC Inventory (Mamey extraction)
| Code | Sheet | Key columns |
|---|---|---|
| B1 | B1_BGC_Master | strain, BGC_ID, contig, region, start, end, length_kb, products, boundary, arch, kcb_top, kcb_score, cctt_triggers, resistance_tier, tta_tier, ab_auto, af_auto, novelty_auto, lead_tier_auto |
| B2 | B2_Product_Class_Matrix | Strain × product class count matrix (raw, includes DROP classes) |
| B3 | B3_Known_Cluster_Matrix | Strain × KCB top-hit count matrix |
| B4 | B4_Cross_Strain_Scans | Strain × scan totals (DasR TFBS, CCTT, CGAD, bldA, resistance, RGGMCI pairs) |

### Section C — Judgment (Sapote)
| Code | Sheet | Content |
|---|---|---|
| C1 | C1_DAPR_Antibacterial | Ranked AB leads. Columns: Rank, strain, BGC_ID, Product_Class, AN_Score, WL_Score, Rationale, KCB_Provenance, Activity_Ref |
| C2 | C2_DAPR_Antifungal | Ranked AF leads (same schema) |
| C3 | C3_Lead_Tier_Summary | One row per strain: top AB lead, top AF lead, tier, band |
| C4 | C4_Strain_Decision_Table | Composite score, recommended action per strain |

### Section D — RGGMCI and split-locus rescue
| Code | Sheet | Content |
|---|---|---|
| D1 | D1_RGGMCI_All_Strains | Per-strain pair counts, promoted groups, state |
| D2 | D2_RGGMCI_Top_Pairs | Top 10 HIGH pairs per strain |
| D3 | D3_RGGMCI_Promoted | Promoted rescue groups with evidence chain |
| D5 | Fragment_Rescue_Tiers | Assembly + fragment-rescue tier A–D |

Fragment Rescue Tier thresholds: A = N50 ≥ 1,000,000 bp; D = EFLS_Pairs < 20; B = EFLS_Pairs ≥ 600; C = otherwise.

### Section E — Deep Analysis (Mode B)
| Code | Sheet | Content |
|---|---|---|
| E1 | E1_Mode_B_Index | BGCs with completed Mode B cards |
| E2 | E2_Comparative_Pairs | Ortholog/paralog pairs with protein %ID |
| E3 | E3_Megacluster_Registry | BGCs >150 kb |
| E4 | E4_A_Domain_Summary | NRPS A-domain specificities |

### Section F — Ecology and Regulatory Context
| Code | Sheet | Content |
|---|---|---|
| F1 | F1_Ecology_Readiness | Per-strain: taxonomy, source, habitat, CGAD/TFBS/lead readiness |
| F2 | F2_Regulatory_TFBS | TFBS hits (deployed as "TFBS_Motifs") |
| F3 | F3_Ecology_Theme_Board | Cross-strain ecological themes |

### Section G — Literature and Validation
| Code | Sheet | Content |
|---|---|---|
| G1 | G1_Literature_Index | Per-BGC citation/evidence entries |
| G2 | G2_Validation_Roles | Per-strain validation assignment |
| G3 | G3_Hallucination_Trap_Audit | Trap checks with disposition |

### Section H — Handoff and Audit
| Code | Sheet | Content |
|---|---|---|
| H1 | H1_Handoff_Log | Platform handoff events with SHA-256 |
| H2 | H2_Gap_Queue | Outstanding gaps with priority |
| H3 | H3_Schema_Version | Schema version, column definitions |

**B6 (addon)** — B6_Compound_Reference. Added at engine 1.9.107. Per-BGC NP Atlas lookup: npclassifier class, formula, exact_mass, [M+H]⁺, [M+Na]⁺, InChIKey, primary DOI. Requires the NP Atlas addon files. INVENTORY_ONLY — no genus-restriction or product-identity claim.

---

## Section 12: Mode B Card Contract (§1–§30)

Source: `mamey/data/mode_b/modeb_full30_corrective_contract.json`, schema `modeb_corrective_full30_v1`. Generated from `tools/regen_modeb_contract_docs.py`.

### Always-required sections (§1–§20, §28, §30)
| § | Title | What it must contain |
|---|---|---|
| 1 | Identity and node/region | BGC ID + contig/region citation on first mention |
| 2 | Why this BGC was selected | Priority axis, score, triggers that drove selection |
| 3 | Boundary and assembly status | Edge status, assembly tier, truncation caveat if applicable |
| 4 | Gene-by-gene interpretation | Prose + table; must include protein_length_aa; explain how genes work together |
| 5 | Core biosynthetic logic | Domain architecture → structural consequences; not just naming |
| 6 | Tailoring and maturation logic | Tailoring enzymes and their predicted modifications |
| 7 | Transport, resistance, and regulation | Export, self-resistance, regulatory genes |
| 8 | Comparator/KCB interpretation | KCB similarity analysis; architecture wins when discordant |
| 9 | Alternative hypotheses | Each alternative: state it, evidence for, evidence against, conclusion |
| 10 | Fragmentation and co-capture risks | Assembly artefacts that could affect interpretation |
| 11 | Product-family interpretation | Tailoring complement → scaffold complexity; what novelty means structurally |
| 12 | Bee/microbe ecological interpretation | Mechanism, not just context; host-specific chemical ecology challenge |
| 13 | Antibacterial/antifungal relevance | Mechanism and confidence tag |
| 14 | What cannot be claimed | Explicit claim ceiling |
| 15 | Missing evidence | Evidence gaps and next steps |
| 16 | BLASTP/HMMER next steps | Priority queue; emit FASTA files after this section |
| 17 | LC-MS / fermentation implications | Predicted masses, extraction strategy |
| 18 | Figure/locus-map notes | Figure content and interpretation |
| 19 | Final Mode B judgement | Evidence summary → alternative rejection → claim ceiling → confidence tags |
| 20 | Next actions | Specific numbered experimental and bioinformatic actions |
| 28 | Evidence provenance ledger | Claim-by-claim: observed/computed/inferred/assumed tagging |
| 30 | Experimental decision tree | Open questions → experiments → programme consequences |

### Conditional sections (fire on predicate)
| § | Title | Predicate |
|---|---|---|
| 21 | Precursor mass ladder | Any RiPP BGC |
| 22 | RiPP database search | Any RiPP BGC |
| 23 | Heterologous expression | MATURATION_GAP present OR novel compound class |
| 24 | Scaffold novelty score | Novel compound / no MIBiG hit |
| 25 | Genome neighbourhood | Isolation-worthy BGC (HIGH or PRIORITY_ISO lead tier) |
| 26 | OSMAC protocol | Fermentation-selected BGC |
| 27 | Self-resistance assessment | Any antimicrobial candidate (default for AB/AF leads) |
| 29 | Cross-cluster interactions | Strain has >3 high-priority BGCs |

### Interpretive Floor Requirements (source: `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md`)

**§5 floor:** Must connect domain architecture to structural consequences. Required for T1PKS/NRPS/hybrid: (1) what the domain arrangement produces at the molecular level; (2) what structural feature a specific domain determines; (3) one sentence distinguishing from nearest comparator based on domain evidence. "The KS domain catalyses Claisen condensation" fails this floor.

**§9 floor:** Each alternative must be weighed. Required: state the alternative, evidence for, evidence against, closing sentence on most parsimonious interpretation.

**§11 floor:** Tailoring complement must connect to scaffold complexity. Required: if more P450s than reference → state what the extra implies; if ER at unusual position → state structural consequence; if no MIBiG hit → state it is a novel compound class, not just "no hit found."

**§12 floor:** Must reason through mechanism, not just name context. Required: specific host chemical ecology challenge, mechanism by which this compound class addresses it, relevant literature citation with specific finding, confidence tag.

**§19 floor:** Must be an argument structure: (1) evidence summary; (2) alternative rejection with reference to §9; (3) claim ceiling (what evidence supports AND what it does not); (4) confidence tags. "Capacity consistent with X" alone fails this floor.

---

## Section 13: Claim Safety Vocabulary

**Capacity consistent with** — The mandatory phrase for any product class claim. "Biosynthetic capacity consistent with antifungal polyene class" is correct; "produces an antifungal polyene" is not. Claims are capacity-level because the BGC evidence establishes biosynthetic potential, not confirmed production.

**Confidence tags** (observed / computed / inferred / assumed):
- **observed** — directly present in a named field, file, or database hit
- **computed** — derived by a stated deterministic rule
- **inferred** — drawn from multiple observed facts by reasoned argument; defensible but not direct
- **assumed** — default position in absence of contrary evidence; must be flagged explicitly

**Extract-level bioactivity** — Bioactivity data (MRSA inhibition, Candida inhibition) belongs to the crude extract, not to any individual BGC. "The strain shows extract-level antibacterial activity" is correct; "BGC007 is the antibacterial" is not, unless activity has been bioassay-guided to a specific fraction linked to that cluster's product.

**Never antifungal-negative / never antibacterial-negative** — A strain with no recorded bioassay activity in a particular axis is not "negative" — it is untested under the conditions that might elicit that activity. Contrast strains by biosynthetic mechanism, not phenotype.

**KCB = similarity, not identity** — KnownClusterBlast reports sequence similarity to a reference. It does not identify the compound. A 90% KCB score to nystatin means 90% of the proteins share homologs with the nystatin cluster, not that the compound is nystatin.

**Affiliation** Not UW-Madison. All outputs including workbooks, compiled reports, and public-tier deliverables use this affiliation.

**NAPAA exclusion** — NAPAA domains are excluded from all cross-habitat and within-habitat comparative claims because they are ubiquitous and convergent, not ecologically informative.

---

## Section 14: CLI Commands Reference

All commands: `python -m mamey <subcommand> [options]`.

| Subcommand | Purpose |
|---|---|
| `doctor` | Environment self-check; confirms all deps, file permissions, bundle integrity |
| `inspect <antiSMASH.zip>` | Pre-run preview of raw antiSMASH ZIP content |
| `run` | Main extraction run. Key flags: `--strain`, `--display`, `--input-zip`, `--outdir`, `--mode gold`, `--release PUBLIC/PRIVATE`, `--capped-session`, `--json-evidence off/bounded`, `--master` |
| `validate <pkg>` | Seal a completed package; checks structure, checksums, schema |
| `explain <pkg>` | Narrative walkthrough of a sealed package |
| `list-bgcs <pkg>` | BGC inventory from triage board; `--axis rank/ab/af`, `--top N`, `--json` |
| `emit-modeb-template` | Emit §1–§30 skeleton pre-filled from package. `--bgc <BGC_ID>` or `--batch --scope all/top/leads/pending` |
| `verify-modeb <card.md>` | Validate authored Mode B card: structure + depth. `--interp` (v9.7.338) adds the Mode-B interpretation/judgment gate (alternative reads, resolving experiment, capacity framing) — **WARN-only**, never a structural refuse |
| `guide` | Emit BGC Guide skeleton. `--blastp-store`, `--audience both`, `--format both` |
| `verify-guide <guide.md>` | Validate authored BGC Guide: no residual LAY slots, no thin Parts |
| `ingest-receipts` | Persist Sapote Mode B cards into durable store. `--receipt`, `--auto-detect`, `--card` |
| `blastp-online` | Submit BGC proteins to NCBI BLASTp. Real network call; fail-closed on error |
| `ingest-blastp` | Ingest Hit Table CSV or BLAST XML2 into evidence store |
| `render-all-figures` | Post-seal figure suite: smoke, brief, locus-maps, figure-suite, domain-level |
| `compile-report` | Assemble compiled analysis report. `--strict` exits 1 on open SAPOTE slots |
| `write-narrative` | Write a narrative section into package. Runs claim-safety linter; exit 3 on violation |
| `compare` | Two-strain comparison (formerly `gemini`). Requires pyswrd addon |
| `workflow` | Sapote workflow status gate (W0–W10). `--strict`, `--json` |
| `mode-b` | Triage top-leads table (NOT the §1–§30 card) |
| `comparator-coverage` (v9.7.338) | Two-denominator MIBiG comparator-coverage evidence for a sealed package: matched/all-locus-genes **and** matched-core/all-defining-core, plus a housekeeping-only collision flag. Report-only, non-scoring — the false-positive killer for KCB comparators carried by transporters/regulators. `mamey comparator-coverage <pkg>` → `<STRAIN>_3b_comparator_coverage.csv` + JSON summary |
| `good-guesses` (v9.7.338) | Claim-safe interpretive-priors deliverable: per notable BGC, the single best class-level capacity read, tagged `solid`/`rare`/`remarkable`/`notable`/`interesting`, with a confidence band and the resolving experiment. `mamey good-guesses <root> --out <dir> [--docx] [--pdf]` → `GOOD_GUESSES.md`/`.csv`/`.docx`/`.pdf`. Judgment deferred — capacity hypotheses only |
| `af-dossier` (v9.7.338) | Antifungal (AF) Lead Dossier: the AF lead board joined against an optional measured-*Candida* activity crosswalk. Report-only. `mamey af-dossier <root> --out <dir> [--activity-table <csv>]` → `AF_LEAD_DOSSIER.csv`/`.md` |
| `novelty-shortlist` (v9.7.338) | Shortlist of the strongest reference-dark / novelty-prior candidates (high AB/AF capacity, no MIBiG family anchor). Novelty is a prior, not proof. `mamey novelty-shortlist --package <pkg> --out <dir>` |
| `realistic-count` (v9.7.338) | Honest corrected BGC denominator — nets fragments, primary-metabolism loci and duplicate/split calls out of the raw region count so headline BGC totals are not inflated. `mamey realistic-count <pkg>` |
| `domain-reference` (v9.7.338) | Emit the domain-level reference sheet (KS/AT/KR/C/A/PCP… glossary + per-BGC ordered-domain readout) for authoring §4/§5 Mode-B content. `mamey domain-reference --package <pkg> --out <dir>` |
| `modeb-export` (v9.7.338) | Render authored Mode-B §1–§30 cards to Word + PDF for hand-off. `mamey modeb-export --package <pkg> [--bgc <BGC_ID>] --out <dir>` → `.docx` + `.pdf` |
| `cohort-leads` (v9.7.338) | Cross-strain priority-leads CSV — one ranked lead board spanning every sealed run in a cohort. `mamey cohort-leads --runs-dir <runs_gold> --out <dir>` → `PRIORITY_LEADS.csv` |
| `cohort-assemble` (v9.7.338) | Assemble/refresh the cross-cohort master workbook from a directory of sealed per-strain gold runs. `mamey cohort-assemble --runs-dir <runs_gold> --master <cohort_master.xlsx>` |
| `signoff` (v9.7.338) | Analysis QC gate ("would a master's student sign off?") over a phylogenomic tree/analysis — outgroup sanity, ANI-boundary honesty, label integrity, support/sampling. **Advisory** (never blocks). `mamey signoff <tree.treefile>` (also `python tools/signoff_check.py <tree.treefile>`) |
| `figures kcb-locusmap` (v9.7.338) | Offline KnownClusterBlast comparative locus map — the query BGC's gene-arrow track aligned against its KCB/MIBiG comparator, rendered with zero network. `mamey figures kcb-locusmap --package <pkg> --bgc <BGC_ID> --out <png>` |

**`--capped-session`** (formerly `--chatgpt-safe`) — Applies timeout-safe defaults: skips figure rendering (`--brief none`), caps streaming. Use `render-all-figures` post-seal to recover figures. Gold mode completes in ~1 minute on a typical genome.

**`--json-evidence off`** — Suppresses the large evidence array output. Default for capped sessions.

**`--json-evidence bounded`** — Streams evidence via ijson with record cap and size cap. Memory-safe for large antiSMASH JSONs.

---

## Section 15: Mamey Module Index

All 105 Python modules in `mamey/`. Source: docstrings extracted directly.

**Core extraction pipeline:** `parsers.py` (antiSMASH JSON/GBK parsing), `assembly.py` (assembly stats, tier), `scoring.py` (AB/AF/novelty scoring), `antismash_evidence.py` (KCB, RiQ, evidence extraction), `source_scans.py` (all ten genome-wide scans), `rggmci.py` (split-pathway reconstruction), `efls.py` (edge-flank linkage scoring).

**BGC annotation:** `compound_class.py` (deterministic class annotation), `architecture_first.py` (KCB-blind pathway classification), `diagnostic_rescue.py` (class-aware trigger rescue), `class_architecture.py` (architecture-based capacity layer), `bgc_decomp.py` (two-model decomposition), `two_pathway.py` (multi-pathway detection), `dkp_cdps.py` (DKP/CDPS scanners).

**BLASTp pipeline:** `blastp_online.py` (NCBI web submission + async polling), `blastp_ingest.py` (Hit Table and XML2 ingest), `blastp_evidence_store.py` (durable per-BGC store), `blastp_followup.py` (result parsing and batch planning), `blastp_batch_emitter.py` (FASTA emitter), `bgc_blastp_panel.py` (large modular PKS/NRPS panel exporter), `blastp_ebi.py` (EBI BLASTp transport), `ebi_xml_to_outfmt10.py` (EBI XML → outfmt10 converter).

**HMM pipeline:** `bgc_walk.py` (ordered HMM readout along a BGC), `hmm_blastp_adjudicate.py` (intrinsic HMM + BLASTp reconciliation), `mamey_markers.py` (marker registry), `mamey_cassettes.py` (cassette registry), `registry_detector.py` (registry-backed detector loader).

**Mode B and deliverables:** `modeb_template_emitter.py` (§1–§30 skeleton emitter), `modeb_structure_gate.py` (structural validator), `mode_b_quality_gate.py` (depth enforcement), `modeb_class_checklist.py` (class-triggered content expectations), `modeb_round.py` (Mode B round orchestrator), `modeb_blastp.py` (per-BGC FASTA emitter), `judgment_store.py` (Mode B durable register), `mode_b_receipt.py` (Sapote→store front door), `compile_report.py` (compiled report assembler), `enrichment_sections.py` (Mode B §11–§20 generators), `s3_census_generator.py` (§3 gene-census deepener), `report_card.py` (L0–L1 per-BGC report card), `authored_verify.py` (verify finished deliverables), `deep_data.py` (gene-level deep-data extraction).

**Interpretive-priors and cross-strain deliverables (v9.7.338):** `good_guesses.py` (claim-safe interpretive-priors report — `good-guesses`, flavours solid/rare/remarkable/notable/interesting), `mibig_comparator_coverage.py` (two-denominator comparator-coverage evidence — `comparator-coverage`, report-only false-positive killer), `af_dossier.py` (Antifungal Lead Dossier × measured-*Candida* join — `af-dossier`).

**BGC Guide:** `bgc_guide.py` (layered per-gene Guide), `bgc_figures.py` (publication figures from antiSMASH).

**Figures:** `figures_smoke.py` (smoke-mode figures from triage CSVs), `figures_sapote.py` (Sapote-layer figures), `figures_extra.py` (extended auto-emit figures), `cohort_figures.py` (gold gene/domain figures), `domain_figures.py` (domain-level figures), `locus_map.py` (gene-arrow locus maps), `cross_strain_figures.py` (cross-strain figure emitter), `cross_strain_threads.py` (shared biosynthetic-thread arc), `collection_figures.py` (metadata-gated collection figures), `master_figure_atlas.py` (boss-ready atlas), `mamey_native_figures.py` (workbook-native figures), `render_brief.py` (extraction-layer strain brief), `render_all_figures.py` (post-seal aggregate runner), `boundary_palette.py` (single-source boundary tier colours), `render_safe.py` (layout-safe rendering helpers).

**Workbook and output:** `workbook.py` (master workbook writer), `master_workbook.py` (master workbook orchestration), `workbook_dedup.py` (idempotent append), `workbook_schema_check.py` (schema validator), `b1_normalizer.py` (B1 sheet normalizer), `b2_structured_evaluators.py` (B2 Phase 2 evaluator framework), `lead_board.py` (per-strain lead board).

**Cross-strain analysis:** `comparative_pairs.py` (E2 comparative pairs), `cohort_cards.py` (cohort-scale Mode B orchestrator), `cohort_synthesis.py` (cross-strain synthesis writer), `cohort_resolver.py` (cohort/actinomycete status), `cohort_class_heatmap.py` (class capacity heatmap), `rare_motif.py` (cross-strain rare motif detection), `compare.py` (two-strain comparison layer), `cnbu.py` (Class-Normalized BGC Units), `background_control.py` (known-compound background control branch).

**NP Atlas and references:** `npatlas_resolver.py` (B6 NP Atlas lookups), `genus_reference.py` (shipped genus reference banks), `adjudication.py` (curated adjudication overlay), `antimicrobial_recall.py` (boost-only compound-anchor capacity layer), `bacterial_pks_marker_debug.py` (PKS/macrolide marker debug).

**Claim safety and validation:** `claim_safety_gate.py` (package-level claim safety), `boundary_audit.py` (deterministic↔judgment contract), `mode_b_quality_gate.py` (Mode B depth enforcement), `concordance.py` (reference-BGC concordance), `precision.py` (false precision elimination), `fragment_ceiling.py` (fragment claim ceiling).

**Infrastructure:** `parsers.py` (antiSMASH JSON/GBK), `_gbk_shim.py` (minimal GBK parser, no Biopython), `antismash_evidence.py` (KCB/RiQ extraction), `manifest_schema.py` (canonical field names), `models.py` (data models), `packaging.py` (package construction), `seal_package.py` (final QC gate), `validate.py` (package validation), `recovery_status.py` (status semantics), `package_addons.py` (post-package emitters), `package_inspector.py` (B4/B6/B7 exploration), `package_map.py` (PACKAGE_MAP.json generator), `id_resolver.py` (BGC identifier crosswalk), `crosswalk.py` (BGC-to-contig crosswalk), `serialize.py` (deterministic↔judgment boundary emission).

**Release and deployment:** `release_qa.py` (release QA + dual-LLM handoff gates), `legacy_feature_gate.py` (legacy feature matrix gate), `llm_handoff.py` (dual-LLM handoff receipt), `handoff.py` (portable handoff bundler), `dedup_and_guard.py` (dedup, release guard, fragment classification), `merge_policy.py` (de-duplication/supersedure policy), `session_resume.py` (session-state reducer).

**Workflow and timing:** `sapote_workflow.py` (W0–W10 gate driver), `cli.py` (Mamey CLI, all subcommands), `timing.py` (machine-readable timing telemetry), `chatgpt_commands.py` (capped-session subcommands), `output_checklist.py` (deliverable checklist).

**Domain-level analysis:** `domain_level.py` (native domain-level Mode B enrichment), `clusterblast_genes.py` (ClusterBlast per-gene correspondence), `tab_reconcile.py` (antiSMASH tab reconciliation), `bgc_walk.py` (ordered HMM readout), `singleton_filter.py` (biosynthetic-relevance filter).

**Special scanners:** `nrps_predictions.py` (antiSMASH NRPS prediction recovery), `raw_antismash_triage.py` (guided pre-extraction genome triage), `split_detector.py` (contig-end split detection), `wise_fragmented_pks.py` (WISE fragmented PKS/NRPS queue), `directed_pks_study.py` (directed PKS study scaffold), `genome_explore.py` (question-driven genome exploration), `nominal_length.py` (BGC length normalization), `gene_context.py` (normalized per-CDS gene context), `gene_by_gene.py` (per-gene table for Mode B leads).

**External interfaces:** `diamond_align.py` (offline DIAMOND alignment), `external_adapters.py` (scan_status builder), `compat_v941.py` (v9.4.1 compatibility fields), `cell_provenance.py` (cell provenance tracking), `citation_compact.py` (citation-compact helpers), `wheelhouse.py` (Wheelhouse lab-data CLI), `gemini.py` (deprecated shim → compare.py).

---

## Section 16: Gates and Quality Checks (Ordered)

Source: `docs/TRIGGER_ROUTING.md`, `docs/SAPOTE_WORKFLOW_CONTRACT.md`.

1. `mamey doctor` — Environment pre-check (deps, file permissions, bundle files)
2. `mamey inspect` — Pre-run antiSMASH ZIP preview
3. `mamey run` — Extraction (includes all ten scans)
4. `mamey validate` — Package seal (structure + checksums + schema)
5. Architecture-first assessment — Domain-based classification before KCB (internal)
6. INTERPRETIVE_FLOOR_CHECK — §5/§9/§11/§12 depth before §19 (behavioral)
7. `mamey verify-modeb` — Mode B card structure + depth. **The §4 Mode-B evidence gate now bites (MB-01, v9.7.338):** on a card whose strain carries a BLASTp panel, §4 asserting `CONFIRM/REFINE/OVERTURN` without the reconciled per-gene closest-match table now raises `EVIDENCE_GAP`/`COVERAGE_UNVERIFIED` (WARN) instead of the old dead-on-every-card pass. `--interp` (WARN-only) additionally checks interpretive judgment (alternative reads, resolving experiment, capacity framing)
8. `mamey verify-guide` — BGC Guide authored prose completeness
8b. `mamey signoff` — analysis QC gate over a phylogenomic tree/analysis (outgroup sanity, ANI-boundary honesty, label integrity, support/sampling). Advisory, never blocks (v9.7.338; also `tools/signoff_check.py`)
9. Sapote Workflow Contract W0–W10 (`tools/sapote_workflow.py`)
10. `mamey compile-report --strict` — Open narrative slot detection
11. `tools/check_deliverable_suite.py` — 13-item deliverable contract enforcement
12. `tools/sapote_judgment_receipt.py` — gold_completeness write-back
13. `tools/claim_safety_linter.py` — Claim-safety linter (invoked by `write-narrative`)
14. Novelty contradiction guard — Conservation background vs. floor detection (engine internal)

---

## Section 17: Named Trigger Constants

Source: `docs/TRIGGER_ROUTING.md`.

| Constant | Meaning |
|---|---|
| `CHATGPT_EXECUTION_SLICE_LOADED` | New default Sapote execution controller is active |
| `MAMEY_COMPLETE_HANDOFF_REQUIRED` | Present code-backed outputs, offer/produce prompt-backed set |
| `ANALYSIS_COMPLETE_DELIVERABLE_OFFER` | Auto-produce or offer deliverable set after analysis |
| `LOCUS_MAP_PRESENTATION_REQUIRED` | Surface all locus maps to user |
| `POOR_TIER_EDGE_EQUALITY` | POOR/VERY_POOR: rank by score, not boundary; all BGCs visible |
| `FULL_MODEB_REQUEST_DETECTED` | §1–§30 contract; validated by `modeb_structure_gate.lint_card` against `mamey/data/mode_b/modeb_full30_corrective_contract.json` |
| `INTEGRATED_TABLE_AS_COMPANION` | Emit table alongside card; never substitute for card |
| `CLAIM_CEILING_REQUIRED` | §19+§20 receipts; suppress per-gene claim repetition |
| `OFFLINE_EVIDENCE_ALLOWED` | BLASTp absence does not block Mode B |
| `INTERPRETIVE_FLOOR_CHECK` | Expand §5/§9/§11/§12 before drafting §19 |
| `WISE_PKS_QUEUE_DETECTED` | Use wise_fragmented_pks.py FASTA queue |
| `CROSS_STRAIN_COMPARISON_REQUESTED` | Separate comparative report; never replaces Mode B |
| `PDF_DELIVERABLE_REQUESTED` | Narrative PDF + source MD + evidence CSV + manifest |

---

## Section 18: DAPR Activity Framework

Source: `docs/DAPR_CLASS_FRAMEWORK.md`. All class-activity associations are literature-verified against the 18-strain cohort.

### Antifungal buckets (highest confidence first)
Polyenes (nystatin, amphotericin, candicidin, filipin, linearmycin) · Peptidyl nucleosides (nikkomycin, polyoxin, pacidamycin) · PTM tetramate macrolactams (HSAF, dihydromaltophilin, frontalamide, ikarugamycin) · Bacillus lipopeptides (iturin, fengycin; atypical in Streptomyces) · Phenylpyrroles (pyrrolnitrin) · Glycolipopeptides (occidiofungin) · Phenazines · Polyether ionophores (CYTOTOXIC CAUTION) · Macrolide ATP-synthase inhibitors (oligomycin; CYTOTOXIC CAUTION)

### Antibacterial buckets
Aminoglycosides (streptomycin, neomycin, kanamycin, apramycin) · Glycopeptides anti-MRSA (vancomycin, teicoplanin) · β-lactams/carbapenems (thienamycin, clavulanate) · Lipopeptides membrane (daptomycin, A54145, glycinocin) · Lanthipeptides/thiopeptides (nisin, thiostrepton) · Aromatic T2PKS (formicamycin, tetracyclines) · Macrolides (erythromycin, tylosin) · Orthosomycins (evernimicin) · Aminocoumarins (novobiocin) · Phosphonates/FabF/moenomycin · Liponucleosides (tunicamycin, muraymycin)

### Routed OUT (cytotoxic or ecological, not antibacterial/antifungal leads)
Indolocarbazoles (staurosporine, rebeccamycin) · Enediynes (kedarcidin; [E-signal] only, no drug-lead claim) · Aureolic acids (mithramycin) · Anthracyclines (cosmomycin) · Hsp90 ansamycins (geldanamycin) · Angucycline-diazo (kinamycin) · Aminoquinone (streptonigrin) · Siderophores/metallophores (coelichelin, desferrioxamine; ecological iron-acquisition, not direct antibiotic) · arylpolyene (flexirubin-type pigment; oxidative-stress, NOT antifungal)

---

## Section 19: Evidence and Provenance Vocabulary

**operator_supplied** — Citation/provenance row came from runtime evidence already present in the package. No additional verification needed for this row.

**citation_needed** — Literature support is missing. Must be filled by a separate literature-search pass. Source: `docs/CITATION_COMPACT_MODE.md`.

**PASS_STRUCTURE** — Package structure, citation ledger, work-order files, compact reports, manifest tracking, and checksum tracking passed validation. Does NOT mean every literature claim has been manually verified.

**Literature_Search_WorkOrder** — A safe handoff file for a web-literature session. It is a search instruction, not a verified fact.

**BGC citation format** — First mention in any deliverable: `BGC007 (NODE_1_length_406707 · region001)`. Subsequent mentions in same section: `BGC007 (NODE_1 · r001)`. Bare BGC IDs without node/region are never acceptable.

**conservation_background** — The genome-wide median BLASTp identity across all BGC overlays. Added at v9.7.240 to contextualize per-BGC identity values. A BGC at 94% identity in a genome with 95.4% background (Δ−1.6%) is not distinctive — but neither is it a weak novelty signal; the background itself is saturated (conservation_saturated = True).

**conservation_saturated** — True when the conservation_background itself clears the novelty floor (≥90%). When saturated, the absolute identity value carries little novelty signal; judge by delta from background, not absolute.

---

## Section 20: Operational Protocol (CDSW)

**CDSW Protocol** — the source lab Documented Session Workflow. Three mandatory steps for every session:
1. At session start, search complete conversation history and review SESSION_START_MANIFEST.md.
2. At task completion, present up to 6 (minimum 3) strategically differentiated next paths as a plain-text numbered list.
3. Acknowledge prior context explicitly before beginning new work.

**Multi-chat architecture** — Standard operating model: separate Claude sessions run simultaneously for patch application, audit, and strain analysis. The "patch chat" role is performed by other Claude instances, not ChatGPT. Past sessions' findings are available via conversation search.

**Full Analysis Mode override** — Active. Every BGC receives full §1–§30 Mode B treatment. No compact/flag/minimal entries. Compilation order: Lay Guide → Synopsis → Chapter → KCB sweep → Mode B (BGC# order) → Ferm Card.

---

*Sources: `mamey/source_scans.py` (scan patterns), `docs/reference/01_Math_Reference_VolI.md` (scoring formulas), `docs/WORKBOOK_SCHEMA.md` (workbook structure), `docs/MARKER_CATALOG.generated.md` (pattern catalogs), `docs/FULL_MODEB_30_SECTION_CONTRACT_v97150.md` (Mode B contract), `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md` (depth floors), `docs/DAPR_CLASS_FRAMEWORK.md` (activity framework), `docs/TRIGGER_ROUTING.md` (trigger constants), `docs/SAPOTE_WORKFLOW_CONTRACT.md` (W0–W10 gate order), `mamey/*.py` module docstrings. All formulas transcribed from source; all pattern counts verified by direct inspection.*

---

## Section 21: Figure Output System

All figures are pure extraction-layer outputs — no LLM judgment required. Every PNG ships with a companion `_data.csv` file. All captions and labels use capacity-level language and KCB = similarity. The saccharide policy (omit pure-saccharide regions from figures, cover in text only) is enforced via a single source of truth: `mamey/figure_policy.py:is_pure_saccharide`. Sources: module docstrings from `render_brief.py`, `figures_sapote.py`, `figures_extra.py`, `figures_smoke.py`, `cohort_figures.py`.

### Per-strain figure suite (_8a through _8n, +_data.csv per figure)

| File suffix | Name | Content | Source module |
|---|---|---|---|
| `_8a_fig_landscape.png` | Landscape overview | Top 15+ BGCs ranked by AB score, horizontal bar chart coloured by edge status (Interior/Edge/Full-contig) and assembly tier. Strain header, assembly tier legend, BGC ID labels with KCB anchor. | `render_brief.py:fig_landscape` |
| `_8b_fig_composition.png` | Class composition | Stacked bar of BGC product class counts. Standing-rule exclusions (saccharide, NAPAA) removed before rendering; pure-saccharide BGCs omitted. | `render_brief.py:fig_composition` |
| `_8c_fig_dapr_scatter.png` | DAPR dual-track scatter | Scatter plot: AB score (x) vs AF score (y), one point per BGC, coloured by lead tier. BGCs above LEAD_AB_MIN (70) or LEAD_AF_MIN (44) are labelled. | `figures_sapote.py:fig_dapr_scatter` |
| `_8d_fig_ab_ranked.png` | Antibacterial priority | Horizontal bar chart of top 30 BGCs by AB score, coloured by edge status. Capacity-level axis label. | `figures_sapote.py:fig_ab_ranked` |
| `_8e_fig_af_ranked.png` | Antifungal priority | Same as _8d but by AF score. | `figures_sapote.py:fig_af_ranked` |
| `_8f_fig_funnel.png` | Claim-safety funnel | Funnel chart of BGC triage stages: all detected → non-excluded → lead-tier-qualified → mode-B-complete. Shows where BGCs exit at each gate. | `figures_sapote.py:fig_funnel` |
| `_8g_fig_class_distribution.png` | Class distribution | Bar chart of BGC product-class counts (primary class per BGC). Used for per-strain class composition overview. | `figures_extra.py:fig_class_distribution` |
| `_8g_fig_ab_af_panels.png` | AB/AF vertical panels | Two-panel vertical: AB-ranked (top) and AF-ranked (bottom) in a single figure for compact deliverable use. | `figures_sapote.py:fig_ab_af_vertical_panels` |
| `_8h_fig_cctt_map.png` | CCTT trigger map | Horizontal bar chart: one bar per T43-XXX trigger family, bar length = number of BGCs carrying that trigger. Sorted by prevalence. | `figures_extra.py:fig_cctt_map` |
| `_8i_fig_length_hist.png` | BGC length distribution | Stacked histogram of BGC sizes in kb, colour-coded by edge status. Shows the assembly's fragmentation pattern in size-space. | `figures_extra.py:fig_length_hist` |
| `_8j_fig_edge_composition.png` | Boundary composition | Bar chart: counts of Interior / Edge / Full-contig BGCs. Contextualises the corrected-count discount. | `figures_extra.py:fig_edge_composition` |
| `_8k_fig_novelty_ranked.png` | Novelty ranking | Horizontal bar chart of top BGCs by novelty score. Complements the AB/AF views for KCB-dark discovery leads. | `figures_extra.py:fig_novelty_ranked` |
| `_8l_fig_kcb_anchors.png` | KCB anchor inventory | Horizontal bar chart of most-cited KCB anchor products across all BGCs. Shows how much of the cluster space is anchored to known chemistry. | `figures_extra.py:fig_kcb_anchors` |
| `_8m_fig_genome_atlas.png` | Genome position atlas | Strip figure: each BGC as a coloured segment at its genomic position (absolute contig coordinates). Colour by product class. Shows clustering of BGCs on specific contigs. | `figures_extra.py:fig_genome_atlas` |
| `_8n_fig_rggmci_rescue.png` | RGGMCI rescue pairs | Dot plot or bar of HIGH/MODERATE RG-GMCI pairs, showing rescue confidence and the fragment IDs involved. Only rendered when RGGMCI pairs are present. | `render_brief.py:fig_rggmci_rescue` |

**Smoke-mode figures** (produced in `<pkg>/smoke_figures/` when only triage CSV is available, no deep_data): `fig_bgc_ranking.png` (top-15 by length, coloured by boundary), `fig_class_composition.png` (class counts), `fig_assembly_tier.png` (stacked bar of Interior/Edge/FC fractions). Source: `mamey/figures_smoke.py`.

### Gold figure suite (F01–F15, cohort-level, requires `--mode gold`)

Gold figures are cross-strain multi-panel figures produced by `mamey/cohort_figures.py`. They require `--mode gold` and the presence of deep_data across multiple strains. Each ships a sidecar `_data.csv`.

| Figure | Title | What it shows |
|---|---|---|
| F01 | Per-strain gene/domain census (z-score heatmap) | Five metrics per strain: total domain hits, distinct Pfam, tier-1 core domains, active-site calls, RiPP calls. Cells = raw counts; colour = z-score per metric. Assembly tier colour strip above columns. |
| F02 | Megasynthase/NRPS-PKS catalytic core (domain count heatmap) | Domain counts for PKS_KS, PKS_AT, PKS_KR, PKS_DH, PKS_ER, ACP, PP-binding, Condensation, AMP-binding, Epimerization, Thioesterase, LANC_like, YcaO across all strains. |
| F03 | BGC product classes per strain (class count heatmap) | antiSMASH product class counts per strain, plus a computed macrolide-type proxy row (BGCs with both KR and DH in reducing PKS loop). |
| F04 | Tailoring/accessory enzyme heatmap | Domain counts for: halogenase, chitinase GH18, siderophore synthetase IucA/IucC, siderophore reductase FhuF, metallophosphatase, aminotransferase, O/N-methyltransferase, cytochrome P450, glycosyltransferase. |
| F05 | CCTT diagnostic-chemistry trigger heatmap | BGC counts per T43-XXX trigger family per strain. |
| F06 | Resistance-axis tier distribution | BGC counts per resistance tier (T1/T2/T3/NULL) per strain. |
| F07 | NRPS A-domain substrate consensus | Heatmap of NRPS A-domain substrate inferences (top 15 substrates) per strain. |
| F08 | PKS AT extender-unit consensus | Heatmap of PKS AT extender-unit inferences per strain. |
| F09 | Transporter family heatmap | Domain counts for ABC, MFS, AA_permease, GntP_permease, MatE families per strain. |
| F10 | Transcription-factor/regulator family heatmap | Domain counts for TetR_N, GntR, LysR_substrate, HTH families, MarR, AraC per strain. |
| F11 | Top-40 Pfam domain clustermap | Hierarchically clustered (Ward linkage, log counts) heatmap of the 40 most prevalent Pfam domains across the cohort. Falls back to prevalence-ordered if scipy absent. |
| F12 | Active-site completeness bars | Per-strain bar chart of active-site completeness % (fraction of catalytic genes with all expected active-site residues confirmed). Notes when active-site scan was not populated (json_mode:off). |
| F13–F15 | Domain architecture ordinations | PCA-based ordinations of PKS/NRPS domain architecture vectors across all BGCs (vocabulary: PKS_KS, PKS_AT, PKS_KR, PKS_DH, PKS_ER, PKS_ACP, NRPS_C, NRPS_A, NRPS_T_PCP, TE_release). |

**Figure policy rules:** Pure-saccharide BGCs are excluded from all figures (they appear in text only). The `is_pure_saccharide()` function in `mamey/figure_policy.py` is the single gate — no figure module duplicates this logic. BGCs with multiple classes are classified by `_primary_class()` for display. All figure titles and axis labels are capacity-level.

**Render-all-figures:** `mamey render-all-figures --package <pkg>` runs every applicable figure module post-seal. Recommended after every `--capped-session` run because `--brief none` suppresses figures inside the session. Non-blocking per module: if one fails, the rest continue.

---

## Section 22: Deliverable Contract

Source: `docs/DELIVERABLE_CONTRACT.md`. This is the canonical specification for what the pipeline must produce.

### Deliverable categories

**CODE_BACKED** — produced deterministically by Python code; reproducible and auditable.
**SCHEMA_BACKED** — conforms to a validated workbook schema; verifiable by `workbook_schema_check.py`.
**PROMPT_BACKED** — produced by Sapote judgment; requires human or LLM authoring.

### Part A: Per-strain mandatory deliverables

**A1 (CODE_BACKED)** — Mamey extraction outputs. Every file in `mamey/validate.py:REQUIRED_SUFFIXES`. Key items: `_1_intake.json` (genome assembly stats), `_2_inventory.csv` (all BGCs), `_2b_bgc_crosswalk.csv` (BGC_ID ↔ contig/region locator map), `_3_scan_states.json` (all ten scans), `_4_triage_board.csv`, `_4A_RGGMCI_*.csv`, `_4B_Diagnostic_Rescue_Leads.*`, `_5_workbook.xlsx`, `_6_output_checklist.*`, `_7_cell_provenance.csv`, `_8_strain_brief.pdf`, `_8a`–`_8m_fig_*.png` (each with `_data.csv`), `manifest.json`, `checksums_sha256.txt`, `issue_log.md`, `commit_receipt.json`.

**A2 (PROMPT_BACKED)** — Sapote interpretation documents:
- Layperson-Ranked BGC Guide: strain header, 2–3 sentence narrative, 5-BGC ranked table with layperson headlines, assembly caveat, immediate next action.
- Technical Full-Analysis Report: intake + assembly summary, all ten scan results, full triage board (every BGC, ranked), DAPR (AB + AF), Mode B for HIGH BGCs, candidate cards for MEDIUM, minimum candidate cards for remaining BGCs, wet-lab matrix, metabolomics readiness, fermentation card, ecology synthesis, cross-strain cohort context block (A2.1), method caveats block (A2.2), literature-search handoff list (A2.3), PNAS references.
- Compound Detection and Isolation Bench Guide: per-BGC bench protocols for HIGH and MEDIUM BGCs.

**A2.1 Cross-Strain Cohort Context block** — required in every per-strain deliverable. Contains: corrected-BGC rank in cohort, shared accessory chemistry with count of other strains carrying each class, strain-unique classes (provisional, sample-limited), novelty footprint (KCB-dark BGC fraction of cohort total), diagnostics carried vs. cohort. Source: `Strain_Cohort_Context` and `Cross_Strain_Class_Prevalence` workbook sheets.

**A2.2 Method Caveats block** — inherited boilerplate every deliverable carries verbatim: (1) `kcb_cumulative` is a score not a percentage; (2) RG-GMCI HIGH-pair counts are not a fragmentation severity metric; (3) four universal classes are non-discriminating; (4) hglE-KS-PREV-001 is collection-specific.

**A2.3 Literature-Search Handoff list** — structured search list for parallel execution. Format: Lead (BGC locator) | search query | purpose | citation purpose. This replaces inline literature review — Sapote emits the search plan; a separate web-literature session executes it and returns PMID/DOI + Verified/Partial/Not-found tags.

**A2.4 Figure-Ready Tidy Export** — produced by `tools/export_figure_ready.py`. Tidy CSVs in `figure_ready/` folder with a `DATA_DICTIONARY.md`. One row per observation, snake_case headers, no formulas, no merged cells. Files: `strain_summary.csv`, `bgc_inventory.csv`, `bgc_class_long.csv`, `class_by_strain.csv`, `class_prevalence.csv`, `diagnostics_long.csv`, `cross_strain_findings.csv`. Column names are stable and versioned with the bundle.

**A2.5 Per-BGC page layout mandate** — in compiled deliverables, each BGC is a single page-unit: locus map (top 45%) + predicted class line + Mode B card (remaining 55%). No page break between a locus map and its analysis. Source: `docs/PER_BGC_PAGE_LAYOUT_SPEC.md`.

**A2.6 POOR/VERY_POOR equal-visibility rule** — all detected BGCs visible in every report, sorted by `Corrected_rank`, edge/FC labeled but not buried. Every BGC gets at minimum a minimum candidate card.

### Part B: Project-bundle deliverables (all strains complete)

Cross-strain AB/AF rankings · RG-GMCI statistics · Cassette-family statistics · Hallucination-trap statistics · Ecological-theme comparisons · Environmental-trigger matrix · Master literature index · Qualified-null/validation-control report · Completion audit · Project bundle manifest.

### Part C: Treatment status vocabulary

Every BGC must carry one of: `full Mode B` / `candidate card` / `minimum candidate card` / `deferred` / `not applicable`. A BGC without a recorded treatment status is not analyzed, it is missing.

**Minimum candidate card** — required fields: BGC_ID (contig · regionXXX), class/product hypothesis, boundary status, KCB top hit or NONE, one interpretive sentence, next action.

### Part D: Deferred ledger

Every deferred item must record: item name and type, reason for deferral, exact inputs needed to complete, responsible tier (Mamey/Sapote), target session or completion path. An item not in the deferred ledger is considered missing, not deferred.

### Deliverable offer protocol

At analysis-complete, Sapote must either auto-produce or explicitly offer the full deep-dive set. Stopping at the workbook without surfacing the deep-dive is an incomplete delivery. Default format: single consolidated PDF.

### Non-negotiable generation requirements

1. No internal/personal codenames. Public name: "Actinomycetes Project." Affiliation: .
2. Contig-ID locator on every BGC in every deliverable. `BGC007 (NODE_1_length_406707 · region001)` on first mention; `BGC007 (r001)` on subsequent mentions in same section. A bare BGC_ID without a locator is non-conformant.

### Citation-compact mode (v9.7.136+)

An optional output profile for token-efficient handbacks. Rules: (1) one global BGC caveat per report; (2) no repeated claim-safety prose per lead; (3) claim-safety as structured fields: `interpretation_scope`, `evidence_basis`, `citation_basis`, `uncertainty_flags`, `next_experiment`; (4) write `Citation_Ledger.csv` and `.json`; (5) EXCEPTIONAL and HIGH leads require citation basis or explicit `citation_needed` marker. Source: `mamey/citation_compact.py`, `docs/CITATION_COMPACT_MODE.md`.

antiSMASH 8.0 provenance: DOI `10.1093/nar/gkaf334`. MIBiG 4.0 provenance: DOI `10.1093/nar/gkae1115`.

---

## Section 23: Common Mistakes and Failure Diagnostics

Source: `docs/COMMON_MISTAKES.md`. Documented failure modes with symptoms, causes, and fixes.

**Mistake 1: Uploading raw genome FASTA instead of antiSMASH ZIP**
Symptom: `No antiSMASH regions found in input — bare assembly` or `MAMEY_FAILED, raw_bgcs 0`. Fix: run antiSMASH 8 first at `https://antismash.secondarymetabolites.org`, then run Mamey on the results ZIP.

**Mistake 2: Stale antiSMASH export (pre-v7 or stripped JSON)**
Symptom: Missing KCB scores, blank `KCB_top` columns, `KCB/RiQ parser found no antiSMASH JSON/TXT evidence`. Cause: antiSMASH ZIP lacks `knownclusterblast/*.txt` or the full `*.json`. Fix: re-run antiSMASH 8+ and download the full output ZIP.

**Mistake 3: Using an NCBI accession as the strain ID**
Symptom: `Warning: Strain label 'NZ_QHHY00000000.1' is an NCBI accession (fallback)`. Cause: accessions propagate into every deliverable and make cross-referencing hard. Fix: supply a meaningful `--strain` name and use the accession as metadata only. Accessions are a FALLBACK label; when one appears as a primary label, flag it.

**Mistake 4: ijson absent → TXT-only mode**
Symptom: `ijson✗ bounded→TXT-only` in dependency banner; KCB scores present but RiQ scores blank. Cause: ijson not installed; Mamey falls back to KnownClusterBlast TXT parsing which provides KCB but not RiQ. Fix: install ijson (vendored in bundle) or use `--json-evidence off` to accept TXT-only mode explicitly.

**Mistake 5: --master pointed at Schema-v1.2 workbook**
Symptom: `[BLOCKED] --master target is a Schema-v1.2 workbook`. Cause: legacy cohort workbook schema conflicts with Mamey's `--master` writer. Fix: use `tools/ingest_package.py` + `tools/build_master.py` instead.

**Mistake 6: Expecting analysis from a MAMEY_COMPLETE package**
Symptom: package says MAMEY_COMPLETE but no Mode B cards, no compound interpretations. Cause: Mamey is the extraction layer only. Mode B, DAPR, ecology synthesis, and guides are the Sapote judgment step. Fix: upload `manifest.json` to Claude and request "Run full Sapote analysis."

**Mistake 7: Taxonomy as `.` or blank**
Symptom: display name shows `. strain AS-XXX`. Cause: antiSMASH GBK for some strains deposits `ORGANISM .`. Fix: always supply `--taxonomy "Genus sp."` explicitly.

**Mistake 8: openpyxl not installed**
Symptom: `openpyxl✗ REQUIRED for workbooks` in dependency banner; no `*_5_workbook.xlsx` produced. Fix: `pip install openpyxl` or install from `offline_deps/`.

**Mistake 9: Figures not rendered (two causes)**
Symptom: `BRIEF_SKIPPED_TIMEOUT.md` or `NO_FIGURES_RENDERED.md` in package. Cause A: numpy/matplotlib not installed. Cause B: font-manager cache build timed out on first render in restricted environments. Fix A: install figure deps. Fix B: run `mamey render-all-figures --package <pkg>` after the cache builds, or increase `MAMEY_RENDER_TIMEOUT_S`.

**Mistake 10: Not running mamey doctor first**
Fix: `python -m mamey doctor` checks Python version, all dependencies, write permissions, bundle integrity, and antiSMASH ZIP detection. Run before any troubleshooting.

**Mistake 11: pytest absent blocks cut gates**
Symptom: `FATAL: public-tier unpublished-ID invariant FAILED` during `make_public_tier.sh`. Cause: release cut gates require pytest + pluggy + iniconfig. Fix: download the three wheels from PyPI and install.

**General diagnostic principle:** `mamey doctor` is always the first diagnostic step. It provides a structured pass/fail checklist of every dependency and bundle file, so any startup failure can be attributed to a specific missing component rather than diagnosed by trial and error.

---

## Section 24: Mode B Judgment Persistence Protocol

Source: `docs/modules/MODE_B_WRITE.md`, `mamey/judgment_store.py`, `mamey/mode_b_receipt.py`.

### The judgment store

Mode B cards must be persisted to disk after each session. Without persistence, Mode B analysis lives only in chat and is lost between sessions. The judgment store (`mamey/judgment_store.py`) provides the durable register.

**Files written by `record_mode_b()`:**
```
<package_dir>/judgment/<strain>_BGC001_mode_b.md         # per-BGC Mode B card
<package_dir>/judgment/<strain>_laypersons_section.md    # accumulated layperson text
<package_dir>/judgment/<strain>_fermentation_section.md  # accumulated fermentation text
<package_dir>/<strain>_judgment_register.json            # completion tracker
```

**Required call fields:** `package_dir` (absolute path to sealed package), `bgc_id` (exact BGC ID from triage board), `mode_b_md` (full §1–§30 card markdown). Recommended fields: `rank` (sets character floor: HIGH≥9k / MID≥8k / LOW≥6k), `layperson_paragraph` (3–5 sentences for the layperson guide), `fermentation_note` (isolation strategy condensed), `session_id` (batch label for provenance).

**Idempotent:** Re-running `record_mode_b()` for the same BGC overwrites the prior card. The register tracks completion status.

### ingest-receipts (the canonical front door)

`mamey ingest-receipts --package <pkg> --receipt <mode_b_receipt.json>` — the production path for persisting Mode B cards. A Sapote session ends by writing one `mode_b_receipt.json` file (`{strain_id, session_id, cards:[{bgc_id, mode_b_md, layperson_paragraph?, fermentation_note?}]}`); `ingest-receipts` persists each card, flips the register to COMPLETE, and reconciles `E1_Mode_B_Index` with `--master`. Fail-closed (unknown BGC skipped, never invented) and idempotent.

`mamey ingest-receipts --package <pkg> --auto-detect` — scans `<pkg>/judgment/` for `*_mode_b.md` cards not yet in the register and ingests them. Use at session start to recover orphan cards from prior sessions.

`mamey ingest-receipts --package <pkg> --card <file.md>` — one-card synchronous persist.

### Workbook write-back functions

After completing specific Sapote steps, call these functions to populate judgment-facing workbook sheets. Source: `mamey/master_workbook.py`.

- `update_e1_from_judgment(package_dir, master_workbook_path)` — updates E1_Mode_B_Index and A4_Completeness_Audit from the judgment register. Idempotent: Batch 2 replaces Batch 1 rows.
- `update_c3c4_from_sapote(...)` — populates C3_Lead_Tier_Summary and C4_Strain_Decision_Table with Sapote composite rank, score, and recommended role.
- `update_d3_from_sapote(...)` — populates D3_RGGMCI_Promoted with Mode B–supported rescue pairs.
- `update_g1_from_sapote(...)` — accumulates literature citations in G1_Literature_Index. De-duplicates on (strain, BGC_ID, doi).
- `update_g2_from_sapote(...)` — populates G2_Validation_Roles with strategic validation assignment.

### §11–§20 enrichment sections

Cards must carry ≥1,000 characters of combined §11–§20 content (for non-fragment BGCs). The `mamey.enrichment_sections` module generates this deterministically from the gene table: `compose_enrichment(genes, genome_domain_frequency, products, floor=1000)`. Rarity catch-alls (`rarest_genes`, `rarest_domains`) and domain_inventory fire on any card with ≥1 domain-bearing gene. Genuine fragments (STUB, sub-2k characters) are exempt from the enrichment floor.

### Compiled report trigger

The compiled master PDF should only be rendered when `read_register()` returns `judgment_status == "COMPLETE"`. Until then, `render-brief` emits PDF pages with whatever Sapote content is already written (partial progress is acceptable during a campaign).

---

## Section 25: BGC Class Reference

Source: antiSMASH 8 product type labels as seen in `_2_inventory.csv` and triage board. Scoring weights from `docs/reference/01_Math_Reference_VolI.md`. DAPR routing from `docs/DAPR_CLASS_FRAMEWORK.md`.

### Primary PKS classes

**T1PKS** — Type I modular polyketide synthase. Large multi-domain megasynthase with KS-AT-DH-ER-KR-ACP module architecture. Produces macrolides, polyenes, polyols. AB weight +10, AF weight +10, novelty weight +8. Detecting a reducing PKS loop (KR + DH co-occurrence) is the macrolide-type proxy in F03.

**transAT-PKS** — Trans-acyltransferase PKS. AT domain is free-standing, shared across modules (not embedded). Produces complex polyketides (difficidin, bacillaene, taveuniamide). AB weight +14, AF weight +12, novelty weight +18 (highest of any class — trans-AT clusters are rare and often novel). Subsumes T1PKS in scoring.

**T2PKS** — Type II aromatic polyketide synthase. Minimal PKS (KS, CLF, ACP) + cyclases produce aromatic ring systems. Produces tetracyclines, anthracyclines, aromatic antibiotics. AB weight +12. hr-T2PKS (highly reducing T2PKS) weight +14.

**T3PKS** — Type III PKS (chalcone synthase superfamily). Simple iterative condensation, no ACP. Produces stilbenes, flavonoids, resorcinols.

**NRPS** — Nonribosomal peptide synthetase. A-C-T (adenylation-condensation-thiolation) module architecture. Produces cyclic and linear peptides. AB weight +12, AF weight +8.

### RiPP classes (Ribosomally synthesised and Post-translationally modified Peptides)

**lanthipeptide** — RiPP with LanB dehydration + LanC cyclization (class I/II) or LanM bifunctional (class III/IV). Detects by LANC_like, Lant_dehydr_N/C. AB weight +12. T43-LAN trigger. Precursor mass ladder (§21) required in Mode B.

**lassopeptide** — Bicyclic RiPP with a macrolactam ring threading. T43-LASSO trigger.

**thiopeptide / thiazolylpeptide** — Heavily modified RiPP with azole heterocycles and pyridine macrocycle. AB weight +14. T43-THA trigger.

**sactipeptide / ranthipeptide** — Radical SAM-dependent RiPP. Novelty weight +12.

**CDPS / diketopiperazine** — Cyclodipeptide synthase pathway. T43-DKP trigger. Vetoed when copalyl diphosphate synthase (ent-CDPS terpene cyclase) is present in the same locus.

### Terpenoid classes

**terpene** — Geranylgeranyl-diphosphate cyclase products. Includes hopanoids, sterols, sesquiterpenes. AF weight +6 (low; most are not directly antifungal but sterol interference is mechanism-relevant). Novelty weight 0.

**indolocarbazole** — Tryptophan-derived shikimate product (not a terpene). Cytotoxic; routed OUT of antibacterial/antifungal DAPR lead boards.

### Other important classes

**nucleoside** — Dedicated nucleoside-antibiotic pathway (NikJ/NikD markers). AF weight +18. T43-NUC trigger. Chitin-synthase inhibitor class (nikkomycin, polyoxin); the strongest antifungal pathway class in the project.

**phosphonate** — PEP mutase (PepM) initiates C-P bond formation. AB weight +15. T43-PHO trigger.

**phenazine** — Phenazine-1-carboxylic acid and derivatives. Antifungal by redox mechanism.

**ectoine** — Osmolyte/compatible-solute biosynthesis. Standing-rule exclusion: capped at Inventory tier. Excluded from NAPAA scope.

**NAPAA** — Excluded from all comparative claims (see Section 2 and Section 13).

**saccharide** — Pure sugar/glycan cluster. Standing-rule exclusion. Note: saccharide *tailoring* on an NRPS/PKS backbone does NOT trigger the exclusion — only clusters where the primary product classes are exclusively saccharide-type.

**arylpolyene** — Flexirubin-type yellow/orange pigment. NOT an antifungal polyene despite "polyene" in the name. Routed OUT of AF leads. The scoring substring-containment guard ensures "arylpolyene" does not inherit "polyene" AF weight.

**betalactone** — Unusual β-lactone pharmacophore. T43-BLT trigger. Includes salinosporamide (proteasome inhibitor — cytotoxic caution applies).

**HSAF / PTM (polyene tetramate macrolactam)** — Hybrid PKS-NRPS producing a 5,5,6-tricyclic tetramate. Detects by ornithine A-domain + T43-PTM trigger. Sphingolipid inhibitor; antifungal by lipid metabolism disruption. Confirmed in 5 bee-associated strains across 4 genera in AS-series. AF weight +12–20 depending on named anchor.

---

*Last updated: 2026-07-09 · v2 additions (Sections 21–25) · Bundle v9.7.319*

---

## Section 26: Terms Introduced v9.7.243–v9.7.246

**PHANTOM_LOCUS** — An ERROR-severity, release-blocking lint that checks whether every `ctgN_M` locus tag cited in a Mode B card exists in that strain's own CDS table. A locus from another organism is a **fabricated observation**, however true it is elsewhere. Regex: `\bctg\d+_\d+\b`. Requires `bgc_context["known_loci"]`, loaded by `authored_verify` from the sealed `<strain>_cds_table.csv`; **silent without it** — the lint cannot judge what it cannot see, and a false accusation of fabrication is worse than none. Added to `_READINESS_BLOCKING`, so a card citing a foreign locus cannot reach `RELEASE_READY`. Source: `mamey/modeb_structure_gate.py:_phantom_locus_findings` (v9.7.246).

**LOCUS_BGC_MISMATCH** — An ERROR-severity referent lint (v9.7.256), sibling of `PHANTOM_LOCUS` in the same file. Where `PHANTOM_LOCUS` asks whether a gene exists in the strain, this asks whether a gene that *does* exist is cited under the BGC it belongs to. Catches the AS-XXX BGC006/BGC010 leak class — templated boilerplate that carries a real gene into another BGC's card. `authored_verify` builds per-BGC membership to distinguish a misattributed real gene from a correctly-placed one. Not a `_READINESS_BLOCKING` member; blocks via the any-ERROR path (→ `DRAFT`).

**PANEL_ABSENT_CLAIM** — An ERROR-severity referent lint (v9.7.256), sibling of `PHANTOM_LOCUS`. Flags a per-gene BLASTp *result* asserted for a BGC that has no BLASTp panel in the package. Keys on whether a BGC has a panel *selection*, **not** on returned alignments — so a fabricated result on an in-panel-but-never-run BGC still passes (reproduced on `S_erythraea` BGC017); the residual gap ("asserted result vs actual alignments") is to be closed by extending this lint to require a results artifact, not by adding a gate. Not a `_READINESS_BLOCKING` member; blocks via the any-ERROR path.

**Referent validation** — Checking that a cited identifier (locus tag, BGC id, accession, score) refers to something that exists in the subject under discussion. Distinct from **claim validation**, which checks that the assertion made about it is appropriately hedged. "Capacity consistent with a glycopeptide" is claim-safe phrasing about a real cluster. "BLASTp settled `ctg12_71`" is unsafe not because of its phrasing but because `ctg12_71` does not exist in this strain. The claim-safety linter cannot catch this class; the referent lints in the structure gate perform it — `PHANTOM_LOCUS` (does the gene exist), plus its v9.7.256 siblings `LOCUS_BGC_MISMATCH` (is it under the right BGC) and `PANEL_ABSENT_CLAIM` (is a per-gene BLASTp result claimed for a BGC with no panel).

**Readiness state** — The Mode B card lifecycle, reported by `verify-modeb`. Three values: `DRAFT` (any ERROR finding, or `quality_tier` in `{None, STUB, UNKNOWN}`), `VERIFIED` (depth adequate, but a blocking correctness code is present), `RELEASE_READY` (depth adequate and no blocking code). **Only `RELEASE_READY` may flow into user-facing documents** — this is the presentation gate. Source: `mamey/modeb_structure_gate.py:readiness_state`.

**`_READINESS_BLOCKING`** — The four finding codes that hold a card below `RELEASE_READY` regardless of its depth: `NOVELTY_CONTRADICTION`, `INTERNAL_CONTRADICTION`, `FACT_MISMATCH`, `PHANTOM_LOCUS`. Each is a correctness failure, not a style failure. A card can be structurally complete, adequately deep, and claim-safe and still be blocked — because a fact in it contradicts the package, or a locus in it belongs to another organism.

**Orphan candidate** — A Python module under `mamey/` or `tools/` that no other module imports, that no CLI verb reaches, and that no test names. Computed by `tools/file_atlas.py` from the real tree via `ast`. Live count on v9.7.246: **35 of 280 files**. The orphan list is the roll pool for the Bunny Hop audit game, and it is the population from which the "defined and never invoked" defect class is drawn. **Caveat:** an AST scan sees Python imports, not shell invocations, not `gate_registry.tsv` rows. The first pass called `verify_release_identity.py` an orphan; it is invoked by `release.sh`. Shell and gate-registry invocations now count (42 → 35).

**Fan-in / fan-out** — In `docs/FILE_ATLAS.csv`: `imported_by` (fan-in) is the number of internal modules importing this file; `imports_internal` (fan-out) is the number it imports. Highest fan-in on v9.7.246: `tools/_wbio.py` (38), `mamey/models.py` (13), `mamey/crosswalk.py` (11). High fan-in identifies the files where a latent defect propagates furthest — both `_wbio.py` and `crosswalk.py` were hardened immediately after the atlas surfaced them.

**Defined and never invoked** — A recurring defect class in this codebase, named in its own changelog. A constant, flag, computed local, or output file is created with correct semantics and a passing unit test, and the production call path bypasses it. Four documented instances: the `blastp_online/` overlay (three readers, zero writers, v9.7.239); `check_dangling_refs --strict-paths` (existed, nothing ran it, v9.7.242); `wanted_region` (computed, never read, v9.7.244); `DEFAULT_BATCH = 10` (defined, never read, so `chunk_proteins` defaulted to `MAX_BATCH = 30`, v9.7.245). **Diagnostic:** for any newly added constant or file, grep for its name and count the *read* sites, not the write sites.

**Spot-vet** — A partial verification of a document, recorded honestly as partial. For `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md`, a spot-vet covers doctrine (no retired positions present), anchor (states its true drift), and dangling references — and explicitly does **not** claim to be a full read-through. Introduced when the monolith's anchor was found to be 185 cuts behind while claiming a read-through against v9.7.6. The distinction matters because a fresh chat reads the monolith first and takes its self-description at face value.

**Retired doctrine** — Positions the project has explicitly reversed, whose presence in the parent design document is a real defect. `tools/check_monolith_freshness.py` scans for four: the 66/50/33 assembly tier thresholds (superseded by 70/45/20), per-BGC BSL-2 flagging (retired; the engine emits a neutral `[E-signal]`), AS_SCRUB (retired 2026-07-06 when the AS cohort went public), and the PUBLIC/PRIVATE figure divider. The scan is **negation-aware**: a sentence saying "no per-BGC BSL-2 flagging" must not be flagged as asserting the doctrine it denies.

**`region_label` semantics** — `mamey/crosswalk.py:region_label(n)`. Region numbers are 1-based. `region_label(0)` → `region_unknown` (0 is invalid, not zero). `region_label(-1)` → `region_unknown` (a leading minus is rejected before digits are read; `re.search(r"(\d+)", "-1")` would otherwise match `"1"` and silently produce `region001`). `region_label("region003")` → `region003` (tolerates an already-formatted label, because callers read `antismash_region`, whose value *is* that string). Fan-in 11.

**Region index = area index** — In an antiSMASH record JSON, the `areas` list carries **no region number**. The region number is the 1-based index into `areas`. Verified against the real AS-XXX 74 MB JSON across all three regions of `NODE_2_length_553361`. Any code that needs region *N*'s evidence must resolve `areas[N-1]`; hardcoding `areas[0]` returns the first region on the contig regardless of which region was requested — the v9.7.244 `tab-reconcile` bug.

**`DEFAULT_BATCH` vs `MAX_BATCH`** — `mamey/blastp_online.py`. `MAX_BATCH = 30` is the ceiling (a hard clamp: `batch_size = min(batch_size, MAX_BATCH)`). `DEFAULT_BATCH = 10` is the courteous default used when the caller omits `batch_size`. From v9.7.240 to v9.7.245 the signature read `batch_size: int = MAX_BATCH`, so every caller that omitted the argument silently submitted 30-protein batches to NCBI. `chunk_proteins(60)` returned `[30, 30]`; it now returns `[10] × 6`. Explicit `30` is still honoured; `99` still clamps to 30. Giant proteins (`> GIANT_AA = 2500`) go solo regardless.

**Colibrimycin-class fix** — The §8 lesson, retained after the foreign identifiers were stripped: *a high KCB score backed by only a handful of shared genes is NOT the compound.* Originally illustrated with a concrete score (3734) and BGC id from another strain's run; the illustration was removed in v9.7.246, the lesson kept. Cite gene coverage alongside any KCB anchor: "KCB top hit: colibrimycin (3734, 3/22 proteins)" — never "similar to colibrimycin."

**Single-region fixture blindness** — A test fixture that cannot distinguish correct behaviour from the bug under test. The `tab-reconcile` region-selection bug survived because the reference fixture (BGC028/AS-XXX) sits on a contig with exactly one region, where `areas[0]` is always the right answer. **A single-region fixture cannot exercise region selection.** Generalises: before trusting a passing test, ask whether the fixture could have failed had the code been wrong.

**Proxy test** — A test that exercises a stub of the artifact rather than the artifact. The v9.7.230 `kcb-frontpage` test stubbed `bgc_id` into the hit dicts and asserted the `--bgc` filter worked. The real `regions.js` carries no `bgc_id`; the filter could only ever return "no hits after filter." The test passed CI for thirteen cuts. Related to the P7a failure: the reviewer exercised `write_nr_overlay()` with one BGC and one round — a shape of test that cannot expose a truncate-on-second-write bug. *"I checked the mechanism, not the workflow. The mechanism worked. The workflow lost 43% of the data."*

**Fail closed** — When a capability cannot honour its contract, exit non-zero with a pointer to the working path, rather than returning an empty result that reads as "nothing found." `kcb-frontpage --node` / `--bgc` now exit 2 with a pointer to `--region` and `<strain>_2b_bgc_crosswalk.csv`, because the anchors they filter on do not exist in `regions.js`. Contrast **fail silent**, which is correct for `PHANTOM_LOCUS` without a CDS table: a lint that would accuse the author of fabrication must not fire on absent evidence.

**`atomic_save` / `atomic_write_text` / `atomic_dump_json` / `atomic_open`** — The four helpers in `tools/_wbio.py` (38 importers, the highest fan-in in the bundle). Invariant: **the target file is always present and always complete.** Three v9.7.243 fixes: all four now inherit the target's file mode (`os.replace()` adopts the *temp* file's mode, so rewriting a `0600` deliverable left it `0644`); all four now discard the temp and re-raise on failure (three of four leaked `.tmp` files); and `atomic_save(keep_bak=True)` now *copies* to `.bak` rather than renaming, closing a window in which the target did not exist at all.

**Version-lineage split** — Three concurrent codebases, two of which independently shipped a `v9.7.244`. Bunny Hop (head v9.7.246: file_atlas, `_wbio`, `kcb-frontpage`, `tab-reconcile`, crosswalk, monolith gate, `PHANTOM_LOCUS`); Guide (head v9.7.244: P8/P9/P10); Docs (head v9.7.243: `P-emit-01`, `--fail-on-empty`, `docs/user_guides/` v2–v3, `math_reference_vol2.md`). Bunny Hop reproduced and independently fixed P8 and P10, so the code differs from Guide even where behaviour agrees. Recommended consolidation at **v9.7.250**. **Test counts across lineages are expected to differ** (2884p/152s vs 2877p/147s vs 2857p/152s); zero failures on all three is the invariant. **Scoring parity holds:** six independent `mamey run` invocations across lineages gave 46 raw / 32.25 corrected / MODERATE, six times.

---

*Last updated: 2026-07-09 · v3 additions (Section 26) · Bundle v9.7.246*
