# Sapote–Mamey Doc Navigation Guide
**"I want to X... which doc should I read?"**

**v9.7.149a** | Last updated: 2026-06-29

---

## Quick lookup by task

### Installing & Getting Started

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Get running in 5 minutes | `batch03_new_user_5min_runbook.md` | 5 min | First-time users |
| Understand the overview | `README.md` | 10 min | Everyone |
| Human-friendly walkthrough | `README_START_HERE.md` | 15 min | Non-developers |
| Know exactly where to start | `CHATGPT_START_HERE.md` or `CLAUDE_START_HERE.md` | 10 min | LLM operators |
| Check dependencies | `PREREQUISITES.md` | 2 min | Developers |
| Understand the architecture | `batch02_bundle_file_structure_guide.md` | 15 min | Everyone |

---

### Extracting BGCs (Mamey Engine)

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Run Mamey on one strain | `batch03_new_user_5min_runbook.md` → Steps 1–4 | 5 min | First-time |
| Understand run modes (smoke/standard/gold) | `docs/GUIDE/02_Quick_Guide.md` or `README.md` (Quick Start section) | 5 min | Everyone |
| See a schematic walkthrough (SID8370 example) | `batch05_worked_example_sid8370.md` | 10 min | Everyone |
| Run multiple strains (batch) | `docs/INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md` | 10 min | Operators |
| Prepare antiSMASH input correctly | `docs/ANTISMASH_PROFILE.md` | 5 min | Input prep |
| Validate a package after Mamey | `SESSION_START_MANIFEST.md` § 0.6 (Post-MAMEY handback) | 3 min | Operators |
| Debug "VALIDATION_FAIL" or assembly issues | `batch04_gotcha_guide.md` § 2–3 | 10 min | Troubleshooting |
| Understand assembly tiers (GOOD/MODERATE/POOR/VERY_POOR) | `batch04_gotcha_guide.md` § 3.1 or `docs/GUIDE/04_Glossary.md` | 5 min | Everyone |

---

### Prioritizing & Triaging BGCs

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Understand the triage board (ranked list) | `batch05_worked_example_sid8370.md` § 3–4 | 5 min | Everyone |
| Know which BGCs to pick for Mode B | `SESSION_START_MANIFEST.md` § 1 (Analysis modes) | 5 min | Operators |
| Learn about CCTT triggers and special features | `docs/GUIDE/04_Glossary.md` (search "CCTT") | 3 min | Technical |
| Understand scoring: AB (antibacterial) vs AF (antifungal) | `docs/DAPR_CLASS_FRAMEWORK.md` | 10 min | Technical |
| See the first-pass scans (KCB, FLBR, UMED, etc.) | `docs/GUIDE/02_Quick_Guide.md` or `SESSION_START_MANIFEST.md` § 1.5 | 5 min | Everyone |
| Filter out saccharide false positives | `tools/build_saccharide_triage.py` (tool, not a doc) + `batch01_tools_discoverability_map.md` § Category 3 | 5 min | Technical |

---

### Writing Mode B Cards (Sapote Judgment Layer)

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Understand what Mode B is | `docs/GUIDE/02_Quick_Guide.md` | 5 min | Everyone |
| See the full Mode B output contract (§1–§20) | `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md` | 15 min | Mode B writers |
| Get guidance on section titles & reconciliation | `docs/MODE_B_20_SECTION_CANONICAL_TITLES.md` | 5 min | Technical |
| Understand compact (§1–§8) vs full (§1–§20) Mode B | `docs/MODE_B_FULL20_CONTRACT_RECONCILIATION.md` | 5 min | Technical |
| See a complete Mode B example | `batch05_worked_example_sid8370.md` § 8 | 10 min | Everyone |
| Avoid claim-safety mistakes (hallucination traps) | `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md` § Evidence & Traps | 5 min | Mode B writers |
| Learn the interpretive floor (minimum depth per class) | `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md` | 10 min | Technical |
| Fix an error in Mode B (hallucination detected) | `docs/MODEB_CORRECTIVE_PROTOCOL.md` | 5 min | Troubleshooting |
| Escalate a low-confidence Mode B → high confidence | `docs/MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md` | 10 min | Technical |
| Learn how to cite properly | `docs/GUIDE/06_Concepts_QandA.md` (search "citation") or `CHATGPT_START_HERE.md` § 1 (non-negotiable framing) | 5 min | Everyone |

