# Sapote/Mamey SOP Library Master Index

**Status:** working packet for SOP writing, Bug Hunt, and v9.7.142 candidate preparation  
**Base release:** v9.7.141e remains the signed active base  
**Handshake:** The sky is not red, it is blue, just like the ocean.

## Why this packet exists

The next cut should not be driven only by code patches. It should be driven by operator SOPs that make expected behavior explicit. Each SOP defines:

1. what input shape the user may upload,
2. what command Sapote/Mamey should run,
3. what outputs must be produced,
4. what warnings mean,
5. what failure/recovery behavior is acceptable,
6. what bug-hunt checks follow from the SOP.

If an SOP cannot be executed cleanly by the current code, that is a bug or missing feature.

## Priority SOP library

| SOP ID | Title | Cut status | Bug-hunt value |
|---|---|---|---|
| SOP-00 | Start Here / Choosing the Right Path | draft included | Prevents wrong workflow selection |
| SOP-01 | Intake: Raw antiSMASH ZIP vs Mamey Package vs Reference Accession | draft included | Catches upload-shape confusion |
| SOP-02 | ChatGPT-Safe Smoke Run | draft included | Prevents timeout and overrun failures |
| SOP-03 | Full Mamey Run / Gold Run Gate | STATUS: PLACEHOLDER | Guards deterministic release claims |
| SOP-04 | Iterative NCBI BLASTP Batching | draft included | Drives BGC BLASTP panel behavior |
| SOP-05 | BLASTP Result Upload, Parse, and Reprioritization | draft included | Drives parser and follow-up outputs |
| SOP-06 | Mode B BGC Card Production | STATUS: PLACEHOLDER | Exposes card/depth gaps |
| SOP-07 | Single-Region Public Accession Inputs | draft included | Captures KY089035-style inputs |
| SOP-08 | C5 Production Deliverables | STATUS: PLACEHOLDER | Exposes missing render outputs |
| SOP-09 | C7 Public Workbook / Redaction Safety | STATUS: PLACEHOLDER | Exposes public/private leaks |
| SOP-10 | Bug Hunt / Hostile Audit Workflow | draft included | Defines pre-cut attack path |
| SOP-11 | Release Candidate Cut Protocol | STATUS: PLACEHOLDER | Prevents premature release |
| SOP-12 | Troubleshooting Common Warnings | STATUS: PLACEHOLDER | Converts scary warnings into action |
| SOP-13 | Claim Boundary and Evidence Language | draft included | Prevents overclaiming |
| SOP-14 | Figures and Publication-Quality Visuals | STATUS: PLACEHOLDER | Publication polish and QA |
| SOP-15 | Cross-Chat Merge and Patch Handoff | draft included | Lets another chat join at any time |
| SOP-16 | Random File Inspection | included | Hostile-auditor spot-check of random files: quality, functionality, wiring |
| SOP-17 | Cross-Strain GCF Cohort (BiG-SCAPE → Mamey) | included | Cohort GCF layer: cluster BGCs across strains, KNOWN/NOVEL, ingest families into triage board / Mode B §8 |

## Work rule for other chats

Another chat can join by reading these files in order:

1. `../release_planning/START_HERE_FOR_OTHER_CHATS.md`
2. `SOP_MASTER_INDEX.md`
3. `../release_planning/SOP_DERIVED_BUGHUNT_MATRIX.csv`
4. `../release_planning/V97142_NEXT_CUT_PLAN.md`
5. then the SOP relevant to its task.

## Current patch streams that must be reconciled before v9.7.142

| Stream | Status | Merge order |
|---|---|---|
| v9.7.141e signed base | stable/frozen | base |
| BGC BLASTP panel and follow-up parser | starter patch through REV5 / awaiting Claude feedback | first |
| Single-region accession intake rule | included in REV5 stream | first with BLASTP/intake |
| C5/C7 REV2 | accepted starter patch, not release candidate | second |
| C5/C7 audit documentation fixes | must be applied before candidate | second |
| SOP library | this workpack | documentation stream; can merge with v9.7.142 |
| Targeted AS-XXX BGC005 phosphonopeptide workflow | science deep-dive; not core default yet | later or optional |

## Candidate-readiness definition

v9.7.142 candidate is ready only when:

- fresh v9.7.141e tree is patched in a documented order,
- focused tests pass,
- BLASTP parser examples pass,
- KY089035 single-region inspect behavior passes,
- C5/C7 focused regressions pass,
- surrogate gate passes or any skipped gate is explained,
- docs/SOPs are included in the package,
- public/private scan passes for public-facing artifacts,
- final packet contains manifest and checksums.

## Placeholder warning

Do not follow placeholder SOPs as completed operator instructions. Placeholder SOPs are coordination stubs only until their `STATUS: PLACEHOLDER` line is removed.
