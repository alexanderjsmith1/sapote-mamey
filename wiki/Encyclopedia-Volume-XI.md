# Volume XI — Both Layers Together: *Streptomyces* sp. M56

Volume X showed what the Mamey extraction layer produces on a complete genome: assembly stats, scan tables, lead board rankings. This volume shows what happens when the Sapote judgment layer runs on top of that output. The subject is *Streptomyces* sp. M56 (GCF_002812405.1), a soil isolate with a single complete chromosome and 51 detected biosynthetic regions. Unlike the spectabilis case in Volume X — where the compound the species is named after was the KCB anchor — M56 produces no named compound with a clean literature trail. It is a discovery-mode strain: rich biosynthetic capacity, substantial novelty signals, and interpretation that requires genuine judgment.

This volume is structured as a teaching document around the judgment process. It does not reproduce all 51 Mode B cards; it illustrates the key decision types that came up and why the engine and the judgment layer diverged on several of them.

## §XI.1 · The genome and the run

| Property                      | Value                           |
|-------------------------------|---------------------------------|
| Strain                        | *Streptomyces* sp. M56          |
| Accession                     | GCF_002812405.1 · NZ_CP025018.1 |
| Chromosome                    | Single, complete (closed)       |
| Genome size                   | 11,742,376 bp                   |
| GC content                    | 71.0%                           |
| Mamey mode                    | standard                        |
| Release class                 | PUBLIC                          |
| Raw BGCs                      | 51                              |
| Interior / Edge / Full-contig | 50 / 1 / 0                      |
| Corrected count               | 50.5 (= 50 × 1.0 + 1 × 0.5)     |
| Assembly tier                 | GOOD (98% interior)             |

One BGC sits at the 5' chromosome terminus (BGC001, Edge, 36.8 kb, NRPS fragment). Its corrected weight is 0.5, and the judgment treats it differently from the 50 interior BGCs: no product class can be fully assigned from a truncated assembly-line fragment.

## §XI.2 · The tier distribution and what it tells you

After all standing-rule exclusions and primary-metabolism drops, the 51 raw BGCs distribute as: 1 Exceptional · 2 High · 13 Medium · 35 Inventory. Two BGCs are dropped entirely (BGC002 and BGC017, both primary-metabolism terpene-precursor pathways). Two are downgraded by standing rules: BGC044 (hglE-KS-PREV-001) and BGC049 (NAPAA).

The 13 Medium-tier clusters represent the core analytical workload. None of them was elevated by a CCTT trigger alone — in most cases, T1 self-protection resistance, an anomalous co-annotation, or a structural novelty signal (low RiQ with substantial cluster size) contributed to the tier. The key insight from the M56 run is that Medium tier in a 51-BGC GOOD-assembly genome is a meaningful signal: it means the cluster passed at least one non-trivial filter beyond simple text-keyword scoring.

## §XI.3 · The Exceptional lead: BGC047

BGC047 (75 kb, 10,498,357–10,573,363 bp, Interior, Arch A) is the most architecturally complex cluster in the genome. Its product annotation carries five distinct biosynthetic classes: NRPS, PKS, RiPP, T1PKS, lanthipeptide-class-II, and terpene. Two CCTT triggers fired: T43-LAN (lanthipeptide, confirmed LanM class-II modification enzymes) and T43-TET (tetronate/spirotetronate biosynthetic enzyme). AB=96 (highest in genome). KCB top hit: misaugamycin A/B (BGC0002638.3), 2 proteins, KCB=1,254 — very low score.

The low KCB score requires explanation. A 75 kb multi-class cluster cannot be captured by any single MIBiG reference, because no deposited cluster combines all five of these classes. The NRPS subunit alone hits misaugamycin (a small dipeptide antibiotic); the PKS, RiPP, lanthipeptide, and terpene components have no single-entry match. This is exactly the scenario the engine's multi-class architecture guard was built to handle: rather than reporting "small NRPS peptide" based on the one subunit it can match, it routes to "complex multi-class hybrid (lanthipeptide-class-ii/nrps/pks/ripp/t1pks/terpene)" — a capacity label that captures the genuine complexity without overclaiming a specific product identity.

The diagnostic signal the judgment layer treats as the novelty anchor is the combination of Class II lanthipeptide modification (T43-LAN, LanM enzymes) with tetronate biosynthesis (T43-TET). Lanthipeptides and tetronates co-occurring in a single locus is not a documented combination in MIBiG 4.0. The low RiQ (0.836) is consistent with this: the cluster is partially novel by reference-library standards, specifically in the combination of modification systems. AB=96 reflects the combined scoring weight of multiple corroborated trigger families plus high-scoring class keywords; it is not traceable to any single compound.

Claim-safe capacity statement: biosynthetic capacity consistent with a complex multi-class hybrid megacluster encoding a product or suite of products incorporating NRPS peptide backbone, Type I PKS extension, Class II lanthipeptide modification, tetronate-forming enzyme, and terpene accessory elements. This cluster warrants highest isolation priority.

