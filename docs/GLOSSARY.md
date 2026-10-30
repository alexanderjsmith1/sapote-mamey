<!-- CANONICAL GLOSSARY -->
# Sapote-Mamey glossary

Find a term from a result, report or command. Search this page with **Ctrl+F**
(**Command+F** on Mac), or start with the core concepts below. Workbook cell codes
have their own [cell-status glossary](troubleshooting/CELL_STATUS_CODE_GLOSSARY.md).

This is the canonical glossary. Formulas and thresholds describe the named
implementation; check that source when comparing results from different builds.

## Core concepts

### 1. BGC — biosynthetic gene cluster

An antiSMASH-called genome region containing genes associated with specialized
metabolism. One biological pathway can span several calls in a fragmented assembly.
The call describes encoded capacity; identifying a produced compound needs other evidence.

Find it in `*_2_inventory.csv`. Identify each locus as
**strain / full node-or-contig / region / BGC alias**, using one source record.
The `BGC###` alias alone is local to that run.

### 2. KCB — KnownClusterBlast

An antiSMASH comparison with characterized clusters in MIBiG. The cumulative
score and protein-hit count describe similarity to the reference cluster.
A leading `~` before a reference compound name means “resembles.”

Read the reference name, score and matched proteins together. “KCB-dark” means
no reference match was found; other diagnostic evidence can still guide review.

### 3. Corrected BGC count

A weighted summary of region boundary categories:
**Interior × 1.0 + Edge × 0.5 + Full-contig × 0.25**, rounded to two decimals by
`mamey/assembly.py::corrected_bgc_count`.

Report it with the raw region count and boundary distribution. A weight of 0.5
is a scoring rule, not a measurement that half a pathway was recovered.
Use matched processing and settings when comparing these counts.

### 4. Edge status

The called region's position relative to contig boundaries. Unknown contig
length gives **Unknown**. A span of at least 95% of the contig gives **Full-contig**
before topology is considered. Otherwise circular records give **Interior**;
a linear or unknown-topology record within 5,000 bp of either end gives **Edge**.

These labels describe geometry. Read the gene evidence separately when assessing
whether a pathway is complete. Terminus-truncation rescue uses a boundary at the
contig end as a trigger.

<a id="5-architecture-confidence-ae-and-the-three-confidence-axes"></a>
### 5. Architecture confidence (A–E) and the confidence axes

The A–E grade summarizes structural evidence from boundaries, annotations,
length and selected supporting signals. It is separate from product-class
confidence, architecture-grade confidence and lead confidence.

`Arch=A, Class_Conf=LOW` can describe a structurally clear region whose class is
uncertain. Keep the axes separate when reading a result. Older files can label
class confidence `Arch_Conf`; check their schema before comparing columns.

### 6. BGC-inventory assembly tier and fragmentation tier

`assembly_tier` summarizes the percentage of BGC calls away from contig edges.
`fragmentation_tier` describes sequence contiguity using contig count and N50.
A genome can score favorably on the first while remaining fragmented on the second.

Use the boundary summary for BGC recovery and contig/N50 measures for genome
contiguity. Genome-size and contamination warnings are separate checks.

### 7. RG-GMCI and the rescue layer

RG-GMCI proposes candidate relationships between fragments using reference
similarity and gene context. Keep the candidate pair, supporting sources and
recorded rule together. Its routing bonus changes review priority.

The contigs remain separate sequences. Compare competing partner assignments
and the actual supporting genes before interpreting a pair as one split locus.
See the detailed rescue definitions below for the selected workflow's fields.

### 8. CCTT / T43 class-trigger framework

CCTT/T43 signals flag genes or motifs associated with biosynthetic classes,
such as HAL, LAN, TET, PHO, NUC and ENE. They can draw attention to regions with
weak or unavailable KnownClusterBlast evidence.

Report both the number of hits and the number of regions containing them.
Several marker hits in one region are different from a marker spread across
several regions.

### 9. Marker registry

The diagnostic-marker registry gives each scoring signal a stable ID, class
and weight. It connects a score to the annotation or motif that triggered it.

Look for marker IDs in the board and evidence-traceability records. The
real-anchor rule matches keywords to strings antiSMASH actually emits; use the
recorded match when explaining a score.

### 10. Mamey triage tier / routing prior

The triage tier tells you where the engine suggests spending review effort.
It uses the largest antibacterial, antifungal or novelty routing score, followed
by diagnostic floors and other scoring rules.

`mamey/scoring.py::triage_bgcs` uses **Exceptional ≥85**, **High ≥70** and
**Medium ≥50**. Below 50, class policy selects **Low** or **Inventory**.
Read these as prioritization categories rather than measured activity.
A downstream Wet-Lab score is a separate metric.

### 11. Diagnostic bonus & diagnostic floor

A diagnostic bonus changes a routing score. A diagnostic floor can raise an
eligible candidate to Medium when corroborated class evidence warrants attention
despite weak or unavailable KCB evidence.

Eligibility, tailoring-only exclusions and later standing-rule or RiPP downgrades
still apply. Read the score-rationale record, including
`AF_DIAGNOSTIC_TRIGGERS`, to see which rule affected that region.

### 12. Standing rules and workflow-scoped exclusions

A standing rule changes how a particular signal is used in a named workflow.
Read its current scope: a historical prevalence note or neutral annotation does
not automatically exclude a region from every comparison.

For cohort comparisons, keep the selected rule, measured cohort and denominator
with the result. Revisit an earlier interpretation when its evidence or scope changes.

### 13. Claim-safety vocabulary

Use language that matches the evidence: sequence predictions describe capacity,
reference comparisons describe similarity, and measured results name their assay
conditions. Missing or unrun evidence stays marked as missing.

`[EG]` means evidence-grounded and `[VL]` means literature-verified. A claim ceiling
is the strongest statement the available evidence supports. Keep strain-level
bioactivity with its material, assay and source; connecting it to an individual
locus requires separate evidence.

### 14. Mode B

A written interpretation of one locus, built from its full gene roster and
supporting sources. The default full48 profile uses **§1–§48**; the optional
current50 v2 profile uses 50 sections. Follow the
[authoring walkthrough](MODE_B_USER_WALKTHROUGH.md) for the selected profile.

The template, authored card, verification report and saved package record are
different files. Keep `document_state`, typed evidence states and complete locus
identity with the card. Distinguish nr, NCBI ClusteredNR and local Swiss-Prot matches.

### 15. Evidence axes & legacy lead classes (A / B / C)

Evidence axes keep different reasons for pursuing a region visible. Some
historical cohort workflows combine them into A/B/C lead classes. Those labels
are separate from the current Mamey triage tiers.

Use the emitting workflow's rules, weights and cohort denominator when comparing
classes. Recompute a cohort result after changing its membership.

### 16. Compound-class annotation

A label for the type of chemistry suggested by product annotations, class
diagnostics and reference matches. Read the class label together with its source
and supporting references.

Class matrices summarize a selected cohort. Recompute them after merging cohorts
so their counts and membership describe the new set.

## Enumerations & code tables

*The sections below are scan-friendly lookup tables. They hold codes, classes, and status values you match against output. The concepts behind them live in **Core concepts** above.*

## BGC classes (antiSMASH product annotations)

These are antiSMASH product-class annotations. Read the examples as reference-class
context; the core BGC definition explains what a call establishes.

