# BLASTp and BGC novelty: how to read four channels

This page is a reading guide for people who already ran the pipeline and have BLASTp results. It tells you what each BLASTp channel can answer and how to combine them without mixing them. To run the searches and load the results, use [ONLINE_BLASTP_PROTOCOL.md](ONLINE_BLASTP_PROTOCOL.md). To use the results in a card, see the [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md). Terms are in the [glossary](GLOSSARY.md).

The page changes no files. Everything below produces class-level capacity hypotheses.

## Claim ceiling

- A BLASTp percent identity measures identical residues in an alignment; it can support a homology hypothesis but does not establish the same molecule.
- A few genes that resemble a characterized cluster are a class-level anchor, not that compound.
- A close hit in nr does not mean "known". nr is dominated by genomes never assayed for natural products. A close hit means a similar sequence exists.
- A distant nr hit is a prior that says "worth a look". It is not activity, and it is not taxonomic or chemical novelty. It holds only inside the database, query and settings you searched.
- This layer ranks where to look. Judgment is deferred.

## The four channels

Each channel answers one question. Never mix them. Keep each channel's results in their own folder and keep its channel label. The label column differs by output: `blastp-online` writes `<BGC>_online_blastp.csv` with `channel` and `source_channel`, identity in `pct_identity` and positives in `pct_positive`. The SQLite BLASTp store (`hits` table, loaded by `tools/ingest_blastp_rollups.py`) uses `subject_db` and `channel`, with `pct_identity` and `pct_positives`. Not every output carries a `subject_db` tag. Identity and positives stay separate columns in both. Never average or merge them, and keep a blank cell blank.

| Channel | Database | Runs | Question it answers |
|---|---|---|---|
| nr | NCBI `nr`, the non-redundant protein database (remote) | submitted to NCBI one batch at a time | How close is each gene to its best returned sequence? This is a divergence prior, bounded by database version, coverage and settings. |
| MIBiG / ClusterBlast | antiSMASH KnownClusterBlast, read from your package (local) | when the package is built | Does the locus resemble a characterized reference cluster, across several genes? |
| SwissProt (Swiss-Prot) and other UniProt | the exact local database you selected | local search | What function does a reviewed or unreviewed protein suggest for each gene? A named subject does not verify the query's function. Keep reviewed and unreviewed records apart. |
| ClusteredNR | NCBI `nr_cluster_seq`, one representative per cluster of nr (remote) | submitted to NCBI one batch at a time | A representative per cluster. It helps where nr is saturated. |

A hit from one channel is never merged into, averaged with, or relabeled as another. Unavailable evidence stays a hold. It is never a negative. A channel that did not run reads "stream not run", not "no hit".

## What your package prints for the MIBiG / ClusterBlast channel

Use the package's own labels. `READING_YOUR_RESULTS.md` explains the evidence states and the percent bands. In short:

- `KCB_similarity_pct` is antiSMASH's similarity percent for the top KnownClusterBlast hit. The package turns it into a band: high at 70 or above, moderate at 40 or above, low above 0, `none` at exactly 0. Blank is not zero. See [Reading your results](READING_YOUR_RESULTS.md).
- `mamey/kcb_frontpage.py` also gives a front-page tier from similarity and the number of matching genes:

| Tier | Rule |
|---|---|
| STRONG | similarity 40 or above, and 8 or more matching genes |
| MODERATE | 25 or above, and 5 or more genes |
| COINCIDENTAL | 80 or above, but 2 or fewer genes |
| WEAK | 15 or above, and 4 or more genes |
| LARGE_GENERIC | 8 or more genes, under 15 |
| LOW | none of the above |

Quote the label with its source, the channel, the reference name and the gene count. Write it as `N genes at X% similarity, <family>`. Never write `= <compound>`. A hit only to genes that recur across many unrelated clusters (scaffold or tailoring genes) is capacity noise, not a family call.

## Combine anchor and nr distance by hand

The strongest lead is real machinery in a distant background: a clear MIBiG family match and a low nr identity. The tools do not compute this rank. You compute it from the package tables.

1. Take nr distance as 100 minus the median nr percent identity across the BGC's genes.
2. Sort the BGCs with a strong family match by nr identity, lowest first.
3. Carry the number of genes behind each median. A median over 2 genes is not comparable to one over 40. Treat a distance from fewer than about 5 genes as soft, and say so.
4. Check for a possible over-merged region. The `COMPOSITE_SEPARABLE` label is an annotation-based signal, not proof of separate biosynthetic units. Review the source architecture before splitting the region or interpreting either number.

