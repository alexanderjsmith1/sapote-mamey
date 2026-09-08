# Mode B reference authoring exemplar

**Exact locus:** `Kitasatospora setae KM-6054T / NC_016109.1 / region016 / BGC016`  
**Document state:** `REFERENCE_AUTHORING_EXEMPLAR_WITH_TYPED_BLASTP_LIMITATION`  
**Source profile:** Mamey v1.9.124, bundle v9.7.371, gold mode, relaxed antiSMASH profile  
**Independent BLASTP state:** `STRUCTURALLY_UNAVAILABLE_IN_PORTABLE_REFERENCE_FIXTURE`  
**Rendering:** not run

**Calibration boundary:** this is a typed-terminal format exemplar, not positive substantive calibration
for §§20, 39, 40, 42, or 48. Its §20 predates the one-highest-information-action contract, and its late
sections demonstrate honest unavailable-evidence closure rather than measured cohort evidence. Follow
`docs/MODEB_GATE_CLEAN_AUTHORING.md` for current source-bound authoring requirements; do not copy this
locus's prose or scientific content.

This is a writing exemplar, not proof that the exact product, expression state, production, activity, or novelty is known. It demonstrates how an LLM should reconcile all available non-BLASTP streams without inventing BLASTP hits or converting their absence into biological novelty. MIBiG/ClusterBlast percentages are comparator homology, not independent nr or ClusteredNR results.

## §1 Identity and node/region

`Kitasatospora setae KM-6054T / NC_016109.1 / region016 / BGC016` spans coordinates 2,504,042–2,527,571 on the 8,783,278-bp closed chromosome NC_016109.1. The 23.53-kb region is Interior and contains one antiSMASH protocluster labelled `other; phosphonate`. The exact display always retains strain, accession, antiSMASH region, and BGC alias; the alias is not used alone as an evidence join.

## §2 Why this BGC was selected

This locus is a useful reference exemplar because the chemistry is interpretable but not trivial. A diagnostic phosphoenolpyruvate-mutase signal establishes phosphonate-building capacity, while adjacent condensation, carrier-protein, adenylation, aminotransferase, kinase, oxygenase, transport, and regulatory functions suggest a larger modified small-molecule pathway rather than a single isolated phosphonate reaction. It also teaches restraint: its best characterized comparator is phosphonoacetic-acid biosynthesis, but only 3 of the 22 MIBiG-screened query genes support that comparator, so the card must not rename the locus after that hit.

## §3 Boundary and assembly status

The source package reports one 8.78-Mb contig, N50 equal to genome size, 74.198% GC, and a CLOSED fragmentation tier. All 48 detected regions are Interior. Thus, truncation is not the primary uncertainty for `Kitasatospora setae KM-6054T / NC_016109.1 / region016 / BGC016`; functional partitioning and product-family resolution are. The source package is relaxed-profile evidence, so a cross-profile comparison must use accession, coordinates, sequence identity, and CDS roster rather than transferring region aliases.

## §4 Gene-by-gene interpretation

The locus resolves into five functional blocks. The left flank contains export and regulation. A compact condensation–carrier–adenylation block follows. The diagnostic phosphonate block begins with KSE_RS11130 and is followed by amino-group, nucleotide-transfer, redox, kinase, oxygenase, and thiamine-dependent functions. The right flank carries a second transporter, regulatory context, methylation capacity, and two unresolved small proteins.

