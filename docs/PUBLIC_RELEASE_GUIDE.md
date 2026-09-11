# Public release — user guide

> **Current-tree status.** This CODE tree is a controlled quality-recheck candidate, not a signed public release. [`pyproject.toml`](../pyproject.toml) and the synced package identity define its canonical bundle version; [`RELEASE_MANIFEST.md`](../RELEASE_MANIFEST.md) defines its current release status.

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

1. The Pfam HMM is **not bundled** (see `docs/EXTERNAL_ASSETS_GUIDE.md`); acquire or rebuild it before any HMM step for
   HMM-based scanning — it works offline out of the box. (Only if you deliberately removed it would you
   need to carry a copy in, or rely on the regex fallback / antiSMASH `--fullhmmer` output.)
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
| `scanner_pfam.hmm` — **not bundled (operator-acquired)** | Only if you removed it: scanner uses regex; HMMER cells report `NEEDS_HMMER_DOMTBLOUT` | Nothing needed; rebuild from Pfam-A (§3) only for a newer Pfam |
| cairosvg (`render` extra) | Compiled-PDF SVG figures are dropped, not embedded; render still succeeds | `pip install '.[render]'`, or install a system `rsvg-convert`/`inkscape` |
| figure stack (`matplotlib`/…) | Figure generation is skipped | `pip install '.[figures]'` or `'.[all]'` |

Nothing in this list blocks a run from reaching completion; each is a graceful fallback, not a failure.
