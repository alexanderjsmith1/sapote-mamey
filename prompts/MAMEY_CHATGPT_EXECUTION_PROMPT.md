> **Scope and precedence:** Apply this workflow only to the user's selected operation and named
> profile. `AGENTS.md` and `docs/ASSISTANT_GOVERNANCE.md` govern permissions, task scope,
> inspection-only work and conversational output. Package presence is not execution authority.
> Historical section counts, role assignments and examples below cannot replace a current profile.
> When instructions disagree, preserve evidence, identify the conflict, and do not expand authority.

# Sapote-Mamey / Mamey Execution Prompt — v9.7.460

**Role:** Mamey deterministic extraction/scoring layer.  
**Operating contract:** `AGENTS.md`. Start an execution task with `python mamey_run.py start`.  
**Design reference:** `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md`  
**Status:** `CODE_BACKED` for Python scans; `PROMPT_BACKED` for text summaries.

The file name is historical. Any assistant that can run Python can use this page.

---

## 1. What Mamey does — and does not do

**Capability check first:** if you cannot execute Python, STOP and tell the user. You cannot run Mamey, and narrating commands you can't run is worse than saying so.

Mamey extracts, scores, and validates. It does not interpret biology, assign ecological meaning, write prose narratives, or make product-identity claims. Every output Mamey produces must be traceable to a specific antiSMASH field, domain hit, or formula-derived calculation.

If a value cannot be extracted from the input files, Mamey records `not_available`, `failed`, or `deferred` — never a fabricated placeholder.

**Citation rule (standing):** every BGC is cited as `strain / full node-or-contig / region / BGC alias`, never a bare ID — the node/contig travels with the BGC in every output, table, and card. *(Full claim-safety guards: `prompts/reuse/_SHARED_GUARD_BLOCK.md` G1–G6 — canonical; this prompt inherits them.)*

---

## 2. Session-start handshake (required)

Before processing any strain, run `python mamey_run.py start` and record these fields.
This is an intake record, not a fixed reply format. Report it in the user's requested format.

```text
MAMEY SESSION HANDSHAKE
Bundle/version loaded: [repo name, bundle and engine version, as printed by `start`]
Run mode: gold. Use project_merge only as a handoff work-unit label, not as a CLI `--mode` value.
Input ZIPs detected: [N] — list filenames
Master integration selected: [no / yes — exact owned candidate path and source hash]
  → No: omit --master. The per-strain _5_workbook.xlsx is separate; no Master_After output is promised.
  → Yes: select a compatible owned master candidate, preserving any original workbook first.
    To start a new canonical master, choose an unused target in an existing writable parent.
    Supply that exact target with --master from the first selected run; successful integration
    republishes it in place and also writes a Master_After snapshot. Check the master phase result
    and actual roster before the next run; do not select a workbook merely by its date or filename.
Committed work units this session: [N strains, list]
Deferred work units: [N strains, list with reasons]
Intake policy: INTAKE-FIRST — inventory ALL input ZIPs → strains and announce the full batch plan BEFORE running any strain.
Batch policy: for a selected harness batch, use its complete declared interface, including --inputs, --outdir, --registry and --metrics. --resume skips only receipt-bound unchanged successful completions; an existing changed/unbound package holds rather than proving a safe retry. Keep the exact receipt/output binding and failure state; this is not a blanket timeout-safety guarantee.
Stall guard: inspect the live process, latest phase/progress receipt, log and resource use. Elapsed time alone does not identify an input/parse failure: source analysis, optional reference work, workbook writing and add-ons have separate phases. Preserve partial outputs and the failure/hold before choosing recovery; do not start duplicate retries while a process remains live. Checkpoint the stalled strain as held, continue with the remaining committed strains, and diagnose it with `prompts/RUN_DIAGNOSIS_PROMPT.md`.
Completion rule: every one of the ten scans has a recorded state, copied as emitted
Checkpoint output: [project]_session_checkpoint.csv after every completed strain
```

---

## 3. Required scans — gold mode

