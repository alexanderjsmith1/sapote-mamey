# Sapote–Mamey · Concepts Q&A

Use this page to understand what the pipeline evidence means and where an interpretation must stop.
Definitions are in the [glossary](../GLOSSARY.md).
Detailed implementation context is in the [Encyclopedia](03_Technical_Manual_Encyclopedia.html).

*Current to bundle v9.7.461 / engine Mamey 1.9.177.*

## Contents

- [Evidence and interpretation](#evidence-and-interpretation)
- [Software and data handling](#software-and-data-handling)
- [Genome evidence channels](#genome-evidence-channels)
- [Scores and comparison](#scores-and-comparison)
- [Standing rules and claim limits](#standing-rules-and-claim-limits)
- [Search methods and file formats](#search-methods-and-file-formats)
- [Biosynthetic biology](#biosynthetic-biology)

Start with the evidence and interpretation questions before reading scores as biological findings.

## Evidence and interpretation

<a id="part-2--question-bank-answers"></a>

### Bank 1 · Why split the pipeline into Mamey (deterministic) and Sapote (judgment), and what does each layer guarantee?

Mamey extracts and computes evidence from antiSMASH results.
Sapote authors an interpretation of that evidence.
The separation lets a reader audit a biological judgment against the records and rules that support it.

Deterministic code can still contain parsing, joining or scoring defects.
Traceable inputs and focused checks make those defects inspectable.
Reproducibility applies within the recorded input, configuration and environment scope; it does not promise identical timestamps or every package byte.
Judgment remains fallible and needs source review.
See [the shared contract](../../AGENTS.md).

### Bank 6 · What is Mode B, and what are its named profiles?

Mode B is an authored interpretation of one BGC under a named section contract.
The card connects locus identity, architecture, comparator evidence, alternatives and a claim-safe verdict.
It must identify the BGC as strain / full node-or-contig / region / BGC alias from one bound record.

Default `full48` uses `FINISHED_FULL48_CURRENT_EVIDENCE`.
Opt-in `current50_v2` uses `FINISHED_FULL50_CURRENT50_V2`.
Use the same explicit `--contract` for template emission and verification of the saved authored file.
The [profile matrix](../MODEB_PROFILE_MATRIX.md) identifies the machine-readable contracts and their scope.

A template, top-leads table or register count is not a finished interpretation.
Filling every section does not establish scientific completeness or verified literature support.
`PASS_STRUCTURE` reports structure; `operator_supplied` records provenance; `citation_needed` remains unresolved.
Read the actual verification report and inspect the evidence behind the claims.
See [the authoring walkthrough](../MODE_B_USER_WALKTHROUGH.md).

### Bank 7 · Observed / computed / inferred / assumed — what's the difference?

These labels describe how a claim was obtained.
They let a reader inspect each reasoning step separately.

| Label | Meaning | Generic example |
|---|---|---|
| Observed | Present in a named source | A manifest records a PKS product annotation. |
| Computed | Produced by a stated rule | An Edge record contributes the configured boundary weight. |
| Inferred | Interpreted from evidence | A domain set supports a chemotype hypothesis. |
| Assumed | Used without confirmation | The submitted genome has the identity on its label. |

An observed annotation can itself be a prediction made by the upstream tool.
The label does not turn that prediction into experimentally observed chemistry.

### Bank 8 · Why are supplied bioactivity observations strain-level and never pinned to one BGC?

An assay result belongs to its recorded strain, material, target and conditions.
Co-occurrence with a BGC does not identify that BGC as the source of activity.
A similarity match does not supply the missing causal evidence.

The `bioactivity_metadata_v1` input contract requires `compound_linkage = NOT_ESTABLISHED`.
It does not admit locus-linkage claims.
Preserve the measured observation separately from predicted biosynthetic capacity.
See [the bioactivity metadata contract](../BIOACTIVITY_METADATA_CONTRACT.md).

<a id="bank-9--why-can-a-strain-never-be-called-antifungal-negative"></a>

### Bank 9 · What does a negative or missing bioactivity result mean?

Missing assays, failed measurements and untested strains are not negative results.
A valid measured negative can be reported for its actual material, target and assay conditions.
It does not establish absence of all activity or biosynthetic capacity.

The metadata contract distinguishes `NOT_SUPPLIED / NOT_OBSERVED` from `MEASURED_NEGATIVE / NEGATIVE`.
Keep those states separate in tables and comparisons.
Compare phenotypes only when the underlying assay evidence is comparable.

### Bank 10 · What is a hallucination-trap / evidence-conservation check?

An evidence check asks whether a reported identifier, number or claim is supported by its bound source.
Reconciliation checks compare values derived through different routes, such as a manifest count and a report count.
A disagreement requires diagnosis; it does not identify which route is wrong.

Evidence conservation means carrying source values, uncertainty and missing states through parsing and summarization.
Do not silently drop conflicting records or replace unknown values with zeros.
A passed check supports only the fields and cases it actually examined.


## Software and data handling

<a id="part-1--conversational-thread-q1q10"></a>
<a id="part-1--conversational-thread-q1q11"></a>

### Q4 · What is a chunk?

A chunk is a piece of a larger input or output.
Its meaning depends on the context.
Retrieval chunks are excerpts selected for search; they can omit a qualifier elsewhere in the source.
Read the surrounding source before relying on an excerpt for a substantive claim.

Streaming chunks and parser events are different from retrieval excerpts.
In Mamey, record iteration and the main evidence walker have separate loading and retention rules.
Streaming one path does not show that every path avoids whole-file loading.
See Q10 and Bank 70 below.

### Q5 · What is parsing?

Parsing recognizes a file's structure and turns it into objects a program can inspect.
For example, a JSON parser distinguishes a record, its fields and the values within a list.
Recognizing that structure does not establish that the source annotation is biologically correct.

Mamey reads antiSMASH JSON and GenBank annotations through its parsing and evidence paths.
Schema changes, missing fields and incorrect joins can affect the resulting evidence.
Keep source pointers and explicit refusal or missing states so those problems can be diagnosed.
See [`mamey/parsers.py`](../../mamey/parsers.py) and [`mamey/antismash_evidence.py`](../../mamey/antismash_evidence.py).

### Q6 · What is CGAD?

CGAD means Chitinase Genome Architecture Detection.
The current chitinase channel matches annotation text for GH18, GH19, AA10/LPMO, chitin-binding/CBM and GlcNAc-related terms.
Those patterns are evidence from the supplied records, not a validated complete enzyme census.

Record whether the input covers a whole proteome or only selected BGC regions.
An annotation match can support a capacity hypothesis within that scope.
It does not establish antifungal activity or an ecological role.
See [`mamey/source_scans.py`](../../mamey/source_scans.py), Bank 34 and Bank 88.

### Q7 · What other project jargon is there?

Start with the canonical [glossary](../GLOSSARY.md) for definitions.
Use this page for what a term permits you to conclude.

| Term | What to inspect |
|---|---|
| KCB | Similarity evidence and search provenance, not product identity. |
| RG-GMCI / EFLS | Candidate relationships with both complete locus identities. |
| FLBR | Fragmentation context, not a reconstructed pathway. |
| CCTT / resistance | Source matches, class context and scoring eligibility. |
| CGAD / UMED | Input scope and the actual source-derived verdict. |
| bldA / TFBS | Counts, taxonomy applicability and regulatory uncertainty. |
| AB / AF / lead class | Prioritization evidence, not measured activity. |

A public-looking identifier does not establish disclosure permission.
Use the recorded privacy profile and explicit authority for the actual input.

### Q8 · Are there more bacterial chitinases to scan for?

GH19 is already present in `CHITINASE_PATTERNS`.
The current dictionary also includes GH18, AA10/LPMO, chitin-binding/CBM and GlcNAc-related wording.
It has no separately named GH20 bucket.

A pattern's presence does not establish validated family-specific recall or substrate specificity.
Review the actual annotations and scope before describing a detection gap.
Adding markers requires verified family definitions and focused positive and negative controls.
See [`mamey/source_scans.py`](../../mamey/source_scans.py) and Bank 88.

### Q9 · What is idempotent?

An operation is idempotent when repeating it with the same relevant state leaves the same result as applying it once.
Assigning a value is a simple example; incrementing a counter is not.

The property needs a defined scope.
A repeated update can still overwrite a source, append a log or fail partway through several writes.
Changing inputs and external side effects need separate review.
Idempotence does not provide execution permission, preserve earlier snapshots or establish release authority.

### Q10 · What exactly is ijson used for in Sapote–Mamey?

ijson supports incremental reading of large antiSMASH JSON.
The record iterator can stream one record at a time; smaller files or an unavailable parser can follow a full-loading path.
One streamed record can still be large.

The bounded evidence walker is a separate path.
It retains selected evidence and records truncation; it still reads the member.
If neither available ijson copy can be used, bounded mode switches to `off` and records that change.
It does not fall back to a full evidence load.

`--json-evidence full` is an older selective flatten with a member-size refusal.
It is not a completeness or memory guarantee.
Check requested and effective modes, walk receipts and retained evidence.
See [`mamey/antismash_evidence.py`](../../mamey/antismash_evidence.py).


## Genome evidence channels

<a id="bank-16--why-retire-665033-for-704520"></a>

### Bank 16 · What does the assembly tier describe?

The assembly tier summarizes the percentage of regions labeled Interior.
Current thresholds are GOOD at 70%, MODERATE at 45%, POOR at 20%, and VERY_POOR below 20%.
An unavailable percentage yields UNKNOWN.

This is a boundary-derived heuristic, separate from source-contig statistics such as N50.
Read the raw boundary distribution and locus-specific uncertainty alongside it.
A whole-genome tier is not evidence that every locus is complete.
See [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 20 · What is "KCB-dark," and why is it a novelty signal?

KCB-dark describes a locus without a meaningful reported match in an admitted KnownClusterBlast search.
An absent, unavailable or unbound search is a different state.
Retain the search and database provenance before interpreting a no-match result.

Dark status can motivate novelty review when coherent architecture and supporting markers are present.
It does not establish new chemistry, expression or activity.
An incomplete or uninformative locus can also lack a match.

### Bank 22 · What is RG-GMCI?

RG-GMCI means Reference-Guided Genome Mining Candidate Inference.
It proposes fragmented-locus relationships from shared reference support and geometry.
Both overlapping and adjacent reference intervals can supply useful geometry.
Locus-tag proximity can provide a coarser proxy when coordinates are unavailable.

Keep cross-genome ClusterBlast evidence separate from characterized KnownClusterBlast evidence.
SubClusterBlast is retained outside the pairing pool.
A HIGH label does not prove physical continuity or exclude paralogy.
Inspect both complete endpoints, alternatives and availability states in [the channel guide](../reference/04_RGGMCI_ClusterBlast_Utilization.md).

### Bank 23 · What is CCTT, and how do the T43-* triggers work?

CCTT is the compound-class trigger table.
Its T43 labels identify configured annotation-pattern matches.
A hit count and a count of distinct BGCs carrying hits answer different questions.
Repeated matches within one locus do not imply several independent pathways.

Scoring eligibility additionally depends on class compatibility and source-context guards.
Do not treat every fired pattern as corroborated diagnostic credit.
See [`mamey/source_scans.py`](../../mamey/source_scans.py) and [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 24 · What are the T43 families?

The exact T43 roster is defined by `CCTT_PATTERNS`, not by an old prose count.
The labels distinguish classes and tailoring context; TET means tetronate/spirotetronate, not tetracycline.
Current families use the short labels HAL, XHAL, PHO, NUC, BLA, AMC, ENE, LAN, LASSO, THA, DKP, IDC, PTM, TET, NN, PYE, GPA and BLT.
For orientation, PHO concerns phosphonate, NUC nucleoside, PTM polycyclic tetramate macrolactam, and LAN/LASSO their corresponding RiPP classes.

Dictionary membership, corroboration, an axis bonus and tier-floor eligibility are separate contracts.
For example, halogenation context does not itself define a compound class.
Read the configured source and scorer before interpreting a trigger's effect.
See [`mamey/source_scans.py`](../../mamey/source_scans.py) and [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 25 · What is FLBR / a fragmented megasynthase?

FLBR summarizes megasynthase annotation patterns and fragmentation context.
PKS/NRPS machinery on Edge or Full-contig records can motivate review of a possible split pathway.
STRONG and WEAK are heuristic flags.

The census does not reconstruct an assembly line or prove that scattered genes belong to one pathway.
Review complete locus identities and pair-specific evidence before linking records.
See [`mamey/source_scans.py`](../../mamey/source_scans.py).

### Bank 26 · What is UMED / an "in-cluster vs GAP" verdict?

UMED checks selected maturation-associated annotation patterns near declared maturation-gated product classes.
Its source-derived verdict distinguishes coupled evidence, a maturation gap and a non-gated product.
The current proximity check uses a 5 kb flank.

It does not establish a full maturation complement or detect every precursor.
The separate short-RiPP scoring rule uses product wording, Edge/Full-contig geometry and span.
It does not directly test precursor absence or use the UMED gap as its trigger.
See [`mamey/source_scans.py`](../../mamey/source_scans.py) and [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 27 · How does EFLS differ from RG-GMCI?

EFLS proposes preliminary pairs from shared product, reference, cassette and trigger labels over a capped input set.
It skips pairs whose records are both exactly Interior.
It does not compare raw contig ends or prove complementary sequence tiles.
Different contigs are not required by that preliminary check.

RG-GMCI uses its separate reference/geometry contract.
Shared annotations can feed both methods, so agreement is not automatically independent evidence.
Neither output establishes physical continuity.
See [`mamey/source_scans.py`](../../mamey/source_scans.py) and the [RG-GMCI guide](../reference/04_RGGMCI_ClusterBlast_Utilization.md).

### Bank 28 · What is the resistance scan, and what does a resistance gene next to a BGC suggest?

Resistance-associated annotations near a BGC can suggest a self-protection hypothesis and a candidate target class.
For example, ribosomal modification and cell-wall resistance cassettes provide different mechanistic context.
The interpretation also depends on class concordance, location and mobile-element evidence.

A nearby resistance gene can be unrelated or acquired.
An annotation scan does not prove self-resistance or the product's mechanism.
Keep that uncertainty separate from the current resistance evidence in [`mamey/source_scans.py`](../../mamey/source_scans.py).

### Bank 29 · What is the APH-sugar-kinase veto, and why is it needed?

Some housekeeping sugar kinases resemble aminoglycoside phosphotransferase annotations.
The APH-sugar-kinase veto suppresses that context-dependent false-positive route.
Otherwise a housekeeping match could contribute misleading resistance or downstream class evidence.

The lesson is that a motif match and its functional context must be read together.
The veto does not establish experimentally measured susceptibility or resistance.
See [`mamey/source_scans.py`](../../mamey/source_scans.py).

### Bank 30 · What is the bldA/TTA tiering, and what does the rare codon have to do with secondary metabolism?

bldA encodes the tRNA associated with the rare TTA leucine codon in relevant actinomycetes.
That biology motivates examining TTA-bearing genes as regulatory context.
The scan's T1–T4 labels describe counted TTA burden: zero, one or two, three to five, and six or more.

These labels are not the resistance scan's tiers.
A count does not measure expression, growth-phase control or inducibility in the submitted strain.
Check taxonomy applicability and the actual CDS scope in [`mamey/source_scans.py`](../../mamey/source_scans.py).

<a id="bank-31--why-does-blda-emit-spurious-t4-on-non-actinomycetes-p-11"></a>

### Bank 31 · When does bldA/TTA interpretation apply?

The current bldA scan reports per-BGC NOT_APPLICABLE when its taxonomy resolver recognizes a non-actinomycete.
It still retains source counts.
An unlisted genus can remain unknown rather than being gated out.

Review taxonomy and applicability before interpreting a TTA tier.
Unknown applicability is not positive evidence for a developmental mechanism.
See [`mamey/source_scans.py`](../../mamey/source_scans.py).

### Bank 32 · What is TFBS scanning, and which regulator families matter?

TFBS means transcription-factor binding site.
Regulatory motifs can suggest candidate control by families such as DasR, BldD, DmdR1, FuR or SARP.
DasR's connection to GlcNAc metabolism can motivate a chitin-related regulatory hypothesis.

A predicted motif does not establish binding, expression or induction under particular conditions.
Record the source sequence or annotation scope and the actual scan state.
See [`mamey/source_scans.py`](../../mamey/source_scans.py).

### Bank 33 · What is RES_CLASS_CONCORDANCE?

`RES_CLASS_CONCORDANCE` relates resistance families to compatible compound-class hypotheses.
Agreement can support a coherent interpretation of a locus.
A mismatch can indicate an unrelated determinant or an uncertain class annotation.

Concordance is not proof of the product or its target.
Keep mobile context and shared annotation sources visible when weighing the evidence.
See [`mamey/source_scans.py`](../../mamey/source_scans.py).

### Bank 34 · What does "genome-grounded, proteome-scope-gated, NOT isolation-source-gated" mean?

Genome-grounded means that a capacity interpretation rests on admitted genomic evidence.
Proteome-scope-gated means that the verdict records what was actually searched.
A BGC-region scan cannot establish absence across a whole proteome.

Isolation source can motivate a question, but it cannot supply missing genes or activity evidence.
Apply the same evidence standard across habitats.
Retain isolation source and geography as deposited rather than inferring either from a label.

### Bank 35 · Why ten scans, and how do they feed the first-pass page?

The ten-scan overview describes evidence channels; it is not a receipt that all channels ran genome-wide.
Check each channel's inputs, scope and effective status.
For example, RG-GMCI can initially be `PENDING_NOT_RUN` while its reference context is supplied separately.

`build_first_pass_scans.py` renders selected manifest evidence.
Rebuilding that page does not rerun the underlying scans or establish complete source coverage.
See [`mamey/source_scans.py`](../../mamey/source_scans.py) and [`tools/build_first_pass_scans.py`](../../tools/build_first_pass_scans.py).


## Scores and comparison

### Bank 36 · How is a score like AB76 built?

AB and AF are versioned capacity/routing scores, not measurements of activity.
The scorer combines eligible class, chemotype and diagnostic evidence with source-context guards.
Some guards limit credit; rescue context, bounds and tier handling also affect the final result.
Read the complete per-record rationale rather than treating one baseline or bonus as the formula.

The retained `edge_penalty` currently returns zero.
Boundary-weighted BGC counts and architecture uncertainty remain separate from axis-score deductions.
NAPAA is neutral in the registry.
The hglE registry note is informational, but a separate scorer branch can still downgrade own-product hglE annotations.
Bank 47 explains that branch and its CCTT exemption.
See [`mamey/scoring.py`](../../mamey/scoring.py) and [the rules registry](../../mamey/data/rules_registry.json).

### Bank 37 · What are lead classes A/B/C, and why doesn't class raise claim confidence?

Lead classes summarize the support for prioritizing a candidate.
They do not establish confidence in a named product.
Several agreeing annotations can strengthen a review case while leaving expression and activity untested.

Keep the claim at the level supported by the evidence.
A well-supported capacity hypothesis remains a capacity hypothesis until corresponding product or activity evidence exists.

### Bank 38 · What is the diagnostic floor / marker-aware scoring?

Eligible corroborated diagnostics can raise an axis score or impose a tier floor.
That allows architecture and marker evidence to contribute when similarity evidence is weak or absent.

A scoring floor is a prioritization rule, not an assay result.
Bind each marker to the complete source locus and inspect class-context guards.
Do not infer a named compound, expression or antifungal activity from the floor.
See [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 39 · What is DAPR, and why is wiring DAPR scoring a "scoring boundary"?

DAPR is a compound-class framework.
Recognizing a chemotype and assigning it a scoring consequence are separate decisions.
Do not assume that every recorded class contributes to AB or AF.

Changing which annotations feed the scorer can change comparisons across runs.
Review the actual framework and scoring implementation before crossing that boundary.
See [the framework](../DAPR_CLASS_FRAMEWORK.md) and [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 40 · What is a scoring boundary?

A scoring boundary changes the rules that produce scores, counts or priority tiers.
Results across that boundary may no longer be directly comparable.

Record the engine, configuration and admitted evidence for each run.
An editorial change does not itself cross a scoring boundary.
A release label alone does not demonstrate unchanged numerical behavior.

<a id="bank-41--why-must-the-cohort-be-re-scored-before-cross-strain-claims"></a>

### Bank 41 · When must results be re-scored before comparison?

Comparative scores need a common, compatible scoring and evidence basis.
Re-scoring is required when a scoring boundary or changed evidence contract would otherwise mix incompatible results.
Different version labels alone do not show which numerical rules changed.

Use one documented engine/configuration for an admitted comparison and retain denominators, strictness and assembly context.
Re-scoring does not cure differences in sampling or assay design.

### Bank 42 · What are the evidence axes, and how do they combine into a verdict?

Architecture, similarity, diagnostic markers, regulation and completeness answer different questions.
Keep those contributions visible rather than letting one score hide disagreement.
For example, weak similarity and coherent biosynthetic architecture can motivate further review without proving novelty.

Several outputs can reuse the same upstream annotation.
Do not count that shared source as independent corroboration twice.
The verdict should explain the supported interpretation and the alternatives still open.

### Bank 43 · What is the WL tier / priority tiering?

WL means watchlist.
It retains a candidate signal whose curation or evidence is insufficient for stronger interpretation.
Watchlist context does not establish a scored lead or a confirmed mechanism.

Review the marker's tier, confidence and confirmation requirements in [`mamey/sapote_markers.py`](../../mamey/sapote_markers.py).
Additional evidence needs its own review before the claim changes.
Do not treat a proposed confirmation route as a completed result.

### Bank 44 · What is the promiscuity cap, and what is it preventing?

The promiscuity cap limits one BGC's contribution to class-capacity accounting.
This prevents a large hybrid region from contributing unlimited apparent breadth through several class labels.
Fragment handling adds separate restrictions.

The capped tally is an accounting convention, not a count of measured products or an estimate of biological diversity by itself.
Read its units and configuration in [`mamey/cnbu.py`](../../mamey/cnbu.py).

### Bank 45 · How does the compound-class annotation layer pick a chemotype?

A chemotype annotation interprets biosynthetic architecture at a class level.
Domain combinations can support descriptions such as a reducing PKS or a hybrid PKS–NRPS capacity.
They do not identify the final molecule.

Some class context has a scoring consequence and some remains annotation-only.
Keep the architecture evidence and the actual scoring rule separate.
See [the class framework](../DAPR_CLASS_FRAMEWORK.md) and [`mamey/scoring.py`](../../mamey/scoring.py).


## Standing rules and claim limits

### Bank 46 · What does the current NAPAA rule permit?

The registry records NAPAA as neutral, with action `none` and `lead_blocking = false`.
The former Nosema hypothesis remains retired.
That retirement does not exclude the class itself from evidence-based comparative interpretation.

Use the actual admitted observations, denominator and assembly context.
A label alone does not establish habitat association, expression or activity.
See [the rules registry](../../mamey/data/rules_registry.json) and [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 47 · How should hglE-KS-PREV-001 be interpreted?

The registry and scorer currently have different effects.
The registry marks `HGLE-KS-PREV-001` as informational, with action `flag` and `lead_blocking = false`.
Its note is not a complete description of scoring behavior.

In `triage_bgcs`, a separate branch examines the BGC's own product annotations for hglE.
If no standing rule is already selected and no CCTT trigger is present for that BGC, it assigns `hglE-KS-PREV-001`.
The record then receives its class-dependent bottom tier: Inventory for housekeeping-only products, otherwise Low.
Its raw AB, AF and novelty scores remain, but `corrected_rank` is unset.

A CCTT trigger suppresses that direct hglE branch; other guards and exclusions can still apply.
hglE appearing only in a KCB anchor does not activate the own-product branch.
The separate gene-level enediyne-artifact guard also remains distinct.
Read the record's actual flags and rationale rather than assuming normal lead eligibility from the registry note.
See [`mamey/scoring.py`](../../mamey/scoring.py) and [the rules registry](../../mamey/data/rules_registry.json).

### Bank 48 · Why is the saccharide class downgraded?

The saccharide standing rule addresses a weak, saccharide-only product-class call.
It does not reject glycosylation wherever it occurs.
A committed biosynthetic backbone can retain its status when it also carries a saccharide tailoring arm.

The rule uses the BGC's own products; saccharide wording only in a KCB anchor is a different case.
Neither a downgrade nor its exemption establishes production or activity.
See [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 49 · What is the enediyne [E-signal], and why was the per-BGC BSL-2 flag retired?

The neutral [E-signal] note marks enediyne-related cytotoxicity and self-protection review context.
It is not a per-BGC biosafety classification.
The former selective BSL-2 flag could imply that unflagged loci were cleared, which was not established.

Keep the genuine enediyne-versus-hglE annotation-artifact question separate from a safety verdict.
An absent note is not safety clearance.
See [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 50 · What does "KCB = similarity, not identity" prevent in practice?

KnownClusterBlast compares evidence of related biosynthetic genes, not the query strain's isolated product.
Related machinery can support a class-level hypothesis while differing in substrates, tailoring or expression.

Report similarity with its actual coverage, reference and source context.
Do not replace “similar to a characterized cluster” with “produces that compound.”
The scorer's mis-anchor guard is a separate check on eligible credit, not experimental confirmation.


## Search methods and file formats

### Bank 66 · HMMER vs BLAST — what's the difference?

Pairwise sequence searches ask what a particular sequence resembles.
A profile HMM represents a family using patterns learned from a multiple alignment.
These methods supply complementary evidence at different levels.

Mamey generally reads the admitted antiSMASH domain and cluster-search results rather than repeating every upstream search.
Keep the actual method, database and version with the result.
Do not infer which executable ran from a tool label alone.

### Bank 67 · What is a profile HMM / a marker?

A profile HMM is a statistical sequence-family model.
A marker in this bundle is often a curated annotation-detection rule, rather than a fresh HMM search.
The registries record patterns, tiers and confidence for interpreting supplied evidence.

Read the actual rule before describing its detection power.
An annotation regex and a family-model search have different coverage and failure modes.
See [`mamey/mamey_markers.py`](../../mamey/mamey_markers.py) and [`mamey/sapote_markers.py`](../../mamey/sapote_markers.py).

### Bank 68 · What are Pfam / TIGRFAM / dbCAN accessions, and why are they never quoted from memory?

Protein-family identifiers name particular database entries or family categories.
An accession and its associated model must be verified against the source used in the analysis.
Do not invent a precise-looking identifier from memory.

GH, AA and CBM family labels are not interchangeable with Pfam or TIGRFAM model accessions.
Retain the database, version and source evidence when interpreting a family call.

### Bank 69 · What is BLAST, and what does KnownClusterBlast actually compare?

BLAST finds local sequence similarity.
KnownClusterBlast uses protein-similarity and cluster context to compare a query BGC with characterized reference clusters.
Read the actual antiSMASH method and database provenance rather than assuming an executable from the name.

Coverage, gene correspondence and similarity strength matter.
A thin match and a broad match do not support the same interpretation.
Neither establishes the query product's identity.

### Bank 70 · What is "bounded" streaming, and what is the leaf budget?

Bounded mode limits selected auxiliary evidence retained by the main JSON walker.
Reaching the auxiliary leaf budget marks truncation but does not stop all later traversal.
Region-mapped RiQ evidence has separate authority and group limits.

Inspect `walk_complete`, truncation, mapped/unassigned counts and holds.
Bounded retention is not a guarantee of flat memory, bounded runtime or complete upstream evidence.
See [`mamey/antismash_evidence.py`](../../mamey/antismash_evidence.py).

### Bank 71 · What is the Decimal-vs-float gotcha?

Some streaming parsers represent JSON numbers as Decimal values, which default JSON serialization cannot directly encode.
The record-streaming path uses `use_float=True`.
The bounded walker separately accepts numeric Decimal RiQ values and converts admitted scores to float.

That representation choice does not establish whole-document parity or show that every parser uses the same path.
Keep mode and source scope with any comparison.
See [`mamey/antismash_evidence.py`](../../mamey/antismash_evidence.py).

### Bank 72 · What is a regression test, and what makes a "negative control" test?

A regression test preserves a specific expected behavior so a later change cannot silently break it.
A negative control checks that a signal stays absent for a defined input that should not trigger it.
Both need justified expectations.

Focused controls can catch annotation-context false positives and taxonomy-applicability defects.
A passing test supports its tested cases, not every genome or a universal biological rule.

<a id="bank-73--what-is-an-xfail-and-why-is-isid-xxx-kept-as-an-xfail-tripwire"></a>

### Bank 73 · What do xfail and XPASS mean?

`xfail` marks an expected test failure.
An unexpected pass is an XPASS; its effect depends on strictness and configuration.
Read the actual result instead of assuming every XPASS fails the suite.

The historical ISID example is now an ordinary assertion test, not a current xfail tripwire.
It can skip when the required asset is unavailable.
See [`tests/test_mibig_no_redaction_corruption.py`](../../tests/test_mibig_no_redaction_corruption.py).
An executed assertion and a skip support different claims.

### Bank 76 · What is a GBK file, and what is the _gbk_shim for?

A GenBank file stores sequence, features, coordinates and qualifiers.
antiSMASH region GBKs carry annotations used by Mamey.
The bundled `_gbk_shim` is a minimal reader for selected record shapes.

The core `read_genbank_records` path tries Biopython first and uses the shim when that import is unavailable.
Other callers can select the shim directly.
The fallback does not establish complete GenBank-format coverage.
See [`mamey/parsers.py`](../../mamey/parsers.py) and [`mamey/_gbk_shim.py`](../../mamey/_gbk_shim.py).


## Biosynthetic biology

### Bank 78 · What is a PKS vs an NRPS, and what is a megasynthase?

PKS means polyketide synthase; NRPS means nonribosomal peptide synthetase.
PKS machinery extends carbon backbones, while NRPS machinery assembles amino-acid-derived units without a ribosome.
Hybrid pathways combine these kinds of chemistry.

Large modular enzymes are often called megasynthases.
Their size makes assembly fragmentation important when interpreting a domain set.
Module order informs a capacity hypothesis, but does not uniquely determine the final product.

### Bank 79 · What are the core PKS domains?

KS catalyzes chain-extending condensation; AT selects/transfers an acyl unit; ACP carries the growing chain.
KR, DH and ER supply successive reduction-related functions that affect oxidation state.
TE commonly contributes release or cyclization.

The domain combination informs an architecture-level hypothesis.
For example, an unreduced segment and one carrying KR/DH/ER support different reduction-state interpretations.
Missing annotations, trans-acting functions and tailoring limit a direct sequence-to-product reading.

### Bank 80 · What are the core NRPS domains?

An NRPS A domain selects and activates a substrate.
The T/PCP domain carries it, and a C domain supports condensation.
E domains can alter stereochemistry; TE domains commonly contribute product release.
Other domains can support heterocyclization, oxidation or methylation.

These functions help interpret the assembly line.
They do not by themselves verify substrate identity or the final peptide structure.

### Bank 81 · What is the Stachelhaus code, and what does it predict?

The Stachelhaus code relates residues in an NRPS A-domain substrate-binding pocket to substrate preference.
It is a prediction based on characterized examples.
Unusual substrates and poorly represented families can remain uncertain.

Retain the actual predictor, confidence and source annotation.
A substrate prediction is one architecture clue, not direct evidence that the finished product was made.

### Bank 82 · What is a RiPP, and what does "maturation enzyme" mean?

A RiPP is a ribosomally synthesized and post-translationally modified peptide.
A translated precursor is remodeled by maturation enzymes that can change connectivity and remove processing segments.
The precursor and maturation machinery therefore contribute different evidence.

An annotated precursor alone does not establish the mature product.
UMED supplies a limited proximity/pattern check, not a complete reconstruction of maturation.
See Bank 26 for that implementation boundary.

<a id="bank-83--what-is-a-lanthipeptide-vs-a-lasso-peptide-and-why-do-they-score-high"></a>

### Bank 83 · What distinguishes a lanthipeptide from a lasso peptide?

Lanthipeptides contain characteristic lanthionine-related cross-links.
Lasso peptides have a threaded peptide topology involving a ring and tail.
Those distinct architectures motivate class-specific interpretation.

Eligible diagnostic evidence can affect scoring, but no class automatically guarantees HIGH priority or antibacterial activity.
Read the actual class guards, completeness context and rationale in [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 84 · What is a halogenase, and why does halogenation matter?

A halogenase catalyzes halogen incorporation.
Halogenation can alter a molecule's properties, making the annotation useful tailoring context.
Its presence does not show which substrate was modified or whether activity improved.

HAL/XHAL context does not itself define a compound class or qualify for a class tier floor.
See [`mamey/scoring.py`](../../mamey/scoring.py) for the actual eligibility rules.

<a id="bank-85--what-are-hsafptm-and-why-do-they-recur-across-the-bee-strains"></a>

### Bank 85 · What are HSAF and PTM?

HSAF means Heat-Stable Antifungal Factor, a name associated with a characterized reference product.
PTM means polycyclic tetramate macrolactam, a broader chemotype associated with hybrid PKS–NRPS machinery.
The terms are related but not interchangeable compound-identification results.

An architecture or trigger match can support a PTM-class capacity hypothesis.
It does not establish HSAF production or transfer a reference compound's antifungal mechanism to the query locus.
Any recurrence claim needs an admitted roster, denominators and comparable evidence.

<a id="bank-86--what-is-nikkomycin-and-why-is-it-the-candida-lead-in-as-xxx"></a>

### Bank 86 · What can a nikkomycin-like annotation establish?

Nikkomycin/polyoxin-style comparisons concern nucleoside compounds associated with chitin-synthesis inhibition in characterized examples.
A compatible nucleoside trigger, family evidence and chitin context can motivate an antifungal-capacity hypothesis.
The configured scorer may assign diagnostic credit when its guards are satisfied.

Those annotations do not establish nikkomycin production, inhibition by the query strain or therapeutic selectivity.
Keep the class-level hypothesis separate from compound identity and measured activity.
See [`mamey/scoring.py`](../../mamey/scoring.py).

### Bank 88 · What are GH18/GH19/GH20 chitinases, and how do they relate to antifungal ecology?

GH18 and GH19 include chitin-hydrolyzing enzymes; GH20 includes related downstream hexosaminidase functions.
Family membership and substrate specificity still need the actual protein evidence.
AA10/LPMO and chitin-binding annotations provide different context from hydrolytic enzyme families.

Current `CHITINASE_PATTERNS` includes GH18, GH19, AA10/LPMO, broad binding and GlcNAc-related wording.
It has no separately named GH20 bucket.
The dictionary alone establishes neither exhaustive detection nor an ecological function.
See [`mamey/source_scans.py`](../../mamey/source_scans.py).

### Bank 89 · What is resistance-gene-directed genome mining?

Resistance-directed mining uses candidate self-protection evidence to motivate review of nearby biosynthetic capacity.
Duplicated or altered target genes can be one research signal, but require evidence that distinguishes them from ordinary duplication or acquired resistance.

The current annotation-based resistance scan is not a completed duplicated-target discovery workflow.
Do not describe a proposed extension as an executed analysis.
See Bank 28 and [`mamey/source_scans.py`](../../mamey/source_scans.py).

### Bank 90 · What is a self-resistance gene, and how does it hint at a product's target?

A self-resistance mechanism protects a producer against its own bioactive product.
Possible mechanisms include target modification, export or inactivation.
A compatible gene near a BGC can motivate that interpretation.

Not every producer colocates protection, and not every nearby resistance gene is self-resistance.
Class concordance and mobile context help evaluate the hypothesis but do not prove the product's target.
Retain the alternative explanations.

---

*Sapote–Mamey Concepts Q&A · current to bundle v9.7.461 / engine Mamey 1.9.177.*
