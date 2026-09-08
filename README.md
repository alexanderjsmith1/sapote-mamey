# Sapote-Mamey

**Claim-safe interpretive genome mining for actinomycete biosynthetic gene clusters (BGCs).**

Sapote-Mamey turns antiSMASH output into auditable, claim-safe biosynthetic evidence packages and interpretations. It is built in two layers, and the boundary between them is deliberate:

- **Mamey.** Mamey is the executable BGC-analysis module — a deterministic Python engine that extracts and records source-derived measurements and evidence states: BGC inventory, boundary tiers, KCB triage, per-gene comparison evidence, and figures. Given the same admitted inputs and configuration, it produces the same outputs and defers biological judgment.
- **Sapote.** Sapote is the governed post-extraction judgment workflow. It uses Mamey's sealed evidence packages to author gene-by-gene Mode B cards, ecological synthesis, and deliverables under hard claim-safety rules: capacity is not production; similarity is not identity; missing evidence is not biological absence; and every claim must remain tied to a retrievable source. Mode B authoring is therefore not part of Mamey's deterministic fact-generation layer.

Developed for natural-product discovery from bee-, wasp-, and bryophyte-associated actinomycetes, targeting MRSA and *Candida*.

## What it does

A strain flows through the pipeline as: antiSMASH ZIP → Mamey extraction and inventory → boundary/assembly tiering → KCB triage → per-gene comparison evidence → sealed evidence package → governed Sapote review → gene-by-gene Mode B cards → ecological synthesis → candidate deliverables. The gates are designed to reject unsupported observations, flag product-identity language, and fail closed when an exact locus or source binding cannot be established. Gate success verifies the encoded checks; it does not establish biological identity, production, activity, acceptance, or publication readiness.

## Install

> **Build status.** This CODE tree is a controlled quality-recheck candidate, not a signed public release; the footer of this file carries the exact bundle and engine versions. [`RELEASE_MANIFEST.md`](RELEASE_MANIFEST.md) is the authoritative status source.
>
> GitHub source users: start with `docs/PUBLIC_RELEASE_GUIDE.md` for what ships, the Pfam HMM you provision yourself, the tool's runtime network behavior, and air-gapped operation. Full step-by-step setup is in `INSTALL.md`.
>
> **Online BLASTp contact email:** the tool ships with no email baked in and never sends one it invented. If you use the optional online BLASTp channels you supply your own address — `mamey blastp-ebi --submit` requires `--email`, and NCBI's `blastp-online` runs without one but asks you to include it for fair use. See §4 of `docs/PUBLIC_RELEASE_GUIDE.md`. The offline `ingest-blastp` path needs no email and no network.

### Core

The core engine needs **Python 3.12 or newer**. Core dependencies (`openpyxl`, `ijson`, `numpy`, `pandas`, `matplotlib`, and `biopython` for the online BLASTp channel) install from `requirements.txt`:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pip install -e .                # install the mamey package + `mamey` entry point (run from any dir)
python -m mamey doctor          # pre-flight environment check
```

That runs the deterministic engine. Domain scanning falls back to regex patterns until you add the science stack below.

### Add-on science stack (optional, set up yourself)

The add-on stack adds accelerated gene calling, ANI, alignment, offline HMM domain scanning, and the NP Atlas reference data. It ships as a separate archive of prebuilt wheels to keep the clone lean, and installs with **no network access**. It needs **Python 3.12 on Linux x86_64** (the wheels are built `cp312` / `manylinux` x86_64).

1. Download the add-on archive from the Releases page (`sapote-addons-core-<date>.zip`, ~29 MB: 34 wheels plus NP Atlas data; grab `sapote-addons-figures-<date>.zip` too for the full figure stack if it is published).
2. Unzip it at the repository root, next to `install_sapote_addons.sh`. It expands to `sapote_addons_core/`:
   ```bash
   unzip sapote-addons-core-<date>.zip
   ```
3. Run the installer from the repository root (it discovers the wheels and installs from local files only):
   ```bash
   bash install_sapote_addons.sh
   # or point it straight at the wheels:
   bash install_sapote_addons.sh sapote_addons_core/wheels
   ```

Skip this and the core still runs. See `PREREQUISITES.md` for the full add-on layout.

**If you have internet, install the wheels from PyPI instead.** Every wheel in the archive is a standard PyPI package, so on a connected machine you can skip the archive:

```bash
pip install pyrodigal pyrodigal-gv pyfastani pyskani pyswrd pyopal scoring-matrices \
            pyfamsa pytrimal pytantan pyhmmer biopython taxopy dendropy \
            gb-io pyfaidx pyfastx bcbio-gff gffutils