---

### Using the Workbook & Data

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Understand workbook columns & schema | `docs/MASTER_SCHEMA_FROZEN_v1_1.md` | 15 min | Technical |
| Export data for figures | `SESSION_START_MANIFEST.md` § 2 (Tool: export_figure_ready.py) | 3 min | Figure makers |
| Merge multiple strains into a master workbook | `SESSION_START_MANIFEST.md` § 2 (Tool: hub_merge.py) | 5 min | Cohort builders |
| Find a specific BGC or field | `batch01_tools_discoverability_map.md` (search task-based flowchart) | 3 min | Everyone |
| Validate workbook schema after edits | `SESSION_START_MANIFEST.md` § 2 (Tool: schema_deployed_audit.py) | 3 min | Data QA |

---

### Making Figures

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Understand the figure system | `docs/FIGURE_STYLE.md` and `docs/FIGURE_REPRODUCIBILITY.md` | 10 min | Figure makers |
| See locus maps (gene topology) | `batch05_worked_example_sid8370.md` § 5 | 3 min | Everyone |
| Find available figures (catalog) | `FIGURES_START_HERE.md` (in bundle root) | 5 min | Everyone |
| Build a figure from data | `SESSION_START_MANIFEST.md` § 2 (Tool: build_figures.py) | 5 min | Technical |
| Make a multi-panel figure | `SESSION_START_MANIFEST.md` § 2 (Tool: build_panel_figure.py) | 5 min | Technical |
| Create an interactive HTML atlas | `SESSION_START_MANIFEST.md` § 2 (Tool: generate_bgc_atlas.py) | 5 min | Technical |

---

### Delivering Results (Deliverables)

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Know what to produce (the contract) | `docs/DELIVERABLE_CONTRACT.md` | 10 min | Everyone |
| See a menu of options (pick-and-choose) | `docs/DELIVERABLE_MENU_v97146.md` | 5 min | Everyone |
| Write a Layperson Guide | `examples/layperson_guide_exemplar.md` (worked example) | 15 min | Writers |
| Write a Wet-Lab Decision Matrix | `SESSION_START_MANIFEST.md` § 2 (Tool: build_wetlab_matrix.py) | 5 min | Operators |
| Write a Fermentation Card | `examples/fermentation_card_exemplar.md` | 10 min | Lab-focused |
| Understand PDF formatting rules | `docs/PDF_OUTPUT_CONTRACT_v97144.md` | 5 min | Technical |
| Check deliverable completion | `SESSION_START_MANIFEST.md` § 2 (Tool: check_deliverable_suite.py) | 3 min | QA |

---

### Managing Multi-Strain Cohorts

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Merge multiple strains' workbooks | `SESSION_START_MANIFEST.md` § 2 (Tool: hub_merge.py) or `batch01_tools_discoverability_map.md` § Cross-Strain | 5 min | Technical |
| Handle fragmentation across strains | `batch04_gotcha_guide.md` § 3.2 or `SESSION_START_MANIFEST.md` § 2 (Tool: build_normalization_matrix.py) | 10 min | Comparative |
| Compare BGCs across strains (pan-genome) | `SESSION_START_MANIFEST.md` § 2 (Tool: build_pangenome.py) | 5 min | Comparative |
| Do cross-strain figures | `SESSION_START_MANIFEST.md` § 2 (Tool: build_cross_strain_figures.py) | 5 min | Figures |

---

