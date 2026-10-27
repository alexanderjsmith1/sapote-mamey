# Monolith design history

Historical release, session and layout designs. Use [the current rules reference](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md) and its linked operational contracts for current work. Archived instructions do not expand the user's task.

# SECTION -2 — v9.2 Bundle Hardening Patch / Release Bridge

## -2.0 Purpose

v9.2 is not a science-module expansion. It is a **bundle-hardening patch**. Its purpose is to make the monolith usable as the parent controller for the repository bundle without letting prose silently outrun the executable kernel. v9.1 established the Mamey-first / Sapote-second architecture; v9.2 adds release gates, derived-prompt generation rules, test expectations, and code/document synchronization rules.

**Central rule:** the monolith may define the desired contract, but the bundle release is valid only when documentation, prompts, workbook schema, executable behavior, and tests agree.

## -2.1 Historical parent-controller design

The following block records the v9.2 design and is historical, not a session instruction.
Current operational authority is `AGENTS.md` and `docs/ASSISTANT_GOVERNANCE.md`, within the user's authorized task. Derived prompts must respect that authority.

The historical design specified:

```text
Active parent controller: docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md
Legacy monoliths: archived / historical only
Derived prompts: regenerated from the active parent controller
Executable code: Mamey kernel; not overwritten by prose without tests
```

Do not keep v8.1.1, v8.4 candidate, v9.0, v9.1, and v9.2 as parallel active instructions. Older monoliths may remain in `docs/history/` with a clear `HISTORICAL_DO_NOT_USE_AS_CONTROLLER` banner.

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
[ ] Old monoliths moved to docs/history/ or marked historical.
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

1. Check the current input contract before promising a public-accession run.
2. The bundled `run --accession` option is a placeholder: without `--input-zip`, the CLI returns `UNSUPPORTED_ACCESSION_MODE`. Its presence in help is not accession-fetching support.
3. The extraction inputs are existing antiSMASH ZIPs: `--input-zip` selects one and `--strains` selects a batch. Fetching a genome and running antiSMASH preprocessing require a separately selected workflow and inputs.
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
2. Move prior active monoliths to `docs/history/` with `HISTORICAL_DO_NOT_USE_AS_CONTROLLER` banner (completed v9.3).
3. Generate the five derived prompt/doc files in §-2.8.
4. Update `README.md` to say Mamey is deterministic extraction and Sapote is interpretation.
5. Update `RELEASE_MANIFEST.md` with release profile and known limitations.
6. Verify `mamey_run.py --help` against documented run modes and arguments.
7. Verify workbook schema docs/templates against actual produced workbook columns.
8. Add tests or manual validation files for the minimal test matrix.
9. Build release ZIP.
10. Run smoke/gold validation and record results.

---

## -1.0 Purpose

This v9.2 candidate is the **bundle-first monolith**. It keeps the v8.4 Sapote scientific logic, but adds the missing execution architecture that the software bundle now needs: deterministic extraction first, interpretive judgment second, workbook write-back third, and explicit batching/resume state throughout.

This monolith is intended to replace scattered prompt fragments in the Sapote-Mamey bundle. It does **not** replace executable code. It is the controlling specification that tells ChatGPT, Claude, or another analyst how to use the bundle correctly, what must be produced, what may be deferred, and how claims are bounded.

## -1.4 Bundle session-start handshake

At the start of every bundle run, state the following before doing analysis:

