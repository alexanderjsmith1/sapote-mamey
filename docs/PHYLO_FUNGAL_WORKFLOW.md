# Fungal phylogenetics workflow (Sapote-Mamey)

The bacterial workflows (`PHYLOGENETICS_WORKFLOW.md`, `PHYLO_PLACEMENT_WORKFLOW.md`, `GTOTREE_WORKFLOW.md`)
do NOT apply to fungi: different loci, different alphabet, different reference world, and
`outgroup_registry.tsv` is actinomycete-only. This is the fungal sibling — for any fungal isolate that
turns up as a comparator (e.g. a Chaetothyriales black yeast from an insect host). Generic; carries no
project specifics.

## Two tiers (same philosophy as the bacterial two-tier)
1. **rDNA screen (fast, low CPU)** — find the isolate's family/genus neighbourhood.
   - **ITS** (ITS1-5.8S-ITS2, the fungal barcode) via **ITSx**; **18S/SSU** and **28S/LSU** via **barrnap
     `--kingdom euk`**; or `blastn` the assembly with a reference operon when a tool is unavailable.
   - Align per locus (MUSCLE), trim (trimAl), IQ-TREE, root on the registry outgroup, gate.
   - **Marker caveat (enforced):** 18S is conserved (family/genus neighbourhood only); ITS resolves
     WITHIN a genus but is UNALIGNABLE across divergent genera — never concatenate family-wide ITS.
     A **matched whole-operon (18S+ITS+28S) matrix** from full-operon records is the strongest rDNA tree.
2. **Genome MLSA (definitive, CPU-heavy) = the fungal GToTree equivalent** — **BUSCO** single-copy
   orthologs (lineage `ascomycota_odb10`/`dothideomycetes_odb10`) on the query + reference genomes
   (fetched with NCBI `datasets`), concatenate hundreds of loci → partitioned IQ-TREE → gate. Use when
   rDNA markers disagree on genus (the usual case for a divergent/novel lineage). **compleasm** is a
   faster drop-in for BUSCO; on macOS-arm64 BUSCO's deps often fail — run in the Linux container.

## Rooting rule (same as bacterial: prevents the #1 defect)
Outgroup from `mamey/data/fungal_outgroup_registry.tsv` by `(taxon, scope)`, never ad hoc. A family tree
roots on a sister-family genus one rank out; never a distant taxon; never an ingroup member.

## Gates (identical to bacterial)
`tools/tree_sanity_check.py` MUST PASS (outgroup-aware) then `tools/signoff_check.py`, BEFORE any render.
A genuinely divergent/novel query can itself be the longest branch — that is a *finding*, reported with a
proper outgroup, not hidden; but it must not dominate an artifactual alignment.

## Claim-safety
ITS/rDNA = family/genus neighbourhood, NOT a species call; genome MLSA (+ ANI/AAI) delimits species;
judgment deferred. State the nearest named genus with % identity as an anchor, never as an identification.

## Hard-won rules (v9.7.406) — each of these cost a real detour

These were learned by making the mistake, not by reasoning ahead. Follow them.

### R1. Take the outgroup from the registry row, never from whichever comparator finished first
`mamey/data/fungal_outgroup_registry.tsv` names a **primary and an alternate** per scope precisely
so there is a documented fallback. Picking a different genus because its genome was ready is not
covered by "same family, close enough" — the row's author already reasoned about fallbacks and
chose these. If a registry outgroup genuinely is not available, say so in the caption as a stated
limitation rather than silently substituting.

### R2. Cross-check a new tree against any EXISTING marker tree for the same organism, before presenting
A genome tree that contradicts an rDNA tree you already built is a finding that needs stating, not
a result to publish over. State both, weigh them by evidence strength (alignment columns and locus
conservation, not bootstrap alone — a short conserved locus can show 98/98 on very few informative
sites), and say plainly that neither settles the question if neither does.

### R3. One genome per genus for a placement tree; congeners are optional breadth
A genus-placement question needs one representative per genus. Queuing five congeners multiplies
runtime without changing the answer. Add breadth later, deliberately, if a reviewer asks for it.

### R4. A high-quality assembly of a taxonomically incoherent genus is still a bad comparator
Check the *name* as well as the assembly stats. A **form-genus** (NCBI brackets these, e.g.
`[Coniosporium]`) is polyphyletic by definition, so its "genus" tells you nothing about where the
genome will sit. One such comparator, despite 99.58% completeness, produced a branch 79% of tree
depth and failed the gate. The registry now carries BANNED rows for these.

### R5. A gate FAIL can be the finding — report the numbers, withhold the figure
A genuinely divergent query trips `DOMINATING_BRANCH` because it *is* divergent. Do not loosen the
gate, do not prune the query, and do not present the figure as clean. Report the branch length and
its fraction of tree depth, say which check failed and why, and let the number carry the claim.

### R6. Never resume a partial ortholog run
compleasm writes `miniprot.done` before hmmsearch completes; resuming after an interrupt yields a
silently truncated ortholog set. Delete the output directory and restart that genome.
