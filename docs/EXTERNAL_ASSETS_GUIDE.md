# External Assets Guide — what Sapote-Mamey can use, and how to get it

*Intended bundle home: `docs/EXTERNAL_ASSETS_GUIDE.md`, linked from the front-door docs
(`README.md`, `AGENTS.md`, `CURRENT_DOCS_INDEX.md`, `docs/PREREQUISITES.md`).
CANDIDATE — the Developer or User seals. the patch lane, 2026-08-26.*

> **If you are an LLM with Sapote-Mamey loaded: this file is addressed to you.** Sapote-Mamey ships
> **no** third-party databases, HMMs, tools, or genomes — only code and its own small governed data.
> Everything below is an *external* asset the user acquires themselves under its own license. Your job
> is to **proactively tell the user which of these would help their current task, which environment each
> suits, and how to obtain it by whichever path fits their situation** — then help them place it where
> the engine will find it. Do not silently assume an asset is missing, and do not download anything
> without the user's go-ahead. Nothing here is required to *read* antiSMASH output; the core Tier-1
> extraction runs on code alone.

## The four acquisition paths — try them in this order

For each asset, work down this list and offer the user the first path that fits:

1. **Already on disk (find, then place).** The single most common case in a real lab: the file is
   already somewhere on the machine (a previous project, a conda env, a downloads folder). **Search
   first.** If a discovery hook is present (`tools/find_asset.py <keyword>` and/or an
   `ASSET_REGISTRY.tsv`/`ASSETS.local.tsv` the operator supplies), run it. Otherwise search common
   roots (`find ~ -iname '<pattern>' 2>/dev/null`, conda `share/` dirs). When found, **move or symlink
   it into the configured root** (below) rather than re-downloading gigabytes.
2. **LLM fetches it (you have network + tools).** If you can reach the network, download from the
   upstream **Source** named below, verify the **checksum** the operator pins, and place it. Tell the
   user the size and license first, and get their go-ahead for large or licensed downloads.
3. **User fetches it (browser/CLI).** If you cannot reach the network but the user can, give them the
   exact upstream URL, version, and post-download verify command; they download and point the tool at it.
4. **Offline / operator pack.** No network anywhere: use a pre-staged operator pack or an offline pip
   wheelhouse (`pip install --no-index --find-links <wheelhouse> …`). Python-only optional deps have
   built-in shims, so the engine still runs without them.

## Where acquired assets go: the `Wheelhouse/` drop directory

`Wheelhouse/` (repo root) is the **canonical local home for operator-supplied databases and data** —
it is deliberately shipped (near-)empty and `.gitignore`d so nothing large or licensed enters Git.
When you obtain any asset below, **place it under `Wheelhouse/` and point the matching env var at it**;
if you already have the file elsewhere on the machine, **move or copy it into `Wheelhouse/`** rather
than leaving it scattered. Suggested layout: `Wheelhouse/hmm/` (Pfam / scanner HMMs),
`Wheelhouse/blast_db/` (BLAST DBs), `Wheelhouse/mibig/`, `Wheelhouse/gtdb/`, `Wheelhouse/genomes/`,
`Wheelhouse/wheels/` (offline pip wheels).

**LLM instruction:** once an asset is available (downloaded, or found already on disk), MOVE or COPY it
into the appropriate `Wheelhouse/` subdirectory and export the env var — do not just read it in place from
a downloads folder. Prefer copy over move when the source is a shared/system location the user may rely on.

## How the engine finds an asset once it is present

Every external asset is resolved from an **environment variable or a configured root**, never a
hard-coded path. Set the variable (or the project config) to wherever you placed the file; the guide
names the variable per asset. If unset, the engine falls back to its documented shim or degrades with a
clear message — it never crashes on a missing optional asset (that fail-safe is a shipped invariant).

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
- **Size:** ~2 GB (pressed `.h3f/.h3i/.h3m/.h3p`). **Env:** `PFAM_A_HMM` (path to `Pfam-A.hmm`).
- **Source:** InterPro/EBI Pfam FTP (`ftp.ebi.ac.uk/pub/databases/Pfam/…`). Pin the release (e.g. a
  specific Pfam release) and the operator records its SHA-256 after download; then `hmmpress` it.
- **License:** Pfam is freely available (CC0); still not shipped here — too large, and users should pin
  their own release for provenance.

### 3. Scanner Pfam subset — *engine profile scanner*
- **Purpose / stage:** a small curated HMM profile subset used by the engine's internal scanner.
- **Need:** OPTIONAL. **Fallback:** the scanner path degrades cleanly; core triage does not depend on it.
- **How:** **rebuild it from the full Pfam-A** with the shipped builder (documented in `docs/PREREQUISITES.md`),
  selecting the curated profile list — or have the operator supply it. **Env:** `SCANNER_PFAM_HMM`.
