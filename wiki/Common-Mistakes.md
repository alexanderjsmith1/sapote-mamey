# Common Mistakes — Sapote–Mamey

A concise reference for the errors collaborators and new users encounter most often.

---

## 1. Uploading the wrong ZIP type

**Symptom:** `No antiSMASH regions found in input — bare assembly` or `MAMEY_FAILED, raw_bgcs 0`

**Cause:** You uploaded a raw genome assembly (FASTA/NCBI download) instead of an antiSMASH output ZIP.

**Fix:** Run antiSMASH 8 on your genome first (`https://antismash.secondarymetabolites.org`), download the results ZIP, then run Mamey on that ZIP.

```bash
# Wrong — raw NCBI download
python mamey_run.py run --input-zip GCA_009862675.fna.gz

# Right — antiSMASH output
python mamey_run.py run --input-zip AS-XXX_antismash_results.zip
```

---

## 2. Stale antiSMASH exports

**Symptom:** Missing KCB scores, blank `KCB_top` columns, or `KCB/RiQ parser found no antiSMASH JSON/TXT evidence`

**Cause:** The antiSMASH ZIP was exported from an old run (pre-v7) or the internal JSON files were stripped.

**Fix:** Re-run antiSMASH 8+ and download the full output ZIP (not just the GBK files). The ZIP must contain `knownclusterblast/*.txt` and ideally the full `*.json` results file.

---

## 3. Accession-only strain labels

**Symptom:** Warning: `Strain label 'NZ_QHHY00000000.1' is an NCBI accession (fallback). Prefer a strain name.`

**Cause:** You used an NCBI accession as the `--strain` argument. Accessions propagate into every deliverable file name, report header, and workbook row — making the output hard to read and cross-reference.

**Fix:** Supply a meaningful strain name via `--strain`:

```bash
# Less ideal
python mamey_run.py run --strain NZ_QHHY00000000.1 --input-zip NZ_QHHY.zip

# Better
python mamey_run.py run --strain AS-XXX --input-zip NZ_QHHY.zip \
    --taxonomy "Streptomyces sp." --source "bee-associated"
```

---

## 4. Missing JSON files (bounded evidence off)

**Symptom:** `ijson✗ bounded→TXT-only` in the dependency banner; KCB scores present but RiQ scores blank.

**Cause:** `ijson` is not installed and the antiSMASH JSON is too large to load fully. Mamey falls back to TXT-only clusterblast parsing, which gives KCB but not RiQ.

**Fix (option A):** Install ijson — it ships vendored in the bundle:
```bash
pip install ijson
# or use the offline wheel in offline_deps/
```

**Fix (option B):** Use `--json-evidence off` explicitly if you only need KCB (TXT-only is a supported mode):
```bash
python mamey_run.py run --json-evidence off --input-zip ...
```

---

## 5. Running Mamey against a v1.2 workbook with `--master`

**Symptom:** `[BLOCKED] --master target is a Schema-v1.2 workbook`

**Cause:** You pointed `--master` at a workbook built by `tools/build_master.py` (the legacy cohort builder). The canonical `--master` writer uses a different sheet schema and will silently drop sheets if forced onto the v1.2 workbook.

**Fix:** Bank the strain using the ingest path instead:
```bash
python tools/ingest_package.py --package runs/AS-XXX/package --ww WWGP0000000 --merge --banked-dir cohort
python tools/build_master.py --workbook Sapote-Mamey_Master.xlsx
```

---

## 6. Expecting a finished analysis from a PASS package

**Symptom:** Package says `MAMEY_COMPLETE` but there are no Mode B cards, no compound interpretations, no ecology section.

**Cause:** Mamey is the **extraction layer only** — inventory, scans, scores, and evidence. The interpretive deliverables (Mode B, DAPR, claim-safe ecology, bench/layperson guides) are the separate **Sapote judgment** step.

**Fix:** Open `OPEN_ME_FIRST.html` (or `START_HERE.md`) inside the package and follow the instructions to trigger the judgment layer:
> Upload `manifest.json` to Claude and type: **"Run full Sapote analysis on \<strain\>"**

---

## 7. Taxonomy as `.` or blank organism

**Symptom:** Display name shows `. strain AS-XXX` or organism field is a bare dot.

**Cause:** The antiSMASH GBK files for some private strains deposit `ORGANISM  .` (no genus), which Mamey normalises to avoid propagating a literal dot.

**Fix:** Always supply `--taxonomy` explicitly:
```bash
python mamey_run.py run --strain AS-XXX --taxonomy "Streptomyces sp." --input-zip ...
```

---

## 8. `openpyxl` not installed

**Symptom:** `openpyxl✗ REQUIRED for workbooks` in the dependency banner; no `*_5_workbook.xlsx` in the package.

**Fix:**
```bash
pip install openpyxl
# offline: pip install --no-index offline_deps/openpyxl-*.whl
```
Run `python mamey_run.py doctor` to check all dependencies at once.

---

## 9. Figures not rendered

**Symptom:** `BRIEF_SKIPPED_TIMEOUT.md` or `NO_FIGURES_RENDERED.md` in the package; no PDF strain brief.

**Cause (A):** `numpy` and/or `matplotlib` are not installed.
**Cause (B):** The font-manager cache build timed out on first render (common in restricted environments).

**Fix (A):** Install figure dependencies:
```bash
pip install numpy matplotlib
```

**Fix (B):** Re-render after the cache builds:
```bash
python mamey_run.py render-figures --package runs/AS-XXX/package
```
Or increase the timeout:
```bash
MAMEY_RENDER_TIMEOUT_S=300 python mamey_run.py run ...
```

---

## 10. `mamey doctor` — run this first

If you are new to the bundle or hit an unexpected error, run the pre-flight check before anything else:

```bash
python mamey_run.py doctor
```

It checks Python version, all dependencies, write permissions, bundle integrity, and antiSMASH ZIP detection in the current directory — and tells you exactly what to fix.

---

## 11. pytest not installed (cut gates blocked)

**Symptom:** `FATAL: public-tier unpublished-ID invariant FAILED` during `make_public_tier.sh`, or `No module named pytest` during version cuts.

**Cause:** The cut gates and the 1540-test safety suite require pytest (+ pluggy + iniconfig). These are not bundled because they're dev dependencies, but they're essential for cutting releases.

**Fix:** Download the three wheels from PyPI on any networked machine and upload them into the chat:
```bash
# On a networked machine:
pip download pytest pluggy iniconfig -d wheels/
# Then upload the 3 files into the Claude/ChatGPT session
```
Installation in the session takes under 2 minutes. See `PREREQUISITES.md` and `CUT_PROTOCOL.md` for details.

---

*· Sapote–Mamey v9.7.319*