| Order | Gene | aa | Source-derived annotation/domain | Mode B role | Independent BLASTP state |
|---:|---|---:|---|---|---|
| 1 | KSE_RS11105 | 429 | MFS transporter | export/self-protection context | SB-0 |
| 2 | KSE_RS11110 | 341 | helix-turn-helix regulator | local regulation | SB-0 |
| 3 | KSE_RS11115 | 438 | active LCL condensation domain; PF00668 | assembly/ligation candidate | SB-0 |
| 4 | KSE_RS11120 | 81 | PP-binding carrier domain; PF00550 | carrier protein | SB-0 |
| 5 | KSE_RS11125 | 533 | AMP-binding domain; PF00501 | substrate activation | SB-0 |
| 6 | KSE_RS11130 | 286 | PEP_mutase PF05042; phosphonates/phosphonates-like HMMs | diagnostic C–P-bond-forming core | SB-0 |
| 7 | KSE_RS11135 | 327 | SbnA-like PLP enzyme; PALP | amino-group/substrate-supply chemistry | SB-0 |
| 8 | KSE_RS11140 | 555 | AMP-binding A-domain; PF00501 | second substrate-activation enzyme | SB-0 |
| 9 | KSE_RS11145 | 387 | NTP_transf_5 | nucleotide-transfer/activation candidate | SB-0 |
| 10 | KSE_RS39880 | 657 | Aminotran_5 | aminotransferase tailoring | SB-0 |
| 11 | KSE_RS11155 | 758 | FAD/NAD(P)-binding protein | redox tailoring candidate | SB-0 |
| 12 | KSE_RS43800 | 226 | mycothiol-dependent isomerase-family protein | accessory redox/isomerization context | SB-0 |
| 13 | KSE_RS43805 | 337 | FomB-family phosphonate monophosphate kinase | phosphonate phosphorylation candidate | SB-0 |
| 14 | KSE_RS11170 | 322 | TauD-family dioxygenase | oxidative tailoring | SB-0 |
| 15 | KSE_RS11175 | 218 | pyridoxamine-5′-phosphate oxidase-family protein | PLP cofactor support | SB-0 |
| 16 | KSE_RS11180 | 174 | TPP_enzyme_N | thiamine-dependent chemistry, N fragment | SB-0 |
| 17 | KSE_RS11185 | 206 | TPP_enzyme_C | thiamine-dependent chemistry, C fragment | SB-0 |
| 18 | KSE_RS11190 | 346 | SbnB-like enzyme | amino-acid/substrate-supply chemistry | SB-0 |
| 19 | KSE_RS11195 | 289 | EamA-family transporter | export/self-protection context | SB-0 |
| 20 | KSE_RS11200 | 79 | DUF397 protein | unresolved accessory | SB-0 |
| 21 | KSE_RS11205 | 323 | Scr1-family antitoxin-like regulator | regulatory/stress-response context | SB-0 |
| 22 | KSE_RS11210 | 276 | SAM-dependent methyltransferase | methyl tailoring candidate | SB-0 |
| 23 | KSE_RS11215 | 142 | hypothetical protein | unresolved right-boundary context | SB-0 |

`SB-0` means `STRUCTURALLY_UNAVAILABLE_IN_PORTABLE_REFERENCE_FIXTURE` for every canonical gene. No independent nr, ClusteredNR, Swiss-Prot, or EBI/UniProt table is available in the portable reference fixture. This is a typed source limitation, not a completed no-hit result or novelty evidence. The source does contain MIBiG/ClusterBlast comparator alignments; those remain in §§8 and 46 and are not relabelled as BLASTP channels.

## §5 Core biosynthetic logic

KSE_RS11130 is the decisive class anchor: phosphoenolpyruvate mutase catalyses formation of a carbon–phosphorus bond, the defining entry reaction of many phosphonate pathways. KSE_RS11115, KSE_RS11120, KSE_RS11125, and KSE_RS11140 provide condensation, carrier, and two substrate-activation activities. Together with the SbnA/SbnB-like pair and the large aminotransferase, this supports capacity for an amino-containing, enzymatically assembled phosphonate-family metabolite. The data do not determine its exact scaffold.

## §6 Tailoring and maturation logic

The predicted tailoring repertoire includes a FomB-family phosphonate kinase, an NTP-transferase, an aminotransferase, a TauD-like dioxygenase, a SAM-dependent methyltransferase, a large flavin/nicotinamide-binding protein, and paired TPP-enzyme fragments. This combination could alter oxidation, amino substitution, phosphorylation, methylation, or carbon skeleton processing after the initial C–P bond is formed. The card treats these as pathway-capacity hypotheses, not proof that every enzyme acts on one product.

## §7 Transport, resistance, and regulation

An MFS transporter at the left flank and an EamA-family transporter near the right flank provide a plausible export/self-protection envelope. Mamey routes the region as `T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED` with four resistance-like observations. That routing strengthens prioritization but does not identify a molecular target or prove antimicrobial production. Regulation is represented by the HTH protein KSE_RS11110 and the Scr1-family antitoxin-like regulator KSE_RS11205.

## §8 Comparator/KCB interpretation

KnownClusterBlast ranks MIBiG BGC0001739.3, phosphonoacetic-acid biosynthesis, first with cumulative score 558. Mamey’s per-gene convergence binds three query genes to that comparator, with median identity 52.0% and median query coverage 95.455%. The region is not dominated by this comparator: only 3/22 MIBiG-screened genes bind it, the dominant status is `CO_DOMINANT_OR_DIFFUSE`, and multiple other phosphonate or mixed-pathway references recur. The correct conclusion is phosphonate-family relatedness, not phosphonoacetic-acid identity.

