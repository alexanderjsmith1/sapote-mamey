# External data — what this bundle does NOT ship, and how to provision it

Before any `doctor` example below, read the [write-probe boundary](INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation; if `runs/_doctor_probe` is occupied, leave it
untouched. The current diagnostic can overwrite or remove its probe file.

Run engine examples from the selected bundle directory containing `pyproject.toml` and `mamey_run.py`, using its compatible activated Python interpreter; bind external inputs separately.


**The main full reference-database snapshots are operator-provisioned.** Small retained reference assets and optional scanner/add-on tiers have their own ownership and availability; inspect what the selected bundle actually contains. Provisioning a directory does not admit it as scientific evidence.

The bundle is MIT-licensed **code**. Reference databases carry their own licences, their own citation
requirements, and their own release cadence. Three problems with bundling them:

1. **Licence misstatement.** MIBiG is CC BY 4.0 and NP Atlas is CC BY-NC 4.0 (non-commercial; corrected v9.7.405 — the earlier text understated the restriction) — attribution required. Shipping them
   inside an MIT tree implies terms that do not apply. PubMed **abstracts** are copyrighted by their
   publishers and are not ours to redistribute at all.
2. **Frozen snapshots.** A bundled copy pins you to whichever release happened to be current when the
   cut was made, while your manuscript cites something else.
3. **Weight.** These payloads were **34% of the extracted tree** (17.6 MB of 51 MB).

So you download the real thing, once, and point the engine at it.

---

## Quick start

```bash
# one root for everything (recommended)
export MAMEY_DATA_ROOT=/path/to/sapote-external-data

mkdir -p "$MAMEY_DATA_ROOT"/{mibig,mibig/neighborhoods,literature,hmm,npatlas}
# ... download each dataset into its directory (see below) ...

python mamey_run.py doctor          # reports which datasets are provisioned and which are missing
```

For the generic resolver, the first candidate containing the expected probe file wins. A configured override with a missing probe can fall through to the shared root or legacy path. Inspect the reported resolved path, not just the environment string. HMM and exclusion governance have their own owner-specific rules below.

| Dataset | Env var | Default location under `$MAMEY_DATA_ROOT` |
|---|---|---|
| MIBiG reference index | `MAMEY_MIBIG_DIR` | `mibig/` |
| MIBiG neighborhoods | `MAMEY_MIBIG_NEIGHBORHOODS_DIR` | `mibig/neighborhoods/` |
| Literature corpus | `MAMEY_LITERATURE_CORPUS` | `literature/` |
| Pfam profile HMMs | `MAMEY_HMM_DIR` | `hmm/` |
| NP Atlas | `MAMEY_NPATLAS_DIR` | `npatlas/` |

---

## The datasets

### 1. MIBiG — reference index and neighborhoods

- **Licence:** CC BY 4.0. **Attribution required**; cite the MIBiG release you used.
- **Get it:** <https://mibig.secondarymetabolites.org/download>
- **Put it at:** `$MAMEY_DATA_ROOT/mibig/`, containing `mibig_reference_index.bacterial.json`.
- **Neighborhoods** are *derived* partitions (KS / AT / C / A / glyc / resi), not raw MIBiG. They are
  **deterministically rebuildable** from the panel:

  ```bash
  python tools/mibig_neighborhoods.py --faa MIBiG_KS.faa --fam KS --thresh 1.5
  ```

  Method: MUSCLE 5.2 `-align` → FastTree 2.2.0 `-lg` → complete-linkage clade cut at patristic
  diameter ≤ 1.5 (chosen to avoid single-linkage chaining) → medoid representative per clade.
  Treat reproduction as dependent on the exact input panel and actual tool versions; this doc review did not run an alignment or tree. The helper obtains its output root from `workspace_root()` and writes under `strain_data/_NEIGHBORHOODS_2026-08-10/<fam>`; it has no `--out` option and can reuse that directory. Confirm the configured workspace and outputs before execution. It prepends a workspace-specific phylo environment bin path. A successful generic dataset probe does not prove those binaries or output destinations are ready.
- **Used by:** `mamey/mibig_neighborhoods_api.py`, `tools/mibig_neighborhoods.py`, comparator anchoring,
  `fragment_ceiling` reference sizes.
- **If absent:** anchor/comparator sections render `NOT MEASURED`. They do **not** render an empty
  result — absence of a comparator is never evidence of novelty.

### 2. Literature corpus — PMIDs, DOIs, titles, abstracts

> **This is the one with the sharpest constraint.** PubMed *metadata* is freely available, but
> **abstracts are copyrighted by their publishers**. The previously-bundled corpus contained **4,658
> full abstracts** shipping under an MIT code licence. Do not redistribute it.

- **Build it locally from PDF exports you obtained and are permitted to process.** The helper is not a
  network client: it parses local `*.pdf` files and writes the corpus directory. Install its optional
  PDF reader in your own environment if it is not already present:

  ```bash
  python -m pip install pypdf
  python mamey/data/literature/_corpus/pubmed_ingest.py \
    /path/to/pubmed-search-result-pdfs \
    "$MAMEY_DATA_ROOT/literature_candidate_new"
  ```

  It writes `literature_corpus.jsonl`, `literature_corpus.sqlite`, and `_manifest.json` to the supplied output directory. Build into a fresh candidate directory, inspect its source/counts and outputs, then explicitly point `MAMEY_LITERATURE_CORPUS` at that candidate if it is adopted. Do not rerun directly into the active corpus: JSONL is truncated/replaced, an existing SQLite file is deleted before rebuilding, and the manifest is written last with no three-file rollback. A failure can leave mixed old/new or partial artifacts. Preserve the candidate and captured stdout/stderr; recover into a fresh destination after resolving the cause.

  This is a full rebuild from the current input folder, not an incremental merge with an existing corpus. The helper scans only immediate lowercase `*.pdf` matches, not nested folders or uppercase `.PDF` names. Keep every intended export in the bound input scope. A nonexistent/empty input folder or PDFs with extraction errors can still produce a zero-entry corpus and finish normally: extraction errors print a diagnostic and return empty text. Compare expected PDF roster, per-file counts, unique PMIDs and `with_abstract` before adopting outputs. Zero parsed entries or an empty abstract is not proof that no paper or abstract exists. Obtaining, retaining, and using the PDF exports remains the operator's responsibility.

  Parsing is a heuristic for PubMed search-result list PDFs, not arbitrary articles or OCR. It requires PMID anchors and a parsed title, leaves authors blank, searches a small text window for DOI, and limits normalized abstract text to 6,000 characters. For repeated PMIDs, the first parsed title/year/DOI remain while a longer later abstract can replace the earlier one; source filenames and query tags accumulate. Review possible conflicting/truncated records against the original permitted PDF. `_manifest.json` records counts/query tags but no PDF, owner or output hashes; retain a separate source/output path-and-SHA-256 roster. Preserve original PDF exports in place.
- **Put it at:** `$MAMEY_DATA_ROOT/literature/literature_corpus.jsonl`
- **Used by:** §5 literature enrichment in Mode B cards. The `mamey/literature_lookup.py` reader uses JSONL rather than this helper's SQLite copy. Its process-local cache does not automatically refresh when the same corpus path or environment binding changes; use a new reader process after selecting/rebuilding a corpus. Invalid JSON lines are skipped, and repeated PMIDs take the last readable JSONL record. A missing lookup can therefore reflect missing, malformed or stale local corpus content, not a completed negative literature search. Corpus text is reference context, not independently accepted locus/product/activity evidence.
- **If absent:** literature enrichment is **optional** — the loader returns empty and the section must
  render `NOT MEASURED`, never a silent zero. This was already the designed behaviour for the
  purgeable public tier.

### 3. Pfam profile HMMs

- **Licence:** Pfam is CC0, so redistribution is *permitted* — but the profile set is large, versioned
  and upstream-maintained, so pin the release you cite rather than freezing a copy in a code release.
- **Get it:** <https://www.ebi.ac.uk/interpro/download/pfam/>
- **Put it at:** `$MAMEY_DATA_ROOT/hmm/`, with a scanner-compatible `scanner_pfam_150.hmm` or `scanner_pfam.hmm`. `SM_HMM_DB` can instead bind an explicit HMM file. The scanner resolver prefers that existing explicit file, then `MAMEY_HMM_DIR`, shared-root hmm, available bundle/add-on tiers and legacy scanner assets. Within a directory it prefers the larger named scanner set. Those filename-derived model-count hints are not a recomputed library census; bind the actual file hash/model metadata.
- **Used by:** the biosynthetic domain scanner (`mamey/wheelhouse.py`, `hmm_blastp_adjudicate.py`,
  `bgc_walk.py`, `tools/build_domain_matrix.py`).
- **If absent:** HMM-based domain scanning is unavailable and reports so. antiSMASH-derived domain
  tables are unaffected.

### 4. NP Atlas (optional; never previously bundled)

- **Recorded licence metadata:** the current bundle resolver records CC BY-NC 4.0 (noncommercial), correcting the older CC BY 4.0 text. Check the upstream licence for the exact release you obtain; a recorded resolver label alone does not verify the licence of a new download.
- **Get it:** <https://www.npatlas.org/download>
- **Put it at:** `$MAMEY_DATA_ROOT/npatlas/`, containing `np_atlas.json`.
- **Used by:** chemical dereplication (optional evidence layer 8).

### Still shipped in-bundle (and why that is fine)

`mamey/data/phylo_seeds/*.faa` — five MLSA seed proteins (atpD, gyrB, recA, rpoB, trpB) from the
**public type strain *Kitasatospora setae* KM-6054**. ~4 KB total. These are BLASTp **bait** only: the
seed's own identity never enters results, since `build_mlsa` takes each target genome's best-ortholog
CDS. Retained because they are tiny, public, and the pipeline is unusable without them.

---

## Checking your setup

```bash
python -c "from mamey import external_data as x, json; print(json.dumps(x.status(), indent=2))"
```

`external_data.resolve(key)` returns a resolved directory or None when a known dataset is absent; `require(key)` raises actionable MissingExternalData. An unknown key raises ValueError. `status()` reports file-layout availability; it does not validate the contents, reference release, licence compliance, HMM compatibility or a completed downstream analysis. Optional caller behavior varies: inspect the actual channel state rather than treating every empty value as a tested negative.

Exclusion/governance loading is distinct: explicit `MAMEY_OFFICIAL_DATA` or shared-root bindings are exclusive in the exclusion owner. See [the cohort-pack interface](COHORT_PACK_INTERFACE.md) before interpreting an empty exclusion set or denominator.

## Citation

When you publish, cite the datasets you actually used, at the release you used. The bundle does not
cite them on your behalf and cannot know which release you provisioned.