## Split loci

Two loci can be two halves of one pathway. Two fields describe that. Read them separately:

- `subject_tiling_verdict` holds `COMPLEMENTARY_SPLIT` or `TERMINUS_TRUNCATION_SPLIT`.
- `functional_rescue_class` holds `COMPLEMENTARY`, `BOTH_CORE`, `ACCESSORY_ONLY`, `AMBIGUOUS` or `UNKNOWN_NO_PROFILE`.

These fields come from the RG-GMCI rescue step. See [the rescue atlas](RGGMCI_RESCUE_ATLAS.md). They can mark a candidate split. They do not prove adjacency, one pathway, product identity, or the absence of paralogs. Keep both source records visible, with each endpoint written as `strain / full contig / region / BGC alias`. Do not collapse the loci or subtract a rescue from a BGC count without independent assembly and synteny evidence and review.

## Running the remote channels

Details and commands are in [ONLINE_BLASTP_PROTOCOL.md](ONLINE_BLASTP_PROTOCOL.md). The rules that matter here:

- nr and ClusteredNR share one NCBI search budget. Submit one batch at a time, never a burst, and keep few open RIDs (a RID is NCBI's job ID for one search). `auto-blastp` paces itself at about one query every 8 minutes.
- If NCBI refuses new submissions while status checks still return results, stop and wait. Too many open searches is one possible cause; retain the response and check the service guidance before assigning a cause or retrying.
- The daily submission ledger (`mamey/blast_ledger.py`) counts searches against NCBI's soft limit of about 100 per 24 hours.
- NCBI submissions carry no e-mail address or personal identifier. The EMBL-EBI route (`blastp-ebi`) is different: EBI requires a contact `--email`.
- Send only sequence you may make public.

## Using the result downstream

- Phylogeny overlay: the per-strain count of anchored and divergent BGCs can be painted on tree tips that use the tree's exact leaf labels. The checks are in [PHYLOGENETICS_WORKFLOW.md](PHYLOGENETICS_WORKFLOW.md).
- Mode B: an anchored lead can be promoted in a card only when the per-gene BLASTp channel is current for every gene on the declared roster (no unresolved genes, "U = 0"). The query and result must be bound to each other. The card also needs the observation, inference, alternative and falsifier structure. Thin or weak evidence is a hold, not a lead.

`python tools/modeb_evidence_gate.py <card.md> [--fresh-blastp yes|no]` lints a card file for this structure. It is a text check. It does not verify the gene roster, the query hashes or the job receipts. You supply the freshness answer yourself.

## Exclusions

Respect the engine's exclusion list in `mamey/exclusions.py`. Do not hard-code exclusions. The accessors have separate scopes: `raw_analysis_excluded()` (contaminated plus void raw assemblies) for readers of raw per-gene and BLASTp tables, and `governed_excluded()` for governed conclusions. With no cohort exclusion file bound (`OFFICIAL_DATA/exclusions.json` via `MAMEY_OFFICIAL_DATA` or `MAMEY_DATA_ROOT`), the shipped default excludes nothing. Not every reader applies an accessor: `blastp-followup` parses the Hit Table you give it and does not filter strains, and `tools/ingest_blastp_rollups.py` skips only the strains named in the `SAPOTE_EXCLUDE_STRAINS` environment variable (comma-separated), not the `mamey/exclusions.py` list. Record which exclusion file and version a result used, and check the input roster against it yourself.

## The report wrapper

`tools/mamey_pipeline.py` collects the package hashes, the validation output, the explanation output and optional figure text into one report.

```bash
python tools/mamey_pipeline.py --strain EXAMPLE --package runs/EXAMPLE/package \
  --engine . --out report_run
```

`--figures <dir>` and `--lit-refs <tool>` are optional. Choose a new `--out` folder. Report files are overwritten on a rerun. Figures render into `<figures dir>/_rendered`, not into `--out`.

Exit 0 means the report was written. Exit 1 means validation or explanation failed, a requested figure folder was missing, or the figure renderer failed. A report can still contain failed stages, so read each stage's output. A zero exit from a child step is not proof that its files are good. The wrapper does not check that package bytes stay unchanged while it runs. Keep the stage receipts and hashes. It does not run BLASTp or comparator searches. Those need their own commands and receipts.
