# extract_cluster — bring a raw genome into the pipeline

The Mamey pipeline starts from antiSMASH ZIPs; a bare genome FASTA has no entry point. This
tool provides one: given a genome and one or more diagnostic marker proteins, it gene-calls
(pyrodigal), finds the tightest gene window where the markers co-localise, and writes that
region as an annotated GenBank file — no antiSMASH run required.

It is the missing link that closes the external-genome loop:

    cluster_discovery   marker -> candidate genomes (accessions)
    extract_cluster     genome -> annotated cluster GBK        <-- this tool
    cluster_gene_compare clusters -> gene-by-gene deliverable

## Usage

    python tools/extract_cluster.py \
        --genome GCF_044742665.1.fna \
        --marker nucleoside_markers.faa \
        --label NPDC08785 \
        --min-markers 2 --outdir OUT

`--marker` holds >=1 diagnostic proteins (e.g. a radical-SAM signature + 1-2 co-conserved
genes). Outputs `LABEL_cluster.gbk` (marker genes labelled via /gene, ready for clinker /
cluster_gene_compare) and `LABEL_extract.json` (present/absent, contig, coords, marker identities).

## Doubles as cluster_discovery's confirmation step

A marker BLAST hit says a strain *may* carry the cluster. Running extract_cluster on that
genome with `--min-markers 2` confirms it — the cluster is called present only when >=2 distinct
markers co-occur in one window. So discovery -> extract_cluster upgrades a candidate to a
confirmed carrier, and hands back the GBK in one step.

## Validated

On the real NPDC08785 and x-80 genomes it reproduces the by-hand extractions exactly
(cluster PRESENT, ~14 kb, 11 CDS, correct contig). Marker co-occurrence is capacity-level
evidence of cluster presence, not proof of product identity.
