# Compare green-algal and cyanobacterial records

**Scope and status.** This guide supports planning and review for the requested
green-algal genera *Trebouxia*, *Chlorella* and *Coccomyxa*, and cyanobacteria.
Cyanobacteria are bacteria; keep their source and reference decisions distinct
from eukaryotic algae and fungi. The bundle does not provide a validated
one-command workflow or an outgroup registry for these groups. A label, local
package or record name is a starting lead, not a verified identification.

## Start from existing evidence

Record the biological question and taxonomic scale. Inventory the selected input
records, existing alignments, analysis trees, display trees and reports before
considering a new analysis. Bind each to its original path and SHA-256. For a
public record preserve the exact accession and version, record URL, retrieval
source and date; local bytes need their own hash. Record the source sample,
strain and any asserted relationship between different files. A matching name
alone does not establish that two records represent the same individual.

An antiSMASH results ZIP is not automatically a complete genome or marker
sequence. Identify the relevant member and its provenance before proposing it
for a phylogenetic input. A missing or inaccessible source is **unavailable**;
it is not evidence that the source or organism is absent. Preserve quarantine
and exclusion decisions. Do not silently substitute a different record.

## Keep compartments and lineages distinct

For each eukaryotic record, document whether the evidence is nuclear, plastid,
mitochondrial, mixed or unresolved. Treat organellar and nuclear trees as
separate evidence channels: their histories or sampled taxa can differ. Mixed
source material may also contain multiple symbionts or other organisms. The
claim that a record belongs to the selected photobiont requires independent
source review; sequence similarity or a file label alone does not establish it.

