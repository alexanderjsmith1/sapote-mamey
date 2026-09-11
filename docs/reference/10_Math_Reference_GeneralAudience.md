# The Mathematics of Sapote–Mamey: A Complete Reference

**Mamey engine v1.9.110 · bundle v9.7.319**  
****  
**Date:** 2026-06-23

This document combines the full general-audience mathematics reference for the Sapote–Mamey biosynthetic gene cluster analysis pipeline. It covers the deterministic extraction engine (Mamey) across two volumes: Volume I documents the core quantitative pipeline (boundary classification, corrected BGC counts, assembly tiers, AB/AF/novelty scoring, lead tiers, guards, RG-GMCI reconstruction, KCB anchor display, the triage rationale, and completeness invariants); Volume II documents the subsystems that feed and surround it, organized into seven clusters (CCTT trigger engine, architecture-first assessment, KCB/RiQ extraction, compound-class annotation, rescue and concordance layers, the Mode B enrichment stack, and the figure system).

Two interpretive rules apply throughout both volumes:

**Scores are routing priors, not biological proof.** AB, AF, and novelty values order clusters for human attention. They are not evidence that a strain produces any compound. The appropriate language downstream is "biosynthetic capacity consistent with…" — never "produces."

**KCB is similarity, not identity.** Every KnownClusterBlast signal is a sequence-similarity score against a reference database. It informs routing and display but never confirms a product.

---

## Contents

- **Volume I** — Core counting, scoring, RG-GMCI, KCB anchor display, triage rationale, and completeness
- **Volume II, Cluster A** — The source-scan and CCTT trigger engine
- **Volume II, Cluster B** — Architecture-first assessment and scoring context
- **Volume II, Cluster C** — KCB / RiQ extraction and gene-level correspondence
- **Volume II, Cluster D** — Compound-class annotation, domain-level enrichment, and DKP/CDPS detection
- **Volume II, Cluster E** — Rescue, concordance, fragment ceiling, and comparative pairs
- **Volume II, Cluster F** — Singleton filter, §3 census, enrichment sections, and nominal length
- **Volume II, Cluster G** — The figure system

---



---

# The Mathematics of Sapote–Mamey: A Plain-Language Guide

**Mamey engine v1.9.110 · bundle v9.7.319**  
****

This document explains the quantitative logic behind Mamey's deterministic extraction engine — how it counts biosynthetic gene clusters, measures assembly quality, scores clusters for prioritization, and reconstructs clusters that were split by fragmented assemblies. The target reader is a biologist or bioinformatician who uses the pipeline or reviews its output and wants to understand what the numbers mean and why they are computed the way they are.

Two interpretive rules apply to every number in this document and should be kept in mind throughout:

**Scores are routing priors, not biological proof.** The AB, AF, and novelty scores sort clusters for human attention and downstream analysis. They are not evidence that a strain produces a particular compound. The appropriate language downstream of any score is "biosynthetic capacity consistent with…" — never "this strain produces compound X."

**KCB similarity is not product identity.** Every appearance of a KnownClusterBlast (KCB) signal is a sequence-similarity measure between the query cluster and a reference database entry. It informs novelty estimation and display labelling; it never confirms a product.

---

## 1. How a BGC's position on its contig is classified

Before any counting or scoring begins, each detected BGC is assigned a boundary status based purely on its position within its contig. This classification — Interior, Edge, or Full-contig — drives several downstream decisions including the corrected count formula and confidence grading.

**Interior** means the cluster sits well within a contig, with at least 5,000 base pairs of sequence on both sides. The biosynthetic machinery is fully captured; the cluster is complete as antiSMASH detected it.

**Edge** means one end of the cluster runs to within 5,000 bp of a contig terminus. The contig ends there — not the cluster. Some genes on the truncated side are missing because the assembler could not extend the contig further, likely due to a repetitive region or low coverage.

**Full-contig** means the cluster spans ≥ 95% of the contig's total length. The contig is so short that the cluster essentially *is* the contig. Both ends are presumed truncated, and the cluster is probably a fragment of something larger stranded on a short contig by assembly gaps.

Two points of nuance in the implementation:

**Circular chromosomes.** On a closed circular replicon, the origin of replication is not a truncation point. A cluster that happens to sit adjacent to the origin wraps around the chromosome; it is not cut off. Without an explicit correction, genome assemblers that annotate closed chromosomes can produce false Edge calls at the origin — the cluster coordinate touches the contig end, but the contig end is an artifact of linearization, not a real truncation. The pipeline corrects for this: Edge is only assigned when the genome topology is linear or unknown.

**Coordinate system.** antiSMASH writes each region into a GenBank file with coordinates that restart from 1 within the clipped region. Edge classification requires the cluster's *original* coordinates on its full contig — not the restarted coordinates inside the region file — along with the full contig length. Using the restarted coordinates would falsely classify many Interior clusters on long contigs as Edge.

---

## 2. The corrected BGC count

The raw count from antiSMASH — the total number of regions detected — is not the right number to report as a strain's biosynthetic gene cluster count. The reason is that assembly fragmentation inflates it: one real cluster that was split across three contigs by assembly gaps appears as three separate BGCs. Reporting the raw count overstates the strain's biosynthetic richness.

The corrected count applies a partial-evidence discount based on boundary status. An Interior cluster is fully captured and counts at full weight. An Edge cluster is truncated at one boundary, so some genes are missing; it counts at half weight. A Full-contig cluster is presumed truncated at both ends and counts at quarter weight.

> **Corrected count = Interior + ½ × Edge + ¼ × Full-contig**

For a strain with 12 Interior, 6 Edge, and 4 Full-contig regions:
> Raw count: 12 + 6 + 4 = 22  
> Corrected count: 12 + (½ × 6) + (¼ × 4) = 12 + 3 + 1 = **16**

The raw count is always reported alongside the corrected count — the discount is transparent. And because every weight is ≤ 1, the corrected count can never exceed the raw count. A result where it does indicates a coordinate or boundary-classification bug.

---

## 3. Assembly quality tier

A corrected count of 16 means something different depending on whether the genome is nearly complete or badly fragmented. A strain with 40 BGCs in a GOOD assembly likely has 40 genuine clusters; a strain with 40 BGCs in a VERY_POOR assembly may have 15 real clusters represented as 40 fragments.

The assembly quality tier makes this interpretive context explicit. It is computed from the **interior fraction** — what percentage of detected BGCs are Interior:

> Interior fraction (%) = Interior ÷ Raw count × 100

| Tier | Interior fraction | Interpretation |
|---|---|---|
| **GOOD** | ≥ 70% | Most clusters are complete. The corrected count is trustworthy. |
| **MODERATE** | 45–70% | Significant fragmentation. Corrected count is a reasonable estimate. |
| **POOR** | 20–45% | Heavy fragmentation. Corrected count is a floor, not an estimate. |
| **VERY_POOR** | < 20% | Nearly all clusters are fragments. The raw count is largely noise. |

Two supporting assembly statistics travel with every package: **N50** (the length at which contigs covering half the total assembly have been accumulated — higher is better) and **GC%** (the genome-wide fraction of guanine and cytosine bases).

### The contamination check

Two VERY_POOR assemblies once passed through the pipeline without any flag despite clear pathology: bimodal GC content and megabases of foreign sequence from a co-cultured organism. The pipeline now runs a non-blocking contamination check at assembly stage. It computes the length-weighted standard deviation of GC% across all contigs. Clean genomes typically show 1–2% GC standard deviation; the contaminated drafts showed 7–12%. A standard deviation ≥ 5% raises a CONTAMINATION_SUSPECT flag. This flag does not block extraction — the analyst makes the final call — but it ensures the problem is never silent.

---

## 4. The three routing scores

Each BGC receives three numerical scores on a 0–100 scale:

- **AB** — antibacterial routing prior: how likely this cluster is to be a lead in the antibacterial space
- **AF** — antifungal routing prior: how likely it is to be a lead in the antifungal space
- **Novelty** — how structurally unusual or underexplored the cluster appears to be

These scores *sort* clusters — they tell the pipeline and the analyst which clusters to look at first. They are not evidence of bioactivity. A high AB score means the cluster carries the gene-content signatures associated with antibacterial natural products; it says nothing about whether the cluster is expressed or whether its product actually inhibits bacteria.

### How the scores are built

Each axis starts from a fixed base value — 25 for AB, 20 for AF, 30 for novelty — and adds up class-specific weights based on the cluster's own product annotation:

> AB = 25 + (sum of AB weights for matching product classes)  
> AF = 20 + (sum of AF weights for matching product classes)  
> Novelty = 30 + (sum of novelty weights for matching product classes)

The weight tables encode the prior probability that a cluster of each class will be relevant to a given bioactivity target. Carbapenem clusters get the highest AB weight (18 points) because carbapenems are a clinically critical antibiotic class. Polyene macrolide clusters get a high AF weight (18 points) because polyenes are a primary antifungal class. Enediyne clusters get a high novelty weight (18 points) because they are rare and structurally extreme.

**The keyword scorer only sees the cluster's own evidence.** It reads the cluster's own antiSMASH product class annotations, its MIBiG similarity hits, and a resolved compound name from the KCB database if one is available. It deliberately does not read the raw KnownClusterBlast rank-1 text field, which often contains a description of the reference organism's entire genome rather than just the matched cluster. Including that text would credit a saccharide-only cluster with the antibacterial potential of all the NRPS and PKS clusters the reference organism happens to carry.

**Substring matching is bounded.** The word "polyene" appears inside "arylpolyene" — an orange pigment with no antifungal activity. Without a word-boundary check, arylpolyene clusters would score as antifungal leads. The keyword matcher uses regex word-boundary anchors to prevent this. Similarly, if a cluster matches "hr-t2pks" (a specific subtype of type-II PKS), it does not additionally receive the generic "t2pks" weight on top — the subclass subsumes its parent class.

### The diagnostic marker bonus

Some gene-level evidence is strong enough to establish a compound class independently, even when the cluster's product label and KCB similarity are both uninformative. The 14 CCTT (Chemistry-Class Trigger Tower) triggers are domain-level markers with a high specificity for particular chemotypes. When a corroborated trigger fires, a flat bonus of 25 points is added to the relevant axis:

- **Antifungal triggers:** T43-NUC (nucleoside chitin-synthase inhibitor class) and T43-PTM (HSAF/polycyclic tetramate macrolactam class)
- **Antibacterial triggers:** T43-LAN (lanthipeptide), T43-LASSO (lassopeptide), T43-THA (thioamide), T43-PHO (phosphonate), T43-AMC (aminoglycoside), T43-BLA (beta-lactam)

The canonical case that motivated this mechanism: a cluster labelled only "nucleoside; other" with no KCB hit — nearly invisible to the keyword scorer — but carrying the NikJ enzyme diagnostic for the nikkomycin/polyoxin class of nucleoside chitin-synthase inhibitors. Nikkomycin and polyoxin are potent antifungals. Without the trigger mechanism, this cluster would have scored near the antifungal floor and been buried; the T43-NUC trigger adds 25 points and ensures it reaches a meaningful lead tier.

**"Corroborated" is the key word.** A trigger is corroborated when the cluster's own product class is compatible with the trigger's chemotype. T43-PHO (phosphonate) firing on a type-III PKS cluster is suspicious — phosphonate biosynthesis has nothing to do with chalcone synthases. An uncorroborated trigger is still recorded and visible to the analyst, but it does not grant the bonus and does not affect tier assignment.

### Novelty adjustments from KCB similarity

After the keyword base, novelty is adjusted by how well-characterized the cluster appears to be:

- Strong KnownClusterBlast similarity to a known reference cluster (cumulative score > 10,000) lowers novelty by 15 points — a cluster with close known relatives is less likely to be genuinely new.
- No KCB similarity at all raises novelty by 5 points — a cluster with no known relatives is slightly more likely to be new.
- A low RiQ ratio (< 0.5) — antiSMASH's recognition index, which is low when the cluster structure is unusual — raises novelty by 10 points.

### Final score assembly

The three scores are clamped to the 0–100 range. The RG-GMCI reconstruction engine (§7) can add a routing bonus of 8 points (HIGH confidence) or 4 points (MODERATE confidence) to all three scores for clusters identified as fragments of a larger split pathway. This bonus increases routing priority — it does not increase confidence in the product class call.

The edge penalty, which previously subtracted points from scores of Edge and Full-contig clusters, was neutralized in v9.7.84. Empirical analysis of a large cluster cohort showed no systematic difference in base scores between Interior, Edge, and Full-contig clusters — the penalty was a flat pessimism prior without measurement basis, and it was decisive in 83% of near-threshold Edge cases, burying exactly the kind of overlooked fragments the tool is meant to surface. Truncation uncertainty is now expressed through the architecture confidence grade (§5), not the score.

---

## 5. Lead tier and architecture confidence

Two independent assessments sit on top of the scores. They answer different questions and must not be conflated.

### Lead tier

The lead tier is derived from the *best* score across all three axes:

| Tier | Best score | Meaning |
|---|---|---|
| **Exceptional** | ≥ 85 | Strong evidence on at least one axis. Highest priority. |
| **High** | 70–84 | Clear class assignment and good supporting evidence. |
| **Medium** | 50–69 | Reasonable evidence; may be boosted by a diagnostic floor. |
| **Inventory** | < 50 | Weak or unclear evidence. Record but low immediate priority. |

The tier is then subject to a set of floors and downgrades described in §6.

### Architecture confidence grade

The architecture confidence grade — A through E — measures how structurally complete and well-supported the cluster is, independent of its lead tier. It is derived from boundary status, whether a recognizable biosynthetic class is present, cluster length, and KCB similarity:

| Grade | Condition | Meaning |
|---|---|---|
| **A** | Interior + known class + ≥ 10 kb | Complete, coherent cluster |
| **B** | Interior + (known class or strong KCB) | Complete but compact or KCB-supported |
| **C** | Edge + known class | Truncated but architecturally coherent |
| **D** | Edge without known class, or Full-contig with known class | Truncated and limited |
| **E** | Everything else | Weak or ambiguous |

The judgment layer displays these as: A → High confidence, B → Moderate-High, C → Moderate, D → Low-Moderate, E → Low. This grade travels with every BGC record and is distinct from the lead tier — a cluster can be architecture grade A (well-supported structure) but Inventory tier (unattractive compound class for the current search), or grade C (truncated) but High tier (strong class evidence and KCB support).

### The RiQ recognition label

antiSMASH computes a recognition index (RiQ) for each region — how well the cluster matches the expected architecture for its assigned class. The pipeline converts this to a three-level label:

- RiQ ≥ 0.85 → "Likely known"
- RiQ 0.50–0.85 → "Possibly novel / structural variant"
- RiQ < 0.50 → "Potentially novel"

This label is additional context for the analyst; it does not affect tier assignment directly.

---

## 6. Floors, downgrades, and guards

The most analytically important logic in the pipeline is the system of floors and guards that prevents both over-claiming (a high keyword score on weak evidence) and under-claiming (a real lead buried by a low text score). These apply after the base scores are computed.

### The Tier-1 diagnostic floor

A BGC carrying a definitive class marker must not land in Inventory just because its product label is sparse or its KCB hit is absent. When a corroborated class-defining trigger fires, if the cluster would otherwise be assigned Inventory tier, it is floated to Medium:

> If a corroborated class trigger fired AND tier would be Inventory → tier becomes Medium

This floor does *not* apply to lone tailoring-enzyme markers. A halogenase installs a chlorine or bromine modification onto an existing scaffold — it modifies a compound, it does not define a compound class. A cluster with only a halogenase trigger could belong to any of dozens of compound classes. Before this exclusion was added, halogenase triggers accounted for roughly half of all floored BGCs, producing misleading Medium-tier calls for clusters whose actual class was completely undetermined.