## §9 Alternative hypotheses

The leading model is an amino-containing phosphonate-family small molecule assembled through C–P-bond formation plus carrier/adenylation chemistry. A narrower alternative is a phosphonoacetate-like pathway with co-captured NRPS-like enzymes. A broader alternative is a hybrid phosphonate–peptide or phosphonate-decorated metabolite. The diffuse MIBiG convergence and the two activation enzymes keep these alternatives open.

## §10 Fragmentation and co-capture risks

Contig fragmentation risk is low because the chromosome is closed and the region is Interior. Co-capture remains plausible: the 23-CDS region contains regulators, two transporters, cofactor-support proteins, and two unresolved proteins. The one-protocluster antiSMASH call argues against a detected multi-protocluster overmerge, but it does not prove that every boundary CDS is chemically required.

## §11 Product-family interpretation

The defensible product-family statement is: **encoded capacity for a modified phosphonate-family small molecule, potentially amino-containing and assembled with carrier/adenylation chemistry**. The card does not name phosphonoacetic acid, dehydrofosmidomycin, rhizocticin, fosfomycin, or any mixed-pathway comparator as the produced compound.

## §12 Bee/microbe ecological interpretation

The reference package supplies no verified isolation source and no host metadata. Therefore no bee, wasp, plant, soil, or microbial-interaction role is assigned. A phosphonate pathway could mediate competition or nutrient interactions at a class level, but ecology remains unbound for this exemplar.

## §13 Antibacterial/antifungal relevance

Several characterized phosphonate families contain antimicrobial metabolites, and the source-derived resistance/export envelope makes antibacterial follow-up reasonable. That is a prioritization rationale, not an activity result. The package’s default-assumed MRSA/Candida context is not attributed to this locus, this product family, or this strain without extract and linkage evidence.

## §14 What cannot be claimed

This card cannot claim an exact compound, a phosphonoacetic-acid product, expression, production, titre, antibacterial or antifungal activity, target identity, ecological function, cross-region physical linkage, or scaffold novelty. It also cannot claim an independent BLASTP result. MIBiG/ClusterBlast identities are comparator evidence and remain labelled as such.

## §15 Missing evidence

Material limitations use closed typed states. Independent BLASTP is `STRUCTURALLY_UNAVAILABLE_IN_PORTABLE_REFERENCE_FIXTURE`. BiG-SCAPE placement, cohort prevalence, chitin context, domain-rarity statistics, and externally verified literature are `SOURCE_NOT_INCLUDED_IN_EXEMPLAR_FIXTURE`. Fermentation, expression, metabolomics, and bioactivity are `NOT_MEASURED`. These limitations prevent a finished-current-evidence or publication-ready label but do not prevent the card from serving as an authoring exemplar.

## §16 BLASTP/HMMER next steps

If the exemplar is later promoted beyond its no-BLASTP profile, run every canonical protein separately against nr, ClusteredNR, and reviewed Swiss-Prot, preserving accession, matched-protein description, organism, identity, positives/similarity, query coverage, e-value, bitscore, channel, and source receipt. Priority genes are KSE_RS11130, KSE_RS11120, KSE_RS11125, KSE_RS11140, KSE_RS43805, and the SbnA/SbnB-like pair. Retain the current exemplar state while those runs are active and revise only after the matrix is bound.

## §17 LC-MS / fermentation implications

Use untargeted LC-HRMS with phosphorus-aware annotation and compare multiple media, phosphate concentrations, growth phases, and stress conditions. Pair parent-ion discovery with MS/MS neutral-loss patterns appropriate for phosphonate chemistry, but do not constrain the search to phosphonoacetic acid. A knockout of KSE_RS11130 provides the strongest locus-linkage control: a metabolite lost in the mutant and restored by complementation would connect chemistry to the region.

## §18 Figure/locus-map notes

Future rendering should preserve all 23 locus labels and use the V7 information standard: gene arrows, locus tags, selected-gene emphasis, domains/HMMs, comparator identity and coverage, and explicit evidence-channel labels. Mark KSE_RS11130 as the diagnostic core; group KSE_RS11115–KSE_RS11145 as the assembly/activation block; show KSE_RS11105 and KSE_RS11195 as transport; and distinguish MIBiG comparator percentages from absent independent BLASTP. Rendering is not part of this patch.

