# Per-gene MIBiG convergence tables

Read this before you cite a convergence field or tier label in a card, manuscript or slide.

A convergence table shows how many genes in one BGC (biosynthetic gene cluster) match genes of one
MIBiG reference cluster. MIBiG is the database of characterized clusters. See the
[glossary](GLOSSARY.md) for other terms.

## What the tables are and are not

The tables are reporting only. They add no score and no bonus, and they change no triage or count.
`mibig_per_gene.REPORT_ONLY_CONTRACT` is `REPORT_ONLY_NO_SCORING`.

The tables parse the gene-level hits that antiSMASH saved in its KnownClusterBlast summaries. Many
matching genes are bounded support for the hypothesis that two clusters belong to related pathways.
Matches can come from generic or shared genes, so a pathway relationship needs locus-specific review.
The saved summaries do not prove the exact query bytes that were searched or a complete gene roster.
They do not show the same product, expression, production, bioactivity, resistance, novelty or
physical linkage across contigs. The named MIBiG compound is a comparator, not an identified product.

## Get the files

The `run` command writes them into the strain's package folder
(`runs/<strain>/package/`; see [first run](reader/01_FIRST_RUN.md)). Nothing else is needed. To get
them for an older package, run the strain again. Old packages are not upgraded in place.

| File | What it holds |
|---|---|
| `<strain>_3_mibig_per_gene.{json,csv}` | One row per query gene and MIBiG accession pair. |
| `<strain>_3_mibig_convergence.{json,csv}` | One row per BGC and MIBiG accession, with the tier. |
| `<strain>_3_mibig_profile.csv` | One row per BGC: the dominant accession, gene counts and tier. |
| `<strain>_3_antismash_structured.json` | Module, RiPP motif and RRE-Finder evidence together. |
| `<strain>_3_length_weighted_capacity.csv` and `<strain>_3_length_weighted_summary.json` | A trial capacity measure for assembly sensitivity. It is not a lead score and not a BGC count. |

The workbook has matching sheets: `MIBiG_Per_Gene`, `MIBiG_Convergence`, `MIBiG_Profile`,
`antiSMASH_Modules`, `antiSMASH_RiPP_Motifs`, `antiSMASH_Motifs` and `antiSMASH_RREfinder`.

To read the result, open `<strain>_3_mibig_convergence.csv`. The columns to look at are `bgc_id`,
`mibig_accession`, `distinct_query_genes`, `median_pct_identity`, `median_pct_coverage`,
`class_concordance`, `convergence_tier`, `dominant_reference` and `dominance_status`.

## Tiers

Each BGC and MIBiG row gets one tier. The thresholds come from `_convergence_tier` in
`mamey/mibig_per_gene.py`. The tiers sort rows by how much per-gene agreement there is. They are not
judgments.

| Tier | Requires |
|---|---|
| `H1_HIGH_DENSITY` | At least 12 query genes, median identity 70% or more, median coverage 80% or more, recognizable-gene share 0.65 or more, best reference rank 3 or better. |
| `H2_STRONG_FAMILY` | At least 8 genes, identity 55% or more, coverage 75% or more, share 0.40 or more. |
| `H3_MULTI_GENE` | At least 4 genes, identity 40% or more, coverage 60% or more. |
| `H4_REPEATED_SUPPORT` | At least 2 genes, identity 35% or more. |
| `HOLD_COVERAGE_UNMEASURED` | At least 4 genes and identity 40% or more, but no hit for this reference has a numeric coverage. H1 to H3 need coverage, so the row is held, not scored as 0% coverage. |
| `CAUTION_CLASS_MISMATCH` | The antiSMASH class and the MIBiG class conflict. Checked first, so it replaces any H tier for that reference. |
| `H5_SINGLE_OR_WEAK` | Everything else. |

The class mismatch applies to one reference, not to the whole BGC. A BGC can be `CAUTION_CLASS_MISMATCH`
against one MIBiG cluster and `H3_MULTI_GENE` against another. The profile picks its dominant
reference with tier first, so a weaker positive tier from another reference can outrank a larger
mismatch. Read `dominance_status` and the runner-up columns with the tier.

## What the numbers mean

- **Query genes.** The count comes from the parsed query table plus genes that appear in hits. It is
  not a checked list of every gene. A trimmed query table shrinks the count and raises the fractions.
- **Recognizable.** In the convergence table it means a query gene with a hit. In the profile it
  applies a minimum-identity rule. The two shares are not interchangeable.
- **One hit per pair.** For each query gene and reference, the row with the highest BLAST score is
  kept. This is not a one-to-one match between genes.
- **Coverage over 100%.** The source value is kept and flagged `SOURCE_GT100_CAPPED_FOR_INTERPRETATION`.
  Tiers use the capped value.
- **Missing coverage.** A blank or non-numeric coverage cell stays blank. It is not 0% and it is not
  in range. The row's `coverage_qc_flag` then includes `MISSING_OR_NONNUMERIC_COVERAGE`, and
  `coverage_missing_row_count` gives how many hits lacked it. The coverage medians use the hits that
  have a value; they are blank when none do.
- **Bad files.** A file that fails to parse adds to `parse_error_count`. The overall status can still
  read `PASS` if other files gave rows. Check the count.
- **Empty or missing input.** `NULL_NO_MIBIG_GENE_HITS` covers an empty, missing, skipped or failed
  parse. Look at the source and error context to tell which. A KnownClusterBlast file that is present
  with no hits is reported as `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED` in the KnownClusterBlast evidence
  state. See [reading your results](READING_YOUR_RESULTS.md). It is not a validated negative.
- **`KNOWN_ANCHORED`.** This label means an accession pattern plus a profile fraction of 0.20 or more.
  It is not compound identity. The dark-matter labels are reporting labels, not novelty findings.

## How to cite

- Do write: "antiSMASH reported N proteins with similarity to the <family> comparator (median identity
  X%, coverage Y%), tier H2_STRONG_FAMILY. This supports the hypothesis of a related biosynthetic
  cassette, pending locus-specific review." Give the locus as
  strain / full node-or-contig / region / BGC alias, plus the MIBiG accession and version.
- Do say when the region is on a contig edge. Its annotations are then incomplete context.
- Do not read a tier as a product, activity or novelty claim.
- Do not count convergence and KnownClusterBlast as two separate confirmations. Both come from the
  same antiSMASH output.

## Checks and limits

Packages without the v2 reporting schema return `LEGACY_NOT_APPLICABLE` from the reporting gate. That
is not a claim that the old evidence is complete. The gate checks the declared schema, files, headers,
row counts and workbook match. It does not check source bytes or full locus identity.

The tier logic is covered by unit tests. A self-reported trial on 1,507 BGCs gave 45,767 retained rows
and no parse errors. Treat live tiers as provisional. Before you cite a result, record the source ZIP,
package and parameters, and report how complete the query-gene count is. For ranking limits, see
[the BGC ranker](DEFINITIVE_BGC_RANKER.md).
