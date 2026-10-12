<!-- Mirror of docs/PHYLO_PLACEMENT_WORKFLOW.md, made by tools/sync_wiki_mirrors.py. Edit the source, then run: python3 tools/sync_wiki_mirrors.py --apply -->
# Phylogenetic placement workflow — putting lab strains into a strong reference tree's neighborhood

**Purpose.** Build a trustworthy reference phylogeny from high-quality data (type strains), then *place* the lab
test strains onto that fixed backbone and report which clade/neighborhood each lands in — without letting the
lower-quality query sequences distort the reference topology. This is the published, standard method: it is
what EPA-ng and related placement methods were built for, and it is exactly the design the user proposed
("use better data to build a strong phylogeny, then state the user strains are in a neighborhood of it").

## Yes, people do this — and here is the honest framing
- **The method has a name: phylogenetic placement.** A reference tree + reference alignment are fixed; each
  query is attached to the branch (edge) that maximizes likelihood, reported with a **likelihood-weight ratio
  (LWR)** and a **pendant length**. You then say *"query X places within/near clade Y"* — a neighborhood
  statement, with a confidence number, not a hard species call.
- **Two correctness constraints with different checks:**
  1. **Data types must match.** A 16S query places onto a **16S** reference tree. It cannot be placed onto a
     **GToTree** backbone — GToTree concatenates single-copy *protein/core genes*, a different alphabet and
     different loci. GToTree is the backbone only for strains that have **genomes** (place them there directly,
     no 16S needed, far higher resolution). 16S-only strains use the 16S backbone here.
  2. **Source separation.** Keep each selected biological cohort's references, queries and outputs
     separate, with a source-bound query roster. `build-ref` requires `--group`, and placement stamps
     that reference group into its receipts; this does not verify that each supplied query belongs
     to the cohort. The operator must validate membership before placing. Molecule compatibility
     and duplicate/backbone-tip checks do not replace that provenance check.
- **16S resolution ceiling.** 16S often cannot separate Streptomyces species (near-identical rRNA). Placement
  then gives a **genus/clade neighborhood**, which is the correct, defensible claim; species-level resolution
  needs genomes (GToTree backbone) + ANI. Every report states this.

## The pipeline (one cohort at a time)
1. **Reference set** — select source-bound full-length 16S references for the cohort's genera
   from separately supplied NCBI 16S, SILVA or LPSN-associated material. Record actual local asset
   paths, sequence hashes and reference metadata; the bundle does not ship a `Tools/databases/`
   directory. Curate the selected type-material evidence rather than inferring it from collection
   names, and use NCBI Assembly `from_type` evidence for `[Type]` labels. Preserve each tip's full
   name/designation and accession in the metadata and display according to the figure house rules.
2. **`build-ref`** — `mafft` align → `raxml-ng` (or `iqtree`) ML tree + model → frozen `refpkg/`. CPU-heavy →
   **requires `--approved-by`** (tree-approval gate). Select an explicit output location
   outside the sealed code bundle; .447 refuses a reference package inside that bundle. Bootstraps for the backbone only; the queries never enter
   this inference. Without `--refpkg`, the package goes beside the placements (`<outdir>/refpkg`) when the
   command has an `--outdir` (the `all` command), and otherwise to `_PLACEMENT/<group>/refpkg` in the
   generic `trees/` home. Set `SAPOTE_TREE_HOME` to an absolute path or a workspace-relative path to override it. No top-level `strain_data/` folder is made, and
   `placement_to_docx --auto` finds both locations.
3. **`place`** — align the lab 16S into the reference coordinate system (`mafft --add --keeplength`, or
   `mafft --addfragments --keeplength` via `--fragmentary` for short Sanger reads) → **epa-ng** →
   `epa_result.jplace`. The autopilot writes `query_qc.tsv` and selects fragment mode when any
   routed query is shorter than 1,200 bp; unsupported symbols and reads shorter than 200 bp are held.
