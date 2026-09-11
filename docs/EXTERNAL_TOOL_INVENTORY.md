# External tool & database inventory

**Bundle v9.7.428 · engine Mamey 1.9.163 · compiled 2026-09-11**

The external bioinformatics tools and reference databases the Sapote-Mamey workflow
depends on, with the version of record, the run-defining parameters, and a
version-matched citation for each. This is the reproducibility spine of the Methods.
For the *internal* helper scripts shipped in `tools/`, see
`docs/TOOLS_INVENTORY.generated.md` — a different document.

**Claim-safety:** this inventory documents *methods*, not results. It asserts nothing
about product structure or bioactivity. Similarity tools (BLAST / KnownClusterBlast /
BiG-SCAPE) measure *similarity, not identity*.

**Provenance model:** this inventory contains historical environment snapshots, not
a guarantee about the binaries installed on the reader's machine. Record the executable
path, successful version probe, database identity, and run arguments for each analysis.
For historical results, use the original run receipt; a current installation does not
establish which version produced an older result.

---

## Pipeline stages → tool → version

| # | Stage | Tool | Version (verified) | Run-defining parameters | Citation |
|---|---|---|---|---|---|
| 1 | Assembly | **SPAdes** (via Galaxy / usegalaxy.org) | 4.2.0 (confirmed for AS-XXX; confirm per strain from its Galaxy history) | `--isolate --cov-cutoff off`, error-correction off, k=21,33,55,77 | Prjibelski 2020, *Curr Protoc Bioinformatics* 70:e102; Galaxy Community 2024, *NAR* 52(W1):W83–W94, 10.1093/nar/gkae410 |
| 2 | BGC detection | **antiSMASH** | 8.0.4 (core cohort) | `--taxon bacteria`, detection strictness = **loose**; KnownClusterBlast + ClusterBlast + Pfam-domain + RRE-finder enabled (schema 4) | Blin 2023 (antiSMASH 7), plus the antiSMASH 8 paper of record — cite the version actually run |
| 3 | Extraction + triage | **Sapote-Mamey (Mamey)** | engine 1.9.142 / bundle 9.7.400 (verified: the sealed 45-package AS estate, uniform by filename stamp; per-package stamp is authoritative) | `run --mode gold` | historical package snapshot; inspect the actual package manifest |
| 4a | Homology — curated, local | **BLAST+ `blastp`** vs Swiss-Prot | record successful `blastp -version` / `blastn -version` for the run | default protein search | Camacho 2009, *BMC Bioinformatics* 10:421 |
| 4b | Homology — comprehensive, remote | **NCBI BLAST (web)** vs **nr** | web service (nr is rolling/unversioned) | record per-run access date | Sayers 2024 (NCBI resources) |
| 4c | Homology — curated, remote | **EBI Job Dispatcher** vs **UniProtKB** | remote service (UniProtKB release not locally stamped — record access date) | default | Madeira 2024, *NAR* 52(W1):W521–W525, 10.1093/nar/gkae241 |
| 5 | GCF families / network | **BiG-SCAPE 2** (bundled **pyhmmer**, **Pfam-A**) on **MIBiG** | BiG-SCAPE 2.0.3 · pyhmmer **0.12.1** · Pfam **38.2** · MIBiG **4.0** | GCF clustering anchored on MIBiG | BiG-SCAPE 2 (Navarro-Muñoz 2020 lineage); pyhmmer — Larralde & Zeller 2023, *Bioinformatics* 39(5):btad214, 10.1093/bioinformatics/btad214; Pfam — Paysan-Lafosse 2025, *NAR* (gkae997) |
| 6 | Cluster figures | **clinker**; **matplotlib**; **NumPy** | clinker 0.0.32 | default alignment | clinker — Gilchrist 2021; matplotlib — Hunter 2007; NumPy — Harris 2020 |
| 7 | Taxonomy / phylogenomics | **Prodigal, BLAST+, MUSCLE, trimAl, IQ-TREE 3, fastANI, GToTree, NCBI datasets** | Prodigal 2.6.3 · MUSCLE major version must match the driver and run receipt · trimAl 1.5.rev1 · IQ-TREE 3.1.2 · fastANI 1.34 · GToTree >=1.8.19 convention; record actual version · datasets 18.33.1 | 6-locus MLSA (MUSCLE) + 138-SCG core-genome ML backbone (GToTree) | per-tool papers of record (see phylogenomics methods) |
| 7b | Phylogenetic **placement** (query→fixed reference tree) | **MAFFT, RAxML-NG, EPA-ng, gappa** — *conda env, NOT bundled; `tools/` ships only the driver `phylo_place.py`* | MAFFT 7.526 · RAxML-NG 2.0.2 · EPA-ng 0.3.8 · gappa 0.9.0 (probed from the installed env — see *Version provenance* below) | `molecule=nucleotide`, `model=GTR+G`; reference tree built then held **FIXED**; queries placed, they do not re-infer the topology | EPA-ng — Barbera 2019, *Syst Biol* 68:365; gappa — Czech 2020, *Bioinformatics* 36:3263; RAxML-NG — Kozlov 2019, *Bioinformatics* 35:4453; MAFFT — Katoh & Standley 2013, *Mol Biol Evol* 30:772 |
| 7c | Reference-set construction / quick trees | **FastTree**, **BLAST+ `blastn`**, **BLAST+ `makeblastdb`** | per installed env (BLAST+ record successful `blastp -version` / `blastn -version` for the run) | local reference DB build + nucleotide search; FastTree for fast draft topologies | FastTree — Price 2010, *PLoS ONE* 5:e9490; BLAST+ — Camacho 2009, *BMC Bioinformatics* 10:421 |
| 7d | Optional sequence-file inspection | **SeqKit** (external, not bundled) | record the resolved executable and successful version output when used | record the exact inspection/extraction command; this optional tool is not silently required by every workflow | retain the installed tool's citation with the run |
| 7e | Rectangular tree figures | **R**, **ggtree**, **treeio**, **ape**, **aplot**, **ggplot2** | retain the renderer's `.session.txt` output for the exact R and package versions | `tools/ggtree_rect_heatmap.R`; rectangular phylogram, optional titled metadata strips, exact tree/metadata joins | retain R and package citation output for the versions used |
| 8 | Reference databases | see database table below | — | — | — |
| 9 | Interpretive judgment | Sapote (Tier 2/3, LLM protocol) | Markdown protocol, not code | — | — |

