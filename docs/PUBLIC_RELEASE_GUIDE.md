# Public release — user guide

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
and `bio`, or `all` together. Run `python mamey_run.py start` and `python mamey_run.py doctor`
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

1. The Pfam HMM (`scanner_pfam.hmm`) is **not bundled** — the public-tier tests forbid it in the tree — so
   HMM-based scanning does not work out of the box. Before going offline, rebuild it from Pfam-A with
   the `hmmfetch` recipe in `docs/PUBLIC_RELEASE_DATA.md` (or obtain a copy), carry the file in, and
   point the engine at it: set `SM_HMM_DB` to the file path, and/or place it at
   `$MAMEY_DATA_ROOT/hmm/scanner_pfam.hmm` (or set `MAMEY_HMM_DIR` to its folder) so `doctor` reports it
   (see `docs/EXTERNAL_ASSETS_GUIDE.md`). Without it the scanner uses the regex fallback, or you can
   supply antiSMASH `--fullhmmer` output instead. `bundle_support/install_sapote_addons.sh` installs the
   add-on Python stack (`pyhmmer` etc.), not the HMM file itself.
2. Produce your antiSMASH result ZIP(s) on a connected machine or a local antiSMASH install.
3. For BLASTp evidence, run BLASTp externally and bring in the Hit Table (CSV) + XML2, then use
   `ingest-blastp` (no network).
4. Everything else — extraction, boundary/assembly tiering, KCB triage, Mode B cards, figures,
   packaging, gates, and reporting — runs locally with no network.

Under an enforced offline environment, provision required inputs before the run; fetching is an explicit preparation step you perform
yourself, on your terms, ahead of time.

## 6. Graceful degradation summary

| Missing | Effect | Fix |
|---------|--------|-----|
| `scanner_pfam.hmm` — **not bundled (operator-acquired)** | Absent by default: scanner uses regex; HMMER cells report `NEEDS_HMMER_DOMTBLOUT` | Rebuild from Pfam-A per `docs/PUBLIC_RELEASE_DATA.md` (or obtain a copy), then set `SM_HMM_DB` / `MAMEY_HMM_DIR` as in §5 |
| cairosvg (`render` extra) | Compiled-PDF SVG figures are dropped, not embedded; render still succeeds | `pip install '.[render]'`, or install a system `rsvg-convert`/`inkscape` |
| figure stack (`matplotlib`/…) | Figure generation is skipped | `pip install '.[figures]'` or `'.[all]'` |

Nothing in this list blocks a run from reaching completion; each is a graceful fallback, not a failure.
A fallback is not the missing capability, though: HMM-based scanning is unavailable until you provision
the HMM, and a regex-path result must not be reported as an HMM scan.
