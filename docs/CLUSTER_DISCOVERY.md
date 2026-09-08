# cluster_discovery — find strains carrying a BGC from a diagnostic marker

Discovers other strains that carry a cluster, from a single diagnostic marker protein, using
only public NCBI data:

    marker.faa --BLASTp(NCBI, Entrez-filtered)--> homolog proteins
               --IPG (Identical Protein Groups)-> source assemblies + organism
               (--verify, optional)-------------> confirm by co-occurring cluster genes

Output: `candidate_strains.csv` (assembly, organism, strain, marker %identity, protein) and a
an external download_genomes.sh helper you write around the NCBI `datasets` command ( — ready to feed a genome download + cluster
extraction + `cluster_gene_compare` run.

## Usage

    python tools/cluster_discovery.py \
        --marker nikJ.faa \
        --entrez "Streptomyces[Organism]" \
        --min-identity 60 --max-strains 20 \
        --outdir OUT

## Why a marker + IPG (not just BLAST)

A diagnostic gene (e.g. the cluster's radical-SAM signature) is a sharper probe than the whole
cluster: it is present once per cluster and diverges slowly. NCBI's non-redundant proteins
(`WP_...`) collapse many assemblies, so a raw BLAST hit does not name a genome — the **IPG**
database maps each protein back to every assembly that encodes it, which is how one hit becomes a
concrete, downloadable list of strains.

## Confirming the cluster is really there

A marker homolog means a strain *may* carry the cluster — radical-SAM enzymes occur in other
contexts. Confirm presence by checking that >=2 cluster genes co-occur in a short window of the
candidate genome (the same gene-call + marker-scan step used to locate the cluster in the seed
strains). `--verify` is the hook for this; without it the table is candidates, not confirmed
carriers, and is labelled as such.

## Testability

The single network dependency is the injectable `Net` object; `test_cluster_discovery.py` runs
the whole pipeline against a fake `Net` (no NCBI), and the parsers are validated on real NCBI
BLAST/IPG output shapes. 4 tests, network-free.

## Validated

nikJ (BGC008 radical SAM) -> 100 Streptomyces homologs at 76-79% -> IPG -> assembly accessions
(e.g. GCF_042756365.1, Streptomyces sp. NPDC059092). Capacity-level throughout.
