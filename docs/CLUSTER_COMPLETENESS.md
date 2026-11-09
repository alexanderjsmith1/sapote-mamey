# Cluster completeness: reference-dependent homology coverage

`tools/cluster_completeness.py` asks how many of the genes in complete reference clusters also appear in your query cluster. It reports a coverage score and a positional heuristic. It cannot tell whether an unmatched gene is biologically absent or was lost to assembly. It does not show orthology, physical linkage, compound identity or activity.

Setup is in [the first-run recipe](reader/01_FIRST_RUN.md). The tool needs Biopython and runs local protein alignments, so check the input size and your machine's limits first. It is not a BLAST job.

## Run it

```bash
python tools/cluster_completeness.py \
  --query EXAMPLE:query_region.gbk \
  --reference REF1:ref1.gbk --reference REF2:ref2.gbk \
  --query-boundary interior \
  --outdir completeness_out
```

| Flag | Meaning | Default |
|---|---|---|
| `--query LABEL:path.gbk` | One antiSMASH region GenBank file, or one RG-GMCI group file (one record per fragment). It is read as a single query. | required |
| `--reference LABEL:path.gbk` | A complete reference cluster. Repeat the flag for each reference. | required |
| `--min-id` | Minimum global percent identity for a match. | 30 |
| `--query-boundary` | Free text from triage: `interior`, `edge` or `full-contig`. It only selects which wording the interpretation uses. If you leave it blank, the interpretation treats the query as interior and says contig-end truncation does not explain the missing genes. Set it from triage before you rely on that sentence. | blank |
| `--outdir` | Output folder. The tool creates it and reuses it if it exists. | `completeness_out` |

Choose complete reference clusters of the type you are testing, each from a different source. Each `--reference` entry counts as its own reference, even if two entries are the same file. Duplicates inflate the majority rule. [RG-GMCI](GLOSSARY.md) is the shared-reference linkage used to group fragments.

Only CDS features that carry a translation are used. Use a threshold from 0 to 100. The tool does not check the range, and 0 admits zero-similarity matches, so it cannot support a presence claim. Keep a reviewed positive value and record it.

## What you should see

The console prints one line and one interpretation sentence:

```text
[cluster_completeness] EXAMPLE: <pct>% complete (<tier>), <present>/<total> cluster genes; <n> missing.
```

With no eligible reference group the first line reads `unmeasured complete (unmeasured)` and the second line is the `HOLD UNMEASURED_NO_ELIGIBLE_REFERENCE_GENES` sentence.

The output folder holds:

- `EXAMPLE_completeness.json`: keys include `completeness_pct`, `denominator_state`, `tier`, `n_present`, `n_cluster_genes`, `n_missing`, `present`, `missing`, `fragments`, `references`, `query`, `query_boundary` and `interpretation`.
- `EXAMPLE_missing_genes.csv`: columns `status`, `gene_label`, `n_refs_with_it`, `query_best_id_pct`. Despite the name, it lists both `MISSING` and `present` genes.
- `EXAMPLE_genes_by_fragment.csv`: only when the query has more than one fragment. One column per fragment marks where each reference gene was found.

Exit code 0 means the files were written. It is not a scientific acceptance. If the run fails or stops, inspect every file in the folder before retrying. There is no fresh-output guard, so use a new folder for each attempt.

## How to read the score

Completeness is present groups divided by eligible reference groups. The tiers are software labels, not a biological certificate:

| Tier | Completeness |
|---|---|
| near-complete | 85% or more |
| substantial | 60% or more |
| partial | 35% or more |
| fragment | below 35% |

Zero eligible reference groups leaves `completeness_pct` and each fragment's percentage blank (`null`), sets `denominator_state` to `UNMEASURED_NO_ELIGIBLE_REFERENCE_GENES` and `tier` to `unmeasured`, and replaces the interpretation with a hold sentence. No missing-gene or absence sentence is written. With a denominator, `denominator_state` is `MEASURED`. An empty translation set or a poorly chosen reference panel needs review for the same reason.

## How the score is computed

- Reference genes are grouped by thresholded global protein alignment. Groups form by single linkage across references, so related copies can merge through a chain.
- A group is eligible when a strict majority of references carry it. With two references, both must. With one, every gene is eligible.
- The first member of a group is its representative, so reference order matters. Keep the order and record it.
- A query gene counts as present using its rounded best identity. The per-fragment list uses unrounded identity, so near-threshold calls can differ between the two.
- This is not one-to-one ortholog assignment. One query protein can satisfy several groups. The emitted interpretation calls the measure thresholded, reference-dependent similarity, not orthology, function or locus identity.

## Positional heuristic

The tool orders groups along the reference that holds the most groups. Missing groups outside the span of matches feed an "end-missing" heuristic. Missing groups inside it feed an "interior-missing" heuristic. If there is no query match, the positional counts stay zero while `missing_end_loaded` can still be true.

Do not accept emitted phrases such as "all missing genes at the ends" without checking the matched span and the denominator. Read any truncation or loss text as a hypothesis. Reference divergence, translation gaps, the threshold and assembly gaps are all possible causes.

## Multi-fragment queries

For a query with several records, the tool reports combined coverage, per-fragment coverage and genes carried only by a partner fragment. Having several records, or an RG-GMCI members table, does not prove the fragments are physically joined.

The tool loads a same-stem `.members.tsv` next to the query GenBank file if one exists. When there is more than one fragment, any non-empty members list sets the RG-GMCI flag and supplies the fragment labels. It does not check the table's schema, record count or order. A stale or unrelated sibling file changes the labels without changing any alignment, so confirm the table matches the query's records.

The fragment count comes from the highest record index with a translated CDS. Empty records before it show as zero-covered fragments. Trailing empty records are omitted. Compare the reported fragments with your full record list.

## Keep your own record

The outputs hold the reference and query labels, not input hashes or a checked full-locus identity. Record each input path with its SHA-256, the reference version, the threshold, and the complete `strain / full contig / region / BGC alias` for the query. A short `--query` label does not validate identity.