```text
BUNDLE SESSION HANDSHAKE
Bundle/version loaded: [repo/bundle name and version]
Input ZIPs detected: [N]
Master workbook detected: [yes/no + filename]
Committed strain count this session: [N]
Deferred strain count: [N]
Run mode: [gold/sapote_standard/sapote_archive/project_merge]
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

## -1.9 Batch continuation protocol

When the user says “continue,” do not restart from scratch. Do this:

1. Locate the latest checkpoint and final ZIP/package in the current session.
2. Read the checkpoint and identify the next `MAMEY_DEFERRED`, `MAMEY_FAILED`, or missing required strain/BGC.
3. Continue from the next unfinished item.
4. Rebuild only changed artifacts plus the final handoff ZIP.
5. Report exactly what changed since the previous ZIP.

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
3. **Run document consistency check.** Search the repo for stale terms and conflicting instructions: `v8.1`, `Davey`, `optional RG-GMCI`, `PENDING`, `Full Coverage Mode`, and outdated workbook tabs. (Do not flag `Bert` — live literature-mode feature; or `v8.4 candidate` — intentional backward-compat triggers in §0/§0.11.)
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

Design vocabulary: only `UNSUPPORTED_ACCESSION_MODE` above is emitted by the current CLI. Every `MAMEY_FAILED` row must include one failure code, a human-readable reason, and a recovery action.

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
- [ ] Gold mode produces the ten required scan statuses.
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

-1. [Bundle Kernel / All-in-One Replacement Layer](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section--1--bundle-kernel--all-in-one-replacement-layer)
  - -1.12 Bundle file-map and replacement protocol
  - -1.13 Bundle update workflow after monolith finalization
  - -1.14 Batch Controller v2 — committed work units
  - -1.15 Failure taxonomy and recovery actions
  - -1.16 Minimum scan-state schema
  - -1.17 Workbook merge contract v2
  - -1.18 Claim boundary matrix
  - -1.19 Derived prompt targets
  - -1.20 Release-readiness checklist

0. [Run Controller / Execution Spine](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-0--run-controller--execution-spine)
0.5. [Reader-Layered Output System](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-05--reader-layered-output-system)
0.6. [Triage First Board](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-06--triage-first-board)
0.7. [LC-MS Chemical Handle Module](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-07--lc-ms-chemical-handle-module)
0.8. [Visual Load Reduction Standard](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-08--visual-load-reduction-standard)
0.9. [Standard vs Archive-Quality Full Analysis](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-09--standard-full-analysis-vs-archive-quality-full-analysis)
0.10. [Evidence / Claim Separation Card](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-010--evidence--claim-separation-card)
0.11. [Package Manifest and Deferred Ledger](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-011--package-manifest-and-deferred-ledger)

1. [Purpose](#purpose)
2. [How to Use This Prompt](#how-to-use-this-prompt)
3. [Global Data Governance Rules](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#global-data-governance-rules)
4. [Full Analysis Mode — Active Override](#full-analysis-mode--active-override)
5. [§2B Batch Plan Protocol](#2b--batch-plan-protocol)
6. [Session Startup Checklist](#section-1--session-startup-checklist)
6. [Input File Inventory and Source Roles](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-2--input-file-inventory-and-source-roles)
7. [antiSMASH ZIP / JSON Parsing Pipeline](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-3--antismash-zip--json-parsing-pipeline)
8. [Assembly, BGC Inventory, RiQ, and Corrected BGC Counts](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-4--assembly-bgc-inventory-riq-and-corrected-bgc-counts)
9. [KCB Sweep Module](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-5--kcb-sweep-module)
10. [Domain-Level Analysis](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-6--domain-level-analysis)
11. [NRPS/PKS Module Architecture](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-7--nrpspks-module-architecture)
12. [Diagnostic Domain Combinations](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-8--diagnostic-domain-combinations)
13. [TTA Codon / bldA Gating](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-9--tta-codon--blda-gating)
14. [TFBS Signals and Induction Conditions](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-10--tfbs-signals-and-induction-conditions)
15. [Dereplication Verdicts and Novelty Language](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-11--dereplication-verdicts-and-novelty-language)
16. [Coverage and HGT Flags](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-12--coverage-and-hgt-flags)
17. [Neighborhood Comparison and Medium-BGC Rescue](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-13--neighborhood-comparison-and-medium-bgc-rescue)
18. [Taxonomy Integration](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-14--taxonomy-integration)
19. [Strain-Level Deliverables](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-15--strain-level-deliverables)
20. [Cross-Habitat Figures](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-16--cross-habitat-figures)
21. [Ecological Synthesis Module](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-17--ecological-synthesis-module)
22. [Excel Deliverables](#section-18--excel-deliverables)
23. [Manuscript Update Procedure](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-19--manuscript-update-procedure)
24. [Glossary and Layperson Explanation Workflow](#section-20--glossary-and-layperson-explanation-workflow)
25. [Verified Literature Deep Dive v2.0](#section-21--verified-literature-deep-dive-v20)
26. [Rapid Literature Deep Dive v2.0](#section-22--rapid-literature-deep-dive-v20)
27. [Mode Selection Decision Tree](#section-23--mode-selection-decision-tree)
28. [Cross-Strain Comparison Module](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-24--cross-strain-comparison-module)
29. [Key Scientific Findings to Preserve](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-25--key-scientific-findings-to-preserve)
30. [Reference Implementations](#section-26--reference-implementations)
31. [Output Audit Log Template](#section-27--output-audit-log-template)
32. [File Naming Conventions](#section-28--file-naming-conventions)
33. [CDSW Protocol Summary](#section-29--cdsw-protocol-summary)
34. [Output Quality Assurance Gates](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-30--output-quality-assurance-gates)
35. [BGC Architecture Confidence System](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-31--bgc-architecture-confidence-system)
36. [Evidence Traceability Blocks](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-32--evidence-traceability-blocks)
37. [Wet-Lab Decision Matrix](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-33--wet-lab-decision-matrix)
38. [Diagnostic Signature Weighting + antiSMASH Hallucination-Trap / Claim-Calibration Audit](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-34--diagnostic-signature-weighting--antismash-hallucination-trap--claim-calibration-audit)
39. [Cross-Strain BGC Family Clustering Hook](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-35--cross-strain-bgc-family-clustering-hook)
40. [Reviewer Attack Simulation](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-36--reviewer-attack-simulation)
41. [Metabolomics Readiness Module](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-37--metabolomics-readiness-module)
42. [Known Missingness Tracking](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-38--known-missingness-tracking)
43. [Figure Suggestion Module](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-39--figure-suggestion-module)
44. [Project Memory Snapshot](#section-40--project-memory-snapshot)
45. [Cross-Comparative Synthesis Module](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-41--cross-comparative-synthesis-module-ccsm-v11)
46. [Large Modular PKS Rescue Workflow](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-42--large-modular-pks-rescue-workflow-lmpks-rw-v10)
47. [Cryptic-Class / Tailoring Trigger Module](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-43--cryptic-class--tailoring-trigger-module-cctt-v10)
48. [Chitin / Glycan-Active Defense Module](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-44--chitin--glycan-active-defense-module-cgad-v10)
49. [Resistance Gene-Guided Compound Class Confirmation](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-45--resistance-gene-guided-compound-class-confirmation)
50. [Standalone Prompt Completeness Check](#standalone-prompt-completeness-check)
51. [Reader-Facing Front Page and Briefing Package](#section-49--reader-facing-front-page-and-briefing-package)
52. [v8.2 Compound-Class Coverage + Claim-Safety Patch](#section-50--v82-compound-class-coverage--claim-safety-patch)
53. [§51 Fragmented Large-BGC Rescue (FLBR)](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-51--fragmented-large-bgc-rescue-flbr-v10)
54. [§52 Unclustered Maturation Enzyme Detection (UMED)](../SAPOTE_MAMEY_BUNDLE_MONOLITH.md#section-52--unclustered-maturation-enzyme-detection-umed-v10)

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
Run standard full analysis on [Strain ID]. [Taxonomy]. [Host/source]. [Bioactivity]. Apply architecture confidence, evidence traceability, wet-lab decision scoring, hallucination-trap audit, metabolomics readiness, reviewer attack simulation, resistance gene confirmation, UMED maturation-enzyme detection, PDF Style Standard, typed bioactivity metadata and missingness, and project memory snapshot. Use single-pass execution if feasible; otherwise run in batches but preserve the final compiled deliverable plan.
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
- [ ] **Typed bioactivity metadata recorded**: metadata_state, observation_state, supplied assay/source receipt and NOT_ESTABLISHED linkage; absent data remain NOT_SUPPLIED without inventing a target.
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

## Full Analysis Mode — Active Override

Sapote v8.0 uses **Standard Full Analysis** as the default full-run behavior. Standard Full Analysis accounts for every BGC but gives full Mode B treatment only to triage-selected top candidates, while routing lower-priority or fragmentary entries to abbreviated ledger entries and the Archive Appendix.

**Archive-Quality Full Analysis**, when explicitly selected, requires the requested BGC roster’s current-profile authored cards, batching as needed. Historical §1–§8 is a legacy scaffold, not current full48/current50_v2 completion.

Full Analysis Mode remains an active override against accidental omission: every BGC is accounted for in the inventory, triage, ledger, or archive plan. Priority tiers determine output depth and routing in Standard mode; they do not permit silent omission.

| Mode | Meaning | When to use |
|---|---|---|
| **Standard Full Analysis** | Reader-layered, triage-first report. All BGCs accounted for; top candidates receive full Mode B; remaining BGCs receive abbreviated ledger entries unless elevated by triggers. | Default for `Run v8.0 full analysis`, `Run the workflow`, and routine strain analysis. |
| **Archive-Quality Full Analysis** | Exhaustive selected-roster interpretation using the current named Mode B profile, gene-by-gene evidence, archive and explicit holds; verify actual authored files under that same contract. | Use when the user explicitly selects this scope; an old eight-section scaffold is insufficient. |
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

**Context window and batch execution:** Archive-Quality Full Analysis for strains with more than approximately 15 BGCs typically requires multiple sessions. This is expected and correct behavior, not a failure mode. Do not reduce analytical depth in Archive-Quality mode to fit a single session. Batch instead.


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
Prior session(s) completed: [source-bound full locus identities and authored-profile verification receipts].
This session: BGC[list].
Project Memory Snapshot loaded: [Strain ID]_Project_Memory_Snapshot_[date].json
Proceeding to BGC[first BGC of this batch].
```

