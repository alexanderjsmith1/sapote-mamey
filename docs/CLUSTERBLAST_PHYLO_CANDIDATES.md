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

## Implemented join, hash and status limits

The inventory reader expects BGC ID, contig and a numerically parseable `Region`/`region_number`. Rows lacking those fields or a parseable region are silently skipped. It maps contig+region to alias and refuses conflicting aliases for the same region key, but does not validate unique alias-to-full-locus mapping or the manifest strain against a sealed package. Child support groups by strain+BGC alias+candidate assembly; if an alias spans different contigs/regions, support can collapse. Preserve the complete strain/full contig/region/alias roster and hold ambiguous alias mappings before interpreting “exact” support units (`tools/rank_clusterblast_phylo_candidates.py:259–279,371–400,421–445`).

Assembly provenance hashes the ZIP, selected assembly member and sorted uppercase nucleotide sequences. The content hash is header/order-independent, not reverse-complement-normalized or proof of whole-assembly completeness. The code accepts a parsed GenBank member without independently proving that it is whole-genome rather than a region; the whole-assembly input rule is operator admission, not an enforced distinction (`157–193`).

The receipt hashes manifest and resolver, plus ZIP/assembly provenance elsewhere; it does not hash the consumed BGC inventory, individual raw ClusterBlast members, source code or output TSVs. Pin those in a separate receipt. Resolver accession/evidence schema validation does not authenticate reference claims; repeated mapping to the same assembly can replace organism/evidence text. Empty gene-hit blocks do not become child support because aggregation starts from parsed gene rows (`229–249,421–445,524–576`).

The output directory must be new. Writes are sequential, with no complete-set rollback; a failure can leave a partial directory that refuses reuse. Zero exit can contain unresolved-accession and unmapped-region holds, or no candidate rows. `CANDIDATE_LEDGER_ONLY_NOT_DOWNLOADED_NOT_RUN` describes successful ledger production, not a hold-free accepted reference pool. Inspect counts, all hold tables and the actual artifact roster before panel curation. Preserve partial evidence in place and choose a separately reviewed recovery candidate; do not delete source assets to retry (`515–601`).
