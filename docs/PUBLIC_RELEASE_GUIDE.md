# Public release — user guide

Before any `doctor` example below, read the [write-probe boundary](INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation; if `runs/_doctor_probe` is occupied, leave it
untouched. The current diagnostic can overwrite or remove its probe file.

> **Current-tree status.** This CODE archive records its validation results in the release manifest. [`pyproject.toml`](../pyproject.toml) and the synced package identity define its canonical bundle version; [`RELEASE_MANIFEST.md`](../RELEASE_MANIFEST.md) defines its current release status.

This supporting guide describes public-release setup and network behavior. Start at [README](../README.md). It covers what the release contains
(code and small governed data; the Pfam HMM is operator-provisioned, not bundled), how the pipeline uses the network, and how to run it in a sensitive
or air-gapped environment with confidence. For the step-by-step setup see `docs/INSTALL.md`; for the HMM's
provenance and an optional rebuild recipe see `docs/PUBLIC_RELEASE_DATA.md`.

## 1. What this release is

Check the actual [tier manifest](../TIER_MANIFEST.txt) and [release manifest](../RELEASE_MANIFEST.md)
for shipped files and release status. External datasets and some integration-test fixtures are
provisioned separately. The curated Pfam HMM is not bundled. See [NOTICE](../NOTICE) for attribution
and the [external assets guide](EXTERNAL_ASSETS_GUIDE.md) for data provision. A fallback or missing
evidence state does not establish that an HMM scan ran.

## 2. Setup in brief

Follow [INSTALL](INSTALL.md) using **Python 3.12 or newer** and an isolated environment.
Install the core with `python -m pip install -e .`; optional extras include `figures`, `documents`,
and `bio`, or `all` for the declared combined extras (including slides/render/documents in this source). Run `python mamey_run.py start` and `python mamey_run.py doctor`
from the bundle root, then follow the [Quick Guide](GUIDE/02_Quick_Guide.md).
Offline wheels must match the selected Python ABI, operating system, and architecture.

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

1. Provision the exact local inputs, dependencies, external binaries and reference data needed by the selected workflow before the offline run. For operator-provisioned scanner models, follow [the source-bound data guide](PUBLIC_RELEASE_DATA.md) and [scanner manifest limits](reference/SCANNER_PFAM_MANIFEST.md). A filename/doctor path check does not verify the model bytes, membership or scan execution. `SM_HMM_DB` wins when its path exists; directory discovery then checks `MAMEY_HMM_DIR`, `$MAMEY_DATA_ROOT/hmm` and source/add-on locations (`mamey/wheelhouse.py:60–126`).
2. Retain the selected antiSMASH result ZIP and version/options provenance. Saved `--fullhmmer` annotations and a regex fallback are separate evidence paths; neither proves a local scanner HMM run or fills a missing custom HMMER domtblout channel.
3. Bring in already saved BLASTP results with their query/run/database binding and use the [stored-result ingestion protocol](ONLINE_BLASTP_PROTOCOL.md). Saved evidence ingestion is separate from authorizing or performing online searches.
4. Select commands documented to use local inputs and enforce the required environment-level network restriction. Review invoked companions, dependency provisioning and configurations separately; local availability does not guarantee every possible workflow in the bundle is offline or complete.

Under an enforced offline environment, provision required inputs before the run; fetching is an explicit preparation step you perform
yourself, on your terms, ahead of time.

## 6. Missing capability and output states

| Missing capability | Source-backed consequence | Recovery |
| --- | --- | --- |
| Operator-provisioned scanner HMM | Discovery may have no model path; a regex-path result does not establish HMM scanning. Custom-marker HMMER evidence can remain `NEEDS_HMMER_DOMTBLOUT` independently of scanner discovery (`mamey/wheelhouse.py:60–126`; `mamey/cell_provenance.py:117–145`). | Bind the exact model source/receipt for the selected owner; preserve each evidence channel's missingness. |
| SVG converter | Compiled-report publication artwork tries vector conversion, then a resolution-bound raster fallback. If neither works it raises `FIGURE_VECTOR_EMBED_UNAVAILABLE`; missing/escaping artwork also raises (`mamey/compile_report.py:950–1045`). It does not silently drop required SVG artwork and claim success. | Use the selected renderer's local converter prerequisites and retain the error/receipt. |
| Figure dependencies | Behavior depends on the owner: some tools have hard imports; BiG-SCAPE network output returns `SKIPPED_NO_DEPS` when networkx/matplotlib imports fail (`mamey/bigscape_figures.py:88–95`). | Follow [external-tool prerequisites](EXTERNAL_TOOL_INVENTORY.md) and inspect each required output/status; skipped is not completed. |
| Primary PDF renderer or fallback toolchain | `tools/md_to_pdf.sh:25–49` tries ReportLab, then requires pandoc and xelatex; missing fallback tools exits 2. Later artwork/render errors can also fail. | Preserve canonical Markdown and render diagnostics; install/provisioning and rendered-page review are separate authorized work. |

No global completion guarantee follows from a fallback. Check required files, per-output states, bound inputs and current acceptance holds; report incomplete deliverables explicitly. See [installation](INSTALL.md), [result reading](READING_YOUR_RESULTS.md) and [deliverable contract](DELIVERABLE_CONTRACT.md). This documentation patch performs no installation, network workflow, render, cut or release.
