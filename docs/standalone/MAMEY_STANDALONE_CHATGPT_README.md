# Mamey v1.9.152 Standalone ChatGPT Bundle

**Purpose.** This bundle makes Mamey usable as a self-contained ChatGPT batch workflow for uploaded antiSMASH ZIPs. It is a practical execution package: Python performs extraction, workbook writing, scan-state accounting, validation, checksums, and ZIP packaging; the ChatGPT/Sapote-style judgment layer performs narrative Mode B interpretation, literature synthesis, wet-lab planning, and reader-facing PDFs when requested.

## What "standalone" means here

Mamey v1.9.152 is standalone **inside ChatGPT** when the user uploads this bundle plus antiSMASH ZIPs. The workflow does not depend on a previously installed Mamey package or on hidden project state. The local `mamey_run.py` launcher forces this bundle's `mamey/` package to be used first.

It is not a full external bioinformatics installation. ChatGPT can run included Python code and use files that are uploaded into the session. It cannot assume BLAST, HMMER, antiSMASH, Prodigal, Prokka, or internet access unless those outputs or executables are explicitly present in the uploaded files/environment.

## What works well in ChatGPT

- antiSMASH ZIP intake and region-GBK parsing.
- KCB/TXT evidence extraction without opening large antiSMASH JSON files.
- Corrected BGC count, edge/fragmentation review, depth-floor routing, and auto-triage priors.
- Ten source-derived scan families when their evidence is present in antiSMASH/GBK/TXT outputs.
- Persistent master workbook updates across a batch.
- Per-strain package creation with manifest, validation, checksums, issue log, and project-memory alias.
- Batch continuation: usually 1–3 strains per pass for extraction; judgment/Mode B can continue in later batches.

## What is intentionally limited

- Mamey does not identify exact compounds from antiSMASH labels, KCB hits, or m/z-like handles alone.
- Mamey does not perform new BLAST/HMMER searches unless the necessary tools and databases are provided.
- Mamey does not prove BGC-level activity without metabolomics, fractionation, purified-compound, genetic, or other orthogonal evidence.
- A fresh `--mode gold` extraction validates as `MAMEY_COMPLETE` when all BGCs have a depth-floor assignment. Mode B cards and ledger entries are added by the Sapote judgment layer in a separate Claude session.

## Recommended ChatGPT batch size

- **Extraction/workbook pass:** 1–3 antiSMASH ZIPs per batch.
- **Standard judgment:** process the triage board plus all depth-floor BGCs in batches.
- **Archive/gold judgment:** full Mode B for every BGC; always batch large strains instead of reducing depth.

## Minimal command

```bash
python mamey_run.py run \
  --strains AS-XXX.zip AS-XXX.zip AS-XXX.zip \
  --master mamey_master.xlsx \
  --mode gold \
  --taxonomy "Kitasatospora sp.|Pseudonocardia sp.|Streptomyces sp." \
  --source "bumblebee|attine fungal garden|bee-associated"
```

## Required outputs from a ChatGPT extraction batch

1. Updated master workbook.
2. Per-strain complete package ZIPs.
3. Batch summary table/CSV/Markdown.
4. Combined batch-output ZIP.
5. A short status note distinguishing extraction completion from judgment completion.

## Status language

Use precise status labels:

- `MAMEY_COMPLETE`: extraction package is complete; all BGCs have depth-floor assignments; package is ready for Sapote judgment. This is the normal completion state for a ChatGPT extraction pass.
- `MAMEY_FAILED`: a required extraction gate failed (file presence, RGGMCI, or gold completeness check); fix the issue and reprocess.
- `MAMEY_DEFERRED`: intentionally assigned to a later batch; must be named in the deferred ledger with a reason.
- `MAMEY_SKIPPED`: excluded by user instruction; no action required.
- `PASS`: extraction and judgment package are fully complete (rare; only after a Sapote full-run judgment pass confirms all BGC Mode B cards are written).

**Legacy note:** older packages may show `PASS_EXTRACTION_JUDGMENT_PENDING`; this status was retired in v1.9.7. Treat any complete extraction package with this label as `MAMEY_COMPLETE`.

