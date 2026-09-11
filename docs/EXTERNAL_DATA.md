# External data — what this bundle does NOT ship, and how to provision it

**As of v9.7.362, Sapote-Mamey redistributes no third-party reference datasets.**

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

mamey doctor          # reports which datasets are provisioned and which are missing
```

Per-dataset overrides win over the shared root, if you keep things in different places:

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
  tools/mibig_neighborhoods.py --faa MIBiG_KS.faa --fam KS --thresh 1.5
  ```

  Method: MUSCLE 5.2 `-align` → FastTree 2.2.0 `-lg` → complete-linkage clade cut at patristic
  diameter ≤ 1.5 (chosen to avoid single-linkage chaining) → medoid representative per clade.
  Deterministic given the same panel and tool versions.
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
    "$MAMEY_DATA_ROOT/literature"
  ```

  It writes `literature_corpus.jsonl`, `literature_corpus.sqlite`, and `_manifest.json` to the supplied
  output directory. Obtaining, retaining, and using the PDF exports remains the operator's responsibility.
- **Put it at:** `$MAMEY_DATA_ROOT/literature/literature_corpus.jsonl`
- **Used by:** §5 literature enrichment in Mode B cards.
- **If absent:** literature enrichment is **optional** — the loader returns empty and the section must
  render `NOT MEASURED`, never a silent zero. This was already the designed behaviour for the
  purgeable public tier.

### 3. Pfam profile HMMs

- **Licence:** Pfam is CC0, so redistribution is *permitted* — but the profile set is large, versioned
  and upstream-maintained, so pin the release you cite rather than freezing a copy in a code release.
- **Get it:** <https://www.ebi.ac.uk/interpro/download/pfam/>
- **Put it at:** `$MAMEY_DATA_ROOT/hmm/`, containing `scanner_pfam.hmm`.
- **Used by:** the biosynthetic domain scanner (`mamey/wheelhouse.py`, `hmm_blastp_adjudicate.py`,
  `bgc_walk.py`, `tools/build_domain_matrix.py`).
- **If absent:** HMM-based domain scanning is unavailable and reports so. antiSMASH-derived domain
  tables are unaffected.

### 4. NP Atlas (optional; never previously bundled)

- **Licence:** CC BY 4.0 — attribution required.
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

Every accessor fails **loud and actionable** when a required dataset is missing — you get the dataset
name, the env var, the expected layout, the upstream URL and the licence, not a stack trace.

## Citation

When you publish, cite the datasets you actually used, at the release you used. The bundle does not
cite them on your behalf and cannot know which release you provisioned.
