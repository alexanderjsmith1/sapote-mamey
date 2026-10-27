# Retained SOP-library planning record

Historical record from `docs/SOPs/SOP_MASTER_INDEX.md`. Use the [current SOP index](../SOPs/SOP_MASTER_INDEX.md) for procedures. The original body follows; Markdown links were adjusted for this location. Historical paths in code text retain their original SOP-directory context. Examples with incomplete locus identifiers are historical and are not live source bindings.

# Sapote/Mamey SOP Library Master Index

**Status:** SOP library index. SOP-03, 06, 08, 09, 11, 12 and 14 were never written; they now point to the
documents that hold those procedures.  
**Scope:** current procedure directory plus a historical v9.7.142 planning record below. No handshake or historical cut plan expands the current task. Start with [the current docs index](../../CURRENT_DOCS_INDEX.md), [the user task router](../USER_TASK_ROUTER.md) and [the shared assistant contract](../../AGENTS.md).

## Find the procedure for your task

Choose a linked SOP below. A POINTER page takes you to the maintained procedure; an included
draft still needs to be checked against your selected bundle and task. Use each procedure to
identify inputs, commands, expected outputs, warnings and recovery before starting the selected
operation. If the current code cannot perform a documented step, retain the error or missing
capability and report it to the procedure owner.

The original v9.7.142 coordination plan follows the directory. Use it to understand that
workpack's history; the current task router and owning procedures supply today's entry route.

## Priority SOP library

| SOP ID | Title | Page status | Use it for |
|---|---|---|---|
| [SOP-00](../SOPs/SOP-00_Start_Here_Choosing_Path.md) | Start Here / Choosing the Right Path | draft included | Prevents wrong workflow selection |
| [SOP-01](../SOPs/SOP-01_Intake_RawAntiSMASH_vs_MameyPackage.md) | Intake: Raw antiSMASH ZIP vs Mamey Package vs Reference Accession | draft included | Catches upload-shape confusion |
| [SOP-02](../SOPs/SOP-02_ChatGPT_Safe_Smoke_Run.md) | Capped-session gold run (historical filename retained) | draft included | Reduced-output profile; inspect the evidence/runtime tradeoff |
| [SOP-03](../SOPs/SOP-03_Full_Mamey_Run_Gold_Run_Gate.md) | Full Mamey Run / Gold Run Gate | POINTER (never written) | Guards deterministic release claims |
| [SOP-04](../SOPs/SOP-04_Iterative_NCBI_BLASTP_Batching.md) | Iterative NCBI BLASTP Batching | draft included | Drives BGC BLASTP panel behavior |
| [SOP-05](../SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md) | BLASTP Result Upload, Parse, and Reprioritization | draft included | Drives parser and follow-up outputs |
| [SOP-06](../SOPs/SOP-06_Mode_B_BGC_Card_Production.md) | Mode B BGC Card Production | POINTER (never written) | Exposes card/depth gaps |
| [SOP-07](../SOPs/SOP-07_Single_Region_Public_Accession_Inputs.md) | Single-Region Public Accession Inputs | draft included | Captures KY089035-style inputs |
| [SOP-08](../SOPs/SOP-08_C5_Production_Deliverables.md) | C5 Production Deliverables | POINTER (never written) | Exposes missing render outputs |
| [SOP-09](../SOPs/SOP-09_C7_Public_Workbook_Redaction_Safety.md) | C7 Public Workbook / Redaction Safety | POINTER (never written) | Exposes public/private leaks |
| [SOP-10](../SOPs/SOP-10_Bug_Hunt_Hostile_Audit_Workflow.md) | Bug Hunt / Hostile Audit Workflow | draft included | Defines pre-cut attack path |
| [SOP-11](../SOPs/SOP-11_Release_Candidate_Cut_Protocol.md) | Release Candidate Cut Protocol | POINTER (never written) | Prevents premature release |
| [SOP-12](../SOPs/SOP-12_Troubleshooting_Common_Warnings.md) | Troubleshooting Common Warnings | POINTER (never written) | Converts scary warnings into action |
| [SOP-13](../SOPs/SOP-13_Claim_Boundary_Evidence_Language.md) | Claim Boundary and Evidence Language | draft included | Prevents overclaiming |
| [SOP-14](../SOPs/SOP-14_Figures_Publication_Quality_Visuals.md) | Figures and Publication-Quality Visuals | POINTER (never written) | Publication polish and QA |
| [SOP-15](../SOPs/SOP-15_Cross_Chat_Merge_and_Patch_Handoff.md) | Cross-Chat Merge and Patch Handoff | draft included | Lets another chat join at any time |
| [SOP-16](../SOPs/SOP-16_Random_File_Inspection.md) | Random File Inspection | included | Hostile-auditor spot-check of random files: quality, functionality, wiring |
| [SOP-17](../SOPs/SOP-17_CrossStrain_GCF_Cohort.md) | Cross-Strain GCF Cohort (BiG-SCAPE → Mamey) | included | Within-run family similarity, exact source/run joins and receipt-backed exports; no KNOWN/NOVEL labels in cohort-only mode |

## Historical coordination reading order (v9.7.142)

The following reading order and patch streams are retained as planning history, not current startup requirements. Use current documentation first; release work requires the current owner cut process.

Another chat can join by reading these files in order:

1. `retired_458/release_planning/START_HERE_FOR_OTHER_CHATS.md`
2. `SOP_MASTER_INDEX.md`
3. `retired_458/release_planning/SOP_DERIVED_BUGHUNT_MATRIX.csv`
4. `retired_458/release_planning/V97142_NEXT_CUT_PLAN.md`
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
