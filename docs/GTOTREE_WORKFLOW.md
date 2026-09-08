# The Sapote-Mamey GToTree Workflow — execution guide (two-tier MLSA → approved core-genome)

**Version:** rebased onto v9.7.348 for the v9.7.349 line · companion workflow (detected, not bundled)
**Scope:** downstream of a sealed Mamey package. It **never blocks or alters a core run.**
**Governance authority:** [`docs/phylogenomics.md`](phylogenomics.md) and, for the LLM contract,
`docs/LLM_COMPANION_TOOL_PROTOCOL.md`. This document is the **execution** companion to those; where
they govern *what is allowed and what needs approval*, this one gives the *commands that carry it out*.

> **Two-speed rule (governing).** **MLSA trees are cheap — build as many as you like, un-gated.**
> The **expensive 138-SCG core-genome + long IQ-TREE inference is approval-gated**: no CPU cores are
> committed until you have seen and approved the compute preflight (`plan_gtotree_iqtree.py` leaves a
> run in `PLANNED_AWAITING_APPROVAL`). Codex's panel/preflight tools are **plan-only by design** — that
> is the gate working, not a missing builder.

> **Claim-safety.** A genome tree strengthens *topology*; **whole-genome ANI delimits species**
> (~95–96%). "Candidate novel" is a **prior**, not a rank; 16S over-lumps; AAI ≠ ANI. BGC content is
> an **annotation track**, never a character used to infer the organismal tree. Class-level
> hypotheses, judgment deferred; no bioactivity/structure claims.

---

## 1. Where this sits in the canonical chain

This workflow provides the **cheap wide-net screen** and the **post-approval executor** that bracket
Codex's bounded-panel governance. One direction of data flow (see `phylogenomics.md` §"Canonical
preparation chain"):

```
raw antiSMASH ClusterBlast channel
  → tools/rank_clusterblast_phylo_candidates.py         (Codex: candidate evidence only)
  → tools/marker_candidate_search.py                    (this workflow: 16S/rpoB/gyrB marker BLAST
                                                         → candidate panel TSV; discovery+downloads
                                                         are network/approval-gated, plan-only)
  → [ OPTIONAL cheap screen, this workflow:                                            ]
  →   tools/build_mlsa.py            (5-locus full-pool MLSA — cheap, un-gated, MANY ok) ]
  →   tools/prune_neighbors_from_tree.py --emit-panel-tsv   (≤60-tip bounded panel)     ]
  → tools/build_phylo_panel.py                          (Codex: membership, 1 outgroup, dedup)
  → tools/plan_gtotree_iqtree.py --prepared-panel        (Codex: immutable compute preflight)
  → ★ USER APPROVAL ★                                    (cores committed only past this point)
  → GToTree 138-SCG alignment  →  IQ-TREE inference      (this workflow: §4–§5)
  → fastANI species calls (§6)  +  tools/signoff_check.py (§7)
  → tree × BGC overlay figure (§8, docs/TREE_BGC_OVERLAY.md)
```

The two-tier screen is **not a competing panel planner** — its only output is a bounded panel TSV
that feeds `build_phylo_panel.py`, so the ≤60-tip cap and the approval gate still apply to whatever
becomes a heavy tree.

## 2. Install the companions (once)

```bash
conda create -n sapote-phylo -c conda-forge -c bioconda \
    gtotree iqtree muscle prodigal blast fastani ncbi-datasets-cli -y
conda activate sapote-phylo
GToTree -v && GToTree -h        # never assume 1.8.16 behaviour — check the installed interface
mamey doctor --companions       # confirm detection
```

The drivers here find binaries via `--bin-dir`, then `$MAMEY_PHYLO_BIN`, then `PATH` — nothing is
hardcoded to any one machine.

## 3. Tier 1 — full-pool MLSA (cheap, un-gated, build many)

```bash
# genomes_dir holds *.fna; exactly one may carry an _OUTGROUP suffix in its filename
python tools/build_mlsa.py  <genomes_dir>  <out_dir>  --threads 4
```

Prodigal → `blastp` the five bundled seed proteins (atpD, gyrB, recA, rpoB, trpB;
`mamey/data/phylo_seeds/*.faa`) against each proteome → best-bitscore ortholog's **CDS** → MUSCLE →
trim >50%-gap columns → **partitioned** supermatrix → IQ-TREE (`-m MFP`, DNA models, 1000 UFBoot +
1000 SH-aLRT, seed 12345). Outputs `<out>/tree.treefile`, `<out>/loci_report.tsv` (per-taxon seed
%id — your data-quality read), `<out>/mlsa.log`.

