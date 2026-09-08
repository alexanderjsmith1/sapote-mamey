# Sapote-Mamey All-in-One Bundle Monolith

**Monolith content version:** vetted against bundle v9.7.6 (last full read-through 2026-06-13); **spot-vetted against bundle v9.7.378** (2026-08-25: doctrine scan clean — no retired assembly tiers, no per-BGC BSL-2 flagging, no active AS_SCRUB, no PRIVATE(AS-) identifier doctrine, no PUBLIC/PRIVATE figure divider; supersedes the 2026-07-16 v9.7.317 spot-vet, re-cleared at the drift threshold. One standing operational reference — `sapote_pdf_styles.py`, an upload-at-session-time PDF style module — is intentionally not a bundled script and was not certifiable by the dangling-ref scan; it is a deliberate session-time artifact, not a broken internal ref). **Established:** May 25, 2026.
**Note:** the monolith is the parent design controller; its content is reviewed at major checkpoints, not bumped every patch. It is intentionally tracked separately from the engine/bundle version (for the authoritative live versions see CITATION.cff / pyproject.toml / mamey/__init__.py — this document does not restate them, because a restated version number rots silently). Sections describing concrete code behavior (e.g. §-1.17 merge contract) are kept current with the code even between full read-throughs.
**Project:** Multi-habitat actinomycete BGC discovery and manuscript support  
**Scope:** Any actinomycete or bacterial collection with antiSMASH output. Reference project covers isolates from four [Habitat] categories; the workflow is not restricted to these categories.  
**Core protocols:** Mamey deterministic extraction/scoring kernel + Sapote interpretive judgment layer + Workbook Contract + Batch Controller + Resume/Checkpoint Protocol + CDSW + Triage First + LC-MS Chemical Handle Module + Reader-Facing Front Page and Briefing Package + CCTT + CGAD + Resistance + bldA/TTA + RG-GMCI + FLBR + UMED + EFLS + DKP-CDPS + Linear Polyether Ionophore Detection + PKS Stereochemistry Reasoning + Output Registry (§54) + EFLS Constellation Reporting (§55) + Known-Outcome Benchmarking (§56) + Per-Class Constellation Sub-Grades (§57)  
**Primary use:** Paste this prompt at the start of a new AI session, then upload the required master files or strain-specific antiSMASH ZIPs.



---


# SECTION -2 — v9.2 Bundle Hardening Patch / Release Bridge

## -2.0 Purpose

v9.2 is not a science-module expansion. It is a **bundle-hardening patch**. Its purpose is to make the monolith usable as the parent controller for the repository bundle without letting prose silently outrun the executable kernel. v9.1 established the Mamey-first / Sapote-second architecture; v9.2 adds release gates, derived-prompt generation rules, test expectations, and code/document synchronization rules.

**Central rule:** the monolith may define the desired contract, but the bundle release is valid only when documentation, prompts, workbook schema, executable behavior, and tests agree.

## -2.1 Active-controller rule

The bundle must have exactly one active parent controller:

```text
Active parent controller: docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md
Legacy monoliths: archived / historical only
Derived prompts: regenerated from the active parent controller
Executable code: Mamey kernel; not overwritten by prose without tests
```

Do not keep v8.1.1, v8.4 candidate, v9.0, v9.1, and v9.2 as parallel active instructions. Older monoliths may remain in `docs/legacy/` with a clear `HISTORICAL_DO_NOT_USE_AS_CONTROLLER` banner.

## -2.2 Requirement status labels

Every bundle requirement should be classed into one of four implementation states:

| Status | Meaning | Allowed in release? | Required action |
|---|---|---|---|
| `CODE_BACKED` | implemented in Python/CLI and covered by a test or manual validation | yes | keep docs and tests synchronized |
| `SCHEMA_BACKED` | represented in workbook templates, CSV schemas, JSON contracts, or validation scripts | yes | validate column names and allowed values |
| `PROMPT_BACKED` | handled by ChatGPT/Claude instructions but not executable | yes, if labeled | do not present as deterministic output |
| `ASPIRATIONAL` | desired future behavior not yet implemented | no, unless in roadmap | move to roadmap or create issue |

A release-facing guide must not describe `ASPIRATIONAL` behavior as available functionality. If a module is `PROMPT_BACKED`, its outputs must carry interpretation/provenance labels rather than deterministic scan labels.

## -2.3 Repo synchronization gate

Before the bundle is released, run this document/code synchronization checklist:

```text
REPO SYNC GATE
[ ] One active parent monolith exists.
[ ] Old monoliths moved to docs/legacy/ or marked historical.
[ ] Derived prompts regenerated from the active monolith.
[ ] README quick start matches current CLI behavior.
[ ] WORKBOOK_SCHEMA.md matches workbook templates and produced workbooks.
[ ] mamey_run.py help text matches documented modes and arguments.
[ ] Accession support is either implemented/tested or documented as unsupported.
[ ] Failure codes in docs match failure codes emitted by packages.
[ ] scan_states JSON schema is documented and validated.
[ ] At least one smoke test and one gold test were run or explicitly deferred.
[ ] Release manifest lists known limitations honestly.
```

## -2.4 Execution profiles

Different assistants/environments have different capabilities. The parent monolith must route work by profile instead of pretending all environments can do everything.

| Profile | Typical environment | Can do | Cannot assume | Required wording |
|---|---|---|---|---|
| `CHATGPT_SANDBOX` | ChatGPT with uploaded files | unzip, parse, run bundled Python, create workbooks/ZIPs | internet, full antiSMASH install, NCBI accession fetch | “I can run supplied antiSMASH ZIPs; accessions require an accession-enabled runner or supplied ZIP.” |
| `LOCAL_REPO` | user/Claude/local shell with repo | full CLI, tests, file edits, git | external services unless installed/configured | “Run tests before release.” |
| `CLAUDE_SAPOTE_TIER` | interpretation/merge reviewer | reason over Mamey outputs, produce Sapote judgment, merge by schema | deterministic extraction from raw antiSMASH unless given package outputs | “Mamey outputs are the evidence source; Sapote does not invent extraction fields.” |
| `PUBLIC_ACCESSION_MODE` | environment with internet + assembly/antiSMASH pipeline | fetch genome, run antiSMASH, then Mamey | not available in basic sandbox | “Only valid when accession fetch and antiSMASH execution are actually available.” |

## -2.5 Accession support boundary

The task brief may request `--accession`, but the executable runner must be checked before promising accession runs.

Required decision path:

1. Inspect `mamey_run.py --help` or equivalent CLI docs.
2. If `--accession` exists and is tested, run accession mode.
3. If not, require antiSMASH ZIP input or a local accession→antiSMASH preprocessing step.
4. If the user later supplies the ZIP, replace the failed placeholder with a complete package and rebuild the handoff.

Never create workbook rows that imply completed Mamey extraction from accession metadata alone.

## -2.6 Stable project-state file

Every multi-strain or multi-batch project should include a lightweight state file:

```json
{
  "project_id": "SID-XXX_or_project_name",
  "active_monolith": "SAPOTE_MAMEY_BUNDLE_MONOLITH",
  "bundle_version": "sapote-mamey-repo-vX.Y.Z",
  "master_workbook": "filename.xlsx",
  "last_handoff_zip": "filename.zip",
  "completed_strains": [],
  "deferred_strains": [],
  "failed_strains": [],
  "next_action": "one sentence",
  "schema_version": "workbook_schema_version",
  "timestamp": "ISO-8601"
}
```

This does not replace the per-strain checkpoint CSV. It gives the next session a single place to find what to continue.

## -2.7 Idempotent rerun and rebuild policy

When rebuilding a handoff ZIP:

- Preserve completed per-strain packages unless the input, code version, or schema changed.
- Rebuild the final ZIP after any changed artifact.
- Report a delta: `added`, `replaced`, `unchanged`, `removed`.
- Never silently overwrite a complete package with a failed placeholder.
- If two versions exist, keep the newer one only when its manifest is complete and checksums validate.

## -2.8 Derived prompt set required for the bundle

The bundle should ship one parent monolith plus these derived prompts:

| Derived file | Purpose | Must include | Must omit |
|---|---|---|---|
| `prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md` | deterministic ChatGPT/Mamey run instructions | ten scans, depth-first, checkpoint, failure codes, package manifest | long Sapote literature prose |
| `prompts/CLAUDE_SYSTEM_PROMPT.md` | Sapote-tier interpretation/merge instructions | evidence boundaries, candidate cards, workbook merge contract | raw extraction instructions that duplicate Mamey |
| `prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md` | user-facing batch brief template | inputs, committed/deferred count, exact output schemas, validation checklist | vague “run everything” language |
| `docs/HOW_TO_USE.md` | human quick-start guide | run profiles, examples, common failures | internal prompt history |
| `docs/RELEASE_CHECKLIST_v9.md` | release manager checklist | sync gate, tests, archive old monoliths | scientific interpretation narrative |

## -2.9 Minimal test matrix before release

A candidate bundle should not be called final until the following have been exercised:

| Test | Input | Expected outcome |
|---|---|---|
| `smoke_parse_small_zip` | small antiSMASH ZIP | assembly stats, raw BGC count, manifest |
| `gold_complete_one_zip` | representative antiSMASH ZIP | ten scan statuses, sealed package, checksums |
| `workbook_merge_append` | existing workbook + one complete package | new rows appended, no old rows deleted |
| `failed_accession_boundary` | accession request without accession-enabled runner | `UNSUPPORTED_ACCESSION_MODE`, no fabricated rows |
| `continue_checkpoint` | prior checkpoint with deferred item | next item processed, completed items not rerun |
| `schema_mismatch_stop` | workbook missing required columns | merge stops with `WORKBOOK_SCHEMA_CONFLICT` |

## -2.10 Release profile labels

Every bundle ZIP should declare one of these release profiles in `RELEASE_MANIFEST.md`:

| Profile | Meaning |
|---|---|
| `DEV_CANDIDATE` | suitable for testing; may contain aspirational docs or incomplete tests |
| `CHATGPT_STANDALONE_CANDIDATE` | expected to run in ChatGPT with uploaded antiSMASH ZIPs and bundled Python |
| `LOCAL_FULL_PIPELINE_CANDIDATE` | expected to run locally with repo, dependencies, and tests |
| `PUBLIC_RELEASE` | docs, code, tests, schema, and examples synchronized |

v9.7.6 monolith status: `PUBLIC_RELEASE` — bundle patched, reviewed, and checksums verified during v9.7.6 read-through (2026-06-09).

## -2.11 Immediate bundle update order

Completed in v9.3 (2026-06-09). Steps for reference:

1. Add `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md`.
2. Move prior active monoliths to `docs/legacy/` with `HISTORICAL_DO_NOT_USE_AS_CONTROLLER` banner (completed v9.3).
3. Generate the five derived prompt/doc files in §-2.8.
4. Update `README.md` to say Mamey is deterministic extraction and Sapote is interpretation.
5. Update `RELEASE_MANIFEST.md` with release profile and known limitations.
6. Verify `mamey_run.py --help` against documented run modes and arguments.
7. Verify workbook schema docs/templates against actual produced workbook columns.
8. Add tests or manual validation files for the minimal test matrix.
9. Build release ZIP.
10. Run smoke/gold validation and record results.

---

# SECTION -1 — Bundle Kernel / All-in-One Replacement Layer

## -1.0 Purpose

This v9.2 candidate is the **bundle-first monolith**. It keeps the v8.4 Sapote scientific logic, but adds the missing execution architecture that the software bundle now needs: deterministic extraction first, interpretive judgment second, workbook write-back third, and explicit batching/resume state throughout.

This monolith is intended to replace scattered prompt fragments in the Sapote-Mamey bundle. It does **not** replace executable code. It is the controlling specification that tells ChatGPT, Claude, or another analyst how to use the bundle correctly, what must be produced, what may be deferred, and how claims are bounded.

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

> **Mapping to the Mamey CLI (`mamey_run.py run --mode`):** the executable `--mode` flag has exactly three values — `smoke`, `standard`, `gold` (default `standard`). The `smoke` and `gold` rows above are those CLI modes directly. The CLI's **`standard`** mode (the default; full Mode B for Interior / CCTT-coupled / KCB>5000 BGCs, abbreviated ledger otherwise) is the routine extraction that feeds the **`sapote_standard`** interpretation stage. `sapote_standard` / `sapote_archive` are Sapote *interpretation* stages run on a completed Mamey package (they are not `--mode` flags), and `project_merge` is the master-workbook merge operation (`update_master_workbook` / the `validate` path), also not a `--mode` flag. In short: `smoke`/`standard`/`gold` are deterministic extraction depths; `sapote_*` and `project_merge` are downstream bundle stages.

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

At the start of every bundle run, state the following before doing analysis:

```text
BUNDLE SESSION HANDSHAKE
Bundle/version loaded: [repo/bundle name and version]
Input ZIPs detected: [N]
Master workbook detected: [yes/no + filename]
Committed strain count this session: [N]
Deferred strain count: [N]
Run mode: [smoke/gold/sapote_standard/sapote_archive/project_merge]
Depth policy: depth-first, one strain at a time unless project_merge only
Completion rule: all required deterministic scans complete or failed explicitly
Output checkpoint: SID_session_checkpoint.csv or project_session_checkpoint.csv after every completed strain
```

## -1.5 Depth-first batching rule

For strain runs, process **one strain at a time**. Do not start interpretation for strain B until strain A has:

- sealed per-strain package,
- manifest,
- checksums,
- scan-states JSON,
- workbook-ready tables,
- checkpoint row,
- failure ledger if anything failed.

For uploaded batches larger than the session can safely finish, commit to the number that can be finished, mark the rest `MAMEY_DEFERRED`, and include their filenames in the checkpoint.

## -1.6 Per-strain checkpoint schema

After each completed or failed strain, emit or update:

```csv
strain_id,assembly_bp,contigs,n50,gc_pct,raw_bgcs,interior_pct,rggmci_pairs_total,rggmci_high,dasr,cbm_chitin,bldA_t4,t1r,flbr_grade,session_id,timestamp,mamey_status
```

Allowed `mamey_status` values only:

- `MAMEY_COMPLETE`
- `MAMEY_FAILED`
- `MAMEY_DEFERRED`
- `MAMEY_RECOVERY_NEEDED`

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

When the user says “continue,” do not restart from scratch. Do this:

1. Locate the latest checkpoint and final ZIP/package in the current session.
2. Read the checkpoint and identify the next `MAMEY_DEFERRED`, `MAMEY_FAILED`, or missing required strain/BGC.
3. Continue from the next unfinished item.
4. Rebuild only changed artifacts plus the final handoff ZIP.
5. Report exactly what changed since the previous ZIP.

## -1.10 Accession and public-genome rule

If a task requests a public accession:

- Use `--accession` only if the runner exposes it.
- If the runner requires antiSMASH ZIP input, say so explicitly.
- Do not fabricate antiSMASH or Mamey outputs from accession metadata alone.
- If antiSMASH ZIPs are supplied later, replace failed placeholders with complete sealed packages and rebuild the batch ZIP.

## -1.12 Bundle file-map and replacement protocol

This monolith is the controlling specification for the bundle. It should be treated as the parent source for prompt/document updates, but it should not overwrite Python modules without a code patch and tests.

### Parent/derived document model

| Bundle file | Role after v9.2 | Update action |
|---|---|---|
| (retired) | Legacy v8.10.2 Sapote monolith | Retired; not shipped in this bundle. |
| `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` | Derived Sapote-only judgment kernel | Regenerate from v9.2 sections covering Sapote interpretation, claim-safety, Triage First, Mode B, literature, and reports. |
| `prompts/CLAUDE_SYSTEM_PROMPT.md` | Claude/Sapote-tier execution prompt | Regenerate as a concise derived prompt from v9.2: Sapote reads Mamey evidence, never invents extraction fields, and returns merge-ready deltas. |
| `prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md` | ChatGPT/Mamey-tier execution prompt | Regenerate as deterministic run instructions: one strain at a time, ten scans, checkpoint after every strain, sealed package. |
| `docs/standalone/CHATGPT_BATCH_PROTOCOL.md` | Batch/resume guide | Replace with the v9.2 Batch Controller and continuation protocol. |
| `prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md` | User-facing batch brief | Update to require explicit inputs, committed strain count, exact output schema, and failure/recovery vocabulary. |
| `docs/WORKFLOW_GUIDE.md` and `docs/HOW_TO_USE.md` | User guide | Update examples to show Mamey-first, Sapote-second, workbook-third execution. |
| `docs/WORKBOOK_SCHEMA.md` | Workbook contract | Do not edit from prose alone. Update only after confirming workbook tabs/columns in code and templates. |
| `templates/master_workbook_template_v1.0.xlsx` | Workbook template | Update only after schema validation and user approval. |
| `mamey/*.py` | Executable kernel | Do not change from monolith text alone. Create code issue/patch, add tests, then update. |
| `tests/*.py` | Validation suite | Add/adjust tests whenever monolith requirements become code requirements. |
| `README.md` and `RELEASE_MANIFEST.md` | Public-facing bundle summary | Update after the monolith and derived prompts stabilize. |

### Replacement rule

The active bundle should contain **one parent controller** and several derived short prompts. Avoid multiple active monoliths with conflicting instructions. If an older Sapote monolith remains in the repository, mark it explicitly as `legacy_reference`, not `current_controller`.

## -1.13 Bundle update workflow after monolith finalization

When this monolith is finalized, update the bundle in this order:

1. **Freeze parent monolith.** Save as `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` or the agreed release name.
2. **Regenerate derived prompts.** Create short, task-specific prompts from the parent: ChatGPT execution, Claude interpretation, batch brief, handoff protocol, and user guide snippets.
3. **Run document consistency check.** Search the repo for stale terms and conflicting instructions: `v8.1`, the retired project codename (renamed to ``), `Davey`, `optional RG-GMCI`, `PENDING`, `Full Coverage Mode`, and outdated workbook tabs. (Do not flag `Bert` — live literature-mode feature; or `v8.4 candidate` — intentional backward-compat triggers in §0/§0.11.)
4. **Update workbook schema docs only after verification.** Compare `docs/WORKBOOK_SCHEMA.md`, `templates/master_workbook_template_v1.0.xlsx`, and actual workbook output columns. Resolve conflicts before release.
5. **Patch code only where the executable kernel disagrees with the final contract.** Example: if v9.2 requires accession mode but `mamey_run.py` cannot run accessions, either add tested accession support or state clearly that accession tasks require precomputed antiSMASH ZIPs.
6. **Add or update tests.** Every executable requirement needs a test or a documented manual validation item.
7. **Build release ZIP.** Include source checksums, release manifest, changelog, package profile, and quick-start examples.
8. **Run one smoke test and one gold test.** The release is not ready until at least one small antiSMASH ZIP passes smoke mode and one representative strain passes gold mode or fails transparently for a documented reason.

## -1.14 Batch Controller v2 — committed work units

The bundle should avoid overcommitting. At session start, classify uploaded work into committed and deferred work units.

### Work-unit types

| Work unit | Commit size guideline | Completion artifact |
|---|---:|---|
| antiSMASH ZIP → Mamey smoke | 2–6 strains/session depending on ZIP size | assembly/stats CSV + manifest |
| antiSMASH ZIP → Mamey gold | 1–2 strains/session | sealed package + checkpoint row |
| completed Mamey package → Sapote standard | 1–3 strains/session | candidate cards/report sections |
| completed Mamey package → Sapote archive | one strain split by BGC batches | archive checkpoint + deferred ledger |
| master workbook merge | one workbook/session | updated workbook + merge log + schema report |
| cross-strain analysis | one defined cohort/session | cohort table/figure/report |

### Session-start commitment text

```text
I detect [N] uploaded work units. I can safely complete [K] in this session at the requested depth.
Committed now: [list strain IDs/files]
Deferred: [list strain IDs/files]
Depth policy: depth-first; I will finish each committed strain before starting the next.
Checkpoint policy: after every strain, I will update [checkpoint filename].
```

### Continue command behavior

When the user says `continue`, process the next deferred or failed work unit from the latest checkpoint. Do not re-run completed work unless the user asks for reanalysis, a new bundle version, or a schema change.

## -1.15 Failure taxonomy and recovery actions

Failures must be informative enough that another assistant can recover them.

| Failure code | Meaning | Required recovery action |
|---|---|---|
| `INPUT_MISSING` | Required ZIP/workbook/manifest not available | List exact filename needed. |
| `UNSUPPORTED_ACCESSION_MODE` | Public accession requested but runner cannot fetch/run antiSMASH | Request antiSMASH ZIP or accession-enabled runner. |
| `ANTISMASH_PARSE_FAILED` | ZIP present but antiSMASH structure unsupported/incomplete | Record parser error and required file paths. |
| `SCAN_FAILED_KCB` | KCB sweep failed | Record whether KCB files were absent or parser failed. |
| `SCAN_FAILED_RGGMCI` | RG-GMCI failed | Record missing contig/BGC crosswalk inputs. |
| `SCAN_FAILED_SOURCE_DERIVED` | CCTT/CGAD/UMED/EFLS/resistance/bldA_TTA failed | Record exact scan and missing evidence source. |
| `WORKBOOK_SCHEMA_CONFLICT` | Output columns do not match workbook schema | Stop merge; emit schema report. |
| `PACKAGE_QA_FAILED` | Final ZIP missing required artifacts/checksums | Rebuild package before handoff. |

Every `MAMEY_FAILED` row must include one failure code, a human-readable reason, and a recovery action.

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

Each scan is a `[name, state, detail]` triple. Valid scan states are `PASS`, `NULL`, `NOT_APPLICABLE`, `DEFERRED`, and `FAILED` (this matches the README and the code). `evidence_channels` records the status of the GBK-domain / HMMER / DIAMOND / BLASTP channels, several of which are Release-2 scope.

> **Release-2 (aspirational, not yet emitted):** a richer per-scan object — `{scan_name, status, started_at, completed_at, input_sources, output_files, summary_counts, failure_code, failure_reason, recovery_action, claim_boundary}` with `MAMEY_COMPLETE`/`MAMEY_FAILED`/`MAMEY_DEFERRED`/`MAMEY_NOT_APPLICABLE`/`MAMEY_RECOVERY_NEEDED` statuses — is the intended future schema. It is documented here as a target, not a current contract; the current emitted form is the `[name, state, detail]` triple above.