4. **`report`** — `gappa examine graft` (a tree with the queries attached = the figure) + a
   `<group>_placements.tsv` (per query: best edge, LWR, pendant length) + a claim-safe README; the optional advisory
   sign-off helper runs only if found in the resolved external workspace's uppercase `Tools/` directory as `signoff_check.py`. This is an optional workspace path; the bundled helper is `tools/signoff_check.py`.
   Its status is not a hard completion gate. Reporting can return zero while a figure
   or caption is held; inspect the actual output roster and diagnostics.

## EPA-ng version admission before placement

`place` checks the exact selected EPA-ng executable with `--version` before creating its output directory or aligning queries. The upstream [rooted-input warning](https://github.com/pierrebarbera/epa-ng#warning-v030---v033) identifies a result-breaking bug in 0.3.0–0.3.3 and recommends at least 0.3.4. This route conservatively requires a release version >=0.3.4 for every placement, because it does not independently prove that an arbitrary supplied reference tree is unrooted. Older versions outside the known affected range are unsupported by this policy, rather than automatically labelled affected.

A missing, failed, timed-out, ambiguous, unknown or development-version banner is refused. There is no version-gate bypass. The executable content is bound around the version probe and checked again before and after placement; success provenance retains the observed release version, selected executable identity and probe-output hashes. A changed executable after alignment or placement causes a refusal and retains partial outputs for inspection, without a success stamp. This is not a transaction or a guarantee against concurrent executable replacement between checks. Existing `--redo` and output reuse behavior is otherwise unchanged: use a fresh output directory and preserve earlier evidence.

The gate avoids this documented version risk; it does not validate all EPA-ng APIs, models, input-tree rooting, cohort metadata or historical results. No affected past run is inferred without its actual executable/version and tree provenance. Existing reports remain usable without rerunning placement, and this new check does not invent historical versions for them.

## Example (after install; approval recorded)
```bash
export PLACEMENT_BIN="/absolute/path/to/placement/bin"
export PHYLO_BIN="/absolute/path/to/phylo/bin"
PLACEMENT_OUT="/absolute/path/to/writable/placement/streptomyces"
python tools/phylo_place.py build-ref /path/to/streptomyces_reference_16S.fasta \
    --group streptomyces --refpkg "$PLACEMENT_OUT/refpkg" \
    --approved-by "<recorded-approval>" --threads 2
python tools/phylo_place.py place --refpkg "$PLACEMENT_OUT/refpkg" \
    --query /path/to/cohort_query_16S.fasta --outdir "$PLACEMENT_OUT/placements"
python tools/phylo_place.py report --refpkg "$PLACEMENT_OUT/refpkg" \
    --jplace "$PLACEMENT_OUT/placements/epa_result.jplace"
```

## How to state the result (claim-safe)
Replace all example paths and the approval placeholder with selected inputs and recorded authority.
Use the actual inference receipt for software, model and support method: the RAxML-NG route uses
classical bootstraps and a `GTR+I+G` nucleotide model; the IQ-TREE fallback selects a model and uses
ultrafast bootstraps. Backbone support is separate from EPA-ng query LWR. Do not relabel one method
as the other or claim that this workflow's example text verifies type status.

> "On the selected 16S reference backbone (n=NN, software/model/support method from the receipt), isolate QUERY places within the
> *Streptomyces* clade containing *S. albidoflavus* (LWR 0.86, pendant 0.004) — i.e. it falls in that
> neighborhood of 16S phylogenetic space. 16S is an anchor, not a species call; species-level placement awaits
> the genome/ANI track."

## Relationship to the genome track (when genomes exist)
For strains **with genomes**, use a GToTree core-genome backbone and ANI/aligned fraction to selected,
source-verified reference assemblies for higher-resolution comparison. These measurements
support taxonomic investigation; neither a tree nor an ANI threshold automatically
establishes a species name, formal taxonomy or strain identity. Use 16S placement for the strains that only have Sanger 16S, and as a fast,
cohort-wide first pass. The two are complementary; do not graft a 16S query onto a genome tree.
