# Working method — cohort phylogenomic trees (Sapote-Mamey)

**Status:** historical working-method record from 2026-08-26; not the current portable execution recipe.
Use [the current companion contracts](COMPANION_RUN_CONTRACTS.md),
[phylogenomics](phylogenomics.md) and [preflight](GTOTREE_IQTREE_PREFLIGHT.md)
for .447 behavior and authority. The prior source records, timing claims and owner
sign-offs below are retained history requiring their original run packets before reuse.
They do not authorize rebuilding,
upgrading or relabeling a current tree.

Recorded historical status: Two trees built this way reportedly received reviewer sign-off
review (bee/wasp Pseudonocardiaceae and bee/wasp *Nocardia*). This is the reproducible recipe
plus the reasoning behind each governed choice, so the next tree is a parameter change, not a
re-derivation.

---

## Which GToTree — and why the passing figures say 1.8.19

**The two figures the owner passed were built with GToTree v1.8.19** (confirmed in each run's
`citations.txt`). A figure's methods must describe how *that* figure was made, so their methods
sections state 1.8.19 / the 138-gene NCBI-taxonomy Actinobacteria SCG set. That is not a
placeholder to be relabelled later.

**Go-forward, the working method moves to GToTree v2.0.0**, on three findings from this
session's trial:
- v2's marker sets are re-derived from GTDB r232 and are better curated. For actinomycetes the
  set is Actinomycetota (92 genes): it drops all 14 domains-of-unknown-function and a batch of
  paralogy-prone metabolic enzymes (ADK, PGI, HisG, ArgJ, ...) that the 138-gene set carried,
  keeping 78 shared markers and adding 14 better-behaved ones. Provenance is fully recorded
  (GTDB release, Pfam version, genome count, build date); the 138-gene set's metadata has none
  of that.
- Head-to-head on an identical 19-genome input with the identical HMM and IQ-TREE settings, v2
  and 1.8.19 produced trees at Robinson-Foulds distance 2 of a possible 32, and the single
  differing node was unsupported either way. The versions agree.
- v2 is faster (2.9 min vs 1.2 min GToTree stage on the 19-genome set) and adds resume,
  partition files, and `-w` reference auto-selection.

**The one hard rule for a mixed series:** the marker set must be stated per tree. A 92-gene v2
tree and a 138-gene 1.8.19 tree are not directly comparable, so a published figure series must
be all-one or explicitly labelled. Recommended path: rebuild the current passing trees on v2/92
once, so the whole series is internally consistent, and cite 1.8.19 only if those exact figures
are published as-is.

**Retained GToTree v2 compatibility reference:** [compatibility patch notes](../tools/upstream_gtotree2/COMPATIBILITY_PATCH_NOTES.md)
describe the target snapshot and mechanics of `tools/upstream_gtotree2/gtotree2-input-sanity-and-env-compat.patch`:
nonzero fatal exits, legacy environment-variable fallback and input-format preflight.
The recorded 1294 passed, 1 skipped result is historical and unverified against an actual external
checkout for this documentation change; it does not establish current installation compatibility.
Author correspondence is excluded from the bundle.

## Historical recipe and current portability holds

```text
# Historical commands, not a copy/paste recipe for the portable .447 bundle.
# 1. Stage a tree directory:  <dir>/genomes/  +  <dir>/TREE_SPEC.json
#    - queries: pulled from OFFICIAL_DATA/STRAIN_METADATA.tsv, filtered to one cohort,
#      genus as required, excluded==Y dropped
#    - comparators: >= 1 named genome per query genus (skip for declared novel genera)
#    - outgroup: from OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv (see rule below), filename *_OUTGROUP

# 2. Build through the gate (the ONLY sanctioned path — no skip flag):
bash tools/build_tree.sh <dir>
#    sources gtotree_env.sh, runs phylo_preflight.py on the FINAL staged dir, refuses on any FAIL,
#    then: GToTree -f genome_list.txt -H "$GToTree_HMM_dir/Actinobacteria.hmm" -N -j 4 -o gtotree

# 3. Tree + support:
iqtree -s gtotree/Aligned_SCGs.faa -m LG+F+G4 -B 1000 -alrt 1000 -T 4 -o <OUTGROUP> --prefix iqtree -redo

# 4. Label + render + validate the finished tree:
Tools/bin/python3 amber_phylo/render_all.py <dir>/iqtree.treefile <dir>/genomes <out.png> "Title||Subtitle"
miniconda3/envs/phylo/bin/python tools/phylo_postflight.py <dir>/iqtree.treefile --scope family
```

