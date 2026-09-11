# Volume X — A Complete Genome: *Streptomyces spectabilis* ATCC 27465

> **Currency scope:** This volume retains its historical edition and review stamps. Only the checks listed in the [currency record](Encyclopedia-Currency.md) have been refreshed for the current candidate. Other constants, numerical claims, literature interpretations, and worked-run results have not been comprehensively revalidated. A newer bundle does not make those older observations current.

Every earlier volume describes the pipeline in the abstract — what the engine does, how each scan works, what the scoring model measures. This volume describes what all of it looks like when run on a real, publicly available, fully closed genome from a well-studied organism. *Streptomyces spectabilis* ATCC 27465 is an ideal teaching case: the complete chromosome is publicly deposited (CP023690.1, GenBank accession GCA_008704795.1), it is the type strain for the species, and one of its biosynthetic clusters produces the compound the species is literally named after. There is no ambiguity about what is public, and there is a direct, literature-traceable link between a specific cluster and a named compound. The analysis documented here was performed using Mamey v1.9.81 against antiSMASH 8.0.4 output. All numbers are observed; nothing is imputed. *Re-grounded to v9.7.91 (2026-06-20):* this worked run predates the current bundle — it was cut at Mamey 1.9.81 / bundle v9.7.74. Re-reviewed against the v9.7.91 engine, the structural framework it exercises is unchanged: the ten-scan roster (§X.6), the fifteen-family CCTT set, the `[E-signal]` doctrine, the saccharide standing-rule exclusion, and the corrected-count formula all behave identically at v9.7.91. What is **version-pinned** is the scoring: the AB/AF lead tiers and ranks below are the observed 1.9.81 values, and they predate the scoring-boundary changes that stacked across engine 1.9.84→1.9.87. A v9.7.91 re-run would reproduce the same clusters, triggers, and KCB anchors but could shift individual tier/rank numbers, so the §X.8 calibration expectations should be re-baselined against a fresh v9.7.91 run before being used as a regression oracle.

## §X.1 · The genome

*Streptomyces spectabilis* is a soil actinobacterium within the family Streptomycetaceae. The ATCC 27465 type strain was originally isolated as the producer of actinospectacin — now better known as spectinomycin — a broad-spectrum aminocyclitol antibiotic used clinically against gonorrhoea and in veterinary medicine. The complete genome sequence was deposited in 2019 (CP023690.1) and spans a single circular chromosome.

| Property          | Value                                               |
|-------------------|-----------------------------------------------------|
| Strain            | *Streptomyces spectabilis* ATCC 27465 (type strain) |
| Accession         | CP023690.1 · GCA_008704795.1                        |
| Chromosome        | Single, complete (closed)                           |
| Genome size       | 9,807,160 bp                                        |
| GC content        | 72.4%                                               |
| N50               | 9,807,160 bp (the whole chromosome)                 |
| antiSMASH version | 8.0.4                                               |
| Mamey version     | 1.9.81 (bundle v9.7.74)                             |
| Mode              | gold                                                |
| Release class     | PUBLIC                                              |

The genome is large even by *Streptomyces* standards: 9.8 megabases, single contig. That single-contig status is the most important fact for the analysis. Every cluster the pipeline sees is an interior cluster — it sits within the chromosome with real sequence on both sides — because there are no contig ends for a region to run off. This means the assembly tier is GOOD by definition, the corrected count equals the raw count, and every claim the pipeline makes about cluster size and completeness is trustworthy.

## §X.2 · Assembly quality and the corrected count

The engine resolves the boundary status of each of the 67 detected clusters as follows:

<table>
<thead>
<tr>
<th>Status</th>
<th>Count</th>
<th>Weight in corrected count</th>
</tr>
</thead>
<tbody>
<tr>
<td>Interior</td>
<td>67</td>
<td>× 1.0</td>
</tr>
<tr>
<td>Edge</td>
<td>0</td>
<td>× 0.5</td>
</tr>
<tr>
<td>Full-contig</td>
<td>0</td>
<td>× 0.25</td>
</tr>
<tr>
<td><strong>Corrected count</strong></td>
<td colspan="2"><strong>67.0</strong></td>
</tr>
</tbody>
</table>