| Term | Full name | What it means in plain English |
|---|---|---|
| T1PKS | Type I polyketide synthase | A large assembly-line enzyme that builds polyketide natural products (e.g. erythromycin, rapamycin). Often antibacterial or antifungal. |
| T2PKS | Type II polyketide synthase | An iterative enzyme system making aromatic polyketides (e.g. tetracyclines, anthracyclines, angucyclines). Usually has a strong UV chromophore. |
| T3PKS | Type III polyketide synthase | Simpler single-enzyme PKS; makes flavonoids and some phenolic compounds. |
| transAT-PKS | trans-acyltransferase PKS | A Type I PKS variant where the acyltransferase acts in *trans* (as a standalone enzyme). Frequently fragments across contigs; a common source of split pathways. |
| PKS-NRPS hybrid | Hybrid assembly line | A single megasynthase combining polyketide and peptide modules; builds mixed peptide-polyketide scaffolds. |
| hglE-KS | Heterocyst-glycolipid KS-like | A KS domain related to cyanobacterial glycolipid synthesis; used as a marker for certain reducing polyketide assemblies. (See *hglE-KS-PREV-001* under standing constraints — prevalent and habitat-non-specific.) |
| NRPS | Non-ribosomal peptide synthetase | Assembly-line enzyme building peptide natural products without the ribosome (e.g. vancomycin, daptomycin). |
| NRPS-like | NRPS-related | Has NRPS domains but doesn't follow the standard modular architecture; often makes small aryl-acid or diketo compounds. |
| RiPP | Ribosomally synthesized and post-translationally modified peptide | A peptide made by the ribosome, then chemically modified. Includes lanthipeptides, thiopeptides, sactipeptides. |
| Lanthipeptide (class I–IV) | Lanthipeptide | A RiPP with thioether (lanthionine) bridges. Class III made by LanKC multifunctional synthetase. Often antimicrobial. |
| Thiopeptide | Thiazolyl peptide | A heavily modified RiPP with a central pyridine/dehydro-ring; potent Gram-positive antibacterials (e.g. thiostrepton). |
| LAP | Linear azol(in)e-containing peptide | A RiPP class with heterocyclized cysteine/serine residues; includes the microcin/plantazolicin family. |
| Lassopeptide | Lasso peptide | A RiPP threaded into a knot-like lasso fold; protease- and heat-stable, often receptor antagonists. |
| Sactipeptide | Sulfur-to-alpha-carbon peptide | A RiPP with sactionine (Cα–S) bridges installed by a radical-SAM enzyme. |
| RaS-RiPP / ranthipeptide | Radical-SAM RiPP | A RiPP modified by a radical-SAM maturase; structurally novel, often KCB-dark. |
| NI-siderophore | NRPS-independent siderophore | An iron-scavenging molecule made without an NRPS assembly line. |
| NRP-metallophore | Non-ribosomal peptide metallophore | A metal-chelating NRP; often dual-function (iron-scavenging + bioactive warhead). |
| Betalactone | β-Lactone | A four-membered ring lactone; electrophilic warhead that inhibits serine hydrolases and proteases. Rare, high bioactivity potential. |
| Spirotetronate | Spirotetronate | A polyketide with a spiro-linked tetronic-acid ring; large clusters, often potent antibacterials (e.g. abyssomicin, kijanimicin). |
| Enediyne | Enediyne (9-/10-membered) | An extremely potent DNA-cleaving warhead class (e.g. calicheamicin). cytotoxicity caveats apply (handling per standard lab SOPs); see *T43-ENE / [E-signal]*. |
| Ansamycin / ansa-PKS | Ansamycin | A polyketide with a macrocyclic *ansa* bridge across an aromatic core (e.g. rifamycin). |
| Glycopeptide | Glycopeptide NRPS | A cross-linked, glycosylated heptapeptide class (e.g. vancomycin, kistamicin). Often carries *VanHAX* self-resistance. |
| Aminoglycoside / amglyccycl | Aminoglycoside / aminocyclitol | Sugar-based antibacterials (e.g. streptomycin, kanamycin); may carry *APH/AAC* self-resistance. |
| Nucleoside | Nucleoside antibiotic | A modified-nucleoside scaffold; includes chitin-synthase-inhibiting antifungals (e.g. nikkomycin/polyoxin class). Frequently KCB-dark. |
| Azoxy / guanidinotide | Azoxy / guanidino natural products | Specialized nitrogen-rich warhead classes flagged for novelty. |
| Terpene | Terpene/terpenoid | Built from isoprene units; includes antibiotics, pigments, and volatile compounds. |
| Saccharide | Sugar/glycoside | Carbohydrate-modifying cluster; often appended to a polyketide or peptide aglycone. (See *saccharide-gating* under standing constraints.) |
| Butyrolactone | γ-Butyrolactone | Autoregulatory signaling molecule (quorum sensing) in Streptomyces. Routes to ecology, not drug discovery. |
| Ectoine | Ectoine | Compatible solute for osmotic stress; not a drug-discovery target. |
| Indole | Indole-derived | Clusters making indole-containing metabolites (some pigments, some bioactive). |
| Phosphonate | Phosphonate | C–P-bonded compounds (e.g. fosfomycin class); may carry fosfomycin self-resistance. |
| Redox-cofactor | Redox cofactor | Biosynthesis of cofactor-like small molecules; usually primary-metabolism-adjacent. |
| Melanin | Melanin | Pigment biosynthesis. |
| Fatty acid | Fatty acid | Lipid/fatty acid biosynthesis cluster. |
| NAPAA | Non-alpha poly-amino acids | e.g. poly-gamma-glutamate; structural/protective rather than bioactive. Registry-neutral (listed, not interpreted; neither downgraded nor lead-blocking). |
| Halogenated | Halogenated compound | Cluster predicted to make a chlorinated or brominated product (halogenase present). |

---

## Scan names and abbreviations

Mamey runs a fixed battery of deterministic detection modules ("scans") over the antiSMASH output. Each BGC carries a record of which scans fired.

| Abbreviation | Full name | What it checks |
|---|---|---|
| KCB | KnownClusterBlast sweep | Scores each BGC against the MIBiG database of known clusters; high scores = known-class candidate. |
| RG-GMCI / RGGMCI | Reference-Guided Genome Mining Candidate Inference | Homology-guided linkage of fragmented BGC regions that map to the same reference producer cluster in ClusterBlast/KnownClusterBlast output. Candidate inference, not a physical contig joiner; mandatory pre-triage step for fragmented (multi-contig) assemblies. |
| FLBR | Fragment-Linkage BGC Recovery | Census of fragmented megasynthase (PKS/NRPS) sets across contigs — flags LMPKS_FRAGMENT_SET; identifies the candidate fragments that EFLS/RG-GMCI then link (a detection step that feeds recovery, not the linkage itself). The README labels the same scan the "fragmented-megasynthase census". |
| EFLS | Edge-Flank Linkage Scan | Preliminary shared-label pair heuristic over a capped BGC set. Skips pairs whose two records are both exactly Interior; scores shared product, MIBiG, cassette and CCTT labels. It does not compare raw contig ends, require different contigs or establish physical linkage. |
| CCTT | Compound-Class Trigger Table | Flags specific biosynthetic signals: HAL (halogenase), LAN (lanthipeptide), TET (tetronate/spirotetronate), PHO (phosphonate), NUC (nucleoside), and others. A CCTT trigger is the per-BGC signal the marker-aware scorer reads. |
| CGAD | Chitinase Genome Architecture Detection | Detects chitin-degrading enzyme families (GH18, GH19, AA10_LPMO, CBM_CHITIN, GlcNAc). Used as the chitin-context gate for nucleoside antifungal calls. |
| UMED | Unclustered Maturation Enzyme Detection | Scans maturation keyword patterns and couples hits to each BGC within a 5,000-bp flank. For selected family-enriched product tokens, any coupled hit yields IN_CLUSTER_OR_PROXIMAL_MATURATION_SOURCE_SUPPORTED and no hit yields MATURATION_GAP_SOURCE_DERIVED; other products are NOT_MATURATION_GATED. This does not verify the full required enzyme complement, precursor presence, function or a separately rescued enzyme. Missing/unrun evidence is not absence. |
| FLBR/EFLS/RG-GMCI trio | Fragment review context | FLBR records a motif/count-based megasynthase census and fragment flags; EFLS nominates shared-label pairs; RG-GMCI retains its separate reference/geometry candidate-inference contract. Shared source annotations are not automatically independent corroboration. None physically rejoins contigs or establishes a single shared pathway. |
| bldA/TTA | bldA codon scan | Counts TTA codons in BGC-overlapping CDS: T1 zero, T2 one or two, T3 three to five, T4 six or more. Recognized non-actinomycetes receive NOT_APPLICABLE while counts remain recorded; unknown taxonomy needs review. A burden flag does not measure expression or prove bldA dependence under a selected culture condition. |
| TFBS | Transcription Factor Binding Site scan | Counts regulatory motifs (GBL/AdpA, DasR, BldD, PhoP, SARP) near BGCs; guides induction strategies. (See *Regulatory elements* below.) |
| CCSM | Cross-Cohort Strain Module | Cross-strain comparison module: compares a strain's BGC/marker profile against the rest of the cohort. |
| DAPR | Dual Antibacterial/Antifungal Prioritization Ranking | Sapote protocol for ranking top 3 antibacterial and top 3 antifungal BGC leads. |
| LMPKS | Linear Megasynthase PKS | Historical label within LMPKS_FRAGMENT_SET. The current FLBR flag uses KS-like pattern counts plus fragmented PKS/NRPS/transAT product labels; it does not establish linear assembly architecture, polyether chemistry or ionophore activity. |