```

The vendored archive exists for offline installs and exact-version reproducibility; with network access, PyPI is simpler.

### External tools and data (not on PyPI)

A few pieces are not Python packages and are not installed by pip or the add-on archive. Get them from their own sources:

- **antiSMASH (required).** Sapote-Mamey interprets antiSMASH output; it does not run antiSMASH for you. Produce your result ZIPs with the web service at `https://antismash.secondarymetabolites.org` or a local Bioconda/Docker install, then feed them to `mamey run`.
- **pandoc (only for PDF/DOCX deliverables).** A system package: `https://pandoc.org/installing.html`. Markdown output works without it.
- **DIAMOND (optional).** A C++ binary from `https://github.com/bbuchfink/diamond` (or Bioconda). The bundled pyswrd backend is the default and needs no compile; the compare module auto-upgrades to DIAMOND only if a `diamond` binary is on PATH.
- **NP Atlas reference data (ships pre-built).** The `sapote_addons_core/npatlas/` JSONs derive from an NP Atlas download; source and updates at `https://www.np-atlas.org`.
- **Pfam-A / HMMER (ship as data).** The curated 35-family HMM is **not bundled**; rebuild it from Pfam-A (CC0) per `docs/EXTERNAL_ASSETS_GUIDE.md`. You need Pfam-A from EMBL-EBI / InterPro (`https://www.ebi.ac.uk/interpro`) only to rebuild it, and standalone HMMER (`https://hmmer.org`) only for the command-line tool rather than pyhmmer.

## Quickstart

```bash
# Extract and package one or more antiSMASH result ZIPs
python mamey_run.py run --input-zip path/to/antismash_result.zip --outdir runs/

# Validate and seal the package (runs all QC gates)
python mamey_run.py seal-package runs/<strain>/package

# Render the figure suite from the sealed package
python mamey_run.py render-all-figures runs/<strain>/package
```

`python mamey_run.py --help` lists the extraction, validation, comparison, figure, and post-seal support commands. Any Mode B command prepares or validates material for the governed Sapote judgment workflow; it does not convert Mode B interpretation into deterministic Mamey output.

For long strains in a length-limited session, add `--chatgpt-safe` (alias `--capped-session`) to `run` for a timeout-safe capped pass, then finish figures post-seal with `render-all-figures`.

## Repository layout

- `mamey/` — the deterministic engine (extraction, gating, figures; vendored `ijson` under `_vendor/`).
- `tools/` — release, audit, and authoring utilities.
- `docs/` — the operating contracts (Mode B, deliverables, claim-safety) and reference material; start at `SESSION_START_MANIFEST.md`.
- `skills/sapote-mamey/` — the operating skill: the front door for running the pipeline with an AI assistant.
- `tests/` — the regression suite (`python -m pytest`).

## Using with an AI assistant

This bundle is designed to be operated by Claude or ChatGPT. Upload the release ZIP into an assistant chat; the one door for coding agents is **`python mamey_run.py start`, then `AGENTS.md`** (= `CLAUDE.md`). `start` prints this bundle's real version and the ordered happy path, and `AGENTS.md` is the canonical contract. Read `CHATGPT_START_HERE.md` (ChatGPT — which runs from the controller `docs/CHATGPT_EXECUTION_SLICE_v97147.md`) or `CLAUDE_START_HERE.md` (Claude) only for assistant-specific rules; `000_READ_ME_FIRST_CHATGPT_CLAUDE.md` is the ChatGPT upload router. The `skills/sapote-mamey/SKILL.md` file encodes the claim-safety, Mode B, and audit disciplines the pipeline runs on.

## Citation-Compact Provenance and Citation Status

Sapote-Mamey uses citation-compact outputs to separate runtime evidence structure from literature verification.

- **antiSMASH 8.0** is recorded as method/database provenance for BGC detection and product/region calls: DOI `10.1093/nar/gkaf334`.
- **MIBiG 4.0** is recorded as reference-database provenance for curated BGC entries and KnownClusterBlast dereplication context: DOI `10.1093/nar/gkae1115`.
- **`PASS_STRUCTURE`** means the package structure, citation ledger, work-order files, compact reports, manifest tracking, and checksum tracking passed validation. It does **not** mean every literature claim has been manually verified.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a safe handoff for another literature session — a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope.

## Data availability

Strain identifiers in this repository are public: the **SID** cohort follows the Chevrette et al. (2019) dataset, and the **AS** cohort is published with strain/genus/host/16S/accession metadata. No unpublished strain data ships in the public release; banked cohort data (`cohort/`) and any private material (`private/`) are excluded via `.gitignore` and distributed separately.

## Scientific integrity

The interpretive layer is bound by claim-safety rules enforced in code (`tools/claim_safety_linter.py`, `mamey/claim_safety_gate.py`, and the Mode B structure gate): biosynthetic *capacity* is never reported as confirmed *production*; KCB/BLASTp similarity is never rendered as identity; bioactivity is extract-level, never per-BGC; and no observation is stated that isn't tied to a real result.

## Citation

If you use Sapote-Mamey, please cite it (see `CITATION.cff`) and antiSMASH 8.0 (Blin et al.). BGC detection depends on antiSMASH; interpretation depends on this pipeline.

## License

Code is released under the MIT License (`LICENSE`), © 2026 Alexander J. Smith. Documentation is covered by `LICENSE-DOCS.txt`. Bundled third-party code and its licenses are listed in `THIRD_PARTY_LICENSES.md`.

---
*Current bundle: v9.7.414 / engine 1.9.152 · build 20260907v97414a · release profile: CODE quality-recheck candidate; not signed public release (see RELEASE_MANIFEST.md)*
