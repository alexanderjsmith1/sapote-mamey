# Bundle capabilities — Sapote–Mamey
Reference menu of tools, modes, and deliverables. Begin with `AGENTS.md` for assistant operation; consult this catalog as needed. Engine: Mamey v1.9.163 · Bundle: sapote-mamey-v9.7.428.
**Before reporting any capability as unavailable, read `docs/COMPANION_FILES.md`** — Sapote–Mamey always travels with companion files (genome FASTAs, antiSMASH ZIPs, MIBiG references, an optional DIAMOND binary) that are attached separately in the chat, not packed in this zip. If one is missing, name it and ask the user to attach it; assume "forgot to attach" before "doesn't exist." (The optional alignment/add-on wheels are **not** packed in this zip — they ship separately and are installed via `bundle_support/install_sapote_addons.sh`; without them the add-on stack is unavailable, so name the installer and ask the user to attach the wheels rather than reporting the stack as broken.)
Current operating contract: `AGENTS.md`. The parent judgment workflow remains `docs/CHATGPT_EXECUTION_SLICE_v97147.md`; `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` (legacy only). Human landing page: `README.md`. Detailed workflows: `docs/WORKFLOW_GUIDE.md`, `docs/DELIVERABLE_CONTRACT.md`, and `docs/LLM_COMPANION_TOOL_PROTOCOL.md`.
**External companion tools:** `docs/LLM_COMPANION_TOOL_PROTOCOL.md` is the single LLM-facing
contract for BiG-SCAPE/GToTree/IQ-TREE preparation, resource approval, resume, exact-run QA, and
Claude↔Codex handoff. Read it before older cohort-specific guides or historical implementation notes.

> **Current compatibility notes:** `tools/bigscape_prep.py` requires an explicit `--strictness`;
> run `modeb-availability` before Mode B authoring; use `tools/find_asset.py` before fetching or
> recomputing data and `tools/register_compute_output.py` after compute; install optional guard
> hooks through the documented `sapote_hooks/` registry. Older version literals in historical
> sections describe provenance, not a second active workflow.

---

## 0 · Engine (Mamey) — deterministic extraction
Run first in capped ChatGPT/Claude sessions: `PYTHONPATH=<bundle> python3 -m mamey run --input-zip <antiSMASH.zip> --strain <ID> --taxonomy "..." --source "..." --mode gold --capped-session --json-evidence off --outdir <dir>`; Gold is the only analysis mode (smoke retired v9.7.161; `standard` is a deprecated alias of gold); re-run figures post-seal with `render-all-figures`.
Validate: `python3 -m mamey validate <pkg>/package`. Output = `manifest.json` (authoritative handoff) + coded CSVs + workbook. `--json-evidence bounded` enables the v9.7.7 region-mapped **RiQ** layer (streams large JSONs; RiQ exempt from the record cap).
Startup banner prints dep status (ijson / openpyxl / numpy+matplotlib / biopython) and `registry_detector✓` or `registry_detector—(fallback)` — the registry detector governs whether the CCTT/cassette scan uses the live registry or hardcoded fallback patterns (E1/C4).

## 0.5 · Quick-access subcommands (v9.7.83+)
Read-only inspection and judgment-persistence commands that operate on a sealed package without re-running extraction:
- `mamey doctor` — environment/dependency self-check; exit 0 when the bundle can run.
- `mamey inspect <antiSMASH.zip>` — one-screen preview of what Mamey sees in a **raw antiSMASH output ZIP** *before* running (positional; this is a pre-run preview, not a sealed-package reader — passing a sealed `*_Complete_Package.zip` errors with "doesn't look like an antiSMASH output ZIP"). Exit 1 on invalid input.
- `mamey explain <package_dir>` — narrative walkthrough of what a **sealed package directory** contains and what to do next (positional package directory).
- `mamey list-bgcs <package_dir> [--axis rank|ab|af] [--top N] [--json]` — BGC inventory from the triage board (positional package directory; `--axis` default `rank`). `--json` emits `bgc_id, contig, node_id, products, boundary, ab_score, af_score, novelty_auto, cctt_triggers, lead_tier, kcb_top, ...` (v9.7.85 added `novelty_auto` + `cctt_triggers`).
- **`mamey ingest-receipts --package <pkg> --receipt <mode_b_receipt.json> [--master <wb.xlsx>]`** (v9.7.85) — the Sapote→durable-store front door. A Sapote session ends a Mode B batch by writing one `mode_b_receipt.json` (`{strain_id, session_id, cards:[{bgc_id, mode_b_md, layperson_paragraph?, fermentation_note?}]}`); this command persists each card via the judgment store (writes the per-BGC `.md`, flips the register to COMPLETE) and, with `--master`, reconciles the workbook's `E1_Mode_B_Index` from the register. Fail-closed (unknown BGC skipped, never invented) and idempotent. **Use this so Mode B cards never live only in chat.**
- **`mamey ingest-receipts --package <pkg> --auto-detect`** (v9.7.149c, W4) — session-start recovery: scan `<pkg>/judgment/` for `*_mode_b.md` cards not yet in the register and ingest them. Use at session start before any other Mode B work to surface orphan cards from prior sessions.
- **`mamey ingest-receipts --package <pkg> --card <file.md>`** (v9.7.149c, N4) — one-card synchronous persist. Resolves BGC + session ID from the card's `<!-- MODE B: ... -->` header.
- **`mamey emit-modeb-template --package <pkg> --bgc <BGC_ID>`** *or* **`--batch [--scope all|top|leads|pending] [--top-n N]`** (v9.7.150+, W9) — emit a canonical §1–§30 Mode B template skeleton pre-filled with the BGC's facts from the triage board. **Use this to start every new Mode B card — it eliminates the wrong-scaffold authoring failure documented in `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md:521`.** Batch mode writes one card per BGC to `<pkg>/mode_b_templates/` plus an `_INDEX.md` work order — the per-strain batching workflow.
- **`mamey render-all-figures --package <pkg> [--all --workbook <wb.xlsx>]`** (v9.7.150e+, W9-Gap3) — post-seal aggregate over every applicable figure module: `smoke`, `brief` (the `_8a..._8m_fig_*.png` suite), `locus-maps`, `figure-suite` (lead boards), `domain-level`. With `--all --workbook` also runs `cohort-class` and `mamey-native`. **Use this after every `--capped-session` run** — the capped-session profile suppresses `--brief` and `--locus-maps` for wall-clock budget reasons, so the full figure suite never populates inside the capped session. `render-all-figures` populates it post-seal, non-blocking per module.

### Mode B canonical contract — read this before authoring any card (v9.7.150+, W9)

