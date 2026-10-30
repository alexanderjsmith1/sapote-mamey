# Route 16S queries and prepare placement

Classify your sequence files, route 16S queries against references and
prepare one placement group. You need FASTA files, a local 16S database, and
BLAST+'s `blastn` and `blastdbcmd` available on your terminal's PATH.
Use an existing 16S FASTA or the 16S records from [Barrnap](BARRNAP.md).

## Check the files

```bash
python tools/phylo_autopilot.py plan inputs/EXAMPLE-sequences
```

The labels `rrna`, `genome`, `protein` and `empty` use size and alphabet. Short
DNA can be labeled `rrna` without marker identification; many short records can
be labeled `genome`.

## Route 16S queries

Use your installed database's absolute prefix; see [local setup](LOCAL_16S_DATABASE.md).
Replace `/tmp/EXAMPLE-reference/16S` below with that prefix.

```bash
python tools/phylo_autopilot.py route --query inputs/EXAMPLE-16S.fasta \
  --db /tmp/EXAMPLE-reference/16S
```

Open `routing_table.tsv` in the working folder. It lists matched query IDs,
genus, alignment length, identity, alternatives and route group. `pident` uses
unambiguous columns; `pident_raw` is BLAST's value. Resolve `GENUS_CONFLICT` and
compare query IDs with your FASTA before preparing placement.

## Prepare one group

Choose `--group` from the routing table; this example uses `rare_genera`.
Use a new output directory:

```bash
python tools/phylo_autopilot.py run-16s --query inputs/EXAMPLE-16S.fasta \
  --db /tmp/EXAMPLE-reference/16S --group rare_genera \
  --outdir reviews/EXAMPLE-placement --dry-run
```

`--dry-run` runs local BLAST and writes files, then stops before placement.
Open `query_qc.tsv`, `routing_table.tsv`, the group query/reference FASTAs and
`rare_genera_reference.fasta.acc` in that output directory.

The defaults select up to 30 references per query genus, add Streptomyces and
Nocardia comparators, and use Corynebacterium as an outgroup. Review the selected
accessions, outgroup and type-material evidence before approving a tree.

Placement needs the EPA-ng toolchain and approval recorded with `--approved-by`.
Keep the complete inference panel when a later figure displays fewer tips.
Use [R figure workflows](R_FIGURE_WORKFLOWS.md) for display.

For whole-genome trees, follow [GToTree](GTOTREE_WORKFLOW.md). Its governed v2
route needs the runtime bindings in the [run contract](COMPANION_RUN_CONTRACTS.md);
the shorter `phylo-run` front door omits those controls.

<a id="choose-the-sequence-route"></a>
<a id="install--prerequisites"></a>
<a id="commands"></a>
<a id="1-plan--what-did-i-upload--no-ml-no-network"></a>
<a id="2-route--assign-a-genus-and-route-every-16s--blast-no-ml"></a>
<a id="3-run-16s--build-the-gated-tree-for-one-group--auto-reference--phylo_place"></a>
<a id="whole-genome-workflow"></a>
<a id="review-and-annotate-the-results"></a>
<a id="source-and-subprocess-checks"></a>
<a id="requested-stage-completion"></a>
<a id="shell-builder-retention"></a>
