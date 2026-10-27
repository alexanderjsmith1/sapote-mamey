# Public release — user guide

To install this CODE archive, follow [INSTALL](INSTALL.md). To check its recorded release and validation
evidence, use [Release records](RELEASE_RECORDS_GUIDE.md). This page explains which assets you need to
supply and how to prepare a selected workflow for local or offline use.

> **Current-tree status.** This CODE archive records its validation results in the release manifest. [`pyproject.toml`](../pyproject.toml) and the synced package identity define its canonical bundle version; [`RELEASE_MANIFEST.md`](../RELEASE_MANIFEST.md) defines its current release status.

Suite logs and archive seal or owner receipts are external evidence. The manifest's recorded status does
not validate later source edits or make a new release decision.

The archive contains code and small governed data. The curated Pfam HMM is operator-provisioned;
use [Public release data](PUBLIC_RELEASE_DATA.md) for its provenance and optional rebuild recipe.

## 1. What this release is

Check the actual [tier manifest](../TIER_MANIFEST.txt) and [release manifest](../RELEASE_MANIFEST.md)
for shipped files and release status. External datasets and some integration-test fixtures are
provisioned separately. The curated Pfam HMM is not bundled. See [NOTICE](../NOTICE) for attribution
and the [external assets guide](EXTERNAL_ASSETS_GUIDE.md) for data provision. A fallback or missing
evidence state does not establish that an HMM scan ran.

## 2. Setup in brief

Follow [INSTALL](INSTALL.md) using **Python 3.12 or newer** and an isolated environment.
Install the core with `python -m pip install -e .`; choose only the optional extras your task needs:
`figures`, `documents`, `bio`, or `all` for the declared combined set (including slides and render support).
Offline wheels must match the selected Python ABI, operating system and architecture.

In an editable working installation, read the [doctor write-probe boundary](INSTALL.md#doctor-scope-and-write-probe)
and leave an occupied `runs/_doctor_probe` untouched. If you have not already completed INSTALL diagnostics in this installation, run
orientation and then the diagnostic once from the bundle root:

```bash
python -B mamey_run.py start --no-doctor
python mamey_run.py doctor
```

Plain `start` already invokes `doctor`. Read the diagnostic result, then follow the
[first-analysis walkthrough](MASTER_WALKTHROUGH.md), or use the [Quick Guide](GUIDE/02_Quick_Guide.md)
for command and evidence-budget choices.

## 3. Inputs and external assets

Supply the antiSMASH result ZIP for your input. Sapote-Mamey consumes that output; it does not
run antiSMASH itself. Provision additional databases and system tools required by your selected
workflow using [PREREQUISITES](PREREQUISITES.md) and [EXTERNAL ASSETS](EXTERNAL_ASSETS_GUIDE.md).
The optional HMM rebuild recipe is in [PUBLIC RELEASE DATA](PUBLIC_RELEASE_DATA.md).
Record unavailable channels explicitly; installation alone does not verify an evidence result.

## 4. Network behavior depends on the command

Core extraction from local antiSMASH inputs and local package validation use local data.
Optional online homology, reference-fetching tools, dependency installation, and externally
invoked companions may contact remote services. The existence of an offline workflow is not
a guarantee that every command in this bundle is offline.

For a restricted environment, provision dependencies and reference data in advance, use the
local extraction and validation commands, and admit already saved evidence through the
appropriate import workflow. Review each companion command and configuration before running it;
use an environment-level network restriction when a zero-network guarantee is required.

## 5. Running fully air-gapped

To run with zero network access:

1. Provision the exact local inputs, dependencies, external binaries and reference data needed by the selected workflow before the offline run. For operator-provisioned scanner models, follow [the source-bound data guide](PUBLIC_RELEASE_DATA.md) and [scanner manifest limits](reference/SCANNER_PFAM_MANIFEST.md). A filename/doctor path check does not verify the model bytes, membership or scan execution. `SM_HMM_DB` wins when its path exists; directory discovery then checks `MAMEY_HMM_DIR`, `$MAMEY_DATA_ROOT/hmm` and source/add-on locations (`mamey/wheelhouse.py`).
2. Retain the selected antiSMASH result ZIP and version/options provenance. Saved `--fullhmmer` annotations and a regex fallback are separate evidence paths; neither proves a local scanner HMM run or fills a missing custom HMMER domtblout channel.
3. Bring in already saved BLASTP results with their query/run/database binding and use the [stored-result ingestion protocol](ONLINE_BLASTP_PROTOCOL.md). Saved evidence ingestion is separate from authorizing or performing online searches.
4. Select commands documented to use local inputs and enforce the required environment-level network restriction. Review invoked companions, dependency provisioning and configurations separately; local availability does not guarantee every possible workflow in the bundle is offline or complete.

Under an enforced offline environment, provision required inputs before the run; fetching is an explicit preparation step you perform
yourself, on your terms, ahead of time.

## 6. Missing capability and output states

| Missing capability | Source-backed consequence | Recovery |
| --- | --- | --- |
| Operator-provisioned scanner HMM | Discovery may have no model path; a regex-path result does not establish HMM scanning. Custom-marker HMMER evidence can remain `NEEDS_HMMER_DOMTBLOUT` independently of scanner discovery (`mamey/wheelhouse.py`; `mamey/cell_provenance.py`). | Bind the exact model source/receipt for the selected owner; preserve each evidence channel's missingness. |
| SVG converter | For an SVG reference, the compiled-PDF artwork stage tries vector conversion, then a publication-resolution raster fallback. Conversion failure, missing artwork or an escaping path returns `FIGURE_QUALITY_REFUSED` through the PDF reader. A requested PDF failure exits nonzero while the written Markdown remains available (`mamey/compile_report.py`). | Read the PDF diagnostic, provision the selected converter if needed, and retain the Markdown and failed-render evidence before retrying. |
| Figure dependencies | BiG-SCAPE network output returns `SKIPPED_NO_DEPS` when its networkx/matplotlib import block fails; other figure owners have their own dependency behavior (`mamey/bigscape_figures.py`). | Follow [external-tool prerequisites](EXTERNAL_TOOL_INVENTORY.md) and inspect each required output/status; skipped is not completed. |
| Primary PDF renderer or fallback toolchain | `tools/md_to_pdf.sh` tries the primary renderer, then requires pandoc and xelatex after a primary failure; a missing fallback tool exits 2. The fallback also prepares local resources, writes preflight sidecars and can fail during rendering. | Keep the canonical Markdown and diagnostics. Check both the requested PDF and any fallback sidecars; provisioning and rendered-page review remain separate work. |

No global completion guarantee follows from a fallback. Check required files, per-output states, bound inputs and current acceptance holds; report incomplete deliverables explicitly. See [installation](INSTALL.md), [result reading](READING_YOUR_RESULTS.md) and [deliverable contract](DELIVERABLE_CONTRACT.md).