- **This is the 5 protein-coding loci only.** The project's **6th locus, 16S rRNA, is built
  separately** (rRNA cannot be blastp-seeded; extract with e.g. `barrnap`) and kept as its own
  analysis — never disguised as a GToTree protein HMM (see `phylogenomics.md`).
- **Nucleotide loci — pass no protein `-mset`.** ModelFinder must pick DNA models; `LG/WAG/JTT` here
  throws `File not found LG`. (The driver already omits it.)
- Fast even at ~293 tips. Run one per family, run them for sub-panels, run them freely — MLSA does not
  need the compute-approval preflight.

## 4. Prune → bounded panel (the bridge into Codex's chain)

```bash
python tools/prune_neighbors_from_tree.py  <out_dir>/tree.treefile  --k 3  --max-tips 60 \
    --genomes-dir <genomes_dir>  --emit-panel-tsv panel_candidates.tsv
```

For every query tip (`AS-####`/`AJS-####`) it keeps the **k nearest reference tips by patristic
distance**, plus the outgroup, and writes `panel_candidates.tsv` in exactly the columns
`build_phylo_panel.py` consumes (`candidate_id, role, source_path, selection_basis,
related_query_ids`; references carry `selection_basis=nearest_neighbour_patristic_MLSA`). Queries and
the outgroup are never dropped; if the set would exceed `--max-tips` (hard ceiling 60), the
**farthest** references are trimmed first and reported. Then hand it to Codex:

```bash
python tools/build_phylo_panel.py panel_candidates.tsv staged_panel/ --panel-size <N>
python tools/plan_gtotree_iqtree.py plan --prepared-panel staged_panel/ ...   # preflight only
#   → review the preflight, then APPROVE before anything below runs
```

## 4.5 Hand-curation loop (numbered roster + remove-by-number) and outgroup testing

MLSA is cheap, so the intended way to work is **iteratively and by hand**: build many small MLSA
trees, curate members by eye, and test the root. Two tools make that fast.

**Panel composition.** Each AS/AJS query wants ~**3 related strains** (`prune --k 3`) **plus other
relevant genus-/family-mates isolated from the same niche** (e.g. other bee-derived strains). Hand-add
those to the panel TSV; they are `REFERENCE` rows with a curator `selection_basis`.

**Numbered roster + edit by number.** Every tree or panel prints as a stable, 1-based list so you can
say *"remove 30, 31, 36"* and the exact strains drop — no guessing:

```bash
python tools/phylo_roster.py --tree fam.treefile [--strain-table hosts.csv]   # print numbered list
python tools/phylo_roster.py --panel panel.tsv --remove "30,31,36" --out panel_v2.tsv   # edit it
```

Tips are numbered in tree-leaf order (the figure stacking order); removing a QUERY (an AS strain) is
allowed but flagged loudly. Re-print after each edit so the numbers always match what you see.

**Test the root (3× per family).** Because MLSA is cheap, build the same ingroup rooted on several
candidate outgroups and check whether the ingroup topology is stable:

```bash
python tools/mlsa_outgroup_scan.py --build --ingroup-dir genomes_ingroup/ \
    --outgroup outA.fna --outgroup outB.fna --outgroup outC.fna --workdir scan/
# or compare trees you already built:
python tools/mlsa_outgroup_scan.py --trees scan/mlsa_outA/tree.treefile scan/mlsa_outB/tree.treefile ...
```

It reports the Robinson-Foulds distance between ingroup topologies (RF=0 = identical, root-robust). A
non-zero RF means the deep splits move with outgroup choice — report them cautiously (a sign-off item).
This never builds a heavy core-genome tree; it only orchestrates cheap MLSA runs.

## 5. Tier 2 — approved core-genome backbone (cores committed here)

Only after you approve the preflight:

```bash
GToTree -f genomes.txt -H Actinobacteria -m labels.tsv -j 1 -n 1 -M 1 -N -k -o run/gtotree_align
#   -H Actinobacteria : the 138-SCG set. Make -n/-M/-j explicit — GToTree defaults can exceed the
#                       project core ceiling. Use -B only after documenting the multicopy tradeoff
#                       (it can mask contamination/paralogy); report with and without it if it changes
#                       taxon retention. Discover the emitted alignment; do not assume Aligned_SCGs.faa.

iqtree3 -s <discovered-alignment> -m MFP -mset LG,WAG,JTT,Q.pfam -mrate G,I,I+G \
        -B 1000 -alrt 1000 -T 1 -seed 12345 --prefix run/iqtree/final
#   protein supermatrix -> RESTRICT ModelFinder (bare -m MFP never finishes on ~30k cols).
#   One core-committed tree per approval; a dispatcher must prove the combined ceiling ≤ 4 cores.
```

