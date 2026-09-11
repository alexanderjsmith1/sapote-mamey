# Sapote-Mamey: The Plumbing Reference

### CLI, workbook, figures, packaging, stores, and parse layer of the Mamey engine

**Version of record:** Mamey engine v1.9.110 · bundle v9.7.319 · compiled 2026-06-23
**Author:** Alexander J. Smith
**Companion to:** *The Mathematics of Sapote-Mamey* (Volumes I & II — the engine's quantitative core and subsystems).
**Status:** Architecture reference. Every component is transcribed from engine source and cited to `module.py:symbol`; nothing is reconstructed from memory. Each cluster was verified against source; corrections made during review are noted inline.

---

## How to read this document

Where the math volumes cover *what the engine computes*, this covers *how the computed data becomes deliverables* — the command surface, the workbook substrate, the figure subsystem, packaging and sealing, the stores, and the parse/shim layer beneath it all. It answers "what does this subcommand do," "what sheet holds this," "what file is sealed where," and "where does the public/private boundary live."

Two cross-cutting concerns recur and should be read into every section:

1. **The four-tier release architecture.** The bundle ships as CODE, CODE-analysis-free, SID-public, and MERGED-PRIVATE-scaffold. Where a component behaves differently by tier — or touches the redaction boundary that keeps unpublished AS-strains out of public cuts — that is load-bearing and is noted explicitly.
2. **Claim-safety surfaces in output.** Capacity-level language, KCB = similarity not identity, and BGCs cited with contig/node are enforced not only in the scoring math but at the points where renderers and workbooks *write labels*. Those enforcement points are flagged where they live in the code.

The parse-layer write-up (`parsers.py` / `_gbk_shim.py`, Part 6) overlaps the math volumes at two functions — `_edge_status` and `architecture_grade` — whose *formulas* are documented in Volume I §1 and §5. Here those functions are covered for their *parse mechanics and the biopython-free shim*; the two are complementary, not contradictory.

---

## Part 1 — The CLI Surface

**Source modules:** `mamey/cli.py` (2427 lines), `mamey/chatgpt_commands.py` (649 lines), `mamey/package_inspector.py` (301 lines)
**Entry point:** `mamey_run.py` → `mamey.cli:main()` → `build_parser()` → subcommand dispatch

The CLI is the user-facing map of everything the engine can do. Every other module in the system is orchestrated from here. Reading `build_parser()` (line 2164) and `run_one_strain()` (line 437) together gives the complete picture of what runs, in what order, with what guardrails.

### Subcommand table

| Subcommand | Source | Purpose | Primary inputs | Primary outputs |
|---|---|---|---|---|
| `run` | `cli.py:run_command` | Full extraction for one or more strains | antiSMASH ZIP(s) | Package dir(s) with all deliverables |
| `validate` | `cli.py:validate_command` | Post-run package integrity check | Package dir | JSON validation report |
| `render-figures` | `chatgpt_commands.py:render_figures_command` | Post-seal figure rendering | Sealed package dir | PNGs + figure_manifest.csv + FIGURE_QA.md |
| `cohort-figures` | `cli.py:cohort_figures_command` | Cross-strain figure suite | `runs_gold/` dir | Cohort PNGs + sidecar CSVs |
| `doctor` | `cli.py:doctor_command` | Pre-flight environment check | None | Console PASS/WARN/FAIL report |
| `chatgpt-init` | `cli.py:chatgpt_init_command` | Surface the ChatGPT operating contract | `AGENTS.md` | Console: SHA256 + version + gotcha + file inventory |
| `inspect` | `package_inspector.py:inspect_command` | Preview an antiSMASH ZIP before running | antiSMASH ZIP | Console summary + suggested run command |
| `explain` | `package_inspector.py:explain_command` | Human-readable summary of a sealed package | Package dir | Console: status, tiers, top leads, issues |
| `list-bgcs` | `package_inspector.py:list_bgcs_command` | Quick BGC inventory from a sealed package | Package dir | Console table or JSON array |
| `mode-b` | `chatgpt_commands.py:mode_b_command` | Mode B top-lead cards from a sealed package | Sealed package dir | `<strain>_Mode_B_Top_Leads.md` + `.csv` |
| `domain-level` | `cli.py:_domain_level_command` | Post-seal domain-level Mode B enrichment | Sealed package dir | `domain_level/` CSV outputs |
| `ingest-receipts` | `mode_b_receipt.py:ingest_receipts_command` | Ingest Sapote judgment receipts into the register | Package dir + receipt JSON | Updated judgment register + optional workbook E1 reconcile |

The recommended ChatGPT workflow (printed by `chatgpt-init`) is: `doctor → inspect → run(--chatgpt-safe) → validate → list-bgcs → mode-b → render-figures → ingest-receipts`.

### `run` — the core extraction command

**Source:** `cli.py:run_command`, `cli.py:run_one_strain`, `cli.py:run_batch`

This is the main pipeline entry point. It accepts either a single strain (`--input-zip`) or a batch (`--strains`). The batch path calls `run_one_strain` sequentially for each ZIP and then auto-emits cross-strain figures if more than one strain was processed.

Key flags:

| Flag | Default | What it controls |
|---|---|---|
| `--strain` | Derived from ZIP name | Strain ID used for all output filenames |
| `--input-zip` | (required for single) | Path to antiSMASH output ZIP |
| `--strains` | (batch alternative) | One or more ZIP paths; mutually exclusive with `--input-zip` |
| `--outdir` | `./runs` | Output root; each strain lands in `<outdir>/<strain_id>/package/` |
| `--master` | None | Path to master workbook; created if absent, updated on each run |
| `--mode` | `gold` | `smoke` = triage-only; `gold` = full Mode B every BGC; `standard` = deprecated alias for gold (retired v9.7.92) |
| `--taxonomy` | `not verified` | Genus+species string; batch: pipe-separated values |
| `--source` | `not supplied` | Isolation source/host; batch: pipe-separated |
| `--release` | Fail-safe derived | `PUBLIC` or `PRIVATE`; derivation rule: AS/AJS/PENDING strain IDs → always PRIVATE; a PUBLIC override on an AS/AJS/PENDING strain is refused (not operator-overridable) |
| `--bioactivity` | omitted (`NOT_SUPPLIED`) | Deprecated scalar compatibility context; it never supplies a named assay target |
| `--brief` | `standard` | `none` = no brief; `minimal` = ~2pp; `standard` = ~3pp including figures |
| `--chatgpt-safe` | False | Profile switch: sets `--brief none --json-evidence off --require-workbook --locus-maps off`. Use inside any wall-clock-capped LLM session. |
| `--json-evidence` | `bounded` | `bounded` = stream JSON with ijson (falls back to `off` on timeout or if ijson absent); `off` = TXT clusterblast only; `full` = legacy full flatten (refuses files >20 MB) |
| `--locus-maps` | `auto` | `auto` = render unless capped run (brief=none) with >20 BGCs; `off` = never; `on` = always. Expensive on large strains. |
| `--antismash-profile` | `unknown` | Records antiSMASH hmmdetection strictness in manifest for cross-strain comparability. Pooling strains run under different profiles is unsafe. |
| `--require-workbook` | False | If set, workbook failure fails the run rather than continuing |
| `--metadata-csv` | None | Strain metadata CSV for collection figures; if absent, a figure availability report is written instead |

The phases of `run_one_strain()` execute in this sequence, each writing a phase receipt to `run_phase_receipts.jsonl`:

1. **Environment banner** — prints dependency status (openpyxl, ijson/vendor, figures, biopython, registry_detector) and the `MAMEY_DISABLE_REGISTRY_DETECTOR` state. All failures surface here before any work begins.
2. **Taxonomy normalization** — `cohort_resolver.normalize_taxonomy()` catches the antiSMASH `ORGANISM .` artifact (genus written as a literal dot) and substitutes a safe "sp." placeholder.
3. **antiSMASH JSON evidence parse** — `parse_antismash_evidence_status()` under a configurable wall-clock budget (default 300 s, `MAMEY_BOUNDED_BUDGET_S`). On overrun, falls back to `json_mode=off` rather than hanging.
4. **BGC region parse** — `parse_bgcs_from_zip()` + `apply_evidence_to_bgcs()`. Reuses the evidence object already parsed in step 3 (one parse per run, not two).
5. **Compound-class annotation** — `compound_class.annotate_bgc()` per BGC, using coordinate overlap to assign predictions (v9.7.87 P-10 fix: no longer contig-broadcast on single-contig genomes).
6. **Release tagging** — `dedup_and_guard.resolve_release()` stamps each BGC with PRIVATE/PUBLIC.
7. **GBK Pfam + TIGRFAM extraction** — `extract_gbk_pfam_hits()` + TIGRFAM merge. The TIGRFAM diagnostics (AHBA_synth_RP, ene_KS, TIGR03604, NikJ-family) are extracted from the JSON pass and merged here; they do not appear in `GBK sec_met_domain` and were previously dropped.
8. **CDS/contig/domain extraction** — `extract_cds_features()`, `extract_contig_sequences()`, `extract_domain_features()`.
9. **Source-derived scans** — `run_source_scans()` (the full CCTT/CGAD/EFLS/resistance/TFBS/bldA/FLBR/misanchor scan suite — documented in the math reference, Volume II Cluster A).
10. **Gene context seal** — `gene_context.write_gene_context()`: serializes normalized per-CDS records to `<strain>_gene_context.jsonl`. This is the durable sealed source that Mode B and gene-by-gene use post-seal when the original ZIP is gone (v9.7.88 roadmap #1).
11. **Locus-map rendering** — conditional on `locus_maps` policy. Each BGC's region GBK is extracted from the ZIP and rendered to `locus_maps/<bid>_<node>_locus.png` + companion CSV. Post-seal, non-blocking (`_LocusMapsSkipped` sentinel on policy skip).
12. **RG-GMCI** — `run_rggmci()`: split-cluster rescue using shared-reference linkage.
13. **Triage scoring** — produces the triage board, AB/AF/novelty scores, lead tiers, downgrade flags.
14. **Workbook update** — `update_master_workbook()`: writes/updates the per-strain workbook and optionally the master workbook.
15. **Mode B verdicts** — `deep_data.modeb_verdict_rows()` writes `modeb_verdicts.csv` (gold mode only).
16. **BLASTP worklist** — `crosswalk.candidate_blastp_rows()` writes `<strain>_5b_manual_blastp_worklist.csv`.
17. **Cell provenance** — `cell_provenance.write_cell_provenance()`.
18. **manifest.json** — full JSON snapshot (`MameyRun.to_dict()`); the complete handoff object for Sapote.
19. **bgc_data.json** — W6: per-strain single-strain bank JSON for `build_modeb_deepdive` without requiring the full cohort ingest.
20. **Seal-first gate** — if `MAMEY_SEAL_FIRST=1` (default since v9.7.88 Finding L): manifest/gate/checksums/ZIP are written BEFORE the brief renders. Brief/figure files live outside the core ZIP/checksum set. A render hang costs figures, never the core.
21. **Strain brief** — `render_brief()` in a subprocess with hard-kill timeout (`MAMEY_RENDER_TIMEOUT_S`, default 120 s). Failure writes `BRIEF_SKIPPED_TIMEOUT.md` or `BRIEF_SKIPPED_ERROR.md`; never blocks the package seal.
22. **START_HERE.md + BATCH_PLAN.md** — user-facing entrypoints written last, after all deliverable paths are known.

**Tier-specific note (redaction wording corrected — E2E-03):** the `--release` guard is an absolute invariant, and PRIVATE is the fail-safe default. Since the v9.7.236 PI decision (2026-07-06) the **AS-series cohort is PUBLIC by default** (the 2026 Hymenoptera paper), so the fail-safe PRIVATE guard maps only **AJS/PENDING/unrecognized** shapes to PRIVATE regardless of `--release PUBLIC`; an AS-series `--release PUBLIC` is honored, not refused. A future private cohort re-arms the AS guard (`AS_SCRUB=1`). This is the leak guard for genuinely unpublished strains in the MERGED-PRIVATE tier.

### `validate` — package integrity check

**Source:** `cli.py:validate_command` → `validate.validate_package()`

Reads the sealed package directory and verifies: manifest.json present and parseable, required deliverable files present, enrichment check (gate_validation.json, triage board). Returns a JSON report with `status` starting `PASS` or `FAIL`. Used as the post-`run` sanity check in the recommended workflow.

### `render-figures` — post-seal figure rendering

**Source:** `chatgpt_commands.py:render_figures_command`

Lightweight post-seal figure rendering from a sealed package. Does not re-run scans. Reads `*_4_triage_board.csv`. Five `--figure-set` modes:

| `--figure-set` | What it renders | Requires |
|---|---|---|
| `standard` (default) | Top-N antibacterial + antifungal lead bar charts | `*_4_triage_board.csv` in package |
| `mamey-native` (alias: `compiled-mamey`) | DAPR/RG-GMCI/ecology/completeness figures (v9.7.111; avoids raw BGC count ranking) | `--workbook <Mamey_Master.xlsx>` |
| `cohort-class` | Strain × biosynthetic-class capacity heatmap (v9.7.90) | `--workbook <cohort.xlsx>` |
| `locus-maps` | Post-seal gene-arrow maps from the sealed gene context (K0, v9.7.90) | Gene context JSONL in package |
| `domain-level` | Domain burden/claim-ceiling figures from `domain_level/` output (v9.7.89) | `domain_level/` in package (auto-runs if absent) |

The standard set is the **lead subset** — antibacterial/antifungal bar charts only. The full in-run figure suite (composition, length histogram, DAPR scatter, funnel, genome atlas, KCB anchors, novelty, edge composition, CCTT map, class distribution) requires `--brief standard` at run time and is not regenerated post-seal because not all its render inputs are retained in the sealed package (documented in `FIGURE_QA.md`, "Coverage" section, v9.7.88-D).

Active BGCs for figure ranking: rows where `Standing_rule` is blank AND `Primary_metab_flag != YES`. Scores from `AB_auto` / `AF_auto` columns. Label style `--style chatgpt-node-first` (default) labels bars `NODE_ID (BGC_ID)`, contig/node first. Outputs: `top_antibacterial_leads.png`, `top_antifungal_leads.png`, `figure_manifest.csv`, `FIGURE_QA.md`. If matplotlib is absent: `NO_FIGURES_RENDERED.md`.

### `cohort-figures` — cross-strain figure suite

**Source:** `cli.py:cohort_figures_command` → `cohort_figures.generate()`

Reads all `<ID>/package/` gold outputs under `--runs-dir` and emits the gene/domain figure suite. Four `--series` choices: `F` (heatmaps, default), `G` (complementary), `D` (dot/bubble), `all`. `--public-only` drops PRIVATE (AS-/AJS-/PENDING-) strains for a shareable PUBLIC cut. A batch run with >1 strain also auto-invokes `cohort_figures_bridge.build_cohort_figures()` at the end of `run_batch()`.

### `doctor` — pre-flight environment check

**Source:** `cli.py:doctor_command`

Checks Python version (3.10+ recommended, 3.8+ minimum), required deps (openpyxl, zipfile stdlib), optional deps (biopython, ijson, numpy, matplotlib, pytest), write permissions to `./runs/`, bundle file integrity, and antiSMASH ZIP detection in the current directory. Prints a PASS/WARN/FAIL summary per item. Windows: notes that the SIGALRM timeout guard is unavailable (non-fatal). Returns exit code 0 on PASS or WARN, 1 on FAIL.

### `chatgpt-init` — contract surface

**Source:** `cli.py:chatgpt_init_command`

Read-only. Prints the SHA256 of `AGENTS.md`, the current bundle/engine/build string (version-freshness probe — changes every cut, so emitting current values proves the current file was read, not a remembered one), the known-gotcha line(s), the recommended workflow, the inventory of ChatGPT-specific instruction files present vs absent, and the contract read-marker phrase if defined. Changes no files.

### `inspect` — preview antiSMASH ZIP (B4)

**Source:** `package_inspector.py:inspect_command`

Read-only; never invokes the extraction engine. Reports: antiSMASH version (from first region GBK), GBK region file count (one per BGC), JSON evidence presence, KCB TXT file count, HTML file count, total ZIP entries. Detects a bare assembly ZIP (no GBK region files) and prints a redirect to run antiSMASH first. Emits a ready-to-run `--mode gold --capped-session` command (gold is the only analysis mode) with the strain name derived from the ZIP filename; for large strains it instead notes the BGC count and the number of Mode-B authoring batches to expect, without suggesting a different `--mode` (`package_inspector.py:inspect_command`, ~lines 183-201 — the `--mode smoke` suggestion this line described was removed along with smoke mode at v9.7.161 and is not present in the current source).

### `explain` — package summary (B6)

**Source:** `package_inspector.py:explain_command`

Read-only. Reads `manifest_short.json` (fast path) or falls back to `manifest.json`. Prints: status, taxonomy, source, mode, Mamey version, assembly tier, raw/corrected BGC counts, top-3 antibacterial and antifungal leads, up to 5 issues from `issue_log.md`. Lists key files present vs missing. Ends with the trigger phrase for Sapote judgment.

### `list-bgcs` — BGC inventory (B7)

**Source:** `package_inspector.py:list_bgcs_command`

Read-only. Reads `*_4_triage_board.csv`. Supports `--axis rank|ab|af`, `--top N`, `--json` (machine-readable array with `bgc_id`, `contig`, `node_id`, `products`, `boundary`, `ab_score`, `af_score`, `novelty_auto`, `cctt_triggers`, `lead_tier`, `kcb_top`, `depth_floor`, `standing_rule`, `primary_metab`), and `--include-dropped` (default: primary-metabolism and standing-rule-excluded BGCs excluded). Default table columns: BGC_ID, Contig/Node, Products (truncated to 28 chars), Boundary, AB, AF, Lead_tier.

### `mode-b` — top-lead cards (P1)

**Source:** `chatgpt_commands.py:mode_b_command`

Post-seal, ChatGPT-safe. Reads `manifest.json` and `*_4_triage_board.csv` (and optionally `*_4A_RGGMCI_ranked_pairs.csv`, `*_4A2_ClusterBlast_gene_map.json`, and the sealed gene context JSONL). Ranking: active BGCs (no Standing_rule, no Primary_metab_flag) sorted by `AB_auto + AF_auto`, top N. Outputs `<strain>_Mode_B_Top_Leads.md` (one card per lead) and `.csv` (structured, one row per lead).

**Claim-safety surfaces here** in two places. The `_claim_ceiling()` function (lines 288–309) assigns one of five ceilings from `kcb_cumulative`, `kcb_protein_hits`, and `architecture_confidence`:

```
architecture == E, OR Standing_rule set:  "inventory only"
kcb > 50000 AND kp >= 5 AND arch not D/E: "candidate product-level similarity"
kcb > 5000  AND kp >= 4:                  "candidate family similarity"
kcb > 0:                                  "source-derived similarity"
else:                                     "inventory only"
```

And the `safe_claim` sentence template (lines 563–568) enforces a fixed capacity-level phrasing: "BGC `<id>` (`<contig>`) encodes biosynthetic capacity consistent with a `<class>` pathway; `<ceiling>`. KCB similarity: `<anchor>`… Product identity requires isolation and chemical characterisation." The ClusterBlast per-gene block header carries: "%identity = similarity to a reference protein, not product identity."

### `domain-level` — post-seal domain enrichment (v9.7.89)

**Source:** `cli.py:_domain_level_command` → `domain_level.run_domain_level()`

Post-seal, non-blocking (returns 0 unless the package is unreadable). Runs or loads domain-level enrichment for the top-N BGCs, emitting `domain_level/` outputs including `domain_complexity_metrics_by_bgc.csv` and `domain_safe_unsafe_claims.csv`. Two input modes: `--source-antismash <zip>` for full per-domain detail; otherwise reads the sealed gene context (limited mode). Optional `--emit-figures`.

### `ingest-receipts` — Sapote judgment ingestion

**Source:** `mode_b_receipt.py:ingest_receipts_command`

The P-D front door for persisting Sapote Mode B judgment. Reads `mode_b_receipt.json` from a Sapote session, ingests it into the per-strain judgment register, and optionally reconciles the master workbook's `E1_Mode_B_Index` sheet from the updated register (`--master <workbook.xlsx>`).

### Runtime guardrails and environment variables

| Variable | Default | Effect |
|---|---|---|
| `MAMEY_BRIEF_TIMEOUT_S` | 120 | Wall-clock budget for the brief render subprocess |
| `MAMEY_RENDER_TIMEOUT_S` | Same as BRIEF | Hard-kill timeout for subprocess render (v9.7.80 P0) |
| `MAMEY_SEAL_FIRST` | `1` | If `1`: seal core ZIP/checksums BEFORE rendering the brief (Finding L, v9.7.88). `0` restores render-before-seal. |
| `MAMEY_BOUNDED_BUDGET_S` | 300 | Wall-clock budget for the bounded JSON evidence parse |
| `MAMEY_QUIET_STAGES` | unset | If set: suppress the heartbeat stage lines |
| `MAMEY_BRIEF_FORCE_INPROCESS` | unset | Skip subprocess render, use in-process path (unit tests) |
| `MAMEY_DISABLE_REGISTRY_DETECTOR` | unset | Force fallback to hardcoded patterns in `source_scans.py` |

The dependency banner printed at every run shows the live state of all these capabilities — the operator's single always-on signal for capability availability.

### The strain-label accession guard

**Source:** `cli.py:_ACCESSION_RE`, `cli.py:_label_is_accession`

The run command detects when `--strain` looks like an NCBI accession shape (RefSeq `NC_/NZ_/NW_/NT_/NG_`, WGS `NZ_XXXX*`, assembly `GC[AF]_*`) and suggests a real strain name. Advisory: the accession is still used as the label, but the flag surfaces the fallback so it never silently propagates into every deliverable.

### The `chatgpt-safe` profile

**Source:** `cli.py:run_command` (lines 1851–1857)

`--chatgpt-safe` sets four flags atomically: `--brief none`, `--json-evidence off`, `--require-workbook`, and `--locus-maps off` (the last only if locus-maps was `auto`). Calibrated for wall-clock-capped LLM tool sessions: brief=none skips the render subprocess, json-evidence=off avoids large JSON streaming, require-workbook surfaces workbook failures immediately, locus-maps=off skips the expensive per-BGC rendering. The correct operating mode for the ChatGPT / Claude tool-call environment.

### Package output layout

Every `run` for strain `<ID>` writes to `<outdir>/<ID>/package/`. Key sealed files:

| File | Contents |
|---|---|
| `START_HERE.md` | User entrypoint: status, headline counts, judgment trigger phrase, RG-GMCI reading guide |
| `manifest.json` | Full JSON handoff object: all BGC records, assembly metrics, scan results, triage |
| `manifest_short.json` | Fast-load summary: status, tier, top-3 AB/AF leads, assembly, BGC counts |
| `bgc_data.json` | W6 per-strain bank JSON for single-strain `build_modeb_deepdive` |
| `commit_receipt.json` | Short: strain, mode, version, raw BGC count, issues, status |
| `issue_log.md` | All warnings/issues logged during the run |
| `run_phase_receipts.jsonl` | Machine-readable per-phase timing and status log (monotonic since v9.7.87) |
| `<strain>_AntiSMASH_Evidence_Parse.json` | Full antiSMASH JSON evidence incl. GBK Pfam and TIGRFAM hits |
| `<strain>_gene_context.jsonl` | Sealed per-CDS normalized gene records for Mode B / gene-by-gene (v9.7.88) |
| `<strain>_4_triage_board.csv` | Full triage table: all BGCs, scores, CCTT triggers, lead tiers, downgrade flags |
| `<strain>_4c_AB_lead_board.csv` | Pre-sorted antibacterial lead board |
| `<strain>_4c_AF_lead_board.csv` | Pre-sorted antifungal lead board |
| `<strain>_4A_RGGMCI_ranked_pairs.csv` | RG-GMCI split-cluster candidate pairs |
| `<strain>_4A2_ClusterBlast_gene_map.json` | ClusterBlast per-gene correspondence (P-CBG) |
| `<strain>_5b_manual_blastp_worklist.csv` | BLASTP spot-check worklist (metadata only; not a BLASTP run) |
| `<strain>_BATCH_PLAN.md` | Ready-to-run projected next-batch command |
| `modeb_verdicts.csv` | Per-BGC Mode B verdict placeholders (gold mode only) |
| `locus_maps/` | Gene-arrow PNG + data CSV per BGC (when rendered) |
| `BRIEF_SKIPPED_TIMEOUT.md` / `BRIEF_SKIPPED_ERROR.md` | Written if the brief render times out or errors |

*Cluster P1 verified against `cli.py`, `chatgpt_commands.py`, `package_inspector.py` @ v9.7.117. All flags, env-var defaults, and the chatgpt-safe profile confirmed exact.*

---
## Part 2 — The Master Workbook

**Source modules:** `mamey/master_workbook.py` (1573 lines), `mamey/workbook_schema_check.py` (350 lines), `mamey/b1_normalizer.py` (103 lines), `mamey/cell_provenance.py` (218 lines)
**Entry point:** `master_workbook.update_master_workbook()` called from `cli.run_one_strain()`

The master workbook is the persistent cross-strain analysis substrate. Every `run` call appends one strain's data; the workbook accumulates across the full cohort. It is created fresh if absent; otherwise loaded, deduplicated (idempotent re-ingest), and updated in-place with an atomic tmp-rename save. The schema was frozen at v1.1 — the coded A/B/C/D/E/F/G/H scheme — and validated by `workbook_schema_check.py` against that contract.

### Sheet architecture

**Color convention** (`master_workbook.py:HDR_FILL_BLUE / HDR_FILL_GREEN / HDR_FILL_ORANGE`):

| Style | Color (hex) | Used for |
|---|---|---|
| Dark blue `1F4E79` | Persistent cross-strain sheets (A–H coded scheme) | One row per strain or per BGC across all strains |
| Dark green `375623` | Per-strain sheets (`[code]_Summary`, `[code]_Triage`, etc.) | One set per strain, added once |
| Dark orange `833C00` | A1_Dashboard | Top-level summary only |

Per-strain sheet names are derived via `_sheet_code()` (lines 132–146): the last underscore-split token of the strain ID, capped at 14 characters. So `Actinomadura_rubrisoli_H3C3` → `H3C3`; `AS-XXX` → `AS-XXX`.

**The append-by-header pattern** (`_append_row_by_header`, `_col_map`): all writes build a column-index map from row 1 headers and write only to matching positions. This means (a) extra columns written by Sapote or the operator are preserved on re-ingest; (b) new schema columns don't break old workbooks; (c) row-dict keys must match header text exactly (an unknown key is silently skipped). The v1.9.2 `_repair_leading_blank_header` handles workbooks where `ws.append()` placed the header in row 2, leaving row 1 blank.

### Complete sheet inventory (A–H coded scheme, schema v1.1)

All headers transcribed from `CANONICAL_V1_HEADERS`. The validator derives its column contract directly from this dict at import — the two cannot drift independently.

| Sheet | Type | Key columns | Written by | Purpose |
|---|---|---|---|---|
| **A1_Dashboard** | Summary | (free-form cells) | `_ensure_canonical_headers` | Counts: strains, total BGC records, last updated, Mamey version. A8 flag for MIXED_MODE_COHORT. |
| **A2_Strain_Registry** | per_strain | 23 columns (list below) | `_write_canonical_v1_views` | One row per strain: assembly stats, top leads, tier |
| **A3_Run_Manifest** | fixed | 10 columns (list below) | `_write_canonical_v1_views` | One row per run: provenance/audit trail |
| **A4_Completeness_Audit** | per_strain | 11 columns (list below) | `_write_canonical_v1_views` | Pass/fail per-sheet gate per strain |
| **B1_BGC_Master** | per_bgc | 45 columns (full list below) | `_write_canonical_v1_views` | One row per BGC across all strains: **45 canonical columns**. The central per-BGC ledger. Augmented with Domain_total/Core_domain_burden/Tailoring_domain_burden by `update_domain_level_sheets`. |
| **B2_Product_Class_Matrix** | per_strain | strain + one column per antiSMASH class + counts_reliability | `_write_canonical_v1_views` | Strain × class count pivot; baseline = 52-entry `ALL_AS_CLASSES`, extended with novel classes. |
| **B3_Known_Cluster_Matrix** | dynamic | strain + (one column per KCB top-hit reference — data-dynamic) | `_update_known_cluster_matrix` | Strain × KCB family presence; validator checks only the leading `strain` column. |
| **B4_Cross_Strain_Scans** | per_strain | 19 columns (list below) | `_write_canonical_v1_views` | Aggregate scan counts per strain. Gold-only columns (resistance_T1, UMED_gaps, EFLS_pairs) written as `"NA"` for non-gold strains (v9.7.101 PC-A1). |
| **C1_DAPR_Antibacterial** | leads | 17 columns (list below) | `_write_canonical_v1_views` | Top-10 AB leads per strain in corrected-rank order |
| **C2_DAPR_Antifungal** | leads | (same as C1) | `_write_canonical_v1_views` | Top-10 AF leads per strain |
| **C3_Lead_Tier_Summary** | per_strain | 11 columns (list below) | `_write_canonical_v1_views` + `update_c3c4_from_sapote` | Top AB/AF headline; sapote fields filled post-judgment |
| **C4_Strain_Decision_Table** | per_strain | 12 columns (list below) | `_write_canonical_v1_views` + `update_c3c4_from_sapote` | Cross-strain priority table |
| **D1_RGGMCI_All_Strains** | per_strain | 8 columns (list below) | `_write_canonical_v1_views` | Per-strain fragmentation review state |
| **D2_RGGMCI_Top_Pairs** | pairs | 10 columns (list below) | `_write_canonical_v1_views` | Top-25 RG-GMCI pairs per strain (`RGGMCI_D2_TOP_N = 25`) |
| **D3_RGGMCI_Promoted** | per_strain | 8 columns (list below) | `_write_canonical_v1_views` + `update_d3_from_sapote` | Top-12 HIGH-grade promoted pairs (`RGGMCI_D3_TOP_N = 12`) |
| **E1_Mode_B_Index** | per_strain | 11 columns (list below) | `_write_canonical_v1_views` + `update_e1_from_judgment` | Placeholder `ALL/JUDGMENT_PENDING` at extraction; per-BGC rows after Sapote. layperson_summary ≤800 chars; fermentation_note ≤400 chars. |
| **E2_Comparative_Pairs** | per-pair | 14 columns (list below) | `update_e2_comparative_pairs` | Cross-strain BGC comparison; ≥2 strains; idempotent (clears before re-write) |
| **E3_Megacluster_Registry** | per_bgc | 9 columns (list below) | `_write_canonical_v1_views` | BGCs ≥100 kb (`_MEGA_KB = 100.0`) |
| **E4_A_Domain_Summary** | per_domain | 9 columns (list below) | (not populated at extraction) | A-domain substrate predictions; filled by Sapote/external tools |
| **F1_Ecology_Readiness** | per_strain | 12 columns (list below) | `_write_canonical_v1_views` | Habitat-readiness; `habitat` from `_infer_habitat()` keyword matching (bee/wasp/ant → `4_Hymenoptera`; moss/bryophyte → `3_Bryophyte_lichen`; soil → `1_Terrestrial_soil`; marine → `2_Marine`; fungal → `7_Fungal`; else → `ENGINE_DEFAULT_PLACEHOLDER`). The placeholder is intentional — wrong habitat stamps propagate into ecological claims. |
| **G1_Literature_Index** | per-citation | strain, BGC_ID, track, citation, doi, evidence_purpose, verification_status | `update_g1_from_sapote` | Literature from Sapote Deep Dive. Append-only, de-duped on (strain, BGC_ID, doi, evidence_purpose). citation ≤300 chars. |
| **G2_Validation_Roles** | per_strain | strain, primary_role, manuscript_use | `_write_canonical_v1_views` + `update_g2_from_sapote` | Strategic role per strain |
| **H1_Handoff_Log** | fixed | 8 columns (list below) | `_write_canonical_v1_views` | Audit trail of workbook touches |
| **H2_Gap_Queue** | per_strain | priority, gap_class, strains, required_input, next_action, assigned_platform, status | `_write_canonical_v1_views` | Action queue; required_input/next_action derived from run flags (v9.7.84 P-F) |
| **H3_Schema_Version** | fixed | Schema version, v1.1 | `_write_canonical_v1_views` | Schema provenance stamp |



**Full column lists** for the multi-column sheets above (kept out of table cells so the inventory stays legible):

- **A2_Strain_Registry**: strain, taxonomy, ecology_source, habitat, assembly_bp, contigs, n50, gc_pct, bgc_count, interior_pct, assembly_tier, workflow_version, package_status, top_ab_bgc, top_ab_class, ab_score, ab_band, top_af_bgc, top_af_class, af_score, af_band, rggmci_state, gap_next_action.
- **A3_Run_Manifest**: run_date, strain, version, mode, antismash_profile, input_zip, raw_bgcs, corrected_bgcs, issues, package_path.
- **A4_Completeness_Audit**: strain, A2_registry, B1_bgc_master, B4_scans, C1_dapr_ab, C2_dapr_af, D1_rggmci, E1_mode_b, F1_ecology, overall, gap_action.
- **B4_Cross_Strain_Scans**: strain, run_mode, KCB_status, RGGMCI_pairs, RGGMCI_HIGH, CCTT_triggers, CCTT_HAL, CCTT_LAN, CCTT_LASSO, CCTT_THA, CCTT_PHO, CCTT_ENE, CGAD_chitin, TFBS_DasR, TFBS_total, bldA_T4, resistance_T1, UMED_gaps, EFLS_pairs.
- **C1_DAPR_Antibacterial**: strain, rank, assembly_locator, contig, BGC_ID, products, score, lead_tier, band, standing_rule, corrected_rank, kcb_top, kcb_score, boundary, arch, cctt, status_note.
- **C3_Lead_Tier_Summary**: strain, top_ab_bgc, top_ab_products, ab_score, ab_band, top_af_bgc, top_af_products, af_score, af_band, sapote_composite, recommended_role.
- **C4_Strain_Decision_Table**: sapote_rank, strain, sapote_score, bgc_count, assembly_tier, top_lead, top_kcb_score, rggmci_high, class_diversity, high_value_hits, rare_class_hits, recommended_role.
- **D1_RGGMCI_All_Strains**: strain, contigs, review_required, final_state, promoted_grades, fragment_sets, promoted_bgcs, interpretation.
- **D2_RGGMCI_Top_Pairs**: strain, rank, bgc_a, bgc_b, rggmci_score, confidence, products_a, products_b, shared_references, interpretation.
- **D3_RGGMCI_Promoted**: group_id, strain, grade, fragments, evidence_basis, claim_ceiling, chemistry_consequence, status.
- **E1_Mode_B_Index**: strain, BGC_ID, length_kb, products, subprograms, mode_b_status, analysis_platform, date, report_file, layperson_summary, fermentation_note.
- **E2_Comparative_Pairs**: pair_id, strain_a, bgc_a, strain_b, bgc_b, length_a_kb, length_b_kb, products, subprogram_match, mean_pct_id_core, mean_pct_id_all, a_domain_match, diverged_genes, interpretation.
- **E3_Megacluster_Registry**: strain, BGC_ID, length_kb, boundary, products, kcb_top, kcb_score, long_read_status, notes.
- **E4_A_Domain_Summary**: strain, BGC_ID, module_position, gene_locus_tag, stachelhaus_code, predicted_substrate, method, confidence, notes.
- **F1_Ecology_Readiness**: strain, taxonomy, source, habitat, assembly_tier, bgc_count, ab_lead, af_lead, tfbs_hits, cctt_classes, readiness, route.
- **H1_Handoff_Log**: date, platform, direction, strains_affected, sheets_modified, file_sha256, validation_result, notes.

**Per-strain sheets** (green headers, one set per strain): `[code]_Summary` (Field/Value + scan rows + issues), `[code]_Triage` (full per-BGC triage board with depth-floor), `[code]_Lead_Propagation` (top-15 AB + top-15 AF leads), `[code]_Missingness` (skeleton missingness register).

**Domain-level sheets** (added on demand by `update_domain_level_sheets`, v9.7.89, not part of the frozen v1.1 set): `Domain_Rows_Long`, `Domain_Role_Counts_By_BGC`, `Domain_Role_Counts_By_Strain`, `Domain_Architecture_Strings`, `ASModules_Domain_Level`, `Domain_Claim_Safety`. This function also back-populates `Domain_total`, `Core_domain_burden`, `Tailoring_domain_burden` onto `B1_BGC_Master` for affected BGCs.

### Key invariants and write contracts

**Idempotent re-ingest (P2 fix):** before writing, `drop_existing_strain()` removes all existing rows for the strain. A second `run` produces an identical result, not a doubled row. **Atomic save (F2):** every write uses `wb.save(path + ".tmp")` then `os.replace(tmp, path)`. **Non-canonical sheet preservation (default):** sheets not in the canonical v1.1 set are preserved (pass `prune_noncanonical=True` to drop) — changed from the old silent-gutting behavior. **Gold-only scan columns:** B4 `resistance_T1`/`UMED_gaps`/`EFLS_pairs` written as `"NA"` for non-gold strains, with a `MIXED_MODE_COHORT` dashboard flag when modes differ.

### Sapote write-back functions

The Sapote → workbook contract: called after each analysis step. All follow the pattern load → drop prior rows → write → update A4 → atomic save.

| Function | Sheets updated | Trigger |
|---|---|---|
| `update_e1_from_judgment` | E1_Mode_B_Index, A4 (E1_mode_b cell) | After each Sapote Mode B batch |
| `update_c3c4_from_sapote` | C3_Lead_Tier_Summary, C4_Strain_Decision_Table | After cross-strain priority synthesis |
| `update_d3_from_sapote` | D3_RGGMCI_Promoted | After Sapote confirms RG-GMCI anchors |
| `update_g1_from_sapote` | G1_Literature_Index | After Literature Deep Dive (append-only) |
| `update_g2_from_sapote` | G2_Validation_Roles | After strategic-role assignment |
| `update_e2_comparative_pairs` | E2_Comparative_Pairs | After cohort bank assembled (≥2 strains) |
| `update_domain_level_sheets` | 6 domain sheets + B1 augmentation | After `domain-level` runs |

### The schema validator — `workbook_schema_check.py`

Validates a master workbook against frozen schema v1.1. Returns JSON with pass/fail per sheet, missing sheets, column mismatches, row-count consistency. Exit 0 = PASS, 1 = FAIL. The validator **derives its column contract from `master_workbook.CANONICAL_V1_HEADERS` at import** (the F5 fix — builder and validator cannot drift independently).

Validation paths: `auto` (cohort <26 strains → full-deep, ≥26 → fast-structural, via `LARGE_COHORT_THRESHOLD = 26`), `fast` (sheets/headers/row counts/coverage), `full` (adds A2↔B1 strain cross-check + per-row re-validation), `--v12` add-on (checks v1.2 additions: `Fragment_Rescue_Tiers` D5 + `Activity_Ref` from `FRAMEWORK_ACTIVITY_TAGS`).

Sheet typing for consistency: `per_strain` (A2/A4/B4/F1, row counts should match), `per_bgc` (B1, cross-checked against A2 in full mode), `leads` (C1/C2, no coupling), `dynamic` (B3, leading column only), `fixed` (all others, column order). Column comparison is case-insensitive. Extra sheets are a warning, not a failure. The validator is master-only — it rejects per-strain Mamey workbooks with a clear error.

### `b1_normalizer.py` — B1 column normalizer

Normalizes divergent B1 source data onto the canonical **45-column** B1 schema (single source of truth: `CANONICAL_V1_HEADERS['B1_BGC_Master']`). Resolution order per column: (1) exact canonical-header match, (2) explicit `ALIASES` entry, (3) unmapped — surfaced in ledger, never silently dropped. Value normalizers: products → semicolon-separated; boundary → `Interior`/`Edge`/`Full-contig` canonical casing; region → `regionNNN` zero-padded. Columns matching `_ALIAS` suffix → `extra_columns`; `_A2_` prefix → routed to A2 note. `normalize_table()` returns a ledger with unmapped/extra/A2-routed columns and `blank_pct_by_column` (the evidence-conservation check — honest blanks over silent drops). Frozen-schema rule: a row with `kcb_top` filled but `needs_manual_kcb_check` blank defaults to `"yes"`.

### `cell_provenance.py` — per-field provenance

Writes a per-field provenance table into the package (`<strain>_cell_provenance.csv`) plus a prioritized `<strain>_missing_data_worklist.csv`, called from `run_one_strain()` step 17. Columns: worksheet, cell_or_field, data_label, current_value, status_code, derived_from, source_file, source_parser, evidence_type, confidence, why_missing_if_blank, how_to_fill, release_handling, notes_for_llm.

The `STATUS_GLOSSARY` carries **13** status codes: `COMPLETE_NATIVE`, `COMPLETE_USER_METADATA`, `COMPLETE_EXTERNAL_EVIDENCE`, `COMPLETE_INFERRED_LOW_CONFIDENCE`, `NEEDS_ANTISMASH_OUTPUT`, `NEEDS_PROTEIN_FASTA`, `NEEDS_HMMER_DOMTBLOUT`, `NEEDS_DIAMOND_TSV`, `MANUAL_BLASTP_OPTIONAL`, `LOW_CONFIDENCE_REVIEW`, `UNRESOLVED_METADATA`, `NOT_APPLICABLE`, `DEFER_SERVER_R2`. The `notes_for_llm` field carries explicit constraints: "Do not infer exact species from BGC content", "Leave blank cells flagged; do not synthesize missing external evidence", "BGC numbering is immutable once written."

### Flags and latent issues (surfaced during review)

- **`BGC_Class_Matrix` vs `B2_Product_Class_Matrix`:** two sheets track class distributions. `B2` is the frozen v1.1 coded sheet; `BGC_Class_Matrix` predates it (legacy naming, `_update_class_matrix`, data-dynamic from the 52-entry `ALL_AS_CLASSES`). A cohort workbook may carry both; prefer the coded `B2`.
- **`manifest_short.json` write-path:** `explain` reads it as a fast path, but it is not written by `update_master_workbook()` or `run_one_strain()`. Likely written by `render_brief.py` or `packaging.py` — to confirm in the packaging cluster (P4). If absent, `explain` falls back to `manifest.json`.
- **D3 strain column position:** D3 uses `strain` as column 2 (column 1 is `group_id`); `drop_existing_strain()` operates on column 1 by default, so `update_d3_from_sapote()` has explicit per-column handling. Any future D3 write-back must follow the same pattern.

*Cluster P2 verified against `master_workbook.py:CANONICAL_V1_HEADERS` and surrounding code @ v9.7.117. One correction applied during review: B1_BGC_Master is **45 columns**, not 44 — the source's own `b1_normalizer.py` docstring says "44 cols", a stale comment flagged back to the engine chats for a future fix.*

---
## Plumbing Reference — P3: The Figure Subsystem

> ⚠️ **STALE, v9.7.213 audit.** This section's module inventory predates the v9.7.155 module-consolidation pass; as flagged by the
> current .213 tree — and was never updated through the v9.7.155 module-consolidation pass. Verified
> against the live `mamey/` tree on 2026-07-06: **4 of the 15 named modules no longer exist** —
> *cohort_figures_d.py*, *cohort_figures_g.py*, *cohort_figures_bridge.py*, *cohort_figure_captions.py*.
> Two are independently confirmed elsewhere in-bundle as rename artifacts: `docs/BUNNY_HOP_WISHLIST_v9.7.150e.md`
> notes *cohort_figures_g.py* was *make_figures_complement.py*; `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md`
> notes `cohort_figures.py` (which survives) absorbed *make_figures_v3.py*. Current equivalents, per a live
> `ls mamey/*figure* mamey/cohort*`: `bgc_figures.py`, `cohort_cards.py`, `cohort_class_heatmap.py`,
> `cohort_figures.py`, `cohort_resolver.py`, `cohort_synthesis.py`, `collection_figures.py`,
> `cross_strain_figures.py`, `domain_figures.py`, `figure_policy.py`, `figures_extra.py`, `figures_sapote.py`,
> `figures_smoke.py`, `figures_split.py`, `mamey_native_figures.py`, `master_figure_atlas.py`,
> `render_all_figures.py`, plus `mamey/figures/locus_map.py` and `locus_renderer_v2.py`.
>
> **The staleness goes deeper than this header line.** §3 (cohort_figure_captions.py — Captions and
> Glossary, ~line 427), §12 (cohort_figures_bridge.py — Batch Auto-Fire Bridge, ~line 647), the
> G-series/D-series aside (~line 694), and P4's §9 (package_addons_html.py — OPEN_ME_FIRST.html,
> ~line 1024) are full API-documentation subsections for modules that no longer exist as separate
> files. I have not traced where each documented function (write_captions, build_cohort_figures,
> write_open_me_first, etc.) landed after the v9.7.155 consolidation, so those subsections are left
> as-is rather than rewritten on an unverified guess. `tools/check_dangling_refs.py --scope tools`
> will keep flagging those subsection headers, correctly, until someone does that tracing — that's
> the gate working, not a bug in it. The rest of this doc beyond P3/P4 has not been checked at all.

**Source modules (per the .213 audit — see staleness note above; italics = confirmed gone in .213):** `mamey_native_figures.py` (315), `master_figure_atlas.py` (905), `collection_figures.py` (1078), `cross_strain_figures.py` (604), `cohort_figures.py` (438), *cohort_figures_d.py* (277), *cohort_figures_g.py* (361), *cohort_figures_bridge.py* (197), `cohort_class_heatmap.py` (127), `domain_figures.py` (240), `figures_sapote.py` (402), `figures_extra.py` (355), `figures_split.py` (134), `figure_policy.py` (56), *cohort_figure_captions.py* (128), `locus_map.py` (247)  
**Engine version:** Mamey v1.9.110 · Bundle v9.7.319

---

### 1. Shared Architecture and Invariants

Every figure module in the system enforces the same set of output disciplines, which are worth stating once:

**Data-only PNGs + companion CSVs.** Every PNG has a sidecar `<name>_data.csv` carrying the exact data plotted. This is not optional — it is the evidence-conservation contract for figures.

**Non-blocking best-effort.** All figure render paths are try/catch wrapped. A render failure writes a skip marker (`*.SKIPPED.md` or `NO_FIGURES_RENDERED.md`) and returns a status dict. It never blocks the package seal.

**Saccharide policy** (`figure_policy.py`): pure-saccharide BGCs are omitted from all comparative figures. "Pure saccharide" = the region's only specialist signal is `saccharide` and it carries none of the `SPECIALIST_CLASSES` set (which includes NRPS, PKS, RiPP, terpene, siderophore, etc.). A BGC carrying `NRPS;saccharide` is NOT pure saccharide — it plots under NRPS. This is enforced via `figure_policy.is_pure_saccharide()` / `omit_saccharides()`, and all figure modules import from this single source of truth rather than re-deriving the rule.

**Claim-safety surfaces in figure footers.** Every figure carries a footer line. The standard text (from `render_brief.SCORE_NOTE` / `KCB_NOTE`) reads along the lines of: "Data-only figure · scores are deterministic capacity signals, not activity measurements · KCB = similarity, not identity · capacity-level." The `locus_map.py` footer is: "Data-only figure · capacity-level, not a product claim · gene roles = antiSMASH rule/smCOG annotation (not BLASTP-confirmed) · KCB = similarity, not identity · arrows to scale within each panel."

**Raw BGC count policy** (`mamey_native_figures.RAW_BGC_COUNT_POLICY`): raw BGC counts are fragmentation-sensitive and must not appear as headline biological rankings. They are allowed only in QC/context panels. `mamey_native_figures.py` makes this explicit with a policy string that is embedded in the QC-only figure's caption and written to `FIGURE_QA.md`.

**House-style palette** (v9.7.115): the workbook-native figure set uses a blues-led palette (`mamey_native_figures.py`); greens replace orange for the antifungal track to avoid confusion with POOR assembly-tier orange.

**Matplotlib backend:** all modules call `matplotlib.use("Agg")` (or import it with that backend) so figure rendering never requires a display server.

---

### 2. `figure_policy.py` — Saccharide Exclusion

**Source:** `figure_policy.py:SPECIALIST_CLASSES`, `figure_policy.py:is_pure_saccharide`, `figure_policy.py:omit_saccharides`

The policy switch `FIGURE_OMIT_SACCHARIDE = True` is the global gate. `SPECIALIST_CLASSES` is a frozenset of 33 antiSMASH product-class tokens. Any BGC carrying `saccharide` AND at least one member of `SPECIALIST_CLASSES` is not pure saccharide and is kept.

Note: `SPECIALIST_CLASSES` is NOT the same as the lead-board CONFIRM set. Ectoine, redox-cofactor, siderophore, butyrolactone, and others appear here so multi-class BGCs (e.g. `NRPS;ectoine`) plot under their specialist class rather than being dropped. These are still downranked on the DAPR board by the scoring/standing-rule layer.

`cohort_class_heatmap.py` uses a separate centralized exclusion set from `genus_reference.STANDING_EXCLUSIONS` (PC-A5, v9.7.101) rather than SPECIALIST_CLASSES, ensuring all comparative consumers drop identical classes.

---

### 3. `cohort_figure_captions.py` — Captions and Glossary

**Source:** `cohort_figure_captions.py:CAPTIONS`, `cohort_figure_captions.py:GLOSSARY`, `cohort_figure_captions.py:write_captions`

All captions are keyed by figure stem (the part after the `Fxx_/Gxx_/Dxx_` prefix) so numbering can shift without breaking lookups. Every caption is capacity-level: "biosynthetic *capacity*", "inferred predictions", "KCB = similarity, not identity."

`write_captions(out, png_names)` writes `figure_captions.md` covering PNGs present in the output dir, organized by F/G/D series with a glossary section covering regulators, assembly-line genes, and key terms (corrected BGC count formula, assembly tier thresholds, PUBLIC/PRIVATE guard).

---

### 4. `locus_map.py` — Gene-Arrow Locus Maps

**Source:** `locus_map.py:render_locus_map`, `locus_map.py:cds_rows_from_gbk`, `locus_map.py:cds_rows_from_table`, `locus_map.py:classify`, `locus_map.py:_load_palette`

**Role:** Deterministic gene-arrow figures for single-BGC (top AB/AF leads, Mode B BGCs) and paired panels (RG-GMCI HIGH pairs).

**Two CDS row sources:**

| Source | Function | When used |
|---|---|---|
| Region GBK from antiSMASH ZIP | `cds_rows_from_gbk(gbk_path)` | In-run (v9.7.90): reads from the ZIP while it's open during inventory |
| Sealed gene context JSONL (K0) | `cds_rows_from_table(rows)` | Post-seal re-render via `render-figures --figure-set locus-maps` |

Both paths classify each CDS through the same palette so in-run and post-seal outputs are identical. Gene roles are derived from antiSMASH `gene_functions` / `sec_met_domain` qualifiers — NOT from the `product` field — so a CDS with an empty product annotation still receives a role classification.

**Palette:** loaded from `mamey/data/locus_role_palette.json` at module import. Unknown gene function tokens fall to the default role ("other / hypothetical") and never crash. The JSON-driven palette allows chemotype roles to extend without code edits.

**Key constants:**

| Constant | Value | Effect |
|---|---|---|
| `SPARSE_MAX` | 18 | ≤18 genes → horizontal locus labels; >18 → rotated 90° |
| `LABEL_FONT_PT` | 6.0 | Per-arrow locus label minimum (LS-2) |
| Gene-span zoom (v9.7.117) | `_pad = max(span * 0.04, 500)` | Zoom to the gene span, not full-contig coordinates; prevents BGC near a contig end being crushed into a sliver |

**Outputs per BGC:** `<bid>_<node>_locus.png` + `<bid>_<node>_locus_data.csv`. CSV columns: panel, locus_tag, order, start, end, strand, length_aa, role, gene_functions.

**Claim-safety:** the FOOTER constant is written to every figure, and the `claim_prefix` argument (typically `PRIVATE` or `PUBLIC`) prepends the release status.

**Render policy** in `run_one_strain()` (P1 reference): locus-map rendering is gated by `--locus-maps auto|off|on`. Under `auto`: skip when `brief=none` AND `raw_bgc_count > 20`. Under `--chatgpt-safe`: `locus-maps=off` by default.

---

### 5. `figures_sapote.py` — Per-Strain Sapote-Layer Figures

**Source:** `figures_sapote.py:fig_dapr_scatter`, `fig_ab_ranked`, `fig_af_ranked`, `fig_funnel`, `fig_ab_af_vertical_panels`, `_kcb_short`

**Role:** Per-strain reader-facing figures emitted as part of the standard brief. All read the normalized triage rows from `render_brief.load_facts()` — no LLM, no network.

**`_kcb_short(kcb)` — the KCB compound-name claim-safety surface:**  
Extracts the compound name from a KCB top-hit string (splits on `|`, strips boilerplate). Truncated to **18 characters**. This is the only place KCB compound names appear on figure labels; truncation forces brevity and discourages over-precise compound naming from a similarity signal.

**Figure outputs (all `{strain}_{id}_fig_*.png` + companion `_data.csv`):**

| Figure | Stem | What it shows |
|---|---|---|
| DAPR dual-track scatter | `8c_fig_dapr_scatter` | AB vs AF score scatter; each point = one BGC; coloured by boundary; median guide lines; top-5 AB + top-3 AF labeled node/contig-first (v9.7.86 P-8). De-collision logic for ties (v9.7.87 Defect 1). |
| Antibacterial ranking | `8d_fig_ab_ranked` | Top-30 by AB score, horizontal lollipop, boundary-coloured |
| Antifungal ranking | `8e_fig_af_ranked` | Top-30 by AF score |
| Claim-safety funnel | `8f_fig_funnel` | Four-stage funnel: raw BGCs → corrected count (Int+½Edge+¼FC) → minus saccharide-only → genuine lead tier (AB≥70 or AF≥44). The thresholds `LEAD_AB_MIN=70.0`, `LEAD_AF_MIN=44.0` are module constants. Each stage is a stated deterministic rule. |
| Combined AB+AF vertical panels | `8n_fig_ab_af_panels` (v9.7.72) | Side-by-side vertical bars, node/contig-first labels with class/KCB context key below |

---

### 6. `figures_extra.py` — Extended Per-Strain Auto-Emit Figures

**Source:** `figures_extra.py:render_extra_figures`

**Role:** Second tier of per-strain auto-emit figures, previously hand-produced per chat. All read `bgc_data.json` + normalized triage rows; no LLM; each figure independently best-effort.

**Figure outputs:**

| Figure | Stem | What it shows |
|---|---|---|
| Class distribution | `8g_fig_class_distribution` | BGC product-class composition bar chart |
| CCTT trigger map | `8h_fig_cctt_map` | CCTT diagnostic-trigger inventory per BGC, horizontal bar |
| Length histogram | `8i_fig_length_hist` | BGC length (kb) stacked by boundary status |
| Edge composition | `8j_fig_edge_composition` | Interior / Edge / Full-contig boundary mix |
| Novelty ranking | `8k_fig_novelty_ranked` | Top BGCs by novelty score |
| KCB anchors | `8l_fig_kcb_anchors` | Most-cited KCB anchor products (similarity, not identity) |
| Genome atlas | `8m_fig_genome_atlas` | Genome-position strip, each BGC coloured by class |

---

### 7. `figures_split.py` — Split-Pathway Visualisations

**Source:** `figures_split.py`

**Role:** Auto-emit split-pathway figures for HIGH RG-GMCI candidates and high-KCB single BGCs. Non-blocking and best-effort; if antiSMASH GBKs / clusterblast dirs aren't present, logs why and emits nothing.

**Selection criteria:** HIGH RG-GMCI pairs where both fragments resolve to the same MIBiG class anchor; single BGCs with strong KCB hits in non-ubiquitous classes. `UBIQUITOUS` exclusion set: `{saccharide, napaa, ectoine, siderophore, melanin, terpene, betalactone, butyrolactone, lanthipeptide, lassopeptide, hgle}`.

---

### 8. `mamey_native_figures.py` — Workbook-Native Figure Set

**Source:** `mamey_native_figures.py:render_mamey_native_figure_set`, `mamey_native_figures.py:FIGURE_SET_SPEC`, `mamey_native_figures.py:RAW_BGC_COUNT_POLICY`

**Role:** Renders the "mamey-native" figure pack from a master workbook. Invoked by `render-figures --figure-set mamey-native --workbook <Mamey_Master.xlsx>`. Requires pandas + numpy + matplotlib.

**v9.7.115 schema adapter:** the module was originally written against pre-v1.1 legacy sheet names (e.g. `Strain_Registry`, `DAPR_Antibacterial`) and CamelCase column names. A `_SHEET_ALIASES` dict maps both legacy and coded (`A2_Strain_Registry`, `C1_DAPR_Antibacterial`) names; `_COL_ALIASES` normalizes snake_case column names to their legacy form. This allows the module to render from a current v1.1 workbook without any workbook change.

**Status distinction (v9.7.115):** distinguishes `NO_DATA` (required sheets resolved, but no DAPR scores present — the cohort hasn't been through a Sapote scoring pass yet) from `NO_FIGURES` (sheets unreadable or genuine rendering failure). Previously both returned `NO_FIGURES`, masking schema drift behind the benign unscored-cohort case.

**Figure outputs (`mamey_native_*.png`):**

| Index | Stem | What it shows |
|---|---|---|
| 01 | `ab_vs_af_portfolio` | AB vs AF lead portfolio scatter; point size ≈ contig count (fragmentation proxy) |
| 02 | `dual_track_leads` | Dumbbell comparison of AB and AF DAPR scores per strain |
| 03 | `top_antibacterial` | Ranked horizontal bar of top-15 AB strains |
| 04 | `top_antifungal` | Ranked horizontal bar of top-15 AF strains |
| 06 | `ecology_readiness` | Ecology readiness ranking (optional; needs `Ecology_Readiness_Audit` sheet) |
| 08 | `rggmci_state_summary` | RG-GMCI state bucket summary |
| 13 | `raw_bgc_qc_only` | Raw BGC count vs contig count — **QC only**; carries RAW_BGC_COUNT_POLICY annotation on the figure |
| 14 | `max_kcb_support` | Strongest KCB support per strain; labelled "similarity, not identity" |
| 15 | `full_depth_inventory` | Full-depth package inventory (optional; needs package sheet) |

---

### 9. `master_figure_atlas.py` — Boss-Ready Atlas

**Source:** `master_figure_atlas.py:FIGURE_ID_REGISTRY`, `master_figure_atlas.py:PALETTE`

**Role:** Renders a cross-strain dashboard/card figure bundle from a master workbook with legacy sheet names (`Strain_Summary`, `Special_Buckets`, `Top_Antibacterial`, `Top_Antifungal`). Produces publication-ready PNGs + SVGs + a ZIP bundle. The atlas pre-dates the schema v1.1 migration; it reads the legacy named sheets rather than the coded A/B/C scheme.

**FIGURE_ID_REGISTRY** (v9.7.73): stable figure IDs with visible IDs (e.g. `CSA18-00`), long IDs with date/revision stamps, purpose strings, slugs, and captions. Registered figures include:

| Visible ID | Slug | Purpose |
|---|---|---|
| CSA18-00 | master_dashboard | Boss-facing cohort dashboard |
| CSA18-01 | cross_strain_dual_priority_node_first | Cross-strain AB vs AF priority scatter |
| CSA18-03 | bgc_boundary_landscape_by_strain | Raw vs corrected BGC burden + assembly tier |
| CSA18-04 | special_bucket_burden_by_strain | Special-review bucket heatmap |
| CSA18-07 | top_lead_board_node_first | Best AB/AF lead per strain |
| CSA18-08 | strain_card_atlas | One card per strain |

All figures use the house palette (`PALETTE`): navy/blue/teal for primary; amber/orange for caution; green for GOOD assembly; red/orange for POOR. `ASSEMBLY_COLORS` maps tier → color.

---

### 10. `collection_figures.py` — Metadata-Gated Collection Bundle

**Source:** `collection_figures.py:FIGURE_REGISTRY`, `collection_figures.py:normalize_metadata`, `collection_figures.py:render_collection_figures`

**Role:** Renders a cross-strain collection figure bundle gated by available metadata fields. The key design: each figure declares its required and optional fields as a `FigureSpec`; `normalize_metadata()` maps column-name variants to canonical names before any gating; `render_collection_figures()` checks each spec against the normalized frame and either renders or writes a skip entry.

**Metadata normalization:** `_ALIASES` maps 19 canonical field names (strain_id, genus, host, source, location, collection_date, candida_call, candida_tested, mrsa_call, mrsa_tested, closest_type_similarity, closest_type_strain, accession, genome_mined, priority, in_vivo, chemistry_done, and two others) to lists of recognized column-name variants. First matching alias wins. Ambiguous matches (multiple aliases resolving to the same canonical) generate a warning, not a failure.

**`NOT_TESTED_VALUES`:** blank, "na", "n/a", "n.t.", "not tested", "nt", "unknown", "not_tested", "none", "nd", "not done", "pending" are treated as not-tested (explicitly distinct from negative). `_is_positive()` accepts only explicit positive tokens: "1", "yes", "true", "positive", "pos", "+", "active", "hit".

**Bioactivity claim-safety:** "positive call" / "activity observation" language only, never "active strain" or "produces". "Not tested" remains distinct from negative in all counts and figures. `LOW_16S_HARD = 98.65%` and `LOW_16S_SOFT = 99.0%` are the species-boundary and novelty-prioritization thresholds; these flag prioritization signals, never species descriptions.

**Layout-safety rules (FB-1 through FB-9):**

| Rule | Value/Policy |
|---|---|
| FB-1 Label density | Min 7pt; top-N + "other" if >MAX_LABEL_ROWS |
| FB-2 Top-N cap | 15 bars max; full data in CSV |
| FB-3 Long names | Word-wrap then truncate |
| FB-4 Heatmap height | Dynamic |
| FB-5 Missing vs zero | Visually distinct (`miss` color vs `neg` color) |
| FB-6 Provenance footer | On every figure |
| FB-7 Non-blocking skip | Any figure failure skips, not crashes |
| FB-8 Export pair | PNG + CSV for every figure |
| FB-9 Stable filenames | Lowercase, stable across runs |

**Registered figures (21 total):**

| figure_id | Required fields | Multi-source required? |
|---|---|---|
| fig_collection_overview | strain_id | No |
| fig_top_genera | strain_id, genus | No |
| fig_shared_unique_genera | strain_id, genus, source | Yes |
| fig_genus_relative_abundance | strain_id, genus, source | Yes |
| fig_candida_counts | strain_id, candida_tested, candida_call | No |
| fig_mrsa_counts | strain_id, mrsa_tested, mrsa_call | No |
| fig_activity_rate | strain_id | No |
| fig_activity_pattern | strain_id, candida_call, mrsa_call | No |
| fig_genus_source_matrix | strain_id, genus, source | Yes |
| fig_genus_activity_heatmap | strain_id, genus, source | No |
| fig_16s_similarity_dist | strain_id, closest_type_similarity | No |
| fig_low_16s_rate | strain_id, closest_type_similarity | No |
| fig_activity_vs_16s | strain_id, closest_type_similarity | No |
| fig_top_hosts | strain_id, host | No |
| fig_top_locations | strain_id, location | No |
| fig_accession_coverage | strain_id, accession | No |
| fig_collection_timeline | strain_id, collection_date | No |
| fig_closest_type_strains | strain_id, closest_type_strain | No |
| fig_followup_candidates | strain_id | No |
| fig_non_streptomyces | strain_id, genus | No |

**Outputs** per run: each eligible figure → `<figure_id>.png` + `<figure_id>_data.csv`. Always: `FIGURE_AVAILABILITY.md` (all 21 figures with gate status) + `figure_manifest.csv`.

---

### 11. `cross_strain_figures.py` — Cross-Strain RG-GMCI Figure Emitter

**Source:** `cross_strain_figures.py:build_cross_strain_figures`

**Role:** Turns RG-GMCI batch CSVs into a complete cross-strain figure folder. Pure extraction-layer — never re-runs RG-GMCI or upgrades product-identity claims.

**Inputs** (looked up by glob pattern from `--rg-dir`):

| Key | Glob patterns | Contents |
|---|---|---|
| summary | `*priority_summary.csv` | One row per strain: BGC counts, assembly tier, pair counts |
| ranked | `*ranked_pairs_all.csv` | All RG-GMCI pairs, strain-tagged |
| global_top | `*global_top150.csv` | Top-150 pairs by score |
| diff | `*summary_diff.csv` | Summary diff between two runs |
| ab_top / af_top | `*AB_top50*.csv` / `*AF_top*.csv` | Optional AB/AF triage CSVs |

**Output contract per figure:** `fig_NN_<key>.png` + `fig_NN_<key>.svg` + `fig_NN_<key>_data.csv`. Every figure has both a PNG (220 dpi) and an SVG, plus the source CSV. A `FIGURE_INDEX.md` carries claim-safety notes.

**Summary-level figures emitted:** ~14 bar/scatter charts covering raw/corrected BGC counts, fragmentation loss, pair counts (HIGH/MODERATE/good-geometry), assembly tier distributions, priority scores. Also boundary composition (Interior/Edge/FC stacked bar) and HIGH+MODERATE pair stacked bar.

**Ranked-pair figures:** confidence class counts, score/reference/identity distributions (histograms), top-pair profiles.

---

### 12. `cohort_figures_bridge.py` — Batch Auto-Fire Bridge

**Source:** `cohort_figures_bridge.py:build_cohort_figures`

**Role:** Closes the gap between `mamey run --strains` (which produces per-strain packages) and `cross_strain_figures.py` (which reads cohort-level RG-GMCI batch CSVs). Automatically fires after a multi-strain batch run.

**Wire:** After `run_batch()` completes with >1 strain, `build_cohort_figures(results, outdir)` is called. It aggregates per-strain packages into two cohort tables:
- `cohort_figs_input/cohort_priority_summary.csv` — one row per strain (raw/corrected BGCs, tier, pair counts, boundary counts)
- `cohort_figs_input/cohort_ranked_pairs_all.csv` — all pairs, strain-tagged

Then calls `build_cross_strain_figures()` on `cohort_figs_input/` to produce the cross-strain figure pack in `<outdir>/cohort_figures/`.

**Fallback for post-hoc runs** (v9.7.88 9.7.88-I): if result dicts lack raw/corrected/tier/interior fields (as happens when running `cohort-figures` subcommand on existing packages), the bridge falls back to `manifest_short.json` in each package dir.

**Bug fixed (v9.7.88 9.7.88-H):** HIGH pair count from ranked CSV was checking `== "HIGH"` but the full label is `HIGH_RG_GMCI_RESCUE`; fixed to prefix-match with `conf(r).startswith("HIGH")`.

Single-strain batches are a no-op by design (gated by `len(ok) < 2`).

---

### 13. `cohort_figures.py` — F-Series Heatmap Generator (Series F)

**Source:** `cohort_figures.py:generate`, `cohort_figures.py:figs_multi`

**Role:** Generates the F-series (heatmaps), G-series, and D-series figure packs from gold package directories. Invoked by the `cohort-figures` CLI subcommand or auto-fired by `run_batch()`.

**Inputs:** reads `deep_data.json`, `gene_data.json`, `manifest_short.json`, and inventory CSVs from each `<runs_dir>/<strain_id>/package/` directory.

**Strain ordering:** PUBLIC (SID/WW) strains first (sorted by raw BGC count), then PRIVATE (AS-/AJS-/PENDING-) strains. A dashed `soft_divider` line separates the two groups on heatmap figures. `--public-only` drops PRIVATE strains for a shareable PUBLIC cut.

**F-series heatmap outputs** (each PNG + sidecar CSV with F0N stamp):

| Stem | Content |
|---|---|
| `census_zscore_heatmap` | Per-strain gene/domain census, z-scored; top strip = assembly tier |
| `megasynthase_heatmap` | 13 core PKS/NRPS catalytic domains (KS, AT, KR, DH, ER, ACP, PCP, C, A, E, TE, LANC_like, YcaO) |
| `product_class_heatmap` | antiSMASH product classes + computed macrolide-type proxy row (KR+DH present) |
| `tailoring_enzyme_heatmap` | Tailoring enzymes: halogenase, chitinase GH18, siderophore synthetase/reductase, P450, methyltransferase, glycosyltransferase |
| `cctt_trigger_heatmap` | CCTT diagnostic-chemistry triggers per BGC count |
| `resistance_tier_heatmap` | Resistance-axis tier distribution |
| `adomain_substrate_heatmap` | NRPS A-domain substrate consensus (inferred) |
| `AT_extender_heatmap` | PKS AT extender-unit consensus (inferred) |
| `transporter_family_heatmap` | Transporter family domain counts |
| `regulator_TF_heatmap` | TF/regulator families (TetR, GntR, LysR, Sigma70, MarR, HTH, AraC) |
| `domain_clustermap_top40` | Top-40 Pfam domains, hierarchically clustered (Ward linkage on log counts; falls back to count-ordered if scipy absent) |
| `active_site_completeness` | Fraction of catalytic active-site residues confirmed present |

G-series (`cohort_figures_g.py`) and D-series (`cohort_figures_d.py`) add complementary and dot/bubble views respectively (see `cohort_figure_captions.py` for the full caption catalog; titles transcribed above in §3).

---

### 14. `cohort_class_heatmap.py` — Cohort Class-Capacity Heatmap

**Source:** `cohort_class_heatmap.py:render_cohort_class_heatmap`, `cohort_class_heatmap.py:build_class_matrix`

**Role:** Strain × biosynthetic-class capacity heatmap from the master workbook's `B2_Product_Class_Matrix` sheet. Invoked by `render-figures --figure-set cohort-class --workbook <cohort.xlsx>`.

**Exclusions:** `STANDING_EXCLUSIONS` from `genus_reference` (centralized PC-A5, v9.7.101); `_NON_CLASS_COLS = {"strain", "counts_reliability"}`. NAPAA is explicitly NOT excluded (registry-neutral since v9.7.22). Zero-count class columns are dropped to keep the figure legible.

**Outputs:** `cohort_class_capacity_heatmap.png` (viridis colormap, count-annotated cells, white/black text based on cell darkness) + `cohort_class_capacity_heatmap_data.csv`. Footer carries the PRIVATE claim-prefix + the standing disclaimer about NAPAA and saccharide exclusion.

---

### 15. `domain_figures.py` — Domain-Level Figures

**Source:** `domain_figures.py:render_domain_figures`

**Role:** Three post-seal, non-blocking figure types from `domain_level/` output tables. Invoked by `render-figures --figure-set domain-level` or automatically if `--emit-figures` is passed to `domain-level` subcommand.

Style settings live in `mamey/data/domain_level/domain_figure_specs.v1.json`, not in code — so the palette and layout can be updated without code changes.

**Outputs per BGC (up to `per_bgc_strip_top=6` BGCs):**

| Figure type | Stem | What it shows |
|---|---|---|
| Role-burden heatmap | `domain_role_burden_heatmap` | Top BGCs × role categories; cell = domain count |
| Core-biosynthetic burden bar | `core_biosynthetic_domain_burden` | Core vs accessory domain burden per BGC |
| Per-BGC domain strip | `<Strain>_<BGC>_domain_strip` | Node-first ordered domain arrows (one strip per BGC) |

All outputs are non-blocking; a failure writes a skip card and leaves prior outputs intact.

---

### 16. Tier-Specific Behavior

The figure system has one hard public/private boundary: any figure set containing a PRIVATE strain (AS-/AJS-/PENDING-) is tagged PRIVATE. The `cohort_figures.py` `--public-only` flag drops these. The cohort class heatmap accepts a `claim_prefix` argument that prepends the release tag to the figure footer. The locus map's `claim_prefix` argument serves the same purpose.

In the `render-figures --figure-set mamey-native` path, the tier is inferred from the package's BGC release tags (first non-empty `release` field in the manifest BGC list, defaulting to PRIVATE).

---

*Mamey engine v1.9.110 · Bundle v9.7.319*  
*All figure stems, constants, and policy rules cited from source. Claim-safety language is enforced in figure footers, not just documentation.*
## Plumbing Reference — P4: Packaging, Sealing, and Output

> ⚠️ **STALE, v9.7.213 audit.** Same module-inventory staleness as P3 above. Verified against the live tree
> on 2026-07-06: *package_addons_html.py* no longer exists as a separate file — only `mamey/package_addons.py`
> is present now. Not independently confirmed elsewhere in-bundle (unlike the P3 renames), so treat as
> "missing, cause unconfirmed" rather than a traced rename.

**Source modules (per the .213 audit — see staleness note above; italics = confirmed gone in .213):** `gene_context.py` (214), `packaging.py` (44), `output_checklist.py` (150), `render_brief.py` (678), `render_safe.py` (194), `report_mode.py` (99), `serialize.py` (98), `package_addons.py` (266), *package_addons_html.py* (221)  
**Engine version:** Mamey v1.9.110 · Bundle v9.7.319

This cluster covers everything that happens after the source-scan and scoring phases seal their results into the package: writing the gene context, rendering the strain brief and figures, serializing the deterministic↔judgment boundary, writing the analysis-forward directive, producing the HTML collaborator view, and packaging the final ZIP.

---

### 1. `gene_context.py` — Sealed Per-CDS Gene Context (v9.7.88)

**Source:** `gene_context.py:write_gene_context`, `gene_context.py:build_gene_context`, `gene_context.py:load_gene_context`  
**Role:** Serializes normalized per-CDS records into the package so Mode B and gene-by-gene walkthroughs work post-seal without re-opening the original antiSMASH ZIP.

**The problem it solves (roadmap #1 / AS-XXX finding E):** Before v9.7.88, the sealed package had no gene-level context. The gene-by-gene builder fell back to a single synthetic `<bgc>_NOLOCUS` row per BGC — not gene-resolved. Mode B could not do true gene-by-gene walkthroughs in a ChatGPT/sealed context.

**Schema:** `gene_context/1.0`

**Per-CDS row fields:**

| Field | Source | Notes |
|---|---|---|
| `locus_tag` | CDS qualifier | None if absent |
| `contig` | CDS feature | antiSMASH contig ID |
| `start`, `end` | CDS coordinates | 0-based |
| `strand` | CDS feature | +1 / -1 |
| `length_bp` | `end - start + 1` | |
| `aa_length` | translation length | Falls back to `(end - start + 1) // 3 - 1` when translation absent |
| `product` | CDS qualifier | antiSMASH product annotation |
| `sec_met_domains` | domain features | Sorted set of domain names for this CDS |
| `gene_functions` | qualifiers `gene_functions` + `sec_met_domain` + `note` | Blob used by locus-map classifier |
| `gene_kind` | qualifier `gene_kind` | Kept for functional-role profiling (P-CBDB v9.7.100) |
| `tta_codons` | nucleotide_seq scan | TTA codon count for bldA tier |
| `has_translation` | bool | True when full translation is present |

**Assignment rule:** A CDS is assigned to a BGC when it shares the BGC's contig AND its coordinates overlap the BGC span. A CDS may appear under multiple BGC IDs only if those BGCs overlap (rare).

**Two output files (both atomic write with .tmp rename):**

| File | Format | What it holds |
|---|---|---|
| `<strain>_gene_context.jsonl` | JSONL (one JSON object per line) | Line 0: header `{schema_version, claim_safety, n_cds, n_bgcs_with_cds}`; subsequent lines: `{bgc_id, cds: [row, ...]}` ordered by start coordinate within each BGC |
| `<strain>_cds_table.csv` | CSV | 13 fields (list below) |

**Reading back (`load_gene_context`):** Returns `{bgc_id: [cds_row, ...]}`. Skips the header line (detected by absence of `bgc_id` key). Returns empty dict silently if the file is absent. Safe to call on pre-v9.7.88 packages.

**Claim-safety note built into the schema:** "Structural gene context from GenBank CDS features; no product-identity or activity claim."

---

### 2. `packaging.py` — Manifest, Checksums, and ZIP

**Source:** `packaging.py:write_manifest`, `packaging.py:zip_package`, `packaging.py:write_checksums`

The smallest module in P4. Three functions, no dependencies beyond stdlib.

**`write_manifest(package_dir)`:**
- Recursively scans all files in the package dir (excludes `manifest.json` and `checksums_sha256.txt` themselves)
- For each file: records relative path, SHA-256 hash, and byte size
- Merges the file inventory into the existing `manifest.json` (preserving the run snapshot: mode, bgcs, scans) rather than replacing it
- Writes `checksums_sha256.txt` in `<sha256>  <relative_path>` format

**`zip_package(package_dir, zip_path)`:**
- Removes existing zip if present
- Writes a DEFLATE-compressed ZIP; all files use their path relative to `package_dir.parent` (so `<strain_id>/package/...` is preserved inside the ZIP)
- ZIP name format (from `cli.py:1287`): `{strain_id}_SapoteMamey_v{BUNDLE_VERSION}_engine{__version__}_Complete_Package.zip`

**`write_checksums(package_dir)`:** variant that writes only `checksums_sha256.txt` without regenerating `manifest.json`.

**Seal-first architecture (v9.7.88 Finding L):** `MAMEY_SEAL_FIRST=1` (default) means `write_manifest()` + `zip_package()` run BEFORE `render_brief()`. The brief and its figures are written to the package dir afterward but are NOT included in the core checksums. This is the reliability split: scientific artifacts (manifest, triage, scans, gene context) are guaranteed sealed; figures are best-effort cosmetics.

---

### 3. `output_checklist.py` — Output Completeness Checklist

**Source:** `output_checklist.py:write_output_checklist`, `output_checklist.py:build_output_checklist`

**Role:** Writes a user-facing status table showing which deliverables are produced (extraction-layer) vs pending (judgment-layer). Written to both CSV (`<strain>_6_output_checklist.csv`) and Markdown (`<strain>_6_output_checklist.md`).

**Checklist structure (phases and their rows):**

| Phase | Row | Status logic |
|---|---|---|
| Run setup | Intake metadata locked | File exists: `<strain>_1_intake.json` |
| Extraction | BGC inventory table | File + raw_n > 0 |
| Extraction | Auto triage board | File exists: `<strain>_4_triage_board.csv` |
| Workbook | Per-strain workbook | File exists: `<strain>_5_workbook.xlsx` |
| Packaging | Manifest and checksums | `manifest.json` + `checksums_sha256.txt` both exist |
| Deliverable | Deterministic strain brief | `<strain>_8_strain_brief.pdf` present → COMPLETE (extraction-layer); absent → SKIPPED |
| Deliverable | Sapote-layer figures (DAPR scatter, AB/AF ranked, funnel) | `<strain>_8d_fig_ab_ranked.png` present → COMPLETE; absent → SKIPPED |
| Source scans (×9) | KCB, FLBR, CCTT, CGAD, UMED, EFLS, resistance, bldA_TTA, TFBS | Status from `run.scan_status` dict |
| Source scans (×8) | 8 fields (list below) | Present/absent from `SourceScanBundle` attributes |
| Sapote judgment | Full Mode B status | Always JUDGMENT_PENDING at extraction time |
| Sapote reporting (×4) | Technical report PDF, DAPR table, Fermentation plan, Layperson guide, Bench guide | Always REQUIRED at extraction time |

**Column schema:** Phase, Output_or_task, Expected_artifact_or_evidence, Status, Progress, Evidence, Next_action

The "JUDGMENT_PENDING" and "REQUIRED" statuses make it explicit to any operator or LLM reading the package that Mamey delivers the skeleton, not the finished analysis.

---

### 4. `render_brief.py` — Deterministic Strain Brief

**Source:** `render_brief.py:render_brief`, `render_brief.py:load_facts`, `render_brief.py:strain_display_label`

**Role:** Renders a PDF strain brief and the full per-strain figure pack. Reads ONLY `manifest.json` + `*_4_triage_board.csv` from the sealed package — no new analysis, no judgment-layer slots.

**`load_facts(pkg)`:** The brief's data contract function. Reads the manifest and normalizes triage rows to a canonical shape with fields: rank, bgc_id, contig, region, products, boundary, arch, ab, af, novelty, lead_tier, kcb_top, kcb_score, cctt. Uses `col(r, *names)` to tolerate header supersets and column renames.

**`strain_display_label(manifest)`:** Enforces the strain-label hierarchy:
1. `"<Genus species> strain <ID>"` when taxonomy is real and strain ID has a hyphen
2. Canonical strain ID alone
3. Full accession WITH an explicit `"(NO STRAIN NAME — accession shown)"` warning (never a sliced accession prefix)

The WWKH/WWJO bug guard: if the strain ID is purely alphanumeric and prefixes the accession (e.g. `WWKH` prefixes `WWKH00000000`), it is treated as an accession echo, not a real strain name, and is blanked.

**JUDGMENT_SLOTS** (`render_brief.py:24`): Seven slots that must never be rendered as populated:
`top_bgc_targets`, `split_pathway_candidates`, `hallucination_traps_triggered`, `wet_lab_priorities`, `metabolomics_targets`, `missingness`, `recommended_next_steps`. The brief's footer text states these are pending a Sapote pass. (See patch flag P4-F3 — this is a passive guard, not an active assertion.)

**Figure outputs emitted by `render_brief()`** (all best-effort, non-blocking):

| Stem | Module | What |
|---|---|---|
| `8a_fig_landscape` | `render_brief.fig_landscape` | BGC priority landscape bar; AB solid, AF faded; boundary-coloured; pure-saccharide omitted |
| `8b_fig_composition` | `render_brief.fig_composition` | Product-class composition (standard tier only) |
| `8c_fig_dapr_scatter` through `8f_fig_funnel` | `figures_sapote` | DAPR scatter, AB/AF ranked, claim-safety funnel |
| `8g_fig_class_distribution` through `8m_fig_genome_atlas` | `figures_extra` | Extended figure pack (7 figures) |
| `8n_fig_rggmci_rescue` | `render_brief.fig_rggmci_rescue` | Fragment rescue candidates from ranked pairs CSV |
| `8n_fig_ab_af_panels` | `figures_sapote.fig_ab_af_vertical_panels` | Combined AB+AF vertical panel (v9.7.72) |
| Split-pathway figures | `figures_split` | High-KCB and RG-GMCI topology figures (best-effort; requires raw GBKs) |
| `_cnbu.json` | `cnbu.compute_cnbu` | CNBU sidecar JSON (v9.7.72) |
| `PRINT_FIGURE_PACK.*` | `figures_sapote.write_print_figure_pack` | Print-ready pack (v9.7.72) |

**PDF structure (standard tier):**
1. Text page: strain ID, taxonomy, source, assembly stats, BGC counts, key capacity signals, corrected-count formula, claim-safety bullets, JUDGMENT_SLOTS footer
2. Landscape figure page (BGC priority bar)
3. Composition page (product classes)
4. One page per emitted PNG (all figures bound into single PDF)
5. Layperson overview page (if judgment store has layperson text)
6. Fermentation notes page (if judgment store has fermentation text)

**PDF (minimal tier):** text page + landscape figure only.  
**PDF (none tier):** returns `{"status": "DISABLED"}` immediately — the entire render is skipped.

**Claim-safety constants** used across the figure layer:
- `KCB_NOTE = "KCB = similarity, not identity"`
- `SCORE_NOTE = "AB/AF/Novelty are auto-computed priority scores, not activity measurements"`
- `GAP_NOTE = "Mode B, DAPR, fermentation, layperson and bench-guide deliverables are produced by the Sapote judgment pass and are not part of this sealed extraction package."`
- `AFFILIATION = ""`
- `CORRECTED_FORMULA = "Interior + ½·Edge + ¼·Full-contig"`

---

### 5. `render_safe.py` — Layout-Safe Rendering Helpers

**Source:** `render_safe.py:clean_scalar`, `render_safe.py:safe_kcb_display`, `render_safe.py:locus_label`, `render_safe.py:shorten_label`

**Role:** Shared helpers used across all figure and PDF modules. Dependency-light; pure Python.

**`clean_scalar(value)`:** Converts any value to a plain Python scalar safe for Markdown/PDF output. Strips numpy reprs (`np.int64(48)` → `48`), converts `nan`/`inf` to empty string, dicts to a `key: value` summary (≤6 entries), and lists to semicolon-joined strings.

**`safe_kcb_display(record)`:** The provenance-aware claim-safety gate for KCB anchor display. Three paths:

| Provenance | Output format |
|---|---|
| `MIBIG_REFERENCE_LINE` | `"<raw_kcb_top> (similarity)"` |
| Has `closest_candidate_kcb_product` (not UNRESOLVED) | `"~<safe_product> (similarity anchor only)"` |
| `KCB_TOP_FIELD` or unknown | `"~<raw_kcb_top> (source-derived similarity anchor only; not product identity)"` |
| Nothing | `"unresolved"` |

This is the authoritative KCB display surface for all prose. The `_kcb_short()` in `figures_sapote.py` is a figure-label shortening helper (18-char truncation for tick labels), NOT a semantic claim-safety gate.

**`locus_label(value)`:** Builds a node/contig-first label for figures: `"<contig> <region> (<bgc_id>)"`. Accepts both dict and object inputs. Bounded by `shorten_label` at `max_chars=42`.

**`figure_text_overlap_report(fig)` / `assert_no_figure_text_overlap(fig)`:** Matplotlib smoke-test for CI. Reports text-element bounding-box overlaps > 2 pixels. Not used in production figure rendering; called from tests.

---

### 6. `serialize.py` — Deterministic↔Judgment Boundary

**Source:** `serialize.py:records_payload`, `serialize.py:verdicts_payload`, `serialize.py:write_boundary_payloads`

**Role:** Serializes the two sides of the W4/W23 deterministic↔judgment boundary into audit-ready JSON, enabling `mamey.boundary_audit` to diff them and reviewers to inspect the contract directly.

**Two files written:** `<strain>_records.json` (deterministic facts) and `<strain>_verdicts.json` (judgment layer), both atomically via `.tmp` rename.

**`records_payload`** (schema `mamey.records/1`) — deterministic side only. Deliberately no scores:

| Field | From |
|---|---|
| bgc_id, contig, node_id, user_label | BGCRecord |
| region_number, antismash_region | BGCRecord |
| edge_status | BGCRecord |
| products, mibig_hits | BGCRecord |
| architecture_confidence, architecture_capacity | BGCRecord |
| kcb_top, kcb_cumulative | BGCRecord |

**`verdicts_payload`** (schema `sapote.verdicts/1`) — judgment side:

| Field | From | Notes |
|---|---|---|
| bgc_id, contig, user_label | TriageRecord | |
| lead_tier, claim_confidence | TriageRecord | |
| corrected_rank, standing_rule_flag | TriageRecord | |
| primary_metabolism_flag, misanchor_flag | TriageRecord | |
| ab_score, af_score, novelty_score | TriageRecord | |
| kcb_similarity_band | `precision.similarity_band(kcb_cumulative)` | **W26: coarse band, never a bare bitscore** |
| concordance_verdict | TriageRecord | C1 v9.7.58 |
| umed_gap_flag | TriageRecord | v9.7.62 |

**W26 design:** The similarity band converts the raw KCB cumulative bitscore to a coarse bucket to prevent false precision in judgment-facing outputs. The band is intentionally non-invertible.

---

### 7. `report_mode.py` — Terse Board and Mode B Scaffold

**Source:** `report_mode.py:render_terse`, `report_mode.py:render_full_scaffold`, `report_mode.py:render_board`

**Role:** Generates the compact terse board (default) or the full §1–§8 Mode B scaffold written into `ANALYSIS_FORWARD.md` for use as Sapote session input.

**`render_terse(record, verdict)`:** One line per BGC:
```
<node/contig> (<bgc_id>)  —  <lead_tier>/<claim_confidence>  ·  <arch_capacity>  ·  KCB:<band> (similarity, not identity)[flags]
```
Always carries the contig/node (never a bare BGC ID) and the similarity band (never a raw number) — W26.

**`render_full_scaffold(record, verdict)`:** The §1–§8 skeleton with deterministic facts pre-slotted under each heading. The judgment layer fills prose into this fixed, fact-anchored skeleton rather than reconstructing fields from scratch. Six of the eight sections have pre-filled deterministic facts; §5 (source-derived scans) and §6 (bioactivity context) carry only the placeholder `_(judgment layer: prose here)_`.

**`MODE_B_SECTIONS`:** The eight canonical section headings:
1. Identity & location
2. Architecture & class capacity
3. Boundary / truncation caveats
4. KCB / MIBiG similarity (similarity, not identity)
5. Source-derived scans (cassettes, resistance, regulators)
6. Non-isolation / bioactivity context
7. Lead tier & claim calibration
8. Standing-rule / mis-anchor flags

**`render_board(records, verdicts, mode, full_ids)`:** Renders the full board. `DEFAULT_MODE = "terse"`. Pass `mode="full"` for everything, or `full_ids={bgc_id, ...}` to expand specific BGCs (terse for the rest).

---

### 8. `package_addons.py` — Diagnostic Rescue 4B and Analysis-Forward

**Source:** `package_addons.py:emit_rescue_4b`, `package_addons.py:write_analysis_forward`, `package_addons.py:add_d4_sheet`

#### 8.1 Diagnostic Rescue 4B

`emit_rescue_4b(package_dir, clusterblast_dir)` reads the RG-GMCI full JSON (`*_4A_RGGMCI_full.json`) and builds diagnostic rescue leads via `diagnostic_rescue.build_leads()`. Writes four files:

| File | Contents |
|---|---|
| `<strain>_4B_Diagnostic_Rescue_Leads.csv` | 20-column table: pair, rescue_tier, kcb_concordance, core/arm BGC+node+triggers+KCB family, shared_scaffold, reference gene coverage, overlap fraction, tiling verdict, claim_ceiling, safe_claim |
| `<strain>_4B_Diagnostic_Rescue_Leads.json` | Same leads as structured JSON with `claim_ceiling` and `tiling_basis` |
| `<strain>_4B_Diagnostic_Rescue_Tiling.csv` | Tiling-specific columns only (pair, scaffold, ref_source, coverage, fraction, verdict) |
| `<strain>_4B_Diagnostic_Rescue_Leads.md` | Human-readable markdown table |

`add_d4_sheet(workbook_path, leads)` adds/replaces a `D4_Diagnostic_Rescues` sheet on the per-strain workbook.

#### 8.2 ANALYSIS_FORWARD

`write_analysis_forward(package_dir, top=12)` writes two files:
- `<strain>_ANALYSIS_FORWARD.md` — the judgment directive
- `<strain>_analysis_forward.json` — machine-readable sidecar for session-log compiler

The ANALYSIS_FORWARD markdown structure:
1. Status header: EXTRACTION COMPLETE / JUDGMENT PENDING (or COMPLETE if judgment fields found)
2. If pending: start-judgment trigger phrase (`"Run full Sapote analysis on <strain>"`), compilation order (Layperson's Guide → Synopsis → Chapter → KCB → Mode B → Fermentation Card)
3. "Judge these first" section: HIGH-confidence diagnostic rescue pairs (★ flagged in the worklist)
4. "Worth a look" section: up to 8 MODERATE rescue leads
5. Priority worklist: top-12 by `_LEAD_TIER_ORDER` (Exceptional → High → Medium → Low → Inventory, tie-broken by corrected_rank — the N-01 fix ensuring bottom-tier or standing-rule-downgraded fragments do not outrank real leads)
6. Progress tracker checkboxes
7. Terse board (Sapote session input) from `report_mode.render_board`
8. Claim ceiling footer

**`COMPILATION_ORDER`:** `["Layperson's Guide", "Synopsis", "Chapter", "KCB", "Mode B (BGC# order)", "Fermentation Card"]`

---

### 9. `mamey/package_addons.py` — OPEN_ME_FIRST.html

**Source:** `package_addons_html.py:write_open_me_first`

**Role:** Writes `OPEN_ME_FIRST.html` — the collaborator-facing package entry point. Reads `manifest_short.json` (fast path) or `manifest.json` (fallback) and renders a self-contained HTML page with no external dependencies.

**HTML contents:**
- Header with strain name, status badge (PASS/FAIL), mamey version
- Assembly stats: tier, raw/corrected BGC counts, genome bp
- Top-3 antibacterial and antifungal leads with BGC ID, contig, score
- Key files table with links to manifests and triage boards
- Claim-safety section: bullet points stating "All assignments are bioinformatic predictions", KCB = similarity not identity, bioactivity is extract-level default
- Judgment-pending section: trigger phrase, judgment status

The HTML is kept deliberately minimal and self-contained (no external CSS, no JS framework) so it renders correctly in any browser without network access.

**Known file list rendered in the HTML** (from `package_addons_html.py:115`):
- `OPEN_ME_FIRST.html` (self)
- `manifest_short.json`
- `<strain>_4_triage_board.csv`
- `<strain>_8_strain_brief.pdf`
- `<strain>_gene_context.jsonl`

---

### 10. Execution Position in `run_one_strain()`

For reference, the P4 modules execute in this order within `run_one_strain()`:

| Step | Module | Output |
|---|---|---|
| 10 | `gene_context.write_gene_context` | `<strain>_gene_context.jsonl` + `<strain>_cds_table.csv` |
| 15 | (triage scoring, not P4) | `*_4_triage_board.csv` |
| 16 | `package_addons.emit_rescue_4b` | `*_4B_*` files |
| 17 | `cell_provenance.write_cell_provenance` | `*_cell_provenance.csv` + `*_missing_data_worklist.csv` |
| 18 | `cli._write_package` → `serialize.write_boundary_payloads` | `*_records.json` + `*_verdicts.json` |
| 18 | `output_checklist.write_output_checklist` | `*_6_output_checklist.csv/.md` |
| 18 | `cli:~1212` | `manifest_short.json` |
| 18 | `package_addons_html.write_open_me_first` | `OPEN_ME_FIRST.html` |
| 18 | `package_addons.write_analysis_forward` | `*_ANALYSIS_FORWARD.md/.json` |
| Seal | `packaging.write_manifest` + `packaging.zip_package` | `manifest.json` + `checksums_sha256.txt` + Complete_Package.zip |
| Post-seal | `render_brief.render_brief` (subprocess, non-blocking) | `*_8_strain_brief.pdf` + all figures |

---

*Mamey engine v1.9.110 · Bundle v9.7.319*  
*All file names, field names, and constants cited from source.*


**Field lists** for the wide rows above:

- **<strain>_cds_table.csv**: Flat per-CDS table: bgc_id, contig, locus_tag, order, start, end, strand, length_bp, length_aa, product, sec_met_domains, gene_functions (truncated to 300 chars), tta_codons.
- **row1**: chitinase, regulators, transporters, cassettes, wetlab_rows, qs_signals, glycosylation_arms, per_bgc_dss.

## Plumbing Reference — P5: Stores, Telemetry, Orchestration, and Supporting Infrastructure

**Source modules:** `judgment_store.py` (455), `timing.py` (311), `validate.py` (167), `deep_data.py` (177), `mode_b_receipt.py` (209), `mode_b_quality_gate.py` (324), `cohort_resolver.py` (134), `id_resolver.py` (39), `cohort_cards.py` (132), `cohort_synthesis.py` (343), `cross_strain_card_context.py` (158), `external_adapters.py` (190), `compat_v941.py` (227), `_gbk_shim.py` (139), `dedup_and_guard.py` (96), `merge_policy.py` (78), `cnbu.py` (171), `models.py` (367)  
**Engine version:** Mamey v1.9.110 · Bundle v9.7.319

---

### 1. `models.py` — Core Data Contracts

**Source:** `models.py`

The four dataclasses that define the extraction-layer type system. "Extraction layer only. No WL scoring, no claim confidence, no prose."

#### `AssemblyMetrics`
Fields: `genome_bp`, `contigs`, `n50`, `gc_pct`, `largest_contig`.

#### `CDSFeature`
One per antiSMASH GBK CDS feature. Fields: `contig`, `start`, `end`, `strand`, `locus_tag`, `product`, `translation`, `nucleotide_seq`, `qualifiers` (dict). Passed to `gene_context.build_gene_context()`.

#### `DomainFeature`
One per antiSMASH aSDomain/PFAM_domain/CDS_motif/module feature. Fields: `contig`, `start`, `end`, `strand`, `feature_type`, `locus_tag`, `domain`, `database`, `bitscore`, `evalue`, `qualifiers`.

#### `BGCRecord`
The central per-BGC data object. 35+ fields at extraction time; key groups:

**Identity and location:**
- `bgc_id` — BGC001…BGCnnn, locked at parse time, immutable
- `contig`, `region_number`, `start`, `end`, `contig_length`
- `antismash_region` (e.g. "region004"), `source_gbk`, `node_id`, `user_label`
- `edge_status` — "Interior" / "Edge" / "Full-contig"

**KCB provenance chain** (schema v1.1 product/source contract):
- `kcb_top` — the resolved MIBiG identity line when one exists (not the raw rank-1 line); `clusterblast_top` preserves the displaced rank-1
- `kcb_cumulative`, `kcb_protein_hits`, `riq_score`, `riq_label`
- `closest_mibig_accession`, `closest_candidate_kcb_product`, `closest_product_provenance` — default "UNRESOLVED"
- `source_kcb_file`, `source_kcb_locator`, `kcb_hit_rank`, `denominator_type`
- `parse_confidence` — default "LOW"
- `needs_manual_kcb_check` — default "yes"
- `product_claim_ceiling` — default "unresolved; do not use product name"

**Architecture:**
- `architecture_confidence` — A–E (parsers.py assigns; prompt refines)
- `architecture_capacity`, `architecture_class_confidence` — v9.7.21 claim-safe class-capacity call

**Special flags:**
- `composite_region` / `single_protocluster_count` / `protocluster_breakdown` — antiSMASH region-merge inflation guard
- `ks_domain_count` — authoritative PKS_KS aSDomain count
- `ene_ks_count` — Enediyne-KS subtype count
- `compound_class_annotation` — v9.7.86 deterministic chemotype annotation
- `release` — PUBLIC/PRIVATE
- `cctt_triggers`, `cctt_uncorroborated`

The `crosswalk_dict()` method returns the stable identifier map (bgc_id, user_label, contig, node_id, antismash_region, region_number, source_gbk, start, end, contig_length, edge_status, products) used in manifest.json bgc_crosswalk.

#### `TriageRecord`
Per-BGC scoring output from `scoring.triage_bgcs()`. Key fields:
- `bgc_id`, `ab_score`, `af_score`, `novelty_score`, `lead_tier`, `claim_confidence`, `rationale`
- `corrected_rank` — rank among non-downgraded, non-primary-metab leads (None for excluded BGCs)
- `standing_rule_flag` — permanent-exclusion downgrade (saccharide/NAPAA/hglE-KS)
- `primary_metabolism_flag` — v9.7.7 housekeeping/pigment core-gene guard
- `misanchor_flag` — v9.7.15 aminoglycoside(no-DOIS) / polyene(<4 PKS_KS) anchor downgrade
- `mobile_element_flag` — v9.7.33 mobile/ICE machinery
- `contig`, `user_label` — carried so DAPR tables never show a bare BGC ID
- `concordance_verdict` — C1 v9.7.58: CONCORDANT/PARTIAL/DISCORDANT/NO_REFERENCE
- `umed_gap_flag` — v9.7.62: MATURATION_GAP for RiPP/nucleoside BGCs lacking maturation genes

#### `SourceScanBundle`
Container for all 19 source-scan result dicts from `run_source_scans()`. Key scans: `chitinase` (CGAD), `tfbs`, `blda_tta`, `regulators`, `transporters`, `resistance`, `cctt`, `flbr`, `cassettes`, `umed`, `efls`, `domain_architecture`, `resistance_tiers`, `wetlab_rows`, `qs_signals`, `glycosylation_arms`, `per_bgc_dss`, `rggmci`. Plus v9.7.100 additions: `clusterblast_genes`, `functional_profiles`.

#### `RunContext`
Run metadata: `strain_id`, `display_name`, `version`, `analysis_mode` (smoke|gold — "standard" retired v9.7.92, aliased to gold), `input_zip`, `outdir`, `taxonomy`, `source`, `bioactivity`, `master_path`.

#### `MameyRun`
Top-level run container: `context`, `assembly`, `bgcs`, `scan_status`, `source_scans`, `issues`. The `to_dict()` method produces the full manifest.json snapshot — the deterministic↔judgment handoff object. Carries seven judgment-layer slots as empty lists: `top_bgc_targets`, `split_pathway_candidates`, `hallucination_traps_triggered`, `wet_lab_priorities`, `metabolomics_targets`, `missingness`, `recommended_next_steps`.

---

### 2. `judgment_store.py` — Persistent Mode B Register

**Source:** `judgment_store.py`

The write path that was missing before v9.7.67: Sapote's LLM output was produced in-session but never written to disk, so render_brief had no data to populate PDF-003/004 pages.

#### File layout

| File | Written by | Read by |
|---|---|---|
| `<pkg>/<strain>_judgment_register.json` | `init_register`, `record_mode_b` | `read_register`, `batch_status`, `compile_ready` |
| `<pkg>/judgment/<strain>_<BGC_ID>_mode_b.md` | `record_mode_b` | `read_mode_b`, PDF compilation |
| `<pkg>/judgment/<strain>_laypersons_section.md` | `record_mode_b` (append) | `read_laypersons`, `render_brief` PDF-003 |
| `<pkg>/judgment/<strain>_fermentation_section.md` | `record_mode_b` (append) | `read_fermentation`, `render_brief` PDF-004 |

All file writes are atomic (`.tmp` + `os.replace`). Layperson and fermentation accumulation files are append-mode under `## BGC_ID` headers; `update_e1_from_judgment` extracts per-BGC snippets via `## {bgc_id}` regex.

#### Register schema (`schema_version: "1.0"`)

Top-level fields: `strain_id`, `total_bgcs`, `complete_bgcs`, `completion_pct`, `judgment_status` (PENDING / IN_PROGRESS / COMPLETE / NOT_INITIALISED / CORRUPT), `mamey_init_timestamp`, `last_sapote_session`, `bgcs` (dict).

Per-BGC register row: `status` (PENDING / COMPLETE), `mode_b_file`, `session_id`, `timestamp`, `quality_tier` (FULL / SHALLOW / STUB / UNKNOWN), `quality_message`, `char_count`, `section_count`.

#### Key functions

| Function | Called by | Behavior |
|---|---|---|
| `init_register(pkg, strain_id, bgc_ids)` | Mamey CLI after extraction | Idempotent — preserves existing COMPLETE rows; only adds missing BGC slots. Never wipes partial Sapote progress. |
| `record_mode_b(pkg, bgc_id, mode_b_md, ...)` | Sapote (judgment layer) | Writes per-BGC .md, appends layperson/fermentation sections, evaluates quality gate at write time (passive — records but never blocks), updates register. Returns `{path, verdict}`. |
| `batch_status(pkg, ranked_bgc_ids)` | CDSW session resume, output checklist | Returns rank-ordered per-BGC status list (FULL / SHALLOW / STUB / NOT_STARTED) and aggregate counts. `compile_ready` = `n_full == total`. |
| `compile_ready(pkg, ranked_bgc_ids)` | Master PDF compilation gate | Returns `(True, reason)` only when every BGC is FULL. Blocks partial strains from a masquerading final compilation. |
| `incomplete_cards(pkg)` | Audit pass | Returns register rows for every COMPLETE card whose `quality_tier` is not "FULL". |
| `read_register`, `read_laypersons`, `read_fermentation`, `read_mode_b` | render_brief, update_e1, batch orchestration | All return safe defaults (empty string / stub dict) if not yet initialised. |

---

### 3. `mode_b_quality_gate.py` — Card Depth Enforcement

**Source:** `mode_b_quality_gate.py:evaluate_card`, `mode_b_quality_gate.py:FLOORS`

Structural depth gating for Mode B cards. Enforced at every `record_mode_b` call. **Does NOT block ingest** — records the quality tier so the gap is visible, not silent.

#### Floors (raised 2026-06-22 for §1–§10 contract)

| Priority tier | Rank range | Char floor |
|---|---|---|
| HIGH | Top 10 | 9,000 chars |
| MID | Ranks 11–25 | 8,000 chars |
| LOW | Ranks 26+ | 6,000 chars |
| STUB (any) | — | < 2,000 chars |

**Fragment-floor exemption (v9.7.114):** Edge/Full-contig clusters with `cds_count ≤ 22` (`FRAGMENT_CDS_MAX`) use a reduced floor of 2,500 chars (`FRAGMENT_FLOOR`). Interior clusters with the same CDS count are NOT exempt — a small intact cluster still owes full depth. Missing `edge_status` → no exemption (conservative).

#### FULL verdict criteria (all must pass)
1. `n_chars ≥ floor` (tier-appropriate or fragment floor)
2. `n_gene ≥ 5` (locus tags + domain terms combined: `_RE_LOCUS` + `_RE_DOMAIN` counts)
3. `n_sections ≥ 4` (distinct section-header matches: `_RE_SECTION`)
4. Both §9 and §10 explicitly present (`REQUIRED_SECTION_NUMBERS = (9, 10)`)
5. §11–§20 enrichment block ≥ 1,000 chars (`MIN_ENRICHMENT_CHARS`)

#### `_RE_LOCUS` — the REFINED4 regex (confirmed fixed in v9.7.111)
```
ctg\d+_\d{1,6}(?:_[a-z][a-z_]*)?
|[A-Za-z]{2,8}\d*_\d{4,6}
```
The first arm matches real antiSMASH contig loci including RiPP-precursor class suffixes (e.g. `ctg42_21_lanthipeptide`). Validated at 100% match / 0 FP across 9,312 locus tags from five genera. This was the P0 `_RE_LOCUS` bug fix: the prior regex matched 0% of real locus tags.

#### `_RE_SECTION_NUM` — explicit §-number extraction
`r'§(10|[1-9])'` — matches §1 through §10 (10-first to avoid parsing §10 as §1+0). `present_section_numbers(text)` returns the set of integers. The gate checks `{9, 10} ⊆ present_section_numbers(text)`.

#### `_RE_ENRICHMENT_HEAD`
`r'§(?:20|1[1-9])\b'` — matches §11 through §20. `_enrichment_chars` measures the char span from the first such header to end-of-card.

#### Quality tiers
- **FULL** — meets all five criteria
- **SHALLOW** — above FLOOR_STUB but fails at least one FULL criterion; `quality_message` lists what's missing
- **STUB** — < 2,000 chars; fragments at this depth are not held to §9/§10

---

### 4. `mode_b_receipt.py` — The Sapote→Store Ingest Front Door

**Source:** `mode_b_receipt.py:ingest_receipt`, `mode_b_receipt.py:ingest_receipts_command`

The front door the judgment layer lacked: a documented JSON contract that a Sapote session emits at end-of-batch, consumed by `mamey ingest-receipts` to drive both the judgment store and the workbook E1 sheet.

#### Receipt schema (`mode-b-receipt-1.0`)

```json
{
  "schema_version": "mode-b-receipt-1.0",
  "strain_id": "AS-XXX",
  "session_id": "sapote_2026-06-19_AF",
  "cards": [
    {
      "bgc_id": "BGC018",
      "mode_b_md": "# §1 Identity ...",
      "layperson_paragraph": "...",
      "fermentation_note": "..."
    }
  ]
}
```
Only `bgc_id` + `mode_b_md` are required per card. `strain_id` and `session_id` are optional; `strain_id` is resolved from the package if absent.

#### Ingest behavior
- **Fail-closed:** unknown BGC IDs (not in the register) are reported and skipped — never invented.
- **Idempotent:** re-ingesting the same receipt overwrites the card and refreshes timestamps; the register deduplications naturally.
- **Quality gate at ingest:** SHALLOW cards print WARNING, STUB cards print CRITICAL to stderr — neither is blocked from the store.
- **Register not pre-initialised:** raises `ValueError` — run a Mamey extraction first.
- **Optional workbook update:** if `--master` is supplied, calls `update_e1_from_judgment` after all cards are stored.

#### Return value
`{"strain_id", "recorded": [bgc_ids], "skipped_unknown": [bgc_ids], "skipped_no_content": [bgc_ids], "register_status", "complete_bgcs", "total_bgcs", "quality": <summary_line>, "quality_verdicts": [...], "e1_updated": bool, "e1_summary"}`

---

### 5. `timing.py` — Run Telemetry

**Source:** `timing.py:TimingRecorder`

Every completed run emits three timing files into the package. The recorder uses `time.monotonic_ns()` (not wall clock) and `resource.getrusage` (Unix only; silently skipped on Windows).

#### Output files

| File | Format | Contents |
|---|---|---|
| `<strain>_timing_breakdown.json` | JSON | 13 fields (list below) |
| `<strain>_timing_breakdown.csv` | CSV | Flat phase table: name, elapsed_seconds, status, records_in, records_out, notes |
| `<strain>_timing_breakdown.md` | Markdown | Human-readable summary table; phase sum vs process total; overhead |

#### 16 canonical phase names (PHASE_* constants)
startup_dependency_probe, input_zip_inventory, antismash_kcb_riq_parse, bgc_region_inventory_parse, gbk_pfam_extract, source_scans_cctt_cgad_efls_resistance_tfbs, rggmci_reconstruction, scan_pack_and_triage, workbook_write, package_write, manifest_write, checksum_write, zip_seal, post_seal_receipt, brief_render, gene_by_gene_table.

#### `populate_from_receipts` (v9.7.87 backfill)
If no phases were recorded via the `.phase()` context manager (as happens in ChatGPT/non-instrumented runs), reads `run_phase_receipts.jsonl` and reconstructs phases from START receipt timestamps. Each phase's elapsed = gap from its START to the next phase's START. Skips synthetic terminal markers (MAMEY_COMPLETE, terminal). Returns 0 if no receipts found; never raises.

---

### 6. `validate.py` — Package Validation Gate

**Source:** `validate.py:validate_package`, `validate.py:REQUIRED_SUFFIXES`, `validate.py:ENRICHMENT_SUFFIXES`

#### `REQUIRED_SUFFIXES` (14 files — core gate)
manifest.json, checksums_sha256.txt, 1_intake.json, 2_inventory.csv, 3_scan_states.json, 4A_RGGMCI_full.json, 4A_RGGMCI_ranked_pairs.csv, 4A_RGGMCI_evidence.csv, 4_triage_board.csv, 5_workbook.xlsx, commit_receipt.json, issue_log.md, Project_Memory_Snapshot.json, 7_cell_provenance.csv

#### `ENRICHMENT_SUFFIXES` (2 files — post-seal check)
OPEN_ME_FIRST.html, manifest_short.json

The enrichment check runs after sealing (when `enrichment_check=True`). A missing enrichment file emits `[WARN]` but does not fail the package.

#### Status outcomes

| Status | Condition |
|---|---|
| `PASS` | All required files present + RG-GMCI gate passes |
| `FAIL` | Missing required files OR RG-GMCI gate fails OR gold completeness FAIL |
| `MAMEY_COMPLETE` | Gold mode: extraction complete, depth-floor assigned to all BGCs, but no Mode B cards yet |

#### RG-GMCI gate
Reads `4A_RGGMCI_full.json`; expects `status` in `{"PASS", "NULL_NO_RGGMCI_PAIRS"}`. Any other status → FAIL.

#### Gold completeness dimension (`gold_aware=True`, mode=="gold")
Reads `2_inventory.csv`, counts BGCs with `Depth_floor` assigned. If depth-floor assigned to all BGCs but no Mode B cards exist (`*mode_b*` filename pattern absent) → `MAMEY_COMPLETE` (extraction done; judgment pending). Three-way: all assigned + cards = PASS; not all assigned = FAIL; all assigned but no cards = MAMEY_COMPLETE.

---

### 7. `deep_data.py` — Gold Deep-Data Files

**Source:** `deep_data.py:build_deep_data_files`, `deep_data.py:modeb_verdict_rows`

**The gap it fills:** the gene-by-gene Mode B deep dive needs `deep_data.json` + `gene_data.json`. Both derive from the package's own `Project_Memory_Snapshot.json` + `AntiSMASH_Evidence_Parse.json`.

**`build_deep_data_files(package_dir, sid)`:** reads the two input JSONs via glob, calls `extract_profiles` + `extract_finer`, writes two files atomically:

| File | Contents |
|---|---|
| `deep_data.json` | `{bgc_profile: [...], domain_hits: [...], active_sites: [...], class_pred: [...]}` |
| `gene_data.json` | `{domain_arch: [...], substrates: [...], ripp: [...], tfbs: {}}` |

This resolves patch flag P3-F2: `cohort_figures.py` reads `gene_data.json`, which is written by `deep_data.build_deep_data_files()`. It is NOT the same as `gene_context.jsonl`. `gene_data.json` is written during gold-mode processing from the `Project_Memory_Snapshot.json` (the packaged in-run evidence snapshot), while `gene_context.jsonl` is written at extraction time from live GBK CDS features.

**`modeb_verdict_rows(strain, triage)`:** deterministic first-pass verdict scaffold — DROP (primary metabolism), DOWNGRADE (standing rule or mis-anchor), CONFIRM (no exclusion fired). These are scaffolds the Sapote layer refines; not the final call.

**`PROFILE_DOMAINS`:** NRPS_A, NRPS_C, NRPS_T_PCP, PKS_KS, PKS_AT, PKS_KR, PKS_DH, PKS_ER, TE_release, Transporter, Regulator, Oxidoreductase.  
**`TIER1_DOMAINS`:** PKS_KS, NRPS_A, NRPS_C, PKS_AT.

---

### 8. `cohort_resolver.py` — Cohort and Actinomycete Classification

**Source:** `cohort_resolver.py:resolve_cohort`, `cohort_resolver.py:actino_status`, `cohort_resolver.py:ACTINO_GENERA`

**`resolve_cohort(strain_id, organism)`:** Returns `{cohort, actino_status, resolved_sid, note}`. Cohort vocabulary: AS / SID / OTHER. SID strains deposited under WGS accessions (e.g. `WWGG00000000` with organism "Streptomyces sp. SID-XXX") resolve to SID via `_SID_RE` matching on the organism string. Non-actinomycetes fire a loud note.

**`actino_status(organism)`:** "actinomycete" / "non_actinomycete" / "unknown". "unknown" is a **review tag**, not a silent pass — it means the genus is absent from both allowlists and should be surfaced in the issue_log. `ACTINO_GENERA` covers 57 genera across Streptomycetales, Pseudonocardiaceae, Micromonosporaceae, Streptosporangiaceae, Nocardiaceae, and related families. `NON_ACTINO_GENERA` covers 35+ non-actinomycete genera including bee-associated endosymbionts (Melissococcus, Gilliamella, Snodgrassella), fungi, and kingdom-level tokens (fungi, eukaryota).

**`normalize_taxonomy(taxonomy)`:** Fixes the AS GBK `ORGANISM  .` artifact (no genus, just a dot). A taxonomy with no leading alphabetic character is normalized to "sp." so the literal "." never propagates into organism/display fields.

**`_AS_RE`:** `r'^(AS-?\d|AJS)'` — canonical AS-regex with optional hyphen. Aligned with `dedup_and_guard.AS_PATTERN`.

---

### 9. `cohort_cards.py` — Gap 1: Cohort-Scale Mode B Orchestrator

**Source:** `cohort_cards.py:run_cohort_cards`, `cohort_cards.py:inject_cross_strain`

Cards N strains in one pass by driving `mode_b_command` per strain and injecting the Gap-2 §X cross-strain context block from the cohort master. Output: `<sid>_Mode_B_cohort.md` per strain in the outdir.

**`inject_cross_strain`:** Splits the Mode B markdown on `"## Rank \d+:"` headers, appends a `§X. Cross-strain context` block after each BGC card (unless already present). Silently skips if the prevalence dict is empty (stale/empty master).

**Dependency:** a populated cohort master with `Cross_Strain_Class_Prevalence` recomputed (denominator invariant must hold). Stale master → cards generated without §X annotation, warning emitted. Never produces wrong cards; just un-annotated ones.

---

### 10. `cross_strain_card_context.py` — Gap 2: Per-BGC Cross-Strain Context

**Source:** `cross_strain_card_context.py:load_prevalence`, `cross_strain_card_context.py:card_context_block`

Reads `Cross_Strain_Class_Prevalence` from the cohort master and classifies each BGC's product classes:
- **COHORT-UBIQUITOUS** — `band == CORE` AND `informative_for_comparison == NO` → down-weight
- **COHORT-UNIQUE** — `n_strains == 1` → differentiating lead
- **COHORT-SHARED** — everything between → host-distribution context

`_UBIQUITOUS_FALLBACK` set: {other, saccharide, fatty_acid, terpene, NI-siderophore, NRP-metallophore, ectoine, melanin, NAPAA, terpene-precursor} — classes that are biosynthetically uninformative as differentiators even when not explicitly flagged.

Returns "" on stale/empty master (safe fallback). `registry_size()` reads N from `A2_Strain_Registry.max_row - 1` — the invariant denominator.

---

### 11. `cohort_synthesis.py` — Gap 3: Cross-Strain Synthesis Writer

**Source:** `cohort_synthesis.py:write_synthesis`, `cohort_synthesis.py:load_master`

**v9.7.118 — no-workbook path.** `cohort_synthesis.py:write_synthesis_from_capacity_csv` and `cohort_synthesis.py:load_from_capacity_csv` provide a `--capacity-csv` entry point that builds the cross-strain synthesis from a CCSM capacity-integration CSV when the private master workbook is unavailable. `--master` becomes optional (one of `--master` / `--capacity-csv` is required). The novelty-gradient section is omitted in this mode (it requires `B1_BGC_Master`).

Reads the verified cohort master and emits methods-paper cross-strain results prose: cohort composition, convergent capacities, host-biased classes, novelty gradient, differentiating leads, genus signatures. Capacity-level throughout; every number traces to a named sheet.

**Two novelty_basis definitions (do not conflate):**
- `fully_dark` — no MIBiG anchor at all: 164/1131 = **15%** on the 24-strain cohort
- `dark_or_unresolved` — no MIBiG accession in the KCB hit: 423/1131 = **37%**

Every novelty number is tagged with its basis. The `novelty_basis` parameter (default "fully_dark") selects the headline; the non-selected figure is still reported, explicitly labelled.

**Guard:** refuses to synthesize from a stale master (DAPR not populated, `Cross_Strain_Findings` not recomputed, denominator invariant broken) rather than emitting wrong prose.

**`_host_group(h)`:** Classifies host strings to: Bombus, Attine, Apis, Wasp, Moss, Other Apidae, Other.

---

### 12. `dedup_and_guard.py` — Release Guard and Fragment Ceiling

**Source:** `dedup_and_guard.py:resolve_release`, `dedup_and_guard.py:derive_release`, `dedup_and_guard.py:leak_audit`, `dedup_and_guard.py:fragment_claim_ceiling`

#### Release guard (v9.7.81 P2)

Three detection patterns: `AS_PATTERN` (`\bAS-?\d{2,4}\b`), `AJS_PATTERN` (`\bAJS-?\d{2,4}\b`), `PENDING_PATTERN` (`\bPENDING\b`). `PUBLIC_PATTERN` matches known-cleared public identifiers.

`derive_release(strain)` — fail-safe to PRIVATE: PUBLIC only if a known-cleared shape AND no private guard trips.

`resolve_release(strain, override)` — honors `--release` flag, but the **private-identifier guard is not operator-bypassable**: a PUBLIC override is refused if the strain trips the private guard. Since v9.7.236 (PI decision 2026-07-06) that guard keys on **AJS/PENDING/unrecognized** shapes only — the AS-series is PUBLIC by default, so an AS `--release PUBLIC` is honored (re-arm the AS guard with `AS_SCRUB=1` for a future private cohort). PRIVATE override is always honored.

`leak_audit(rows)` — scans every cell of PUBLIC-tagged rows for private-identifier patterns; returns a list of `"strain:BGC_ID::field=value"` strings. Called after any merge or export step.

#### Fragment claim-ceiling

`fragment_claim_ceiling(bgc)` — if a large-backbone compound (from `fragment_ceiling.LARGE_BACKBONE_KEYWORDS`, 38 entries) is named on a sub-45 kb fragment, caps the claim to "class_capacity_only". Returns `(downgraded: bool, ceiling: str, reason: str|None)`.

---

### 13. `merge_policy.py` — Source Supersedure Policy

**Source:** `merge_policy.py:choose_authoritative_source`, `merge_policy.py:dominates`

Three verdicts:
- **SUPERSEDE** — one source dominates (≥ on every signal axis, > on at least one); keep it, drop the rest
- **CONSULT** — no single source dominates (each is richer on some axis); surface the fork to the user — do not auto-pick
- **NOOP** — 0 or 1 source; nothing to de-dup

The motivating case: a single-strain deep run (21 Mode B cards, 635 domain evidence rows) vs a cohort run (zero Mode B, but tidier schema). Schema tidiness is never the tiebreaker that drops evidence.

`SUMMARY_ROW_SENTINEL = "__SUMMARY__"` and `is_summary_row()`: flags phantom `TOTAL`/`GRAND TOTAL` footer rows in merged Strain_Master tables so cohort-keyed parsers skip them.

---

### 14. `external_adapters.py` — Scan State Builder

**Source:** `external_adapters.py:run_external_scan_pack`

Converts a `SourceScanBundle` into the ten-scan state list for `manifest.json`. Scan state logic:

| State | Condition |
|---|---|
| DEFERRED | Scan status contains "PENDING" or "PLACEHOLDER" |
| PASS | ≥1 hit or ≥1 BGC coupled |
| NULL | No triggers |
| FAILED | Scan dict missing `status` key |

Special handling per scan: KCB reads from `antismash_evidence` (not SSB); FLBR grades from `flbr_grade` key; EFLS from candidate pair count; UMED from per-BGC verdict count; CGAD from chitin-binding-module hits; TTA from T4-tier count.

---

### 15. `compat_v941.py` — Forward-Compatible Output Fields

**Source:** `compat_v941.py:compatibility_fields_for_bgc`

Adds forward-compatible claim-calibration fields to workbook rows without changing regex backends or legacy scoring. Called from `_write_canonical_v1_views`. Key fields added:

- `cctt_triggers` on B1_BGC_Master — using the **full trigger name** from `CCTT_PATTERNS.keys()` (not the old 3-letter substring). Previous hand-typed subset silently dropped IDC/NUC/BLA/AMC/NN triggers.
- `efls_status` and `efls_claim_ceiling` — "edge/linkage candidate; flank evidence is source-derived; not a merged-cluster claim without long-read closure"
- `dkp_rank`, `dkp_cdps_evidence`, `dkp_oxidase_homology`, `dkp_provenance`, `dkp_claim_ceiling` — DKP scaffold BGC fields
- `diagnostic_signal_score` (DSS), `evidence_weight_tier`, `claim_confidence`, `claim_ceiling`, `safe_claim`
- `flank_census_tier1`, `flank_census_tier2_todo`, `cross_contig_candidate_set`

---

### 16. Supporting Utilities

**`_gbk_shim.py`** — Minimal stdlib GenBank parser replacing BioPython `SeqIO` for antiSMASH region GBKs. Used when BioPython is unavailable. Parses qualifiers, features (CDS, aSDomain, PFAM_domain, CDS_motif, module), and basic sequence records. Handles multi-line qualifier values and complement(join(...)) location syntax.

**`id_resolver.py`** — One-row-per-BGC identifier crosswalk table: BGC_ID, bgc_uid, contig/NODE, region, antiSMASH file, workbook_row. `bgc_uid` is authoritative from a workbook_map if supplied; otherwise a derived "(derived)" best-effort uid. Honest blanks for absent fields — never fabricated.

**`cnbu.py`** — Class-Normalized BGC Units. CNBU = `observed_length_kb / expected_complete_length_kb_for_class`, capped at a maximum. Summing CNBU across a strain gives a length-normalized capacity estimate less biased by many small (terpene) or large (transAT-PKS) clusters. `CLASS_PRIORS_KB` covers 30+ antiSMASH product classes from MIBiG representative lengths. Claims: "structural-length metric derived from assembly data and class reference priors; does not imply any compound is produced."

---

### 17. P5 Patch Flags

#### P5-F1 · `gene_data.json` write-path confirmed (resolves P3-F2)
**Confidence:** CONFIRMED  
`gene_data.json` is written by `deep_data.build_deep_data_files()`, which is called during gold-mode processing. It is NOT the same as `gene_context.jsonl`. `cohort_figures.py` line 40 reads it for domain_arch / substrates / ripp — this is correct; the file exists in gold packages. The P3-F2 flag is resolved: `gene_data.json` is a gold-mode artifact from the deep-data extraction step.

#### P5-F2 · `cohort_synthesis.py` novelty numbers: two incompatible definitions
**Confidence:** CONFIRMED — design choice, not a bug  
The 15% vs 37% novelty figures are both valid on the same dataset, computed from different definitions. Any downstream use of these numbers (manuscript prose, figures, tables) must tag which basis was used. The module enforces this internally; the risk is at the manuscript-writing layer where an undifferentiated "37% dark" could be reported against a figure legend that says "no KCB anchor."

#### P5-F3 · `actino_status` "unknown" is a review tag, not a pass
**Confidence:** CONFIRMED — documented behavior, not a bug  
Callers that use `actino_status() == "unknown"` as an implicit pass condition are wrong. The bldA/TTA scan v9.7.87 P-11 fix already handles this correctly (kingdom-only declarations like "Fungi sp." now return "non_actinomycete"). But any module that runs bldA analysis on an "unknown" genus and applies the actinomycete bldA T4 tier rule is over-calling. The rule "unknown → apply" should be "unknown → surface in issue_log for human review."

---

*Mamey engine v1.9.110 · Bundle v9.7.319*  
*All dataclass fields, function signatures, constants, and schema versions cited from source.*


**Field lists** for the wide rows above:

- **<strain>_timing_breakdown.json**: Full schema: strain_id, version, mode, chatgpt_safe, input_zip_bytes, raw/corrected BGCs, process block (start_utc, end_utc, elapsed_s, cpu_user_s, cpu_sys_s, peak_rss_kb), phases list.

## Mamey Engine Module Write-up: `parsers.py` and `_gbk_shim.py`

**Bundle:** Sapote–Mamey v9.7.319 · **Engine:** Mamey v1.9.110  
**Written:** 2026-06-23 · **Status:** Draft v1.0

---

### Overview

`mamey/parsers.py` is the engine's primary antiSMASH intake layer. Every downstream module that touches BGCs, CDS features, domain annotations, or assembly statistics gets its data from functions here. `mamey/_gbk_shim.py` is a biopython-free GenBank parser that sits beneath `parsers.py` as a fallback, making the engine portable across environments where the biopython wheel is unavailable or architecturally mismatched.

These two files are best understood together. `parsers.py` owns the public-facing parse API; `_gbk_shim.py` owns the fallback implementation that keeps the API alive when biopython is absent. Neither module makes biosynthetic judgments — that belongs to the Sapote layer. They translate raw antiSMASH ZIP output into the structured `BGCRecord`, `CDSFeature`, `DomainFeature`, and `AssemblyMetrics` objects that the rest of the engine consumes.

---

### `mamey/parsers.py`

#### Role and scope

`parsers.py` contains every function that reads bytes out of an antiSMASH output ZIP and converts them into first-class Python objects. Its responsibilities are:

- Enumerate and parse GenBank (`.gbk`/`.gbff`/`.gb`) files from the ZIP
- Extract FASTA contig sequences when available
- Parse the antiSMASH JSON for the version string (without loading the full document)
- Classify BGC boundary status (Interior / Edge / Full-contig) using absolute genomic coordinates
- Build `BGCRecord` objects with product annotations, protocluster breakdowns, KS domain counts, and architecture grades
- Extract CDS and domain feature inventories for the downstream source-derived scan modules
- Feed assembly metrics (genome size, N50, GC%) from FASTA or GBK sequences

The file has no network dependencies, no subprocess calls, and does not re-run antiSMASH — it is purely a parser and classifier operating on the archive.

#### Key constants

```python
FASTA_EXTS = (".fasta", ".fa", ".fna", ".ffn")
GBK_EXTS   = (".gbk", ".gbff", ".gb")
```

These are the only file extensions the parser examines within the ZIP. Every GBK-consuming function filters on `GBK_EXTS` at the `zf.namelist()` level.

---

#### `_require_seqio()` — lazy biopython import

```python
def _require_seqio():
    try:
        from Bio import SeqIO
        return SeqIO
    except ImportError:
        return None
```

Biopython is imported lazily and once. Every GBK-parsing function calls `_require_seqio()` at the top of its body to determine which parse path to take. Returning `None` rather than raising means that `python -m mamey validate`, `mamey doctor`, and all JSON/TXT-only utilities work in restricted environments without biopython installed. The error is deferred to the specific call that actually needs the parser, and only if the shim also fails — which in practice never happens for well-formed antiSMASH output.

The biopython wheel in the Sapote–Mamey offline dependency set is compiled for `manylinux2014_x86_64`. On non-x86_64 systems (the Claude.ai sandbox runs `aarch64`) the wheel refuses to install. This is a known, recurring, non-blocking issue — the shim fallback path runs the full engine correctly on all tested antiSMASH datasets.

---

#### `read_genbank_records()` — the primary parse gateway

```python
def read_genbank_records(zip_path, region_only=False, exclude_regions=False):
```

This is the single entry point for all GenBank reading in the engine. Every function that needs parsed GBK records calls this one; none of them open the ZIP directly. Its behavior is governed by three parameters:

**`region_only=True`** filters to files whose name contains `region` (e.g., `NODE_5.region003.gbk`). This is the mode used by `parse_bgcs_from_zip` — antiSMASH region GBKs are the primary BGC records.

**`exclude_regions=True`** is the complement, introduced in the v9.7.105 gene-context scoping fix. It filters to full-assembly GBKs only. Per-region GBKs carry region-local coordinates, so including them in a genome-wide CDS inventory duplicates every CDS at shifted frame positions and piles false low-coordinate copies onto the first region. Every region CDS is already present in the full-assembly GBK, so excluding region files loses nothing. The guard `if _full:` means the exclusion only applies when a full-assembly GBK actually exists — it doesn't silently drop everything on a region-only archive.

**Default (`region_only=False`, `exclude_regions=False`)** reads all GBK files, used by `assembly_metrics_from_zip` and the contig-length fallback.

The parse loop follows a resilience-first design. One malformed GBK must not abort the parse of the remaining N-1 files, so each file is processed inside a `try/except Exception` block. Failed files accumulate in `errored[]`. A separate check after parsing — `if len(records) == n_before` — catches the more insidious case: a GBK that parses without raising but yields zero records. These go into `empty[]`. Both lists are surfaced via `warnings.warn()` at the end of the function if either is non-empty, naming the affected files. The warning message always includes both the count and the filenames (up to 8, then `…`), so a downstream BGC-count mismatch is traceable to the parse layer rather than appearing as a mysterious inventory deficit.

The parse dispatch itself is two lines:

```python
if SeqIO is not None:
    # biopython path: SeqIO.parse(handle, "genbank")
else:
    from ._gbk_shim import parse_genbank_text
    # shim path: parse_genbank_text(text)
```

Both paths append `(filename, record)` tuples to the same `records` list. Everything downstream receives the same data structure regardless of which parser ran.

##### Known test brittleness: the `_BAD_GBK` fixture

The test `test_malformed_gbk_warns_but_keeps_good_records` in `test_parsers_failed_gbk_warning.py` fails in the shim environment (observed on v9.7.117, Claude.ai sandbox). The `_BAD_GBK` fixture was designed to force a biopython parse exception via a non-numeric LOCUS length and a `join(abc..xyz)` coordinate string. The shim's regex-based parser is more permissive — it extracts `NODE_2` as the record ID from the LOCUS line and produces a record with zero coordinates rather than raising. The resilience logic, the warning emission, and the `errored[]` branch are all correct; the fixture simply does not exercise the `errored` path under the shim. This is a **P2 test fixture issue**, not a production bug. The fix shipped in v9.7.118: the test is marked `xfail(strict=True)` when biopython is absent (`_require_seqio() is None`), documenting the shim's permissiveness while still failing loudly if the shim ever starts raising on the malformed GBK.

---

#### `_region_orig_bounds_from_zip()` and `_contig_length_map_from_zip()` — absolute coordinate recovery

antiSMASH region GBKs are clipped records: all feature coordinates restart from 1 at the region boundary, not from the absolute position on the source contig. The comment block of each region GBK contains the original bounds:

```
##antiSMASH-Data-START##
Orig. start :: 142053
Orig. end   :: 178901
##antiSMASH-Data-END##
```

`_region_orig_bounds_from_zip()` extracts these with two regex searches (`Orig\.\s*start\s*::\s*(\d+)` and `Orig\.\s*end\s*::\s*(\d+)`) across all region GBKs in the archive and returns a `dict[filename, (start, end)]`. When a region GBK is present in this map, `parse_bgcs_from_zip` substitutes the absolute coordinates for the local ones.

`_contig_length_map_from_zip()` builds the true per-contig length table, which is needed for Edge/Interior classification. It prefers FASTA sequences (exact nucleotide lengths) and falls back to full-assembly GBKs. Region GBKs are explicitly excluded from the fallback — they contain only the clipped window, not the full contig length.

Both are internal helpers. Neither is exported; they exist to support `parse_bgcs_from_zip` and are not part of the public surface.

---

#### `_edge_status()` — BGC boundary classification

```python
def _edge_status(start, end, contig_len, flank_bp=5000, is_circular=False) -> str:
```

Returns one of three values: `"Interior"`, `"Edge"`, or `"Full-contig"`.

**Full-contig** is assigned when the BGC span covers ≥95% of the contig. This is the most severe fragmentation category — the cluster likely extends beyond both ends of the contig and requires long-read assembly or linkage data before interpretation.

**Edge** is assigned when the BGC start or end falls within 5000 bp of a contig terminus. The default 5000 bp flank was chosen to match antiSMASH's own edge-detection heuristic and captures clusters that are clearly truncated without over-flagging those that simply happen to be near a boundary.

**The `is_circular` fix (v9.7.87):** on closed/circular replicons, the origin is not a truncation point. A BGC adjacent to position 0 on a circularized chromosome wraps around — it is complete, not truncated. Before this fix, such BGCs were classified as Edge and contributed to a deflated corrected BGC count (since Edge BGCs are counted as ½ in the `Interior + ½·Edge + ¼·Full-contig` formula). The topology token is read from the GenBank LOCUS line (`annotations["topology"] == "circular"`) and, when present, forces `is_circular=True`, bypassing the edge check entirely and returning `"Interior"`. Without this: closed genomes (e.g., *N. nova* NZ_CP006850) produced corrected counts lower than raw, a counter-intuitive signal that had been attributed to fragmentation until the real cause was identified.

---

#### `parse_bgcs_from_zip()` — the main BGC constructor

```python
def parse_bgcs_from_zip(zip_path, json_mode="off", evidence=None) -> list[BGCRecord]:
```

This is the workhorse function that most of the engine calls. It:

1. Reads region GBKs (falling back to all GBKs if no region GBKs exist — unusual but handled)
2. Recovers absolute coordinates from `_region_orig_bounds_from_zip()`
3. Reads true contig lengths from `_contig_length_map_from_zip()`
4. Iterates over records, deduplicating on `(contig, region_number, start, end, products)` to prevent double-counting when the same region appears in both region and full-assembly GBKs
5. Counts `single` cand_cluster features to flag composite regions (≥3 merged protoclusters produce an inflated product string and lead score)
6. Assigns an initial architecture grade A–E from `architecture_grade()`
7. Parses antiSMASH evidence (KCB, RiQ, domain annotations) via `parse_antismash_evidence()`, either from a pre-parsed dict passed in by the caller or parsed fresh here
8. **Reassigns** architecture grades after KCB evidence is applied, because KCB cumulative score can elevate a weakly-annotated Interior BGC from grade D to B

The evidence pre-parse option exists because the CLI parses antiSMASH evidence once for the status dict (which feeds the run-phase receipt system), and passing that parsed evidence avoids a redundant second full JSON parse on large antiSMASH outputs.

Notes appended to each `BGCRecord` preserve parse provenance: `source_gbk`, `absolute_coordinates_from_antismash_orig_start_end`, and `WARNING_region_gbk_lacks_orig_bounds_boundary_may_be_local` are written at construction time, not inferred post-hoc.

---

#### `extract_cds_features()` — genome-wide CDS inventory

```python
def extract_cds_features(zip_path) -> list[CDSFeature]:
```

Reads the full-assembly GBKs (via `read_genbank_records(..., region_only=False, exclude_regions=True)`) and extracts all CDS features. This is the data source for the CCTT trigger scan, CGAD chitin detection, TFBS/DasR profiling, resistance gene detection, bldA TTA-codon tiering, and UMED maturation-enzyme detection — the eight genome-wide first-pass scans.

The `exclude_regions=True` flag is critical here. Mixing region GBKs into the CDS inventory was the v9.7.105 gene-context scoping bug: region-local coordinates overlap zero, producing CDS records with coordinates far below their true genomic positions, which in turn caused the scoping logic to assign hundreds of CDS to the first BGC region. On closed genomes this manifested as 511 CDS assigned to one BGC versus the correct 18.

Compound/split locations (origin-spanning CDS on circular genomes) are handled by taking the longest `parts` segment as the representative coordinates, which avoids the naive `min..max` span that would bracket the full contig and falsely overlap every region.

---

#### `extract_domain_features()` — aSDomain and PFAM inventory

```python
def extract_domain_features(zip_path) -> list[DomainFeature]:
```

Reads all GBK files (not region-only) and extracts features of types `aSDomain`, `PFAM_domain`, `CDS_motif`, and `module`. These are the antiSMASH-assigned domain annotations — PKS_KS, C, A, T, E, Cy, TIGR hits, etc. — and are used by the FLBR megasynthase census, the PKS-KS domain count, and the enrichment analysis.

Bitscore and evalue are extracted with tolerant `_parse_float_maybe()` wrappers that handle commas, `None` inputs, and non-numeric strings without raising.

---

#### `architecture_grade()` — structural reliability assignment

```python
def architecture_grade(edge_status, products, length_bp, kcb_score=None) -> tuple[str, str]:
```

Assigns a letter grade A–E and a rationale string. This is a structural reliability grade, not a lead-priority score. A high-priority BGC can be grade C (Edge-truncated but coherently annotated); a low-priority BGC can be grade A (Interior, long, well-annotated but uninteresting product class).

The grade logic: Interior + coherent product + ≥10 kb → A. Interior + limited annotation or KCB-only support → B. Edge + coherent product → C. Edge + limited → D. Full-contig with product → D. Anything else → E. KCB can elevate an unannotated Interior BGC to grade B but cannot elevate an Edge or Full-contig BGC, which is intentional — KCB similarity does not compensate for physical truncation.

`architecture_grade` is called twice per BGC in `parse_bgcs_from_zip`: once before evidence parsing (initial grade using product strings only) and once after (final grade with `kcb_cumulative` available). The two-pass design ensures the final manifest always reflects KCB evidence.

---

#### `extract_antismash_version()` — bounded JSON read

antiSMASH JSONs can exceed 150 MB. Reading the full JSON to extract a version string is wasteful. `extract_antismash_version()` reads only the first 8 KB of each JSON file in the archive and regex-searches for `"version"` or `"antismash_version"` in that prefix. If the version key is in the header (it always is in standard antiSMASH output), this reads ~8 KB instead of 150 MB. The full-parse fallback is gated on `file_size <= 5 MB` and handles atypical JSON structures with a `metadata` sub-object.

---

### `mamey/_gbk_shim.py`

#### Role and motivation

`_gbk_shim.py` is a minimal, dependency-free GenBank parser written to replace biopython in environments where the biopython wheel is unavailable. It was introduced in engine v1.9.6 (2026-06-08) after the first cross-platform validation run established that Claude (no biopython) and ChatGPT (biopython) produced identical BGC outputs on 4 *Streptomyces* strains (240 BGCs), confirming that the shim was a viable production fallback rather than a temporary workaround.

The shim provides three dataclasses — `_Record`, `_Feature`, `_Location` — and one public function, `parse_genbank_text(text: str) -> list[_Record]`. The dataclass interfaces are designed to match the subset of the biopython SeqRecord API that `parsers.py` actually uses. Fields not accessed by `parsers.py` are not implemented.

---

#### Dataclass interface

**`_Location`**

```python
@dataclass
class _Location:
    start: int = 0    # 0-based (matches biopython)
    end: int = 0
    strand: int = 1   # 1 = forward, -1 = complement
```

The `extract(seq)` method implements forward and reverse-complement subsequence extraction. It is used by `extract_cds_features()` when pulling nucleotide sequences for TTA-codon counting.

**`_Feature`**

```python
@dataclass
class _Feature:
    type: str
    qualifiers: dict[str, list[str]]   # values are always lists, matching biopython
    location: _Location
```

`qualifiers` values are always `list[str]`, matching biopython's convention. Parsers.py accesses qualifiers uniformly as `(f.qualifiers.get("locus_tag") or [None])[0]` — this works on both biopython and shim records without branching.

**`_Record`**

```python
@dataclass
class _Record:
    id: str
    seq: str
    features: list[_Feature]
    annotations: dict    # added v9.7.104; required for topology access
```

The `annotations` dict was missing in the original shim, causing a crash (`AttributeError: '_Record' object has no attribute 'annotations'`) on the first real-data run that hit the circular-genome topology check in `parse_bgcs_from_zip`. The field is populated with `{"topology": "linear"|"circular"}` from the LOCUS line if the keyword is present, and left empty otherwise. `parsers.py` accesses it as `(rec.annotations or {}).get("topology", "")`, which handles both cases safely.

---

#### `parse_genbank_text()` — the parser

The parser splits the input text on `\n//\s*` (the GenBank record terminator) and processes each entry. An entry is skipped if it is empty or if `LOCUS` does not appear in the first 500 characters — this filters header noise and guarantees that every returned record has a LOCUS line.

**Record ID** is taken from the `VERSION` line if present, falling back to the `LOCUS` line identifier. The `VERSION` line carries the accession.version string (e.g., `CP006850.1`) which is what `parsers.py` expects as `rec.id`.

**Sequence** is extracted from the `ORIGIN` block by stripping everything that is not `[a-zA-Z]`. When the ORIGIN block is empty or absent (common in region-only archives that omit sequence data), the parser falls back to the LOCUS line's declared length and fills the sequence with `N * length`. This ensures `len(rec.seq)` is always a meaningful length for contig-length calculations, avoiding zero-length sequences that could cause division errors in assembly metrics.

**Features** are parsed by `_parse_features()`, which splits the FEATURES block on the five-space indent that precedes each feature type. Each block's first line is parsed for feature type and location string; subsequent lines are the qualifier block.

**Qualifier parsing** (`_parse_qualifiers()`) joins continuation lines (GenBank wraps long qualifier values at 80 characters) and extracts `/key="value"` pairs with a single `re.match`. Flag qualifiers (`/pseudo`, `/codon_start`) without values are captured and stored as empty-string list entries, matching biopython's behavior.

**Location parsing** extracts coordinates with `re.findall(r'(\d+)\.\.(\d+)', loc_str)`. For `complement(...)` locations, `strand = -1` is set and the pattern still extracts the inner coordinates correctly. For `join(...)` locations, all `start..end` pairs are found and the shim takes the outermost (`nums[0]` and `nums[-1]`), which approximates the full span. This is a known leniency delta from biopython, discussed below.

**Topology** is extracted from the first line of the entry (the LOCUS line) with `re.search(r'\b(linear|circular)\b', ...)`. The match is case-insensitive and anchored to word boundaries to avoid false matches on values like `circularRNA`. The result is stored in `annotations["topology"]`.

---

#### Known leniency delta from biopython

The shim is intentionally lenient in two respects:

**1. Malformed GBK tolerance.** The `_BAD_GBK` fixture in `test_parsers_failed_gbk_warning.py` — a record with a non-numeric LOCUS length and an `join(abc..xyz)` coordinate — is parsed successfully by the shim (producing a record with `id = "NODE_2"` and `seq = "N * 0"`) rather than raising. Biopython raises a `ValueError` on the non-numeric length. This is the root cause of the test failure on v9.7.117 (observed). In production this difference does not cause data loss: the shim correctly parses all well-formed antiSMASH output, and truly corrupted GBKs (zip-level read errors, truncation mid-file) still propagate as exceptions caught by `read_genbank_records`'s `try/except` block. But it means the `errored` warning path is not exercised under the shim, and the test fixture needs a fix for accurate coverage reporting.

**2. `join()` coordinate approximation.** When a CDS feature has a `join(1..500, 1000..1500)` location (split across an intron or contig origin on a circular genome), biopython builds a `CompoundLocation` with correct part-by-part handling. The shim takes `nums[0]` as start and `nums[-1]` as end, representing the full outer span rather than the parts. In `extract_cds_features()`, parsers.py already handles this at a higher level with its own compound-location logic (taking the longest part as representative), so the shim's approximation does not propagate into scan results.

---

#### Bug history

**v1.9.6 — missing `strand` attribute (critical, 2026-06-08)**

The original shim `_Location` dataclass had no `strand` field. `extract_cds_features()` accesses `f.location.strand` inside a `try/except` that swallows the `AttributeError` and `continue`s — which is correct resilience behavior for a genuinely bad feature, but here it silently skipped every single CDS record in the genome on the shim path. The downstream effect was that all eight source-derived scans (CCTT, CGAD, TFBS, DasR, resistance, bldA, UMED, EFLS) received empty CDS inventories and reported NULL across the board, while BGC parsing and RGGMCI — which do not touch `strand` — worked correctly. The mismatch between correctly-parsed BGCs and completely empty scan states was the diagnostic signal. The fix was one line: adding `strand: int = 1` to `_Location`. The `extract()` method for reverse-complement subsequence extraction was added at the same time.

**v9.7.104 — missing `annotations` dict (P0, 2026-06-xx)**

`_Record` was missing the `annotations` dict field. `parsers.py` accesses `(rec.annotations or {}).get("topology", "")` in `parse_bgcs_from_zip` for the circular-genome origin Edge fix. On any shim-path run touching a GBK with a topology annotation, this produced `AttributeError: '_Record' object has no attribute 'annotations'`. The crash was caught on AS-XXX real-data verification. Fix: added `annotations: dict = field(default_factory=dict)` to `_Record` and populated it from the LOCUS line.

**v9.7.104 — duplicate `annotations` line (P2, same version)**

The fix above was initially applied twice in the same commit, producing a duplicate `annotations` field definition in `_Record`. This was a linter-visible error caught in the v9.7.104 post-cut verification pass and removed.

---

#### Standing rule: shim fallback required for all GBK-touching tools

As of v9.7.56, any tool in `tools/` that imports `Bio.SeqIO` must also include a `_gbk_shim` fallback. This rule is enforced by the CI lint test `test_gbk_shim_lint_e2.py`, which scans all `tools/*.py` for bare `from Bio import SeqIO` imports without a `_gbk_shim` reference and fails the suite on violations. The rule was introduced after a propagation bug (v9.7.53–55) where three new tools (`topology_scan.py`, `gene_topology.py`, `cluster_alignment.py`) were shipped with bare Bio imports and crashed in every shim-path environment. The correct pattern:

```python
try:
    from Bio import SeqIO as _SeqIO
except ImportError:
    _SeqIO = None

if _SeqIO is not None:
    records = list(_SeqIO.parse(handle, "genbank"))
else:
    from mamey._gbk_shim import parse_genbank_text
    records = parse_genbank_text(text)
```

`mamey/parsers.py` itself uses the same pattern via `_require_seqio()`, and tools that import from `parsers.py` (rather than calling `Bio.SeqIO` directly) inherit the fallback automatically and do not need their own shim wiring.

---

### Data flow summary

```
antiSMASH output ZIP
        │
        ├─ extract_antismash_version()     → str (bounded 8 KB read)
        │
        ├─ read_fasta_sequences_from_zip() → dict[contig_id, seq]
        │
        ├─ read_genbank_records()          → list[(filename, Record)]
        │       │
        │       ├─ biopython SeqIO.parse()  (when available)
        │       └─ _gbk_shim.parse_genbank_text()  (fallback)
        │
        ├─ _region_orig_bounds_from_zip()  → dict[filename, (abs_start, abs_end)]
        ├─ _contig_length_map_from_zip()   → dict[contig_id, length_bp]
        │
        ├─ parse_bgcs_from_zip()           → list[BGCRecord]    ← main BGC output
        ├─ extract_cds_features()          → list[CDSFeature]   ← scan input
        ├─ extract_domain_features()       → list[DomainFeature]
        ├─ assembly_metrics_from_zip()     → AssemblyMetrics
        └─ extract_contig_sequences()      → dict[contig_id, seq]
```

All outputs from `parsers.py` are typed dataclasses defined in `mamey/models.py`. No raw strings or untyped dicts cross the module boundary into downstream callers.

---

### Open issues (as of v9.7.117)

**P2 — `_BAD_GBK` test fixture does not exercise `errored` path under shim.** The fixture relies on biopython raising on a malformed LOCUS line. The shim tolerates it. Fix: replace the fixture with a ZIP-level construct that causes `zf.open()` or `zf.read()` to raise (e.g., a CRC-corrupt member), which both biopython and shim paths would propagate to the `except Exception` block. Deferred to v9.7.117.

**P3 — `join()` location approximation not tested.** The shim takes the outermost `start..end` span for multi-part locations. There is no test asserting concordance between shim and biopython on a CDS with a genuine `join()` location. Low impact in practice (parsers.py independently handles compound locations in `extract_cds_features`), but a synthetic test would close the gap. Deferred.

---

## Assembly status

| Part | Subsystem | Status |
|---|---|---|
| 1 | CLI surface | folded, verified |
| 2 | Master workbook | folded, verified (B1 = 45 cols, corrected) |
| 3 | Figure subsystem | folded, verified |
| 4 | Packaging, sealing, output | folded, verified |
| 5 | Stores, telemetry, orchestration | folded, verified |
| 6 | Parse layer (parsers.py / _gbk_shim.py) | folded, verified |

*Sapote-Mamey: The Plumbing Reference · Mamey engine v1.9.110 · bundle v9.7.319 · 2026-06-23*
