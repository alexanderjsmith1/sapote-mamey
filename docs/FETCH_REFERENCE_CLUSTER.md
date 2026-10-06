# fetch_reference_cluster — reference/cohort cluster GBKs, as a shared step

The comparative tools (`clinker`, `cluster_gene_compare`, `bgc_reference_align`, `extract_cluster`)
all consume GenBank files, but there was no first-class way to *obtain* a reference or cohort
cluster as a GBK — the DB->CDS logic was embedded inside `bgc_reference_align` (returning internal
dicts, not files). So every comparison against a MIBiG reference or a cohort member meant
hand-reconstructing a GBK. This exposes that as a reusable step and improves on it:

- **Annotated output.** The anchored BiG-SCAPE DB stores Pfam domains (`hsp`) next to every CDS
  (`cds.aa_seq`), so the reconstructed GBK is written with `/gene` labels (Pfam short-names where
  known, the accession otherwise — never blank). Those labels flow straight into clinker and
  cluster_gene_compare's auto-labelling.

## Usage

    # --acc <text>:<label>   a MIBiG or cohort cluster from the DB (repeatable)
    # --ncbi <acc>:<label>   an NCBI nucleotide record (repeatable)
    python tools/fetch_reference_cluster.py \
        --db anchored.db \
        --acc BGC0000877:polyoxin \
        --acc AS-XXX_NODE_42_length_51234_cov_12.3.region001:AS-XXX_BGC043 \
        --ncbi MF055656.1:nikkomycin \
        --outdir refs/

Writes `refs/<label>.gbk` per reference. Each `--acc` text must select **exactly one** record in the
DB's `gbk.path`. It is matched as plain text (SQL wildcards are escaped). No match stops with "not
found". More than one match stops with the list of matching paths: give a longer substring, such as the
full region file name. The selected path is printed on stderr and preserved in
`refs/<label>.reference_selection.json`. Each receipt contains the requested selector, resolved DB
path and SHA256, selected `gbk` row ID and original source path, CDS count, and output GBK path
and SHA256. If a SQLite WAL exists, its path and SHA256 are included too. For NCBI inputs, the
receipt records the request URL, returned record IDs and response SHA256 instead of a DB binding.
Keep the receipt alongside the GBK; it records source selection and output bytes, without upgrading
similarity into a compound or activity claim. A strain/contig fragment without the region can match several
regions on the same contig; that is now refused rather than resolved to the first row.

All requested references are resolved and the complete output/receipt set is staged before
publication. Missing, ambiguous, or empty selections fail visibly with a nonzero exit. Labels must
be unique, nonempty filename basenames; path separators and traversal names are refused.
Existing output destinations are refused rather than overwritten. Use a fresh output directory
for a new selection or rerun, and retain earlier GBK/receipt pairs as history.

The query and every local or fetched GenBank reference must contain exactly one record; multiple
records are refused rather than concatenated or silently truncated. All final paths are checked
for containment within the resolved output directory. Ordinary publication errors roll back newly
published files. This is not a concurrent atomic multi-file transaction or crash-recovery mechanism:
keep sources stable, avoid concurrent output writers, and inspect an interrupted output directory
before treating any set as complete.

`bgc_reference_align` applies the same DB selection rule. Every requested DB, NCBI, or local GBK
reference must contain translated CDS; a missing or empty member stops the comparison before its
figure or CSV is written. A successful comparison also writes
`<strain>_<bgc>_reference_selection.json` (or `<bgc>_reference_selection.json` without `--strain`),
which binds the query GBK, each source selection, the global-identity threshold, and both output
files to their SHA256 values. Local GBK references are bound to their resolved paths and bytes.
Use a stable source DB during the run and retain any WAL with the DB when reproducing its state.

## Why this closes a loop

    fetch_reference_cluster   accession -> annotated reference/cohort GBK   <-- this tool
    extract_cluster           raw genome -> annotated cluster GBK
    cluster_gene_compare      GBKs -> gene-by-gene deliverable

Between these two ingress tools, every kind of cluster — your strains (antiSMASH), external
genomes (extract_cluster), and characterised/cohort references (fetch_reference_cluster) — becomes
a comparable GBK without hand-reconstruction.

## Validated

Reconstructed polyoxin (BGC0000877) from the real anchored DB: 39 CDS, 35 annotated
(FMO_monooxygenase, carbamoyltransferase, MFS_transporter, ...). Capacity/architecture-level:
a reconstructed reference is the characterised cluster's genes; comparison to it is homology.
