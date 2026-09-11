<!-- MODE B exemplar | class: NI-siderophore (desferrioxamine) | strain: S. avermitilis MA-4680 | bgc: BGC042 | node: BA000030.4 region042 | contract: modeb_full30 | public -->

# Mode B — BGC042 (BA000030.4 · region042) — *Streptomyces avermitilis* MA-4680

*Public exemplar — NI-siderophore (desferrioxamine) class. Authored from store-backed antiSMASH + KnownClusterBlast for the finished public genome BA000030.4. §4 is authored to the honest no-live-BLASTp read: the independent per-gene BLASTp channel was not run for this card, so no per-gene BLASTp outcome is asserted; the panel can be run or its hit-table ingested offline later (`mamey ingest-blastp`). Every product statement is capacity language.*

## §1 Identity and node/region
BGC042 sits on contig BA000030.4 · region042 (store-backed, finished single-contig genome) of *Streptomyces avermitilis* MA-4680, spanning roughly 6,369,180–6,398,953 (~29.77 kb), classed by antiSMASH as an NI-siderophore (NRPS-independent siderophore) region with associated "other" tailoring. It is an Interior BGC — both flanks are internal to the contig, so no edge/fragmentation correction applies to its boundaries.

## §2 Why this BGC was selected
It was selected as the public class exemplar for NRPS-independent siderophores because it carries the diagnostic IucA/IucC (NIS synthetase) architecture together with the lysine/ornithine hydroxylase and acyltransferase that define the desferrioxamine (des) route, and because its KnownClusterBlast anchor to the characterised desferrioxamine B/E cluster is unusually strong. That combination makes it a clean teaching case for how a siderophore is called from architecture rather than from a single marker.

## §3 Boundary and assembly status
The region is Interior on a finished genome (accession-level contig BA000030.4, not a SPAdes draft), so assembly-tier penalties and edge corrections do not apply and the gene complement can be read as complete for this locus. The corrected-count contribution is a full Interior 1.0. There is no co-located neighbour within the region call that would suggest a merged or split boundary.

## §4 Gene-by-gene interpretation
This section reads the antiSMASH Pfam/HMMER domain calls together with an independent per-gene BLASTp channel: a three-gene panel (`bgc-blastp-panel`) was run on public NCBI nr via web BLASTp and offline-ingested (`ingest-blastp`; results in `blastp_online/BGC042_online_blastp.csv`). The biosynthetic core is a canonical NRPS-independent siderophore (NIS) set, and BLASTp corroborates the panel calls as similarity, not identity. ctg1_5461 (590 aa, FhuF; IucA_IucC) is the NIS synthetase (the DesD-type condensing enzyme) that assembles the hydroxamate backbone without a thiotemplate NRPS — the diagnostic gene for the class; its top BLASTp hit is an IucA/IucC-family protein (WP_406477488.1, *Streptomyces* sp. NBC_01615) at 90.8% identity over 99.7% query coverage (E=0.0, 1110 bits). ctg1_5462 (183 aa, Acetyltransf_8), the DesC-type acyltransferase that acylates the hydroxylamine to complete each hydroxamate, hits a GNAT-family N-acetyltransferase from *S. avermitilis* (WP_403366190.1) at 96.2% / 100% coverage. ctg1_5471 (196 aa, TetR_N; TetR_C_24), the co-selected regulator, hits a SACE_7040-family (TetR) transcriptional regulator (WP_385261189.1) at 93.3%. All three are high-coverage similarity hits that corroborate the antiSMASH annotation without establishing product identity. The DesB-type hydroxylase ctg1_5463 (423 aa, Lys_Orn_oxgnase — the flavin-dependent lysine/ornithine N-hydroxylase that installs the N-hydroxyl for the hydroxamate ligand) was outside the three-gene panel and is read from domains only. ctg1_5457 (605 aa, GATase_6; SIS; TIGR01135) supplies amino-sugar/glutamine-amidotransferase support consistent with precursor supply; ctg1_5456 (Gpr1_Fun34_YaaH) and the flanking transporters are consistent with siderophore or precursor movement; the remaining domain-bearing genes (LacI/Peripla_BP_1 regulator ctg1_5449, Acetyltransf_3 ctg1_5450, DJ-1_PfpI/HTH_18 ctg1_5453, Usp ctg1_5455, Metallophos ctg1_5459, Glyco_hydro_20 ctg1_5460) frame regulation and accessory metabolism around that core.

## §5 Core biosynthetic logic
The pathway is the classic NIS logic: a diamine or hydroxylysine precursor is N-hydroxylated (DesB-type oxygenase), the hydroxylamine is acylated to a hydroxamate (DesC-type acyltransferase), and the NIS synthetase (DesD-type, IucA_IucC) condenses hydroxamate-bearing units — alternating with a diamine linker — into the ferrioxamine chain, which can be linear or macrocyclic. No NRPS adenylation/thiolation modules are needed, which is exactly what "NRPS-independent" denotes.

