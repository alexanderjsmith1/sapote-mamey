# External Assets Guide — what Sapote-Mamey can use, and how to get it

*Intended bundle home: `docs/EXTERNAL_ASSETS_GUIDE.md`, linked from the front-door docs
(`README.md`, `AGENTS.md`, `CURRENT_DOCS_INDEX.md`, `docs/PREREQUISITES.md`).
CANDIDATE — the Developer or User seals. the patch lane, 2026-08-26.*

> Sapote-Mamey ships **no** third-party databases, HMMs, tools, or genomes — only code and its own
> small governed data. Everything below is an *external* asset that you acquire yourself under its
> own license and then point the engine at. Nothing here is required to *read* antiSMASH output; the
> core Tier-1 extraction runs on code alone. Use this guide to decide which assets your task needs,
> where to obtain them, and which environment variable (if any) makes the engine find each one.
> Do not assume an asset is missing without checking; do not download anything you have not
> reviewed for source, version, size and license.

## Acquire only the assets needed for the selected task

1. Check your own inventory and explicitly permitted project paths first. Do not
   search the home directory or unrelated projects merely because an asset might be there.
2. If the asset is already available, point the selected command/configuration to it where
   supported. Do not move, copy or symlink a shared database automatically.
3. If a download is needed, identify the source, version, size, license and destination before
   the transfer. Network availability alone does not justify downloading assets.
4. For offline work, use a compatible pre-staged database or wheelhouse and preserve the
   missing-capability state when the required asset is absent.

## Where assets belong

Preserve your established project layout. `Wheelhouse/` is an available convention, not
an instruction to reorganize existing shared data or duplicate gigabytes into the source tree.
Record the actual configured path and hash. Distinguish Python package wheels from biological
reference databases even if a prior directory used one name for both. Use environment variables
or explicit options supported by the particular command; a generic root helper does not change
all output destinations. Announce file creation and include it in the session inventory.

## How the engine finds an asset once it is present

The engine-registered datasets are resolved by `mamey/external_data.py` in this order (first hit
wins): the dataset's own `MAMEY_*` variable → `$MAMEY_DATA_ROOT/<subdir>` → a legacy in-tree path,
if one still exists. `python mamey_run.py doctor` reports which of these datasets are provisioned.
Assets that are consumed by a companion tool rather than by the engine are passed on that tool's
command line (for example `--pfam`, `--mibig-dir`) or located through a tool-specific variable.
If a variable is unset, inspect that workflow's actual error or fallback receipt. Missing optional
assets may block a selected capability; no blanket no-crash or complete-fallback guarantee is made here.

Environment variables the code actually reads (verified against `mamey/` and `tools/`):

| Variable | Set it to | Read by |
|---|---|---|
| `MAMEY_DATA_ROOT` | one root folder holding `mibig/`, `mibig/neighborhoods/`, `literature/`, `hmm/`, `npatlas/`, `OFFICIAL_DATA/` subfolders | `mamey/external_data.py` (fallback for every dataset below), `mamey/exclusions.py`, `mamey/lead_pages.py`, several `tools/phylo_*.py` |
| `MAMEY_MIBIG_DIR` | folder containing `mibig_reference_index.bacterial.json` | `mamey/external_data.py` (`mibig`); `mamey/fragment_ceiling.py` |
| `MAMEY_MIBIG_NEIGHBORHOODS_DIR` | folder containing `PROVENANCE.md` and the KS/AT/C/A/glyc/resi neighborhood partitions | `mamey/external_data.py` (`mibig_neighborhoods`); `mamey/mibig_neighborhoods_api.py` |
| `MAMEY_LITERATURE_CORPUS` | folder containing `literature_corpus.jsonl` | `mamey/external_data.py` (`literature`); `mamey/literature_lookup.py` |
| `MAMEY_HMM_DIR` | folder containing `scanner_pfam.hmm` | `mamey/external_data.py` (`hmm`) — this is what `doctor` reports |
| `SM_HMM_DB` | the HMM **file** itself (`.../scanner_pfam.hmm` or `.../scanner_pfam_150.hmm`) | `mamey/wheelhouse.py:resolve_hmm_database` — the scanner's runtime override; checked before any in-tree or add-on location |
| `MAMEY_OFFICIAL_DATA` | folder containing `exclusions.json` (governed denominator / exclusion SSOT) | `mamey/external_data.py` (`official_data`); `mamey/exclusions.py`, `mamey/reference_strain_registry.py` |
| `MAMEY_NPATLAS_DIR` | folder containing `np_atlas.json` (`SM_NPATLAS_DIR` is a warned legacy alias) | `mamey/external_data.py` (`npatlas`); `mamey/npatlas_resolver.py`, `mamey/npatlas_structure.py` |
| `BLAST_BIN` | folder containing the BLAST+ executables | `tools/outgroup_registry.py`, `tools/phylo_refset.py`, `tools/_phylo16s.py` |
| `NCBI_EMAIL` | the e-mail address NCBI E-utilities require | `tools/phylo_16s_fetch.py` |
| `MAMEY_PHYLO_BIN` / `PHYLO_BIN` / `PLACEMENT_BIN` | folders containing the phylogeny / placement binaries | `tools/build_mlsa.py`, `tools/phylo_place.py`, `tools/figure_methods.py` |
| `BIGSCAPE_HOME` | the BiG-SCAPE install location | `tools/bigscape_pipeline.py` (`--bigscape` default) |

