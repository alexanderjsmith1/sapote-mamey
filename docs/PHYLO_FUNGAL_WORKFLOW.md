# Compare a fungal isolate with references

Choose fungal markers or genome orthologs to study an isolate's placement.
You need a fungal assembly, selected reference records, the external tools and
a runtime/resource plan. There is no one-command fungal runner. Use the fungal
outgroup registry; the bacterial registry and workflows cover different inputs.

## Choose the scale

For an **rDNA screen**, extract ITS with ITSx and 18S/28S with the installed
Barrnap version's fungal model; see [Barrnap](BARRNAP.md). The workflow also
allows `blastn` against a reference operon when an extractor is unavailable.
Align each locus with MUSCLE, trim with trimAl and infer with IQ-TREE.

Use 18S for broad family/genus context and ITS within a genus. Do not concatenate
family-wide ITS across divergent genera. A matched whole-operon matrix needs
checked source correspondence and a defensible alignment.

For **genome orthologs**, use BUSCO or compleasm with the selected lineage,
such as `ascomycota_odb10` or `dothideomycetes_odb10`, across the query and
references. Concatenate the orthologs for a partitioned IQ-TREE analysis.
This is the heavier route when markers disagree. Reference acquisition with
NCBI `datasets` is a separate step. Check installation compatibility first;
the documented BUSCO setup uses Linux when macOS-arm64 dependencies fail.

## Select references and an outgroup

Read `mamey/data/fungal_outgroup_registry.tsv` by `tree_scope` and
`ingroup_taxon`. Check the row's LOCKED, CONFIRM or BANNED status and whether
it supplies a marker accession or a genome assembly. Some scopes lack a complete
confirmed primary/alternate pair; leave that choice open instead of choosing
whichever genome is ready.

Use a sister group appropriate to the tree's scope, outside the ingroup.
Record the chosen row, accession and supporting record. Check deposited names
as well as assembly statistics. The registry's BANNED entry for
`[Coniosporium] apollinis CBS 100218` is a specific comparator decision;
a bracketed name alone is not a general exclusion rule.

One representative per genus can give an initial placement view. Record the
selected roster and why congeners were omitted. Expand it deliberately when
the question requires more breadth.

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