**CCTT counts:** `cctt.counts` counts gene/motif matches across the genome;
`cctt.trigger_bgc_counts` counts the distinct regions containing them.
Eight hits in one region and eight hits across eight regions describe different distributions.

---

## Regulatory elements & TFBS

The TFBS scan counts binding-site motifs for the regulators below near each BGC. They do not change *what* a cluster makes; they hint at *how to switch it on* in the lab (induction strategy) and, in the SARP case, feed the lead-class logic.

| Regulator | What it is | Why it matters here |
|---|---|---|
| SARP | Streptomyces Antibiotic Regulatory Protein | A pathway-specific *activator*. A SARP sitting in/near a BGC is positive evidence the cluster is a real, regulated antibiotic pathway — it is one of the five evidence axes and the second axis (with Mode B) that defines a Class-A lead. Read per-BGC, not genome-wide. |
| DasR | GlcNAc-responsive global repressor | Links nutrient sensing (N-acetylglucosamine, a chitin breakdown product) to antibiotic onset. A DasR site is a weak positive (a fractional point) in the score. |
| AdpA / GBL | A-factor / γ-butyrolactone cascade | The quorum-sensing developmental switch; GBL/AdpA control timing of secondary metabolism. |
| BldD | Master developmental repressor | Gatekeeps the switch from growth to sporulation/secondary metabolism. |
| PhoP | Phosphate-response regulator | Couples phosphate limitation to antibiotic production; relevant to media design. |

---

## Architecture confidence codes

→ *Concept and the four-axis framework: **Core concepts #5**. The lookup grids are below.*

Mamey assigns the A–E structural grade to every BGC from its position in the assembly.

| Code | Name | Meaning |
|---|---|---|
| A | Interior, coherent | Interior with a core-bearing product and length ≥10 kb, or a guarded compact chemical-hybrid promotion. Structural heuristic, not pathway-completeness proof. |
| B | Interior, limited/compact | Interior with core annotation or KCB score ≥10,000 that does not meet the A branches; strong KCB can support B without core annotation. |
| C | Edge, core-bearing | Edge with a recognized core-bearing product annotation. Partial interpretation only. |
| D | Edge limited / Full-contig core-bearing | Edge without core annotation, or Full-contig with core annotation. Keep geometry and partial-capacity caveats. |
| E | Other weak/ambiguous cases | Remaining cases, including Full-contig without core annotation or Unknown geometry. Inventory-level architecture interpretation. |

The four confidence fields in `*_4_triage_board.csv` answer different questions:

| Column / field | What it measures | Values |
|---|---|---|
| `Arch` (architecture_confidence) | Structural completeness of the locus — the A–E grade above. | A–E |
| `Arch_Capacity` (architecture_capacity) | The claim-safe class-capacity call — a class *name*, not a confidence. | e.g. "lanthipeptide-class capacity" |
| `Class_Conf` (architecture_class_confidence) | Confidence in that class call. | HIGH / MODERATE / LOW |
| `claim_confidence` (B1) | Lead-claim label mapped from the A–E architecture grade by the current scorer; distinct from product-class confidence. It does not measure assay activity or product identity. | High / Moderate-High / Moderate / Low-Moderate / Low; Unknown fallback |

*History: through v9.7.27 `Class_Conf` was labeled `Arch_Conf`, which read as architecture-grade confidence (which it is not); renamed in v9.7.28*.

`Composite_region` fires when `Single_protocluster_count >= 3`.
`Overmerge_state` reports the E5 verdict: `OVERMERGE_SUSPECT`,
`COHERENT_CHEMICAL_HYBRID` or `NOT_VERIFIABLE`. Use `Protocluster_count`
for the number of resolved antiSMASH protoclusters, including a two-protocluster merge.

---

## Edge status (used in the corrected count)

→ *Concept and claim ceiling: **Core concepts #4**.*

The truncation label that drives the corrected count:

| Status | Meaning | Weight in corrected count |
|---|---|---|
| Interior | Does not trigger current boundary tests; circular records reach this branch only after the 95%-span test | 1.0 |
| Edge | Within 5,000 bp of either contig end on linear/unknown topology | 0.5 |
| Full-contig | Region span is at least 95% of contig length, tested before circular topology | 0.25 |
| Unknown | Contig length unavailable/nonpositive; preserve missingness rather than infer geometry | Preserve producer’s separate handling |

---

## Evidence axes & legacy lead classes (A / B / C)

→ *Concept and the precision-not-confidence caveat: **Core concepts #15**.*

Evidence axes remain separate because they answer different questions. A
downstream builder may combine selected axes, but its versioned rule and
denominator must travel with the output.

| Axis | Question it answers |
|---|---|
| Structure / completeness | Is the visible locus coherent and physically complete enough for the proposed class? |
| Similarity | Does the locus resemble a characterized reference cluster? |
| Novelty / reference darkness | How weakly is the locus represented in the bound reference channels? |
| Diagnostic machinery | Do class-compatible genes, domains, or resistance signals corroborate the class? |
| Regulation / expression planning | Are pathway-linked regulatory signals present? This is not expression evidence. |
| Authored judgment | What claim-safe synthesis did the current Mode B review reach from the bound evidence? |

**Class-A / B / C** are legacy judgment-layer labels from selected cohort builders.
Read the emitting file's rule, version and denominator when comparing them.

---|---|---|
| Class-A / B / C | Legacy judgment-layer labels emitted by selected cohort builders. | Read the emitting artifact's rule, version, and denominator; there is no version-free membership count. |

---

## Marker-aware scoring & the diagnostic floor

→ *Concept and the KCB-dark rationale: **Core concepts #11**.*

| Term | Meaning |
|---|---|
| T43-NUC | A nucleoside diagnostic trigger. On a KCB-dark nucleoside cluster *with chitin context* (CGAD-positive), it adds an antifungal bonus and floors the cluster to at least Medium — the nikkomycin/polyoxin-style antifungal case a KCB-only scorer would miss. |
| Diagnostic floor | An eligible corroborated class marker or cargo-aware T1 self-protection signal can raise Low/Inventory to Medium. Tailoring-only exclusions and eligibility checks apply; later standing-rule and short RiPP-fragment guards can lower the resulting tier.  |
| AF_DIAGNOSTIC_TRIGGERS | The set of antifungal-diagnostic markers that fire the floor. |
| Real-anchor rule | Audit every keyword against the strings antiSMASH *actually emits* (e.g. "nucleoside", "SGR PTMs"), not textbook compound names (e.g. "nikkomycin"). |

---

## Mamey triage tiers

→ *Concept and the effort-not-confidence caveat: **Core concepts #10**. Code remains the threshold authority.*

Mamey assigns every BGC a routing tier from its AB, AF, and novelty priors,
then applies corroborated floors and fail-safe downgrades.

| Tier | Criteria | Treatment |
|---|---|---|
| Exceptional | Current best routing prior ≥85 | Highest engine routing prior; still capacity-level and subject to guards |
| High | Current best routing prior ≥70 | High routing priority |
| Medium | Current best routing prior ≥50, or an applicable diagnostic/machinery floor | Review priority; a floor does not raise claim confidence |
| Low | Below 50 with a resolved specialized class outside the governed Inventory policy | Keep visible at lower routing priority |
| Inventory | Below 50 and unresolved or covered by the governed Inventory policy | Keep in the complete inventory; do not equate with biological unimportance |