## §19 Final Mode B judgement

`Kitasatospora setae KM-6054T / NC_016109.1 / region016 / BGC016` is a closed-chromosome, Interior, single-protocluster phosphonate locus with a diagnostic PEP-mutase core, compact carrier/adenylation/condensation machinery, extensive amino/redox/phosphorylation tailoring capacity, and flanking transport/regulatory context. The evidence supports phosphonate-family biosynthetic capacity. Exact product, expression, production, activity, and novelty remain unestablished.

## §20 Next actions

For scientific closure: validate the reference metadata; bind an exact antiSMASH region hash; add channel-separated BLASTP if available; test KSE_RS11130 by deletion/complementation; and perform phosphorus-aware metabolomics across OSMAC conditions. For software closure: use this card to test full §1–§48 parsing, exact identity display, all-stream disposition, typed no-BLASTP handling, and prevention of comparator-to-BLASTP relabelling.

## §21 Precursor mass ladder

`NOT_APPLICABLE`: antiSMASH does not classify this region as a RiPP and no ribosomal precursor peptide is bound. Do not fabricate a precursor mass ladder.

## §22 RiPP database search

`NOT_APPLICABLE`: no RiPP precursor/maturase architecture is established for this locus. RiPP databases are not the appropriate first search route. The short KSE_RS11200 and KSE_RS11215 proteins are not promoted to precursor peptides merely because they are small; neither has an admitted precursor call or matched maturation context. The appropriate comparison channels are phosphonate enzymes and characterized phosphonate-pathway clusters.

## §23 Heterologous expression

Clone a minimal region centred on KSE_RS11130 and the KSE_RS11115–KSE_RS11145 assembly block, then expand boundaries to include tailoring and transport if the minimal construct is inactive. Compare empty vector, full construct, PEP-mutase catalytic mutant, and complemented strains. A new phosphorus-containing metabolite dependent on intact KSE_RS11130 would provide a direct capacity-to-product bridge.

## §24 Scaffold novelty score

The Mamey novelty prior is 53.0, a routing value rather than an adjudicated scaffold-novelty score. Repeated MIBiG support argues against a wholly unprecedented biochemical class, while diffuse comparator dominance leaves room for a distinct scaffold or decoration pattern. The honest qualitative read is `FAMILY_KNOWN_SCAFFOLD_UNRESOLVED`; no stronger novelty claim is warranted.

## §25 Genome neighbourhood

The region lies within a closed chromosome and has regulatory and transport functions on both sides of the biosynthetic core. The left MFS/HTH block and right EamA/regulator/methyltransferase block are plausible functional boundaries, but exact knockout or transcript boundaries should decide whether KSE_RS11200–KSE_RS11215 are pathway members or co-captured context.

## §26 OSMAC protocol

Use a small factorial design varying phosphate availability, carbon source, nitrogen source, metal availability, and growth phase. Retain matched biomass and supernatant extracts. Compare wild type, KSE_RS11130 knockout, and complemented strain. Prioritize conditions that produce a reproducible, genotype-dependent phosphorus-containing feature rather than optimizing a comparator-named mass.

## §27 Self-resistance assessment

#### Candidate gene orientation

| Gene | Physical membership | Candidate role | Evidence source | Class concordance | Allowed inference |
|---|---|---|---|---|---|
| KSE_RS11105 | EXACT_REGION | MFS-family export/self-protection candidate | exact Mamey CDS table plus T1 resistance routing | UNRESOLVED | prioritize transporter testing after a locus-dependent metabolite is detected |
| KSE_RS11195 | EXACT_REGION | EamA-family export/self-protection candidate | exact Mamey CDS table plus T1 resistance routing | UNRESOLVED | paired transport context only; substrate and direction remain unknown |

#### Claim ceiling

The two exact transporters and the Mamey T1 routing justify testing export/self-protection, but no target-modification determinant is identified. Transporter knockdowns can test sensitivity to any locus-dependent metabolite after a product is detected. Until then, resistance is pathway context, not proof of toxicity or producer protection.

## §28 Evidence provenance ledger

