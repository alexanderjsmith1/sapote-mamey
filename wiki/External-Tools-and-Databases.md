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

**Provenance model:** tool versions below are the versions **installed in this
workflow's environment** (the re-run contract). Where a *specific historical cohort run*
is cited in a manuscript, confirm that tool against that run's own `run.log` /
`manifest.json` — the value here is the environment, not each past log.

---

## Pipeline stages → tool → version

| # | Stage | Tool | Version (verified) | Run-defining parameters | Citation |
|---|---|---|---|---|---|
| 1 | Assembly | **SPAdes** (via Galaxy / usegalaxy.org) | 4.2.0 (confirmed for AS-XXX; confirm per strain from its Galaxy history) | `--isolate --cov-cutoff off`, error-correction off, k=21,33,55,77 | Prjibelski 2020, *Curr Protoc Bioinformatics* 70:e102; Galaxy Community 2024, *NAR* 52(W1):W83–W94, 10.1093/nar/gkae410 |
| 2 | BGC detection | **antiSMASH** | 8.0.4 (core cohort) | `--taxon bacteria`, detection strictness = **loose**; KnownClusterBlast + ClusterBlast + Pfam-domain + RRE-finder enabled (schema 4) | Blin 2023 (antiSMASH 7), plus the antiSMASH 8 paper of record — cite the version actually run |
| 3 | Extraction + triage | **Sapote-Mamey (Mamey)** | engine 1.9.142 / bundle 9.7.400 (verified: the sealed 45-package AS estate, uniform by filename stamp; per-package stamp is authoritative) | `run --mode gold` | this bundle (doc ships in 9.7.401) |
| 4a | Homology — curated, local | **BLAST+ `blastp`** vs Swiss-Prot | 2.17.0+ | default protein search | Camacho 2009, *BMC Bioinformatics* 10:421 |
| 4b | Homology — comprehensive, remote | **NCBI BLAST (web)** vs **nr** | web service (nr is rolling/unversioned) | record per-run access date | Sayers 2024 (NCBI resources) |
| 4c | Homology — curated, remote | **EBI Job Dispatcher** vs **UniProtKB** | remote service (UniProtKB release not locally stamped — record access date) | default | Madeira 2024, *NAR* 52(W1):W521–W525, 10.1093/nar/gkae241 |
| 5 | GCF families / network | **BiG-SCAPE 2** (bundled **pyhmmer**, **Pfam-A**) on **MIBiG** | BiG-SCAPE 2.0.3 · pyhmmer **0.12.1** · Pfam **38.2** · MIBiG **4.0** | GCF clustering anchored on MIBiG | BiG-SCAPE 2 (Navarro-Muñoz 2020 lineage); pyhmmer — Larralde & Zeller 2023, *Bioinformatics* 39(5):btad214, 10.1093/bioinformatics/btad214; Pfam — Paysan-Lafosse 2025, *NAR* (gkae997) |
| 6 | Cluster figures | **clinker**; **matplotlib**; **NumPy** | clinker 0.0.32 | default alignment | clinker — Gilchrist 2021; matplotlib — Hunter 2007; NumPy — Harris 2020 |
| 7 | Taxonomy / phylogenomics | **Prodigal, BLAST+, MUSCLE, trimAl, IQ-TREE 3, fastANI, GToTree, NCBI datasets** | Prodigal 2.6.3 · MUSCLE v5 · trimAl 1.5.rev1 · IQ-TREE 3.1.2 · fastANI 1.34 · GToTree 1.8.16 · datasets 18.33.1 | 6-locus MLSA (MUSCLE) + 138-SCG core-genome ML backbone (GToTree) | per-tool papers of record (see phylogenomics methods) |
| 7b | Phylogenetic **placement** (query→fixed reference tree) | **MAFFT, RAxML-NG, EPA-ng, gappa** — *conda env, NOT bundled; `tools/` ships only the driver `phylo_place.py`* | MAFFT 7.526 · RAxML-NG 2.0.2 · EPA-ng 0.3.8 · gappa 0.9.0 (probed from the installed env — see *Version provenance* below) | `molecule=nucleotide`, `model=GTR+G`; reference tree built then held **FIXED**; queries placed, they do not re-infer the topology | EPA-ng — Barbera 2019, *Syst Biol* 68:365; gappa — Czech 2020, *Bioinformatics* 36:3263; RAxML-NG — Kozlov 2019, *Bioinformatics* 35:4453; MAFFT — Katoh & Standley 2013, *Mol Biol Evol* 30:772 |
| 7c | Reference-set construction / quick trees | **FastTree**, **BLAST+ `blastn`**, **BLAST+ `makeblastdb`** | per installed env (BLAST+ 2.17.0+) | local reference DB build + nucleotide search; FastTree for fast draft topologies | FastTree — Price 2010, *PLoS ONE* 5:e9490; BLAST+ — Camacho 2009, *BMC Bioinformatics* 10:421 |
| 7d | **Fungal** phylogenetics (rDNA screen → BUSCO-gene genome MLSA; see [Fungal Phylogenetics](Fungal-Phylogenetics.md)) | **ITSx, barrnap, BUSCO *or* compleasm** (+ MUSCLE/trimAl/IQ-TREE/BLAST+/`datasets` from rows 7/7c) | ITSx 1.1.3 · barrnap **1.10.5** (verified by run; engine **Infernal 1.1.5** `cmsearch`; `fun.rRNA.cm` built from Rfam RF00001+RF01960+RF02543) · compleasm **0.2.9** (miniprot + hmmsearch; the working macOS path) · BUSCO 5.x (fails on macOS-arm64 — Linux container only) | rDNA: ITSx / barrnap `--kingdom euk` or blastn reference-probe; MLSA: BUSCO/compleasm lineage `ascomycota_odb10+`, shared single-copy orthologs → partitioned IQ-TREE | ITSx — Bengtsson-Palme 2013, *Methods Ecol Evol* 4:914; barrnap — Seemann, github.com/tseemann/barrnap; BUSCO — Manni 2021, *Mol Biol Evol* 38:4647; compleasm — Huang & Li 2023, *Bioinformatics* 39:btad595 |
| 8 | Reference databases | see database table below | — | — | — |
| 9 | Interpretive judgment | Sapote (Tier 2/3, LLM protocol) | Markdown protocol, not code | — | — |

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