Load the Project Memory Snapshot before resuming. Do not re-run assembly statistics, KCB sweep, TFBS extraction, or hallucination-trap audit unless new data has been uploaded since the prior session. Those outputs carry forward.

### Batch session end format

At the end of every batch session, produce a Batch Session Summary before presenting files:

```text
Batch [X] complete.
Loci completed this session: [full source-bound identities, selected contract and actual authored-file verification state].
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

1b. **Record supplied provenance and typed bioactivity metadata.** Retain confirmed or uncertain host/source as declared; absence does not establish a terrestrial or marine origin. With no supplied bioactivity data, use NOT_SUPPLIED / NOT_OBSERVED, no assay targets and NOT_ESTABLISHED locus/compound linkage. Supplied observations remain strain/extract context. Continue within the user’s authorized scope where missing fields are not required; clarify only a material unresolved input.

1c. **Run Metadata Conflict Audit.** Compare current-session strain metadata against uploaded files, master tables, prior reports, project-memory snapshots, reference implementation rows, and model memory. If host/source, habitat category, taxonomy, bioactivity, assembly quality, or prior BGC highlights conflict, treat current-session user confirmation as highest priority unless the user says otherwise; log the conflict; mark affected ecology, CCSM, cross-habitat, and manuscript-facing claims as `metadata-sensitive`; and do not reuse prior habitat-specific claims until reconciled.

1d. **Check for active Batch Plan.** Search the Project Memory Snapshot and any prior session outputs for an active Batch Plan for this strain. If one exists, state: "Active Batch Plan found — Batch [X] of [Y]. Prior session completed: BGC[list]. This session: BGC[list]. Proceeding." If no Batch Plan exists and the strain has more than 15 BGCs, announce a new Batch Plan before starting Mode B work.

1f. **Preserve the producing inventory’s identity map.** The current constructor reads admitted GenBank records, orders explicit chromosome labels before plasmid labels and then unknown/contradictory labels, with lexical source-name ordering within groups. It deduplicates its explicit record/region/bounds/products key before assigning sequential `BGC001` aliases. This is not JSON FASTA-input order and a changed admitted source set can change aliases.

Copy each individual locus as `strain / full node-or-contig / region / BGC alias` from one bound source record, with archive/member hashes. Do not renumber a saved package, invent a missing component or infer that an alias identifies the same physical locus across re-extractions. Reconcile the source map before cross-session reuse; keep missing/conflicting identity as a hold.


2. **Load the bound package manifest and any authored session snapshot.** The native `[Strain ID]_Project_Memory_Snapshot.json` is an undated alias stub pointing to `manifest.json`; follow `alias_of`. The dated snapshots in §40 are an authored design, not an automatically generated narrative history. Confirm strain, source hashes and actual saved context before resuming.
3. **Load master JSON** if working project-wide.
4. **Load strain tables** if updating bioactivity, taxonomy, or host metadata.
5. **Load antiSMASH ZIP** if performing strain-level analysis. When loading the ZIP, verify whether GBK region files are present (files named `*.region001.gbk`, `*.region002.gbk`, etc. inside the strain subfolder). These are the fallback source for TTA/bldA gating and HGT transposase scanning when JSON modules are incomplete. Note their presence or absence explicitly in the context acknowledgement.
6. **Load manuscript** if editing or rewriting manuscript text.
7. **Acknowledge context.** State what has been loaded, what is missing, and what the session will cover.
8. **Confirm source-of-truth order.**
9. **Use the current handoff policy in [AGENTS.md](../../AGENTS.md).** Keep routine replies concise; offer distinct next paths only when useful and follow the user’s requested format.

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
└─ Verified Literature Deep Dive v2.0 → verified bibliography + anchored summaries

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

- Producing inventory identity map: [source archive/member paths and SHA-256; actual admitted-source ordering; strain / full node-or-contig / region / BGC alias from the bound record]. Do not infer alias identity from JSON order or reuse it across changed source sets without reconciliation.

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
| v7.4 Supplement PDF | `[Strain ID]_v7.4_Supplement_YYYY-MM-DD.pdf` |
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

For the current session/handoff policy use [AGENTS.md](../../AGENTS.md#next-paths-automatic-save-state-and-transcripts). Recover source-bound context and report the requested result, supporting evidence and unresolved holds. Routine handoffs need at most one useful next action; major deliveries or explicit plans may include distinct options when helpful, following the user’s requested format. The paths below are historical examples to select from when relevant.

**Suggested next paths (after strain analysis):**
- Path A: Upload new antiSMASH ZIPs and update master JSON
- Path B: Build or rebuild cross-habitat figures
- Path C: Write Results/Discussion manuscript sections
- Path D: Run Verified Literature Deep Dive bibliography for priority BGC classes
- Path E: Build layperson glossary and fermentation cards
- Path F: Run CCSM Phase 2 (within-habitat) or Phase 3 (cross-habitat) using Section 41

**For an authorized batch:** report the next unfinished item from the actual batch plan, with complete source-bound locus identities. Keep the selected scope and current named Mode B contract; the historical §1–§8 treatment and optional-path count do not establish current completion requirements or authorize every-locus authoring.

CDSW modification command: `CDSW modification: [instruction]`

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
    "schema_version": "bioactivity_metadata_v1",
    "metadata_state": "NOT_SUPPLIED",
    "observation_state": "NOT_OBSERVED",
    "usage_scope": "PRODUCTION",
    "assays": [],
    "compound_linkage": "NOT_ESTABLISHED",
    "warnings": []
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
- project-specific assumptions outside labeled worked examples

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
- Smoke-test mode is clearly labeled as incomplete.
- LMPKS Rescue has a guardrail preventing PKS over-calling.
- FLBR §51 is present, runs before final megasynthase priority assignment, and includes STRONG/WEAK tiers, assembly-quality gate, double-docking carve-out, NRPS/hybrid sibling logic, audit-log language, and QA gate 30.11.
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
- **Abbreviated ledger entry minimum fields are defined in §0.9** (8 required fields; satisfies Run Controller treatment-status non-negotiable).
- **Triage First Board parallel-scan dependency is explicit in §0.6 Required Timing** (all ten first-pass checks must complete before the board is generated).
- **Layer C content is explicitly defined for both Standard and Archive-Quality modes in §0.5.**
- **Chemical handle status line is present in the §0.6 Candidate Card format** (connects §0.7 identity-safety rule to the first output layer where handles appear).
- **§33.3 includes the §46 chemical handle WL modifier table inline** (no cross-reference lookup required during scoring).
- **CGAD Step 0 proteome scope check is defined in §44.1A** and distinguishes `full proteome scanned`, `BGC-region only`, and `full proteome unavailable` states.
- **§34 includes the BGC-local null misread as genome-wide null hallucination trap.**
- **§38.2 includes the Proteome scope limitation missingness category.**
- **§17.2A distinguishes BGC-local evidence from genome-wide functional scan evidence.**
- **§44.5 includes the DasR/NagR coupling guard requiring full-proteome CGAD before genome-level substrate-supply claims.**

- [ ] §1 preserves the actual producing inventory’s source-bound alias map and complete
      strain / full node-or-contig / region / BGC alias; it does not reassign JSON-order IDs.
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
| v5.3 | 2026-05-26 | Strain-level analysis: JSON-first parsing, KCB sweep, TTA/bldA, tiered dereplication, HGT scan, neighborhood comparison, POOR assembly protocol, VLD / RLD v2.0. |
| v6.0 | 2026-05-27 | Consolidated project-wide v1.1 with v5.3 strain modules; Full Analysis Mode override; KCB/TTA/HGT/dereplication modules; fermentation card; standardized audit/file-naming. |
| v6.1 | 2026-05-27 | Compiled PDF must include production TOC with page numbers. |
| v6.2 | 2026-05-27 | Ecological synthesis claim-safety parent policy; cross-habitat comparison flags; fast ecological synthesis trigger. |
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
| v7.9.1 | 2026-05-30 | **Compound class coverage patch — 10 items across 6 sections.** Triggered by post-hoc identification of a split indolocarbazole BGC in AS-XXX (NODE_182 indsynth E=0 BS=1349.6 + NODE_105 Trp_halogenase BS=567.6) that was undetected by all prior workflow runs despite being present in the antiSMASH GBK files. Systematic gap review identified 9 further items. **§8:** MODIFIED existing glycosylated T2PKS entry to cross-reference new disambiguation; ADDED 7 new entries: indolocarbazole (indsynth marker), HSAF/PTM (ornithine A-domain + iterative PKS-NRPS), mannopeptimycin (TIGR01720 ×2; as distinct from enduracididine), carbapenem (CarB/CarC), ansamycin (AHBA synthase PF06353 + aminoDAHP/aminodehydroquinase context), angular T2PKS (+ angular-fold oxygenase), linear T2PKS (+ linear cyclase). **§26:** UPDATED AS-XXX reference entry with NODE_182/105 indolocarbazole split-pathway candidate. **§33.3:** ADDED HSAF/PTM as Candida-specific mechanistic link (+2 WL); ADDED explicit exclusion of indolocarbazoles from the Candida mechanistic link category. **§34:** ADDED 3 new traps: "indole masking indolocarbazole"; "ectoine masking showdomycin"; "saccharide BGC as split-pathway glycosylation arm." **§37:** ADDED 5 new class rows: indolocarbazole (cytotoxicity caution mandatory), HSAF/PTM (acid-labile tetramate ring noted), prodiginine (visual plate screen as primary detection), ansamycin (color handle noted), showdomycin (C18 reversed-phase explicitly flagged as insufficient). **§43:** ADDED T43-IDC (indolocarbazole, indsynth ≥500 single-marker trigger); ADDED T43-PTM (HSAF/PTM, ornithine A-domain + iterative PKS trigger; Candida mechanistic link activates +2 WL bonus); MODIFIED T43-AMC to add mandatory streptomycin-class carve-out preventing false DOIS rule-out. |
| v8.0 | 2026-05-30 | **Execution and readability integration.** Added Run Controller / Execution Spine (§0); Reader-Layered Output System (§0.5); Triage First Board (§0.6); LC-MS Chemical Handle Module (§0.7); Visual Load Reduction Standard (§0.8); Standard vs Archive-Quality Full Analysis distinction (§0.9) - **Standard Full Analysis is now the default, overriding the v7.8 Full Depth unconditional default**; Evidence / Claim Separation Card (§0.10); Package Manifest and Deferred Ledger (§0.11); §46 v8.0 Execution and Readability Integration Supplement (chemical handle WL modifiers, PDF/QA integration, §37 and §43 CCTT integration, v8.0 completeness check). No v7.9.1 detection modules modified or removed. |
| v8.0.1 | 2026-05-30 | **Specification refinement patch - 7 items.** R1 (§0.9): Abbreviated ledger entry minimum fields defined - 9-field table prevents variable abbreviated-entry content across runs. R2 (§33.3): §46 chemical handle WL modifier table added inline - eliminates need to cross-reference §46 during WL scoring. R3 (§0.6): Triage First Board parallel-scan dependency made explicit in Required Timing - board requires all six parallel first-pass scans. R4 (Option 6): Top-3 Triage First Board entries with class-level chemical handles added to smoke-test minimum outputs. R5 (§0.5): Layer C content for Standard and Archive-Quality modes explicitly defined - removes ambiguity about abbreviated ledger vs full Mode B in Layer C. R6 (Version History): v8.0 and v8.0.1 rows added to main version history table. R7 (§0.6): Chemical handle status line added to Candidate Card format - connects §0.7 identity-safety rule to the first output layer where chemical handles appear. Header version number updated to 8.0.1. Patch note block updated. Standalone Prompt Completeness Check updated. |
| v8.0.2 | 2026-05-30 | **CGAD genome-wide proteome scope patch.** Added required §44.1A Proteome Scope Check before CGAD verdicts; defined `full proteome scanned`, `BGC-region only`, and `full proteome unavailable` states; required full-record CDS/proteome scanning from antiSMASH GBK `/translation=` fields when available, with Prodigal/Prokka protein FASTA fallback; added motif-vs-HMMER claim-language tiers for GH18/GH19/AA10 calls; updated §44.4 CGAD output table with scope/method/confidence fields and state-aware verdict language; added §44.5 DasR/NagR coupling guard; added §34 trap for BGC-local null misread as genome-wide null; added §38.2 Proteome scope limitation missingness category; updated §17.2A to distinguish BGC-local evidence from genome-wide functional scan evidence; updated Run Controller and §0.6 timing to require CGAD proteome scope state before Triage First Board; updated Standalone Prompt Completeness Check. Prior BGC-region-only CGAD nulls must be reclassified as `Not Assessable pending proteome rescan`. |
| v8.0.3 | 2026-05-30 | **9-item patch from ICBG1735 WFA test case.** (1) Canonical BGC ID convention: JSON FASTA-input order; always paired with contig·region (§1, §4, §27, §28). (2) Ecological hypothesis citation field: required Supporting literature with evidence-grade labels (§17.10, §30.4). (4) Arylpolyene (APE_KS2) class entry (§8, §37). (5) CGAD HMMER-unavailable motif fallback protocol with claim-language tiers (§44.1A, §38.2). (6) QS signal compound routing: hserlactone/BDSF/butyrolactone → Ecological Synthesis only, no mechanistic link WL bonus (§33.3). (7) Two Gram-negative KCB false-positive traps: plant glucosinolate and actinomycete kingdom-mismatch (§34). (8) Mode B §4 citation requirement with evidence-grade labelling (§30.1). (9) Multi-siderophore capacity flag: ≥3 siderophore BGCs → iron-acquisition table + §17.10 hypothesis (§17.4, §17.8A). (10) Phenazine→Escovopsis attine-context specificity guard: class analogy label required; direct-evidence labels for pyrrolnitrin and occidiofungin/burkholdine (PMID 33962985) (§33.3, §17.6). Item 3 (non-actinomycete startup declaration) deferred. Test-ready parent policy also adds §14 taxonomy preflight support for assembled FASTA users: optional ContEst16S/EzBioCloud 16S extraction, BLAST genus anchoring, and species-level claim guardrails. |

---

*Sapote Actinomycete Natural Product Discovery Workflow · v8.3 candidate · 2026-05-31*

---

## SECTION 46 — v8.0 Execution and Readability Integration Supplement

> **[ARCHIVED — v8.0 parent policy, superseded.]** Content integrated into §0–§0.11 (execution spine) and §0.8 (visual load standard) in v9.x. Retained for version history only; not an active instruction set.

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

## SECTION 47 — v8.0.2 CGAD Genome-Wide Proteome Scope Supplement

> **[ARCHIVED — v8.0.2 parent policy, superseded.]** CGAD proteome-scope rule now lives in §44 (active CGAD module). Retained for version history only.

### 47.1 Purpose

This parent policy documents the v8.0.2 boundary correction for CGAD. CGAD declares itself a genome-wide ecological-capacity module, so it must not be scored from BGC-local cluster_hmmer evidence alone. The ICBG1735 test case showed the failure mode clearly: a BGC-region-only scan produced `Not Assessable` / apparent null chitinase evidence, while full-proteome extraction from antiSMASH GBK `/translation=` fields revealed multiple secreted GH18 candidates. This is a module-definition issue, not a rare edge case.

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

## SECTION 48 — v8.0.3 ICBG1735 Workflow-Flexibility Supplement

> **[ARCHIVED — v8.0.3 parent policy, superseded.]** Workflow-flexibility guidance folded into §23 (mode selection) in v9.x. Retained for version history only.

### 48.1 Purpose

This parent policy documents the v8.0.3 patch set derived from the ICBG1735 *Burkholderia* sp. (*Atta* sp.) workflow-flexibility assessment. The patch strengthens cross-session BGC identifiers, non-actinomycete/Gram-negative safety rails, ecological-citation discipline, CGAD fallback behavior, and wet-lab scoring specificity without weakening the existing actinomycete discovery workflow.

A test-ready taxonomy preflight note has also been added to §14 so assembled-FASTA users can extract 16S candidates with ContEst16S/EzBioCloud, BLAST those sequences for genus anchoring, and keep species-level claims guarded unless supported by ANI/GTDB/phylogenomic evidence.

### 48.2 Design status

Items 1, 2, 4, 5, 6, 7, 8, 9, and 10 are integrated into their operational sections. Item 3, the non-actinomycete startup declaration, remains deferred for further design; until then, non-actinomycete applicability is handled by existing source-category parsing, TTA/bldA applicability notes, and the new Gram-negative KCB false-positive guards.

---

## SECTION 49 — Reader-Facing Front Page and Briefing Package

### 49.1 Purpose

The **Reader-Facing Front Page and Briefing Package** is a historical v8.1 layout design that can be selected for authored summaries. It translates technical analysis into reader-facing pages without replacing the source inventory or verification; current extraction does not automatically author these reports.

### 49.1A Front-page claim-safety gate

Reader-facing headlines must pass the Diagnostic Signature / Hallucination-Trap Card. Headlines may emphasize high-interest genetic signatures, rare markers, and follow-up value, but must not convert biosynthetic potential into confirmed production. PDB-style or news-style outputs should use phrases such as “genetic signature,” “candidate fragment,” “BGC lead,” “pathway-family signal,” or “high-priority follow-up lead” unless product-level chemistry is confirmed.


The package is intended for collaborators, PIs, lab meetings, internal presentations, development-phase strain prioritization, and visually memorable summaries that still preserve evidence boundaries.

### 49.2 Default package

When the user selects a front-page package, choose the requested formats and record their actual generation/omission states. The historical v8.1 design offered these three layouts; they are not automatically authored by a current engine extraction:

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
- preserve typed supplied or missing bioactivity metadata; do not create default-assumed assay outcomes.

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
- [ ] Complete source-bound locus identity on every individual-locus surface, including front pages
- [ ] Raw antiSMASH vs corrected BGC count disclosure
- [ ] Rounded reader-facing genome-statistics policy
- [ ] Priority-lead support fields for compound class/key genes/domains/architecture
- [ ] Evidence Boundary / Claim Safety language in every format



---

## SECTION 50 — v8.2 Compound-Class Coverage + Claim-Safety Patch

### 50.0 Integration status

This section integrates **Sapote Workflow Patch v8.1.1 → v8.2**. It is additive and does not remove or weaken any v8.1.1 detection module. When a rule in this section conflicts with an older v8.1.1 rule, the v8.2 rule takes precedence.

### 50.1 Patch source and insertion map

#### Sapote Workflow Patch v8.1.1 → v8.2

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

The following historical rows are redacted illustrations, not fully bound current loci. Strain/region/source identity remains held; the four-column table does not support individual-locus reuse.

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

1. **In-cluster positives (controls).** Three regions across two strains (one Moderate, one Poor assembly) carry their maturation protease in-cluster — UMED correctly reports them as maturation-autonomous. In-cluster types observed: FlaP/AplP (S9-family serine protease, classes II and IV) and an M16 metallopeptidase (class V). The M16 case is notable: it is the family newly characterized by Xue et al. 2022, and it is paired with a class V lanthipeptide — a class not included in that paper's analysis.
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