Current source differs from this recorded recipe: `build_tree.sh` now runs
IQ-TREE internally through supported completion and final retention checks. Running
the historical standalone IQ-TREE command afterward would duplicate/overwrite
inference. The shell wrapper selects Python from
`$PROJECT_ROOT/miniconda3/envs/phylo/bin/python`; it is not an arbitrary activated
interpreter. Its default GToTree jobs and IQ-TREE threads are four, not the default
one-core policy. Bind the actual environment and explicit resource settings before
considering that specialized workspace route. The portable `phylo-run` interface
has its own defaults and preflight boundaries described in the linked guide.

The external historical renderer shown above is not a bundle command; the shipped
helper is `tools/render_all.py`. Select the maintained Figure Factory or prepared
series route for current rendering and retain the original methods and topology.

## The governed choices (do not re-decide these per tree)

- **Cohort separation is a governing rule.** moss / bee-wasp / attine strains go in SEPARATE
  trees. The gate reads the `cohort` column of the governed table and FAILs a cross-cohort mix
  (check H1). This exists because three trees were built cross-contaminated before it did.
- **Outgroup by ingroup rank.** Single-genus ingroup -> the sister *genus* from the registry
  (e.g. *Nocardia* ingroup -> *Rhodococcus erythropolis* GCF_017656525.1). Multi-genus,
  family-scoped ingroup -> the sister *family* / near sister order (e.g. Pseudonocardiaceae ->
  *Nonomuraea pusilla*, because *Actinosynnema*/*Actinopolyspora* sit inside the family).
- **Exclusions are enforced, not remembered.** `excluded==Y` in the governed table with a reason
  keeps a strain out of every tree automatically (check H2). Contaminated assemblies
  (size-inflated, high contig count, low SCG recovery) are excluded pending decontamination, not
  silently dropped by the SCG filter.
- **A novel genus is declared, not inferred.** A strain with no same-genus comparator is a FAIL
  unless it is listed in the spec's `novel_genus_queries`, which turns it into a documented WARN
  (C2n): placed against the family, rooted on the family-level outgroup, captioned as a
  candidate novel genus. This keeps "no comparator = novel genus" from ever silently meaning
  "I forgot to stage a comparator".

## What the gate checks (phylo_preflight.py, before expensive tree analysis)

S1 spec present · E1/E1b/E1c/E2 environment + HMM presence + local `file`/version probes · G1/G2 file integrity +
byte-identical duplicates · G3/G3b assembly quality · G4 superseded assembly · H1 cohort
coherence · H2 no excluded strain staged · H3 strain-in-canonical · T1 genus resolution ·
T2 family/order coherence (scope-aware) · T3 order span · O1/O2/O3 outgroup sanity ·
C1 comparator ratio · C2/C2n per-genus comparators + novel-genus exemption · R1 registry sanity.

This is a conditional checklist, not proof that every named check ran. In current source, multiple filename-matched outgroups produce a warning and skip O2/O3; warning-only results can exit0. Read the saved per-check rows and retain pinned input/tool evidence. See [the current preflight scope and recovery contract](reference/06_CURRENT_SOURCE_SCOPE.md#phylogeny-preflight-local-probes-and-conditional-checks). Historical threshold/rooting rationales above remain unverified by this documentation change.

## Files (candidate homes in the bundle)

`tools/build_tree.sh` · `tools/phylo_preflight.py` · `tools/phylo_postflight.py` ·
`tools/gtotree_env.sh` · `tools/render_all.py` · one `TREE_SPEC.json` per tree directory.