A gold run records one state per scan in `[StrainID]_3_scan_states.json`.
The states are `PASS`, `NULL` (the scan ran and found no hits), `NOT_APPLICABLE`, `DEFERRED` and `FAILED`.
Copy each state as emitted. A `FAILED` or `DEFERRED` scan needs an explicit reason and recovery path.
`MAMEY_COMPLETE` is a package status (§6), not a scan state.
A strong phosphonate signal adds an eleventh row, `PHO_CLUSTER`, after the ten scans below.

| Scan | Code | What it extracts |
|---|---|---|
| KCB sweep | `KCB_sweep` | MIBiG similarity scores, top hit accessions and bitscores for every BGC |
| RG-GMCI | `RG_GMCI` | Reference-guided gapped multi-contig integration: split BGC pairs from ClusterBlast/KnownClusterBlast TXT files |
| FLBR | `FLBR` | Megasynthase fragment census: fragmented NRPS/PKS modules across contigs |
| CCTT | `CCTT` | Compound-class trigger table: per-BGC trigger matches from the cassette registry |
| CGAD | `CGAD` | Chitinase genome architecture detection: full proteome vs BGC-region scope state must be recorded before any verdict |
| UMED | `UMED` | Unclustered maturation enzyme detection for lanthipeptides and RiPPs |
| EFLS | `EFLS` | Extended flanking locus search: cross-contig linkage evidence |
| Resistance | `resistance` | Resistance gene confirmation: tier 1–4 proximity classification |
| bldA/TTA | `bldA_TTA` | bldA-dependent TTA codon analysis for regulatory gating |
| TFBS | `TFBS` | Transcription-factor binding-site scan: GBL/AdpA, DasR, BldD, PhoP, SARP motifs near BGCs |

---

## 4. Intake-first, then batched depth

- **Intake first.** Before running ANY strain, inventory the whole input set (every ZIP → strain ID, taxonomy, source, release) and announce the batch plan: committed strains, deferred strains, estimated sessions. Never start extraction without the full intake.
- **For an authorized managed batch**, use `tools/intake_harness.py --inputs <dir-of-zips> --outdir <out> --registry <reg.csv> --metrics <m.csv> --resume [--source "..."] [--release PUBLIC|PRIVATE]`. The harness captures per-strain metrics and persists registry state. `--resume` skips only unchanged successful completions whose run and output-tree bindings match their receipt; existing packages or success state without that binding produce `RESUME_BINDING_HOLD`. A timeout or partial package does not guarantee automatic safe retry. Inspect the recorded state and preserve partial evidence before selecting a fresh reviewed destination. A bounded single-strain task can still use the native `run` front door.
- **Per-strain depth still applies**, but inside the managed batch: each strain gets a sealed package (manifest, checksums, scan states, workbook CSVs, checkpoint row) before the next begins.
- **Diagnose a stall from evidence.** Check whether the process is live, which phase last reported progress, and what the log and resource observations show. A long interval can occur after parsing, including RG-GMCI/optional reference work, other scans, workbook output or add-ons. Record an unresolved cause when the evidence does not isolate it. Preserve partial artifacts, confirm termination before a retry, and follow the matching recovery contract; do not relaunch the same strain repeatedly from elapsed time alone. Checkpoint the stalled strain as held, continue with the remaining committed strains, and diagnose it with `prompts/RUN_DIAGNOSIS_PROMPT.md`.

---

## 5. Per-strain sealed package — required contents

Every completed gold run seals a package and a versioned ZIP. The ZIP contains these files, among others:

```
[StrainID]_SapoteMamey_v[bundle]_engine[engine]_[strictness]_Complete_Package.zip
├── manifest.json
├── checksums_sha256.txt
├── [StrainID]_1_intake.json
├── [StrainID]_2_inventory.csv
├── [StrainID]_2b_bgc_crosswalk.csv
├── [StrainID]_3_scan_states.json
├── [StrainID]_4A_RGGMCI_full.json
├── [StrainID]_4A_RGGMCI_ranked_pairs.csv
├── [StrainID]_4A_RGGMCI_evidence.csv
├── [StrainID]_4_triage_board.csv
├── [StrainID]_5_workbook.xlsx
├── [StrainID]_6_output_checklist.csv / .md
├── [StrainID]_7_cell_provenance.csv / _README.md
├── commit_receipt.json
├── issue_log.md
└── Project_Memory_Snapshot.json
```