### Primary-metabolism suppression

antiSMASH sometimes annotates housekeeping genes — enzymes involved in fatty acid synthesis, peptidoglycan maintenance, or other primary metabolic processes — as biosynthetic because they carry domain architectures that superficially resemble secondary metabolite machinery. A cluster annotated as "NRPS-like" because of a distant AMP-binding domain in a non-biosynthetic gene is not a lead.

When the primary-metabolism scan identifies housekeeping or pigment core genes in a cluster whose own product class annotations are exclusively weak labels (NRPS-like, terpene-precursor, saccharide, other), the cluster's keyword credit is stripped back to the base value. The tier and scores remain in the data for the analyst but the keyword inflation is removed.

### Mobile-element demotion

ICE (integrative and conjugative elements) and transposons can carry gene sequences that look like biosynthetic domains — antiSMASH may annotate a transposon as a lanthipeptide cluster because it noticed a LANC domain in a gene that hitched a ride on the mobile element. A cluster whose gene content is dominated by mobility machinery (integrase, recombinase, transposase, plus at least one further mobile family gene) is not a biosynthetic lead.

When the resistance tier analysis identifies a cluster as mobile-dominant and no independent class evidence corroborates it, the cluster's keyword credit is suppressed. A genuine biosynthetic cluster with incidental flanking mobile genes is protected: corroborated CCTT triggers or T1 self-resistance provide the independent evidence needed to exempt it.

### Mis-anchor guards

KnownClusterBlast similarity to a named compound does not prove that compound is made. Three specific families have known failure modes where the sequence similarity is high enough for a hit but the biosynthetic context is wrong:

**Aminoglycoside mis-anchor.** 2-deoxystreptamine-class aminoglycosides (kanamycin, gentamicin, and relatives) require a specific committed first step: the enzyme 2-deoxy-scyllo-inosose (DOIS) synthase, which forms the aminocyclitol core. Without this enzyme, no aminoglycoside backbone can be assembled regardless of what other genes are present. When an aminoglycoside KCB hit is found but the DOIS synthase gene is absent from the cluster, the hit is flagged as a mis-anchor and the aminoglycoside-derived AB score credit is suppressed.

**Polyene macrolide mis-anchor.** A genuine polyene macrolide backbone requires a large modular PKS with at least four PKS_KS (ketosynthase) domains, because the polyene chromophore requires multiple rounds of chain extension by dedicated modules. A cluster with fewer than four ketosynthase domains cannot build a polyene backbone; a polyene KCB hit under those circumstances is a mis-anchor, and the polyene-derived AF credit is suppressed.

**Enediyne discrimination.** Enediyne natural products are characterized by a specific warhead PKS — the enediyne ketosynthase (ene_KS) — whose active site is distinct from standard PKS ketosynthases. The hglE gene family encodes a different type of ketosynthase involved in hexacosalactone glycolipid biosynthesis; it cross-reacts with enediyne database entries. The pipeline distinguishes four cases: a named enediyne compound with a genuine ene_KS present (real enediyne signal), a named enediyne compound without ene_KS (mis-anchor — named compound, absent warhead), a generic enediyne signal with an hglE-type KS (PREV-001 artifact — the hexacosalactone cross-reaction), and a generic enediyne signal without hglE (unresolved). Only the first case is treated as genuine enediyne evidence.

### Standing-rule permanent downgrades

Three compound classes are permanently removed from the corrected lead order regardless of their scores:

**Saccharide** clusters encode sugar biosynthesis pathways. Sugar biosynthetic genes are present in virtually every bacterium and produce polysaccharide structural components; they are not specialized metabolite leads.

**NAPAA** (N-alkylated poly-amino acid) clusters are excluded from comparative lead claims by registry rule.

**hglE-KS / hexacosalactone** clusters are flagged with the PREV-001 standing rule: this gene family is present across essentially all actinomycetes, has no habitat specificity, and is not a discovery lead.

These BGCs keep their raw scores and are visible in the data — the downgrade is transparent and recorded. They simply do not receive a corrected lead rank, so they cannot be accidentally treated as leads in downstream analysis.

### RiPP fragment floor

Ribosomally synthesized and post-translationally modified peptide (RiPP) natural products require both a precursor peptide gene and dedicated maturation enzymes. A truncated RiPP cluster — one that is Edge or Full-contig, smaller than 8 kilobases, and carries no detectable precursor gene — cannot be evaluated as a product lead because the most important component (the precursor peptide that will become the final compound) is likely missing. Such fragments are capped at Inventory tier regardless of their score. Full-length Interior RiPP clusters are never affected.

---

## 7. Reconstructing split clusters: RG-GMCI

When a biosynthetic cluster is physically split across two or more contigs by assembly gaps, antiSMASH sees the fragments as separate, unrelated BGCs. Each fragment receives only a fraction of the cluster's gene content, which means both the architecture assessment and the scoring are degraded. A large modular PKS split into three fragments would appear as three small, weakly-annotated clusters rather than one High-tier lead.

RG-GMCI (Reference-Guided Genomic Module Co-Identification) addresses this by asking whether two BGC fragments are candidates for being two halves of the same original cluster. The evidence it uses is *shared reference geometry*: do both fragments hit the same reference cluster, and do they hit *complementary* parts of it?

RG-GMCI reads two of antiSMASH's three BLAST databases: **ClusterBlast** (cross-genome hits against other sequenced genomes) and **KnownClusterBlast** (hits against characterized MIBiG reference clusters). It explicitly excludes SubClusterBlast. Cross-genome ClusterBlast is the primary signal for fragmentation splits — a complete reference genome can tile across both arms of a split, providing the shared-reference geometry that identifies the pair. KnownClusterBlast adds named-compound corroboration when it is available, but a rescue pair can reach HIGH confidence on cross-genome ClusterBlast evidence alone, with zero MIBiG hits. This matters for discovery: most cryptic clusters have no MIBiG entry, so restricting to KnownClusterBlast would blind the rescue to exactly the clusters most worth finding.

### The pairwise evidence score

For each pair of BGCs, RG-GMCI computes an additive score from several lines of evidence:

The most important is **reference adjacency**: if fragment A's best reference hit and fragment B's best reference hit are adjacent or overlapping segments of the same reference cluster, that is strong evidence they are flanking halves of a split. If the fragments hit distant parts of the same reference, that is weak and cautionary. If the fragments hit overlapping segments of the reference (both covering the same reference genes), that is evidence they are *paralogs* — two related but distinct clusters — not two halves of the same cluster.

Additional evidence comes from **protein support** (how many query genes from each fragment hit the reference), **reference rank quality** (whether the reference hit appears among the top-5 hits, indicating strong rather than marginal similarity), **sequence identity** (what percent identity the gene-level matches show), and **shared product tokens** (whether both fragments carry matching product class or compound-type labels).

A small bonus is added when either fragment is not Interior — fragmentation evidence — and when the two fragments are on different contigs. These signals are consistent with a genuine split.

The score thresholds: ≥ 14 is HIGH_RGGMCI_RESCUE (strong evidence for a genuine split); 9–13 is MODERATE_RGGMCI_CANDIDATE; below 9 is LOW (noise).

### Why a high score is necessary but not sufficient

A high raw score alone is not sufficient to call a pair a genuine split. Several quality gates can demote HIGH → MODERATE:

A pair where both fragments drop their product class after standing-rule exclusions is demoted — there is no meaningful class to rescue. A pair where neither fragment has strong reference support is demoted. A BGC that scores HIGH against more than four other BGCs is flagged as "hub-promiscuous" — a genuine split is between two specific fragments, not one fragment and five others simultaneously.

### What the split verdict means

Independently of the score, RG-GMCI classifies the geometric relationship between the two fragments' reference gene sets:

- **Complementary split**: the two fragments hit different, non-overlapping parts of the reference. This is the canonical split-cluster pattern and is treated as genuine.
- **Terminus truncation**: one fragment ends at a contig boundary in a way that is consistent with it being a severed arm of a larger cluster. Also genuine.
- **Overlapping paralog**: both fragments hit the same reference genes, meaning they are likely two members of the same compound family rather than two halves of the same cluster. This is excluded. Raw-score ranking once placed an overlapping paralog pair at the top of the rescue list before this classification was added.
- **Mixed or insufficient data**: ambiguous; sent to the manual review queue.

### What rescue changes

When a BGC pair is classified as a genuine split, the routing bonus (+8 or +4 points on all three axes) is applied to both fragments. This raises their priority in the lead queue so they are analyzed together rather than separately and belatedly. The bonus changes *routing priority* only — it does not change the *claim confidence* for either fragment. Both fragments are still Edge or Full-contig BGCs with truncated gene content; the architecture assessment and product class claims still reflect what is actually sequenced.

---

## 8. Completeness: every cluster is scored

A prior cohort merge passed scores only for lead-tier clusters — roughly 9% of the total — while silently omitting the rest. The pipeline enforces a completeness invariant: every BGC in a run, including Edge and Full-contig fragments, receives AB, AF, and novelty scores. Runs that fail this invariant raise an error rather than shipping incomplete data silently.

This matters for cross-strain comparisons. If one strain has 40 BGCs scored and another has 40 BGCs with only the top 8 scored, any calculation that averages or compares score distributions across strains will be wrong. The invariant ensures this failure mode cannot occur silently.

---

## 9. When a run is split into batches

Very large runs — more than 25 raw BGCs, or more than 15 Edge/Full-contig BGCs combined, or a run with complex split-cluster rescue candidates — are flagged for multi-batch judgment processing. The extraction is complete and produces a single sealed package; the multi-batch flag tells the judgment layer to divide the Mode B analysis into coherent sub-sessions rather than attempting to process everything at once.

---

## 10. Which KCB hit gets displayed

Every BGC may carry a KnownClusterBlast hit, and the obvious thing to display is the rank-1 hit — the single best-scoring reference cluster. In practice, the rank-1 hit is usually the wrong thing to show.

The reason is the genome self-hit problem. The KCB reference database contains both curated MIBiG entries (characterized compounds) and whole sequenced genomes. When a BGC is queried, its strongest hit is almost always to a related organism's genome rather than to a named compound's cluster — there are far more genome entries than MIBiG entries, and a closely related genome will match across the entire cluster. Across a corpus of more than 3,400 BGCs, only about 2.2% surface a MIBiG accession as their rank-1 hit, while about 59% have a MIBiG entry resolvable somewhere in their results.

The consequence: if the display simply showed the rank-1 line, the vast majority of BGCs would show an uninformative genome description ("Streptomyces vietnamensis genome assembly, scaffold 4") instead of the meaningful compound name ("granaticin") that is sitting a few ranks down. The granaticin positive control was exactly this case — its rank-1 hit is a genome self-hit that masks the granaticin MIBiG line.

The pipeline resolves this with a preferred-anchor rule. The resolved MIBiG compound line is captured separately during extraction (in the `closest_candidate_kcb_product` and `closest_mibig_accession` fields). Whenever a BGC has a resolved MIBiG reference line, the display prefers it over the raw rank-1 hit:

> If a resolved MIBiG reference line exists → display "compound name (accession)"  
> Otherwise → display the raw rank-1 KCB line

This rule surfaces an already-captured field; it does not re-rank or recompute anything. Every consumer that displays the known-cluster hit — the workbook KCB column, figure labels, lead tables — applies this rule so the meaningful compound name is shown consistently. And it remains a similarity signal throughout: the displayed compound name says the cluster *resembles* that reference, never that the strain produces that compound.

---

## 11. Reading the triage rationale

Every scored BGC carries a rationale string — a compact, machine-generated audit trail explaining how it was assessed. This string appears in the workbook and in Mode B cards, and learning to read it is the fastest way to understand why a BGC scored the way it did. It is pure formatting: it reports the flags and decisions made elsewhere in the scoring, in a fixed order.

A rationale always begins with the structural basics:

> `Edge; Arch C; KCB=8450; RiQ=0.62; products=NRPS, halogenated`

This says: the BGC is an Edge fragment, architecture confidence grade C (truncated but coherent), cumulative KCB similarity 8,450, RiQ recognition 0.62, and its product classes are NRPS and halogenated. When an architecture-capacity call is available, it is appended as `ARCH-CAPACITY: ...` with its confidence.

After the basics, the rationale appends a segment for each guard, floor, or flag that fired — and only those that fired. The possible segments, each a self-explaining tag:

- **`RG-GMCI=HIGH via BGC013+BGC001`** — this BGC is supported by a split-cluster rescue link at the stated confidence and partner.
- **`DIAG-FLOOR: T43-NUC floored to Medium`** — a corroborated class-defining trigger fired and lifted an otherwise-Inventory BGC to Medium tier.
- **`RIPP-FRAGMENT-FLOOR: ...capped at Inventory`** — a truncated sub-8 kb RiPP fragment with no precursor was capped at Inventory.
- **`AF-diagnostic(T43-PTM)`** — a corroborated antifungal diagnostic trigger added its bonus to the AF axis.
- **`CCTT-UNCORROBORATED (T43-PHO): fired on class-incompatible locus`** — a trigger fired but on an incompatible class, so it was recorded but excluded from any bonus or floor.
- **`PRIMARY-METAB/PIGMENT FLAG (housekeeping): AB/AF credit suppressed`** — the BGC was identified as housekeeping or pigment, and its keyword credit was stripped.
- **`STANDING-RULE DOWNGRADE (saccharide-exclusion): excluded from corrected lead rank`** — a permanent exclusion removed the BGC from the lead order. For hglE-KS the note adds "structural novelty unaffected," because only the lead claim is downgraded while the novelty score stands.
- **`MIS-ANCHOR (aminoglycoside_anchor_no_DOIS): anchor-derived credit suppressed`** — a KCB anchor was found to lack its class-diagnostic gene, so the anchor credit was removed.
- **`MOBILE-ELEMENT DEMOTION (transposase,integrase): AB/AF credit suppressed`** — the region is dominated by mobility machinery and was not independently class-typed.
- **`[E-signal] named-enediyne KCB anchor (similarity, structure NOT confirmed)`** — a named enediyne anchor is present but the enediyne warhead was not confirmed; the BGC is flagged as an enediyne candidate, neutrally.

Reading a rationale top to bottom reconstructs the full scoring decision: the structural starting point, then every adjustment in the order it was applied. A BGC that reads `Interior; Arch A; KCB=0; RiQ=0.41; products=lanthipeptide; AF-diagnostic(T43-LAN)... DIAG-FLOOR: T43-LAN floored to Medium` tells you at a glance that this is a complete, KCB-dark, structurally-novel lanthipeptide whose diagnostic trigger rescued it from a low text score — exactly the kind of cryptic lead the pipeline exists to surface. The rationale is the single best place to audit whether a score is trustworthy.

---

## Summary of key constants

