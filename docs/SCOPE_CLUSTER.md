# scope_cluster — scope an over-merged antiSMASH region to its true protocluster

antiSMASH merges neighbouring protoclusters into one region ("candidate cluster"). A region GBK
for a nucleoside BGC can therefore silently include an adjacent saccharide or NRPS cluster, so
measuring or comparing the whole region over-counts the cluster and can assign genes to the wrong
pathway. This tool reads the region's own `protocluster` / `cand_cluster` / `core_location`
features and extracts just the target category's genes — no gene-window guessing.

## Why it exists (a real correction)

While comparing nucleoside clusters, a 69-CDS antiSMASH region was taken as one nucleoside BGC; it
was actually three merged protoclusters (nucleoside + saccharide + NRPS). A glycosyltransferase
and epimerase from the merged **saccharide** cluster were briefly read as decoration on the
**nucleoside** product. Scoping to the nucleoside protocluster excludes them and fixes the read.

## Usage

    python tools/scope_cluster.py --gbk region.gbk --category nucleoside \
        --label NPDC08785 --outdir OUT [--core]

Outputs `OUT/<label>_<category>_scoped.gbk` (the scoped cluster, ready for cluster_gene_compare /
cluster_relate / clinker) and `OUT/<label>_<category>_scope.json` (boundary, genes kept, genes
excluded as merged neighbours, and overlap flags where a kept gene also sits in another category's
protocluster core). `--core` uses the tight protocluster core span instead of the candidate
neighbourhood.

## Fits the pipeline

Runs directly after antiSMASH / before comparison:

    antiSMASH region GBK  ->  scope_cluster (true boundary)  ->  cluster_gene_compare / cluster_relate

## Validated

NPDC08785 region015 (69 CDS, 3 merged protoclusters) -> nucleoside scoped to 22 CDS / 30.3 kb,
correctly excluding the saccharide glycosyltransferase + epimerase; the carbamoyltransferase,
nikJ, truD, and O-methyltransferase are retained. Capacity/architecture-level.