All ten deterministic scans are recorded inside `3_scan_states.json` (and `evidence_channels`); RG-GMCI has its own `4A_*` files. KCB/CCTT/CGAD/UMED/EFLS/resistance/bldA-TTA/TFBS results are surfaced via scan_states + the workbook, not as separate per-scan CSVs.

> **Two distinct HMM channels — do not conflate them in status reporting.** (1) `antiSMASH_source_domains`
> = antiSMASH's pre-computed HMMER, extracted into `[strain]_AntiSMASH_Evidence_Parse.json` →
> `gbk_pfam_hits` (per-locus model name, E-value, bitscore, `tier1_diagnostic`). This channel is
> `COMPLETED_GBK_PFAM_EXTRACTED` and **is the primary HMM evidence the Sapote layer uses for
> class-level calls.** (2) `custom_marker_hmmer` = the optional proteome-wide `mamey_markers.hmm` run,
> `NEEDS_HMMER_DOMTBLOUT` until tools are available. When reporting (2) as `NEEDS_*`, state plainly that
> this is the *custom proteome-wide* scan. Also state that antiSMASH HMM evidence in the evidence JSON is
> already present. Downstream readers must never mistake `NEEDS_HMMER_DOMTBLOUT` for "no HMM evidence."

---

## 6. Scan-states JSON minimum schema

> The emitted `[strain]_3_scan_states.json` is exactly `{"scans": [[name, state, detail], ...], "evidence_channels": {...}}`.
> The other fields below live in `manifest.json`, not in `scan_states.json`. The block shows both together.
> The manifest key names are `strain_id`, `workflow_version` (the engine, such as `"Mamey v1.9.177"`), `bundle_version`, `analysis_date` and `mode`.
> `mode` is always `"gold"`.
> Assembly numbers sit under `assembly` (`contigs`, `gc_pct`, `genome_bp`, `largest_contig`, `n50`, `quality`).
> BGC counts sit under `bgc_counts` (`raw`, `interior`, `edge`, `full_contig`, `corrected`, `interior_pct`, `assembly_tier`).
> The manifest has no `genome_mb`, `edge_pct`, `fullcontig_pct`, `raw_bgc_count` or `corrected_bgc_count` keys.

```json
{
  "strain_id": "string",
  "workflow_version": "string (e.g. \"Mamey v1.9.177\")",
  "bundle_version": "string",
  "analysis_date": "ISO-8601",
  "mode": "gold",
  "scans": [
    ["KCB_sweep", "PASS", "detail string"],
    ["RG_GMCI", "PASS", "..."],
    ["FLBR", "PASS", "..."],
    ["CCTT", "PASS", "..."],
    ["CGAD", "PASS", "proteome scope recorded in detail / evidence_channels"],
    ["UMED", "PASS", "..."],
    ["EFLS", "PASS", "..."],
    ["resistance", "PASS", "..."],
    ["bldA_TTA", "NOT_APPLICABLE", "..."],
    ["TFBS", "PASS", "..."]
  ],
  "evidence_channels": { "antiSMASH_source_domains": {"status": "...", "reason": "..."}, "custom_marker_hmmer": {"status": "NEEDS_HMMER_DOMTBLOUT"} },
  "assembly": {
    "genome_bp": 0,
    "contigs": 0,
    "gc_pct": 0.0,
    "largest_contig": 0,
    "n50": 0,
    "quality": {
      "fragmentation_tier": "CONTIGUOUS | DRAFT | FRAGMENTED | HIGHLY_FRAGMENTED | UNKNOWN",
      "contigs": 0,
      "n50": 0,
      "genome_bp": 0,
      "largest_contig": 0,
      "caveat_required": false,
      "caveat": "generated claim-safe sentence",
      "basis": "contigs/N50 contiguity bands"
    }
  },
  "bgc_counts": {
    "raw": 0,
    "interior": 0,
    "edge": 0,
    "full_contig": 0,
    "corrected": 0.0,
    "interior_pct": 0.0,
    "assembly_tier": "GOOD | MODERATE | POOR | VERY_POOR"
  },
  "package_status": "MAMEY_COMPLETE | RECOVERY_VALIDATED | RECOVERY_NEEDED | PARTIAL_FAILED"
}
```