The thresholds above describe the current engine and must be checked against
`mamey/scoring.py::triage_bgcs` when used outside this bundle.

---

## Resistance gene families

| Term | What it is | Self-protection significance |
|---|---|---|
| Beta_lactamase_fold | β-Lactamase-fold protein adjacent to biosynthetic genes | T1 diagnostic: strong evidence the BGC makes an antibacterial compound the producer must resist |
| APH/AAC | Aminoglycoside phosphotransferase / acetyltransferase | T1/T2: self-protection or routing; also common housekeeping |
| Erm_methylase | Erythromycin ribosome methylase | T1 diagnostic: typically paired with macrolide biosynthesis |
| VanHAX_like | Vancomycin resistance cluster | T1 diagnostic: paired with glycopeptide biosynthesis |
| Fosfomycin | Fosfomycin resistance | T1 diagnostic |
| Self_resistance_general | General self-resistance annotation | T2: supportive but non-specific |

**Resistance tiers:**

- **T1** — diagnostic self-protection co-located with biosynthetic genes
- **T2** — resistance-like but not directly diagnostic
- **T3** — transporter-only routing (efflux without biosynthetic coupling)
- **NULL** — no source-derived resistance detected

**Proximity rule:** a resistance marker only counts toward a lead if it sits *near* the BGC. A genome-wide β-lactamase elsewhere on the chromosome is not self-protection evidence for a distant cluster.

---

## BGC-inventory and fragmentation tiers

→ *Concept and claim-ceiling role: **Core concepts #6**. Keep the two fields separate.*

`assembly_tier` is derived only from the proportion of BGC calls that are Interior:

| `assembly_tier` | Interior-BGC percentage | Meaning |
|---|---|---|
| GOOD | ≥70% | Most called regions avoid contig boundaries |
| MODERATE | ≥45% | Mixed boundary recovery |
| POOR | ≥20% | Many called regions meet contig boundaries |
| VERY_POOR | <20% | Most called regions meet contig boundaries |
| UNKNOWN | unavailable denominator | Boundary-recovery tier cannot be computed |

`fragmentation_tier` is a separate ordered contig/N50 classification. The first
band satisfying both limits wins:

| `fragmentation_tier` | Current ordered band |
|---|---|
| CLOSED | ≤2 contigs and N50 ≥1,000,000 bp |
| CONTIGUOUS | ≤20 contigs and N50 ≥500,000 bp |
| DRAFT | ≤100 contigs and N50 ≥100,000 bp |
| FRAGMENTED | ≤1,000 contigs and N50 ≥10,000 bp |
| HIGHLY_FRAGMENTED | valid contig count but no earlier band matches |
| UNKNOWN | contig count unavailable or invalid |

Report raw region counts, weighted counts and these tiers together.
The core corrected-count definition explains the weighting and its limits.

---

## Key metrics

| Term | Meaning |
|---|---|
| KCB cumulative score | Sum of KnownClusterBlast protein hit scores vs MIBiG; higher = closer match to a known cluster |
| KCB protein hits | Number of proteins with significant KCB hits; more hits = more complete match |
| MIBiG | Minimum Information about a Biosynthetic Gene cluster database; reference collection of known BGCs |
| Corrected BGC count | Interior + 0.5 × Edge + 0.25 × Full-contig; the defensible BGC inventory figure |
| Interior % | Fraction of BGCs fully inside contigs (not truncated at edges) |
| N50 | Contig length at which 50% of the assembly is in contigs this size or larger; proxy for assembly contiguity |
| RGGMCI | Reference-Guided Genome Mining Candidate Inference; the mandatory pre-triage, homology-guided linkage of fragmented BGC regions to a shared reference producer cluster (ClusterBlast/KnownClusterBlast) |
| Mode B | Expanded §1–§48 per-BGC interpretation protocol: exact-locus identity, canonical gene roster, channel-separated evidence, architecture, tailoring, resistance, product class, provenance, caveats, decisions, and claim-safe verdict |
| DAPR | Dual Antibacterial/Antifungal Prioritization Ranking — the two parallel top-3 lead tracks |
| Hallucination trap | A check applied to every BGC to catch over-interpretation of generic or ambiguous domain annotations |
| Wet-Lab / WL score | A downstream experimental-priority metric emitted by selected judgment tools. It is separate from the Mamey triage tier and must identify its own versioned inputs and rule. |

---

## Claim-safety vocabulary

→ *The discipline in full: **Core concepts #13**. The complete term list is below.*

Use these terms when explaining the evidence behind a result.

| Term | Meaning |
|---|---|
| Biosynthetic capacity | The permitted way to describe what a cluster *could* make. "Biosynthetic capacity consistent with a glycopeptide" — never "produces vancomycin." |
| Claim ceiling | The maximum confidence a statement may reach for a given evidence level. Fragmented assemblies, KCB-dark clusters, and edge clusters all lower the ceiling. |
| `[EG]` / `[VL]` | Evidence-tag on a verdict. `[EG]` = *evidence-grounded* but not literature-verified (provisional); `[VL]` = *verified against literature*. A project identifier or privacy tier never upgrades the tag. |
| Architecture Confidence | The A–E grade (above), reported alongside every claim so a reader sees the structural basis. |
| Evidence Traceability | A block linking each claim back to the specific scan/hit that supports it. |
| ~ (tilde) | "Resembles, is not." Prefixes any known-compound name attached by KCB (e.g. "~kijanimicin"). Similarity, not identity. |
| Bioactivity metadata | Optional typed isolate-level assay context. Omission is `NOT_SUPPLIED`; distinguish `NOT_OBSERVED`, `UNKNOWN`, `NEGATIVE` and `POSITIVE` as defined below. A measured negative is assay-scoped; no observation is attributed to a BGC without governed linkage. |
| Missingness vs absence | "Not found in this assembly" (a fragmented genome may simply not contain the region) is reported as *missingness*, never as proof a gene is *absent*. |

---

## Typed assay observations

Observation states apply to the recorded assay, target, tested material, dose,
time point and decision criterion. These isolate-level records need a separate
evidence link before activity can be assigned to a BGC.

| Observation state | Meaning |
|---|---|
| `NOT_OBSERVED` | No assay observation is supplied; this is not a measured negative. |
| `UNKNOWN` | Context is supplied but an interpretable measured outcome is not established. |
| `NEGATIVE` | A bound measured result is negative under the stated assay conditions and criterion; it does not establish biological inactivity under every condition. |
| `POSITIVE` | A bound measured result is positive under the stated assay conditions and criterion; it does not establish a named compound, expression or locus-level causality. |

`bioactivity_metadata_v1` also records `metadata_state`: `NOT_SUPPLIED`,
`SUPPLIED_UNKNOWN`, `MEASURED_NEGATIVE`, `MEASURED_POSITIVE`,
`BIOACTIVITY_LEGACY_SHAPE_HOLD` or `LEGACY_UNTYPED_CONTEXT`.
Keep this field with the assay records, usage scope, receipt binding and
`compound_linkage`. Example or legacy metadata cannot supply a missing observation.

## Evidence, identity, portability, and authority vocabulary

These terms describe how the portable application finds and binds external
evidence, how Mode B reports readiness, and how release tooling separates a
candidate from an authorized release.

