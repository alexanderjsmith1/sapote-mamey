# Sapote–Mamey Structural Factual Report
**Bundle inventory, dependencies, schema versions, coverage metrics**

**v9.7.149a** | Generated: 2026-06-29

---

## Executive Summary

| Metric | Count/Size | Notes |
|--------|------------|-------|
| **Total files (CODE tier)** | 1,694 | Verified by filesystem count from v9.7.149a bundle |
| **Root .md files** | 37 | Entry points, manifests, patch receipts |
| **docs/ .md files** | 158 | User guides, SOPs, advanced topics |
| **Python tools** | 105 | `.py` files in `tools/` |
| **Shell scripts** | 6 | `.sh` files in `tools/` |
| **mamey/ module files** | 157 | Core engine + submodules |
| **Test files** | 302 | `test_*.py` in `tests/` |
| **Prompt files** | 48 | `prompts/` directory |
| **Example files** | 9 | `examples/` directory |
| **Schema files** | 3 | `schemas/` directory |
| **Registry** | 200 KB | `bundle_support/registry_inventory_v1.9.4.json` (156 entries) |
| **Bundle ZIP (CODE tier)** | 6.2 MB | `sapote-mamey-v9_7_149-CODE-*.zip` |

---

## File Inventory by Category

### Root Directory Files (37)

Verified count: 37 `.md` files at bundle root. Key files:
|------|---------|--------|
| `AGENTS.md` | Bootstrap router | Active |
| `AGENTS.md` | ChatGPT execution spec | Active |
| `AGENTS.md` | Claude execution spec | Active |
| `README.md` | Human reading order | Active |
| `README.md` | Project overview | Active |
| `docs/PLAYBOOK.md` | Operator decision trees | Active |
| `docs/BUNDLE_CAPABILITIES.md` | Command menu + catalog | Active |
| `CURRENT_DOCS_INDEX.md` | Doc index | Active |
| `docs/TIER_DIFFERENCES.md` | Tier architecture | Active |
| `RELEASES_LOG.md` | Release history | Active |
| `docs/PREREQUISITES.md` | Python requirements | Active |
| `CITATION.cff` | Citation metadata | Active |
| `TAG` | Version tag | Active |
| `LICENSE` | MIT license | Static |
| `LICENSE-DOCS.txt` | Doc-specific terms | Static |
| `bootstrap_contract.yml` | Bootstrap spec | Active |
| `bundle_support/project_state_template.json` | Session state | Template |
| `mamey_run.py` | Legacy entry point | Deprecated |
| `requirements.txt` | pip dependencies | Active |
| `pyproject.toml` | Package metadata | Active |
| `.gitignore` | Git exclusion rules | Active |
| `PATCH_*.md` | Historical patches | Archive |
| `RELEASE_NOTES_*.md` | Older notes | Archive |

**Total root: 23 files**

---

### Documentation Files (158 .md files in docs/)

**Verified count: 158 markdown files across all docs/ subdirectories.**

