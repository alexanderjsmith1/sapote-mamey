# Cohort protein comparison for Mode B

`python mamey_run.py cohort-proteins` compares the proteins of one biosynthetic gene cluster (BGC) with the proteins of the other strains you have measured. It is optional. Use it when a Mode B card needs a within-project comparison that external BLASTp and whole-region BiG-SCAPE do not give you: for a chosen gene, which proteins in your other cohorts are closest, and do several of them sit together in the same comparator BGC?

A **cohort** is a named group of packages, such as your own strains, a set of type strains, or a set of reference genomes. The label is free text. This page uses `COHORT_A`, `COHORT_B` and `REFERENCE`.

Run the commands from the bundle root. The card recipe is in the [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md). Terms are in the [glossary](GLOSSARY.md).

## What you need

- One sealed package per strain, from `run` and `validate`. See the [first-run recipe](reader/01_FIRST_RUN.md).
- Biopython, only if you use a GenBank register (below). Install it with `python -m pip install -e '.[bio]'`; [install guide](INSTALL.md).
- A new folder for each output.

## 1. Build the catalog

```bash
python mamey_run.py cohort-proteins build \
  --cohort COHORT_A=/path/to/cohort_a/runs \
  --cohort COHORT_B=/path/to/cohort_b/runs \
  --cohort REFERENCE=/path/to/reference/runs \
  --out project_evidence/cohort_proteins.sqlite
```

Each `--cohort` is `LABEL=PATH`. The build looks under PATH for package folders, meaning any folder that holds `<strain>_2_inventory.csv`. Each package must also hold `<strain>_proteins.faa`.

You should see a JSON report. It lists `packages_by_cohort`, `unique_occurrences`, `typed_quarantine_rows` and, per cohort, the counts of distinct strains, exact loci, protein occurrences and distinct sequences. The build also writes `cohort_proteins.receipt.json` next to the database, holding the database hash and the same counts.

`"status": "PASS"` means nothing was held back. `PASS_WITH_TYPED_QUARANTINE` means some proteins or packages were not loaded. That includes a folder with no packages, which gives an empty cohort. Read `typed_quarantine_rows` and the quarantine table before you rely on the catalog. A zero exit does not show the cohort is complete.

The database and its receipt are one pair. Without `--replace`, the build refuses to start when either file already exists, and it publishes each new file under a name that must still be free. Add `--replace` to rebuild both. Keep the old database and receipt until the new pair is checked, because the replace swap is not crash-safe. After an interruption, compare the receipt's hash with the database.

### Older packages without a protein file

Add an exact-locus GenBank register instead:

```bash
python mamey_run.py cohort-proteins build \
  --cohort COHORT_A=/path/to/current/runs \
  --gbk-register /path/to/region_gbks.tsv \
  --out project_evidence/cohort_proteins.sqlite
```

The register is a tab-separated file with the columns `cohort`, `strain`, `full_node_or_contig`, `region`, `bgc_alias`, `gbk_path` and, optionally, `gbk_sha256`. The tool takes identity only from these columns, never from a file name. It holds back missing files, hash mismatches, files with more than one record, and CDS entries without a locus tag.

## 2. Compare one BGC

Pick the BGC alias (`BGC_ID`) from `<strain>_2_inventory.csv` in the focal package.

```bash
python mamey_run.py cohort-proteins compare \
  --database project_evidence/cohort_proteins.sqlite \
  --package runs/EXAMPLE/package \
  --bgc BGC041 \
  --query-cohort COHORT_A \
  --outdir project_outputs/EXAMPLE/BGC041_cohort_proteins
```

- `--bgc` is a lookup key inside that one package. Every output row shows the full identity: strain / full node-or-contig / region / BGC alias.
- By default the tool picks the core, resistance-routing and transporter genes. Use `--genes tag1,tag2` to name locus tags yourself. Tags with no sequence are skipped, so compare your list with `query_genes` in the receipt.
- `--query-cohort` is the label that holds the focal strain. The focal strain's rows in that cohort are left out of the ranking. A label that is not in the database, or a cohort with no rows for the focal strain, is refused. Rows with the same strain label in other cohorts stay in the ranking. The receipt lists `focal_strain_rows_by_cohort`, `focal_strain_excluded_cohorts` and `focal_strain_still_ranked_in_cohorts`. `target_strain_excluded_from_query_cohort` is true only when rows were actually left out. Without `--query-cohort`, nothing is left out.
- `--top-n` (default 3) is the number of comparator loci kept per gene and cohort. `--prefilter-n` is the number of candidates aligned per gene and cohort.

