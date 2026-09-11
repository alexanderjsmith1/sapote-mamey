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

    python tools/fetch_reference_cluster.py \
        --db anchored.db \
        --acc BGC0000877:polyoxin \        # MIBiG or cohort cluster from the DB (repeatable)
        --acc AS-XXX_NODE_42:AS-XXX_BGC043 \ # cohort clusters match on gbk.path substring
        --ncbi MF055656.1:nikkomycin \      # NCBI nucleotide efetch (repeatable)
        --outdir refs/

Writes `refs/<label>.gbk` per reference, ready to drop into any comparison. Cohort members are
selected the same way as MIBiG accessions — by a substring of `gbk.path` — so a strain's region
is one flag away from a comparable GBK.

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
