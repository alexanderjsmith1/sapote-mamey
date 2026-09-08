# Bunny Hop Audit Request — Sapote–Mamey v9.7.108

**Bundle:** `Sapote_Mamey_v9_7_108.zip` (upload this alongside this document)
**Engine:** v1.9.98 / Bundle v9.7.108 / Build 20260622d
**Game rules:** `docs/BUNNY_HOP_AUDIT_GAME.md` in the bundle
**Date:** 2026-06-22

---

## What is the Bunny Hop?

An adversarial code/doc audit game. For each file:

**Inspector** argues the file should be CHANGED (finds bugs, gaps, drift, claim-safety issues). Gets exactly 3 arguments.

**Defender** argues the file should be KEPT AS-IS (rebuts with design rationale, correct-by-construction arguments).

**Consensus** decides: KEEP AS-IS, KEEP + actions (with effort: XS/S/M), or CHANGE.

Both sides must be honest. The Inspector shouldn't invent problems. The Defender shouldn't ignore real ones.

---

## Inspector Panels — Use a Mix

- **2-inspector** (fast, for files <100 lines): I1 (Claim-Safety) + I2 (Accuracy)
- **3-inspector** (medium files): add I3 (Completeness)
- **4-inspector** (files >200 lines and governance docs): add I4 (SSOT/Actionability)

---

## What Each Inspector Checks

**I1 (Claim-Safety):** KCB = similarity not identity. Capacity language ("consistent with," never "produces"). safe_kcb_display used for rendering. Standing exclusions enforced (NAPAA, hglE-KS, saccharide). No product-identity claims from genomics alone.

**I2 (Accuracy/Fail-Closed):** Version strings current. Bare `open()` writes without atomic pattern. Silent `except: pass` swallowing. Stale references. Off-by-one errors. Correct imports. Functions that exist but are never called.

**I3 (Completeness/Evidence-Conservation):** Honest blanks (never fabricated). Missing columns documented. Evidence trail from source to output. No dropped fields during schema transforms.

**I4 (SSOT/Actionability):** No duplicated constants across files. Single source of truth chains intact. Gate registry coverage. Copy-paste commands present. Actionable next steps.

---

## Files to Audit

### Priority 1 — 38 unaudited .py files

These have never been read by any auditor. Use 3- or 4-inspector panels for files >200 lines, 2-inspector for smaller ones.

| File | Lines | Suggested panel |
|------|-------|-----------------|
| `mamey/cohort_figures.py` | 438 | 4-inspector |
| `mamey/figures_sapote.py` | 405 | 4-inspector |
| `tools/dark_gene_scan.py` | 397 | 4-inspector |
| `tools/build_first_pass_scans.py` | 341 | 4-inspector |
| `mamey/compound_class.py` | 333 | 4-inspector (compare against architecture_first.py) |
| `tools/build_punchcard.py` | 262 | 3-inspector |
| `tools/build_modeb_deepdive.py` | 250 | 3-inspector |
| `mamey/compat_v941.py` | 227 | 3-inspector |
| `mamey/cross_strain_threads.py` | 222 | 3-inspector |
| `tools/build_genelevel_triage.py` | 211 | 3-inspector |
| `tools/fragment_concordance_scorer.py` | 199 | 3-inspector |
| `tools/gene_topology.py` | 157 | 3-inspector |
| `tools/encyclopedia_reground_check.py` | 156 | 3-inspector |
| `tools/build_dapr_rescue_sheets.py` | 152 | 3-inspector |
| `mamey/output_checklist.py` | 150 | 3-inspector |
| `tools/build_size_profile.py` | 150 | 3-inspector |
| `tools/build_chat_export.py` | 149 | 3-inspector |
| `mamey/cohort_figures.py` | 128 | 2-inspector |
| `mamey/cohort_class_heatmap.py` | 127 | 2-inspector |
| `tools/add_xstrain_sheets.py` | 127 | 2-inspector |
| `tools/build_pangenome.py` | 122 | 2-inspector |
| `tools/schema_deployed_audit.py` | 121 | 2-inspector |
| `tools/build_priority_leads.py` | 115 | 2-inspector |
| `tools/mamey_intake.py` | 107 | 2-inspector |
| `tools/build_workbook.py` | 103 | 2-inspector |
| `tools/build_overview_figures.py` | 96 | 2-inspector |
| `tools/build_validation_panel.py` | 89 | 2-inspector |
| `scripts/chatgpt_make_batch_summary.py` | 83 | 2-inspector |
| `tools/build_workflow_figure.py` | 83 | 2-inspector |
| `tools/build_tfbs_profile.py` | 82 | 2-inspector |
| `tools/cohort_concordance_summary.py` | 82 | 2-inspector |
| `mamey/sapote_markers.py` | 60 | 2-inspector |
| `tools/log_release.py` | 59 | 2-inspector |
| `tools/plot_examples.py` | 57 | 2-inspector |
| `tools/build_panel_figure.py` | 44 | 2-inspector |
| `tools/apply_dapr_boards.py` | 36 | 2-inspector |
| `mamey_run.py` | 19 | 2-inspector |
| `mamey/__init__.py` | 2 | 2-inspector |

