# Read a citation-compact report

This page explains what the citation-compact outputs contain and how far to trust each part. To make them, see [Make a compact citation report](CITATION_COMPACT_MODE.md). A package is the folder a run writes; a lead is one ranked region in its triage board. Terms are in the [glossary](GLOSSARY.md).

## What you get

A run with `--token-budget citation-compact` writes these files in the package folder:

| File | Holds |
|---|---|
| `Citation_Ledger.csv` and `.json` (package root) | One row per citation: ID, label, status, what it supports. |
| `citation_compact/<strain>_lead_table_citation_compact.md` | The lead table. |
| `citation_compact/<strain>_technical_report_citation_compact.md`, `..._bench_guide_...`, `..._layperson_guide_...` | Three short reports. Each ends with the same lead table. |
| `citation_compact/Literature_Search_WorkOrder.md` and `.json` | Searches still to do. The tool does not run them. |
| `citation_compact/CITATION_COMPACT_QA.json` | The structural check result. |

## Where the leads come from

The leads come from the first file, in sorted order, that matches `*_4_triage_board.csv` in the package root. If none matches, there are no leads. If several match, only the first is read, so remove the extra boards from a working copy before you run again.

The three reports fill their opening fields from the first lead only. That lead is the first row in the board, not necessarily the highest priority. Read the full lead table at the end of each report.

## Read each lead with its full identity

The table shows a locus as `stable_locus`, which is the first non-empty value among the board's assembly locator, node ID and contig columns. It does not check the region. A lead ID or BGC label may be a generated fallback. Neither proves that the lead matches a specific region.

Before you quote a lead, copy the full **strain / full node-or-contig / region / BGC alias** from the package inventory.

## What the text means

- The detection method, assay, decision threshold and plain-language phrases in the bench and layperson reports are fixed generic wording. They are not recommendations for your strain, and no experiment has been done. Check them against your evidence before you share a report.
- The lead-table file opens with a placeholder table whose cells read `{{ ... }}`. That is a template. The filled rows follow under the "Rendered Lead Table" heading. Read those rows.
- The ledger keeps each citation's ID, label, status and supports. It drops DOI, PMID, URL, MIBiG and accession values. Take those from your original evidence.
- Every lead gets the antiSMASH 8.0 and MIBiG 4.0 method and database labels. The emitter adds them to each lead automatically, including a lead with no reference match. They are method provenance for the bundle, not a record that this method or database was used for that lead. Check the run's own records, such as `manifest.json` and the KnownClusterBlast columns, for what was actually run. The labels do not support a lead's literature claim. See the status words in [the provenance block](CITATION_COMPACT_MODE.md#citation-compact-provenance-and-citation-status).

## The QA status

`CITATION_COMPACT_QA.json` has `status` set to `PASS_STRUCTURE` or `WARN`. `PASS_STRUCTURE` means two structural checks found no error: every priority lead has well-formed citation fields, and the global caveat text appears at most once across the reports. It does not check that a DOI is correct, that a citation supports a lead, that the locus identity is complete, or that an assay suits the strain. A literature review and your own sign-off are separate steps.

`status` is `WARN` when either check found a problem. The package validator accepts `WARN`. Read `coverage_errors` and `caveat_errors` in the QA file.

## If an output is missing or wrong

The files are written one after another. If a later write fails, earlier files stay written and the run records a WARN or ERROR in `run_phase_receipts.jsonl` while the rest of the run finishes. See [Recovery and limits](reader/04_RECOVERY_AND_LIMITS.md).

To regenerate, run `run` again with a new `--outdir`, as in [Make a compact citation report](CITATION_COMPACT_MODE.md). Compare the new files with the old package. Do not rewrite a package you have already sealed or shared.
