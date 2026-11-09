# External data: what the bundle does not ship, and how to add it

Core extraction needs only your antiSMASH result ZIP and a working Python environment. Optional stages (comparisons, domain scanning, literature, phylogeny) need reference data you download yourself. Get only what your task needs, then point the engine at it:

Run engine commands from the bundle folder that holds `pyproject.toml` and `mamey_run.py`. Install steps are in [your first run](reader/01_FIRST_RUN.md) and [installation](INSTALL.md).

```bash
export MAMEY_DATA_ROOT=/path/to/sapote-external-data
mkdir -p "$MAMEY_DATA_ROOT"/{mibig,mibig/neighborhoods,literature,hmm,npatlas}
# download each dataset into its folder (see below)
```

Check which datasets the engine can find:

```bash
python mamey_run.py doctor
```

If `runs/_doctor_probe` already exists, `doctor` reports a failed write check and leaves that folder alone ([details](INSTALL.md#doctor-scope-and-write-probe)).

To pick your task's inputs, start with [companion files](COMPANION_FILES.md#inputs-for-the-selected-task). Python packages are in [installation](INSTALL.md); system tools are in [prerequisites](PREREQUISITES.md). Reuse assets you already have, in place, and record each one's source path, version and SHA-256. A dataset you did not provision is recorded as unavailable, never as zero.

## Why these are not in the bundle

The bundle is MIT-licensed code. The databases have their own licenses, citations and release cycles:

1. **Terms.** The bundle records CC BY 4.0 for MIBiG and CC BY-NC 4.0 for NP Atlas, and does not redistribute publisher abstracts. Check the terms of the release you actually download.
2. **Release.** A bundled copy would pin one release, while your manuscript cites another.
3. **Size.** The databases are large and change with each release.

## How the engine finds a dataset

For each dataset the resolver checks, in order: the dataset's own variable, then `$MAMEY_DATA_ROOT/<folder>`, then the old in-tree path (`mamey/data/mibig`, `mamey/data/literature/_corpus`, `Wheelhouse/hmm`, `OFFICIAL_DATA`). The bundle ships none of these, but files you place there are found. The first folder that contains the probe file wins. The Pfam HMM set is the exception: it follows its own lookup, described under the HMM heading below. A variable that points at a folder without the probe falls through to the next candidate, so check the path `status()` reports (the one-liner below), not the variable. `doctor` prints how many datasets it found (for example `2/6`) and, for each missing one, its variable and download URL. It never prints a path.

| Dataset | Variable | Folder under `$MAMEY_DATA_ROOT` | Probe file | Size |
|---|---|---|---|---|
| MIBiG reference index | `MAMEY_MIBIG_DIR` | `mibig/` | `mibig_reference_index.bacterial.json` | about 2.3 MB |
| MIBiG neighborhoods | `MAMEY_MIBIG_NEIGHBORHOODS_DIR` | `mibig/neighborhoods/` | `PROVENANCE.md` | about 0.1 MB |
| Literature corpus | `MAMEY_LITERATURE_CORPUS` | `literature/` | `literature_corpus.jsonl` | about 10.8 MB for about 7,600 records |
| Pfam scanner HMMs | `MAMEY_HMM_DIR` | `hmm/` | `scanner_pfam_150.hmm` or `scanner_pfam.hmm` (own lookup; see below) | about 4.4 MB (subset) |
| NP Atlas (raw) | `MAMEY_NPATLAS_DIR` | `npatlas/` | `np_atlas.json` | 50 to 200 MB; the full JSON is about 475 MB |
| Governance | `MAMEY_OFFICIAL_DATA` | `OFFICIAL_DATA/` | `exclusions.json` | under 1 MB |

Sizes are the code's own estimates. A probe file is the file whose presence tells the resolver a folder holds that dataset. `OFFICIAL_DATA/` holds the project's governance record: the exclusion list and the denominators that figures and counts use. It is supplied with your project and is not downloadable. If you have no project governance, you do not need it; the engine uses a built-in default.

The same variables are also covered in the [external assets guide](EXTERNAL_ASSETS_GUIDE.md). This page owns the dataset list.

HMMs, NP Atlas and governance have their own rules, below. Finding the probe file does not mean the consumer can use the data.

Check your setup:

```bash
python -c "import json; from mamey import external_data as x; print(json.dumps(x.status(), indent=2))"
```

It prints one entry per dataset. Trimmed output from a tree with only governance data present:

```json
{
  "literature": {
    "provisioned": false,
    "path": null,
    "env_var": "MAMEY_LITERATURE_CORPUS",
    "what": "PMID/DOI/title/abstract corpus for §5 literature enrichment",
    ...
  },
  "official_data": {
    "provisioned": true,
    "path": "<workspace>/OFFICIAL_DATA",
    "env_var": "MAMEY_OFFICIAL_DATA",
    ...
  }
}
```

`provisioned: true` with a path means the expected probe file was found in that folder. `provisioned: false` with `path: null` means the probe file was not found in the locations the resolver checks: the dataset's environment variable, then `$MAMEY_DATA_ROOT/<subfolder>`, then the bundle's legacy folder where one exists (`hmm` uses the scanner's own order). It does not mean no copy exists elsewhere, and a folder with partial files but no probe file also reads `false`. Check the source you intended before you decide the data are unavailable. A Python traceback usually means the command was not run from the bundle folder or the environment is not active; read the traceback for the actual error.

In code, `external_data.resolve(key)` returns a folder, or `None` when no checked location holds the probe file. `require(key)` raises `MissingExternalData` with instructions. An unknown key raises `ValueError`. NP Atlas also reports whether its normalized files are readable and how many named records they hold. That can disagree with its raw probe. None of these reports verifies scientific content or release terms. Governance consumers use the binding rules below.

## The datasets

### antiSMASH results

Supply the result ZIP for each strain. Mamey reads the results; it does not run antiSMASH or need its databases. Intake is in the [Quick Guide](GUIDE/02_Quick_Guide.md). To recover the genome FASTA from a ZIP, see [companion files](COMPANION_FILES.md#recover-a-genome-from-an-antismash-zip).

### MIBiG reference index and neighborhoods

- **Recorded license label:** CC BY 4.0.
- **Get it:** <https://mibig.secondarymetabolites.org/download>
- **Put it at:** `$MAMEY_DATA_ROOT/mibig/`, containing `mibig_reference_index.bacterial.json`.
- **Used by:** `mamey/mibig_neighborhoods_api.py`, `tools/mibig_neighborhoods.py`, looking up the closest known cluster for each region you analyze.
- **If absent:** required consumers can refuse the operation; optional sections must keep unavailable references distinct from a measured empty result. No comparator is never evidence of novelty.

Neighborhoods are groups of related MIBiG proteins, one set per enzyme family (KS, AT, C, A, glyc, resi). They are built from MIBiG, not copied from it. Rebuild one family with:

```bash
export SAPOTE_WORKSPACE_ROOT=/path/to/workspace   # a folder OUTSIDE the bundle
python tools/mibig_neighborhoods.py --faa MIBiG_KS.faa --fam KS --thresh 1.5
```

`<workspace>` below means `SAPOTE_WORKSPACE_ROOT`. If it is unset, the tool looks for a parent folder holding `miniconda3`, `blast_dbs` or `Tools/databases`, and otherwise uses the current folder. Run from the bundle folder, that is inside the bundle, and the tool exits with `OUTPUT_INSIDE_BUNDLE`. Set the variable first.

Method: MUSCLE `-align`, then FastTree `-lg`, then the bundle's complete-linkage clade cut at patristic diameter ≤ 1.5, then one medoid per clade. The helper does not enforce tool versions; record the versions you actually used and the exact input panel. It needs `muscle` and `FastTree` in `<workspace>/miniconda3/envs/phylo/bin` (that folder is put first on `PATH`) or elsewhere on `PATH`. `--from-tree NEWICK` reuses an existing tree and skips both. The tool has no `--out` option: it writes under `<workspace>/strain_data/_NEIGHBORHOODS_2026-08-10/<fam>` (from `workspace_root()`) and can reuse that folder. Check it before running.

antiSMASH-processed MIBiG GBKs for BiG-SCAPE anchoring are a separate input, given with `--mibig-dir`; see the [BiG-SCAPE cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md).

### Pfam HMMs for the domain scanner

- **Recorded license label:** CC0. Pin the release you cite.
- **Get it:** download `Pfam-A.hmm` from <https://www.ebi.ac.uk/interpro/download/pfam/>. The scanner needs a subset, not the full file. Build it as described under [Build the scanner Pfam HMM subset](447_COMPANION_RETRIEVAL_CONTROLS.md#2-build-the-scanner-pfam-hmm-subset).
- **Put the resulting file at:** `$MAMEY_DATA_ROOT/hmm/`, as `scanner_pfam_150.hmm` (148-model hint) or `scanner_pfam.hmm` (35-model hint).
- **Used by:** the domain scanner (`mamey/wheelhouse.py`, `hmm_blastp_adjudicate.py`, `bgc_walk.py`).
- **If absent:** HMM scanning reports itself unavailable, and HMMER fields read `NEEDS_HMMER_DOMTBLOUT`. antiSMASH domain tables are unaffected.

The scanner looks in this order:

1. `SM_HMM_DB`, an explicit file path.
2. `MAMEY_HMM_DIR`.
3. `$MAMEY_DATA_ROOT/hmm/`.
4. Bundle `Wheelhouse/hmm/scanner_pfam_150.hmm`.
5. An add-on `scanner_pfam_150.hmm`.
6. Bundle `Wheelhouse/hmm/scanner_pfam.hmm`.

Steps 4 to 6 apply only to a bundle that carries its own HMM files. This bundle does not.

In a folder, the 148-model file wins. `SM_HMM_DB` is accepted if the path exists, even if it is a folder, so point it at the file itself. The 148 and 35 counts come from the file name, not from reading the file; record the file's hash.

Full Pfam-A is a different input, used only by BiG-SCAPE through `--pfam`, with its pressed index files. The scanner subset cannot replace it.

<a id="2-literature-corpus--pmids-dois-titles-abstracts"></a>
### Literature corpus

The bundle does not ship a corpus. Publisher abstracts are copyrighted, so you build one locally.

- **Build it offline from saved PubMed search-result PDFs you obtained and may process.** The helper is not a
  network client. In PubMed, run a search and save the result list as PDF. The helper
  `mamey/data/literature/_corpus/pubmed_ingest.py` reads those local `*.pdf` files and writes the corpus
  folder. Install its PDF reader if needed:

  ```bash
  python -m pip install pypdf
  python mamey/data/literature/_corpus/pubmed_ingest.py \
    /path/to/pubmed-search-result-pdfs \
    "$MAMEY_DATA_ROOT/literature_candidate_new"
  ```

  It writes `literature_corpus.jsonl`, `literature_corpus.sqlite` and `_manifest.json`. Build into a new folder, check the counts, then point `MAMEY_LITERATURE_CORPUS` at it. Never rebuild into the active corpus: the JSONL is truncated, the SQLite file is deleted first, the manifest is written last, and nothing is rolled back.
- **What it reads:** only lowercase `*.pdf` directly in the input folder (not subfolders, not `.PDF`). It is a full rebuild, not a merge. An empty folder or unreadable PDFs can still finish normally with zero entries, so compare the expected PDF list, per-file counts, unique PMIDs and `with_abstract` before adopting it.
- **Parsing:** built for PubMed search-result PDFs, not articles or scans. It needs a PMID and a title, leaves authors blank, looks for a DOI near the record and cuts abstracts at 6,000 characters. For a repeated PMID, the first title, year and DOI stay, and a longer later abstract can replace an earlier one. `_manifest.json` has counts and query tags but no hashes; keep your own list of PDF and output hashes.
- **Put it at:** `$MAMEY_DATA_ROOT/literature/literature_corpus.jsonl`.
- **Used by:** literature enrichment in Mode B cards, through `mamey/literature_lookup.py`, which reads the JSONL. It caches per process, so start a new process after switching corpus. Bad JSON lines are skipped, and a repeated PMID takes the last line.
- **If absent:** the reader returns empty results. The CLI can therefore print `0 hit(s)` without having a usable corpus; that is not a finished negative literature search. Its `stats()` uses `bool(records)` for `corpus_present`, so check the resolved file and source/count manifest as well. Literature remains reference context, not accepted locus, product or activity evidence.

### NP Atlas

- **License:** the resolver records CC BY-NC 4.0.
- **Get it:** <https://www.npatlas.org/download>
- **Raw file:** `$MAMEY_DATA_ROOT/npatlas/np_atlas.json` satisfies the presence check. It is not what the consumer reads.
- **Consumer files:** `npatlas_resolver.py` reads `all_actinobacteria_npatlas_ref.json` and `bacteria_nonactino_npatlas_ref.json`. Set `MAMEY_NPATLAS_DIR` to the folder holding them; `SM_NPATLAS_DIR` is an old name that still works with a warning. The resolver does not look in `$MAMEY_DATA_ROOT/npatlas` directly. It also searches fallback folders and keeps the first record for each lowercased name, so the variable is not exclusive. Start a new process after changing files; the index is cached.
- **Readiness:** `status()` reports `consumer_ready`, the named-compound count, the files used and unreadable files, separately from the raw presence check.
- **Used by:** named-compound enrichment, an optional evidence layer. It enriches a named similarity hit; it does not identify a strain's product.

Normalized schemas and receipts are in [NP Atlas provisioning](NPATLAS_PROVISIONING.md).

### OFFICIAL_DATA (governance)

When a source context is active it supplies governance first; see [cohort-pack binding](COHORT_PACK_INTERFACE.md#binding). Otherwise:

- `MAMEY_OFFICIAL_DATA`, if set, is the only place searched.
- Else `$MAMEY_DATA_ROOT/OFFICIAL_DATA/`, if `MAMEY_DATA_ROOT` is set, is the only place searched.
- Else the engine walks up from the package folders.

A bound or discovered missing, unreadable or malformed pack fails strict checks. A code-only tree with no binding and no discovered governance folder can still return the empty in-module default, even in strict mode. Non-strict runs can fall back to that default (with warnings for unusable discovered data). The general presence resolver is not proof of the governance pack a consumer selected. Check the actual binding before using a denominator; an empty default does not establish your cohort's policy.

### BLAST and reference comparisons

Local homology needs BLAST+ and a database. The phylogeny and outgroup tools read `BLAST_BIN` or find BLAST on `PATH`; database paths are set per command. For a local 16S database (`SAPOTE_16S_DB`), see [the local 16S database guide](LOCAL_16S_DATABASE.md). For online protein searches, follow [the online BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md).

### Phylogenomics

Use the reference genomes, metadata and tools your workflow names; see [phylogeny autopilot](PHYLO_AUTOPILOT_WORKFLOW.md). Binaries are found through `MAMEY_PHYLO_BIN`, `PHYLO_BIN`, `PLACEMENT_BIN` or command options. GToTree has its own data setup. A tree task does not need every GTDB resource.

### Shipped seed files

`mamey/data/phylo_seeds/` holds five MLSA seed proteins (atpD, gyrB, recA, rpoB, trpB; 4,172 bytes). Their headers name one reference strain; read the FASTA headers for it. They are BLASTp bait: the driver takes the highest-bitscore subject and retrieves that subject's CDS. The seed is not added to the alignment, and a hit does not prove orthology (`tools/build_mlsa.py`). You can supply your own seed folder.

### Python packages

Use the extras in `pyproject.toml`. `.[addons]` adds the comparative and scanner stack. `.[all]` covers figures, bio, render, documents and slides; it does not include addons or test tools. The three wheels in `wheels/` (packaging, setuptools, wheel) are not an offline runtime. See [companion installation](COMPANION_FILES.md#installation-and-companion-tool-boundaries).

## Citation

Cite every dataset you used, at the release you used. The bundle cannot know which release you provisioned.