| Term | Meaning |
|---|---|
| Exact-locus identity | The mandatory display and join identity for one BGC: `strain / full node-or-contig / region / BGC alias`. The alias is last and source-scoped. Missing components cause a hold; they are never guessed. |
| Source object | An external evidence file or dataset represented by its source role, logical locator, SHA-256, byte count, and binding/admission state. A path, filename, timestamp, or duplicate copy is not source authority by itself. |
| Logical locator | A portable reference such as `evidence://root-id/path` that resolves through runtime configuration. Machine-specific absolute paths may be supplied at runtime but do not enter portable or public reports. |
| Discovery catalog | A bounded inventory of candidate collections. `DISCOVERED_NOT_ADMITTED` means exactly that: discovery proposes material for review and does not authorize consumption. |
| Admission / collection decision | The recorded choice `CONSUME`, `REJECT_WITH_REASON` or `SUPERSEDED_WITH_RECEIPT` for a collection identified by its hash. `CONSUME` permits the workflow to read those files. |
| Exact-locus evidence states | `EXACT_LOCUS` is bound to strain, full node/contig, and region; `ALIAS_BOUND` lacks an independent full locator; `STRAIN_ONLY` is context only; `UNBOUND` cannot yet join; `ABSENT` means no matching artifact in the configured scope. `UNBOUND` and `ABSENT` are workflow states, not biological negatives. |
| Evidence-readiness states | `READY_BOUND` may be integrated; `AVAILABLE_UNINGESTED` must be ingested first; `NEAR_READY_ACTIVE_RUN` remains blocked while a run completes; `PRACTICALLY_ATTAINABLE` should be obtained before content QA; `STRUCTURALLY_UNAVAILABLE` and `NOT_APPLICABLE` require a typed reason. |
| Gene-first / sequence-first review | Build the canonical gene roster before prose and preserve its order. Bind a protein result by the exact locus plus protein SHA-256; a locus tag or similar name alone does not prove sequence identity. Every canonical gene remains in the denominator, including boundary/context genes. |
| Channel-separated BLASTp | NCBI nr, NCBI ClusteredNR, and local Swiss-Prot are separate evidence channels with separate named-match, alignment-metric, state, and coverage fields. Missing or unbound evidence in one channel is never filled from another. ClusteredNR is not nr; percent positives is not percent identity; similarity is not functional proof. |
| `document_state` / `evidence_state` | Two orthogonal Mode B axes. `document_state` says where the card is in the authoring/review ladder; `evidence_state` records bound, unbound, quarantined, unavailable, or not-applicable evidence. Read both fields to distinguish writing progress from evidence availability. |
| Privacy profile | User-owned policy mapping exact strain IDs to named access tiers. Unassigned strains inherit a required non-public default. Only a tier explicitly marked `public_export: true` maps to package `PUBLIC`; all others map to `PRIVATE`. |
| Package `PUBLIC` / `PRIVATE` | Binary run/export metadata used by package consumers. An exact privacy profile uses its required non-public default for unassigned strains. Without a profile or explicit public authority, the current resolver defaults to PRIVATE for every ID prefix; an admitted public override or exact public assignment has a separate recorded basis.  |
| Release/archive transaction states | **Source tree**, **staged tier tree**, **archive candidate**, and **verified archive** are distinct objects.  `PUBLIC_RELEASE` is a separately authorized promotion state; a CODE or `NOT_FOR_PUBLIC_RELEASE` candidate is not one. |
| Portable / offline core | The application, small reference assets, vendored fallbacks, and local wheel paths are designed to run without network access. Optional commands whose names or help explicitly say online may contact their named service and must keep provenance; their absence is an evidence gap, not a failed core extraction. |
| Sealed package | A package that passed the extraction and package-integrity checks for its recorded engine and inputs. `MAMEY_COMPLETE` reports that extraction state; written interpretation has a separate status. |
| Post-seal tool | A tool that uses an existing sealed package, such as Mode B, comparison or figure tooling.  Authoring can write package files and refresh checksums; validation normally writes a status receipt. |
| Mechanical gate / authority ceiling | A check of named conditions such as schema, hashes, identity or completeness. Read the check's scope and result; release decisions follow the separate release procedure. |

Contract sources: `PORTABLE_EVIDENCE_WORKSPACE.md`,
`MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md`,
`MODE_B_SUPPORT_CARD_CONTRACT.md`,
`MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md`,
`PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md`, and the release tools under `tools/`.

---

## Standing biological constraints

Permanent rules, learned across many strains, that override case-by-case interpretation. They exist to stop recurring over-claims.

| Constraint | Rule |
|---|---|
| NAPAA (poly-amino-acid class) | Current registry status is neutral, action none, lead_blocking false: no intrinsic comparison/ecological exclusion or score downgrade. Keep product tokens and interpret only bound evidence at its actual scope. The former Nosema/glucocerebrosidase hypothesis remains retired. |
| hglE-KS-PREV-001 | Current registry status is noted, scope informational, lead_blocking false. Historical prevalence is context, not by itself a comparative-ranking downgrade or a universal habitat claim. Separately, the current scorer’s direct hglE-product check can set a standing-rule flag when no CCTT trigger is present and lower the tier; inspect the actual flag and producer. The separate gene-level enediyne-artifact guard remains applicable; a zero/unbound KCB result does not prove new chemistry. |
| Saccharide-gating null | Pure-saccharide clusters (carbohydrate machinery with no specialist warhead) are omitted from comparative counts; the polysaccharide-gating signal was confirmed null in the bryophyte and attine sets. |
| Multi-siderophore flag | Carrying several siderophore systems recurs across many strains; treated as an iron-economy observation, not a per-strain distinction. |
| T43-ENE / [E-signal] | A genuine enediyne (`ene_KS`) carries an [E-signal] claim-safety note — cytotoxic/DNA-damaging class; cytotoxicity/self-protection review, handling per standard lab SOPs (no selective BSL-2 gate — selective biosafety flags give false reassurance). Confirm a genuine `ene_KS` call vs an `hglE-KS` cross-reaction at the gene level first. |

---

## Validation vocabulary

Terms used in the external-validation record (runs on public reference genomes that test whether the pipeline behaves).

| Term | Meaning |
|---|---|
| Type strain | The designated reference isolate for a species, with a public, well-characterized genome. Used as a known-answer test. Label a genome `[Type]` only when its NCBI Assembly record says "assembly from type material". A strain name that looks like a type designation is not enough ([figure house rules](FIGURE_HOUSE_RULES.md), rule 7). |
| ANI de-replication cutoff | Reference genomes at 96% ANI or above, with an aligned fraction of at least 0.5, count as redundant, and one is kept. The cutoff limits compute. It is not a species boundary. A 99% figure in this project refers to 16S rRNA similarity, not ANI. |
| Positive control | A genome whose chemistry is known in advance (e.g. MAR4 marine *Streptomyces* and its halogenated meroterpenoids); the run should recover that signature. |
| Negative control | A genome expected *not* to light up (e.g. *Deinococcus radiodurans*); guards against false positives. |
| Blinded prospective validation | Running the pipeline on a genome before checking the literature answer, so the call can't be tuned to fit. |
| Corrected-vs-raw percentile | The validation figure's axis: a strain's BGC-count rank before and after the correction. High-retention genomes rise; fragmented ones fall. The point is that the *corrected* count tracks quality, not raw abundance. |

---

## Ecological habitats & host systems

The cohort spans three symbiotic niches; these words appear in strain descriptions and chapter titles.

| Term | Meaning |
|---|---|
| Attine / fungus-garden | Fungus-growing ants and the actinomycetes associated with their gardens (e.g. *Pseudonocardia*, *Amycolatopsis*); a classic defensive-symbiosis source of antifungals. |
| Bryophyte / lichen | Mosses, liverworts, and lichens and their associated actinomycetes; one of the three habitat sets. |
| Hymenoptera / bee | Bees and wasps and their symbionts (e.g. *Streptomyces philanthi*, the beewolf symbiont); the third habitat set. |
| Fungus-growing termite | An independent insect-fungiculture system (e.g. *Macrotermes*); a natural cross-system comparator to the attine ants. *Actinomadura macrotermitis* RB68 is the bundle's public termite-symbiont validation genome. |
| Actinomycete | The bacterial group (Actinomycetota) that dominates this project; prolific producers of natural products. Genera here include *Streptomyces*, *Amycolatopsis*, *Pseudonocardia*, *Saccharothrix*, *Micromonospora*, *Nocardia*, *Actinomadura*, *Sciscionella*. |

---

## Release tiers & gates

How the bundle is staged for distribution. Tier construction, package privacy,
and promotion to a public release are separate controls.

