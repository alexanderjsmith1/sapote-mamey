# Sapote–Mamey · Concepts Q&A

Use this page to learn what a result means and where your interpretation must stop.
It answers one question per heading.
Terms are defined in the [glossary](../GLOSSARY.md).
To run the pipeline first, follow [the first-run recipe](../reader/01_FIRST_RUN.md).
To read a results table, see [reading your results](../READING_YOUR_RESULTS.md).

*Current to bundle v9.7.464 / engine Mamey 1.9.180.*

## Contents

- [The big picture](#the-big-picture)
- [Reading evidence and scores](#reading-evidence-and-scores)
- [The evidence scans](#the-evidence-scans)
- [Standing rules and special cases](#standing-rules-and-special-cases)
- [Biosynthetic biology in brief](#biosynthetic-biology-in-brief)

## The big picture

### Why are there two layers, Mamey and Sapote?

Mamey is the deterministic layer.
It reads antiSMASH results and computes evidence: tables, scores, flags.
Sapote is the judgment layer.
A person, or an assistant working from a validated package, writes an interpretation of that evidence.

The split lets you check a judgment against the records and rules behind it.
Deterministic code can still have parsing, joining or scoring defects.
Judgment can be wrong.
Check both against the source files.
The shared rules are in [AGENTS.md](../../AGENTS.md).

### What is Mode B?

Mode B is a written interpretation of one biosynthetic gene cluster (BGC).
It follows a named section contract.
It ties together the locus identity, the gene architecture, comparator evidence, alternative explanations and a claim-safe verdict.

Every BGC is named as `strain / full node-or-contig / region / BGC alias`, copied from one source record.
A bare alias such as `BGC003` is local to one run and is not an identity.

The default profile is `full48`.
The optional profile is `current50_v2`.
Use the same `--contract` value when you emit the template and when you verify the saved card.
The [profile matrix](../MODEB_PROFILE_MATRIX.md) lists both, and the [authoring walkthrough](../MODE_B_USER_WALKTHROUGH.md) shows the steps.

A template or a top-leads table is not a finished card.
`PASS_STRUCTURE` means the sections are present.
It does not mean the science or the citations are checked.
`operator_supplied` records where a value came from.
`citation_needed` means a literature check is still open.

### What do observed, computed, inferred and assumed mean?

These words say how a claim was obtained.

| Label | Meaning | Example |
|---|---|---|
| Observed | Present in a named source | The antiSMASH output lists a PKS product. |
| Computed | Produced by a stated rule | A score built from configured weights. |
| Inferred | Interpreted from evidence | A domain set supports a chemotype hypothesis. |
| Assumed | Used without confirmation | The genome is the strain on its label. |

An observed annotation can still be an upstream prediction.
The label does not turn it into measured chemistry.

### Why is bioactivity tied to a strain and never to one BGC?

An assay result belongs to its strain, material, target and conditions.
A BGC in the same strain is not shown to cause it.
A similarity match does not supply that link.
The metadata contract requires `compound_linkage = NOT_ESTABLISHED`.
See [the bioactivity metadata contract](../BIOACTIVITY_METADATA_CONTRACT.md).

### What does a negative or missing assay mean?

An untested strain and a failed measurement are not negatives.
A measured negative applies to its own material, target and conditions.
It does not show the strain lacks all activity or lacks the genes.
Keep `NOT_SUPPLIED / NOT_OBSERVED` and `MEASURED_NEGATIVE / NEGATIVE` as separate states in every table.

### What is an evidence-conservation check?

It asks whether a number, identifier or claim is supported by its bound source.
A reconciliation check compares one value reached by two routes, such as a manifest count and a report count.
A mismatch means "diagnose", not "the second route is right".
Carry source values, uncertainty and missing states through every summary.
Do not drop conflicting records or turn unknowns into zeros.
A passed check covers only the fields it examined.

## Reading evidence and scores

### What does the assembly tier tell me?

The assembly tier is the percentage of regions that sit away from a contig edge (labeled Interior).
The bands are GOOD at 70% or more, MODERATE at 45%, POOR at 20%, and VERY_POOR below 20%.
It reads UNKNOWN when no percentage is available.

It is not N50 or any other contig statistic.
A good tier does not mean every locus is complete.
Read the edge status of the locus you care about.
See the [glossary](../GLOSSARY.md) for how it differs from the fragmentation tier.

### What is KCB, and how does Mamey band its similarity?

KCB is KnownClusterBlast.
antiSMASH compares a region against characterized clusters in MIBiG, the reference collection of known clusters.
Mamey reads antiSMASH's own similarity percent for the top hit and bands it:

| Band | Percent |
|---|---|
| high | 70 or more |
| moderate | 40 to below 70 |
| low | above 0 to below 40 |
| none | exactly 0 |
| unresolved | no percent available |

The cumulative BLAST score (`KCB_score`) is a different number.
It is not a percent and does not compare across clusters of different size.

Similarity is not identity.
A high band says the region shares genes with a known cluster.
It does not say the strain makes that compound.
Report the match with its coverage, the reference and its source.
Write "similar to a characterized cluster", never "produces that compound".

### What is "KCB-dark", and what is an empty KCB file?

KCB-dark means no reference match was reported.
It can motivate a novelty review when the architecture and markers are coherent.
It does not show new chemistry, expression or activity.
An incomplete or uninformative locus can also have no match.

The `KCB_evidence_state` column tells the cases apart:

| Value | Meaning |
|---|---|
| `KNOWNCLUSTERBLAST_OBSERVED` | The KnownClusterBlast file had hits. |
| `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED` | The file was present and empty. This is not a validated negative, and it is a different state from "KCB-dark". |
| `CLUSTERBLAST_FALLBACK_OBSERVED` | No usable KnownClusterBlast file. ClusterBlast hits were read instead. Check them by hand. |
| `UNKNOWN_KCB` | Nothing was read. This is missing evidence, not a low similarity. |

### How is a score such as AB or AF built?

AB and AF are capacity and routing scores, not activity measurements.
The scorer combines eligible class, chemotype and diagnostic evidence.
Guards limit some credit, and the tier rules affect the final result.
No single baseline or bonus is the whole formula.
Read the per-record rationale text.

The edge penalty exists in the code and returns zero.
Boundary status does not lower an axis score.
NAPAA is neutral in the rules registry.
See [`mamey/scoring.py`](../../mamey/scoring.py).

### What are lead classes A, B and C?

They summarize how well a candidate supports being prioritized.
They do not raise confidence in a named product.
Several agreeing annotations strengthen a review case.
Expression and activity stay untested.
A capacity hypothesis stays a capacity hypothesis until product or activity evidence exists.

### What is the diagnostic floor?

An eligible, corroborated diagnostic marker can raise a score or set a minimum tier.
That lets architecture and markers count when KCB similarity is weak or absent.
The floor is a prioritization rule, not an assay result.
Tie each marker to the full source locus and check its class guards.
Do not infer a named compound, expression or antifungal activity from it.

### What are the evidence axes, and how do they become a verdict?

Architecture, similarity, diagnostic markers, regulation and completeness answer different questions.
Keep them visible rather than letting one score hide a disagreement.
Weak similarity plus a coherent architecture can justify more review.
It does not prove novelty.
Several outputs can reuse one upstream annotation.
Do not count that shared source twice as corroboration.

### When must I re-score before comparing runs?

Compare scores only when they come from a compatible engine, configuration and evidence basis.
A change to the scoring rules or the evidence contract can make old and new numbers incomparable.
A version label alone does not show which rules changed.
Record the engine and configuration for each run, and keep denominators and assembly context with them.
Re-scoring does not fix differences in sampling or assay design.

## The evidence scans

Each scan answers a narrow question about annotation text or geometry.
A scan result is evidence from the records you supplied.
Check each scan's scope before you read it.
Some scans cover only BGC regions, and a region scan cannot show absence across a whole proteome.

| Term | Plain meaning | What to inspect |
|---|---|---|
| CCTT | Class-trigger table: annotation patterns that point to a compound class | The pattern that matched, class fit, scoring eligibility |
| CGAD | Chitinase genome architecture detection | Whether the input was a proteome or only BGC regions |
| FLBR | Fragment-linkage census of split PKS/NRPS genes | Fragment flags, not a rebuilt pathway |
| EFLS | Shared-label pairing of possible fragments | The pair and its labels |
| RG-GMCI | Reference-guided linkage of fragment regions | Both locus identities and the shared references |
| UMED | Maturation-enzyme check near RiPP and nucleoside loci | Verdict and the 5 kb window |
| bldA / TFBS | Rare-codon burden and regulator-binding motifs | Counts, taxonomy fit, scope |

### What is RG-GMCI?

RG-GMCI is Reference-Guided Genome Mining Candidate Inference.
It proposes that two fragments are parts of one split pathway when they match the same reference cluster.
It is homology-guided linkage.
It does not join contigs.
The two sequences stay separate, and no nucleotide-level joining happens.

It uses overlapping or adjacent reference intervals as geometry.
When coordinates are missing, locus-tag proximity gives a coarser proxy.
Cross-genome ClusterBlast evidence and characterized KnownClusterBlast evidence are kept apart.
SubClusterBlast hits stay out of the pairing.
A HIGH label does not prove physical continuity and does not rule out paralogs.
Its routing bonus changes review priority, not claim confidence.
Inspect both endpoints, competing partners and the availability states in [the channel guide](../reference/04_RGGMCI_ClusterBlast_Utilization.md).

### How does EFLS differ from RG-GMCI?

EFLS makes preliminary pairs from shared product, reference, cassette and trigger labels.
It keeps only pairs where at least one member is Edge or Full-contig.
It does not compare contig ends or show that two pieces fit together.
RG-GMCI uses its own reference and geometry rules.
Both draw on shared annotations, so agreement between them is not independent evidence.
Neither shows physical continuity.

### What is FLBR?

FLBR is a census of PKS and NRPS machinery that looks split across contigs.
Its STRONG and WEAK flags are heuristics.
It does not rebuild an assembly line or show that scattered genes belong to one pathway.
Check complete locus identities before you link records.

### What are the CCTT trigger families?

The labels start with `T43-`.
The roster lives in `CCTT_PATTERNS` in [`mamey/source_scans.py`](../../mamey/source_scans.py).
It has 18 families: HAL, XHAL, PHO, NUC, BLA, AMC, ENE, LAN, LASSO, THA, DKP, IDC, PTM, TET, NN, PYE, GPA and BLT.
TET means tetronate and spirotetronate, not tetracycline.
PHO is phosphonate, NUC is nucleoside, PTM is polycyclic tetramate macrolactam, and LAN and LASSO are the lanthipeptide and lasso RiPP classes.

A hit count and a count of distinct BGCs with hits answer different questions.
Repeated matches in one locus are not several pathways.
A fired trigger earns scoring credit only when it fits the locus class.
Halogenation context alone does not define a compound class.

### What does the chitinase scan look for?

It matches annotation text for five groups: GH18, GH19, AA10/LPMO, chitin-binding (CBM) and GlcNAc-related terms.
There is no separate GH20 group.
The patterns are not a validated complete census.
A match supports a capacity hypothesis within the input's scope.
It does not show antifungal activity or an ecological role.

GH18 and GH19 enzymes hydrolyze chitin.
GH20 enzymes act on related fragments.
AA10/LPMO and chitin-binding annotations give different context.
Family and substrate still need the protein evidence.

### What does UMED report?

UMED checks for maturation-associated annotations within 5 kb of loci whose product class needs maturation.
Its verdict separates coupled evidence, a maturation gap and a product that is not maturation-gated.
It does not show a full maturation set and does not detect every precursor.
The short-RiPP scoring rule is separate.
It uses product wording, edge geometry and span.

### What does a resistance gene next to a BGC suggest?

It can suggest a self-protection hypothesis and a candidate target class.
Class fit, location and mobile-element evidence all matter.
A nearby resistance gene can be unrelated or acquired.
The scan reads annotations, so it does not prove self-resistance or the product's mechanism.
`RES_CLASS_CONCORDANCE` relates resistance families to compatible compound classes.
Agreement supports a coherent story and is not proof.

### Why is there an APH sugar-kinase veto?

Some housekeeping sugar kinases are annotated like aminoglycoside phosphotransferases.
The veto stops them from adding resistance or class evidence.
Read a motif match together with its functional context.

### What are the bldA tiers?

bldA encodes the tRNA for the rare TTA leucine codon in many actinomycetes.
TTA-bearing genes can be under that regulatory control.
The scan counts TTA codons in each BGC.
T1 is zero, T2 is one or two, T3 is three to five, and T4 is six or more.
For a recognized non-actinomycete the tier reads `NOT_APPLICABLE`, and the counts are kept.
An unlisted genus can stay unknown.
Unknown applicability is not positive evidence.
A count does not measure expression or timing in your strain.

### What does the TFBS scan do?

TFBS means transcription-factor binding site.
The scan looks for motifs of regulator families such as DasR, BldD, DmdR1, FuR and SARP.
DasR is linked to GlcNAc metabolism, which can motivate a chitin-related hypothesis.
A predicted motif does not show binding, expression or induction.

### Does isolation source affect how I read the scans?

Isolation source can raise a question.
It cannot supply missing genes or activity evidence.
Apply the same evidence standard in every habitat.
Report isolation source and geography exactly as deposited.
Do not infer or bin them from a label.

### Do all ten scans run on the whole genome?

No.
Check each scan's input, scope and status.
RG-GMCI, for example, starts as `PENDING_NOT_RUN` and is filled in when the run has the ClusterBlast context.
`tools/build_first_pass_scans.py` renders selected manifest evidence into the first-pass page.
Rebuilding the page does not rerun any scan.

## Standing rules and special cases

A standing rule is a fixed, registry-defined rule that changes how a class of locus is ranked.
Rules are listed in [the rules registry](../../mamey/data/rules_registry.json).
The rule that fired shows up in the record's flags and rationale.

### What does the NAPAA rule allow?

The registry marks NAPAA as neutral: action `none`, `lead_blocking = false`.
The class stays open to evidence-based comparison.
A label alone does not show habitat association, expression or activity.

### How is hglE-KS-PREV-001 handled?

hglE is a ketosynthase-associated annotation that often marks a generic glycolipid locus.
Two parts of the tool treat it differently, so read the record, not the registry note.

- The registry marks the rule informational, with action `flag` and `lead_blocking = false`.
- In `triage_bgcs`, a separate branch checks the BGC's own product annotations for hglE.
  If no other standing rule was chosen and no CCTT trigger fired for that BGC, it assigns the rule.
  The record then takes its class-dependent bottom tier: Inventory for housekeeping-only products, otherwise Low.
  Raw AB, AF and novelty scores stay, and `corrected_rank` is unset.

A CCTT trigger suppresses that branch.
hglE seen only in a KCB anchor does not trigger it.
The enediyne-artifact guard is separate.
So expect a downgrade in `triage` output when the conditions above hold, even though the registry text says "ranks as a normal lead".

### Why is the saccharide class downgraded?

The rule targets a weak call whose own products are saccharide only.
It does not reject glycosylation in general.
A locus with a committed backbone keeps its status when it also has a saccharide tailoring arm.
Saccharide wording seen only in a KCB anchor is a different case.
A downgrade or an exemption says nothing about production or activity.

### What is the enediyne [E-signal]?

It is a neutral note that marks enediyne-related cytotoxicity and self-protection for review.
It is not a biosafety class.
The tool does not set a per-BGC BSL-2 flag, because an unflagged locus would look cleared.
No note is not safety clearance.
The enediyne-versus-hglE annotation-artifact question is a separate check.

### What does "genome-grounded, proteome-scope-gated" mean?

Genome-grounded: a capacity claim rests on admitted genomic evidence.
Proteome-scope-gated: a verdict records what was searched.
A BGC-region scan cannot show absence across a proteome.

### What is DAPR?

DAPR is a compound-class framework.
Recognizing a chemotype and giving it a scoring effect are separate steps.
Do not assume every recorded class feeds AB or AF.
Read [the class framework](../DAPR_CLASS_FRAMEWORK.md) and the scorer.

### How does a chemotype annotation work?

It reads the domain architecture at class level.
Domain sets can support a statement such as "reducing PKS" or "hybrid PKS–NRPS capacity".
They do not identify the final molecule.
Some classes affect scoring and some are annotation only.

## Biosynthetic biology in brief

### What are PKS, NRPS and a megasynthase?

PKS is polyketide synthase, which extends carbon backbones.
NRPS is nonribosomal peptide synthetase, which links amino-acid-derived units without a ribosome.
Hybrids combine both.
Large modular enzymes are called megasynthases.
Their size makes assembly splits likely, so check for fragmentation.
Module order informs a capacity hypothesis but does not fix the product.

### What are the core PKS and NRPS domains?

PKS: KS extends the chain, AT picks the acyl unit, and ACP carries the chain.
KR, DH and ER set the reduction state.
TE usually releases or cyclizes.

NRPS: the A domain selects and activates a substrate, T/PCP carries it, and C joins units.
E domains change stereochemistry, and TE releases the product.

These help you read the assembly line.
They do not confirm the substrate or the final structure.
The Stachelhaus code predicts an A-domain's substrate from its binding-pocket residues.
It is a prediction and can be uncertain for unusual substrates.

### What is a RiPP and a maturation enzyme?

A RiPP is a ribosomally synthesized and post-translationally modified peptide.
A precursor peptide is remodeled by maturation enzymes.
An annotated precursor alone does not show the mature product.
Lanthipeptides have lanthionine cross-links.
Lasso peptides have a threaded ring-and-tail shape.
No class guarantees a HIGH tier or antibacterial activity.

### What do HSAF and PTM mean?

PTM is polycyclic tetramate macrolactam, a chemotype tied to hybrid PKS–NRPS machinery.
HSAF is Heat-Stable Antifungal Factor, one characterized reference product.
They are related but not interchangeable.
A PTM-type trigger supports a class-level capacity hypothesis.
It does not show HSAF production or give the query locus that compound's antifungal mechanism.

### What can a nikkomycin-like annotation show?

Nikkomycin and polyoxin are nucleoside compounds that inhibit chitin synthesis in characterized cases.
A nucleoside trigger plus family and chitin context can motivate an antifungal-capacity hypothesis.
The scorer may give diagnostic credit when its guards pass.
It does not show nikkomycin production, inhibition by your strain or therapeutic selectivity.

### What does a halogenase tell me?

A halogenase adds halogens, which can change a molecule's properties.
Its presence does not say which substrate was modified or whether activity improved.
HAL and XHAL context does not define a compound class or earn a class tier floor by itself.

### What is self-resistance, and what is resistance-directed mining?

A producer can protect itself by modifying a target, exporting the product or inactivating it.
A compatible gene near a BGC can motivate that reading.
Not every producer keeps protection next to its cluster, and not every nearby resistance gene is self-resistance.
Resistance-directed mining uses such genes to flag loci for review.
The current scan reads annotations only.
It does not find duplicated target genes.

### How do HMMER and BLAST differ, and what is a marker?

BLAST asks what one sequence resembles.
A profile HMM models a whole family from an alignment.
The two give complementary evidence.
Mamey mostly reads antiSMASH's domain and cluster-search results instead of repeating those searches.
A marker in this bundle is usually a curated annotation rule, not a fresh HMM search.
Read the rule before you describe its detection power.
Family accessions (Pfam, TIGRFAM, dbCAN) must be checked against the source database, never typed from memory.
GH, AA and CBM labels are not Pfam or TIGRFAM accessions.

For the parser and test internals behind these answers, see the [Encyclopedia](03_Technical_Manual_Encyclopedia.html).

---

*Sapote–Mamey Concepts Q&A · current to bundle v9.7.464 / engine Mamey 1.9.180.*
