# SOP-00 — Start Here / Choosing the Right Sapote/Mamey Path

## Purpose

This SOP helps the operator decide what Sapote/Mamey path to run after a file is uploaded. It prevents wasted time, wrong commands, and misleading interpretations.

## First question

Before running analysis, decide what kind of input was uploaded.

## Input classes

| Input shape | Meaning | First action |
|---|---|---|
| Raw antiSMASH ZIP with many regions | Full or draft genome antiSMASH output | `python -m mamey inspect <zip>` |
| Raw antiSMASH ZIP with one region | Single accession / reference BGC / small test | `python -m mamey inspect <zip>` and interpret warnings carefully |
| Sealed Mamey package | Previous run output | `python -m mamey validate <package_dir>` |
| BLASTP Hit Table CSV | Follow-up evidence from NCBI | `python -m mamey blastp-followup --hit-table <csv>` |
| BLASTP XML2 file | Proof-grade optional follow-up | Pair with hit table when possible |
| FASTA only | Candidate for BLASTP or intake support | Do not run Mamey directly unless command supports it |
| Spreadsheet/workbook | Prior run table or manual ledger | Inspect sheet names before interpreting |
| Patch packet ZIP | Development patch | Read README / manifest / diffs before applying |

## Standard decision tree

1. If it is an antiSMASH ZIP, run `inspect` first.
2. If `inspect` passes, run smoke mode before full/gold.
3. If it is a Mamey package, validate it instead of re-running.
4. If it is BLASTP output, parse and reprioritize, do not rerun Mamey.
5. If it is a patch packet, audit contents before applying.
6. If file type is unclear, list archive contents and classify.

## Required operator language

The assistant should say what the file appears to be before running commands:

- "This appears to be raw antiSMASH output."
- "This appears to be a sealed Mamey package."
- "This appears to be BLASTP result output."
- "This appears to be a patch handoff packet."

## Failure modes

| Failure | What to do |
|---|---|
| No region GBKs | Not parseable as antiSMASH intake |
| No KnownClusterBlast | Still parseable, but KCB evidence unavailable |
| Single region only | Treat as accession/reference/test, not full genome |
| Huge region count | Use ChatGPT-safe smoke and batching |
| Mac dotfiles present | Warn but ignore if real GBKs parse |
| Filename differs from internal accession | Use uploaded filename for `--input-zip`; internal accession can be strain label |

## Bug-hunt checks

1. `inspect` must classify raw antiSMASH vs Mamey package vs BLASTP results.
2. Single-region antiSMASH ZIPs must not trigger misleading full-genome failure language.
3. ChatGPT should never parse antiSMASH JSON manually when Mamey can inspect.
4. The command recommendation must match input type.