## Tool licenses (transparency — invoked-only, no copyleft reach)

Several of these external tools are copyleft. Because the bundle **invokes them as separate
programs** (conda/bioconda installs; no source vendored, no linking), their licenses do **not**
attach to the MIT-licensed bundle — standard "mere aggregation," no conflict. Listed here for
transparency; each project's own license file governs the version you install. The canonical copy
of this table lives in `docs/THIRD_PARTY_LICENSES.md`.

| Tool | Upstream license (for reference) |
|---|---|
| BiG-SCAPE 2 | AGPL-3.0 |
| DIAMOND | GPL-3.0 |
| GToTree | GPL-3.0 |
| Prodigal | GPL-3.0 |
| trimAl | GPL-3.0 |
| IQ-TREE | GPL-2.0 |
| FastTree | GPL-2.0 |
| HMMER | BSD-3-Clause |
| MUSCLE | GPL-3.0 (v5; verify per installed version) |
| BLAST+ | public domain (US Government work) |
| fastANI | Apache-2.0 |

## Installing the external binaries (they are **not** in the bundle)

The bundle ships Python **drivers**, not the scientific binaries. A fresh clone therefore has
`tools/phylo_place.py`, `tools/placement_figure.py`, `tools/placement_to_docx.py` and friends, but
still needs the binaries those drivers call. They are installed as conda environments:

```bash
# placement stack (row 7b)
conda create -n placement -c bioconda -c conda-forge mafft raxml-ng epa-ng gappa
# phylogenomics stack (row 7, 7c)
conda create -n phylo     -c bioconda -c conda-forge prodigal muscle trimal iqtree fastani gtotree fasttree blast
```

**Where the drivers look for them.** Three environment variables are honoured; all default to a
conda env under the workspace root:

| Variable | Default | Read by |
|---|---|---|
| `PLACEMENT_BIN` | `<root>/miniconda3/envs/placement/bin` | `tools/phylo_place.py`, `tools/figure_methods.py` |
| `PHYLO_BIN` | `<root>/miniconda3/envs/phylo/bin` | `tools/phylo_place.py`, `tools/figure_methods.py`, `tools/mibig_neighborhoods.py` |
| `MAMEY_PHYLO_BIN` | *(unset)* | `tools/build_mlsa.py` — **historical alias for the same directory as `PHYLO_BIN`**; `build_mlsa.py` now falls back to `PHYLO_BIN` when it is unset, so setting either works |