The corrected count equals the raw count. This is the ideal case: a closed chromosome means there is no fragmentation to discount. In the real-world actinomycete cohort most analyses are built on draft genomes assembled into hundreds of contigs; the corrected count is typically 60–75% of the raw count for a MODERATE-tier assembly. Here there is no such penalty. The assembly tier is **GOOD** (interior fraction 100%).

This also means RG-GMCI — the contig-reconstruction module that searches for clusters split across contigs — plays a different role on this genome than on a draft. It still evaluates all pairs (2,120 candidate pairs from 67 clusters), and it identifies 7 HIGH-confidence and 186 MODERATE-confidence pairs as potential split-pathway relationships, but these are not broken-chromosome joins. On a closed genome, a HIGH pair from RG-GMCI is better read as evidence that two adjacent clusters may share biosynthetic logic — a co-pathway signal — rather than as evidence that they are physically one cluster separated by an assembly break. The pipeline does not mechanically fuse them in either case; it proposes pairs with evidence, and the judgment layer reads the evidence with context.

## §X.3 · The BGC landscape

antiSMASH detected 67 biosynthetic regions. After standing-rule exclusions (saccharide-only clusters, which represent primary sugar metabolism and carry no meaningful secondary-metabolite discovery signal) 49 clusters remain on the analytical lead boards. The standing-rule exclusions are not losses: the pipeline removes them from the lead boards but records them in the workbook and inventory so the full antiSMASH call set is never silently discarded.

The class distribution of the 67 raw clusters reflects a typical high-abundance *Streptomyces* chromosome:

| Class (antiSMASH call) | Raw count | Note |
|----|----|----|
| saccharide | 27 | All 18 pure-saccharide clusters excluded from lead boards by standing rule; co-located instances counted here but see §X.5 for saccharide flag policy |
| NRPS / hybrid | 18 | Includes most of the top-ranked leads |
| PKS (T1PKS, T3PKS, transAT) | 11 dominant | Several in hybrid clusters |
| RiPP (lanthipeptide, lassopeptide, CDPS, atropopeptide) | 10 | Multiple lanthipeptide classes represented |
| terpene | 11 | Includes melanin, redox-cofactor precursors |
| other / fatty acid / NRP-metallophore | remainder | Siderophores, beta-lactam, prodigiosin-type |

The NRPS/hybrid dominance is expected for a genome of this size and GC content. Many of the high-ranking leads are heterologous hybrids — clusters that carry both NRPS and PKS modules, a common architecture in large-chromosome *Streptomyces*.

## §X.4 · The anchor cluster: actinospectacin / spectinomycin (BGC057)

BGC057 is the cluster the species is named after. Spectinomycin (also known as actinospectacin) is a broad-spectrum aminocyclitol antibiotic — structurally distinct from the aminoglycosides despite sharing a general mechanism of action (binding to the 30S ribosomal subunit and inhibiting translocation). The pipeline's output on this cluster is worth reading closely as an illustration of how the engine handles a well-characterised, well-deposited reference compound.

| Field | BGC057 / CP023690.1 region057 |
|----|----|
| User label | BGC057 / CP023690.1 region057 |
| Coordinates | 8,578,312–8,686,956 (108 kb) |
| Boundary | Interior |
| Products | NRPS, NRPS-like, PKS, T1PKS, amglyccycl, other, saccharide, terpene, terpene-precursor |
| CCTT triggers | None fired |
| KCB top hit | BGC0000715.5 \| actinospectacin \| KnownClusterBlast rank 1 |
| KCB cumulative score | 61,598 |
| RiQ score | 0.990 (Likely known) |
| Architecture confidence | A |
| AB lead tier | Medium (rank 9 on AB board) |
| AF lead tier | Medium (rank 3 on AF board) |

Several things are worth noting about this output:

**The KCB hit is unambiguous.** A cumulative score of 61,598 with a RiQ of 0.990 is a near-perfect match against the deposited actinospectacin reference cluster (BGC0000715.5 in MIBiG 4.0). The engine does not use this to claim the cluster produces actinospectacin — the standing claim-safety rule is that KCB similarity is similarity, not identity. But the evidence is about as strong as similarity evidence gets.

