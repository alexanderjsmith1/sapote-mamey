# The Sapote-Mamey GToTree Workflow — execution guide (two-tier MLSA → approved core-genome)

Before any `doctor` example below, read the [write-probe boundary](INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation. If `runs/_doctor_probe` is occupied, leave it
untouched and report the hold; the diagnostic refuses an occupied probe location.

Run engine examples from the selected bundle directory containing `pyproject.toml` and `mamey_run.py`, using its compatible activated Python interpreter; bind external inputs separately.


**Source scope:** companion workflow (detected, not bundled). The pruning, roster, outgroup-scan and advisory signoff clauses below match their current source owners. The remaining installation, runtime/interface, marker, inference and historical cohort claims require their own source/run evidence; this is not a completed native workflow validation.
Historical cohort/version examples below are context, not proof of current installed assets.
**Scope:** downstream of a sealed Mamey package. It **never blocks or alters a core run.**
**Governance authority:** [`docs/phylogenomics.md`](phylogenomics.md) and, for the LLM contract,
`docs/LLM_COMPANION_TOOL_PROTOCOL.md`. This document is the **execution** companion to those; where
they govern *what is allowed and what needs approval*, this one gives the *commands that carry it out*.

> **Two-speed rule (governing).** The shipped MLSA screen has no approval flag, but executes external tools and
> consumes CPU. Use the user's authorized inputs, output root and resource budget;
> an absent flag is not unlimited execution permission.
> The **expensive 138-SCG core-genome + long IQ-TREE inference is approval-gated**: no CPU cores are
> committed until you have seen and approved the compute preflight (`plan_gtotree_iqtree.py` leaves a
> run in `PLANNED_AWAITING_APPROVAL`). Codex's panel/preflight tools are **plan-only by design** — that
> is the gate working, not a missing builder.

> **Claim-safety.** A genome tree strengthens *topology*; ANI and aligned fraction support taxonomic comparison; thresholds
> around 95–96% are interpretation aids and do not automatically delimit or name species. "Candidate novel" is a **prior**, not a rank; 16S over-lumps; AAI ≠ ANI. BGC content is
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
  →   tools/build_mlsa.py            (5-locus MLSA; authorized inputs, output and CPU budget) ]
  →   tools/prune_neighbors_from_tree.py --emit-panel-tsv   (≤60-tip bounded panel)     ]
  → tools/build_phylo_panel.py                          (Codex: membership, 1 outgroup, dedup)
  → tools/plan_gtotree_iqtree.py --prepared-panel        (Codex: immutable compute preflight)
  → ★ USER APPROVAL ★                                    (cores committed only past this point)
  → GToTree 138-SCG alignment  →  IQ-TREE inference      (this workflow: §4–§5)
  → fastANI assembly comparisons (§6)  +  tools/signoff_check.py (§7)
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
python mamey_run.py doctor --companions       # confirm detection
```

The drivers here find binaries via `--bin-dir`, then `$MAMEY_PHYLO_BIN`, then `PATH` — nothing is
hardcoded to any one machine.

### Shared GToTree interface admission

Released **1.8.19** is the current workflow priority. The unreleased v2 rewrite is
**experimental source integration**, not a released production workflow; further
native v2 work is deferred. The interface allowlist below is retained for explicit
compatibility/admission checks, not installation, study-version or release authority.

`tools/_gtotree_versions.py` owns executable-name discovery, exact version
admission, version-specific help/probe rules and alignment-only command building
for the immutable planner, approved runner and packet gate. Accepted families
remain **1.8.19** and **2.0.x**. A numeric major alone, a prerequisite's version,
a prerelease suffix, conflicting banners, or nonzero version/help exit is not
admission. Missing or drifted options produce a hold before analysis; a held
planner writes a non-executable `COMMAND.sh` refusal stub. Re-plan into a fresh
run after resolving the hold; old plans are preserved.

The documented native contracts are the upstream [v1.8.19 source](https://github.com/AstrobioMike/GToTree/blob/c4e526449d5933339d2f0d2f9318de9e82eaef12/bin/GToTree)
and [v2 rewrite parser](https://github.com/AstrobioMike/GToTree/blob/bc70746e6c01a1d44596b2adfba8e4e6717fe70d/gtotree/cli/parser.py).
The v2 branch reports 2.0.0; this pin is not a proof that a historical locally
patched 2.0 installation is identical. Its current [detailed help](https://github.com/AstrobioMike/GToTree/blob/bc70746e6c01a1d44596b2adfba8e4e6717fe70d/gtotree/cli/helpmenu.py)
is requested with `-s`, because condensed `-h` omits required optional flags.
Runtime interface probes must still pass for the selected executable.

| Profile | Version/help probes | Alignment-only resources and flags |
|---|---|---|
| 1.8.19 | `-v`, `-h`, both exit zero | `-j jobs -n threads -M threads -N`; optional `-m` mapping and `-k` retention |
| 2.0.x | `-v`, `-s`, both exit zero | `-j jobs -M threads -N`; no `-n`; optional `-m` mapping and `-k` retention |

CLI interface admission and runtime/resource admission are separate. The reviewed
v2 source hardcodes **two** threads in `search_threads_per_genome`; `-M` controls
MUSCLE and does not set HMM-search CPUs. A version banner does not bind that source
implementation to the selected executable. Without an admitted exact v2 source
profile, the planner records `HOLD_RESOURCE_PROFILE`, unknown HMM threads and zero
scheduled concurrent trees; the runner refuses `GTOTREE_RESOURCE_PROFILE` before
creating outputs or launching analysis. This is a hold pending source/resource
admission, not a claim that every v2 implementation is incompatible. The exact
reviewed profile described in [runtime admission](GTOTREE_RUNTIME_ADMISSION.md)
can admit the two-thread-per-genome search within an explicit phase-worker budget. There is no force bypass and no fabricated one-CPU receipt.

The v1.8.19 controlled mapping retains basename keys. The reviewed v2 parser
accepts the exact supplied input path or its extension-free genome ID; this
planner/runner uses exact supplied absolute paths for v2 mapping keys. Full mapped
labels, including accession-version dots, are preserved. The runner now passes its resolved exact HMM file
for both profiles, explicitly caps MUSCLE threads and skips GToTree's internal
tree on v1 as well as v2, because its separately configured IQ-TREE stage owns
inference. These are recorded command/resource migrations, not a change to the
marker filters or IQ-TREE scientific settings. 1.8.16 and future/unrecognized
families remain refused. Marker sets and resulting trees are not pooled between
major versions without a separate scientific comparison. The installed toolchain,
selected marker hashes, retained/excluded tips and completion evidence are still
required; interface admission alone is not native validation.

## 3. Tier 1 — full-pool MLSA within the authorized resource budget

```bash
# genomes_dir holds immediate *.fna; _OUTGROUP is an inert label here, not a rooting flag
python tools/build_mlsa.py  <genomes_dir>  <out_dir>  --threads 4
```

Prodigal → `blastp` the five bundled seed proteins (atpD, gyrB, recA, rpoB, trpB; `mamey/data/phylo_seeds/*.faa`) against each proteome → highest-bitscore returned subject's **CDS** → MUSCLE → trim >50%-gap columns → available-locus **partitioned** supermatrix → IQ-TREE (`-m MFP`, DNA models, 1000 UFBoot + 1000 SH-aLRT, seed 12345). Best-hit selection does not establish orthology. Outputs include `<out>/tree.treefile`, `<out>/loci_report.tsv`, `<out>/taxon_map.tsv`, `<out>/run_status.json`, `<out>/mlsa.log` and alignment/partition files. Reconcile per-locus HIT/NO_HIT rows and retained tips/partitions: successful output can omit a locus or a genome without any retained locus. See [MLSA completion and recovery](COMPANION_RUN_CONTRACTS.md#mlsa-inputs-completion-and-recovery) for source bindings, output reuse, thread forwarding and the nonempty-tree-only completion check.

- **This is the 5 protein-coding loci only.** The project's **6th locus, 16S rRNA, is built
  separately** (rRNA cannot be blastp-seeded; extract with e.g. `barrnap`) and kept as its own
  analysis — never disguised as a GToTree protein HMM (see `phylogenomics.md`).
- **Nucleotide loci — pass no protein `-mset`.** ModelFinder must pick DNA models; `LG/WAG/JTT` here
  throws `File not found LG`. (The driver already omits it.)
- Fast even at ~293 tips. A five-locus screen can precede the expensive core-genome preflight;
  record actual input counts, runtime and threads. Execute only within the existing
  user authorization rather than treating this as unrestricted fan-out.

## 4. Prune → bounded panel (the bridge into Codex's chain)

```bash
python tools/prune_neighbors_from_tree.py  <out_dir>/tree.treefile  --k 3  --max-tips 60 \
    --genomes-dir <genomes_dir>  --emit-panel-tsv panel_candidates.tsv
```

The pruner classifies query tips by its prefix regex (`AS-`/`AS_`, `AJS-`/`AJS_`, or `SID` followed by digits), and outgroups by an `OUTGROUP` substring; reconcile these inferred roles with the approved roster. Other query naming schemes can be treated as references. It selects up to **k nearest reference tips by patristic distance per recognized query**; equal distances retain tree-tip order. It emits `candidate_id, role, source_path, selection_basis, related_query_ids`, with `nearest_neighbour_patristic_MLSA` for reference rows (`tools/prune_neighbors_from_tree.py`).

The CLI clamps a requested cap above 60, then trims references by descending minimum distance to any query. Queries and all inferred outgroups remain: if those fixed tips alone exceed the cap, the function can still emit an oversized panel. Missing or multiple outgroups do not enforce exactly-one admission here. Source paths can be constructed for absent genomes, and optional staging can warn and finish with fewer copied files. Inspect the roster, actual paths, counts and logs; the governed panel builder and compute gate remain separate. Then submit the selected panel for current review:

```bash
python tools/build_phylo_panel.py panel_candidates.tsv staged_panel/ --panel-size <N>
python tools/plan_gtotree_iqtree.py plan --prepared-panel staged_panel/ \
    --workspace /path/to/writable/phylo_workspace \
    --run-id gtotree_candidate_001 --hmm /path/to/Actinobacteria.hmm \
    --threads-per-tree 1 --max-concurrent-cores 4   # preflight only
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

Tree tips are numbered in parsed leaf order; panel rows are numbered in file order. Numbering is relative to that exact input, not a durable identity or guaranteed later figure order. Explicit panel roles are used when present; tree role inference recognizes AS/AJS prefixes but not the pruner’s SID prefix. Query removal and out-of-range indices produce warnings, not refusal. Duplicate labels are not rejected; panel output filters by retained label, so a duplicate can preserve a row selected for removal (`tools/phylo_roster.py`). Reconcile unique identities and roles first, retain the source roster/hash, use a fresh output and inspect the saved rows. The tool directly overwrites a supplied output path and is not an atomic or source-protecting editor. Re-print after each edit.

**Test the root (3× per family).** Because MLSA is cheap, build the same ingroup rooted on several
candidate outgroups and check whether the ingroup topology is stable:

```bash
python tools/mlsa_outgroup_scan.py --build --ingroup-dir genomes_ingroup/ \
    --outgroup outA.fna --outgroup outB.fna --outgroup outC.fna --workdir scan/
# or compare trees you already built:
python tools/mlsa_outgroup_scan.py --trees scan/mlsa_outA/tree.treefile scan/mlsa_outB/tree.treefile ...
```

It reports the symmetric difference of nontrivial bipartitions on shared tips after removing names containing `OUTGROUP`. RF=0 means no difference among those retained splits; it does not test rooting, all original tips, branch lengths, support, orthology or biological panel adequacy (`tools/mlsa_outgroup_scan.py`). Record shared-tip counts, complete retained/excluded rosters and split denominators. The implementation does not enforce a minimum informative common roster; zero splits, unresolved trees or incomplete overlap cannot establish root robustness. A nonzero RF identifies a difference on the compared scope, not its biological cause.

Build mode copies every immediate ingroup `.fna` for each outgroup into reusable work directories, runs MLSA serially and retains only zero-exit builds with an existing tree. Failures are logged while remaining comparisons can continue; the wrapper returns zero even when fewer than two trees remain. Repeated outgroup basenames or prebuilt parent-directory labels can overwrite dictionary entries. Use a fresh work root, estimate the aggregate copies before launch, unique labels and a declared expected build/roster count. Do not infer complete comparative success from the printed STABLE verdict or exit status. These are still external compute jobs within the authorized resource scope.

## 5. Tier 2 — approved core-genome backbone (cores committed here)

Only after you approve the preflight:

```bash
# GToTree 1.8 interface; reconcile flags for v2 before execution.
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

## 6. Compare assemblies with ANI

```bash
fastANI --query AS-XXX.fna --refList comparators.txt -o AS-XXX.ani.tsv
```

Record the exact query/reference assembly identities, raw identity, matched-fragment
count and total query fragments. Preserve the comparison direction and calculated
aligned fraction. A missing row is not zero identity: it may be outside the method's
reporting range or reflect an execution/input problem. Compare to selected, verified
reference material and describe the sampled panel.

ANI thresholds alone do not make species or genus calls. High ANI supports close
assembly similarity within the compared panel; low ANI to one named reference does
not establish novelty, and ANI is not a universal genus delimiter. Report uncertainty
and investigate assembly quality, duplicates and reference provenance before adoption.

## 7. Sign-off gate — run on every tree

```bash
python tools/signoff_check.py  <tree.treefile>          # advisory, always exits 0
```

The advisory checker uses label/text heuristics, not sequence, taxonomy or accession reconciliation. It requires some recognized outgroup; multiple automatic OUTGROUP-tagged names are flagged, while explicitly designated multi-tip outgroups are supported. An exact-one biological outgroup is not proved. Genus comparison uses label prefixes; rogue-taxon/MAG/cruft checks use finite regexes. Duplicate/bare labels, repeated numeric assembly-accession cores and digit-bearing internal labels are screened, not verified as true duplicate genomes or valid support values (`tools/signoff_check.py`). Missing branch-length syntax can escape its tip regex.

Use repeated `--outgroup` values consistently with the selected hard tree gate when naming untagged outgroups. With no file argument the tool scans recent `.treefile` files only, excluding configured directory names; that is not an exhaustive tree inventory. No recent tree, an inspection error, detected issues and a clean advisory check can all return zero. Preserve output, actual file roster and unresolved checks. Outgroup choice, comparator provenance, host traceability, ANI interpretation and assembly caveats remain independent judgment items.

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
- **Use the admitted version-specific GToTree thread controls** (`-n -M -j` for 1.8.19; v2 omits `-n` and needs its separately admitted phase-worker profile). A shared flag list or version/help pass alone does not establish the requested CPU bound.
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
*Quote the exact installed versions (`python mamey_run.py doctor --companions`); the Tool Master supplies
version-matched strings.*
# Frozen execution identity

Production GToTree packets must pass `tools/gtotree_execution_gate.py` before launch.
The packet binds the GToTree version (one of the accepted versions below), the exact executable SHA-256, the HMM file SHA-256,
every genome SHA-256, one unique working directory and output directory per panel,
and a maximum of four concurrent jobs. Each process runs from its own panel directory;
shared working directories are prohibited. Postflight repeats the gate and refuses
silent loss of any approved tip before downstream inference. GToTree v2 requires a
separate controlled migration because its marker set is not assumed comparable with
the established 138-marker Actinobacteria workflow.

**Accepted GToTree versions** — one list, in `tools/_gtotree_versions.py`, read by both the planner
(`tools/plan_gtotree_iqtree.py`) and the gate (`tools/gtotree_execution_gate.py`):

| Version | Status |
|---|---|
| 1.8.19 | released-version priority for the 138-marker workflow; selected installation and run still require admission |
| 2.0.x | experimental unreleased-source interface support; native work deferred; its trees are not pooled with 1.8.19 trees without the migration above |
| 1.8.16 and anything else | refused (1.8.16 also has the interactive-prompt hang fixed in 1.8.19) |

The planner and runner share the version-specific argv policy: `-n` is emitted
only for 1.8.19; v2 uses `-M` for MUSCLE and omits `-n`. Successful version/help
probes alone do not authorize v2 analysis. The governed v2 route additionally
requires its exact reviewed runtime proof, recorded plan approval, and an explicit
execution approval. See [runtime admission](GTOTREE_RUNTIME_ADMISSION.md) and
[companion run contracts](COMPANION_RUN_CONTRACTS.md).

`--threads-per-tree N` (1–4, default 1) controls MUSCLE and IQ-TREE. V1 schedules
`--max-concurrent-cores` ÷ N trees. Governed v2 uses the admitted phase-worker
estimate `max(2 * jobs, jobs * MUSCLE threads)` instead; its scheduled concurrency
is the caller's at-most-four budget divided by that estimate. IQ-TREE's threads
must also fit the caller budget and observed available CPUs. These are requested
worker bounds, not total OS-thread or CPU-use guarantees.

For the optional Barrnap route, see [version and integration scope](BARRNAP.md). The marker planner prints a recipe; the separate comparator selector has a BLASTn route that does not require Barrnap. Neither a printed plan nor an absent tool is evidence that marker extraction ran.
