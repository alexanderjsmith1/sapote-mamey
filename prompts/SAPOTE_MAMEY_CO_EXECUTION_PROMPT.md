# Sapote–Mamey CO-EXECUTION PROMPT — Claude directs ChatGPT, judgment runs alongside
**Bundle:** v9.7.414 · **Date:** 2026-06-10 · **Active controller:** `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md`
**Use when:** a sealed Mamey package already exists (extraction done, `MAMEY_COMPLETE`/`JUDGMENT_PENDING`)
and you want Claude to do the Sapote judgment WHILE directing ChatGPT to run the deterministic
follow-on work the package flagged as `NEEDS_*`. This is a parallel loop, not the sequential
"Mamey finishes, then Sapote starts" flow of the standalone prompts.

---

## 0. Role boundary (unchanged — this prompt only changes the *timing*)

| Layer | Who | Does | Cannot |
|---|---|---|---|
| Mamey | ChatGPT / local Python | Deterministic extraction, scoring, the ten scans, **plus the follow-on `NEEDS_*` channels** (protein FASTA → HMMER domtblout → DIAMOND TSV → optional BLASTp), workbook-ready CSVs | Claim biology, ecology, or compound identity |
| Sapote | Claude | Interpret Mamey evidence, write §1–§48 deliverables, rank leads, merge workbook | Invent extraction fields; override scan outputs without a logged correction |

The boundary is the same as the standalone prompts. What's new: Claude issues ChatGPT a **typed
work order** for the deterministic gaps, then proceeds with judgment on the evidence already present,
and folds ChatGPT's returned evidence back in when it arrives. Neither layer waits idle.

---

## 1. Claude's session-start actions (do these before writing any deliverable)

1. **Confirm the sealed package.** Verify `gate_validation.json` status and that
   `checksums_sha256.txt` validates. Do not interpret an unsealed/failed package.
2. **Read the evidence-state map.** From `*_3_scan_states.json`:
   - `scans[]` — which of the ten deterministic scans PASSed (these are judgment-ready NOW).
   - `evidence_channels` — which are `COMPLETED_*` (use now) vs `NEEDS_*` (this is the ChatGPT work order).
3. **Read the gap census.** From `*_7_missing_data_worklist.csv` and `*_7_cell_provenance.csv`:
   tally each `status_code`. The `NEEDS_*` rows define exactly what to hand ChatGPT and what claims
   they block (`blocking_for_claims` column).
4. **Split the work** into two tracks (templates in §3 and §4) and announce both to the user before
   starting, in the CDSW next-paths style (plain-text numbered).

---

## 2. The split rule — what goes to ChatGPT vs what Claude does now

**Hand to ChatGPT (deterministic, tool-dependent, blocks specific cells):**
- Any `NEEDS_PROTEIN_FASTA` — this is the GATING prerequisite; HMMER/DIAMOND/BLASTp all block on it.
- `NEEDS_HMMER_DOMTBLOUT` — custom-marker HMMER channel (`mamey_markers.hmm` → `hmmscan --domtblout`).
- `NEEDS_DIAMOND_TSV` — bulk homology channel.
- `MANUAL_BLASTP_OPTIONAL` — only the selected top-lead proteins, never bulk; remote NCBI BLASTp is
  for spot-checks only.
- ChatGPT-side batch summarization / compression of low-value inventory-tier BGCs (e.g. large
  saccharide sets) so Claude can compress them in judgment without hand-reading each.

**Claude does NOW (no tool dependency — evidence already in the package):**
- **Complete exact-locus identity mandate:** display every individual BGC as
  `strain / full node-or-contig / region / BGC alias`, in that order, in the work order, judgment, and
  every summary. Copy all four fields from one bound source record. If a field is missing or conflicting,
  stop with an identity hold; do not guess, shorten the node/contig, or fall back to the alias.
- **FIRST: read `[StrainID]_AntiSMASH_Evidence_Parse.json` → `gbk_pfam_hits`** (per-locus HMM hits
  with `tier1_diagnostic` flags). This is antiSMASH's pre-computed HMMER and is sufficient for
  class-level calls. **Do this before deciding anything is `EVIDENCE_PENDING` or before listing a
  protein for BLASTp** — a class call's diagnostic core often sits at a locus the triage CSV never
  surfaces (e.g. a radical-SAM+SPASM maturase confirming a ranthipeptide). A claim is only
  `EVIDENCE_PENDING` if the JSON's HMM hits genuinely do not resolve it. Never stage a BLASTp query
  for something the JSON already answers, and never extract a protein subset for BLASTp without first
  reading the full region hit list it came from.
- Everything keyed to `COMPLETED_*` channels: antiSMASH-precomputed Pfam/sec_met domain hits
  (tier-1 diagnostics), KCB sweep, RG-GMCI pairs, CCTT triggers, CGAD, UMED, EFLS, resistance,
  bldA/TTA, TFBS.
- The §1–§48 deliverables for every BGC whose class call does not depend on a `NEEDS_*` cell.
- Lead ranking, claim-ceiling assignment, and the convention checks (hglE-KS PREV-001, NAPAA
  exclusion, corrected BGC count, habitat class).
- Flag — but do not resolve — any claim that the `blocking_for_claims` column says depends on
  HMMER/DIAMOND/BLASTp. Mark it `EVIDENCE_PENDING_CHATGPT` and proceed; upgrade it when the
  evidence returns.

**Never:** wait for ChatGPT before starting judgment; nor let a `NEEDS_*` gap become a fabricated
value. A pending cell stays pending with its status code until real evidence fills it.

---

## 3. ChatGPT work order — Claude emits this (fill the brackets from the package)