| Tier | Contents | Purpose |
|---|---|---|
| CODE | Data-free: engine, tools, docs, templates. No banks, no internal working docs. | The GitHub-push artifact. |
| CODE-analysis-free | A lean CODE variant with selected analysis outputs removed. | Smaller code/tool handoff. |
| SID-public | CODE + the public SID cohort banks (the SID strains carry public GenBank/GCA genomes). | The supplementary data archive. |
| MERGED-PRIVATE | Everything, including `private/` and real AS identifiers. | The private scaffold; never published. |
| PUBLIC-RELEASE | A separately authorized public promotion cut. | Publication/distribution only after the active governance and archive gates pass. |

| Gate | Meaning |
|---|---|
| Technical release gates | Schema, tests, identity, checksum, membership, derivation, and content-audit checks. Passing them creates technical evidence only. |
| Governance gate | A separately active, signed, non-invalidated decision required for `PUBLIC_RELEASE`; candidate tiers remain candidates without it. |
| Leak/content audit | The staged public tree is checked for disallowed cohort identifiers, private paths/content, forbidden payloads, and other configured leaks. The archive still requires its own identity/integrity verification. |

---

## Failure / status codes

Current `package_status.json` uses MAMEY_COMPLETE, RECOVERY_VALIDATED, RECOVERY_NEEDED and
PARTIAL_FAILED. Package recovery status, terminal run status, scan/channel state and historical
work-order failure codes are different dimensions; copy the producer's actual code rather than
normalizing every condition to the mixed historical vocabulary below. DEFERRED is a work decision,
not an engine completion status.

| Code | Meaning |
|---|---|
| `INPUT_MISSING` | Required input file not present |
| `MAMEY_FAILED` | Deterministic scan failed; reason required |
| `UNSUPPORTED_ACCESSION_MODE` | Accession-only run requested; must supply antiSMASH ZIP |
| `ANTISMASH_PARSE_FAILED` | antiSMASH output could not be parsed |
| `WORKBOOK_SCHEMA_CONFLICT` | Workbook columns do not match required schema |
| `PACKAGE_QA_FAILED` | Package manifest, checksums, or required files missing |
| `RECOVERY_NEEDED` | Partial output exists; exact recovery inputs listed |
| `DEFERRED` | Item intentionally deferred; reason and completion path required |
| `MAMEY_COMPLETE` | Package passed all deterministic extraction/handoff gates for its recorded inputs; Sapote judgment, acceptance, release, and publication remain separate |

---

## Plain-language terms (overloaded everyday words)

These familiar words have specific meanings in the bundle.

### Names

| Name | What it means here |
|---|---|
| Mamey | The deterministic engine: the Python layer that parses antiSMASH output and extracts the BGC inventory. It does no biological interpretation. |
| Sapote | The judgment layer: interprets Mamey's output and writes the claim-safe reports. Mamey + Sapote together = the bundle. |
| Bert / Davey / Eden | Retired internal mode names. Now "Verified Literature Deep Dive," "Rapid Literature Deep Dive," and the summary-table workflow. Kept here only because the old names may still appear in some files. |

### Overloaded common words

| Word | What it means in Sapote–Mamey |
|---|---|
| Gate | A bounded validation checkpoint. Its name and receipt say what it checked. |
| Cassette | A reusable biosynthetic logic pattern in the registry, used for marker-aware scoring. |
| Marker | A literature-backed diagnostic signature that flags a specific biosynthetic capability. |
| Arm | A glycosylation arm: sugar-tailoring genes sitting outside the core BGC boundary. Reported as evidence, not proof of physical linkage. |
| Scan | One detection-module pass (CCTT, CGAD, EFLS, etc.). Each BGC carries "scan states." |
| Sweep | A scoring pass across a whole reference database. The KCB sweep scores every BGC against MIBiG. |
| Triage | Ranking BGCs by promise. The "triage board" is the ranked output. |
| Board | A results table: Lead Board, Hive Board, Triage Board. |
| Lead | A prioritized BGC candidate worth pursuing. Raising lead priority never raises claim confidence. |
| Kernel | The Slim Judgment Kernel, an older condensed instruction file for Sapote, replaced by the execution slice and AGENTS.md. |
| Monolith | A large reference/controller document used only when selected.  See ASSISTANT_GOVERNANCE.md. |
| Manifest | Two senses: the `manifest.json` handoff object Mamey emits, and the release manifest listing shipped files. |
| Ledger | The append-only audit log of findings. |
| Freeze | A locked baseline that must not drift: schema freeze, frozen release candidate, freeze-triage. |
| Constellation | An evidence constellation: a set of co-occurring signals reported together instead of as one over-claim. |
| Edge | A contig edge: where a BGC is cut off at the end of a contig, so it may be truncated or incomplete. |
| Flank | A region next to a feature or boundary. The relevant scan defines its coordinate distance; EFLS currently compares shared labels and does not match raw contig-end sequence or prove the other half of a pathway. |
| Warhead | The reactive chemical group that gives a compound its bioactivity (e.g. a β-lactone electrophile). |
| Rescue | A candidate inference that relates fragments split across contigs. FLBR finds fragments and RG-GMCI/related tools propose linkage; they do not reassemble or physically join the contigs. |
| Census | FLBR's tally of fragmented megasynthase sets across contigs. |
| Banked / Bank | The stored cross-session cohort state (`cohort/`) that the master workbook is built from. |
| Handoff | The structured transfer of data from Mamey to Sapote (and between the execution and judgment layers). |
| Trap | A hallucination trap: a deliberate check on every BGC to catch over-interpretation of generic domains. |
| Card | A structured per-item write-up: a Mode B card per BGC, or an A5 fermentation card. |
| Corrected | The assembly-quality-adjusted BGC count (vs. the raw antiSMASH region count). |
| Tier | A named band whose meaning depends on the field: evidence tier, Mamey routing tier, privacy tier, or release tier. Never compare two "tiers" until their namespace is clear. |
| Atlas | The interactive BGC Atlas HTML tool. |
| Hub | The master Hub workbook that integrates every workstream. |
| Register | A structured ledger such as a missingness, judgment, or output register. A missingness row records a workflow observation, not proof of biological absence. |
| Contract | The current named specification for the selected output/profile and its evidence requirements. It defines coverage and checks within the selected task. |
| Anchor | A publicly reproducible reference point (KCB anchor, calibration anchor) that grounds a threshold. |
| Floor | A minimum applied at a named scoring stage. The diagnostic floor is conditional, and later guards may lower the final tier; read the actual producer and rule order. |
| Ceiling | A maximum a claim cannot exceed. The claim ceiling caps how confident a statement is allowed to be. |
| Band | A prevalence bracket (e.g. core / common / rare) used to judge whether a class is informative for comparison. |
| Proximity | The proximity rule: a resistance marker only counts toward a lead if it sits near the BGC. |
| Snapshot | The Project Memory Snapshot: a captured cross-session state of a strain's analysis. |
| Split | A split pathway: one biosynthetic pathway whose genes are spread across two or more contigs (Split-A / Split-B). |
| Routed out | A class deliberately excluded from a track (e.g. cytotoxic-adjacent classes routed out of the antibacterial lead track). |
| Verdict | A Mode B verdict: the confirm/drop call on whether a candidate is genuine. |
| Profile | A scan profile: the assembled per-BGC summary of all scan results. |
| Pack | A judgment pack or prompt pack: a grouped set of inputs or instructions handed off as one unit. |
| Guard | An audit-finding guard (G1–G6): an automated check that fails the build if a known defect reappears. |
| Trigger | A CCTT trigger: a specific biosynthetic signal (halogenase, lanthipeptide, etc.) that fires a flag. |
| Axis | One independent evidence question, such as structure, similarity, novelty, diagnostics, regulation, or authored judgment. A versioned builder may combine selected axes, but the combination is not a biological truth score. |
| Class | Either a biosynthetic/compound class or a legacy A/B/C lead overlay, depending on context. Neither is the Mamey routing tier, and neither raises the claim ceiling. |
| Dark | KCB-dark: a cluster with no KnownClusterBlast match — unknown, possibly novel, easy to under-rank. |
| Tilde (~) | "Resembles, is not" — the similarity marker before any known-compound name. |

