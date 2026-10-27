# Sapote-Mamey rules reference
<a id="sapote-mamey-all-in-one-bundle-monolith"></a>

**Monolith content version:** vetted against bundle v9.7.6; spot-vetted against bundle v9.7.439 for retired doctrine and dangling references.
> **Scope and precedence.** Operational startup is governed by `AGENTS.md` and `docs/ASSISTANT_GOVERNANCE.md`; they take precedence over this document. The task the user asked for sets the scope: reading this file never expands a review into a run, a full-suite authoring job, or a release. A version stamp at the top records version synchronization, not a full content review.

**Note:** the monolith is the analytical design reference (it was formerly called the parent design controller); its content is reviewed at major checkpoints, not bumped every patch. It is intentionally tracked separately from the engine/bundle version (for the authoritative live versions see CITATION.cff / pyproject.toml / mamey/__init__.py — this document does not restate them, because a restated version number rots silently). Concrete code descriptions (including §-1.17) require comparison with their selected current owners before use; this historical body and its version stamps do not guarantee that comparison has occurred.
**Project:** Multi-habitat actinomycete BGC discovery and manuscript support  
**Scope:** Any actinomycete or bacterial collection with antiSMASH output. Reference project covers isolates from four [Habitat] categories; the workflow is not restricted to these categories.  
**Core protocols:** Mamey deterministic extraction/scoring kernel + Sapote interpretive judgment layer + Workbook Contract + Batch Controller + Resume/Checkpoint Protocol + CDSW + Triage First + LC-MS Chemical Handle Module + Reader-Facing Front Page and Briefing Package + CCTT + CGAD + Resistance + bldA/TTA + RG-GMCI + FLBR + UMED + EFLS + DKP-CDPS + Linear Polyether Ionophore Detection + PKS Stereochemistry Reasoning + Output Registry (§54) + EFLS Constellation Reporting (§55) + Known-Outcome Benchmarking (§56) + Per-Class Constellation Sub-Grades (§57)  
**Primary use:** an analytical reference for designing and reviewing interpretation. Start a session from [AGENTS.md](../AGENTS.md). For a current task, use [Choose a task](USER_TASK_ROUTER.md); for a saved package, use [Reading your results](READING_YOUR_RESULTS.md). The [large-reference reading guide](GUIDE/07_LARGE_REFERENCE_ENTRY.md) connects this design history to current profiles, metrics and source owners. Use the contents below to explore the retained designs and examples.



---



## Read this reference by task

This page retains analytical rules and their unresolved policy choices. Start execution from [AGENTS.md](../AGENTS.md), choose deliverables from [the deliverable contract](DELIVERABLE_CONTRACT.md), and select Mode B depth from [the profile matrix](MODEB_PROFILE_MATRIX.md). Use [the task router](USER_TASK_ROUTER.md) for commands. Scientific adoption and release remain separate decisions.

Release bridges, session scripts, old layouts and validation histories are collected in [one history page](history/MONOLITH_DESIGN_HISTORY.md). The rule tables and owner-held policy text remain unchanged below.

# SECTION -2 — v9.2 Bundle Hardening Patch / Release Bridge

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section--2--v92-bundle-hardening-patch--release-bridge).

## -2.0 Purpose

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-20-purpose).

## -2.1 Historical parent-controller design

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-21-historical-parent-controller-design).

## -2.2 Requirement status labels

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-22-requirement-status-labels).

## -2.3 Repo synchronization gate

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-23-repo-synchronization-gate).

## -2.4 Execution profiles

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-24-execution-profiles).

## -2.5 Accession support boundary

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-25-accession-support-boundary).

## -2.6 Stable project-state file

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-26-stable-project-state-file).

## -2.7 Idempotent rerun and rebuild policy

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-27-idempotent-rerun-and-rebuild-policy).

## -2.8 Derived prompt set required for the bundle

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-28-derived-prompt-set-required-for-the-bundle).

## -2.9 Minimal test matrix before release

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-29-minimal-test-matrix-before-release).

## -2.10 Release profile labels

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-210-release-profile-labels).

## -2.11 Immediate bundle update order

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-211-immediate-bundle-update-order).

# SECTION -1 — Bundle Kernel / All-in-One Replacement Layer

## -1.0 Purpose

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-10-purpose).

## -1.1 Two-layer architecture

| Layer | Name | Role | Claim boundary |
|---|---|---|---|
| Layer 1 | **Mamey deterministic kernel** | Extracts and scores antiSMASH-derived evidence into stable machine-readable tables. Runs fixed scans and validates workbook fields. | May report coordinates, counts, scan hits, formula-derived scores, and status flags. Must not make unsupported product-identity or ecological claims. |
| Layer 2 | **Sapote interpretation layer** | Reads Mamey outputs and writes candidate cards, Mode B interpretation, literature context, wet-lab planning, and reader reports. | May interpret evidence using claim-safe language. Must cite which Mamey fields support each claim and must not override extraction outputs without logging a correction. |

**Non-negotiable:** extraction and judgment are separate acts. If a value belongs in a workbook, CSV, manifest, or scan state, Mamey is the source of truth. If a statement says what the value means biologically or experimentally, Sapote is the interpretation layer and must cite the deterministic evidence source.

## -1.2 Standard bundle run modes

| Mode | Use case | Required outputs | Completion rule |
|---|---|---|---|
| `smoke` | Recover assembly stats, test parsing, or validate a ZIP quickly. | intake, assembly stats, BGC inventory summary, manifest, scan-status ledger. | Complete when required extraction fields are populated or explicitly failed. |
| `gold` | Routine production run for adding strains to the master workbook. | All ten deterministic scans, workbook-ready CSVs, manifest, checksums, sealed package. | Complete only when every required scan is `MAMEY_COMPLETE` or explicitly `MAMEY_FAILED` with reason. |
| `sapote_standard` | Reader-friendly interpretation of a completed Mamey package. | Triage First Board, top candidate cards, executive/scientific/archive reports as needed. | Complete when all BGCs are accounted for and top leads receive interpretation. |
| `sapote_archive` | Publication archive or every-BGC deep dive. | Full Mode B for every BGC, batched if necessary, with checkpoint after every batch. | Complete only when every BGC has full treatment or a named deferred ledger entry. |
| `project_merge` | Adds strain/run outputs into a master workbook. | updated workbook, merge log, schema validation report, before/after row counts. | Complete when schema validation passes and no existing rows are silently removed. |

> **Current executable mapping (`mamey_run.py run --mode`):** the selected CLI accepts `gold` (default) and the deprecated `standard` alias, which routes to gold; `smoke` was removed. These modes produce extraction/ranked evidence and do not author completed Mode B cards. The table above retains historical design vocabulary. `sapote_standard` / `sapote_archive` describe downstream interpretation stages and `project_merge` a workbook operation; none is a current `run --mode` value. Select the actual command owner and preserve its output/receipt scope before promising completion.

## -1.3 Required deterministic scan spine

A Mamey `gold` run is not complete until the following scans finish or fail explicitly:

1. `KCB_sweep`
2. `RG_GMCI`
3. `FLBR`
4. `CCTT`
5. `CGAD`
6. `UMED`
7. `EFLS`
8. `resistance`
9. `bldA_TTA`
10. `TFBS`

Each scan writes a machine-readable status into `[strain]_3_scan_states.json` and each workbook-facing summary must preserve that status. Do not replace a missing scan with prose. Mark it failed and record the reason.

## -1.4 Bundle session-start handshake

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-14-bundle-session-start-handshake).

## -1.5 Depth-first batching rule

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-15-depth-first-batching-rule).

## -1.6 Per-strain checkpoint schema

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-16-per-strain-checkpoint-schema).

## -1.7 Workbook contract

The workbook is a controlled output, not a scratchpad. Every merge must follow these rules:

1. Never remove existing rows unless the user explicitly requests deletion.
2. Append new strains and new BGCs; update existing rows only through keyed strain/BGC IDs.
3. Preserve exact schema names required by the current project workbook.
4. Record every update in a merge log with: sheet, key, field, old value, new value, source file, timestamp.
5. If a field is not supported by deterministic evidence, leave it blank or mark `not_available`; do not fill by narrative inference.
6. Workbook-facing values come from Mamey outputs first, then manually supplied user metadata, then Sapote interpretation only for explicitly interpretive columns.

## -1.8 All-in-one package manifest

Every final handoff ZIP must include, when applicable:

| Required item | Filename pattern |
|---|---|
| Run summary | `batch_summary.md` or `[strain]_summary.md` |
| Checkpoint | `SID_session_checkpoint.csv` or `project_session_checkpoint.csv` |
| Updated workbook | `[project]_master_after_[batch].xlsx` |
| Per-strain sealed packages | `[strain]_Mamey_[version]_Complete_Package.zip` or `[strain]_Mamey_failed_package.zip` |
| Merge log | `workbook_merge_log.csv` |
| Validation report | `validation_report.md` |
| Checksums | `checksums_sha256.txt` |
| Deferred/recovery ledger | `deferred_or_recovery_needed.csv` |

## -1.9 Batch continuation protocol

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-19-batch-continuation-protocol).

## -1.10 Accession and public-genome rule

If a task requests a public accession:

- The current `--accession` flag is a placeholder; accession-only input returns `UNSUPPORTED_ACCESSION_MODE`.
- The bundled extraction inputs are existing antiSMASH ZIPs: `--input-zip` for one strain or `--strains` for a batch. Record any separately selected preprocessing route.
- Do not fabricate antiSMASH or Mamey outputs from accession metadata alone.
- If antiSMASH ZIPs are supplied later, replace failed placeholders with complete sealed packages and rebuild the batch ZIP.

## -1.12 Bundle file-map and replacement protocol

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-112-bundle-file-map-and-replacement-protocol).

## -1.13 Bundle update workflow after monolith finalization

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-113-bundle-update-workflow-after-monolith-finalization).

## -1.14 Batch Controller v2 — committed work units

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-114-batch-controller-v2--committed-work-units).

## -1.15 Failure taxonomy and recovery actions

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-115-failure-taxonomy-and-recovery-actions).

## -1.16 Scan-state file format

`[strain]_3_scan_states.json` is written verbatim from `run_external_scan_pack` (mamey/external_adapters.py). Its actual emitted structure is a `scans` list plus an `evidence_channels` map:

```json
{
  "scans": [
    ["KCB_sweep", "PASS", "free-text detail string"],
    ["RG_GMCI", "NULL", "..."],
    ["bldA_TTA", "NOT_APPLICABLE", "..."]
  ],
  "evidence_channels": {
    "antiSMASH_source_domains": {"status": "...", "reason": "...", "claim_safety": "..."},
    "custom_marker_hmmer": {"status": "NEEDS_HMMER_DOMTBLOUT", "reason": "Release 2 scope."}
  }
}
```

Each scan is a `[name, state, detail]` triple. The ten names are fixed. An extra `PHO_CLUSTER` entry is added when T43-PHO has five or more hits. Valid scan states are `PASS`, `NULL`, `NOT_APPLICABLE`, `DEFERRED`, and `FAILED` (this matches the README and the code). `evidence_channels` records the status of the GBK-domain / HMMER / DIAMOND / BLASTP channels, several of which are Release-2 scope.

> **Release-2 (aspirational, not yet emitted):** a richer per-scan object — `{scan_name, status, started_at, completed_at, input_sources, output_files, summary_counts, failure_code, failure_reason, recovery_action, claim_boundary}` with `MAMEY_COMPLETE`/`MAMEY_FAILED`/`MAMEY_DEFERRED`/`MAMEY_NOT_APPLICABLE`/`MAMEY_RECOVERY_NEEDED` statuses — is the intended future schema. It is documented here as a target, not a current contract; the current emitted form is the `[name, state, detail]` triple above.

## -1.17 Workbook merge contract

The selected `update_master_workbook` loads or creates the workbook, preserves extra sheets by default, ensures canonical headers, drops this strain’s rows on an explicit sheet allowlist, writes fresh canonical views and saves the requested output path. It does not create an immutable snapshot itself, reconcile arbitrary prior column values or call the standalone schema checker inline. CLI orchestration has additional publication behavior with its own contract. Preserve a separately bound before state: deleted strain rows can contain prior judgment or operator annotations that this rewrite does not automatically restore.

### Current behavior (idempotent re-ingest)

| Sheet family | Row identity | Merge behavior (current code) |
|---|---|---|
| strain registry / A2 | `Strain` / `strain_id` | drop prior strain rows, then append (one per run) |
| BGC master | `Strain` + `BGC_ID` | drop prior strain rows, then append (one per BGC per run) |
| RG-GMCI | `Strain` | drop prior strain rows, then append summary row(s) |
| scan comparison | `Strain` + `scan_name` | drop prior strain rows, then append per scan |
| lead/candidate sheets | `Strain` + `BGC_ID` + `lead_id` | drop prior strain rows, then append |
| provenance/merge log | timestamped row | append-only (audit trail; not deduped) |

**Re-ingest scope:** normal replacement avoids repeated deterministic strain rows on the configured allowlist; it is not universally safe or byte-idempotent. A3_Run_Manifest, H1_Handoff_Log and H2_Gap_Queue are three append-history sheets excluded from that replacement. Re-ingest can change history, dates and retained annotations. Compare expected identities and prior authored/operator values before adopting the output; matching local strain/BGC aliases alone does not prove unchanged physical loci.



### Schema validation (separate step)

The standalone `workbook_schema_check.py` utility checks a master workbook’s selected sheets, physical header positions, row counts and (in the full path) A2/B1 strain-set consistency; optional v1.2 checks have separate scope. It reports PASS/FAIL and is not called inline by `update_master_workbook`. It has no before/after workbook input, so it cannot certify no prior rows were deleted, reconcile conflicting values/provenance, decide interpretive column authority or prove full locus identity. Treat schema acceptance and source/value conservation as separate checks.

> **Release-2 (aspirational):** keyed upsert (update existing `Strain`+`BGC_ID` rows; append only when new) with an inline pre-merge schema-validation gate that hard-stops on `WORKBOOK_SCHEMA_CONFLICT` and a version-note log for any overwrite. Documented as the intended future contract, not current behavior.

## -1.18 Claim boundary matrix

| Output field or statement type | Source of truth | Allowed layer | Claim ceiling |
|---|---|---|---|
| coordinates, contig, region, start/end | antiSMASH parsed by Mamey | Mamey | factual extraction |
| raw BGC count / corrected BGC count | Mamey assembly/BGC inventory | Mamey | calculated summary |
| scan hits and trigger counts | Mamey scan outputs | Mamey | evidence present/absent |
| resistance tier | Mamey source-derived scan | Mamey + Sapote note | class-supporting evidence, not product proof |
| lead priority | Sapote from Mamey evidence | Sapote | follow-up priority only |
| compound identity | chemical/metabolomic evidence | Sapote only with external evidence | never from genome alone |
| ecological interpretation | metadata + Sapote logic | Sapote | hypothesis / context, not proof |
| wet-lab next action | Sapote | Sapote | recommendation |

### -1.18.1 KCB provenance discipline

KCB (KnownClusterBlast) values are **similarity signals, not product identifications.** The display and rendering system enforces this structurally:

- **Schema:** the "KCB/MIBiG Provenance Patch" section of [MASTER_SCHEMA_FROZEN_v1_1.md](MASTER_SCHEMA_FROZEN_v1_1.md) defines the `closest_product_provenance` field with 7 enumerated values (KCB_TEXT_EXACT, MIBIG_REFERENCE_LINE, KCB_TOP_FIELD, etc.). Any workbook sheet carrying a product name must carry its provenance field.
- **Code:** `mamey/render_safe.py:safe_kcb_display()` and `mamey/concordance.py:concordance_for_bgc()` (which anchors on the `closest_candidate_kcb_product` field) implement provenance-aware rendering. Raw `kcb_top` values must never appear in user-facing outputs without provenance qualification.
- **Architecture-first override:** `mamey/architecture_first.py` (v9.7.107) enforces KCB-blind pathway classification. When gene architecture and KCB disagree, architecture wins. See `assess_architecture()`, `check_kcb_concordance()` and `make_assignment()` in the same module.

## -1.19 Derived prompt targets

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-119-derived-prompt-targets).

## -1.20 Release-readiness checklist

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-120-release-readiness-checklist).

## -1.11 Minimum all-in-one completeness check

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#-111-minimum-all-in-one-completeness-check).

## Prompt Table of Contents

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#prompt-table-of-contents).

## SECTION 0 — Run Controller / Execution Spine

### Purpose

The Run Controller is the default execution spine for Sapote. It prevents model-side drift, reduces decision burden, and makes a full workflow run behave like a controlled pipeline.

When the user says any of the following, the Run Controller is active automatically:

```text
Run v8.4 candidate full analysis on [Strain ID]
Run v8.0 full analysis on [Strain ID]
Run full Sapote analysis on [Strain ID]
Run standard full analysis on [Strain ID]
Run archive-quality full analysis on [Strain ID]
Run the workflow on [Strain ID]
```

### Default execution order

When a full-analysis trigger fires, execute in this exact order unless the user explicitly requests a narrower module:

1. **Session intake and context acknowledgement**
   - Load antiSMASH ZIP / JSON / GBK / KCB files.
   - Parse strain ID, taxonomy, host/source, ecological category, and bioactivity status.
   - Preserve typed bioactivity metadata; when strain-specific data are absent record `NOT_SUPPLIED` without naming an assay target.
   - Run Metadata Conflict Audit.

2. **Assembly and BGC inventory**
   - Assembly statistics.
   - BGC inventory with edge status, corrected BGC count, Architecture Confidence, LMPKS/FLBR grade, UMED maturation status for lanthipeptides, RiQ, KCB top hit, and bldA/TTA status.

3. **Parallel first-pass scans** (the interpretation roster in §0.6 and `prompts/CLAUDE_SYSTEM_PROMPT.md` §4.2. This roster is not the engine's ten scans in §-1.3. It adds the hallucination-trap audit and LMPKS rescue, merges bldA/TTA with TFBS, and omits EFLS.)
   - KCB sweep.
   - Diagnostic Signature Weighting + antiSMASH Hallucination-Trap / Claim-Calibration Audit (§34): classify high-information versus generic genes, preserve promising fragments, and calibrate allowable claim language before Mode B, Triage First, Front Page/PDB, and Wet-Lab Decision Matrix outputs.
   - LMPKS Rescue (§42).
   - FLBR megasynthase fragment census (§51).
   - UMED maturation-enzyme scan (§52) for lanthipeptide/RiPP maturation gaps.
   - CCTT Trigger Scan (§43).
   - CGAD (§44): in `run_source_scans`, the first-pass helper scans annotation text in the supplied CDS list for the configured chitin/glycan patterns; this call has no habitat condition. Confirm the proteome/CDS source and actual scope before interpretation. This helper call does not itself perform the historical protein motif, secretion or HMMER validation described in §44, and a BGC-limited or unavailable channel does not establish genome-wide absence.
   - Resistance Gene Confirmation (§45).
   - RG-GMCI (Reference-Guided Genome Mining Candidate Inference; homology-guided linkage of fragmented BGC regions to a shared reference producer cluster; mandatory for every multi-contig genome).
   - bldA/TTA + TFBS (TTA codon routing → bldA tiers T1–T4; transcription-factor binding-site motif scan).

4. **Triage First Board**
   - Rank top candidates before any long Mode B reports.
   - Include chemical class, representative compound/formula/MW, expected adducts, m/z extraction windows, confidence, caveat, and next action.

5. **Run-mode decision**
   - Standard Full Analysis by default unless the user explicitly says “archive-quality,” “full depth for every BGC,” “workflow validation,” or equivalent.
   - Archive-Quality Full Analysis when exhaustive full Mode B reports are requested or the run is a formal workflow stress test.

6. **Batch Plan if needed**
   - Required if Archive-Quality mode and BGC count >15.
   - Optional in Standard mode; use only if top-candidate report cannot fit a single session.

7. **Mode B / Candidate Cards**
   - Standard mode: full Mode B for top candidates and abbreviated ledger entries for all others.
   - Archive-Quality mode: author the selected current Mode B profile for every requested BGC, batching as needed. The historical §1–§8 scaffold is not a finished full48/current50_v2 card; carry the same selected contract through native template emission and actual-file verification.

8. **Decision-support modules**
   - Wet-Lab Decision Matrix.
   - Metabolomics Readiness Summary.
   - Reviewer Attack Simulation.
   - Fermentation Card.
   - Recommended Figures.

9. **Reader-layered deliverables**
   - Executive / Layperson Report.
   - Scientific Deep Dive Report.
   - Archive Appendix.
   - Reader-Facing Front Page and Briefing Package (Editorial Broadsheet, Color Tabloid, Executive Briefing) unless omitted by user request.
   - Machine-readable Project Memory Snapshot.
   - Package manifest.

10. **Final audit**
   - QA gates.
   - Missingness register.
   - Deferred ledger.
   - Output audit log.

### Run Controller non-negotiables

- Do not skip the Triage First Board.
- Do not bury top wet-lab actions after dozens of dense BGC pages.
- Do not claim compound identity from mass, KCB, or antiSMASH labels alone.
- Do not downgrade Archive-Quality depth to fit a single session; batch instead.
- Do not force Standard mode to produce exhaustive gene-by-gene reports for every low-priority fragment.
- Always record whether each BGC received: `full Mode B`, `candidate card`, `abbreviated ledger entry`, `deferred`, or `not applicable`.
- Do not treat hallucination-trap flags as automatic disqualifiers. Sapote is designed for fragmented assemblies; QC flags lower claim confidence, not necessarily lead priority.
- Do not collapse Lead Priority and Claim Confidence into one score.
- Do not treat all genes equally. Classify each named gene/domain as diagnostic, class-supporting, context-dependent, generic, or overinterpretation-prone before using it as evidence.
- Do not use transporters, regulators, common oxidoreductases, methyltransferases, glycosyltransferases, or broad NRPS/PKS domains as primary product-identity evidence unless stronger context is present.
- Do not dismiss transporter or resistance genes by default: when literature-backed, BGC-adjacent, duplicated, divergent, horizontally acquired, or paired with diagnostic biosynthetic genes, they may increase follow-up priority while still requiring conservative wording.
- Do not treat an antiSMASH lanthipeptide/RiPP product label as maturation-complete until UMED status is checked; a missing maturation protease is a pathway-completeness/missingness issue, not evidence of mature product production.

---

## SECTION 0.5 — Reader-Layered Output System

### Purpose

Sapote outputs must serve three different readers without forcing all readers through the same dense document.

### Required output layers

| Layer | Audience | Purpose | Default filename suffix |
|---|---|---|---|
| Layer A — Executive / Layperson Report | PI, collaborator, student, non-specialist reader | Explain the strain, top discoveries, caveats, and next actions in readable language | `_Executive_Report.pdf` |
| Layer B — Scientific Deep Dive Report | Natural-products / microbiology / genomics reader | Main technical report with curated evidence, triage, top Mode B reports, scoring, metabolomics, and reviewer critique | `_Scientific_Report.pdf` |
| Layer C — Archive Appendix | Future reviewer, workflow auditor, model comparison, rerun context | Exhaustive tables, full Mode B set, gene-by-gene details, raw traceability, missingness, and deferred ledger | `_Archive_Appendix.pdf` |

### Layer routing rules

**Layer A must include (target quality: `examples/layperson_guide_exemplar.md`):**
- Strain header block (inline): genome Mb · contigs · raw BGCs · corrected BGCs · interior % · assembly tier · bioassay.
- 2–3 sentence plain-English narrative: organism, habitat/source, top finding named explicitly with compound class.
- BGC table (exactly 5 rows): BGC | Class | Size (kb) | Novelty (Known N% / Novel) | Layperson headline.
  - Report the observed comparison value with its exact source field, units, reference, coverage and missingness. Do not turn a raw cumulative KCB score into a percentage or use a <50% cutoff as proof of scientific novelty; an unavailable comparator remains unavailable.
  - Layperson headline must name the compound class specifically; one sentence; no unexplained acronyms.
  - NAPAA/housekeeping BGCs flagged: “epsilon-Poly-L-Lysine — housekeeping reference, not a discovery target.”
  - Cytotoxic/enediyne BGCs flagged: “⚠ cytotoxic class — [E-signal] note; cytotoxicity-guided handling per standard lab SOPs (non-selective).”
- Assembly/claim caveat: 1–3 sentences on what cannot be claimed and which BGCs are truncated.
- Immediate next action: one sentence, specific experiment or sequencing step.

For multi-strain sessions, Layer A also includes:
- Global Ranked Top Targets table (up to 13 rows): Rank | Strain | Habitat | Assembly | Key BGC(s) | Why it ranks here | Next experiment.
- Cross-Habitat Statistics table: total corrected BGCs, mean per strain, % novel, good/very-poor counts per habitat.

**Layer B must include (contig ID mandate — applies to every BGC reference in every table and report):**
- Every BGC reference carries the full canonical contig identifier: `BGC_ID | contig_full_name | regionXXX | start–end bp | size kb | edge_status | Arch | TTA_tier`.
  Shortened node numbers (e.g., “NODE_2”) are not acceptable in any Layer B deliverable.
- Intake and metadata audit.
- Assembly/BGC summary with corrected count derivation shown.
- Full Triage First Board with full contig IDs in every row.
- KCB / hallucination / LMPKS / CCTT / resistance summaries.
- Full Mode B reports for top candidates (with canonical BGC identifier block at top of each card).
- Wet-Lab Decision Matrix.
- Metabolomics Readiness Summary with chemical handles and expected m/z.
- Reviewer Attack Simulation.
- Ecological Synthesis.
- Fermentation Card with TTA tier noted for every target BGC.

**Layer C must include (target quality: `examples/bench_guide_exemplar.md`):**

Structured in three sub-sections per strain (see Section G of [prompts/FULL_RUN_PROFILE.md](../prompts/FULL_RUN_PROFILE.md)):

Sub-section 1 — Known / Reference BGCs table: compound detection matrix with columns for MW, UV/Vis, color/CAS, extraction protocol, LC-MS mode, key assay, induction hint, safety. One column per known BGC (≥60% MIBiG); rows are compound properties. This is a TABLE-format deliverable, not prose.

Sub-section 2 — Novel / Highest-Priority BGC Candidates: table (BGC# | size | class | MIBiG% | closest reference | priority) followed by one-paragraph extraction/detection guide per HIGH BGC.

Sub-section 3 — Fermentation Strategy: one paragraph per strain covering genus-appropriate media, OSMAC sequence, priority BGC extraction targets, long-read note if POOR/VERY_POOR, and dereplication instructions (what known compounds to subtract).

All Mode B reports required by run mode, abbreviated ledger entries, full BGC inventory, full KCB sweep, missingness register, deferred ledger, and output audit log also included.

**Layer C content by run mode:**

In **Standard Full Analysis** mode, Layer C contains:
- Full Mode B reports for top-candidate BGCs (these are shared with Layer B)
- Abbreviated ledger entries for all remaining BGCs (minimum fields per §0.9)
- Full BGC inventory table
- Full KCB sweep table
- Full domain inventory
- Full evidence traceability tables
- Missingness Register
- Deferred Ledger
- Output Audit Log
- Project Memory Snapshot text view

Full gene-by-gene domain tables appear in Layer C **only** for top-candidate BGCs in Standard mode. For all other BGCs, the abbreviated ledger entry is the Layer C record; it does not include a gene-by-gene table.

In **Archive-Quality Full Analysis** mode, Layer C contains the requested complete BGC roster, current-profile authored cards, gene-by-gene/source tables, KCB extraction, traceability and explicit deferred/held states. Preserve historical §1–§8 material as a legacy scaffold; current completion requires the selected contract/template and actual authored-file verification rather than an eight-heading count.

### PDF compilation rule

If a single compiled master PDF is requested, it must preserve reader layering in this order:

1. Executive / Layperson Report
2. Scientific Deep Dive Report
3. Archive Appendix
4. Audit log and package manifest

Do not interleave archive tables into the executive or main scientific narrative unless necessary for interpretation.

---

## SECTION 0.6 — Triage First Board

### Purpose

The Triage First Board is the first interpretive output after BGC inventory and first-pass scans. It converts a long BGC list into ranked wet-lab priorities.

### Required timing

Generate the Triage First Board before long Mode B reports. **The Triage First Board cannot be generated until all ten first-pass scans are complete:** KCB sweep, antiSMASH Hallucination-Trap Audit, LMPKS Rescue (§42), FLBR megasynthase fragment census (§51), UMED maturation-enzyme scan (§52), CCTT Trigger Scan (§43), CGAD (§44), Resistance Gene Confirmation (§45), RG-GMCI (Reference-Guided Genome Mining Candidate Inference; mandatory for every multi-contig genome), and bldA/TTA + TFBS (TTA codon routing and transcription-factor binding-site motif scan). These correspond to Run Controller step 3 and match the §4.2 first-pass roster in the Sapote system prompt. Do not begin the board until all ten scan outputs are available. **For CGAD, the scan output must include the §44 Step 0 proteome scope state (`full proteome scanned`, `BGC-region only`, or `full proteome unavailable`).**

### Required columns

| Column | Meaning |
|---|---|
| Rank | Overall triage rank |
| Locus identity | Source-bound strain / full node-or-contig / region / BGC alias for every individual locus; retain both complete identities and linkage holds for a proposed pair |
| Predicted class / candidate | Compound class or candidate family; label as specific, class-level, or broad-class |
| Key genome evidence | Highest-value markers: KCB, diagnostic domains, resistance genes, split-pathway logic, architecture confidence |
| Chemical handle | Known compound if specific; representative compounds or MW range if class-level |
| Formula / MW | Verified formula and exact or nominal MW when known; representative examples for class-level calls |
| Expected ions | Common adducts and ionization polarity |
| LC-MS / LC-DAD target window | Suggested EIC/TIC windows and UV/Vis wavelengths when useful |
| Confidence | High / Medium / Low plus why |
| Caveat | Main reason this could be wrong or overcalled |
| Diagnostic Signal Score | 0–5 score for high-information genes/domains/signatures independent of assembly completeness |
| Claim Confidence | VERY LOW / LOW / MODERATE / HIGH / CONFIRMED; separate from lead value |
| Evidence-weight tier | Highest tier supporting the interpretation, Tier 1–5 |
| Marker basis | Named diagnostic marker, pathway constellation, transporter/resistance pattern, or generic-domain basis |
| Generic-gene overclaim risk | LOW / MODERATE / HIGH risk that the claim depends on broad/common genes |
| Safe claim | One sentence allowed in reports and front-page outputs |

A candidate may rank HIGH or EXCEPTIONAL in Lead Priority even when Claim Confidence is LOW if it carries a high-information diagnostic marker, rare pathway constellation, or strong self-resistance/target-directed signal. Conversely, a complete-looking BGC with only generic domains may remain low priority.

### Triage ranking logic

Rank by integrated decision value, not by KCB score alone:

1. Fit to explicitly supplied assay context or the user’s selected review question. Missing assay metadata stays NOT_SUPPLIED, without assigning a default target or inferring activity.
2. Strong diagnostic domain or resistance-gene confirmation.
3. High-value cryptic class trigger: indolocarbazole, HSAF/PTM, peptidyl-nucleoside, enediyne, phosphonate, carbapenem, ansamycin, angular/linear T2PKS, LMPKS/polyene/macrolide.
4. Architecture confidence and assembly completeness.
5. Chemical tractability in crude LC-MS / LC-DAD-MS.
6. Novelty and dereplication status.
7. Feasibility of next experiment.

### Candidate card format

For every top candidate in Layer A and Layer B, use the following compact card before the detailed prose:

```text
Candidate: [compound class / family / split-pathway unit]
Genome support: [domains, KCB, resistance gene, architecture]
Assay context: [typed metadata_state / observation_state / source receipt; NOT_SUPPLIED when absent; NOT_ESTABLISHED locus/compound linkage unless separately governed]
Chemical handle: [specific compound or representative class examples]
Formula / MW: [formula and MW, or class range]
Chemical handle status: [verified / class-level example - unverified / no reliable handle]
Expected LC-MS: [ion mode, adducts, target m/z windows]
UV/Vis or visual handle: [if applicable]
Confidence: [High / Medium / Low]
Caveat: [main uncertainty]
Next action: [specific experiment]
```

---

## SECTION 0.7 — LC-MS Chemical Handle Module

### Purpose

Genome-mining outputs are most useful when they point to specific chemical searches. The LC-MS Chemical Handle Module converts BGC predictions into practical mass/UV/isotope/extraction targets for crude extracts, fractions, or purified-compound work.

### Required use

Apply this module to:
- Every Triage First Board row.
- Every high-priority Mode B candidate.
- Every CCTT-triggered candidate.
- Every LMPKS rescue candidate.
- Every KCB hit above moderate confidence.
- Every candidate for which the user has selected chemical-context review; retain explicit assay targets only when supplied and source-bound. Missing metadata does not default to MRSA/Candida activity or establish a locus link.

### Evidence categories

| Category | When to use | Required output |
|---|---|---|
| Specific known-compound handle | KCB or diagnostic genes strongly point to a named compound/family member | Formula, MW, common adducts, UV/Vis, extraction notes, source of formula to verify |
| Class representative handle | BGC supports a class but not a specific compound | 2–5 representative compounds with formulas/MWs or a class MW range |
| Broad-class handle | Only broad class is known, e.g. T1PKS macrolide-like | MW range, representative examples, likely adducts, extraction behavior |
| Split-pathway handle | BGC is fragmented or tailoring genes are on different contigs | Multiple possible chemical handles corresponding to alternative tailoring states |
| No reliable handle | Class is too vague or formula would be misleading | State “no reliable formula/MW handle; use untargeted LC-MS/MS and molecular networking” |

### Required chemical-handle fields

For each candidate, report:

- Representative compound name or class label.
- Formula when known and verified.
- Molecular weight / monoisotopic mass if available.
- Nominal MW if exact mass is unavailable.
- Expected ionization polarity.
- Expected adducts, usually including:
  - ESI+ `[M+H]+`
  - ESI+ `[M+Na]+`
  - ESI+ `[M+NH4]+` when appropriate
  - ESI− `[M−H]−` for acidic compounds
- Recommended EIC/TIC target windows:
  - High-resolution LC-MS: ±5–10 ppm around expected adduct.
  - Low-resolution LC-MS: ±0.3–0.5 Da around expected adduct.
  - Crude extract broad screen: ±1–2 Da or class-range window.
- UV/Vis or DAD wavelength handles when known.
- Isotope-pattern notes for halogenated compounds.
- Extraction and stability caveats.

### Formula/MW verification rule

Formula and MW values must be verified against a reliable chemical source when presented as final. Acceptable sources include PubChem, ChemSpider, ChEBI, KEGG, NPAtlas, MIBiG, Dictionary of Natural Products, primary literature, or an authentic-standard vendor page. If not verified, label the value as `unverified example — check before targeted extraction`.

### Representative class examples

Use examples like the following when class-level predictions need chemical handles. These are examples to verify at final-output time, not automatic compound identifications.

| Class | Representative handles to consider | Notes |
|---|---|---|
| Macrolide / erythromycin-like | Erythromycin A; erythromycin B; tylosin; spiramycin | Useful for 700–1000 Da ESI+ windows; glycosylation shifts mass |
| Polyene macrolide | Nystatin-like; amphotericin-like; filipin-like | UV/Vis polyene bands are highly informative; often broad MW range |
| Indolocarbazole | Staurosporine-like; rebeccamycin-like; AT2433-like; arcyriarubin-like | Halogenated variants require isotope-pattern review |
| HSAF / PTM | HSAF; 10-epi-HSAF; frontalamide/frontalin-type PTM examples | Neutral pH extraction; avoid strong acid |
| Peptidyl-nucleoside | Nikkomycin-like; polyoxin-like; pacidamycin-like | Polar extraction; standard EtOAc may miss activity |
| Ansamycin | Rifamycin-like; geldanamycin-like; ansatrienin-like | UV/Vis and redox/photostability caveats matter |
| Angular T2PKS | Angucycline/landomycin/kinamycin-like | Aromatic chromophores; cytotoxic warhead caution for kinamycin-like calls |
| Linear T2PKS | Tetracycline/tetracenomycin/anthracycline-like | UV/Vis and pH-sensitive extraction; cytotoxicity caution for anthracycline-like calls |
| Carbapenem | MM4550-like; thienamycin-like | Small polar β-lactam; instability and bioassay-guided capture important |
| Prodiginine | Prodigiosin/undecylprodigiosin/streptorubin-like | Visual red/magenta colony pigment is a first-pass screen |

### Identity-safety rule

Do not claim compound identity from m/z alone. Matching mass is triage evidence only. Identification requires at least one additional orthogonal support line such as isotope pattern, UV/Vis, MS/MS, retention comparison, authentic standard, purified-compound NMR, genetic knockout, or co-elution with bioactivity.

Required wording:

```text
The formula/MW entry is a chemical search handle, not a compound identification. A matching m/z feature should be treated as a candidate signal until supported by isotope pattern, UV/Vis, MS/MS, retention behavior, authentic standard, purification/NMR, or genetic/metabolomic evidence.
```

---

## SECTION 0.8 — Visual Load Reduction Standard

### Purpose

Sapote reports should be readable first and exhaustive second. Dense material is preserved, but routed to the correct layer.

### Required rules

1. **One dense table per page** in PDF outputs unless the page is explicitly part of the Archive Appendix.
2. **Every dense table must be preceded by an interpretation box** explaining the 2–4 most important takeaways.
3. **Candidate cards before paragraphs** for top BGCs.
4. **Appendix routing for full gene-by-gene tables** unless the BGC is a top candidate or the user requests archive-quality inline reports.
5. **Landscape orientation for wide tables** such as BGC inventory, KCB sweep, and metabolomics target tables.
6. **Short section summaries** at the start of every major section.
7. **Use callout boxes** for:
   - high-confidence discovery leads
   - cytotoxicity caution
   - split-pathway candidates
   - assembly/fragmentation limitations
   - wet-lab-ready next actions
   - claim-safety caveats
8. **Avoid wall-of-text Mode B reports** by using the fixed order:
   - Candidate Card
   - Evidence Summary
   - Gene/Domain Highlights
   - Chemical Handle
   - Mechanistic Interpretation
   - Caveats
   - Next Actions
   - Archive Details

### Standard callout labels

Use consistent labels in all PDFs and Markdown reports:

```text
TOP LEAD
WET-LAB READY
CHEMICAL HANDLE
SPLIT PATHWAY
FRAGMENTED ASSEMBLY
CYTOTOXICITY CAUTION
CLAIM-SAFETY CAVEAT
BIOACTIVITY METADATA NOT SUPPLIED / SUPPLIED STATE
REQUIRES VERIFICATION
DEFERRED TO ARCHIVE
```

---

## SECTION 0.9 — Standard Full Analysis vs Archive-Quality Full Analysis

### Default mode

Sapote v8.0 defaults to **Standard Full Analysis** unless the user explicitly requests Archive-Quality mode.

### Standard Full Analysis

Use for routine strain interpretation, exploratory genome mining, and readable collaborator-facing output.

Required outputs:
- Executive / Layperson Report.
- Scientific Deep Dive Report.
- Triage First Board.
- BGC inventory for all BGCs.
- Full Mode B reports for top candidates selected by triage.
- Abbreviated ledger entries for all remaining BGCs.
- KCB / hallucination / LMPKS / CCTT / resistance summaries.
- Wet-Lab Decision Matrix.
- Metabolomics Readiness Summary with LC-MS chemical handles.
- Ecological Synthesis.
- Fermentation Card.
- Missingness register.
- Project Memory Snapshot.
- Package manifest.

### Abbreviated ledger entry - minimum required fields

Every BGC not receiving full Mode B treatment in Standard mode must appear as an abbreviated ledger entry in the Archive Appendix (Layer C). This is an inventory accountability record, not a triage entry, and does not require a chemical handle, Mode B narrative, or gene-by-gene domain table.

| Field | Required content |
|---|---|
| Locus identity | Strain / full node-or-contig / region / BGC alias copied from one bound inventory record; hold missing or conflicting components |
| Class | antiSMASH product label and/or domain-derived class assignment |
| Edge status | Interior / Edge / Full-contig |
| Architecture Confidence | Grade A-E (per §31) |
| WL score | Wet-lab decision score (per §33) |
| Priority tier | HIGH* / HIGH / MEDIUM / LOW / Deprioritized |
| Reason for abbreviated treatment | One sentence, e.g., "Edge BGC, WL = 2, no CCTT trigger, no Tier 1/2 resistance marker within proximity rule, low-confidence class assignment" |
| Treatment status | `full Mode B` / `candidate card` / `abbreviated ledger` / `deferred` / `not applicable` |

The treatment status field satisfies the Run Controller non-negotiable: "Always record whether each BGC received: `full Mode B`, `candidate card`, `abbreviated ledger entry`, `deferred`, or `not applicable`."

Standard Full Analysis must still account for every BGC, but not every BGC requires a full-length Mode B report.

### Archive-Quality Full Analysis

Use when the user asks for:
- “archive-quality”
- “full depth”
- “full Mode B for every BGC”
- “workflow validation”
- “stress test”
- “publication archive”
- “complete gene-by-gene analysis for every BGC”

Required outputs:
- Everything in Standard Full Analysis.
- Authored current-profile Mode B report for every selected BGC, using the same explicit full48/current50_v2 contract for template emission and actual-file verification; historical §1–§8 is a legacy scaffold.
- Gene-by-gene table for every BGC.
- Full KCB extraction table.
- Full domain inventory.
- Full evidence traceability blocks.
- Full audit and deferred ledger.
- Archive Appendix PDF.

Archive-Quality mode may require multiple sessions. Do not reduce depth to fit a single context window; batch instead.

### User wording interpretation

| User wording | Mode |
|---|---|
| “Run v8.0 full analysis” | Standard Full Analysis |
| “Run the full workflow” | Standard Full Analysis |
| “Run full depth” | Archive-Quality Full Analysis |
| “Full archive-quality execution is needed” | Archive-Quality Full Analysis |
| “Test whether the workflow can produce everything” | Archive-Quality Full Analysis |
| “I need every BGC deep dive” | Archive-Quality Full Analysis |
| “Make a readable report” | Standard Full Analysis |
| “Smoke test” | Smoke-test mode |

---

## SECTION 0.10 — Evidence / Claim Separation Card

### Purpose

Every BGC interpretation must separate evidence from interpretation and action.

### Required structure

For each top candidate and every full Mode B report, include:

| Field | Required content |
|---|---|
| What the genome supports | Domains, KCB hits, architecture, resistance genes, tailoring logic, split-pathway evidence |
| What the assay supports | Typed metadata/observation state with source; NOT_SUPPLIED when absent. Strain/extract observations remain separate from governed locus attribution. |
| What is plausible | Mechanistic or chemical interpretation that is reasonable but not proven |
| What remains unproven | Compound production, BGC-level attribution, mechanism, final structure, activity source |
| What to do next | Specific LC-MS, extraction, bioassay, cytotoxicity, MS/MS, long-read, or genetics action |

**Assay states.** `NOT_OBSERVED` means no observation was supplied; it is not a negative. Assay columns keep four states, mapped to the typed metadata in `mamey/bioactivity_metadata.py` like this:

| Assay column | Typed state (`metadata_state` / `observation_state`) |
|---|---|
| + | `MEASURED_POSITIVE` / `POSITIVE` |
| − | `MEASURED_NEGATIVE` / `NEGATIVE` |
| n.t. (not tested) | No dedicated typed state. Record `SUPPLIED_UNKNOWN` / `UNKNOWN` and note "n.t." with its source. The owner confirms this mapping. |
| blank (nothing supplied) | `NOT_SUPPLIED` / `NOT_OBSERVED` |

Never convert one state into another. A blank or n.t. is never a −.

### Required claim-safety wording

```text
This BGC shows biosynthetic capacity consistent with [class/candidate]. It does not prove production of [compound] or explain extract-level bioactivity without fractionation, metabolomics, purified-compound, genetic, or orthogonal evidence.
```

---

## SECTION 0.11 — Package Manifest and Deferred Ledger

### Package manifest

Every full run must end with a package manifest:

| File | Layer | Purpose | Completed? | Notes |
|---|---|---|---|---|
| `[Strain]_Executive_Report.pdf` | A | readable summary | yes/no |  |
| `[Strain]_Scientific_Report.pdf` | B | main technical report | yes/no |  |
| `[Strain]_Archive_Appendix.pdf` | C | exhaustive appendix | yes/no/deferred |  |
| `[Strain]_Editorial_Broadsheet_Front_Page.pdf` | Front Page Package | serious reader-facing broadsheet summary | yes/no/omitted | optional compiled-page inclusion |
| `[Strain]_Color_Tabloid_Front_Page.pdf` | Front Page Package | high-energy reader-facing discovery summary | yes/no/omitted | optional compiled-page inclusion |
| `[Strain]_Executive_Briefing_Memo.pdf` | Front Page Package | formal decision memo / next-action briefing | yes/no/omitted | optional compiled-page inclusion |
| `[Strain]_BGC_Inventory.xlsx` | Data | spreadsheet table | yes/no |  |
| `[Strain]_Project_Memory_Snapshot.json` | Machine-readable | continuation context | yes/no |  |
| `[Strain]_Package.zip` | Package | all outputs | yes/no |  |

### Deferred ledger

If any item cannot be completed in the current session, record it explicitly:

| Deferred item | Reason | Required input/action | Assigned batch/session | Impact on claims |
|---|---|---|---|---|
| BGC[N] full Mode B | context limit | continue archive run | Batch 2 | BGC accounted for but not fully deep-dived |
| Exact formula/MW verification | no web/database access | verify PubChem/ChEBI/primary literature | final polish | chemical handle remains provisional |

A deferred item is not a failure if it is named, assigned, and carried into the Project Memory Snapshot.

---

---

## Purpose

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#purpose).

## How to Use This Prompt

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#how-to-use-this-prompt).

## Global Data Governance Rules

### Source-of-truth hierarchy

1. **User confirmation in the current session** — highest priority; log the change.
2. **Current master JSON**
3. **Current master strain spreadsheet**
4. **Paper-specific strain tables**
5. **Current manuscript `.docx`**
6. **Prior PDFs/reports/figures** — reference context only
7. **Project Memory Snapshot JSON** — fast-load context aid for resumed sessions
8. **Model memory or conversation history** — context aid only

### Missing-data and uncertainty rules

- Do not infer missing metadata from memory.
- Mark absent values as `missing`, `not tested`, `not available`, `not verified`, or `not applicable`.
- Separate verified, calculated, user-confirmed, derived, and unverified values.
- Preserve strain IDs exactly as written.
- Log corrections with original value, corrected value, reason, date, and source file.

### Manuscript-safe claim language

Preferred: "shows biosynthetic capacity for…" / "contains domains consistent with…" / "is predicted to encode…" / "contains a BGC similar to…"

Never (without direct chemical evidence): "produces X" / "makes X" / "the compound is X"

---

### Historical analytical defaults

The historical defaults below are retained as design provenance. They do not override current typed metadata admission or authorize inferred assay/host observations; use the current contract and source-bound supplied values.

**Bioactivity contract:** In the absence of strain-specific metadata, record `NOT_SUPPLIED`. Do not name an assay target, infer an outcome, or create BGC-level attribution. Typed supplied observations remain strain-level context unless a separately governed linkage is available.

#### Retired bioactivity-default enforcement (v7.9 historical record)

**Do not apply the excerpt below.** It is preserved only to identify the retired default-assumed MRSA/Candida policy. The current contract immediately above and `mamey/bioactivity_metadata.py` require NOT_SUPPLIED / NOT_OBSERVED with no assays when data are absent; typed supplied observations remain strain context. Do not propagate the retired labels into cards, ledgers, snapshots, reports or scores.

> When strain-specific bioactivity is not supplied, the workflow must treat MRSA and Candida inhibition as `default-assumed`, **not** as `missing`, and must explicitly carry that status through the analysis.
>
> Required wording at session start:
>
> ```text
> Bioactivity status: default-assumed MRSA and Candida extract-level inhibition. This workflow default does not assign activity to any specific BGC; BGC-level links require fractionation, metabolomics, genetics, or purified-compound evidence.
> ```
>
> Required propagation points:
> - Context acknowledgement / metadata audit
> - Deep Dive Synopsis strain metadata table
> - BGC Inventory notes or legend
> - Every Mode B §6 mechanistic-link section
> - Wet-Lab Decision Matrix scoring notes
> - Metabolomics Readiness Summary
> - Ecological Synthesis caveats
> - Missingness Register, where it must be listed as `default-assumed`, not `missing`
> - Project Memory Snapshot JSON and MD
> - Final audit log
>
> Required claim-safety language:
> - Preferred: "This BGC is mechanistically compatible with the default extract-level MRSA/Candida screen, but no BGC-level attribution is made."
> - Do not write: "This BGC explains the MRSA/Candida activity" unless supported by fractionation, metabolomics, genetics, or purified-compound evidence.
>
> When actual assay data are supplied, replace `default-assumed` with `user-confirmed`, `file-confirmed`, or `not tested`, and log the override source.

**Ecological source default and natural language parsing:**

> **SOURCE-INDEPENDENCE OVERRIDE (governs this entire section).** Sapote's interpretation is grounded in the GENOME / BGC evidence and is **independent of isolation source**. Isolation source is **provenance metadata only** — often unreliable (haphazard collection, inexperienced isolators) and a weak proxy for ecological function, which for most environmental actinomycetes is genuinely unknown. The Ecological Source Category below is an **OPTIONAL exploratory lens**, never a gate and never a functional claim: it must NOT change the biosynthetic-capacity call, defer/downgrade any deliverable, or be escalated into an ecological assertion (no "isolated from X → ecological role Y"). Unknown / `not supplied` source NEVER blocks interpretation — proceed with the general, source-independent framing (actinomycetes broadly carry antimicrobial / defensive biosynthetic capacity). When a source IS given, report it as caveated provenance only.

The default ecological framing is the general antimicrobial / defensive capacity of actinomycetes — the SAME regardless of source. The category lookup below may be noted as optional provenance context when a host/source description is supplied; parse it as given, label it `assumed`, and never let it drive an analytical output.

---

#### Ecological Source Category Lookup

**How to apply:** Scan the user's strain description, trigger phrase, or any session-start statement for terms matching the keywords below. Match to the first category whose keywords fit. If multiple categories match, prefer the more specific (e.g. "kelp forest" matches Marine before Plant-associated). If the source is genuinely ambiguous, note the ambiguity, state which category was assumed, and continue.

---

**CATEGORY 1 — Terrestrial plant-associated (DEFAULT)**

Applies when: no source is given, OR source matches soil, rhizosphere, root, plant, leaf, bark, stem, wood, compost, agricultural, forest floor, garden, crop, grass, meadow, peat (non-coastal), prairie, savanna, field, farm, orchard, vineyard, herb, flower, seed, endophyte, phyllosphere, or any named plant species (oak, pine, wheat, rice, maize, mangrove when terrestrial, etc.).

TFBS defaults:
- FuR / DmdR1 → rhizosphere iron competition; siderophore induction
- DasR → plant chitin / fungal pathogen signals in soil; GlcNAc from root fungi
- IolR → plant phytate and inositol phosphate catabolism; rhizosphere polyols
- ANR → microaerobic soil aggregates and root zone anaerobiosis
- LexA → UV oxidative stress in surface soil; plant defense ROS bursts
- BldD → seasonal developmental timing; dry season sporulation
- OsdR → soil desiccation and osmotic stress cycles

---

**CATEGORY 2 — Marine / coastal** ← SET MARINE FLAG

Applies when: source matches any of the following:
- Water bodies / habitats: marine, sea, ocean, seawater, saltwater, tidal, intertidal, subtidal, coral reef, reef, kelp, kelp forest, seagrass, mangrove (coastal), estuary, lagoon, coast, coastal, shore, beach, tide pool, rocky shore
- Sediments / substrates: marine sediment, sea floor, ocean sediment, sand (when coastal context is present), deep sea, hydrothermal vent, brine, salt flat, salt marsh, salt pan
- Organisms: fish (any species), whale, dolphin, seal, sea lion, sea otter, crab, lobster, shrimp, mussel, oyster, clam, sea urchin, starfish, jellyfish, squid, octopus, sponge (marine), tunicate, coral organism, algae (marine), macroalgae, seaweed, kelp (organism)
- Named locations with clear marine association: Monterey Bay, Pacific Ocean, Atlantic, Mediterranean, Red Sea, Gulf of Mexico, North Sea, Black Sea, Great Barrier Reef, Dead Sea, Chesapeake Bay, San Francisco Bay, any named ocean or sea
- Other: mariculture, aquaculture, fish farm, fish gut, marine mammal tissue, ocean floor, pelagic, benthic, bathypelagic

TFBS defaults:
- FuR / DmdR1 → iron limitation in iron-poor surface ocean; siderophore competition in oligotrophic zones
- DasR → chitin from crustacean moulting and marine invertebrate exoskeletons; copepod chitin; diatom cell walls
- IolR → phytoplankton inositol lipids; marine algal polyol catabolism
- ANR → oxygen minimum zones; sediment anaerobiosis; biofilm microaerobia
- LexA → UV damage in surface ocean; oxidative stress from reactive oxygen species in photic zone
- BldD → marine sediment seasonal cycles; biofilm developmental transitions
- OsdR → osmotic fluctuation in intertidal and estuarine zones; desiccation in tidal flat exposure

Additional notes for marine strains:
- Halogenated compound classes (chlorinated or brominated PKS/NRPS products) are more prevalent in marine actinomycetes — flag any halogenase domain (PF04820, PF00561 halogenase variants) as high priority.
- Standard EtOAc extraction may perform differently under high-salt conditions — note extraction caveat in Metabolomics Readiness sheet.
- Salt tolerance of producer strain should be confirmed before fermentation medium design — note in Fermentation Card.

---

**CATEGORY 3 — Bryophyte / lichen**

Applies when: source matches lichen, lichenised, lichen thallus, foliose, crustose, fruticose, Usnea, Peltigera, Cladonia, Xanthoria, Parmelia, Ramalina, Lecanora, or any named lichen genus; moss, Sphagnum, peat moss, liverwort, hornwort, bryophyte, Bryophyta, Hepatica, Marchantia, or any named moss genus.

TFBS defaults: per Section 17.3 Habitat 3 (bryophyte/lichen) worked examples. Key signals: IolR = polyol catabolism from photobiont (arabitol, mannitol, sorbitol); OsdR = seasonal desiccation and dormancy cycles; LexA = UV-induced damage on exposed rock or bark surfaces.

---

**CATEGORY 4 — Insect / arthropod-associated**

Applies when: source matches bee, bumblebee, honey bee, Apis, Bombus, ant, attine, leafcutter, fungus-growing ant, termite, wasp, beetle, bark beetle, weevil, fly, Drosophila, cricket, cockroach, tick, mite, spider, caterpillar, moth, butterfly, dragonfly, earwig, aphid, scale insect, or any named insect species or order; also: insect gut, insect cuticle, insect haemolymph, larval frass, brood cell, honeycomb, propolis, colony debris.

TFBS defaults: per Section 17.3 Habitat 1 (Hymenoptera) and Habitat 2 (Attine) worked examples. Key signals: DasR = moulting exuvia chitin; ANR = sealed brood cell microaerobia; LexA = hemocyte ROS burst and honey peroxide signals.

---

**CATEGORY 5 — Vertebrate-associated (non-marine)**

Applies when: source matches mammal, rodent, mouse, rat, rabbit, cow, sheep, pig, horse, dog, cat, bat, primate, human, skin, gut, intestine, faeces, stool, tissue, lung, blood, wound, skin lesion, nasal, oral, vaginal, or any named mammal species not in the marine list; also bird, chicken, turkey, crow, pigeon, raptor, avian, egg; reptile, snake, lizard, turtle, amphibian, frog, salamander; freshwater fish (trout, bass, perch, carp, catfish — when freshwater context is clear).

TFBS defaults:
- FuR / DmdR1 → host iron sequestration (ferritin, lactoferrin, transferrin competition in host tissue)
- DasR → host mucin GlcNAc signals in gut; chitin from cuticle if arthropod-associated
- LexA → host immune ROS burst (neutrophil oxidative killing)
- ANR → gut anaerobiosis; tissue microaerobic niches
- BldD / OsdR → host fever or stress responses (temperature-linked developmental regulation)

---

**CATEGORY 6 — Freshwater**

Applies when: source matches lake, river, stream, creek, pond, freshwater, wetland, marsh, swamp, bog (non-Sphagnum), canal, reservoir, aquifer, spring, waterfall, or any named freshwater body (Great Lakes, Amazon River, Nile, etc.); also freshwater sediment, lake sediment, river sediment, biofilm (freshwater context), freshwater sponge, freshwater algae.

TFBS defaults: apply terrestrial plant-associated defaults as baseline; flag DasR → freshwater invertebrate chitin (cladocerans, chironomid larvae, freshwater crustaceans); ANR → sediment oxygen gradients and seasonal stratification.

---

**CATEGORY 7 — Fungal / myco-associated**

Applies when: source matches mushroom, fruiting body, fungus, fungal mycelium, myco, mycorrhiza, mycorrhizal, endophytic fungus, Aspergillus, Penicillium, Trichoderma, Agaricus, Pleurotus, Ganoderma, or any named fungal genus; also: fungal garden (attine ants), fungal compost, wood rot fungus.

TFBS defaults: DasR → fungal chitin and glucan signals (GlcNAc from fungal cell walls); IolR → fungal inositol lipids and mannitol; FuR → fungal siderophore competition in mycelium-rich substrate.

---

#### Ambiguity handling

If the source description is ambiguous (e.g., "sand" without coastal context, "river" without freshwater confirmation, "tissue" without host specification):

1. State the ambiguity explicitly at session start.
2. Apply the best-matching category and name it.
3. Note in the audit log: "Ecological source category: [X] — assumed from '[user phrase]'; confirm if incorrect."
4. Continue analysis with the assumed category. Do not halt for clarification unless the ambiguity fundamentally changes the TFBS interpretation.

#### Override priority

User-provided host or source data at any point in the session overrides the assumed category immediately. Log the override and the session point at which it occurred.

---

### Metadata Conflict Audit

Run this audit before ecological synthesis, cross-strain comparison, CCSM, manuscript-facing habitat claims, or any full strain analysis using prior project memory.

Before starting, compare current-session strain metadata against any embedded project memory, master JSON, master strain spreadsheet, prior reports, reference implementation tables, and project-memory snapshots. Check at minimum: strain ID, taxonomy, host/source, habitat category, collection context, bioactivity status, assembly quality, and prior BGC highlights.

If strain ID, host/source, habitat category, taxonomy, or bioactivity conflict:
- Treat current-session user confirmation as highest priority unless the user says otherwise.
- Log the prior value, current value, source file, source date if known, and reason for the selected value.
- Mark all ecology, CCSM, cross-habitat, and manuscript-ready claims involving that strain as `metadata-sensitive` until reconciled.
- Do not reuse prior ecological synthesis, CCSM habitat labels, or manuscript-ready cross-habitat claims without rechecking them against the corrected metadata.
- Preserve the conflict note in the Project Memory Snapshot and Missingness Register when relevant.

**Required audit-log wording:**

```text
Metadata conflict audit: [no conflict detected / conflict detected]
Fields checked: strain ID, taxonomy, host/source, habitat category, bioactivity, assembly quality, prior BGC highlights
Conflicts: [none / list prior value → current value, source, action]
Decision: [current-session user confirmation / master JSON / master spreadsheet / other]
Metadata-sensitive claims: [none / list affected modules]
```

---

### Pre-Analysis Clarification Protocol

Before starting any full strain analysis or ecological synthesis, assess whether any uncertainty would materially change the analytical output. If defaults are sufficient, proceed silently — do not ask questions for the sake of asking them.

**Ask only when ALL of the following are true:**
1. The uncertain information would change a primary analytical output (TFBS interpretation, ecological category, bioactivity framing, culture condition recommendation, or WL score by ≥3 points).
2. The answer cannot be reasonably inferred from context already provided.
3. A default exists but it is a poor fit for the likely actual situation.

**Do not ask when:**
- Source or bioactivity is absent: preserve the corresponding unknown/NOT_SUPPLIED state and continue within the authorized task where those fields are not required. Do not create a default assay result or confirm an inferred source.
- Running a specific module rather than a full analysis (KCB sweep, LMPKS rescue, CCSM comparison, figure rebuild, etc.).
- The source description unambiguously matches one category.
- The question is about preference rather than analytical consequence.

**Maximum questions per session start: 3.** Present all questions together in a single block, not sequentially. Use multiple-choice or short-answer format where possible.

**Question format:**

```text
Before starting, I have [N] quick question(s) that would affect the analysis:

1. [Question — specific, one sentence, with options where possible]
2. [Question — only if genuinely needed]
3. [Question — only if genuinely needed]

If you prefer to proceed with defaults, just say "use defaults" or "go ahead" and I will start immediately.
```

**If the user says "go ahead" / "use defaults" / "just start":** Apply all relevant defaults, state them in the context acknowledgement, and proceed. Never halt the analysis waiting for clarification.

**Materiality examples — when to ask:**

| Situation | Ask? | Reason |
|---|---|---|
| Source = "sand" (no other context) | Yes — 1 question | Marine vs desert changes every TFBS call |
| Source = "soil" | No | Terrestrial plant default applies cleanly |
| Source = "beetle found on kelp" | Yes — 1 question | Insect vs marine; ask which is the isolation substrate |
| Source = "Amazon River fish" | No | Freshwater Category 6 — unambiguous |
| User says "MRSA inactive" with no other context | Clarify the measurement/source only if material | Preserve the supplied negative context and its provenance; there is no positive default to override |
| No bioactivity mentioned | No assay-target assumption | Record NOT_SUPPLIED / NOT_OBSERVED, empty assays and NOT_ESTABLISHED linkage |
| Source = "Monterey Bay sediment" | No | Marine Category 2 — unambiguous |
| Source = "from a patient" | No | Vertebrate Category 5 — unambiguous |
| Source = "isolated from seaweed" | No | Marine Category 2 — unambiguous |
| Source = "lichen from the Alps" | No | Bryophyte/lichen Category 3 — unambiguous |
| Source = "isolated from salmon" | No | Marine Category 2 — fish = marine flag |
| Assembly Very Poor AND no host given | Yes — 1 question | Ask if host known before committing to full ecological synthesis |
| Genus is Salinispora, source not stated | Yes — 1 question | Marine genus; flag changes extraction and TFBS materially |
| Genus is Streptomyces, source not stated | No | Terrestrial plant default statistically correct |
| User says "isolated from a garden" | No | Terrestrial plant — do not ask what type |
| User says "from compost" | No | Terrestrial plant — do not ask what it contained |
| User says "isolated from ant" | No | Insect/arthropod Category 4 — unambiguous |

**Logging:** Record in the audit log:

```text
Pre-analysis clarification: [Asked N question(s) / No questions — defaults applied]
Questions asked: [list or "none"]
User response: [verbatim or "use defaults"]
Defaults applied: [list all defaults active for this session]
```

---

## Full Analysis Mode — Active Override

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#full-analysis-mode--active-override).

## §2B — Batch Plan Protocol

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#2b--batch-plan-protocol).

## SECTION 1 — Session Startup Checklist

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-1--session-startup-checklist).

1b. **Record supplied provenance and typed bioactivity metadata.** Retain confirmed or uncertain host/source as declared; absence does not establish a terrestrial or marine origin. With no supplied bioactivity data, use NOT_SUPPLIED / NOT_OBSERVED, no assay targets and NOT_ESTABLISHED locus/compound linkage. Supplied observations remain strain/extract context. Continue within the user’s authorized scope where missing fields are not required; clarify only a material unresolved input.

1c. **Run Metadata Conflict Audit.** Compare current-session strain metadata against uploaded files, master tables, prior reports, project-memory snapshots, reference implementation rows, and model memory. If host/source, habitat category, taxonomy, bioactivity, assembly quality, or prior BGC highlights conflict, treat current-session user confirmation as highest priority unless the user says otherwise; log the conflict; mark affected ecology, CCSM, cross-habitat, and manuscript-facing claims as `metadata-sensitive`; and do not reuse prior habitat-specific claims until reconciled.


1f. **Preserve the producing inventory’s identity map.** The current constructor reads admitted GenBank records, orders explicit chromosome labels before plasmid labels and then unknown/contradictory labels, with lexical source-name ordering within groups. It deduplicates its explicit record/region/bounds/products key before assigning sequential `BGC001` aliases. This is not JSON FASTA-input order and a changed admitted source set can change aliases.

Copy each individual locus as `strain / full node-or-contig / region / BGC alias` from one bound source record, with archive/member hashes. Do not renumber a saved package, invent a missing component or infer that an alias identifies the same physical locus across re-extractions. Reconcile the source map before cross-session reuse; keep missing/conflicting identity as a hold.



## SECTION 2 — Input File Inventory and Source Roles

### Identifier Conventions

> **Strain identifiers:** Use your existing strain ID, isolate number, or collection code exactly as it appears in your records — notebooks, databases, and publications. Do not renumber or relabel strains to fit this workflow. The prompt uses `[Strain ID]` as a placeholder in instructional positions throughout. Worked examples in §25, §26, and §41.12 use the reference project's identifiers (AS-XXX format) — treat these as illustrations of a populated dataset, not required naming conventions.

> **Isolate source identifiers:** The source of each strain is recorded as `[Host]` throughout. This field accepts any level of specificity your data supports: a host species binomial, a taxonomic group, a habitat type, a substrate type, or an environmental description. Default to `[Host]` when the isolate source is a specific organism; use `[Habitat]` when the source is an environmental context without a specific host. The prompt does not require or prefer one level of specificity over another.

> **Habitat categories:** Define your own isolate source groupings at session start. The prompt uses `[Habitat]` as a placeholder in instructional positions. Category names used in §25, §26, §41.7, and §41.12 — Hymenoptera, Bryophyte-Lichen, Attine, Mushroom — are worked examples from the reference project showing what a populated multi-habitat dataset looks like. Replace with your own category names.

### Master files

| File | Contents | Priority |
|---|---|---|
| `master_bgc_[project].json` | All strains, full BGC data, taxonomy, corrected counts | Essential for project-wide BGC analysis |
| `Master_Strain_List_[project].xlsx` | Full strain collection, bioactivity, genus, [Host], location | Essential for bioactivity/taxonomy/figures |
| `[Manuscript_name].docx` | Current manuscript | Manuscript work |
| `Bioactivity_Predictions_[project].xlsx` | Compound predictions and mechanisms | Compound prioritization |
| `Supplementary_Methods.pdf` | Protocols/methods | Methods writing |
| antiSMASH `[Strain ID].zip` | Strain-specific antiSMASH output | Strain analysis |
| `[Strain ID]_Project_Memory_Snapshot_YYYY-MM-DD.json` | Compact prior-session summary | Fast context recovery |

### Strain set accounting

Define your strain set composition at session start: total n, counts per [Habitat] category, and any special subsets. State this explicitly in the context acknowledgement.

*Reference project example:* [Habitat 1] n=20, [Habitat 2] n=6, [Habitat 3] n=10, [Habitat 4] n=1, Total n=37.

---

## SECTION 3 — antiSMASH ZIP / JSON Parsing Pipeline

### Primary rule

For the current native BGC inventory, admitted region GenBank records are primary, with an all-GenBank retry only when the region read returns no records. JSON and ClusterBlast text supply separately scoped evidence channels; a partially successful region read is not a complete fallback/reconciliation guarantee. Retain member admission/warnings and the producing inventory rather than rebuilding current aliases from a freehand JSON pass.

### Parsed per-BGC fields

For every BGC, extract or calculate:
- Strain ID, Record/contig ID, Contig length, BGC number, BGC coordinates, BGC length
- Products/classes, Edge status (Interior / Edge / Full-contig), Corrected BGC contribution
- **Architecture Confidence grade (A–E) — see Section 31**
- RiQ score, Novelty tier, KCB top hit, KCB cumulative score, KCB protein hit count
- Dereplication verdict, Priority tier
- TTA count — from JSON TTA module (preferred), region GBK nucleotide sequence, or uploaded FASTA; designate T? only if all three sources are exhausted and state which was tried
- bldA tier, TFBS hits and induction recommendations
- Coverage flag, HGT flag, Key diagnostic domains, Notes/caveats

**LMPKS cross-contig scan (v7.5.1):** After extracting per-BGC domain data, additionally extract ALL mod_KS, hyb_KS, and tra_KS domain hits from CDS features across the entire record (not only within annotated BGC coordinates). Record locus tag, bitscore, and contig for each hit. This genome-wide mod_KS inventory feeds the LMPKS Fragment Accumulation check in Section 42. If total mod_KS count across all contigs reaches ≥4, automatic LMPKS triggers fire per Section 42.2.

---

## SECTION 4 — Assembly, BGC Inventory, RiQ, and Corrected BGC Counts

### Edge status rules

```text
if contig_length <= 0:                 edge_status = "Unknown"
elif (end - start + 1) >= 0.95 * contig_length:
                                       edge_status = "Full-contig"
elif is_circular:                      edge_status = "Interior"
elif start <= 5000 or contig_length - end <= 5000:
                                       edge_status = "Edge"
else:                                  edge_status = "Interior"
```

These are software geometry labels, not proof of pathway completeness or exact missing genes. Preserve Unknown separately; the Full-contig test precedes the circular exception.

### Corrected BGC count

```text
Corrected = Interior + 0.5 × Edge + 0.25 × Full-contig
```

### Assembly quality tier (project-wide)

| Tier | Interior BGC % |
|---|---:|
| Good | ≥70% |
| Moderate | 45–69% |
| Poor | 20–44% |
| Very poor | <20% |

### BGC Inventory table — required columns (v7.4)

**Current identity note:** copy strain / full node-or-contig / region / BGC alias from the producing inventory and retain its source hash/map. Current aliases follow admitted GenBank record ordering/deduplication, not JSON FASTA-input order; changed source admission requires identity reconciliation rather than assuming stable alias numbering.


The BGC inventory table must include these columns in order:

| BGC # | Node | cLen kb | bLen kb | ES | Products | **Arch** | **LMPKS** | RiQ | Novelty | KCB top | Cum | Priority | bldA |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

The **Arch** column (Architecture Confidence grade A–E, per Section 31) is required in the inventory table, KCB sweep table, Excel workbook BGC_Inventory sheet, and every Mode B §1 overview table.

The **LMPKS** column records the rescue grade (LMPKS-A through LMPKS-X) assigned by Section 42 for T1PKS BGCs. Enter "—" for non-PKS BGCs and for BGCs where no trigger fired. Do not leave blank — enter either a rescue grade or "—".

> **Cross-strain hook (v7.5):** After completing the BGC inventory for any strain, add a row to the `CrossStrain_Family_Seeds` sheet (Section 35) and check whether any BGC class now reaches the ≥3-strain threshold triggering CCSM Phase 2 (Section 41.6).

> **LMPKS hook (v7.5.1):** After completing the BGC inventory, check the automatic trigger conditions in Section 42.2 before proceeding to the KCB sweep.

### RiQ extraction

Always use `RegionToRegion_RiQ`, not `ProtoToRegion`, when available.

### Novelty tiers

| RiQ | Label |
|---|---|
| ≥0.85 | Likely known |
| 0.50–0.85 | Possibly novel |
| <0.50 | Potentially novel |
| Missing / held RiQ | Comparison unavailable or held; do not convert to no MIBiG match or novelty evidence |

### Fragmentation checks

Flag likely fragmentation artifacts:
- >5 solo T1PKS BGCs <10 kb on tiny full-contig contigs
- Repeated identical KCB top hits across multiple small BGCs
- High cumulative score with only 2–3 protein hits
- Saccharide or terpene-precursor labels matching macrolide/glycopeptide/T2PKS KCB hits

*Reference project calibration examples:* AS-XXX: 72→49 corrected; AS-XXX: 50→42 corrected; AS-XXX: 22 saccharide BGCs confirmed genuine.

### POOR assembly protocol

When Interior % = 0: designate priority-product FC/Edge BGCs as HIGH*, produce Partial Mode B reports, add assembly warning box, flag long-read sequencing as Priority 1.

---

## SECTION 5 — KCB Sweep Module

### Trigger

Runs automatically after BGC inventory. Standalone: `Run KCB sweep on [Strain ID].`

### Primary source

Use `knownclusterblast/*.txt` files when present. JSON `clusterblast/knowncluster` is secondary.

### Extract for every BGC

Top MIBiG compound, BGC accession, cumulative BLAST score, protein hit count, product class, edge status, **Architecture Confidence grade**, RiQ score, priority tier, cross-hit warnings.

### Interpretation guide

The historical hit-count/cumulative-score bins below are not current scientific novelty, class-identity or full-reference-coverage criteria. A cumulative score is not a percentage, and score/protein-hit projections can use different selected comparators. Retain the exact source member, rank, accession, matched query set, denominator and coverage state. A missing/held/failed channel is unavailable; even a completed scoped no-hit result does not establish biological absence or product novelty.

Use the current source-derived comparison fields and explicit claim ceiling, rather than treating fixed count/score thresholds as “genuinely novel” or a “full match.”

### Cross-hit patterns to flag

| Pattern | Interpretation |
|---|---|
| Saccharide BGC → macrolide/glycopeptide KCB hit | Deoxysugar fragment from larger split cluster |
| High cumulative score + 2–3 protein hits | Assembly truncation likely |
| Two BGCs with identical top KCB compound | Possible split cluster — apply Section 30.3 cross-BGC gate |
| KCB class does not match antiSMASH product label | Hallucination-Trap trigger — apply Section 34 |

**LMPKS escalation (v7.5.1):** When KCB cumulative score is <1,500 (including zero) for any T1PKS BGC, this is an automatic trigger for Section 42 (LMPKS Rescue Workflow). Note the escalation in the KCB sweep table with the annotation "→ LMPKS §42 trigger 1".

### RiQ and KCB are orthogonal

Report RiQ and KCB separately with their source/denominator and missingness states. A high supplied RiQ plus zero, missing or held KCB does not independently establish conserved architecture, divergent proteins or discovery value.

### Outputs

1. PDF: `[Strain ID]_KCB_Sweep_AllBGCs_YYYY-MM-DD.pdf`

---

## SECTION 6 — Domain-Level Analysis

For each BGC, extract all TIGRFAM and PFAM domain hits within coordinates plus 3 kb padding. Sort hits per gene by bitscore descending.

### False-call checks

Always check for: `gene_kind = housekeeping` conflicting with high-bitscore biosynthetic domain evidence; antiSMASH SMCOG annotations contradicted by domain evidence; DUF3516 (PF12029) incorrectly labeled as helicase.

**LMPKS domain extraction (v7.5.1):** For all T1PKS BGCs, extract the following additional fields beyond the standard domain hit list: KS subtype (mod_KS / hyb_KS / ene_KS / tra_KS / itr_KS), PKS_AT substrate prediction (malonyl / methylmalonyl / methoxymalonyl), reductive loop completeness per module (KR/DH/ER), presence of PKS_Docking_Nterm and PKS_Docking_Cterm, and TE / Abhydrolase_1 domain presence. These fields are required for Section 42 module architecture reconstruction.

---

## SECTION 7 — NRPS/PKS Module Architecture

For NRPS, NRP-like, T1PKS, T2PKS, PKS-NRPS hybrid BGCs, extract module architecture and substrate predictions. For each A-domain record Stachelhaus aa10/aa34 scores, best substrate, condensation domain type, and active-site motifs.

---

## SECTION 8 — Diagnostic Domain Combinations

| Domains present | Assignment |
|---|---|
| TIGR04462 + TIGR04460 | Enduracididine-type NRPS; lipid II inhibitor class |
| TIGR03550 + TIGR03551 + TIGR03620 | F420-embedded polyketide |
| PF12029 + TIGR02353 | NAPAA / poly-amino acid candidate |
| TIGR04363 + TIGR04364 | FxLD class-I lanthipeptide |
| PF19402 ×3 | Triple-precursor class-III lanthipeptide |
| PF00109 + PF02514 + TIGR01181 + PF01041 | Glycosylated T2PKS — apply angular vs linear disambiguation below before assigning compound class or isolation strategy |
| TIGR03604 ×2 | TOMM heterocyclic RiPP |
| PF00668 Cglyc-type + HHILLDG | Glycopeptide-type condensation |

| indsynth (BS ≥500; E ≤ 1e-100 preferred; cf. AS-XXX ctg182_7 reference: E=0, BS=1349.6) | **Indolocarbazole / chromopyrrolic acid scaffold** (rebeccamycin / staurosporine / AT2433-A1 / loonamycin / arcyriarubin class). Core biosynthetic enzyme is the chromopyrrolic acid synthase (StaD/RebD-type), which couples two tryptophan-derived indole units. indsynth is as class-definitive for indolocarbazoles as ene_KS is for enediynes — cumulative KCB = 0 is expected when the contig is truncated and does NOT indicate the class is absent (apply §34 "0% MIBiG cluster similarity" trap). Primary precedent: topoisomerase I inhibitor and/or kinase inhibitor; antitumor class. Anti-Candida activity via CaTop1 inhibition exists but is not specific — do NOT use as a dedicated Candida mechanistic link in §33.3 unless supported by fractionation data. Cross-check for Trp_halogenase (PF04820, BS ≥150) on same or adjacent contigs: if found → halogenated variant (rebeccamycin / AT2433 class); if absent → non-halogenated variant (arcyriarubin / staurosporine class). If Trp_halogenase is on a different contig, flag as split-pathway indolocarbazole candidate (§42.7). Apply §34 "indole masking indolocarbazole" trap if antiSMASH product label is "indole". Route to §37 indolocarbazole row. ⚠ Cytotoxicity caution required (staurosporine-class kinase inhibitors are highly cytotoxic — cytotoxicity-guided handling per standard lab SOPs; test HeLa IC₅₀ before bioassay-guided fractionation). |
| Ornithine-selective A-domain (by Stachelhaus code comparison to HslO/HslI from *Lysobacter enzymogenes* ATCC 29,214 or equivalent characterized HSAF synthetase) + iterative PKS-NRPS single-module architecture (single KS reused across extension cycles, detectable as one KS with multiple downstream ACP domains or anomalously high KS:ACP ratio in one ORF) | **HSAF / polycyclic tetramate macrolactam (PTM) class** (HSAF, 10-epi-HSAF, militarinone, frontalin-type). Sphingolipid (ceramide) synthase inhibitor — specific, well-characterized anti-Candida mechanism (CaCsg1/Lag1 target); award §33.3 Candida-specific mechanistic link (+2 WL) when Candida bioactivity is explicitly supplied with its source (never default-assumed). Also active against filamentous fungal pathogens (*Botrytis*, *Fusarium*). Route to §37 HSAF/PTM row. Note: tetramate ring is acid-labile at pH <4 — do NOT use strongly acidic extraction conditions. |
| TIGR01720 ×2 | **Mannopeptimycin-type NRPS** (distinct from the enduracididine class above; both have unusual amino acids but different scaffolds). Cyclic glycopeptide antibiotic; lipid II inhibition via β-hydroxy-enduracididine residues; MRSA-active class. Supporting evidence: TauD hydroxylase (PF07366) and mannose-type glycosyltransferases co-located in BGC. Note: TIGR01720 and TIGR04462/TIGR04460 overlap in function — use TIGR01720 ×2 as the primary marker for mannopeptimycin-class assignment when distinguishing these two BGC types. Reference implementation: AS-XXX BGC#7 (TIGR01720 ×2, TauD, PF07366 ×3, 13-gene MIBiG match, 2026-01-08). |
| CarB (β-carbapenam synthetase, ATP-dependent bicyclase, BS ≥150) ± CarC (carbapenem C3-desaturase / tautomerase) | **Carbapenem β-lactam** (MM4550-type simple carbapenem or thienamycin-type complex carbapenem). Exceptionally rare in actinomycetes — flag as high-priority whenever detected. PBP (penicillin-binding protein) inhibitor class; MRSA-active; also Gram-negative active (broad spectrum). Confirm class with KCB vs MM4550 and thienamycin reference clusters. A β-lactamase or altered-PBP self-protection gene should be within 15 kb — absence is a §45 missingness flag and a required §36.4 reviewer attack target. Reference: AS-XXX BGC-05 (58% MIBiG to MM4550-type, interior BGC in poor assembly). |
| AHBA synthase (PF06353 / rifK-type; confirmed by co-occurrence of aminoDAHP synthase and aminodehydroquinase in the same BGC — these three enzymes are the committed steps of the 3-amino-5-hydroxybenzoic acid starter unit pathway) | **Ansamycin class** (rifamycin / geldanamycin / herbimycin / ansatrienin / mitomycin). AHBA (3-amino-5-hydroxybenzoic acid) is the committed starter unit — its presence defines the ansamycin class independent of PKS module count or KCB score. Mechanism depends on sub-class: rifamycin-type = RNA polymerase inhibitor (rpoB binding); geldanamycin-type = Hsp90 ATPase inhibitor. Cross-check ArrA/Arr-type ADP-ribosyltransferase resistance gene (§45 Tier 2) as concordant marker. Route to §37 ansamycin row. |
| APE_KS2 (arylpolyene-specific β-ketoacyl synthase 2; BS ≥200) ± Iterative-KS | **Arylpolyene (APE) pigment class** (flexirubin-type arylpolyenes, carotenoid-analogue bacterial pigments). APE_KS2 is class-definitive for arylpolyenes in the same way ene_KS is definitive for enediynes — it is not present in other polyketide families at this bitscore. Arylpolyene BGCs encode iterative type I PKS enzymes producing conjugated aryl-polyene chromophores responsible for yellow/orange colony pigmentation visible without instrumentation — the cheapest possible first-pass production screen. UV/Vis 420–450 nm is the primary chromophore handle. Common in Proteobacteria (Xanthomonas, Lysobacter, Pseudomonas, Burkholderia, Bacteroidetes) and some Actinobacteria. In fragmented assemblies, APE_KS2 is commonly found on tiny FC contigs (<10 kb) because the full APE pathway (8–15 genes) is rarely intact in short-read drafts — apply §42.7 split-pathway rescue logic for any APE_KS2 hit on a contig <10 kb. Route to §37 arylpolyene row. No cytotoxicity caution. No self-protection resistance gene expected. |
| PF00109 + PF02514 + TIGR01181 + PF01041 + angular-fold oxygenase (UrdE / LanV / GriF-type flavoprotein monooxygenase or UrdM-type Baeyer-Villiger oxygenase, BS ≥150) | **Angular T2PKS** (angucycline / griseusin / kinamycin / landomycin class). UV ~430 nm (aromatic chromophore). EtOAc extraction at pH 5. Note that kinamycin-class angular T2PKS may also carry a diazofluorene warhead (highly reactive — cytotoxicity caution). Isolation strategy differs from linear T2PKS — see §37. |
| PF00109 + PF02514 + TIGR01181 + PF01041 + linear cyclase (OxyTC / ActVI-ORF1 / TcmI-type cyclase, BS ≥150), absent angular oxygenase | **Linear T2PKS** (tetracycline / oxytetracycline / doxorubicin / tetracenomycin class). UV ~450–470 nm (anthraquinone/naphthacene chromophore). EtOAc extraction at pH 4–5. Anthracycline sub-class (doxorubicin-type) requires cytotoxicity caution. Distinguish from angular T2PKS by absence of angular-fold oxygenase and presence of linear cyclase. |

---


### 8.X Diagnostic gene weighting rule

Not all genes/domains carry equal interpretive value. Before making any BGC claim, Sapote must classify the evidence basis into one of five evidence-weight tiers:

| Tier | Name | Definition | Allowed claim |
|---|---|---|---|
| Tier 1 | Diagnostic marker | Rare or mechanistically defining gene/domain strongly associated with a narrow biosynthetic logic or compound family | Strong marker for [class/family] biosynthetic potential |
| Tier 2 | Class-supporting marker | Supports a chemical class or scaffold type but requires surrounding genes/domains | Consistent with [class/family] biosynthetic logic |
| Tier 3 | Context/tailoring marker | Informative only when paired with core biosynthetic logic, synteny, or pathway constellation | May support tailoring/decoration/pathway coherence |
| Tier 4 | Generic biosynthetic gene | Common across many unrelated pathways | Not product-specific; record only as background support |
| Tier 5 | Overinterpretation-risk gene | Frequently tempting but weak alone, including generic transporters/regulators/resistance-like genes | Do not use as primary evidence; require stronger context |

Fragmentation lowers product-identity confidence but does not erase diagnostic signal. A fragmented BGC carrying a Tier 1 diagnostic marker may outrank a complete region containing only Tier 4/Tier 5 genes.

### 8.X.1 Literature-backed diagnostic marker library placeholder

| Marker/signature | Candidate class/family | Evidence tier | Required context | Safe claim | Citation status |
|---|---|---:|---|---|---|
| NikJ/PolH-like radical-SAM PN enzyme | Peptidyl nucleoside / nikkomycin-polyoxin-like | Tier 1 candidate | Multiple neighboring nik/poly/pac-like genes or PN pathway constellation | Strong peptidyl-nucleoside-family signal; product unresolved unless chemistry exists | Needs curated VLD entry |
| PepM | Phosphonate | Tier 1 | Neighboring phosphonate genes strengthen call | Strong marker for phosphonate biosynthetic potential | Literature-backed |
| ene_KS / enediyne PKS cassette | Enediyne | Tier 1 | Enediyne neighborhood/cassette genes | Strong enediyne-like BGC signal | Literature-backed |
| DOIS / BtrC-like 2DOS marker | Aminocyclitol / aminoglycoside | Tier 1–2 | Aminotransferases/glycosyltransferases/aminoglycoside context | Supports aminocyclitol/aminoglycoside biosynthetic logic | Literature-backed |
| RiPP maturation enzyme + credible precursor | RiPP class | Tier 1–2 | Precursor peptide and class-specific maturation context | Supports [RiPP class] logic | Needs class-specific curation |
| Flavin-dependent halogenase | Halogenated NP potential | Tier 2–3 | In-cluster placement and substrate/scaffold logic | Supports possible halogenation; not product identity | Context-dependent |
| Generic ABC/MFS transporter | Export/uptake possible | Tier 4–5 unless literature-backed | BGC adjacency plus class-specific transporter evidence | Supportive only; not product identity | Context-dependent |
| Duplicated target/resistance gene near BGC | Self-resistance/target hypothesis | Tier 1–2 pattern | BGC proximity, duplication, divergence, HGT, or ARTS-style support | Increases follow-up priority; MOA hypothesis only | Literature-backed pattern |

## SECTION 9 — TTA Codon / bldA Gating

Count TTA codons in biosynthetic CDS features within every BGC.

> **Applicability note:** TTA codon / bldA gating is specific to actinomycetes (particularly Streptomyces and related genera). If your organism is outside this group, confirm whether bldA-dependent regulation is relevant before applying this section.

### TTA codon lookup order — try each source in sequence; stop at first success

**1. antiSMASH JSON TTA module (preferred)**

Path: `record['modules']['antismash.modules.tta_codons']['hits']`

Each hit has: locus_tag, location, strand. Count hits whose locus_tag belongs to a biosynthetic or biosynthetic-additional CDS within the BGC coordinate window.

```python
tta_mod = record['modules'].get('antismash.modules.tta_codons', {})
hits = tta_mod.get('hits', [])
tta_count = sum(
    1 for h in hits
    if bgc_start <= parse_loc(h['location']) <= bgc_end
    and is_biosynthetic(h['locus_tag'], record)
)
```

**2. Region GBK files from the antiSMASH ZIP**

Files: `[strain]/[NODE_X_...].region001.gbk` (one per BGC region). Count TTA codons in CDS features with `/gene_kind="biosynthetic"` or `"biosynthetic-additional"`.

**3. Original genome FASTA (if uploaded separately or present in ZIP)**

Locate CDS coordinates from the JSON features list, slice the nucleotide sequence, and count TTA in frame for biosynthetic CDS only.

**4. T? — only if steps 1–3 all fail**

State explicitly which source was tried and why it failed.

### bldA gating tiers

| TTA count | Tier | Culture requirement |
|---:|---|---|
| 0 | T1 | Liquid or solid |
| 1–2 | T2 | Liquid stationary or solid ISP2 |
| 3–5 | T3 | Solid ISP2/R5, 14+ days |
| 6+ | T4 | Sporulating solid media only |
| Not calculable | T? | State reason |

Include TTA count and bldA tier in: BGC inventory table, Mode B §1, Mode B §7, Fermentation card.

---

## SECTION 10 — TFBS Signals and Induction Conditions

Extract TFBS hits when available. Apply score thresholds from the induction guide table. Flag any regulator appearing in ≥6 BGCs as a **genome-wide antibiotic regulatory network**.

> **Applicability note:** The regulators and thresholds in this table are validated for actinomycetes. For other bacterial groups, confirm TFBS model applicability before interpreting hits.

| TFBS | Score threshold | Recommended induction condition |
|---|---:|---|
| FuR | ≥3 hits, any score | Iron limitation: Chelex-treated media |
| DmdR1 | ≥18 | Iron limitation; Fe-dependent repression |
| DasR | ≥20 | GlcNAc 1–25 mM in minimal media |
| LexA | ≥18 | Sublethal DNA damage: MMC or UV, with caution |
| AfsQ1 | protein-level call | Nitrogen/phosphate limitation |
| BldD | ≥18 | Stationary phase; solid media preferred |
| ANR | ≥18 | Microaerophilic or anaerobic conditions |
| OsdR | protein-level call | Solid media, full sporulation, 14–21 days |
| IolR | ≥18 | Inositol-supplemented minimal media |
| NtrC | not detected (Release 2) | Nitrogen limitation |
| ZuR | ≥18 | Zinc limitation (low-Zn minimal media or TPEN 1–10 µM) |
| SARP | ≥3 hits | Phosphate limitation (low-KH₂PO₄ minimal) |
| GBL/AdpA | ≥18 | Stationary phase + 10% conditioned medium |
| CopR | protein-level call | Copper limitation: CuSO₄ 0.1 µM (vs 10 µM standard) |
| CatR | protein-level call | Oxidative: H₂O₂ 0.1 mM pulse, then remove |
| HypR | protein-level call | Oxidative: H₂O₂ 0.5 mM, or MMC 0.1 µg/mL 2h pulse |
| NrtR | protein-level call | NAD limitation: niacin-restricted minimal media |

> CopR, CatR, HypR, AfsQ1, and NrtR currently have no calibrated DNA motif in `TFBS_MOTIFS`; they are reported from the protein-level regulator scan (REGULATOR_PATTERNS / antiSMASH annotation) and must be marked `(protein-level call)` until Release 2 motif models are added.

**Fermentation Card deliverable:** when a strain reaches Layer C, translate the TFBS + RiQ + bldA outputs into a one-page Fermentation Card — priority BGC ranking (★), induction conditions ranked by BGC coverage, extraction by compound class, dereplication verdicts, solid-media/bldA-T4 notes. Format and the full regulator→induction lookup: `docs/history/retired_458/fermentation_card_exemplar.md`.

---

## SECTION 11 — Dereplication Verdicts and Novelty Language

| RiQ / evidence | Verdict | Action |
|---|---|---|
| ≥0.95 + matching A-domain predictions | CLOSE | Confirm only by CAS/HRMS |
| 0.85–0.95 or ≥0.95 with divergent tailoring | VERIFY-FIRST | HRMS before isolation |
| 0.70–0.84 + unusual tailoring | STRUCTURAL VARIANT | Medium/high follow-up |
| <0.70 | POSSIBLY / POTENTIALLY NOVEL | Standard discovery priority |
| No KCB + no/low RiQ | POTENTIALLY NOVEL, weakly anchored | High novelty; class cautious |

---

## SECTION 12 — Coverage and HGT Flags

Flag BGC-containing contigs with coverage >1.5× genome mean as HIGH COV. Scan for transposases, integrases, phage integrases, Lsr2/H-NS-like silencers within BGCs and 5 kb flanking regions (PFAM/TIGRFAM ≥40 bitscore). Classify positions as Internal, Boundary (<2 kb), or Flanking (2–5 kb).

---

## SECTION 13 — Neighborhood Comparison and Medium-BGC Rescue

For each MEDIUM BGC: count biosynthetic genes, identify divergent domains (bitscore ≥150), and upgrade to HIGH when warranted.

**Divergence classes:** EXTENDED / SUBSTITUTED / NOVEL CONTEXT / FRAGMENTED

**Automatic upgrade triggers:** Phytoene synthase in non-terpene context; MshC; F420 enzymes (CofG/CofH/FbiB); DUF1702 ×2; HypF+HypE; CobN cobaltochelatase.

**LMPKS split-pathway cross-contig detection (v7.5.1):** For large modular PKS clusters fragmented across multiple contigs, use Section 42.7 (Split-Pathway Rescue) instead. The cross-contig module accumulation protocol in Section 42.6 supersedes the neighborhood comparison for T1PKS BGCs with docking domains on different nodes.

---

## SECTION 14 — Taxonomy Integration

Source priority: paper-specific strain tables > master strain list > gap-fill source > user confirmation > model memory (pointer only).

### 14.1 Taxonomy preflight for assembled FASTA inputs

When the user supplies an assembled FASTA but no confident genus or species assignment, run a taxonomy preflight before BGC interpretation is finalized. This is especially important for non-actinomycete, Gram-negative, environmental, and workflow-validation test cases.

Minimum preflight status field:

```text
Taxonomy preflight status: [user-confirmed / file-confirmed / 16S extracted from assembled FASTA / whole-genome ANI-GTDB available / unresolved / deferred]
Taxonomy evidence used: [user statement, FASTA-derived 16S, BLAST result, GTDB-Tk, ANI, CheckM/quality report, antiSMASH taxon label, other]
Genus call: [genus / unresolved]
Species call: [species / no species-level claim]
Claim-safety note: [16S genus-level only / ANI needed for species-level / conflicting evidence / contamination suspected]
```

### 14.2 ContEst16S / EzBioCloud assembled-FASTA workflow

If a user has only an assembled FASTA, the workflow may point them to EzBioCloud ContEst16S (`https://www.ezbiocloud.net/tools/contest16s`) as a practical external route to extract 16S rRNA gene sequences from assembled prokaryotic genomes. The user can then BLAST the extracted 16S sequence(s) against EzBioCloud or another curated 16S database to obtain a genus-level taxonomic anchor. EzBioCloud also provides whole-genome identification workflows for assembled genome FASTA uploads, but Sapote should keep the evidence type explicit.

Recommended user-facing note:

```text
Taxonomy preflight option: If you have an assembled FASTA, use EzBioCloud ContEst16S to extract candidate 16S rRNA gene sequences, then BLAST those sequences against EzBioCloud or another curated 16S database. Treat this as a genus-level anchor unless supported by whole-genome ANI/GTDB or high-confidence species-level evidence.
```

### 14.3 16S interpretation guardrails

- 16S extracted from an assembly is useful for genus confirmation, contamination checks, and detecting multiple divergent 16S copies.
- Do not use 16S alone to make strong species-level claims in difficult genera or closely related complexes.
- If multiple 16S copies disagree at genus level, flag possible contamination, assembly mixture, or taxonomic conflict and route to the Missingness Register.
- If the genus inferred from 16S conflicts with antiSMASH metadata, file names, prior reports, or user-provided taxonomy, run the Metadata Conflict Audit and mark taxonomy-sensitive claims.
- For publication-facing species claims, prefer whole-genome ANI, GTDB-Tk placement, digital DDH where appropriate, and/or phylogenomics.

### 14.4 Taxonomy-sensitive downstream routing

Taxonomy affects:

- TTA/bldA interpretation — actinomycete-specific unless otherwise justified.
- TFBS defaults and ecological analogies.
- Gram-negative KCB false-positive traps.
- QS signal routing.
- Resistance-gene interpretation and HGT guards.
- Compound-class plausibility, especially actinomycete-specific KCB matches in Proteobacteria.

If taxonomy remains unresolved, proceed with BGC analysis but label outputs as `taxonomy-sensitive` and avoid organism-specific claims beyond the evidence supplied.

---

## SECTION 15 — Strain-Level Deliverables

### 15.1 Layperson's Guide PDF
Filename: `[Strain ID]_Laypersons_Guide_YYYY-MM-DD.pdf`

### 15.2 Deep Dive Synopsis PDF
Required sections: strain & assembly table, novelty profile, full BGC inventory table (with Arch Confidence column), KCB sweep summary, **Reviewer Attack Simulation** (see Section 36), executive summary (5 bullets + synthesis paragraph), assembly warning box if applicable, fragmentation pattern note for very-poor assemblies, audit log.
Filename: `[Strain ID]_Deep_Dive_Synopsis_YYYY-MM-DD.pdf`

### 15.3 Historical eight-section Mode B design (not current profile completion)

For current authored cards, select the native named contract/template, preserve its exact titles and verify the actual authored file under the same full48/current50_v2 choice. The following retained §1–§8 layout records the historical design only and is not a substitute for that current profile:

**§1** Overview table (include Architecture Confidence grade + Evidence Traceability compact block) | **§2** Gene-by-gene domain analysis table (see §6 for extraction method). For every CDS within BGC coordinates ± 3 kb padding: locus tag, strand, location, gene_kind, all PFAM hits (ID/name/bitscore descending), all TIGRFAM hits (ID/name/bitscore descending), functional assignment derived from domain evidence (not antiSMASH product label), and functional flag (biosynthetic / resistance / transport / regulatory / housekeeping). This table is the primary analytical layer. It must be completed before §3–§8 are populated. It is not abbreviatable within a Full Depth Mode B report and cannot be deferred to a later step. | **§3** Module architecture (NRPS/PKS) | **§4** Biosynthetic pathway hypothesis (include Evidence Traceability expanded block) | **§5** MIBiG/KCB comparison | **§6** Mechanistic link to bioactivity | **§7** Isolation strategy | **§8** Claim-safety audit

Apply Section 30.1 Mode B Depth Gate before finalising every §4.
Apply Section 31 Architecture Confidence grade to §1.
Apply Section 32 Evidence Traceability blocks to §1 (compact) and §4 (expanded).

Filename: `[Strain ID]_NODE_[N]_BGC[N]_Mode_B_[Class]_YYYY-MM-DD.pdf`

### 15.4 Edge/FC BGC presentation (v9.7.147)

Edge and full-contig BGCs are presented with equal structural depth to Interior BGCs. Assembly boundary status is a metadata flag, not a depth limiter.

**Minimum required for every edge/FC BGC, regardless of corrected rank:**
- §1: Identity and contig/region citation.
- §3: Boundary and truncation statement. This is where the edge caveat lives.
- §4: Gene table or gene-by-gene interpretation for all CDS visible on the contig.
- §5: Core biosynthetic logic from the visible evidence.
- §11: Product-family interpretation with explicit truncation caveat.
- §19: Claim ceiling — what the evidence supports and what it cannot support given the boundary.
- §20: Next actions — include long-read sequencing and/or RG-GMCI reconstruction when applicable.

The boundary caveat belongs in §3 and §19, not as a reason to reduce depth everywhere else.

For edge/FC BGCs where evidence is insufficient for interpretation, such as single-gene contig fragments with no diagnostic domains, a one-paragraph minimum candidate card is acceptable with: class/product hypothesis if available, boundary status, KCB top hit if any, one interpretive sentence, and why full interpretation is not possible. This is the minimum, not the default.

### 15.5 KCB Sweep PDF + JSX dashboard
See Section 5.

### 15.5.1 LMPKS Rescue Report PDF
Generated automatically when any Section 42.2 trigger fires. If no trigger fires, include a one-page null result stating which criteria were checked and the outcome.
Filename: `[Strain ID]_LMPKS_Rescue_Report_YYYY-MM-DD.pdf`

### 15.6 Chapter PDF (if applicable to host/habitat)
Filename: `[Strain ID]_NODE_[range]_Chapter_YYYY-MM-DD.pdf`

### 15.6.1 CCTT Trigger Report PDF
Generated when any §43 trigger fires. One-page null result if no trigger fires.
Filename: `[Strain ID]_CCTT_Trigger_Report_YYYY-MM-DD.pdf`

### 15.6.2 Resistance Gene Confirmation Report PDF
Generated from Section 45 scan. One-page null result if no Tier 1/2 markers found within proximity rule.
Filename: `[Strain ID]_ResistanceGene_Confirmation_YYYY-MM-DD.pdf`

### 15.7 Fermentation Card A5 PDF
Filename: `[Strain ID]_Fermentation_Card_YYYY-MM-DD.pdf`

### 15.8 Compiled Master PDF

Required order (v7.9 — 20+ items):

1. Cover
2. Production TOC with accurate page numbers
3. Layperson's Guide
4. Deep Dive Synopsis
5. KCB Sweep
5.5. LMPKS / FLBR Rescue Report (one-page null result if no Section 42/51 trigger fired)
5.6. CCTT Trigger Report (one-page null result if no T43 trigger fired)
5.7. Resistance Gene Confirmation Report (one-page null result if no Tier 1/2 markers found)
6. antiSMASH Hallucination-Trap Audit
7. Mode B reports in BGC# order
8. Cross-BGC / split-pathway appendix (if applicable)
9. Chapter (if applicable)
10. Ecological Synthesis
10.1. Chitin / Glycan-Active Defense output (Section 44)
11. Wet-Lab Decision Matrix
12. Metabolomics Readiness Summary
13. Reviewer Attack Simulation
14. Recommended Figures
15. Missingness Register
16. Fermentation Card
17. Project Memory Snapshot (MD version) + Audit Log

Apply Section 30.5 PDF generation rules throughout.

Filename: `[Strain ID]_Complete_Analysis_Compilation_YYYY-MM-DD.pdf`

### 15.9 Ecological Synthesis PDF
See Section 17. Filename: `[Strain ID]_Ecological_Synthesis_YYYY-MM-DD.pdf`

### 15.10 Project Memory Snapshot
See Section 40. Files: `[Strain ID]_Project_Memory_Snapshot_YYYY-MM-DD.json` + `.md`


### 15.11 PDF Style Standard and bioactivity-default display requirements (v7.9)

**Historical v7.9 style recipe.** The `sapote_pdf_styles.py` upload and helper names below are retained design history. For a current compiled report, follow [Postseal readers — PDF routes](POSTSEAL_READERS.md#pdf-routes) and the selected renderer owner; `compile-report` dispatches through `tools/md_to_pdf.sh`, while Mode B Markdown export has its packaged `mamey/markdown_pdf.py` renderer. The current compiled-report guide describes ReportLab as primary and Pandoc/XeLaTeX as fallback. Do not create a substitute style module merely to satisfy this archived recipe.

Every compiled PDF must include a visible metadata/defaults block in the opening pages with:
- Workflow version
- Strain ID
- Taxonomy status
- Host/source status and ecological category
- Typed bioactivity metadata/observation state and source receipt; NOT_SUPPLIED / NOT_OBSERVED when absent, without creating assay targets
- Assembly tier
- BGC count and corrected BGC count
- Date of execution

When no strain-specific assay data are supplied, include an explicit missing-metadata note in the opening block and audit log:

```text
Bioactivity metadata NOT_SUPPLIED; observation NOT_OBSERVED; no assay target or outcome inferred. Locus/compound linkage NOT_ESTABLISHED.
```

PDF layout requirements:
- Every major deliverable starts on a new page with a section banner.
- Long tables may split across pages, but headers must repeat.
- Dense BGC tables must use wrapped text, not clipped text.
- Every Mode B report begins with a compact one-page overview block before gene-by-gene detail.
- Use consistent callout boxes for supplied metadata, missing/unavailable evidence, caution, routing priority and deferred notes; never use a default-assumed assay label as an observation.
- Compiled master PDFs must include bookmarks/outlines for all major sections and for every Mode B BGC report.


---

## SECTION 16 — Cross-Habitat Figures

**Trigger:** `Update/rebuild the cross-habitat figures.`

**Required data:** Master JSON + Master strain spreadsheet

**Color palette — define one color per [Habitat] category:**
```python
C_HAB1 = '#1d4e6b'   # [Habitat 1]
C_HAB2 = '#2a5c3a'   # [Habitat 2]
C_HAB3 = '#7a3520'   # [Habitat 3]
C_HAB4 = '#c06840'   # [Habitat 4] — optional second batch or additional category
# Reference project: C_HAB1=Hymenoptera, C_HAB2=Bryophyte+Lichen, C_HAB3=Attine Batch 1, C_HAB4=Attine Batch 2
```

**Figure set:**
- Fig 1: BGC strip plot
- Fig 2: Genus composition
- Fig 3: Bioactivity vs inhibition
- Fig 4: Bioactivity by genus
- Fig 5: Novelty % vs BGC count
- Fig 6: [Genus] cross-[Habitat] comparison
- Fig 7: Assembly quality
- Fig 8: BGC type composition

**Universal rules:** No date watermarks. Integer ticks. PDF 200 DPI bbox_inches='tight'. Filename: `Fig[N]_[Description]_YYYY-MM-DD.pdf`.

---

## SECTION 17 — Ecological Synthesis Module

**Trigger:** `Run ecological synthesis for [Strain ID]. [Host]. [Habitat context].`

Also triggered automatically at end of full v7.9 analysis when host metadata is available.

**Fast-mode trigger:** `Run fast ecological synthesis for [Strain ID]. [Host].`

### 17.1 Purpose

Translate BGC-level data into testable ecological hypotheses about how predicted chemistry maps onto host biology, ecology, and pathology. Every hypothesis must cite specific BGC evidence (node, locus tag, domain, bitscore, TFBS score). All ecological interpretations are labeled as hypotheses requiring experimental validation.

### 17.2 Data Inputs Required

Run after all Mode B reports are complete. Requires: [Host] identity, isolation substrate, strain bioactivity, TFBS network (score ≥18), polysaccharide-degrading domains, bldA tier, compound class, HGT flags, RiQ, KCB top hit.

### 17.2A Evidence and Confidence Labels

| Evidence basis | Allowed claim strength |
|---|---|
| Direct assay | Strain-level activity; no compound-level causation without fractionation |
| Bioinformatic BGC-local evidence | "contains domains within BGC coordinates consistent with" / "is predicted to encode" |
| Genome-wide functional scan evidence | "full-proteome scan identifies [N] secreted candidates consistent with [capacity]"; stronger ecological capacity support than BGC-local evidence when method is stated |
| Regulatory prediction | "predicts" / "consistent with regulated activation under..." |
| Ecological analogy | "could represent" / "is hypothesised to" |
| Literature verified | Cited, cautious; no untested strain-specific causality |

Confidence: High / Medium / Low / Unknown

If evidence is unavailable, unrun, failed or incomplete, retain that state. Only a completed scoped search with a recorded negative result can support a scoped no-hit statement; neither missingness nor a no-hit result establishes biological absence or an ecological story.

### 17.3 Step 1 — Cross-Genome TFBS Regulatory Coupling Table

Extract all TFBS hits ≥18 across all BGCs. Flag regulators in ≥2 BGCs as coupled networks. Flag ≥6 BGCs as genome-wide antibiotic regulatory networks.

**Host-specific TFBS ecological trigger lookup:**

> *Define [Habitat] column headers to match your project's isolate source categories. The table below is a worked example from the reference project.*

| TFBS | [Habitat 1] | [Habitat 2] | [Habitat 3] |
|---|---|---|---|
| DmdR1 | Intracolony Fe²⁺ scarcity | Fe²⁺ scarcity in gut | Iron limitation in acidic substrate |
| DasR | Moulting exuvia; fungal chitin | Exoskeleton moulting | Insect debris on substrate |
| IolR | Pollen phytate/inositol | Fungal mycelium inositol catabolism | Lichen polyol degradation |
| ANR | Sealed brood cell O₂ depletion | Sealed garden chambers | Waterlogged microaerobic zones |
| LexA | Hemocyte ROS burst; honey H₂O₂ | Formic acid DNA damage | UV-induced damage; desiccation |
| OsdR | Colony overwintering; sporulation | Long-term fungal garden management | Seasonal dormancy |

**Important (general rule):** Always interpret TFBS hits in the ecological context of the [Host] or [Habitat]. Generic stress regulator dismissal is a common error when habitat-specific metabolite signals are present.

> **CGAD coupling (v7.6):** When Section 44 reports Moderate/High chitinolytic capacity, the DasR row must be interpreted as a chitin-responsive antibiotic-activation signal (GlcNAc liberated from chitin de-represses DasR), not a generic stress signal. Cite the secreted-chitinase loci as the substrate-supply evidence for the DasR interpretation.

### 17.4 Step 2 — Polysaccharide Substrate Coupling Analysis

Scan all BGCs for GH/LPMO/t2fas/CotH domains co-encoded within cluster boundaries. Flag BGC with polysaccharide domain + cognate TFBS as candidate polysaccharide-gated BGC.

A null result (no polysaccharide-gating network detected) is ecologically informative and must be reported explicitly, not omitted.

> **CGAD input (v7.6):** Section 44 chitinase/LPMO loci are a primary input to this polysaccharide-coupling scan.


**Multi-siderophore capacity flag:**

After completing the per-BGC siderophore scan, count all siderophore-class BGCs
(catecholate, hydroxamate, mixed-type, or NRPS siderophore-like BGCs carrying
diagnostic domains including ArCP, Ent/VibH-type condensation, HMGS, IucA/IucC,
NIS synthetase, or siderophore-class KCB hits with RiQ ≥ 0.30).

If ≥ 3 distinct siderophore-class BGCs are identified, raise the
MULTI-SIDEROPHORE CAPACITY flag and:

1. Compile a standalone iron-acquisition capacity table in the Ecological
   Synthesis PDF:

   | BGC ID + node | Siderophore class | KCB compound | Score / RiQ |
   | Diagnostic domains | Edge status | Notes |

2. Generate one §17.10 ecological hypothesis for iron competition in the host
   niche. The testable prediction must specify:
     (a) Culture condition: iron-limited media (e.g., Chelex-treated, or
         defined low-iron minimal media).
     (b) Detection method: CAS assay for siderophore activity, or LC-MS EIC
         for the specific siderophore compound class.
     (c) Which BGC(s) the experiment will test, by genetics or fractionation.

3. Note the ecological interpretation: multi-siderophore capacity is consistent
   with competitive iron acquisition in a microbe-dense environment (attine
   garden, soil, rhizosphere, biofilm). This is a mechanistically distinct
   ecological claim and does not require antimicrobial bioactivity data.

A null result (< 3 siderophore BGCs) does not require explicit reporting beyond
the standard BGC inventory.

### 17.5 Step 3 — bldA Tier → Host Developmental Mapping

> *Define [Habitat] column headers to match your project's isolate source categories. Cell content below is a worked example from the reference project.*

| bldA Tier | [Habitat 1] | [Habitat 2] | [Habitat 3] |
|---|---|---|---|
| T1 | Active foraging season | Active fungal garden | Growing season / wet phase |
| T2 | Late-season workers | Late-season contraction | Seasonal transition |
| T3 | Autumn colony stress | Pre-dormancy reduction | Early desiccation |
| T4 | Deep overwintering | Dormant phase | Full dormancy |

### 17.6 Step 4 — Host Disease Defense Matching

> *The table below is a worked example from the reference project. Replace [Host] entries and pathogens with those relevant to your isolate sources.*

| Host / Isolate source | Pathogen | Matching BGC classes | Notes |
|---|---|---|---|
| Honey bee (*Apis mellifera*) | *Paenibacillus larvae* (AFB) | Orthosomycins, glycopeptides, NRPS lipopeptides | Replace with project-specific citation/evidence grade when used. |
| Honey bee (*Apis mellifera*) | *Ascosphaera apis* (Chalkbrood) | Thioamide-NRP, polyene antifungals, HCN | Replace with project-specific citation/evidence grade when used. |
| Honey bee (*Apis mellifera*) | *Nosema ceranae* | NRPS unusual amino acids; F420-modified compounds | Replace with project-specific citation/evidence grade when used. |
| Bumblebee (*Bombus* spp.) | *Crithidia bombi* | Polyketides with antiprotozoal activity | Replace with project-specific citation/evidence grade when used. |
| Attine ants | *Escovopsis* spp. | Antifungal polyketides, NRPS lipopeptides, T2PKS | Matching BGC classes: pyrrolnitrin (phenylpyrrole, PMID 33962985 — direct evidence) and occidiofungin/burkholdine-class glycolipopeptide (PMID 33962985, PMID 19673482 — direct evidence). Both are required together for Escovopsis inhibition. Phenazine BGCs: class analogy only in this context — do not assign direct Escovopsis evidence without independent experimental support. |

### 17.7–17.8 Steps 5–6 — Novel Regulatory Signals and Integrated Model

After Steps 1–4, identify TFBS regulators not in the standard lookup appearing in ≥2 BGCs. Build integrated model addressing: substrate degradation, activation signals, pathogen targets, timing of production, nutritional benefits, ecological role (Mutualist / Opportunistic mutualist / Commensal / Unknown).

### 17.8A BGC-by-BGC Ecological Matrix

Required columns: BGC # / node, Edge status, **Architecture Confidence**, Product class, KCB/RiQ comparator, Diagnostic domains, TFBS signals, bldA tier, Substrate coupling, Disease-defense match, HGT/coverage flag, Ecological hypothesis, Testable prediction, Confidence, Claim-safety note.

When the MULTI-SIDEROPHORE CAPACITY flag is raised, add `Iron-acquisition system (multi-siderophore)` to the Ecological hypothesis column for each siderophore BGC row.

### 17.8B Ecological Synthesis Scoring Rubric

Host-relevant substrate coupling +1 | Cognate TFBS +1 | Bioactivity match +1 | Interior BGC +1 | Strong KCB/RiQ comparator +1 | Zero KCB + strong domains +1 discovery bonus | Edge/FC truncation −1 | No host/substrate metadata −1

Score ≥4: High-priority | 2–3: Plausible | 0–1: Low-confidence | <0: Insufficient evidence

### 17.9 Ecological Synthesis PDF

Required sections §1–§12 (host context, TFBS table, polysaccharide coupling, bldA mapping, disease defense, novel signals, ecological matrix, hypotheses, integrated model, testable predictions, claim-safety statement, missing-data register).

Filename: `[Strain ID]_Ecological_Synthesis_YYYY-MM-DD.pdf`

Apply Section 30.4 Ecological Synthesis Depth Gate before finalising.

### 17.10 Ecological Hypothesis Format

```
Hypothesis [N] — [Short title]
Evidence: [BGC node, domain, bitscore, TFBS regulator, score]
Mechanism: [Biochemical or regulatory pathway]
Ecological interpretation: [Strain-host relationship]
Testable prediction: [One specific, falsifiable experiment]
Claim-safety status: HYPOTHESIS — requires experimental validation
Supporting literature: [Required field. Cite at least one PMID or DOI when the
mechanistic analogy or ecological precedent is drawn from published work.

Distinguish the three evidence grades and state which applies:
  (a) Direct evidence    — same compound, same host taxon, published outcome.
  (b) Class analogy      — same compound class, different ecological context.
  (c) Structural analogy — related scaffold, different organism.

If no direct citation exists, write:
  "Analogy only — no direct literature support."

Examples:
  Direct:  BGC47 pyrrolnitrin → Escovopsis inhibition in Atta gardens:
           Francoeur et al. 2021 AEM 87(14):e00178-21; PMID 33962985.
  Analogy: Phenazine BGC → Escovopsis defense in attine context:
           Analogy only — not cited in Francoeur et al. 2021.]
```

### 17.11 Ecological Claim-Safety Language

Approved: "BGC [N] contains domains consistent with…" / "TFBS analysis predicts that [regulator] de-represses BGC [N] when [signal] is present."

Not approved: "This strain protects the [Host] against [disease]." / "This compound defends against [pathogen]."

### 17.12 — Cross-Habitat Comparison / Fast Mode / Integration Map

Fast mode minimum: TFBS coupling table, polysaccharide audit, bldA Tier 4 mapping, primary role hypothesis (1 sentence), 3 testable predictions, claim-safety statement.

> **Cross-habitat comparison (v7.5):** For formal multi-strain cross-habitat analysis, use CCSM Phase 3 (Section 41.7) after completing UCS tables (Section 41.3) and Gap Register (Section 41.4) for all strains.

---

## SECTION 18 — Excel Deliverables

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-18--excel-deliverables).

## SECTION 19 — Manuscript Update Procedure

Core rules: never mix content between manuscripts covering different [Host] or [Habitat] groups. Use tracked changes if requested. Final check for each manuscript: search for terminology specific to other [Host] groups before finalising.

**Key statistics to preserve — generic template:**

> Fill this table at session start with the statistics for the current manuscript.

| Metric | Value |
|---|---:|
| Total [Host] strains | [N] |
| Tested ≥1 assay | [N] |
| [Target 1] active | [N]/[N] = [%] |
| [Target 2] active | [N]/[N] = [%] |
| Dual active | [N]/[N] = [%] |
| Top [Target 1] fraction performer | [Strain ID] ([Value]) |
| Top [Target 2] fraction performer | [Strain ID] ([Value]) |
| [Genus] [Target] hit rate | [N]/[N] = [%] |

*Reference project worked example (bee paper):*

| Metric | Value |
|---|---:|
| Total bee strains | 180 |
| Tested ≥1 assay | 165 |
| Candida active | 45/165 = 27% |
| MRSA active | 64/165 = 39% |
| Dual active | 28/165 = 17% |
| Top Candida fraction performer | [see companion publication] |
| Top MRSA fraction performer | [see companion publication] |
| Micromonospora Candida hit rate | 4/8 = 50% |

---

## SECTION 20 — Glossary and Layperson Explanation Workflow

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-20--glossary-and-layperson-explanation-workflow).

## SECTION 21 — Verified Literature Deep Dive v2.0

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-21--verified-literature-deep-dive-v20).

## SECTION 22 — Rapid Literature Deep Dive v2.0

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-22--rapid-literature-deep-dive-v20).

## SECTION 23 — Mode Selection Decision Tree

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-23--mode-selection-decision-tree).

## SECTION 24 — Cross-Strain Comparison Module

**Trigger:** `Run cross-strain comparison: [Strain A] vs [Strain B] for [compound class or domain].`

Output: architecture table, shared vs divergent enzyme inventory, RiQ/KCB comparison, domain overlap, HGT/coverage notes, verdict, manuscript-safe hypothesis, isolation recommendation.

For systematic multi-strain comparisons, use CCSM (Section 41) instead of this pairwise module.

Filename: `CrossStrain_[StrainA]-[StrainB]_[Class]_YYYY-MM-DD.pdf`

---

## SECTION 25 — Key Scientific Findings to Preserve

> *Named-strain findings from the reference project (actinomycete collection) are published in the companion data paper and Zenodo deposit. This section is intentionally left as a placeholder in the public software release. New users: populate this section with your own project findings as they accumulate.*

**Current bioactivity contract:** absence of strain-specific metadata is NOT_SUPPLIED / NOT_OBSERVED with no named assays and NOT_ESTABLISHED locus/compound linkage. Supplied observations require their source and remain strain/extract context; the historical assumption that every strain inhibits MRSA/Candida is retired.

**hglE-KS-PREV-001 status:** hglE-KS confirmed as a prevalent, habitat-non-specific domain across all habitat classes in the reference collection. BRYO-HGT-001 designation retired 2026-05-29. The current rules registry records hglE-KS as informational and nonblocking. A zero or unavailable KCB result does not establish structural novelty; retain the actual comparison state and source scope. See §41.8 for the formal record.

---

## SECTION 26 — Reference Implementations

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-26--reference-implementations).

## SECTION 27 — Output Audit Log Template

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-27--output-audit-log-template).

## SECTION 28 — File Naming Conventions

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-28--file-naming-conventions).

## SECTION 29 — CDSW Protocol Summary

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-29--cdsw-protocol-summary).

## SECTION 30 — Output Quality Assurance Gates

These gates are self-checks applied before finalising deliverables. All gates must be applied before compiling the master PDF. Log outcomes in the audit log.

### 30.1 Mode B Depth Gate

Before finalising any Mode B §4 (biosynthetic pathway hypothesis), verify all of the following. If any check fails, **rewrite §4 before proceeding.**

**Required for every §4:**
- Names at least one specific domain hit by identifier (TIGRFAM ID, PFAM accession, or Stachelhaus code) with bitscore.
- Identifies the most mechanistically distinctive feature of this BGC.
- Contains compound-class or structural reasoning specific to this BGC, not copied from another BGC.
- Describes the predicted product outcome: structural class, reactive functional groups, unusual amino acids, or scaffold family.
- Includes an Evidence Traceability block (Section 32).
- Where §4 draws a mechanistic analogy to a characterized compound, BGC, or
  enzyme family in another organism, includes at least one PMID, DOI, or named
  MIBiG accession anchoring that analogy. Distinguish in the text which evidence
  grade applies:
    (a) Direct evidence    — same compound, same host/ecological context.
    (b) Class analogy      — same compound class, different context.
    (c) Structural analogy — related scaffold, different organism.

  If no citation is available, state explicitly in §4:
    "No direct literature citation available — class analogy only."

**Minimum prose lengths (excluding tables and headers):**
- §1 overview narrative: ≥80 words
- §4 biosynthetic pathway hypothesis: ≥120 words
- §6 mechanistic link to bioactivity: ≥60 words
- §7 isolation strategy: ≥80 words

**Boilerplate detection** — if §4 contains either phrase below as its primary content, it MUST be rewritten:
- Identical isolation strategy text across ≥3 consecutive BGCs — differentiate by bldA tier, TFBS induction condition, and target MW range.

### 30.2 Priority Assignment Gate

Before assigning any priority tier, apply these hard constraints:

**Cannot be LOW if:**
- KCB cumulative score > 5,000 — regardless of edge status or contig size.
- BGC contains a thioesterase (TE) domain and matches a polyene or large PKS reference at KCB > 5,000 → minimum MEDIUM; strongly consider HIGH*.
- BGC is the sole interior BGC in a very-poor-assembly strain → minimum HIGH.

**Cannot be HIGH/HIGH* if:**
- BGC is an unanchored zero-KCB T1PKS fragment < 8 kb that shares RiQ signature with a larger BGC already rated HIGH* in the same strain.

**Minimum evidence rule (v7.4):** Cannot be assigned HIGH or HIGH* unless at least **two independent evidence types** support the interpretation. See Section 32.4 for the evidence type list, which now includes concordant resistance gene evidence.

**After assigning all priorities:**
- If > 40% of all BGCs are HIGH/HIGH*: the priority list is likely inflated. Review FC/Edge fragments; downgrade zero-KCB fragments that lack diagnostic domain signatures.
- If HIGH* count exceeds the number of genuinely independent BGC pathways: check for split-cluster inflation.

- BGC carries a Section 34 verdict of likely tailoring/deoxysugar arm, split-pathway arm, or fragmentation artifact → maximum MEDIUM.

### 30.3 Cross-BGC Pattern Gate

After completing the BGC inventory, run these checks before writing Mode B reports.

**Run the antiSMASH Hallucination-Trap Audit (Section 34) at this stage** — before any Mode B report is started.

**Split pathway detection — required:**
- If ≥2 BGCs match the same KCB top compound at cumulative score >3,000: flag as **SPLIT PATHWAY CANDIDATE**. Identify which BGC carries the TE/release domain. Explicitly state the combined analysis in Deep Dive Synopsis §5 and in each affected Mode B §5.

**Fragmentation pattern summary — required for very-poor assemblies:**
Add a "Fragmentation Pattern Note" to the Deep Dive Synopsis.

### 30.4 Ecological Synthesis Depth Gate

> **Source-independence:** this gate checks hypothesis QUALITY, not isolation source. It must never defer, downgrade, or gate the synthesis on missing/unknown source — the synthesis is genome-grounded and proceeds on the general source-independent framing regardless. A supplied source is caveated provenance only.

Before finalising the Ecological Synthesis PDF, verify:

**Hypothesis differentiation:**
- Minimum 3 hypotheses with mechanistically distinct evidence.
- At least one hypothesis references a specific domain hit (TIGRFAM/PFAM ID with bitscore).
- No two hypotheses have the same testable prediction.
- Testable predictions must specify: culture condition, target compound class or MW range, and which specific BGC(s) the experiment will test.
- Every ecological hypothesis in §17.10 format includes a Supporting literature field containing either a PMID/DOI or the explicit statement "analogy only — no direct literature support."

**TFBS ecological mapping:**
- FuR or DmdR1 appearing in ≥4 BGCs must be flagged as a **genome-wide iron-competition network**.
- IolR appearing across BGCs is a **genome-grounded** inositol/polyol catabolism capacity signal; if a host/source description happens to mention polyol-rich substrate, note it as optional caveated provenance only — never assert it as a host-habitat-specific functional claim.
- Any regulator in ≥6 BGCs must be flagged as "genome-wide antibiotic regulatory network."

**Null results must be reported explicitly.**

### 30.5 PDF Generation Rules and PDF Style Standard (v7.9)

**Historical v7.9 style recipe.** The `sapote_pdf_styles.py` upload and helper names below are retained design history. For a current compiled report, follow [Postseal readers — PDF routes](POSTSEAL_READERS.md#pdf-routes) and the selected renderer owner; `compile-report` dispatches through `tools/md_to_pdf.sh`, while Mode B Markdown export has its packaged `mamey/markdown_pdf.py` renderer. The current compiled-report guide describes ReportLab as primary and Pandoc/XeLaTeX as fallback. Do not create a substitute style module merely to satisfy this archived recipe.

Apply these rules in all ReportLab PDF generation code:

**Always use Paragraph objects in table cells — never raw strings.**

**Always use `sapote_table()` for structured tables unless a specialized table helper is required.** If a custom table is unavoidable, it must still use the same font family, header style, wrapped Paragraph cells, padding, and repeatRows behavior as `sapote_table()`.

**Always include VALIGN and padding in TableStyle:**
```python
TableStyle([
    ('VALIGN',         (0,0), (-1,-1), 'TOP'),
    ('TOPPADDING',     (0,0), (-1,-1), 4),
    ('BOTTOMPADDING',  (0,0), (-1,-1), 4),
    ('LEFTPADDING',    (0,0), (-1,-1), 5),
    ('RIGHTPADDING',   (0,0), (-1,-1), 5),
])
```

**Never set fixed rowHeights on tables with variable text content.**

**Leading must be ≥ fontSize + 2.5 pt.**

**Add Spacer before PageBreak to prevent bottom-of-page clipping.**

**Long compound names in narrow columns:** truncate with `name[:40] + '…'` or widen the column.

**Bookmarks/outlines are required** for the compiled master PDF: Cover, TOC, Layperson's Guide, Deep Dive Synopsis, KCB Sweep, Hallucination-Trap Audit, every Mode B BGC report, Ecological Synthesis, Wet-Lab Decision Matrix, Metabolomics Readiness, Reviewer Attack Simulation, Missingness Register, Fermentation Card, Project Memory Snapshot, and Audit Log.

**Visible metadata/status boxes are required** near the beginning of every selected compiled master PDF. Preserve source/taxonomy uncertainty and typed bioactivity metadata/observation state, source receipt and linkage hold. Do not replace absent observations with a default-assumed assay result.

**PDF QA gate:** Before final compilation, render the PDF or inspect pages to confirm no overlapping text, clipped table cells, missing bookmarks, or missing default/status boxes. If any problem is detected, regenerate before delivery.

> **Gates 30.6 (CCSM Normalization Gate) and 30.7 (CCSM Cross-Strain Claim Gate) are defined in Section 41.13.**

### 30.8 LMPKS Rescue Gate (v7.5.1)

Before finalising the compiled master PDF, verify all Section 42 QA checks (§42.12).

### 30.9 Resistance Gene Confirmation Gate (v7.7)

Before finalising the compiled master PDF, verify all Section 45 QA checks (§45.11):

- [ ] All BGCs with a Tier 1 compound class prediction scanned for concordant resistance markers within BGC coordinates
- [ ] All BGCs within 15 kb of a Tier 1/2 marker checked for class concordance
- [ ] HGT guard applied to every Erm, Van, APH, or AAC hit
- [ ] Absence flag raised for claimed enediyne/cytotoxic BGCs lacking any visible self-protection within 15 kb
- [ ] Resistance Gene Confirmation Report included in compiled master PDF (or one-page null result)
- [ ] Architecture Confidence adjustments recorded in Evidence Traceability blocks
- [ ] WL adjustments recorded in WetLab_Decision_Matrix sheet


### 30.10 PDF Style and Typed Bioactivity-Metadata Gate

Before finalising any compiled master PDF, verify:

- [ ] `sapote_pdf_styles.py` was imported or its equivalent style functions were used consistently
- [ ] No PDF-generating script redefined the full style system independently
- [ ] Narrative text used Sapote text-flow helpers or equivalent wrapped Paragraph flows
- [ ] Structured tables used `sapote_table()` or a compatible wrapped-table helper
- [ ] Compiled PDF includes bookmarks/outlines for all major sections and every Mode B report
- [ ] Opening metadata/defaults block states source, taxonomy, ecological category, and bioactivity status
- [ ] Missing assay data remain NOT_SUPPLIED / NOT_OBSERVED with no inferred targets
- [ ] Missingness Register retains unavailable/unperformed evidence separately from measured negatives
- [ ] Audit log records typed supplied/unknown/positive/negative states, their source and NOT_ESTABLISHED locus/compound linkage
- [ ] A rendered-page check found no overlapping text, clipped tables, or bottom-of-page clipping



---


### 30.11 FLBR Megasynthase Fragment Rescue Gate (v8.3 candidate)

- [ ] FLBR census run genome-wide for all megasynthase classes before final priority assignment.
- [ ] Every T1PKS, modular NRPS, PKS-NRPS hybrid, and trans-AT fragment assigned a tier: `STRONG`, `WEAK`, or `STRONG (Very-Poor carve-out)`.
- [ ] Assembly-quality gate applied; Very-Poor demotions recorded with the deciding marker.
- [ ] Double-docking carve-out applied only to Ndock…Cdock single-ORF modules, with mandatory caveat.
- [ ] STRONG fragment sets flagged as Priority-1 long-read candidates and grouped as combined-pathway hypotheses.
- [ ] No STRONG-tier large-system claim made from WEAK evidence.
- [ ] §42 LMPKS results expressed under the §51 tier model; NRPS/hybrid results handled through §51.5.

## SECTION 31 — BGC Architecture Confidence System

> **Current native grade boundary:** the historical interpretive A–E rules below differ from `parsers.architecture_grade`. That classifier uses boundary, product text/families, length, optional KCB support and the chemical-hybrid flag; it does not measure a 70% expected-core fraction or assign C merely because a pair shares KCB. The compact Interior hybrid promotion requires at least two distinct normalized core product families, not two matching keywords. Unknown boundaries fall to E; the grade is a software structural heuristic, not measured confidence or production. Keep saved native grades and separately authored interpretive assessments distinct.

### 31.1 Purpose

Priority tells us whether a BGC is worth following. Novelty tells us whether it resembles known clusters. **Architecture confidence** tells us whether the structural interpretation itself is reliable. This score is reported in the BGC Inventory table (Arch column), KCB sweep, Mode B §1, Excel BGC_Inventory sheet, and Fermentation Card target table.

### 31.2 Architecture Confidence Grades

| Grade | Label | Definition | Interpretation |
|---|---|---|---|
| A | High-confidence architecture | Interior BGC; ≥70% core pathway logic visible; diagnostic domains support antiSMASH product label; module/release logic visible; KCB/RiQ either coherent or clearly novel | Structural hypothesis is relatively reliable |
| B | Mostly interpretable | Edge or mildly truncated BGC, but core biosynthetic machinery is visible; or Interior BGC where <70% core pathway logic visible due to annotation gaps | Useful for follow-up with caveats |
| C | Split-pathway candidate | Multiple BGC fragments likely represent one pathway; interpretation requires joint analysis | Interpret only as a combined pathway |
| D | Heavily truncated / speculative | Full-contig or edge fragment lacks key start/release/context genes | Treat as fragment-level evidence only |
| E | Tiny fragment / low interpretability | Very small BGC, unanchored fragment, no diagnostic domains, or likely false/minimal call | Do not prioritize unless connected to a larger split pathway |

### 31.3 Automatic Grade Rules

**Grade A:** BGC is Interior AND ≥70% of expected core pathway logic is visible AND diagnostic domains support antiSMASH product label AND no unresolved split-pathway warning.

**Grade B:** BGC is Edge but core biosynthetic machinery is mostly visible. Or BGC is Full-contig but contains a coherent terminal/release module and strong KCB/RiQ anchor. Or Interior BGC where <70% of core pathway logic is visible due to annotation gaps.

**Grade C:** ≥2 BGCs match the same KCB compound with score >3,000. Or multiple PKS/NRPS fragments share related RiQ/KCB signatures. Or a TE/release module appears in one BGC while upstream extension modules occur in separate contigs.

**Grade D:** BGC is Full-contig or Edge and lacks release/start/context domains. Product class is inferred from only partial biosynthetic machinery.

**Grade E:** BGC is <8 kb, full-contig, zero-KCB, and lacks strong diagnostic domains. Or the BGC is likely a fragment of a larger already-prioritized pathway.

### 31.4 Required Wording

- **Architecture Confidence A:** "The visible gene architecture is sufficiently complete for a class-level structural hypothesis."
- **Architecture Confidence B:** "The core pathway is interpretable, but boundary truncation or annotation gaps limit full structural prediction."
- **Architecture Confidence C:** "This BGC should be interpreted jointly with other fragments as a split-pathway candidate."
- **Architecture Confidence D:** "Only fragment-level structural inference is supported."
- **Architecture Confidence E:** "This call is retained for inventory completeness but should not drive isolation decisions alone."

### 31.5 Verdict feedback (v7.6) — REQUIRED before finalising Arch grade

Architecture confidence must be reconciled against Section 34 hallucination-trap and Section 30.3 fragmentation/split verdicts BEFORE the grade is finalised:

- A BGC flagged as a **likely tailoring/deoxysugar arm** of a larger pathway is capped at **Architecture Confidence C** regardless of interior status or gene count.
- A BGC flagged as a **split-pathway arm** (Section 30.3) takes **Grade C** and is interpreted only as a combined pathway.
- A BGC flagged as a **fragmentation artifact** (Section 4 fragmentation checks) cannot exceed **Grade D**.
- These caps override the automatic Grade A/B rules in 31.3.

**Resistance gene confirmation (v7.7):** A concordant Tier 1 resistance gene within BGC coordinates, or a concordant Tier 2 resistance gene within 15 kb (see Section 45), satisfies one independent evidence type for the §32.4 minimum evidence rule. It may support a Grade B→A upgrade when all other Grade A criteria are already met, but it does not override the hallucination-trap caps above. Record the confirmation in the Evidence Traceability block with locus tag, bitscore, and distance from BGC boundary.

---

## SECTION 32 — Evidence Traceability Blocks

### 32.1 Purpose

Every major interpretation must expose the evidence trail. These blocks reduce hallucination risk and make the report auditable.

### 32.2 Required Placement

- Deep Dive Synopsis: one compact block per featured BGC
- Mode B §1: compact block
- Mode B §4: expanded block
- Ecological Synthesis hypotheses: one block per hypothesis
- Fermentation Card: compact target evidence rows
- Excel workbook: `Evidence_Traceability` sheet

### 32.3 Evidence Traceability Template

```text
Evidence Traceability — [strain / full node-or-contig / region / BGC alias]
- Source files: [JSON / GBK / KCB txt / FASTA]
- antiSMASH product label: [label]
- Coordinates: [node:start-end]
- Edge status: [Interior / Edge / Full-contig]
- Architecture confidence: [A–E]
- RiQ evidence: [score, comparator, database]
- KCB evidence: [top compound, accession, cumulative score, protein count]
- Diagnostic domains: [PFAM/TIGRFAM IDs, names, bitscores]
- NRPS/PKS module evidence: [C/A/T/KS/AT/TE etc.; Stachelhaus if available]
- TFBS evidence: [regulator, score, ecological/culture interpretation]
- TTA/bldA evidence: [source and count]
- Coverage/HGT evidence: [flags or null]
- Resistance gene evidence: [gene type, locus tag, bitscore, distance from BGC boundary, tier (1/2/3/none), class concordance (Y/N), HGT guard outcome (pass/flag/na), Arch Confidence effect (none/B→A support/na)]
- Interpretation supported: [one-sentence class-level claim]
- Interpretation not supported: [named compound production / compound-level activity / complete structure]
```

### 32.4 Minimum Evidence Rule

No BGC may be assigned HIGH or HIGH* unless at least two independent evidence types support the interpretation, from the following:

- Domain architecture (PFAM/TIGRFAM, bitscore ≥150)
- KCB protein homology (cumulative score ≥500, ≥5 proteins)
- RiQ architecture similarity (<0.70 = distinct; 0.70–0.85 = variant; ≥0.85 = close)
- NRPS or PKS module logic (coherent C/A/T/TE or KS/AT/ACP module string)
- TFBS induction logic (regulator ≥18, ecologically plausible)
- Bioactivity consistency (compound class mechanistically linked to tested activity)
- Cross-strain recurrence (BGC family seed present in ≥2 strains)
- **Concordant resistance gene (Tier 1 within BGC coordinates, or Tier 2 within 15 kb, per Section 45 proximity rule)**

Exception: a sole Interior BGC in a very poor assembly may be HIGH based on architecture completeness plus novelty even with no KCB or resistance gene evidence.

---

## SECTION 33 — Wet-Lab Decision Matrix

### 33.1 Purpose

Convert BGC analysis into practical next steps: sequencing, fermentation, extraction, HRMS, bioassay, or deprioritization.

Wet-lab priority must use Lead Priority, Diagnostic Signal Score, and Claim Confidence separately. A low-confidence fragmented BGC may receive high wet-lab priority if it contains Tier 1 diagnostic markers, a coherent partial pathway constellation, or strong self-resistance/target-directed support. Record the follow-up experiment that would resolve the uncertainty.


### 33.2 Required Output

- Deep Dive Synopsis: top 10 wet-lab target table
- Excel workbook: `WetLab_Decision_Matrix` sheet
- Fermentation Card: top 3–5 action targets
- Project Memory Snapshot

### 33.3 Scoring Criteria

| Criterion | Score |
|---|---:|
| Interior BGC | +3 |
| Architecture Confidence A | +3 |
| Architecture Confidence B | +2 |
| Architecture Confidence C | +1, plus sequencing priority |
| Strong KCB >5,000 with divergent tailoring | +3 |
| No KCB + strong diagnostic domains (Arch A) | +4 |
| No KCB + moderate evidence (Arch B) | +2 |
| RiQ <0.50 with coherent domains | +3 |
| RiQ 0.50–0.85 with unusual tailoring | +2 |
| TFBS gives clear induction condition | +2 |
| T3/T4 bldA gating suggests hidden expression | +2 |
| BGC class has SPECIFIC mechanistic link to a tested activity | +2 |
| Distinctive detection handle (halogen isotope, strong chromophore e.g. polyene/angucycline UV, or characteristic mass class) | +2 |
| Full-contig/edge truncation | −2 |
| Tiny unanchored fragment | −3 |
| Likely split-cluster arm without TE/release | −2 |
| Likely housekeeping/conserved cluster | −3 |
| No chemical/expression evidence | −1 caveat, not a penalty if discovery-stage |
| **Concordant resistance gene (Tier 1 or Tier 2, within proximity rule — see Section 45)** | **+1** |

**Stacking rule:** "No KCB + strong diagnostic domains" and "RiQ <0.50 with coherent domains" may be claimed simultaneously — they are orthogonal evidence types. The resistance gene +1 bonus does not stack with itself; apply once regardless of how many concordant resistance markers are found for a given BGC.

**QS signal compound routing:**

When the antiSMASH product label is `hserlactone`, `BDSF`, `butyrolactone`,
or the BGC encodes a LuxI-type AHL synthase (PF07392/PF07395 family), an
RpfF-type BDSF synthase, or an AfsA-type γ-butyrolactone synthase — and the
BGC lacks additional biosynthetic machinery consistent with a direct antimicrobial
compound — apply the following routing:

  - Do NOT apply the "BGC class specific mechanistic link to tested activity"
    (+2 WL) bonus. QS signals are colony-coordination molecules, not direct
    antimicrobials.
  - Do NOT score against the MRSA or Candida default bioactivity screen.
  - Route to Ecological Synthesis (§17) only.
  - In the WL matrix, enter the note:
      "QS signal compound — ecological priority; WL score does not reflect
       antimicrobial discovery value."
  - Generate a §17.10 ecological hypothesis for the QS regulatory context
    (colony signalling, biofilm, co-regulation of secondary metabolite output).


**LMPKS scoring adjustments (v7.5.1):** Apply after standard score. Apply only the highest applicable LMPKS bonus (non-stacking with other LMPKS bonuses):

| LMPKS rescue result | WL adjustment |
|---|---|
| LMPKS-A (≥3 complete modules, TE, classifiable) | +2 |
| trans-AT PKS confirmed | +2 |
| Polyene rescue (≥5 DH, no ER run) | +2 |
| LMPKS-B (≥2 modules + docking domains) | +1 |
| LMPKS-C (fragment accumulation ≥4 mod_KS) | +1 sequencing priority only |
| Linear PKS (no TE, ≥3 modules) | +1 |

**Chemical handle readiness modifiers (§46):** Apply after all other §33 scoring. These modifiers reflect wet-lab tractability - a BGC with a strong class call and targeted chemical search handles is more immediately actionable than an equally high-scoring BGC with no tractable approach. Non-stacking with each other; apply the highest single applicable modifier per BGC.

| Condition | WL modifier |
|---|---:|
| Specific compound/family handle with verified formula/MW and expected adducts (per §0.7) | +1 |
| Class-level handle with 2-5 representative compounds or narrow MW range | +0.5 |
| Diagnostic UV/Vis wavelength or isotope pattern available | +0.5 |
| No reliable chemical handle despite high genomic interest | 0; note as untargeted LC-MS/MS and molecular networking priority |

These modifiers do not override claim-safety language, architecture confidence grades, or hallucination-trap caps. They do not apply to BGCs already scored at Deprioritized (≤0) unless a CCTT trigger elevates the BGC first.

Specific mechanistic links only (examples): glycopeptide / lipopeptide / halogenated-arylpyrrole / enediyne → MRSA; polyene / azole-NRPS / peptidyl-nucleoside chitin-synthase-inhibitor → Candida. Do NOT award for generic "antibacterial-ish PKS", saccharide, terpene, fatty-acid, or precursor-supply loci.

Additional Candida-specific example:

- **HSAF / PTM** sphingolipid (ceramide) synthase inhibitor → Candida (CaCsg1/Lag1 ceramide synthase is the specific target; disrupts sphingolipid biosynthesis required for Candida virulence and membrane integrity; mechanistically distinct from azoles, echinocandins, and polyenes — award +2 WL when Candida bioactivity is explicitly supplied with its source (never default-assumed))

> **Do NOT award the Candida-specific mechanistic link (+2 WL) for indolocarbazole BGCs** (rebeccamycin / staurosporine / AT2433 class). While Candida topoisomerase I (CaTop1) is a theoretical target, indolocarbazoles are characterized as antitumor and antibacterial agents, not dedicated antifungals. Topoisomerase I inhibition is not a specific antifungal mechanism in the clinical sense. If Candida activity is observed in fractions containing an indolocarbazole compound, attribute it to cytotoxicity (non-specific) rather than a dedicated antifungal mechanism, and cross-check for co-eluting compounds before assigning mechanistic causality.


**Phenazine class specificity note (attine context):** In the attine ant context (*Atta*/*Acromyrmex*/any attine genus), do NOT award the "BGC class specific mechanistic link" (+2 WL) bonus to phenazine BGCs on Escovopsis-defense grounds — phenazines are not the active anti-*Escovopsis* agents in the primary literature. Award only for direct anti-MRSA/broad-antibacterial support, and label any Escovopsis connection "class analogy only." Full precedent, evidence grades, and citations: see the §17.10 ecological precedent table (Attine / *Escovopsis* row).

### 33.4 Decision Categories

| Score | Category | Recommended action |
|---:|---|---|
| ≥10 | Immediate follow-up | Culture induction + LC-MS + bioassay-guided fractionation |
| 7–9 | Strong follow-up | Targeted culture/HRMS or sequencing clarification first |
| 4–6 | Conditional follow-up | Retain; revisit after long-read assembly or metabolomics |
| 1–3 | Inventory only | Do not prioritize unless cross-strain evidence emerges |
| ≤0 | Deprioritized | Keep for completeness; no immediate wet-lab action |

### 33.5 Four Independent Action Scores

For each BGC, output the four action scores below plus the diagnostic-marker follow-up (item 5):

1. **Sequencing priority** — need for long-read correction (HIGH if Edge/FC/split-pathway).
2. **Activation priority** — likelihood that special culture conditions matter (HIGH if TFBS/bldA T3–T4).
3. **Isolation priority** — suitability for purification/fractionation (HIGH if score ≥10).
4. **Dereplication priority** — need for HRMS/reference comparison before isolation.
5. **Diagnostic marker follow-up** — HMMER/BLAST confirmation, reassembly, targeted PCR, long-read sequencing, LC-MS/MS, isotope/adduct check, fraction-BGC linkage, or genetics.

---

## SECTION 34 — Diagnostic Signature Weighting + antiSMASH Hallucination-Trap / Claim-Calibration Audit

### 34.1 Purpose

This module prevents overclaiming while preserving high-value leads from fragmented assemblies. Sapote is designed for low-quality or fragmented contigs. Therefore, hallucination-trap flags are not exclusion criteria. They determine claim confidence, allowable wording, and follow-up route.

**Run this audit immediately after BGC inventory, before any Mode B report is started.**

### 34.1.1 Evidence source for the domain audit — read the evidence JSON, not the CSV summaries (MANDATORY)

Read the source-bound per-locus hits and their extraction/availability receipts before a class-level interpretation. `[StrainID]_AntiSMASH_Evidence_Parse.json` can retain antiSMASH-derived HMM annotations in `gbk_pfam_hits`, with model, E-value, bitscore and authored diagnostic flags. The file’s existence or a flag is not proof that every selected region/channel was extracted or that the biological class is validated. Preserve the source/member identity, requested/effective JSON mode, typed extraction states and missingness alongside the hit list.

The `*_2_inventory.csv` and `*_4_triage_board.csv` are derived *summaries*: they hold the antiSMASH
product label, KCB, and scores, but **not** the per-locus domain hit list. A class call (or a doubt
about one) made from the CSVs alone is unsupported, because the diagnostic core of a BGC frequently
sits at a locus the summaries never surface. Standing failure mode to avoid (observed repeatedly): a
ranthipeptide/RiPP call flagged "maturase unconfirmed" when the radical-SAM + SPASM maturase and the
RiPP recognition element were present in `gbk_pfam_hits` all along, simply unread.

Rules:
1. Before classifying a BGC or assigning/doubting its class, read its region's full `gbk_pfam_hits`
   entry, including all `tier1_diagnostic=true` hits.
2. Preserve EVIDENCE_PENDING when the source, mapping, extraction or scientific interpretation remains unresolved; a terse CSV alone does not prove absence.
3. A pending optional custom-marker channel does not by itself establish the availability or absence of antiSMASH HMM evidence. Check each source-derived channel and its typed receipt independently. Existing annotations remain annotation evidence, with their own source scope and scientific limits.

### 34.2 Fragment-tolerant principle

A BGC can be high-priority even when incomplete, edge-truncated, split, or weakly annotated. Fragmentation reduces product-identity confidence, not necessarily lead value. High-information diagnostic markers, pathway-constellation signatures, rare domain architectures, BGC-adjacent self-resistance genes, or biologically relevant transporter patterns may preserve or increase Lead Priority.

### 34.3 Mandatory two-axis scoring

Each prioritized BGC must receive separate scores:

| Score | Required values | Meaning |
|---|---|---|
| Lead Priority | LOW / MEDIUM / HIGH / EXCEPTIONAL | Biological or chemical follow-up value |
| Claim Confidence | VERY LOW / LOW / MODERATE / HIGH / CONFIRMED | How safely Sapote can state product class, family, activity, or mechanism |
| Diagnostic Signal Score | 0–5 | Strength of high-information genes/domains/signatures independent of assembly completeness |
| Generic Overclaim Risk | LOW / MODERATE / HIGH | Risk that interpretation depends on broad/common genes rather than diagnostic evidence |

### 34.4 Evidence-weight audit

For every named gene/domain/compound-family inference, record:

| Evidence item | Evidence tier | Source location | Claim role | Required caveat |
|---|---|---|---|---|
| [gene/domain] | Tier 1–5 | region GBK / antiSMASH JSON / HMMER / KCB / literature | primary / supportive / weak / reject | [safe wording] |

Every named gene/domain must be traceable to antiSMASH output, region GBK, whole-genome GBK/FASTA/protein search, HMMER result, curated marker table, or user-supplied evidence.

### 34.5 Core hallucination traps

| Trap | Check | Required response |
|---|---|---|
| Compound-name overclaim | Is the name from antiSMASH/KCB/MIBiG similarity only? | Use “similar to [compound] BGC” unless chemical evidence exists |
| BGC equals production | Is there metabolite, fraction, purified-compound, expression, or genetics evidence? | If no, say biosynthetic potential only |
| Similarity inflation | Does KCB/MIBiG match cover whole cluster or only a few proteins? | Record basis: whole-cluster/core-only/single-gene/tailoring-subset/weak |
| Region/protocluster confusion | Does one antiSMASH region contain multiple protoclusters or overlapping calls? | Do not treat region count as pathway count without curation |
| Split/fragmented pathway | Are key pieces on separate contigs/regions? | Preserve as split-pathway hypothesis; lower claim confidence |
| Missing hallmark gene | Is a required marker absent or unsearched? | Lower claim level; search whole proteome if available |
| Generic-gene overclaim | Is interpretation driven by transporter/regulator/common tailoring gene only? | Downgrade or rewrite as supportive only |
| Bioactivity-to-BGC overlink | Is MRSA/Candida activity assigned to a BGC without fraction/MS/genetics? | Keep as strain-level context only |
| Ecology overclaim | Is host/source used to imply function without direct evidence? | Rewrite as hypothesis/testable prediction |
| Silent-cluster assumption | Is expression assumed? | Mark as expression unknown unless transcript/metabolite evidence exists |
| BGC-local null misread as genome-wide null | Did a genome-wide module report absence using only BGC-region hits or product labels? | Reclassify as `Not Assessable — BGC-region scope only` until full proteome/CDS scan is confirmed |
| Resistance gene HGT acquisition misread as producer self-protection | Is a resistance gene distant, mobile-element-associated, or mechanistically incompatible? | Record as HGT resistance island candidate; do not use as class confirmation |
| Indole masking indolocarbazole | Is antiSMASH product “indole” but indsynth / indolocarbazole evidence present? | Apply indolocarbazole diagnostic entry; use domain evidence over generic label |
| Ectoine masking showdomycin | Does an ectoine label mask showdomycin-like KCB or maleimide nucleoside context? | Investigate showdomycin-class logic; do not dismiss as osmoprotectant only |
| Saccharide BGC as split-pathway glycosylation arm | Does a saccharide BGC lack aglycone genes but carry deoxysugar/glycosylation logic? | Treat as candidate split-pathway glycosylation arm, not standalone novel compound |

### 34.6 Safe-claim ladder

| Claim level | Allowed language | Evidence required |
|---|---|---|
| Level 0 | No interpretable signal | No diagnostic marker or coherent context |
| Level 1 | General BGC / secondary-metabolite potential | antiSMASH region only |
| Level 2 | Class-compatible fragment | core class domains or generic class support |
| Level 3 | Diagnostic marker present | Tier 1 marker, but incomplete context |
| Level 4 | Pathway-family-like BGC fragment | diagnostic marker + multiple pathway-family genes / synteny / constellation |
| Level 5 | Close BGC-family candidate | high similarity + conserved core/tailoring context; no chemistry yet |
| Level 6 | Confirmed product or BGC-product link | LC-MS/MS, isolation/NMR, isotope pattern, genetics, expression, or purified-compound evidence |

### 34.7 Transporter and self-resistance exception

Transporters and resistance genes must not be dismissed as generic by default. They are weak product-identity markers when isolated, but they can become high-value prioritization evidence when literature-backed, BGC-adjacent, duplicated, divergent, horizontally acquired, class-associated, or paired with diagnostic biosynthetic genes.

Transporters may support predictions about siderophore activity, molecular properties, uptake/export, or pathway coherence. Resistance genes may support biological-activity prioritization or target hypotheses. Neither category alone may be used to claim exact compound identity without stronger biosynthetic or chemical evidence.

| Pattern | Evidence weight | Allowed interpretation | Forbidden overclaim |
|---|---:|---|---|
| Duplicated housekeeping target near BGC | High pattern evidence | self-resistance/target hypothesis; prioritize follow-up | Does not prove MOA or product identity |
| Divergent target homolog inside/near BGC | High pattern evidence | possible resistant target | Does not prove compound class alone |
| Specific resistance enzyme embedded in BGC | Moderate-high | self-protection hypothesis | Not causal without context |
| Transporter family enriched in a metabolite class | Moderate-high if literature-backed | feature/function predictor | Not exact product identity |
| Transporter co-localized with diagnostic biosynthetic genes | Supportive | pathway coherence/export/uptake support | Not standalone evidence |
| Generic ABC/MFS transporter alone | Low | possible export only | No product, MOA, or activity claim |
| Distant genome-wide ARG | Low unless comparative logic supports it | strain background resistance | Not BGC evidence by default |

### 34.8 Required output card

```markdown
#### Diagnostic Signature / Hallucination-Trap Card — [BGC ID]

| Field | Output |
|---|---|
| Strain / full node-or-contig / region / BGC alias | Copy all components from one bound source; hold missing/conflicting identity |
| Raw antiSMASH product label |  |
| Curated candidate class |  |
| Lead Priority | LOW / MEDIUM / HIGH / EXCEPTIONAL |
| Claim Confidence | VERY LOW / LOW / MODERATE / HIGH / CONFIRMED |
| Diagnostic Signal Score | 0–5 |
| Highest evidence tier | Tier 1–5 |
| Marker basis |  |
| Transporter / resistance support | none / weak / supportive / high-value pattern |
| Region completeness | complete / edge-truncated / split / fragmented / uncertain |
| Similarity basis | whole-cluster / core-only / single-gene / tailoring-subset / weak |
| Missing hallmark genes |  |
| Generic-gene overclaim risk | LOW / MODERATE / HIGH |
| Bioassay linkage | none / strain-level only / fraction-linked / LC-MS-linked / purified / genetic |
| Safe claim |  |
| Follow-up route | search whole proteome / HMMER / reassembly / targeted PCR / LC-MS / fractionation / genetics |
```

### 34.9 Required report language

Every report must include:

```text
Diagnostic Signature Weighting + antiSMASH Hallucination-Trap / Claim-Calibration Audit: Product labels were treated as hypotheses, not compound identifications. The audit separated Lead Priority from Claim Confidence, classified genes/domains by evidence weight, preserved promising fragmented leads with high-information markers, checked split-cluster and similarity-inflation patterns, and prevented transporter/resistance/regulatory genes from being used as standalone product-identity evidence.
```

---

## SECTION 35 — Cross-Strain BGC Family Clustering Hook

### 35.1 Purpose

Every strain report should produce data that can later support project-wide BGC family comparisons.

### 35.2 Required Fields

Add to Excel workbook `CrossStrain_Family_Seeds` sheet:

| Strain ID | Habitat | Genus | BGC # | Product class | Arch confidence | KCB top compound | KCB score | RiQ comparator | RiQ score | Diagnostic domains | Module signature | TFBS signature | TTA tier | Family seed label | Cross-strain comparison priority |

### 35.3 Family Seed Naming

```text
[Genus]_[Habitat]_[CompoundClass]_[StrainID]_BGC[N]
```

*Reference project examples:*
- `Kribbella_Bryophyte_Lincosamide_AS-XXX_BGC05`
- `Kribbella_Bryophyte_Lipolanthine_AS-XXX_BGC06`
- `Pseudonocardia_Bryophyte_NAPAA_AS-XXX_BGC01`
- `Saccharothrix_Bryophyte_hglE-KS_AS-XXX_BGC07`

### 35.4 Project-Wide Clustering Trigger

If ≥3 strains have family seeds in the same class, recommend:

```text
Run cross-strain BGC family clustering for [class/family].
```

**Project-wide audit rule:** After every fifth strain analysis, run a project-wide family seed audit against the master JSON and identify classes that have reached the ≥3 strain threshold.

**hglE-KS status update (2026-05-29):** hglE-KS-PREV-001 is now a **habitat-non-specific prevalent domain** confirmed in 8 strains/7 genera across all 3 habitats (Bryophyte, Attine, Hymenoptera). The ≥3-strain clustering threshold was exceeded; cross-strain comparison is complete; BRYO-HGT-001 designation retired. The current rules registry records hglE-KS as informational and nonblocking. A zero or unavailable KCB result does not establish structural novelty; retain the actual comparison state and source scope. Do not add new hglE-KS seeds to a habitat-specific or HGT candidate register; add them to the hglE-KS-PREV-001 prevalence record and update the strain/genus count.


---

## SECTION 36 — Reviewer Attack Simulation

### 36.1 Purpose

Generate manuscript-safe interpretations by anticipating likely reviewer criticisms.

### 36.2 Required Placement

- Deep Dive Synopsis: after Executive Summary
- Ecological Synthesis: after integrated model
- Manuscript-writing outputs when strain findings are used

### 36.3 Template

```text
Reviewer Attack Simulation

Claim or interpretation:
[State the report's strongest claim]

Likely reviewer criticism:
1. [Assembly/fragmentation criticism]
2. [Bioinformatics-only criticism]
3. [Dereplication/known-compound criticism]
4. [Ecological overreach criticism]

Defense / safe revision:
1. [How report limits claim]
2. [Evidence supporting class-level interpretation]
3. [Experiment needed to resolve]
4. [Manuscript-safe wording]

Recommended manuscript wording:
"[One sentence suitable for Results or Discussion]"
```

### 36.4 Required Reviewer-Attack Categories

For every report, include at least one criticism and response for:

- Assembly fragmentation
- Compound identity overclaiming
- Bioactivity-to-BGC causality
- Ecological causality
- Need for chemical validation
- **Self-protection absent from claimed cytotoxic/genotoxic BGC (enediyne, DNA-damaging anthracycline):** If no CalC-type or equivalent resistance gene is detected within 15 kb of a claimed enediyne/cytotoxic BGC, the reviewer will ask how the producer protects itself. State that: (a) the self-protection gene may reside on an unassembled contig, and (b) long-read sequencing is required to confirm whether self-protection is encoded. Use this wording: "No self-protection gene was detected within 15 kb of this BGC in the current draft assembly; a CalC-type or equivalent resistance gene may be present on an unassembled or misassembled contig."

---

## SECTION 37 — Metabolomics Readiness Module

### 37.1 Purpose

Prepare BGC hypotheses for LC-MS, HRMS, UV, and fractionation work.

### 37.2 Required Fields

Add to Excel workbook `Metabolomics_Readiness` sheet:

| BGC # | Product class | Arch confidence | Expected MW range | Ionization expectation | UV/Vis expectation | Polarity | Extraction recommendation | Dereplication target | HRMS priority | Bioassay pairing | Resistance gene concordance note | Caveat |

### 37.3 Class-Level Defaults

| Class | MW range | Ionization | UV/Vis | Extraction | Resistance gene confirmation marker |
|---|---:|---|---|---|---|
| NAPAA | ~400–900 Da | Positive likely | weak/moderate | EtOAc/BuOH, C18 | — (no well-characterized producer resistance gene) |
| Lanthipeptide/RiPP | ~800–3,500 Da | Positive likely | variable | SPE/C18, MeOH/water | ABC transporter co-localized in BGC (Tier 3 routing) |
| Polyene PKS | ~700–1,300+ Da | Positive/negative variable | strong polyene UV | organic extraction, monitor UV | — |
| NRPS peptide | ~500–2,500 Da | Positive likely | variable | EtOAc/BuOH/C18 | — |
| Siderophore-like NRPS | ~500–1,500 Da | Positive/negative; metal complexes | variable | iron-limited culture, CAS assay | — |
| Terpene/carotenoid | ~300–800 Da | APCI/positive often useful | visible/UV if carotenoid | nonpolar organic extraction | — |
| Ectoine | ~142 Da | polar; positive | weak | aqueous/polar extraction | — |
| Glycopeptide | variable | Positive/negative | variable | EtOAc/BuOH; check polarity | VanHAX operon (Tier 1); if concordant → high class confidence |
| Macrolide (14-membered) | 500–900 Da | Positive | UV ~280 nm weak | EtOAc/BuOH, C18, macrolide window | ErmE/ErmSF methyltransferase within 15 kb (Tier 2, check HGT guard) |
| Macrolide (16-membered) | 600–1,200 Da | Positive | UV ~280 nm weak | EtOAc/BuOH, C18, macrolide window | ErmE/ErmSF methyltransferase within 15 kb (Tier 2, check HGT guard) |
| Aminoglycoside/aminocyclitol | 400–900 Da | Positive | weak | polar/cation-exchange | DOIS + APH/AAC within BGC (Tier 1) |
| Enediyne chromoprotein | variable | Positive | variable | organic; extreme caution (cytotoxic) | CalC-type radical SAM within BGC coordinates (Tier 1); ABSENCE = §36.4 reviewer attack flag |
| Phosphonate | 200–800 Da | Positive; ³¹P-NMR distinctive | weak | polar extraction | FomA/FomB near PepM-containing BGC (Tier 1) |
| Peptidyl nucleoside (nikkomycin/polyoxin class) | ~490–600 Da | Positive likely; zwitterionic | UV 262 nm | Aqueous/polar extraction (50% MeOH/H₂O); SAX fractionation at pH 7.0; C18 desalting only. Standard C18 is insufficient. | NikT/NikD-type resistance gene (Tier 1); chitin synthase paralogue with divergent active site (Tier 2) |
| trans-AT polyketide | 500–1,500 Da | Positive likely | Variable | EtOAc/BuOH, GNPS networking | — |
| Linear polyketide | 400–1,200 Da | Positive/negative | Variable | EtOAc/BuOH broad extraction | — |
| Large macrolide / rapamycin class (≥24-membered) | 800–1,500 Da | Positive | UV variable | EtOAc/BuOH, C18 | ErmE/ErmSF within 15 kb (Tier 2, check HGT guard) |

| Indolocarbazole (rebeccamycin / staurosporine / AT2433-A1 / loonamycin / arcyriarubin class) | ~390–650 Da (rebeccamycin: 602; AT2433-A1: ~590; staurosporine: 466; arcyriarubin A: 393) | ESI+ [M+H]+ likely; staurosporine ionizes well as [M+H]+ at m/z 467 | 320 nm primary (strong, conjugated indolocarbazole chromophore) + 360 nm secondary (diagnostic doublet); both bands should be confirmed together before assigning class by UV; note: crude extracts may show orange-brown coloration at high concentration | EtOAc pH 6–7; C18 semi-prep; MeOH/H2O + 0.1% FA gradient; protect from prolonged light exposure; ⚠ **CYTOTOXICITY CAUTION** — staurosporine-class kinase inhibitors are among the most cytotoxic natural products known; test HeLa/mammalian cytotox IC₅₀ BEFORE MRSA/Candida MIC; handle per standard cytotoxic-compound SOPs; do NOT scale up without toxicology pre-screen | No established Tier 1 resistance gene for indolocarbazoles as a class; self-resistance may involve drug efflux MFS/ABC transporter or modified Top1 — if found near BGC, note as Tier 3 routing signal (§45.5) |
| HSAF / PTM (polycyclic tetramate macrolactam; HSAF, 10-epi-HSAF, militarinone, frontalin class) | ~450–600 Da (HSAF: 531.31; 10-epi-HSAF: 531.31; militarinone A: ~450; frontalin-type: varies) | ESI+ [M+H]+; HSAF m/z 532 ([M+H]+) confirmed in multiple literature sources | 305 nm strong (conjugated tetramate chromophore) + 270 nm shoulder; yellow-brown coloration in concentrated crude extracts possible | EtOAc pH 6–7 (DO NOT use pH <4 — tetramate ring is acid-labile and will hydrolyze); C18 semi-prep; MeOH/H2O + 0.1% FA; reverse-phase at neutral pH is optimal | No Tier 1/2 resistance gene established for PTM class in actinomycetes; if present, a ceramide synthase (Lag1-family) paralogue with altered drug-binding residues may be detectable near BGC |
| Prodiginine (prodigiosin / cycloprodigiosin / streptorubin / metacycloprodigiosin class) | ~295–450 Da (prodigiosin: 323.44; cycloprodigiosin: 309.41; streptorubin B: ~450; undecylprodigiosin: 393) | ESI+ [M+H]+; prodigiosin [M+H]+ = 324 | 530 nm intense (magenta/red; this is a visual screen — prodiginines produce vivid red/magenta pigment on ISP2 plates, visible without any instrumentation); 485 nm shoulder; TLC detection by eye | **Visual plate inspection first** — red/magenta pigment on ISP2 plate at 7–14 days is a positive screen for prodiginine expression; EtOAc or acetone extraction; TLC under visible light (no UV required); C18 HPLC MeOH/H2O gradient; no special precautions needed | No characterized Tier 1/2 actinomycete resistance gene for prodiginines; H+/Cl- co-transport inhibition is the proposed membrane mechanism; also weak topoisomerase inhibition reported |
| Ansamycin (rifamycin / geldanamycin / herbimycin / ansatrienin / ansamitocin class) | ~530–900 Da (rifamycin SV: 697; geldanamycin: 560; herbimycin A: 578; ansamitocin P-3: 549; rifamycin B: 756) | ESI+ [M+H]+ or [M+Na]+; geldanamycin ionizes as [M+H]+ at m/z 561 | ~340 nm (rifamycin-type: naphthalenol chromophore; orange-red coloration in crude extract); ~310 nm (geldanamycin-type: benzoquinone/ansa chain; purple-brown coloration); color visible in crude extracts provides preliminary identification handle | EtOAc / n-BuOH extraction; C18 semi-prep; MeOH/H2O gradient; geldanamycin benzoquinone is redox-active — protect from light and reducing agents; rifamycins are photostable | ArrA/Arr-type ADP-ribosyltransferase within 15 kb of ansamycin PKS fragments (Tier 2, §45.4; apply HGT guard per §45.4); for rifamycin class, mutant rpoB (RNA polymerase subunit with altered drug-binding pocket) may serve as an additional self-protection mechanism |
| Showdomycin (maleimide C-nucleoside) | ~229 Da (monoisotopic: C₉H₁₁NO₆ = 229.0586 Da, PubChem CID 28032; [M+H]+ = m/z 230.0659) | ESI+ [M+H]+ m/z 230; verify ionization mode empirically; very small MW means it elutes at or near the void volume of standard C18 reversed-phase columns | ~260 nm (nucleoside base chromophore); maleimide carbonyl ~215 nm | ⚠ **Standard C18 reversed-phase is insufficient** — showdomycin will be lost in the void volume or early wash fractions; use aqueous extraction (50% MeOH/H₂O or water), followed by HILIC or graphitic carbon (Hypercarb-type) primary fractionation; ion exchange (SAX or SCX) as alternative primary fractionation before C18 desalting; MW is so small that MS fragmentation patterns are minimal — confirm by exact mass and UV | No characterized Tier 1 resistance gene; maleimide warhead reacts covalently with active-site Cys residues of MurA — producer self-protection may involve MurA paralogue with Cys→Asp/Ser substitution at the reactive position; flag absence of a modified MurA as a §38.2 missingness item for this class |
| Arylpolyene (APE; flexirubin-type) | ~350–700 Da (varies with chain length and aryl moiety) | APCI+ / ESI+ variable; often best detected by UV rather than MS | 420–450 nm strong primary handle. **Visual screen first:** yellow/orange colony pigment on plates is the cheapest first-pass production indicator, no instrumentation required. Also ~320 nm secondary absorption. | Non-polar extraction (EtOAc, acetone, or hexane); TLC under visible light (no UV lamp needed); LC-DAD 430 nm monitoring | — (no characterized Tier 1/2 resistance gene; arylpolyenes are pigments, not toxic to producer) |

**Polar compound caveat:** Standard C18 reversed-phase extraction and fractionation will underrepresent or lose highly polar and zwitterionic compounds including peptidyl nucleosides, siderophores, and charged NRP fragments. When a BGC predicts a polar product, explicitly flag in the Metabolomics_Readiness sheet that standard C18 crude extraction is insufficient, and recommend aqueous or ion-exchange primary fractionation before HRMS dereplication.

### 37.4 Claim-Safety Rule

Do not provide exact molecular formulas, exact masses, or structures unless supported by a named reference cluster with strong evidence. Use broad MW ranges.

### 37.5 Trigger-driven routing (v7.6)

Metabolomics rows are auto-assigned when a CCTT (Section 43) trigger fires:
- **T43-NUC fires →** route to peptidyl-nucleoside / polar row: UV 262 nm, aqueous/50% MeOH extraction, SAX or ion-exchange primary fractionation, C18 desalting only. Flag explicitly that standard C18 reversed-phase crude extraction is insufficient.
- **T43-HAL fires →** set dereplication handle to halogen-isotope-aware HRMS (Cl M+2; Br M+2/M+4).
- **T43-PHO fires →** flag ³¹P-NMR / phosphonate-aware detection and polar extraction.

---

## SECTION 38 — Known Missingness Tracking

### 38.1 Purpose

Track what is unknown so uncertainty is not accidentally converted into confident prose.

### 38.2 Missingness Categories

| Category | Examples |
|---|---|
| Assembly missingness | Edge/FC BGC, absent TE, absent start module, split contigs |
| Annotation missingness | TFBS absent, TTA unavailable, domain module missing, unannotated ORFs |
| Biological missingness | no expression data, no culture condition data |
| Chemical missingness | no HRMS, no NMR, no purified compound |
| Bioactivity missingness | no MIC, no fraction linkage, no assay replication noted |
| Taxonomic missingness | unresolved species, no 16S accession, conflicting genus |
| Ecological missingness | [Host] substrate unknown, habitat metadata incomplete |
| Comparative missingness | no project-wide family comparison yet; genus absent from MIBiG |
| **Proteome scope limitation** | **CGAD or another genome-wide ecological module was assessed from BGC-region hits only, or full-proteome translations were unavailable/incomplete. Effect: chitinolytic capacity, LPMO capacity, Nag/GlcNAc substrate-supply capacity, and DasR coupling interpretation are not valid as genome-wide null calls. Fix: extract all `/translation=` fields from full-genome antiSMASH GBK when present; otherwise use Prodigal/Prokka-derived proteins from FASTA; then rescan. If only motif/signal-peptide screening was used, record HMMER confirmation as a named missing item.** |
| **Resistance gene missingness** | **No identifiable self-protection mechanism within 15 kb of a BGC predicted to encode a highly bioactive compound class (enediyne, glycopeptide, aminoglycoside, nikkomycin-type). Flag which self-protection type would be expected. Note that fragmented assembly may prevent detection.** |

**Proteome scope limitation sub-type — HMMER unavailable, motif scan only:** Full proteome was scanned using active-site motif screens rather than HMMER profiles. GH18-like candidates are at motif-level confidence only. GH19 and AA10 capacity is Not Assessable. HMMER PF00704/PF00182/PF03067 confirmation is outstanding. List as named missing item: "HMMER CGAD confirmation — [Strain ID]."


### 38.3 Required Output

- Deep Dive Synopsis audit log
- Ecological Synthesis missing-data register
- Excel workbook `Missingness_Register` sheet
- Project Memory Snapshot

### 38.4 Missingness Register Template

| Missing item | Category | Affected BGCs | Effect on interpretation | Recommended fix | Priority |
|---|---|---|---|---|---|

---

## SECTION 39 — Figure Suggestion Module

### 39.1 Purpose

Suggest figures that could support manuscripts, talks, lab meetings, or future white papers.

### 39.2 Required Placement

Add a short section near the end of every complete strain report:

```text
Recommended Figures from This Analysis
```

### 39.3 Figure Recommendation Types

| Figure type | When to recommend |
|---|---|
| Split-pathway schematic | ≥2 BGC fragments likely belong to one large pathway |
| BGC architecture cartoon | Architecture Confidence A/B high-priority BGC |
| KCB/RiQ novelty scatter | Many BGCs with mixed novelty |
| TFBS regulatory heatmap | ≥4 BGCs share regulator family |
| Wet-lab priority matrix | ≥5 plausible targets |
| Cross-habitat comparison | Genus/BGC class appears in multiple [Habitat] categories |
| Ecological model figure | Strong ecological synthesis with multiple evidence streams |
| Missingness/assembly caveat figure | Very poor assembly drives interpretation |

### 39.4 Figure Suggestion Template

```text
Figure [X] — [Title]
Purpose: [What the figure communicates]
Data needed: [BGC table / KCB / TFBS / domains / bioactivity]
Recommended visual form: [schematic, heatmap, scatter, table, network]
Manuscript use: [Results / Discussion / Supplement]
Claim-safety note: [What the figure must not imply]
```

---

## SECTION 40 — Project Memory Snapshot

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-40--project-memory-snapshot).

## SECTION 41 — CROSS-COMPARATIVE SYNTHESIS MODULE (CCSM) v1.1

**Version:** 1.1 | **Established:** May 27, 2026  
**Scope:** Within-habitat and cross-habitat BGC comparison across strains analyzed with heterogeneous workflows  
**Trigger phrases:** See Section 41.11  
**Prerequisite:** Section 3 (parsing), Section 4 (BGC inventory), Section 5 (KCB sweep) ideally complete for all strains being compared.

---

## 41.0 DESIGN RATIONALE — THE HETEROGENEITY PROBLEM

Cross-strain comparison is structurally harder than per-strain analysis because outputs from different sessions are **never directly comparable without normalization**.

| Heterogeneity source | Examples | Risk if unresolved |
|---|---|---|
| Prompt version | Different workflow versions across strains | Different fields populated; different priority language |
| antiSMASH version | v6.x vs v7.x vs v8.0.4 | Product labels, KCB scores, PFAM versions differ |
| MIBiG version | MIBiG 3.0 vs 4.0 | KCB hits changed; some BGCs re-classified |
| Analysis depth | Full Mode B vs KCB sweep only | Missing fields for shallow analyses |
| TTA source | JSON TTA module vs GBK vs FASTA | bldA tier comparisons invalid if sources differ |
| Assembly quality | Very Poor vs Good | BGC count comparisons misleading without corrected count |
| Bioactivity assay differences | Different panels, concentrations | Bioactivity comparisons require explicit assay matching |

**Rule:** Never compare a raw field value across strains without first recording the analysis version and evidence grade for that field in both strains.

---

## 41.1 PURPOSE

The CCSM provides a structured, evidence-graded workflow for comparing multiple strains:

- **Within-habitat:** Strains sharing the same [Host] or [Habitat]
- **Cross-habitat:** Strains from different [Host] or [Habitat] categories
- **Cross-genus:** Strains of the same genus across [Habitat] categories

CCSM outputs are designed to be manuscript-ready and claim-safe.

---

## 41.2 FOUR PHASES OF THE CCSM WORKFLOW

```
Phase 1 — NORMALIZE        Build Universal Comparison Schema (UCS) for all strains
     ↓
Phase 2 — WITHIN-HABITAT   Compare strains sharing the same [Host] or [Habitat]
     ↓
Phase 3 — CROSS-HABITAT    Compare [Habitat] sets against each other
     ↓
Phase 4 — COMPILE          Produce comparison deliverables (tables, figures, text)
```

---

## 41.3 UNIVERSAL COMPARISON SCHEMA (UCS)

### UCS Field Tiers

**Tier 1 — Mandatory (block comparison if absent):**

| Field | Notes |
|---|---|
| Strain ID | Exactly as in source files |
| Genus | At minimum; species if available |
| Host / Isolate source | Your project's defined [Host] / [Habitat] terms |
| Habitat class | Your project's defined [Habitat] groupings |
| Bioactivity summary | Active organism(s), assay type, qualitative result; or "not tested" |
| Analysis version | Prompt version that produced the available output |
| antiSMASH version | e.g., 6.1.1, 7.0.1, 8.0.4 |
| MIBiG version | e.g., 3.1, 4.0 |
| Raw BGC count | Integer from antiSMASH |
| Interior / Edge / FC counts | Required for corrected BGC count |
| Corrected BGC count | Per Section 4 formula |
| Assembly quality tier | Good / Moderate / Poor / Very Poor |

**Tier 2 — Strongly recommended (flag if absent; do not block comparison):**

| Field | Notes |
|---|---|
| BGC class inventory | Counted list: e.g., NRPS ×4, T1PKS ×3, lanthipeptide ×2 |
| Novelty profile | Count of BGCs per RiQ tier |
| Top 5 KCB hits | Compound, MIBiG accession, cumulative score, BGC number |
| bldA tier distribution | Count of T1 / T2 / T3 / T4 / T? |
| Key diagnostic domains | List of notable TIGRFAM/PFAM IDs with bitscore |
| Priority tier distribution | HIGH* / HIGH / MEDIUM / LOW counts |

**Tier 3 — Enriched (use if Mode B / full analysis available; do not fill by inference):**

| Field | Notes |
|---|---|
| TFBS network | All TFBS hits ≥18 across all BGCs; genome-wide networks flagged |
| HGT flags | Transposase/integrase positions; coverage outliers |
| Ecological synthesis summary | Role hypothesis; top testable prediction |
| Bioactivity–BGC mechanistic map | BGC-to-activity mechanistic link |
| Isolation strategy summary | bldA tier + TFBS induction conditions |

---

## 41.4 OUTPUT NORMALIZATION PROTOCOL (ONP)

### Step 1 — Source inventory per strain

For every strain in the comparison set, list all available source materials.

### Step 2 — Field extraction priority per source

| Source | Evidence Grade | When to use |
|---|---|---|
| antiSMASH JSON uploaded this session | **A** | Best — all fields extractable |
| Prior session PDF report (parsed this session) | **B** | Use for summary fields |
| Master JSON | **C** | Use for BGC counts, RiQ, KCB top hits |
| User-confirmed note or memory instruction | **D** | Use for corrections or confirmed values only |
| Model approximation from partial data | **E** | Must be flagged explicitly; never use for Tier 1 fields |
| Not available | **X** | Field absent; do not fill; do not infer |

**Never fill a Tier 1 field with Grade E.**

### Step 3 — Version reconciliation

Before comparing any KCB or RiQ value across strains, check: antiSMASH version match, MIBiG version match, TTA source tier match, and antiSMASH product vocabulary normalization.

### Step 4 — Gap register

After completing Steps 1–3, produce a Gap Register.

**If a strain has >50% of Tier 1 fields at Grade X, recommend re-analysis before including in the comparison.**

---

## 41.4a CROSS-STRAIN ASSEMBLY POLICY (mandatory)

**Fragmented assemblies are flagged, not penalized.**

When comparing marker burden, BGC counts, or any per-strain metric across a set that includes fragmented assemblies, apply this policy:

1. **Flag, do not weight.** Report raw counts with an assembly-quality indicator (⚠ or tier label). Do not apply a strain-level weight multiplier (e.g. ×0.45 for VERY_POOR) to marker counts or BGC inventories. Hidden numerical corrections to cross-strain rankings are undocumented judgment and must not be added silently.

2. **BGC-level discrimination only.** Edge or Full-contig truncation may receive −2 in GOOD/MODERATE assemblies when the boundary materially limits interpretation. In POOR/VERY_POOR assemblies the Edge/FC score effect is 0 because truncation is primarily an assembly artifact. **Interior BGCs from fragmented genomes are not discounted** — a shattered assembly can still contain a real, complete Interior/Arch-A cluster on a long contig.

3. **Long-read priority.** For POOR or VERY_POOR strains: note long-read sequencing as Priority 1 in the Layer B report. Do not exclude the strain from cross-strain tables pending re-sequencing.

4. **Distinguish inflated count from confirmed biology.** AS-class strains with >1500 contigs may have inflated raw BGC counts from assembly fragmentation. State this explicitly in the gap register and synthesis, but do not replace raw counts with a corrected estimate — the correction is unverifiable without re-assembly. Show the raw number and the ⚠ flag together; let the reader apply judgment.

5. **What is permitted:** sorting strains by assembly quality in supplementary tables; adding a "reliable for quantitative comparison" Boolean field in the UCS master; noting that strains with >1500 contigs have unreliable raw BGC counts. None of these constitute numeric down-weighting.

---



All UCS tables and comparison tables must include an evidence grade column or cell-level superscript (A–E/X).

*Worked example from reference project:*

| Strain ID | Corrected BGC | Grade | NRPS count | Grade | Top KCB hit | Grade |
|--------|--------------|-------|------------|-------|-------------|-------|
| [Strain A] | [value] | [grade] | [value] | [grade] | [class] | [grade] |
| [Strain B] | [value] | [grade] | [value] | [grade] | [class] | [grade] |
| [Strain C] | [value] | [grade] | [value] | [grade] | [class] | [grade] |

*Reference project examples are published in the companion data paper. Populate with your own collection's values.*

Shading convention: A = white, B = pale blue, C = pale yellow, D = pale orange, E = pale red (warning), X = grey strikethrough.

---

## 41.6 WITHIN-HABITAT COMPARISON WORKFLOW

**Trigger:** `Run within-habitat comparison for [Habitat class]. Strains: [list].`

**Steps 1–9:** (UCS population → Genus diversity → BGC class co-occurrence → Shared domain scan → Novelty profile → bldA tier → Bioactivity correlation → TFBS network → Synthesis paragraph)

Apply all steps per the full workflow. Shared signature classification:
- **VERTICAL INHERITANCE:** Shared by strains of the same genus or family
- **HGT CANDIDATE:** Shared by strains of unrelated genera with flanking transposase/integrase
- **CONVERGENT:** Shared by distantly related genera with different gene neighborhood

Evidence requirement: shared domain must reach Grade A or B in both strains to qualify.

---

## 41.7 CROSS-HABITAT COMPARISON WORKFLOW

**Trigger:** `Run cross-habitat comparison: [Habitat A] vs [Habitat B].`

Steps include: aggregate habitat-level UCS tables → habitat-level BGC class enrichment → shared vs exclusive compound class matrix → TFBS cross-habitat comparison → genus overlap analysis → assembly quality confound check → cross-habitat synthesis (≥200 words).

**Assembly quality confound warning (mandatory when mean quality tier differs by >1 level between habitat categories):**

> "Direct BGC count comparisons between [Habitat A] and [Habitat B] are partially confounded by assembly quality differences (mean tier: [A] vs [B]). Corrected BGC counts are used throughout; per-strain range is provided."

---

## 41.8 HGT CANDIDATE IDENTIFICATION PROTOCOL

Shared unusual domain signatures across phylogenetically distant strains in the same [Habitat] are the strongest evidence for horizontal gene transfer (HGT) within an actinomycete community.

### Criteria for flagging as HGT candidate (must meet ALL):

1. Domain is present in ≥2 strains from different genera in the same [Habitat]
2. Domain bitscore is Grade A or B in both strains
3. Domain is unusual in context (not a standard housekeeping or siderophore domain)
4. Gene neighborhood in both strains includes a compatible ecological context
5. At least one flanking transposase or integrase is present within 10 kb in at least one strain (Grade A/B)

### HGT candidate record format:

```markdown
## HGT Candidate — [Domain ID] — [Habitat class]
**Domain:** [TIGRFAM/PFAM ID, domain name]
**Strains carrying it:** [list with BGC node, bitscore, evidence grade]
**Genera:** [list — must be phylogenetically distant for HGT call]
**Gene neighborhood match:** [Describe shared flanking architecture, if any]
**Transposase/integrase:** [Present in [Strain ID], [distance from domain], [bitscore]]
**Candidate donor lineage:** [Organism class + ecological rationale]
**Ecological context:** [Why would this gene be selectively advantageous in this [Habitat]?]
**Classification:** HGT CANDIDATE — requires phylogenetic confirmation (ML tree of domain protein sequences across reference database)
**Recommended validation:** Reconstruct ML protein tree for [domain]; topology inconsistent with organismal phylogeny = HGT confirmation
```

### Current HGT candidate register (reference project):

**BRYO-HGT-001 — RETIRED 2026-05-29.**

hglE-KS glycolipid domain was initially designated BRYO-HGT-001 (cyanobacterial donor hypothesis, moss-specific). This designation is now retired. hglE-KS has since been confirmed in 8 strains/7 genera across all 3 habitats (Bryophyte, Attine, Hymenoptera), refuting the moss-cyanobacterium donor hypothesis and the habitat-specificity claim. hglE-KS is now designated **hglE-KS-PREV-001 — Prevalent Glycolipid Domain, habitat-non-specific.** The current rules registry records hglE-KS as informational and nonblocking. A zero or unavailable KCB result does not establish structural novelty; retain the actual comparison state and source scope. Reference PDF: CCSM_HGT_Register_Update_hglE-KS_2026-05-29.pdf.

**Active HGT candidates:** None currently active. New candidates will be designated PREV-XXX (prevalent/non-specific) or HGT-XXX (confirmed habitat-linked with ML phylogenetic evidence) as they emerge.

---

## 41.9 SPLIT-PATHWAY CROSS-STRAIN DETECTION

Distinct from within-strain split pathways (Section 30.3). Flag as PARALLEL CAPACITY (most common) or CROSS-STRAIN FRAGMENT CANDIDATE (rare, requires strong domain-level evidence).

---

## 41.10 COMPARISON DELIVERABLES

### 41.10.1 Gap Register PDF
Filename: `CCSM_GapRegister_[HabitatOrSet]_YYYY-MM-DD.pdf`

### 41.10.2 UCS Master Table (Excel)
Filename: `CCSM_UCS_[HabitatOrSet]_YYYY-MM-DD.xlsx`

### 41.10.3 Within-Habitat Comparison Report (PDF)
Sections: Gap Register summary → Genus diversity → BGC class co-occurrence matrix → Shared signature table → Novelty profile → bldA tier → Bioactivity correlation → TFBS comparison → HGT candidates → Synthesis → Manuscript-safe claim inventory → Audit log.
Filename: `CCSM_WithinHabitat_[HabitatClass]_YYYY-MM-DD.pdf`

### 41.10.4 Cross-Habitat Comparison Report (PDF)
Filename: `CCSM_CrossHabitat_[HabitatA]-vs-[HabitatB]_YYYY-MM-DD.pdf`

### 41.10.5 React JSX Comparison Dashboard
Filename: `CCSM_Dashboard_[Set]_YYYY-MM-DD.jsx`

### 41.10.6 Ecological Hypothesis Register (PDF)
Filename: `CCSM_EcoHypotheses_[Set]_YYYY-MM-DD.pdf`

### 41.10.7 Figures
- Fig A: BGC class co-occurrence heatmap (within-habitat)
- Fig B: Novelty profile stacked bar (within-habitat + cross-habitat)
- Fig C: TFBS network radar chart (per [Habitat])
- Fig D: Cross-habitat Venn/UpSet of shared vs exclusive compound classes
- Fig E: HGT candidate network diagram

All figure rules from Section 16 apply.

---

## 41.11 TRIGGER PHRASES

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#4111-trigger-phrases).

## 41.12 APPLICATION TO CURRENT PROJECT DATASET

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#4112-application-to-current-project-dataset).

## 41.13 QA GATES FOR CCSM (additions to Section 30)

### 30.6 CCSM Normalization Gate

- [ ] UCS populated for all strains to Grade A–D (no Grade E or X in Tier 1 fields)
- [ ] Gap Register produced and acknowledged
- [ ] antiSMASH and MIBiG versions documented for every strain
- [ ] Version-mismatch warnings applied to all cross-version comparisons
- [ ] TTA source tier documented

### 30.7 CCSM Cross-Strain Claim Gate

- [ ] Evidence grade cited for each contributing strain
- [ ] Assembly quality confound check applied
- [ ] No shared signature attributed to HGT without meeting all five criteria in Section 41.8
- [ ] No bioactivity–BGC correlative claim made across strains without matching assay methods
- [ ] All comparative ecological hypotheses follow Section 17.10 format
- [ ] At least one testable prediction per cross-strain hypothesis references a specific experiment design

---

## 41.14 VERSION HISTORY FOR THIS SECTION

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#4114-version-history-for-this-section).

## SECTION 42 — Large Modular PKS Rescue Workflow (LMPKS-RW) v1.0

### 42.1 Purpose

Detect large modular type I PKS, macrolide, polyene, trans-AT, and linear polyketide pathways that are missed, undercalled, split across contigs, or dereplicated poorly by standard antiSMASH product labels and KCB scores. Section 42 is a rescue workflow, not a replacement for standard BGC inventory. It is run alongside the KCB sweep whenever the automatic triggers below fire.

Use manuscript-safe language throughout: **"contains domains consistent with"**, **"candidate large modular PKS"**, **"candidate macrolide-family architecture"**, or **"split-pathway hypothesis"**.

**Guardrail:** LMPKS Rescue must not override stronger non-PKS interpretations unless modular PKS evidence is present. Require at least one of the following before assigning an LMPKS rescue grade: mod_KS / hyb_KS / tra_KS evidence, PKS_AT evidence, PKS_Docking_Nterm or PKS_Docking_Cterm evidence, TE / Abhydrolase_1 release-domain evidence, repeated KR/DH/ER reductive-loop logic, or cross-contig PKS module accumulation. If those signatures are absent, record an LMPKS null result.

### 42.2 Automatic trigger conditions

| Trigger | Condition | Required action |
|---|---|---|
| Trigger 1 — Weak KCB T1PKS | Any Interior T1PKS BGC with KCB cumulative score <1,500, including zero | Run full module reconstruction (§42.3–42.5) |
| Trigger 2 — Truncated PKS fragment | Any FC/Edge T1PKS BGC with at least one mod_KS/hyb_KS/tra_KS domain ≥300 bitscore | Run fragment rescue (§42.6) |
| Trigger 3 — Genome-wide accumulation | Total genome-wide mod_KS + hyb_KS + tra_KS count ≥4 across all contigs | Report `LMPKS_FRAGMENT_SET`; elevate sequencing priority |
| Trigger 4 — Possible trans-AT PKS | T1PKS-like BGC has KS/KR/DH/ER modules but lacks in-cis PKS_AT domains | Run trans-AT protocol (§42.8) |
| Trigger 5 — Possible polyene | Any BGC has ≥3 DH domains, especially with repeated KR/DH modules and absent/limited ER | Run polyene rescue (§42.9) |
| Trigger 6 — Published chemistry mismatch | Published macrolide, polyene, linear PKS, or large modular PKS chemistry exists for the strain/genus but antiSMASH lacks a clean matching named BGC | Map chemistry back to BGC/domain evidence (§42.10) |

Null result rule: if no trigger fires, include a one-page LMPKS null result in the compiled PDF listing each criterion checked.

### 42.3 Required domain signature library

For every T1PKS candidate, extract and tabulate: mod_KS, hyb_KS, tra_KS, ene_KS, itr_KS, PKS_AT (with substrate prediction), PKS_KR, PKS_DH, PKS_ER, ACP/PP-binding, PKS_Docking_Nterm / PKS_Docking_Cterm, Thioesterase / Abhydrolase_1, Glycosyltransferases / deoxysugar enzymes.

### 42.4 Module architecture reconstruction

Classify each module as: Complete module (KS + AT + ACP ± KR/DH/ER), Reduced module, trans-AT module (KS + ACP, no in-cis AT), Fragmentary module (KS-only or KS + partial reductive loop), or Release module (TE/Abhydrolase_1 or other release/cyclization domain).

Report module string compactly, e.g.:
```text
M1: KS-AT(mmal)-KR-ACP | M2: KS-AT(mal)-DH-KR-ACP | M3: KS-AT(mmal)-KR-ACP-TE
```

For FC/Edge contigs, prefix missing termini with `[missing start]` or `[missing terminus]`.

### 42.5 Chain length, oxidation state, and ring-size estimation

Estimate only broad classes unless the full module series is visible.

| Evidence | Interpretation |
|---|---|
| ≥3 complete modules + TE | Candidate macrolide / modular PKS product |
| ≥5 modules + TE | Large macrolide or large modular PKS candidate |
| ≥3 modules without TE | Linear PKS or incomplete macrolide pathway |
| methylmalonyl-dominant AT | Branched macrolide-like chain possible |
| malonyl-dominant AT | Linear or less methyl-branched polyketide possible |
| repeated DH with few/no ER | Polyene or highly unsaturated chain candidate |

Ring-size language must be cautious: say **"consistent with a 14-/16-/large-membered macrolide-family architecture"** only when module count, AT pattern, and release logic support it.

### 42.6 Fragment accumulation and LMPKS_FRAGMENT_SET protocol

Create a genome-wide table of all mod_KS, hyb_KS, and tra_KS domains found across the entire antiSMASH record, including domains outside annotated BGC coordinates.

Required columns:

| Strain ID | BGC # or unclustered | Node/contig | Locus tag | KS subtype | Bitscore | Edge status | Nearby AT/KR/DH/ER/ACP | Docking domain | TE/Abhydrolase nearby | Interpretation |

Assign `LMPKS_FRAGMENT_SET` when total mod_KS + hyb_KS + tra_KS count is ≥4 across the genome. If hits occur on ≥3 contigs or include both N-terminal and C-terminal docking domains on different contigs, elevate long-read sequencing to Priority 1.

### 42.7 Split-pathway rescue for large modular PKS

When multiple contigs/BGCs contain compatible PKS fragments: group fragments by KS subtype, AT substrate pattern, docking domains, and KCB/RiQ hints; identify start/internal/terminal fragments; check for TE/Abhydrolase-containing terminal fragment; check for deoxysugar/tailoring genes near PKS fragments.

Required claim-safety sentence:

```text
This is a split-pathway rescue hypothesis based on modular PKS domain architecture across contigs; long-read sequencing is required to confirm physical linkage and module order.
```

### 42.8 trans-AT PKS special protocol

Run when a T1PKS candidate has KS/ACP/reductive domains but lacks in-cis PKS_AT domains. Check for: standalone AT enzymes elsewhere, ACP-rich modular genes with docking domains, DH/KR/ER patterns inconsistent with cis-AT assembly, KCB/RiQ hints to known trans-AT polyketide families.

Call **trans-AT PKS confirmed** only when AT absence is real and a plausible trans-acting AT source exists. Otherwise call **trans-AT-like candidate** or **AT-missing fragment**.

### 42.9 Polyene rescue protocol

Run when ≥3 DH domains occur in a T1PKS candidate or fragment set.

| Feature | Polyene interpretation |
|---|---|
| ≥3 DH domains | Unsaturated-chain candidate |
| ≥5 DH domains | Strong polyene rescue trigger |
| DH-rich + ER-poor | Polyene-like oxidation pattern |
| TE present | Polyene macrolide closure plausible |

Do not call a named polyene without strong KCB/RiQ or chemistry. Use **"polyene-like modular PKS candidate"** unless confirmed.

### 42.10 Published compound family mapping table

| Family / class | BGC signals to look for | Report language |
|---|---|---|
| 14-membered macrolide / erythromycin class | Modular cis-AT PKS, TE, methylmalonyl modules, deoxysugar tailoring | Candidate 14-membered macrolide-family architecture |
| 16-membered macrolide / tylosin/spiramycin/niddamycin class | Multiple methylmalonyl modules, glycosylation/tailoring, TE, large split PKS possible | Candidate 16-membered macrolide-family architecture |
| Large macrolide / rapamycin class | Many modules, large BGC, TE, mixed AT patterns | Candidate large macrolide / rapamycin-like architecture |
| Polyene macrolide | DH-rich modular PKS, ER-poor regions, TE, UV 300–400 nm prediction | Candidate polyene macrolide architecture |
| Linear polyketide | ≥3 modules, absent TE or no clear cyclization domain | Candidate linear PKS architecture |
| trans-AT polyketide | KS/ACP/reductive modules with missing cis AT and candidate standalone AT | Candidate trans-AT PKS architecture |

### 42.11 Rescue grades and wet-lab interpretation

| Grade | Definition | Recommended interpretation |
|---|---|---|
| LMPKS-A | ≥3 complete modules, TE/release domain, classifiable AT/reductive pattern | High-confidence LMPKS candidate; wet-lab bonus +2 |
| LMPKS-B | ≥2 modules plus docking domains or clear split-module evidence, but incomplete release or termini | Strong rescue candidate; wet-lab bonus +1 |
| LMPKS-C | Fragment accumulation ≥4 mod_KS/hyb_KS/tra_KS but insufficient ordering | `LMPKS_FRAGMENT_SET`; sequencing priority +1 |
| LMPKS-D | Single T1PKS fragment with high bitscore but no joining evidence | Keep in inventory; no wet-lab bonus |
| LMPKS-T | trans-AT PKS confirmed or strongly supported | Wet-lab bonus +2 |
| LMPKS-P | Polyene rescue confirmed or strongly supported | Wet-lab bonus +2 |
| LMPKS-L | Linear PKS candidate, ≥3 modules, no TE/release recovered | Wet-lab bonus +1 |
| LMPKS-X | Trigger fired but evidence fails rescue criteria | Report null/negative rescue result; no bonus |

LMPKS bonuses do not stack with each other. Apply only the highest applicable LMPKS bonus.

### 42.12 QA checklist

- [ ] Every T1PKS Interior BGC with KCB <1,500 evaluated
- [ ] Every FC/Edge T1PKS BGC with mod_KS/hyb_KS/tra_KS ≥300 bitscore evaluated
- [ ] Genome-wide mod_KS/hyb_KS/tra_KS count reported
- [ ] `LMPKS_FRAGMENT_SET` assigned when total qualifying KS count ≥4
- [ ] Docking domains searched and reported
- [ ] TE/Abhydrolase_1 release logic searched and reported
- [ ] AT predictions summarized
- [ ] Reductive loops summarized by KR/DH/ER presence
- [ ] trans-AT criteria checked for AT-missing modular PKS candidates
- [ ] Polyene criteria checked for DH-rich candidates
- [ ] Rescue grade assigned for every triggered BGC or fragment set
- [ ] Long-read sequencing recommendation updated where fragment accumulation or split-pathway evidence exists

### 42.13 LMPKS Rescue Report format

Filename: `[Strain ID]_LMPKS_Rescue_Report_YYYY-MM-DD.pdf`

Required sections: Trigger summary and null-result status | Genome-wide KS inventory table | Per-BGC LMPKS trigger table | Module architecture reconstruction | Split-pathway / fragment accumulation model | trans-AT and polyene rescue checks | Published chemistry mapping | Rescue grades and WL adjustments | Long-read sequencing recommendation | Claim-safety statement.

### 42.14 Section 42 version history

| Version | Date | Notes |
|---|---|---|
| LMPKS-RW v1.0 | 2026-05-28 | Initial large modular PKS rescue workflow. |

---

## SECTION 43 — Cryptic-Class / Tailoring Trigger Module (CCTT) v1.0

### 43.1 Purpose

Detect compound classes and tailoring signals that standard antiSMASH product labels, KnownClusterBlast cumulative scores, and RiQ systematically miss or under-weight. CCTT generalizes the LMPKS rescue principle (Section 42): when cluster-level scores fail, interrogate at the domain/gene level. **Section 42 (LMPKS) is the prototype and first member of this module.**

Two failure axes are addressed:
- **Tailoring signals** antiSMASH detects as accessory domains but does not promote to a class label (e.g., halogenation).
- **Core scaffolds** antiSMASH detects badly and that score near-zero at the cluster level even when individual genes are definitive (e.g., peptidyl-nucleosides — cf. the Section 34 "0% MIBiG cluster similarity" trap and the AS-XXX NODE_162 worked example).

Use manuscript-safe language throughout.

### 43.2 Trigger table

Run a marker scan across the full record (CDS features within and outside annotated BGC coordinates, as in the Section 42 genome-wide KS inventory).

| Trigger | Marker (with bitscore floor) | Co-location requirement | Cluster-score override? | Routes to / action | Priority & WL effect (bounded) |
|---|---|---|---|---|---|
| **T43-HAL — Halogenation** | FAD-dependent halogenase (Trp_halogenase, PF04820-type, BS ≥150); non-heme Fe(II)/α-KG halogenase (SyrB2/CytC3-type, Fe2OG/TauD context — active-site check required) | A biosynthetic scaffold (PKS/NRPS/RiPP/sugar) present in the same BGC | **No** (tailoring, not core class) | Flag "halogenated [scaffold] candidate"; route extraction to **halogen-isotope-aware HRMS** (Cl M+2, Br M+2/M+4) | Tiered — see 43.4 |
| **T43-NUC — Peptidyl-nucleoside** | Characterized nucleoside-antibiotic enzyme homology (NikJ-type, BS ≥300, AS-XXX seed); translocase-I / MraY-family inhibitor-pathway markers; nucleoside-core / sugar-nucleotide enzymes; nucleobase deaminase/cytidylyltransferase | Secondary-metabolite context: partial NRPS (peptidyl arm), sugar tailoring, dedicated transporter, or resistance gene | **Yes** — gene-level homology governs even at cluster KCB/RiQ ≈ 0 | Call candidate nucleoside class; state mechanism hypothesis; route to **§37 polar/peptidyl-nucleoside row** (UV 262 nm, SAX/ion-exchange, NOT standard C18) | Override low-cluster deprioritization; floor MEDIUM; bounded bonus 43.4 |
| **T43-PHO — Phosphonate** | PEP mutase (PepM; ICL/PEP-mutase family, PF13714-type, BS ≥150) — the committed/diagnostic step of phosphonate biosynthesis | None (PepM is effectively single-marker diagnostic) | **Yes** | Affirmative phosphonate class call; resolves saccharide/"phosphonoglycan" fragmentation mislabels | Floor MEDIUM if interior; bounded +1 |
| **T43-ENE — Enediyne** | Enediyne PKS warhead ketosynthase (ene_KS; AS-XXX seed ene_KS E=2.3e-264) | PKS context | **Partial** (ene_KS is highly specific) | Cytotoxic / DNA-damaging warhead lead; [E-signal] note (cytotoxicity-guided handling, standard SOPs) | Bounded +1; flag as cytotoxic |
| **T43-AMC — Aminocyclitol / aminoglycoside** | 2-deoxy-scyllo-inosose synthase (DOIS / BtrC family, BS ≥150) — committed step of 2-deoxystreptamine aminoglycosides | Sugar/glycosyltransferase context | **Yes (affirmative AND rule-out)** | If present: candidate aminoglycoside/aminocyclitol. **If absent on a BGC whose KCB top hit is an aminoglycoside: affirmatively rule out the KCB call**, except when the KCB top hit is streptomycin-class; then apply the mandatory streptomycin carve-out below. | Affirmative: floor MEDIUM. Rule-out: no bonus; correct the class label |

> **Streptomycin-class carve-out (mandatory):** The DOIS rule-out does **not** apply when the aminoglycoside KCB top hit is specifically the streptomycin class (streptomycin, dihydrostreptomycin, bluensomycin, or closely related compounds). Streptomycin biosynthesis uses the streptidine / TDP-L-dihydrostreptose pathway, which does not involve DOIS. The committed diagnostic steps for this class are: scyllo-inosamine-4-phosphate amidinotransferase (StrB1-type), streptomycin-6-kinase (StrK-type), and NDP-L-dihydrostreptose synthase. If the KCB hit is streptomycin-class and DOIS is absent: check for StrB1/StrK homologs before applying the rule-out. If those markers are also absent, the KCB hit is likely spurious — assign class from domain architecture. If StrB1/StrK homologs ARE present, call as streptomycin-class candidate without a DOIS requirement.
| **T43-IDC — Indolocarbazole** | Chromopyrrolic acid synthase / indsynth (antiSMASH rule-based marker, BS ≥500; E ≤ 1e-100 preferred; reference: AS-XXX ctg182_7, E=0, BS=1349.6). Note: antiSMASH "indole" product rule fires on `(indsynth or dmat or indole_PTase)` — dmat (dimethylallyl tryptophan synthase, ergot alkaloid class) and indole_PTase must be ruled out; indsynth at BS ≥500 is specific for the indolocarbazole / chromopyrrolic acid class | None required — indsynth at this bitscore threshold is effectively single-marker diagnostic; cross-check for Trp_halogenase (PF04820) on same or adjacent contigs to distinguish halogenated (rebeccamycin / AT2433 class) from non-halogenated (arcyriarubin / staurosporine class) variants | **Yes** — indsynth is as class-definitive as ene_KS for enediynes or NikJ-type for nikkomycin; cumulative KCB = 0 is expected when contig is truncated and does NOT indicate absence of the class; apply the §34 "0% MIBiG cluster similarity" trap | Call candidate indolocarbazole class; if antiSMASH product label is "indole", apply §34 "indole masking indolocarbazole" trap; if Trp_halogenase on a different contig → split-pathway candidate (§42.7); route to §37 indolocarbazole row; flag ⚠ cytotoxicity caution; do NOT award Candida mechanistic link (+2 WL) per §33.3 clarification | Floor MEDIUM regardless of KCB score; bounded WL +1; ⚠ cytotoxicity flag mandatory |
| **T43-PTM — HSAF / Polycyclic Tetramate Macrolactam** | Ornithine-selective A-domain (confirmed by Stachelhaus code prediction or NRPS substrate predictor comparison against HslO/HslI from *Lysobacter enzymogenes* ATCC 29,214 or equivalent characterized HSAF synthetase reference) + iterative PKS architecture (same KS domain reused across multiple extension cycles — detectable as a single KS ORF with anomalously high KS:ACP ratio or multiple downstream ACP domains on the same polypeptide) | PKS-NRPS hybrid context required; standalone ornithine A-domain without iterative PKS co-occurrence is insufficient to fire this trigger | **Yes** — ornithine A-domain selectivity within an iterative PKS-NRPS context is not shared with any other major natural product class; gene-level evidence governs even when KCB score is low or zero | Call candidate HSAF/PTM class; route to §37 HSAF/PTM row; award §33.3 Candida-specific mechanistic link (+2 WL) if Candida bioactivity is explicitly supplied with its source (never default-assumed); note acid-labile tetramate ring in extraction instructions (§37 and Fermentation Card); cross-check for three Hymenoptera strains with confirmed HSAF-class BGCs in this project (AS-XXX, AS-XXX, AS-XXX) for CCSM cross-strain comparison eligibility | Floor MEDIUM; Candida mechanistic link awards bounded WL +2 (Candida-specific, §33.3) |

> LMPKS (Section 42) is row **T43-LMPKS** of this module by reference; its full protocol remains in Section 42.

### 43.3 Detection rules and specificity guards

- **Halogenase guard.** Require BS ≥150 AND a halogenase substrate-binding-motif check. A lone halogenase with **no co-located biosynthetic scaffold** is NOT a trigger — see Section 34 trap.
- **Nucleoside guard.** Require EITHER high-confidence homology to a *characterized nucleoside-antibiotic* enzyme OR the co-location requirement. Do not fire on housekeeping nucleotide metabolism.
- **Fluorinase / vanadium haloperoxidase.** A fluorinase (SalL/FlA-type) or vanadium-dependent haloperoxidase anywhere is a **standalone high-novelty flag** regardless of co-location.
- **Bitscore floors are minima**, not targets.

### 43.4 Halogenation tiering (T43-HAL)

| Condition | Action | Priority / WL |
|---|---|---|
| 1 halogenase, scaffold present | Annotate; add Cl/Br isotope HRMS handle | No priority change; routing only |
| ≥2 halogenases in one BGC, OR ≥1 halogenase on a weak/novel-KCB cluster | "Polyhalogenation candidate"; isotope-aware HRMS | Floor MEDIUM; bounded WL +1 |
| Fluorinase or V-haloperoxidase anywhere | High-novelty standalone flag | Floor MEDIUM; bounded WL +1 |

> **Marine generalization:** the marine-flag halogenase emphasis is a special case of T43-HAL. When the marine flag is set, T43-HAL fires at the same thresholds.

### 43.5 Claim-safety and override discipline

CCTT triggers principally **route evidence-gathering and the correct extraction/dereplication protocol, and override a low-cluster-KCB deprioritization**. They are NOT unbounded priority inflators.

- Core-scaffold triggers with gene>cluster evidence (T43-NUC, T43-PHO, T43-AMC affirmative) **prevent LOW/Deprioritized** regardless of cluster KCB.
- WL bonuses from CCTT are **bounded and non-stacking among CCTT rows**: apply only the single highest applicable CCTT bonus (max +2). CCTT bonuses may co-exist with the standard Section 33 evidence bonuses.

### 43.6 CCTT report deliverable

Generated whenever any T43 trigger fires; one-page null result if none fire.
Filename: `[Strain ID]_CCTT_Trigger_Report_YYYY-MM-DD.pdf`

Required sections: Trigger summary table | Per-trigger interpretation with claim-safe class call | Affirmative rule-outs | Routing actions | Pairing notes (e.g., T43-NUC chitin-synthase inhibitor + Section 44 secreted chitinases = two-pronged anti-chitin strategy) | Claim-safety statement.

### 43.7 Trigger phrases

```text
Run cryptic-class trigger scan on [Strain ID].
Run CCTT on [Strain ID].
Run halogenase scan on [Strain ID].
Run nucleoside / peptidyl-nucleoside scan on [Strain ID].
Run phosphonate scan on [Strain ID].
Run enediyne scan on [Strain ID].
Run aminocyclitol / aminoglycoside rule-out on [Strain ID].
```

---

## SECTION 44 — Chitin / Glycan-Active Defense Module (CGAD) v1.0

### 44.1 Purpose and placement

CGAD is a **genome-wide functional output**, reported once per strain like the TFBS networks — NOT a per-BGC biosynthetic call. It detects chitin-active and chitin-catabolic capacity and wires it into ecological synthesis.

Distinct from CCTT (Section 43, biosynthetic): CGAD describes how the strain *interacts with its niche*, not what scaffold it builds.

CGAD output appears in two places, fired together:
1. As a standalone genome-wide capacity table (this section).
2. As an amplifier of Section 17.4 (polysaccharide substrate coupling) and the DasR row of Section 17.3.


### 44.1A Step 0 — Proteome Scope Check (required gate; v8.0.2)

CGAD is explicitly genome-wide. Therefore, CGAD must **not** be scored from BGC-region cluster_hmmer hits alone. Before any §44.2 detection target is interpreted, establish and report the proteome scope state:

| Scope state | Definition | Allowed CGAD verdict language |
|---|---|---|
| `full proteome scanned` | All predicted CDS translations across the full record/genome were scanned, including CDS features inside and outside annotated BGC coordinate windows. Preferred source: antiSMASH full-genome GBK `/translation=` fields; fallback: Prodigal/Prokka protein FASTA from uploaded genome FASTA. | None / Low / Moderate / High, with method stated. A true null is allowed only in this state. |
| `BGC-region only` | Only antiSMASH BGC-region domain hits, cluster_hmmer, or BGC-coordinate features were available/scanned. | `Not Assessable — BGC-region scope only`; do not report null chitinolytic capacity. |
| `full proteome unavailable` | No complete GBK translations, protein FASTA, or feasible CDS prediction was available. | `Not Assessable — full proteome unavailable`; record missingness in §38.2. |

**Required extraction rule:** when antiSMASH GBK files contain `/translation=` qualifiers for CDS features, extract all CDS translations across every contig/record as the first-pass proteome. This is the normal path for antiSMASH runs from raw FASTA because the full Prodigal-predicted proteome is often already embedded in the GBK. Do not require a separate Prokka run unless GBK translations are absent or incomplete.

**Genome-wide scan rule:** scan CDS features across the entire record, not only within annotated BGC coordinate windows. This mirrors the genome-wide KS inventory in §42.3 and the full-record marker scan in §43.

**Detection-method tiering:**

| Detection method | Claim language |
|---|---|
| Motif/signature scan only (e.g., PROSITE catalytic motif plus signal peptide prediction) | "secreted GH18/GH19/LPMO candidates" |
| HMMER profile scan against appropriate families (e.g., PF00704 GH18, PF00182 GH19, PF03067 AA10/CBM33) at stated threshold (default E ≤ 1e-5 unless otherwise justified) plus architecture/signal-peptide checks | "high-confidence secreted GH18/GH19/LPMO candidates" |
| BGC-region-only hit list | "BGC-local carbohydrate-active signatures only; genome-wide chitinolytic capacity not assessable" |


**HMMER-unavailable fallback protocol:**

When HMMER profiles (PF00704 GH18, PF00182 GH19, PF03067 AA10) are not
accessible, apply the following validated active-site motif screen as a minimum
CGAD effort. The full proteome must still be scanned — do not fall back to
BGC-region-only scope.

GH18 candidates — screen all predicted protein translations for all of:
  (1) Active-site motif D[ILVM]D[MLIFY]E (conserved DxDxE catalytic triad
      of bacterial GH18 chitinases)
  (2) Aromatic enrichment: W + Y count ≥ 6 per protein
  (3) N-terminal signal peptide: ≥ 8 hydrophobic residues (ILVMFYWCA)
      within the first 30 amino acids
  (4) Length filter: 200–850 aa (bacterial secreted GH18 range)

AA10 / GH19: report as "Not Assessable by motif screen — HMMER confirmation
required." Do not infer null capacity for these classes from a motif scan.

Claim language for motif-only results:
  APPROVED:   "Motif-level scan identified [N] secreted proteins consistent
               with GH18-type chitinase architecture; HMMER PF00704
               confirmation required before publication-level claims."
  NOT APPROVED: "High-confidence secreted GH18 candidates" — this phrase
               requires HMMER confirmation.
  NOT APPROVED: "No chitinases detected" or "lacks chitinolytic capacity"
               after a motif-only scan.

The proteome scope state for a motif-only run is: `full proteome scanned
(motif-only method)` — not `BGC-region only` and not `full proteome
unavailable`. A true null verdict requires full-proteome HMMER.

**Prior-result rule:** any prior CGAD null or weak verdict based only on BGC-region scope must be reclassified as `Not Assessable pending proteome rescan`, not as confirmed absence.

### 44.2 Detection targets

Run these targets only after §44.1A establishes proteome scope. Report the scope state and detection method for every row.

| Class | Markers | Notes |
|---|---|---|
| Endo/exo-chitinases | GH18 (PF00704-type), GH19 (PF00182-type) | GH18 is large and includes non-chitinase members — require catalytic-motif and modular-architecture check |
| LPMOs (chitin-active) | AA10 / CBM33 lytic polysaccharide monooxygenases | **Flag separately** — high-value oxidative chitin-active enzymes |
| Chitin-binding modules | CBM5, CBM12, CBM14 | Accessory; count toward "secreted multimodular" classification |
| GlcNAc / chitobiose catabolism (DasR regulon) | NagA, NagB, chitobiose ABC transporter (DasABC-type), NagKC | Links chitin breakdown → GlcNAc → DasR de-repression of antibiotic BGCs |

### 44.3 Specificity guards

- **GH18 discrimination:** distinguish secreted, multimodular chitinases (catalytic GH18/GH19 + CBM + signal peptide) from lone catalytic domains. Report secreted multimodular separately.
- **LPMO (AA10)** reported as its own line — do not merge into the GH18 count.

### 44.4 Genome-wide capacity output

Produce a single table:

| Category | Proteome scope | Detection method | Count | Secreted/multimodular (n) | Top loci (locus tag, bitscore/E-value if available, contig) | Confidence language |
|---|---|---|---:|---:|---|---|
| GH18 chitinase | full proteome / BGC-region only / unavailable | HMMER / motif+signal peptide / BGC-local only | | | | candidate / high-confidence candidate / not assessable |
| GH19 chitinase | full proteome / BGC-region only / unavailable | HMMER / motif+signal peptide / BGC-local only | | | | candidate / high-confidence candidate / not assessable |
| AA10 LPMO (chitin-active) | full proteome / BGC-region only / unavailable | HMMER PF03067 / motif-only / BGC-local only | | | | candidate / high-confidence candidate / specificity unresolved |
| CBM5/12/14 chitin-binding | full proteome / BGC-region only / unavailable | HMMER / motif / BGC-local only | | | | accessory evidence |
| GlcNAc catabolism (DasR/NagR regulon context) | full proteome / BGC-region only / unavailable | HMMER/annotation / motif / BGC-local only | | | | substrate-supply evidence |

Plus a one-line **chitinolytic capacity verdict** using one of the three state-aware forms:

- `Full proteome scanned — None / Low / Moderate / High`, with method and whether a DasR/NagR genome-wide regulatory network co-occurs.
- `BGC-region only — scope limited; chitinolytic capacity not assessable`.
- `Full proteome unavailable — Not Assessable; do not report null capacity`.

A true `None` verdict is valid only when the full proteome was scanned with an appropriate method. If the scan was motif-only, state `candidate` language and list HMMER confirmation as missingness when manuscript-level confidence is needed.

### 44.5 Ecological wiring and hypotheses

When chitinolytic capacity is Moderate/High AND a DasR network is present, report a coupled hypothesis in Section 17.10 format:

- **Insect-associated hosts:** chitinases are dual-use — degrade fungal-pathogen cell walls (e.g., Escovopsis, Ascosphaera, entomopathogenic fungi) AND invertebrate-pest/competitor cuticle; liberated GlcNAc de-represses DasR → antibiotic BGC activation. This is the detectable backbone of a "guard" phenotype (cf. AS-XXX "Guard and Nourish").
- **Plant-associated / chitin-metabolizing plant contexts:** antiherbivore / anti-nematode / anti-fungal-pest defense via the same enzymes.
- **Pairing with CCTT T43-NUC:** if a nucleoside chitin-synthase inhibitor (nikkomycin/polyoxin-type) co-occurs with secreted chitinases, flag an explicit **two-pronged anti-chitin strategy** (degrade existing chitin + block new chitin synthesis).


**DasR/NagR coupling guard (v8.0.2):** DasR or NagR coupling hypotheses must not be written as genome-level mechanistic claims unless CGAD was run at full-proteome scope. If only BGC-region scope was available, write: "DasR/NagR coupling is plausible, but the GlcNAc substrate-supply component is unvalidated at genome scale." For non-actinomycetes, do not force DasR language; use the organism-appropriate GlcNAc regulator when known (e.g., NagR in many Proteobacteria/Burkholderia contexts) and state the regulatory assignment.

### 44.6 Claim-safety

Chitinolytic capacity is *consistent with* antifungal / anti-invertebrate defense; it is NOT proof the strain protects its host. State as Section 17.10 hypothesis with a testable prediction:
- "Chitin-induced cultures show elevated antifungal fractions" (induction prediction), or
- "Chitinase knockdown reduces Escovopsis/Candida inhibition" (loss-of-function prediction).

Approved: "full-proteome scan identified secreted GH18/GH19 chitinase candidates consistent with chitin-active defense capacity." Approved when HMMER-confirmed: "full-proteome HMMER scan identified high-confidence secreted GH18/GH19 chitinase candidates." Not approved: "protects the [Host] against fungal infection." Not approved after BGC-only scan: "lacks chitinases" or "no chitinolytic capacity."

### 44.7 Trigger phrases

```text
Run chitin / glycan-defense scan on [Strain ID].
Run CGAD on [Strain ID].
```


---

## SECTION 45 — Resistance Gene-Guided Compound Class Confirmation

### 45.1 Purpose and placement

Resistance genes within or adjacent to a BGC encode self-protection mechanisms that are mechanistically matched to the compound produced. This matching relationship provides a class-level confirmation signal independent of KCB score, RiQ, and domain architecture — and is therefore an orthogonal evidence type under the Section 32.4 minimum evidence rule.

Section 45 has three analytical functions:
1. **Class confirmation:** concordant resistance gene + biosynthetic BGC = strong class-level evidence.
2. **Polarity routing:** certain resistance transporters predict compound polarity and inform extraction protocol (§37).
3. **Conflict detection:** a resistance gene present but mechanistically incompatible with the BGC compound class is a §34 hallucination-trap signal (HGT resistance island, not producer self-protection).

**Important constraint:** Section 45 is a confirmation and routing tool, not a primary annotation tool. It does not replace domain architecture, KCB, RiQ, or module logic as the foundation of class assignment. Run it in parallel with the CCTT scan (§43), after the BGC inventory and hallucination-trap audit are complete.


**v8.1.1 claim-calibration rename:** Treat this section internally as the **Resistance Gene-Guided Prioritization and Target-Hypothesis Module**. Resistance genes are prioritization evidence, not product-identity proof. The strongest patterns are BGC proximity + target duplication + divergence + HGT/phylogenetic anomaly + concordance with biosynthetic logic. Generic efflux pumps, broad resistance annotations, or distant ARGs must not drive compound-family claims.

### 45.2 Proximity rule — critical guard

**A resistance gene contributes to class confirmation only if it is located:**
- Within the annotated BGC coordinates (highest confidence), **OR**
- Within 15 kb of either BGC boundary on the same contig (strong confidence, Tier 2).

Resistance genes on different contigs or >15 kb from the BGC boundary are **noted in the Evidence Traceability block** (§32.3) but do **not** contribute to Architecture Confidence scoring, WL adjustment, or the §32.4 minimum evidence count. Explain their absence as possible assembly fragmentation rather than absent self-protection.

**Why 15 kb?** Most actinomycete biosynthetic resistance genes are co-transcribed with the BGC or within a few gene lengths of its boundary. A 15 kb window captures these arrangements while excluding unrelated chromosomally acquired resistance islands.

### 45.3 Tier 1 — Near-definitive class confirmation

Tier 1 markers are so mechanistically specific that their presence within BGC coordinates provides near-definitive class confirmation independent of cluster-level KCB or RiQ scores. A single Tier 1 concordant hit counts as one independent evidence type under §32.4, and may support a Grade B → A upgrade in §31.5 when all other Grade A criteria are already met.

| Resistance marker | Required location | Compound class confirmed | Mechanistic basis |
|---|---|---|---|
| VanHAX operon (≥2 of 3 genes: VanH, VanA/B/D, VanX) | Within BGC coordinates | Glycopeptide producer | D-Ala–D-Lac remodelling of lipid II terminus confers producer immunity to its own glycopeptide product |
| CalC-type radical SAM self-sacrifice protein (MadL ortholog, BS ≥150 to characterized CalC) | Within BGC coordinates | Enediyne chromoprotein (maduropeptin/dynemicin/C-1027 class) | Radical SAM protein quenches the enediyne warhead via self-sacrificial radical abstraction; universal in chromoprotein enediyne producers |
| NikT/NikD-type high-affinity permease and/or self-resistance protein (BS ≥150 to characterized NikT/NikD from *S. tendae* Tu901) | Within BGC coordinates | Peptidyl-nucleoside (nikkomycin/polyoxin class) | Producer exports compound via dedicated MFS/ABC system; NikT encodes the nucleoside efflux system that protects the producer from chitin synthase inhibition by its own product |
| FomA (adenylyltransferase) + FomB (kinase) both present near PepM-containing BGC | Within BGC coordinates OR within 15 kb | Phosphonate (fosfomycin-class or closely related phosphonate) | FomA/B inactivate fosfomycin by adenylylation + phosphorylation; their co-presence with PepM (the committed phosphonate step) defines phosphonate class |
| DOIS (2-deoxy-scyllo-inosose synthase, BtrC family, BS ≥150) + ≥1 APH (aminoglycoside phosphotransferase) or AAC (aminoglycoside acetyltransferase) in same BGC | Within BGC coordinates | Aminoglycoside / aminocyclitol producer | DOIS encodes the committed step of 2-deoxystreptamine biosynthesis; co-encoded APH/AAC inactivates the producer's own compound for self-protection |

**Absence flag for CalC-type / enediyne BGCs (mandatory):** If a BGC contains ene_KS (T43-ENE trigger) or strong KCB/RiQ evidence for an enediyne compound class, but no CalC-type radical SAM gene is detected within 15 kb, raise an explicit flag in §36.4 (Reviewer Attack Simulation) and in the Missingness Register (§38.2):

```text
No CalC-type self-protection gene detected within 15 kb of [BGC] in the current draft assembly.
Interpretation: a CalC-type or equivalent self-protection gene is present in all characterized chromoprotein enediyne producers. The absence in this BGC likely reflects an unassembled or misassembled contig in the current draft, rather than a genuine absence. Long-read sequencing is required to resolve this.
Manuscript-safe wording: "No self-protection gene was detected within 15 kb of [BGC] in the current draft assembly; a CalC-type or equivalent resistance gene may reside on an unassembled or misassembled contig."
```

### 45.4 Tier 2 — Strong contextual support

Tier 2 markers are class-associated but require a concordance check: the predicted resistance mechanism must be compatible with the BGC compound class. A single Tier 2 concordant hit within 15 kb counts as one independent evidence type under §32.4, and may provide +0.5 support toward a Grade B → A upgrade when the architecture grade is otherwise borderline.

| Resistance marker | Required location | Compound class supported | Key concordance check | HGT guard condition |
|---|---|---|---|---|
| ErmC / ErmE / ErmSF rRNA adenine N-6-methyltransferase (BS ≥150) | Within 15 kb of BGC boundary | Macrolide / lincosamide / streptogramin B (MLSB) producer | The BGC must contain T1PKS macrolide-class modules OR lincosamide biosynthetic domains. Do NOT apply to T2PKS, NRPS-peptide, or terpene BGCs | If Erm gene is flanked by integrase or transposase elements within 5 kb AND biosynthetic gene neighbors are absent → HGT resistance island; classify under §34 trap; do not use as class confirmation |
| ErmC / ErmE within 15 kb of lincosamide adenylation or modification genes | Within 15 kb | Lincosamide producer | Require co-location with lincosamide-specific adenylation or modification domains | Same HGT guard as above |
| Divergent chitin synthase paralogue (same BGC, diverged active-site residues consistent with resistance, BS ≥150 to CaChs2 or ScChs2) | Within BGC coordinates or within 15 kb | Nikkomycin / polyoxin class (chitin synthase inhibitor) | Active-site divergence consistent with resistance must be demonstrable (compare key catalytic residues to reference chitin synthases) | Not applicable — endogenous paralogue; confirm it is not the primary chitin synthase gene of the producer |
| Rif-ADP-ribosyltransferase (ArrA / Arr-type, BS ≥150) | Within 15 kb of ansamycin-class PKS fragments | Ansamycin / rifamycin-class producer | BGC must contain PKS modules consistent with ansamycin scaffold (methylmalonyl-dominant AT, naphthalenic AHBA-primed modules, or strong KCB hit to rifamycin/geldanamycin/mitomycin) | If ArrA is flanked by integrase elements without biosynthetic neighbors → HGT resistance island |

### 45.5 Tier 3 — Polarity routing only

Tier 3 markers do not confirm compound class and do not affect Architecture Confidence or WL score. They inform extraction and fractionation strategy via the Metabolomics Readiness module (§37).

| Marker | Routing action |
|---|---|
| Large MFS transporter (≥14 TM helices, drug-efflux substrate-binding domain orientation) co-localized within BGC | Flag compound as moderate-polarity predicted; standard EtOAc/BuOH extraction likely sufficient; add to §37 in the moderate/nonpolar row |
| ABC transporter (2-component drug-type: substrate-binding protein + ATPase) co-localized within BGC | Flag compound as potentially polar or amphoteric; recommend parallel polar (50% MeOH/H₂O) and nonpolar (EtOAc) fractionation before HRMS dereplication |

Record in the Evidence Traceability block (§32.3 resistance gene row): "Tier 3 — polarity routing only; no class confirmation or WL adjustment."

### 45.6 Conflict detection — HGT resistance island vs producer self-protection

A resistance gene that is present but NOT functioning as producer self-protection is an analytically important null result. Mis-attributing it as class confirmation is the §34 hallucination trap "Resistance gene HGT acquisition misread as producer self-protection."

**Apply the HGT resistance island flag when ANY of the following conditions are met:**

| Condition | Interpretation | Action |
|---|---|---|
| Resistance gene is on a different contig from the claimed BGC | Assembly fragmentation may have separated gene from BGC — do not confirm class | Note in Evidence Traceability as "contig-separated; class confirmation not applicable until assembly resolved" |
| Resistance gene is >15 kb from the BGC boundary on the same contig | Outside proximity rule — not producer self-protection by this criterion | Record distance; note in Missingness Register if relevant compound class; do not count toward §32.4 |
| Resistance gene is flanked by integrase and/or transposase elements within 5 kb, with no biosynthetic gene neighbors | Classic HGT resistance island | Classify under §34 trap; flag in audit log; do not use as class confirmation |
| Resistance mechanism is mechanistically incompatible with the BGC compound class (e.g., ErmC near a T2PKS producing a non-macrolide compound; VanHAX near a NRPS-lipopeptide BGC) | Coincidental proximity; different evolutionary origin | Record as "mechanistic mismatch"; flag under §34 trap; rule out as class confirmation |

### 45.7 Architecture Confidence and WL scoring

**Architecture Confidence effects (§31.5):**
- Tier 1 concordant hit within BGC coordinates → counted as one independent evidence type for §32.4; supports B→A upgrade when all other Grade A criteria are already met. Does NOT override hallucination-trap caps (Grade C/D caps from split-pathway/fragmentation verdicts stand).
- Tier 2 concordant hit within 15 kb → provides additional support but is not independently sufficient for B→A upgrade; combine with other evidence.
- Neither tier upgrades a Grade D or E BGC beyond Grade D/E.

**WL adjustment (§33.3):**
- Concordant Tier 1 or Tier 2 resistance gene within proximity rule → **+1 WL** (non-stacking; apply once per BGC regardless of how many concordant markers are present).
- Tier 3 → no WL adjustment.
- HGT resistance island flagged → no WL adjustment (§34 trap applies instead).

### 45.8 Integration with other modules

- **§32.3 Evidence Traceability:** Every BGC's traceability block must include the resistance gene row — populated with marker type, locus tag, bitscore, distance from BGC boundary, tier, concordance verdict, and HGT guard outcome.
- **§34 Hallucination-Trap Audit:** HGT resistance island trap must be checked for all Erm, Van, APH, AAC, and ArrA hits.
- **§36.4 Reviewer Attack Simulation:** Self-protection absent from claimed cytotoxic BGC must be included as a reviewer attack category.
- **§37 Metabolomics Readiness:** Tier 3 routing notes populate the "Resistance gene concordance note" column in the Metabolomics_Readiness sheet.
- **§38.2 Missingness Register:** Absent self-protection from high-priority enediyne/glycopeptide/aminoglycoside BGCs is recorded as "Resistance gene missingness."
- **§43 CCTT:** T43-NUC and T43-ENE triggers are expected to co-occur with Tier 1 resistance markers when those classes are genuinely present. Flag the cross-check explicitly in the CCTT trigger report.

### 45.9 Genome-wide resistance gene scan procedure

For efficiency, scan the entire genome (not just BGC coordinates) for all Tier 1 and Tier 2 markers in a single pass, then map hits to BGC coordinates using the proximity rule.

**Recommended scan targets in order of class specificity:**

1. CalC-type radical SAM (ene_KS-containing BGCs → enediyne class)
2. VanHAX operon components (glycopeptide class)
3. NikT/NikD-type efflux (T43-NUC triggered BGCs → nikkomycin class)
4. FomA/FomB pair (T43-PHO triggered BGCs → phosphonate class)
5. DOIS + APH/AAC combination (T43-AMC triggered BGCs → aminoglycoside class)
6. ErmC/ErmE/ErmSF (T1PKS BGCs → macrolide/lincosamide class, HGT guard required)
7. ArrA/Arr-type (PKS BGCs with ansamycin KCB hits → ansamycin class, HGT guard required)
8. MFS and ABC transporters genome-wide → Tier 3 routing mapping

Record every hit in the `ResistanceGene_Confirmation` Excel sheet (Sheet 20) regardless of tier.

### 45.10 Resistance Gene Confirmation Report format

**Null result rule:** If no Tier 1 or Tier 2 markers are found within the proximity rule for any BGC, include a one-page null result stating which markers were searched, the scan scope, and the outcome. Do not omit the null result from the compiled PDF.

Filename: `[Strain ID]_ResistanceGene_Confirmation_YYYY-MM-DD.pdf`

Required sections:
1. Scan summary (markers searched, genome-wide scope confirmed, null/positive result).
2. Genome-wide hit table (all markers found, with locus tag, bitscore, contig, distance to nearest BGC boundary).
3. Per-BGC concordance table (Tier assigned, class concordance Y/N, HGT guard outcome, Arch Confidence effect, WL adjustment).
4. Absence flags for Tier 1 expected markers on high-priority BGCs (see §45.3 CalC absence flag).
5. HGT resistance island flags (§34 trap outcomes).
6. Routing actions issued (§37 polarity notes).
7. Integration summary (§32.4 evidence type count updated, §33.3 WL adjustments applied).
8. Claim-safety statement.

### 45.11 QA checklist (§30.9)

Before finalising the compiled master PDF:

- [ ] All BGCs with Tier 1 class predictions scanned for concordant resistance markers within BGC coordinates
- [ ] All BGCs within 15 kb of a Tier 1/2 marker checked for class concordance
- [ ] HGT guard applied to every Erm, Van, APH, AAC, and ArrA hit
- [ ] Absence flag raised for claimed enediyne/cytotoxic BGCs lacking any visible self-protection within 15 kb
- [ ] Absence flag raised for claimed glycopeptide or aminoglycoside BGCs lacking concordant self-protection within 15 kb
- [ ] Resistance Gene Confirmation Report included in compiled master PDF (or one-page null result at position 5.7)
- [ ] Architecture Confidence adjustments recorded in Evidence Traceability blocks
- [ ] WL adjustments recorded in WetLab_Decision_Matrix sheet (Sheet 10)
- [ ] All hits recorded in ResistanceGene_Confirmation sheet (Sheet 20)

### 45.12 Trigger phrases

```text
Run resistance gene confirmation on [Strain ID].
Run resistance gene scan on [Strain ID].
Check resistance gene profile for [BGC class] in [Strain ID].
Check self-protection genes for [Strain ID] BGC [N].
```

### 45.13 Section 45 version history

| Version | Date | Notes |
|---|---|---|
| v1.0 | 2026-05-29 | Initial section. Five Tier 1 markers (VanHAX, CalC-type, NikT/NikD-type, FomA/FomB, DOIS+APH/AAC); three Tier 2 markers (ErmC/ErmE/ErmSF, chitin synthase paralogue, ArrA); two Tier 3 routing-only markers (MFS, ABC transporter). Proximity rule: within BGC coordinates (highest confidence) or within 15 kb of BGC boundary on same contig (strong confidence). CalC absence flag for enediyne BGCs. HGT resistance island conflict detection as §34 trap. §36.4 required reviewer attack for absent self-protection from cytotoxic BGC. Architecture Confidence and WL scoring rules. Integration with §32.3, §32.4, §33.3, §34, §37, §38, §40, §43. QA gate §30.9. ResistanceGene_Confirmation sheet (Sheet 20 of Excel workbook). |


---

## v7.9 Final Completion Statement Template

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#v79-final-completion-statement-template).

## Standalone Prompt Completeness Check

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#standalone-prompt-completeness-check).

## Version History

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#version-history).

## SECTION 46 — v8.0 Execution and Readability Integration Supplement

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-46--v80-execution-and-readability-integration-supplement).

## SECTION 47 — v8.0.2 CGAD Genome-Wide Proteome Scope Supplement

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-47--v802-cgad-genome-wide-proteome-scope-supplement).

## SECTION 48 — v8.0.3 ICBG1735 Workflow-Flexibility Supplement

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-48--v803-icbg1735-workflow-flexibility-supplement).

## SECTION 49 — Reader-Facing Front Page and Briefing Package

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-49--reader-facing-front-page-and-briefing-package).

### 49.1A Front-page claim-safety gate

Reader-facing headlines must pass the Diagnostic Signature / Hallucination-Trap Card. Headlines may emphasize high-interest genetic signatures, rare markers, and follow-up value, but must not convert biosynthetic potential into confirmed production. PDB-style or news-style outputs should use phrases such as “genetic signature,” “candidate fragment,” “BGC lead,” “pathway-family signal,” or “high-priority follow-up lead” unless product-level chemistry is confirmed.


The package is intended for collaborators, PIs, lab meetings, internal presentations, development-phase strain prioritization, and visually memorable summaries that still preserve evidence boundaries.

### 49.7 Complete locus identity on reader-facing pages

For every individual locus, display `strain / full node-or-contig / region / BGC alias`, copied from one bound source record. The earlier shortened Node labels are superseded by the current evidence safeguard, including on front pages and executive memos. Do not omit the region when a contig carries several loci, shorten the contig string or invent a missing mapping. Missing/conflicting components remain an identity hold; retain source paths/hashes and coordinates in the accompanying record.


### 49.8 BGC count policy

Every reader-facing page must specify whether the BGC count is:

- raw antiSMASH region count;
- corrected BGC count;
- manually curated pathway count;
- split-pathway-adjusted count.

Recommended phrasing:

```text
38 raw antiSMASH regions; corrected BGC count pending curation.
```

or:

```text
38 raw antiSMASH regions; corrected BGC count: 34.
```

Avoid unqualified statements such as:

```text
38 BGCs
```

unless the output defines what `BGCs` means.


### 49.9 Genome-statistics policy

Reader-facing pages may round large genome statistics.

Recommended front-page style:

```text
Genome size: 6.9 Mb
Contigs: 112
N50: 138 kb
Longest contig: 436 kb
```

Exact values remain in technical reports and data tables:

```text
Genome size: 6,867,086 bp
N50: 138,477 bp
Longest contig: 435,651 bp
```

If both are shown:

```text
6.9 Mb genome (exact: 6,867,086 bp)
```


### 49.10 Priority-lead content policy

Priority leads should include one or more of the following rather than only BGC numbers and generic labels:

- simplified node label;
- full node identifier in the technical table;
- compound class or scaffold class;
- strongest key genes/domains;
- architecture clue;
- resistance/self-protection marker if relevant;
- LC-MS / UV / assay action.

Recommended reader-facing lead template (placeholders, not source evidence):

```text
[strain] / [full node-or-contig] / [region] / [BGC alias]
Capacity hypothesis: [source-supported class/family; preserve uncertainty]
Support: [bound genes/domains/comparison evidence and provenance]
Unresolved: [identity, source, interpretation or linkage holds]
```

The previous alias-only kendomycin example was not a complete source binding; do not reuse it as evidence for a specific locus.

The lead table should prioritize **why the conclusion was drawn**, not just the predicted label.


### 49.11 Evidence boundary / claim safety

Every format must include claim-safety language.

Required language:

```text
Genome mining indicates biosynthetic capacity, not confirmed compound production or activity attribution. BGC-level claims require orthogonal evidence such as LC-MS/MS, UV/DAD, isotope pattern, fractionation, genetics, purified-compound testing, or NMR.
```

If bioactivity metadata are not supplied:

```text
Bioactivity metadata NOT_SUPPLIED; observation NOT_OBSERVED. No assay target/outcome is inferred; locus/compound linkage NOT_ESTABLISHED.
```

If bioactivity is user-confirmed:

```text
MRSA and Candida inhibition are user-confirmed at the extract level. BGC-level attribution remains unproven without fractionation, metabolomics, genetics, or purified-compound evidence.
```


### 49.12 Omission and compilation rules

Default order in compiled reports:
1. Editorial Broadsheet
2. Executive Briefing / Memorandum
3. Color Tabloid
4. Executive / Layperson Report
5. Scientific Report
6. Archive Appendix

Alternative conservative order:
1. Editorial Broadsheet
2. Executive / Layperson Report
3. Scientific Report
4. Executive Briefing / Memorandum
5. Archive Appendix
6. Color Tabloid as optional supplement

Users may request omission:

```text
Omit the Color Tabloid from the compiled report.
```

or:

```text
Generate the Front Page Package separately but do not include it in the main PDF.
```

Sapote should comply without altering scientific report content.


## SECTION 50 — v8.2 Compound-Class Coverage + Claim-Safety Patch

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#section-50--v82-compound-class-coverage--claim-safety-patch).

## BLOCK A — §33.3 general claim-safety principle (promoted, applies workflow-wide)

Add as a standing principle in §33.3, applicable to **every** bioactivity call:

> **Absence of assay is not evidence of inactivity. Do not translate an assay-panel limitation into a negative bioactivity claim.** When a source paper reports only a subset of assays (e.g., cancer cytotoxicity but no antibacterial/antifungal panel), the untested activities are **unknown**, not absent. Carrying a source paper's silence — or a "not active" statement that referred only to the assays it ran — into a Sapote negative claim is a claim-safety error.
>
> Apply class context when routing an untested compound:
> - If the class is frequently active against a screen target (macrolides/macrolactones, glycopeptides, lipopeptides, polyethers vs Gram-positive bacteria; polyenes/azole-NRPS/peptidyl-nucleosides vs *Candida*) and no MIC data exist → **flag as an untested candidate for that activity pending assay**; do not deprioritize as inactive.
> - If the class is characterized as selectively cytotoxic/target-specific in a non-antimicrobial mode (dehydro-DKP/plinabulin-class tubulin binders; indolocarbazole topoisomerase/kinase inhibitors) → route to **cytotoxicity caution**, no MRSA/*Candida* mechanistic-link bonus.
>
> **Worked contrast (reference, both from AJS-XXX):**
> - *Marinolide A/B* (24-/26-membered macrolactones): tested only vs SK-OV-3 and U87 cancer lines; **no MRSA/*Candida* assay reported.** Correct: flag as **candidate anti-MRSA lead pending assay** + cytotoxicity-caution note. Incorrect: "no antibacterial activity" (never tested).
> - *Photopiperazine A–D* (dehydro-DKP): characterized as selectively cytotoxic. Correct: cytotoxicity caution, **no** antibacterial flag, no mechanistic-link bonus.
>
> This principle supersedes any per-compound "not active" language inherited from source papers throughout the workflow.

---

## BLOCK B — Diketopiperazine / Cyclodipeptide Synthase (DKP-CDPS)

### B1 — §8 diagnostic-domain entry

| Domains present | Assignment |
|---|---|
| Cyclodipeptide synthase (rule-based antiSMASH `CDPS` product call; CDPS family, Pfam PF16715 when annotated) | **Cyclodipeptide / diketopiperazine (DKP) class.** tRNA-dependent CDPS condenses two aminoacyl-tRNAs into a cyclo-dipeptide scaffold; the CDPS call is class-definitive for the backbone, independent of cluster KCB (albonoursin-type clusters routinely score 1–2 KCB proteins). Subclass set by DKP detection rank (B2). Amino acid selectivity is set by CDPS P1/P2 pocket residues (AJS-XXX's is an NYH-family CDPS, Trp specificity in P1). ⚠ Cytotoxicity caution for the dehydro-DKP subclass (CDPS + co-located confirmed oxidase) — plinabulin-class dehydro-DKPs are tubulin-targeting; cytotoxicity leads, not antibacterial leads. Route to §37 DKP row, §43 T43-DKP, §33.3 guard. Reference: AJS-XXX ctg1_80 CDPS + ctg1_78 oxidase = photopiperazine locus (Kim et al., *J. Nat. Prod.* 2019, 82:2262–2267; DOI 10.1021/acs.jnatprod.9b00429; PMID 31368305); albonoursin BGC0000851. |

### B2 — DKP detection rank (subclass + boundary grading)

| Grade | Criteria | Call |
|---|---|---|
| **DKP-A** | CDPS + co-located candidate cyclodipeptide oxidase (PF00881/nitroreductase-family within the CDPS region), oxidase identity ideally homology-confirmed (see B4 guard) | Dehydro-DKP subclass (albonoursin/photopiperazine/plinabulin-like). Cytotoxic. ⚠ cytotoxicity caution; §37 dehydro-DKP row. |
| **DKP-B** | CDPS alone; no co-located oxidase | Saturated cyclo-dipeptide (e.g., cyclo(Trp-Pro)-type). Non-cytotoxic prediction; inventory/MEDIUM; §37 saturated row. |
| **DKP-C** | CDPS co-called inside another region (e.g., CDPS + lassopeptide in one area) | DKP signal present, boundary uncertain — do not let the co-call suppress the DKP assignment; flag for boundary audit (CLMR composite-locus check); resolve subclass after boundary clarified. |
| **DKP-D** | PF00881-like/nitroreductase oxidase only, **no CDPS** | **Do not call DKP.** Record only as generic oxidoreductase. |

**Verified application to AJS-XXX:**
- NZ_SKBR01000001.1 ~98.4–119.2 kb → **confirmed DKP-A** (photopiperazine locus). ctg1_80 CDPS (domain bitscore 235.4, E 6.5e-71) + ctg1_78 oxidase. Oxidase identity **confirmed by homology, not inferred from PF00881**: embedded KnownClusterBlast pairings vs albonoursin (BGC0000851) record ctg1_78 ↔ **AlbA** (characterized albonoursin oxidase) at 50% id / 90.6% cov / E 4.17e-55, and ctg1_80 ↔ **AlbC** (albonoursin CDPS) at 48% id / 85% cov / E 1.16e-58. Both B4 guard criteria met. (AlbA = oxidase, AlbC = CDPS.)
- NZ_SKBR01000004.1 ~227.6–260.8 kb → **DKP-B** (bare CDPS ctg4_254, no oxidase) **+ DKP-C** boundary caveat (co-called with `lassopeptide`). Absent a co-located oxidase, subclass = saturated cyclo-dipeptide.

> **General lesson:** when a CDPS region returns even a weak whole-cluster albonoursin KCB hit, the per-gene pairings inside that hit can confirm the oxidase identity directly, satisfying the B4 homology criterion without a separate alignment run.

### B3 — §43 CCTT trigger (T43-DKP)

| Trigger | Marker | Co-location | Cluster-score override? | Routes to / action | Priority & WL effect |
|---|---|---|---|---|---|
| **T43-DKP — Cyclodipeptide / diketopiperazine** | Rule-based antiSMASH `CDPS` call OR CDPS-family domain (PF16715 when annotated) | None required for the cyclo-dipeptide class call (CDPS single-marker diagnostic). Apply DKP rank (B2) for subclass + boundary. | **Yes** — gene-level CDPS governs even at KCB ≈ 0–2 proteins; apply §34 low-similarity trap. | Assign DKP grade A–D. DKP-A → dehydro-DKP + ⚠ cytotoxicity. DKP-B → saturated. DKP-C → boundary flag. DKP-D → not a DKP call. Route to §37. | Floor MEDIUM if CDPS unambiguous; bounded WL +1. Dehydro-DKP (DKP-A): cytotoxicity flag mandatory; **no** MRSA/*Candida* mechanistic-link bonus. |

### B4 — §43.3 specificity guards (strengthened)

> **PF00881 is not itself diagnostic for cyclodipeptide oxidase.** PF00881 is a broad nitroreductase-family domain in many unrelated contexts. Treat a PF00881/nitroreductase gene as a **candidate cyclodipeptide oxidase only when** (a) co-located within the CDPS region, **and** where possible (b) supported by homology to a characterized albonoursin/photopiperazine/plinabulin-type oxidase or by gene-neighborhood context. PF00881 without a co-located CDPS = **DKP-D — not a DKP call.** Do not upgrade a bare CDPS (DKP-B) to the dehydro-DKP subclass on a PF00881 gene unless co-location and ideally homology are met.
>
> **CDPS specificity:** the rule-based `CDPS` call / PF16715 is specific for tRNA-dependent cyclodipeptide synthases and is sufficient to assign the cyclo-dipeptide *class*; it is **not** sufficient to assign a specific dipeptide identity (Trp-Leu vs Trp-Pro etc.) without P1/P2 pocket analysis or chemistry.

### B5 — §37 metabolomics rows

| Class | MW range | Ionization | UV/Vis | Extraction | Resistance marker |
|---|---:|---|---|---|---|
| Cyclo-dipeptide / DKP (saturated, DKP-B) | ~190–350 Da | ESI+ [M+H]+ | weak; ~210–230 nm | EtOAc; C18; MeOH/H₂O | — (none characterized) |
| Dehydro-DKP (DKP-A; albonoursin/photopiperazine/plinabulin-like) | ~250–400 Da | ESI+ [M+H]+ (photopiperazine [M+H]+ 296.1393, C₁₇H₁₇N₃O₂, verified) | **diagnostic dual UV ~280 + ~360–375 nm** (photopiperazines 280 + 370 nm) — strong DAD handle + cheapest first-pass screen | EtOAc whole-broth or CH₂Cl₂/MeOH silica → C18 semi-prep; ⚠ **photo-interconversion** — exocyclic-olefin dehydro-DKPs photoisomerize among E/Z forms; amber glass/dim light; expect isomer mixtures appearing as "impure" HPLC peaks | — |

**Verified handle:** photopiperazine, C₁₇H₁₇N₃O₂, [M+H]⁺ 296.1393 (calcd 296.1399), UV 280 + 370 nm, tR 29–32 min, cyclo(Trp-Leu); four photo-interconverting isomers A–D. **Identity-safety:** the four isomers share one formula and one [M+H]⁺; mass cannot distinguish E/Z, and they photo-interconvert during isolation — identity requires controlled-light handling + NMR.

### B6 — §34 hallucination-trap entries

| Trap | Check | Required response |
|---|---|---|
| PF00881 oxidase misread as confirmed cyclodipeptide oxidase | Is the PF00881 gene co-located with a CDPS, or a standalone broad-family oxidase? | No co-located CDPS → DKP-D, do not call DKP. Co-located but no homology support → call DKP-A as candidate with explicit "oxidase identity unconfirmed" caveat. |
| Low/zero MIBiG similarity misread as "no DKP" | Near-zero KCB despite an unambiguous CDPS call? | CDPS gene governs; small DKP clusters routinely score near-zero. Assign class from CDPS, not KCB (apply existing §34 "0% MIBiG similarity" trap). |

### B7 — §45 resistance / self-protection

> **Cyclo-dipeptide / DKP class:** no robust characterized producer self-resistance marker is established. Do not expect or require a Tier 1/2 self-protection gene; its absence is **not** a missingness flag for DKPs (contrast enediyne/glycopeptide/aminoglycoside). A candidate efflux transporter (MFS/ABC) co-localized with the CDPS is Tier 3 polarity-routing only, not class confirmation.

### B8 — §33.3 wet-lab / mechanistic-link guard

> **DKP routing.** Do **not** award the class-specific mechanistic-link (+2 WL) bonus to CDPS/DKP BGCs on a MRSA/*Candida* basis. Dehydro-DKP (DKP-A) is tubulin-targeting/antiproliferative — apply cytotoxicity-caution, route to mammalian cytotoxicity screening, treat antibacterial/antifungal activity in a DKP-containing fraction as non-specific/co-eluting until fractionation/MS proves otherwise. Saturated cyclo-dipeptides (DKP-B) stay inventory/MEDIUM, no bonus; some are weak signaling/iron-binding molecules → route ecology to §17. (Dehydro-DKP half of the Block A principle.)

### B9 — cross-module routing + reader-facing wording

Routing: §8 (B1) · §43 T43-DKP (B3) · §37 (B5) · §33.3 (B8) · §34 (B6) · §45 (B7). Reader-Facing Front Page Package: include **only** when DKP-A, or when notable ecology/literature exists. CLMR: route when exact strain or ClusterBlast homologs point to photopiperazine/albonoursin/plinabulin literature; also resolves DKP-C boundary cases.

- **Front page (DKP-A or notable ecology/literature only):** "Small BGC, high signal: a CDPS + oxidase pair flags a dehydro-diketopiperazine cytotoxicity handle."
- **Archive/scientific report:** "CDPS + co-located PF00881/nitroreductase-family oxidase supports a dehydro-DKP subclass search handle. This is not a compound identification; DKP identity and E/Z isomer state require LC-MS/MS, UV/DAD, controlled-light handling, and NMR."

---

## BLOCK C — Linear Polyether Ionophore

### C1 — §8 diagnostic-domain entry

| Domains present | Assignment |
|---|---|
| Large modular *cis*-AT T1PKS (≥5 modules, TE) **+ polyether cassette**: an epoxidase/FAD-binding monooxygenase (monCI/lsd-type) **and** ≥1 epoxide hydrolase (monBI/BII/lsd-type) co-located in the BGC | **Linear polyether (carboxyl) ionophore class** (monensin/lasalocid/salinomycin/nigericin/nanchangmycin/laidlomycin/ionomycin–ionostatin). The polyether cassette distinguishes this from a generic large modular PKS: a PKS-built polyene is converted to cyclic (THF/THP) ethers by stereospecific epoxidation then epoxide-hydrolase ring opening/cyclization. Expect a free carboxylic-acid terminus. Broad bioactivity — antibacterial (esp. Gram-positive), antifungal, antiparasitic/coccidiostat, often cytotoxic; complexes Na⁺/K⁺/Ca²⁺. ⚠ **Cation-adduct MS note:** known ionophores often appear as [M+Na]⁺/[M+K]⁺ rather than [M+H]⁺; a strong [M+Na]⁺ with weak [M+H]⁺ is a soft class handle. Route to §42 (LMPKS-PE) and §37 polyether row. Reference: AJS-XXX *ion* cluster (NZ_SKBR01000002.1 region 8; 7 PKS genes; ionostatin KCB 16 hits, lasalocid 11 hits); Kim et al., *ACS Chem. Biol.* 2020, 15:2507–2515; DOI 10.1021/acschembio.0c00526; GenBank MT571494. |

### C2 — §42 LMPKS rescue grade + family mapping

Add to §42.11 rescue-grade table:

| Grade | Definition | Interpretation |
|---|---|---|
| **LMPKS-PE** | ≥5-module *cis*-AT T1PKS (TE) **with** a co-located polyether cassette (epoxidase + ≥1 epoxide hydrolase) | Linear polyether ionophore candidate. WL bonus +2 (non-stacking with other LMPKS bonuses). Flag cation-adduct MS handle and free-acid terminus. |

Add to §42.10 family-mapping table:

| Family / class | BGC signals | Report language |
|---|---|---|
| Linear polyether / carboxyl ionophore (monensin/lasalocid/ionomycin class) | ≥5-module *cis*-AT T1PKS, TE, free-acid terminus, **epoxidase + epoxide hydrolase cassette**, KCB to monensin/lasalocid/salinomycin/nigericin/nanchangmycin/ionostatin | Candidate linear polyether ionophore architecture |

### C3 — §42.3 polyether cassette detection rule (verified against real annotations)

**Detection reality check (verified on the AJS-XXX *ion* region JSON):**
1. This JSON carries **no clean PFAM IDs** for the cassette — only SMCOG and rule-based tokens. Do **not** key detection on assumed PFAM accessions; key on SMCOG/rule-based tokens or run HMMER separately for PFAM resolution.
2. The **epoxidase is detectable** (ctg2_1294 = SMCOG1246 "monooxygenase FAD-binding"); the **epoxide hydrolases (IonBI/BII) are NOT cleanly annotated** here (the only hydrolase-family gene is the PKS-release TE). Their absence in the label set is a detection limitation, not biological absence.

Run for any T1PKS BGC with ≥5 modules:

```text
Polyether cassette scan (BGC coordinates +/- 5 kb), using tokens this JSON actually
contains (SMCOG / rule-based), HMMER as publication-grade fallback:

  1. Epoxidase (primary detectable signal): FAD-binding monooxygenase
     -> SMCOG1246 "monooxygenase FAD-binding" (verified: ctg2_1294 in AJS-XXX ion).
     HMMER fallback for PFAM resolution: FAD-binding monooxygenase families;
     confirm IDs against installed antiSMASH/Pfam version; do NOT assume accessions.

  2. Epoxide hydrolase (often NOT label-detectable): alpha/beta-hydrolase or
     epoxide-hydrolase-family gene distinct from the PKS-release TE. NOT cleanly
     annotated in AJS-XXX ion; treat label-absence as a detection limitation.
     HMMER vs epoxide-hydrolase profiles or homology to monBI/BII / lsd hydrolases
     required to confirm.

  Practical label-level trigger: large (>=5-module) cis-AT T1PKS
     + co-located SMCOG1246 FAD-binding monooxygenase
     + KCB anchor to a polyether ionophore
   -> assign LMPKS-PE; set §37 polyether row.

  The KCB anchor does most of the class-assignment work; the FAD-monooxygenase +
  large PKS is the supporting constellation. Confirm the full cassette by HMMER
  before any publication-grade cassette claim.
```

**Claim-safety:** the class call rests on the KCB anchor + large modular PKS + FAD-monooxygenase epoxidase signal — **not** on a fully label-detectable epoxidase+hydrolase cassette. State the epoxide-hydrolase component as inferred/HMMER-pending unless confirmed. Ring count/size (THF vs THP) and cation selectivity are not predictable from the cassette alone. Use "candidate polyether ionophore architecture," not a named ionophore, unless KCB strongly anchors a specific family.

> **Boundary note (verified):** the antiSMASH region (area 8, 134 kb, labeled `terpene, T1PKS`) fused the 101 kb *ion* cluster with an adjacent terpene/second PKS — a real "region ≠ single pathway" case for the CLMR composite-locus boundary audit.

### C4 — §37 metabolomics row

| Class | MW range | Ionization | UV/Vis | Extraction | Resistance marker |
|---|---:|---|---|---|---|
| Linear polyether / carboxyl ionophore (monensin/lasalocid/ionomycin/ionostatin class) | ~600–950 Da (ionostatin C₄₁H₇₂O₉, 708.5 Da; [M+Na]⁺ 731.5061 verified) | **ESI+ as cation adducts** — [M+Na]⁺/[M+K]⁺ often dominate over [M+H]⁺ (polyether chelates cations); screen Na/K adducts explicitly. Acidic (free-carboxyl) ionophores also give [M−H]⁻. | generally weak; ionostatin λmax 276 nm. A *calcium-salt* UV band (ionomycin ~300 nm as Ca salt) is a class cue when the compound complexes Ca²⁺; ionostatin notably does **not** form a strong Ca salt — a within-class discriminator. | silica VLC (CH₂Cl₂→MeOH) then C18 (MeCN/H₂O); often viscous oils; standard organic extraction works | — (no characterized producer self-resistance gene for the class) |

**Verified handle:** ionostatin, C₄₁H₇₂O₉, [M+Na]⁺ 731.5061 (calcd 731.5074), UV 276 nm, pale yellow oil, free-carboxyl linear polyether (two THF rings, enolized 1,3-diketone); LD50 7.4 µg/mL U87/SKOV3. **Identity-safety:** cation-adduct masses are class-supporting handles, not identifications; confirm free-acid neutral mass + ring count by HRMS + NMR before naming a specific ionophore.

---

## BLOCK D — PKS KR/ER stereochemistry reasoning (optional, gated)

New optional §6/§7 capability for *cis*-AT modular T1PKS BGCs at Architecture Confidence A/B where stereostructure prediction adds value (linear polyketides, polyethers, macrolides).

### D1 — method (add to §7 module-architecture analysis)

Beyond recording KR/DH/ER presence, classify subtype per module:

- **KR subtype** (sets β-hydroxyl + α-methyl config): A-type vs B-type from signature residues (LDD-motif region + characterized Caffrey/Keatinge-Clay positions); A1/A2 and B1/B2 (epimerizing vs not) from further residues; redox-inactive **C-type** → epimerization only, gives (2S)-2-methyl-3-keto product. Anchor against characterized reference KRs: erythromycin, tylosin, amphotericin, oleandomycin, megalomycin, nystatin, avermectin, pikromycin, rapamycin.
- **ER subtype** (sets α-methyl config when present): active-site residue at the ionostatin ER position ~44 — **Val → 2R-2-methyl-acyl; Tyr → 2S-2-methyl-acyl**.
- **AT motif** (sets methyl branching): **HAFH → malonyl-CoA** (no branch); **YASH → methylmalonyl-CoA** (methyl branch).
- **Cryptic DH:** a DH in a module lacking a functional KR may act as an α-methyl-ketone **epimerase** (cf. nanchangmycin/monensin/nigericin), not a dehydratase — flag as ambiguous.

### D2 — output (add to Mode B §7 for qualifying BGCs)

Per-module table: module # · AT motif → extender unit · KR present/subtype → predicted β-OH + α-Me config · DH (functional/cryptic) · ER present/residue → α-Me config · predicted module stereochemistry. Conclude with a bioinformatics-predicted planar+stereo hypothesis, explicitly labeled as prediction.

### D3 — claim-safety (mandatory; add to §30.1 Mode B depth gate)

The ionostatin paper documents this method's failures in the very cluster it characterizes: module 1 AT predicted methylmalonyl (YASH) but NMR showed **malonyl** (no C-30 methyl); module 12 cryptic DH predicted possibly active but NMR showed **inactive**; ~11/15 stereocenters correctly predicted, the rest needed NMR. Required wording:

```text
PKS domain-subtype analysis predicts the extender units and the configuration of
[N] stereocenters for this modular polyketide. These are biosynthetic-logic
predictions, not determined structures: AT substrate calls, cryptic-DH activity,
and individual KR/ER subtype assignments can be incorrect, and absolute
configuration requires NMR/chemical confirmation. Treat the predicted
stereostructure as a hypothesis to guide isolation and dereplication, not as an
assigned structure.
```

Do **not** present a bioinformatically predicted stereostructure as the compound's structure in any reader- or manuscript-facing output without NMR/chemical support.

> **Implementation note:** for programmatic KR/ER subtype calling, use the actual Keatinge-Clay/Caffrey reference alignments rather than prose summaries of the signature residues.

---

## BLOCK E — trigger phrases (add to Option 3 / module trigger list)

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#block-e--trigger-phrases-add-to-option-3--module-trigger-list).

## BLOCK F — version history entry

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#block-f--version-history-entry).

## Validation summary (AJS-XXX, five published families)

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#validation-summary-ajs-xxx-five-published-families).

## SECTION 51 — Fragmented Large-BGC Rescue (FLBR) v1.0

**Apply onto:** Sapote Actinomycete Natural Product Discovery Workflow v8.2
**Patch version:** v8.3 candidate · **Date:** 2026-05-31
**Validated against:** a six-strain reference set spanning Moderate and Very-Poor assembly tiers (one Moderate-assembly positive correctly retained as STRONG; two Very-Poor-assembly negatives correctly auto-demoted to WEAK). Full per-strain detail is published in the companion data paper.

---

#### 0. What this patch does and why

Fragmentation can distribute a large locus across contigs, leaving separately called regions with incomplete evidence. Assembly N50 alone does not establish that any particular locus is shattered or that separate regions belong to one pathway. Preserve candidate linkage and completeness holds before interpreting a combined system.

This failure mode is **not specific to T1PKS**. It applies to every assembly-line megasynthase — modular type I PKS, modular NRPS, PKS-NRPS hybrids, and trans-AT PKS — because they share the genetics that make the rescue possible: repeated KS-AT-ACP or C-A-T modules, inter-subunit **docking / communication (COM) domains**, terminal **thioesterase (TE) release** domains, and total cluster sizes that routinely exceed contig length.

§42 (LMPKS-RW) already implements this concept *for PKS*. §51 promotes the shared logic — the two-tier evidence model and the assembly-quality gate — to a thin parent concept that governs all four megasynthase classes, with §42 LMPKS as the PKS worked instance and a new NRPS/hybrid sibling (§51.5).

**Scope guard.** The STRONG-track markers (docking domains, terminal TE) exist only in assembly-line megasynthases. Other large BGC classes (saccharide, large lanthipeptide, type II PKS) fragment too but lack inter-subunit docking domains, so they cannot use the STRONG track. They are **out of scope for §51** and remain handled by their own sections; a future extension could add a class-appropriate weak-track marker for them, but it is not part of this patch.

---

### 51.0 Module text — Fragmented Large-BGC Rescue (FLBR)

### §51.1 Purpose and placement

FLBR is the parent concept for recovering megasynthase pathways fragmented by short-read assembly. It runs in the Run Controller first-pass scan block (parallel with the KCB sweep), and it **must complete before any T1PKS, NRPS, hybrid, or trans-AT region receives a final priority tier** (see §51.6 sequencing guard). FLBR owns:

- the megasynthase scope definition (§51.2),
- the two-tier evidence model (§51.3),
- the assembly-quality gate with the double-docking carve-out (§51.4),
- the genome-wide fragment census (§51.5),
- the sequencing/priority guard (§51.6).

Class-specific mechanics are delegated: **PKS → §42 (LMPKS-RW)**; **NRPS / PKS-NRPS hybrid → §51.5**; **trans-AT → §42.8**, interpreted under the §51 tier model.

### §51.2 Scope — assembly-line megasynthases only

FLBR applies to a region or fragment set if it carries any of: PKS modular KS (mod_KS / hyb_KS / tra_KS), NRPS modules (Condensation + AMP-binding + PCP), or PKS-NRPS hybrid modules. It does **not** apply to saccharide, lanthipeptide, RiPP, terpene, or type II PKS clusters (no inter-subunit docking domains; STRONG markers undefined).

### §51.3 Two-tier evidence model

Every fragmented-megasynthase call carries one of two tiers. The tiers are kept formally separate because they license different claims and different downstream actions.

| Tier | Evidence | Allowed claim | Action |
|---|---|---|---|
| **STRONG** | Any of: (a) a **double-docking-bracketed internal module** — Ndock…Cdock on a single ORF; (b) a **terminal-TE / release fragment** (TE or TD or Abhydrolase_1 terminating a module string); (c) **≥2 fragments sharing a docking and/or KCB family** consistent with one assembly line — **on a contig in a Good / Moderate / Poor assembly** | "Fragmented large modular [PKS/NRPS/hybrid] assembly line; pieces distributed across contigs" | Architecture Confidence C (split-pathway candidate); **Priority-1 long-read sequencing**; group fragments as a combined pathway hypothesis |
| **WEAK** | Any of: docking/TE/edge megasynthase fragments **in a Very-Poor assembly** (auto-demoted, see §51.4); OR the **high-identity / low-protein-count / contig-edge KCB pattern** (a region matching a known-large BGC at high per-protein identity but on only 1–3 proteins, abutting a contig edge — e.g. a terpene/PKS locus hitting nanchangmycin on 2 proteins at the contig boundary); OR a single module fragment with no docking, no TE, and no shared family | "Possible fragmented megasynthase; assembly or evidence insufficient to confirm a large system vs a small cluster" | Routing/sequencing note only; **no confident large-system claim**; do not inflate priority |

A WEAK call is informative and must be reported — it tells the reader where to look after reassembly — but it does not earn the STRONG-tier Architecture Confidence or sequencing priority.

### §51.4 Assembly-quality gate (with double-docking carve-out)

The same genetic evidence means different things depending on assembly quality, so the assembly tier (§4) gates the STRONG track:

1. **Good / Moderate / Poor assembly:** STRONG markers earn the STRONG tier as defined in §51.3.
2. **Very-Poor assembly (interior BGC % < 20):** **all STRONG-tier calls are auto-demoted to WEAK.** Rationale: in a shattered genome, docking/TE/edge fragments on small contigs cannot be distinguished from small clusters that simply landed on small contigs. The markers are real; their interpretation as *one large interrupted system* is unsafe.
3. **Double-docking carve-out (the one exception):** a **double-docking-bracketed internal module** (Ndock…Cdock on a single ORF) **holds at STRONG even in a Very-Poor assembly**, because a module flanked by docking domains on both ends is *intrinsically* an internal subunit of a multi-protein assembly line — there is no benign small-cluster reading of it. Such a call carries a **mandatory caveat**: "assembly Very-Poor; physical linkage to partner subunits unconfirmed; long-read required." Terminal-TE-only and shared-family-only evidence do **not** qualify for the carve-out.

Record the gate outcome explicitly: `FLBR tier: STRONG / WEAK / STRONG (Very-Poor carve-out)` with the assembly tier and the deciding marker.

### §51.5 NRPS / PKS-NRPS hybrid instance

This is the sibling to §42 (LMPKS) for non-PKS megasynthases. Run the same genome-wide census and tier logic, using NRPS/hybrid markers:

- **Module markers:** Condensation (C), Adenylation (A / AMP-binding), Thiolation (PCP / PP-binding), Epimerization (E), heterocyclization (Cy).
- **Inter-subunit markers (STRONG track):** NRPS **COM domains** (NRPS-COM_Nterm / NRPS-COM_Cterm) and PKS-type docking domains on hybrid ORFs — the NRPS equivalent of PKS docking domains.
- **Release markers (STRONG track):** terminal **TE / TD (thioester reductase) / Cyclization-release** domains.
- **Hybrid handling:** a PKS-NRPS hybrid fragment set is grouped as one candidate even when individual fragments are labeled separately (PKS on one contig, NRPS on another); flag explicitly that a hybrid can masquerade as two unrelated low-score clusters.
- **KCB family anchoring:** group fragments whose KCB anchors fall in the same large-NRPS family (glycopeptide, lipopeptide, large siderophore, etc.).

Apply §51.3 tiers and the §51.4 gate identically. Deliverable: fold NRPS/hybrid results into the LMPKS Rescue Report (§42.13) as an "NRPS / hybrid fragment set" section, or emit a parallel `[Strain]_FLBR_NRPS_Rescue_Report_YYYY-MM-DD.pdf` when PKS rescue is null but NRPS rescue fires.

### §51.6 Sequencing / priority guard (Run Controller)

In the Run Controller first-pass block and in §30.2 (Priority Assignment Gate):

- The **genome-wide megasynthase KS/module + docking + TE census (§51.5 / §42.6) must run and be reconciled before any T1PKS, NRPS, hybrid, or trans-AT region is assigned a final priority tier.** A megasynthase region may not be individually deprioritized to LOW/Deprioritized until the FLBR census has had the chance to group it into a fragment set.
- If FLBR assigns a fragment set STRONG, every member region inherits at least the split-pathway Architecture Confidence (C) and the Priority-1 long-read flag, regardless of its individual KCB score.
- Record in the audit log: `FLBR census: [N] megasynthase fragments, [M] STRONG sets, [K] WEAK; long-read priority = [Y/N]`.

### §51.7 Required report language

```text
Fragmented Large-BGC Rescue (FLBR): megasynthase regions were assessed genome-wide for
fragmentation before per-region prioritization. Docking-bracketed internal modules, terminal-TE
release fragments, and shared-family fragment sets were read as positive evidence of a fragmented
large modular assembly line, not as low-value fragments. Tier (STRONG/WEAK) reflects both the
marker strength and the assembly quality; in Very-Poor assemblies, STRONG calls were auto-demoted
to WEAK except double-docking-bracketed internal modules, which are intrinsically internal subunits
of a multi-protein system. STRONG fragment sets are split-pathway candidates requiring long-read
sequencing; no compound identity is claimed.
```

### §51.8 QA gate additions (§30)

- [ ] FLBR census run genome-wide for all megasynthase classes before final priority assignment
- [ ] Every megasynthase fragment assigned a tier (STRONG / WEAK / STRONG Very-Poor carve-out)
- [ ] Assembly-quality gate applied; Very-Poor demotions recorded with the deciding marker
- [ ] Double-docking carve-out applied only to Ndock…Cdock single-ORF modules, with mandatory caveat
- [ ] STRONG fragment sets flagged Priority-1 long-read and grouped as combined-pathway hypotheses
- [ ] No STRONG-tier large-system claim made from WEAK evidence
- [ ] §42 LMPKS results expressed under the §51 tier model; NRPS/hybrid via §51.5

### §51.9 Trigger phrases

```text
Run FLBR on [Strain ID].
Run fragmented megasynthase rescue on [Strain ID].
Run NRPS fragment rescue on [Strain ID].
Run megasynthase fragment census on [Strain ID].
```

### §51.10 Version history

| Version | Date | Notes |
|---|---|---|
| FLBR v1.0 | 2026-05-31 | Initial parent concept. Two-tier (STRONG/WEAK) evidence model; assembly-quality gate with double-docking carve-out; scope = T1PKS + modular NRPS + PKS-NRPS hybrid + trans-AT; §42 LMPKS = PKS instance, §51.5 NRPS/hybrid sibling; Run Controller sequencing guard; QA gate. Validated on a six-strain reference set (one Moderate-assembly positive retained as STRONG; two Very-Poor-assembly negatives auto-demoted to WEAK). |

---

### 51.11 Rationale and Validation — §51 Fragmented Large-BGC Rescue (FLBR)

**Companion to:** Sapote Workflow Patch §51 FLBR v1.0 · **Date:** 2026-05-31

---

#### 1. The problem in one sentence

A locus larger than the assembly N50 may warrant fragmentation review, but N50 alone cannot establish that this locus is split: it summarizes a length distribution, and some contigs exceed it. Inspect the bound locus/contig coordinates and source evidence before making a fragmentation claim.

This is the single most consequential blind spot for antimicrobial discovery from draft genomes, because the highest-value targets — large modular PKS (macrolides, polyethers), large NRPS (glycopeptides, lipopeptides), and PKS-NRPS hybrids — are precisely the clusters too big to assemble intact from short reads. A triage that ranks BGCs by per-region KnownClusterBlast score systematically discards them.

#### 2. Why this became a patch

In the six-strain v8.2 module test, the Moderate-assembly positive strain's PKS content was first reported as "weak / fragmented" — seven or eight unremarkable T1PKS regions. That framing was wrong, and the way it was wrong is the lesson: the regions were scored individually and per-region scoring is exactly what this failure mode defeats. Only a genome-wide domain census — reading docking domains and terminal thioesterases as assembly-line position markers, and contig-edge adjacency as truncation evidence — revealed that the strain carries the fragmented remains of one or more large modular assembly lines.

The capability to do this already existed in §42 (LMPKS-RW) for PKS. Three things were missing:
1. it was **PKS-only**, when the identical failure mode hits NRPS and hybrids;
2. nothing **forced the genome-wide census to run before per-region prioritization**, so fragments could be deprioritized before the accumulation check saw them (this is what produced the wrong first-pass call);
3. there was **no explicit confidence model** to stop a Very-Poor assembly from generating dozens of false "fragmented megasynthase!" calls.

§51 fixes all three: it generalizes the concept to all four megasynthase classes, adds a Run-Controller sequencing guard, and introduces the two-tier evidence model with an assembly-quality gate.

#### 3. The two-tier model and why the tiers stay separate

The core design tension: the same genetic markers (docking domains, terminal TE, contig-edge fragments) appear in two very different situations.

- **Interrupted-large:** a genuine large assembly line broken across otherwise-decent contigs. High value, worth long-read sequencing.
- **Small-and-shattered:** a Very-Poor assembly where everything is on tiny contigs, so small clusters and fragments of large ones are indistinguishable.

A single unified flag would fire identically in both, forcing the reader to re-apply judgment case by case — reintroducing exactly the discernment the module was supposed to encode. Keeping STRONG and WEAK formally separate puts that judgment in the rule, not the reader.

The gate that separates them is **assembly quality**, not contig length. This is deliberate: the workflow already computes an assembly tier (§4), so the gate is reproducible and needs no arbitrary kilobase threshold. Very-Poor → auto-demote STRONG to WEAK.

#### 4. The one carve-out

The auto-demote rule has a single exception: a **double-docking-bracketed internal module** (Ndock…Cdock on one ORF) holds at STRONG even in a Very-Poor assembly. The reasoning is structural, not statistical — a module flanked by docking domains on *both* ends is by construction an internal subunit of a multi-protein assembly line; there is no reading of it as a standalone small cluster. It is the one marker strong enough to survive a bad assembly, and it carries a mandatory "linkage unconfirmed" caveat so it is never overstated. Terminal-TE-only or shared-family-only evidence does not qualify, because those *can* have benign small-cluster readings.

#### 5. What FLBR does not claim

FLBR never claims a compound. Its output is a **sequencing and prioritization decision**: "this strain harbors large modular megasynthase capacity, fragmented by the assembly; here are the contigs likely to join; long-read sequencing is Priority 1." Compound-class language stays at the family level the KCB anchors support, and all the standard claim-safety rules continue to apply.

#### 6. Scope boundary

FLBR's STRONG markers (docking, TE) exist only in assembly-line megasynthases, so the scope is T1PKS + modular NRPS + PKS-NRPS hybrid + trans-AT. Other large clusters that also fragment (saccharide, large lanthipeptide, type II PKS) lack inter-subunit docking domains and cannot use the STRONG track; they are out of scope for this patch. A future extension could give them a class-appropriate weak-track marker, but conflating them now would dilute the strong call.

---

### 51.12 Validation Appendix — FLBR design rationale

**Companion to:** §51 FLBR v1.0 · **Date:** 2026-05-31

The two-tier design was validated on a six-strain reference set with two contrasting assembly conditions. Full per-strain data are published in the companion data paper; the logic is summarized here.

---

#### A. Moderate assembly → STRONG (retained)

A strain with a Moderate-tier assembly (56% interior, 39 regions) carried 34 PKS_KS domains across 15 genes on 10 contigs, with substantial NRPS content alongside. The fragments carry STRONG-track markers on contigs of normal size, so the gate retains them as STRONG.

Representative STRONG markers present: double-docking-bracketed internal module (NODE_94); N-terminal docking + reduced module at contig edge (NODE_104); terminal-TE release fragments (NODE_31, NODE_37); shared-family 6-module reductive run at contig edge (NODE_66). KCB anchors were all large modular polyketides (oligomycin class, quinolidomicin class, lobophorin class, neocarzilin class) too large to assemble from short reads.

**FLBR verdict:** STRONG fragment set; Architecture Confidence C; Priority-1 long-read; "≥1 large modular PKS, fragmented." This is the call a per-region KCB triage misses and FLBR recovers.

#### B. Very-Poor assembly → auto-demoted to WEAK

A strain with a Very-Poor assembly (0% interior, 43 regions, heavily fragmented). The same marker classes appear — but almost entirely on tiny contigs (4–13 kb), where a fragment of a large NRPS is indistinguishable from a small cluster that happens to sit on a small contig.

Representative entries: DOCK + TE + edge on a 9.6 kb contig; DOCK + edge (0-module) on a 4.8 kb contig; TE + edge on a 4.9 kb contig; ~10 further NRPS edge fragments on 3–11 kb contigs. All demoted to WEAK. No double-docking-bracketed internal module present; carve-out does not apply.

#### C. Second Very-Poor assembly → auto-demoted to WEAK

A further Very-Poor strain (0% interior, 49 regions, saccharide-dominated) with NRPS docking/TE fragments on 2.9–5.9 kb contigs. All demoted to WEAK under the Very-Poor gate; no double-docking carve-out triggered.

#### D. The contrast that validates the design

| | Moderate assembly (positive) | Very-Poor assemblies (negatives) |
|---|---|---|
| Assembly tier | Moderate | Very-Poor |
| Same markers present? | Yes (DOCK, TE, edge) | Yes (DOCK, TE, edge) |
| Contig sizes | normal (11–227 kb) | tiny (3–13 kb) |
| FLBR tier | **STRONG** | **WEAK** (auto-demoted) |
| Double-docking carve-out | n/a (already STRONG) | not triggered (none present) |
| Action | Priority-1 long-read, combined-pathway hypothesis | reassembly note only, no confident claim |

The identical genetic evidence yields opposite confidence purely on assembly quality — which is what assembly quality is *for*. The design surfaces the true positive and suppresses the noise with one reproducible rule keyed on the §4 assembly tier.

---

*Sapote Actinomycete Natural Product Discovery Workflow · v8.3 candidate · 2026-05-31*

---

## SECTION 52 — Unclustered Maturation Enzyme Detection (UMED) v1.0

**Apply onto:** Sapote Actinomycete Natural Product Discovery Workflow v8.3 candidate
**Patch version:** v8.4 candidate · **Date:** 2026-05-31
**Method basis:** Xue, Older, Zhong et al., *Nat. Commun.* 2022, 13:1647 (DOI 10.1038/s41467-022-29325-1; PMID 35347143 — both verified) — correlational networking of lanthipeptide precursors to hidden, unclustered proteases across 161,954 bacterial genomes.
**Validated against:** 25 lanthipeptide regions across 9 strains from the reference collection, spanning all four assembly tiers (Good, Moderate, Poor, Very-Poor). Full per-strain data are published in the companion data paper; the aggregate result and diagnostic outcomes are summarized below.

---

## §52.1 Purpose and placement

> **Current implementation boundary:** this retained v8.4 candidate design is not a complete description of the native `source_scans.scan_umed` output. The current helper gates on tokenized family-enriched products and couples annotation-pattern hits within a 5 kb expanded interval. Its three verdicts distinguish in-cluster-or-proximal support, a source-derived gap and not-gated state; it does not perform the full genome-wide precursor–protease specificity workflow described below. The scorer transports the designated gap as a flag after score/tier calculation, without a gap bonus. Keep scan/source completeness and scientific pairing holds separately.

Many RiPP biosynthetic gene clusters do not encode the full enzyme set required to mature
their product; a critical maturation enzyme is encoded **elsewhere in the genome**, outside the
antiSMASH-annotated BGC. For lanthipeptides specifically, the leader-peptide-cleaving protease
is frequently unclustered — Xue et al. found ~⅓ of lanthipeptide BGCs genome-wide lack any
co-localized protease, and the figure is higher for class III/IV systems. An antiSMASH
lanthipeptide call is therefore frequently an **incomplete pathway**, not a complete one.

UMED is the parent concept: *when a BGC class is known to require a maturation enzyme that is
often unclustered, check the cluster for that enzyme; if absent, scan the genome for candidate
enzymes of the appropriate family and report them as leads — never as confirmed maturases.*

UMED runs in the Run Controller first-pass scan block, after BGC inventory, in parallel with
the FLBR census (§51) and CGAD (§44). It is the direct RiPP-side analogue of those genome-wide
"the BGC is missing a required component; look outside its coordinates" scans. The first and
only validated instance is the **lanthipeptide-protease detector** (§52.4). The parent is
RiPP-extensible (§52.7).

**UMED is a confirmation/lead-generation tool, not an annotation tool.** It does not assign
function, does not establish precursor–enzyme specificity, and does not replace the
cross-genome correlation + co-expression method of the source paper, which Sapote — operating
on one genome at a time, offline — cannot reproduce.

## §52.2 The single-genome scope boundary (critical)

The source paper's contribution is a **161,954-genome correlation network** that establishes
precursor↔protease *specificity*. Sapote cannot do this. UMED therefore implements only the
complementary, single-genome half: presence/absence of an in-cluster maturation enzyme, and a
genome-wide candidate search when it is absent. The paper's own results are the claim-safety
guardrail:

- The implicated proteases (M16B metallopeptidases) are **widely distributed** in genomes that
  do not even carry the cognate precursor.
- Homologs from different genomic loci show **different efficiencies** (~4% to 100% relative
  yield in their assays).
- Specificity is **strict and non-transferable**: PttP1/PttP2-like and AplP-like proteases each
  failed to process the other's precursors.

Therefore genomic presence of a candidate protease ≠ functional maturase for a given precursor.
UMED output is capped accordingly (§52.5).

## §52.3 Two-axis output model

Mirroring the FLBR STRONG/WEAK and the §34 Lead-Priority/Claim-Confidence separations, every
maturation-gap call carries two independent axes:

| Axis | Values | Meaning |
|---|---|---|
| Maturation status | `IN-CLUSTER` / `GAP` / `GAP — no candidate in assembly` | Whether the BGC can mature autonomously, needs a hidden enzyme, or has none findable here |
| Candidate confidence | `family-matched candidate` / `specificity-unverified` (ceiling) | Strength of any genome-wide candidate; never exceeds "candidate" without wet-lab/correlation evidence Sapote cannot generate |

## §52.4 Lanthipeptide-protease instance

### §52.4.1 Maturation-protease family library (from Xue et al. Supplementary Table 1)

| Family | Pfam / signature | Lanthipeptide classes served | Notes |
|---|---|---|---|
| LanP (subtilisin-like serine protease) | Peptidase_S8 (PF00082) | I, II | Best-characterized; pathway-specific when clustered |
| LanT (papain-like cysteine protease domain of transporter) | Peptidase_C39 (PF03412) | II (exclusively) | Protease domain embedded in the LanT ABC transporter |
| FlaP / AplP (prolyl oligopeptidase) | Peptidase_S9 (PF00326) | III (reported) | Frequently unclustered; Actinobacteria-biased |
| M16B metallopeptidase (heteromeric, HXXEH + R/Y) | Peptidase_M16 (PF00675) / M16_C (PF05193) | III, and class V (this project) | New family established by the source paper; HXXEH Zn-binding motif on the catalytic subunit, R/Y substrate-binding pair on the partner subunit; functions as a heterodimer |

### §52.4.2 Procedure

For every antiSMASH lanthipeptide region (class I–V):

1. **In-cluster scan.** Search CDS within region coordinates for any §52.4.1 family. If found →
   `IN-CLUSTER`; record family and locus. Pathway is maturation-autonomous (subject to the
   normal caveat that presence ≠ proven function).
2. **Gap flag.** If no in-cluster protease → `GAP`; the BGC is maturation-incomplete.
3. **Genome-wide candidate scan.** For a GAP region, scan the entire record (all contigs,
   inside and outside BGC coordinates — same genome-wide scope as §42.3 / §44.1A) for §52.4.1
   families. Report each candidate with family, locus tag, contig, and distance from the BGC if
   on the same contig.
4. **Assembly-quality gate.** If the assembly tier (§4) is Very-Poor AND no genome-wide
   candidate is found → report `GAP — no candidate in assembly`, classified as a missingness
   item (§38.2), NOT as biological absence. A fragmented assembly may simply not contain the
   protease contig.
5. **Claim ceiling.** Any reported candidate is labeled `candidate maturation protease, family
   X, genome-wide, specificity-unverified`. No precursor–protease pairing is asserted.

### §52.4.3 Heteromeric guard (M16B)

The M16B maturase is a **heterodimer** (catalytic HXXEH subunit + R/Y substrate-binding
subunit). A lone M16-family gene is half a maturase. When reporting an M16 candidate, note
whether a plausible partner subunit is adjacent; a solitary subunit is a weaker candidate than
an adjacent pair and must be labeled as such.

## §52.5 Required claim-safety language

```text
UMED reports whether a lanthipeptide BGC encodes its own maturation protease and, if not, lists
genome-wide candidate proteases of the families known to mature lanthipeptides. A listed
candidate is a lead for follow-up, not a confirmed maturase: candidate proteases of these
families are widely distributed, vary in efficiency, and show strict precursor specificity that
cannot be established from single-genome presence. Precursor–protease pairing requires the
cross-genome correlation, co-expression, and in vitro evidence of the source method, which is
outside single-genome scope. A "no candidate in assembly" result in a Poor/Very-Poor assembly
is a missingness flag, not evidence that the producer lacks the enzyme.
```

## §52.6 Integration

- **§38.2 Missingness Register:** new sub-type "Maturation-enzyme missingness — lanthipeptide
  BGC lacks in-cluster protease and no genome-wide candidate recovered (assembly-limited)."
- **§34 Hallucination-Trap:** new trap — "complete-looking RiPP call masking a maturation gap":
  an antiSMASH lanthipeptide product label does not imply a mature product; check UMED status
  before any production-capacity language.
- **§37 Metabolomics Readiness:** a GAP region's predicted mass is the *unprocessed precursor*
  unless a maturation route is credible; note leader-peptide mass uncertainty.
- **§33.3 Wet-Lab:** a GAP lanthipeptide with a strong genome-wide candidate is a coherent
  heterologous-expression / co-expression target (the source paper's own strategy); record as a
  follow-up experiment, no WL bonus for the protease itself.
- **Run Controller:** UMED status recorded for every lanthipeptide BGC before priority assignment.

## §52.7 RiPP-extensibility (parent hooks, not yet validated)

The same "BGC lacks a required, often-unclustered maturation enzyme" pattern is documented for
other RiPP classes and tailoring steps (the paper cites gentamicin/geldanamycin methyltransferases
and prodigiosin oxidative cyclization as non-RiPP precedents). Future UMED instances would add a
family library and the same in-cluster→gap→genome-wide→ceiling logic. No other instance is
validated; do not apply UMED outside lanthipeptide-protease detection until a class-specific
library and validation set exist.

## §52.8 Trigger phrases

```text
Run UMED on [Strain ID].
Run maturation enzyme scan on [Strain ID].
Check lanthipeptide protease for [Strain ID].
Find unclustered protease for [Strain ID] BGC [N].
Run lanthipeptide maturation gap scan on [Strain ID].
```

## §52.9 QA gate (additions to §30)

- [ ] Every lanthipeptide region assigned IN-CLUSTER / GAP / GAP-no-candidate
- [ ] Genome-wide candidate scan run for every GAP region (full-record scope confirmed)
- [ ] Very-Poor + no-candidate reported as missingness, not absence
- [ ] M16 candidates checked for heterodimer partner
- [ ] No candidate described beyond "specificity-unverified" ceiling
- [ ] No precursor–protease pairing asserted
- [ ] UMED status carried into Run Controller priority + Missingness Register

## §52.10 Version history

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#5210-version-history).

## §52.11 Validation Appendix — UMED across 16 project genomes

Historical release, session or layout material: [read the retained section](history/MONOLITH_DESIGN_HISTORY.md#5211-validation-appendix--umed-across-16-project-genomes).

## SECTION 53 — Marker Addenda and Block Registry (v8.x consolidated)

> **[ARCHIVED — v8.x consolidation, superseded.]** Marker vocabulary now formalized in mamey/mamey_markers.py and the active CCTT patterns in mamey/source_scans.py. This section is maintenance history; do not use it as the authoritative marker list.

*The per-class detection blocks for compound classes beyond DKP and linear polyether are documented
in the following sections and in the retired v8.10.2 monolith (not carried forward into this bundle).
Blocks G–L (lasso peptide, TOMM, NN-diazo, tetronate, PTM/HSAF, thioamitide) are cross-referenced
in §57 sub-grade tables and in the CCTT registry (MMK-CCTT-001 through MMK-CCTT-015).
T43-TOMM (MMK-CCTT-015) was restored to the formal registry in v9.3.*

The §53 Blocks B–L and "OP-2" that §57 cites are not shipped in this bundle. They are not the Blocks A–F of §50.

*Sapote-Mamey Bundle v9.4 | §53 2026-06-09*


---

## SECTION 54 — Output Registry (Optional Layouts + Named Bundles) v1.0

### §54.1 Purpose and placement

The **Output Registry** is a user-facing list of optional report layouts and analyses.
It is presented at task completion (folded into CDSW next-step paths) and on explicit request.
It is **not** a mid-run menu — after the Triage First Board the run proceeds directly to the
Default Complete Package, and optional add-ons are offered at delivery.

The registry is strictly additive. Default deliverables (Layers A/B/C) ship as normal
regardless of selections. Items marked `●` are produced by default; requesting them by name
re-emits them without changing detection, scoring, or claim-safety wording.

### §54.2 Named output bundles

**Trigger:** `Give me the [bundle name or code]`, `Run CM-6`, `Run the Bench Packet`,
`Give me the Full Spread`, `What bundle is right for my PI?`

| Bundle | Contents | Default? | When |
|---|---|---|---|
| **CM-1 Snapshot** | A2 + A3 | — | on request |
| **CM-2 Discovery Brief** ● | A2 + A3 + A5 + A15 | ● | every full-analysis run |
| **CM-3 Bench Packet** | A5 + A6 + A16 | — | on request |
| **CM-4 Mode B Dinner** | A4 + A5 + A6 | — | per-BGC deep dive |
| **CM-5 Ecology Set** ● | A7 + A8 + A12 + A13 + A14 | ● conditional | when §17 applies |
| **CM-6 Publication Packet** ● | A5 + A6 + A7 + A8 | ● | every full-analysis run |
| **CM-7 Full Spread** | all A-layouts | — | `Give me the Full Spread` |
| **CM-8 Rolling Batch Update** ● | A9 + A15 | ● conditional | end of batch session |
| **CM-9 Cohort Brief** | B1 + B3 | — | needs ≥2 strains |
| **CM-10 Cross-strain Deep Dive** | B1 + B2 + B3 + B5 | — | needs ≥2 strains |

### §54.3 Single-strain layouts (Group A — always ready)

- **A1** Reading-guide ribbon — evidence-level key
- **A2** At-a-glance stat cards — genome snapshot
- **A3** Key-finding banner — one bold result line
- **A4** Gene-by-gene plate — per-gene table with ★CORE flags
- **A5** Compound-class prediction table — one row per BGC
- **A6** Manuscript-ready statement box — paste-ready claim-safe sentence
- **A7** ● Ecological-hypothesis register — numbered hypothesis cards
- **A8** ● BGC-by-BGC ecological matrix — ecology-centric per-BGC table
- **A9** Deep-dive progress tracker — rolling BGC status for batch runs
- **A10** Strain TTA/bldA summary table
- **A11** Within-strain domain recurrence table
- **A12** ● Ecological evidence matrices (substrate-signal + host-pathogen defense)
- **A13** ● bldA temporal gating table
- **A14** ● TFBS ecological network map
- **A15** Novel cluster discovery spotlight — zero-KCB BGC focus table
- **A16** Ranked isolation priority list — bench-accessible action list
- **A17** Compound-class grammar table — class-first divergence summary
- **A18** Genus-signature context table — taxonomic BGC context

### §54.4 Cross-strain layouts (Group B — needs ≥2 strains)
- **B1** Cohort comparison platter | **B2** Marker-sweep | **B3** Position-in-cohort scorecard
- **B4** Long-read priority ranking | **B5** ● Cross-habitat enrichment + shared/exclusive matrix

### §54.5 Literature layouts (Group C — needs Literature Deep Dive corpus)
C1 Topic-synthesis matrix · C2 Citation index · C3 Claim-to-citation table ·
C4 Evidence-grade matrix · C5 Target/mechanism review · C6 ● Gaps-scoping ledger

### §54.6 Packaging layouts (Group D — always ready)
D1 Domain quick-ref appendix · D2 Document-overview manifest · D3 Version-history table ·
D4 Summary-statistics dashboard · D5 Accountability TOC · D6 Claim-safety rewrite table

### §54.7 Presentation rules
- Present as plain text, **never** the tappable/interactive question widget.
- Tag each option `ready` or `needs: [input]`.
- Surface only options relevant to the run.
- At task completion: proactively name CM-2 and CM-6 as defaults; offer CM-3 as bench alternative.
- After ecological synthesis: offer CM-5.
- After batch session: offer CM-8.
- When user says "send to my PI" / "write this up": offer CM-6 and CM-3.

### §54.8 QA gate additions
- [ ] CM-2 Discovery Brief present in front-of-report section for every full-analysis run.
- [ ] CM-6 Publication Packet present by default (A5+A6 when §17 does not apply).
- [ ] CM-5 Ecology Set present when §17 applies and host metadata supports A12/A13/A14.
- [ ] CM-8 Rolling Batch Update present at session end when Batch Plan is active.
- [ ] Registry presented as plain text, never via tappable widget.
- [ ] No selected layout changes detection, scoring, Architecture Confidence, or claim-safety.

*Full §54 specification including §54.9 first-contact orientation and §54.11 Master Layperson's Guide
is in the retired v8.10.2 monolith (not carried forward into this bundle) §54.*

*Sapote-Mamey Bundle v9.4 | §54 Output Registry restored 2026-06-09*


---

## SECTION 55 — Edge-Triggered Flank & Linkage Scan (EFLS) — section header

> **Current native distinction:** `source_scans.scan_efls` is a capped preliminary shared-label pair nomination over supplied products, MIBiG strings, cassette labels and CCTT labels. It skips two exact Interior labels, counts positive candidates within the admitted prefix and exports at most 500 sorted pairs. This helper does not implement the historical Jaccard/protein-overlap confirmation described here, perform physical joining or change triage scores itself. Preserve full partner identities, requested/admitted/exported denominators and cap/availability states.

EFLS fires automatically for every Edge or Full-contig region before final priority assignment.
Three components: (1) within-contig flank census with 4 kb chaining rule; (2) diagnostic-constellation
reporting rule — every constellation member listed, never compressed to highest-bitscore;
(3) cross-contig linkage scan with Jaccard overlap discriminator (COMPLEMENTARY J<0.25 /
PARTIAL J 0.25–0.55 / REDUNDANT J>0.55).

Architecture Confidence ceiling for any candidate split set: **C**. EFLS raises lead priority;
it does not raise claim confidence or novelty scores.

*Full §55 EFLS specification is in the retired v8.10.2 monolith (not carried forward into this bundle) §55.*

*Sapote-Mamey Bundle v9.4 | §55 header 2026-06-09*


---

## SECTION 56 — Known-Outcome Producer-Genome Benchmarking and Reference Genome Controls

*Restored from v8.10 in Sapote-Mamey Bundle v9.3 (2026-06-09). This section was present in
v8.10.2 and archived in v9.2; it does not change detection, scoring, Architecture Confidence,
marker weighting, class sub-grade rules, or claim-safety ceilings.*

#### SECTION 56 — Known-Outcome Producer-Genome Benchmarking and Reference Genome Controls

## §56.1 Purpose

Sapote must be able to show that its triage, claim-safety, and BGC interpretation rules work on genomes where the real biosynthetic outcome is already known. This module runs Sapote on public producer genomes and asks a small set of validation questions.

The goal is not to prove that Sapote can identify every compound in every genome. The goal is to show that when a known, characterized producer is analyzed, Sapote:

1. inventories the known BGC or region;
2. ranks the known BGC as a plausible wet-lab lead when its class is relevant;
3. assigns a reasonable Architecture Confidence grade;
4. provides a useful chemical handle;
5. uses safe language and does not overclaim production from homology alone;
6. records failure modes when the expected result is missed or under-ranked.

## §56.2 Trigger phrases

Run §56 when the user says any of the following:

```text
Run known-producer benchmark mode
Run Sapote validation panel
Run benchmark panel on these genomes
Run Candida nucleoside benchmark panel
Run peptidyl nucleoside benchmark panel
Run insect-associated genome controls
Use this strain as a positive control
Compare this output to the known product
```

Also run §56 automatically when a provided strain is explicitly labeled as a known producer, for example:

```text
Streptomyces coelicolor A3(2) — actinorhodin/prodigiosin/CDA control
Streptomyces avermitilis — avermectin control
Saccharopolyspora erythraea — erythromycin control
Amycolatopsis orientalis — vancomycin/norvancomycin control
Streptomyces cacaoi — polyoxin control
Streptomyces griseochromogenes — blasticidin S control
Streptomyces chartreusis — tunicamycin control
AJS-XXX — tetrachlorizine / ClusterBlast literature-control example
```

## §56.3 Benchmark tiers

| Tier | Definition | Sapote use |
|---|---|---|
| **Benchmark-A — full positive control** | public genome or BGC sequence + characterized compound + biochemical/mechanistic study + BGC-to-compound evidence | best for validation statistics and manuscript claims |
| **Benchmark-B — producer/BGC control** | genome or BGC sequence + known compound, but limited mechanistic or biochemical depth | useful for recovery/ranking validation, weaker for mechanism claims |
| **Benchmark-C — ecological/project control** | insect-associated or habitat-relevant genome with useful ecology but incomplete chemistry | useful for CCSM/ecology/host-context validation, not a product-recovery control |
| **Benchmark-D — stress/failure control** | toxic, broad-mechanism, fragmented, or ambiguous case | used to test claim-safety, cytotoxicity caution, and failure-mode logging |

## §56.4 Required benchmark output table

Every benchmark run must include this table in the compiled PDF and Excel workbook.

| Field | Required value |
|---|---|
| Benchmark genome | genus/species/strain/accession when available |
| Benchmark role | positive control / Candida nucleoside control / insect-associated control / stress control |
| Benchmark tier | Benchmark-A / Benchmark-B / Benchmark-C / Benchmark-D |
| Known product or family | known product, class, or expected negative |
| Known BGC evidence | MIBiG ID, GenBank locus, paper, or supplied reference |
| Known mechanism / target | mechanism when verified; otherwise `not benchmarked` |
| Sapote rank | rank of known BGC or nearest candidate |
| Sapote class call | class or family assigned by Sapote |
| Class sub-grade | if a class-specific sub-grade module applies, record it here (for example T43-NUC-A, T43-NUC-B, or T43-NUC-C); otherwise `not applicable` |
| Architecture Confidence | A-E |
| Claim Confidence | VERY LOW / LOW / MODERATE / HIGH / CONFIRMED |
| KCB/RiQ result | top hit, cumulative KCB, RiQ if available |
| Diagnostic markers | named marker genes/domains, resistance genes, or constellation |
| Chemical handle | formula/MW/adducts/UV or `no reliable handle` |
| Recovery result | recovered-high / recovered-under-ranked / detected-unsafe-wording / missed / not assessable |
| Failure mode | none / missed BGC / over-specific claim / wrong mechanism / assembly limited / metadata limited |
| Safe benchmark conclusion | one sentence that can be used in manuscript text |

## §56.5 Scoring benchmark success

Use these categories; do not collapse them into a single pass/fail unless a manuscript table needs a simplified summary.

| Result | Definition | Manuscript-safe wording |
|---|---|---|
| **RECOVERED-HIGH** | known BGC/class appears in top 5 or HIGH/EXCEPTIONAL wet-lab tier | Sapote recovered and prioritized the known product-class BGC. |
| **RECOVERED-MODERATE** | known BGC/class detected but ranked below top 5 for defensible reasons | Sapote detected the known class but did not prioritize it above stronger discovery leads. |
| **RECOVERED-LOW** | detected but low-ranked because known class does not match project bioactivity, novelty, or feasibility | Sapote detected the known class but appropriately deprioritized it for this project objective. |
| **DETECTED-UNSAFE** | BGC detected, but initial wording would overclaim product identity or mechanism | Sapote detected the signal; claim language required correction. |
| **MISSED** | known BGC not detected or not assigned to relevant class | This is a benchmark failure requiring audit. |
| **NOT ASSESSABLE** | expected BGC absent from uploaded files, genome incomplete, accession wrong, or required metadata missing | The benchmark could not be evaluated from available inputs. |

## §56.6 Known producer general benchmark panel

Use these as default candidates for broad Sapote validation. Verify exact accessions locally before final publication tables.

| Priority | Producer genome | Known product/class | Why this matters for Sapote |
|---|---|---|---|
| 1 | *Streptomyces coelicolor* A3(2) | actinorhodin, undecylprodigiosin, CDA, methylenomycin | model multi-BGC closed-genome control; corrected-count and overclaim test |
| 2 | *Streptomyces venezuelae* ATCC 10712 | chloramphenicol; other characterized pathways depending annotation | compact known-producer control and manuscript-friendly benchmark |
| 3 | *Streptomyces avermitilis* MA-4680 / NBRC 14893 | avermectin | large modular PKS / LMPKS / FLBR stress test |
| 4 | *Saccharopolyspora erythraea* NRRL 2338 | erythromycin | non-*Streptomyces* macrolide PKS benchmark |
| 5 | *Amycolatopsis orientalis* HCCB10007 / ATCC 43491 | vancomycin | glycopeptide NRPS/saccharide/halogenation/resistance benchmark |
| 6 | *Amycolatopsis orientalis* CPCC200066 | norvancomycin | same-family-not-identical product claim-safety control |
| 7 | *Streptomyces clavuligerus* ATCC 27064 | clavulanic acid, clavam/beta-lactam, cephamycin context | beta-lactam/clavam and complex-genome/plasmid caution control |
| 8 | *Streptomyces filamentosus* / *Streptomyces roseosporus* NRRL 11379 | daptomycin | NRPS lipopeptide and clinically relevant product benchmark |
| 9 | *Streptomyces tendae* Tü901 or *Streptomyces ansochromogenes* | nikkomycin | peptidyl-nucleoside / Candida chitin-synthase relevance |
| 10 | *Amycolatopsis mediterranei* S699 or related verified rifamycin producer | rifamycin | ansamycin benchmark; verify exact genome before publication use |

## §56.7 Candida-relevant nucleoside / peptidyl-nucleoside benchmark panel

This is a dedicated subpanel because nucleoside/peptidyl-nucleoside BGCs are easy to under-rank when antiSMASH labels are generic.

**Sub-grade cross-reference.** When the per-class sub-grade patch is active, record the most specific nucleoside sub-grade in the §56.4 `Class sub-grade` field. Use **T43-NUC-A** for nikkomycin/polyoxin-like Candida-relevant chitin-synthase inhibitor logic; **T43-NUC-B** for antifungal nucleosides where Candida mechanism or chitin-synthase linkage is plausible but not established; and **T43-NUC-C** for broad/cytotoxic, protein-synthesis, glycosylation-stress, antibacterial MraY/translocase-I, or otherwise non-Candida-priority nucleoside controls. If the sub-grade patch is not active, keep the group labels below and record `class sub-grade not applied` rather than inventing one.

### Group A — direct Candida/chitin-synthase relevance

| Producer/BGC target | Compound family | Sapote expectation |
|---|---|---|
| *Streptomyces cacaoi* subsp. *asoensis* | polyoxins | T43-NUC-A/peptidyl-nucleoside trigger should fire; Candida/chitin-synthase relevance should be surfaced; polar-extraction caveat required |
| *Streptomyces ansochromogenes* or *Streptomyces tendae* | nikkomycins / neopolyoxin | T43-NUC-A; strongest positive control for chitin-synthase-inhibitor logic and Candida-safe wording |

### Group B — antifungal nucleosides but not necessarily Candida-first

| Producer/BGC target | Compound family | Sapote expectation |
|---|---|---|
| *Streptomyces rimofaciens* / historical *Streptoverticillium rimofaciens* | mildiomycin | T43-NUC-B unless Candida/chitin-synthase evidence is supplied; antifungal nucleoside signal; do not assume Candida mechanism without evidence |
| *Streptomyces novoguineensis* | amipurimycin | T43-NUC-B; antifungal nucleoside family; useful marker-library expansion control |
| *Streptomyces miharaensis* | miharamycin | T43-NUC-B; companion antifungal nucleoside benchmark; useful for family-level call calibration |

### Group C — broad/cytotoxic nucleoside stress cases

| Producer/BGC target | Compound family | Sapote expectation |
|---|---|---|
| *Streptomyces griseochromogenes* | blasticidin S | T43-NUC-C; antifungal/cytotoxic/protein-synthesis caution; should not be treated as chitin-synthase class |
| *Streptomyces chartreusis* NRRL 3882 | tunicamycin | T43-NUC-C; Candida-relevant cell-wall/glycosylation biology but strong cytotoxicity/stress caveat required |
| *Streptomyces graminearus* | gougerotin | T43-NUC-C; peptidyl nucleoside/protein-synthesis class; antifungal relevance should be qualified |

### Group D — nucleoside antibiotics that are not Candida-priority

| Producer/BGC target | Compound family | Sapote expectation |
|---|---|---|
| *Streptomyces coeruleorubidus* | pacidamycins | T43-NUC-C or non-Candida nucleoside control; MraY/antibacterial translocase-I class; useful nucleoside architecture control but not Candida-priority |
| *Streptomyces* sp. MK730-62F2 | caprazamycins | T43-NUC-C or non-Candida nucleoside control; liponucleoside/MraY control; not a Candida-priority lead by default |

### §56.7.1 Nucleoside claim-safety rules

Sapote must distinguish these mechanisms:

| Class | Class sub-grade cross-reference | Allowed shorthand | Forbidden shortcut |
|---|---|---|---|
| nikkomycin/polyoxin-like | T43-NUC-A | peptidyl nucleoside; fungal chitin-synthase-inhibitor class; Candida-relevant when evidence supports it | all nucleoside antibiotics inhibit Candida chitin synthase |
| blasticidin/gougerotin-like | T43-NUC-C | peptidyl nucleoside/protein-synthesis inhibitor; antifungal/cytotoxic caution | chitin-synthase inhibitor |
| tunicamycin-like | T43-NUC-C | nucleoside antibiotic affecting glycosylation/cell-wall stress biology; cytotoxicity caution | clean antifungal therapeutic lead |
| pacidamycin/caprazamycin-like | T43-NUC-C / non-Candida nucleoside control | antibacterial nucleoside/liponucleoside; MraY/translocase-I class | Candida-priority antifungal lead |
| amipurimycin/miharamycin/mildiomycin-like | T43-NUC-B | antifungal nucleoside family; mechanism and Candida specificity must be verified | confirmed Candida-active mechanism without evidence |

## §56.8 AJS-XXX rule — literature-rich same-strain examples are validation handles, not product-identity shortcuts

AJS-XXX is a core teaching example for Sapote because it shows that a published same-strain chemistry paper can reveal important chemistry not captured cleanly by antiSMASH product labels.

Use AJS-XXX to validate:

1. exact-strain literature search;
2. ClusterBlast/KnownClusterBlast follow-up;
3. BGC-homology vs product-identity claim safety;
4. halogenation/warhead constellation reporting;
5. literature-rich strain handling.

Required safe wording:

```text
A homologous or related BGC can justify literature follow-up and targeted metabolomics, but it does not establish production of the same compound in the query strain unless supported by orthogonal chemical or genetic evidence.
```

## §56.9 Insect-associated bacterial genome control list

This list supports project-context validation. It is not limited to actinomycetes. Label every entry as natural-product-priority, ecological-control, pathogen-control, or non-actinomycete microbiome-control.

### §56.9A Sapote-priority actinomycete / natural-product examples

| Group | Example genomes/lineages to seek | Benchmark use |
|---|---|---|
| Beewolf wasp symbionts | *Streptomyces philanthi* and related *Streptomyces* from beewolf antennae | insect-protective actinomycete control; strong ecology + antimicrobials |
| Attine ant symbionts | *Pseudonocardia* spp. from fungus-growing ants | insect mutualism, antifungal ecology, Pseudonocardiaceae comparison |
| Wasp-associated literature-rich strains | *Streptomyces* sp. AJS-XXX and related solitary-wasp isolates | exact-strain literature and BGC-to-chemistry validation |
| Bee-associated actinomycetes | *Streptomyces*, *Micromonospora*, *Pseudonocardia*, *Saccharopolyspora*, *Amycolatopsis* from bees or nests | closest match to user reference project; useful for CCSM and ecology rules |
| Termite-associated actinomycetes | *Streptomyces*, *Amycolatopsis*, *Actinoplanes*, *Micromonospora* from termite guts/nests | degradation + antimicrobial ecology; useful non-Hymenoptera insect control |

### §56.9B Broader insect-associated genome controls

Use these mostly for ecology, host-associated genome behavior, and non-actinomycete contrast, not as primary BGC/natural-product controls.

| Group | Example taxa | Benchmark use |
|---|---|---|
| Honeybee core gut bacteria | *Snodgrassella alvi*, *Gilliamella apicola*, *Bifidobacterium asteroides*, *Lactobacillus* Firm-4/Firm-5 lineages, *Bombella apis* | non-actinomycete microbiome controls; should not be overinterpreted as actinomycete NP leads |
| Honeybee pathogens | *Paenibacillus larvae*, *Melissococcus plutonius* | pathogen-control genomes; useful for biosafety and ecology comparison |
| Aphid symbionts | *Buchnera aphidicola*, *Hamiltonella defensa*, *Regiella insecticola*, *Serratia symbiotica* | obligate/facultative symbiont genome controls; reduced-genome contrast |
| General insect endosymbionts | *Wolbachia pipientis*, *Spiroplasma* spp., *Arsenophonus* spp. | host-associated genome controls; generally not Sapote natural-product priority |
| Insect pathogens/entomopathogens | *Serratia marcescens*, *Photorhabdus luminescens*, *Xenorhabdus nematophila*, *Bacillus thuringiensis* | secondary-metabolite-rich non-actinomycete contrast; useful for claim-safety and class-diversity controls |

### §56.9C Insect-associated genome curation fields

Add these fields to the benchmark metadata table when insect-associated genomes are used:

| Field | Notes |
|---|---|
| insect host | species if known; otherwise genus/family/order |
| association type | gut, external symbiont, pathogen, defensive mutualist, nest/garden, substrate-associated |
| isolation site | host tissue, nest, brood cell, antennae, fungus garden, gut, cuticle, hive material |
| evidence strength | genome only / genome + bioactivity / genome + chemistry / genome + ecology experiment |
| natural-product relevance | high / moderate / low / non-priority control |
| Sapote role | BGC benchmark / ecology benchmark / negative control / non-actinomycete contrast |

## §56.10 Remedies mapped to the 100-refinement list

This table converts the high-impact refinement list into concrete Sapote actions.

| Refinement area | What Sapote does now | Gap | Remedy introduced by this patch |
|---|---|---|---|
| Known-outcome benchmarking | strong internal examples and project cases | not enough public positive controls | §56 benchmark panel with Benchmark-A..D tiers and recovery/failure table |
| Wet-lab validation | Wet-Lab Matrix and project bioactivity context | BGC-to-compound link may be missing | benchmark table separates genome validation from wet-lab validation; flags next fractionation action |
| Inter-rater reliability | deterministic Architecture Confidence | no kappa test | benchmark appendix reserves Architecture Confidence audit fields |
| WL sensitivity | non-stacking rules and hard constraints | no perturbation test | benchmark appendix logs top-5 stability as validation metric |
| Corrected BGC counts | formula exists | not validated on closed references | §56 general panel includes closed/model genomes for count calibration |
| TFBS/regulation | TFBS module exists | citations/thresholds need grounding | §56 metadata table can flag TFBS evidence as unverified until literature-backed |
| Nucleoside/Candida relevance | T43-NUC exists | all nucleosides risk being conflated | §56.7 separates chitin-synthase, protein-synthesis, glycosylation, and antibacterial nucleosides and records T43-NUC-A/-B/-C when the sub-grade patch is active |
| Insect ecology | ecological synthesis exists | public insect-associated controls not formalized | §56.9 adds insect-associated genome control routing |
| Claim safety | already strong | benchmark failures not formally counted | §56.5 records detected-unsafe and overclaim failure modes |
| Teaching dataset | not yet assembled | no public install/test panel | §56 panel can become public teaching dataset after accessions and expected outputs are verified |

## §56.11 QA gates

Before a benchmark report can be marked complete, confirm:

- [ ] Every benchmark genome has expected-product metadata or is explicitly marked ecological/non-actinomycete control.
- [ ] Expected product metadata were not used to force Sapote rank.
- [ ] Known product/BGC recovery was assessed after normal scoring.
- [ ] Every known-product control has a recovery result: recovered-high, recovered-moderate, recovered-low, detected-unsafe, missed, or not assessable.
- [ ] Every benchmark control has Benchmark-A, Benchmark-B, Benchmark-C, or Benchmark-D recorded.
- [ ] Every applicable nucleoside/peptidyl-nucleoside control has a Class sub-grade recorded as T43-NUC-A, T43-NUC-B, T43-NUC-C, or `class sub-grade not applied`.
- [ ] Every missed or under-ranked known BGC has a failure-mode note.
- [ ] Every Candida-relevant nucleoside call separates chitin-synthase, protein-synthesis, glycosylation, and antibacterial nucleoside mechanisms.
- [ ] Every insect-associated genome is labeled by association type and Sapote role.
- [ ] The report includes a benchmark summary paragraph suitable for manuscript Methods/Results.

## §56.12 Manuscript-ready summary template

```text
We evaluated Sapote against a known-producer benchmark panel spanning model actinomycete genomes, modular PKS systems, NRPS/glycopeptide systems, beta-lactam/clavam systems, and Candida-relevant nucleoside or peptidyl-nucleoside biosynthesis. For each genome, the workflow was run without forcing the known product into the ranking. We then compared the normal Sapote output against the expected biosynthetic outcome, recording whether the known BGC was recovered, how it ranked, whether Architecture Confidence and claim language were appropriate, and whether any failure reflected assembly, annotation, ranking, or claim-calibration limitations. This benchmark separates recovery of biosynthetic capacity from proof of compound production and is used only to validate workflow behavior, not to infer chemistry in unvalidated query strains.
```

## §56.13 Version-history entry

Add to the Version History table:

| Version | Date | Change |
|---|---|---|
| v8.10 | 2026-06-04 | Adds §56 Known-Outcome Producer-Genome Benchmarking and Reference Genome Controls, including a Candida-relevant nucleoside/peptidyl-nucleoside benchmark panel, insect-associated genome control routing, Benchmark-A..D tiers, class sub-grade recording fields, benchmark recovery/failure tables, and remedies mapped to the 100-refinement publication-readiness checklist. Does not change detection, marker weighting, Architecture Confidence, KCB/RiQ, class sub-grade rules, or claim-safety ceilings. |
| v8.10 integration cleanup | 2026-06-04 | Integrates the §56 patch into the top-level header, Quickstart, trigger index, module map, Run Controller trigger recognition, upload checklist, and non-negotiables so the producer-genome benchmark mode is discoverable from the front matter. No detection, scoring, marker weighting, Architecture Confidence, KCB/RiQ, or claim-safety ceiling changes. |
| v8.10 benchmarking polish | 2026-06-04 | Renames benchmark tiers to Benchmark-A..D, adds the §56.4 Class sub-grade field, cross-references T43-NUC-A/-B/-C in the Candida-relevant nucleoside benchmark panel, and clarifies the patch header as validation-only rather than detection/scoring-changing. |

---

## Final implementation note

This patch should be treated as a validation and manuscript-readiness layer. It should not inflate routine strain reports unless the user explicitly asks for benchmark mode or uploads a known-producer/control genome. In normal AS-strain runs, §56 should remain dormant except for reusable lessons already integrated into CCTT, claim safety, and Triage First.

*Sapote-Mamey Bundle v9.4 | §56 Known-Outcome Benchmarking restored 2026-06-09*


---

## SECTION 57 — Per-Class Constellation Sub-Grades + Tier-6 Marker

*Restored from v8.10 in Sapote-Mamey Bundle v9.3 (2026-06-09). This section was present in
v8.10.2 and archived in v9.2; DKP sub-grades (§50 BLOCK B) remained active throughout.
No detection, scoring, Architecture Confidence, or claim-safety ceiling changed.*

<!-- v8.10 (2026-06-04). Per-class constellation sub-grades + Tier 6.
     Installed as §57 because §56 is the Known-Outcome Producer-Genome
     Benchmarking module. No prior marker, trigger, scoring rule,
     Architecture Confidence grade, or claim-safety ceiling changed. -->

### §57.0 Purpose and scope

Two changes:

1. **Tier 6 — Ecology/Mobility/Genomic-context marker** (§57.1): a sixth row added to the §8.X evidence-weight table.
2. **Per-class constellation sub-grades** (§57.2–§57.15): lettered confidence grades for every CCTT-triggered class, following the DKP-A/B/C/D (§50) and LMPKS-A/X (§42) pattern.

Sub-grades do not replace Lead Priority or Claim Confidence. The §34.8 Hallucination-Trap card remains the authoritative two-axis output. Add `Class sub-grade:` as one field on that card immediately after `Curated candidate class`. The field is also the final column of the `CrypticClass_Triggers` and `Hallucination_Trap_Audit` Excel sheets (schema v1.1, §18.1(c) append-only).

### §57.1 Tier 6 addition to §8.X

Add this row to the §8.X evidence-weight tier table after Tier 5:

| Tier | Name | Definition | Allowed claim |
|---|---|---|---|
| **Tier 6** | **Ecology/Mobility/Genomic-context marker** | Gene whose primary value is ecological, host-interaction, genomic-mobility, or assembly-diagnostic rather than biosynthetic-class-defining. Integrase, transposase, recombinase, tRNA-insertion-site marker, plasmid replication/conjugation gene, chitinase/LPMO (ecology), DasR/NagR regulon gene (ecology), HGT candidate marker, contig-topology indicator. | Route to ecology (§17), HGT/CCSM (§41.8), genomic-island flag (§12), or assembly hypothesis (§51/§55). **Never** primary or secondary compound-class evidence. |

A Tier-6 hit is recorded but does not contribute to the §32.4 minimum two-evidence-type requirement.

### §57.2 Phosphonate — PHO-A / PHO-B / PHO-C
**Fires when:** T43-PHO (PepM). **Base marker:** PepM (Tier 1). **Existing handling:** §43 T43-PHO · §37 phosphonate row · §45.3 FomA/FomB Tier 1.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS |
|---|---|---|---|---|
| **PHO-A** | PepM in BGC or ±15 kb **+ ≥2 phosphonate-pathway genes** (phosphonopyruvate decarboxylase-like, C–P lyase, dedicated aminotransferase, phosphonate tailoring, or FomA/FomB §45.3 Tier 1) + specialized-metabolite context confirmed | HIGH | HIGH | 4–5 |
| **PHO-B** | PepM in/near a BGC **+ 1 supporting phosphonate gene**, or PepM + KCB phosphonate-family hit | HIGH | MODERATE | 3 |
| **PHO-C** | PepM present, context insufficient (BGC-linked but no supporting genes, or genome-wide no proximity) | MEDIUM | LOW | 1–2 |

PHO-C cannot be Deprioritized (PepM Tier 1, §43.5 floor). **Trap:** lone primary-metabolic PepM → PHO-C with "primary-metabolic context cannot be excluded."

### §57.3 Enediyne — ENE-A / ENE-B / ENE-C
**Fires when:** T43-ENE (ene_KS). **Base marker:** ene_KS (Tier 1). **Existing handling:** §43 T43-ENE · §37 enediyne row · §45.3 CalC Tier 1 · §53 BLOCK J apo-protein.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | Label |
|---|---|---|---|---|---|
| **ENE-A** | ene_KS **+ ≥2 cassette genes** (cyclase/TE, polyene-processing, epoxide-forming, chromoprotein gene, tailoring) **+ self-protection confirmed** (CalC-type 10-membered; apo-protein 9-membered §53 BLOCK J). Interior or FLBR/EFLS-rescued. | EXCEPTIONAL | HIGH | 5 | ⚠ CYTOTOXICITY CAUTION |
| **ENE-B** | ene_KS **+ ≥1 enediyne-associated gene**, coherent. Self-protection not confirmed. | HIGH | MODERATE | 3–6 | ⚠ CYTOTOXICITY CAUTION + CalC/apo-protein absence flag (§45.3, §36.4) |
| **ENE-C** | ene_KS fragmented/edge-truncated. EFLS complement (Arch C) or FLBR-routed. No confirmed cassette. | MEDIUM | LOW | 2–3 | FRAGMENTED ASSEMBLY |

Self-protection absence flag applies to ENE-A and ENE-B and does not downgrade ENE-B to ENE-C. **Trap:** ene_KS bitscore required (high-confidence enediyne producers typically show E ≤ 1e-200, BS ≥ 1000 for the warhead KS); generic mod_KS/hyb_KS routes to LMPKS/FLBR.

### §57.4 Aminocyclitol / aminoglycoside — AMC-A / AMC-B / AMC-C
**Fires when:** T43-AMC (DOIS). **Base marker:** DOIS (Tier 1–2). **Existing handling:** §43 T43-AMC (streptomycin carve-out) · §37 row · §45.3 DOIS+APH/AAC Tier 1.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS |
|---|---|---|---|---|
| **AMC-A** | DOIS in/adjacent to BGC **+ ≥2 aminocyclitol tailoring genes** (aminotransferase, dehydrogenase/reductase, sugar-activation, glycosyltransferase) **+ concordant APH/AAC/ANT** (§45.3 Tier 1) or strong KCB aminoglycoside hit | HIGH | HIGH | 4–5 |
| **AMC-B** | DOIS + 1 supporting tailoring gene; context plausible but incomplete | HIGH | MODERATE | 3 |
| **AMC-C** | DOIS present, context insufficient; or KCB aminoglycoside but DOIS absent and streptomycin carve-out (§43) does not apply | MEDIUM | LOW | 1–2 |

Streptomycin carve-out: StrB1/StrK present → AMC-B regardless of DOIS absence. **Trap:** standalone DOIS in housekeeping neighborhood is AMC-C.

### §57.5 Lanthipeptide — LAN-A / LAN-B / LAN-C
**Fires when:** T43-LAN (any lanthipeptide-class region; triggers UMED §52 together — see OP-2). **Existing handling:** §8 class entries · §52 UMED.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | UMED |
|---|---|---|---|---|---|
| **LAN-A** | Synthetase (class-appropriate) **+ precursor + maturation route** (in-cluster §52 IN-CLUSTER, or UMED genome-wide candidate family-matched, no Very-Poor limitation). Boundary coherent. | HIGH | HIGH | 4–5 | IN-CLUSTER or GAP-with-candidate |
| **LAN-B** | Synthetase + precursor; **maturation gap**, UMED external candidate (specificity-unverified) | HIGH | MODERATE | 3–6 | GAP — external candidate |
| **LAN-C** | Synthetase but precursor missing (truncated/annotation gap), or precursor + fragmented synthetase; UMED blocked pending reassembly | MEDIUM | LOW | 2 | GAP — no candidate / deferred |

LAN-A does not confirm production (§52 ceiling). **Trap:** an antiSMASH lanthipeptide label is not maturation-complete; check UMED before LAN-A.

### §57.6 Lasso peptide — LASSO-A / LASSO-B / LASSO-C
**Fires when:** T43-LASSO (§53 BLOCK H). **Existing handling:** §53 BLOCK H · §37 lasso row · §52 hook.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS |
|---|---|---|---|---|
| **LASSO-A** | Precursor **+ lasso B (PF00733) + lasso C**, gene order coherent. Optional D (ABC transporter) → antibacterial prior. | HIGH | HIGH | 4–5 |
| **LASSO-B** | B + C present, precursor not confidently identified (small ORF), or precursor + one enzyme + KCB support | HIGH | MODERATE | 3 |
| **LASSO-C** | B/C-like enzymes without credible precursor, or lone precursor-like ORF without maturation | MEDIUM | LOW | 1–2 |

Precursor absence at LASSO-B is an annotation limitation, not a rule-out. **Trap:** PF00733 alone without lasso C + RiPP context does not trigger LASSO grading.

### §57.7 Thiopeptide / TOMM — TOMM-A / TOMM-B
**Fires when:** T43-TOMM (TIGR03604×2 — see OP-2). **Existing handling:** §8 TIGR03604×2 · §37.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | Note |
|---|---|---|---|---|---|
| **TOMM-A** | Precursor **+ YcaO/azole machinery (YcaO-like + partner cyclodehydratase) + class-specific tailoring** (thiopeptide dehydrogenase; TIGR03604×2). | HIGH | HIGH | 4–5 | Cytotoxicity context caution |
| **TOMM-B** | YcaO + azole/cyclodehydratase, partial maturation context; precursor uncertain but TIGR03604×2 strong | HIGH | MODERATE | 3 | Cytotoxicity context caution |

**Trap (§53 BLOCK H):** YcaO alone without partner cyclodehydratase and RiPP context does not trigger TOMM grading.

### §57.8 Halogenase + backbone — HAL-A / HAL-B / HAL-C
**Fires when:** T43-HAL / T43-XHAL / vanadium haloperoxidase. **Existing handling:** §43 T43-HAL (§43.4) · §53 BLOCK B T43-XHAL · §37 isotope-HRMS.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | Handle |
|---|---|---|---|---|---|
| **HAL-A** | Halogenase **+ class-specific backbone identified** (indolocarbazole/indsynth, glycopeptide NRPS, spirotetronate/FkbH, enediyne/ene_KS, peptidyl-nucleoside/NikJ, or novel high-KCB PKS/NRPS class-consistent) + KCB/diagnostic confirm | HIGH | MODERATE–HIGH | 3–5 | Isotope-aware HRMS mandatory: Cl M+2/M+4, Br M+2/M+4 |
| **HAL-B** | Halogenase + broad plausible PKS/NRPS backbone (class unresolved), or ≥2 halogenases in one BGC | MEDIUM–HIGH | LOW–MODERATE | 2–3 | "class-level halogenation handle only" |
| **HAL-C** | Isolated halogenase, no class-specific backbone | MEDIUM | VERY LOW | 1 | Routing note only; no compound-class handle |

Combined firing: record as `T43-IDC / HAL-A` etc.; backbone sub-grade governs priority, HAL adds isotope handle. **Trap:** halogenase confirms capacity, not a specific compound.

### §57.9 Peptidyl-nucleoside — NUC-A / NUC-B / NUC-C
**Fires when:** T43-NUC. **Existing handling:** §43 T43-NUC · §37 polar row (UV 262 nm, SAX) · §45.3 NikT/NikD Tier 1, §45.4 chitin-synthase paralogue Tier 2.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | Labels |
|---|---|---|---|---|---|
| **NUC-A** | NikJ/PolH-like (BS≥300) **+ ≥2 pathway genes** (aminotransferase/amidinotransferase, sugar/nucleobase modification, uridyl transferase) **+ transporter or target-protection** (NikT/NikD §45.3 Tier 1, chitin-synthase paralogue §45.4 Tier 2, or MraY resistance) + KCB antifungal/antibacterial nucleoside family | HIGH–EXCEPTIONAL | HIGH | 5 | POLAR EXTRACTION WARNING · CANDIDA-RELEVANT if chitin-synthase-inhibitor family · MRSA if MraY/translocase-I |
| **NUC-B** | Nucleoside-core + aminotransferase/amidinotransferase context; family unresolved; transporter/resistance or partial KCB | HIGH | MODERATE | 3–6 | POLAR EXTRACTION WARNING |
| **NUC-C** | Resembles broad/cytotoxic sub-class: blasticidin-S (ribosomal), tunicamycin (glycosylation), gougerotin (peptidyl transferase) | MEDIUM–HIGH | MODERATE | 3–6 | ⚠ CYTOTOXICITY CAUTION · no MRSA/Candida selectivity claim without fractionation |

Polar warning (NUC-A/B): "Standard C18 insufficient; use aqueous/polar primary extraction then SAX or HILIC before C18 desalting and HRMS." **Trap:** NUC-A Candida label only for nikkomycin/polyoxin/mildiomycin-like; blasticidin/tunicamycin/gougerotin → NUC-C.

### §57.10 Glycopeptide — GLY-A / GLY-B
**Fires when:** §8 Cglyc-type detection (CCTT NRPS scan). **Existing handling:** §8 Cglyc-type · §37 · §45.3 VanHAX Tier 1.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | Label |
|---|---|---|---|---|---|
| **GLY-A** | Cglyc-type NRPS **+ VanHAX** (≥2 of VanH, VanA/B/D, VanX) within BGC or ±15 kb (§45.3 Tier 1), **HGT guard passed** (§45.4) **+ halogenase/GT/crosslinking tailoring + KCB glycopeptide-family** | EXCEPTIONAL | HIGH | 5 | MRSA-relevant (lipid II inhibitor) |
| **GLY-B** | Glycopeptide-like NRPS + tailoring; VanHAX missing/outside proximity, or KCB without VanHAX | HIGH | MODERATE | 3–6 | — |

VanHAX HGT guard (GLY-A): integrase/transposase within 5 kb without biosynthetic neighbors = HGT island, excluded; different contig = GLY-B. **Trap:** Cglyc-type (HHILLDG) required; enduracididine (TIGR04462/60) and mannopeptimycin (TIGR01720×2) are distinct classes.

### §57.11 Indolocarbazole — IDC-A / IDC-B / IDC-C
**Fires when:** T43-IDC (indsynth BS≥500). **Existing handling:** §43 T43-IDC · §37 indolocarbazole row · §45.5 Tier-3 note.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | Label |
|---|---|---|---|---|---|
| **IDC-A** | indsynth (BS≥500, E≤1e-100 preferred) **+ Trp_halogenase (PF04820) same/adjacent contig**. Halogenated class (rebeccamycin/AT2433-A1/loonamycin). | EXCEPTIONAL | HIGH | 5 | ⚠ CYTOTOXICITY CAUTION · different contig → split-pathway (§42.7/§55) |
| **IDC-B** | indsynth (BS≥500) **+ no Trp_halogenase**. Non-halogenated class (arcyriarubin/staurosporine). | HIGH | HIGH | 4 | ⚠ CYTOTOXICITY CAUTION |
| **IDC-C** | indsynth BS 200–499 with no further confirmation, or antiSMASH "indole" label with partial indsynth support | MEDIUM | MODERATE | 2–3 | §34 "indole masking indolocarbazole" verification |

Neither IDC-A nor IDC-B earns the Candida mechanistic-link WL bonus (§33.3). KCB=0 expected for truncated contigs (§34 "0% MIBiG" trap); gene homology governs.

### §57.12 HSAF / PTM — PTM-A / PTM-B
**Fires when:** T43-PTM (ornithine A-domain + iterative PKS-NRPS). **Existing handling:** §43 T43-PTM · §37 HSAF/PTM row · §33.3 Candida link (+2 WL).

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | Note |
|---|---|---|---|---|---|
| **PTM-A** | Ornithine A-domain (Stachelhaus vs HslO/HslI) **+ iterative PKS-NRPS confirmed** (one KS reused, multiple downstream ACP / high KS:ACP ratio). Optional class-consistent tailoring. | HIGH | HIGH | 4–5 | §33.3 Candida link +2 WL only with explicitly supplied, source-bound Candida assay context; no default assumption. Acid-labile tetramate: no pH<4 extraction. |
| **PTM-B** | Ornithine A-domain confirmed; iterative PKS architecture only partially visible (edge-truncated / module-reuse unconfirmed) | HIGH | MODERATE | 3 | Candida label with "architecture partially confirmed"; acid-labile caveat |

Iterative-PKS detection distinguishes A from B; truncated-but-KS-visible → PTM-B.

### §57.13 N–N bond / diazo — NN-A / NN-B / NN-C
**Fires when:** T43-NN (CreE + CreD, §53 BLOCK C). **Existing handling:** §53 BLOCK C · §53 BLOCK L (current enzymology) · §53 BLOCK G (NmrA biaryl overlap).

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | Note |
|---|---|---|---|---|---|
| **NN-A** | CreE + CreD **+ downstream route enzyme** (CreM, or AlpH+glutamylhydrazine, or Alp1J+Alp1I) **+ N–N-compatible scaffold**. Subtype determinable. | HIGH | HIGH | 4–5 | Diazofluorene subtype (kinamycin/lomaiviticin KCB, or angular T2PKS + NmrA §53 BLOCK G) → ⚠ CYTOTOXICITY CAUTION |
| **NN-B** | CreE + CreD; **downstream route enzyme absent/unidentified**. Subtype unresolved. | HIGH | MODERATE | 3 | "N-N capacity; subtype unresolved" |
| **NN-C** | Legacy lom29-35 cassette only (no CreE/CreD confirmation) | MEDIUM | LOW | 1–2 | "lom29-35 superseded by CreE/CreD/CreM/Alp1J enzymology (§53 BLOCK L); subtype not assignable from cassette; route to HMMER/BLASTp" |

Enzymology-currency rule (§53 BLOCK L): current CreE/CreD are primary markers; cassette-only evidence yields NN-C.

### §57.14 Tetronate / spirotetronate — TET-A / TET-B
**Fires when:** T43-TET (FkbH-like + dedicated ACP on ≥5-module cis-AT T1PKS, §53 BLOCK D). **Existing handling:** §53 BLOCK D · §37 tetronate row · LMPKS §42.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | Note |
|---|---|---|---|---|---|
| **TET-A** | FkbH-like + dedicated ACP **+ Diels-Alderase (TedJ-type) + trans-decalin**. SPIROTETRONATE (chlorothricin/kijanimicin/tetrocarcin A). | HIGH | HIGH | 4–5 | ⚠ CYTOTOXICITY CAUTION if tetrocarcin/abyssomicin-class |
| **TET-B** | FkbH-like + dedicated ACP + ≥5-module PKS; **no Diels-Alderase**. LINEAR TETRONATE (tetronasin/tetronomycin). | HIGH | MODERATE | 3–6 | Route PKS to LMPKS §42 |

Both TET-A/B carry a large modular PKS that receives a parallel LMPKS §42 rescue-grade; both grades are reported.

### §57.15 Thioamitide — THA-A / THA-B
**Fires when:** T43-THA (YcaO + TfuA + precursor, §53 BLOCK H). **Existing handling:** §53 BLOCK H · §37 thioamitide row.

| Grade | Criteria | Lead Priority | Claim Confidence | DSS | Label |
|---|---|---|---|---|---|
| **THA-A** | YcaO + TfuA **+ RiPP precursor confirmed** (± LanD-like flavoprotein for AviCys) | HIGH | HIGH | 4–5 | ⚠ CYTOTOXICITY CAUTION (antitumor); **no MRSA/Candida WL bonus** (§33.3) |
| **THA-B** | YcaO + TfuA; precursor uncertain/not confidently identified | HIGH | MODERATE | 3 | ⚠ CYTOTOXICITY CAUTION |

**Trap (§53 BLOCK H):** YcaO without TfuA does not fire T43-THA; THA-B requires YcaO+TfuA confirmed.

### §57.16 Quick-reference (all sub-grades)

| Class | Codes | Firing condition | Grade-A headline | Lead Priority at A | Claim Confidence at A | Label at A |
|---|---|---|---|---|---|---|
| Phosphonate | PHO-A/B/C | T43-PHO | PepM + ≥2 pathway genes + context | HIGH | HIGH | — |
| Enediyne | ENE-A/B/C | T43-ENE | ene_KS + ≥2 cassette + self-protection | EXCEPTIONAL | HIGH | ⚠ CYTOTOXICITY |
| Aminoglycoside | AMC-A/B/C | T43-AMC | DOIS + ≥2 tailoring + APH/AAC or KCB | HIGH | HIGH | — |
| Lanthipeptide | LAN-A/B/C | T43-LAN | synthetase + precursor + maturation route | HIGH | HIGH | LAN-A ≠ production |
| Lasso | LASSO-A/B/C | T43-LASSO | precursor + B(PF00733) + C | HIGH | HIGH | +antibacterial prior if D |
| Thiopeptide/TOMM | TOMM-A/B | T43-TOMM | precursor + YcaO/azole + tailoring | HIGH | HIGH | Cytotoxicity context |
| Halogenase | HAL-A/B/C | T43-HAL/XHAL/V-perox | halogenase + class backbone | HIGH | MODERATE–HIGH | Isotope handle |
| Peptidyl-nucleoside | NUC-A/B/C | T43-NUC | NikJ-like + ≥2 genes + transporter/protection | HIGH–EXCEPTIONAL | HIGH | POLAR EXTRACTION |
| Glycopeptide | GLY-A/B | §8 Cglyc-type | Cglyc NRPS + VanHAX (HGT guard) + tailoring + KCB | EXCEPTIONAL | HIGH | MRSA-relevant |
| Indolocarbazole | IDC-A/B/C | T43-IDC | indsynth + Trp_halogenase (A) / without (B) | EXCEPTIONAL/HIGH | HIGH | ⚠ CYTOTOXICITY |
| HSAF/PTM | PTM-A/B | T43-PTM | ornithine A + iterative PKS-NRPS | HIGH | HIGH | Candida +2 WL · acid-labile |
| N–N/diazo | NN-A/B/C | T43-NN | CreE+CreD + downstream + scaffold | HIGH | HIGH | Cytotoxic if diazofluorene |
| Tetronate | TET-A/B | T43-TET | FkbH + ACP + Diels-Alderase (A) / without (B) | HIGH | HIGH/MODERATE | Cytotoxicity if tetrocarcin |
| Thioamitide | THA-A/B | T43-THA | YcaO + TfuA + precursor | HIGH | HIGH | ⚠ CYTOTOXICITY · no MRSA/Candida bonus |

Already defined elsewhere: DKP-A/B/C/D (§50), LMPKS-A/X (§42).

### §57.17 §34 two-axis mapping

| Grade letter | Lead Priority | Claim Confidence | DSS |
|---|---|---|---|
| **A** | HIGH or EXCEPTIONAL | HIGH | 4–5 |
| **B** | HIGH | MODERATE | 3–6 |
| **C** | MEDIUM | LOW | 1–3 |
| null / rule-out | LOW or Deprioritized for the class | VERY LOW | 0–1 |

The §34.8 card is authoritative; a one-step deviation is allowed if explicitly stated. Add `Class sub-grade:` to the §34.8 card after `Curated candidate class`.

### §57.18 QA gate additions (to §30)

- [ ] Every T43-triggered BGC has a `Class sub-grade` on the §34.8 card.
- [ ] Every lanthipeptide region has a LAN sub-grade after UMED §52.
- [ ] ENE-A/B carry the CalC/apo-protein absence flag where applicable.
- [ ] NUC-A/B carry the POLAR EXTRACTION WARNING.
- [ ] HAL-A carries an isotope-aware HRMS handle.
- [ ] GLY-A passed the VanHAX HGT guard and proximity rule.
- [ ] LASSO-B states precursor absence is annotation limitation, not rule-out.
- [ ] TOMM not assigned from YcaO alone.
- [ ] IDC-A/B carry CYTOTOXICITY CAUTION; neither earns the Candida WL bonus.
- [ ] NN-C cites current-enzymology limitation.
- [ ] TET grades report both TET sub-grade and the associated LMPKS rescue grade.
- [ ] THA-A/B carry CYTOTOXICITY CAUTION; no MRSA/Candida bonus.
- [ ] Sub-grades assert no compound identity, production, or BGC-level bioactivity attribution.
- [ ] `Class sub-grade` populated in CrypticClass_Triggers (col J) and Hallucination_Trap_Audit (col O), schema v1.1.

### §57.19 Version stamp

```
Section 57 content baseline : v8.10 (2026-06-04)
Installed as §57 (§56 = Known-Outcome Producer-Genome Benchmarking).
Kernel hooks: §43.2 (T43-LAN, T43-TOMM), §52 UMED, §34, §30.
Excel: CrypticClass_Triggers col J + Hallucination_Trap_Audit col O
       = Class sub-grade (Sapote_Excel_Schema_v1.1).
No prior marker, trigger, scoring rule, Architecture Confidence grade,
or claim-safety ceiling changed.
```


*Sapote-Mamey Bundle v9.4 | §57 Sub-grades restored 2026-06-09*

## Historical section anchors

The following entry points lead to retained design history.

<a id="15-deliverable-integration"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#15-deliverable-integration).

<a id="30-pdf-and-qa-integration"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#30-pdf-and-qa-integration).

<a id="33-wet-lab-scoring-integration"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#33-wet-lab-scoring-integration).

<a id="37-metabolomics-integration"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#37-metabolomics-integration).

<a id="401-purpose"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#401-purpose).

<a id="402-required-files"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#402-required-files).

<a id="403-json-schema"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#403-json-schema).

<a id="404-markdown-snapshot-template"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#404-markdown-snapshot-template).

<a id="43-cctt-integration"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#43-cctt-integration).

<a id="471-purpose"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#471-purpose).

<a id="472-rule"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#472-rule).

<a id="473-required-routing"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#473-required-routing).

<a id="474-claim-safety-language"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#474-claim-safety-language).

<a id="475-triggered-completeness-check"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#475-triggered-completeness-check).

<a id="481-purpose"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#481-purpose).

<a id="482-design-status"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#482-design-status).

<a id="491-purpose"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#491-purpose).

<a id="4913-end-of-analysis-user-prompt"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#4913-end-of-analysis-user-prompt).

<a id="4914-v81-completeness-check"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#4914-v81-completeness-check).

<a id="492-default-package"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#492-default-package).

<a id="493-format-a--editorial-broadsheet"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#493-format-a--editorial-broadsheet).

<a id="494-format-b--color-tabloid"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#494-format-b--color-tabloid).

<a id="495-format-c--executive-briefing--memorandum"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#495-format-c--executive-briefing--memorandum).

<a id="496-image-upload-and-visual-content-workflow"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#496-image-upload-and-visual-content-workflow).

<a id="500-integration-status"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#500-integration-status).

<a id="501-patch-source-and-insertion-map"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#501-patch-source-and-insertion-map).

<a id="502-v82-completeness-check"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#502-v82-completeness-check).

<a id="6-step-workflow"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#6-step-workflow).

<a id="9-step-workflow"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#9-step-workflow).

<a id="announcement-format"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#announcement-format).

<a id="batch-session-end-format"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#batch-session-end-format).

<a id="best-for"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#best-for).

<a id="best-for-1"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#best-for-1).

<a id="bgc-analysis-workbook-sheets-v79--20-sheets"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#bgc-analysis-workbook-sheets-v79--20-sheets).

<a id="claim-safety-note"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#claim-safety-note).

<a id="context-anchor--required"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#context-anchor--required).

<a id="context-anchor--required-before-paper-summaries"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#context-anchor--required-before-paper-summaries).

<a id="continue-command-behavior"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#continue-command-behavior).

<a id="core-purpose"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#core-purpose).

<a id="core-purpose-1"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#core-purpose-1).

<a id="escalate-to-verified-literature-deep-dive-if"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#escalate-to-verified-literature-deep-dive-if).

<a id="evidence-type-hierarchy"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#evidence-type-hierarchy).

<a id="extended-verified-literature-deep-dive-note"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#extended-verified-literature-deep-dive-note).

<a id="gap-rate-by-class"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#gap-rate-by-class).

<a id="gaps-analysis--primary-deliverable"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#gaps-analysis--primary-deliverable).

<a id="module-priority-for-limited-runs"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#module-priority-for-limited-runs).

<a id="note-on-fragmented-strains"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#note-on-fragmented-strains).

<a id="option-1--full-project-restart"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#option-1--full-project-restart).

<a id="option-2--run-strain-level-full-analysis"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#option-2--run-strain-level-full-analysis).

<a id="option-3--run-only-a-specific-module"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#option-3--run-only-a-specific-module).

<a id="option-4--use-as-a-technical-appendix"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#option-4--use-as-a-technical-appendix).

<a id="option-5--one-command-full-workflow-with-adaptive-execution"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#option-5--one-command-full-workflow-with-adaptive-execution).

<a id="option-6--smoke-test--development-run"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#option-6--smoke-test--development-run).

<a id="output-workbook"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#output-workbook).

<a id="output-workbook-1"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#output-workbook-1).

<a id="parentderived-document-model"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#parentderived-document-model).

<a id="per-region-result"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#per-region-result).

<a id="priority-ordering-for-batch-assignment"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#priority-ordering-for-batch-assignment).

<a id="quality-standard"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#quality-standard).

<a id="quantitative-extraction-requirements"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#quantitative-extraction-requirements).

<a id="rapid-literature-deep-dive-vs-verified-literature-deep-dive-comparison"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#rapid-literature-deep-dive-vs-verified-literature-deep-dive-comparison).

<a id="relevance-tiers"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#relevance-tiers).

<a id="replacement-rule"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#replacement-rule).

<a id="required-summary-structure"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#required-summary-structure).

<a id="sapote-workflow-patch-v811--v82"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#sapote-workflow-patch-v811--v82).

<a id="session-continuation-format"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#session-continuation-format).

<a id="session-start-commitment-text"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#session-start-commitment-text).

<a id="source-and-metadata-verification-standard"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#source-and-metadata-verification-standard).

<a id="three-diagnostic-outcomes"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#three-diagnostic-outcomes).

<a id="triggers"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#triggers).

<a id="triggers-1"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#triggers-1).

<a id="v80-standalone-completeness-check"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#v80-standalone-completeness-check).

<a id="v803-canonical-bgc-id-audit-field"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#v803-canonical-bgc-id-audit-field).

<a id="version-history-1"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#version-history-1).

<a id="when-to-announce"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#when-to-announce).

<a id="work-unit-types"></a>
[Read the archived section](history/MONOLITH_DESIGN_HISTORY.md#work-unit-types).

[Open the archived sections](history/MONOLITH_DESIGN_HISTORY.md).