## §XI.4 · The two High leads: BGC031 and BGC050

**BGC031** (185 kb, 7,086,446–7,271,689 bp, Interior) carries the highest KCB score in the genome: 335,397 against desulfoclethramycin/clethramycin (BGC0002498.3, 23 proteins). Desulfoclethramycin is a 26-membered polyene macrolide with antifungal activity. Alongside the PKS machinery, BGC031 also carries a Class I lanthipeptide biosynthetic module (T43-LAN, lanthipeptide-class-i annotation). The composite architecture — large macrolide PKS co-resident with a lanthipeptide system — is unusual. RiQ=0.762 (possibly novel despite the high KCB score) reflects this: the desulfoclethramycin reference accounts for the PKS component but not the lanthipeptide. The cluster is TTA-codon gated (T4 tier), suggesting conditional expression requiring bldA. AB=84.

This illustrates a recurring pattern in large hybrid clusters: the KCB score can be very high (strong evidence for the macrolide component) while RiQ remains moderate (the total architecture diverges from the reference because the reference doesn't encode the co-resident RiPP). The correct interpretation is that structural novelty is possible in the lanthipeptide component specifically, even though the macrolide backbone is well-characterised by similarity.

**BGC050** (203 kb, 11,203,964–11,407,643 bp, Interior) is the largest cluster in the genome. KCB top hit: bafilomycin B1 (BGC0000028.5, 10 proteins, KCB=160,481). Bafilomycin B1 is a macrolide V-ATPase inhibitor with potent antifungal activity — the mechanism of action explains AF=77, the highest antifungal score in the genome. Two CCTT triggers fired: T43-NUC (nucleoside biosynthesis enzyme) and T43-TET (tetronate, same genome-wide signal appearing in BGC036, BGC038, and BGC047). The T3PKS annotation within a large T1PKS cluster is architecturally unusual. RiQ=0.858 (likely known, but with meaningful divergence from the bafilomycin reference). Primary antifungal lead for this genome.

## §XI.5 · The arch_capacity bug and its fix: BGC040 and BGC047

Two M56 clusters exposed a routing error in the architecture classification engine that was corrected in v9.7.58. This section documents it because it illustrates how the extraction layer and judgment layer interact when the engine produces an incorrect intermediate result.

**BGC040** (21 kb, pure terpene product annotation) was assigned arch_capacity = "small NRPS peptide (β-lactam / nucleoside-peptide / siderophore class)". The root cause: one condensation domain from a boundary gene fell within the BGC coordinate window, making the domain counter report nrps_c=1. The terpene guard in classify_architecture() required nrps_c==0; with nrps_c=1 it fell through to the NRPS-dominant branch. The Sapote judgment layer correctly overrode this to "sesquiterpene / diterpene class" based on the product annotation. The fix (v9.7.58) adds a terpene-only product guard that fires when terpene is the only non-noise product and pks_ks==0, regardless of minor domain noise from boundary genes.

**BGC047** (75 kb, five distinct biosynthetic classes) received arch_capacity = "small NRPS peptide" because the NRPS-dominant branch fired on nrps_c=2 before any multi-class check existed. The fix adds a multi-class guard (position 0, before all class-specific routing) that routes to "complex multi-class hybrid (classes)" when ≥3 real biosynthetic product classes are present. The glycopeptide compound class (teicoplanin-type, which has NRPS+PKS+T3PKS = 3 classes) required a pre-check to avoid regression — the glycopeptide specific branch runs before the generic multi-class guard.

The pattern here matters beyond these two BGCs: the judgment layer should always read arch_capacity critically on multi-class or terpene clusters from runs prior to v9.7.58, and override with the product annotation when the two disagree.

## §XI.6 · Standing-rule flags: BGC044 and BGC049

Two clusters required mandatory Inventory downgrades under standing project rules, and their analysis illustrates why the flag traceability matters.

**BGC044** (126 kb, Interior, KCB=126,409 against hexacosalactone A, 42 proteins — highest protein count in the genome) carries the hglE-KS domain, triggering the hglE-KS-PREV-001 standing rule. Hexacosalactone-class glycolipid PKS clusters are habitat-non-specific and are not meaningful comparative or ecological signals. Structural novelty of the hexacosalactone class per se is acknowledged but the cluster is excluded from priority lead boards. The high KCB (42 proteins, RiQ=0.920) makes this a near-certain hexacosalactone — not a case where the rule strips genuine novelty from an unknown compound.

**BGC049** (34 kb, NAPAA+NRPS) carries the NAPAA annotation, triggering the NAPAA standing exclusion (Nosema hypothesis retired; NAPAA is convergent, ubiquitous, not a meaningful ecological signal). The nocathiacin KCB hit (2 proteins, KCB=313) is a class-mismatch misanchor and should be disregarded.

A v9.7.58 fix (Audit Flag A) resolved a traceability gap: both clusters were correctly placed in Inventory but the Standing_rule field in the triage board CSV was blank. The root cause was that the registry classified NAPAA and hglE-KS as non-blocking (action=none/flag), causing standing_rule_for() to return "" even for clusters that should be downgraded. The fix directly detects these product annotations in the scoring block and sets the flag explicitly, independent of the registry classification.

## §XI.7 · Key scan findings

Several scan results from M56 are worth recording explicitly as reference data for the judgment layer.

**FLBR: STRONG (LMPKS_FRAGMENT_SET).** The large modular PKS architecture census found a confirmed large-backbone fragment set — expected given BGC010 (138 kb azalomycin-class), BGC011 (173 kb nigericin-class), BGC031 (185 kb desulfoclethramycin-class), and BGC050 (203 kb bafilomycin-class). The LMPKS_FRAGMENT_SET verdict means the genome carries credibly large modular PKS machinery, and fragment-ceiling reasoning applies: individual KS domain counts within a fragment may understate the full pathway.

**CGAD: active (chitinase/glucan-active profile).** GH18 (13 hits), AA10_LPMO (11 hits), CBM_CHITIN (9 hits), GlcNAc (18 hits). This is an active chitinase/glucan-degradation profile. In the T43-NUC context (BGC050 carries T43-NUC), the chitin-active CGAD profile is relevant — the nucleoside-is-antifungal rule is most credible when chitin-active context is present in the genome. The BGC050 T43-NUC hit is consistent with chitin-synthase inhibitor class (nikkomycin/polyoxin-type), though the bafilomycin KCB anchor points at a different mechanism. The judgment layer should hold both possibilities.

**T43-TET recurring across four clusters (BGC036, BGC038, BGC047, BGC050).** The tetronate/spirotetronate enzyme signal appears in four distinct BGCs. In BGC036 and BGC038 (both geldanamycin-class ansamycins), the T43-TET hit is anomalous — geldanamycin does not incorporate a tetronate ring. The judgment layer assessment is that a tetronate biosynthesis gene may reside near these ansamycin clusters and be captured within the antiSMASH boundary, or the two clusters share a flanking tetronate gene region. This should be verified against the GBK coordinate boundaries before interpreting T43-TET as evidence of a genuinely tetronate-modified ansamycin.

**Two thioamide RiPP clusters (BGC024 and BGC030), both T43-THA positive.** Thioamide incorporation (radical SAM-mediated) is a rare and potent modification. BGC024 (22.6 kb, thioamitide RiPP, RiQ=0.535, AB=58) and BGC030 (12.4 kb, RiPP-like, RiQ=0.427, AB=62) are the two Medium-tier thioamide leads. Both warrant precursor peptide analysis to assign class and novelty.

**Two ansamycin clusters (BGC035/macbecin-class and BGC036+BGC038/geldanamycin-class).** Dual ansamycin producing capacity is documented in some *Streptomyces* (e.g. *S. hygroscopicus* ATCC 29253). BGC035 carries an unusual 2-deoxystreptamine co-annotation within the ansamycin PKS boundary — this should be verified against the GBK before inferring a 2dos-modified ansamycin, as it may be a boundary annotation artefact.

## §XI.8 · M56 as a reference case for the pipeline

M56 complements spectabilis as a reference strain for different reasons. Where spectabilis provides ground truth (a named compound, a near-perfect KCB hit, and a fully closed chromosome to verify boundary-status logic), M56 provides coverage of the judgment scenarios the pipeline faces in discovery-mode strains.

Specific properties that make M56 useful as a test case: (1) the multi-class megacluster (BGC047) exercises the arch_capacity multi-class guard introduced in v9.7.58 — any run where BGC047 returns "small NRPS peptide" instead of "complex multi-class hybrid" indicates the guard was not applied; (2) the NAPAA and hglE-KS standing rules exercise the Flag A fix — any run where Standing_rule is blank for BGC044 and BGC049 indicates the direct product-annotation detection is missing; (3) the FLBR STRONG verdict and the four-BGC T43-TET pattern exercise the CCTT co-annotation ambiguity resolution; (4) the 11.74 Mb genome size (larger than spectabilis by 1.9 Mb) tests the pipeline's behaviour on larger inputs, including KCB sweep saturation (200,000 loose hits, capped) and RG-GMCI pair count scaling (848 pairs).

The package from this run is available as a public reference in the project's validation infrastructure alongside the spectabilis run.

→ Volume X for the spectabilis Mamey-only comparison. → Volume II for the extraction engine. → Volume IV for each scan. → Volume V for the scoring model. → §VIII.5 for the version history covering the v9.7.58 fixes documented in §XI.5 and §XI.6.

</div>

<div id="vol-xii" class="section vol">