| Stream | State | Admitted contribution | Claim ceiling |
|---|---|---|---|
| exact antiSMASH/Mamey inventory | `READY_BOUND` | identity, coordinates, 23-CDS roster, domains, boundary, one protocluster | annotation/capacity |
| Mamey HMM/domain evidence | `READY_BOUND` | PEP_mutase, PP-binding, AMP-binding, Condensation, Aminotran_5, TauD | domain-function hypotheses |
| MIBiG convergence/per-gene | `READY_BOUND` | nine ranked comparator families; 3-gene top phosphonoacetate support | pathway-family relatedness |
| ClusterBlast per-gene | `READY_BOUND` | six representative comparator-gene alignments | similarity only |
| RG-GMCI | `READY_BOUND` | four above-low region-pair hypotheses, strongest with NC_016109.1 region039 | homology-guided linkage only |
| independent BLASTP | `STRUCTURALLY_UNAVAILABLE_IN_PORTABLE_REFERENCE_FIXTURE` | none | no BLASTP claim |
| BiG-SCAPE | `SOURCE_NOT_INCLUDED_IN_EXEMPLAR_FIXTURE` | none | no GCF claim |
| chitin | `SOURCE_NOT_INCLUDED_IN_EXEMPLAR_FIXTURE` | none | no chitin/ecology claim |
| domain rarity | `SOURCE_NOT_INCLUDED_IN_EXEMPLAR_FIXTURE` | none | no rarity claim |
| literature | `SOURCE_NOT_INCLUDED_IN_EXEMPLAR_FIXTURE` | none beyond comparator names | no literature-derived product/activity claim |
| prevalence/cohort | `SOURCE_NOT_INCLUDED_IN_EXEMPLAR_FIXTURE` | none | no prevalence claim |
| historical card/V7 | `NOT_APPLICABLE_NEW_REFERENCE_EXEMPLAR` | presentation rules only | no transferred science |

## §29 Cross-cluster interactions

The strain has more than three high-priority regions, but no metabolite-level interaction is demonstrated. RG-GMCI links this locus most strongly to NC_016109.1 region039 through shared characterized references; because both regions are complete and physically separate on one chromosome, this is a hypothesis of complementary family resemblance, not permission to merge them into one pathway.

## §30 Experimental decision tree

1. Verify exact region bytes and metadata.  
2. Confirm KSE_RS11130 PEP-mutase activity and define the activation/carrier block.  
3. If independent BLASTP becomes available, exact-bind all 23 genes and retain channel separation.  
4. Run OSMAC metabolomics with wild type, KSE_RS11130 knockout, and complementation.  
5. If a genotype-dependent phosphorus-containing feature appears, map tailoring by staged deletions.  
6. Only then test activity and name the product family more narrowly.

## §31 Region CDS census

The exact Mamey CDS table contains 23 genes ordered KSE_RS11105 through KSE_RS11215, including the alternate locus KSE_RS39880 and two KSE_RS438xx loci. The MIBiG convergence file reports a 22-query denominator and seven recognizable genes. This 23-versus-22 difference is a source-screen denominator difference, not an identity failure; the card preserves both denominators.

## §32 Assembly-line inventory

Measured domain evidence identifies one condensation domain (KSE_RS11115), one PP-binding carrier (KSE_RS11120), and two AMP-binding activation enzymes (KSE_RS11125 and KSE_RS11140). The source package does not establish a canonical multi-module NRPS assembly line with a complete module-by-module peptide prediction. Interpret this as compact activation/carrier/condensation machinery embedded in a phosphonate pathway.

## §33 Module programming readout

Both AMP-binding entries have unresolved substrate consensus (`X`) in the compact table. KSE_RS11140 carries A-domain motifs and a Stachelhaus-like signal compatible with diaminopropionate/diaminobutyrate-class chemistry, but the prediction is not sufficiently decisive to assign a final monomer. No linear peptide sequence is inferred.

## §34 Initiation & release logic

Initiation likely begins with PEP-mutase-dependent C–P-bond formation and/or adenylation of a small substrate, followed by carrier-dependent processing. The region lacks an admitted, unambiguous terminal thioesterase call, so release could occur through transfer, hydrolysis, phosphorylation, or a noncanonical route. The card leaves release unresolved.

## §35 Protocluster decomposition

antiSMASH reports one protocluster for `Kitasatospora setae KM-6054T / NC_016109.1 / region016 / BGC016`. No internal multi-protocluster decomposition is required. Functional blocks are used for interpretation only and are not relabelled as separate BGCs.

## §36 Boundary status + overmerge/locus-splitting adjudication (merged)

The region is Interior on a closed chromosome, with no edge or truncation flag and one detected protocluster. Overmerge risk is therefore low but not zero; the boundary regulators, transporters, DUF397 protein, and terminal hypothetical protein remain candidates for co-capture. No locus splitting is asserted without transcript or knockout evidence.