| Parameter | Value | What it governs |
|---|---|---|
| Edge flank tolerance | 5,000 bp | Minimum distance from contig end for Interior classification |
| Full-contig threshold | ≥ 95% of contig length | Cluster is "essentially the whole contig" |
| Corrected-count weights | 1.0 / 0.5 / 0.25 | Interior / Edge / Full-contig discounting |
| Assembly tier thresholds | 70% / 45% / 20% | GOOD / MODERATE / POOR / VERY_POOR |
| GC dispersion flag | ≥ 5% standard deviation | CONTAMINATION_SUSPECT |
| Score base values | 25 / 20 / 30 | AB / AF / novelty floor |
| Diagnostic bonus | 25 points | Corroborated CCTT class trigger |
| KCB strong novelty adjustment | −15 points | KCB cumulative score > 10,000 |
| No-KCB novelty adjustment | +5 points | No KCB signal present |
| Low-RiQ novelty adjustment | +10 points | RiQ < 0.5 |
| Rescue bonus | 8 / 4 points | HIGH / MODERATE RG-GMCI split-cluster pair |
| Lead tier thresholds | 85 / 70 / 50 | Exceptional / High / Medium |
| RiPP fragment size ceiling | < 8 kb | Truncated RiPP clusters capped at Inventory |
| RG-GMCI HIGH threshold | Score ≥ 14 | Strong split-cluster evidence |
| RG-GMCI MODERATE threshold | Score ≥ 9 | Candidate split-cluster evidence |
| Hub-degree maximum | 4 links | Promiscuity demotion |
| Multi-batch trigger | 25 raw BGCs or 15 Edge+FC BGCs | Split judgment into sub-sessions |

---

*Sapote–Mamey · Mamey engine v1.9.110 (frozen; the math tracks the engine, not the rolling bundle) · constants re-verified against source 2026-07-14*  
*Every formula and constant cited from engine source. Scores are routing priors, not biological proof; KCB is similarity, not identity; capacity-level language is mandatory downstream of all values in this document.*


---

# The Mathematics of Sapote–Mamey, Volume II

## Cluster A: The Source-Scan and CCTT Trigger Engine

**Mamey engine v1.9.110 · bundle v9.7.319**  
****  
**Companion to:** Volume I (core counting, scoring, tiers, RG-GMCI) and Clusters B–F of this volume.

This cluster covers the source-scan engine — the battery of analytical passes Mamey runs on every genome after the BGC inventory is built. All of these passes work exclusively from the antiSMASH GenBank files that were already parsed; nothing here calls antiSMASH again or hits an external database at runtime.

Two standing interpretive rules apply throughout:

**Scores are routing priors, not biological proof.** No CCTT trigger — singly or in combination — is evidence that a strain produces a compound. The appropriate language is "biosynthetic capacity consistent with…" never "produces."

**KCB is similarity, not identity.** Every KnownClusterBlast signal is a sequence-similarity score against a reference database. The mis-anchor guards described below exist precisely because KCB similarity is easy to over-read.

---

### What the source-scan engine does

Before scoring, the pipeline needs a richer picture of each BGC than the raw antiSMASH product class label provides. A cluster labelled "NRPS,T1PKS" could be many things — a glycopeptide, a lipopeptide, a PTM antifungal, a siderophore, a butyrolactone autoregulator. The source-scan engine interrogates the gene content to find out which.

Every scan operates on the same input: the list of CDS features and their annotations from the antiSMASH GenBank files. Each scan answers a different question:

- **CCTT triggers** — does this BGC carry a diagnostic marker for a specific chemotype?
- **FLBR/LMPKS** — does the genome contain more large-synthase machinery than the called BGC set accounts for?
- **Resistance tiering** — does this BGC carry self-protection genes consistent with producing a bioactive compound?
- **bldA/TTA tiering** — are genes in this cluster developmentally regulated (actinomycetes only)?
- **UMED** — if this is a RiPP cluster, are its maturation enzymes present?
- **EFLS** — do two BGCs on different contigs share evidence that might link them as parts of the same pathway?
- **TFBS** — are there transcription factor binding sites upstream of genes in this cluster?
- **QS/NAPAA routing** — should this BGC be flagged as a signalling molecule rather than a bioactive lead?
- **Primary-metabolism suppression** — are the "biosynthetic" genes in this cluster actually housekeeping genes?
- **Mis-anchor guards** — does the KCB compound hit require a biosynthetic gene that is absent?
- **Cassette families** — does the cluster carry characteristic tailoring-enzyme cassettes?
- **DSS precompute** — what is the combined diagnostic signal weight of this BGC?

The outputs of all these scans feed the scoring engine. Seven of them directly affect how a BGC is scored or tiered.

---

### How matching works: the annotation haystack

Every scan uses the same matching substrate: a lowercase text string assembled from each CDS's annotation fields. This "haystack" combines the gene product annotation, the locus tag, and all qualifier fields (excluding the raw translation sequence, which is large and would cause catastrophic regex backtracking). Matching is case-insensitive throughout.

Importantly, the scans match against antiSMASH's gene-level text annotations — they do not run HMMER or BLAST profiles. Domain evidence comes from antiSMASH's `sec_met_domain` qualifiers that were already computed during genome annotation; the scan engine reads and re-uses those rather than recomputing them.