The command prints a JSON receipt and writes four files, named from the full identity. `--outdir` may already hold other files, but if any of these four names exists there, the command stops before aligning and replaces nothing; choose a new `--outdir` to rerun the same BGC. The four files are written to a staging folder first. If publishing fails part-way with an error the tool can catch, it removes the files it already published; a killed process can leave a partial set. The files are:

- `..__COHORT_PROTEIN_MATCHES.tsv`: ranked matches per gene.
- `..__COHORT_NEIGHBORHOOD_SUMMARY.tsv`: matches grouped by comparator locus.
- `..__MODEB_SECTION45_PAYLOAD.md`: text for the card.
- `..__COHORT_PROTEIN_COMPARISON_RECEIPT.json`: output hashes.

Open the payload first, then the matches table. Use a new `--outdir` for each attempt; existing same-named comparison outputs are refused.

Keep an external record of the database path, its receipt, the package and the gene list. The comparison receipt hashes only its outputs, not its inputs. Open the database from a closed, finished copy.

## How matches are ranked

The tool filters, then aligns:

1. It keeps the top 40 candidates per gene and cohort by shared 4-mers. A candidate must be 0.55 to 1.80 times the query length.
2. It aligns those with BLOSUM62, gap open -11, gap extend -1.

It ranks by alignment score, then query coverage, then identity. For each distinct comparator locus it keeps the best protein, up to `--top-n` loci. A missing match means nothing was found in the screened set. It does not show there is no homolog.

Each match gets a navigation label:

- `STRONG_WHOLE_PROTEIN_FAMILY_NAVIGATION`: identity at least 60% and coverage at least 80% on both proteins.
- `MODERATE_WHOLE_PROTEIN_FAMILY_NAVIGATION`: identity at least 40% and coverage at least 70% on both.
- `WEAK_CLOSEST_AVAILABLE`: the best measured candidate is below the moderate bar.
- `ALIGNMENT_SKIPPED_UNMEASURED`: one protein was longer than `MAMEY_MAX_ALIGN_AA` (default 10,000), so it was not aligned. Its zero metrics are placeholders, not measurements.

The labels are for navigation, not verdicts.

### Neighborhoods

Matches are grouped by comparator locus. Several matched genes in one comparator BGC are reported with an order label: `MULTI_GENE_SAME_LOCUS_ORDER_CONCORDANT`, `..._REVERSE_ORDER`, `..._ORDER_MIXED` or `..._ORDER_UNMEASURED`. A single matched gene reads `SINGLE_QUERY_GENE_ONLY`. `matched_query_gene_count` counts distinct query genes. Several query genes can match the same comparator gene, so the count is not a one-to-one synteny score.

Identical proteins in overlapping regions stay visible as occurrences. They do not count as independent strains. Every comparison reports its cohort denominator as strains, exact loci, protein occurrences and distinct sequences, counted before the focal strain is removed.

## Where the results go in a card

| Section | Use |
|---|---|
| §5, §6 | Name the exact core and tailoring genes. Show which are conserved in the cohort and which are weak. |
| §7, §27, §38 | Compare resistance-like and transporter candidates. Ask for the same biosynthetic class and the same locus before you suggest producer protection. |
| §3 | With a separate nucleotide comparison, test boundary continuation and assembly splits. |
| §25 | Ask whether similar core machinery recurs with the same neighbors. |
| §39 | Report identity and coverage on exact genes, with denominators. |
| §41 | Choose nonredundant comparator proteins for a phylogeny. |
| §44 | Report distinct-strain and exact-locus prevalence apart from repeated region observations. Exact duplicates are not independent. |
| §45 | Use only for a declared supervisor or university cohort. The payload file name says Section 45; use the section whose title fits the cohort you measured. |
| §46 | Add type and reference cohorts with the same database. A genome name is not gene-level evidence. |

A nucleotide comparison (BLASTN) is a separate channel. It must bind exact CDS or region sequences, report its own counts, and never be labeled as protein BLASTp.

## Claim ceiling

Within-project similarity is not identity or orthology. Neighborhood recurrence is not pathway identity or operon proof. Capacity is not production. A transporter or resistance-family match is not producer protection without gene-specific biochemistry and class agreement. The database denominator is the package set you measured, not nature.