### Publishing & Release

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Understand the four tiers (CODE, CODE-analysis-free, SID-public, MERGED-PRIVATE) | `batch02_bundle_file_structure_guide.md` § Four-Tier Architecture | 10 min | Release managers |
| Understand tier differences | `TIER_DIFFERENCES.md` | 10 min | Release managers |
| Cut a release | `SESSION_START_MANIFEST.md` § 3 (Tool: release.sh) | 5 min | Operators |
| Make a public tier (anonymize AS strains) | `SESSION_START_MANIFEST.md` § 2 (Tool: redact_public_tier.py) | 5 min | Release QA |
| Verify tier parity | `SESSION_START_MANIFEST.md` § 2 (Tool: check_tier_parity.py) | 3 min | QA |
| Verify SHA256 checksums | `SESSION_START_MANIFEST.md` § 2 (Tool: emit_release_sums.sh) | 3 min | QA |
| Check for data leaks before public release | `SESSION_START_MANIFEST.md` § 2 (Tool: audit_public_cut.py) | 3 min | Release QA |

---

### Literature & Annotation

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Plan a literature review | `docs/LITERATURE_SEARCH_PROTOCOL.md` | 10 min | Literature |
| Understand Verified vs. Rapid Deep Dive modes | `docs/LITERATURE_REVIEW_MODES.md` | 5 min | Literature |
| Use BLASTP to validate or extend KCB hits | `docs/SOPs/SOP-04_Iterative_NCBI_BLASTP_Batching.md` | 15 min | BLASTP |
| Parse BLASTP results and reprioritize | `docs/SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md` | 10 min | BLASTP |

---

### Troubleshooting

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Quick gotcha lookup (by error message) | `batch04_gotcha_guide.md` § 11 (Error Message → Gotcha lookup table) | 1 min | Troubleshooting |
| Know common mistakes | `docs/COMMON_MISTAKES.md` | 10 min | Everyone |
| Understand known issues from development | `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md` | 15 min | Technical |
| Debug a failing Mamey run | `batch04_gotcha_guide.md` § 1–2 | 10 min | Troubleshooting |
| Debug a timeout in ChatGPT/Claude | `batch04_gotcha_guide.md` § 4 | 5 min | Troubleshooting |
| Fix a Mode B error (hallucination, wrong ID, etc.) | `batch04_gotcha_guide.md` § 6 | 10 min | Troubleshooting |
| Decode assembly-tier warnings | `batch04_gotcha_guide.md` § 3 | 5 min | Troubleshooting |
| Check operator next steps | `PLAYBOOK.md` | 10 min | Decision-making |

---

### Reference & Concepts

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Define technical terms | `docs/GUIDE/04_Glossary.md` | 5 min (per lookup) | Everyone |
| Understand concepts in plain English | `docs/GUIDE/06_Concepts_QandA.md` | 15 min | Everyone |
| Know the command menu | `SESSION_START_MANIFEST.md` | 20 min | Operators |
| Understand the tools & which one to use | `batch01_tools_discoverability_map.md` | 15 min | Technical |
| See the file structure | `batch02_bundle_file_structure_guide.md` | 15 min | Everyone |

---

### Administration & Maintenance

| I want to... | Read this | Time | Audience |
|--------------|-----------|------|----------|
| Understand CI/test fixtures | `docs/CI_REFERENCE_FIXTURES_GUIDE.md` | 10 min | Developers |
| Check GitHub hygiene | `docs/GITHUB_HYGIENE_CHECKLIST.md` | 5 min | Release |
| Maintain bootstrap surfaces | `SESSION_START_MANIFEST.md` § 2 (Tool: render_bootstrap_contract.py) | 5 min | Maintenance |
| Regenerate the tools inventory | `SESSION_START_MANIFEST.md` § 2 (Tool: gen_tools_inventory.py) | 3 min | Maintenance |

---

## Quick reference by document name

