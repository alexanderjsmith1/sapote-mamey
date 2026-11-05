# Compare a fungal isolate with references

Choose fungal markers or genome orthologs to study an isolate's placement.
You need a fungal assembly, selected reference records, the external tools and
a runtime/resource plan. There is no one-command fungal runner. Use the fungal
outgroup registry; the bacterial registry and workflows cover different inputs.

For green algae and cyanobacteria, see [their separate guide](PHYLO_ALGAL_CYANO_WORKFLOW.md). Their inputs, reference choices and outgroups require independent review.

## Choose the scale

For an **rDNA screen**, extract ITS with ITSx and use an appropriate installed
Barrnap model for 18S/28S; see [Barrnap](BARRNAP.md). Model names vary by
version: Barrnap 0.9 has a general `euk` model, whereas the newer upstream
interface lists `fun` for fungi. Inspect the installed version, available
models and their documentation before choosing; neither model guarantees a
complete or correctly identified marker. Preserve the model identity, partial
calls and the review of marker boundaries. The workflow also allows `blastn`
against a reference operon when an extractor is unavailable.
Align each locus with MUSCLE, trim with trimAl and infer with IQ-TREE.

Use 18S for broad family/genus context and ITS within a genus. Do not concatenate
family-wide ITS across divergent genera. A matched whole-operon matrix needs
checked source correspondence and a defensible alignment.

For **genome orthologs**, use BUSCO or compleasm with the selected lineage,
such as `ascomycota_odb10` or `dothideomycetes_odb10`, across the query and
references. Review ortholog identity, duplicates and missingness before alignment,
concatenation and a partitioned IQ-TREE analysis. This heavier route is one
possible follow-up when markers disagree; it is not automatically triggered. Reference acquisition with
NCBI `datasets` is a separate step. Check installation compatibility first;
the documented BUSCO setup uses Linux when macOS-arm64 dependencies fail.

## Select references and an outgroup

Read `mamey/data/fungal_outgroup_registry.tsv` by `tree_scope` and
`ingroup_taxon`. Check the row's LOCKED, CONFIRM or BANNED status and whether
it supplies a marker accession or a genome assembly. Some scopes lack a complete
confirmed primary/alternate pair; leave that choice open instead of choosing
whichever genome is ready.

Start from the [fungal intake example](../examples/phylo_fungal_intake.example.json)
and replace every placeholder in a separate working manifest. The untouched
example is deliberately incomplete and cannot be used for a run. The optional
cross-group intake checker accepts a `fungal_registry.selection`
object with exact `tree_scope`, `ingroup_taxon` and `accession` values. It can
bind one row in the hash-checked registry to a declared outgroup; missing,
ambiguous or BANNED selections are errors. This is a mechanical check, not a
choice of row or proof of its suitability, record identity or marker/genome
compatibility. Additional outgroups need separate review. See
[algal and cyanobacterial guide](PHYLO_ALGAL_CYANO_WORKFLOW.md#check-declared-intake-metadata)
for the intake command and its limits.

Use a sister group appropriate to the tree's scope, outside the ingroup.
Record the chosen row, accession and supporting record. Check deposited names
as well as assembly statistics. The registry's BANNED entry for
`[Coniosporium] apollinis CBS 100218` is a specific comparator decision;
a bracketed name alone is not a general exclusion rule.

One representative per genus can give an initial placement view. Record the
selected roster and why congeners were omitted. Expand it deliberately when
the question requires more breadth.

## Prepare and retain evidence by stage

Before any external tool, use the [companion protocol](LLM_COMPANION_TOOL_PROTOCOL.md)
to record the question, exact inputs and source hashes, reference and outgroup
rule, tool and dataset versions, proposed output location, resource estimate
and any required authorization. Keep unavailable inputs as a hold. The intake
checker is a separate preliminary byte and metadata check, not that approval.

| Stage | Existing method to review | Evidence to retain |
|---|---|---|
| Input and roster | Identify each query, ingroup and outgroup; inspect the applicable fungal registry row. | Exact source paths, hashes, accession versions, strain labels, sequence extent, roles, exclusions, registry hash and any unresolved identity or contamination questions. |
| rDNA markers | ITSx for ITS, a reviewed installed Barrnap model for 18S/28S, or the guide's reviewed `blastn` probe route. | Tool/model versions, inputs, coordinates and orientation, complete and partial calls, extraction logs, and the mapping from each marker to its source record. Record multiple or ambiguous calls rather than silently choosing one. |
| Marker alignment | Align loci separately with MUSCLE and review trimming with trimAl. | Pre- and post-trim alignments, exact taxon roster, parameters, removed sites or sequences and reasons, and alignment hashes. A shared name alone does not establish that records form a matched operon. |
| Genome orthologs | If separately justified and authorized, review BUSCO or compleasm lineage and installed interface before using the existing ortholog route. | Lineage dataset and tool versions, input hashes, per-taxon results and logs, duplicate/missing/partial orthologs, occupancy rule, locus exclusions, per-locus alignments and partition mapping. A completion marker alone is not proof of complete output. |
| Tree inference and review | Use the reviewed IQ-TREE plan, then run the applicable tree-sanity and advisory checks. | Command and version, model and support settings, random seed when applicable, alignment and tree hashes, outgroup and rooting rationale, native reports, and analysis-versus-display tip differences with reasons. A technical pass is not scientific signoff. |

These are evidence requirements for the proposed stages, not commands to run or
proof that an installed tool or selected dataset is suitable. Review marker and
genome results independently; explain discordance and missing evidence rather
than automatically promoting one route or changing the roster.

## Check and interpret the tree

Run the outgroup-aware `tools/tree_sanity_check.py` check before rendering.
`tools/signoff_check.py` is advisory and can exit 0 while reporting issues or
no inspectable trees; read its findings.

Compare a new genome tree with any existing rDNA tree for the same isolate.
Describe disagreements and consider informative alignment sites and locus
conservation alongside support values. Marker placement and similarity provide
comparison context; bacterial ANI thresholds are not a fungal naming rule.

If `DOMINATING_BRANCH` fails, report the branch length and its fraction of tree
depth. Check the alignment and outgroup; do not loosen the check or prune the
query to make the figure pass. Keep the figure unfinished while that result is
reviewed.

## Recover an interrupted ortholog run

Start that genome in a fresh output directory and keep the failed run and logs.
The recorded compleasm failure writes `miniprot.done` before hmmsearch finishes;
resuming it can leave a truncated ortholog set. Check the installed version and
its outputs rather than assuming that marker means the run completed.

<a id="two-tiers-same-philosophy-as-the-bacterial-two-tier"></a>
<a id="rooting-rule-same-as-bacterial-prevents-the-1-defect"></a>
<a id="gates-identical-to-bacterial"></a>
<a id="claim-safety"></a>
<a id="rules-from-earlier-fungal-trees"></a>
