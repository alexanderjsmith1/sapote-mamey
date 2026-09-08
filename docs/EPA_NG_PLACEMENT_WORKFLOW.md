# EPA-ng 16S Placement — the formal Sapote-Mamey workflow (paper-ready)

**Lane:** Eggplant · **Engine:** sapote-mamey ≥ v9.7.411 (needs the EGGPLANT_411 patches) · **Status:** formal, end-to-end.
**Supersedes** the older `docs/PHYLO_PLACEMENT_WORKFLOW.md`, which referenced a producer (an older unpackaged producer script)
that was never packaged, leaving the ggtree renderer orphaned. This workflow is self-contained: every step
is a shipped tool.

> **Claim-safety (governing).** 16S rRNA is a phylogenetic **anchor / clade-neighbourhood** indicator, **not**
> a species assignment. A placement states the genus/clade neighbourhood a query falls into on a FIXED
> reference backbone, with a per-query **likelihood-weight ratio (LWR)** as confidence. No ANI/AAI, no
> bioactivity/structure claims; judgment deferred.

## When to use this
16S-only strains (no genome), or a fast neighbourhood read before a genome/MLSA tree. Queries are **placed**
on a fixed type-strain backbone; they never perturb its topology. For genome trees use `docs/GTOTREE_WORKFLOW.md`.

## The pipeline (one command per stage)

```
phylo_place.py all <ref_16S.fasta> --group <Genus> --query <queries.fasta> \
     --add-outgroup <Genus> --one-per-species --bootstrap 10 --outdir <run>/placement
     # build-ref (mafft → raxml-ng GTR+G, rooted on the registry outgroup) → EPA-ng place → gappa graft → report
     # driver interpreter: Tools/bin/python3 (Biopython); binaries: miniconda3/envs/placement/bin
     # → epa_result.jplace, epa_result.newick, <Genus>_placements.tsv, <Genus>_neighborhoods.tsv, refpkg/

phylo_postflight.py <run>/placement/epa_result.newick --outgroup <OutgroupGenus>   # P3 is placement-aware
tree_sanity_check.py <run>/placement/epa_result.newick --outgroup <OutgroupGenus>  # must PASS (outgroup-aware)

build_placement_ggtree_inputs.py --graft <run>/placement/epa_result.newick --group <Genus> \
     --neighbors <N> --host-table <paper strain table> --origin-table <isolation_source.tsv> \
     --outgroup-substr <OutgroupGenus> --out-prefix <run>/ggtree/<Genus>
     # → <Genus>_pruned.nwk + <Genus>_ggtree_annotation.tsv (host+accession on queries; isolation-source on refs)

GG_TITLE="..." GG_METHODS="<full methods paragraph>" \
Rscript ggtree_placement.R <run>/ggtree/<Genus>_pruned.nwk <run>/ggtree/<Genus>_ggtree_annotation.tsv \
     <run>/ggtree/<Genus>_fig noloc
     # → paper-ready PDF + PNG: queries red/bold (host + 16S accession), refs blue with an
     #   isolation-source dot, methods footer below the tree.
```

## Governing rules (baked into the tools)
1. **Source separation.** One genus/cohort per tree. `--group` is required and stamped into every output;
   a single genus is the strictest separation (EGGPLANT_411 per-genus patch).
2. **Registry outgroup, rooted.** The outgroup is looked up in `OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv`
   (e.g. Actinomadura → *Actinocorallia herbida* GCF_003751225.1 / NR_115631.1, LOCKED — sister genus, not
   *Spirillospora* which nests inside Actinomadura). build-ref appends it and roots the backbone on it.
3. **No foreign-genus sentinels.** On a per-genus backbone with a registry outgroup, off-genus "sentinel"
   records are stripped before inference (they otherwise dominate the tree and FAIL sanity).
4. **Gates before render.** `tree_sanity_check` (outgroup-aware) must PASS. `phylo_postflight` P3 is
   placement-aware (a graft carries no tree-wide UFBoot; confidence = LWR + backbone Felsenstein bootstrap).
5. **The prune ladder.** `--neighbors-per-query N` (figure) / `--neighbors N` (producer) renders a series:
   N=1 tight, N=3 medium, `--keep-all-refs` full. The full backbone size is always stated.
6. **Honest labels.** Query tips = strain / host / 16S GenBank accession from the paper strain table (the
   authoritative host source; NOT `host_common`, which had defects). Reference tips carry an **isolation
   source** dot (soil / soil-rock / plant / lichen / insect-associated / clinical-animal / other / unresolved),
   curated from species-description papers + BacDive — never invented; "unresolved" where no source is found.
   The outgroup is **not** an isolation source and carries no dot.
7. **Methods travel with the figure.** `GG_METHODS` prints a wrapped methods block below the tree, so a bare
   image is still a complete, sourced deliverable.

## Confidence reading
LWR ≥ 0.8 = "within" that clade's neighbourhood; LWR < 0.4 = report as "near", not "in". A denser reference
lowers LWRs (finer ambiguity), which is more honest, not worse. A long pendant length = a divergent query.

## Package layout (self-contained deliverable)
```
<run>/
  METHODS.md                       question, provenance, exact command, tool versions, LWR table, denominators
  inputs/                          harvested reference 16S + query 16S
  tree/placement/                  jplace, grafted newick, placements TSV, neighborhoods, refpkg (+ FBP support)
  ggtree/                          pruned.nwk, annotation TSV, isolation_source.tsv, PDF+PNG (ladder rungs)
  logs/                            build log, tool provenance (versions)
```

## Version-matched tools
raxml-ng 2.0.2 · EPA-ng 0.3.8 · gappa 0.9.0 · mafft 7.526 · Biopython 1.87 · ggtree 4.2.0 / R 4.6.0 ·
Sapote-Mamey phylo_place (engine 1.9.149). Cite the exact installed versions (`mamey doctor`).