## -1.17 Workbook merge contract

The current `update_master_workbook` (mamey/master_workbook.py) performs **idempotent re-ingest**: it loads the master, ensures all persistent sheets exist with correct headers (additively), calls `workbook_dedup.drop_existing_strain` to remove any prior rows for the incoming strain, then appends the fresh rows (one per strain to the registry/dashboard sheets, one per BGC to the per-BGC sheets) and writes an immutable snapshot copy. It does **not** run schema validation inline (that is a separate `workbook_schema_check` step). Keyed upsert across arbitrary columns is not performed — dedup is by strain.

### Current behavior (idempotent re-ingest)

| Sheet family | Row identity | Merge behavior (current code) |
|---|---|---|
| strain registry / A2 | `Strain` / `strain_id` | drop prior strain rows, then append (one per run) |
| BGC master | `Strain` + `BGC_ID` | drop prior strain rows, then append (one per BGC per run) |
| RG-GMCI | `Strain` | drop prior strain rows, then append summary row(s) |
| scan comparison | `Strain` + `scan_name` | drop prior strain rows, then append per scan |
| lead/candidate sheets | `Strain` + `BGC_ID` + `lead_id` | drop prior strain rows, then append |
| provenance/merge log | timestamped row | append-only (audit trail; not deduped) |

**Operational discipline (because re-ingest is idempotent):** re-running the same strain into the master is **safe** — `drop_existing_strain` removes that strain's prior rows before re-appending, so a re-run replaces rather than duplicates. `Strain` + `BGC_ID` is the row *identity*; dedup is performed by strain on re-ingest. The provenance/merge log is the one append-only sheet, intentionally, as an audit trail.



### Schema validation (separate step)

Schema validation is provided by the standalone `workbook_schema_check.py` utility (`python -m mamey.workbook_schema_check <workbook.xlsx>` or run directly), which checks required sheets/columns and can emit `WORKBOOK_SCHEMA_CONFLICT`. It is **run separately**, not wired into the merge. The conditions it checks for: required columns missing; duplicate keys that cannot be reconciled; a merge that would delete existing rows; a field requiring Sapote interpretation in a Mamey-only task; or old/new values conflicting with no clear provenance.

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

- **Schema:** `MASTER_SCHEMA_FROZEN_v1_1.md` §Provenance gate (lines 75-101) defines the `closest_product_provenance` field with 7 enumerated values (KCB_TEXT_EXACT, MIBIG_REFERENCE_LINE, KCB_TOP_FIELD, etc.). Any workbook sheet carrying a product name must carry its provenance field.
- **Code:** `mamey/render_safe.py:safe_kcb_display()` and `mamey/concordance.py:closest_candidate_kcb_product()` implement provenance-aware rendering. Raw `kcb_top` values must never appear in user-facing outputs without provenance qualification.
- **Architecture-first override:** `mamey/architecture_first.py` (v9.7.107) enforces KCB-blind pathway classification. When gene architecture and KCB disagree, architecture wins. See Slim Judgment Kernel Module 2.5.

## -1.19 Derived prompt targets

After finalization, derive these shorter files from this monolith:

1. `prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md` — maximum 2–4 pages; no long Sapote interpretation sections.
2. `prompts/CLAUDE_SYSTEM_PROMPT.md` — maximum 2–4 pages; reads Mamey outputs and produces claim-safe interpretation/workbook deltas.
3. `docs/standalone/CHATGPT_BATCH_PROTOCOL.md` — maximum 2 pages; session-start commitment, checkpoint, continue behavior.
4. `prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md` — fill-in-the-blank brief for new batches.
5. `docs/HOW_TO_USE.md` — user guide with examples: smoke, gold, Sapote standard, archive, merge.
6. `docs/WORKFLOW_GUIDE.md` — workflow diagram and operational descriptions.

The parent monolith should be comprehensive. Derived prompts should be short enough to actually use.

## -1.20 Release-readiness checklist

A bundle release is ready only when all of the following are true:

- [ ] Exactly one current parent monolith is named in `README.md` and `RELEASE_MANIFEST.md`.
- [ ] Legacy monoliths are marked as archived/reference.
- [ ] Derived prompts agree with the parent monolith.
- [ ] CLI examples in docs match the actual CLI.
- [ ] Accession support is either implemented/tested or explicitly unsupported.
- [ ] Workbook schema docs match workbook templates and generated outputs.
- [ ] Gold mode produces the nine required scan statuses.
- [ ] Failure packages include failure code, reason, and recovery action.
- [ ] Batch continuation works from a checkpoint.
- [ ] Final package QA checks manifest, checksums, and required files.
- [ ] At least one smoke run and one gold run have been validated on known input.
- [ ] The changelog explains the Sapote-Mamey split and why the monolith is a controller, not a replacement for code.


## -1.11 Minimum all-in-one completeness check

A bundle monolith is complete only if it contains:

- deterministic Mamey scan spine,
- Sapote interpretation layer,
- run modes,
- session-start handshake,
- depth-first batching rule,
- checkpoint schema,
- workbook contract,
- package manifest,
- validation checklist,
- continuation protocol,
- failure/recovery status vocabulary,
- claim-safety boundaries,
- reader-layered reports,
- Triage First Board,
- LC-MS chemical handles,
- FLBR/RG-GMCI fragmentation handling,
- CCTT/CGAD/UMED/EFLS/resistance/bldA_TTA scans,
- standard vs archive-quality interpretation modes.

If any item is missing, the monolith is a Sapote prompt, not a Sapote-Mamey bundle controller.

---

## Prompt Table of Contents

