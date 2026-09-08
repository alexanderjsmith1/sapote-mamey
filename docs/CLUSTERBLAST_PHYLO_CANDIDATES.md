# ClusterBlast-derived phylogeny candidate ledger

This optional, post-seal companion converts raw cross-genome ClusterBlast
evidence into a transparent **candidate-reference ledger** for later GToTree
panel curation. It does not download a genome, declare a nearest relative, or
run GToTree/IQ-TREE.

## Why raw antiSMASH evidence is required

Current Mamey `_4A2_ClusterBlast_per_gene.csv` files preserve useful per-gene
identity and coverage but do not retain a database-channel field on every row.
The generating layer can read `clusterblast/`, `knownclusterblast/`, and
`subclusterblast/`; after flattening, those rows cannot always be separated
without returning to the raw ZIP.

Accordingly, this tool:

1. parses only exact raw ZIP members whose directory component is
   `clusterblast`;
2. inventories but does not use `knownclusterblast` or `subclusterblast`;
3. does not ingest MIBiG, nr, Swiss-Prot, or EBI evidence;
4. hashes and row-counts the current Mamey CSV only as an audit source and marks
   a channel-collapsed export `AUDIT_ONLY_CHANNEL_COLLAPSED_NOT_RANKED`.

KnownClusterBlast/MIBiG compound anchors are therefore never converted into
organism phylogeny candidates. ClusterBlast remains distinct from nr protein
homology and from whole-genome relatedness.

## Inputs

Copy `examples/clusterblast_phylo_sources.template.tsv`. Each strain row must
provide:

- `strain_id` and `cohort`;
- the exact antiSMASH ZIP path;
- the exact whole-assembly FASTA or GenBank `assembly_member` inside that ZIP;
- the sealed Mamey `_2_inventory.csv` used to map raw region filenames to exact
  `(strain_id, bgc_id)` keys;
- optionally, the current `_4A2_ClusterBlast_per_gene.csv` for audit only.

The assembly member is parsed and receipted with ZIP SHA-256, member SHA-256,
header/contig-order-independent nucleotide-content SHA-256, record count, and
total bases. Region GenBanks are not assembly inputs.

## Assembly-accession resolution gate

Raw ClusterBlast references are commonly nucleotide/contig accessions such as
`NZ_CP...` or `NZ_J...`; those are not silently promoted to whole assemblies.
An optional resolver TSV must explicitly map each reference accession to a
versioned `GCA_...` or `GCF_...` assembly accession and preserve a
`resolution_evidence` note:

```text
reference_accession  assembly_accession  organism_label  resolution_evidence
NZ_CP012345          GCF_012345678.1     Genus species   curator crosswalk + source
```

Without that mapping, the row is `HOLD_REQUEST_ASSEMBLY_ACCESSION` and is not
eligible for a 20/40/60 candidate pool. The tool performs no network resolution
or download and does not authenticate a curator assertion beyond schema and
accession-format checks.

## Ranking and non-independence

```bash
python tools/rank_clusterblast_phylo_candidates.py \
  clusterblast_sources.tsv candidate_ledger/ \
  --assembly-resolver assembly_resolver.tsv \
  --max-reference-rank 5
```

The default uses the top five raw ClusterBlast references for each exact BGC.
The setting is recorded and may be changed from 1 to 50.

The support unit is one distinct exact `(strain_id, bgc_id)` child row per
collapsed candidate assembly. Ranking is deterministic:

1. number of distinct supporting query BGCs, descending;
2. number of distinct supporting query strains, descending;
3. median child identity and coverage, descending;
4. best raw reference rank, ascending;
5. candidate key.

Every child preserves reference accession(s), organism/source text, query and
subject gene counts, gene-hit row count, median identity/coverage, cumulative
score, and exact source region. The full gene table remains available beneath
the child rows.

If multiple raw accessions resolve to the same `GCA/GCF`, they collapse to one
candidate. If they occur in the same query BGC, they remain one BGC support
unit—not multiple independent votes. Multiple BGC matches raise selection
priority, but they are correlated genome-content signals, not independent
experiments and not proof of organism relatedness.

## Outputs

| Artifact | Meaning |
|---|---|
| `clusterblast_phylo_candidates.tsv` | Ranked resolved candidates and unresolved HOLDs; visible top-20/40/60 pool flags |
| `clusterblast_bgc_children.tsv` | One exact strain+BGC child row per collapsed candidate |
| `clusterblast_gene_hits.tsv` | Full raw ClusterBlast gene correspondence used in summaries |
| `assembly_accession_holds.tsv` | References requiring an assembly accession/evidence crosswalk |
| `source_assembly_provenance.tsv` | Exact antiSMASH ZIP/member provenance and assembly-content metrics |
| `channel_inventory.tsv` | Separate ClusterBlast/KnownClusterBlast/SubClusterBlast/MIBiG/nr/Swiss-Prot/EBI accounting |
| `legacy_mamey_export_audit.tsv` | Current Mamey CSV hash, row count, and channel-preservation status |
| `unmapped_region_holds.tsv` | Raw ClusterBlast files lacking an exact inventory BGC join |
| `candidate_receipt.json` | Scope, parameters, counts, channel policy, support unit, and claim ceiling |

The top-20/40/60 flags refer to the **resolved reference-candidate pool**. They
do not create a 20/40/60-tip tree. Final total-tip accounting still includes
queries and one outgroup and is governed by `tools/build_phylo_panel.py` from
the bounded panel-selection patch.

## Required biological interpretation

ClusterBlast is BGC-local homology, not a genome-wide taxonomic method. A highly
ranked candidate may share mobile or horizontally transferred biosynthetic loci
while being distant across the core genome. Use this ledger as one comparator-
discovery input alongside MLSA/core-marker context, documented type/reference
status, assembly quality, and ANI. Never describe these candidates as “nearest
genomes” until independent genome-wide evidence supports that wording.

Claim ceiling: ClusterBlast similarity can prioritize comparator candidates but
does not prove organism relatedness, species identity, strain independence,
product identity, biosynthetic production, or biological activity.