## 6. Delimit species with ANI

```bash
fastANI --query AS-XXX.fna --refList comparators.txt -o AS-XXX.ani.tsv
```

The tree shows relationships; **fastANI makes the species call** — reported to the nearest *named*
species, not a sibling query. Calls within ~1% of 95% are boundary/indeterminate; say so.

| Level | ANI to closest | Worked example |
|---|---|---|
| known species | ~98–99% | AS-XXX = *S. antibioticus* |
| candidate novel **species** | ~85–90% | AS-XXX vs *Peterkaempfera bronchialis* (~87%) |
| candidate novel **genus** | ≤ ~78% | AS-XXX (sister *Labedaea*, outside the *Pseudonocardia* crown) |

## 7. Sign-off gate — run on every tree

```bash
python tools/signoff_check.py  <tree.treefile>          # advisory, always exits 0
```

Objective checks: exactly one outgroup present, and not an ingroup genus mislabelled as one; no
non-Actinomycetota **rogue** tip; no **MAG/unclassified-bin** tip; no contig **cruft**/duplicate/bare
labels; no same-assembly **GCA+GCF twin**; internal-node **support** present; **thin** trees (n<12)
flagged. Judgment items (outgroup *choice*, comparator provenance, host traceability, ANI-boundary
honesty, draft-assembly caveats, claim-safety) are printed as reminders.

## 8. Overlay the tree with Sapote-Mamey BGC figures

The point of placing strains phylogenetically is to read BGC patterns **at their tree position**. That
overlay has its own formal workflow — see **[`docs/TREE_BGC_OVERLAY.md`](TREE_BGC_OVERLAY.md)** — which
joins a treefile (tip order + topology) to sealed-package BGC inventories through an **explicit
tip↔strain crosswalk**, and renders the tree beside an aligned BGC class/domain matrix. The BGC panel
is an **annotation track**: row position implies shared ancestry only, never chemistry; the smaller
138-SCG topology is overlaid on the broad MLSA context only when the common-tip mapping is explicit.

## 9. Gotchas (learned the hard way)

- **Record per-genome SCG completeness/redundancy and caption fragmented tips.** GToTree reports SCG
  completion and redundancy per input for free (in `Genomes_summary_info.tsv`). Carry those numbers
  into the QA and the figure caption: a fragmented tip with, say, 62% SCG completeness should say so.
  It is the honest, per-tip fragmentation flag — its position may hold while its branch length does not.
- **Make GToTree thread controls explicit** (`-n -M -j`) — defaults can exceed the core ceiling.
- **Restrict ModelFinder** on the protein core-genome matrix; pass **no** protein `-mset` on the
  nucleotide MLSA matrix.
- **Spaces in paths break GToTree's HMM handling.** Work in a space-free dir; a symlinked
  `dir/../Tools` resolves to the *link's* parent — use absolute paths for sibling tools.
- **Chimeric/contaminated assemblies** (bimodal GC, size-inflated, 16S disagrees with bulk) are
  excluded until re-assembled — core genes and BGC counts are a mix. *Worked:* AS-XXX was ~40%
  *Paenibacillus* (clean GC gap 56–60), decontaminated by a GC≥58 cut; AS-XXX and AS-XXX
  (Nocardia+Micromonospora chimera, long branch) are **void**.
- **Long-branch check** — a truncated/read-through ORF in a fragmented reference can throw an
  artefactual long branch; drop it and re-run to confirm a placement is intrinsic.
- Use `SUSPECT/REQUEST`, not "contaminated", until you have assembly-level evidence (ANI + aligned
  fraction + locus identity), and never merge records on 100% 16S alone.

## 10. Citations (version-matched)

GToTree — Lee (2019) *Bioinformatics* 35:4162, doi:10.1093/bioinformatics/btz188 · IQ-TREE 2 — Minh
et al. (2020) *MBE* 37:1530 · ModelFinder — Kalyaanamoorthy et al. (2017) *Nat Methods* 14:587 ·
UFBoot2 — Hoang et al. (2018) *MBE* 35:518 · MUSCLE 5 — Edgar (2022) *Nat Commun* 13:6968 · Prodigal —
Hyatt et al. (2010) *BMC Bioinf* 11:119 · BLAST+ — Camacho et al. (2009) *BMC Bioinf* 10:421 · fastANI
— Jain et al. (2018) *Nat Commun* 9:5114 · ncbi-datasets-cli — NCBI Datasets docs + access date.
*Quote the exact installed versions (`mamey doctor --companions`); the Tool Master supplies
version-matched strings.*
