# START HERE FOR OTHER CHATS — Sapote/Mamey v9.7.142 SOP + Bug Hunt Workpack

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