-1. [Bundle Kernel / All-in-One Replacement Layer](#section--1--bundle-kernel--all-in-one-replacement-layer)
  - -1.12 Bundle file-map and replacement protocol
  - -1.13 Bundle update workflow after monolith finalization
  - -1.14 Batch Controller v2 — committed work units
  - -1.15 Failure taxonomy and recovery actions
  - -1.16 Minimum scan-state schema
  - -1.17 Workbook merge contract v2
  - -1.18 Claim boundary matrix
  - -1.19 Derived prompt targets
  - -1.20 Release-readiness checklist

0. [Run Controller / Execution Spine](#section-0--run-controller--execution-spine)
0.5. [Reader-Layered Output System](#section-05--reader-layered-output-system)
0.6. [Triage First Board](#section-06--triage-first-board)
0.7. [LC-MS Chemical Handle Module](#section-07--lc-ms-chemical-handle-module)
0.8. [Visual Load Reduction Standard](#section-08--visual-load-reduction-standard)
0.9. [Standard vs Archive-Quality Full Analysis](#section-09--standard-vs-archive-quality-full-analysis)
0.10. [Evidence / Claim Separation Card](#section-010--evidence--claim-separation-card)
0.11. [Package Manifest and Deferred Ledger](#section-011--package-manifest-and-deferred-ledger)

1. [Purpose](#purpose)
2. [How to Use This Prompt](#how-to-use-this-prompt)
3. [Global Data Governance Rules](#global-data-governance-rules)
4. [Full Analysis Mode — Active Override](#full-analysis-mode--active-override)
5. [§2B Batch Plan Protocol](#2b--batch-plan-protocol)
6. [Session Startup Checklist](#section-1--session-startup-checklist)
6. [Input File Inventory and Source Roles](#section-2--input-file-inventory-and-source-roles)
7. [antiSMASH ZIP / JSON Parsing Pipeline](#section-3--antismash-zip--json-parsing-pipeline)
8. [Assembly, BGC Inventory, RiQ, and Corrected BGC Counts](#section-4--assembly-bgc-inventory-riq-and-corrected-bgc-counts)
9. [KCB Sweep Module](#section-5--kcb-sweep-module)
10. [Domain-Level Analysis](#section-6--domain-level-analysis)
11. [NRPS/PKS Module Architecture](#section-7--nrpspks-module-architecture)
12. [Diagnostic Domain Combinations](#section-8--diagnostic-domain-combinations)
13. [TTA Codon / bldA Gating](#section-9--tta-codon--blda-gating)
14. [TFBS Signals and Induction Conditions](#section-10--tfbs-signals-and-induction-conditions)
15. [Dereplication Verdicts and Novelty Language](#section-11--dereplication-verdicts-and-novelty-language)
16. [Coverage and HGT Flags](#section-12--coverage-and-hgt-flags)
17. [Neighbourhood Comparison and Medium-BGC Rescue](#section-13--neighbourhood-comparison-and-medium-bgc-rescue)
18. [Taxonomy Integration](#section-14--taxonomy-integration)
19. [Strain-Level Deliverables](#section-15--strain-level-deliverables)
20. [Cross-Habitat Figures](#section-16--cross-habitat-figures)
21. [Ecological Synthesis Module](#section-17--ecological-synthesis-module)
22. [Excel Deliverables](#section-18--excel-deliverables)
23. [Manuscript Update Procedure](#section-19--manuscript-update-procedure)
24. [Glossary and Layperson Explanation Workflow](#section-20--glossary-and-layperson-explanation-workflow)
25. [Verified Literature Deep Dive v2.0](#section-21--verified-literature-deep-dive-v20)
26. [Rapid Literature Deep Dive v2.0](#section-22--rapid-literature-deep-dive-v20)
27. [Mode Selection Decision Tree](#section-23--mode-selection-decision-tree)
28. [Cross-Strain Comparison Module](#section-24--cross-strain-comparison-module)
29. [Key Scientific Findings to Preserve](#section-25--key-scientific-findings-to-preserve)
30. [Reference Implementations](#section-26--reference-implementations)
31. [Output Audit Log Template](#section-27--output-audit-log-template)
32. [File Naming Conventions](#section-28--file-naming-conventions)
33. [CDSW Protocol Summary](#section-29--cdsw-protocol-summary)
34. [Output Quality Assurance Gates](#section-30--output-quality-assurance-gates)
35. [BGC Architecture Confidence System](#section-31--bgc-architecture-confidence-system)
36. [Evidence Traceability Blocks](#section-32--evidence-traceability-blocks)
37. [Wet-Lab Decision Matrix](#section-33--wet-lab-decision-matrix)
38. [Diagnostic Signature Weighting + antiSMASH Hallucination-Trap / Claim-Calibration Audit](#section-34--diagnostic-signature-weighting--antismash-hallucination-trap--claim-calibration-audit)
39. [Cross-Strain BGC Family Clustering Hook](#section-35--cross-strain-bgc-family-clustering-hook)
40. [Reviewer Attack Simulation](#section-36--reviewer-attack-simulation)
41. [Metabolomics Readiness Module](#section-37--metabolomics-readiness-module)
42. [Known Missingness Tracking](#section-38--known-missingness-tracking)
43. [Figure Suggestion Module](#section-39--figure-suggestion-module)
44. [Project Memory Snapshot](#section-40--project-memory-snapshot)
45. [Cross-Comparative Synthesis Module](#section-41--cross-comparative-synthesis-module-ccsm-v11)
46. [Large Modular PKS Rescue Workflow](#section-42--large-modular-pks-rescue-workflow-lmpks-rw)
47. [Cryptic-Class / Tailoring Trigger Module](#section-43--cryptic-class--tailoring-trigger-module-cctt-v10)
48. [Chitin / Glycan-Active Defense Module](#section-44--chitin--glycan-active-defense-module-cgad-v10)
49. [Resistance Gene-Guided Compound Class Confirmation](#section-45--resistance-gene-guided-compound-class-confirmation)
50. [Standalone Prompt Completeness Check](#standalone-prompt-completeness-check)
51. [Reader-Facing Front Page and Briefing Package](#section-49--reader-facing-front-page-and-briefing-package)
52. [v8.2 Compound-Class Coverage + Claim-Safety Patch](#section-50--v82-compound-class-coverage--claim-safety-patch)
53. [§51 Fragmented Large-BGC Rescue (FLBR)](#section-51--fragmented-large-bgc-rescue-flbr)
54. [§52 Unclustered Maturation Enzyme Detection (UMED)](#section-52--unclustered-maturation-enzyme-detection-umed-v10)

**Patches applied:**
- v9.2 bundle-hardening/release-bridge patch (2026-06-08): added active-controller rule, requirement implementation-status labels, repo synchronization gate, execution profiles, accession boundary decision path, project_state.json contract, idempotent rebuild policy, derived-prompt set, minimal test matrix, release profile labels, and immediate bundle update order.
- v9.1 candidate bundle-hardening patch (2026-06-08): extends v9.0 with bundle file-map/replacement protocol, parent/derived prompt model, release update workflow, committed work-unit batching, failure taxonomy, minimum scan-state schema, workbook merge contract v2, claim boundary matrix, derived prompt targets, and release-readiness checklist.
- v9.0 candidate bundle-controller patch (2026-06-08): added all-in-one Sapote-Mamey bundle kernel, deterministic scan spine, depth-first batching, checkpoint schema, workbook contract, continuation protocol, accession/public-genome boundary, all-in-one package manifest, and bundle completeness check.
- v7.9.1 compound-class coverage patch (2026-05-30): modified §8, §26, §33.3, §34, §37, and §43; added version-history and standalone-completeness-check items.
- v8.0 execution and readability integration (2026-05-30): added §0, §0.5, §0.6, §0.7, §0.8, §0.9, §0.10, §0.11, §46; mode default changed to Standard Full Analysis.
- v8.0.1 specification refinement patch (2026-05-30): 7 items - see version history.
- v8.0.2 CGAD genome-wide proteome scope patch (2026-05-30): added CGAD Step 0 full-proteome gate, BGC-local null hallucination trap, proteome-scope missingness category, ecological-evidence labels, DasR coupling guard, version-history and completeness-check updates.
- v8.0.3 ICBG1735 workflow-flexibility patch (2026-05-30): added canonical BGC IDs, ecological citation evidence grades, APE_KS2 arylpolyene handling, CGAD HMMER-unavailable motif fallback, QS signal routing, Gram-negative KCB false-positive traps, Mode B §4 citation requirement, multi-siderophore capacity flag, and phenazine→Escovopsis specificity guard. Added test-ready taxonomy preflight note: optional ContEst16S/EzBioCloud 16S extraction and BLAST workflow for assembled FASTA inputs, with genus-level use and species-level caution.
- v8.1 Reader-Facing Front Page and Briefing Package patch (2026-05-30): added default post-analysis front-page package with Editorial Broadsheet, Color Tabloid, and Executive Briefing formats; optional user-uploaded imagery slots; simplified front-page Node labels with full NODE preservation in technical tables; raw-vs-corrected BGC count disclosure; rounded reader-facing genome statistics; smaller Sapote-version memo signature; and priority-lead support fields for compound class, key genes/domains, architecture, and next wet-lab action.
- v8.1.1 Diagnostic Signature Weighting + antiSMASH Hallucination-Trap / Claim-Calibration Audit patch (2026-05-31): expanded the Hallucination-Trap module into a fragment-tolerant claim-calibration system. Added evidence-weight tiers for genes/domains; separated Lead Priority from Claim Confidence; added Diagnostic Signal Score; formalized high-information signature rescue for fragmented contigs; added transporter and self-resistance exception handling; distinguished exact product markers, class-supporting markers, physicochemical-feature predictors, and self-resistance/target-directed prioritization markers; added required safe-claim language, marker-library placeholders, and front-page/PDB claim-safety routing.
- v8.2 compound-class coverage + claim-safety patch (2026-05-31): added absence-of-assay ≠ inactivity standing principle; DKP/CDPS detection rank A–D and T43-DKP; linear polyether ionophore LMPKS-PE routing; optional gated PKS KR/ER stereochemistry reasoning; metabolomics rows and hallucination-trap guards for DKP and polyether cases; updated trigger phrases and version history.
- v8.3 candidate Fragmented Large-BGC Rescue (FLBR) patch (2026-05-31): added §51 parent rescue logic for fragmented assembly-line megasynthases across T1PKS, modular NRPS, PKS-NRPS hybrid, and trans-AT systems; added two-tier STRONG/WEAK evidence model, assembly-quality gate, double-docking Very-Poor carve-out, Run Controller sequencing guard, QA gates, trigger phrases, and validation appendix.
- v8.4 candidate Unclustered Maturation Enzyme Detection (UMED) patch (2026-05-31): added §52 parent maturation-gap logic, first validated for lanthipeptide protease detection; added in-cluster/GAP/GAP-no-candidate statuses, genome-wide candidate protease scans, M16B heterodimer guard, specificity-unverified claim ceiling, Very-Poor missingness handling, UMED QA gates, trigger phrases, and validation appendix.

---

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

3. **Parallel first-pass scans** (all ten; matches §0.6 Triage timing and system-prompt §4.2)
   - KCB sweep.
   - Diagnostic Signature Weighting + antiSMASH Hallucination-Trap / Claim-Calibration Audit (§34): classify high-information versus generic genes, preserve promising fragments, and calibrate allowable claim language before Mode B, Triage First, Front Page/PDB, and Wet-Lab Decision Matrix outputs.
   - LMPKS Rescue (§42).
   - FLBR megasynthase fragment census (§51).
   - UMED maturation-enzyme scan (§52) for lanthipeptide/RiPP maturation gaps.
   - CCTT Trigger Scan (§43).
   - CGAD if ecological source supports it (§44) — **only after Proteome Scope Check confirms `full proteome scanned`, `BGC-region only`, or `full proteome unavailable`; confirm proteome source before any CGAD verdict is recorded.**
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
   - Archive-Quality mode: full Mode B §1–§8 for every BGC, batched if needed.

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
  - Novelty % = highest antiSMASH knownclusterblast MIBiG similarity; “Known (N%)” ≥50%; “Novel” <50%.
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

Structured in three sub-sections per strain (see FULL_RUN_PROFILE.md §G for full format spec):

Sub-section 1 — Known / Reference BGCs table: compound detection matrix with columns for MW, UV/Vis, colour/CAS, extraction protocol, LC-MS mode, key assay, induction hint, safety. One column per known BGC (≥60% MIBiG); rows are compound properties. This is a TABLE-format deliverable, not prose.

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

In **Archive-Quality Full Analysis** mode, Layer C contains all of the above plus full Mode B §1–§8 for every BGC, gene-by-gene tables for every BGC, full KCB extraction table, and complete traceability blocks for every BGC.

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
| BGC / node | BGC number, contig/node, or split-pathway unit |
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

1. Specific mechanistic fit to bioactivity or default screen.
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
Assay support: [user-confirmed / file-confirmed / default-assumed / not tested]
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
- Every candidate linked to MRSA/Candida default or confirmed bioactivity.

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
DEFAULT-ASSUMED BIOACTIVITY
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
| BGC # | As in BGC inventory table |
| Node / contig | Node identifier |
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
- Full Mode B §1–§8 report for every BGC.
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
| What the assay supports | User-confirmed, file-confirmed, default-assumed, not tested, inactive, or unknown |
| What is plausible | Mechanistic or chemical interpretation that is reasonable but not proven |
| What remains unproven | Compound production, BGC-level attribution, mechanism, final structure, activity source |
| What to do next | Specific LC-MS, extraction, bioassay, cytotoxicity, MS/MS, long-read, or genetics action |

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

This prompt enables an AI assistant to reproduce and extend the Sapote actinomycete natural product discovery workflow across sessions. It combines project-scale management, strain-level antiSMASH/BGC analysis, cross-habitat comparison, bioactivity correlation, taxonomy integration, manuscript updating, figure generation, glossary building, citation-verified bibliography workflows, and cross-strain comparative synthesis.

The workflow is designed to prevent context loss across long projects and to be reusable across any actinomycete or bacterial collection with antiSMASH output. At the beginning of a new session, upload the master files or strain-specific ZIPs, then use one of the trigger phrases below.

---

## How to Use This Prompt

### Option 1 — Full project restart

```text
We are continuing the Sapote actinomycete natural product discovery project.
Use the current Sapote-Mamey workflow version.
I am uploading the master JSON, master strain list, and current manuscript.
Today's goal is: [describe goal].
```

### Option 2 — Run strain-level full analysis

```text
Run standard full analysis on [Strain ID]. [Taxonomy]. [Host/source]. [Bioactivity]. Apply architecture confidence, evidence traceability, wet-lab decision scoring, hallucination-trap audit, metabolomics readiness, reviewer attack simulation, resistance gene confirmation, UMED maturation-enzyme detection, PDF Style Standard, bioactivity default enforcement, and project memory snapshot. Use single-pass execution if feasible; otherwise run in batches but preserve the final compiled deliverable plan.
```

### Option 3 — Run only a specific module

```text
Run taxonomy preflight on [Strain ID] from assembled FASTA.
Extract/check 16S from assembled FASTA for [Strain ID].
Run KCB sweep on [Strain ID].
Make fermentation card for [Strain ID].
Run cross-strain comparison: [Strain A] vs [Strain B] for [compound class or domain].
Update/rebuild the cross-habitat figures.
Run Verified Literature Deep Dive on [compound/BGC/domain/paper set].
Use Rapid Literature Deep Dive for [compound class or BGC family].
Build glossary entries from these documents.
Run CCSM for [Habitat class]. Strains: [list].
Run within-habitat comparison for [Habitat class].
Run cross-habitat comparison: [Habitat A] vs [Habitat B].
Run Macrolide / Large Modular PKS Rescue on [Strain ID].
Run LMPKS rescue on [Strain ID].
Scan for hidden macrolide and large modular PKS signatures.
Find published macrolide or linear PKS candidates.
Map published chemistry back to antiSMASH BGCs.
Run trans-AT PKS scan on [Strain ID].
Run polyene rescue on [Strain ID].
Run linear PKS rescue on [Strain ID].
Run LMPKS fragment accumulation on [Strain ID].
Run LMPKS_FRAGMENT_SET analysis on [Strain ID].
Run FLBR on [Strain ID].
Run fragmented megasynthase rescue on [Strain ID].
Run NRPS fragment rescue on [Strain ID].
Run megasynthase fragment census on [Strain ID].
Run UMED on [Strain ID].
Run maturation enzyme scan on [Strain ID].
Check lanthipeptide protease for [Strain ID].
Find unclustered protease for [Strain ID] BGC [N].
Run lanthipeptide maturation gap scan on [Strain ID].
Run cryptic-class trigger scan on [Strain ID].
Run CCTT on [Strain ID].
Run halogenase scan on [Strain ID].
Run nucleoside / peptidyl-nucleoside scan on [Strain ID].
Run phosphonate scan on [Strain ID].
Run enediyne scan on [Strain ID].
Run aminocyclitol / aminoglycoside rule-out on [Strain ID].
Run chitin / glycan-defense scan on [Strain ID].
Run CGAD on [Strain ID].
Run resistance gene confirmation on [Strain ID].
Run resistance gene scan on [Strain ID].
Run DKP / CDPS scan on [Strain ID].
Run cyclodipeptide synthase scan on [Strain ID].
Run polyether scan on [Strain ID].
Run polyether ionophore scan on [Strain ID].
Check polyether cassette for [Strain ID] BGC [N].
Run PKS stereo prediction on [Strain ID] BGC [N].
Predict polyketide stereochemistry for [Strain ID] BGC [N].
```

### Option 4 — Use as a technical appendix

Paste only the relevant section for short tasks:
- Figures: Section 16 | Ecological synthesis: Section 17 | Excel: Section 18
- Manuscript: Section 19 | Strain antiSMASH analysis: Sections 3–15
- Glossary: Section 20 | Literature: Sections 21–23
- Architecture/traceability: Sections 31–32 | Wet-lab: Section 33
- Hallucination checks: Section 34 | Metabolomics: Section 37
- Cross-strain comparison: Section 41 (CCSM) | Resistance gene: Section 45

### Option 5 — One-command full workflow with adaptive execution

```text
Run full Sapote analysis on [Strain ID]. [Taxonomy]. [Host/source]. [Bioactivity]. Use single-pass execution if feasible; otherwise use stepwise batches, but preserve the final compiled deliverable plan.
```

**Workflow Ledger** — minimum stages:

- [ ] **Batch Plan announced** (required if BGC count > 15; announce before any Mode B work begins)
- [ ] **Bioactivity default/override status recorded** (`default-assumed MRSA+Candida`, `user-confirmed`, `file-confirmed`, `not tested`, or `not available`)
- [ ] Intake / JSON extraction
- [ ] Metadata conflict audit completed
- [ ] Taxonomy preflight status recorded (`user-confirmed`, `file-confirmed`, `16S extracted from assembled FASTA`, `whole-genome/GTDB/ANI available`, `not available`, or `deferred`)
- [ ] Host/source and habitat category reconciled
- [ ] Prior strain-specific claims checked against corrected metadata
- [ ] Assembly statistics
- [ ] BGC inventory (with Architecture Confidence column)
- [ ] RiQ extraction
- [ ] KCB sweep
- [ ] **antiSMASH Hallucination-Trap Audit** ← run before Mode B, not after
- [ ] **LMPKS Rescue (§42)** ← run in parallel with KCB sweep; check auto-triggers §42.2
- [ ] **FLBR megasynthase fragment census (§51)** ← run in parallel with KCB sweep/LMPKS; reconcile all T1PKS, modular NRPS, PKS-NRPS hybrid, and trans-AT fragments before final priority assignment
- [ ] **UMED maturation-enzyme scan (§52)** ← run in parallel with FLBR/CGAD for lanthipeptide regions; assign IN-CLUSTER / GAP / GAP-no-candidate status and record genome-wide candidate proteases with specificity-unverified ceiling
- [ ] **CCTT trigger scan (§43)** ← run in parallel with KCB sweep / LMPKS; check halogenase, nucleoside, phosphonate, enediyne, aminocyclitol markers
- [ ] **DKP / CDPS scan (§8/§43/§37/§34/§45)** ← run automatically within CCTT; assign DKP-A/B/C/D when CDPS or PF16715 is present
- [ ] **Linear polyether ionophore scan (§8/§42/§37)** ← run automatically within LMPKS for ≥5-module cis-AT T1PKS regions; assign LMPKS-PE when cassette/KCB evidence supports it
- [ ] **PKS KR/ER stereochemistry reasoning (§6/§7/§30.1)** ← optional/gated for high-confidence modular cis-AT T1PKS BGCs where stereochemical hypotheses are useful
- [ ] **Resistance gene scan (§45)** ← run in parallel with CCTT; check Tier 1/2/3 markers; record concordance and HGT guard outcomes
- [ ] TTA / bldA tiers
- [ ] Coverage and HGT flags
- [ ] Dereplication verdicts
- [ ] **Architecture Confidence assigned for every BGC**
- [ ] **Evidence Traceability blocks generated**
- [ ] Deep Dive Synopsis (including Reviewer Attack Simulation)
- [ ] Mode B / Partial Mode B reports (with Arch Confidence + Traceability in §1)
- [ ] **Wet-Lab Decision Matrix scored**
- [ ] **Metabolomics Readiness table generated**
- [ ] **Missingness Register completed**
- [ ] Ecological Synthesis
- [ ] **CGAD chitin/glycan-defense scan (§44)** ← genome-wide; feeds Ecological Synthesis §17.3/§17.4
- [ ] **Cross-Strain Family Seed table generated** → check CCSM threshold (Section 41.6)
- [ ] **Figure Suggestion Module completed**
- [ ] Layperson's Guide
- [ ] Fermentation Card
- [ ] Final compiled PDF
- [ ] Production TOC with page numbers
- [ ] PDF bookmarks/outlines
- [ ] **Project Memory Snapshot generated (JSON + MD)**
- [ ] Output audit log
- [ ] QA gate checks (Sections 30 + 31.13) — applied before compiling master PDF
- [ ] Package ZIP

### Option 6 — Smoke-test / development run

Use this when testing the workflow on a new AI system, validating a prompt change, or checking an antiSMASH ZIP before committing to a full report. Smoke-test mode is intentionally incomplete and must not be represented as the full workflow.

```text
Run smoke-test analysis on [Strain ID]. [Taxonomy]. [Host/source]. [Bioactivity].
```

Minimum smoke-test outputs:
- Intake / JSON extraction confirmation
- Assembly statistics and BGC inventory
- KCB summary if KCB files are present
- antiSMASH Hallucination-Trap quick audit
- Top-3 Triage First Board entries using the §0.6 column format (rank, BGC/node, predicted class, key genome evidence, chemical handle, confidence, caveat, next action); formula/MW may be class-level examples labeled `unverified example - check before targeted extraction`
- Fast ecological synthesis when host metadata is present
- Audit log and missingness note

Smoke-test mode does **not** require a final compiled PDF, full Mode B reports for every BGC, production TOC, bookmarks, or package ZIP unless explicitly requested.

### Module priority for limited runs

If the AI system has output, context, or tool limits, preserve the workflow by prioritizing modules in this order rather than skipping arbitrarily.

**Required core for strain analysis:** Sections 3–15, 27, 30, 31, 32, and 34.

**Strongly recommended:** Sections 17, 33, 37, 38, 40, 42, 45, and 52.

**Project-level or task-dependent:** Sections 16, 19, 20–23, 35, 39, and 41.

When modules are deferred, record them in the Workflow Ledger as `deferred`, not `completed`, and state what output would be needed to finish them.


---

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

These defaults apply to every strain analysis unless explicitly overridden at session start with strain-specific data. Log any override in the audit log.

**Bioactivity contract:** In the absence of strain-specific metadata, record `NOT_SUPPLIED`. Do not name an assay target, infer an outcome, or create BGC-level attribution. Typed supplied observations remain strain-level context unless a separately governed linkage is available.

#### Bioactivity default enforcement (v7.9)

When strain-specific bioactivity is not supplied, the workflow must treat MRSA and Candida inhibition as `default-assumed`, **not** as `missing`, and must explicitly carry that status through the analysis.

Required wording at session start:

```text
Bioactivity status: default-assumed MRSA and Candida extract-level inhibition. This workflow default does not assign activity to any specific BGC; BGC-level links require fractionation, metabolomics, genetics, or purified-compound evidence.
```

Required propagation points:
- Context acknowledgement / metadata audit
- Deep Dive Synopsis strain metadata table
- BGC Inventory notes or legend
- Every Mode B §6 mechanistic-link section
- Wet-Lab Decision Matrix scoring notes
- Metabolomics Readiness Summary
- Ecological Synthesis caveats
- Missingness Register, where it must be listed as `default-assumed`, not `missing`
- Project Memory Snapshot JSON and MD
- Final audit log

Required claim-safety language:
- Preferred: "This BGC is mechanistically compatible with the default extract-level MRSA/Candida screen, but no BGC-level attribution is made."
- Do not write: "This BGC explains the MRSA/Candida activity" unless supported by fractionation, metabolomics, genetics, or purified-compound evidence.

When actual assay data are supplied, replace `default-assumed` with `user-confirmed`, `file-confirmed`, or `not tested`, and log the override source.

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
- LexA → UV oxidative stress in surface soil; plant defence ROS bursts
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
- No source or bioactivity is given and defaults apply cleanly — state the defaults being used and proceed.
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
| User says "MRSA inactive" with no other context | Yes — 1 question | Conflicts with default; ask whether to override for this strain |
| No bioactivity mentioned | No | Apply MRSA+Candida default silently |
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

Sapote v8.0 uses **Standard Full Analysis** as the default full-run behavior. Standard Full Analysis accounts for every BGC but gives full Mode B treatment only to triage-selected top candidates, while routing lower-priority or fragmentary entries to abbreviated ledger entries and the Archive Appendix.

**Archive-Quality Full Analysis** is activated only when explicitly requested and requires full Mode B §1–§8 treatment for every BGC, batched if necessary.

Full Analysis Mode remains an active override against accidental omission: every BGC is accounted for in the inventory, triage, ledger, or archive plan. Priority tiers determine output depth and routing in Standard mode; they do not permit silent omission.

| Mode | Meaning | When to use |
|---|---|---|
| **Standard Full Analysis** | Reader-layered, triage-first report. All BGCs accounted for; top candidates receive full Mode B; remaining BGCs receive abbreviated ledger entries unless elevated by triggers. | Default for `Run v8.0 full analysis`, `Run the workflow`, and routine strain analysis. |
| **Archive-Quality Full Analysis** | Exhaustive run. Every BGC receives full §1–§8 Mode B treatment, including gene-by-gene analysis, with archive appendix and complete traceability. | Use only when user explicitly requests archive-quality, full depth, every BGC deep dive, publication archive, or workflow validation. |
| **Smoke-test Mode** | Fast incomplete validation run. | Use only when explicitly requested as smoke-test/development mode. |

**Standard deliverables (v8.0 order):** Context acknowledgement → BGC Inventory → KCB / Hallucination / LMPKS / CCTT / Resistance summaries → **Triage First Board with LC-MS Chemical Handles** → Executive Report → Scientific Deep Dive Report → top-candidate Mode B reports → Wet-Lab Decision Matrix → Metabolomics Readiness Summary → Reviewer Attack Simulation → Recommended Figures → Missingness Register → Fermentation Card → Project Memory Snapshot → Package Manifest → Archive Appendix or Deferred Ledger.

**Archive-quality deliverables:** All Standard deliverables plus full Mode B PDFs for every BGC, full gene-by-gene tables, complete raw traceability, full KCB/domain appendices, and complete archive package. If this cannot be completed in one session, use the §2B Batch Plan Protocol and continue in batches.

**Trigger phrases:**
```text
Full Analysis Mode
Run v8.0 full analysis on [Strain ID]. [Taxonomy]. [Host]. [Bioactivity].
Run standard full analysis on [Strain ID].
Run archive-quality full analysis on [Strain ID].
Run full depth analysis on [Strain ID].
Run v8.0.3 full analysis on [Strain ID]. [Taxonomy]. [Host]. [Bioactivity].
Run v7.9 full analysis on [Strain ID]. [Taxonomy]. [Host]. [Bioactivity].
```

**Context window and batch execution:** Archive-Quality Full Analysis for strains with more than approximately 15 BGCs typically requires multiple sessions. This is expected and correct behaviour, not a failure mode. Do not reduce analytical depth in Archive-Quality mode to fit a single session. Batch instead.


## §2B — Batch Plan Protocol

### When to announce

A Batch Plan is required whenever a full analysis trigger fires on a strain with **more than 15 BGCs**. The Batch Plan is announced before any Mode B report is started and before any per-BGC gene-by-gene work begins. Strains with 15 or fewer BGCs proceed to Mode B work immediately without a Batch Plan.

### Announcement format

```text
BATCH PLAN — [Strain ID] — [N] total BGCs — Full Depth Mode
Estimated sessions: approximately [X]

Batch 1 (this session): BGC[N1], BGC[N2], BGC[N3], ...
  Priority 1 — Interior BGCs WL ≥ 10: BGC[N1] (WL=[X]), BGC[N2] (WL=[Y])
  Priority 1 — §45 Tier 1 confirmed: BGC[N3]
  Priority 1 — §43 trigger (T43-ENE/T43-NUC): BGC[N4]
  Priority 2 — Remaining Interior BGCs: BGC[N5]–BGC[N8]

Batch 2: BGC[N9]–BGC[N15]
  Priority 2 — Edge BGCs Arch B, WL ≥ 7: BGC[N9]–BGC[N12]
  Priority 2 — Split-pathway unit: BGC[N13]+BGC[N14]+BGC[N15]

Batch 3+: BGC[N16]–BGC[N61]
  Priority 3–6 — Remaining Edge/FC BGCs sorted by WL

Proceeding to Batch 1 now.
```

### Priority ordering for batch assignment

Within each tier, BGCs are sorted by Wet-Lab (WL) score descending.

**Priority 1 — Always Batch 1:**
- All Interior BGCs with WL ≥ 10
- Any BGC (any edge status) with a §45 Tier 1 resistance gene confirmed within BGC coordinates
- Any BGC with a T43-ENE trigger (enediyne class — cytotoxic; self-protection must be confirmed before isolation proceeds)
- Any BGC with a T43-NUC trigger (peptidyl-nucleoside chitin synthase inhibitor class)

**Priority 2 — Batch 1 if space remains; otherwise Batch 2:**
- Remaining Interior BGCs, sorted by WL descending
- Edge BGCs with Architecture Confidence B and WL ≥ 7, sorted by WL descending
- Any BGC with a §43 trigger (T43-HAL, T43-PHO, T43-AMC affirmative)
- Any BGC with LMPKS rescue grade A or T
- Split-pathway units (BGCs sharing a pathway candidate) are scheduled as a unit in the same batch

**Priority 3 — Batch 2 or later:**
- Edge BGCs with Arch B and WL < 7
- Edge BGCs with Arch C, sorted by WL descending

**Priority 4 — Final batch:**
- All FC/Edge BGCs with Arch D or E
- All BGCs assigned LOW priority or Deprioritized in the WL matrix

### Note on fragmented strains

Poor and Very Poor assembly strains often have many Edge and FC BGCs that individually appear low-priority. However, any set of BGCs that form a cross-contig split-pathway candidate (identified in §30.3 and §42) should be scheduled in the same batch, because the gene-by-gene pass on each fragment is needed to reconstruct the pathway architecture. Do not separate split-pathway units across batches.

### Session continuation format

At the start of any session continuing a prior batch, the CDSW startup check (§1) must explicitly state the following before any other work:

```text
Continuing [Strain ID] — Batch [X] of approximately [Y].
Prior session(s) completed: BGC[list] (full §1–§8 Mode B).
This session: BGC[list].
Project Memory Snapshot loaded: [Strain ID]_Project_Memory_Snapshot_[date].json
Proceeding to BGC[first BGC of this batch].
```

Load the Project Memory Snapshot before resuming. Do not re-run assembly statistics, KCB sweep, TFBS extraction, or hallucination-trap audit unless new data has been uploaded since the prior session. Those outputs carry forward.

### Batch session end format

At the end of every batch session, produce a Batch Session Summary before presenting files:

```text
Batch [X] complete.
BGCs completed this session (full §1–§8 Mode B): BGC[list]
BGCs deferred to Batch [X+1]: BGC[list]

Revised plan:
  Batch [X+1]: BGC[list] — estimated [1] session
  Batch [X+2]: BGC[list] — estimated [1] session

Files generated this session:
  [list]

Project Memory Snapshot updated.

Primary next step: Continue with Batch [X+1] for [Strain ID].
```

For batch sessions, the primary CDSW next-step path is always "Continue with Batch [X+1]." The other 2–3 optional paths (Verified Literature Deep Dive, CCSM, figures, etc.) are offered after the primary path.

---

## SECTION 1 — Session Startup Checklist

1. **Recover context.** Search conversation, uploaded files, prior prompt-library documents, and memory.

1b. **Record provenance + confirm bioactivity default (source-independent).** If a host/source/isolation description is supplied, record it as caveated provenance and may optionally note the Ecological Source Category lens (per the SOURCE-INDEPENDENCE OVERRIDE in Global Analytical Defaults) — never as a gate or functional claim. Apply the `default-assumed MRSA and Candida extract-level inhibition` bioactivity status regardless of source, and carry it through all required propagation points. Unknown / no source NEVER blocks or defers analysis — state the source-independent default framing and proceed immediately. Only ask a clarifying question if uncertainty meets the Pre-Analysis materiality threshold (max 3, single block, "use defaults / go ahead" escape).

1c. **Run Metadata Conflict Audit.** Compare current-session strain metadata against uploaded files, master tables, prior reports, project-memory snapshots, reference implementation rows, and model memory. If host/source, habitat category, taxonomy, bioactivity, assembly quality, or prior BGC highlights conflict, treat current-session user confirmation as highest priority unless the user says otherwise; log the conflict; mark affected ecology, CCSM, cross-habitat, and manuscript-facing claims as `metadata-sensitive`; and do not reuse prior habitat-specific claims until reconciled.

1d. **Check for active Batch Plan.** Search the Project Memory Snapshot and any prior session outputs for an active Batch Plan for this strain. If one exists, state: "Active Batch Plan found — Batch [X] of [Y]. Prior session completed: BGC[list]. This session: BGC[list]. Proceeding." If no Batch Plan exists and the strain has more than 15 BGCs, announce a new Batch Plan before starting Mode B work.

1f. **Assign and lock canonical BGC IDs.** Number BGCs in antiSMASH JSON FASTA-input
order (the order records appear in the JSON, which follows the FASTA submission
order and does not change between sessions on the same assembly). Assign each BGC
the stable sequential number BGC01, BGC02, ... BGC[N] based on this ordering.

In every output — tables, Mode B headers, Triage Board rows, WL matrix entries,
ecological synthesis matrices, file names, and cross-session references — display
each BGC as the atomic paired identifier:

```text
BGC[N] (CONTIG_ACCESSION·rYYY)
```

where CONTIG_ACCESSION is the contig/scaffold identifier and rYYY is the antiSMASH
region number (r001, r002, etc.). This pairing is invariant for the lifetime of the
project. BGC numbers must not be reassigned between sessions (e.g., by resorting
by contig length, corrected count, or WL score).

Record in the audit log: "Canonical BGC IDs: assigned BGC01-BGC[N] in JSON
FASTA-input order; contig·region paired in every output."


2. **Load Project Memory Snapshot** (`[Strain ID]_Project_Memory_Snapshot_YYYY-MM-DD.json`) if available for the strain — this is the fastest route to prior session context and should be checked before the master JSON.
3. **Load master JSON** if working project-wide.
4. **Load strain tables** if updating bioactivity, taxonomy, or host metadata.
5. **Load antiSMASH ZIP** if performing strain-level analysis. When loading the ZIP, verify whether GBK region files are present (files named `*.region001.gbk`, `*.region002.gbk`, etc. inside the strain subfolder). These are the fallback source for TTA/bldA gating and HGT transposase scanning when JSON modules are incomplete. Note their presence or absence explicitly in the context acknowledgement.
6. **Load manuscript** if editing or rewriting manuscript text.
7. **Acknowledge context.** State what has been loaded, what is missing, and what the session will cover.
8. **Confirm source-of-truth order.**
9. **Offer 3–10 next-step paths** unless the user already gave a precise task.

---

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
| antiSMASH `[Strain ID].zip` | Strain-specific antiSMASH output | v7.9 strain analysis |
| `[Strain ID]_Project_Memory_Snapshot_YYYY-MM-DD.json` | Compact prior-session summary | Fast context recovery |

### Strain set accounting

Define your strain set composition at session start: total n, counts per [Habitat] category, and any special subsets. State this explicitly in the context acknowledgement.

*Reference project example:* [Habitat 1] n=20, [Habitat 2] n=6, [Habitat 3] n=10, [Habitat 4] n=1, Total n=37.

---

## SECTION 3 — antiSMASH ZIP / JSON Parsing Pipeline

### Primary rule

Use the antiSMASH JSON as the primary data source. Use GBK files if the JSON is absent or incomplete. Use KCB text files for the KCB sweep when present.

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
bgc_frac = bgc_length / contig_length
if bgc_frac >= 0.95:          edge_status = 'Full-contig / FC'
elif left_gap < 5000 or right_gap < 5000:  edge_status = 'Edge'
else:                         edge_status = 'Interior'
```

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

**Canonical ID note (v8.0.3):** BGC numbers follow antiSMASH JSON FASTA-input order. Every BGC is displayed as `BGC[N] (contig·regionYYY)`, and the paired identifier must be carried into every table, Mode B header, Triage Board row, ecological matrix row, file name, and cross-session reference.


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
| No hit | No MIBiG match |

### Fragmentation checks

Flag likely fragmentation artefacts:
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

| KCB hits | Cumulative score | Interpretation |
|---:|---:|---|
| 0 | 0 | Genuinely novel at protein-homology level |
| 1–5 | <500 | Weak match; treat as novel or divergent |
| 1–5 | 500–1500 | Moderate match; likely same class, possible novel variant |
| 10–50 | >1500 | Strong match; compound class well anchored |
| 50 max | >3000 | Full match; most genes align to reference |

### Cross-hit patterns to flag

| Pattern | Interpretation |
|---|---|
| Saccharide BGC → macrolide/glycopeptide KCB hit | Deoxysugar fragment from larger split cluster |
| High cumulative score + 2–3 protein hits | Assembly truncation likely |
| Two BGCs with identical top KCB compound | Possible split cluster — apply Section 30.3 cross-BGC gate |
| KCB class does not match antiSMASH product label | Hallucination-Trap trigger — apply Section 34 |

**LMPKS escalation (v7.5.1):** When KCB cumulative score is <1,500 (including zero) for any T1PKS BGC, this is an automatic trigger for Section 42 (LMPKS Rescue Workflow). Note the escalation in the KCB sweep table with the annotation "→ LMPKS §42 trigger 1".

### RiQ and KCB are orthogonal

Report both. High RiQ + zero KCB = conserved architecture, divergent proteins — high discovery value.

### Outputs

1. PDF: `[Strain ID]_KCB_Sweep_AllBGCs_YYYY-MM-DD.pdf`
2. Interactive React JSX: `[Strain ID]_KCB_Triage_YYYY-MM-DD.jsx`

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
| Ornithine-selective A-domain (by Stachelhaus code comparison to HslO/HslI from *Lysobacter enzymogenes* ATCC 29,214 or equivalent characterized HSAF synthetase) + iterative PKS-NRPS single-module architecture (single KS reused across extension cycles, detectable as one KS with multiple downstream ACP domains or anomalously high KS:ACP ratio in one ORF) | **HSAF / polycyclic tetramate macrolactam (PTM) class** (HSAF, 10-epi-HSAF, militarinone, frontalin-type). Sphingolipid (ceramide) synthase inhibitor — specific, well-characterized anti-Candida mechanism (CaCsg1/Lag1 target); award §33.3 Candida-specific mechanistic link (+2 WL) when Candida bioactivity is confirmed or default-assumed. Also active against filamentous fungal pathogens (*Botrytis*, *Fusarium*). Route to §37 HSAF/PTM row. Note: tetramate ring is acid-labile at pH <4 — do NOT use strongly acidic extraction conditions. |
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

**Fermentation Card deliverable:** when a strain reaches Layer C, translate the TFBS + RiQ + bldA outputs into a one-page Fermentation Card — priority BGC ranking (★), induction conditions ranked by BGC coverage, extraction by compound class, dereplication verdicts, solid-media/bldA-T4 notes. Format and the full regulator→induction lookup: `examples/fermentation_card_exemplar.md`.

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

## SECTION 13 — Neighbourhood Comparison and Medium-BGC Rescue

For each MEDIUM BGC: count biosynthetic genes, identify divergent domains (bitscore ≥150), and upgrade to HIGH when warranted.

**Divergence classes:** EXTENDED / SUBSTITUTED / NOVEL CONTEXT / FRAGMENTED

**Automatic upgrade triggers:** Phytoene synthase in non-terpene context; MshC; F420 enzymes (CofG/CofH/FbiB); DUF1702 ×2; HypF+HypE; CobN cobaltochelatase.

**LMPKS split-pathway cross-contig detection (v7.5.1):** For large modular PKS clusters fragmented across multiple contigs, use Section 42.7 (Split-Pathway Rescue) instead. The cross-contig module accumulation protocol in Section 42.6 supersedes the neighbourhood comparison for T1PKS BGCs with docking domains on different nodes.

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

### 15.3 Mode B Report for every BGC

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

All PDF outputs use the Sapote style module (`sapote_pdf_styles.py`). Upload or create this file at session start when generating PDFs. All PDF-generating scripts import it as the first styling step. Narrative sections use text-flow functions (`sapote_body`, `sapote_fix`, `sapote_gap`, `sapote_section`). Structured data uses `sapote_table()`. Do not redefine styles from scratch in individual scripts.

Every compiled PDF must include a visible metadata/defaults block in the opening pages with:
- Workflow version
- Strain ID
- Taxonomy status
- Host/source status and ecological category
- Bioactivity status (`default-assumed`, `user-confirmed`, `file-confirmed`, `not tested`, or `not available`)
- Assembly tier
- BGC count and corrected BGC count
- Date of execution

When MRSA + Candida are default-assumed, include this exact note in the opening metadata/defaults block and in the audit log:

```text
MRSA and Candida inhibition are default-assumed at extract level because no strain-specific assay data were supplied. This default supports discovery triage only and does not assign activity to any BGC.
```

PDF layout requirements:
- Every major deliverable starts on a new page with a section banner.
- Long tables may split across pages, but headers must repeat.
- Dense BGC tables must use wrapped text, not clipped text.
- Every Mode B report begins with a compact one-page overview block before gene-by-gene detail.
- Use consistent callout boxes for `Default-assumed`, `Missing`, `Caution`, `High priority`, and `Deferred` notes.
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

Translate BGC-level data into testable ecological hypotheses about how predicted chemistry maps onto host biology, ecology, and pathology. Every hypothesis must cite specific BGC evidence (node, locus tag, domain, bitscore, TFBS score). All ecological interpretations are labelled as hypotheses requiring experimental validation.

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

If evidence is absent, report a null result rather than inventing an ecological story.

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

### 17.6 Step 4 — Host Disease Defence Matching

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

Required columns: BGC # / node, Edge status, **Architecture Confidence**, Product class, KCB/RiQ comparator, Diagnostic domains, TFBS signals, bldA tier, Substrate coupling, Disease-defence match, HGT/coverage flag, Ecological hypothesis, Testable prediction, Confidence, Claim-safety note.

When the MULTI-SIDEROPHORE CAPACITY flag is raised, add `Iron-acquisition system (multi-siderophore)` to the Ecological hypothesis column for each siderophore BGC row.

### 17.8B Ecological Synthesis Scoring Rubric

Host-relevant substrate coupling +1 | Cognate TFBS +1 | Bioactivity match +1 | Interior BGC +1 | Strong KCB/RiQ comparator +1 | Zero KCB + strong domains +1 discovery bonus | Edge/FC truncation −1 | No host/substrate metadata −1

Score ≥4: High-priority | 2–3: Plausible | 0–1: Low-confidence | <0: Insufficient evidence

### 17.9 Ecological Synthesis PDF

Required sections §1–§12 (host context, TFBS table, polysaccharide coupling, bldA mapping, disease defence, novel signals, ecological matrix, hypotheses, integrated model, testable predictions, claim-safety statement, missing-data register).

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
  Analogy: Phenazine BGC → Escovopsis defence in attine context:
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

### BGC Analysis Workbook sheets (v7.9 — 20 sheets)

1. BGC_Inventory (includes Arch Confidence column)
2. KCB_Sweep
3. Domain_Hits
4. TFBS_Induction
5. TTA_bldA
6. HGT_Coverage
7. Dereplication
8. Ecological_Matrix
9. **Evidence_Traceability**
10. **WetLab_Decision_Matrix**
11. **Hallucination_Trap_Audit**
12. **CrossStrain_Family_Seeds**
13. **Metabolomics_Readiness**
14. **Missingness_Register**
15. **Figure_Suggestions**
16. Audit_Log
17. **LMPKS_KS_Inventory** (Section 42 — genome-wide mod_KS / hyb_KS / tra_KS inventory and fragment accumulation evidence)
18. **CrypticClass_Triggers** (Section 43 — which T43 triggers fired, markers, bitscores, loci, co-location, routing, rule-outs)
19. **Chitin_Glycan_Defense** (Section 44 — genome-wide GH18/GH19/AA10/CBM/DasR-regulon capacity table)
20. **ResistanceGene_Confirmation** (Section 45 — per-BGC resistance marker scan: gene type, locus tag, bitscore, distance from BGC boundary, tier, class concordance, HGT guard outcome, Architecture Confidence effect, WL adjustment)

---

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

**Trigger:** `Build glossary entries from these documents.`

Entry structure: Term, Category, Plain-English definition, Scientific definition, Why it matters, Related strains/BGCs, Evidence type, Claim-safety note, VLD citations, URLs/DOIs/PMIDs.


---

## SECTION 21 — Verified Literature Deep Dive v2.0

### Core purpose

Verified Literature Deep Dive is the accuracy-first scientific bibliography and synthesis workflow. It is designed for publication-ready work where citation accuracy, quantitative extraction, strain anchoring, and conflict detection matter more than speed or breadth.

### Best for

30–75 papers. High-stakes literature synthesis. Publication-ready manuscript support. Compound classes where the evidence base includes mechanism revisions, stereochemical uncertainty, contradictory MIC values, or conflicting biosynthetic interpretations.

### Triggers

```text
Use Verified Literature Deep Dive.
Use Verified Literature Deep Dive.
Run Verified Literature Deep Dive on [compound/class/BGC/domain/paper set].
Run Verified Literature Deep Dive bibliography verification for [list].
Build a Verified Literature Deep Dive bibliography for [strain/BGC/compound family].
```

### Context anchor — required before paper summaries

Before summarizing any paper, confirm: Strain ID, BGC number(s)/node/edge status, Compound class prediction, Key locus tags and diagnostic domain hits, Strain-level bioactivity context, Why this paper is relevant to the project question. Every summary must explicitly connect to a specific BGC, locus tag, domain hit, compound class, strain, or project question.

### Source and metadata verification standard

Verify each citation against: PubMed, PubMed Central, Crossref, DOI.org, Journal or publisher page, Government/university/primary database pages. For every verified record, include: Full author list, Year, Full title, Journal/source, Volume/issue/pages/article number, DOI URL, PMID, PMCID, Publisher/source URL, Relevant accession/strain/compound/host/database identifiers.

Do not guess, autocomplete, or "clean up" citation metadata from memory. Unverifiable citations go to a Partial or Unverified Leads section.

### Evidence type hierarchy

| Evidence type | Definition | How to use in project claims |
|---|---|---|
| Direct biochemical | Enzyme, compound, or BGC experimentally characterized | Strongest support for mechanism or biosynthetic function |
| Heterologous expression | BGC expressed in non-native host | Strong support for BGC-product relationship |
| In vitro enzyme | Enzyme activity characterized outside native organism | Strong support for enzyme function |
| Direct isolation/structural | Compound isolated and structurally characterized | Strong support for compound chemistry |
| Genomic prediction | BGC identified from sequence/domain evidence | Bioinformatic prediction only; no production claim |
| Structural analogy | Chemistry inferred by similarity | Useful hypothesis; not proof |
| Bioassay-only | Strain/extract/fraction activity observed | Attribute to strain/extract/fraction, not a predicted compound |
| Ecological/epidemiological | Host, microbiome, disease, or habitat association | Use as ecological context, not proof of mutualism |
| Review/background | Secondary synthesis | Useful for orientation; not primary evidence |

### Relevance tiers

| Relevance tier | Definition |
|---|---|
| Direct | Characterizes the same compound class, BGC, enzyme family, or diagnostic domain |
| Structural | Characterizes a closely related compound or scaffold |
| Biosynthetic | Explains pathway logic, enzyme mechanism, or domain function |
| Ecological | Host, microbiome, disease, niche, substrate, or symbiosis context |
| Methods | Provides assay, fermentation, extraction, LC-MS, NMR, or dereplication methods |
| Background | General context only; use sparingly |

### Quantitative extraction requirements

Extract: MIC values, IC50/EC50 values, Yield (mg/L, mg/kg), MW/exact mass (HRMS preferred), UV/Vis λmax, NMR details, logP/polarity descriptors, in vivo data, and **negative results** (organisms with no activity, failed expression, absent products).

### 9-step workflow

1. **Metadata verification** — Search PubMed, DOI.org, Crossref, PMC, and publisher pages.
2. **Full-text retrieval** — Use PMC full text when available.
3. **Quantitative extraction** — Extract all quantitative data in structured rows.
4. **Evidence type assignment** — Assign highest applicable evidence type.
5. **Relevance tier assignment** — Assign one primary relevance tier.
6. **Write summary** — 150–300 words: (a) what the paper does; (b) key quantitative/mechanistic findings; (c) explicit connection to the project question; (d) caveats.
7. **Conflict flag** — State whether any finding conflicts with another paper.
8. **Zotero cleanup flag** — Flag duplicates, incomplete metadata, missing DOI/PMID/PMCID.
9. **Final citation formatting** — PNAS/PLOS ONE-compatible style with full author lists, DOI URLs, PMID/PMCID.

### Required summary structure

1. One sentence describing what the paper experimentally or analytically establishes.
2. One to three quantitative or mechanistic facts, with exact values when available.
3. One explicit project anchor (strain, BGC, locus tag, domain hit, compound class, or manuscript question).
4. One caveat or claim-safety statement.
5. One conflict note or "No conflict detected."

### Output workbook

| Sheet | Contents |
|---|---|
| Verified Bibliography | Full citations, DOI URL, PMID, PMCID, evidence type, relevance tier, confidence status |
| Summaries | One row per paper; 150–300 word anchored summary; key caveats; conflict flag |
| Quantitative Data | One row per data point: MIC, yield, MW, λmax, HRMS, logP, assay condition, organism, method, citation |
| Zotero Cleanup | Records requiring merge, correction, DOI/PMID lookup, duplicate handling |
| Summary Stats | Counts by evidence type, relevance tier, compound class, organism, conflict status |
| Unverified Leads | Potentially relevant papers not yet verified |

### Quality standard

Fewer well-anchored, verified citations are better than many generic or uncertain citations. When evidence is weak, say so clearly.

---

## SECTION 22 — Rapid Literature Deep Dive v2.0

### Core purpose

Rapid Literature Deep Dive is a rapid scoping bibliography workflow. It establishes what the field knows, what it does not know, and whether a deeper Verified Literature Deep Dive run is warranted. Its primary deliverable is the **Gaps Analysis**.

### Best for

10–30 papers. New compound classes or unfamiliar BGC families. Rapid orientation before committing to a full Verified Literature Deep Dive run.

### Triggers

```text
Use Rapid Literature Deep Dive.
Use Rapid Literature Deep Dive for [topic].
Run Rapid Literature Deep Dive on [compound class/BGC family/project question].
```

### Context anchor — required

Before summarizing, confirm: Strain ID (if relevant), BGC number or compound class (if relevant), Key locus tags or domain hits (if available), The project question Rapid Literature Deep Dive is answering.

### 6-step workflow

1. **Abstract/source verification** — Confirm author list, title, journal, year, volume/issue/pages, DOI, PMID, and source URL where available.
2. **Evidence type and relevance tier** — Assign both using the Verified Literature Deep Dive definitions.
3. **Extract key numbers** — 3–5 quantitative or highly actionable facts per paper. If none available, write "No quantitative data — mechanistic/review only."
4. **Write brief summary** — 60–100 words: (a) what the paper establishes; (b) the single most relevant quantitative/mechanistic finding; (c) a project-anchored sentence.
5. **Format citation** — PNAS/PLOS ONE-compatible style where metadata is verified.
6. **Write Gaps Analysis** — After processing all papers.

### Gaps Analysis — primary deliverable

1. **What the literature has established** — 2–4 bullets with citations.
2. **What remains unresolved** — 2–4 bullets naming contested mechanisms, missing steps, absent compound isolation, inconsistent results.
3. **What a Verified Literature Deep Dive run should target** — specific search terms, compound classes, enzyme names, domain IDs.
4. **Whether Verified Literature Deep Dive is warranted** — yes/no with one-sentence rationale.
5. **Immediate project implications** — 2–4 bullets.

### Output workbook

| Sheet | Contents |
|---|---|
| Bibliography | Citation, DOI URL, PMID/PMCID if available, evidence type, relevance tier, verification status |
| Summaries | 60–100 word summaries, 3–5 key numbers, project anchor, obvious conflict note |
| Gaps Analysis | Established findings, unresolved questions, VLD targets, escalation recommendation, project implications |

### Escalate to Verified Literature Deep Dive if

- The gaps section identifies more than two unresolved conflicts.
- The compound class has contested stereochemistry, revised mechanisms, or taxonomic confusion.
- More than five papers have direct biochemical, heterologous expression, or direct isolation evidence.
- The output will be cited directly in a manuscript.

---

## SECTION 23 — Mode Selection Decision Tree

```
10–30 papers, new compound class, rapid orientation?
└─ Rapid Literature Deep Dive v2.0 → Gaps Analysis → escalate if needed

30–75 papers, specific BGC/compound class, manuscript support?
└─ BERT MODE v2.0 → verified bibliography + anchored summaries

75+ papers or cross-project integration?
└─ Split into multiple VLD batches by relevance tier

Need strain antiSMASH analysis?
└─ v7.9 strain analysis (Full Analysis Mode unless compact explicitly requested)

Need cross-strain or cross-habitat comparison?
└─ CCSM v1.1 (Section 41) → Phase 1 Normalize → Phase 2 Within-habitat → Phase 3 Cross-habitat
```

### Rapid Literature Deep Dive vs Verified Literature Deep Dive comparison

| Aspect | Rapid Literature Deep Dive v2.0 | Verified Literature Deep Dive v2.0 |
|---|---|---|
| Primary purpose | Rapid scoping and gap finding | Publication-ready verified synthesis |
| Typical paper count | 10–30 | 30–75 |
| Full text | Optional, useful when available | Required/preferred when available |
| Metadata verification | Basic but careful | Full verification against PubMed/PMC/DOI/Crossref/publisher |
| Summary length | 60–100 words | 150–300 words |
| Quantitative data | 3–5 key numbers per paper | Exhaustive structured extraction |
| Primary deliverable | Gaps Analysis | Verified bibliography + summaries + quantitative data |
| Use in manuscript | Orientation only unless upgraded | Suitable when verified |
| Escalation role | Decides whether VLD is needed | Produces citable synthesis |

### Extended Verified Literature Deep Dive note

Use when the task exceeds a single compound class or one 30–75-paper batch, especially for cross-habitat literature integration, large compound-family glossaries, multi-strain BGC-to-literature workbooks, or manuscript supplement tables with hundreds of references.

---

## SECTION 24 — Cross-Strain Comparison Module

**Trigger:** `Run cross-strain comparison: [Strain A] vs [Strain B] for [compound class or domain].`

Output: architecture table, shared vs divergent enzyme inventory, RiQ/KCB comparison, domain overlap, HGT/coverage notes, verdict, manuscript-safe hypothesis, isolation recommendation.

For systematic multi-strain comparisons, use CCSM (Section 41) instead of this pairwise module.

Filename: `CrossStrain_[StrainA]-[StrainB]_[Class]_YYYY-MM-DD.pdf`

---

## SECTION 25 — Key Scientific Findings to Preserve

> *Named-strain findings from the reference project (actinomycete collection) are published in the companion data paper and Zenodo deposit. This section is intentionally left as a placeholder in the public software release. New users: populate this section with your own project findings as they accumulate.*

**Project Bioactivity Default:** All strains are assumed to show MRSA + *Candida* inhibition at extract level until contradicted by data. This default does NOT attribute activity to specific BGCs without fractionation. Claim-safety language is required throughout.

**hglE-KS-PREV-001 status:** hglE-KS confirmed as a prevalent, habitat-non-specific domain across all habitat classes in the reference collection. BRYO-HGT-001 designation retired 2026-05-29. Structural novelty (zero KCB across all instances) preserved as the primary analytical value. See §41.8 for the formal record.

---

## SECTION 26 — Reference Implementations

> *Completed analyses from the reference project (actinomycete collection) are published in the companion data paper and Zenodo deposit. This section is intentionally left as a placeholder in the public software release to avoid disclosing unpublished strain-level findings ahead of the associated manuscript. New users: populate this section with your own completed analyses as they accumulate.*

---

## SECTION 27 — Output Audit Log Template

```markdown
## Audit Log
**Analysis date:** YYYY-MM-DD | **Workflow version:** v7.9.1
**Task:** [strain analysis / figure rebuild / manuscript update / glossary / bibliography / CCSM comparison]

### Input files used
- [filename] — [role]

### Core calculations
- Corrected BGC count: [formula]
- RiQ source: [RegionToRegion_RiQ / other]
- KCB source: [knownclusterblast text / JSON / absent]
- TTA/bldA source: [JSON TTA module / GBK files / FASTA / T? — reason]
- HGT/coverage: [calculated / not available / reason]
- CCSM: [Phase run / not applicable / evidence grades used]

### Corrections or overrides
| Field | Original | Corrected | Reason | Source |

### Missing or unresolved data
### QA gate outcomes (Sections 30 + 31.13)
### Hallucination-trap outcomes (Section 34)
### Architecture confidence summary (Section 31)
### Resistance gene confirmation summary (Section 45)
### Wet-lab decision matrix top scores (Section 33)
### Files generated
```

---

### v8.0.3 Canonical BGC ID audit field

- Canonical BGC ID scheme used: [JSON order / other — state].

## SECTION 28 — File Naming Conventions

**Canonical BGC ID filename note (v8.0.3):** BGC number in filenames always follows canonical scheme.


| File type | Format |
|---|---|
| Layperson's Guide | `[Strain ID]_Laypersons_Guide_YYYY-MM-DD.pdf` |
| Deep Dive Synopsis | `[Strain ID]_Deep_Dive_Synopsis_YYYY-MM-DD.pdf` |
| Mode B report | `[Strain ID]_NODE_[N]_BGC[N]_Mode_B_[Class]_YYYY-MM-DD.pdf` |
| KCB sweep table | `[Strain ID]_KCB_Sweep_AllBGCs_YYYY-MM-DD.pdf` |
| KCB triage dashboard | `[Strain ID]_KCB_Triage_YYYY-MM-DD.jsx` |
| Chapter | `[Strain ID]_NODE_[range]_Chapter_YYYY-MM-DD.pdf` |
| Fermentation card | `[Strain ID]_Fermentation_Card_YYYY-MM-DD.pdf` |
| Cross-strain comparison | `CrossStrain_[StrainA]-[StrainB]_[Class]_YYYY-MM-DD.pdf` |
| Compilation | `[Strain ID]_Complete_Analysis_Compilation_YYYY-MM-DD.pdf` |
| Ecological synthesis (full) | `[Strain ID]_Ecological_Synthesis_YYYY-MM-DD.pdf` |
| Ecological synthesis (fast) | `[Strain ID]_Ecological_Synthesis_Fast_YYYY-MM-DD.pdf` |
| BGC workbook | `[Strain ID]_BGC_Analysis_Workbook_YYYY-MM-DD.xlsx` |
| v7.4 Addendum PDF | `[Strain ID]_v7.4_Addendum_YYYY-MM-DD.pdf` |
| Project Memory Snapshot | `[Strain ID]_Project_Memory_Snapshot_YYYY-MM-DD.json` + `.md` |
| White paper | `Sapote_Workflow_WhitePaper_v7_YYYY-MM-DD.pdf` |
| Prompt library | `Sapote_Actinomycete_Workflow_v7_7_YYYY-MM-DD.md` |
| Package ZIP | `[Strain ID]_v7_Package_YYYY-MM-DD.zip` |
| CCSM Gap Register | `CCSM_GapRegister_[HabitatOrSet]_YYYY-MM-DD.pdf` |
| CCSM UCS table | `CCSM_UCS_[HabitatOrSet]_YYYY-MM-DD.xlsx` |
| CCSM within-habitat report | `CCSM_WithinHabitat_[HabitatClass]_YYYY-MM-DD.pdf` |
| CCSM cross-habitat report | `CCSM_CrossHabitat_[A]-vs-[B]_YYYY-MM-DD.pdf` |
| CCSM dashboard | `CCSM_Dashboard_[Set]_YYYY-MM-DD.jsx` |
| TFBS verification | `[TFBS]_CrossSet_Verification_YYYY-MM-DD.pdf` |
| LMPKS Rescue Report | `[Strain ID]_LMPKS_Rescue_Report_YYYY-MM-DD.pdf` |
| FLBR NRPS / Hybrid Rescue Report | `[Strain ID]_FLBR_NRPS_Rescue_Report_YYYY-MM-DD.pdf` when PKS rescue is null but NRPS/hybrid FLBR fires |
| CCTT Trigger Report | `[Strain ID]_CCTT_Trigger_Report_YYYY-MM-DD.pdf` |
| Resistance Gene Confirmation Report | `[Strain ID]_ResistanceGene_Confirmation_YYYY-MM-DD.pdf` |

---

## SECTION 29 — CDSW Protocol Summary

At every session start: recover context → **load Project Memory Snapshot if available** → load source files → state source-of-truth order → identify missing files → proceed or offer 3–10 distinct paths.

At every task completion: provide files → include audit log → state unresolved data → offer 3–10 genuinely distinct next paths.

**Suggested next paths (after strain analysis):**
- Path A: Upload new antiSMASH ZIPs and update master JSON
- Path B: Build or rebuild cross-habitat figures
- Path C: Write Results/Discussion manuscript sections
- Path D: Run Verified Literature Deep Dive bibliography for priority BGC classes
- Path E: Build layperson glossary and fermentation cards
- Path F: Run CCSM Phase 2 (within-habitat) or Phase 3 (cross-habitat) using Section 41

**For batch sessions:** The primary next-step path is always "Continue with Batch [X+1] for [Strain ID] — BGC[list]." This path is listed first. The other 2–3 optional paths (Verified Literature Deep Dive, CCSM, figures, manuscript work) are offered after the primary batch continuation path. The batch plan takes precedence over other project work until all BGCs for the current strain have received full §1–§8 Mode B treatment.

CDSW modification command: `CDSW modification: [instruction]`

---

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
- Where §4 draws a mechanistic analogy to a characterised compound, BGC, or
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

- BGC carries a Section 34 verdict of likely tailoring/deoxysugar arm, split-pathway arm, or fragmentation artefact → maximum MEDIUM.

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

All PDF outputs use the Sapote style module (`sapote_pdf_styles.py`). Upload or create this file at session start when generating PDFs. All PDF-generating scripts import it as the first styling step. Narrative sections use text-flow functions (`sapote_body`, `sapote_fix`, `sapote_gap`, `sapote_section`). Structured data uses `sapote_table()`. Do not redefine styles from scratch in individual scripts.

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

**Visible default/status boxes are required** near the beginning of every compiled master PDF. Include source/taxonomy/bioactivity status and state whether bioactivity is `default-assumed`, `user-confirmed`, `file-confirmed`, `not tested`, or `not available`.

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


### 30.10 PDF Style and Bioactivity-Default Gate (v7.9)

Before finalising any compiled master PDF, verify:

- [ ] `sapote_pdf_styles.py` was imported or its equivalent style functions were used consistently
- [ ] No PDF-generating script redefined the full style system independently
- [ ] Narrative text used Sapote text-flow helpers or equivalent wrapped Paragraph flows
- [ ] Structured tables used `sapote_table()` or a compatible wrapped-table helper
- [ ] Compiled PDF includes bookmarks/outlines for all major sections and every Mode B report
- [ ] Opening metadata/defaults block states source, taxonomy, ecological category, and bioactivity status
- [ ] MRSA + Candida default is shown as `default-assumed` when no assay data were supplied
- [ ] Missingness Register does not incorrectly list default-assumed MRSA/Candida as missing
- [ ] Audit log records whether bioactivity was default-assumed, user-confirmed, file-confirmed, not tested, or not available
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
- A BGC flagged as a **fragmentation artefact** (Section 4 fragmentation checks) cannot exceed **Grade D**.
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
Evidence Traceability — BGC [N]
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

- **HSAF / PTM** sphingolipid (ceramide) synthase inhibitor → Candida (CaCsg1/Lag1 ceramide synthase is the specific target; disrupts sphingolipid biosynthesis required for Candida virulence and membrane integrity; mechanistically distinct from azoles, echinocandins, and polyenes — award +2 WL when Candida bioactivity is confirmed or default-assumed)

> **Do NOT award the Candida-specific mechanistic link (+2 WL) for indolocarbazole BGCs** (rebeccamycin / staurosporine / AT2433 class). While Candida topoisomerase I (CaTop1) is a theoretical target, indolocarbazoles are characterized as antitumor and antibacterial agents, not dedicated antifungals. Topoisomerase I inhibition is not a specific antifungal mechanism in the clinical sense. If Candida activity is observed in fractions containing an indolocarbazole compound, attribute it to cytotoxicity (non-specific) rather than a dedicated antifungal mechanism, and cross-check for co-eluting compounds before assigning mechanistic causality.


**Phenazine class specificity note (attine context):** In the attine ant context (*Atta*/*Acromyrmex*/any attine genus), do NOT award the "BGC class specific mechanistic link" (+2 WL) bonus to phenazine BGCs on Escovopsis-defence grounds — phenazines are not the active anti-*Escovopsis* agents in the primary literature. Award only for direct anti-MRSA/broad-antibacterial support, and label any Escovopsis connection "class analogy only." Full precedent, evidence grades, and citations: see the §17.10 ecological precedent table (Attine / *Escovopsis* row).

### 33.4 Decision Categories

| Score | Category | Recommended action |
|---:|---|---|
| ≥10 | Immediate follow-up | Culture induction + LC-MS + bioassay-guided fractionation |
| 7–9 | Strong follow-up | Targeted culture/HRMS or sequencing clarification first |
| 4–6 | Conditional follow-up | Retain; revisit after long-read assembly or metabolomics |
| 1–3 | Inventory only | Do not prioritize unless cross-strain evidence emerges |
| ≤0 | Deprioritized | Keep for completeness; no immediate wet-lab action |

### 33.5 Four Independent Action Scores

For each BGC, output four action scores:

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

The domain/marker classifications in this audit, and every class-level call downstream, MUST be made
from the per-locus HMM hit list in `[StrainID]_AntiSMASH_Evidence_Parse.json` → `gbk_pfam_hits`. Each
hit carries model name, E-value, bitscore, and a `tier1_diagnostic` flag. This file is antiSMASH's
pre-computed HMMER output and is the **primary, sufficient evidence channel for class-level calls** —
no external HMMER re-run is required to reach class level.

The `*_2_inventory.csv` and `*_4_triage_board.csv` are derived *summaries*: they hold the antiSMASH
product label, KCB, and scores, but **not** the per-locus domain hit list. A class call (or a doubt
about one) made from the CSVs alone is unsupported, because the diagnostic core of a BGC frequently
sits at a locus the summaries never surface. Standing failure mode to avoid (observed repeatedly): a
ranthipeptide/RiPP call flagged "maturase unconfirmed" when the radical-SAM + SPASM maturase and the
RiPP recognition element were present in `gbk_pfam_hits` all along, simply unread.

Rules:
1. Before classifying a BGC or assigning/doubting its class, read its region's full `gbk_pfam_hits`
   entry, including all `tier1_diagnostic=true` hits.
2. A claim is `EVIDENCE_PENDING` only if the evidence JSON's HMM hits genuinely do not resolve it —
   never merely because a CSV row was terse or a BLASTp subset missed the core protein.
3. `custom_marker_hmmer = NEEDS_HMMER_DOMTBLOUT` in `evidence_channels` means the *optional
   proteome-wide* `mamey_markers.hmm` scan is pending. It does NOT mean "no HMM evidence" — the
   antiSMASH HMM evidence in the evidence JSON is already present.

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
| BGC ID / Node / region |  |
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

**hglE-KS status update (2026-05-29):** hglE-KS-PREV-001 is now a **habitat-non-specific prevalent domain** confirmed in 8 strains/7 genera across all 3 habitats (Bryophyte, Attine, Hymenoptera). The ≥3-strain clustering threshold was exceeded; cross-strain comparison is complete; BRYO-HGT-001 designation retired. Structural novelty (zero KCB) remains the primary analytical value of this domain — it is not a habitat signal or HGT candidate. Do not add new hglE-KS seeds to a habitat-specific or HGT candidate register; add them to the hglE-KS-PREV-001 prevalence record and update the strain/genus count.


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
| Lanthipeptide/RiPP | ~800–3,500 Da | Positive likely | variable | SPE/C18, MeOH/water | ABC transporter co-localised in BGC (Tier 3 routing) |
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

**Polar compound caveat:** Standard C18 reversed-phase extraction and fractionation will underrepresent or lose highly polar and zwitterionic compounds including peptidyl nucleosides, siderophores, and charged NRP fragments. When a BGC predicts a polar product, explicitly flag in the Metabolomics_Readiness sheet that standard C18 crude extraction is insufficient, and recommend aqueous or ion-exchange primary fractionation before HRMS dereplication.
| Indolocarbazole (rebeccamycin / staurosporine / AT2433-A1 / loonamycin / arcyriarubin class) | ~390–650 Da (rebeccamycin: 602; AT2433-A1: ~590; staurosporine: 466; arcyriarubin A: 393) | ESI+ [M+H]+ likely; staurosporine ionizes well as [M+H]+ at m/z 467 | 320 nm primary (strong, conjugated indolocarbazole chromophore) + 360 nm secondary (diagnostic doublet); both bands should be confirmed together before assigning class by UV; note: crude extracts may show orange-brown coloration at high concentration | EtOAc pH 6–7; C18 semi-prep; MeOH/H2O + 0.1% FA gradient; protect from prolonged light exposure; ⚠ **CYTOTOXICITY CAUTION** — staurosporine-class kinase inhibitors are among the most cytotoxic natural products known; test HeLa/mammalian cytotox IC₅₀ BEFORE MRSA/Candida MIC; handle per standard cytotoxic-compound SOPs; do NOT scale up without toxicology pre-screen | No established Tier 1 resistance gene for indolocarbazoles as a class; self-resistance may involve drug efflux MFS/ABC transporter or modified Top1 — if found near BGC, note as Tier 3 routing signal (§45.5) |
| HSAF / PTM (polycyclic tetramate macrolactam; HSAF, 10-epi-HSAF, militarinone, frontalin class) | ~450–600 Da (HSAF: 531.31; 10-epi-HSAF: 531.31; militarinone A: ~450; frontalin-type: varies) | ESI+ [M+H]+; HSAF m/z 532 ([M+H]+) confirmed in multiple literature sources | 305 nm strong (conjugated tetramate chromophore) + 270 nm shoulder; yellow-brown coloration in concentrated crude extracts possible | EtOAc pH 6–7 (DO NOT use pH <4 — tetramate ring is acid-labile and will hydrolyze); C18 semi-prep; MeOH/H2O + 0.1% FA; reverse-phase at neutral pH is optimal | No Tier 1/2 resistance gene established for PTM class in actinomycetes; if present, a ceramide synthase (Lag1-family) paralogue with altered drug-binding residues may be detectable near BGC |
| Prodiginine (prodigiosin / cycloprodigiosin / streptorubin / metacycloprodigiosin class) | ~295–450 Da (prodigiosin: 323.44; cycloprodigiosin: 309.41; streptorubin B: ~450; undecylprodigiosin: 393) | ESI+ [M+H]+; prodigiosin [M+H]+ = 324 | 530 nm intense (magenta/red; this is a visual screen — prodiginines produce vivid red/magenta pigment on ISP2 plates, visible without any instrumentation); 485 nm shoulder; TLC detection by eye | **Visual plate inspection first** — red/magenta pigment on ISP2 plate at 7–14 days is a positive screen for prodiginine expression; EtOAc or acetone extraction; TLC under visible light (no UV required); C18 HPLC MeOH/H2O gradient; no special precautions needed | No characterized Tier 1/2 actinomycete resistance gene for prodiginines; H+/Cl- co-transport inhibition is the proposed membrane mechanism; also weak topoisomerase inhibition reported |
| Ansamycin (rifamycin / geldanamycin / herbimycin / ansatrienin / ansamitocin class) | ~530–900 Da (rifamycin SV: 697; geldanamycin: 560; herbimycin A: 578; ansamitocin P-3: 549; rifamycin B: 756) | ESI+ [M+H]+ or [M+Na]+; geldanamycin ionizes as [M+H]+ at m/z 561 | ~340 nm (rifamycin-type: naphthalenol chromophore; orange-red coloration in crude extract); ~310 nm (geldanamycin-type: benzoquinone/ansa chain; purple-brown coloration); colour visible in crude extracts provides preliminary identification handle | EtOAc / n-BuOH extraction; C18 semi-prep; MeOH/H2O gradient; geldanamycin benzoquinone is redox-active — protect from light and reducing agents; rifamycins are photostable | ArrA/Arr-type ADP-ribosyltransferase within 15 kb of ansamycin PKS fragments (Tier 2, §45.4; apply HGT guard per §45.4); for rifamycin class, mutant rpoB (RNA polymerase subunit with altered drug-binding pocket) may serve as an additional self-protection mechanism |
| Showdomycin (maleimide C-nucleoside) | ~175 Da (exact: C₅H₅NO₄ = 175.0269; [M+H]+ = 176.034) | ESI+ [M+H]+ 176; note: showdomycin is zwitterionic at physiological pH — verify ionization mode empirically; very small MW means it elutes at or near the void volume of standard C18 reversed-phase columns | ~260 nm (nucleoside base chromophore); maleimide carbonyl ~215 nm | ⚠ **Standard C18 reversed-phase is insufficient** — showdomycin will be lost in the void volume or early wash fractions; use aqueous extraction (50% MeOH/H₂O or water), followed by HILIC or graphitic carbon (Hypercarb-type) primary fractionation; ion exchange (SAX or SCX) as alternative primary fractionation before C18 desalting; MW is so small that MS fragmentation patterns are minimal — confirm by exact mass and UV | No characterized Tier 1 resistance gene; maleimide warhead reacts covalently with active-site Cys residues of MurA — producer self-protection may involve MurA paralogue with Cys→Asp/Ser substitution at the reactive position; flag absence of a modified MurA as a §38.2 missingness item for this class |
| Arylpolyene (APE; flexirubin-type) | ~350–700 Da (varies with chain length and aryl moiety) | APCI+ / ESI+ variable; often best detected by UV rather than MS | 420–450 nm strong primary handle. **Visual screen first:** yellow/orange colony pigment on plates is the cheapest first-pass production indicator, no instrumentation required. Also ~320 nm secondary absorption. | Non-polar extraction (EtOAc, acetone, or hexane); TLC under visible light (no UV lamp needed); LC-DAD 430 nm monitoring | — (no characterised Tier 1/2 resistance gene; arylpolyenes are pigments, not toxic to producer) |

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

### 40.1 Purpose

Every major strain run should generate a compact summary that can be reused in later conversations, master JSON updates, manuscript drafting, and prompt-library regeneration.

### 40.2 Required Files

For every full strain analysis, generate:

1. `[Strain ID]_Project_Memory_Snapshot_YYYY-MM-DD.json`
2. `[Strain ID]_Project_Memory_Snapshot_YYYY-MM-DD.md`

### 40.3 JSON Schema

```json
{
  "strain_id": "[Strain ID]",
  "workflow_version": "v7.9",
  "analysis_date": "YYYY-MM-DD",
  "taxonomy": {
    "genus": "[Genus]",
    "species": "not verified",
    "source": "user confirmation / strain table / antiSMASH filename"
  },
  "habitat": {
    "group": "[Habitat]",
    "source": "[Host]",
    "metadata_confidence": "user-confirmed"
  },
  "bioactivity": {
    "target_1": "active / not tested / not available",
    "target_2": "active / not tested / not available",
    "compound_linkage": "not established"
  },
  "assembly": {
    "size_bp": null,
    "contigs": null,
    "n50": null,
    "interior_bgc_percent": null,
    "quality": "Very Poor / Poor / Moderate / Good"
  },
  "bgc_counts": {
    "raw": null,
    "interior": null,
    "edge": null,
    "full_contig": null,
    "corrected": null
  },
  "top_bgc_targets": [],
  "split_pathway_candidates": [],
  "tfbs_networks": [],
  "hallucination_traps_triggered": [],
  "resistance_gene_summary": [],
  "wet_lab_priorities": [],
  "metabolomics_targets": [],
  "major_claim_safety_notes": [],
  "missingness": [],
  "recommended_figures": [],
  "recommended_next_steps": []
}
```

### 40.4 Markdown Snapshot Template

```markdown
# [Strain ID] Project Memory Snapshot

## One-paragraph summary

## Source files used

## Core numbers

## Top BGC targets

## Split-pathway candidates

## Ecological/regulatory model

## Hallucination traps triggered

## Resistance gene confirmation summary

## Wet-lab action priorities

## Metabolomics targets

## Missingness and caveats

## Recommended future prompts
```


---

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

2. **BGC-level discrimination only.** Edge or Full-contig truncation may receive −2 in GOOD/MODERATE assemblies when the boundary materially limits interpretation. In POOR/VERY_POOR assemblies the Edge/FC score effect is 0 because truncation is primarily an assembly artefact. **Interior BGCs from fragmented genomes are not discounted** — a shattered assembly can still contain a real, complete Interior/Arch-A cluster on a long contig.

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
- **CONVERGENT:** Shared by distantly related genera with different gene neighbourhood

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
4. Gene neighbourhood in both strains includes a compatible ecological context
5. At least one flanking transposase or integrase is present within 10 kb in at least one strain (Grade A/B)

### HGT candidate record format:

```markdown
## HGT Candidate — [Domain ID] — [Habitat class]
**Domain:** [TIGRFAM/PFAM ID, domain name]
**Strains carrying it:** [list with BGC node, bitscore, evidence grade]
**Genera:** [list — must be phylogenetically distant for HGT call]
**Gene neighbourhood match:** [Describe shared flanking architecture, if any]
**Transposase/integrase:** [Present in [Strain ID], [distance from domain], [bitscore]]
**Candidate donor lineage:** [Organism class + ecological rationale]
**Ecological context:** [Why would this gene be selectively advantageous in this [Habitat]?]
**Classification:** HGT CANDIDATE — requires phylogenetic confirmation (ML tree of domain protein sequences across reference database)
**Recommended validation:** Reconstruct ML protein tree for [domain]; topology inconsistent with organismal phylogeny = HGT confirmation
```

### Current HGT candidate register (reference project):

**BRYO-HGT-001 — RETIRED 2026-05-29.**

hglE-KS glycolipid domain was initially designated BRYO-HGT-001 (cyanobacterial donor hypothesis, moss-specific). This designation is now retired. hglE-KS has since been confirmed in 8 strains/7 genera across all 3 habitats (Bryophyte, Attine, Hymenoptera), refuting the moss-cyanobacterium donor hypothesis and the habitat-specificity claim. hglE-KS is now designated **hglE-KS-PREV-001 — Prevalent Glycolipid Domain, habitat-non-specific.** Structural novelty (zero KCB across all instances) is preserved as the primary analytical value. Reference PDF: CCSM_HGT_Register_Update_hglE-KS_2026-05-29.pdf.

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

```text
Run CCSM for [Habitat class]. Strains: [list].
Run within-habitat comparison for [Habitat class].
Run cross-habitat comparison: [Habitat A] vs [Habitat B].
Build UCS table for [strain set].
Normalize outputs for [strain list].
Run HGT candidate scan for [Habitat class].
Build Gap Register for [strain set].
```

---

## 41.12 APPLICATION TO CURRENT PROJECT DATASET

> *Worked examples of Phase 2 within-habitat and cross-habitat CCSM results from the reference project (actinomycete collection) are published in the companion data paper and Zenodo deposit. Refer to those resources for annotated within-habitat comparison tables, cross-strain signal summaries, and validated ecological findings. This section is intentionally left as a placeholder in the public software release to avoid disclosing unpublished strain data ahead of the associated manuscript.*

---

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

| Version | Date | Notes |
|---------|------|-------|
| v1.0 | 2026-05-27 | Initial — four-phase workflow; UCS; ONP; evidence grades A–X; within-habitat and cross-habitat modules; HGT candidate protocol; QA gates 30.6–30.7 |
| v1.1 | 2026-05-27 | Corrected fourth bryophyte strain identifier. Added AS-XXX complete v7.4 data. Updated with Phase 2 within-habitat findings. |
| v1.1.1 | 2026-05-29 | BRYO-HGT-001 retired; hglE-KS-PREV-001 designated (prevalent, habitat-non-specific). §41.8 HGT register updated. §41.12 Finding 1 revised. §35.4 cross-reference updated. |
| v8.1 | 2026-05-30 | **Reader-Facing Front Page and Briefing Package.** Added default post-analysis package with three reader-facing formats: Editorial Broadsheet, Color Tabloid, and Executive Briefing / Memorandum. User-uploaded imagery is optional and preferred over generated placeholders; prompts can occur after delivery or during a natural mid-analysis exchange. Front-page node labels are simplified (e.g., `BGC05 | Node_3` or `BGC03 | Node_1 · r003`) while full NODE identifiers remain mandatory in BGC Inventory, Scientific Report, Archive Appendix, and Project Memory Snapshot. Front pages must distinguish raw antiSMASH region count from corrected BGC count, may round genome statistics for readability, and must include evidence-boundary language. Priority leads must include compound/scaffold class and/or key genes/domains/architecture support. Executive Briefing signature defaults to active Sapote version, e.g., `Sapote v8.1`, or user name when requested. |
| v8.1.1 | 2026-05-31 | **Diagnostic Signature Weighting + antiSMASH Hallucination-Trap / Claim-Calibration Audit.** Expanded §34 into a fragment-tolerant claim-calibration system. Added evidence-weight tiers, Diagnostic Signal Score, Lead Priority vs Claim Confidence separation, high-information signature rescue, transporter/self-resistance exception handling, marker-library placeholders, and front-page/PDB claim-safety routing. |

---

*Sapote Actinomycete Natural Product Discovery Workflow · CCSM Section 41 v1.1.1 · 2026-05-29*


---

## SECTION 42 — Large Modular PKS Rescue Workflow (LMPKS-RW) v1.0

### 42.1 Purpose

Detect large modular type I PKS, macrolide, polyene, trans-AT, and linear polyketide pathways that are missed, undercalled, split across contigs, or dereplicated poorly by standard antiSMASH product labels and KCB scores. Section 42 is a rescue workflow, not a replacement for standard BGC inventory. It is run alongside the KCB sweep whenever the automatic triggers below fire.

Use manuscript-safe language throughout: **"contains domains consistent with"**, **"candidate large modular PKS"**, **"candidate macrolide-family architecture"**, or **"split-pathway hypothesis"**.

**Guardrail:** LMPKS Rescue must not override stronger non-PKS interpretations unless modular PKS evidence is present. Require at least one of the following before assigning an LMPKS rescue grade: mod_KS / hyb_KS / tra_KS evidence, PKS_AT evidence, PKS_Docking_Nterm or PKS_Docking_Cterm evidence, TE / Abhydrolase_1 release-domain evidence, repeated KR/DH/ER reductive-loop logic, or cross-contig PKS module accumulation. If those signatures are absent, record an LMPKS null result.

### 42.2 Automatic trigger conditions

| Trigger | Condition | Required action |
|---|---|---|
| Trigger 1 — Weak KCB T1PKS | Any Interior T1PKS BGC with KCB cumulative score <1,500, including zero | Run full module reconstruction (§42.3–62.5) |
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
| **T43-PTM — HSAF / Polycyclic Tetramate Macrolactam** | Ornithine-selective A-domain (confirmed by Stachelhaus code prediction or NRPS substrate predictor comparison against HslO/HslI from *Lysobacter enzymogenes* ATCC 29,214 or equivalent characterized HSAF synthetase reference) + iterative PKS architecture (same KS domain reused across multiple extension cycles — detectable as a single KS ORF with anomalously high KS:ACP ratio or multiple downstream ACP domains on the same polypeptide) | PKS-NRPS hybrid context required; standalone ornithine A-domain without iterative PKS co-occurrence is insufficient to fire this trigger | **Yes** — ornithine A-domain selectivity within an iterative PKS-NRPS context is not shared with any other major natural product class; gene-level evidence governs even when KCB score is low or zero | Call candidate HSAF/PTM class; route to §37 HSAF/PTM row; award §33.3 Candida-specific mechanistic link (+2 WL) if Candida bioactivity is confirmed or default-assumed; note acid-labile tetramate ring in extraction instructions (§37 and Fermentation Card); cross-check for three Hymenoptera strains with confirmed HSAF-class BGCs in this project (AS-XXX, AS-XXX, AS-XXX) for CCSM cross-strain comparison eligibility | Floor MEDIUM; Candida mechanistic link awards bounded WL +2 (Candida-specific, §33.3) |

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
Interpretation: a CalC-type or equivalent self-protection gene is present in all characterised chromoprotein enediyne producers. The absence in this BGC likely reflects an unassembled or misassembled contig in the current draft, rather than a genuine absence. Long-read sequencing is required to resolve this.
Manuscript-safe wording: "No self-protection gene was detected within 15 kb of [BGC] in the current draft assembly; a CalC-type or equivalent resistance gene may reside on an unassembled or misassembled contig."
```

### 45.4 Tier 2 — Strong contextual support

Tier 2 markers are class-associated but require a concordance check: the predicted resistance mechanism must be compatible with the BGC compound class. A single Tier 2 concordant hit within 15 kb counts as one independent evidence type under §32.4, and may provide +0.5 support toward a Grade B → A upgrade when the architecture grade is otherwise borderline.

| Resistance marker | Required location | Compound class supported | Key concordance check | HGT guard condition |
|---|---|---|---|---|
| ErmC / ErmE / ErmSF rRNA adenine N-6-methyltransferase (BS ≥150) | Within 15 kb of BGC boundary | Macrolide / lincosamide / streptogramin B (MLSB) producer | The BGC must contain T1PKS macrolide-class modules OR lincosamide biosynthetic domains. Do NOT apply to T2PKS, NRPS-peptide, or terpene BGCs | If Erm gene is flanked by integrase or transposase elements within 5 kb AND biosynthetic gene neighbours are absent → HGT resistance island; classify under §34 trap; do not use as class confirmation |
| ErmC / ErmE within 15 kb of lincosamide adenylation or modification genes | Within 15 kb | Lincosamide producer | Require co-location with lincosamide-specific adenylation or modification domains | Same HGT guard as above |
| Divergent chitin synthase paralogue (same BGC, diverged active-site residues consistent with resistance, BS ≥150 to CaChs2 or ScChs2) | Within BGC coordinates or within 15 kb | Nikkomycin / polyoxin class (chitin synthase inhibitor) | Active-site divergence consistent with resistance must be demonstrable (compare key catalytic residues to reference chitin synthases) | Not applicable — endogenous paralogue; confirm it is not the primary chitin synthase gene of the producer |
| Rif-ADP-ribosyltransferase (ArrA / Arr-type, BS ≥150) | Within 15 kb of ansamycin-class PKS fragments | Ansamycin / rifamycin-class producer | BGC must contain PKS modules consistent with ansamycin scaffold (methylmalonyl-dominant AT, naphthalenic AHBA-primed modules, or strong KCB hit to rifamycin/geldanamycin/mitomycin) | If ArrA is flanked by integrase elements without biosynthetic neighbours → HGT resistance island |

### 45.5 Tier 3 — Polarity routing only

Tier 3 markers do not confirm compound class and do not affect Architecture Confidence or WL score. They inform extraction and fractionation strategy via the Metabolomics Readiness module (§37).

| Marker | Routing action |
|---|---|
| Large MFS transporter (≥14 TM helices, drug-efflux substrate-binding domain orientation) co-localised within BGC | Flag compound as moderate-polarity predicted; standard EtOAc/BuOH extraction likely sufficient; add to §37 in the moderate/nonpolar row |
| ABC transporter (2-component drug-type: substrate-binding protein + ATPase) co-localised within BGC | Flag compound as potentially polar or amphoteric; recommend parallel polar (50% MeOH/H₂O) and nonpolar (EtOAc) fractionation before HRMS dereplication |

Record in the Evidence Traceability block (§32.3 resistance gene row): "Tier 3 — polarity routing only; no class confirmation or WL adjustment."

### 45.6 Conflict detection — HGT resistance island vs producer self-protection

A resistance gene that is present but NOT functioning as producer self-protection is an analytically important null result. Mis-attributing it as class confirmation is the §34 hallucination trap "Resistance gene HGT acquisition misread as producer self-protection."

**Apply the HGT resistance island flag when ANY of the following conditions are met:**

| Condition | Interpretation | Action |
|---|---|---|
| Resistance gene is on a different contig from the claimed BGC | Assembly fragmentation may have separated gene from BGC — do not confirm class | Note in Evidence Traceability as "contig-separated; class confirmation not applicable until assembly resolved" |
| Resistance gene is >15 kb from the BGC boundary on the same contig | Outside proximity rule — not producer self-protection by this criterion | Record distance; note in Missingness Register if relevant compound class; do not count toward §32.4 |
| Resistance gene is flanked by integrase and/or transposase elements within 5 kb, with no biosynthetic gene neighbours | Classic HGT resistance island | Classify under §34 trap; flag in audit log; do not use as class confirmation |
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

At the end of every full v7.9 analysis, respond with:

```text
Completed [Strain ID] using Sapote Actinomycete Workflow v7.9.

Core result:
- Raw BGCs: [N]
- Corrected BGC count: [N]
- Assembly quality: [tier]
- Highest-confidence architecture target: [BGC] (Grade A)
- Highest wet-lab priority target: [BGC] (Score [N])
- Main split-pathway candidate: [BGCs or none]
- LMPKS rescue result: [grade / LMPKS_FRAGMENT_SET / null]
- CCTT triggers fired: [list T43-* / none]
- Resistance gene confirmation: [Tier 1/2 markers found: [list] / Tier 3 routing only / none within proximity rule; class concordant: Y/N; HGT guard triggered: Y/N]
- Chitin/glycan-defense capacity: [None/Low/Moderate/High; DasR-coupled Y/N]
- Main ecological/regulatory model: [one sentence]
- Hallucination traps triggered: [N] — [brief list]

Major caveat:
[One sentence]

Files generated:
- Complete PDF
- Excel workbook (20 sheets)
- KCB dashboard
- Project memory snapshot (JSON + MD)
- Audit log
- ZIP package
```

---

## Standalone Prompt Completeness Check

Before releasing or sharing this prompt, verify that it is self-contained and does not require access to a prior prompt version. Search for and remove or replace phrases such as:

- "unchanged from previous version"
- "unchanged from v7.4"
- "see earlier prompt"
- "as described above" when the referenced section is absent or ambiguous
- project-specific assumptions outside labelled worked examples

Also verify:

- [ ] Diagnostic Signature Weighting rule present.
- [ ] Fragment-tolerant principle present.
- [ ] Lead Priority and Claim Confidence separated.
- [ ] Diagnostic Signal Score present.
- [ ] Evidence-weight tiers for genes/domains present.
- [ ] Transporter and self-resistance exception present.
- [ ] Safe-claim ladder present.
- [ ] Diagnostic Signature / Hallucination-Trap Card present.
- [ ] Front-page/PDB claim-safety gate present.
- [ ] Marker-library placeholder table present.
- [ ] UMED maturation-gap logic present.
- [ ] Lanthipeptide protease family library present.
- [ ] UMED single-genome specificity-unverified claim ceiling present.
- [ ] M16B heterodimer guard present.
- [ ] UMED GAP-no-candidate missingness handling present.


- All trigger phrases reference the current version or say "current workflow version."
- The final compiled PDF TOC is distinct from the prompt TOC.
- Standard Full Analysis and Archive-Quality Full Analysis are both defined in §0.9, with trigger-phrase disambiguation table.
- The mode default reversal from v7.8 (Full Depth unconditional default) to v8.0.1 (Standard Full Analysis default) is documented in §0.9 and the version history table.
- Smoke-test mode is clearly labelled as incomplete.
- LMPKS Rescue has a guardrail preventing PKS over-calling.
- FLBR §51 is present, runs before final megasynthase priority assignment, and includes STRONG/WEAK tiers, assembly-quality gate, double-docking carve-out, NRPS/hybrid sibling logic, audit-log language, and QA gate 30.9.
- Verified Literature Deep Dive and Rapid Literature Deep Dive are fully described in this prompt, not delegated to an earlier version.
- Sections 43 (CCTT) and 44 (CGAD) are fully described in this prompt, not delegated to an earlier version.
- CCTT triggers carry the bounded, non-stacking, override-not-inflate discipline.
- CGAD is framed as ecological capacity (hypothesis), never host-protection fact.
- The two v7.6 scoring fixes (verdict feedback §31.5/§30.2; WL discrimination §33.3) are present.
- **Section 45 (Resistance Gene-Guided Compound Class Confirmation) is fully described with all five Tier 1 markers, Tier 2 markers with HGT guard, Tier 3 routing markers, proximity rule, CalC absence flag, §34 HGT resistance island trap, §36.4 reviewer attack category, §32.4 evidence type update, §33.3 WL adjustment, ResistanceGene_Confirmation Excel sheet (Sheet 20), and QA gate §30.9.**
- **§43.7 and §44.7 trigger phrases are populated (not blank).**
- **hglE-KS-PREV-001 is designated and BRYO-HGT-001 is retired in §25, §35.4, §41.8, and §41.12.**
- **The compiled master PDF order (§15.8) includes position 5.7 for the Resistance Gene Confirmation Report.**
- **The Workflow Ledger (Option 5) includes the resistance gene scan step.**
- **The Excel workbook (§18) lists 20 sheets.**

- **§8 includes entries for: indolocarbazole (indsynth marker); HSAF/PTM (ornithine A-domain + iterative PKS-NRPS); mannopeptimycin (TIGR01720 ×2, distinct from enduracididine); carbapenem (CarB/CarC); ansamycin (AHBA synthase PF06353); angular T2PKS (+ angular-fold oxygenase); linear T2PKS (+ linear cyclase); modified glycosylated T2PKS entry cross-referencing angular/linear disambiguation.**
- **§33.3 includes HSAF/PTM as a Candida-specific mechanistic link and an explicit exclusion note for indolocarbazoles from the Candida mechanistic link category.**
- **§34 includes traps for "indole masking indolocarbazole", "ectoine masking showdomycin", and "saccharide BGC as split-pathway glycosylation arm".**
- **§37 includes rows for indolocarbazole, HSAF/PTM, prodiginine, ansamycin, and showdomycin.**
- **§43 includes T43-IDC (indolocarbazole), T43-PTM (HSAF/PTM), and the T43-AMC streptomycin-class carve-out.**
- **§26 AS-XXX entry reflects the NODE_182/105 indolocarbazole split-pathway candidate identified 2026-05-30.**
- **Abbreviated ledger entry minimum fields are defined in §0.9** (9 required fields; satisfies Run Controller treatment-status non-negotiable).
- **Triage First Board parallel-scan dependency is explicit in §0.6 Required Timing** (all six parallel scans must complete before the board is generated).
- **Layer C content is explicitly defined for both Standard and Archive-Quality modes in §0.5.**
- **Chemical handle status line is present in the §0.6 Candidate Card format** (connects §0.7 identity-safety rule to the first output layer where handles appear).
- **§33.3 includes the §46 chemical handle WL modifier table inline** (no cross-reference lookup required during scoring).
- **CGAD Step 0 proteome scope check is defined in §44.1A** and distinguishes `full proteome scanned`, `BGC-region only`, and `full proteome unavailable` states.
- **§34 includes the BGC-local null misread as genome-wide null hallucination trap.**
- **§38.2 includes the Proteome scope limitation missingness category.**
- **§17.2A distinguishes BGC-local evidence from genome-wide functional scan evidence.**
- **§44.5 includes the DasR/NagR coupling guard requiring full-proteome CGAD before genome-level substrate-supply claims.**

- [ ] §1 Session Startup Checklist includes item 1f: canonical BGC ID assignment
      in JSON FASTA-input order, always paired with contig·region identifier.
- [ ] §17.10 Ecological Hypothesis Format includes required "Supporting literature"
      field with evidence-grade labelling (direct / class analogy / structural analogy).
- [ ] §30.4 Ecological Synthesis Depth Gate includes citation check for §17.10
      Supporting literature field.
- [ ] §8 includes APE_KS2 arylpolyene (APE pigment class) entry.
- [ ] §37 includes arylpolyene (APE; flexirubin-type) metabolomics row.
- [ ] §44.1A includes HMMER-unavailable motif fallback protocol for GH18 with
      approved and prohibited claim-language tiers.
- [ ] §38.2 includes HMMER-unavailable sub-type under Proteome scope limitation.
- [ ] §33.3 includes QS signal compound routing note (hserlactone, BDSF,
      butyrolactone → Ecological Synthesis only; no mechanistic link WL bonus).
- [ ] §34 includes plant glucosinolate KCB false-positive trap.
- [ ] §34 includes Streptomyces/actinomycete KCB kingdom-mismatch trap for
      Proteobacterial FC saccharide BGCs.
- [ ] §30.1 Mode B Depth Gate includes §4 citation requirement with evidence-grade
      labelling.
- [ ] §17.4 includes multi-siderophore capacity flag (≥3 siderophore BGCs →
      iron-acquisition capacity table + §17.10 hypothesis).
- [ ] §33.3 includes phenazine→Escovopsis attine-context specificity note.
- [ ] §17.6 attine Escovopsis row distinguishes direct evidence (pyrrolnitrin,
      occidiofungin/burkholdine; PMID 33962985) from class analogy (phenazine).

---

## Version History

| Version | Date | Changes |
|---|---|---|
| v8.3 candidate | 2026-05-31 | **Fragmented Large-BGC Rescue (FLBR) patch.** Added §51 as parent rescue logic for fragmented assembly-line megasynthases across T1PKS, modular NRPS, PKS-NRPS hybrid, and trans-AT systems. Added STRONG/WEAK evidence tiers; assembly-quality gate with Very-Poor auto-demotion; double-docking-bracketed internal-module carve-out; Run Controller sequencing guard requiring genome-wide megasynthase census before final priority assignment; NRPS/hybrid sibling logic; QA gate 30.9; trigger phrases; report language; and validation appendix using AS-XXX (STRONG retained) versus AS-XXX/AS-XXX (Very-Poor demoted to WEAK). |
| v8.2 | 2026-05-31 | **Compound-class coverage + claim-safety patch.** §33.3: promoted "absence of assay ≠ inactivity" to a standing principle with class-context routing (marinolide correction generalized). **DKP-CDPS** added across §8/§43/§37/§33.3/§34/§45: CDPS rule-based / PF16715 diagnostic entry, T43-DKP trigger (gene-beats-cluster), DKP detection rank A–D, strengthened PF00881/CDO specificity guard, dehydro-DKP vs saturated metabolomics rows, no-self-resistance-marker note, cytotoxicity routing (no MRSA/*Candida* bonus). **Linear polyether ionophore** added across §8/§42/§37: LMPKS-PE grade, SMCOG-based cassette detection rule (epoxidase detectable, epoxide hydrolase HMMER-pending), cation-adduct metabolomics row. **PKS KR/ER stereochemistry reasoning** added as optional/gated §6/§7 capability with mandatory hypothesis-not-structure claim-safety (§30.1). Validated against AJS-XXX (photopiperazine confirmed DKP-A by AlbA/AlbC homology; bare CDPS DKP-B/C; ionostatin polyether 7-PKS + KCB anchor; tetrachlorizine and marinolide as bundled examples). No v8.1.1 detection module removed or weakened. |
| v1.0 | 2026-05-25 | Initial workflow prompt. |
| v1.1 | 2026-05-25 | Data governance, source hierarchy, missing-data rules, claim-safety language, audit logs, glossary workflow. |
| v5.3 | 2026-05-26 | Strain-level analysis: JSON-first parsing, KCB sweep, TTA/bldA, tiered dereplication, HGT scan, neighbourhood comparison, POOR assembly protocol, VLD / RLD v2.0. |
| v6.0 | 2026-05-27 | Consolidated project-wide v1.1 with v5.3 strain modules; Full Analysis Mode override; KCB/TTA/HGT/dereplication modules; fermentation card; standardised audit/file-naming. |
| v6.1 | 2026-05-27 | Compiled PDF must include production TOC with page numbers. |
| v6.2 | 2026-05-27 | Ecological synthesis claim-safety addendum; cross-habitat comparison flags; fast ecological synthesis trigger. |
| v6.3 | 2026-05-27 | Verified Literature Deep Dive / Rapid Literature Deep Dive expanded to full v2.0 descriptions. |
| v7.0 | 2026-05-27 | Ecological Synthesis Module as full Section 17 (14 subsections). |
| v7.1 | 2026-05-27 | Evidence/confidence labels; null-result reporting; BGC-by-BGC ecological matrix; scoring rubric; Workflow Ledger. |
| v7.2 | 2026-05-27 | Fixed §7→§8 reference in Section 17.10. Fixed stale v6 references. Added reference implementations. Package ZIP defined in Workflow Ledger. |
| v7.3 | 2026-05-27 | Added TTA/bldA three-source lookup order to Section 9. Updated Section 3 parsed-fields and Section 1 startup checklist. Added Section 30 Output Quality Assurance Gates (30.1–30.5). |
| v7.4 | 2026-05-27 | Added Sections 31–40 (BGC Architecture Confidence System; Evidence Traceability Blocks; Wet-Lab Decision Matrix; antiSMASH Hallucination-Trap Checks; Cross-Strain BGC Family Clustering Hook; Reviewer Attack Simulation; Metabolomics Readiness Module; Known Missingness Tracking; Figure Suggestion Module; Project Memory Snapshot). Excel workbook expanded to 16 sheets. |
| v7.5 | 2026-05-27 | Added Section 41 — Cross-Comparative Synthesis Module (CCSM) v1.1. Four-phase workflow. Universal Comparison Schema with evidence grades A–X. Output Normalization Protocol. HGT candidate protocol. QA gates 30.6–30.7. |
| v7.5.1 | 2026-05-28 | Added Section 42 — Large Modular PKS Rescue Workflow (LMPKS-RW v1.0). Rescue grades LMPKS-A through LMPKS-X. Fragment rescue protocol and LMPKS_FRAGMENT_SET. QA Gate 30.8. WL scoring adjustments. LMPKS Rescue Report deliverable at position 5.5. |
| v7.5.2 | 2026-05-28 | Generic prompt adaptation. Strain IDs, host species binomials, and habitat category names replaced with placeholders in instructional positions; retained as worked examples in §25, §26, §41.12. Identifier Conventions note added to §2. §37 polar compound caveat and peptidyl nucleoside metabolomics row added. New §34 trap: 0% MIBiG cluster similarity misread as unknown compound class. |
| v7.5.3 | 2026-05-28 | Full Coverage vs Full Depth execution modes; smoke-test trigger; module-priority guidance for limited runs; LMPKS over-calling guardrail; Standalone Prompt Completeness Check. |
| v7.5.4 | 2026-05-28 | Added Global Analytical Defaults: bioactivity default (MRSA + Candida at extract level); seven-category ecological source classification system with natural language keyword lookup; per-category TFBS interpretation defaults; Metadata Conflict Audit; Pre-Analysis Clarification Protocol (materiality-gated, max 3 questions, single block, "use defaults" escape). Section 1 startup checklist items 1b–1c added. |
| v7.6 | 2026-05-29 | Section 43 (CCTT): halogenation tiered; peptidyl-nucleoside gene>cluster override; phosphonate PepM; enediyne ene_KS; aminocyclitol DOIS affirmative+rule-out. Section 44 (CGAD): genome-wide chitinolytic capacity; insect dual-use guard; pairs with T43-NUC. Excel 17→19 sheets. §34 +3 new traps. §37 auto-routing updated. Scoring fixes: hallucination-trap/fragmentation verdicts cap architecture (§31.5/§30.2); distinctive-handle and specific-mechanistic-link discrimination (§33.3). |
| v7.7 | 2026-05-29 | **Section 45 — Resistance Gene-Guided Compound Class Confirmation (new).** Five Tier 1 markers (VanHAX → glycopeptide; CalC-type radical SAM → enediyne chromoprotein; NikT/NikD-type → nikkomycin class; FomA/FomB → phosphonate; DOIS+APH/AAC → aminoglycoside); three Tier 2 markers (ErmC/ErmE/ErmSF → macrolide/lincosamide with HGT guard; chitin synthase paralogue → nikkomycin class; ArrA → ansamycin with HGT guard); two Tier 3 polarity-routing markers (MFS, ABC transporter). Proximity rule: within BGC coordinates (highest) or within 15 kb on same contig (strong). CalC absence flag mandatory for enediyne BGCs. §34 new trap: resistance gene HGT acquisition misread as producer self-protection. §36.4 new required reviewer attack category: self-protection absent from claimed cytotoxic BGC. §32.4: concordant resistance gene added as 8th independent evidence type. §33.3: +1 WL for concordant Tier 1 or Tier 2 marker. §31.5: B→A upgrade support with hallucination-trap cap preservation. §30.9: new QA gate — Resistance Gene Confirmation Gate. §27 audit log: resistance gene confirmation summary added. §28 file naming: ResistanceGene_Confirmation filename added. §37.2/§37.3: resistance gene concordance note column added to Metabolomics_Readiness; class-level default table expanded with resistance marker column. §38.2: Resistance gene missingness category added. §40.3/§40.4: resistance_gene_summary field added to JSON and MD snapshot templates. Excel 19→20 sheets (Sheet 20: ResistanceGene_Confirmation). §15.6.2 and §15.8 position 5.7: Resistance Gene Confirmation Report added to deliverables. Option 3 and Workflow Ledger updated. **hglE-KS-PREV-001 designated; BRYO-HGT-001 retired** across §25, §26, §35.4, §41.8, §41.12, and §41.14. §43.7 trigger phrases populated. §44.7 trigger phrases populated. Standalone Prompt Completeness Check updated for v7.8. v7.5.4 remains runnable as fallback; v7.6 remains runnable as immediate fallback. |
| v7.8 | 2026-05-29 | **Full Depth Mode is now the unconditional default** for all full analysis triggers. Full Coverage Mode demoted to explicit-request-only status; it is no longer a fallback for large strains or context pressure. Added **§2B: Batch Plan Protocol** — mandatory Batch Plan announcement for strains with >15 BGCs before any Mode B work begins; seven-tier priority ordering for batch assignment; formal session continuation and batch-end summary formats. **Mode B §2** redefined: gene-by-gene domain analysis (all PFAM/TIGRFAM hits per CDS, functional assignment from domain evidence, functional flag) is the required, non-abbreviatable primary analytical layer from which all §3–§8 content is derived. Workflow Ledger: 'Batch Plan announced' added as first required stage. Section 1 startup: item 1d — Batch Plan recovery before any Mode B work. Section 29 CDSW: batch continuation is the primary next path for batch sessions. White Paper: 'Batch Execution and Gene-by-Gene Domain Analysis in the Sapote Workflow' (Sapote_Workflow_WhitePaper_BatchExecution_v7.8_2026-05-29.pdf) documents design rationale and implementation. |
| v7.9 | 2026-05-30 | **PDF Style Standard and bioactivity-default enforcement.** Added mandatory Sapote PDF style module (`sapote_pdf_styles.py`) for all PDF outputs; narrative sections use Sapote text-flow helpers and structured data uses `sapote_table()` so individual scripts do not redefine styles from scratch. Expanded §30.5 PDF generation rules and added §30.10 PDF Style and Bioactivity-Default Gate requiring bookmarks/outlines, visible default/status boxes, rendered-page QA, no overlapping text, and no clipped tables. Added §15.11 deliverable-level layout/default requirements. Strengthened Global Analytical Defaults: when strain-specific assay data are absent, MRSA + Candida inhibition must be recorded as `default-assumed` rather than `missing`, propagated to context acknowledgement, Deep Dive Synopsis, Mode B §6, Wet-Lab Decision Matrix, Metabolomics Readiness, Ecological Synthesis, Missingness Register, Project Memory Snapshot, and audit log, while preserving claim-safety language that extract-level defaults do not assign activity to any BGC. |
| v7.9.1 | 2026-05-30 | **Compound class coverage patch — 10 items across 6 sections.** Triggered by post-hoc identification of a split indolocarbazole BGC in AS-XXX (NODE_182 indsynth E=0 BS=1349.6 + NODE_105 Trp_halogenase BS=567.6) that was undetected by all prior workflow runs despite being present in the antiSMASH GBK files. Systematic gap review identified 9 further items. **§8:** MODIFIED existing glycosylated T2PKS entry to cross-reference new disambiguation; ADDED 7 new entries: indolocarbazole (indsynth marker), HSAF/PTM (ornithine A-domain + iterative PKS-NRPS), mannopeptimycin (TIGR01720 ×2; as distinct from enduracididine), carbapenem (CarB/CarC), ansamycin (AHBA synthase PF06353 + aminoDAHP/aminodehydroquinase context), angular T2PKS (+ angular-fold oxygenase), linear T2PKS (+ linear cyclase). **§26:** UPDATED AS-XXX reference entry with NODE_182/105 indolocarbazole split-pathway candidate. **§33.3:** ADDED HSAF/PTM as Candida-specific mechanistic link (+2 WL); ADDED explicit exclusion of indolocarbazoles from the Candida mechanistic link category. **§34:** ADDED 3 new traps: "indole masking indolocarbazole"; "ectoine masking showdomycin"; "saccharide BGC as split-pathway glycosylation arm." **§37:** ADDED 5 new class rows: indolocarbazole (cytotoxicity caution mandatory), HSAF/PTM (acid-labile tetramate ring noted), prodiginine (visual plate screen as primary detection), ansamycin (colour handle noted), showdomycin (C18 reversed-phase explicitly flagged as insufficient). **§43:** ADDED T43-IDC (indolocarbazole, indsynth ≥500 single-marker trigger); ADDED T43-PTM (HSAF/PTM, ornithine A-domain + iterative PKS trigger; Candida mechanistic link activates +2 WL bonus); MODIFIED T43-AMC to add mandatory streptomycin-class carve-out preventing false DOIS rule-out. |
| v8.0 | 2026-05-30 | **Execution and readability integration.** Added Run Controller / Execution Spine (§0); Reader-Layered Output System (§0.5); Triage First Board (§0.6); LC-MS Chemical Handle Module (§0.7); Visual Load Reduction Standard (§0.8); Standard vs Archive-Quality Full Analysis distinction (§0.9) - **Standard Full Analysis is now the default, overriding the v7.8 Full Depth unconditional default**; Evidence / Claim Separation Card (§0.10); Package Manifest and Deferred Ledger (§0.11); §46 v8.0 Execution and Readability Integration Addendum (chemical handle WL modifiers, PDF/QA integration, §37 and §43 CCTT integration, v8.0 completeness check). No v7.9.1 detection modules modified or removed. |
| v8.0.1 | 2026-05-30 | **Specification refinement patch - 7 items.** R1 (§0.9): Abbreviated ledger entry minimum fields defined - 9-field table prevents variable abbreviated-entry content across runs. R2 (§33.3): §46 chemical handle WL modifier table added inline - eliminates need to cross-reference §46 during WL scoring. R3 (§0.6): Triage First Board parallel-scan dependency made explicit in Required Timing - board requires all six parallel first-pass scans. R4 (Option 6): Top-3 Triage First Board entries with class-level chemical handles added to smoke-test minimum outputs. R5 (§0.5): Layer C content for Standard and Archive-Quality modes explicitly defined - removes ambiguity about abbreviated ledger vs full Mode B in Layer C. R6 (Version History): v8.0 and v8.0.1 rows added to main version history table. R7 (§0.6): Chemical handle status line added to Candidate Card format - connects §0.7 identity-safety rule to the first output layer where chemical handles appear. Header version number updated to 8.0.1. Patch note block updated. Standalone Prompt Completeness Check updated. |
| v8.0.2 | 2026-05-30 | **CGAD genome-wide proteome scope patch.** Added required §44.1A Proteome Scope Check before CGAD verdicts; defined `full proteome scanned`, `BGC-region only`, and `full proteome unavailable` states; required full-record CDS/proteome scanning from antiSMASH GBK `/translation=` fields when available, with Prodigal/Prokka protein FASTA fallback; added motif-vs-HMMER claim-language tiers for GH18/GH19/AA10 calls; updated §44.4 CGAD output table with scope/method/confidence fields and state-aware verdict language; added §44.5 DasR/NagR coupling guard; added §34 trap for BGC-local null misread as genome-wide null; added §38.2 Proteome scope limitation missingness category; updated §17.2A to distinguish BGC-local evidence from genome-wide functional scan evidence; updated Run Controller and §0.6 timing to require CGAD proteome scope state before Triage First Board; updated Standalone Prompt Completeness Check. Prior BGC-region-only CGAD nulls must be reclassified as `Not Assessable pending proteome rescan`. |
| v8.0.3 | 2026-05-30 | **9-item patch from ICBG1735 WFA test case.** (1) Canonical BGC ID convention: JSON FASTA-input order; always paired with contig·region (§1, §4, §27, §28). (2) Ecological hypothesis citation field: required Supporting literature with evidence-grade labels (§17.10, §30.4). (4) Arylpolyene (APE_KS2) class entry (§8, §37). (5) CGAD HMMER-unavailable motif fallback protocol with claim-language tiers (§44.1A, §38.2). (6) QS signal compound routing: hserlactone/BDSF/butyrolactone → Ecological Synthesis only, no mechanistic link WL bonus (§33.3). (7) Two Gram-negative KCB false-positive traps: plant glucosinolate and actinomycete kingdom-mismatch (§34). (8) Mode B §4 citation requirement with evidence-grade labelling (§30.1). (9) Multi-siderophore capacity flag: ≥3 siderophore BGCs → iron-acquisition table + §17.10 hypothesis (§17.4, §17.8A). (10) Phenazine→Escovopsis attine-context specificity guard: class analogy label required; direct-evidence labels for pyrrolnitrin and occidiofungin/burkholdine (PMID 33962985) (§33.3, §17.6). Item 3 (non-actinomycete startup declaration) deferred. Test-ready addendum also adds §14 taxonomy preflight support for assembled FASTA users: optional ContEst16S/EzBioCloud 16S extraction, BLAST genus anchoring, and species-level claim guardrails. |

---

*Sapote Actinomycete Natural Product Discovery Workflow · v8.3 candidate · 2026-05-31*

---

## SECTION 46 — v8.0 Execution and Readability Integration Addendum

> **[ARCHIVED — v8.0 addendum, superseded.]** Content integrated into §0–§0.11 (execution spine) and §0.8 (visual load standard) in v9.x. Retained for version history only; not an active instruction set.

### §15 deliverable integration

v8.0 required deliverables:

- Triage First Board with LC-MS Chemical Handle columns.
- Executive / Layperson Report PDF.
- Scientific Deep Dive Report PDF.
- Archive Appendix PDF or deferred archive ledger.
- Chemical Handle Table with representative formulas/MWs, expected adducts, and EIC/TIC windows.
- Package Manifest.
- Deferred Ledger when any item is incomplete.

The Triage First Board must appear before long Mode B reports in both Markdown and PDF outputs. It is the reader’s map to the analysis.

### §30 PDF and QA integration

v8.0 PDF readability gates:

- Reader-layered output verified: Executive, Scientific, Archive.
- Triage First Board appears before deep dives.
- Chemical Handle Table appears in Scientific Report and Archive Appendix.
- Dense tables are preceded by interpretation boxes.
- Wide tables use landscape pages.
- Full gene-by-gene tables are routed to the Archive Appendix unless top-candidate inline inclusion is justified.
- Every top candidate has a Candidate Card.
- Every major claim has genome support / assay support / unproven / next action separation.

### §33 wet-lab scoring integration

Chemical-handle readiness contributes to wet-lab actionability. A BGC with a strong class call, diagnostic formula/MW handles, expected adducts, UV/Vis targets, and feasible extraction conditions should receive higher wet-lab readiness than an equally interesting but chemically vague BGC. Do not let chemical-handle readiness override claim-safety or architecture confidence.

| Condition | WL modifier |
|---|---:|
| Specific compound/family handle with verified formula/MW and expected adducts | +1 |
| Class-level handle with 2–5 representative compounds or narrow MW range | +0.5 |
| Diagnostic UV/Vis or isotope pattern available | +0.5 |
| No reliable chemical handle despite high genomic interest | 0; note as untargeted LC-MS/MS priority |

### §37 metabolomics integration

Every metabolomics-readiness row must include a Chemical Handle subsection:

- predicted class or candidate family
- specific or representative compound handles
- formulas/MWs where verified
- expected adducts
- EIC/TIC windows
- UV/Vis wavelengths
- isotope-pattern notes for halogenated compounds
- extraction/stability caveats
- identity-safety caveat

Chemical handles are search targets, not identifications. Matching m/z should trigger targeted inspection and MS/MS prioritization, not final compound assignment.

### §43 CCTT integration

Every affirmative CCTT trigger must feed the Triage First Board and receive an LC-MS Chemical Handle entry. If the trigger identifies a class but not a specific compound, provide representative class examples and a class-level MW range. If the trigger suggests halogenation, include isotope-pattern guidance. If the trigger suggests a polar nucleoside or β-lactam, flag extraction-method mismatch risk.

### Version history

v8.0 — 2026-05-30 — Major execution/readability release. Added Run Controller, Reader-Layered Output System, Triage First Board, LC-MS Chemical Handle Module, Visual Load Reduction Standard, Standard vs Archive-Quality Full Analysis distinction, Evidence/Claim Separation Cards, Package Manifest, and Deferred Ledger. This release changes how the workflow runs and packages outputs without weakening the v7.9.1 scientific detection modules.

### v8.0 standalone completeness check

A v8.0 prompt is complete only if it contains:

- [ ] Run Controller / Execution Spine
- [ ] Reader-Layered Output System
- [ ] Triage First Board
- [ ] LC-MS Chemical Handle Module
- [ ] Visual Load Reduction Standard
- [ ] Standard vs Archive-Quality mode distinction
- [ ] Evidence / Claim Separation Card
- [ ] Package Manifest
- [ ] Deferred Ledger
- [ ] Existing v7.9.1 detection modules retained: indolocarbazole, HSAF/PTM, ectoine/showdomycin trap, prodiginine tracking, ansamycin AHBA marker, mannopeptimycin TIGR01720 ×2, streptomycin carve-out, carbapenem marker, angular/linear T2PKS disambiguation, saccharide split-pathway glycosylation arm

---

## SECTION 47 — v8.0.2 CGAD Genome-Wide Proteome Scope Addendum

> **[ARCHIVED — v8.0.2 addendum, superseded.]** CGAD proteome-scope rule now lives in §44 (active CGAD module). Retained for version history only.

### 47.1 Purpose

This addendum documents the v8.0.2 boundary correction for CGAD. CGAD declares itself a genome-wide ecological-capacity module, so it must not be scored from BGC-local cluster_hmmer evidence alone. The ICBG1735 test case showed the failure mode clearly: a BGC-region-only scan produced `Not Assessable` / apparent null chitinase evidence, while full-proteome extraction from antiSMASH GBK `/translation=` fields revealed multiple secreted GH18 candidates. This is a module-definition issue, not a rare edge case.

### 47.2 Rule

Never score a genome-wide ecological module from BGC-local evidence alone. Before CGAD reports absence, low capacity, or a high-confidence capacity state, it must declare whether it scanned the full predicted proteome, only BGC-region features, or no full proteome was available.

### 47.3 Required routing

- §3 parsing extracts all CDS `/translation=` fields from antiSMASH GBK files when present.
- §44.1A uses those translations as the default full-proteome input for CGAD.
- §34 prevents BGC-local null calls from being misread as genome-wide absence.
- §38.2 records proteome-scope limitations as missingness.
- §17.2A distinguishes BGC-local evidence from genome-wide functional scan evidence.
- §44.5 blocks DasR/NagR substrate-supply claims unless full-proteome CGAD has been run.

### 47.4 Claim-safety language

Use: "full-proteome scan identified secreted GH18 chitinase candidates."

Use after HMMER confirmation: "full-proteome HMMER scan identified high-confidence secreted GH18 chitinase candidates."

Do not use after BGC-only scans: "no chitinases detected," "lacks chitinolytic capacity," or "CGAD null."

### 47.5 Triggered completeness check

Every CGAD output must include a `Proteome scope` line and a `Detection method` line. Missing either line fails the Standalone Prompt Completeness Check.

---

## SECTION 48 — v8.0.3 ICBG1735 Workflow-Flexibility Addendum

> **[ARCHIVED — v8.0.3 addendum, superseded.]** Workflow-flexibility guidance folded into §23 (mode selection) in v9.x. Retained for version history only.

### 48.1 Purpose

This addendum documents the v8.0.3 patch set derived from the ICBG1735 *Burkholderia* sp. (*Atta* sp.) workflow-flexibility assessment. The patch strengthens cross-session BGC identifiers, non-actinomycete/Gram-negative safety rails, ecological-citation discipline, CGAD fallback behavior, and wet-lab scoring specificity without weakening the existing actinomycete discovery workflow.

A test-ready taxonomy preflight note has also been added to §14 so assembled-FASTA users can extract 16S candidates with ContEst16S/EzBioCloud, BLAST those sequences for genus anchoring, and keep species-level claims guarded unless supported by ANI/GTDB/phylogenomic evidence.

### 48.2 Design status

Items 1, 2, 4, 5, 6, 7, 8, 9, and 10 are integrated into their operational sections. Item 3, the non-actinomycete startup declaration, remains deferred for further design; until then, non-actinomycete applicability is handled by existing source-category parsing, TTA/bldA applicability notes, and the new Gram-negative KCB false-positive guards.

---

## SECTION 49 — Reader-Facing Front Page and Briefing Package

### 49.1 Purpose

The **Reader-Facing Front Page and Briefing Package** is a default post-analysis deliverable layer for Sapote v8.1. It translates the technical analysis into polished, shareable summary pages without replacing the Executive Report, Scientific Report, Archive Appendix, BGC Inventory, or Project Memory Snapshot.

### 49.1A Front-page claim-safety gate

Reader-facing headlines must pass the Diagnostic Signature / Hallucination-Trap Card. Headlines may emphasize high-interest genetic signatures, rare markers, and follow-up value, but must not convert biosynthetic potential into confirmed production. PDB-style or news-style outputs should use phrases such as “genetic signature,” “candidate fragment,” “BGC lead,” “pathway-family signal,” or “high-priority follow-up lead” unless product-level chemistry is confirmed.


The package is intended for collaborators, PIs, lab meetings, internal presentations, development-phase strain prioritization, and visually memorable summaries that still preserve evidence boundaries.

### 49.2 Default package

After the main analysis package is complete, generate all three reader-facing formats by default unless the user requests omission:

1. **Editorial Broadsheet** — serious newspaper-inspired front page.
2. **Color Tabloid** — high-energy colorful discovery front page.
3. **Executive Briefing / Memorandum** — formal decision memo and next-action summary.

Users may later request that any of the three pages be omitted from the compiled report or regenerated separately.

Required wording when generated:

```text
Reader-Facing Front Page and Briefing Package generated: Editorial Broadsheet, Color Tabloid, and Executive Briefing. These are reader-facing summary pages and may be omitted from the compiled report on request.
```

### 49.3 Format A — Editorial Broadsheet

**Internal nickname:** WSJ-style  
**Public-facing name:** Editorial Broadsheet  
**Do not use:** real newspaper names, logos, mastheads, or branding.

Use for archive-quality strain reports, collaborator review, PI review, polished packets, and conservative scientific presentation.

Recommended style:
- cream or off-white paper background;
- black/navy typography;
- classic editorial hierarchy;
- restrained color;
- thin rules and boxed sidebars;
- masthead such as `SAPOTE ANALYSIS BRIEF`;
- large headline;
- host/isolate imagery when available;
- `At a Glance` sidebar;
- `Top Candidates` table;
- `Evidence Boundary` box.

Required core blocks:
- masthead;
- strain line;
- workflow version and run mode;
- headline;
- summary deck;
- host/source image slot;
- isolate/agar plate image slot;
- `At a Glance`;
- `Top Candidates`;
- `Evidence Boundary`;
- simplified node cross-reference note.

### 49.4 Format B — Color Tabloid

**Internal nickname:** Daily-Mail-style  
**Public-facing name:** Color Tabloid  
**Do not use:** real newspaper names, logos, mastheads, or branding.

Use for internal excitement, lab meetings, teaching, outreach, and discovery-forward summaries.

Recommended style:
- high-energy layout;
- larger headline typography;
- brighter color palette;
- strong section blocks;
- stronger visual hierarchy than Format A;
- claim-safe wording throughout.

Required safeguards:
- every dramatic headline must remain hypothesis-safe;
- do not imply confirmed compound production unless experimentally verified;
- include a prominent `Claim Safety` or `Evidence Boundary` box;
- clearly label default-assumed bioactivity when applicable.

Acceptable headline:

```text
High-Value Biosynthetic Potential in AS-XXX
```

Avoid unless production and activity are experimentally verified:

```text
AS-XXX Produces New Antibiotics
```

### 49.5 Format C — Executive Briefing / Memorandum

**Internal nickname:** Presidential Briefing  
**Public-facing name:** Executive Briefing or Executive Memorandum  
**Do not use in final deliverables unless user requests it:** `Presidential`.  
**Do not use:** real government seals, official White House styling, or real governmental branding.

Use for strategic prioritization, wet-lab action planning, decision memos, and discovery-team follow-up.

Recommended style:
- formal internal memo;
- cream paper;
- navy/black typography;
- structured headings;
- right-side data snapshot;
- optional visual reference strip;
- small formal signature block.

Default signature:

```text
Sapote v8.1.1
```

or the current active Sapote version. Use the user's name only when requested.

Recommended memo sections:
1. Purpose
2. Priority Leads
3. Immediate Directives
4. Evidence Boundary
5. Decision Rationale
6. Data Snapshot
7. Visual Reference
8. Approval / Signature Block

### 49.6 Image upload and visual-content workflow

Sapote should **not force image generation** of host systems, agar plates, colonies, or habitats.

After the main analysis is delivered, optionally prompt the user:

```text
Optional front-page imagery: You may upload host-system photos, agar/colony images, habitat photos, microscopy, maps, chromatograms, or other visuals for the Front Page Package. If no images are supplied, Sapote can use a no-image layout or clearly labeled placeholders/mockups.
```

This prompt may also be offered during a natural mid-analysis exchange or stoppage.

Useful uploaded imagery includes:
- host organism photo, such as bee, wasp, ant, plant, moss, fungus, sponge, or other source organism;
- isolate plate image;
- colony morphology image;
- habitat image;
- microscopy image;
- LC-MS chromatogram;
- map or collection-locality image;
- culture flask or fermentation image.

Priority order:
1. user-uploaded real images;
2. user-approved placeholder images;
3. no-image version;
4. generated illustrative placeholder, only if useful and clearly treated as a mockup.

Captions must distinguish real images from placeholders.

Examples:

```text
Host system: user-uploaded Bombus sp. field image.
Inset: user-uploaded AS-XXX agar plate image.
```

```text
Host-system image: illustrative placeholder; replace with user photo when available.
```

### 49.7 Simplified Node-label policy

Front pages and executive memos should use simplified node labels for readability:

```text
BGC05 | Node_3
```

instead of the full technical contig string:

```text
BGC05 | NODE_3_length_268105_cov_91.383837-r002
```

This is appropriate because low-pass NGS assemblies often have few BGCs per contig. A front page for a fully assembled or near-complete genome is not harmed if many leads display as `Node_1`, as long as BGC IDs remain prominent.

If multiple high-priority BGCs occur on the same node, include the BGC ID and optionally the antiSMASH region label:

```text
BGC03 | Node_1 · r003
BGC01 | Node_1 · r001
```

Full technical NODE identifiers remain mandatory in:
- BGC Inventory;
- Archive Appendix;
- Scientific Report;
- Project Memory Snapshot;
- machine-readable tables;
- cross-reference tables.

Required note:

```text
Front-page Node labels are simplified for readability. Full NODE identifiers and region coordinates are preserved in the BGC Inventory and Archive Appendix.
```

Never invent node identifiers. If node mapping is unavailable, say so.

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

Recommended front-page lead format:

```text
BGC05 | Node_3 · r002
Kendomycin-like / aromatic polyketide candidate
Support: hglE-KS + T1PKS architecture; high-priority hybrid locus
Next: LC-MS/MS + DAD/UV + fraction-bioassay linkage
```

Acceptable compact format:

```text
BGC05 | Node_3 · r002 — kendomycin-like aromatic polyketide; hglE-KS + T1PKS support.
```

The lead table should prioritize **why the conclusion was drawn**, not just the predicted label.

### 49.11 Evidence boundary / claim safety

Every format must include claim-safety language.

Required language:

```text
Genome mining indicates biosynthetic capacity, not confirmed compound production or activity attribution. BGC-level claims require orthogonal evidence such as LC-MS/MS, UV/DAD, isotope pattern, fractionation, genetics, purified-compound testing, or NMR.
```

If bioactivity is default-assumed:

```text
MRSA and Candida inhibition are workflow-default extract-level context unless strain-specific assay data are provided. This does not assign activity to any BGC or metabolite.
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

### 49.13 End-of-analysis user prompt

If the package is automatic by default:

```text
The Reader-Facing Front Page and Briefing Package was generated as a default end-of-run deliverable. You can request any of the three formats be omitted from the compiled report or regenerated with uploaded imagery.
```

If imagery is being requested before generation:

```text
The core analysis package is complete. I can also generate the Reader-Facing Front Page and Briefing Package: Editorial Broadsheet, Color Tabloid, and Executive Briefing. You may upload optional host, isolate plate, habitat, microscopy, map, or LC-MS images for these pages. If no images are supplied, I can use a no-image layout or clearly labeled mockup placeholders.
```

### 49.14 v8.1 completeness check

A v8.1 prompt is complete only if it contains:

- [ ] Run Controller / Execution Spine
- [ ] Reader-Layered Output System
- [ ] Triage First Board
- [ ] LC-MS Chemical Handle Module
- [ ] Visual Load Reduction Standard
- [ ] Standard vs Archive-Quality mode distinction
- [ ] Evidence / Claim Separation Card
- [ ] Package Manifest
- [ ] Deferred Ledger
- [ ] Reader-Facing Front Page and Briefing Package
- [ ] Editorial Broadsheet format
- [ ] Color Tabloid format
- [ ] Executive Briefing / Memorandum format
- [ ] Optional imagery upload protocol
- [ ] Simplified Node-label policy with full NODE preservation in technical outputs
- [ ] Raw antiSMASH vs corrected BGC count disclosure
- [ ] Rounded reader-facing genome-statistics policy
- [ ] Priority-lead support fields for compound class/key genes/domains/architecture
- [ ] Evidence Boundary / Claim Safety language in every format



---

## SECTION 50 — v8.2 Compound-Class Coverage + Claim-Safety Patch

### 50.0 Integration status

This section integrates **Sapote Workflow Patch v8.1.1 → v8.2**. It is additive and does not remove or weaken any v8.1.1 detection module. When a rule in this section conflicts with an older v8.1.1 rule, the v8.2 rule takes precedence.

### 50.1 Patch source and insertion map

# Sapote Workflow Patch v8.1.1 → v8.2

**Apply onto:** Sapote Actinomycete Natural Product Discovery Workflow v8.1.1
**Patch version:** v8.2
**Date:** 2026-05-31
**Validated against:** AJS-XXX (marine sponge-associated *Streptomyces*-family actinomycete) — five published compound families used as ground truth.

This single patch consolidates three module additions and one general claim-safety principle. It is additive: it adds compound-class detection (diketopiperazines, linear polyether ionophores), a new optional analytical capability (PKS stereochemistry from domain subtypes), and corrects one prior claim-safety error by promoting it to a standing principle. No v8.1.1 detection module is removed or weakened.

**Insertion map (where each block goes):**

| Block | Target section(s) |
|---|---|
| A. General claim-safety principle (absence of assay ≠ inactivity) | §33.3 (standing principle) |
| B. Diketopiperazine / CDPS detection | §8, §43, §37, §33.3, §34, §45 |
| C. Linear polyether ionophore detection | §8, §42, §37 |
| D. PKS KR/ER stereochemistry reasoning (optional/gated) | §6, §7, §30.1 |
| E. Trigger phrases | Option 3 / module trigger list |
| F. Version history | Version History table |

---

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

Per-module table: module # · AT motif → extender unit · KR present/subtype → predicted β-OH + α-Me config · DH (functional/cryptic) · ER present/residue → α-Me config · predicted module stereochemistry. Conclude with a bioinformatics-predicted planar+stereo hypothesis, explicitly labelled as prediction.

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

```text
Run DKP / CDPS scan on [Strain ID].
Run cyclodipeptide synthase scan on [Strain ID].
Run polyether scan on [Strain ID].
Run polyether ionophore scan on [Strain ID].
Check polyether cassette for [Strain ID] BGC [N].
Run PKS stereo prediction on [Strain ID] BGC [N].
Predict polyketide stereochemistry for [Strain ID] BGC [N].
```

(T43-DKP also fires automatically within the §43 CCTT scan; LMPKS-PE is assigned automatically within the §42 scan.)

---

## BLOCK F — version history entry

| Version | Date | Changes |
|---|---|---|
| v8.2 | 2026-05-31 | **Compound-class coverage + claim-safety patch.** §33.3: promoted "absence of assay ≠ inactivity" to a standing principle with class-context routing (marinolide correction generalized). **DKP-CDPS** added across §8/§43/§37/§33.3/§34/§45: CDPS rule-based / PF16715 diagnostic entry, T43-DKP trigger (gene-beats-cluster), DKP detection rank A–D, strengthened PF00881/CDO specificity guard, dehydro-DKP vs saturated metabolomics rows, no-self-resistance-marker note, cytotoxicity routing (no MRSA/*Candida* bonus). **Linear polyether ionophore** added across §8/§42/§37: LMPKS-PE grade, SMCOG-based cassette detection rule (epoxidase detectable, epoxide hydrolase HMMER-pending), cation-adduct metabolomics row. **PKS KR/ER stereochemistry reasoning** added as optional/gated §6/§7 capability with mandatory hypothesis-not-structure claim-safety (§30.1). Validated against AJS-XXX (photopiperazine confirmed DKP-A by AlbA/AlbC homology; bare CDPS DKP-B/C; ionostatin polyether 7-PKS + KCB anchor; tetrachlorizine and marinolide as bundled examples). No v8.1.1 detection module removed or weakened. |

---

## Validation summary (AJS-XXX, five published families)

| Family | Class | Detection path after patch |
|---|---|---|
| Marinoterpin A–C | meroterpenoid | KnownClusterBlast (BGC0002372) — no new logic needed |
| Ionostatin | linear polyether ionophore | KCB anchor (16 hits, BGC0002446) + new LMPKS-PE / §8 polyether entry |
| Tetrachlorizine | dichloropyrrole alkaloid | KnownClusterBlast (22 hits, BGC0002096); Cl₄ isotope handle; T43-HAL example |
| Marinolide A/B | macrolactone | CLMR Tier-2 literature recovery (KCB miss); Block A → flag as candidate anti-MRSA pending assay |
| Photopiperazine A–D | dehydro-DKP | new T43-DKP / §8 CDPS entry → confirmed DKP-A (AlbA/AlbC homology) |

---

*Sapote Actinomycete Natural Product Discovery Workflow · Patch v8.1.1 → v8.2 · 2026-05-31*

### 50.2 v8.2 completeness check

A v8.2 prompt is complete only if it contains all v8.1.1/v8.1 completeness requirements plus:

- [ ] §33.3 standing principle: **absence of assay is not evidence of inactivity**.
- [ ] DKP/CDPS diagnostic-domain entry in §8.
- [ ] DKP detection rank A–D.
- [ ] T43-DKP trigger in §43.
- [ ] PF00881/CDO specificity guard in §43.3 / §34.
- [ ] DKP and dehydro-DKP metabolomics rows in §37.
- [ ] DKP self-resistance/no-marker rule in §45.
- [ ] DKP wet-lab/mechanistic-link guard in §33.3.
- [ ] Linear polyether ionophore diagnostic-domain entry in §8.
- [ ] LMPKS-PE grade and polyether family mapping in §42.
- [ ] Polyether cassette detection rule using available SMCOG/rule-based tokens and HMMER fallback.
- [ ] Linear polyether metabolomics row in §37, including cation-adduct handling.
- [ ] Optional/gated PKS KR/ER stereochemistry reasoning in §6/§7.
- [ ] Stereochemistry claim-safety language in §30.1.
- [ ] Trigger phrases for DKP/CDPS, polyether, and PKS stereo scans.
- [ ] v8.2 version-history row.

---

*Sapote Actinomycete Natural Product Discovery Workflow · v8.3 candidate · 2026-05-31*

---

## SECTION 51 — Fragmented Large-BGC Rescue (FLBR) v1.0

**Apply onto:** Sapote Actinomycete Natural Product Discovery Workflow v8.2
**Patch version:** v8.3 candidate · **Date:** 2026-05-31
**Validated against:** a six-strain reference set spanning Moderate and Very-Poor assembly tiers (one Moderate-assembly positive correctly retained as STRONG; two Very-Poor-assembly negatives correctly auto-demoted to WEAK). Full per-strain detail is published in the companion data paper.

---

#### 0. What this patch does and why

A biosynthetic gene cluster that is physically larger than the assembly's contig N50 gets shattered across multiple contigs. Each shard then looks like an individually unremarkable, low-KCB-score fragment. Under a per-region, KCB-score-ranked triage these fragments are discarded — yet collectively they are the genetic debris of a large modular assembly line, which is among the highest-value antimicrobial-discovery targets (macrolides, glycopeptides, lipopeptides, polyethers, large NRPS).

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
- **Hybrid handling:** a PKS-NRPS hybrid fragment set is grouped as one candidate even when individual fragments are labelled separately (PKS on one contig, NRPS on another); flag explicitly that a hybrid can masquerade as two unrelated low-score clusters.
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

Any biosynthetic gene cluster larger than the assembly's contig N50 is shattered across contigs, and each shard looks like a forgettable low-score fragment until the fragments are read together as the debris of one large machine.

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

FLBR never claims a compound. Its output is a **sequencing and prioritization decision**: "this strain harbours large modular megasynthase capacity, fragmented by the assembly; here are the contigs likely to join; long-read sequencing is Priority 1." Compound-class language stays at the family level the KCB anchors support, and all the standard claim-safety rules continue to apply.

#### 6. Scope boundary

FLBR's STRONG markers (docking, TE) exist only in assembly-line megasynthases, so the scope is T1PKS + modular NRPS + PKS-NRPS hybrid + trans-AT. Other large clusters that also fragment (saccharide, large lanthipeptide, type II PKS) lack inter-subunit docking domains and cannot use the STRONG track; they are out of scope for this patch. A future extension could give them a class-appropriate weak-track marker, but conflating them now would dilute the strong call.

---

### 51.12 Validation Appendix — FLBR design rationale

**Companion to:** §51 FLBR v1.0 · **Date:** 2026-05-31

The two-tier design was validated on a six-strain reference set with two contrasting assembly conditions. Full per-strain data are published in the companion data paper; the logic is summarised here.

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
**Validated against:** 25 lanthipeptide regions across 9 strains from the reference collection, spanning all four assembly tiers (Good, Moderate, Poor, Very-Poor). Full per-strain data are published in the companion data paper; the aggregate result and diagnostic outcomes are summarised below.

---

## §52.1 Purpose and placement

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
5. **Claim ceiling.** Any reported candidate is labelled `candidate maturation protease, family
   X, genome-wide, specificity-unverified`. No precursor–protease pairing is asserted.

### §52.4.3 Heteromeric guard (M16B)

The M16B maturase is a **heterodimer** (catalytic HXXEH subunit + R/Y substrate-binding
subunit). A lone M16-family gene is half a maturase. When reporting an M16 candidate, note
whether a plausible partner subunit is adjacent; a solitary subunit is a weaker candidate than
an adjacent pair and must be labelled as such.

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

| Version | Date | Notes |
|---|---|---|
| UMED v1.0 | 2026-05-31 | Initial parent concept + lanthipeptide-protease instance. Family library (LanP/S8, LanT/C39, FlaP-AplP/S9, M16B). Two-axis output; single-genome scope boundary; heteromeric M16B guard; Very-Poor→missingness gate; hard specificity-unverified ceiling. Method basis Xue et al. 2022 (DOI 10.1038/s41467-022-29325-1; PMID 35347143). Validated on 25 lanthipeptide regions / 9 project genomes (88% maturation-gap). RiPP-extensible parent; no other instance validated. |

---

## §52.11 Validation Appendix — UMED across 16 project genomes

All antiSMASH v8.0.4. 16 genomes scanned; 9 carry lanthipeptide regions (25 total).

**Headline:** 22 of 25 lanthipeptide regions (88%) lack an in-cluster maturation protease — even
higher than the ~⅓ genome-wide figure of Xue et al., consistent with this project's heavy
class III/IV/V actinomycete content (the paper's hardest cases). A "complete" antiSMASH
lanthipeptide call in this dataset is usually a maturation-incomplete pathway.

### Per-region result

| Strain | Tier | Node | Class | UMED status |
|---|---|---|---|---|
| Assembly tier | Node | Class | UMED status |
|---|---|---|---|
| Poor | NODE_A | I | GAP (1 genome-wide candidate) |
| Poor | NODE_B | I | GAP (1) |
| Poor | NODE_C | III | GAP (2) |
| Poor | NODE_D | I | GAP (2) |
| Moderate | NODE_E | II | **IN-CLUSTER: FlaP/AplP (S9)** |
| Moderate | NODE_F | III | GAP (3) |
| Moderate | NODE_G | II | GAP (4) |
| Moderate | NODE_H | II | GAP (4) |
| Very-Poor | NODE_I | II | GAP (3) |
| Very-Poor | NODE_J | IV | **IN-CLUSTER: FlaP/AplP (S9)** |
| Very-Poor | NODE_K | II | GAP (3) |
| Moderate | NODE_L | I | GAP (2) |
| Moderate | NODE_M | III | GAP (2) |
| Moderate | NODE_N | I | GAP (2) |
| Moderate | NODE_O | IV | GAP (2) |
| Poor | NODE_P | V | **IN-CLUSTER: M16 metallopeptidase** |
| Poor | NODE_Q | I | GAP (1) |
| Poor | NODE_R | IV | GAP (3) |
| Poor | NODE_S | II | GAP (3) |
| Poor | NODE_T | III | GAP (3) |
| Poor | NODE_U | III | GAP (3) |
| Very-Poor | NODE_V | I | **GAP — no candidate in assembly** |
| Very-Poor | NODE_W | IV | **GAP — no candidate in assembly** |
| Very-Poor | NODE_X | I | **GAP — no candidate in assembly** |
| Very-Poor | NODE_Y | II | **GAP — no candidate in assembly** |

*Strain identifiers are omitted from the public release. Full identifiers are in the companion data paper.*

### Gap rate by class

| Class | Gap / total |
|---|---|
| class I | 8/8 |
| class II | 6/7 |
| class III | 5/5 |
| class IV | 3/4 |
| class V | 0/1 |

### Three diagnostic outcomes

1. **In-cluster positives (controls).** Three regions across two strains (one Moderate, one Poor assembly) carry their maturation protease in-cluster — UMED correctly reports them as maturation-autonomous. In-cluster types observed: FlaP/AplP (S9-family serine protease, classes II and IV) and an M16 metallopeptidase (class V). The M16 case is notable: it is the family newly characterised by Xue et al. 2022, and it is paired with a class V lanthipeptide — a class not included in that paper's analysis.
2. **Genome-wide-candidate gaps (the common case).** 18 GAP regions have 1–4 candidate proteases elsewhere in the genome — the exact unclustered-maturase scenario UMED is built for, each a coherent co-expression / heterologous-expression follow-up target. None is asserted as the maturase; all carry the specificity-unverified ceiling.
3. **No-candidate gaps (missingness, not absence).** Four regions from one Very-Poor assembly return no candidate genome-wide. UMED reports these as `GAP — no candidate in assembly` missingness items, not as proof the producer lacks a protease. This is the §52.4.2 assembly-quality gate doing its job, and the direct analogue of the FLBR Very-Poor demotion.

### Claim-safety note

Every GAP candidate above is a lead, not a maturase assignment. Per §52.2, single-genome
presence cannot establish the precursor–protease specificity the source method requires;
confirming any pairing needs cross-genome correlation, co-expression, and in vitro proteolysis
as in Xue et al. 2022.

---

*Sapote Actinomycete Natural Product Discovery Workflow · §52 UMED v1.0 · 2026-05-31*

---


## SECTION 53 — Marker Addenda and Block Registry (v8.x consolidated)

> **[ARCHIVED — v8.x consolidation, superseded.]** Marker vocabulary now formalised in mamey/mamey_markers.py and the active CCTT patterns in mamey/source_scans.py. This section is maintenance history; do not use it as the authoritative marker list.

*The per-class detection blocks for compound classes beyond DKP and linear polyether are documented
in the following sections and in the retired v8.10.2 monolith (not carried forward into this bundle).
Blocks G–L (lasso peptide, TOMM, NN-diazo, tetronate, PTM/HSAF, thioamitide) are cross-referenced
in §57 sub-grade tables and in the CCTT registry (MMK-CCTT-001 through MMK-CCTT-015).
T43-TOMM (MMK-CCTT-015) was restored to the formal registry in v9.3.*

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
- **A12** ● Ecological evidence matrices (substrate-signal + host-pathogen defence)
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

# SECTION 56 — Known-Outcome Producer-Genome Benchmarking and Reference Genome Controls

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

This is a dedicated subpanel because the user's reference project includes Candida bioactivity and because nucleoside/peptidyl-nucleoside BGCs are easy to under-rank when antiSMASH labels are generic.

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

Streptomycin carve-out: StrB1/StrK present → AMC-B regardless of DOIS absence. **Trap:** standalone DOIS in housekeeping neighbourhood is AMC-C.

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

VanHAX HGT guard (GLY-A): integrase/transposase within 5 kb without biosynthetic neighbours = HGT island, excluded; different contig = GLY-B. **Trap:** Cglyc-type (HHILLDG) required; enduracididine (TIGR04462/60) and mannopeptimycin (TIGR01720×2) are distinct classes.

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
| **PTM-A** | Ornithine A-domain (Stachelhaus vs HslO/HslI) **+ iterative PKS-NRPS confirmed** (one KS reused, multiple downstream ACP / high KS:ACP ratio). Optional class-consistent tailoring. | HIGH | HIGH | 4–5 | §33.3 Candida link +2 WL when Candida confirmed/default. Acid-labile tetramate: no pH<4 extraction. |
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