`tools/build_mlsa.py` also accepts `--bin-dir`, and every driver falls back to `PATH`.

Cross-references: `docs/PREREQUISITES.md` (Python-side dependencies and offline wheels) ·
`docs/PHYLO_PLACEMENT_WORKFLOW.md` (the placement run recipe) · `docs/GTOTREE_WORKFLOW.md`
(phylogenomics env).

## Version provenance for rows 7b/7c

These versions are **probed from the installed environment at figure-generation time** by
`tools/figure_methods.py` (it walks `PLACEMENT_BIN` then `PHYLO_BIN` and records what it finds), and
the same values are written into each figure's caption. The values tabulated above are therefore a
snapshot of one environment, consistent with this document's provenance model — for a specific past
run, read that run's own caption/receipt rather than this table.

## Reference databases

| Database | Release / build (verified) | Receipt | Citation |
|---|---|---|---|
| **Pfam-A** | **38.2** (30,134 families) | family count `grep -c "^ACC   PF" Pfam-A.hmm` → 30134 (matches 38.2 relnotes; the `.hmm` carries no literal version line — count-inferred) | Paysan-Lafosse 2025, *NAR* (gkae997) |
| **MIBiG** | **4.0** | antiSMASH KnownClusterBlast reference set | Terlouw 2023 (MIBiG 3) → cite the 4.0 record |
| **UniProtKB / Swiss-Prot** (local BLAST DB) | **NCBI `swissprot` build Jul 14 2026** — 487,492 sequences / 185,956,103 residues, BLASTDB v5 | `blastdbcmd -db swissprot -info` → `Date: Jul 14, 2026`; `swissprot.pin` header confirms | UniProt Consortium 2025, *NAR* (gkae1010) — cite alongside the build date |
| **NP Atlas** | **2024_09** | actinobacteria build stamp (recorded in the workspace tool provenance) | van Santen 2022, NP Atlas |
| **nr** (NCBI) | rolling / unversioned | remote — record per-run access date | Sayers 2024 |

## Honest caveats (do not overstate in Methods)

- **antiSMASH versions must be read per input.** Earlier inventory prose conflated
  intake archives, package directories, and a reference shelf. Do not transfer a dev-build
  label to an organism merely because it appeared in that inventory. Bind each comparison
  to the actual source JSON version and package receipt; describe mixed versions explicitly.
- **antiSMASH does not store its full command line.** `version`, `taxon`, `schema`, and the
  produced analyses are recoverable from the JSON; detection strictness (`loose`) comes from
  Mamey's `antismash_profile` field, not antiSMASH's own record.
- **Pfam "38.2" is count-inferred**, not read from a literal version string in `Pfam-A.hmm`.
- **SPAdes 4.2.0 is confirmed only for AS-XXX.** Assemblies span Oct 2025–2026 and may have
  used different Galaxy SPAdes wrappers; confirm each strain from its own Galaxy history.
- **pyhmmer / BiG-SCAPE versions are the installed-environment versions.** For a specific
  past run, confirm against that run's `run.log`.

## Additional external rendering dependencies

R tree graphics and sequence preparation can require SeqKit, R, ape, ggtree, treeio,
phangorn, and their dependencies. These are external companions, not bundled Python
requirements. Record the actual scripts invoked, `sessionInfo()` for R, and executable
version receipts. A listing here does not establish that these tools were used in a
particular figure, or that every version accepts the same command-line flags.

## Phylogenetic stage and figure provenance

Record the executable path and successful version probe for each stage. Separate protein BLAST and nucleotide/reference BLAST channels can resolve different installations; a single machine-wide BLAST version is insufficient. A failed version probe is unverified, not an empty version that passes.

MUSCLE command syntax must match the selected executable. Preserve the actual argv and version receipt; do not infer compatibility from an environment name. Inspect subprocess exit status before interpreting an empty alignment or search output as missing biological data.

The R renderer is an external dependency, separate from Python and the sequence-analysis binaries. Its session receipt records the loaded package versions. Preserve that receipt alongside the figure, analysis tree, display metadata and methods. The number of metadata strips is configurable; two strips are not mandatory for every figure. Source and host text must come from the bound metadata, with missing values left explicit.

Historical versions in the table are context only. They do not select a current executable, database or scientific result. Optional sequence utilities and R packages have their own upstream license and citation information; record the exact installed versions rather than copying a development machine's environment into a portable methods statement.
