# Install — Sapote-Mamey (public release)

> For the full picture — what's in the release (everything; nothing is stripped) and exactly what the
> tool does over the network at runtime (including air-gapped operation) — see
> **`docs/PUBLIC_RELEASE_GUIDE.md`**. This file is the step-by-step setup only.

This release is complete — nothing is stripped. The curated Pfam HMM set
is **not bundled** (acquire per `docs/EXTERNAL_ASSETS_GUIDE.md`); test fixtures ship in place, so there are minimal
downloads to complete setup. Step 4 below is optional and only relevant if you ever want to rebuild
the HMM yourself. See `NOTICE` for third-party data attribution.

1. **Get the code.** Clone the repository (or download and unzip the release):
   ```bash
   git clone <repo-url> sapote-mamey && cd sapote-mamey
   ```

2. **Python and core dependencies.** The core needs Python 3.10 or newer. (The optional add-on wheels in step 3 need Python 3.12 on Linux x86_64.)
   ```bash
   python3 -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   pip install -e .        # install the mamey package + the `mamey` console entry point
   ```
   The editable install is what lets `mamey` / `python -m mamey` resolve from any directory rather
   than only the repository root. (You can use `pip install .` for a non-editable install instead.)

3. **(Optional) offline science stack.** pyrodigal, pyfastani, pyswrd/pyopal, pyhmmer, biopython and
   friends ship as a separate add-on archive (`sapote-addons-core-<date>.zip`) of prebuilt wheels;
   download it, unzip at the repo root, and run `bash install_sapote_addons.sh`. On a connected machine
   you can instead `pip install` them from PyPI. See `PREREQUISITES.md` and the README for the full
   list and the external tools (antiSMASH, pandoc, DIAMOND) that are not on PyPI. Skip this if you only
   need the deterministic engine and are content with the regex fallback for domain scanning.

4. **(Optional) rebuild the HMM.** The curated Pfam HMM is **not bundled**; acquire or rebuild it per `docs/EXTERNAL_ASSETS_GUIDE.md`. If you ever want to rebuild it
   from a newer Pfam-A, the 35 families are listed in `Wheelhouse/hmm/SCANNER_PFAM_MANIFEST.md` and the
   fetch-and-press recipe is in `docs/PUBLIC_RELEASE_DATA.md`. (If the file is ever missing, the scanner
   falls back to regex patterns and HMMER-dependent cells report `NEEDS_HMMER_DOMTBLOUT`, not a failure.)

5. **Pre-flight check.**
   ```bash
   python -m mamey doctor
   ```

6. **Run the pipeline** on one or more antiSMASH result ZIPs. You need an antiSMASH result ZIP as
   input; Sapote-Mamey interprets antiSMASH output but does not run antiSMASH for you. Produce it with
   the web service at `antismash.secondarymetabolites.org` or a local install first.
   ```bash
   python mamey_run.py run --input-zip path/to/antismash_result.zip --outdir runs/
   ```

7. **(Optional) run the tests.** All fixtures ship in the release, so the suite runs in full
   (HMM-dependent behavior degrades to regex if you skipped step 4, but no tests are skipped for
   missing fixtures):
   ```bash
   python -m pytest -q
   ```

## Workspace root (non-the Developer or User machines)

The engine defaults its workspace root to a machine-specific path. On any other machine, export:

    export SAPOTE_WORKSPACE_ROOT=/path/to/workspace

`mamey.workspace_root.workspace_root()` resolves `SAPOTE_WORKSPACE_ROOT`, then `SAPOTE_ROOT`, then the historical default (v9.7.367 / DEC-02).
