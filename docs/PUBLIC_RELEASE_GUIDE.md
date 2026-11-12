# Public release — user guide

To install this CODE archive, follow [INSTALL](INSTALL.md). This page lists the assets you must supply yourself and how to prepare a workflow for offline use. To see which release you hold, see [RELEASE_MANIFEST](../RELEASE_MANIFEST.md).

> **Current-tree status.** This CODE archive records its validation results in the release manifest. [`pyproject.toml`](../pyproject.toml) and the synced package identity define its canonical bundle version; [`RELEASE_MANIFEST.md`](../RELEASE_MANIFEST.md) defines its current release status. For a working tree changed since that archive, check its own identity and validation records; the inherited manifest does not validate the changed tree.

## 1. What this release is

The archive holds code and small governed data. It does not hold external datasets, some test fixtures or the curated Pfam HMM (a small file of protein-family models used by the optional scanner). Check the [tier manifest](../TIER_MANIFEST.txt) for the files it ships. See [NOTICE](../NOTICE) for attribution and the [external assets guide](EXTERNAL_ASSETS_GUIDE.md) for data you provide.

## 2. Setup

Follow [INSTALL](INSTALL.md) for the Python version, the environment and the optional extras. Then follow [Your first run](reader/01_FIRST_RUN.md). It starts with `doctor` and tells you how to read its last line.

## 3. Inputs and external assets

Supply one antiSMASH result ZIP per strain. Sapote-Mamey reads antiSMASH output. It does not run antiSMASH. [PREREQUISITES](PREREQUISITES.md) and [EXTERNAL ASSETS](EXTERNAL_ASSETS_GUIDE.md) list the databases and programs each workflow needs.

The scanner HMM is optional. To build it, follow [the scanner manifest](reference/SCANNER_PFAM_MANIFEST.md). Without it, `doctor` reports no model and the scanner does not run. A regex fallback result does not mean an HMM scan ran.

## 4. Which commands use the network

Extraction from a local antiSMASH ZIP and package validation use local data only. These commands contact remote services:

- `blastp-online` (NCBI) and `blastp-ebi` (EBI);
- `auto-blastp`, which queues online searches;
- installing packages with `pip`, and the tools that fetch references or 16S records.

Companion programs you run yourself, such as BiG-SCAPE or GToTree, may also fetch data. Read each one before you run it. Use a firewall or an offline machine if you need a guarantee of zero network traffic.

## 5. Running fully air-gapped

1. Before you go offline, install the Python packages and the programs your workflow needs, and download the reference data. Wheels must match your Python version, operating system and CPU type.
2. Set the HMM location if you use the scanner. The scanner and `doctor` use the same search, in this order (`resolve_hmm_database`, `mamey/wheelhouse.py:55-128`):
   1. the file named by `SM_HMM_DB`. It must be a regular file. If it names an existing folder or other non-file, the search stops with no model (tier `none`); if the path does not exist, the resolver continues to later locations. Check the reported path before attributing a model to the override;
   2. a folder named by `MAMEY_HMM_DIR`, but only if it holds `scanner_pfam_150.hmm` (preferred) or `scanner_pfam.hmm`. Otherwise the next place is tried;
   3. `$MAMEY_DATA_ROOT/hmm`, with the same two file names;
   4. folders inside the bundle or the add-on layout.

   Read the path `doctor` reports. A file that is found is not proof that the model file is valid.
3. Keep the antiSMASH ZIP and a note of the antiSMASH version and options. Saved `--fullhmmer` annotations and the regex fallback are separate evidence. Neither replaces a local scanner run.
4. Run the local commands: `doctor`, `inspect`, `run`, `validate`.
5. Bring in BLASTp results you saved earlier with `ingest-blastp`, following the [stored-result protocol](ONLINE_BLASTP_PROTOCOL.md). Importing saved results is separate from running a search.

The run was offline only if you blocked the network at the system level. A missing network connection does not stop a command that does not need it.

## 6. When a capability is missing

| Missing | What you see | What to do |
|---|---|---|
| Scanner HMM | `doctor` shows no model path. Custom-marker HMMER evidence can read `NEEDS_HMMER_DOMTBLOUT`. | Build the HMM ([scanner manifest](reference/SCANNER_PFAM_MANIFEST.md)), or leave the channel missing. Missing is not negative. |
| SVG converter | The PDF step tries vector conversion, then a raster fallback. If both fail it reports `FIGURE_QUALITY_REFUSED`. A requested PDF then exits nonzero. The Markdown is still written. | Read the PDF message, install a converter if needed, and rerun. Keep the Markdown. |
| Figure libraries | BiG-SCAPE network output reports `SKIPPED_NO_DEPS` when `networkx` or `matplotlib` fails to import. | Install the figures extra ([INSTALL](INSTALL.md)). Skipped is not complete. |
| PDF toolchain | `tools/md_to_pdf.sh` tries its main renderer first. If that fails, it needs `pandoc` and `xelatex`. If either is missing it exits 2 and prints `PDF_TOOLCHAIN_UNAVAILABLE`. | Keep the Markdown. Install the missing tool, or use a machine that has it. |

A fallback does not mean the deliverable is complete. Check each required file and each output status. See [reading your results](READING_YOUR_RESULTS.md) and the [deliverable contract](DELIVERABLE_CONTRACT.md).

## 7. Publishing a workbook

This page does not cover the disclosure check for a public workbook. `tools/audit_public_cut.py` compares a public workbook candidate with the private master; read its [audit limits](CUSTOM_PRIVACY_TIERS.md#public-workbook-audit-limits) first. It does not read formulas, sheet names, comments, hyperlinks, document properties or images, so review those by hand as a separate step. Keep the private workbook unchanged. A clean audit or a profile label is not release approval.