- **antiSMASH is not uniformly 8.0.4 across every genome — but the cohort is.** A sweep of
  752 intake files across all packages found **734 on 8.0.4 and 18 on `8.dev-cf2fc5ee(changed)`**.
  Every governed AS-cohort strain and every SID-cohort strain is **8.0.4**; all 18 `8.dev` packages
  (~11 distinct organisms — *Kitasatospora setae*, *Oscillatoria acuminata*, *Paenibacillus
  thiaminolyticus*, several *Streptomyces* type strains, and a few `_reference_shelf/` genomes) are
  reference/type-strain comparison shelf material, not cohort strains. So: cohort BGC detection cites
  antiSMASH **8.0.4**; any figure or tree that mixes in the type-strain shelf must footnote the
  `8.dev` build (a dev commit, not a numbered release — do not cite it as an antiSMASH release), or
  re-run those genomes on released 8.0.4 before folding their BGC counts into 8.0.4 comparative claims.
- **antiSMASH does not store its full command line.** `version`, `taxon`, `schema`, and the
  produced analyses are recoverable from the JSON; detection strictness (`loose`) comes from
  Mamey's `antismash_profile` field, not antiSMASH's own record.
- **Pfam "38.2" is count-inferred**, not read from a literal version string in `Pfam-A.hmm`.
- **SPAdes 4.2.0 is confirmed only for AS-XXX.** Assemblies span Oct 2025–2026 and may have
  used different Galaxy SPAdes wrappers; confirm each strain from its own Galaxy history.
- **pyhmmer / BiG-SCAPE versions are the installed-environment versions.** For a specific
  past run, confirm against that run's `run.log`.