---

## Assets

Legend — **Need:** REQUIRED to run at all / OPTIONAL (speed or extra analysis) / STAGE-ONLY (only for a
specific downstream stage). **Fallback:** what happens when it is absent.

### 1. antiSMASH result (the INPUT) — *prerequisite, you generate it*
- **Purpose / stage:** Tier-1 intake. Mamey parses an antiSMASH output ZIP/GBK; it is the starting material.
- **Need:** REQUIRED (there is no run without an antiSMASH result to read).
- **How:** Run antiSMASH yourself on your genome (bacterial mode) — the antiSMASH **web server**
  (no install) or a local/conda/Docker antiSMASH. Mamey does **not** need antiSMASH's own databases;
  it reads the *results*. Place the ZIP where you point `--input-zip` / the intake convention.
- **Source:** antiSMASH (fungal/bacterial genome-mining; GNU AGPL for the software). Web server or bioconda.

### 2. Pfam-A HMM (full) — *domain scans / BiG-SCAPE*
- **Purpose / stage:** `hmmscan`-based domain annotation and BiG-SCAPE GCF clustering. STAGE-ONLY.
- **Need:** OPTIONAL / STAGE-ONLY. Not needed for core extraction or to read antiSMASH domains.
- **Fallback:** the engine's own small profile scanner and antiSMASH's in-result domains cover the
  core path; full Pfam is only for independent HMM scanning / BiG-SCAPE.
- **Size:** ~2 GB (pressed `.h3f/.h3i/.h3m/.h3p`). **Env:** none — the engine does not read a variable
  for full Pfam-A. Pass the path on the command line: `--pfam /path/Pfam-A.hmm` for
  `python mamey_run.py bigscape`, `tools/bigscape_pipeline.py` and `deliverable_tools/bigscape_run.py`.
- **Source:** InterPro/EBI Pfam FTP (`ftp.ebi.ac.uk/pub/databases/Pfam/…`). Pin the release (e.g. a
  specific Pfam release) and record its SHA-256 after download; then `hmmpress` it.
- **License:** Pfam is freely available (CC0); still not shipped here — too large, and users should pin
  their own release for provenance.

### 3. Scanner Pfam subset — *engine profile scanner*
- **Purpose / stage:** a small curated HMM profile subset (`scanner_pfam.hmm`, 35 families) used by the
  engine's internal scanner.
- **Need:** OPTIONAL. **Fallback:** without it the scanner uses the regex path and HMMER cells report
  `NEEDS_HMMER_DOMTBLOUT`; core triage does not depend on it. The file is not bundled; tests forbid it
  in the tree.