*Trebouxia*, *Chlorella* and *Coccomyxa* require separate reference-roster and
taxonomic-scope decisions. Published studies provide examples, not defaults:
[Trebouxia photobiont study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4204673/),
[Chlorella genus study](https://pubmed.ncbi.nlm.nih.gov/20522192/) and
[Coccomyxa species-concept study](https://pubmed.ncbi.nlm.nih.gov/27028195/).
A broader [green-algal plastid study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4189289/)
illustrates a separate source of phylogenetic evidence. Choose and justify the
actual records and evidence appropriate to the question; do not infer a species
name, an outgroup or a universal marker panel from these examples.

For cyanobacteria, review the actual lineage and reference coverage. The bundle's
existing 16S workflows and actinomycete-specific taxon maps and presets cannot be
presumed appropriate. A [cyanobacterial classification study](https://pubmed.ncbi.nlm.nih.gov/36443823/)
used phylogenomic and 16S evidence and described limitations of 16S at some
broader ranks. Do not apply bacterial species thresholds or outgroups from an
unrelated preset without a source-specific decision. Similarity to a plastid
record does not by itself establish that a query is a cyanobacterial isolate.

### Source-specific example: indexed *Trebouxia* assembly

A [public Zenodo record](https://zenodo.org/records/23749643) lists `GCA_000818905` in a *Trebouxia gelatinosa* archive. [NCBI BioProject PRJNA263654](https://www.ncbi.nlm.nih.gov/bioproject/263654) lists assembly `GCA_000818905.1`, BioSample `SAMN03104849`, and scope “Monoisolate”; the [BioSample](https://www.ncbi.nlm.nih.gov/biosample/SAMN03104849) identifies isolate LA000220 and says the sample was obtained from a mycobiont, with sample type missing. The [Trebouxia Research Portal](https://trebouxia.net/index.php/genomes) instead describes the source material for that assembly as lichen thallus. These descriptions require reconciliation and do not alone determine assembly purity or whether a particular contig belongs to the alga. The [WGS master](https://www.ncbi.nlm.nih.gov/nuccore/JUBA00000000) is a metadata record with no sequence data.

The Zenodo archive and the historical local `TREBOUXIA-SP` package have not been bound to each other or to the versioned assembly bytes. Before using either, verify the exact archive member and assembly version, provenance and relevant record identity; review mixed-organism and compartment questions in the context of the selected analysis. This example is a source lead, not a reference-panel or outgroup choice, and does not authorize downloads or a run.


### Source-specific example: a cyanobacterial chromosome and assembly

[NCBI BioProject PRJNA588357](https://www.ncbi.nlm.nih.gov/bioproject/588357)
lists *Nostoc* sp. ATCC 53789 assembly `GCA_009873495.1` with 13 replicons.
The [genome publication](https://pmc.ncbi.nlm.nih.gov/articles/PMC7118181/)
identifies `CP046703` as the chromosome and `CP046704`–`CP046715` as
additional replicons. A chromosome-labelled record is therefore not, by its
label alone, evidence that a supplied file contains the full assembly.
[Another project](https://www.ncbi.nlm.nih.gov/bioproject/319598) lists a
different assembly under the same strain name. Bind the actual source and
accession versions, and decide the required replicon scope for the question;
this example selects neither an input nor an outgroup.

### Published examples inform a choice; they do not select it

[Xiong et al. 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12366059/) report both 18S and a single-copy-orthologue comparison across sampled Trebouxiophyceae, including *Trebouxia*, *Chlorella* and *Coccomyxa*. Their reference set and outgroups answer their own question. Review applicability, sampling, source identity and the relationship of the evidence channels before using any of their records.

[Darienko et al. 2015](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0127838) found that V9 alone did not distinguish *C. subellipsoidea* and *C. simplex* in their sampled strains. Marker coverage and resolution are therefore specific review questions; neither a single marker nor a generic identity threshold automatically establishes species. These examples do not select an extraction method, comparator panel or naming threshold.

## Check declared intake metadata

For a prepared cross-group intake JSON, the optional bundle tool
`tools/phylo_crossgroup_intake.py` reads declared local files and checks their
SHA-256 bindings, input roles, declared file scopes, sequence extents and compartments, and selected fungal-registry
signals. It requires one or more explicitly authorized read roots; the manifest,
input files and registry must resolve within them. For fungal records, an optional registry selection binds exact row fields and a declared outgroup; the row still requires biological and data-kind review. For recognizable versioned GCA, GCF and NG accessions it compares case-insensitively for exact matches; it does not equate accession versions or resolve aliases. Its `HOLD` result reports
unresolved review decisions even when its narrow checks succeed. It does not
verify organism identity or sequence content, choose a reference, certify a
resource preflight or authorize computation. Root declarations do not replace
the operator's authority to read the referenced files. For an explicitly declared
uncompressed multi-record FASTA, it can count an exact header token in the same
bytes it hashes; a matching header is not biological identity or member-content
validation. For a gzip FASTA, declare `file_scope: multi_record`, `source_format: fasta_gzip`, the exact `record_locator` token and the compressed file SHA-256. The checker hashes the compressed file before and after scanning, limits decompression to 64 MiB, and checks that the token occurs once. It does not extract a file or validate sequence identity. FASTA headers longer than 64 KiB are refused; the file itself has no total-size limit, and hashing may require substantial I/O. For a ZIP member, declare `file_scope` as `archive`, `source_format` as `zip`, the exact `record_locator` path, and its lowercase `member_sha256`. The tool checks a unique unencrypted member up to 64 MiB without extraction and rechecks the archive hash after the read. For a multi-record FASTA member, optionally add `member_format: fasta` and an exact `member_record_locator` header token; the tool requires one occurrence in the verified member. A byte or header match does not establish sequence identity, biological identity or suitability. Other archive and multi-record formats remain uninspected.
Declare `sequence_extent` as `single_marker`, `chromosome`, `single_contig`,
`whole_assembly`, or `unknown`. This is an unverified statement about the
biological extent of the record, separate from the file container. A declared
chromosome or contig does not establish a complete multi-replicon assembly;
missing or conflicting extent remains under review. The checker does not infer
extent or completeness from names, headers or bytes.
The optional `--estimate-only` flag stats declared paths and estimates full-file scan bytes per record, without opening data files. ZIP metadata, ZIP member reads and gzip decompression add I/O; sizes can change, and the estimate is not an authorization or a resource ceiling.
Start with `examples/phylo_crossgroup_intake.example.json`, replace its placeholders
in a separate working manifest, and supply absolute paths and hashes. From the
bundle root, call `python tools/phylo_crossgroup_intake.py /absolute/manifest.json --allow-root /absolute/authorized/root`; repeat the root option when needed for
the manifest, selected files and registry. A root must already be authorized.
The tool prints a JSON result; exit 0 means only that its limited metadata checks
found no errors, and the status remains `HOLD`. It does not create a run or
replace the companion-tool protocol.

## Plan and retain evidence by stage

These stages are a review framework for the actual data, not an automatic
pipeline or a universal marker panel. Use the
[companion protocol](LLM_COMPANION_TOOL_PROTOCOL.md) to prepare the input,
tool-version, resource, output and authorization preflight before external
computation or any separately governed retrieval.

| Stage | Green-algal review | Cyanobacterial review | Evidence to retain |
|---|---|---|---|
| Question and roster | State which of *Trebouxia*, *Chlorella* or *Coccomyxa* is in scope; review sample origin and mixed symbiont sources. | State the actual bacterial lineage and source context; do not assume a generic actinomycete preset fits. | Source paths and hashes, accessions and versions, sample/strain labels, roles, exclusions and unresolved identity. |
| Source and evidence | Review nuclear, plastid and mitochondrial identity separately; decide whether a marker or ortholog question is appropriate. | Distinguish a marker, chromosome and multi-replicon assembly; review whether the intended data type addresses the question. | Exact member/record bindings, declared extent and compartment, source evidence, tool and reference versions, ambiguous or unavailable material. |
| Comparison design | Assess marker or ortholog suitability and reference coverage for the named lineage and compartment. | Assess the chosen bacterial marker or genome route and its reference coverage for the actual lineage. | Reference-selection rule, exact ingroup and outgroup rationale, marker/ortholog definitions, missing data and decision holds. |
| Alignment and inference | Keep distinct markers and compartments separately traceable; review alignment and discordance. | Keep selected loci or genome evidence traceable; review alignment and sampled taxa. | Input and trimmed alignment hashes, parameters, exclusions, model/support settings, tool logs, analysis tree and outgroup. |
| Display and interpretation | Compare a display roster to the analysis roster and disclose differences. | Apply the same provenance discipline without importing algal or fungal taxonomic decisions. | Native gate reports, display binding or explicit unavailable state, visual/provenance review when a figure is produced, and unresolved biological judgments. |

No stage establishes organism identity, marker orthology, correct rooting or
scientific acceptance merely because a technical check returns zero. An absent
source or unavailable display tree is a hold rather than a zero-difference result.

## Preserve the review and approval boundaries

For each proposed comparison, record source roles, reference-selection rule,
exclusions, chosen evidence and genetic compartment, and the explicit outgroup
and rationale. Do not use the fungal registry or bacterial registry adapter as
an algal registry. If a suitable reference or outgroup is not supported, record
a hold and do not silently pick a substitute. Differences between evidence
channels are findings to investigate, not automatic evidence of a novel lineage.

Read [LLM companion-tool protocol](LLM_COMPANION_TOOL_PROTOCOL.md) for the
mandatory source, tool-version, resource, output and approval preflight before
any external-tool run. Some plan or dry-run operations can still write or
perform local searches; inspect their actual contracts. Preserve input and output
receipts and resource estimates. Approval is tied to the selected operation,
inputs, destination, disclosure and resource ceiling; the presence of this
guide is not approval.

For an existing tree, retain the analysis tree, source alignment or explicit
unavailable state, exact tip and reference roster, display tree, exclusions,
metadata and their hashes. Use the applicable bundle tree sanity and advisory
signoff tools; a passing technical check is not scientific acceptance. The
[phylogenetics workflow](PHYLOGENETICS_WORKFLOW.md) describes separate analysis
and display evidence. Render only through the bundle's prescribed figure route
and complete the relevant provenance and visual review when a figure is selected.

Fungal inputs follow the [fungal guide](PHYLO_FUNGAL_WORKFLOW.md); neither guide
changes the scientific-adoption, publication or release decision.

The intake check flags identical verified source bytes used across outgroup and query or ingroup roles when their declarations could refer to the same record. Identical verified ZIP-member bytes are also flagged across opposing roles even in different archives. Distinct locators in a multi-record source are not equated. This warning does not establish identity or replace review of aliases and record membership.

Barrnap model names and scope depend on the installed version. The upstream [0.9 source](https://github.com/tseemann/barrnap/blob/0.9/bin/barrnap) lists a general `euk` model; newer [upstream documentation](https://github.com/tseemann/barrnap#options) lists a fungal `fun` model. Neither naming convention establishes a validated algal marker extractor. Check the installed models and lineage-specific suitability before choosing an extraction method, and keep partial and ambiguous predictions under review.

Archive members can repeat the same accession in their headers while differing in their full bytes. Bind the exact member path and hash as well as the archive hash; do not select a member solely by its basename or accession. Different member hashes alone do not show whether sequence, annotation or formatting differs. Record this as a source-selection hold until the member's role and contents have been reviewed.

### Optional tree-audit snapshot comparison

The candidate tree audit offers `--snapshot-gate` with an explicit `--gate` pointing to the supported v9.7.461 tree-sanity script. It runs an additional tree-only gate snapshot comparison against declared outgroup tips. Matching results remain UNVERIFIED; mismatch and gate failure fail that check. The option limits the initial displayed-tree snapshot to 8 MiB and uses stricter single-tree, parser-agreement and finite nonnegative branch-length rules than the native gate, and may refuse inputs accepted by other workflows. The limit is not a whole-process resource ceiling: analysis-tree and other reads have separate behavior, and a file may change after the initial snapshot. It does not establish source authorization, biological rooting, scientific acceptance or protection from all file races. Review its recorded observation and scope; the native audit gate check remains separate.