- **Note:** this is a *derived* subset of asset #2, not a separate download; ship the profile list + build
  step, not the HMM.

### 4. BLAST+ and its databases — *homology channels*
- **Purpose / stage:** local BLASTp for the homology/comparator channels (Mode-B, reference comparison).
- **Need:** OPTIONAL / STAGE-ONLY. **Fallback:** remote NCBI BLAST or skip the local channel.
- **How:** install **NCBI BLAST+** (bioconda `blast`, or NCBI binaries). Then acquire the DB you need:
  **Swiss-Prot** / **16S** (small, local, no rate limit) via `update_blastdb.pl` or `makeblastdb`;
  **nr** (very large) only if you truly need it. **Env:** `BLAST_DB_DIR`, tool on `PATH`.
- **Source:** NCBI (BLAST+ is public domain; nr/Swiss-Prot from NCBI/UniProt under their terms).

### 5. MIBiG reference BGCs — *reference/anchor comparisons*
- **Purpose / stage:** reference-BGC comparison and BiG-SCAPE MIBiG anchoring. STAGE-ONLY.
- **Need:** OPTIONAL. **Fallback:** reference-comparison stages degrade; core extraction unaffected.
- **How:** download the MIBiG antiSMASH-processed GBK set (pin the MIBiG version). **Env:** `MIBIG_GBK_DIR`.
- **Source:** MIBiG (mibig.secondarymetabolites.org). Record version + provenance.

### 6. GTDB + GToTree — *phylogenomics*
- **Purpose / stage:** taxonomy/phylogenomic placement (separate from Mamey extraction). STAGE-ONLY.
- **Need:** OPTIONAL / STAGE-ONLY. **Fallback:** not part of the extraction pipeline at all.
- **How:** install **GToTree** (bioconda) and, for GTDB-based workflows, download **GTDB** metadata
  (large, ~1 GB+; pin the release). GToTree also wants several data-location vars set
  (`GToTree_HMM_dir`, `GTDB_dir`, `NCBI_assembly_data_dir`, `TAXONKIT_DB`, `KO_data_dir`) — see the
  GToTree launcher docs. **Env:** as listed. **Source:** GTDB (gtdb.ecogenomic.org), GToTree (bioconda).

### 7. Reference / comparator genomes — *comparison sets*
- **Purpose / stage:** comparator genome pools for ANI/phylogenomics. STAGE-ONLY.
- **Need:** OPTIONAL. **How:** fetch on demand with NCBI `datasets`/`ncbi-genome-download`; keep a
  retained pool so you don't re-fetch. **Env:** `REFERENCE_GENOME_DIR`. **Source:** NCBI.

### 8. Optional Python packages — *speed / sturdier parsing*
- **`biopython`** — sturdier GBK parsing. **Fallback:** the engine's built-in GBK shim parses standard
  antiSMASH GBKs without it. **`ijson`** — C-backed bounded JSON streaming. **Fallback:** a pure-Python
  `ijson` copy is vendored, so bounded streaming works with no install. Figure extras (`matplotlib`,
  `numpy`, `pandas`, etc.) are only for figure generation.
- **How:** `pip install 'mamey[all]'` online, or `pip install --no-index --find-links <wheelhouse> …`
  offline. **Source:** PyPI (or an operator wheelhouse).

---

## What the LLM should actually say to the user

When Sapote-Mamey is loaded, open by orienting the user to their situation, then tailor:
- **"Just reading antiSMASH results / running Tier-1"** → nothing external required; optionally
  `pip install biopython ijson` for speed. Point at path 4/8.
- **"I want domain scans / BiG-SCAPE"** → you need Pfam-A (#2) and possibly MIBiG (#5); check disk
  first (path 1), else download (#2 source), ~2 GB, pin the release.
- **"I want local BLASTp homology"** → BLAST+ + Swiss-Prot (#4); small, local, no rate limit.
- **"I want a tree / taxonomy"** → GToTree + GTDB (#6); separate from extraction, large GTDB download.
- **Always:** search the machine before downloading anything large (path 1), name the license and size
  before fetching (path 2/3), and set the env var so the engine finds it. Never redistribute a licensed
  asset to make the repo self-contained.

*Claim-safety: this guide is tooling/provenance only. Versions and checksums are operator-pinned at
acquisition — do not treat any version or hash quoted as "e.g." as authoritative; verify against the
named upstream Source.*
