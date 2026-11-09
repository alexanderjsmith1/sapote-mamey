# fetch_reference_cluster: reference and cohort cluster GenBank files

`tools/fetch_reference_cluster.py` writes a reference cluster as a GenBank (`.gbk`) file. The reference can be a MIBiG cluster or a cohort cluster from a BiG-SCAPE database, or a record from NCBI. You then give the file to the comparison tools: `clinker` (draws gene-by-gene alignments, see [companion tools](companion_tools.md)), [cluster_gene_compare](CLUSTER_GENE_COMPARE.md), `tools/bgc_reference_align.py` and [extract_cluster](EXTRACT_CLUSTER.md).

## Which route you can use

- `--ncbi` needs only a network connection. **It contacts NCBI at once.** It is not a dry run. Use it only when you have decided to make that request.
- `--acc` needs a BiG-SCAPE database (`--db`) that a BiG-SCAPE run wrote and that already holds the MIBiG and cohort clusters. Without such a run you cannot use `--acc`. See the [BiG-SCAPE cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md). Selecting from the database needs no network.
- Both routes need Biopython installed.

## Run it

```bash
python tools/fetch_reference_cluster.py \
    --db anchored.db \
    --acc BGC0000877:polyoxin \
    --acc EXAMPLE_NODE_42_length_51234_cov_12.3.region001:EXAMPLE_BGC043 \
    --ncbi MF055656.1:nikkomycin \
    --outdir refs/
```

- `--acc <text>:<label>` selects a MIBiG or cohort cluster from the database. Repeat it for more.
- `--ncbi <accession>:<label>` fetches an NCBI nucleotide record. Repeat it for more.
- Use a new `--outdir` folder. The check is per destination: an existing folder is accepted, but any output file that already exists there (`<label>.gbk` or `<label>.reference_selection.json`) is refused, and nothing is written.
- Each `<label>` must be unique and a plain file name, with no path separators.

What you should see: for each reference, the selected path on stderr and these files in `refs/`:

```text
refs/polyoxin.gbk
refs/polyoxin.reference_selection.json
refs/EXAMPLE_BGC043.gbk
refs/EXAMPLE_BGC043.reference_selection.json
refs/nikkomycin.gbk
refs/nikkomycin.reference_selection.json
```

Failure is a non-zero exit. A selection that is missing, ambiguous or empty fails visibly. The tool builds and checks the whole set before it publishes anything. If an ordinary publishing error occurs, it rolls back the files it wrote. It is not a crash-safe transaction. After an interrupted run, inspect the folder and use a new `--outdir`.

## How `--acc` picks a record

Each `--acc` text must select exactly one record by its stored GenBank path.

- A MIBiG selector needs all seven digits (`BGC0000877`).
- An NCBI-shaped selector needs an explicit version.
- A bare package BGC alias is not an accession.
- Any other text matches as a literal piece of the path. This binds the chosen path. It does not prove the accession or the full locus identity.
- No match stops with "not found".
- More than one match stops and lists the paths. Give a longer piece, such as the full region file name.
- A contig name with no region is matched like any other text. If it selects exactly one stored path, that path is used; if it matches several regions on the same contig, it is refused as ambiguous. Check the chosen path in the receipt against the complete locus identity `strain / full node-or-contig / region / BGC alias` before you use the file.

## The receipt

`refs/<label>.reference_selection.json` records the requested selector, the database path and SHA-256, the chosen row and its original source path, the CDS count, `retained_cds_scope`, and the output file path and SHA-256. If a SQLite write-ahead file exists, its path and hash are included. For `--ncbi`, the receipt records the request URL, the returned record IDs and the response hash instead, plus `source_cds_feature_count` and `untranslated_cds_dropped`. Both routes record `cluster_completeness_state` and `characterization_state` as `NOT_ASSESSED`. Keep it beside the `.gbk`.

`--ncbi` needs a complete versioned nucleotide accession. It must return exactly one record with a matching ID and translated CDS.

## What the output file is

The `.gbk` is a comparison file built from protein features, not a deposited record.

- Its nucleotide sequence is a run of `N`. Its locus tags are rebuilt labels. Even an NCBI record is reduced to translated CDS features.
- Do not use it as a nucleotide sequence, a CDS-DNA export, an assembly or an input to a nucleotide alignment. Keep the original record when you need those bytes.
- A CDS with a stored Pfam hit gets a `/gene` display label from its best-scoring hit. A CDS without one keeps its rebuilt locus tag. These labels feed `clinker` and `cluster_gene_compare`. They are not gene function, and they do not mean every CDS was annotated.
- The tool checks that the file reads back as one record with the same translations, and that they use only letters the downstream BLOSUM62 matrix accepts. Otherwise it refuses.
- Every query and reference GenBank must hold exactly one record.

`tools/bgc_reference_align.py` applies the same database selection rule. A reference with no translated CDS stops the comparison before it writes a figure or CSV. A successful run also writes `<strain>_<bgc>_reference_selection.json`, or `<bgc>_reference_selection.json` without `--strain`. It binds the query, each reference, the identity threshold and both outputs to their SHA-256 values. Keep the database, and its write-ahead file, stable during the run.

## Labels are not locus identities

The path piece and the output label are lookup and display names. For any BGC of yours that you interpret, take `strain / full node-or-contig / region / BGC alias` from its package. Do not turn a nickname into a locus identity.

## Where this fits

```text
fetch_reference_cluster   accession -> annotated reference or cohort GBK
extract_cluster           raw genome  -> annotated cluster GBK
cluster_gene_compare      GBKs        -> gene-by-gene comparison
```

Your own strains come from antiSMASH, external genomes from `extract_cluster`, and references from this tool. All three end up as comparable GenBank files. A reconstructed reference holds only the CDS its source retained: the CDS rows stored in the database record (`CDS_ROWS_PRESENT_IN_SELECTED_DATABASE_RECORD`), or the translated CDS of the NCBI record (`TRANSLATED_CDS_FEATURES_OF_FETCHED_RECORD`). The tool does not check that every gene of a cluster was kept, and a cohort or NCBI record need not be a characterized cluster. Completeness, record identity and characterization are separate questions. Comparison to the file is homology, not product identity.
