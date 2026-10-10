# Sapote/Mamey SOP Library Master Index

**Status:** SOP library index. SOP-03, 06, 08, 09, 11, 12 and 14 were never written; they now point to the
documents that hold those procedures.  
**Scope:** current procedure directory plus a historical v9.7.142 planning record below. No handshake or historical cut plan expands the current task. Start with [the current docs index](../../CURRENT_DOCS_INDEX.md), [the user task router](../USER_TASK_ROUTER.md) and [the shared assistant contract](../../AGENTS.md).

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
| SOP-02 | Capped-session gold run (historical filename retained) | draft included | Prevents timeout and overrun failures |
| SOP-03 | Full Mamey Run / Gold Run Gate | POINTER (never written) | Guards deterministic release claims |
| SOP-04 | Iterative NCBI BLASTP Batching | draft included | Drives BGC BLASTP panel behavior |
| SOP-05 | BLASTP Result Upload, Parse, and Reprioritization | draft included | Drives parser and follow-up outputs |
| SOP-06 | Mode B BGC Card Production | POINTER (never written) | Exposes card/depth gaps |
| SOP-07 | Single-Region Public Accession Inputs | draft included | Captures KY089035-style inputs |
| SOP-08 | C5 Production Deliverables | POINTER (never written) | Exposes missing render outputs |
| SOP-09 | C7 Public Workbook / Redaction Safety | POINTER (never written) | Exposes public/private leaks |
| SOP-10 | Bug Hunt / Hostile Audit Workflow | draft included | Defines pre-cut attack path |
| SOP-11 | Release Candidate Cut Protocol | POINTER (never written) | Prevents premature release |
| SOP-12 | Troubleshooting Common Warnings | POINTER (never written) | Converts scary warnings into action |
| SOP-13 | Claim Boundary and Evidence Language | draft included | Prevents overclaiming |
| SOP-14 | Figures and Publication-Quality Visuals | POINTER (never written) | Publication polish and QA |
| SOP-15 | Cross-Chat Merge and Patch Handoff | draft included | Lets another chat join at any time |
| SOP-16 | Random File Inspection | included | Hostile-auditor spot-check of random files: quality, functionality, wiring |
| SOP-17 | Cross-Strain GCF Cohort (BiG-SCAPE → Mamey) | included | Within-run family similarity, exact source/run joins and receipt-backed exports; no KNOWN/NOVEL labels in cohort-only mode |

## Historical coordination reading order (v9.7.142)

The following reading order and patch streams are retained as planning history, not current startup requirements. Use current documentation first; release work requires the current owner cut process.

Another chat can join by reading these files in order:

1. `../release_planning/START_HERE_FOR_OTHER_CHATS.md`
2. `SOP_MASTER_INDEX.md`
3. `../release_planning/SOP_DERIVED_BUGHUNT_MATRIX.csv`
4. `../release_planning/V97142_NEXT_CUT_PLAN.md`
5. then the SOP relevant to its task.

## Historical patch streams before v9.7.142

| Stream | Status | Merge order |
|---|---|---|
| v9.7.141e signed base | stable/frozen | base |
| BGC BLASTP panel and follow-up parser | starter patch through REV5 / awaiting Claude feedback | first |
| Single-region accession intake rule | included in REV5 stream | first with BLASTP/intake |
| C5/C7 REV2 | accepted starter patch, not release candidate | second |
| C5/C7 audit documentation fixes | must be applied before candidate | second |
| SOP library | this workpack | documentation stream; can merge with v9.7.142 |
| Targeted AS-XXX BGC005 phosphonopeptide workflow | science deep-dive; not core default yet | later or optional |

## Historical candidate-readiness definition

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

## Pointer and draft status

The POINTER pages route to existing current procedures and are not separate incomplete execution recipes. The draft SOPs need their claims checked against the selected bundle and task. Removal of a placeholder marker does not establish implementation, test completion or release acceptance.