### Priority 2 — 20 high-value unaudited docs

| File | Lines | Suggested panel |
|------|-------|-----------------|
| `docs/GLOSSARY.md` | 745 | 4-inspector |
| `docs/GUIDE/06_Concepts_QandA.md` | 539 | 4-inspector |
| `prompts/FULL_RUN_PROFILE.md` | 434 | 4-inspector |
| `docs/GUIDE/01_User_Manual.md` | 317 | 4-inspector |
| `PLAYBOOK.md` | 308 | 3-inspector |
| `prompts/CLAUDE_SYSTEM_PROMPT.md` | 290 | 3-inspector |
| `docs/modules/MODE_B_WRITE.md` | 255 | 3-inspector |
| `README.md` | 247 | 3-inspector |
| `prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md` | 233 | 3-inspector |
| `examples/bench_guide_exemplar.md` | 222 | 3-inspector |
| `examples/layperson_guide_exemplar.md` | 194 | 3-inspector |
| `docs/modules/DELIVERABLE_WetLabMatrix.md` | 159 | 3-inspector |
| `prompts/SAPOTE_MAMEY_CO_EXECUTION_PROMPT.md` | 146 | 3-inspector |
| `examples/fermentation_card_exemplar.md` | 144 | 2-inspector |
| `docs/BERT_MODE_PROTOCOL.md` | — | 3-inspector |
| `docs/LITERATURE_SEARCH_PROTOCOL.md` | — | 3-inspector |
| `docs/ANTISMASH_PROFILE.md` | — | 2-inspector |
| `docs/FIGURE_STYLE.md` | — | 2-inspector |
| `docs/RELEASE_CHECKLIST_v9.md` | — | 3-inspector |
| `docs/COHORT_RESCORING_PLAN.md` | — | 2-inspector |

---

## Patterns to Grep For

```bash
# Bare writes (data safety)
grep -rn "json.dump(.*open(" mamey/ tools/
grep -rn "\.open(.*\.write(" mamey/ tools/

# Raw kcb_top without safe rendering (claim safety)
grep -rn "kcb_top" mamey/ tools/ | grep -v "closest_candidate\|safe_kcb\|test_\|#"

# Silent exception swallowing
grep -rn "except.*pass$\|except:$" mamey/ tools/

# Stale version strings
grep -rn "v9\.7\.\(10[0-3]\|9[0-9]\)" mamey/ tools/ docs/

# Duplicated constants (SSOT drift)
grep -rn "TIGRFAM\|DIAGNOSTIC_PANEL" mamey/ tools/ | grep -v test
```

---

## How to Run a Session

1. Upload `Sapote_Mamey_v9_7_108.zip` + this document
2. Extract the CODE tier
3. Read `docs/BUNNY_HOP_AUDIT_GAME.md` for the full rules
4. Roll 6 files per round (3 .py + 3 docs is a good mix)
5. Do 3-5 rounds per session
6. For each file: read it fully, then play both Inspector and Defender
7. Save the output as `BUNNY_HOP_<YOUR_SESSION>.md`

---

## Output Format

For each file hopped:

```markdown
## Hop N — `path/to/file.py` (NNN lines)

**What it is.** One-sentence description.

### Inspector — 3 reasons to CHANGE
**I1 (Claim-Safety).** [finding]
**I2 (Accuracy).** [finding]
**I3 (Completeness).** [finding — if 3+ inspectors]
**I4 (SSOT).** [finding — if 4 inspectors]

### Defender
[Rebuttal for each Inspector argument — be specific]

### Consensus
✅ KEEP AS-IS / ✅ KEEP + N actions / ❌ CHANGE
[If actions: list each with effort estimate XS/S/M]
```

At the end of your session, include:

1. **Patch card** — table of all actions with file, fix, and effort
2. **Positive exemplars** — any files that are unusually well-designed
3. **P0/P1 findings** — anything that crashes, loses data, or violates claim-safety
4. **Score** — how many KEEP AS-IS vs KEEP + actions vs CHANGE

---

## Standing Rules (Apply During All Hops)

- **Claim-safe language always** — "biosynthetic capacity consistent with," never "produces"
- **KCB = similarity, not identity**
- **Bioactivity metadata is optional strain-level context** — `NOT_SUPPLIED` when absent; never pin to a specific BGC
- **No strain called activity-negative** — contrast by mechanism, not phenotype
- **NAPAA excluded** from all comparative claims
- **hglE-KS-PREV-001** habitat-non-specific
- **Corrected BGC count** = Interior + ½·Edge + ¼·Full-contig
- **Assembly tiers:** GOOD ≥70% / MODERATE ≥45% / POOR ≥20% / VERY_POOR <20%
- **Affiliation:** 

---

*Bunny Hop Audit Request — Sapote–Mamey v9.7.108*