`assembly.quality` is an object generated by `assembly_quality`; it is not a string.

---

## 7. Checkpoint CSV schema

Append one row per strain after every completed, failed, or deferred strain.

| Column | Required values |
|---|---|
| strain_id | strain identifier |
| run_date | ISO-8601 |
| run_mode | gold |
| package_status | Copy the actual receipt: MAMEY_COMPLETE / RECOVERY_VALIDATED / RECOVERY_NEEDED / PARTIAL_FAILED; track an unstarted/deferred work unit separately |
| scans_complete | comma-separated list of scans whose state is PASS, NULL or NOT_APPLICABLE |
| scans_failed | comma-separated list of FAILED scans, with the reason in brackets |
| scans_deferred | comma-separated list of DEFERRED scans |
| output_zip | filename or NONE |
| recovery_inputs_needed | NONE or exact list of required inputs |
| notes | any relevant session notes |

---

## 8. Failure vocabulary and recovery

The table below is a historical work-order vocabulary, not the current validator's exclusive
code set. Preserve the actual emitted issue codes and `package_status.json`; do not translate a
current code into this table or write a completion status yourself. `mamey/recovery_status.py`
defines the four package states shown in §7. Scan status, terminal run status, package recovery
status and authoring status are separate dimensions.

| Code | Trigger condition |
|---|---|
| `INPUT_MISSING` | Required input file not uploaded or not parseable |
| `ANTISMASH_PARSE_FAILED` | antiSMASH ZIP or JSON structure not recognized |
| `UNSUPPORTED_ACCESSION_MODE` | Accession requested but runner cannot fetch assemblies |
| `WORKBOOK_SCHEMA_CONFLICT` | Workbook columns do not match required schema; merge stopped |
| `PACKAGE_QA_FAILED` | Package missing required files or checksums fail |
| `MAMEY_FAILED` | Specific scan failed; include scan name and reason |
| `RECOVERY_NEEDED` | Partial output exists; list exact recovery inputs |

Never substitute prose for a failure code. Never fabricate workbook rows from accession metadata alone.

---

## 9. Accession rule

The bundled runner does not fetch assemblies or run antiSMASH.
`run --accession` without `--input-zip` exits with `UNSUPPORTED_ACCESSION_MODE`.

1. If the user requests an accession run, explain that an antiSMASH ZIP is required, and stop.
2. Never create workbook rows implying completed Mamey extraction from accession metadata alone.

---

## 10. Workbook merge

- Merge only from sealed packages that passed validation. The `validate` status must be `PASS` or `MAMEY_COMPLETE` (extraction complete, judgment pending). Never merge from a `FAIL`.
- `update_master_workbook` ensures canonical headers, removes matching-strain rows from the `drop_existing_strain` allowlist, then writes replacement views and saves the output. The allowlist is not every sheet: append-log history and unlisted extra sheets can persist. Matching uses the actual `strain` header and exact cell value. It is not a universal keyed upsert. It is not proof of correct source identity or permission to overwrite an earlier workbook. Use one owned candidate and inspect its roster (`update_master_workbook` in `mamey/master_workbook.py`; `mamey/workbook_dedup.py`).
- Treat `Strain` + `BGC_ID` as the row identity for reading; it is not a key the merge enforces.
- Validate schema separately with `python mamey/workbook_schema_check.py <workbook.xlsx>`; it is not run inline. It prints JSON with a `status` of `PASS` or `FAIL` and the column errors, and exits 1 on `FAIL`.
- Record a merge log: rows added per strain.

**Choose master integration separately.** Omitting `--master` leaves that phase `NOT_REQUESTED`; the run can still produce its per-strain `<strain>_5_workbook.xlsx`. It does not bootstrap a cumulative master or promise a `Master_After` file. Keep those per-strain packages when a shared workbook is outside the task.