**No CCTT trigger fired.** This is worth reading carefully, because T43-AMC *is* the aminocyclitol / aminoglycoside family (→ §X.5 corrects an earlier mischaracterisation of it). Its markers are specific — verified key `T43-AMC_aminocyclitol`, tokens `aminocyclitol` / `dois` / `btrc` / `2-deoxy-scyllo-inosose` — and they target the DOIS / 2-deoxy-scyllo-inosose-synthase route of the 2-deoxystreptamine aminoglycosides. BGC057's annotations carry the abbreviated antiSMASH class call `amglyccycl` but not those literal route markers, so the trigger correctly stays silent rather than firing on a class label alone. This is not a failure — it is the corroboration discipline working: a BGC with strong KCB evidence and no corroborating trigger still earns a meaningful score (here the near-perfect actinospectacin anchor carries the call), it just ranks below a cluster with both.

**The saccharide co-annotation is not excluded here.** BGC057 carries both `amglyccycl` and `saccharide` annotations. The pipeline's standing-rule exclusion fires on *pure-saccharide* clusters — those where saccharide is the only non-trivial annotation. BGC057 has substantive NRPS and PKS machinery, so the saccharide co-annotation does not trigger a downgrade. The cluster remains on the lead board, ranked appropriately by its KCB and scoring evidence.

**Medium tier, not Exceptional, reflects the evidence correctly.** Without a CCTT trigger, the score rests on KCB similarity and the amglyccycl class annotation. Both are genuine signals, but neither triggers the +25 diagnostic bonus that elevates the strongest leads. The result — Medium tier — is an honest reading of the evidence available without wet-lab fractionation data tying the bioactivity to this specific cluster.

## §X.5 · Other notable clusters

The genome's biosynthetic richness extends well beyond the name-giving compound. Several clusters illustrate distinct scoring and detection situations worth documenting.

### BGC004 — Lasso peptide megacluster (Exceptional, AB rank 1)

BGC004 occupies 64 kb (coordinates 215,177–279,431) and carries both lasso peptide machinery and large NRPS/transAT-PKS modules — an unusually complex cluster architecture. The T43-LASSO trigger fired, providing corroborating evidence for the lasso peptide class. The KCB top hit (BGC0001645.3, lagmysin) has a high cumulative score (34,899) and a RiQ of 0.903, placing it in the "Likely known" band but below the "perfect match" threshold of the actinospectacin cluster. The combination of trigger corroboration and high KCB score lifts this cluster to Exceptional on the AB board — the pipeline's highest tier. The claim this earns is capacity-level: biosynthetic capacity consistent with a lasso peptide / transAT-PKS hybrid, not a named compound.

### BGC008 — CDPS/lanthipeptide/NRPS (Exceptional, AB rank 2)

BGC008 (56 kb, interior) illustrates a multi-trigger cluster: both T43-DKP (cyclic dipeptide / CDPS) and T43-LAN (lanthipeptide) fired. The KCB top hit is triostin A (BGC0000450.5, RiQ 0.906). Two corroborating triggers from different families, each independently pointing at real enzymatic machinery, is exactly the kind of multi-signal evidence the scoring model rewards. Exceptional tier on AB.

### BGC010 — Enediyne signal (High, AB rank 3)

BGC010 (58 kb, interior) triggers both T43-ENE (enediyne) and T43-LAN (lanthipeptide), with a KCB top hit of calicheamicin (BGC0000033.5, RiQ 0.697). The calicheamicin similarity is at the structural-variant level rather than a near-identical match. The T43-ENE trigger fires on the enediyne polyketide synthase signature, which is the engine's \[E-signal\] — a claim-safety note, not a biosafety flag. The rationale: an enediyne trigger is a genuine class signal and warrants recording, but enediyne-specific biosafety flagging was retired from the engine because selective flagging would give false reassurance across a genome that carries other cytotoxic classes (anthracyclines, indolocarbazoles, ionophores) not similarly flagged. The \[E-signal\] is a marker for the judgment layer to treat the claim carefully, not a recommendation for laboratory handling. Laboratory handling is governed by SOPs that apply uniformly regardless of cluster annotation.