---


## Versioned implementation notes

Use these notes to read older outputs. Check the named current code, registry
or schema before using a formula or threshold from another build.

| Term | Full name | What it means in plain English |
|---|---|---|
| Marker registry | Governed evidence library (`mamey/mamey_markers.py`) | The versioned detection-marker set spanning domain-class, CCTT, regulator, TFBS, maturation, resistance, transporter, chitin/glycan, and fragment-rescue libraries. Each marker has a stable ID, evidence tier, and claim ceiling. Query the current registry for its count; do not copy an older fixed total. |
| CCTT / T43 | Class-trigger framework | The versioned T43 trigger set in `mamey/source_scans.py::CCTT_PATTERNS`. When a class-defining trigger is corroborated on a compatible locus it may drive the current diagnostic bonus and Medium floor; tailoring-only/promiscuous triggers do not receive that floor by themselves. Query the current registry for families and weights. |
| Standing-rule downgrade | Workflow-scoped routing/display consequence | Apply only a current rule's explicit action and scope. NAPAA is neutral; the hglE-KS/PREV-001 registry record is informational, while the scorer separately applies its conditional hglE-product/no-CCTT standing-rule guard. Genome-class displays park saccharide only, while genus/BiG-SCAPE family comparisons keep their separately selected wider policy. Preserve full product tokens, counts and provenance for audit. |
| RiQ | Reference-information quotient | A selected JSON-derived reference signal whose source/channel and region binding must remain explicit. In the current scorer, an admitted nonmissing value below 0.5 adds 10 to the novelty routing prior before other handling; it is not measured chemical novelty. The bounded walker keeps RiQ separate from its auxiliary leaf budget, but RiQ still has group caps, authority limits, source-conflict and unmapped/held states. “Exempt from the record cap” does not mean unlimited or complete. |
| RG-GMCI | Reference-Guided Genome Mining Candidate Inference | Homology-guided shared-reference linkage across contigs — proposes two fragments on different contigs are one split pathway when they share MIBiG references. **Does not join contigs at the nucleotide level.** Its bonus (HIGH +8 / MODERATE +4) is routing priority, not claim confidence; promiscuous-hub and distant-reference pairs are down-weighted. |
| Edge penalty | (removed v9.7.84) | A score deduction for BGCs on a contig edge, **removed in v9.7.84**. It had no measurement basis (edge BGCs show no truncation signature in their base score) and was burying overlooked edge fragments at the tier threshold. Truncation is now carried as a confidence grade (architecture C/D), not a score deduction. The corrected-count weight (Interior 1.0 / Edge 0.5 / Full-contig 0.25) is separate and unchanged. |
| Judgment store / register | Mode B persistence layer | The per-package store (`<strain>_judgment_register.json` + `judgment/*_mode_b.md`) that holds Sapote's Mode B cards durably.  |
| Mode B receipt | `mode_b_receipt.json` | The JSON a Sapote session emits at the end of a Mode B batch (`{strain_id, session_id, cards:[{bgc_id, mode_b_md, …}]}`). `python mamey_run.py ingest-receipts` consumes it to persist the cards into the judgment store and reconcile the workbook's E1 sheet. Fail-closed (unknown BGC skipped, never invented) and idempotent. |
| `doctor` / `inspect` / `explain` / `list-bgcs` | Environment, intake and package inspection | `doctor` checks the environment. `inspect <antiSMASH.zip>` previews raw antiSMASH ZIP intake before a run. `explain <package_dir>` summarizes an existing result package. `list-bgcs <package_dir>` prints its BGC inventory (optionally `--json`). These operations do not rerun extraction. From the bound bundle root, use `python mamey_run.py` before the command. |

### RG-GMCI rescue layer

*These five terms are the new fields you will see on the 4A ranked-pairs output and in Mode B cards. All remain candidate inference — none joins contigs at the nucleotide level*.

| Term | Full name | What it means in plain English |
|---|---|---|
| db_kind / CB–KCB separation | ClusterBlast database-of-origin tag | Each shared-reference hit is now tagged by which antiSMASH file it came from. That file is **knownclusterblast** (a characterized MIBiG cluster — tells you the likely product class), **clusterblast** (a cross-genome GenBank neighbor — tells you two fragments co-occur in real genomes), or **subclusterblast** (sub-operon hits — *excluded* from rescue geometry). Earlier code blind-merged all three because the word "clusterblast" is a substring of all of them; separating them is what surfaces clusterblast-only rescues a KCB-only path would miss. |
| rescue_evidence_base | Which databases corroborate a pair | Per rescued pair, records whether the linkage is supported by **BOTH_KCB_AND_CB** (strongest), **CLUSTERBLAST_ONLY** or **KNOWNCLUSTERBLAST_ONLY**. **CLUSTERBLAST_ONLY** means real genome neighbors but no characterized match — the common case for novel clusters. **KNOWNCLUSTERBLAST_ONLY** means characterized-cluster identity without cross-genome corroboration. Observational; it does not by itself change the score. |
| functional_rescue_class | Gene-role complementarity of the two fragments | Compares the biosynthetic gene roles (core / tailoring / transport / regulatory) on each fragment using **core-fraction asymmetry**. The classes are **COMPLEMENTARY** (one fragment carries the core, the other the accessory genes — what a real split looks like), **BOTH_CORE** (both carry a near-complete core → paralogous clusters, *not* a split), or **ACCESSORY_ONLY** (two accessory fragments; weak). A cross-check on the subject-tiling verdict, not a standalone call. |
| subject-tiling verdict | Disjoint-vs-shared reference subject genes | Reads which genes of a shared reference cluster each fragment hits. The verdict is **COMPLEMENTARY_SPLIT** (disjoint subject genes = two halves of one cluster), **OVERLAPPING_PARALOG** (shared subject genes = independent paralogous clusters), or MIXED/INSUFFICIENT. Gated to avoid calling every low-signal pair a split. |
| Terminus-truncation rescue / TERMINUS_TRUNCATION_SPLIT | Coordinate-confirmed split at a contig break | The simplest, most certain rescue: an **Edge** region whose boundary sits *at* the contig terminus is a cluster sliced by the assembly break. When paired with a small (≤25 kb) complete-contig "severed arm" or a shared *specific* biosynthetic class, it is flagged TERMINUS_TRUNCATION_SPLIT and **overrides** an OVERLAPPING_PARALOG verdict that rests on a gene class which is legitimately multi-copy *within one* cluster (e.g. the bottromycin RRE/methyltransferase). The paralog call is preserved for genuine paralogs. Produces candidates, not confirmed joins — a small contig can be the severed arm of only one cluster, so where it pairs with several Edge regions the evidence base + functional class disambiguate; physical confirmation still needs long-read / gap-PCR. |


### RG-GMCI read depth and residue tiling

*Both are report-only: they add fields to the ranked pairs and change no score or confidence*.

| Term | Full name | What it means in plain English |
|---|---|---|
| depth_flag | Read-depth agreement of a pair's two contigs | Each ranked pair carries `depth_a`, `depth_b` and `depth_ratio` (the lower read depth over the higher). These are read from SPAdes contig names (`_cov_<x>`). **DEPTH_CONSISTENT**: the ratio is 0.67 or more. **DEPTH_MISMATCH**: the ratio is below 0.67, so the two contigs may come from different replicons or copies; plasmids and repeats can differ for good reasons. **DEPTH_UNAVAILABLE**: a contig name has no `_cov_` value, as with other assemblers. |
| residue tiling verdict | Which stretch of each shared MIBiG protein each fragment covers | An optional DIAMOND check, run with `python mamey_run.py run --rggmci-diamond-db <db>` or `run_rggmci(..., diamond_db=...)`. It places each fragment's proteins on the reference proteins the two fragments share, using each residue once. **COMPLEMENTARY_RESIDUES**: the two sides cover different parts, as a gene broken across contigs would. **OVERLAPPING_RESIDUES**: they cover the same parts, as paralogs or copies would. **MIXED_RESIDUES**, **THIN_RESIDUES** and **NO_SHARED_MIBIG_REFERENCE** say what their names say; **NOT_TESTED** means DIAMOND or the database was missing. By default only the pairs the paralog gate demoted are tested. |