## §37 Partner & accessory proteins

Likely partners include the SbnA/SbnB-like pair, KSE_RS39880 aminotransferase, KSE_RS43805 phosphonate kinase, KSE_RS11170 dioxygenase, KSE_RS11155 redox enzyme, KSE_RS11210 methyltransferase, and the paired TPP-enzyme fragments. KSE_RS43800 and KSE_RS11175 may support redox/cofactor balance. KSE_RS11200 and KSE_RS11215 remain unresolved rather than being assigned a convenient role.

## §38 Co-located resistance & efflux

KSE_RS11105 (MFS) and KSE_RS11195 (EamA) form the strongest co-located efflux evidence. The Mamey T1 route records four resistance-like signals, but the exact four-gene interpretation must remain source-bound. This section supports an export/self-protection hypothesis, not an antimicrobial mechanism.

## §39 Cross-strain sequence identity

`SOURCE_NOT_INCLUDED_IN_EXEMPLAR_FIXTURE`: no independently curated cross-strain ortholog panel is bundled for this locus. MIBiG comparator identity values are not substituted for cohort cross-strain identity.

## §40 BiG-SCAPE family / cohort placement

`SOURCE_NOT_INCLUDED_IN_EXEMPLAR_FIXTURE`: no exact-bound BiG-SCAPE family assignment, database identifier, cutoff, or cohort denominator is present in the reference package. The exemplar therefore makes no GCF placement or private-family claim.

## §41 Protein / domain phylogeny

`SOURCE_NOT_INCLUDED_IN_EXEMPLAR_FIXTURE`: no alignment/tree receipt is available. A useful future analysis would place KSE_RS11130 among verified PEP-mutases and separately place KSE_RS11125/KSE_RS11140 among adenylation enzymes; domain similarity alone is not a phylogeny.

## §42 Horizontal transfer evidence

No horizontal-transfer claim is made. Local GC, mobility genes, flanking repeats, phylogenetic incongruence, or comparative synteny were not supplied as an adjudicated panel. High chromosome GC and a self-contained locus are descriptive, not transfer evidence.

## §43 Split-pathway / cross-contig (RG-GMCI)

The strongest RG-GMCI pair joins the exact target to NC_016109.1 region039: score 20, `HIGH_RG_GMCI_RESCUE`, three supporting references, and one strong reference. Additional moderate pairs involve NC_016109.1 regions027, 031, and 046. All are same-chromosome, Interior regions. RG-GMCI here means homology-guided complementary reference signal; it does not join the loci at nucleotide level or prove one product pathway.

## §44 Within-cohort prevalence & tier

`SOURCE_NOT_INCLUDED_IN_EXEMPLAR_FIXTURE`: no defined cohort numerator/denominator is supplied. The card cannot call this locus common, rare, private, conserved, or reference-enriched.

## §45 Supervisor / university cohort comparison

#### Cohort comparison denominator

`COHORT_COMPARISON_NOT_AVAILABLE_TYPED; denominator=0 project cohort strains or loci in this portable reference fixture; sources=portable fixture manifest and bound source register; reason=no project cohort source is included in the portable exemplar.`

#### Cohort-comparison conclusion

No cohort gene-similarity result is reported. Institution-specific or project-specific comparisons belong in a source-bound project overlay; missing cohort evidence in this portable fixture is not biological absence.

## §46 Type / reference strain comparison

This is itself a reference-strain package labelled Kitasatospora setae KM-6054T, but its manifest records taxonomy as `not verified` and source as `not supplied`. The card therefore treats it as a reference authoring fixture without claiming that type status or isolation metadata were reverified in this run. Its characterized comparisons are the source-bound MIBiG entries, led diffusely by phosphonoacetic-acid biosynthesis.

## §47 Host-matched unrelated reference

`NOT_APPLICABLE_UNTIL_SOURCE_METADATA_IS_VERIFIED`: no host or habitat is verified, so a host-matched reference cannot be selected honestly. Do not import bee, wasp, plant, or soil context from another exemplar.

## §48 Cross-cohort synthesis & claim ceiling

Across all admitted streams, the convergent conclusion is phosphonate-family biosynthetic capacity with compact activation/carrier/condensation machinery, broad tailoring potential, and local transport/regulation. The source streams do not converge on an exact product or measured phenotype. The global ceiling is therefore: **reference-locus capacity hypothesis, not product identity, production, activity, ecological function, novelty, owner acceptance, or publication readiness**.