**Named profiles (v9.7.372 — never say the unqualified word 'full'):** `MODEB_SCAFFOLD` (evidence-routing artifact, never a card) · `MODEB_CANDIDATE_30` (the legacy conditional §1–§30 candidate contract described below) · **`FINISHED_FULL48_CURRENT_EVIDENCE`** (the Developer or User's finished deliverable: §§1–48 exactly once in order, complete channel-separated named-match gene matrix, 14-stream typed dispositions, source-loss table, appendices after §48) · `EXPERIMENTALLY_ADJUDICATED` (future; never implied). The legacy candidate contract is §1–§30: Specifically:

- §1–§20 are **always required**, in numeric order, with the exact titles in `docs/MODE_B_30_SECTION_CANONICAL_TITLES.md`.
- §28 (Evidence provenance ledger) and §30 (Experimental decision tree) are **always required** in addition to §1–§20.
- §21–§27 and §29 are **conditional** — required when the BGC matches the predicate (RiPP, MATURATION_GAP, novel-or-no-MIBiG, isolation-worthy, fermentation-selected, antimicrobial-candidate, or strain-has->3-high-priority-BGCs). The full predicate table is in `docs/CHATGPT_EXECUTION_SLICE_v97147.md` §9.

The single source of truth is `mamey/data/mode_b/modeb_full30_corrective_contract.json` (schema `modeb_corrective_full30_v1`). The validator (`mamey.modeb_structure_gate.lint_card`) reads this file; so does the template emitter (`mamey emit-modeb-template`); so does the ingest-receipts structure gate.

**Any earlier scaffold in your chat memory is historical and superseded.** In particular, the §1 Identity / §2 Assembly / §9 Activation / §10 Forensic sweep / §11–§20 enrichment pattern is the pre-v9.7.144 scaffold and must not be authored against. If you see it in your context, do not use it — start every card from `mamey emit-modeb-template` instead. Cards authored against the legacy scaffold are refused by the ingest-receipts structure gate (override: `--force-structure`).

**Status vocabulary (v9.7.83+):** run status is one of `MAMEY_COMPLETE`, `MAMEY_COMPLETE_WITH_ISSUES`, or `VALIDATION_FAIL`. Each package carries `OPEN_ME_FIRST.html` (entry point) and `run_phase_receipts.jsonl` (per-phase START/DONE receipts for auditing the run).


## 0.6 · Mandatory post-MAMEY_COMPLETE handback (v9.7.147)
When a package status is `MAMEY_COMPLETE` or `MAMEY_COMPLETE_WITH_ISSUES`, do not stop at status. Present code-backed outputs first:
- `OPEN_ME_FIRST.html`
- `manifest.json`
- `[StrainID]_8_strain_brief.pdf`
- `_8a…_8m_fig_*.png` plus companion `_data.csv` files
- every file in `locus_maps/`
- `[StrainID]_5_workbook.xlsx`
- `checksums_sha256.txt`
- `issue_log.md`

Then offer or auto-produce the full prompt-backed deliverable set from `docs/DELIVERABLE_CONTRACT.md`: Layperson Guide, Technical Full-Analysis Report, Bench Guide, Fermentation Card, Wet-Lab Matrix, Metabolomics Readiness, Ecological Synthesis, Reviewer Attack Simulation, and triggered Assembly QC / Contig Rescue / LMPKS Rescue. A handback without this block is incomplete.


## 1 · Analysis modes (ChatGPT execution slice — `docs/CHATGPT_EXECUTION_SLICE_v97147.md`)
- **MODULE 0/1** Intake · Assembly & fragmentation declaration (POOR/MODERATE tier, interior/edge/full-contig)
- **MODULE 12** Triage-first board (rank all BGCs; CCTT triggers, e.g. T43-HAL / T43-ENE)
- **Mode B** deep dives — the `MODEB_CANDIDATE_30` legacy profile (§1–§30; machine contract `modeb_corrective_full48_v1`, see §0.5 above; finished deliverables use `FINISHED_FULL48_CURRENT_EVIDENCE`); §1–§20 + §28 + §30 always required, §21–§27 / §29 conditional; all BGCs remain visible; POOR/VERY_POOR assemblies sort by score, not boundary status
- **MODULE 15/16** Missingness register · Output gates (completeness, RGGMCI)
- **MODULE 17** DAPR (antibacterial/antifungal boards)
- **MODULE 18** Fermentation (Ferm Card A5)
- **MODULE 19** Layperson-ranked BGC guide
- **MODULE 20** Compound detection & isolation bench guide
- **MODULE 21** Master multi-strain layperson compilation
- Literature depth: **Verified Literature Deep Dive** / **Rapid Literature Deep Dive** (`docs/LITERATURE_REVIEW_MODES.md`)
- **FULL ANALYSIS MODE** deliverable order: Lay Guide → Synopsis → (Hymenoptera Chapter) → KCB sweep → Mode B (BGC# order) → Ferm Card

## 1.5 · First-Pass Scans — run automatically, pre-triage (outputs already emitted)
The eight genome-wide scans run on every `mamey run` inside `run_source_scans` (no antiSMASH re-run — they
consume the cached parse). They are **computed and emitted**, not missing; surface them before triage/Mode B:
- **`B4_Cross_Strain_Scans`** (master workbook): `CCTT_*`, `CGAD_chitin`, `TFBS_DasR`/total, `bldA_T4`, `resistance_T1`, `UMED_gaps`, `EFLS_pairs`, RGGMCI pairs.
- **`F1_Ecology_Readiness`**: CGAD chitinase + TFBS + leads (the two-pronged anti-chitin ecology read).
- **Triage board** (`{strain}_4_triage_board.csv`): `CCTT_triggers`, `Primary_metab_flag`, `Standing_rule`, `Corrected_rank` per BGC.

The eight: KCB sweep · Hallucination-trap/claim-calibration · FLBR megasynthase census (KS/C/A/T/E + docking; Very-Poor demote) · UMED maturation-enzyme detection · CCTT trigger scan (registry-configurable bitscore floor (per-scanner min_bitscore, unset by default in v9.7.319); bonus ≤ +2, non-stacking) · CGAD chitin/GH18/LPMO · Resistance (APH/Van/Erm + HGT guard) · bldA/TTA tiering (T1–T4). For a cohesive v8.9.3-style First-Pass-Scans page, run **`tools/build_first_pass_scans.py --package <pkg_dir> --out first_pass_scans.md`** — it renders all eight from the package's `manifest.json` (`source_scans`), no re-scan.

## 2 · Tools catalog (`tools/`) — purpose per script
**Intake / QC / validation**
- `mamey_intake.py` — one-command intake for Mamey package outputs
- `ingest_package.py` — map a Mamey package into cohort banked-JSON
- `mamey_package_qa_v2.py` — per-strain package completeness validator
- `assembly_qc_check.py` — deterministic assembly-QC gate
- `evidence_conservation_audit.py` — finds "present in source, dropped in package" bugs
- `schema_deployed_audit.py` — reconcile coded sheets vs WORKBOOK_SCHEMA.md

**Triage / leads**
- `build_first_pass_scans.py` — render the eight genome-wide First-Pass Scans (KCB/hallucination-trap/FLBR/UMED/CCTT/CGAD/Resistance/bldA-TTA) into one pre-triage page from a package's `manifest.json` (no re-scan)
- `lead_board.py` — per-strain ranked Lead Board (single source of truth)
- `build_lead_tiers.py` — re-derive lead tiers (self-protection as 2nd axis)
- `build_priority_leads.py` — highest-confidence shortlist across evidence axes
- `build_genelevel_triage.py` — gene-level heavy pre-pass
- `build_saccharide_triage.py` — separate real saccharide products from glycosylation noise
- `build_lead_detail.py` — per-lead BGC detail extractor

**Mode B / deep analysis**
- `build_modeb_deepdive.py` — gene-by-gene Mode B deep dives
- `build_deep_data.py` — bank full per-BGC deep_data (core-only ingests)
- `build_finer_from_gbk.py` — recover finer sheets from region GBKs, offline
- `build_reconstruction.py` — clusterblast-scaffolded split-pathway reconstruction

**Literature**
- `build_punchcard.py` — **deterministic ChatGPT literature punch-card** (KCB anchors + gene markers → cite-required questions). Run on a package, answer in a web session, return to Sapote.

**Annotation**
- `build_gcf_tags.py` — map KCB anchor → curated GCF/product-family tag
- `build_bgc_markers.py` — bank per-BGC class-definitive markers

**Workbook / master / DAPR**
- `build_workbook.py` — canonical master-workbook orchestrator
- `add_xstrain_sheets.py` · `build_dapr_rescue_sheets.py` · `apply_dapr_boards.py` · `render_dapr_boards.py` · `build_chitinase_screen.py`

**Cohort / cross-strain**
- `build_pangenome.py` — pan-BGC-ome family structure & novelty
- `build_normalization_matrix.py` — fragmentation-robust class counts
- `build_subset_panel.py` — cross-cohort subset panel
- `build_size_profile.py` · `build_tfbs_profile.py` — per-strain BGC size / TFBS regulator profiles

**Wet-lab / metabolomics**
- `build_wetlab_matrix.py` — Wet-Lab Decision Matrix
- `build_metabolomics_readiness.py` — Metabolomics Readiness deliverable

**Figures / atlas / thesis**
- `generate_bgc_atlas.py` — browsable HTML BGC atlas (one strain)
- `build_figures.py` · `build_overview_figures.py` · `build_panel_figure.py` · `build_workflow_figure.py` (manuscript Fig 1)
- `build_causemap.py` · `build_thesis_diagrams.py` · `build_thesis_vignettes.py` · `build_validation_panel.py`
- `export_figure_ready.py` · `plot_examples.py` (tidy figure-ready CSVs → reference plots)

**Release / safety**
- `redact_public_tier.py` — SID-identifier redaction for public tiers
- `check_deliverable_suite.py` — **mechanical enforcement of the 13-item full-run deliverable contract** (reads a filled `DELIVERABLE_MANIFEST_<strain>.md`; fails closed on unfilled/under-justified items + JUDGMENT_PENDING gold gate). Emit the manifest as the last artifact of every full run.
- `sapote_judgment_receipt.py` — write-back that flips `gold_completeness` from asserted to verified; fails closed.
- `make_public_tier.sh` — cut the 4 tiers: CODE / CODE-analysis-free / SID-public / MERGED-PRIVATE (always present all four)


**Deliverable Menu:** `docs/DELIVERABLE_MENU_v97146.md` — the full ordered list of what the bundle can produce, with plain-language descriptions and trigger phrases. Present this to users at MAMEY_COMPLETE or on request.
## 3 · Deliverable types (what you can hand back)
Lay Guide · Deep Dive Synopsis · per-BGC Mode B (selected current named profile) · Triage board · Lead Board / priority shortlist · KCB sweep · **ChatGPT literature punch-card** · Ferm Card A5 · DAPR boards · Wet-Lab Decision Matrix · Metabolomics Readiness · BGC Atlas (HTML) · split-pathway reconstruction · cohort panels (pangenome / normalization / subset) · master multi-strain workbook + layperson compilation · manuscript figures.

## 4 · Handoff / prompts (`prompts/`)
`RUN_DIAGNOSIS_PROMPT.md` (give ChatGPT bundle+ZIP) · `MAMEY_CHATGPT_EXECUTION_PROMPT.md` (incl. `--master` chaining §10) · `CLAUDE_SYSTEM_PROMPT.md` · `SAPOTE_MAMEY_CO_EXECUTION_PROMPT.md` · `CHATGPT_TASK_BRIEF_TEMPLATE.md` · `FULL_RUN_PROFILE.md` · reuse prompts (`prompts/reuse/` — halogenation / polyketide / nucleoside / fragment-rescue / top-N-class). Handoff rules: `docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md`.

## 5 · Standing constraints (always apply)
Claim-safe "biosynthetic capacity consistent with" — never production/activity assertions · bioactivity metadata is optional, typed, and never locus-attributed without governed linkage · **NAPAA excluded** from comparative claims · **hglE-KS** habitat-non-specific · **BSL-2 consult before bulk fermentation**; T43-ENE enediyne trap is mandatory but fires only on a real enediyne domain · **affiliation: ** · SID is the primary strain label; **prefer strain names over NCBI accessions** (NZ_/GCA_/GCF_… accessions are a FALLBACK label only — when the label is an accession, flag it and use a supplied strain name if available) · **figures omit pure-saccharide regions** (figure_policy.py; interesting saccharide BGCs go in TEXT only).
- **Intake-first + batch (extraction layer).** On any multi-file set: inventory ALL zips → strains and announce the batch plan BEFORE running, then drive the set via `tools/intake_harness.py --inputs <dir> --resume` (timeout-safe, per-strain wall-time). Stall guard: Mamey never re-runs antiSMASH, so a multi-minute single-strain hang is an input/parse issue → checkpoint, continue, diagnose; do NOT loop one strain. (`docs/INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md`)
- **Small-N full deliverables (judgment layer).** The full per-strain deliverable suite is produced at ANY N≥1 — never refuse a deliverable (ecology included) for "too few strains" or "not qualified." Only cross-habitat comparative STATISTICS (CCSM/pangenome) are N-limited → qualify, don't refuse. Ecology is **source-independent**: grounded in the genome/BGC evidence, framed as general actinomycete antimicrobial/defensive capacity (claim-safe, `assumed`). Unknown isolation source never blocks interpretation; a known source is provenance only — never over-read into a functional/ecological claim.

## 6 · Document & file index (this manifest is the authoritative answer to "what's in the bundle")
**Bundle file inventory — regenerate, don't freeze a count.** The file count varies by tier (~1279 in the CODE tier) and drifts every cut, so no number is pinned here. List anytime: `find . -type f | grep -v __pycache__ | sort`.

**Glossaries — 3 dedicated files in-bundle:**
- `docs/GLOSSARY.md` — **master bundle glossary** (abbreviations, codes, terms across Mamey output / Sapote Layer-B reports / workbook). ~387 lines. The canonical in-bundle reference.
- `docs/troubleshooting/CELL_STATUS_CODE_GLOSSARY.md` — workbook cell-status code glossary (status-code → meaning → release handling).
- *Not in-bundle (external, staged for merge):* the ** Science Glossary** (~923 entries, 15-field science terms) and the accumulating **per-session glossaries** (e.g. `Sapote_Mamey_Session_Glossary_Chat3_v9.7.x.md`) — tracked outside the repo for later merge into `docs/GLOSSARY.md` and the Science Glossary.

**Canonical reference docs (ask-about-these):**
- Schema — `docs/WORKBOOK_SCHEMA.md`, `docs/MASTER_SCHEMA_FROZEN_v1_1.md`; workbook validator — `mamey/workbook_schema_check.py` (lives in `mamey/`, not `tools/`; run as `python -m mamey.workbook_schema_check [--fast|--full] [--v12] <workbook.xlsx>`)
- Process/contract — `docs/DELIVERABLE_CONTRACT.md`, `docs/WORKFLOW_GUIDE.md`, `docs/HOW_TO_USE.md`
- Judgment — `docs/CHATGPT_EXECUTION_SLICE_v97147.md` (default ChatGPT/Sapote execution controller), `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` (parent controller), `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` (legacy only)
- Literature/handoff — `docs/LITERATURE_SEARCH_PROTOCOL.md`, `docs/LITERATURE_REVIEW_MODES.md`, `docs/CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md`
- Release — `RELEASE_MANIFEST.md`, `CHANGELOG.md`, `docs/RELEASE_CHECKLIST_v9.md`, `docs/GITHUB_HYGIENE_CHECKLIST.md`
- Claim-safety — `docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`

**Directory map:** `mamey/` (engine + `_vendor/ijson`) · `tools/` (349 scripts, §2) · `prompts/` (+`reuse/`, §4) · `docs/` (reference, `modules/`, `troubleshooting/`, `standalone/`, `legacy/`) · `cohort/` · `offline_deps/` · `examples/` · `templates/` · `deliverables/` (+`reports/`).

## Session continuity

Use the shared contract in `AGENTS.md` for session state, scope, and handoff. The inventory below is generated by `tools/gen_tools_inventory.py`.

<!-- TOOLS_INVENTORY:START (generated by tools/gen_tools_inventory.py — do not edit) -->
### Tools inventory (349 scripts in `tools/`)
_Check here before building a new tool. Full table: `docs/TOOLS_INVENTORY.generated.md`._

- `_console.py` — the single owner of direct terminal emission for tools/ and deliverable_tools/.
- `_phylo16s.py` — Configured data roots, local database lookup and checked external tool execution.
- `_phylo_metadata.py` — Conservative display normalization for phylogeny metadata.
- `_safe_walk.py` — shared directory-walk helper that surfaces permission errors instead of
- `_tip_label.py` — Compatibility imports for the portable 16S tools.
- `_wbio.py` — Shared atomic workbook I/O for the secondary-sheet builders.
- `add_reference_source_labels.py` — Add deposited source text by exact versioned accession to new metadata.
- `add_xstrain_sheets.py` — Append or refresh the three deterministic cross-strain workbook sheets.
- `ani_caption_check.py` — Check that a caption/table names ANI versus AAI honestly and flags boundary values.
- `antismash_bigscape_join.py` — antismash_bigscape_join.py -- reconcile antiSMASH per-BGC output with BiG-SCAPE GCF famil…
- `apply_dapr_boards.py` — re-apply the Sapote-layer DAPR judgment boards (C1/C2) to a workbook.
- `archive_leak_scan.py` — private-ID leak guard for the *contents* of committed archives.
- `arts_ingest.py` — ARTS2 → per-BGC self-resistance signal (lead M7, validated against an admitted result fix…
- `assembly_qc_check.py` — deterministic assembly-QC gate (Mamey, runs before lead_board).
- `audit_blastp_zero_alignment.py` — find fabricated tested-negatives in BLASTp evidence.
- `audit_chatgpt_nextpaths_drift.py` — Audit high-risk ChatGPT/Mamey instruction surfaces for next-path drift.
- `audit_documents_wheelhouse.py` — Fail-closed preflight for the governed documents add-on wheelhouse.
- `audit_llm_companion_instructions.py` — Gate the LLM-facing BiG-SCAPE/GToTree instruction surface.
- `audit_modeb_support_card.py` — Audit a Mode B support card and, optionally, its task progress ledger.
- `audit_public_cut.py` — workbook-aware public-cut leak guard for merged-master Excel deliverables.
- `backfill_reference_signatures.py` — Backfill architecture_signature + refresh observed markers/genus into the reference libra…
- `bgc_alias_history.py` — which BGC id did this locus carry in the PRIOR run of the same strain?
- `bgc_deliverable_pdf.py` — bgc_deliverable_pdf.py -- assemble a per-BGC deliverable PDF (cover + facts + figures + M…
- `bgc_figures.py` — bgc_figures.py -- per-BGC figure set for Sapote-Mamey deliverables.
- `bgc_neighbor_layer.py` — build a SEPARATE labeled tree layer for shared-BGC / BLASTp-neighbor
- `bgc_reconcile.py` — pre-authoring cross-channel evidence reconciliation ledger.
- `bgc_reference_align.py` — bgc_reference_align.py -- align one BGC's proteins against characterized reference cluste…
- `bigscape_blastp_novelty.py` — Gene-level protein-homology context against a user-provisioned MIBiG GBK set.
- `bigscape_combined_run.py` — Sapote-Mamey BiG-SCAPE combined-run tool
- `bigscape_cross_strain.py` — Write a deterministic, qualified cross-strain BiG-SCAPE GCF table.
- `bigscape_family_domains.py` — bigscape_family_domains.py
- `bigscape_figure_labels.py` — bigscape_figure_labels.py -- canonical node-category labels/colours for BiG-SCAPE figures.
- `bigscape_ingest_to_mamey.py` — bigscape_ingest_to_mamey.py -- write BiG-SCAPE GCF context INTO the Mamey layer.
- `bigscape_known_novel.py` — Write qualified KNOWN/NOVEL GCF rows from one explicitly selected BiG-SCAPE run.
- `bigscape_merge_anchors.py` — Validate qualified anchor/base rows, then atomically classify base GCFs.
- `bigscape_mibig_anchors.py` — Emit qualified per-run, per-cutoff MIBiG anchoring edges.
- `bigscape_mibig_batches.py` — split the MIBiG reference set into small, prokaryote-filtered
- `bigscape_pipeline.py` — bigscape_pipeline.py -- one-command BiG-SCAPE GCF layer for a Mamey cohort.
- `bigscape_prep.py` — stage antiSMASH region GBKs into a BiG-SCAPE input dir.
- `bigslice_query.py` — bigslice_query.py -- BiG-SLiCE as a second, feature-based GCF opinion (complements BiG-SC…
- `bioassay_plate_map.py` — Map source-plate wells to destination wells with an explicit geometry profile.
- `bioassay_to_activity_channel.py` — emit MEASURED fraction-screen data as Sapote-Mamey
- `blastp_campaign.py` — headless, resumable, checkpoint-first NCBI BLASTp campaign runner.
- `blastp_channel_triage.py` — Command-line front door for the fail-closed BLASTp channel triage sidecar.
- `blastp_coverage_wave.py` — measure BLASTp coverage gaps, stage a priority wave into isolated
- `tools/blastp_monitoring/blastp_dashboard.sh` — one screen of GROUND TRUTH for the BLASTp crawl.
- `tools/blastp_monitoring/blastp_health.py` — GROUND-TRUTH health of the BLASTp crawl.
- `tools/blastp_monitoring/blastp_last_returns.py` — the ONE reliable answer to
- `tools/blastp_monitoring/blastp_stop_guard.sh` — Monitor unattended runs and stop the monitored process group on a real error.
- `tools/blastp_monitoring/plot_crawl_12h_15min.py` — the standing "is blastp still moving?" plot.
- `tools/blastp_monitoring/plot_crawl_cumulative.py` — CUMULATIVE query proteins retrieved over time,
- `tools/blastp_monitoring/plot_crawl_proteins_24_96h.py` — Plot BLASTp crawl cumulative throughput in ACTUAL PROTEINS QUERIED (not
- `tools/blastp_monitoring/plot_crawl_recent.py` — "what is landing RIGHT NOW", across ALL lanes.
- `tools/blastp_monitoring/plot_usable_6h.py` — USABLE data returned over the last 6 hours, all lanes.
- `build_all_deliverables.sh` — regenerate default Sapote–Mamey deliverables from the banked cohort,
- `build_bgc_markers.py` — (no docstring)
- `build_card_workbook.py` — cross-strain card workbook.
- `build_causemap.py` — chain-of-events / cause-effect diagrams (thesis-oriented).
- `build_chat_export.py` — build_chat_export.py  (candidate patch P09)
- `build_chitinase_screen.py` — add the Chitinase_Screen sheet to the master workbook.
- `build_cohort_html.py` — one self-contained HTML analysis across sealed Mamey packages.
- `build_cohort_precompute.py` — Part A: one cohort-wide table per fact-type (v9.7.224).
- `build_combined_bgc_report.py` — Build one portable combined V7 + Mode B BGC dossier.
- `build_cross_strain_figures.py` — CLI wrapper for mamey.cross_strain_figures.
- `build_dapr_rescue_sheets.py` — deterministic (Mamey-layer) regeneration of the schema-v1.2
- `build_deep_data.py` — (no docstring)
- `build_deliverable_menu_widget.py` — render the self-contained Deliverable Menu widget.
- `build_domain_explorer.py` — Read-only projection of the existing architecture owner; no biological scans.
- `build_domain_matrix.py` — cross-strain antiSMASH-HMM domain census (v9.7.221).
- `build_domain_reference.py` — emit a per-package domain functional-context dictionary (DOMREF-01).
- `build_domain_tree.py` — the ONLY sanctioned way to build a BGC-machinery domain tree (VGP-399).
- `build_enzyme_neighborhoods.py` — Explicit local view builder; pins the adjacent bundled package.
- `build_family_map.py` — lexicon growth)
- `build_figure_review_queue.py` — Build a portable, paginated owner-review queue from a Figure Factory manifest.
- `build_figures.py` — reproducible figure module for the Sapote-Mamey bundle.
- `build_finer_from_gbk.py` — recover 3 of the 4 finer sheets from antiSMASH region GBKs, offline.
- `build_first_pass_scans.py` — render the eight genome-wide First-Pass Scans into one cohesive
- `build_gcf_tags.py` — map each BGC's KCB anchor to a curated GCF / product-family tag (Sapote annotation layer).
- `build_genelevel_triage.py` — Mamey deterministic pre-pass that does the gene-level heavy
- `build_id_resolver.py` — emit the BGC ID-resolver table for a banked cohort.
- `build_inventory_table.py` — Improved BGC inventory deliverable: ONE document, two views of the same BGCs.
- `build_lead_detail.py` — per-lead BGC detail extractor for the Sapote judgment layer.
- `build_lead_tiers.py` — re-derive lead tiers with self-protection as an orthogonal second axis.
- `build_master.py` — frozen cohort one-off. NOT the canonical master-workbook builder.
- `build_master_figure_atlas.py` — DEPRECATED alias, retired v9.7.213-audit.
- `build_master_figures.py` — Build boss-ready master figure atlas from a Sapote–Mamey workbook.
- `build_metabolomics_readiness.py` — deterministic writer for the Metabolomics Readiness (MR) deliverable.
- `build_mibig_index.py` — auto-extract a provenance-tagged architecture-signature INDEX from a
- `build_mlsa.py` — 5-locus MLSA tree for a whole family's genome set, in one driver.
- `build_modeb_deepdive.py` — gene-by-gene Mode B deep dives (Sapote deliverable).
- `build_normalization_matrix.py` — fragmentation-robustness of BGC-class counts across a cohort.
- `build_novelty_shortlist.py` — composite (multi-signal) novelty shortlist (advisory report).
- `build_overview_figures.py` — two cohort-level overview figures for Sapote–Mamey.
- `build_owner_kept_figure_inputs.py` — Build current-data tables and readiness receipts for owner-kept figures.
- `build_panel_figure.py` — compose a labelled multi-panel figure from existing single-panel PNGs.
- `build_pangenome.py` — cohort-level BGC family structure and novelty (pan-BGC-ome).
- `build_pfam_desc_map.py` — extract Pfam NAME->{acc,desc} from a local Pfam-A.hmm into pfam_desc_map.json.
- `build_phylo_panel.py` — Build a bounded, provenance-rich genome panel for GToTree.
- `build_placement_ggtree_inputs.py` — the MISSING producer for tools/ggtree_placement.R.
- `build_priority_leads.py` — highest-confidence lead shortlist across independent evidence axes.
- `build_punchcard.py` — deterministic literature punch-card, generated IMMEDIATELY
- `build_reconstruction.py` — clusterblast-scaffolded split-pathway reconstruction.
- `build_saccharide_triage.py` — separate genuine saccharide products from glycosylation noise.
- `build_saved_scan_states.py` — Portable extraction of saved package scan context. Never execute a scan.
- `build_siderophore_atlas.py` — Bounded projection over pinned existing owner databases; never runs searches.
- `build_size_profile.py` — per-strain BGC nucleotide content by class (Mamey standard module).
- `build_subset_panel.py` — deterministic cross-cohort / cohort-subset panel (closes DLV-008; drives G2 & G6).
- `build_tfbs_profile.py` — per-strain transcription-factor binding-site (TFBS) regulator profile.
- `build_thesis_diagrams.py` — chain-of-events and cause-and-effect diagrams for the thesis chapter.
- `build_thesis_vignettes.py` — worked thesis vignettes for the Class-A leads.
- `build_tree.sh` — the ONLY sanctioned way to build a phylogenomic tree in this project.
- `build_validation_panel.py` — corrected-vs-raw percentile scatter for the external-validation panel.
- `build_wetlab_matrix.py` — deterministic writer for the Wet-Lab Decision Matrix (WLDM).
- `build_workbook.py` — canonical master-workbook build orchestrator.
- `build_workflow_figure.py` — Sapote-Mamey file-structure + data-flow diagram (manuscript Figure 1).
- `calibration_run.py` — Run the portable Sapote-Mamey detector calibration panel.
- `candidate_census.py` — file-count and debris census for a candidate cut tree.
- `check_antismash_profile.py` — cross-profile pooling guard.
- `check_bgc_naming.py` — portable enforcement of the AS-strain BGC node-naming rule.
- `check_chatgpt_next_paths.py` — Check ChatGPT handbacks for exactly 8 unique next paths.
- `check_command_pointers.py` — Phantom-command guard (patch 46).
- `check_dangling_refs.py` — list references to `examples/<file>` OR tool/module names that don't
- `check_deliverable_suite.py` — mechanical enforcement of the Sapote full-run deliverable contract.
- `check_duplicate_dict_keys.py` — fail closed on NEW duplicate dict-literal keys.
- `check_license_docs.py` — every file granted CC-BY-4.0 in LICENSE-DOCS.txt must actually ship.
- `check_manifest_contract.py` — Validate a Mamey package against schemas/manifest_contract.json.
- `check_md_links.py` — verify that local file links in Markdown actually resolve on disk.
- `check_module_accretion.py` — the module-accretion gate (Round 4 Item 6).
- `check_monolith_freshness.py` — the monolith is the parent design controller; keep its anchor honest.
- `check_no_brace_paths.py` — fail if any shipped path contains a '{' or '}' (W2).
- `check_onboarding_funnel.py` — One-door onboarding-funnel guard (CLAUDE_409_onboarding_funnel_guard).
- `check_patch_lane.py` — validate patch-lane STRUCTURE and DISPOSITION.
- `check_provenance_columns.py` — fail if a per-BGC table lacks its provenance anchor.
- `check_regex_interpolation.py` — fail closed on regex patterns that interpolate an
- `check_registry_ids_unique.py` — fail if registry inventory IDs collide.
- `check_release_manifest.py` — verify the bundle's integrity artifacts against the tree itself.
- `check_requirements_pyproject_sync.py` — freeze the requirements.txt <-> pyproject.toml core-dep drift.
- `check_schema_drift.py` — check_schema_drift.py  (candidate patch G1)
- `check_tier_parity.py` — fail-closed parity gate across the four release tiers.
- `chitin_reference_eval.py` — tools/chitin_reference_eval.py -- operator front door for the whole-genome chitin/GlcNAc
- `claim_safety_linter.py` — post-hoc claim-safety linter for Sapote interpretive text
- `cluster_alignment.py` — reference-aligned homolog figures for split-pathway BGCs.
- `cluster_brief.py` — one-command driver for the comparative chain → a consolidated brief.
- `cluster_completeness.py` — is a truncated cluster incomplete by assembly, or by biology?
- `cluster_discovery.py` — find strains carrying a BGC from a diagnostic marker gene.
- `cluster_gene_compare.py` — gene-by-gene comparison of biosynthetic gene clusters.
- `cluster_relate.py` — relationship tree + distance matrix from a set of homologous clusters.
- `cohort_blastp_driver.py` — drive BLASTp + overlay ingest across a scoped set of BGCs.
- `cohort_concordance_summary.py` — run the fragment-concordance scorer across a multi-strain ledger
- `cohort_figure_prototypes.py` — Standalone CLI for the extended cohort figure suite (see mamey/cohort_figures_extended.py…
- `cohort_next_evidence_actions.py` — Private, local next-evidence view. Existing registry reader owns SQLite access.
- `cohort_scoring_version_gate.py` — fail-closed: a comparative build may only aggregate strains
- `tools/cohort_tailoring/build_atlas.py` — Private local annotation view. No sequence search or scientific admission.
- `tools/cohort_tailoring/export_evidence_index.py` — Export one exact locus to the existing gene-first evidence-index schema.
- `tools/cohort_tailoring/test_atlas.py` — Generic annotation-view QC; fixtures contain no biological source records.
- `tools/cohort_tailoring/test_integration.py` — Tiny synthetic databases exercise real external readers without copying data.
- `collapse_near_identical.py` — Create a reproducible display derivative; never edit the analysis inputs.
- `collapse_query_groups.py` — collapse_query_groups.py <pruned.nwk> <annotation.tsv> <out_prefix>
- `comparator_discovery.py` — STEP 1 of discover -> download -> analyze (BB09 order).
- `comparator_select.py` — pick a phylogenomic comparator genome by the 16S method.
- `compilation_gate.py` — gate a strain compendium markdown/PDF before it can be called
- `compile_figure_owner_review.py` — Compile human figure decisions into a deterministic, non-rendering action plan.
- `cross_strain_denominator_audit.py` — fail-closed invariant on cohort-size denominators (v9.7.116).
- `cut_audit.py` — reproducible sealed-cut audit + card rebase-verify harness.
- `dark_gene_scan.py` — Dark-gene rescue scanner for edge/FC BGCs.
- `deliverable_citation_audit.py` — pre-delivery §15 citation + provenance gate for FINISHED deliverables.
- `determinism_fingerprint.py` — Run and compare the shipped deterministic-extraction control inventory.
- `domain_phylo_rescue.py` — advisory catalytic-domain-phylogeny corroboration for split-pathway rescue.
- `domain_prevalence.py` — cohort-wide domain-prevalence + host-filterable widget/figures (v9.7.413).
- `domain_prevalence_widget.py` — domain_prevalence_widget.py (v9.7.413): host filter + single-strain drill-down + evidence…
- `edge_fasta_export.py` — Export a FASTA of edge-proximal genes for directed BLASTp.
- `emit_release_sums.sh` — emit_release_sums.sh -- emit SHA256SUMS.txt over the cut tier zips at the release root (P…
- `encyclopedia_reground_check.py` — mechanize per-volume re-grounding of the Encyclopedia.
- `evidence_bundle.py` — per-BGC evidence bundle assembled from a SEALED Mamey package (P360-001 / Idea D).
- `evidence_conservation_audit.py` — finds the 'present in source, dropped in package' bug class.
- `evidence_disagreements.py` — Run the local evidence review view using this extracted bundle's package.
- `export_figure_ready.py` — emit tidy, figure-ready CSVs from a Sapote-Mamey master workbook.
- `export_tree_figure_source_package.py` — Export an editable, portable ggtree source package from one rendered tree folder.
- `extract_cluster.py` — locate and extract a BGC from a RAW genome by its marker genes.
- `extract_module_core_domains.py` — deterministic module-core aSDomain extractor (P358-003 Idea A.1).
- `fetch_mibig_reference.py` — turn a MIBiG accession into a reference GBK from the PUBLIC repo.
- `fetch_reference_cluster.py` — reconstruct a cluster GenBank from the BiG-SCAPE DB or NCBI.
- `figure_check.py` — HARD pre-render gate for tree FIGURES (the render inputs), sibling to
- `figure_factory_next.py` — Render receipt-bound aggregate evidence figures from an external data root.
- `figure_methods.py` — reusable, versioned METHODS-CAPTION library for Sapote-Mamey figure tools.
- `figure_readiness_board.py` — Report repair-spec binding and figure-receipt readiness states.
- `file_atlas.py` — describe every Python file in the bundle, from the source, with receipts.
- `finalize_public_archive.py` — Fail-closed, no-replace final archive transaction.
- `find_asset.py` — locate a big/shared local asset BEFORE downloading or re-deriving it.
- `fixture_inputs.py` — Content-preserving preparation of the one hash-bound synthetic test archive.
- `fragment_concordance_scorer.py` — score a strain's observed BGC fragments against the reference panel.
- `gate_mutation_probe.py` — Reproducibly answer whether a named test detects a minimal protection mutation.
- `gate_stem_aware.py` — Run the sibling tree gate, optionally on a verified display's analysis parent.
- `gen_command_catalog.py` — generate the task-oriented CLI command catalog (v9.7.405).
- `gen_cut_receipt.py` — generate a cut receipt's file-delta from a machine checksum-diff. Generic.
- `gen_figure_r_manifest.py` — derive FIGURE_R_MANIFEST.tsv from the Python figure sources.
- `gen_marker_catalog.py` — generate the marker/cassette catalog FROM the regex backend (W9).
- `gen_release_manifest.py` — regenerate the volatile fields of RELEASE_MANIFEST.md from live truth.
- `gen_tier_doc.py` — generate the tier/release explainer FROM the release-state record. Generic.
- `gen_tools_inventory.py` — list every tool, so nobody rebuilds one that exists (W22-adjacent).
- `gen_user_catalog.py` — generate the USER-FACING cassette + scan catalogs (v9.7.86 B4).
- `gene_assembly_line.py` — gene_assembly_line.py -- reliable PER-GENE NRPS/PKS assembly-line parser for antiSMASH re…
- `gene_modeb_enrichment.py` — gene_modeb_enrichment.py -- gene-level assembly-line block for a Mode B card, floors enfo…
- `gene_topology.py` — antiSMASH-style gene-arrow topology figures from antiSMASH region GBKs.
- `generate_bgc_atlas.py` — browsable HTML atlas of one strain's BGC inventory (deliverable G1).
- `generate_deliverables_menu.py` — Generate or verify the registry-backed Sapote-Mamey Diner Menu.
- `generated_surface_ownership.py` — fail-closed, check-only cut-surface planner.
- `graft_integrity.py` — Read-only metric checks and transactional gappa graft generation.
- `gtotree_env.sh` — canonical environment for a GToTree/IQ-TREE phylogenomic run.
- `harvest_16s.py` — assemble the 16S inputs for a per-genus EPA-ng placement, ALL FROM LOCAL DATA.
- `hub_merge.py` — one-shot hub merge: ingest → schema-gate → normalize → merge → verify.
- `ingest_blastp_rollups.py` — fold the per-strain DATED rollup CSVs into blastp.sqlite.
- `ingest_package.py` — map a Mamey package into the cohort banked-JSON entries.
- `ingest_swissprot_local.py` — fold the local SwissProt BLASTp CSVs into blastp.sqlite.
- `input_manifest.py` — the "no wrong / no half files" guard (portable, stdlib only).
- `intake_harness.py` — multi-strain intake for Sapote-Mamey with performance metrics.
- `kcb_confidence.py` — extract antiSMASH's per-region KnownClusterBlast "Similarity Confidence"
- `ks_burden_table.py` — Build a package-native KS-burden TSV and hash-bound receipt.
- `lab_office_render.py` — the Lab Office "make-report" entry point (batch figure rendering).
- `ladder_test.py` — Describe nearest-neighbor concordance across explicitly selected density rungs.
- `lead_board.py` — the per-strain ranked Lead Board (single source of truth).
- `lead_propagation_gate.py` — does every triage-board lead reach every lead-listing surface?
- `llm_trustworthiness.py` — "Is the LLM being trustworthy right now?"  (candidate module, v1 — F02 rework)
- `locator_reconciliation.py` — verify a Mode B card's header fields match the canonical
- `log_release.py` — append one row to RELEASES_LOG.md for the current build (idempotent).
- `make_public_tier.sh` — cut a clean release tier from the working tree, deterministically.
- `make_release_tarball.sh` — cut-time packaging artifact (v9.7.400, BC/Amber-fork proposal).
- `mamey_habitat_map.py` — build the strain->habitat map L5/L6 need, store-backed.
- `mamey_intake.py` — one-command intake for Mamey package outputs.
- `mamey_package_qa_v2.py` — Mamey per-strain package completeness validator
- `mamey_pipeline.py` — single-entry Lab Office pipeline (the "working program" cohesion piece).
- `marker_candidate_search.py` — find NCBI comparator genomes for an AS strain by
- `materialize_strain_data.py` — one-time staging tool for the canonical
- `md_to_docx.sh` — Word deliverable via pandoc (no LaTeX required).
- `md_to_pdf.sh` — md_to_pdf.sh IN.md OUT.pdf [boss|technical]
- `merge_workbooks.py` — merge_workbooks.py  (candidate patch M1)
- `mibig_neighborhoods.py` — cluster MIBiG reference domains of one family into "neighborhoods", pick one
- `mlsa_outgroup_scan.py` — build the same MLSA panel rooted on several candidate
- `modeb_card_diff.py` — Report current-package facts that would change a stored Mode B card.
- `modeb_card_guard.py` — the check that would have caught 2026-08-17.
- `modeb_evidence_gate.py` — deterministic Mode B evidence-governance gate (v9.7.354).
- `npatlas_provision.py` — tools/npatlas_provision.py -- operator front door for user-provisioned NP Atlas ingestion
- `nrps_substrate.py` — nrps_substrate.py -- predicted peptides + antibiotic-class signatures from A-domain subst…
- `outgroup_registry.py` — the "outgroup generator": genus -> a decided, reproducible outgroup.
- `panel_receipt_to_aux.py` — Export explicit query accessions from a panel receipt to a new auxiliary TSV.
- `panel_split.py` — Split a panel into reference and query FASTAs using its explicit tip-role table.
- `parked_card_audit.py` — flag patch-pool cards that silently fell out of the cut cadence.
- `patch_packet_preflight.py` — Fail closed when a patch packet contains workspace, cache, or evidence bloat.
- `patch_queue_composition_audit.py` — advisory pre-composition audit of a patch queue.
- `phylo_16s_audit_merges.py` — phylo 16s audit merges. External inputs remain outside the software bundle.
- `phylo_16s_build_db.py` — phylo 16s build db. External inputs remain outside the software bundle.
- `phylo_16s_esearch.py` — phylo 16s esearch. External inputs remain outside the software bundle.
- `phylo_16s_fetch.py` — phylo 16s fetch. External inputs remain outside the software bundle.
- `phylo_16s_from_genome.py` — Extract BLAST-supported candidate 16S spans with per-locus relative orientation.
- `phylo_16s_panel.py` — phylo 16s panel. External inputs remain outside the software bundle.
- `phylo_16s_rank.py` — phylo 16s rank. External inputs remain outside the software bundle.
- `phylo_autopilot.py` — one front door for "upload 16S and/or genomes -> gated trees".
- `phylo_neighborhood_catalog.py` — Split one EPA-ng placement run into reproducible species-neighborhood subruns.
- `phylo_outgroup_gate.py` — Evaluate outgroup and ingroup pairwise alignment identity with explicit missingness.
- `phylo_place.py` — reference-backbone phylogenetic PLACEMENT of query 16S (or protein) sequences.
- `phylo_postflight.py` — validate a FINISHED tree before it becomes a figure.
- `phylo_preflight.py` — validate a planned phylogenomic tree BEFORE spending CPU.
- `phylo_refset.py` — build a RIGHT-SIZED, DE-DUPLICATED 16S reference set for phylogenetic placement.
- `phylo_roster.py` — number the strains in a tree or panel, and edit them by number.
- `pks_product_class.py` — pks_product_class.py -- predict polyketide product class from per-module reductive loops.
- `placement_display.py` — Render a placement run in a new output directory, preserving every input tip.
- `placement_figure.py` — a paper-ready companion figure from a phylogenetic-placement grafted tree.
- `placement_to_docx.py` — assemble phylogenetic-placement figures + their methods captions into a Word doc.
- `plan_gtotree_iqtree.py` — Plan and inspect a bounded GToTree -> IQ-TREE workflow without running it.
- `plot_examples.py` — reference figures built ONLY from the figure_ready/ tidy CSVs.
- `preflight_zip_hygiene.py` — scan a built release ZIP for packaging-hygiene violations.
- `prepare_biosynthetic_tree_inputs.py` — Prepare provenance-rich PKS/RiPP sequence pools without running a tree.
- `preview_figure_components.py` — Write the static Figure Factory component gallery without network access.
- `preview_figure_themes.py` — CLI wrapper for the portable Sapote-Mamey figure-theme gallery prototype.
- `professionalism_linter.py` — post-hoc "professionalism" check for Sapote interpretive text
- `project_catalog.py` — Operate the portable, hash-bound project catalog without the UI.
- `prune_neighbors_from_tree.py` — pick each query strain's nearest reference
- `public_release_audit.py` — FAIL-CLOSED audit of a tree destined for the public GitHub release.
- `query_support_table.py` — query_support_table.py <placement_dir> <refpkg_dir> <out.tsv>
- `rank_clusterblast_phylo_candidates.py` — Rank ClusterBlast-derived candidate comparator assemblies for phylogenomics.
- `reaction_gap_board.py` — Build a private offline RG-GMCI review view using the retained semantic reader.
- `realistic_bgc_count.py` — distinct-loci BGC count (advisory report).
- `reclass_check.py` — antiSMASH label vs. diagnostic-domain discrepancy (lead L1).
- `redact_public_tier.py` — CAS-safe SID + AS strain-identifier redaction for PUBLIC bundle tiers.
- `reference_bgc_structural_validator.py` — Measure a curated, exact-bound reference-BGC panel with Mamey.
- `reference_panel_ledger.py` — characterize the detection panel by separating OBSERVED from COMPUTED.
- `refresh_figure_source_manifest.py` — Refresh hashes for files in one exported tree-figure source package.
- `regen_modeb_contract_docs.py` — regenerate Mode B contract docs from the JSON.
- `register_compute_output.py` — the formal "register after running" step for heavy compute.
- `relabel_and_render.py` — Relabel GToTree tip names from genome FASTA headers to a consistent
- `release.sh` — single fail-closed build entrypoint for a Sapote-Mamey release (v9.7.97).
- `release_cut.sh` — one-command, gate-enforced release cut.
- `remediate_phantom_locus.py` — find and excise fabricated locus citations from authored Mode B cards.
- `render_activity_lead_reports.py` — the Day-5-shaped activity-lead deliverable.
- `render_all.py` — Render a built GToTree/IQ-TREE tree with publication-ready tip labels.
- `render_bootstrap_contract.py` — Render/check assistant bootstrap docs from bootstrap_contract.yml.
- `render_clean_tree.py` — Shared clean renderer for the GToTree 138-SCG core-genome ML trees.
- `render_dapr_boards.py` — render the DAPR antibacterial/antifungal boards and the
- `render_deliverable_pdf.py` — Compatibility CLI for the package-scoped ``mamey.markdown_pdf`` renderer.
- `render_siderophore_atlas.py` — Render a pinned atlas snapshot into a standalone local evidence drawer.
- `render_three_channel_evidence_matrix.py` — Render the static three-channel evidence matrix from generic JSON or TSV.
- `repo_health.py` — one-command repo-health gate for the Sapote-Mamey bundle.
- `reroot_postflight_receipt.py` — Reroot a Newick tree on one exact tip and emit a deterministic postflight receipt.
- `rewrite_release_identity.py` — Rewrite cut-time bundle/build identity without platform-specific ``sed -i``.
- `rggmci_cohort_rollup.py` — cross-strain RG-GMCI ranked rollup + confidence tiering (v9.7.117).
- `round_ledger.py` — verify a Mode B card and append one audit row to the round ledger.
- `run_chatgpt_surrogate_gate.py` — Fast ChatGPT surrogate release gate for Sapote--Mamey.
- `run_comparator_antismash_ingest.py` — Run comparator antiSMASH/GBK ingest.
- `run_directed_pks_study.py` — Run Directed PKS Study Mode from a source CDS CSV and JSON spec.
- `run_efls_rewire.py` — Run EFLS Rewire from a Pre-Sapote Lite gene evidence table.
- `run_planned_tree.py` — Execute an APPROVED GToTree -> IQ-TREE -> sign-off -> (optional) fastANI phylogenomics ru…
- `sapote_judgment_receipt.py` — write-back artifact that makes gold_completeness verifiable.
- `sapote_md_preflight.py` — Preflight Markdown before PDF rendering.
- `sapote_workflow.py` — CLI shim for the mandatory Sapote workflow driver.
- `scan_cctt_class_compat.py` — cohort-wide CCTT-trigger vs product-class compatibility scan (N-05/A-04).
- `scan_marker_census.py` — Emit a line-addressable census of registry-backed and inline scan markers.
- `scan_prevalence.py` — cohort prevalence for mamey keyword-scan DBs (resistance/regulator/
- `scan_registry_parity.py` — Prove that registry-backed source scans match the literal fallback.
- `schema_deployed_audit.py` — reconcile the coded sheets in WORKBOOK_SCHEMA.md against what the
- `scope_cluster.py` — scope an over-merged antiSMASH region to its TRUE protocluster.
- `seal_sweep.py` — seal_sweep.py  (candidate patch F10)
- `seed_reference_library.py` — Seed mamey/data/reference_bgc_library.json from the validated reference set.
- `session_checklist.py` — Render a session-close checklist from a governed, portable durability root.
- `session_cost_audit.py` — where did a chat's tokens actually go?
- `signoff_check.py` — the "would a master's student sign off?" gate, mechanised.
- `strain_bigscape_report.py` — strain_bigscape_report.py -- per-strain BiG-SCAPE report as a standard Sapote-Mamey deliv…
- `strict_source_disclosure_audit.py` — COMPATIBILITY ENTRY POINT. Holds no policy.
- `suite_count_census.py` — Measure pytest collection separately from JUnit execution outcomes.
- `sync_version.py` — propagate the single source-of-truth version into restated files.
- `test_reaction_gap_board.py` — (no docstring)
- `tier_vocabulary.py` — the single owner of release-tier names, zip labels and aliases.
- `tip_label.py` — Figure-label compatibility API backed by the bundled source-aware parser.
- `topology_scan.py` — detect inverted (non-co-directional) BGC strand-block topology and
- `tracked_file_policy.py` — Single source of truth for the tier tracked-file policy (NC-001/002/003).
- `tree_bgc_overlay.py` — Hash-bound Figure Factory consumer for existing MLSA/GToTree IQ-TREE outputs.
- `tree_catalog.py` — Plan or render a declared catalog of phylogenetic display variants.
- `tree_heatmap_panel.py` — CLI front door for the tree-aligned heatmap panel (mamey.tree_heatmap_panel).
- `tree_overlay_figure.py` — ONE tree, MANY overlay matrices.
- `tree_sanity_check.py` — HARD pre-render gate. A tree must PASS this before it is rendered or shown.
- `tree_trust_audit.py` — Audit explicitly bound tree artifacts; results cover mechanical checks only.
- `validate_portfolio_config.py` — Validate and bind a portable multi-strain project configuration to its project_registry.py
- `validate_portfolio_registry.py` — Validate portable strain privacy and evidence registries without running Mamey.
- `validate_timing_receipt_parity.py` — compare timing phases to run_phase_receipts.jsonl.
- `verify_external_validation_receipt.py` — Verify a structured full-suite receipt before a release cut reuses external validation.
- `verify_release_identity.py` — fail-closed release identity + LLM bootstrap freshness gate.
- `verify_tier_derivation.py` — assert that a public tier is an exact redaction-view
- `workflow_status.py` — Workflow status: where each strain sits in the pipeline. Emits a stage-matrix CSV + an SV…
- `zip_hygiene_allowlist.py` — a checksum/path-bound allowlist for intentionally-large shipped files. Generic.
- `../bootstrap.sh` — set up the Sapote-Mamey runtime + test deps in one command (W18).
<!-- TOOLS_INVENTORY:END -->

- `docs/CALIBRATION_CORPUS_KNOWN_BGCS.md` — known-compound reference BGCs for Mode B calibration; not for unpublished AS-series analysis
- `docs/batches/` — plain-English distilled reference set (18 of a planned 28 documents; see `docs/batches/batch15_master_index.md` for the navigation index and a status note on which numbers are missing). Covers Mode B interpretive floor, DAPR scoring, RGGMCI split clusters, literature protocol, claim-safety field manual, BGC class reference, multi-strain comparative claims, common mistakes, deliverable contract, handoff protocols, onboarding, and engine lineage — all synthesized from existing bundle source docs into single-purpose quick references.
- `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md` — documented bugs and issues
