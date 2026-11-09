# ClusterBlast-derived phylogeny candidate ledger

`tools/rank_clusterblast_phylo_candidates.py` turns the raw ClusterBlast results in an antiSMASH ZIP into a ranked list of candidate comparator genomes. You use the list later, when you choose a genome panel for a tree (see [GToTree panel selection](GTOTREE_PANEL_SELECTION.md) and [Phylogenetics workflow](PHYLOGENETICS_WORKFLOW.md)). The tool downloads nothing, names no "nearest relative", and runs no GToTree or IQ-TREE.

ClusterBlast compares a cluster's genes with clusters in other genomes. Its hits are local to the cluster. They are not a whole-genome comparison.

## Before you start

You need, for each strain:

1. the raw antiSMASH result ZIP;
2. the whole-assembly FASTA or GenBank file inside that ZIP (not a region GenBank);
3. the package's `_2_inventory.csv`, which maps raw region files to BGC IDs.

You may also supply a resolver table (see below) and the package's `_4A2_ClusterBlast_per_gene.csv` (the per-gene ClusterBlast table in your package), used for audit only.

## Why the raw ZIP is needed

The package's per-gene ClusterBlast table does not record which ClusterBlast database each row came from. The raw ZIP keeps them in separate folders. So the tool:

1. reads only raw ZIP members in the `clusterblast` folder;
2. lists, but does not use, the `knownclusterblast` and `subclusterblast` folders;
3. does not read MIBiG, nr, Swiss-Prot or EMBL-EBI results;
4. hashes the package CSV for audit and marks it `AUDIT_ONLY_CHANNEL_COLLAPSED_NOT_RANKED`.

KnownClusterBlast and MIBiG anchors point to compounds. They are never turned into organism candidates.

## The source table

Copy `examples/clusterblast_phylo_sources.template.tsv`. Its header is:

```text
strain_id	cohort	antismash_zip	assembly_member	bgc_inventory_csv	mamey_clusterblast_csv
```

| Column | Put here |
|---|---|
| `strain_id` | the strain name |
| `cohort` | a group label of your choice |
| `antismash_zip` | path to the antiSMASH ZIP |
| `assembly_member` | name of the whole-assembly file inside that ZIP |
| `bgc_inventory_csv` | path to the package `_2_inventory.csv` |
| `mamey_clusterblast_csv` | optional; the package per-gene ClusterBlast CSV, audit only |

## Resolve accessions

Raw ClusterBlast references are usually nucleotide or contig accessions such as `NZ_CP...`. The tool does not treat them as whole assemblies. A resolver TSV maps each one to a versioned `GCA_...` or `GCF_...` assembly accession and keeps your evidence note:

```text
reference_accession	assembly_accession	organism_label	resolution_evidence
NZ_CP012345	GCF_012345678.1	Genus species	curator crosswalk + source
```

A reference with no mapping becomes `HOLD_REQUEST_ASSEMBLY_ACCESSION` and cannot enter a candidate pool. The tool does no network lookup. It checks the file's shape and the accession format, not whether your claim is true.

## Run it

```bash
python tools/rank_clusterblast_phylo_candidates.py \
  clusterblast_sources.tsv candidate_ledger/ \
  --assembly-resolver assembly_resolver.tsv \
  --max-reference-rank 5
```

The output folder must not exist. `--max-reference-rank` sets how many raw ClusterBlast references are kept per BGC. The default is 5; the range is 1 to 50.

Success prints one JSON line and exits 0:

```text
{"status": "CANDIDATE_LEDGER_ONLY_NOT_DOWNLOADED_NOT_RUN", "candidates": ..., "resolved": ..., "holds": ...}
```

An error prints `rank_clusterblast_phylo_candidates: ERROR: ...` and exits 2. Exit 0 does not mean the ledger is clean. It can hold unresolved accessions, unmapped regions, or no candidates at all. Open `assembly_accession_holds.tsv` and `unmapped_region_holds.tsv` first.

## Read the ledger

| File | Meaning |
|---|---|
| `clusterblast_phylo_candidates.tsv` | ranked candidates, plus unresolved holds, with pool flags `resolved_pool_top20`, `resolved_pool_top40`, `resolved_pool_top60` |
| `clusterblast_bgc_children.tsv` | one row per BGC for each collapsed candidate |
| `clusterblast_gene_hits.tsv` | the admitted gene-level hits behind the summaries |
| `rejected_hit_rows.tsv` | hit rows left out: identity or coverage not a finite 0-100 percentage, or a BLAST score that is not a finite nonnegative number |
| `inventory_skipped_rows.tsv` | inventory rows skipped for a missing BGC ID, contig or region, with the file and line |
| `assembly_accession_holds.tsv` | references that still need an assembly accession and evidence |
| `unmapped_region_holds.tsv` | raw ClusterBlast files with no matching inventory BGC |
| `source_assembly_provenance.tsv` | ZIP and assembly-file hashes and assembly metrics |
| `channel_inventory.tsv` | which databases were read and which were only listed |
| `legacy_mamey_export_audit.tsv` | hash and row count of the package CSV |
| `candidate_receipt.json` | scope, parameters, counts and claim ceiling |

The top-20, top-40 and top-60 flags mark the first 20, 40 or 60 resolved candidates. They are not tree sizes. Queries and one outgroup are added when you build the panel with `tools/build_phylo_panel.py`.

## How candidates are ranked

The unit of support is one distinct `(strain_id, bgc_id)` pair for each candidate assembly. Raw accessions that resolve to the same `GCA` or `GCF` collapse into one candidate. Several accessions inside one BGC count once. The order is:

1. number of supporting BGCs, highest first;
2. number of supporting strains, highest first;
3. median identity and coverage, highest first;
4. best raw reference rank, lowest first;
5. candidate key.

Many matching BGCs raise priority. They are correlated signals from one genome's content, not independent experiments, and not proof of relatedness.

## Check before you use the ledger

- Compare the count of rows in `unmapped_region_holds.tsv` with the number of regions you expect. The inventory reader skips a row with a blank BGC ID, contig or region, and lists it in `inventory_skipped_rows.tsv`. A region that is present but is not a whole number stops the run with exit 2, and no output folder is written.
- Read `rejected_hit_rows.tsv`. Those rows are not in any median or ranking. The receipt gives both counts as `rejected_hit_rows` and `inventory_skipped_rows`.
- Confirm each alias maps to one contig and region. If an alias spans two, its support can merge. Hold such aliases.
- Treat the `assembly_member` as your claim. The tool cannot tell a whole assembly from a region GenBank.
- The content hash ignores headers and order. It does not normalize reverse complements and does not prove completeness.
- The reader expects LF line endings in the raw ClusterBlast text. A block it cannot parse is skipped without a count. If the ledger is empty, compare the members, blocks and rows by hand before you conclude there was no support.
- The receipt does not hash the inventory, the raw ClusterBlast members, the code or the output tables. Record those yourself.
- Files are written one after another with no rollback. A failed run can leave a partial folder that the tool then refuses to reuse. Keep it as evidence and write to a new folder.

## How to use the result

ClusterBlast shows BGC-local homology. A top-ranked candidate may share a mobile or horizontally transferred cluster while being distant across the core genome. Use the ledger as one input next to MLSA or core-marker evidence, type-strain status, assembly quality and ANI. Do not call these candidates "nearest genomes" until genome-wide evidence supports it.

Claim ceiling: ClusterBlast similarity can prioritize comparator candidates. It does not prove organism relatedness, species identity, strain independence, product identity, production or activity.
