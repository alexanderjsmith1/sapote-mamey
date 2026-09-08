# Phylogenetic autopilot — upload 16S and/or genomes, get gated trees

`tools/phylo_autopilot.py` is the **one front door** for turning raw sequence uploads into the
publication-grade, gate-passed trees this project already knows how to make. It does not replace the
existing tools — it removes the manual bookkeeping in front of them so a user does not have to know
which pipeline, which reference, or which outgroup a given upload needs.

```
uploads/  ──▶  autopilot  ──▶  { 16S → phylo_place (EPA-ng) }  ──▶  tree_sanity_check ──▶ figure
   │              │             { genome → build_tree.sh (GToTree→IQ-TREE) }
   │              ├─ classify each file: rRNA locus / whole genome / protein
   │              ├─ assign a genus to every 16S by top-hit BLAST vs a 16S type-strain DB
   │              ├─ route each query: Streptomyces / Nocardia / rare-genera / off-target / FLAG
   │              └─ auto-build the reference for exactly the observed genera
```

## Why it exists (the failure it prevents)

Placing a query onto a fixed backbone is only safe if the query *belongs* on that backbone. In this
cohort, several isolates' 16S top-hit a **non-actinomycete** (`AS-XXX` → *Pseudescherichia*, an
enterobacterium; `AS-XXX` → *Taibaiella*, Bacteroidota; `AS-XXX` → *Devosia*). Forcing those onto a
*Streptomyces* or rare-actino tree would manufacture a false placement. The autopilot **flags** them
(`FLAG_OTHER`) and keeps them out of the actinomycete trees — the human decides whether they are
contaminants, mixed cultures, or genuinely off-target isolates. Distant-but-real actinomycetes
(*Brachybacterium*, *Mycobacterium*, …) are marked `OFF_TARGET_ACTINO`: kept and reported, not
forced into the discovery trees.

## Install / prerequisites

- BLAST+ (`blastn`, `blastdbcmd`) on `PATH` — the offline wheelhouse / `blast` conda env has these.
- A 16S type-strain BLAST DB. This project ships one at
  `Tools/databases/ncbi_16S_RefSeq/16S_ribosomal_RNA` (NCBI 16S RefSeq, ~27.6 k type-strain
  sequences). Any BLAST nucleotide DB whose titles begin `Genus species …` works.
- The placement env for the downstream 16S step (`miniconda3/envs/placement/`: EPA-ng, gappa,
  raxml-ng) and the phylo env for the genome step (`miniconda3/envs/phylo/`: GToTree, IQ-TREE).

## Commands

### 1. `plan` — what did I upload?  (no ML, no network)
```
python tools/phylo_autopilot.py plan <uploads_dir>
```
Classifies every FASTA under the directory as `rrna`, `genome`, or `protein`. Classification is by
sequence **length**, so a single multi-FASTA of many 16S sequences (one per strain) is correctly
`rrna`, never mistaken for a genome.

### 2. `route` — assign a genus and route every 16S  (BLAST, no ML)
```
python tools/phylo_autopilot.py route --query all_16S.fasta \
    --db Tools/databases/ncbi_16S_RefSeq/16S_ribosomal_RNA --out routing_table.tsv
```
Writes a routing table (`query, tophit_genus, pident, aln_len, route_class, group, tophit_title`)
and prints the per-class tally plus the reference genera each group will need. **Read this table
before building anything** — it is where you catch a contaminant or a mis-sort.

### 3. `run-16s` — build the gated tree for one group  (auto-reference → phylo_place)
```
python tools/phylo_autopilot.py run-16s --query all_16S.fasta \
    --db .../16S_ribosomal_RNA --group rare_genera --outdir runs/rare_genera \
    --approved-by "<who authorized this tree>"
```
Routes, subsets the query to that group, auto-builds the reference (type strains for exactly the
observed genera, plus a few sentinels + a distant outgroup, pulled from the DB), then shells
`phylo_place all`. **`--approved-by` is required** — without it the command refuses and tells you to
use `--dry-run`. This is the standing **tree-approval gate**; the autopilot never bypasses it, and
the heavy ML still runs inside `phylo_place`, which enforces the gate itself. Use `--dry-run` to
produce the reference + query FASTAs and stop, so you can inspect them before committing compute.

Whole-genome uploads route to `tools/build_tree.sh` (declare intent in `TREE_SPEC.json`, stage
`genomes/`; it runs `phylo_preflight.py` then GToTree → IQ-TREE). Genome trees give species-level
resolution that single-locus 16S cannot; 16S is the fast triage that tells you *which* genome tree a
strain belongs in.

## After the tree is built

- Every tree must PASS `tools/tree_sanity_check.py <tree> --outgroup <genus>` (outgroup-aware since
  v9.7.398) before it is shown — no dominating/pathological branch.
- `phylo_place` already enriches AS query tips with **host · location · GenBank accession** from
  `OFFICIAL_DATA/STRAIN_METADATA.tsv`, and prunes the display to the nearest named type-strain
  anchor for legibility while placement used the full reference.
- For cohort-split figures (one tree per bee / moss / attine set), place each cohort's query subset
  separately against the same reference package.

## Claim-safety (non-negotiable)

A top-hit genus and a placement are a **neighborhood**, not a species identity and not an ANI call.
Near-identical 16S (patristic ≈ 0) is a *candidate* same-species that **requires genome ANI to
confirm**. 16S resolves genus/clade; the genome tree and ANI resolve species. Judgment is deferred to
the downstream tools and to the human. No structural or bioactivity claim follows from placement.

## Where things land

- Routing table + per-group reference/query FASTAs: `<outdir>/`.
- Placement outputs (jplace, grafted newick, neighborhoods TSV, enriched figure, claim-safe README):
  `<outdir>/placement/`.
- Placement outputs live under `<your project root>/_PLACEMENT/<group>/`; keep that directory beside the cohort data the trees were built from so each tree stays traceable to its inputs.
