# Phylogenetic placement workflow

Use this page to put 16S sequences from your isolates onto a fixed reference tree and report which clade each one lands in. The reference tree is built once from high-quality type-strain sequences. Your queries are attached to it afterward, so lower-quality reads cannot change its shape. The method is called phylogenetic placement, and EPA-ng is the program that does it.

For a shorter route that classifies your files and builds the reference for you, see the [autopilot workflow](PHYLO_AUTOPILOT_WORKFLOW.md). For the EPA-ng details, see [EPA-ng placement](EPA_NG_PLACEMENT_WORKFLOW.md).

## What placement can say

Each query is attached to the branch of the reference tree where it fits best. The report gives two numbers for it:

- the **likelihood-weight ratio (LWR)**, which is the share of the placement likelihood that falls on that branch, out of the alternative branches EPA-ng kept. It holds only for this reference tree, alignment and model. It is not a bootstrap, a species probability or a calibrated confidence;
- the **pendant length**, which is how far the query sits from the branch.

You can say "query X places within or near clade Y". That is a neighborhood statement with a relative placement weight. Report the alternative placements too. It is not a species call. 16S often cannot separate species in a genus such as Streptomyces, so the claim is a genus or clade neighborhood. Species-level work needs genomes and ANI.

Two rules apply:

1. **Match the data type.** A 16S query goes on a 16S reference tree. Do not place it on a GToTree backbone, which is built from protein genes. Strains with genomes use the [GToTree route](GTOTREE_WORKFLOW.md).
2. **Keep cohorts separate.** Use one cohort's references, queries and outputs per run. `build-ref` requires `--group` and stamps it into the receipts. It does not check that your queries belong to that cohort, so check this yourself before step 3.

## Before you start

- Install the placement tools: MAFFT, EPA-ng 0.3.4 or later, gappa, and RAxML-NG (or IQ-TREE). See [external tools](EXTERNAL_TOOL_INVENTORY.md).
- Set `PLACEMENT_BIN` and `PHYLO_BIN` to the folders that hold them, as in the example below.
- Work from the bundle root in the activated environment. Write all outputs to a writable workspace folder outside the bundle. `build-ref` refuses a reference folder inside the bundle.
- Use a new output folder for each run.

