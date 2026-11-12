# RG-GMCI uses ClusterBlast, not just KnownClusterBlast

RG-GMCI is the split-cluster rescue score. It looks for two BGC regions on different contigs that may be two halves of one broken locus. It uses homology to reference genomes to suggest the link. It does not join nucleotide sequence, and a candidate is a hypothesis, not a physical join. See the [glossary](../GLOSSARY.md) for other terms.

## The three antiSMASH comparison files

| File family | What it holds | Role in RG-GMCI |
|---|---|---|
| `clusterblast` | Other genomes that carry a homologous locus | Shared-reference evidence can support a candidate split interpretation; verify the reference identity, locus membership and completeness from its source. The channel does not establish a complete genome. |
| `knownclusterblast` | Characterized MIBiG reference clusters | Adds a named reference when one exists. Its similarity is antiSMASH's percent, with band edges 70 and 40. |
| `subclusterblast` | Sub-operon hits | Kept as a functional marker. Never used for pairing. |

The two paired channels stay separate. A split can be supported by ClusterBlast alone, with no MIBiG hit. The selected data may have no MIBiG match; missing, unavailable and searched no-hit states are different. The classifier is `_classify_db_kind` in `mamey/rggmci.py`.

## Check which channel supports a candidate

Open `<strain>_4A_RGGMCI_canonical.json` in the package. Mamey writes it with seven TSV files that carry the same result.

1. Check `reference_map_status`, `reference_parse_error_count`, `reference_record_count` and `clusterblast_txt_file_count` before you read a zero candidate count. A parse problem or missing reference evidence is not a negative search.
2. For each pair, read `rescue_evidence_base` (`BOTH_KCB_AND_CB`, `KNOWNCLUSTERBLAST_ONLY`, `CLUSTERBLAST_ONLY` or `NONE`) and the per-channel counts `knownclusterblast_refs` and `clusterblast_refs`. The JSON is capped. `rggmci_summary.ranked_pairs_exported` plus `ranked_pairs_not_exported` equals `pairs_total`, and HIGH pairs past the cap are kept. Compare `evidence_rows_total` with `evidence_rows_not_exported` to see how much reference evidence it kept.
3. Copy both endpoints as `strain / full node-or-contig / region / BGC alias`, with the verdict and its source records.

Shared references and subject tiling support a fragmented-locus reading. They do not show one pathway, one compound or a complete reference genome. [Current source scope](06_CURRENT_SOURCE_SCOPE.md) lists what the checks do not cover.

<a id="shared-invocation-contract"></a>
<a id="shared-invocation-contract-rggmci-shared-invocation-v2"></a>
## Saved files and the schema field

Read the `schema` field of the saved JSON before you compare two runs. It reads `rggmci-shared-invocation-v3`. Runs with different values are not directly comparable. A matching value is not enough on its own: comparable runs also need the same implementation, inputs, options and resources.

Each input writes eight files that share one prefix (`<strain>_4A_RGGMCI_canonical` in a Mamey package):

| File suffix | Holds |
|---|---|
| `.json` | Serialized result with region metadata and endpoint identities; pairs and evidence rows can be capped. Inspect status, total/export/omitted counts and full-identity holds |
| `_pairs.tsv` | Ranked pairs |
| `_related_loci.tsv` | Related loci |
| `_candidate_groups.tsv` | Candidate groups |
| `_summary.tsv` | One summary row |
| `_reference_completion.tsv`, `_split_genes.tsv`, `_partner_contigs.tsv` | Reference-completion tables |

Inspect the actual status and available fields after an empty or failed result; normal-result count equalities do not establish that every field exists after failure. An empty table has headers only. An empty completion table keeps one row that names its tier. Nested evidence sits in JSON cells.

`run` controls these settings with `--rggmci-registry-from`, `--rggmci-threads`, `--rggmci-diamond`, `--rggmci-diamond-db`, `--rggmci-residue-scope`, `--rggmci-residue-work-dir`, `--rggmci-completion-work-dir` and `--rggmci-label`. Run `python mamey_run.py run --help` for their defaults. No database is downloaded for you. A missing database stays marked as missing in the result.

The same code also ships as a separately packaged standalone tool (`packaging/rggmci/`). It has its own `--out-dir`, `--out` and `--pairs` options. A matching `schema` field is necessary for comparing its results with Mamey's, but not sufficient; check the implementation, inputs, options and resources too.