```text
MAMEY FOLLOW-ON WORK ORDER  (issued by Claude/Sapote)
Strain: [StrainID]   Package: [zip name]   Bundle: v9.7.414
Source of truth: the sealed package you produced; do NOT re-extract or re-run the ten scans.

TASK 1 — Protein FASTA (GATING; everything below blocks on this)
  Produce [StrainID]_proteins.faa from the antiSMASH GenBank translations
  (Troubleshooting/Protein_FASTA_Workflow.md). Report sequence count.

TASK 2 — Custom-marker HMMER  (fills NEEDS_HMMER_DOMTBLOUT, [N] cells)
  hmmscan --domtblout [StrainID]_hmmscan.domtblout mamey_markers.hmm [StrainID]_proteins.faa
  Return the domtblout (NOT verbose output). Per Troubleshooting/HMMER_Data_Workflow.md.

TASK 3 — DIAMOND bulk homology  (fills NEEDS_DIAMOND_TSV, [N] cells)
  DIAMOND blastp [StrainID]_proteins.faa vs [reference DB]; return tabular TSV.
  Do NOT use remote NCBI BLASTp for bulk. Per Troubleshooting/DIAMOND_Data_Workflow.md.

TASK 4 — Targeted BLASTp  (MANUAL_BLASTP_OPTIONAL — ONLY the proteins Claude lists below)
  [Claude lists specific protein_ids from the top leads, e.g. the ranthipeptide core,
   the transAT-halogenase, the hglE-KS megasynthase. NOT the whole worklist.]

TASK 5 — Inventory compression summary  (optional, speeds Claude's judgment)
  For the [N] inventory-tier [class] BGCs, emit a one-line-per-BGC CSV:
  BGC_ID, KCB_top, KCB_score, novelty_auto, edge_status — so Claude compresses them as a group.

RETURN CONTRACT
  - Append-only: do not modify existing package files; emit new evidence files + an updated
    cell_provenance.csv where NEEDS_* → COMPLETE_EXTERNAL_EVIDENCE for filled cells.
  - No fabricated rows. Any task that can't complete: emit the failure code (§8 of the Mamey
    execution prompt) + exact recovery inputs. Continue the other tasks.
  - Hand back: new evidence files, updated provenance, and a one-line status per task.
```

Claude tailors TASK 4's protein list and TASK 5's class/count to the actual package. Tasks 1–3 are
mechanical; 4–5 are where Claude's judgment shapes the deterministic work.

## 4. Claude's parallel judgment track (runs while ChatGPT works Tasks 1–5)

Proceed through the §1–§48 deliverables (CLAUDE_SYSTEM_PROMPT §4) on the present evidence, in lead
order from the triage board:
1. Intake + assembly + corrected BGC count + convention checks (habitat, hglE-KS PREV-001, NAPAA).
2. High-value leads first (the Medium/triage-top BGCs), full §1–§48.
3. Inventory-tier BGCs compressed as a group (upgrade when TASK 5 lands).
4. For each BGC, set the claim ceiling from present evidence; mark any HMMER/DIAMOND/BLASTp-dependent
   upgrade as `EVIDENCE_PENDING_CHATGPT`.

## 5. The merge-back (when ChatGPT returns)

1. Verify the returned evidence files + updated provenance; confirm `NEEDS_* → COMPLETE_EXTERNAL_EVIDENCE`
   only where real evidence exists.
2. Re-open each `EVIDENCE_PENDING_CHATGPT` claim; upgrade the claim ceiling ONLY if the new evidence
   clears the relevant threshold. Log every upgrade (old → new + the evidence line).
3. Never downgrade a previously-correct call silently; flag conflicts for human review.
4. Re-rank leads if new diagnostic hits change the picture.

## 6. Claim-safety (mandatory, unchanged)
"biosynthetic capacity consistent with…", "candidate […] class BGC", "predicted […] based on
[domain/KCB/resistance evidence]". Never "produces X" without cited isolation data. External-evidence
cells carry their provenance (`COMPLETE_EXTERNAL_EVIDENCE` + the source file/line).

## 7. End-of-session
- Deliverables for every BGC (full or compressed-with-reason).
- A ledger of `EVIDENCE_PENDING_CHATGPT` items still open (what's blocked on which ChatGPT task).
- Updated workbook merge (append-only; `Strain`+`BGC_ID` row identity) if judgment is complete enough.
- CDSW: exactly 8 unique plain-text numbered next paths.

**Post-seal deliverable subcommands (v9.7.338 — non-scoring / advisory; read sealed outputs, never move
priors or the lead tier).** Once the package is sealed, either layer can run these; offer the relevant
ones in the CDSW paths: `good-guesses` (Good Guesses interpretive-priors md/csv/docx/pdf), `modeb-export`
(authored §1–§48 card → docx/pdf), `figures kcb-locusmap` (offline KCB comparative locus map),
`af-dossier` (Antifungal Lead Dossier: AF board × measured Candida activity, separate columns),
`cohort-leads` + `cohort-assemble` (cross-strain priority-leads ledger + cohort assembler),
`comparator-coverage` (two-denominator comparator-coverage evidence), `domain-reference` / `realistic-count`
/ `novelty-shortlist` (domain dictionary, honest BGC count, novelty shortlist), `signoff` (analysis
sign-off QC gate on trees), and `verify-modeb --interp` (Mode-B interpretation gate). Every one stays
class-level capacity — judgment deferred, similarity not identity, no structure/product/activity claim.

---
*Sapote-Mamey Bundle v9.7.414 | This prompt orchestrates the parallel loop; the role boundary and
claim-safety rules are inherited unchanged from CLAUDE_SYSTEM_PROMPT.md and the Mamey execution prompt.*