`place` checks `epa-ng --version` before it writes anything. It refuses versions below 0.3.4 (0.3.0 to 0.3.3 have a [rooted-input bug](https://github.com/pierrebarbera/epa-ng#warning-v030---v033)) and any banner it cannot read. There is no bypass. It also checks the program file before and after the run. A change refuses the run and keeps partial outputs.

## Steps

### 1. Build the reference FASTA

Make a FASTA of full-length 16S type-strain sequences for your cohort's genera. Use `tools/phylo_refset.py`, which finds references for your queries, removes duplicates and adds an outgroup. See [outgroups and reference sets](OUTGROUP_AND_REFSET_WORKFLOW.md). Your FASTA must carry an outgroup. Either build it with `phylo_refset.py`, or pass `--add-outgroup GENUS` in step 2.

Keep each tip's full name and accession. Use NCBI Assembly type-material evidence for any `[Type]` label. Do not infer type status from a collection name.

### 2. Build the reference package (`build-ref`)

`build-ref` aligns the references with MAFFT, builds a maximum-likelihood tree with RAxML-NG (or IQ-TREE), and saves a frozen `refpkg/` folder. It uses a lot of CPU, so it needs `--approved-by NAME`. Give the name of the person who authorized the tree. The run records it in its receipt. Any non-empty text is accepted, so the name is a record, not a check. Queries never enter this tree.

If you do not pass `--refpkg`, the package goes in `<outdir>/refpkg` when the command has `--outdir` (the `all` command), and otherwise in `_PLACEMENT/<group>/refpkg` under the tree home. Set `SAPOTE_TREE_HOME` to change the tree home.

You should see a `refpkg/` folder with `ref.aln.fasta`, `ref.tree` and `_provenance.json`.

### 3. Place the queries (`place`)

Before you place, check that every query belongs to your cohort and that the query count matches your roster. The reader keeps identical sequences that have different IDs. For a repeated ID it keeps only the first record and prints a warning, so a lower count than you expect means some IDs repeated. Resolve them first. The separate sequence-admission gate does not run in this step.

`place` aligns the queries into the reference alignment with `mafft --add --keeplength`. Add `--fragmentary` for short Sanger reads; it uses `mafft --addfragments --keeplength`. The autopilot chooses fragment mode when any routed query is shorter than 1,200 bp and holds reads shorter than 200 bp or with unsupported symbols.

Then EPA-ng places the queries, using the model fitted for the reference tree. It stops with `EPA_MODEL_NOT_REPRESENTABLE` if the IQ-TREE model uses FreeRate, and with `EPA_MODEL_UNFITTED` if a nucleotide package holds only a model name. In both cases, rebuild the package with the current `build-ref`.

You should see `epa_result.jplace` in the placements folder.

### 4. Report (`report`)

`report` runs `gappa examine graft` to attach the queries to the reference tree. It writes these files to the output folder:

- `<group>_placements.tsv`: the best branch, LWR and pendant length for each query;
- `<group>_placement_alternatives.tsv`: the other branches for each query;
- `<group>_neighborhoods.tsv`: each query's nearest reference tip;
- the grafted tree as `.newick`, and `<group>_placement_tree.png` and `.svg` when it can draw the figure;
- `<group>_PLACEMENT_README.md`, which holds the claim-safe summary.

`report` can exit 0 while a figure or caption is held. Open the output folder and check that each file above is there and nonempty. A missing figure is a hold, not a success.

To put the figures and captions in a Word file, use `tools/placement_to_docx.py`; run it with `--help` first.

## Example

```bash
export PLACEMENT_BIN="/absolute/path/to/placement/bin"
export PHYLO_BIN="/absolute/path/to/phylo/bin"
PLACEMENT_OUT="/absolute/path/to/writable/placement/EXAMPLE"
python tools/phylo_place.py build-ref /path/to/EXAMPLE_reference_16S.fasta \
    --group streptomyces --refpkg "$PLACEMENT_OUT/refpkg" \
    --approved-by "Your Name" --threads 2
python tools/phylo_place.py place --refpkg "$PLACEMENT_OUT/refpkg" \
    --query /path/to/cohort_query_16S.fasta --outdir "$PLACEMENT_OUT/placements"
python tools/phylo_place.py report --refpkg "$PLACEMENT_OUT/refpkg" \
    --jplace "$PLACEMENT_OUT/placements/epa_result.jplace"
```

Replace every path and the name with your own. The reference FASTA here already carries its outgroup.

This example and the [autopilot route](PHYLO_AUTOPILOT_WORKFLOW.md) differ in one setting. The autopilot passes `--one-per-species` to keep one reference sequence per species. This example keeps every reference you give it. `build-ref` accepts `--one-per-species` and `--one-per-genus`; both thin the backbone, so compare with a denser one before you interpret the result.

## How to state the result

Read the inference receipt for the software, model and support method. The RAxML-NG route uses classical bootstraps and a `GTR+I+G` model. The IQ-TREE fallback chooses among `+I`, `+G` and `+I+G` models and uses ultrafast bootstraps. FreeRate (`+R`) is excluded because EPA-ng cannot read it. Backbone support is separate from query LWR. Do not describe one method as the other.

Template, with your values in place of the capitals:

> On the selected 16S reference backbone (n=N; software, model and support method from the receipt), isolate QUERY places within the GENUS clade containing REFERENCE (LWR X, pendant Y). It falls in that neighborhood of 16S phylogenetic space. 16S is an anchor, not a species call. Species-level placement awaits the genome and ANI track.

## When you have genomes

For strains with genomes, use a GToTree core-genome backbone and ANI to selected reference assemblies. A tree or an ANI value supports taxonomic work; neither sets a species name or strain identity. Use 16S placement for strains that only have Sanger 16S, and as a fast first pass. Do not graft a 16S query onto a genome tree.