## §6 Tailoring and maturation logic
Tailoring here is intrinsic to backbone assembly rather than post-assembly decoration: the hydroxylation and acylation steps that build each hydroxamate are the maturation logic. Any macrocyclisation versus linear-chain outcome is a property of the NIS synthetase condensation, not of a separate cyclase, so the maturation gap is small and the class assignment is robust.

## §7 Transport, resistance, and regulation
Regulation is consistent with an iron-responsive locus: a LacI-family/periplasmic-binding regulator (ctg1_5449) and accessory HTH genes sit at the region edge, the pattern expected for iron-status control. Transport/uptake is represented by the Gpr1_Fun34_YaaH permease and the FhuF-associated machinery, consistent with siderophore export and ferri-siderophore re-uptake. This is capacity, not a measured phenotype.

## §8 Comparator/KCB interpretation
KnownClusterBlast anchors this region to BGC0000940.5 (desferrioxamine B / desferrioxamine E) as the top hit with a high aggregate score (~3732), the strongest tier of class match in this genome. This is product-class similarity, not identity: it supports "capacity consistent with a desferrioxamine-type hydroxamate siderophore" and does not establish that this strain's product is desferrioxamine B or E specifically. The similarity is a source-derived anchor and requires isolation to assign an exact structure.

## §9 Alternative hypotheses
The main alternative is that the locus has the capacity for a des-family congener (a different chain length or a linear versus macrocyclic ferrioxamine) rather than the exact KCB anchor. A second alternative is that accessory domains (Glyco_hydro_20, Metallophos) reflect co-located non-siderophore metabolism rather than tailoring of the siderophore itself. Both are resolved only by isolation and MS.

## §10 Fragmentation and co-capture risks
Because the region is Interior on a finished contig, fragmentation risk is negligible; there is no split across contigs and no edge truncation. The residual co-capture risk is internal: the "other" accessory genes could belong to an adjacent function rather than the siderophore, which is an interpretation risk, not an assembly one.

## §11 Product-family interpretation
The product family is hydroxamate siderophores of the ferrioxamine/desferrioxamine type — high-affinity ferric-iron chelators. The capacity statement is "consistent with a desferrioxamine-type siderophore"; the specific congener is not assignable from sequence.

## §12 Bee/microbe ecological interpretation
Read ecologically, a high-affinity hydroxamate siderophore is a competition and nutritional-immunity trait: it lets the producer scavenge ferric iron from a shared niche and can withhold iron from neighbours. For a soil/host-associated actinomycete this is a plausible competitive-fitness capacity, stated at the level of capacity rather than an observed ecological outcome.

## §13 Antibacterial/antifungal relevance
Siderophores are not themselves the antibacterial/antifungal principle; their relevance is indirect (iron sequestration can suppress competitors, and siderophore-drug conjugates are a delivery strategy). Any antibacterial or antifungal activity for this strain is an extract-level property of the whole strain, never a per-BGC phenotype attributed to this locus.

## §14 What cannot be claimed
It cannot be claimed that this BGC's product is desferrioxamine B or E, that it is expressed under any given condition, or that it is responsible for any measured activity. It cannot be claimed that the accessory "other" genes are part of the siderophore pathway. The panel BLASTp hits are similarity, not identity — a 90.8% hit to an IucA/IucC homolog does not establish that this locus makes any particular ferrioxamine.

## §15 Missing evidence
Missing: an independent channel on the DesB-type hydroxylase ctg1_5463, which sat outside the three-gene panel; expression evidence under iron limitation; and an isolated compound with high-resolution MS to confirm the exact ferrioxamine congener and its chain length. The KnownClusterBlast anchor and the panel BLASTp are strong but are class/homolog similarity, not structure, and cannot distinguish a linear from a macrocyclic ferrioxamine. No negative control (NRPS-adenylation absence) has been confirmed by HMMER yet either.

## §16 BLASTP/HMMER next steps
The three-gene panel (NIS synthetase ctg1_5461, acyltransferase ctg1_5462, regulator ctg1_5471) has been run on NCBI nr and ingested; the results artifact `BGC042_online_blastp.csv` is present and §4 carries the per-gene outcomes. The remaining homology work is to extend the panel to the DesB-type hydroxylase ctg1_5463 (Lys_Orn_oxgnase), which was outside the three-gene selection, and to run HMMER over the region to confirm the absence of NRPS adenylation modules — the negative evidence that distinguishes NIS from an NRPS metallophore. The route to add the hydroxylase is the same offline path: `bgc-blastp-panel` with a larger `--genes-per-bgc`, then `ingest-blastp --hit-table <hits.csv> --package <package>`.

