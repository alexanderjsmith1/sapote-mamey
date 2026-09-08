# Assistant upload first step

For ChatGPT/Claude uploads, the root file `000_READ_ME_FIRST_CHATGPT_CLAUDE.md` is the front door. ChatGPT then reads `CHATGPT_START_HERE.md`; Claude reads `CLAUDE_START_HERE.md`; accidental `CHATGTP` transpositions are rescued by optional `CHATGTP_READ_ME_FIRST.md`.

---

# START HERE — Sapote–Mamey

Pick what you're doing; go straight to the tier + tool. (Full capability menu: `SESSION_START_MANIFEST.md`.)

**Run one strain** → `docs/SINGLE_STRAIN_QUICKSTART.md` · tier CODE · capped-session first-run: `python -m mamey run --mode gold --capped-session --json-evidence off`; deeper local run: `mamey_run.py run --mode gold`; then `ingest_package.py`. (v9.7.335: this line previously read `--mode smoke --chatgpt-safe`, which **crashes** — `smoke` was retired in v9.7.161 and `run` now accepts only `{standard,gold}`; `--chatgpt-safe` was renamed `--capped-session`. Gold is the only analysis mode and completes in about a minute on a typical genome.)

**Merge / cohort workbook** → tier **MERGED-PRIVATE-scaffold** (v9.7.335: this previously said "AS data is private". Per the PI decision of 2026-07-06 the **AS-series cohort is PUBLIC** and the AS scrub is deactivated by default — re-arm with `AS_SCRUB=1` only for a future private cohort. The MERGED tier remains the place for genuinely private scaffold content) · `ingest_package.py --merge`, `master_workbook.py`. Normalize schemas before combining; recompute cohort-local layers after merge.

**Audit a run / public cut** → tier CODE · `check_deliverable_suite.py`, `audit_public_cut.py`, `pytest tests/test_no_unpublished_ids_in_public_tier.py` (leak invariant), `check_antismash_profile.py` (cross-profile pooling guard).

**Publish / cut a public release** → `tools/make_public_tier.sh` (anchor-free AS-### scrub, emits `TIER_MANIFEST.txt`, runs the leak invariant before zipping). Public tiers: CODE, CODE-analysis-free, SID-public. **Never push a tier containing AS-### (hard guard).**

**Figures** → tier CODE · `build_figures.py --banked-dir cohort`, `build_panel_figure.py`.

**BiG-SCAPE / GToTree / IQ-TREE** → tier CODE, post-seal companion workflows · first read `docs/LLM_COMPANION_TOOL_PROTOCOL.md`. BiG-SCAPE emits additive locator-keyed GCF evidence by default; GToTree requires a visible size/resource preflight and user approval. Direct card/triage mutation is a separate authorization.

**Concordance / panel matching** → `fragment_concordance_scorer.py` (strain fragments vs the 73-ref panel), `reference_panel_ledger.py` (observed signatures from antiSMASH zips).

**Cross-reference an ID** → `build_id_resolver.py --banked-dir cohort` → `BGC_ID | bgc_uid | contig/NODE | region | antiSMASH file | workbook row`.

**Literature / summaries** → Eden/Bert summary mode; the Glossary workflow (`docs/GLOSSARY.md` is canonical).

Standing guards: claim-safe language (capacity, not production); KCB = similarity, not identity; omitted bioactivity metadata is `NOT_SUPPLIED`, not a named assay default; affiliation = .