| Document | Purpose | Read if... |
|----------|---------|-----------|
| `README.md` | Project overview + quick start | You want the essentials |
| `README_START_HERE.md` | Human-friendly walkthrough | You prefer guided narrative |
| `CHATGPT_START_HERE.md` | ChatGPT execution contract | Running in ChatGPT |
| `CLAUDE_START_HERE.md` | Claude execution contract | Running in Claude |
| `PLAYBOOK.md` | Operator decision trees | You need to decide what to do next |
| `SESSION_START_MANIFEST.md` | Command menu + tool catalog | You've started and need options |
| `CURRENT_DOCS_INDEX.md` | Which docs are active vs. historical | You want to know which docs to trust |
| `batch01_tools_discoverability_map.md` | 100+ tools organized by function | You need to find a tool |
| `batch02_bundle_file_structure_guide.md` | File guide + four-tier explanation | You want to understand the bundle structure |
| `batch03_new_user_5min_runbook.md` | Fastest path to first result | You have 5 minutes |
| `batch04_gotcha_guide.md` | Known issues + fixes | Something broke; search here first |
| `batch05_worked_example_sid8370.md` | Schematic walkthrough (SID8370); workflow steps and Mode B structure are accurate; specific scores are illustrative | You want to see how the workflow looks end-to-end |
| `batch06_doc_navigation_guide.md` | This file; "which doc?" lookup | You're here now |
| `docs/GUIDE/01_User_Manual.md` | Complete reference | You want exhaustive documentation |
| `docs/GUIDE/02_Quick_Guide.md` | Fast reference (not step-by-step) | You want key facts only |
| `docs/GUIDE/04_Glossary.md` | 78-entry term reference | You need a definition |
| `docs/GUIDE/06_Concepts_QandA.md` | FAQ + plain-language explainers | You're confused about a concept |
| `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md` | §1–§20 output contract | Writing Mode B |
| `docs/DELIVERABLE_CONTRACT.md` | 13-item deliverable spec | Planning output |
| `docs/FIGURE_STYLE.md` | Figure design rules | Making figures |
| `docs/BUNNY_HOP_AUDIT_GAME.md` | Code audit protocol | Reviewing code collaboratively |

---

## By audience

### **First-time user (just started)**
1. `batch03_new_user_5min_runbook.md` (5 min)
2. `README_START_HERE.md` (15 min)
3. `docs/GUIDE/06_Concepts_QandA.md` (if confused about a term)

### **LLM operator (ChatGPT/Claude)**
1. `CHATGPT_START_HERE.md` or `CLAUDE_START_HERE.md` (read once, bookmark)
2. `docs/CHATGPT_EXECUTION_SLICE_v97147.md` (mode B guidance)
3. `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md` (output spec)
4. `batch04_gotcha_guide.md` (when stuck)

### **Developer / Tool builder**
1. `README.md` (overview)
2. `batch02_bundle_file_structure_guide.md` (file layout)
3. `SESSION_START_MANIFEST.md` § 2 (tools catalog)
4. `docs/MASTER_SCHEMA_FROZEN_v1_1.md` (data schema)
5. `docs/CI_REFERENCE_FIXTURES_GUIDE.md` (testing)

### **Release manager / QA**
1. `TIER_DIFFERENCES.md` (tier architecture)
2. `batch02_bundle_file_structure_guide.md` § Four-Tier Architecture
3. `SESSION_START_MANIFEST.md` § 3 (release workflow)
4. `batch04_gotcha_guide.md` § 8 (release gotchas)

### **Researcher / science user**
1. `batch03_new_user_5min_runbook.md` (quick start)
2. `batch05_worked_example_sid8370.md` (schematic walkthrough — accurate workflow, illustrative scores)
3. `docs/GUIDE/02_Quick_Guide.md` or `docs/GUIDE/01_User_Manual.md` (reference)
4. `docs/GUIDE/04_Glossary.md` (terminology)
5. `docs/DAPR_CLASS_FRAMEWORK.md` (if interested in ecology)

---

## Pro tips

1. **First time?** Start with `batch03_new_user_5min_runbook.md`, then pick a deeper doc based on your interest.

2. **In a hurry?** Use the **Quick lookup by task** table above. Find your task, click the link.

3. **Stuck?** Search `batch04_gotcha_guide.md` by error message or symptom.

4. **Need big-picture context?** Read `batch02_bundle_file_structure_guide.md` to understand the bundle layout and four-tier architecture.

5. **Writing Mode B?** Bookmark `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md` and keep `batch05_worked_example_sid8370.md` as a side-by-side reference.

6. **Building tools?** Start with `batch01_tools_discoverability_map.md` to see what exists, then check `docs/MASTER_SCHEMA_FROZEN_v1_1.md` for data format.

7. **Don't know which doc?** You're reading the right one. Use the tables above.