### BGC002 — Beta-lactam signal (Medium)

BGC002 carries the T43-BLA trigger (beta-lactam), the strongest corroborating evidence for beta-lactam biosynthetic capacity. The KCB top hit (valclavam, BGC0001151.5) has a RiQ of 0.656 — in the structural-variant range rather than a clean match. Clavams are atypical beta-lactams biosynthetically, and the combination of T43-BLA corroboration with a divergent KCB suggests capacity consistent with an unusual beta-lactam pathway variant, not necessarily clavulanic acid. Medium tier is the correct reading.

### BGC057 and the aminocyclitol gap in the CCTT framework

The absence of a T43-AMC trigger on BGC057 is worth addressing directly, because a reader who knows spectinomycin's mechanism might expect a signal. **Correction (this edition):** T43-AMC *is* the aminocyclitol / aminoglycoside family — verified key `T43-AMC_aminocyclitol`, markers `aminocyclitol` / `dois` / `btrc` / `2-deoxy-scyllo-inosose` (an earlier draft of this volume wrongly described it as covering aminocoumarins / novobiocin-type compounds; there is no aminocoumarin or novobiocin token anywhere in `CCTT_PATTERNS`). The trigger did *not* fire here because those markers target the DOIS / 2-deoxy-scyllo-inosose-synthase route — the classic 2-deoxystreptamine aminoglycosides, e.g. butirosin's `btrC` — and the spectinomycin cluster's gene/product annotations do not carry those specific tokens; its aminocyclitol core is built by a different biosynthetic route. So the framework correctly reports no trigger and the near-perfect KCB anchor stands on its own. The honest reading is not "aminocyclitols have no trigger family" but "this aminocyclitol's biosynthetic route sits outside T43-AMC's marker set" — a genuine coverage edge worth noting for any future trigger-set work.

## §X.6 · The scan results, ground-truthed

The complete scan states from the EU158805 run gave a minimal scan set (one cluster, one BGC, one nucleoside). The spectabilis run gives the opposite — 67 clusters, strong signals across multiple scan families. Here is what each scan found:

| Scan | Status | Result |
|----|----|----|
| KCB sweep | PASS | 67 regions parsed; 200,000 loose hits (the run saturates the hit-count ceiling — a very large, well-deposited genome) |
| RG-GMCI | PASS | 2,120 pairs evaluated; 7 HIGH, 186 MODERATE. On a closed chromosome all pairs are interior-interior; interpret as co-pathway signal, not assembly reconstruction. |
| FLBR | PASS (WEAK) | MEGASYNTHASE_FRAGMENT_SUSPECT — the census detects large backbone signals but no single clear megasynthase candidate above the strong-evidence threshold. |
| CCTT | PASS | 8 families active: HAL (halogenase, 1 BGC), PHO (phosphonate, 1 BGC), BLA (beta-lactam, 1 BGC), ENE (enediyne, 2 BGCs), LAN (lanthipeptide, 5 BGCs), LASSO (lassopeptide, 2 BGCs), DKP (CDPS, 1 BGC), TET (tetronate/spirotetronate, 3 BGCs). 26 total lanthipeptide hits across 5 clusters — this is the most trigger-active class in the genome. |
| CGAD | NULL | No chitinase or glycan-active domain hits. Not surprising for a soil isolate without confirmed antifungal phenotype — absence is recorded honestly, not used to infer anything about antifungal capacity. |
| UMED | PASS | No maturation gaps flagged. |
| EFLS | NULL | 0 candidate cross-contig pairs — expected on a single-contig closed genome. |
| Resistance | PASS | 50 total resistance hits; 7 T1 (self-protection tier) BGCs. 7 clusters with self-protection evidence is a strong biosynthetic-activity signal — a producer commonly carries immunity genes for its own products. |
| bldA/TTA | PASS | 67 BGCs assessed; 5 T4 (TTA-codon dependent). 5 clusters whose expression is likely gated by bldA (the rare TTA tRNA) — these are probably activated under specific developmental conditions, relevant for fermentation strategy. |
| TFBS | PASS | 279 motif hits across the genome. GBL_AdpA_like:225 — the AdpA global activator dominates, which is typical for large *Streptomyces* chromosomes (AdpA is the master regulator of secondary metabolite production and morphological differentiation). DasR_like:23 (N-acetylglucosamine sensing), BldD_like:13, SARP_BTAD_like:5 (cluster-specific activators on 5 BGCs), IolR_like:6. |