## §17 LC-MS / fermentation implications
For detection, culture under iron-limited conditions (iron-depleted defined medium, chelex-treated) to derepress siderophore biosynthesis, and run a CAS (chrome azurol S) assay on the spent medium as a fast siderophore readout. For LC-MS, desferrioxamine-type hydroxamates ionise well in positive mode; target the ferrioxamine mass series and confirm iron binding by the mass shift between apo- and ferri- forms (Fe for 3H), and by the characteristic hydroxamate neutral losses. Because congeners differ by chain length, expect a homologous series rather than a single mass; acquire high-resolution MS and MS/MS on the dominant apo-siderophore. Fermentation should pair an iron-replete control so the iron-derepressed features can be picked out. None of this asserts production; it is the detection plan that would test the capacity call.

## §18 Figure/locus-map notes
The locus map should mark the NIS core (ctg1_5461, ctg1_5463, ctg1_5462) as the diagnostic block and shade the regulator/transport genes at the flanks distinctly, so the reader sees the "assemble-then-move" layout typical of siderophore loci. Annotate ctg1_5461 as the NIS synthetase (the single gene that carries the class call) and place the DesB hydroxylase and DesC acyltransferase adjacent to it so the hydroxamate-building order reads left to right. A small inset showing the absence of NRPS adenylation modules across the region would make the "NRPS-independent" point visually, since that negative is the distinction from an NRPS metallophore.

## §19 Final Mode B judgement
Judgement: a well-supported NRPS-independent (desferrioxamine-type) siderophore locus on a finished contig, with a strong class-level KCB anchor, a complete NIS core read from domains, and an independent BLASTp channel that corroborates the NIS synthetase and acyltransferase at 90–96% identity to characterised homologs. Confidence in the class call is HIGH; confidence in the exact congener is LOW pending isolation.

## §20 Next actions
Run the BLASTp panel on the core genes and ingest the hit-table; culture under iron limitation with a CAS screen; acquire HR-MS/MS on the apo-siderophore series; and, if pursued, test iron-withholding competition rather than direct antibacterial activity, since the ecological role is nutritional.

## §23 Heterologous expression
If a native fermentation signal is weak, the des core is a good heterologous-expression target because it is compact and NRPS-independent: the DesA/B/C/D-type set (ctg1_5457 precursor support, ctg1_5463 hydroxylase, ctg1_5462 acyltransferase, ctg1_5461 NIS synthetase) can be refactored onto a single construct under an iron-derepressible or constitutive promoter and moved into a *Streptomyces* host (for example an *S. coelicolor* or *S. albus* expression chassis) with its own siderophore loci intact or deleted as needed. Because the pathway needs no PPTase-primed carrier proteins, expression is simpler than for an NRPS/PKS. Induce under iron limitation and screen the host supernatant by CAS; a positive shift over the empty-vector host tests the capacity call directly.

## §24 Scaffold novelty score
Scaffold novelty: LOW. The desferrioxamine/ferrioxamine hydroxamate scaffold is well-precedented, with a strong class-level KnownClusterBlast anchor to BGC0000940.5 (desferrioxamine B/E, score ~3732) and a canonical NRPS-independent des gene set (IucA_IucC synthetase, Lys/Orn hydroxylase, acyltransferase). There are no unusual domain fusions, orphan tailoring genes, or missing-core signatures that would elevate the novelty read. Any genuine novelty sits at the congener level — chain length, or linear versus macrocyclic ferrioxamine — which is an MS question, not a novel-scaffold claim. This card is therefore not treated as a novel-scaffold case, and the low score is asserted from the strong class anchor rather than from absence of data.

## §27 Self-resistance assessment
Self-protection for a siderophore producer is uptake/efflux control rather than target modification: the FhuF-associated ferri-siderophore reductase domain on ctg1_5461 and the region's transporters are consistent with controlled re-uptake and iron release. There is no source-derived antibiotic-resistance marker in this region, which is expected — a siderophore is not a self-toxic antibiotic — so the self-resistance signal is NULL/transport-mediated rather than target-based.

## §28 Evidence provenance ledger
Store-backed: the region call, coordinates, boundary status, gene/domain table, and KnownClusterBlast anchor all derive from the antiSMASH package for the finished public genome BA000030.4. Reconstructed: the DesB role assignment for ctg1_5463 is inferred from Pfam domains plus the desferrioxamine literature, since it sat outside the panel. Operator-supplied: an NCBI web BLASTp of the three-gene panel (hit-table + XML2), offline-ingested; the per-gene BLASTp results in §4 come from `blastp_online/BGC042_online_blastp.csv`. Not run: an independent channel on the DesB hydroxylase (ctg1_5463).

## §30 Experimental decision tree
If CAS is positive under iron limitation → proceed to HR-MS for the ferrioxamine series; if the mass series matches desferrioxamine B/E within error → report "capacity consistent with desferrioxamine-type siderophore, congener X" and stop over-claiming beyond the detected masses. If CAS is positive but the mass series is novel → treat as a des-family congener and prioritise isolation/NMR. If CAS is negative under iron limitation → check expression (RT-qPCR on ctg1_5461) before concluding the locus is silent. In parallel, run the BLASTp panel; if the NIS synthetase and hydroxylase return the expected class hits → §4 is upgraded to a per-gene result; if they do not → revisit the class call rather than the compound.