- **How:** **rebuild it from the full Pfam-A** with the `hmmfetch` recipe in `docs/PUBLIC_RELEASE_DATA.md`
  (there is no builder script in `tools/`) — or have the operator supply a copy. Then either
  set `SM_HMM_DB` to the file path (this is what the scanner's resolver reads first), or place the
  file at `$MAMEY_DATA_ROOT/hmm/scanner_pfam.hmm` / set `MAMEY_HMM_DIR` to its folder so that
  `doctor` reports it as provisioned. Setting both is the safe choice.
- **Note:** this is a *derived* subset of asset #2, not a separate download; ship the profile list + build
  step, not the HMM.

### 4. BLAST+ and its databases — *homology channels*
- **Purpose / stage:** local BLASTp for the homology/comparator channels (Mode-B, reference comparison).
- **Need:** OPTIONAL / STAGE-ONLY. **Fallback:** remote NCBI BLAST or skip the local channel.
- **How:** install **NCBI BLAST+** (bioconda `blast`, or NCBI binaries). Then acquire the DB you need:
  **Swiss-Prot** / **16S** (small, local, no rate limit) via `update_blastdb.pl` or `makeblastdb`;
  **nr** (very large) only if you truly need it. **Env:** `BLAST_BIN` (folder of the BLAST+
  executables, read by the `tools/phylo_*` and outgroup tools) — otherwise the tool on `PATH`. There is
  no engine variable for a database directory; each command takes its database path as an argument.
  Set `NCBI_EMAIL` for the E-utilities fetch tools.
- **Source:** NCBI (BLAST+ is public domain; nr/Swiss-Prot from NCBI/UniProt under their terms).

### 5. MIBiG reference BGCs — *reference/anchor comparisons*
- **Purpose / stage:** reference-BGC comparison and BiG-SCAPE MIBiG anchoring. STAGE-ONLY.
- **Need:** OPTIONAL. **Fallback:** reference-comparison stages degrade; core extraction unaffected.
- **How:** download the MIBiG release you intend to cite. For the engine, set `MAMEY_MIBIG_DIR` to the
  folder containing `mibig_reference_index.bacterial.json` (or place it at `$MAMEY_DATA_ROOT/mibig/`);
  the derived neighborhood partitions go in `MAMEY_MIBIG_NEIGHBORHOODS_DIR` (default
  `$MAMEY_DATA_ROOT/mibig/neighborhoods/`, rebuildable with `tools/mibig_neighborhoods.py`). For
  BiG-SCAPE anchoring, pass the antiSMASH-processed MIBiG GBK folder as `--mibig-dir` to
  `tools/bigscape_pipeline.py`.
- **Source:** MIBiG (mibig.secondarymetabolites.org; CC BY 4.0). Record version + provenance.

### 6. GTDB + GToTree — *phylogenomics*
- **Purpose / stage:** taxonomy/phylogenomic placement (separate from Mamey extraction). STAGE-ONLY.
- **Need:** OPTIONAL / STAGE-ONLY. **Fallback:** not part of the extraction pipeline at all.
- **How:** install **GToTree** (bioconda) and, for GTDB-based workflows, download **GTDB** metadata
  (large, ~1 GB+; pin the release). GToTree also wants several data-location vars set
  (`GToTree_HMM_dir`, `GTDB_dir`, `NCBI_assembly_data_dir`, `TAXONKIT_DB`, `KO_data_dir`) — see the
  GToTree launcher docs; these are GToTree's variables, not the engine's. The bundle's phylogeny tools
  locate their binaries through `MAMEY_PHYLO_BIN` / `PHYLO_BIN` / `PLACEMENT_BIN` (or `--bin-dir`).
  **Source:** GTDB (gtdb.ecogenomic.org), GToTree (bioconda).

### 7. Reference / comparator genomes — *comparison sets*
- **Purpose / stage:** comparator genome pools for ANI/phylogenomics. STAGE-ONLY.
- **Need:** OPTIONAL. **How:** fetch on demand with NCBI `datasets`/`ncbi-genome-download`; keep a
  retained pool so you don't re-fetch. **Env:** none — the engine reads no comparator-genome variable;
  pass the pool path to the tool you run (see `docs/PHYLO_AUTOPILOT_WORKFLOW.md`). **Source:** NCBI.

### 8. NP Atlas, literature corpus and OFFICIAL_DATA — *other engine-registered datasets*
- **NP Atlas** (dereplication; optional, never bundled): download from npatlas.org (CC BY-NC 4.0,
  non-commercial; do not redistribute). Set `MAMEY_NPATLAS_DIR` to the folder containing `np_atlas.json`
  (or `$MAMEY_DATA_ROOT/npatlas/`).
- **Literature corpus** (§5 literature enrichment; optional): build it locally with
  `mamey/data/literature/_corpus/pubmed_ingest.py` under your own institutional access — abstracts are
  publisher-copyrighted and are not redistributable. Set `MAMEY_LITERATURE_CORPUS` to the folder
  containing `literature_corpus.jsonl` (or `$MAMEY_DATA_ROOT/literature/`). If absent, enrichment
  renders NOT MEASURED.
- **OFFICIAL_DATA** (governance, not third-party): the release owner's `exclusions.json` / `EXCLUSIONS.md`
  set the governed denominator. Set `MAMEY_OFFICIAL_DATA` to that folder (or `$MAMEY_DATA_ROOT/OFFICIAL_DATA/`).
  An explicit `MAMEY_OFFICIAL_DATA` is exclusive; when it is absent the in-module default applies.
  Check `doctor` so you know which denominator is in force before generating a governed claim.

### 9. Optional Python packages — *speed / sturdier parsing*
- **`biopython`** — sturdier GBK parsing. **Fallback:** the engine's built-in GBK shim parses standard
  antiSMASH GBKs without it. **`ijson`** — C-backed bounded JSON streaming. **Fallback:** a pure-Python
  `ijson` copy is vendored, so bounded streaming works with no install. Figure extras (`matplotlib`,
  `numpy`, `pandas`, etc.) are only for figure generation.
- **How:** `pip install 'mamey[all]'` online, or `pip install --no-index --find-links <wheelhouse> …`
  offline. **Source:** PyPI (or an operator wheelhouse).

---

## Which assets your task needs

- **Just reading antiSMASH results / running Tier-1** → nothing external required; optionally
  `pip install biopython ijson` for speed. Point at path 4/9.
- **Domain scans / BiG-SCAPE** → you need Pfam-A (#2) and possibly MIBiG (#5); check disk
  first (path 1), else download (#2 source), ~2 GB, pin the release.
- **Local BLASTp homology** → BLAST+ + Swiss-Prot (#4); small, local, no rate limit.
- **A tree / taxonomy** → GToTree + GTDB (#6); separate from extraction, large GTDB download.
- **Always:** search the machine before downloading anything large (path 1), name the license and size
  before fetching (path 2/3), and set the variable from the table above so the engine finds it.
  Confirm with `python mamey_run.py doctor`. Never redistribute a licensed asset to make the repo
  self-contained.

*Claim-safety: this guide is tooling/provenance only. Versions and checksums are operator-pinned at
acquisition — do not treat any version or hash quoted as "e.g." as authoritative; verify against the
named upstream Source.*
