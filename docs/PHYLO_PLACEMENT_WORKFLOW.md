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
- **Two legitimate correctness constraints** (both enforced by `phylo_place.py`):
  1. **Data types must match.** A 16S query places onto a **16S** reference tree. It cannot be placed onto a
     **GToTree** backbone — GToTree concatenates single-copy *protein/core genes*, a different alphabet and
     different loci. GToTree is the backbone only for strains that have **genomes** (place them there directly,
     no 16S needed, far higher resolution). 16S-only strains use the 16S backbone here.
  2. **Source separation.** Streptomyces, Nocardia, rare-genera Hymenoptera, Attines, Moss, and Bees each get
     their **own** reference package and tree. The tool requires `--group` and never merges cohorts. (The old
     "Bees and Moss combined" tree from the Dec-2025 committee material should be split going forward.)
- **16S resolution ceiling.** 16S often cannot separate Streptomyces species (near-identical rRNA). Placement
  then gives a **genus/clade neighborhood**, which is the correct, defensible claim; species-level resolution
  needs genomes (GToTree backbone) + ANI. Every report states this.

## The pipeline (one cohort at a time)
1. **Reference set** — full-length 16S of **type strains** for the cohort's genera (from
   `Tools/databases/ncbi_16S_RefSeq` / SILVA / LPSN type material). Curate to type material; label every tip
   `Genus species strain` (sign-off gate #5). This is the "better quality data."
2. **`build-ref`** — `mafft` align → `raxml-ng` (or `iqtree`) ML tree + model → frozen `refpkg/`. CPU-heavy →
   **requires `--approved-by`** (tree-approval gate). Bootstraps for the backbone only; the queries never enter
   this inference.
3. **`place`** — align the lab 16S into the reference coordinate system (`mafft --add --keeplength`, or
   `mafft --addfragments --keeplength` via `--fragmentary` for short Sanger reads) → **epa-ng** →
   `epa_result.jplace`. The autopilot writes `query_qc.tsv` and selects fragment mode when any
   routed query is shorter than 1,200 bp; unsupported symbols and reads shorter than 200 bp are held.
4. **`report`** — `gappa examine graft` (a tree with the queries attached = the figure) + a
   `<group>_placements.tsv` (per query: best edge, LWR, pendant length) + a claim-safe README; the advisory
   sign-off gate runs automatically.

## Example (after install; approval recorded)
```bash
PL=$SAPOTE_WORKSPACE_ROOT/miniconda3/envs/placement/bin
Tools/bin/python3 Tools/phylo_place.py build-ref  streptomyces_typestrains_16S.fasta \
    --group streptomyces --approved-by the Developer or User --threads 2 --bootstrap 100
Tools/bin/python3 Tools/phylo_place.py place  --refpkg .../streptomyces/refpkg --query lab_16S.fasta
Tools/bin/python3 Tools/phylo_place.py report --jplace .../placements/epa_result.jplace
```

## How to state the result (claim-safe)
> "On a type-strain 16S backbone (n=NN, RAxML-NG GTR+G, NN% UFBoot), lab strain AS-XXX places within the
> *Streptomyces* clade containing *S. albidoflavus* (LWR 0.86, pendant 0.004) — i.e. it falls in that
> neighborhood of 16S phylogenetic space. 16S is an anchor, not a species call; species-level placement awaits
> the genome/ANI track."

## Relationship to the genome track (when genomes exist)
For strains **with genomes**, prefer the GToTree core-genome backbone + ANI-to-nearest-type — higher resolution
and the honest species-level tool. Use 16S placement for the strains that only have Sanger 16S, and as a fast,
cohort-wide first pass. The two are complementary; do not graft a 16S query onto a genome tree.
