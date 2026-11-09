<!-- Mirror of docs/EXTERNAL_TOOL_INVENTORY.md, made by tools/sync_wiki_mirrors.py. Edit the source, then run: python3 tools/sync_wiki_mirrors.py --apply -->
# External tool & database inventory

**Bundle v9.7.464 · engine Mamey 1.9.180 · compiled 2026-11-08**

This page lists the external bioinformatics tools and reference databases the workflow depends on. Each row gives a version, the run-defining parameters and a citation. For the helper scripts shipped in `tools/`, see [the generated tools inventory](../docs/TOOLS_INVENTORY.generated.md), a different document.

It documents methods, not results. It asserts nothing about product structure or bioactivity. BLAST, KnownClusterBlast and BiG-SCAPE measure similarity, not identity.

## How to read the versions

The versions below were recorded in one environment. They do not tell you what is installed on your machine, and a row is not proof that a method ran. For each analysis, record the executable path, the output of a successful version command, the database release and the arguments. For an older result, use that run's own receipt or figure caption.

`python mamey_run.py doctor --companions` probes for local executables. For each local tool it runs a version command. When that returns one clear version number, it reports the number and compares it with the expected version: `MATCH`, `MISMATCH`, `NOT_SPECIFIED` when no version is expected, or `UNRECOGNIZED_POLICY` when the expected version is not in a form it can compare. Otherwise it reports why no version was read, for example a missing executable or a failed probe. It does not install tools or check that models and databases are present. A detected version is what is installed now, not the version an earlier run used, and it does not show that a workflow is ready. See [companion detection limits](../docs/companion_tools.md#detection).

---

## Pipeline stages → tool → version

| # | Stage | Tool | Recorded version or required run receipt | Run-defining parameters | Citation |
|---|---|---|---|---|---|
| 1 | Assembly | **SPAdes** (via Galaxy / usegalaxy.org) | record the version from your Galaxy history | `--isolate --cov-cutoff off`, error-correction off, k=21,33,55,77 | Prjibelski 2020, *Curr Protoc Bioinformatics* 70:e102; Galaxy Community 2024, *NAR* 52(W1):W83–W94, 10.1093/nar/gkae410 |
| 2 | BGC detection | **antiSMASH** | 8.0.4 (core cohort) | `--taxon bacteria`, detection strictness = **loose**; KnownClusterBlast + ClusterBlast + Pfam-domain + RRE-finder enabled  | antiSMASH 8.0 paper, *NAR*, 10.1093/nar/gkaf334; cite the version actually run |
| 3 | Extraction + triage | **Mamey** (this program) | Read `workflow_version` and `bundle_version` from each package's `manifest.json` | `run --mode gold` | the package manifest records the versions used |
| 4a | Homology — curated, local | **BLAST+ `blastp`** vs Swiss-Prot | record successful `blastp -version` / `blastn -version` for the run | default protein search | Camacho 2009, *BMC Bioinformatics* 10:421 |
| 4b | Homology — comprehensive, remote | **NCBI BLAST (web)** vs **nr** | web service (nr is rolling/unversioned) | record per-run access date | Sayers 2024 (NCBI resources) |
| 4c | Homology — curated, remote | **EBI Job Dispatcher** vs **UniProtKB** | remote service (UniProtKB release not locally stamped — record access date) | default | Madeira 2024, *NAR* 52(W1):W521–W525, 10.1093/nar/gkae241 |
| 5 | GCF families / network | **BiG-SCAPE 2** with operator-provisioned **pyhmmer**, **Pfam-A** and **MIBiG** | BiG-SCAPE 2.0.3 · pyhmmer **0.12.1** · Pfam **38.2** · MIBiG **4.0** | GCF clustering anchored on MIBiG | BiG-SCAPE 2 (Navarro-Muñoz 2020 lineage); pyhmmer — Larralde & Zeller 2023, *Bioinformatics* 39(5):btad214, 10.1093/bioinformatics/btad214; Pfam — Paysan-Lafosse 2025, *NAR* (gkae997) |
| 6 | Cluster figures | **clinker**; **matplotlib**; **NumPy** | clinker 0.0.32 | default alignment | clinker — Gilchrist 2021; matplotlib — Hunter 2007; NumPy — Harris 2020 |
| 7 | Taxonomy / phylogenomics | **Prodigal, BLAST+, MUSCLE, trimAl, IQ-TREE 3, fastANI, GToTree, NCBI datasets** | Prodigal 2.6.3 · MUSCLE major version must match the driver and run receipt · trimAl 1.5.rev1 · IQ-TREE 3.1.2 · fastANI 1.34 · GToTree 1.8.19 (the 2.0.x interface is experimental) · datasets 18.33.1 | `tools/build_mlsa.py` uses five protein loci; record the GToTree HMM set you selected | per-tool papers of record (see phylogenomics methods) |
| 7b | Phylogenetic **placement** (query→fixed reference tree) | **MAFFT, RAxML-NG, EPA-ng, gappa** — *conda env, NOT bundled; `tools/` ships only the driver `phylo_place.py`* | MAFFT 7.526 · RAxML-NG 2.0.2 · EPA-ng 0.3.8 · gappa 0.9.0 (probed from the installed env — see *Version provenance* below) | `molecule=nucleotide`; the current RAxML-NG reference build uses `GTR+I+G` (`LG+I+G` for protein), and for nucleotide the IQ-TREE fallback lets ModelFinder pick among equal rates, `+I`, `+G` and `+I+G`. A run's model comes from its inference receipt. Reference tree built then held **FIXED**; queries placed, they do not re-infer the topology | EPA-ng — Barbera 2019, *Syst Biol* 68:365; gappa — Czech 2020, *Bioinformatics* 36:3263; RAxML-NG — Kozlov 2019, *Bioinformatics* 35:4453; MAFFT — Katoh & Standley 2013, *Mol Biol Evol* 30:772 |
| 7c | Reference-set construction / quick trees | **FastTree**, **BLAST+ `blastn`**, **BLAST+ `makeblastdb`** | per installed env (BLAST+ record successful `blastp -version` / `blastn -version` for the run) | local reference DB build + nucleotide search; FastTree for fast draft topologies | FastTree — Price 2010, *PLoS ONE* 5:e9490; BLAST+ — Camacho 2009, *BMC Bioinformatics* 10:421 |
| 7d | Optional sequence-file inspection | **SeqKit** (external, not bundled) | record the resolved executable and successful version output when used | record the exact inspection/extraction command; this optional tool is not silently required by every workflow | retain the installed tool's citation with the run |
| 7e | Rectangular tree figures | **R**, **ggtree**, **treeio**, **ape**, **aplot**, **ggplot2** | retain the renderer's `.session.txt` output for the exact R and package versions | `tools/ggtree_rect_heatmap.R`; rectangular phylogram, optional titled metadata strips, exact tree/metadata joins | retain R and package citation output for the versions used |
| 8 | Reference databases | see the database table below | — | — | — |

## Tool license records and distribution scope

These labels describe external projects, not legal approval for a combined environment, modified patch, redistributed wheels or datasets. Separate invocation is an implementation fact where the owning driver shows it; no blanket copyleft/conflict conclusion follows from this inventory. Verify the exact installed/redistributed version and retained license notices. [Third-party license records](../docs/THIRD_PARTY_LICENSES.md) distinguish shipped source, bootstrap wheels, runtime companions and external data.

| Tool | Upstream license (for reference) |
|---|---|
| BiG-SCAPE 2 | AGPL-3.0 |
| DIAMOND | GPL-3.0 |
| GToTree | [MIT in current upstream repository](https://github.com/AstrobioMike/GToTree); companion dependencies separately licensed |
| Prodigal | GPL-3.0 |
| trimAl | GPL-3.0 |
| IQ-TREE | GPL-2.0 |
| FastTree | [GPL-3.0 in current upstream LICENSE](https://github.com/morgannprice/fasttree/blob/main/LICENSE); verify older installed distributions separately |
| HMMER | BSD-3-Clause |
| MUSCLE | GPL-3.0 (v5; verify per installed version) |
| BLAST+ | public domain (US Government work) |
| fastANI | Apache-2.0 |

## Installing the external binaries

The bundle ships Python drivers, not the scientific binaries or databases. A fresh clone has `tools/phylo_place.py`, `tools/placement_figure.py` and similar drivers, and still needs the programs they call. These conda commands are unpinned templates, not a version lock:

```bash
# placement stack (row 7b)
conda create -n placement -c bioconda -c conda-forge mafft raxml-ng epa-ng gappa
# phylogenomics stack (rows 7 and 7c)
conda create -n phylo     -c bioconda -c conda-forge prodigal muscle trimal iqtree fastani gtotree fasttree blast
```

Three environment variables tell the drivers where the binaries are. The defaults are conda envs under the workspace root.

| Variable | Default | Read by |
|---|---|---|
| `PLACEMENT_BIN` | `<root>/miniconda3/envs/placement/bin` | `tools/phylo_place.py`, `tools/figure_methods.py` |
| `PHYLO_BIN` | `<root>/miniconda3/envs/phylo/bin` | `tools/phylo_place.py`, `tools/figure_methods.py` |
| `MAMEY_PHYLO_BIN` | unset | `tools/build_mlsa.py`; an older alias for the `PHYLO_BIN` folder, and `build_mlsa.py` falls back to `PHYLO_BIN` when it is unset |

`tools/build_mlsa.py` takes `--bin-dir` first, then `MAMEY_PHYLO_BIN` or `PHYLO_BIN`, then PATH. Other drivers have their own lookup. `tools/mibig_neighborhoods.py` builds its own bin folder from the workspace root and does not read `PHYLO_BIN`.

See also [Prerequisites](Prerequisites.md), [the placement recipe](Phylogenetic-Placement.md) and [the GToTree workflow](../docs/GTOTREE_WORKFLOW.md).

## Reference databases

| Database | Release / build (verified) | Receipt | Citation |
|---|---|---|---|
| **Pfam-A** | **38.2** (30,134 families) | family count `grep -c "^ACC   PF" Pfam-A.hmm` → 30134 (matches 38.2 relnotes; the `.hmm` carries no literal version line — count-inferred) | Paysan-Lafosse 2025, *NAR* (gkae997) |
| **MIBiG** | **4.0** | antiSMASH KnownClusterBlast reference set | MIBiG 4.0 paper, *NAR*, 10.1093/nar/gkae1115 |
| **UniProtKB / Swiss-Prot** (local BLAST DB) | **Example build: NCBI `swissprot`, Jul 14 2026** — 487,492 sequences / 185,956,103 residues, BLASTDB v5 | `blastdbcmd -db swissprot -info` → `Date: Jul 14, 2026`; `swissprot.pin` header confirms | UniProt Consortium 2025, *NAR* (gkae1010) — cite alongside the build date |
| **NP Atlas** | **2024_09** | actinobacteria build stamp; record the release you used | van Santen 2022, NP Atlas |
| **nr** (NCBI) | rolling / unversioned | remote — record per-run access date | Sayers 2024 |

## Recording what you ran

- **antiSMASH.** Read the version from each input's result JSON and package receipt. The JSON holds the version, taxon, schema and analyses. It does not hold the command line; Mamey's `antismash_profile` field records the detection strictness (`loose`).
- **Pfam.** The 38.2 label comes from a family count, which is not a unique release identity. Keep the upstream release or archive hash and the model file you used.
- **SPAdes.** Read the version from each assembly's Galaxy history; Galaxy wrappers change over time.
- **pyhmmer and BiG-SCAPE.** The versions above are from one environment. Confirm against the run's `run.log`.
- **BLAST+.** Protein and nucleotide searches can resolve different installations. Record `blastp -version` and `blastn -version` for the run.
- **MUSCLE.** Command syntax depends on the executable. Keep the argv and version output, and check each subprocess's exit status before reading an empty alignment as biology.
- **R figures.** R, ggtree, treeio, ape, aplot and ggplot2 are external. Keep the renderer's `.session.txt` (or `sessionInfo()`) beside the figure, with the tree and metadata it used. The number of metadata strips is configurable. Source and host text come from the bound metadata, with missing values left explicit.
- **SeqKit and other optional tools.** Record the resolved executable and its version output when used.

`tools/figure_methods.py` automates part of this. It searches `PLACEMENT_BIN`, then `PHYLO_BIN`, then PATH, runs `--version`, takes the first numeric version from a successful exit and writes the values into the figure caption. A failed probe leaves the version empty, which means unverified, not a pass. It does not hash binaries or databases.