After matching, each hit is spatially coupled to BGC records: a gene hit is assigned to a BGC if the gene is within a coupling distance of the BGC's coordinates. Most scans use a 10,000 bp flank — a gene up to 10 kb outside a BGC's formally annotated boundaries is considered coupled to it. The exceptions are meaningful: the UMED and cassette scans use 5,000 bp (tighter, because maturation genes and cassette enzymes are typically proximal to the core), and the primary-metabolism scan uses 0 bp (only genes *inside* the BGC's own coordinates matter, because the failure mode being corrected is a mislabelled gene inside the region, not a flanking neighbor).

---

### The 14 CCTT triggers

The Chemistry-Class Trigger Tower (CCTT) is the pipeline's gene-level diagnostic system. Each trigger is a named chemistry class with a corresponding set of annotation patterns; a trigger fires when any of its patterns matches in the annotation haystack of any gene within 10 kb of a BGC.

| Trigger | What it detects | Bioactivity relevance |
|---|---|---|
| **T43-HAL** | Flavin-dependent halogenase | Chlorinated or brominated derivatives — tailoring modification, not a class call |
| **T43-XHAL** | SAM-dependent fluorinase/chlorinase | Organohalogen building-block enzymes (SalL/FlA family) |
| **T43-PHO** | PEP mutase — committed phosphonate biosynthesis | Phosphonate antibiotics (fosfomycin class) |
| **T43-NUC** | TruD pseudouridine synthase, NikJ, nikkomycin/polyoxin-specific enzymes | Nucleoside antibiotic chitin-synthase inhibitors — antifungal |
| **T43-PTM** | Single-protein KS + AMP-binding fusion (2,500–4,000 aa) or HSAF/PTM KCB hit | HSAF/polycyclic tetramate macrolactam — antifungal |
| **T43-ENE** | Enediyne ketosynthase (ene_KS), TIGRFAM TIGR03828 | Enediyne warhead natural products |
| **T43-LAN** | LANC-like cyclase or Lant_dehydr dehydratase | Lanthipeptide RiPP — antibacterial |
| **T43-LASSO** | Asn_synthase-family lasso cyclase | Lassopeptide RiPP — antibacterial |
| **T43-THA** | Thioamide-associated enzymes | Thioamide NRP — antibacterial |
| **T43-AMC** | 2-deoxy-scyllo-inosose synthase (DOIS) or BtrC | Aminoglycoside/aminocyclitol antibiotics — antibacterial |
| **T43-BLA** | Beta-lactam biosynthetic enzyme (isopenicillin N synthase, nocardicin cyclase) | Beta-lactam antibiotics — antibacterial |
| **T43-IDC** | Indolocarbazole synthase (StaD/RebC family), TIGRFAM TIGR01454 | Indolocarbazole alkaloids (staurosporine class) |
| **T43-NN** | N–N bond forming enzyme | Nitrogen–nitrogen linked natural products |
| **T43-DKP** | Cyclodipeptide synthase (CDPS) | Diketopiperazine scaffolds |

Note that T43-HAL and T43-XHAL are **tailoring triggers**, not class-defining triggers. A halogenase installs a chlorine or bromine on a scaffold, but the scaffold could belong to any compound class. These two triggers do not grant the Tier-1 floor bonus and do not count as class-defining evidence (see the scoring section of Volume I §6.2). They do play a role in the diagnostic rescue engine (Cluster E), where a halogenase-carrying fragment is the expected tailoring arm of a split pathway whose core biosynthetic genes are on a different contig. All other triggers in the table are class-defining.

#### The corroboration requirement

A trigger only counts when it fires on a class-compatible BGC. This is the corroboration check: the trigger's expected compound class must be consistent with the BGC's own product label. T43-PHO (phosphonate) firing on a type-III PKS (chalcone synthase) BGC is suspicious — phosphonate biosynthesis has nothing to do with chalcone synthases. An uncorroborated trigger is still recorded and visible to the analyst but grants no bonus and does not floor the tier.

There is an additional guard for mobile-genetic-element regions. A BGC whose gene content is dominated by mobility machinery (integrase or recombinase or transposase, plus at least one other mobile-element gene family, or three mobile-element families regardless of a core mobility gene) cannot have its class-defining triggers corroborated by a matching product label alone. An ICE element carrying a lanthipeptide annotation because antiSMASH noticed a LANC domain in one of its genes is not a genuine lanthipeptide cluster, and the T43-LAN trigger will not float it to Medium tier.

#### Known asymmetry: T43-PTM corroboration

The T43-PTM corroboration set includes generic tokens like "pks," "nrps," and "t1pks," which are present in a very broad range of antiSMASH product calls. This means T43-PTM is harder to flag as uncorroborated than more specific triggers like T43-NUC. This asymmetry is intentional: genuine HSAF-class clusters are frequently typed by antiSMASH as generic NRPS/PKS hybrids without a compound-specific name, so tight corroboration would miss real PTM leads. The tradeoff is that T43-PTM is somewhat more permissive than other class triggers.

#### How T43-PTM fires: two independent routes

T43-PTM can be triggered by two separate mechanisms, either of which is sufficient:

**Route A (annotation-driven):** any PTM compound name appears in the KCB evidence string — the product annotation, MIBiG hits, or resolved KCB product name.

**Route B (architecture-driven):** the BGC contains a lone hybrid ketosynthase (a megasynthase with both KS and NRPS-type domains) and no modular-KS genes. This is the single-protein iPKS-NRPS signature of HSAF/PTM architecture. Route B requires at least one tetramate or macrolactam keyword anywhere in the evidence string as well — a genuine lone hybrid plus a chemical-class hint. A generic multi-module hybrid assembly line does not trigger Route B.

Both routes record which route fired, for audit.

#### The T43-PHO pattern: precision by exclusion

The phosphonate trigger faces an unusual challenge: the word "phosphonate" appears in many contexts that have nothing to do with phosphonate antibiotic biosynthesis — phosphonate transporters (uptake of environmental phosphonates), phosphonate utilization (catabolism), and the C–P lyase operon (another catabolism pathway). The committed biosynthetic step is PEP mutase activity, which is the *only* context that indicates phosphonate *production*.

The T43-PHO pattern achieves this precision through a positive match (phosphonate or PEP mutase) combined with explicit negative exclusions: carboxyphosphonate (a metabolic intermediate), "transporter," "utilization," "C-P lyase," and the specific structural gene names of the C–P lyase operon. The result is a trigger that fires on the committed biosynthetic step and is silent on the much more abundant catabolic and transport genes.

---

### FLBR: detecting fragmented megasynthase sets

FLBR (Fragment-Locus-BGC-Rescue) asks a genome-level question: does this genome carry more large-synthase-like sequences than the called BGC set can account for? If a genome has four ketosynthase-bearing genes but they are distributed across three BGCs each marked Edge or Full-contig, at least some of those BGCs are probably fragments of a single split pathway.

The scan counts genome-wide CDS annotations matching modular KS (standard PKS ketosynthase), hybrid KS (PKS-NRPS), trans-AT KS (explicit trans-acyltransferase ketosynthase), and nonribosomal peptide synthetase. If there are four or more ketosynthase-bearing genes across a genome AND fragmented BGCs (Edge or Full-contig) with PKS or NRPS annotations, the genome is flagged as a Large Modular PKS Fragment Set (STRONG) or a Megasynthase Fragment Suspect (WEAK) depending on the counts.

Rescue readiness is tiered by how severe the fragmentation is: HIGH when the assembly is below the GOOD threshold and there are both orphan KS-bearing sequences (outside any called BGC) and multiple fragmented BGCs; MODERATE when conditions are less extreme; LOW otherwise.

The orphan KS detection is annotation-independent: the scan examines CDS sequences outside the called BGC boundaries for the KS active-site motif ([DE]TAC[ST]S — the catalytic cysteine motif shared by all beta-ketoacyl synthases). A long protein carrying this motif but not annotated as part of any BGC is likely a stranded biosynthetic fragment. The AT active-site motif (GHSxG) is also checked, but sequences with only that motif are explicitly flagged as "likely standalone hydrolase" — the GHSxG motif is shared with lipases, esterases, and peptidases, so it alone is not strong biosynthetic evidence. Only the KS-motif-bearing orphans are Tier-1 signals; AT-only orphans are listed separately and explicitly excluded from the megasynthase fragment count.

The FLBR output feeds the T43-PTM Route B coupling (see the CCTT section above) and the RG-GMCI rescue engine, which uses FLBR's megasynthase census to contextualize whether a fragmentation split is structurally plausible.

---

### Resistance tiering

Self-resistance is one of the strongest lines of source-derived evidence that a cluster is producing something bioactive. The logic is simple: if an organism has evolved a mechanism to protect itself from a compound class, it almost certainly makes something in that class. A glycopeptide-resistance VanHAX gene cluster sitting inside a BGC annotated as an NRPS is much more likely to be protecting the producer from its own glycopeptide than to be an incidentally acquired resistance cassette.

The resistance tier classifier assigns one of four tiers:

- **T1 (diagnostic self-protection):** a class-specific resistance gene is present AND its resistance class matches the BGC's product class. The resistance gene families that reach T1 are Erm methylases (protect against macrolides, lanthipeptides, and related classes), VanHAX-like enzymes (glycopeptide resistance), APH/AAC aminoglycoside kinases (protect against aminoglycosides and nucleosides), and fosfomycin resistance enzymes (phosphonate resistance).
- **T2 (resistance-like):** a resistance gene is present but the class concordance is weaker or the gene family is broad.
- **T3 (transporter-only):** only an efflux pump or ABC transporter is present, which provides limited class-specificity.
- **NULL:** no resistance signal.

Class concordance is checked by matching the resistance group against the BGC's own product class text. A VanHAX gene is concordant with a BGC annotated as a glycopeptide; it is not concordant with a terpene cluster.

The mobile-element guard applies here too. A T1 resistance gene on a mobile-dominant BGC whose resistance class does not match the BGC's product is reclassified as mobile cargo — an incidentally acquired resistance gene carried by a transposon, not self-protection. This is the PC-12 guard: it was added after an ICE element carrying an aminoglycoside phosphotransferase (APH) was floating to Medium tier as a High-confidence antibacterial lead on the strength of the T1 self-resistance signal.

#### The APH/sugar-kinase veto

APH (aminoglycoside phosphotransferase) genes share sequence motifs with sugar kinases involved in glycogen and trehalose metabolism. When an APH hit is found but the BGC's neighbourhood contains glycogen-, trehalose-, or sugar-kinase-related genes, the APH hit is removed before tiering. The same veto fires for the T43-NUC CCTT trigger, which faces the same sugar-kinase false-positive.

---

### CCTT vetoes: related-family false fires

Three CCTT triggers have known false-positive failure modes where a structurally unrelated gene family uses similar annotation vocabulary:

**T43-NUC (nucleoside)** can misfire on glycogen and trehalose pathway genes because some nucleoside biosynthesis enzymes share names with carbohydrate kinases. When a BGC's neighbourhood contains glycogen/trehalose/sugar-kinase context AND the BGC's own product class does not independently say "nucleoside," the T43-NUC coupling is removed for that BGC.

**T43-ENE (enediyne)** can fire on hglE/hglD (heterocyst glycolipid ketosynthase) genes, which share structural motifs with the enediyne warhead ketosynthase but are entirely different biochemically. When hglE/hglD context is present without independent enediyne product class evidence, the T43-ENE coupling is removed. This is the PREV-001 artifact described in the mis-anchor guards below.

**T43-DKP (diketopiperazine)** can fire on copalyl diphosphate synthase, a terpene cyclase, because both enzymes share the "CDPS" abbreviation in annotation databases. When terpene synthase context (geranylgeranyl diphosphate synthase, copalyl diphosphate synthase) is present without independent cyclodipeptide product class evidence, the T43-DKP coupling is removed.

For each of these vetoes, the trigger is removed from the BGC's coupling but logged separately. The evidence is preserved for the analyst to see; it is only suppressed from the automatic scoring effects.

---

### Mis-anchor guards

Four compound families have well-documented failure modes where sequence similarity produces a credible-looking KCB hit but the essential biosynthetic machinery is absent. The guards operate on the KCB anchor (the resolved MIBiG compound hit), not on the antiSMASH product class.

**Aminoglycoside mis-anchor.** 2-deoxystreptamine aminoglycosides (kanamycin, gentamicin, tobramycin, and relatives) all require 2-deoxy-scyllo-inosose (DOIS) synthase to form the aminocyclitol core. Without this committed first step, no 2-deoxystreptamine scaffold can be assembled. When an aminoglycoside KCB hit is found but DOIS synthase (or its close relative BtrC) is absent from the BGC's own genes, the hit is a mis-anchor and the aminoglycoside-derived AB credit is suppressed.

**Polyene macrolide mis-anchor.** Polyene macrolide antifungals (nystatin, amphotericin, candicidin) require a very large modular PKS with at least four ketosynthase domains — the polyene chromophore needs multiple rounds of chain extension by dedicated modules. A cluster with fewer than four PKS_KS domains cannot build a polyene backbone. When a polyene KCB hit is found on a cluster with fewer than four KS domains, the hit is a mis-anchor and the polyene-derived AF credit is suppressed.

**Enediyne discrimination.** This is the most nuanced guard, because the term "enediyne" appears in both genuine enediyne natural product names (calicheamicin, dynemicin, esperamicin) and in the hglE heterocyst glycolipid ketosynthase gene, which produces a structurally unrelated lipid but shares enough sequence similarity with the enediyne warhead PKS to produce KCB hits against enediyne reference clusters. The pipeline distinguishes four cases:
- Named enediyne compound + ene_KS domain present → **genuine enediyne signal**
- Named enediyne compound + no ene_KS domain → **enediyne mis-anchor** (compound named, warhead absent)
- Generic enediyne signal + hglE/hglD present → **PREV-001 artifact** (hexacosalactone cross-reaction)
- Generic enediyne signal without hglE → **unresolved** (ambiguous, passes to judgment layer)

Only the first case is treated as genuine enediyne evidence.

**KCB class mismatch.** A small set of compound-specific rules catches cases where a named KCB compound is chemically incompatible with the BGC's own antiSMASH product class. For example: a kinamycin hit on a BGC typed as terpene. Kinamycin is an aromatic T2PKS diazobenzofluorene — it has no terpene biosynthetic logic whatsoever. A dozen or so such compound-class incompatibilities are encoded. When the mismatch fires, the anchor-derived AB/AF/novelty credit is suppressed unless a Tier-1 diagnostic independently fires.

---

### The Diagnostic Signal Score (DSS 0–5)

The DSS is a precomputed per-BGC summary of how much diagnostic evidence it carries, on a scale from 0 to 5. It is used by the Sapote judgment layer to quickly assess how well-grounded a BGC is before reading the full Mode B data:

> DSS = +2 if any Tier-1 biosynthetic domain is present (PKS_KS, NRPS adenylation, thioesterase, YcaO cyclodehydratase, halogenase, or RiPP precursor)  
> DSS = +1 if the KCB similarity is supported by 5 or more protein hits  
> DSS = +1 if the resistance tier starts with T1 (self-protection) for this BGC  
> DSS = +1 if any CCTT trigger is coupled to this BGC  
> DSS is capped at 5.

A BGC with DSS 5 has biosynthetic domains, good KCB support, self-resistance, and a class trigger — it is well-grounded on multiple independent lines of evidence. A BGC with DSS 0 has none of these. The DSS is a routing precompute, not a final judgment — the Sapote layer applies the authoritative interpretation.

---

### UMED: detecting missing maturation enzymes

Ribosomally synthesized and post-translationally modified peptide (RiPP) natural products require dedicated maturation enzymes. Lanthipeptides need LanC cyclases and LanB dehydratases. Lassopeptides need an Asn_synthase-family cyclase. Thioamide RiPPs need YcaO and TfuA enzymes. Nucleoside antibiotics need pathway-specific modifications.

When a BGC is annotated as a RiPP class but none of the expected maturation enzymes are found within 5,000 bp of the cluster, UMED flags it as MATURATION_GAP. This usually means the maturation genes are on a different contig (a split cluster) or the BGC is a fragment that captured only part of the pathway.

The MATURATION_GAP verdict does *not* suppress the BGC's lead score — it raises it. A BGC with clear precursor logic but missing maturation enzymes is a candidate for an off-cluster or split-locus enzyme, which is worth noting and investigating. The gap flag tells the judgment layer to look for the missing piece on a nearby contig.

Verdicts: IN_CLUSTER_OR_PROXIMAL_MATURATION (needs maturation + found it), MATURATION_GAP (needs it + missing), NOT_MATURATION_GATED (class does not require post-translational modification).

---

### EFLS: preliminary shared-evidence linkage

EFLS (Evidence-Fragmentation-Linkage-Scan) is a lightweight precursor to the full RG-GMCI split-cluster engine. It nominates BGC pairs that might be halves of the same split pathway by checking how much evidence they share:

> Score = +1 per shared antiSMASH product class token  
> +2 per shared MIBiG reference hit (weighted higher than product class because a named reference is stronger evidence)  
> +1 per shared cassette family  
> +1 per shared CCTT trigger  

A score of 3 or above is classified as "complementary or shared evidence"; lower scores are "weak shared evidence." EFLS only examines pairs where at least one member is Edge or Full-contig — two complete Interior clusters that share vocabulary are more likely to be paralogs than split fragments.

EFLS is explicitly marked as preliminary: it uses shared class vocabulary and named references, not the geometrically verified gene-level tiling that RG-GMCI performs. RG-GMCI uses cross-genome ClusterBlast hits against sequenced reference genomes, not just KnownClusterBlast hits against MIBiG entries — this lets it find split evidence even for cryptic clusters with no characterized close relative. EFLS's output feeds the judgment layer as a first-pass nomination, not a confirmed split.

---

### bldA/TTA tiering (actinomycetes only)

In actinomycetes, the bldA gene encodes the only tRNA that efficiently decodes UUA (TTA) leucine codons. Because bldA expression is linked to morphological differentiation, genes containing TTA codons are developmentally regulated — they can only be fully translated when bldA is expressed.

The TTA tier counts UUA codons across all CDS within a BGC and assigns:

| Tier | TTA codon count | Meaning |
|---|---|---|
| T1 | 0 | No bldA dependence — constitutively translated |
| T2 | 1–2 | Low TTA burden — minor bldA sensitivity |
| T3 | 3–5 | Moderate burden — bldA-sensitive expression plausible |
| T4 | ≥ 6 | High burden — strongly bldA-dependent |

This analysis is gated on actinomycete taxonomy. In non-actinomycete bacteria, fungi, and other organisms, UUA codon frequency reflects GC content, not developmental regulation — a T4 call on a fungal genome would be biologically meaningless. The pipeline explicitly marks TTA analysis as NOT_APPLICABLE for non-actinomycete organisms.

---

### TFBS: transcription factor binding site scan

The TFBS scan looks for regulatory binding site motifs in the 300 bp upstream window of each CDS. Twelve regulator families are scanned, including DasR (central regulator of GlcNAc/chitin catabolism and linked secondary metabolite production), DmdR (iron-responsive repressor), BldD (master developmental regulator), and others covering stress response, iron acquisition, phosphate sensing, and quorum sensing.

The scan uses consensus IUPAC motifs with ambiguity codes rather than calibrated position-weight matrices. The claim-safety string in the output is explicit: "Simple motif scan; replace with calibrated TFBS models/background scoring before manuscript use." These counts are evidence for induction planning — if a BGC has multiple DasR sites, GlcNAc supplementation is worth trying — not expression proof.

---

### QS and NAPAA routing

Clusters encoding quorum-sensing signal molecules (butyrolactones, HSL autoinducers, furans) are flagged for ecology-only routing. These compounds have signalling functions and are excluded from the AB/AF mechanistic-link wet-lab bonus — they are relevant to population biology but not to antibiotic lead programs.

NAPAA (N-alkylated poly-amino acid) BGCs are flagged separately. NAPAA flagging is neutral — the earlier hypothesis linking NAPAA to Nosema infection control has been retired. The flag records the compound class; it does not downgrade the BGC.

---

### Primary-metabolism suppression

antiSMASH sometimes annotates housekeeping genes as biosynthetic because they carry domain architectures that superficially resemble secondary-metabolite machinery. A topoisomerase with a distant AMP-binding domain might be annotated as "NRPS-like." A carotenoid pigment pathway might be annotated as "terpene."

The primary-metabolism scan checks each BGC's own CDS for three housekeeping families: central-metabolism enzymes (DNA polymerases, RNA polymerases, aminoacyl-tRNA synthetases, topoisomerases, elongation factors), pigment biosynthesis genes (lycopene, phytoene, carotenoid, arylpolyene, melanin), and replication-core genes (DnaB helicase, primase, sliding clamp, single-stranded DNA-binding protein).

The suppression fires only when *two* conditions are simultaneously true: the BGC's own antiSMASH product class is an exclusively weak/over-call label (NRPS-like, terpene, saccharide, other), AND a housekeeping/pigment core gene is inside the BGC's own boundaries. A committed biosynthetic backbone class (NRPS, T1PKS, lanthipeptide) overrides the suppression, as does a corroborated Tier-1 CCTT trigger. The coupling is `flank=0` — only genes inside the BGC's own coordinates count, not flanking neighbors.

---

### Cassette families

Fifteen named cassette families are scanned with a 5,000-bp coupling flank. Cassettes are functional groups of tailoring enzymes that are commonly associated with specific compound classes; their presence provides additional class evidence beyond the core biosynthetic genes.

Tier-1 cassettes (strongest evidence): phosphonate, nucleoside, aminoglycoside/aminocyclitol, tetronate/spirotetronate, thioamide/YcaO, lassopeptide, TOMM/azole RiPP, polyene/PTM/HSAF. Tier-2 cassettes: halogenation, lanthipeptide, siderophore/metallophore, chitin/glycan ecology. Tier-3: release macrocyclization, glycosylation. Tier-5 (inventory routing only): transporter/resistance.

---

### Summary of key constants

| Parameter | Value | What it governs |
|---|---|---|
| CCTT coupling flank | 10,000 bp | How far from a BGC a gene hit can be and still couple |
| Cassette/UMED coupling flank | 5,000 bp | Tighter coupling for maturation genes and cassettes |
| Primary-metabolism flank | 0 bp | Only genes inside the BGC count |
| FLBR KS count threshold | ≥ 4 | Minimum ketosynthase genes for STRONG fragmentation flag |
| FLBR orphan exclusion | ± 20,000 bp | How far outside a called BGC before a KS gene is "orphan" |
| Polyene mis-anchor threshold | < 4 PKS_KS domains | Below this, polyene anchor is suppressed |
| T1 self-resistance | class-concordant group present | Required for T1 tier |
| Mobile-dominant threshold | core hit + ≥2 mobile families, or ≥3 mobile families | Below this, one IS element is not "dominant" |
| TTA T4 threshold | ≥ 6 TTA codons | Strongly bldA-sensitive |
| TFBS upstream window | 300 bp | Scanning window for regulatory motifs |
| EFLS minimum score | ≥ 3 | Minimum for "complementary/shared evidence" |
| Glycosylation-arm trap | ≥ 3 protein hits | Distinguishes authentic sugar-cassette arm from incidental overlap |
| DSS cap | 5 | Maximum diagnostic signal score |

---


---

# The Mathematics of Sapote–Mamey, Volume II

## Cluster B: Architecture-First Assessment and Scoring Context

**Mamey engine v1.9.110 · bundle v9.7.319**  
****  
**Cross-reference:** The AB/AF/novelty formulas, tier thresholds, and guard logic are documented in Volume I. This cluster covers the architecture-first assessment that precedes scoring, and the rules-registry and audit tooling that enforce integrity downstream.

---

### The problem: KCB confirmation bias

KnownClusterBlast returns a compound name. If that compound name is read before the cluster's gene content is examined, it anchors the interpretation. A BGC with a "clifednamide" KCB hit gets mentally filed as a PTM antifungal before anyone has checked whether it carries the PTM diagnostic gene — the single-protein fused iPKS-NRPS at 2,500–4,000 amino acids. If the gene content says "trans-AT PKS assembly line," that conflict gets resolved toward the KCB label because it came first. This is confirmation bias baked into the order of operations.

The architecture-first assessment solves this by making the order explicit: gene content is assessed completely, with no knowledge of the KCB hit, before the KCB hit is consulted. The architecture result is the primary evidence. The KCB hit is then checked for concordance with that result. When they agree, both lines of evidence are reported. When they disagree, the architecture wins.

---

### Step 1: Classify the gene content, blind

The input is a list of genes with their protein sizes and antiSMASH domain annotations. The classifier assigns each gene to a functional category based on those two pieces of information alone:

**Megasynthase:** any protein larger than 800 amino acids that carries a ketosynthase (KS) domain or an NRPS adenylation (AMP-binding) domain. These are the large assembly-line enzymes.

**Embedded AT:** a megasynthase that has both a KS domain AND an acyltransferase (AT) domain in the same protein. This is the hallmark of a cis-AT PKS, where each module provides its own AT domain.

**AT-less megasynthase:** a megasynthase with a KS domain but no embedded AT. This is the hallmark of a trans-AT PKS, where a single standalone AT protein serves all modules.

**Standalone AT:** a small protein (under 600 amino acids) carrying an AT domain but no KS domain. This is the dedicated trans-AT protein that explains why the megasynthases lack embedded AT.

With these classifications in hand, the decision tree runs through 23 rules in priority order — first match wins. The priority order matters because the most distinctive architectures go first:

**PTM (polycyclic tetramate macrolactam) — highest priority.** A single protein between 2,500 and 4,000 amino acids that contains *both* a KS domain and an NRPS adenylation domain. This fused iPKS-NRPS is the diagnostic for HSAF-class antifungals. No other common biosynthetic pathway produces this specific fusion at this size. The rule additionally requires that no more than one other KS gene and one other AMP-binding gene exist in the BGC — the fused protein must be the dominant megasynthase.

**T2PKS (type-II PKS, aromatic polyketides) — rule 2.** Two small KS genes in the 300–550 amino acid range, or two genes with specific T2PKS annotations from antiSMASH, accompanied by a small ACP (under 120 amino acids). The KSα/KSβ (chain-length factor) pair is the minimalist diagnostic for aromatic polyketide biosynthesis: tetracyclines, anthracyclines, angucyclines.

**Trans-AT PKS — rule 3.** Any of: (a) the `tra_KS` domain annotation, which antiSMASH assigns specifically to trans-AT ketosynthases; (b) the FkbH glyceryl-ACP synthase, a trans-AT pathway-specific enzyme; (c) two or more AT-less megasynthases plus a standalone AT gene. If NRPS adenylation domains are also present, the call is TRANS_AT_HYBRID.

**T3PKS (type-III PKS, chalcone/stilbene synthases) — rule 4.** A chalcone/stilbene synthase domain (Chal_sti_synt).

**Lanthipeptide — rule 5.** A LANC-like cyclase or a LanB dehydratase. These two enzymes form the minimal lanthipeptide maturation system.

**LAP/Ranthipeptide — rule 6.** A YcaO cyclodehydratase alone indicates a LAP (linear azol(in)e-containing peptide) or thiopeptide. YcaO combined with an SSF domain indicates a ranthipeptide — the SSF is the substrate-specifying scaffold domain that distinguishes ranthipeptide from the broader YcaO-containing family.

Rules 7 through 18 cover ranthipeptide via radical SAM (alternative to YcaO), lassopeptide, mycofactocin, DUF692 metalloenzyme RiPP, indolocarbazole, NAPAA, ectoine, NI-siderophore, butyrolactone, nucleoside, betalactone, and terpene subtypes (carotenoid, hopanoid, cyclized, linear — but only when no megasynthases are present, since a terpene cyclase in a megasynthase-containing BGC is a tailoring enzyme, not a core signal).

Rules 19–22 handle NRPS-dependent siderophore, hybrid PKS/NRPS, pure NRPS, and cis-AT PKS — these are the broad-category assignments that apply when no more specific rule fired.

Rule 23 is UNKNOWN — the fallback for everything else.

#### Module count estimation

For collinear pathways (trans-AT PKS, cis-AT PKS, NRPS, hybrids), the classifier estimates the number of biosynthetic modules from the total protein mass of the relevant megasynthases:

> PKS modules ≈ total KS-bearing megasynthase mass (amino acids) ÷ 1,500  
> NRPS modules ≈ total AMP-bearing megasynthase mass ÷ 1,100

These divisors reflect typical module sizes: a PKS module (KS + AT + ACP, optionally with KR/DH/ER reductive loop) weighs approximately 1,500 amino acids; an NRPS module (C + A + T, optionally with E for epimerization) weighs approximately 1,100. The module count estimate is a rough prior for the product's expected size and complexity — it is not a precision measurement.

#### Boundary confidence adjustment

When a BGC is Edge or Full-contig, missing genes could change the architecture call. The classifier documents this by downgrading the confidence one tier after the main classification: HIGH → MEDIUM, MEDIUM → LOW. Both the adjusted confidence and the original pre-adjustment confidence are recorded, so the judgment layer can see what the call would have been on a complete cluster.

---

### Step 2: Check the KCB hit for concordance

After the architecture is assessed, the KCB hit is consulted. The concordance check asks: does the compound class implied by the KCB compound name match the compound class assigned by the architecture?

**Coverage threshold.** If fewer than 30% of the query BGC's genes match the reference cluster, the KCB hit is too weak to use for class assignment (WEAK_SIGNAL). Even if the compound name is in the class map, a 20% protein-hit coverage is more likely to reflect shared housekeeping genes at the cluster boundary than genuine class similarity.

**Class lookup.** The KCB compound or MIBiG class tag is looked up in two tables. The `MIBIG_CLASS_MAP` translates structured MIBiG class tags — the formal classification strings that appear in MIBiG entries, such as "Polyketide:Trans-AT type I" or "RiPP:Lanthipeptide" — to architecture classes. The `KCB_COMPOUND_MAP` translates compound names (e.g. "clifednamide," "erythromycin," "staurosporine") to architecture classes for the common case where only a compound name rather than a structured class tag is available. Over 60 compound entries are covered across PTM, trans-AT PKS, cis-AT PKS macrolides, T2PKS aromatics, NRPS peptides, siderophores, indolocarbazoles, terpene misanchors, and nucleosides. When neither table produces a match, the concordance is WEAK_SIGNAL regardless of coverage.

**Concordance verdicts:**

| Verdict | Meaning |
|---|---|
| **CONCORDANT** | Architecture and KCB agree on the compound class |
| **DISCORDANT** | They disagree — architecture wins, KCB is noted as a warning |
| **ARCHITECTURE_DEFERS** | Architecture returned UNKNOWN but KCB coverage is ≥60% — use KCB provisionally at LOW confidence |
| **WEAK_SIGNAL** | KCB coverage under 30%, compound not in class map, or UNKNOWN architecture with insufficient KCB |
| **NO_KCB** | No KnownClusterBlast hit — orphan cluster, architecture only |

Four fuzzy-compatible pairs are treated as concordant even when they don't match exactly: trans-AT hybrid ↔ cis-AT PKS/NRPS hybrid (the KCB database's class mapping may not distinguish these reliably), NRPS-siderophore ↔ pure NRPS (siderophore biosynthesis is a subset of NRPS), thiopeptide ↔ LAP (both use YcaO), and cyclized terpene ↔ hopanoid (both involve terpene cyclization).