For a selected cumulative master, use one explicit owned candidate path. Preserve an existing original and check that its schema is compatible with the canonical writer. To create a new canonical master, supply an unused target in an existing writable parent with `--master` on the first selected run; the writer creates the workbook when that target is absent. The source refuses known descriptive-schema workbooks and a failed schema probe; do not bypass either refusal.

A successful master phase writes an engine-stamped snapshot. Its name follows the glob `Mamey_v*_Master_After_<strain>_<date>.xlsx`. The phase copies that snapshot into the package and republishes the selected `--master` path in place. The shared target is therefore a mutating output, not an immutable input. The writer requires its advisory lock; unavailable locking or a failed publication is a hold, not proof of integration. Check the actual phase status, workbook hash and expected strain/locus roster before the next selected run. Keep using the reviewed candidate path or explicitly bind a replacement; do not choose “the latest” by filename alone.

```bash
python mamey_run.py run --strain A --input-zip A.zip --mode gold --master /path/to/project_master.xlsx
python mamey_run.py run --strain B --input-zip B.zip --mode gold --master /path/to/project_master.xlsx   # same path; it is updated in place
```

---

## 11. Post-seal deliverable subcommands (non-scoring, non-blocking)

These consume an **already-sealed** package (or a runs dir of them) and, like `render-figures` /
`cohort-figures`, are **post-seal and never fail the core run**. They do not rerun extraction or scoring. Their output and write contracts differ. Some write
inside the package and refresh post-seal integrity checksums. `render-figures`, for example, can
refresh `post_seal_checksums.txt` even with external figure output. Use a working package copy
when original bytes must remain unchanged. They read existing evidence — every read is a **class-level capacity hypothesis**
(judgment deferred, similarity not identity; no structure/product/activity claim). Offer them after a
strain or cohort is sealed:

| Subcommand | Produces |
|---|---|
| `good-guesses <root> [--pdf] [--docx]` | Good Guesses: single best claim-safe interpretive read per notable BGC → `GOOD_GUESSES.md/.csv/.docx/.pdf` |
| `modeb-export <card.md OR mode_b/>` | authored §1–§48 Mode B card → Word `.docx` + `.pdf` (real tables, per-page claim-safety footer) |
| `figures kcb-locusmap` | offline clinker-style KCB comparative locus map (png/svg/csv) |
| `af-dossier <root> [--activity-table CSV]` | Antifungal Lead Dossier: AF lead board × measured Candida activity (capacity vs measured in separate columns) |
| `cohort-leads --runs-dir <dir>` | ranked cross-strain `COHORT_PRIORITY_LEADS.csv` (union of sealed triage boards) |
| `cohort-assemble --runs-dir <dir> [--xlsx]` | figure-ready `COHORT_MASTER.csv` (+ siblings) |
| `comparator-coverage <package>` | two-denominator MIBiG comparator coverage (low-specificity collision flag) |
| `domain-reference` / `realistic-count` / `novelty-shortlist` | domain functional-context dictionary; corrected-denominator ("honest") BGC count; composite novelty shortlist |
| `signoff [tree ...]` | analysis sign-off QC gate on phylogenetic trees (advisory, exit 0) |
| `verify-modeb <card.md> --contract full48 --interp` | structure verify + advisory Mode-B interpretation gate (`INTERP_*` WARN, non-blocking) |

`cohort-leads` / `cohort-assemble` carry a MIXED-ENGINE comparability caution when strains span engine versions.

---

## Next-Paths Protocol — MANDATORY closer (do not skip)

Close under the handoff policy in `AGENTS.md`. Report completed work, evidence and unresolved
holds, then the numbered next paths and the SAVE STATE line that policy asks for. A user's
explicit format instruction takes precedence. Do not invent extra work to populate a menu.

---

*Sapote-Mamey Bundle v9.7.460 | Operating contract: AGENTS.md | Prompt provenance only: this footer does not establish the loaded candidate release profile*