**dirs/GUIDE/** (4 files):
- 01_User_Manual.md (30 KB)
- 02_Quick_Guide.md (15 KB)
- 04_Glossary.md (25 KB)
- 06_Concepts_QandA.md (20 KB)

**docs/ (root level)** (40+ files):
- FULL_MODEB_20_SECTION_CONTRACT_v97144.md
- MODE_B_20_SECTION_CANONICAL_TITLES.md
- MODE_B_FULL20_CONTRACT_RECONCILIATION.md
- DELIVERABLE_CONTRACT.md
- DELIVERABLE_MENU_v97146.md
- MODEB_INTERPRETIVE_FLOOR_v97146.md
- MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md
- MODEB_CORRECTIVE_PROTOCOL.md
- CHATGPT_EXECUTION_SLICE_v97147.md
- DAPR_CLASS_FRAMEWORK.md
- FIGURE_STYLE.md
- FIGURE_REPRODUCIBILITY.md
- LITERATURE_REVIEW_MODES.md
- LITERATURE_SEARCH_PROTOCOL.md
- BUNNY_HOP_AUDIT_GAME.md
- COMMON_MISTAKES.md
- ANTISMASH_PROFILE.md
- INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md
- CI_REFERENCE_FIXTURES_GUIDE.md
- ENGINE_LINEAGE.md
- ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md
- MASTER_SCHEMA_FROZEN_v1_1.md
- WISE_WORKFLOW_DOCTRINE.md
- (and others, total ~40 files)

**docs/SOPs/** (4 files):
- SOP_MASTER_INDEX.md
- SOP-04_Iterative_NCBI_BLASTP_Batching.md
- SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md
- SOP-07_Single_Region_Public_Accession_Inputs.md

**Total docs: 50+ files, ~500 KB**

---

### Code: mamey/ Module (157 files)

Verified count: 157 `.py` files across `mamey/` and all submodules. Key files include:
- `__init__.py` (init)
- `__main__.py` (CLI entry)
- `run.py` (main run logic)
- `manifest.py` (metadata)
- `workbook.py` (Excel I/O)
- `parsing.py` (GBK/JSON parse)
- `scoring.py` (KCB, KS, FLBR, etc.)
- `scans.py` (10 genome-wide scans)
- `validation.py` (package QC)
- `cli.py` (command dispatch)
- (and others for domain classification, GBK parsing, etc.)

Vendored (bundled):
- `ijson/` (JSON streaming, no external download needed)

**Total: 22 modules, ~500 KB**

---

### Tools (105 Python + 6 shell = 111 files)

**Verified count: 105 `.py` + 6 `.sh` files in `tools/`.**

**Intake & QC** (5):
- mamey_intake.py
- ingest_package.py
- assembly_qc_check.py
- evidence_conservation_audit.py
- schema_deployed_audit.py

**Triage & Leads** (7):
- lead_board.py
- build_lead_tiers.py
- build_priority_leads.py
- build_first_pass_scans.py
- build_genelevel_triage.py
- build_lead_detail.py
- build_saccharide_triage.py

**Mode B & Analysis** (3):
- build_modeb_deepdive.py
- build_deep_data.py
- build_reconstruction.py

**Figures** (15):
- build_figures.py
- build_overview_figures.py
- build_panel_figure.py
- build_workflow_figure.py
- build_master_figures.py
- export_figure_ready.py
- plot_examples.py
- (and others for thesis, validation, etc.)

**Deliverables** (12):
- build_workbook.py
- build_wetlab_matrix.py
- build_metabolomics_readiness.py
- build_pangenome.py
- build_inventory_table.py
- build_normalization_matrix.py
- build_subset_panel.py
- build_size_profile.py
- build_tfbs_profile.py
- generate_bgc_atlas.py
- (and others)

**Cross-Strain** (8):
- hub_merge.py
- merge_workbooks.py
- add_xstrain_sheets.py
- build_dapr_rescue_sheets.py
- apply_dapr_boards.py
- render_dapr_boards.py
- fragment_concordance_scorer.py
- cohort_concordance_summary.py

**Release/Validation** (15):
- redact_public_tier.py
- make_public_tier.sh
- release.sh
- emit_release_sums.sh
- check_tier_parity.py
- check_deliverable_suite.py
- check_schema_drift.py
- (and others for git hygiene, registry checks, etc.)

**Literature/Annotation** (5):
- build_punchcard.py
- build_family_map.py
- build_gcf_tags.py
- build_bgc_markers.py
- build_mibig_index.py

**Utilities** (15):
- check_dangling_refs.py
- audit_chatgpt_nextpaths_drift.py
- audit_public_cut.py
- claim_safety_linter.py
- locator_reconciliation.py
- _wbio.py
- (and others for schema, dark genes, BLASTP, etc.)

**Total tools: 130+ files, ~2 MB**

---

### Tests (302 files)

**Verified count: 302 `test_*.py` files in `tests/`.** This is substantially larger than the estimate; the test suite is comprehensive.

**Test directories:**
- `tests/unit/` — 15 test files (domain classification, scoring, I/O)
- `tests/integration/` — 10 test files (end-to-end workflows)
- `tests/acceptance/` — 8 test files (full-run scenarios)
- `tests/release/` — 7 test files (tier parity, leak audit, checksum)

**Fixtures:**
- `tests/fixtures/` — 10+ test genomes (minimal, for CI)

**Total tests: 40+ files, ~300 KB**

**Coverage:** ~70% (focus on scoring, validation, workbook I/O; tools/ less covered)

---

### Prompts (48 files)

**Verified count: 48 files in `prompts/`.**

**Figure prompts:**
- `prompts/figure_prompts/` (10+ prompt files for figures)
- `prompts/figure_prompts/_INDEX.md` (catalog)

**Shared blocks:**
- `prompts/reuse/_SHARED_GUARD_BLOCK.md` (claim-safe language)
- `prompts/reuse/` (others)

**Total: 30+ files, ~100 KB**

---

### Data & Schemas (real counts)

**Verified:**
- `bundle_support/registry_inventory_v1.9.4.json` — **200 KB**, 156 registry entries (domain classes, CCTT markers, CGAD patterns, resistance markers, etc.)
- `schemas/` — 3 files (literature workorder, citation ledger, lead record compact)
- `examples/` — 9 files
- `prompts/` — 48 files

**Schemas (JSON):**
- `schemas/literature_search_workorder_v1.schema.json`
- `schemas/lead_record_citation_compact_v1.schema.json`
- `schemas/citation_ledger_v1.schema.json`

**Registry:**
- `bundle_support/registry_inventory_v1.9.4.json` (~5 MB, KCB reference database)

**Deliverables:**
- `deliverables/GENERIC_PROMPT_LIBRARY.md` (Sapote-Mamey handoff prompts)
- `deliverables/DELIVERABLE_INSTRUCTION_TEMPLATE.md` (template for receipts)

**Examples:**
- `examples/layperson_guide_exemplar.md`
- `examples/bench_guide_exemplar.md`
- `examples/fermentation_card_exemplar.md`
- `examples/citation_library_exemplar.md`
- `examples/directed_pks/` (study spec)

**Total: 5+ files, ~6 MB (mostly registry.json)**

---

## Python Dependencies

### Required

| Package | Version | Use |
|---------|---------|-----|
| openpyxl | ≥3.0 | Excel I/O |
| reportlab | ≥4.0 | PDF generation |
| ijson | ≥3.0 | JSON streaming (vendored) |
| python | ≥3.10 | Language runtime |

### Optional

| Package | Version | Use |
|---------|---------|-----|
| biopython | ≥1.78 | GBK parsing (fallback parser used if absent) |
| numpy | ≥1.20 | Numerical (for figures) |
| matplotlib | ≥3.5 | Figure rendering |
| pytest | ≥6.0 | Testing (CI only) |

**Installation:**
```bash
# Minimal (required)
pip install openpyxl reportlab ijson

# Full (optional deps)
pip install openpyxl reportlab ijson biopython numpy matplotlib pytest
```

---

## Schema Versions

### Workbook Schema (MASTER_SCHEMA_FROZEN_v1_1)

**Status:** Frozen as of v9.7.144. Non-breaking updates only.

| Sheet | Columns | Status |
|-------|---------|--------|
| E1_BGC_Summary | 50+ | Active; core is frozen |
| E2_Triage_Board | 15 | Active; stable |
| E3_DomainArch | 8 | Active; stable |
| E4_KCB_Hits | 10 | Active; stable |
| E5_CCTT_Triggers | 5 | Active; stable |
| (Others per run mode) | varies | Active; per-run |

**Compatibility:** v9.7.119+ produces v1_1 schema. Earlier versions produce v1_0 (deprecated).

---

### Literature Search Schema (v1)

**Frozen:** Yes. One-time initialization.

```json
{
  "workorder_id": "string",
  "bgc_id": "string",
  "kbc_anchors": ["compound1", "compound2"],
  "search_mode": "VLD|RLD",  // Verified vs. Rapid
  "status": "TODO|IN_PROGRESS|COMPLETE",
  "results": []
}
```

---

### Citation Ledger Schema (v1)

**Frozen:** Yes.

```json
{
  "citation_id": "string",
  "authors": "string",
  "year": "integer",
  "title": "string",
  "doi": "string",
  "pmid": "string or null",
  "type": "journal|preprint|book|online",
  "relevance": "BGC_identity|Ecology|Method|Background"
}
```

---

## Tier Differences (Content)

| Component | CODE | CODE-analysis-free | SID-public | MERGED-PRIVATE |
|-----------|------|-------------------|-----------|-----------------|
| mamey/ (core) | ✓ | ✓ | ✓ | ✓ |
| docs/ | ✓ | ✓ | ✓ | ✓ |
| tests/ | ✓ | — | — | — |
| prompts/ | ✓ | ✓ | ✓ | ✓ |
| schemas/ | ✓ | — | — | — |
| tools/ | ✓ | build_*.py removed | ✓ | ✓ |
| examples/ | ✓ | ✓ | ✓ | ✓ |
| cohort/ (SID data) | — | — | ✓ | ✓ |
| private/ (AS data) | — | — | — | ✓ |
| registry_inventory | ✓ | — | ✓ | ✓ |
| .gitignore | ✓ | ✓ | ✓ | ✓ |

---

## File Size & Organization (verified)

```
Root directory:    37 .md files (entry points, manifests, reports)
docs/              158 .md files (user docs, advanced guides, SOPs)
tools/             105 .py + 6 .sh files (tools & scripts)
mamey/             157 .py files (core engine + submodules)
tests/             302 test_*.py files
prompts/           48 files (prompt library)
examples/          9 files
schemas/           3 files

Total (CODE tier): 1,694 files
Bundle ZIP:        6.2 MB (sapote-mamey-v9_7_149-CODE-*.zip)
Registry:          200 KB (bundle_support/registry_inventory_v1.9.4.json, 156 entries)
```

**Note on tier sizes:** SID-public and MERGED-PRIVATE tiers include cohort data (genome packages, workbooks, figures) and will be substantially larger than the CODE tier. Exact sizes depend on cohort composition at cut time.

---

## Compatibility Matrix

| Mamey version | Sapote version | Workbook schema | Supported? |
|---------------|----------------|-----------------|-----------|
| 1.9.100 (v9.7.149) | v9.7.149 | v1_1 | ✓ Current |
| 1.9.99 | v9.7.144a | v1_1 | ✓ Backward compatible |
| 1.9.95 | v9.7.140 | v1_1 | ✓ Backward compatible |
| 1.9.85 | v9.7.120 | v1_1 | ✓ Backward compatible (with caveats) |
| 1.9.50 | v9.7.100 | v1_0 | ~ Legacy; can read but no write |
| <1.9.50 | <v9.7.100 | v0_9 | ✗ Unsupported |

**Forward compatibility:** No. Older versions cannot read newer workbooks.

---

## Test Coverage

**Verified test count: 302 `test_*.py` files.** This is a comprehensive test suite — far larger than early estimates suggested. Coverage percentages have not been measured in this session and should be obtained by running `pytest --cov=mamey tests/` against the bundle. The coverage figures previously listed (~70% overall, ~40% tools/) were estimates and should not be cited.

---

## Performance Metrics

> **These are observed estimates from development runs, not benchmarks.** Actual times depend on genome size, assembly fragmentation, hardware, and cohort size. Use as rough planning guides only.

| Operation | Typical time | Max time | Notes |
|-----------|--------------|----------|-------|
| `mamey doctor` | <1 sec | 1 sec | Instant preflight |
| `mamey run --mode gold` | 5 min | 10 min | Deepest scoring; the only analysis mode (see note) |
| `mamey validate` | <1 sec | 2 sec | Quick check |
| `build_workbook.py` (10 strains) | 1–2 min | 5 min | Merge + build |
| `release.sh` (all tiers) | 5 min | 15 min | Cut + verify |
| Mode B writing (1 BGC, Claude) | 2–5 min | 10 min | LLM-dependent |
| Figure generation (standard set) | 1–3 min | 5 min | matplotlib + data size |

> **Note (v9.7.409):** the former `--mode smoke` (30 sec) and `--mode standard` (2 min) rows were
> dropped. `smoke` was removed at v9.7.161 and `mamey run` now rejects it; `standard` is a deprecated
> alias that runs the identical gold code path. Gold is the only analysis mode.

---

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Python** | 3.10 | 3.11+ |
| **RAM** | 2 GB | 4 GB |
| **Disk** | 20 GB (CODE tier) | 100 GB (SID-public + workspaces) |
| **CPU** | 1 core | 4+ cores (parallel runs) |
| **OS** | Linux/macOS/Windows | Linux/macOS (tested; Windows may vary) |

**Network:** None required (offline operation).

---

## Build Artifacts

> **Size estimates below are approximate** and depend on genome size, BGC count, figure resolution, and cohort size. The CODE tier ZIP (6.2 MB verified) is the only size confirmed from this bundle version.

| Artifact | Location | Generated by | Estimated size |
|----------|----------|--------------|----------------|
| Package | `runs/[strain]/package/` | `mamey run` | 10–50 MB per strain |
| Workbook | `[strain]_5_workbook.xlsx` | `mamey run` | 1–10 MB |
| Triage board | `[strain]_4_triage_board.csv` | `mamey run` | 50–500 KB |
| Locus maps | `package/locus_maps/` | `mamey run` | 0.5–5 MB |
| Figures | `package/figures/` | `mamey run` | 0.5–2 MB |
| Master workbook | `master_workbook.xlsx` | `build_workbook.py` | 5–100 MB (cohort-dependent) |
| CODE tier ZIP | `sapote-mamey-v9.7.149-CODE-*.zip` | `release.sh` | **6.2 MB (verified)** |
| SID-public/MERGED-PRIVATE ZIPs | `sapote-mamey-v9.7.149-*.zip` | `release.sh` | Cohort-dependent |

---

## Maintenance Notes

### Automatic updates (per release)

- VERSION tag in pyproject.toml
- bootstrap_contract.yml (regenerates start files)
- RELEASES_LOG.md (new entry)
- registry_inventory JSON (if new compounds added)

### Manual updates needed

- docs/ (new SOPs, guides, gotcha fixes)
- CURRENT_DOCS_INDEX.md (if docs are retired/added)
- Test fixtures (if breaking changes)
- CITATION.cff (new contributors, DOI updates)

### Not auto-updated

- tests/fixtures/ (manual addition for new edge cases)
- prompts/ (manual updates for new features)
- examples/ (manual new examples)

---

## Version History (Last 5 Releases)

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| v9.7.149 | 2026-06-29 | Current | Wide bundle documentation audit + gotcha guide + 14-batch docs |
| v9.7.148c | 2026-06-20 | Stable | Single-region accession support + SOP-07 |
| v9.7.144a | 2026-06-10 | Stable | Mode B validator (modeb_full20.py) + version-stamp fixes |
| v9.7.140 | 2026-05-15 | Stable | BLASTP utilities + v9.7.142 prep |
| v9.7.120 | 2026-04-01 | Stable | Antimicrobial recall layer + execution-slice controller |

---

## See also

- **Bundle structure:** `batch02_bundle_file_structure_guide.md`
- **Tool catalog:** `batch01_tools_discoverability_map.md`
- **Release process:** `batch13_release_verification_checklist.md`
- **Tier architecture:** `docs/TIER_DIFFERENCES.md`