---

### Step 3: Make the final assignment

Architecture wins in all cases except ARCHITECTURE_DEFERS. The rule is stated explicitly in the source: "Architecture is primary evidence for product class. When they disagree, architecture wins. Always."

When DISCORDANT, the final product class is taken from the architecture assessment and the Mode B card explicitly states that the KCB compound name is a similarity signal that was overridden. When ARCHITECTURE_DEFERS, the KCB class is used provisionally at LOW confidence and the card states that the architecture could not independently confirm it.

#### Known misanchor patterns

The three most common misanchor patterns in practice:

**T2PKS compound on a terpene BGC.** T2PKS clusters share tailoring enzymes (cyclases, aromatases, cytochrome P450s) with terpene and many other cluster types. Some of those tailoring genes will produce KCB hits against T2PKS reference clusters even when the core terpene machinery (terpene cyclase, no KSα/KSβ pair) is completely different. The architecture classifier sees no small paired KS genes and calls terpene; the T2PKS KCB hit is flagged as a misanchor.

**PTM compound on a collinear trans-AT PKS.** The iterative KS domain in a PTM cluster shares sequence with the ketosynthase domains in trans-AT PKS. A multi-module trans-AT assembly line can produce a KCB hit against an HSAF/clifednamide reference. The architecture classifier sees multiple AT-less megasynthases plus a standalone AT and calls trans-AT PKS; the PTM KCB hit is flagged as a misanchor.

**Macrolide compound on a Full-contig fragment.** A single captured PKS module can match many macrolide KCB references generically because macrolide modules share common domain architecture. The architecture classifier sees one or two megasynthase modules and calls cis-AT PKS with LOW confidence; the macrolide compound name carries no additional confidence because it is a generic match.

---

### The rules registry

Standing rules — permanent exclusions, retired claims, and flags — are maintained in a JSON registry file that is the single source of truth for the pipeline. Each rule has a stable ID, a status (active, retired, excluded, gate), an action (downgrade, drop, flag, exclude), a scope, a rationale, and a set of compiled regex patterns.

The `lint_text()` function scans any text against this registry and returns every match with its rule ID, status, whether it is lead-blocking, and the surrounding context. This is used by the Sapote judgment layer to catch retired claims re-entering verdict prose: if a Mode B card says "this cluster makes NAPAA," the linter catches it. Lead-blocking hits exit with an error code when used in continuous integration.

**False-positive guard.** The `false_positive_guard` field in each rule contains a list of longer words that, if present at the match position, indicate the trigger was a substring false positive. "Saccharide" appearing inside "polysaccharide" should not trigger the saccharide exclusion rule. The guard checks whether any longer-word alternative surrounds the matched span and suppresses the hit if so.

The rules registry is the authoritative source for which classes are permanently excluded (saccharide, fatty acid) and which have been retired (BRYO-HGT-001, the bryophyte horizontal gene transfer hypothesis). Any claim downstream that uses a retired concept is caught by the linter before it can enter a Mode B card or a published figure caption.

---

### Boundary audit

The boundary audit tool verifies that the deterministic extraction layer and the judgment layer are consistent with each other. It diffs the BGCRecord extraction outputs against the TriageRecord judgment outputs and reports seven failure classes:

| Failure | What it means |
|---|---|
| **DROPPED** | A BGC appears in the extraction records but has no judgment verdict — silent omission |
| **ORPHAN** | A verdict names a BGC ID that the extractor never produced — phantom BGC |
| **STRAIN** | The two record sets describe different strains — copy-paste error |
| **TIER** | A verdict's lead tier or claim confidence is outside the known vocabulary |
| **DOWNGRADE** | A standing-rule-flagged or primary-metabolism-flagged BGC retained a corrected rank — the exclusion was recorded but not honored |
| **EXCLUSION** | A BGC whose products trip a lead-blocking excluded rule has a clean lead verdict — the exclusion never fired |
| **RETIRED** | A record carries a retired rule ID |

The DOWNGRADE and EXCLUSION checks are the genuinely new contribution of this tool. The prior count-level completeness check (does the verdict count match the BGC count?) cannot catch a BGC that was silently accepted as a clean lead when it should have been excluded. The boundary audit checks at the individual-BGC-ID level.

---

### Class-architecture capacity calls

A second classification system (`class_architecture.py`) assigns a claim-safe class-capacity label based on PKS/NRPS module counts and the set of tailoring enzymes present. This is distinct from the architecture-first pipeline above: the architecture-first pipeline operates on individual gene domain content from the gene table; the class-architecture layer operates on the aggregate module count and tailoring constellation.

The class-architecture layer fills in compound-class capacity calls for clusters where the CCTT keyword approach (which the text notes covers ~30% of antimicrobial classes) provides no signal but the module-count architecture is diagnostic. A cluster with 7 or more NRPS condensation domains, a halogenase, and a glycosyltransferase has "biosynthetic capacity consistent with a glycopeptide antibiotic" even if none of the specific keyword patterns fired.

Key capacity calls:

- 6+ NRPS condensation domains + halogenase + glycosyltransferase → **glycopeptide** (HIGH confidence)
- 3+ PKS_KS domains + polyene/macrolide product annotation + thioesterase → **polyene macrolide** (HIGH)
- Trans-AT ketosynthase + FkbH glyceryl-ACP synthase → **trans-AT PKS** (HIGH)
- 2+ NRPS condensation domains, no PKS_KS, + siderophore product label → **NRP-metallophore** (HIGH)

When 3 or more distinct real biosynthetic product classes are present (excluding the uninformative catch-alls saccharide, other, and terpene-precursor), the capacity is labelled "complex hybrid locus; class-capacity unresolvable by single label" at MEDIUM confidence — the architecture is too mixed to assign a single class label without misrepresenting the complexity.

---

### KCB similarity precision (W26)

KCB cumulative scores — the sum of bitscore-weighted gene matches to a reference cluster — are reported as coarse bands, not raw numbers. The bands: high (≥70 on the normalized scale), moderate (40–70), low (0–40). For percent identity values, rounding is to the nearest 5%. For bitscores, rounding is to the nearest integer.