## §X.7 · What a complete genome shows that a draft does not

Comparing the spectabilis analysis to a typical draft-genome run illustrates several properties of the pipeline that are hard to see in isolation.

**Corrected count = raw count.** On a MODERATE-tier draft genome with 60% interior clusters, the corrected count is typically 0.70–0.75× the raw count. Here it is exactly 1.0×. The formula does exactly what it says: on a closed chromosome there is nothing to discount.

**EFLS produces no pairs.** The cross-contig shared-evidence linkage scan exists to detect clusters that are split across contigs and that share evidence (e.g. both hit the same reference, or both carry the same marker). On a single-contig genome there are no cross-contig signals by definition. EFLS returning NULL here is correct and expected — it is not a failure of the scan but a feature of the input.

**RG-GMCI runs but interprets differently.** On a draft genome, a HIGH RG-GMCI pair is a proposal that two edge clusters on different contigs are halves of one cluster. On a closed chromosome, the same score is better read as a co-pathway proposal — two clusters that are probably related biosynthetically but are not separated by an assembly break, since there are no breaks. The engine treats both cases the same computationally (the proposal is evidence-weighted, conservative, and never silent); the interpretation difference lives in the judgment layer.

**The standing-rule exclusion rate is high.** 18 of 67 clusters (27%) were excluded by the saccharide standing rule. This is higher than typical for NRPS-rich actinomycetes (usually 15–20%) and reflects the large number of saccharide-tailoring genes in this particular genome — a common feature of organisms with complex glycoside chemistry. The exclusions are correct: saccharide-only clusters do not carry independent secondary-metabolite biosynthetic signals, and including them would inflate the lead count without adding information. They remain in the workbook inventory.

**The resistance screen found 50 hits across 7 T1 BGCs.** Seven clusters with self-protection evidence in a 67-cluster genome is a relatively high density (about 10%). This is consistent with a biosynthetically active strain that produces multiple compounds with mechanisms of action that require self-protection genes. It also illustrates why the resistance scan is run first (before scoring): self-protection tier influences the floor calculation.

## §X.8 · Using spectabilis as a calibration reference

*Streptomyces spectabilis* ATCC 27465 has several properties that make it useful as a pipeline calibration reference beyond its role as a teaching case.

**Ground truth exists.** The spectinomycin biosynthetic gene cluster is well-characterized in the literature and deposited in MIBiG (BGC0000715.5). The pipeline should rank BGC057 in the AB Medium tier with a near-perfect RiQ score for a correctly configured run. *(The RiQ — a near-identity KCB match — is engine-version-stable; the exact AB tier is pinned to the 1.9.81 run here and should be re-baselined against a v9.7.91 run before use as a regression oracle, since the 1.9.84→1.9.87 scoring-boundary changes can move a borderline Medium.)* If BGC057 is missing from the boards, the saccharide co-annotation handling may need review. If it appears at Exceptional tier without a new trigger, the scoring calibration may have shifted.

**The assembly is an ideal control.** Because the genome is closed (100% interior, corrected = raw), any run producing non-integer corrected counts or reporting Edge/Full-contig clusters indicates a parsing problem with the accession. This makes spectabilis useful as a smoke test for the boundary-status logic.

**The CCTT trigger set is representative.** With 8 of 15 trigger families firing across the 67 clusters, the run exercises most of the framework. A pipeline update to any trigger family in {HAL, PHO, BLA, ENE, LAN, LASSO, DKP, TET} can be regression-tested against the spectabilis run's expected trigger calls.

The package from this run is available as a public reference in the project's validation infrastructure.

→ Volume II for the engine that produced these numbers. → Volume IV for each scan. → Volume V for the scoring model. → Volume VII for release and provenance. → §VIII.5 for the version history that includes the engine version (1.9.81) used here.

</div>

<div id="vol-xi" class="section vol">