---

*Maintenance note: this glossary is the reader-facing canonical source for term
definitions. When a new scan, code, or overloaded term enters the bundle, add
or revise the definition here and point other documents here. Keep counts,
formulas, and status enumerations tied to their code/schema source and keep
claim-safe framing in every definition.*

*Maintenance note: version-sync marker for the installed engine 1.9.177.*

---

### Historical additions from v9.7.141–v9.7.147

| Term | Full name | What it means in plain English |
|---|---|---|
| Ranthipeptide | Radical SAM RiPP subclass | A ribosomally synthesized and post-translationally modified peptide (RiPP) associated with radical-SAM maturation, a recognition element, and a precursor peptide. Additional tailoring can diversify the predicted scaffold. A specific locus still requires the complete exact-locus identity and gene-level evidence; class membership alone is not product identity. |
| §28 — Evidence provenance ledger | Mode B card section 28 within the current §1–§48 profile | A per-claim table recording the factual claim, evidence tier, source file or field, engine version, confidence, and update trigger. It supports surgical revision but does not itself validate the claim. |
| §30 — Experimental decision tree | Mode B card section 30 within the current §1–§48 profile | A structured set of unresolved questions, resolution experiments, expected card changes, and downstream consequences. It turns a card into a research plan without implying that any experiment has been performed. |
| ChatGPT Execution Slice | `docs/CHATGPT_EXECUTION_SLICE_v97147.md` | The default ChatGPT/Sapote execution controller as of v9.7.147. Replaces `SAPOTE_SLIM_JUDGMENT_KERNEL.md` in all default load paths. Contains full-depth, non-abbreviated rules: no scope-negotiation, no abbreviated Mode B, edge/FC equality enforced, §28/§30 required, post-MAMEY_COMPLETE handback mandatory. |
| POOR-tier edge equality | Edge/FC equal-visibility rule (v9.7.147) | In POOR or VERY_POOR assemblies (< 45% interior BGCs), the interior/edge/full-contig distinction is primarily an assembly artifact, not a scientific signal. All BGCs appear in the triage board sorted by corrected_rank (score), not Interior-first. Edge/FC BGCs receive full Mode B depth; boundary status appears as a caveat in §3 and §19 only, not as a reason for abbreviated treatment. The Wet Lab Matrix edge/FC −2 penalty is also suppressed for POOR/VERY_POOR assemblies. |
| Mamey-first gate | Workflow enforcement rule (v9.7.146) | A rule in AGENTS.md and the ChatGPT Execution Slice: Mode B, DAPR, triage, or any Sapote interpretation is refused without a sealed Mamey package. The package provides correct boundary computation (flanking-buffer analysis, not just the raw contig_edge flag), WL/AB/AF scores, CCTT triggers, and cluster-level KCB that cannot be reproduced from raw antiSMASH output. Offline analysis (explicitly requested) is permitted with an explicit flag on every fact that would change with a Mamey run. |
| Deliverable Menu | `docs/DELIVERABLE_MENU.md` | A diner-menu-format document listing all deliverables the pipeline can produce, grouped by audience (quick orders, full meals, sides, specials). Each item has a plain-language description and a trigger phrase. Presented at MAMEY_COMPLETE. Replaces the technical deliverable list in SESSION_START_MANIFEST as the user-facing entry point. |
| verify_checksums | Package integrity function (v9.7.145c) | A function in `mamey/validate.py` that recomputes SHA256 for every line in `checksums_sha256.txt` and returns a list of errors. Mutable post-seal files (`run_phase_receipts.jsonl`, `package_status.json`) are excluded from the check because they are appended after checksum generation by design. Now wired into `validate_package()` — a corrupted non-mutable file causes `status: FAIL`. |
| PATCH-PACKAGING-SEAL | Checksum ordering fix (v9.7.146) | The fix to `mamey/packaging.py` that corrects the root cause of recurring checksum failures. `write_manifest()` now excludes mutable post-seal files from the checksum set *before* hashing, so `checksums_sha256.txt` is always self-consistent at the moment of writing. Prior to v9.7.146, receipts appended after the checksum was computed caused mutable-file mismatch on every `sha256sum -c` run. |
| Interpretive floor | Per-section minimum depth (v9.7.146) | The minimum reasoning requirement for Mode B sections §5, §9, §11, §12, and §19, defined in `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md`. §5 must connect domain architecture to structural consequences. §9 must weigh alternatives with evidence. §11 must connect tailoring complement to scaffold complexity. §12 must name the ecological mechanism with a literature anchor. §19 must argue the verdict, not restate §11. |
| ENGINE_LINEAGE.md | Engine version governance document (v9.7.145) | `docs/ENGINE_LINEAGE.md` records every engine version bump with: old/new engine, first bundle carrying the new engine, reason for bump, whether scoring semantics changed, and tests run. `sync_version.py --check` exits non-zero if the current engine version has no entry here. Motivated by the undocumented 1.9.99→1.9.100 bump at v9.7.142. |
| TRIGGER_ROUTING.md | Canonical trigger routing table (v9.7.145) | `docs/TRIGGER_ROUTING.md` is the single authoritative table for what happens when any named trigger fires (workflow triggers, quality-gate triggers, biology-escalation triggers, routing conflict guards). Previously the routing was scattered across multiple prompt documents. All future trigger definitions go here first. |

*Historical note: the rows above entered during the named version window.
Their current definitions and gates remain controlled by the present code and
schema, not by the historical introduction label*.

## Setup, clustering and phylogeny terms

| Term | Meaning and boundary |
|---|---|
| Pfam | A reference collection of protein-family profile HMMs used in domain annotation. Full Pfam and a scanner-specific HMM panel have different roles; provide the panel required by the consuming tool. See [external assets](EXTERNAL_ASSETS_GUIDE.md). |
| HMM / pressed HMM | A hidden Markov model represents a sequence-family profile. A pressed HMM database has HMMER companion index files (`.h3f`, `.h3i`, `.h3m`, `.h3p`) used by the relevant scanner; the source model file alone may not satisfy its prerequisites. See [BiG-SCAPE preparation](BIGSCAPE_GCF_WORKFLOW.md). |
| GCF | Gene cluster family: a grouping of BGCs under the selected similarity/clustering settings. Family membership or singleton status does not prove a common compound, activity or novel chemistry; fragmentation and input scope affect the comparison. See [BiG-SCAPE workflow](BIGSCAPE_GCF_WORKFLOW.md). |
| MLSA | Multilocus sequence analysis: phylogenetic comparison using an explicitly selected panel of sequence loci. The bundled five-protein-coding-locus driver is separate from its 16S extraction route; record loci, alignment and tree method rather than assuming every MLSA panel is identical. See [phylogenomics](phylogenomics.md). |
| 16S | The small-subunit ribosomal RNA marker used by the 16S routing/placement workflows. A 16S similarity or placement is sequence context, not an ANI measurement, compound call or automatic species assignment. See [phylogenetic autopilot](PHYLO_AUTOPILOT_WORKFLOW.md). |
| LWR | Likelihood-weight ratio in a phylogenetic placement result: relative support for candidate attachment edges under the selected reference alignment/tree and model. It is not a probability that an isolate belongs to a species. See [placement workflow](PHYLO_PLACEMENT_WORKFLOW.md). |
| Pendant length | The branch length joining a query tip to its placement attachment. Interpret it with the selected alignment/model and placement output; it is not percent identity or a species threshold. See [placement workflow](PHYLO_PLACEMENT_WORKFLOW.md). |
| Wheelhouse | A local collection of Python distribution wheels for the selected installation. It must cover the target platform, Python ABI, build requirements and chosen extras; possession of some wheels does not prove a complete offline install. See [installation](INSTALL.md). |
| Virtual environment | An isolated Python interpreter/package environment. Use the same environment for bundle installation and commands, and bind the actual bundle root; isolation alone does not identify which bundle a console launcher resolves. See [prerequisites](PREREQUISITES.md). |

