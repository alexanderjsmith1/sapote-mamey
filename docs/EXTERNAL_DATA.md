# External data: what the bundle does not ship, and how to add it

Core extraction needs only your antiSMASH result ZIP and a working Python environment. Optional stages (comparisons, domain scanning, literature, phylogeny) need reference data you download yourself. Get only what your task needs, then point the engine at it:

Read the [doctor write-probe note](INSTALL.md#doctor-scope-and-write-probe) first and use an editable working install. If `runs/_doctor_probe` already exists, `doctor` refuses; leave the folder alone. Run engine commands from the bundle folder that holds `pyproject.toml` and `mamey_run.py`.

```bash
export MAMEY_DATA_ROOT=/path/to/sapote-external-data
mkdir -p "$MAMEY_DATA_ROOT"/{mibig,mibig/neighborhoods,literature,hmm,npatlas}
# download each dataset into its folder (see below)
python mamey_run.py doctor        # reports which datasets it can find
```


To pick your task's inputs, start with [companion files](COMPANION_FILES.md#inputs-for-the-selected-task). Python packages are in [installation](INSTALL.md); system tools are in [prerequisites](PREREQUISITES.md). Reuse assets you already have, in place, and record each one's source path, version and SHA-256. A dataset you did not provision is recorded as unavailable, never as zero.

## Why these are not in the bundle

The bundle is MIT-licensed code. The databases have their own licenses, citations and release cycles:

1. **Recorded terms and policy.** The bundle records CC BY 4.0 for MIBiG and CC BY-NC 4.0 for NP Atlas, and excludes publisher abstracts from redistribution. Those are retained metadata and bundle policy, not an independent legal determination for a newly acquired release.
2. **Release.** A bundled copy pins whatever release was current at the cut, while your manuscript cites another.
3. **Size.** Earlier documentation records 17.6 MB of a 51 MB tree; this is historical, not a current census.

These license labels are what the bundle records. Check the terms of the release you actually download.

## How the engine finds a dataset

For each dataset the resolver checks, in order: the dataset's own variable, then `$MAMEY_DATA_ROOT/<folder>`, then the old bundle location. The first folder that contains the probe file wins. A variable that points at a folder without the probe falls through to the next candidate, so check the path `doctor` reports, not the variable.

| Dataset | Variable | Folder under `$MAMEY_DATA_ROOT` | Probe file |
|---|---|---|---|
| MIBiG reference index | `MAMEY_MIBIG_DIR` | `mibig/` | `mibig_reference_index.bacterial.json` |
| MIBiG neighborhoods | `MAMEY_MIBIG_NEIGHBORHOODS_DIR` | `mibig/neighborhoods/` | `PROVENANCE.md` |
| Literature corpus | `MAMEY_LITERATURE_CORPUS` | `literature/` | `literature_corpus.jsonl` |
| Pfam scanner HMMs | `MAMEY_HMM_DIR` | `hmm/` | `scanner_pfam.hmm` |
| NP Atlas (raw) | `MAMEY_NPATLAS_DIR` | `npatlas/` | `np_atlas.json` |
| Governance | `MAMEY_OFFICIAL_DATA` | `OFFICIAL_DATA/` | `exclusions.json` |

HMMs, NP Atlas and governance have their own rules, below. Finding the probe file does not mean the consumer can use the data.

Check your setup:

```bash
python -c "from mamey import external_data as x, json; print(json.dumps(x.status(), indent=2))"
```

`external_data.resolve(key)` returns a folder, or `None` when the dataset is absent. `require(key)` raises `MissingExternalData` with instructions. An unknown key raises `ValueError`. `status()` reports presence and resolved paths. NP Atlas also gets fresh normalized-consumer readability and named-record counts, which can disagree with its raw probe. Neither report verifies scientific content, release provenance, terms or a finished analysis. Governance consumers use the separate binding rules below.

## The datasets

### antiSMASH results

Supply the result ZIP for each strain. Mamey reads the results; it does not run antiSMASH or need its databases. Intake is in the [Quick Guide](GUIDE/02_Quick_Guide.md). To recover the genome FASTA from a ZIP, see [companion files](COMPANION_FILES.md#recover-a-genome-from-an-antismash-zip).

### MIBiG reference index and neighborhoods

- **Recorded license label:** CC BY 4.0. Bind the actual release and its terms; cite what you used.
- **Get it:** <https://mibig.secondarymetabolites.org/download>
- **Put it at:** `$MAMEY_DATA_ROOT/mibig/`, containing `mibig_reference_index.bacterial.json`.
- **Used by:** `mamey/mibig_neighborhoods_api.py`, `tools/mibig_neighborhoods.py`, comparator anchoring and `fragment_ceiling` reference sizes.
- **If absent:** required consumers can refuse the operation; optional sections must keep unavailable references distinct from a measured empty result. No comparator is never evidence of novelty.

Neighborhoods are partitions built from MIBiG (KS, AT, C, A, glyc, resi), not raw MIBiG. Rebuild one family with:

```bash
python tools/mibig_neighborhoods.py --faa MIBiG_KS.faa --fam KS --thresh 1.5
```

Method: MUSCLE `-align`, then FastTree `-lg`, then the bundle's complete-linkage clade cut at patristic diameter ≤ 1.5, then one medoid per clade. Earlier documentation names MUSCLE 5.2 and FastTree 2.2.0; this helper invokes the selected binaries without enforcing those versions. Record their actual versions and the exact input panel. The tool has no `--out` option: it writes under `<workspace>/strain_data/_NEIGHBORHOODS_2026-08-10/<fam>` (from `workspace_root()`), can reuse that folder, and puts a workspace phylo `bin` folder first on `PATH`. Check those before running.

antiSMASH-processed MIBiG GBKs for BiG-SCAPE anchoring are a separate input, given with `--mibig-dir`; see the [BiG-SCAPE cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md).

### Pfam HMMs for the domain scanner

- **Recorded license label:** CC0. Check the actual release's terms and pin the release you cite.
- **Get it:** <https://www.ebi.ac.uk/interpro/download/pfam/>
- **Put it at:** `$MAMEY_DATA_ROOT/hmm/`, as `scanner_pfam_150.hmm` (148-model hint) or `scanner_pfam.hmm` (35-model hint).
- **Used by:** the domain scanner (`mamey/wheelhouse.py`, `hmm_blastp_adjudicate.py`, `bgc_walk.py`, `tools/build_domain_matrix.py`).
- **If absent:** HMM scanning reports itself unavailable, and HMMER fields read `NEEDS_HMMER_DOMTBLOUT`. antiSMASH domain tables are unaffected.

The scanner looks in this order:

1. `SM_HMM_DB`, an explicit file path.
2. `MAMEY_HMM_DIR`.
3. `$MAMEY_DATA_ROOT/hmm/`.
4. Bundle `Wheelhouse/hmm/scanner_pfam_150.hmm`.
5. An add-on `scanner_pfam_150.hmm`.
6. Bundle `Wheelhouse/hmm/scanner_pfam.hmm`.

In a folder, the 148-model file wins. `SM_HMM_DB` is accepted if the path exists, even if it is a folder, so point it at the file itself. The 148 and 35 counts come from the file name, not from reading the file; record the file's hash. To build a scanner subset from a local Pfam-A, see [scanner provisioning](447_COMPANION_RETRIEVAL_CONTROLS.md#scanner-subset-provisioning); it downloads nothing.

Full Pfam-A is a different input, used only by BiG-SCAPE through `--pfam`, with its pressed index files. The scanner subset cannot replace it.

<a id="2-literature-corpus--pmids-dois-titles-abstracts"></a>
### Literature corpus

Earlier documentation records 4,658 bundled full abstracts. This historical declaration is not a current corpus count or an independent rights review. The bundle's policy is to build the corpus locally and not redistribute publisher abstracts with the MIT code.

- **Build it locally from PDF exports you obtained and may process.** The helper is not a
  network client: it parses local `*.pdf` files and writes the corpus folder. Install its PDF reader if needed:

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

- **License:** the resolver records CC BY-NC 4.0. Check the upstream license for your release, and the bundle's no-redistribution policy.
- **Get it:** <https://www.npatlas.org/download>
- **Raw file:** `$MAMEY_DATA_ROOT/npatlas/np_atlas.json` satisfies the presence check. It is not what the consumer reads.
- **Consumer files:** `npatlas_resolver.py` reads `all_actinobacteria_npatlas_ref.json` and `bacteria_nonactino_npatlas_ref.json`. Set `MAMEY_NPATLAS_DIR` to the folder holding them; `SM_NPATLAS_DIR` is an old name that still works with a warning. The resolver does not look in `$MAMEY_DATA_ROOT/npatlas` directly. It also searches fallback folders and keeps the first record for each lowercased name, so the variable is not exclusive. Start a new process after changing files; the index is cached.
- **Readiness:** `status()` reports `consumer_ready`, the named-compound count, the files used and unreadable files, separately from the raw presence check.
- **Used by:** named-compound enrichment (optional evidence layer 8). It enriches a named similarity hit; it does not identify a strain's product.

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

`mamey/data/phylo_seeds/` holds five MLSA seed proteins (atpD, gyrB, recA, rpoB, trpB; 4,172 bytes). Their headers name *Kitasatospora setae* KM-6054; the header alone does not establish source or terms. They are BLASTp bait: the driver takes the highest-bitscore subject and retrieves that subject's CDS. The seed is not added to the alignment, and a hit does not prove orthology (`tools/build_mlsa.py`). You can supply your own seed folder.

### Python packages

Use the extras in `pyproject.toml`. `.[addons]` adds the comparative and scanner stack. `.[all]` covers figures, bio, render, documents and slides; it does not include addons or test tools. The three wheels in `wheels/` (packaging, setuptools, wheel) are not an offline runtime. See [companion installation](COMPANION_FILES.md#installation-and-companion-tool-boundaries).

## Citation

Cite every dataset you used, at the release you used. The bundle cannot know which release you provisioned.
