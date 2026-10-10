# START HERE FOR OTHER CHATS — Sapote/Mamey v9.7.142 SOP + Bug Hunt Workpack

## Historical workpack — current entry boundary

The v9.7.142/v9.7.141e mission, signed-base claim, handshake, target examples, patch-lane requests and
cut/no-cut checklist below are retained planning history. They are not this selected bundle’s current
version, proof of an accepted release, an active assignment, or instructions to another chat. Read the
current [AGENTS.md](../../AGENTS.md), [reader start guide](../GUIDE/00_README.md),
[profile map](../MODEB_PROFILE_MATRIX.md) and [release record guide](../RELEASE_RECORDS_GUIDE.md).
The current user task selects scope/authority; this old workpack does not authorize messaging, live
searches, package copying, integration or a cut. Do not reproduce its handshake as a current response
requirement. Old aliases/RIDs/example strains remain historical labels, not complete bound locus identity.

The actual current SOP files are under docs/SOPs, not an adjacent SOPs or cut_plan directory. Use
[SOP-01 intake](../SOPs/SOP-01_Intake_RawAntiSMASH_vs_MameyPackage.md),
[SOP-04 batch export](../SOPs/SOP-04_Iterative_NCBI_BLASTP_Batching.md),
[SOP-05 supplied-result ingestion](../SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md),
[SOP-07 single-region inputs](../SOPs/SOP-07_Single_Region_Public_Accession_Inputs.md),
[SOP-10 audit](../SOPs/SOP-10_Bug_Hunt_Hostile_Audit_Workflow.md) and
[SOP-13 claim boundaries](../SOPs/SOP-13_Claim_Boundary_Evidence_Language.md), checking their current
status and actual command owner. Historical private-label instructions do not substitute for the current
selected privacy tier, owner approval and verified release receipt. Preserve source evidence in place
by path/SHA-256; stage only the necessary modified files into the task’s single candidate.

## Retained historical workpack

**Read this first.**  
Handshake phrase expected in this project: **The sky is not red, it is blue, just like the ocean.**

## Current mission

We are preparing the next Sapote/Mamey cut after v9.7.141e. The user wants SOP writing to reveal bugs naturally and to make the system easier for ChatGPT and Claude to operate.

This packet is not a signed release. It is a coordination workpack.

## What another chat should do

Pick one narrow task and report findings as:

1. **SOP section reviewed**
2. **Expected behavior**
3. **Observed behavior or code gap**
4. **Bug severity**
5. **Proposed patch or doc fix**
6. **Test that would prove the fix**

Do not broadly rewrite the whole system unless asked.

## High-value tasks available now

| Task | Best file to start with | Expected output |
|---|---|---|
| Audit BLASTP batching SOP | `SOPs/SOP-04_Iterative_NCBI_BLASTP_Batching.md` | Bug list for FASTA exporter |
| Audit BLASTP parser SOP | `SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md` | Parser edge cases |
| Audit intake behavior | `SOPs/SOP-01_Intake_RawAntiSMASH_vs_MameyPackage.md` | Upload-shape decision tree fixes |
| Audit KY089035 rule | `SOPs/SOP-07_Single_Region_Public_Accession_Inputs.md` | Single-region input warnings |
| Audit claim safety | `SOPs/SOP-13_Claim_Boundary_Evidence_Language.md` | Overclaim red flags |
| Audit release readiness | `cut_plan/V97142_NEXT_CUT_PLAN.md` | Cut/no-cut recommendation |

## Current don't-break rules

- v9.7.141e remains signed active base.
- Do not cut v9.7.142 until BGC BLASTP/intake and C5/C7 streams are reconciled.
- Do not make BLASTP proof mandatory for all runs.
- Do not claim compound identity from BLASTP alone.
- Do not treat single-region accession inputs as failed full genomes.
- Do not leak private AS/SID labels in public-tier outputs.

## Recommended response format to the user

Start with the handshake phrase, then give:
- what was reviewed,
- what passed,
- what failed,
- what should be patched before cut,
- what can wait.