This precision constraint (W26 in the pipeline's internal issues log) exists because a KCB score of 62,450 implies a level of certainty the underlying measurement does not support. The bands carry the appropriate epistemic weight: "this cluster has high similarity to the reference compound's cluster" rather than "62,450 bitscore units of similarity."

---


---

# The Mathematics of Sapote–Mamey, Volume II

## Cluster C: KCB / RiQ Extraction and Gene-Level Correspondence

**Mamey engine v1.9.110 · bundle v9.7.319**  
****

This cluster covers how Mamey extracts similarity data, recognition quotient (RiQ) scores, and gene-level correspondence from antiSMASH's BLAST output — and two specific problems that had to be solved to make that extraction reliable.

antiSMASH emits similarity data from three databases: **ClusterBlast** (cross-genome hits against other sequenced organisms' BGCs), **KnownClusterBlast** (hits against characterized MIBiG reference clusters), and **SubClusterBlast** (sub-operon hits, excluded from most uses). KnownClusterBlast is what most people think of as the KCB hit — the named-compound similarity — but cross-genome ClusterBlast is equally important and is the primary evidence source for RG-GMCI split-cluster rescue.

KCB = similarity, not identity throughout. Every number extracted here is a BLAST similarity score against a reference. Nothing in this cluster constitutes evidence of production or compound identity.

---

### What the extraction layer reads

antiSMASH produces two sources of KCB evidence: a set of plain-text files in a `knownclusterblast/` directory (one per region, listing the top reference hits with gene-level matches), and a JSON file for the whole run that contains RiQ scores, substrate predictions, TIGRFAM hits, and additional evidence.

The text files are the primary source for KCB similarity data. They are small, reliably structured, and available for every run regardless of how antiSMASH was configured. The JSON file contains richer data but can be very large for actinomycete genomes — 50–130 MB is typical — and requires careful handling to avoid memory problems.

---

### Memory-adaptive JSON handling

Loading a 100 MB JSON file with `json.loads()` typically produces a peak memory usage of around 1 GB. For a large cohort of actinomycete genomes processed in sequence, this would be prohibitive. The pipeline avoids this through streaming JSON parsing: rather than loading the entire document into memory, it processes records one at a time as the parser encounters them.

The decision to stream is made automatically based on file size. Files smaller than 20 MB are loaded directly (fast, no streaming overhead); files 20 MB or larger use the streaming path. The 20 MB threshold cleanly separates real genome JSONs from test fixtures. The streaming parser uses the ijson library; if ijson is unavailable, the system falls back gracefully to the direct-load path (with stricter size limits) or to text-file-only mode.

Three JSON evidence modes exist:

- **bounded** (default): stream the JSON; extract KCB, RiQ, substrate predictions, TIGRFAM hits, and RiPP core sequences. This is the recommended mode for all normal runs.
- **off**: ignore the JSON entirely, use only the text KCB files. Always safe, but loses RiQ scores and TIGRFAM diagnostics.
- **full**: legacy mode that loads the entire JSON at once. Refuses files larger than 20 MB.

All JSON extractions for a given run share a single pass through the file. Rather than opening the JSON four times for four different types of evidence, all four extractors run simultaneously as the streaming parser processes each record. A failure in one extractor (due to an unexpected JSON structure) does not abort the others.

---

### Text-file KCB extraction: what it resolves

The text file for each region lists, for each reference cluster in the top results, the reference cluster's name and accession, a list of query genes that matched reference genes, and for each match: the query gene, the reference gene, the percent identity, the BLAST score, the percent coverage, and the e-value.

From this Mamey extracts two key quantities per BGC:

**KCB cumulative score:** the sum of BLAST scores for all gene matches to the best-matching reference cluster. This is a single number representing the overall strength of the similarity.

**KCB protein hits:** the number of distinct query genes that had any match to the best reference cluster. This is often more interpretable than the cumulative score — 8 out of 12 genes matching means something different from 2 out of 12.

The pipeline also resolves the specific MIBiG accession and compound name when they are present (see the "genome self-hit problem" below). The fields `closest_mibig_accession`, `closest_candidate_kcb_product`, and `closest_product_provenance` carry the provenance trail for this resolution.

#### The genome self-hit problem

The KCB database contains two types of entries: curated MIBiG reference clusters (characterized compounds with known structures and bioactivities) and genome-derived clusters (sequences from various organisms deposited in the database). In practice, the top KnownClusterBlast hit for most BGCs is a genome-derived entry from a related organism that happens to contain many similar clusters — the reference organism's genome dominates because genome sequences are far more numerous than MIBiG entries.

The result is that the raw rank-1 KCB line is biologically uninformative for most BGCs: it says "this query BGC resembles some region of organism X's genome" rather than "this query BGC resembles compound Y's characterized cluster." Only about 2% of BGCs have a MIBiG entry as their rank-1 hit; about 59% have a MIBiG entry somewhere in the top results.

The pipeline corrects for this by searching all KCB results for a hit whose identifier matches the MIBiG accession pattern (BGC followed by seven digits). When found, that MIBiG hit is surfaced as `kcb_top`, and the displaced rank-1 genome hit is preserved in `clusterblast_top`. The downstream scoring and architecture systems then see the biologically meaningful compound name rather than a genome description.

---

### RiQ: the recognition quotient

The RiQ (Region-to-region Quotient) is antiSMASH's own measure of how well a detected region matches the expected architecture for its assigned product class. It is a 0–1 ratio derived from antiSMASH's region-to-region comparison module. Regions that match expected architectures closely score near 1.0; unusual regions with mismatched architecture score near 0.

The pipeline extracts RiQ from the JSON file and maps it to the BGC it belongs to. The extraction preserves the *best* (maximum) RiQ value across any ambiguous region-to-region mappings. RiQ scores are capped to the 0–1 range — values that appear outside this range in the JSON (coordinate data, similarity matrices) are excluded.

**RiQ label thresholds:**

| Score | Label |
|---|---|
| ≥ 0.85 | Likely known |
| 0.50–0.85 | Possibly novel / structural variant |
| < 0.50 | Potentially novel |

These thresholds are used to generate a display label and feed the novelty score adjustment (+10 points when RiQ < 0.5). They are capacity-level signals for triage, not manuscript claims.

---

### TIGRFAM diagnostics: what was missing before the fix

TIGRFAM hits are stored in the antiSMASH JSON file under `records[].modules["antismash.detection.tigrfam"].hits[]`. They are *not* included in the GenBank `sec_met_domain` qualifiers that the text-file extraction path reads. Before this was discovered and fixed (the "tigrfix" at v9.4.1), TIGRFAM diagnostics were silently dropped.

This mattered because several important diagnostic markers exist only as TIGRFAM entries, not as Pfam domains:

| TIGRFAM | What it marks |
|---|---|
| TIGR03828 | ene_KS — the enediyne warhead ketosynthase |
| TIGR04186 | NikJ-family enzyme — nikkomycin/polyoxin nucleoside biosynthesis |
| TIGR01454 | AHBA synthase — ansamycin/rifamycin biosynthesis |
| TIGR03604 | TOMM/thiopeptide cyclodehydratase |
| TIGR04363/4 | FxLD class-I lanthipeptide markers |
| TIGR04462/0 | Enduracididine-type NRPS markers |
| TIGR03550/1/3620 | F420-embedded polyketide markers |
| TIGR01181 | Glycosylated T2PKS marker |

Of these, ene_KS (TIGR03828) and NikJ (TIGR04186) are particularly important: they are the diagnostic genes for enediyne and nucleoside detection respectively, and their absence caused false-negative calls before the fix.

One TIGRFAM (TIGR02353, the ε-poly-L-lysine synthetase for NAPAA biosynthesis) is present in the diagnostic set but is explicitly *not* a Tier-1 diagnostic marker. It is present for combination detection (§8 diagnostic combinations in the Sapote judgment layer) only and is not weighted as a class-defining signal.

---

### Data-driven RiPP extraction

Earlier versions of the pipeline extracted RiPP core sequences from a hardcoded list of four RiPP families: lanthipeptides, lassopeptides, sactipeptides, and thiopeptides. antiSMASH 7+ annotates many more RiPP families — ranthipeptides, thioamitides, lipolanthines, microviridins, cyanobactins, and others. The hardcoded list silently dropped them all.

The v9.7.99 fix made this extraction data-driven: rather than checking for specific module names, the extractor iterates all `antismash.modules.*` keys in the JSON and extracts data from any module that carries a `motifs` dict with a `core` key. Non-RiPP modules (NRPS/PKS, active-site finder) naturally don't have this structure and are excluded automatically. Any future RiPP family that antiSMASH adds will be captured without any changes to the pipeline.

---

### Sec_met_domain Pfam hits

In parallel with the JSON-based extraction, antiSMASH writes its HMMER domain results into `sec_met_domain` qualifiers in every region GenBank file. These qualifiers contain the domain name, E-value, and bitscore for each HMMER hit. The pipeline reads these separately and uses them to populate domain-level data for the architecture assessment.

The extraction uses a regex that handles both the standard format (domain, E-value, bitscore) and older antiSMASH versions that omit the bitscore. Domain names are looked up against a curated dictionary of 34 biosynthetically important domains to attach human-readable descriptions and Pfam accessions. Unknown domains are still recorded without annotation rather than dropped.

---

### Per-gene ClusterBlast and KnownClusterBlast correspondence

The standard KCB extraction retains only the cumulative score and protein-hit count for the best-matching reference cluster. A complementary layer extracts the full per-gene correspondence from both ClusterBlast and KnownClusterBlast result files: for each query CDS, which reference gene did it best match, at what percent identity, coverage, and BLAST score?

This finer-grained data is used for two purposes:

**Functional role profiling for split-cluster rescue.** When two BGC fragments are candidates for being halves of the same cluster, the per-gene correspondence allows a complementarity assessment: does one fragment carry the biosynthetic core genes while the other carries the tailoring arm? A fragment where 60% of genes are core biosynthetic and a fragment where 60% are tailoring/transport are functionally complementary; two fragments that are both 50% core are more likely to be paralogs. This complementarity score feeds the RG-GMCI rescue confidence ranking.

**Reference correspondence tables.** The per-gene data is packaged into the sealed output so the judgment layer can perform gene-level Mode B analysis without re-opening the antiSMASH files.

#### Complementarity thresholds

The core fraction — core gene count divided by (core + tailoring + transport + regulatory) — is the key metric:

- Gap of 0.20 or more between the two fragments' core fractions, with the lower fragment at ≤ 0.30: **COMPLEMENTARY** — one fragment is core-dominant and the other is accessory-dominant
- Both fragments at ≥ 0.35 core fraction and gap < 0.20: **BOTH_CORE** — likely paralogous clusters, not a split
- Both fragments at ≤ 0.30 core fraction: **ACCESSORY_ONLY** — two tailoring-arm fragments, weak rescue evidence
- Everything else: **AMBIGUOUS**

These thresholds were calibrated against known genuine splits and known paralogs in the AS-XXX cohort. They are engineering calibration values, not literature-derived constants.

---

### Product-class prediction by coordinate

The T2PKS and terpene product class predictions from the JSON include start and end coordinates for each prediction. These coordinates are used to match each prediction to the specific BGC it falls within, rather than assigning it to all BGCs on the same contig.

This distinction matters for closed circular chromosomes, where the contig key is a single identifier that would otherwise collapse all predictions for the entire chromosome into one bucket. Without coordinate-based matching, every BGC on a closed chromosome would receive every prediction from that chromosome, inflating compound class annotations across all BGCs.

---


---

# The Mathematics of Sapote–Mamey, Volume II

## Cluster D: Compound-Class Annotation, Domain-Level Enrichment, and DKP/CDPS Detection

**Mamey engine v1.9.110 · bundle v9.7.319**  
****

Three modules in this cluster add structured annotation to BGCs at different stages of processing. None of them are scoring engines — one carries a small scored consequence for three specific chemotypes, but the rest are annotation layers that record evidence without changing scores. The distinction between annotation and scoring matters: annotation layers can be reviewed and overridden by the judgment layer; scoring changes affect triage ordering in a way that the judgment layer cannot easily undo.

---

### What each module does and when it runs

**compound_class.py** runs during extraction, on the BGC's own evidence. It records the chemotype the cluster appears to belong to — polyene macrolide, anthracycline, ionophore, tetracycline, and so on — as structured fields on the BGC record. For three well-calibrated chemotypes, it also carries a small score adjustment that is applied before triage.

**domain_level.py** runs after extraction is sealed, on the top-N BGCs by AB+AF score. It produces claim ceilings and complexity metrics derived from the domain-level structure of each BGC's genes. It is the only module in this cluster that writes standalone deliverable files.

**dkp_cdps.py** runs as part of the source-scan pass, inside `run_source_scans()`. It detects diketopiperazine (DKP) scaffold BGCs, grades them by chemical context, and sets explicit claim ceilings.

---

### Compound-class annotation

#### Evidence priority

The chemotype annotation uses three levels of evidence in descending priority:

1. **Specific resolved product name** — the `closest_candidate_kcb_product` field (the MIBiG compound name resolved from KCB results) combined with the BGC's own antiSMASH product class. The raw `kcb_top` field is *never* used here — it often contains genome self-hit descriptions that would pollute the annotation with unrelated compound names.

2. **antiSMASH T2PKS product class prediction** — a machinery-based class prediction extracted from the JSON. Used when the product name didn't resolve to a recognized chemotype.

3. **Product class only** — a coarse fallback when neither of the above produces a result.

#### The three scored chemotypes

Most chemotype annotations are annotation-only — they record the label and evidence trail without affecting AB/AF scores. This is the appropriate treatment for chemotypes where the evidence trail is present but the scoring consequence is not yet calibrated against a reference set. Three chemotypes carry a scored consequence because they are well-calibrated against MIBiG reference clusters and the relationship between gene content and bioactivity target is well-established:

**Polyene macrolides** (e.g. nystatin, amphotericin, candicidin) add weight to the AF (antifungal) axis. Polyene macrolides are a primary antifungal class with a well-characterized mechanism of action (ergosterol binding), and the polyene-specific gene content is distinctive enough that the annotation is reliable.

**Ionophore polyethers** (e.g. monensin, salinomycin) add weight to the AB (antibacterial) axis. Ionophores have antibacterial activity that does not appear in the generic PKS/NRPS keyword weights.

**Anthracyclines** (e.g. daunorubicin, doxorubicin) are flagged as a routing category rather than an AB or AF score adjustment. Anthracyclines are potent cytotoxics with clinical relevance but do not fit neatly into the antibacterial or antifungal routing prior framework.

All other annotated chemotypes — tetracyclines, angucyclines, phenazines, indolocarbazoles, and others — are annotation-only.

---

### Domain-level enrichment

The domain-level module provides a structured gene-by-gene view of a BGC's internal organization. This enrichment runs post-seal on the top-N BGCs (default 10) and produces several complementary analyses.

#### Gene role profiling

Each gene is assigned to one of five functional roles:
- **core** — carries biosynthetic core domains (PKS ketosynthases, NRPS adenylation/condensation, cyclases, etc.)
- **tailoring** — modifies the scaffold after assembly (oxidases, glycosyltransferases, halogenases, methyltransferases)
- **transport** — efflux pumps and ABC transporters
- **regulatory** — transcription factors and other gene expression regulators
- **other** — everything else

The role profile tells you the relative weight of each functional category in the cluster. A cluster with 6 core genes, 4 tailoring genes, 1 transporter, and 1 regulatory gene has a different character from one with 1 core gene and 11 tailoring genes (which might indicate a split cluster where the core is missing).

#### Complexity metrics

The module counts the total number of domain-bearing genes in each role category. These are raw counts, not normalized fractions — a cluster with 20 core domains and 2 tailoring domains has a different profile from one with 2 core domains and 20 tailoring domains, and both values are reported so the judgment layer can assess their relative significance.

#### Architecture archetype assignment

BGCs are assigned to architecture archetypes (e.g. "large modular PKS," "standalone NRPS dipeptide," "RiPP precursor + maturation") based on which role combinations are present. The archetype templates are stored in an external JSON file rather than hardcoded, so the vocabulary can be updated without source changes. The classifier matches the set of roles present against each template's required and forbidden role sets; the first fully-satisfied template wins.

#### Claim-safety verdicts

A claim-safety verdict is derived from the roles present, matched against a versioned rule set. Each matched rule returns three strings: the safe claim ("biosynthetic capacity consistent with a 4-module NRPS peptide"), the unsafe claim that should *not* be made ("produces compound X"), and the claim ceiling ("class-level capacity only"). These strings are written to the `Domain_claim_ceiling` deliverable column and feed the Mode B §2 claim-safety review section.

---

### DKP/CDPS detection and grading

Cyclodipeptide synthases (CDPS) produce diketopiperazine (DKP) scaffold compounds — cyclic dipeptides that can undergo further oxidation by cyclodipeptide oxidases (CDOs) to produce more structurally complex derivatives. The CDPS/DKP class is significant because DKP scaffolds appear across a range of bioactive natural products, from simple cyclic dipeptides to complex indolyl diketopiperazines.

#### Trigger conditions

A BGC enters the DKP scanner when at least one of the following is present: antiSMASH annotated it directly as "CDPS" or "cyclodipeptide," a CDS within 10 kb matches CDPS-associated annotation terms (cyclodipeptide synthase, diketopiperazine synthase, Pfam PF16715), or a domain hit within 10 kb matches those terms.

#### Grade assignment

Three grades reflect increasing chemical specificity:

**DKP-A (dehydrogenated DKP):** a CDO (cyclodipeptide oxidase) or AlbA-like oxidase is present nearby. This indicates the DKP scaffold undergoes post-synthesis oxidation, producing a more structurally complex derivative — an indolyl diketopiperazine, a brevianamide-type compound, or similar. This is the most actionable lead type. Confidence is HIGH for Interior clusters, MEDIUM for Edge.

**DKP-C (boundary uncertain):** no CDO is detected AND the cluster is Edge or Full-contig. The missing CDO could be present on an adjacent contig that wasn't captured. No structural prediction can be made, but the DKP core is present.

**DKP-B (bare or saturated CDP):** no CDO and not at a boundary. The simplest DKP scaffold — a cyclic dipeptide without post-synthesis oxidation. Confidence is MEDIUM when both a gene-level and a domain-level CDPS hit are present, LOW when only a domain hit exists.

#### Claim ceilings

Both claim-ceiling strings are set unconditionally regardless of grade:
- "candidate DKP-scaffold BGC; specific dipeptide/product requires isolation"
- "same-family-not-same-product; do not assert purincyclamide/albonoursin without chemistry"

The second string names two specific compounds (purincyclamide and albonoursin) as examples of claims that must not be made without chemistry. These are the most common over-interpretations of CDPS/CDO-containing BGCs in the literature.

#### Gene classification for confidence

When per-gene KCB correspondence data is available, each KCB hit gene is classified before it can influence DKP confidence:

- **Self-hit** (≥99% identity AND ≥98% coverage to the query itself): excluded from confidence assessment
- **Biosynthetic-diagnostic**: carries CDPS or CDO terms → strengthens confidence
- **Biosynthetic-tailoring**: carries general tailoring enzyme terms → noted
- **Housekeeping/conserved**: clearly a housekeeping gene → does not strengthen confidence
- **Unclassified**: neither clearly biosynthetic nor clearly housekeeping

The self-hit threshold (≥99%/≥98%) is the operational definition of "this query gene is essentially identical to the reference gene." A gene annotated as "putative cyclodipeptide synthase" at these thresholds is still not classified as a self-hit — the "putative" qualification introduces uncertainty about the annotation.

The three modules in this cluster — compound-class annotation, domain-level enrichment, and DKP/CDPS detection — divide by timing and scope rather than by importance. Chemotype annotation happens at extraction time so the BGC record carries the structured label from the start. Domain-level enrichment runs post-seal on the top-N leads so it doesn't add overhead to every BGC. DKP/CDPS detection runs inside the source-scan pass because its grade and claim-ceiling feed the CCTT routing decisions. None of the three modules can create a lead or bury one — that is the scoring engine's job. They annotate; the scoring engine routes; the judgment layer decides.

---


---

# The Mathematics of Sapote–Mamey, Volume II

## Cluster E: Rescue, Concordance, Fragment Ceiling, and Comparative Pairs

**Mamey engine v1.9.110 · bundle v9.7.319**  
****

Four modules in this cluster operate after the main scoring pass. Three of them — diagnostic rescue, concordance checking, and comparative pair building — are purely advisory: they generate evidence the Sapote judgment layer reasons over without changing any triage score. One — the fragment ceiling — does mutate BGC records, but only downward: it enforces a size-based claim ceiling that prevents product-level over-calls on fragments too small to encode the named compound's backbone.

---

### Diagnostic rescue: class-aware split-pathway detection

#### The problem it solves

RG-GMCI (described in Volume I §7) detects split clusters by shared-reference geometry: do two BGC fragments hit the same reference cluster from antiSMASH's ClusterBlast or KnownClusterBlast databases, and do they hit complementary parts of it? RG-GMCI reads both cross-genome ClusterBlast data (hits against other sequenced genomes) and KnownClusterBlast (hits against characterized MIBiG entries). Cross-genome ClusterBlast is the primary signal — a complete reference genome can tile both arms of a split. This geometry check works well when both fragments share a rich enough hit to compute the geometric relationship.

But a specific failure mode eluded the geometry check: a split pathway where one fragment carries the core biosynthetic genes (the class-defining anchor) and the other carries a tailoring arm (a halogenase, a glycosylation cassette). These two fragments are by definition functionally complementary, but they often don't share enough overlapping KCB reference genes for the geometry score to reach HIGH.

The motivating case was a *Streptomyces* indolocarbazole cluster split between two contigs — BGC013 carrying the T43-IDC core (StaD/RebC synthase) and BGC001 carrying a halogenase and saccharide arm. The two fragments tiled the same reference cluster at complementary positions with zero gene overlap, but RG-GMCI gave the pair a LOW score because the geometry thresholds weren't satisfied.

Diagnostic rescue addresses this by using the CCTT trigger system to identify the class of each fragment, independently of reference geometry. A fragment carrying T43-IDC is a core fragment; a fragment carrying T43-HAL is an arm fragment. The pair is a high-confidence split candidate when: both are Edge or Full-contig (Interior clusters don't split), they tile a shared reference complementarily, and the arm trigger is a genuine diagnostic (a halogenase or glycosylation arm). This is a separate scoring path from RG-GMCI — the two systems are complementary, not redundant.

#### Architecture: core and arm triggers

The split pathway has an asymmetry: one fragment carries the class-defining biosynthetic machinery and the other carries modification enzymes.

**Core triggers:** all 13 class-defining CCTT triggers (T43-IDC, T43-PTM, T43-NUC, T43-BLA, T43-AMC, T43-NN, T43-ENE, T43-LAN, T43-LASSO, T43-THA, T43-DKP, T43-TET, T43-PHO). A fragment with one of these triggers is the core.

**Arm triggers:** T43-HAL and T43-XHAL (halogenases). A fragment with only halogenase or extended halogenase triggers and no core trigger is an arm candidate. Saccharide and glycosyl product tokens also flag arm fragments, but these carry lower weight — a bare saccharide annotation without a halogenase trigger does not alone drive a HIGH rescue.

#### The edge gate

Only truncated fragments (Edge or Full-contig) can be halves of a split pathway. This gate is validated by observation: when applied to public GOOD-assembly genomes where nearly all clusters are Interior, requiring edge status on both fragments eliminates false HIGH leads. An Interior cluster is complete by definition — two Interior clusters sharing vocabulary are co-occurring related clusters, not split pathway arms.

#### Precision floors

The tiling quality must meet minimum standards to reach HIGH confidence:
- Total reference genes covered by both fragments combined: at least 8
- Each fragment individually: at least 2 reference genes

These values were calibrated on the motivating indolocarbazole case (8 reference genes, 0 overlap between the two fragments). They apply when per-gene tiling data is available; when only the coarser scaffold-level RG-GMCI data exists, the floors are not enforced.

#### Tiling verdicts

The geometric relationship between the two fragments' reference gene sets is classified into four categories:

- **RECONSTRUCTION_SUPPORTED_COMPLEMENTARY:** overlap fraction ≤15% AND the two fragments' reference gene ranges are adjacent (within a 60-gene gap on the reference). This is the canonical genuine split pattern.
- **RECONSTRUCTION_NOT_SUPPORTED_DISTANT_LOCI:** overlap fraction ≤15% but the fragments are far apart on the reference. Complementary but not adjacent — may be a split but distance reduces confidence.
- **RECONSTRUCTION_WEAK_PARTIAL_OVERLAP:** overlap fraction 16–50%. Partial sharing; ambiguous between split and paralog.
- **RECONSTRUCTION_NOT_SUPPORTED_HIGH_REFERENCE_OVERLAP:** overlap fraction >50%. The two fragments cover the same reference genes — this is two paralogs, not a split.

#### Competing hypotheses

When a BGC fragment scores HIGH against more than one partner, the additional leads are labelled as competing hypotheses rather than independent discoveries. A BGC fragment can have at most one true complement in a split cluster; multiple HIGH rescue leads sharing a fragment are mutually exclusive alternatives that the judgment layer must evaluate. The flag `mutually_exclusive_best=True` marks the case where neither the core BGC nor the arm BGC appears in any other HIGH lead — this pair is the only candidate for both fragments.

#### The claim ceiling

Every diagnostic rescue lead carries an unconditional claim ceiling:
> "Clusterblast-scaffolded reconstruction hypothesis: a homology-guided split-pathway linkage, NOT a nucleotide-level contig join and NOT a product-identity claim. Confirm physical linkage by long-read resequencing or PCR across the contig boundary."

This is non-negotiable and appears on every rescue lead regardless of confidence tier.

---

### Concordance checking

The concordance check asks whether the expected biosynthetic markers for a KCB reference compound are actually present in the queried BGC's gene content. It is advisory only — it generates a verdict that the judgment layer reads, but changes no scores.

Five verdicts are possible:

| Verdict | Meaning |
|---|---|
| **CONCORDANT** | At least 50% of expected markers present AND cluster size within 0.5× to 2.0× reference size |
| **PARTIAL** | Some expected markers present but fewer than 50% |
| **DISCORDANT** | KCB anchor matches but zero expected markers present — strong misanchor warning |
| **NO_REFERENCE** | KCB anchor doesn't match any entry in the concordance library |
| **EXPECTED_PENDING_LIT** | Library entry exists but reference markers haven't been populated yet |

The size check is permissive: the concordance verdict is based primarily on marker presence, and size is only used to add a note when extreme (smaller than 0.3× or larger than 3× the reference) — well outside the 0.5–2.0× range used for the size_ok flag.

The PENDING_LIT state is important: it explicitly distinguishes "this compound is not in our library" (NO_REFERENCE) from "this compound is in our library but we haven't yet filled in the expected markers" (EXPECTED_PENDING_LIT). An analyst seeing PENDING_LIT knows the library has this compound and can check back as the library grows.

The concordance check always reads the `closest_candidate_kcb_product` field (the MIBiG compound name) rather than the raw `kcb_top` field. For clusters from sequenced reference genomes, `kcb_top` can be a genome self-hit; `closest_candidate_kcb_product` is always the MIBiG compound line.

---

### Fragment ceiling: backbone-size claim floor

When a named large-backbone compound appears as the KCB hit for a small fragment, the fragment physically cannot encode that compound's biosynthetic machinery. A 30 kb fragment carrying a vancomycin KCB hit cannot be making vancomycin — the vancomycin biosynthetic cluster is over 100 kb. Claiming "vancomycin-like capacity" for a 30 kb fragment is therefore an over-claim that goes beyond what the gene content can support.

The fragment ceiling enforces a claim-ceiling: any Edge or Full-contig fragment smaller than 45 kb whose KCB hit names a large-backbone compound has its `product_claim_ceiling` field downgraded to "class-capacity only (fragment too small for named backbone; do not use product name)."

The ceiling check runs through two paths:

**Path 1 (preferred):** the MIBiG reference cluster's actual size is looked up in the MIBiG reference index. If the reference is ≥45 kb and the fragment is <45 kb, the ceiling applies. This path is self-maintaining — as MIBiG adds new entries with measured sizes, the ceiling automatically extends to them without keyword updates.

**Path 2 (fallback):** if the reference size isn't in the index, the compound name is checked against a curated keyword list of 28 large-backbone families in three groups — glycopeptides (teicoplanin, vancomycin, balhimycin, and relatives), lipo/Ca-dependent lipopeptides (enduracidin, ramoplanin, daptomycin, friulimicin, and others), and large polyene/modular PKS macrolides (nystatin, amphotericin, rapamycin, avermectin, stambomycin, and others).

Interior clusters are never affected. Lanthipeptides, lassopeptides, and other inherently small-compound classes are never affected — the ceiling applies specifically to large modular-backbone compound families.

When the ceiling trips, the named MIBiG accession and compound name are preserved for the provenance trail. Only the claim ceiling is downgraded; the similarity evidence is not lost.

---

### Comparative pairs: cross-strain BGC similarity

The comparative pairs module populates the E2_Comparative_Pairs sheet in the master workbook, providing a cross-strain BGC similarity layer. This was declared in the schema but had no populator until v9.7.88.

Three signals contribute to the similarity assessment:

**Shared product classes:** antiSMASH product class tokens shared between two BGCs from different strains. This is the pre-filter — a pair with no shared product classes is excluded immediately.

**Shared A-domain count:** the number of adenylation/PKS-carrier domain names shared between the two BGCs' domain signatures. For NRPS and PKS clusters, this is a concrete measure of how many module-level functional elements they have in common, independent of sequence identity.

**KCB anchor overlap:** whether the two BGCs have identical `kcb_top` strings. This is an exact string match, deliberately conservative — two BGCs whose KCB hits differ by even one character will not match. This prevents partial-string false-positive matches while still flagging exact shared references.

`mean_pct_id_core` and `mean_pct_id_all` fields are explicitly set to "not_computed" — not blank, not zero. The "not_computed" value tells a consumer that no sequence alignment was run, which is qualitatively different from "the alignment ran and returned 0%."

The comparison is cross-strain only; same-strain BGC pairs belong to the RG-GMCI engine. The E2_Comparative_Pairs sheet that this module populates was declared in the master workbook schema but had no populator until v9.7.88 — it exists specifically to answer the cross-strain question "does this strain carry a BGC that resembles one we have seen before?"

---


---

# The Mathematics of Sapote–Mamey, Volume II

## Cluster F: Singleton Filter, §3 Census, Enrichment Sections, and Nominal Length

**Mamey engine v1.9.110 · bundle v9.7.319**  
****

This cluster covers the Mode B enrichment stack — the set of deterministic generators that ensure every Mode B card reaches a minimum analytical depth from data rather than padding. None of these modules change triage scores or BGC rankings. They generate the structured content for the §11–§20 block of a Mode B card: domain inventories, rarity rankings, substrate typing, and size comparisons. A Mode B card without this content is a thinner document; the quality gate (documented in the Plumbing Reference) treats it as SHALLOW.

---

### Why a minimum enrichment floor exists

The Mode B quality gate (documented in the Plumbing Reference) requires a minimum of 1,000 characters of §11–§20 enrichment content before a card can reach FULL quality status. This floor exists because enrichment sections are the most commonly skipped part of Mode B analysis — it is easy to write a competent §1–§8 assessment and then produce only a token §11 block.

The enrichment modules guarantee that the 1,000-character floor is always reachable from data. Three sections are "universal catch-alls" that always produce content for any cluster with at least one domain-bearing gene: the rarest-genes section, the rarest-domains section, and the generic domain inventory. Even the most gene-sparse BGC with a single domain hit will produce enough enrichment content from these three sections to meet the floor. The judgment layer cannot claim a card is complete if these sections are absent.

---

### The singleton filter: separating biosynthetic novelty from housekeeping noise

#### The problem

The rarity ranking in the enrichment sections uses genome-wide domain frequency to identify "singleton" domains — domains that appear in only one gene across the entire genome. A genome-unique singleton domain is a novelty signal: if a domain appears only once in this genome, it is less likely to be a ubiquitous housekeeping function and more likely to be a specialized biosynthetic enzyme.

The problem is that fragmented assemblies produce many genomic singletons that are not biosynthetically novel. A ribosomal protein stranded on a short contig is genome-unique only because assembly fragmentation isolated it; it is still a common ribosomal protein. Without filtering, the "rarest genes" section would be dominated by ribosomal proteins, DNA polymerase subunits, and glycogen pathway enzymes — all of which appear once in this genome because of assembly artifacts, not biosynthetic specialization.

Concrete cases that motivated the fix: one BGC had 10 raw singleton genes, 4 of which were ribosomal proteins or elongation factor G. Another had 7 raw singletons all from the glycogen/α-glucan pathway (a primary-metabolism DROP, not a lead). A third had 11 raw singletons mostly from regulatory and MEP-isoprenoid biosynthesis. Without filtering, the glycogen-pathway BGC (11 apparent singletons) ranked above a genuine RiPP cluster (7 singletons, nearly all maturation machinery) because it had more raw singleton genes.

#### The three-tier matching system

The singleton filter classifies each domain as housekeeping-or-not using three progressively stricter matching tiers. This tiering was introduced in v9.7.118 to fix the prior bare-substring matching, which was incorrectly suppressing biosynthetically meaningful domains that happened to contain common substrings.

**PREFIX matching** (stems ≥5 characters or clearly unambiguous): the stem must appear as a delimited token prefix — at a word start, or after an underscore or hyphen. "Ribosom" matches "Ribosomal_S7" and "Ribosom_S12" but not a hypothetical "AutoribosomX" domain. This tier handles the large family of clearly-named housekeeping domains.

**EXACT matching** (specific short identifiers): the stem must appear as a complete delimited token — bounded on both sides. "EFG" matches "EFG" or "X_EFG_Y" but not "EFGH_domain." This tier handles specific gene identifiers (EF-Tu, EF-Ts) that need exact-token matching rather than prefix matching.

**WHOLE matching** (short ambiguous strings): the stem must be the entire domain name — exact equality. "S1" only matches a domain named exactly "S1," not "Peptidase_S1" or "Trans_AT_S1." This tier handles the most ambiguous short terms.

The fix confirmed six biosynthetically meaningful domains that the old bare-substring matching was incorrectly dropping: `Trans_AT_S1` (trans-AT specificity marker), `PKS_Docking_S1` (PKS module docking domain), `Peptidase_S1` (serine protease in lanthipeptide maturation), `NADHpyr_redox` (biosynthetic redox enzyme), `GtrA_like` (glycosyltransferase), and `ABC1_kinase` (biosynthetically active kinase). All six are now retained.

#### Biosynthetic override allowlist

Seven domain families are explicitly protected from the housekeeping blocklist — they look housekeeping by name but are biosynthetically meaningful in a BGC context:

| Domain | Why it's protected |
|---|---|
| RHS | Contact-dependent toxins — ecological weapons, found in BGC contexts |
| Ntox30 | RHS-associated toxin domain |
| Hemerythrin | Non-heme di-iron tailoring enzyme in natural product modification |
| Spermine_synth | Polyamine incorporation into RiPP scaffolds |
| Peptidase_M23 | Cell-wall enzyme found inside antifungal BGCs |
| LysM | Cell-wall binding domain inside antifungal BGCs |
| Transglycosylas | Transglycosylase inside antifungal BGCs |

The override check runs *before* the housekeeping blocklist. A domain in this list can never be filtered out, even if a blocklist stem would otherwise match it.

#### Decision order

For each domain in the cluster:
1. If in the biosynthetic override allowlist → **KEEP** (unconditional)
2. If in the housekeeping blocklist (any tier) → **DROP** (the Pfam identity overrides the antiSMASH biosynthetic annotation)
3. If antiSMASH annotated it as "biosynthetic (rule-based-clusters)," "biosynthetic-additional," or "biosynthetic (core)" → **KEEP** (protects Pfam-ambiguous tailoring enzymes)
4. If antiSMASH annotated it as "regulatory" or "transport" without any biosynthetic tag → **DROP**
5. Otherwise → **KEEP** (conservative default — unknown domains may be novel)

The inversion at step 2 — housekeeping takes priority over the antiSMASH biosynthetic tag — is intentional. A glycogen synthase inside a saccharide cluster is annotated as "biosynthetic (saccharide)" by antiSMASH; the biosynthetic tag is correct in the literal sense but the gene is still primary metabolism. The Pfam identity (glycogen synthase family) is more reliable than the cluster-level annotation for distinguishing primary from secondary metabolism.

---

### The §3 census generator

The §3 Biosynthetic Core section of a Mode B card provides a systematic count of every catalytic domain type in the cluster. Rather than describing gene content ad hoc, the census names every domain family, counts its occurrences, and assigns each to a functional role — the same core/tailoring/transport/regulatory taxonomy used by the domain-level enrichment module.

The census scales to cluster size. For small clusters (12 or fewer genes), every gene is listed individually with its domain content. For larger clusters, the census reports total domain counts by role category and lists the most prevalent domain families.

Domain names in the output are capped at six per gene in the prose display, with a "…" truncation indicator when there are more. This is a display cap only — all domains contribute to role assignment regardless of whether they appear in the truncated list.

---

### Enrichment section composition

The §11–§20 enrichment block is composed from six section generators that run in a defined order. The order is designed so that the most distinctive sections appear first, with generic catch-alls last:

1. **Rarest domains** — the genome-unique or genome-rare biosynthetic domains in this cluster
2. **Rarest genes** — the genes carrying the rarest domain content, ranked by biosynthetic relevance after singleton filtering
3. **Halogenase subtyping** — detailed analysis of any halogenase in the cluster (fires only when a halogenase is present)
4. **RiPP precursor analysis** — short ORFs and maturation enzyme analysis for RiPP-class clusters
5. **NRPS/PKS typing** — module-level typing for clusters with adenylation or ketosynthase domains
6. **Domain inventory** — a generic count of all domain families in the cluster (the catch-all)

Sections are added in order until the 1,000-character floor is reached, then the composer stops. A section that produces no content (e.g. halogenase subtyping on a cluster with no halogenase) is skipped and not counted toward the floor. Because the three catch-alls (rarest domains, rarest genes, domain inventory) always produce content, the floor is always reachable.

The composition ensures that a distinctive feature like a rare halogenase type appears in the enrichment content before it is potentially crowded out by generic content. If halogenase subtyping fills the floor by itself, the domain inventory is not added — the enrichment is driven by what is interesting, not by what fills space.

#### Rarity ranking with housekeeping down-weighting

Both the rarest-genes and rarest-domains sections use a two-level sort: biosynthetically relevant items before housekeeping items, then by genome frequency (rarest first) within each group. This prevents ribosomal proteins and metabolic enzymes from appearing as "rare finds" just because the genome has one copy of each.

A gene is classified as all-housekeeping only when *none* of its domains survive the singleton filter. A gene where at least one domain is biosynthetically relevant sorts with the biosynthetic group even if most of its domains are filtered.

#### The common-machinery exclusion

The domain inventory reports a total domain count and a "distinctive tailoring/structural content" count. The distinctive count excludes the common NRPS/PKS assembly-line domains (PP-binding, AMP-binding, Condensation, Ketoacyl-synt, PKS_KS, PKS_AT, KR, ACP) that appear in essentially every NRPS and PKS cluster. These domains are still listed in the most-prevalent domain families, but they are not counted toward the "distinctive" figure, which is meant to capture what makes this cluster unusual.

---

### Nominal length: fragment-size yardstick

When a BGC is an Edge or Full-contig fragment, knowing its absolute size in kilobases is only partly informative. A 15 kb fragment of a 30 kb lanthipeptide cluster is 50% recovered; a 15 kb fragment of a 150 kb polyene PKS cluster is 10% recovered. The nominal length module provides a reference-anchored size comparison.

The comparison is expressed as a "recovery fraction" — the fragment's observed antiSMASH region span divided by a reference cluster's known size. The language is deliberately careful:

- "Recovery fraction" not "fraction of the cluster present" — the true cluster may differ from the reference
- The reference size is the antiSMASH region span of the reference cluster, not the full GenBank deposit (antiSMASH regions are typically shorter than the complete deposited sequence)
- Fragments longer than the reference report ">100%" explicitly rather than being clipped

The module is in early development (DRAFT since v9.7.104). As of the current version, one reference entry is seeded: the polyoxin-class nucleoside cluster at 30.0 kb (a two-member mean of 27.9 and 32.0 kb). This entry is explicitly marked `confirmed=False` — it is based on two members from the same biosynthetic lineage, not validated across independent class members. The `[unconfirmed ref]` label appears in every output from this entry until validation is complete.

The recovery fraction output is most useful for clusters that have a well-characterized compound family with a known size range. For the polyoxin/nikkomycin class, the 30 kb nominal gives an informative comparison; for a trans-AT PKS or NRPS, no reference entry exists yet and the module returns nothing rather than estimating. Expanding the nominal reference registry as new MIBiG entries are curated is the natural growth path for this module.

---


---

# The Mathematics of Sapote–Mamey, Volume II

## Cluster G: The Figure System

**Mamey engine v1.9.110 · bundle v9.7.319**  
****

This cluster covers how Mamey turns its computed data into figures. The pipeline produces a large library of figures — per-strain charts during a run, post-seal re-renders, and cross-strain cohort comparisons — and they all share a common design discipline. This document explains that design and what each major figure shows. It is an overview of the figure system's logic, not a module-by-module inventory; the full module catalog lives in the Plumbing Reference.

The two standing interpretive rules apply to figures as much as to numbers: scores are routing priors, not biological proof, and KCB is similarity, not identity. Both are enforced in the figures themselves, not just the documentation — every figure carries a claim-safety footer.

---

### The five shared disciplines

Every figure module in the system obeys the same five rules. These are worth stating once because they are what make the figures trustworthy as evidence rather than decoration.

**1. Data-only PNGs with a companion CSV.** Every figure is saved as a PNG accompanied by a sidecar CSV (`<figure_name>_data.csv`) containing the exact data plotted. This is not optional — it is the evidence-conservation contract. Anyone can open the CSV and reconstruct or re-plot the figure, verify a value, or check that nothing was smoothed or hidden. A figure with no CSV would be an unverifiable claim; a figure with its CSV is a reproducible one.

**2. Non-blocking and best-effort.** Every figure render path is wrapped so that a failure never blocks the package seal. If a figure cannot be drawn — a missing input, an absent plotting library, a malformed table — the pipeline writes a skip marker explaining why and moves on. The scientific artifacts (the manifest, the scores, the scans) are always sealed; figures are best-effort cosmetics layered on top. A render hang or crash costs a figure, never the data.

**3. The saccharide exclusion policy.** Pure-saccharide BGCs are omitted from comparative figures. Sugar biosynthesis genes are present in nearly every bacterium and would clutter every comparison without distinguishing strains. "Pure saccharide" has a precise definition: the BGC's only specialist signal is `saccharide` and it carries none of the 33 specialist classes (NRPS, PKS, RiPP, terpene, siderophore, and others). A BGC annotated as `NRPS;saccharide` is *not* pure saccharide — it plots under NRPS. This rule lives in one module (`figure_policy.py`) and every figure module imports it, so the exclusion is identical everywhere rather than re-derived inconsistently.

**4. The raw BGC count prohibition.** Raw BGC counts must never appear as a headline biological ranking. A strain with 60 raw BGCs in a fragmented assembly does not have more biosynthetic capacity than a strain with 40 in a closed genome — it may have less, with its clusters split into more fragments. Raw counts are fragmentation-sensitive and belong only in QC or context panels that explain *why* the corrected count is needed. The one figure that does plot raw counts (raw count vs contig count) carries an explicit policy annotation on the figure itself stating that it is QC-only.

**5. Claim-safety footers.** Every figure carries a footer line stating its epistemic limits. The standard footer reads along the lines of: "Data-only figure · scores are deterministic capacity signals, not activity measurements · KCB = similarity, not identity · capacity-level." The locus-map footer additionally notes that gene roles come from antiSMASH annotation rather than BLASTP confirmation. When a figure includes unpublished strains, the footer carries the PRIVATE release tag. The footer is not boilerplate — it is the figure stating, in its own margin, exactly what it does and does not claim.

A house-style palette ties the set together: blues lead, with greens (not orange) for the antifungal track so it never collides with the orange used for POOR assembly tiers. All rendering uses a display-free backend so figures generate identically whether or not a screen is attached.

---

### Three tiers of figures

Figures are produced at three different points in the workflow, answering three different scopes of question.

**Per-strain figures, auto-emitted during a run.** When a strain is processed with a standard brief, the pipeline automatically emits a set of reader-facing figures for that single strain. These read the normalized triage rows directly — no judgment layer, no network. They are the figures a researcher looks at first to understand one strain's biosynthetic portfolio.

**Post-seal re-renders.** After a package is sealed, a subset of figures can be regenerated from the sealed data without re-running the analysis. This matters in token-limited or resumed sessions: the locus maps, the lead bars, and the workbook-native figure set can all be re-rendered from what is stored in the package, so a figure that was skipped during the run can be produced later.

**Cross-strain cohort figures.** When more than one strain is processed, the pipeline aggregates the per-strain packages into cohort tables and produces cross-strain comparison figures automatically. These are the figures that turn a collection of isolated strains into a connected dataset — heatmaps of shared and unique capacities, cross-strain lead boards, fragmentation comparisons, and the split-cluster rescue rollup.

---

### The per-strain figures

The core per-strain set answers "what is in this strain, and what should I look at first?"

**The DAPR dual-track scatter** plots every BGC as a point, with its antibacterial score on one axis and its antifungal score on the other. Boundary status colors the points; median guide lines divide the plot into quadrants; the top antibacterial and antifungal leads are labelled node-first. This single figure shows the whole strain's portfolio at once — where the leads cluster, whether the strain is antibacterial-leaning or antifungal-leaning, and which specific BGCs sit at the top of each axis.

**The antibacterial and antifungal ranking charts** are horizontal lollipop charts of the top BGCs on each axis, colored by boundary status. They answer "which BGCs are the strongest leads on this axis, and are they complete or truncated?"

**The claim-safety funnel** is the most conceptually important per-strain figure. It shows, as a four-stage funnel, how a raw BGC count becomes a genuine lead count: raw BGCs → corrected count (Interior + ½ Edge + ¼ Full-contig) → minus saccharide-only clusters → genuine lead tier (antibacterial score ≥ 70 or antifungal score ≥ 44). Each stage is a stated deterministic rule, and the figure makes the whole reduction transparent — a reader sees exactly how many clusters survived each filter and why. This is the figure that defends the strain's headline lead count against the objection "but antiSMASH found sixty clusters."

The extended per-strain set adds a class-distribution bar chart, a CCTT trigger map (which diagnostic triggers fired on which BGCs), a length histogram stacked by boundary status, an Interior/Edge/Full-contig boundary composition, a novelty ranking, a KCB anchor chart (most-cited reference compounds, labelled "similarity, not identity"), and a genome atlas showing each BGC's position along the genome colored by class.

One claim-safety surface deserves specific mention: KCB compound names on figure labels are truncated to 18 characters. This is the only place compound names appear on figures, and the truncation deliberately forces brevity — a similarity signal should not be presented as a precise compound identification.

---

### Locus maps

Locus maps are gene-arrow diagrams of a single BGC (or a paired panel for a split-cluster rescue). Each gene is an arrow, scaled and oriented, colored by functional role. They are the most detailed per-BGC figure — the one that shows the actual gene content rather than a summary statistic.

Gene roles are derived from antiSMASH's functional annotations rather than the product field, so a gene with an empty product annotation still receives a role. The role palette is loaded from an external file, so new chemotype roles can be added without code changes, and unknown gene tokens fall to a default "other / hypothetical" role rather than crashing.

Two design details matter. First, locus maps can be rendered from two sources — the antiSMASH GenBank file during a run, or the sealed gene context afterward — and both paths classify genes identically, so in-run and post-seal maps match. Second, the map zooms to the gene span rather than the full contig: a BGC sitting near the end of a long contig fills the panel instead of being crushed into an illegible sliver at one edge.

---

### Cross-strain cohort figures

The cohort figures compare strains against each other. They read all the per-strain packages and produce comparative views.

**The heatmap series** is the heart of the cohort comparison. Each heatmap is a strain-by-feature grid: strains down one axis, a feature category across the other, with cell color showing the count or intensity. The series covers several feature categories — a megasynthase heatmap (the core PKS/NRPS catalytic domains: ketosynthase, acyltransferase, ketoreductase, dehydratase, condensation, adenylation, and others), a product-class heatmap, a tailoring-enzyme heatmap (halogenases, chitinases, P450s, methyltransferases, glycosyltransferases), a CCTT trigger heatmap, a resistance-tier heatmap, NRPS A-domain and PKS AT-domain substrate consensus heatmaps, transporter and regulator family heatmaps, and a hierarchically-clustered top-domain clustermap. Public strains are ordered first, then private strains, separated by a divider line; a public-only switch drops the private strains for a shareable cut.

**The cohort class-capacity heatmap** is a strain-by-biosynthetic-class grid drawn from the master workbook, showing which classes each strain can make. It uses the same centralized exclusion set as the rest of the comparative layer so all consumers drop identical classes.

**The cross-strain RG-GMCI figures** turn the split-cluster rescue results into a comparison: how many rescue pairs each strain has, the confidence distribution, the score and identity distributions, and the boundary composition. These visualize the fragmentation-and-rescue picture across the whole cohort.

**The metadata-gated collection bundle** is a separate cross-strain layer driven by strain metadata (genus, host, isolation source, bioactivity calls, 16S similarity) rather than by BGC content. Each figure in this bundle declares which metadata fields it needs; the bundle renders only the figures whose required fields are present and writes an availability report for the rest. This layer carries its own careful bioactivity claim-safety discipline: "not tested" is kept strictly distinct from "negative" in every count, and only explicit positive tokens count as positive — the absence of a recorded activity never becomes a negative call.

**The master atlas** assembles a publication-ready, cross-strain dashboard bundle — a boss-facing overview, per-strain cards, cross-strain priority scatters, and boundary landscapes — with stable figure IDs so a specific figure can be referenced across revisions.

---

### What the figure system guarantees

Taken together, the figure disciplines make a specific promise: every figure is reproducible from its companion CSV, states its own epistemic limits in its footer, never lets fragmentation-inflated raw counts masquerade as biology, never plots ubiquitous saccharide clusters as if they distinguished strains, and never blocks the scientific seal if it fails to render. A figure from this system is a claim you can check, not a picture you have to trust.

---


---

*The Mathematics of Sapote–Mamey · Mamey engine v1.9.110 (frozen; the math tracks the engine, not the rolling bundle) · constants re-verified against source 2026-07-14 Every formula and constant cited from engine source. Scores are routing priors, not biological proof; KCB is similarity, not identity; capacity-level language is mandatory downstream of all values in this document.*
