# Sapote-Mamey Deliverable Contract — v9.4

This document is the canonical source for what the bundle must produce. It is referenced by `CLAUDE_SYSTEM_PROMPT.md` (§4, §5), `MAMEY_CHATGPT_EXECUTION_PROMPT.md` (§3, §5), and `RELEASE_CHECKLIST_v9.md`. If any other document conflicts with this contract, this document takes precedence (except for the active parent monolith, which supersedes all).

**Status:** `SCHEMA_BACKED` for workbook sheets; `PROMPT_BACKED` for interpretation documents; `CODE_BACKED` for Python scan outputs.

---

## Deliverable Offer Protocol (default behavior — non-negotiable)

The deep-dive deliverables are the bundle's primary value. A user must never have to know they exist in order to receive them. At the point any strain reaches analysis-complete (all A1 extraction outputs present), Sapote must not end its turn without doing ONE of:

1. **Auto-produce** the full per-strain deep-dive set — Layperson-Ranked Guide, Technical Full-Analysis Report, Compound Detection & Isolation Bench Guide, Fermentation Card, and gene-by-gene detail for the top BGC leads; or
2. **Explicitly offer it** — a clear, plain-language question asking whether to generate the deep-dive deliverable set, presented as the first item in the next-steps block, phrased so a first-time user understands what they would receive.

Default delivery format is a **single consolidated PDF** containing all of the above, because a PDF is the colleague-facing hand-off format; markdown and per-file outputs are offered as alternatives. If the user has stated a standing preference (auto-generate, a named subset, or a format), honor it and skip the question. The offer/auto-build is mandatory and may not be silently dropped: an analysis that stops at the workbook without surfacing the deep-dive set is an **incomplete delivery**.

**Generation-time requirements (non-negotiable; verify before any deliverable is handed over).** Every generated deliverable — in tables, prose, headers, and chat — MUST satisfy both:

1. **No internal/personal codenames.** The project name is "Actinomycetes Project" and the affiliation is . Retired internal/personal codenames must never appear in any deliverable. If a codename would otherwise be pulled from project context or memory, substitute the public name. Run a codename scan on every deliverable before release.
2. **Contig-ID locator on every BGC (per §4 Contig-ID Mandate).** A bare `BGC###` is meaningless because it does not locate the cluster. The first time a BGC appears in any section, give at minimum `BGC_ID (contig · regionXXX)`; thereafter `BGC_ID (regionXXX)` is acceptable within that section. This applies to layperson guides, technical reports, bench guides, fermentation cards, gene-by-gene tables, and chat — not just Layer B tables. The package already carries this as the `User_Label` field; carry it through, never strip it.

A deliverable that contains a codename or a bare un-located BGC reference is non-conformant and must be regenerated before hand-over.

**Next-Paths Protocol (every response and every handback, all runners — Sapote/Claude AND ChatGPT/Mamey).** Every substantive response, batch handback, and completed deliverable ends with plain-text numbered next-step paths — concrete, specific to the current state, and chooseable (e.g. "1. Bank SID-XXX to exercise the ansamycin diagnostic"). Plain text only; never tappable widgets, buttons, or UI elements. This is a hard closer: a handback without next-paths is incomplete. **ChatGPT/Mamey rule: exactly 8 unique next paths, numbered 1–8, for every substantive response or handback.** The legacy 3–10 range remains acceptable only for non-ChatGPT Sapote/Claude contexts. ChatGPT-tier runners historically omit or underfill this closer; therefore the ChatGPT execution prompt, startup files, and task-brief template all carry the stricter 8-path rule so the behaviour is inherited, auditable, and not optional. A ChatGPT handback with fewer than eight paths, more than eight paths, duplicate/filler paths, or no paths is non-conformant and must be regenerated before delivery.

---

## Part A — Per-strain deliverables

These are mandatory for every strain. Missing items must be logged in the deferred ledger with reason and completion path.

### A1 — Mamey extraction outputs (CODE_BACKED)

> **Authoritative file list = `mamey/validate.py:REQUIRED_SUFFIXES`.** The table below matches the
> current engine output (v1.9.x). Scan results are consolidated into `manifest.json` and
> `_3_scan_states.json` rather than emitted as separate per-scan CSVs; a validator should check
> `REQUIRED_SUFFIXES`, not the older per-scan filenames.

| Deliverable | File | Required content |
|---|---|---|
| Intake / assembly | `[StrainID]_1_intake.json` | Genome size, contigs, interior/edge/full-contig %, assembly tier, raw and corrected BGC counts |
| BGC inventory | `[StrainID]_2_inventory.csv` | Every BGC with class, edge status, Architecture Confidence, KCB top hit, MIBiG %, WL score, bldA/TTA tier, treatment status |
| BGC crosswalk | `[StrainID]_2b_bgc_crosswalk.csv` | BGC_ID ↔ bgc_uid ↔ contig/region ↔ User_Label locator map |
| Scan states | `[StrainID]_3_scan_states.json` | Status and output file for all source-derived scans; assembly block; package status |
| RG-GMCI (full + ranked + evidence) | `[StrainID]_4A_RGGMCI_full.json`, `_4A_RGGMCI_ranked_pairs.csv`, `_4A_RGGMCI_evidence.csv` | Split-BGC pairs from ClusterBlast/KnownClusterBlast; required for every multi-contig genome |
| Triage board | `[StrainID]_4_triage_board.csv` | Per-BGC triage: CCTT triggers, primary-metab flag, standing rule, corrected rank |
| Diagnostic Rescue (4B) | `[StrainID]_4B_Diagnostic_Rescue_Leads.{csv,json,md}`, `_4B_Diagnostic_Rescue_Tiling.csv` | Auto-emitted rescue leads + tiling (via `package_addons`) |
| Workbook | `[StrainID]_5_workbook.xlsx` | Per-strain workbook (coded sheets) |
| Output checklist | `[StrainID]_6_output_checklist.{csv,md}` | Per-run completeness checklist |
| Cell provenance | `[StrainID]_7_cell_provenance.csv` (+ README) | Status code per workbook cell (no silent blanks) |
| Strain brief + figures | `[StrainID]_8_strain_brief.pdf`, `_8a`…`_8m_fig_*.png` (+ `_data.csv` each) | PDF brief binding all auto-emitted figures, each with companion data CSV |
| Manifest | `manifest.json` | Authoritative handoff object: all key findings, scan statuses, evidence pointers, version |
| Provenance aliases | `[StrainID]_Project_Memory_Snapshot.json`, `_records.json`, `_verdicts.json`, `ANALYSIS_FORWARD.md` | Machine-readable handoff + analysis-forward next steps |
| Commit receipt | `commit_receipt.json` | Run provenance / commit record |
| Issue log | `issue_log.md` | Per-run issues and caveats |
| Checksums | `checksums_sha256.txt` | SHA-256 for every file in the package |

### A2 — Sapote interpretation documents (PROMPT_BACKED)

| Deliverable | Audience | Required sections |
|---|---|---|
| **Layperson-Ranked BGC Guide** | PI, student, collaborator | Strain header block; 2–3 sentence narrative; 5-BGC ranked table with layperson headlines; assembly caveat; immediate next action |
| **Technical Full-Analysis Report** | Natural-products specialist | Intake; assembly/BGC summary; all ten scan results; Triage First Board containing every BGC sorted by rank; DAPR (antibacterial + antifungal, separate); full Mode B for HIGH/HIGH* BGCs; candidate cards for MEDIUM BGCs; minimum candidate cards for remaining BGCs; edge/FC status as caveated metadata rather than a visibility limiter; wet-lab decision matrix; metabolomics readiness; fermentation card; ecology synthesis; **Cross-Strain Cohort Context block** (see A2.1); **Method Caveats block** (see A2.2); reviewer attack simulation; recommended figures; **Literature-Search Handoff list** for parallel ChatGPT execution (see A2.3) in place of inline lit-review prose; PNAS reference list |
| **Compound Detection and Isolation Bench Guide** | Bench scientist | Per-BGC bench protocol for HIGH and MEDIUM BGCs: detection method (UV, pigment, bioassay), extraction protocol, LC-MS method, isolation strategy — in plain English |

#### A2.1 — Cross-Strain Cohort Context block (required in every per-strain deliverable)

Situates the single strain against the current banked cohort so a one-strain package is never read in isolation. Sourced from the `Strain_Cohort_Context` and `Cross_Strain_Class_Prevalence` workbook sheets. Required contents: corrected-BGC **rank in cohort** and assembly tier; **shared accessory chemistry** (each notable class with the count of other strains carrying it, e.g. "T2PKS — shared with 13 others"); **strain-unique classes** in the cohort (provisional, sample-limited); **novelty footprint** = this strain's fully KCB-dark region count expressed as a fraction of the cohort total (the only strict novelty floor); **diagnostics carried** vs the cohort. All figures are presence/prevalence over antiSMASH product-class calls — class-level, never assayed chemistry. The four universal classes (saccharide, fatty_acid, other, terpene) are excluded from shared/novel statements.

#### A2.2 — Method Caveats block (inherited boilerplate; every deliverable carries it verbatim)

1. `kcb_cumulative` is a cumulative **score, not a % identity** — a KCB hit anchors a class hypothesis, it does not mean the compound is known; never phrase a KCB value as "% known."
2. RG-GMCI HIGH-pair counts are **not a fragmentation-severity metric** — they track reference-anchored homologous-pair richness (gated by BGC content) and do not move monotonically with contig count.
3. The four universal product classes are **non-discriminating** and are excluded from cross-strain shared/novel arguments.
4. `hglE-KS-PREV-001` is **collection-specific** — state it against the strain set it was measured on, never assume project-universal prevalence.

#### A2.3 — Literature-Search Handoff list (replaces inline lit-review; for parallel ChatGPT run)

Rather than writing the literature review inline (which serialises the work behind the deep-dive), the Sapote layer emits a **structured list of searches** the user can hand to ChatGPT to run in parallel while the deep-dive is written. Format: a numbered table of `Lead (BGC locator) | search query | purpose | citation purpose`, targeting PubMed first then Scholar. Every row is a **search to run, not a verified fact**; nothing from it may enter a manuscript until citation-verified (Verified/Partial bucket with a confirmed PMID/DOI). ChatGPT returns, per row: PMID/DOI, title, one-line finding, and a Verified/Partial/Not-found tag (no fabrication; unmatched rows return Not-found).

#### A2.4 — Figure-Ready Tidy Export (standardised, portable; for downstream figure workflows)

The master workbook is human-optimised (coded sheets, wide matrices, formulas, units in headers) and is **not** what a third party should plot from directly. Every deliverable set therefore also ships a **figure-ready tidy export** so anyone can turn the outputs into figures in their own workflow (ggplot2, seaborn/matplotlib, Tableau) without wrangling. Produced by `tools/export_figure_ready.py <master_workbook.xlsx>`, which reads only the standard sheets and emits a `figure_ready/` folder of tidy CSVs — one observation per row, snake_case headers, no formulas, no merged cells, plus a `DATA_DICTIONARY.md`:

- `strain_summary.csv` (one row / strain), `bgc_inventory.csv` (one row / BGC), `bgc_class_long.csv` (one row / BGC×class), `class_by_strain.csv` (one row / strain×class), `class_prevalence.csv` (one row / class, banded), `diagnostics_long.csv` (one row / strain×TIGRFAM), `cross_strain_findings.csv`.

The export carries its caveats inline (kcb_cumulative is a score not a percent; universal classes flagged non-informative). `tools/plot_examples.py <figure_ready_dir>` builds three reference figures from the CSVs (fragmentation-loss gradient, class prevalence, class×strain heatmap) as a starting recipe — these are examples, not the only supported plots. **Standardisation rule:** column names, types, and the data dictionary are stable across runs; downstream code may depend on them, so they are versioned with the bundle, not changed ad hoc.

#### A2.5 — Per-BGC page layout in the Mode B / gene-by-gene compilation (co-location mandate)

In any compiled deliverable that pairs a BGC locus map with its analysis (the gene-by-gene deep-dive, the Technical Report's Mode B section, the consolidated PDF), **each BGC is a single page-unit**: the locus map and the analysis that interprets it must render **on the same page**, never split. The historical failure mode — and the one to prevent — is one locus map per page with the rest of the page left blank and the §1–§20 Mode B prose pushed to a following page. Required per-BGC unit, top to bottom:

1. **Locus map** — occupies roughly the **top 45%** of the page (the gene-arrow panel for that BGC).
2. **Predicted BGC class line** — a single line immediately under the map: `BGC_ID (contig · regionXXX) · predicted class: <class> · boundary: <Interior/Edge/Full-contig> · KCB: <similarity note>`. Claim-safe (class-level capacity, KCB = similarity).
3. **Mode B card** — the §1–§20 Mode B analysis for that BGC fills the **remaining ~55%** below the class line.

Rules: do **not** page-break between a locus map and its class line + Mode B card. Only spill to a second page when a single BGC's Mode B card genuinely overflows one page (then the map stays with §1–§4 and §5–§8 continues overleaf, with a "cont." marker). The full layout spec with a worked example is `docs/PER_BGC_PAGE_LAYOUT_SPEC.md`; the ChatGPT-side compiler inherits it via `prompts/figure_prompts/deliverable_maps/map_gene_by_gene.md`.

#### A2.6 — POOR/VERY_POOR equal-visibility rule (v9.7.147)

For POOR and VERY_POOR assemblies, all detected BGCs must remain visible in every report. Edge/full-contig status is assembly context, not a reason for lower visibility.

Required behavior:
- Triage board lists all BGCs at their natural rank position, sorted by `Corrected_rank` when present or the active priority axis otherwise.
- Edge/FC BGCs are labeled with boundary status but are not sorted below all Interior BGCs.
- Every BGC receives at least a minimum candidate card: `BGC_ID (contig · regionXXX) · class/product hypothesis · boundary status · KCB top hit or NONE · one interpretive sentence · next action`.
- Boundary caveats belong in Mode B §3 and §19. They do not justify reducing §4/§5/§11 reasoning depth when visible domain evidence is interpretable.
- Wet-lab/DAPR edge/FC truncation penalty is 0 in POOR/VERY_POOR assemblies unless a separate, documented non-assembly reason makes the fragment uninterpretable.

A deliverable where an edge/FC BGC can only be found in an unlabeled low-detail appendix, or cannot be found without knowing its ID, is incomplete.

### A3 — Workbook sheets (SCHEMA_BACKED)

| Sheet (canonical code · name) | Key columns | Notes |
|---|---|---|
| B1 · `B1_BGC_Master` | Strain, BGC_ID, Class, EdgeStatus, ArchConf, KCB_top_hit, MIBiG_pct, WL_score, TreatmentStatus | Every BGC; no PENDING stubs (was "BGC_Full_Inventory") |
| B3 · `B3_Known_Cluster_Matrix` | Strain, BGC_ID, Known_cluster, Hit_status, Claim_ceiling | KCB/MIBiG known-cluster mapping (absorbs old "Cassette_Registry") |
| D2 · `D2_RGGMCI_Top_Pairs` | Strain, BGC_A, BGC_B, Evidence_tier, Confidence | Multi-contig genomes only (was "RGGMCI_Pairs"; full set in D1) |
| G1 · `G1_Literature_Index` | Strain, BGC_ID, PMID, DOI, Authors, Year, Title, Journal, Evidence_type | All verified references (was "Literature_Index") |
| G2 · `G2_Validation_Roles` | Strain, BGC_family_expected, Evidence_for_absence, Assembly_caveat | Missing-hallmark / negative-evidence records (was "Qualified_Nulls") |
| C3 · `C3_Lead_Tier_Summary` | Strain, BGC_ID, Lead_tier, Assay_target, Priority | Lead tiers plus typed supplied assay metadata; blank targets remain `NOT_SUPPLIED` |
| A4 · `A4_Completeness_Audit` | Strain, BGC_ID, TreatmentStatus, Session, RunDate | Accountability record for every BGC (was "Completion_Audit") |

> **Single source of truth = `docs/WORKBOOK_SCHEMA.md`.** Sheets are referenced by **code** (A1, B1, …); codes never change. Any tool that reads/writes the workbook (including `tools/export_figure_ready.py`, which reads `B1_BGC_Master` + `A2_Strain_Registry`) targets these canonical names. The names above were reconciled from earlier ad-hoc labels so there is one vocabulary.

**Cross-strain analysis overlay (NOT in the frozen schema v1.1; pending fold into the Mamey builder / schema v1.2):**

| Overlay sheet | Key columns | Notes |
|---|---|---|
| `Cross_Strain_Class_Prevalence` | product_class, n_strains, pct_strains, n_BGCs, band, informative_for_comparison | Cohort class matrix; `band` = CORE/COMMON/ACCESSORY/UNIQUE |
| `Cross_Strain_Findings` | #, finding, metric, value, claim_status, note | Synthesis; `claim_status` = GROUNDED/FLAG/METHOD CAVEAT/PRIORITY/UNEXERCISED |
| `Strain_Cohort_Context` | SID, corrected_rank, tier, n_classes, shared_classes, unique_classes, zero_KCB_regions, zero_KCB_share_of_cohort, diagnostics_present | Backs the per-strain A2.1 cohort-context block |

### A4 — Provenance and packaging (CODE_BACKED + PROMPT_BACKED)

| Deliverable | Required content |
|---|---|
| Project Memory Snapshot | Machine-readable JSON: all key findings, BGC scores, evidence pointers, scan statuses, session date/version |
| Dated per-strain ZIP | `[StrainID]_Mamey_[BundleVersion]_[YYYY-MM-DD].zip` containing all A1 + A2 + A3 outputs |
| QA gate record | Confirmation that all required items are present or logged as deferred |

---

### A3 — Ported deliverable modules (auto-offered; v9.6.18)

Registered so each is auto-built/auto-offered per the Offer Protocol (the user must never need to know the deliverable exists to receive it). Authority for each is its `docs/modules/` module.

| Deliverable | Module | Auto-build trigger | Incomplete-delivery condition |
|---|---|---|---|
| Wet-Lab Decision Matrix | `docs/modules/DELIVERABLE_WetLabMatrix.md` | any Mode B / synopsis | score without the 4 action scores |
| Reviewer Attack Simulation | `docs/modules/DELIVERABLE_ReviewerAttack.md` | any contestable claim | claim with no RAS block / missing category |
| Diagnostic Domain Combos (knowledge) | `docs/modules/KNOWLEDGE_DiagnosticDomainCombos.md` | any class call | label asserted without the domain combo |
| LMPKS Rescue | `docs/modules/DELIVERABLE_LMPKSRescue.md` | any §42.2 trigger | no LMPKS section (even null) |
| Metabolomics Readiness | `docs/modules/DELIVERABLE_MetabolomicsReadiness.md` | Full-Run Profile | class without analytics handle; exact masses |
| Ecological Synthesis | `docs/modules/DELIVERABLE_EcologicalSynthesis.md` | end of Full-Run + host metadata | hypothesis without BGC citation; missing null |
| Figure Suggestion | `docs/modules/DELIVERABLE_FigureSuggestion.md` | complete strain report | no recommended-figures section |
| Cross-Strain Family Seeds | `docs/modules/DELIVERABLE_FamilySeeds.md` | after BGC inventory | inventory without seed rows |

## Part B — Project-bundle deliverables

Mandatory when all strains are complete or at user request. Produced by Claude (Sapote tier).

| Deliverable | Required content | Status |
|---|---|---|
| Cross-strain antibacterial rankings | Top ten BGC leads across all strains; compound class, WL score, assembly tier, bioactivity evidence | PROMPT_BACKED |
| Cross-strain antifungal rankings | Same format | PROMPT_BACKED |
| RG-GMCI statistics | Success rate, failure reasons, provisional-rescue counts, per-habitat breakdown | SCHEMA_BACKED |
| Cassette-family statistics | Frequency per cassette family; habitat enrichment table | SCHEMA_BACKED |
| Hallucination-trap statistics | PASS/FLAG/DISQUALIFY counts; most-flagged domain types | SCHEMA_BACKED |
| Ecological-theme comparisons | BGC class composition by habitat; novelty gradient; known-bioactive compound distribution | PROMPT_BACKED |
| Environmental-trigger matrix | Induction strategies across all strains; priority targets for cryptic BGC activation | PROMPT_BACKED |
| Master literature index | Deduplicated, verified reference list across all strain reports; PNAS format | PROMPT_BACKED |
| Qualified-null / validation-control report | BGC families expected but absent per habitat; positive-control compound recoveries | PROMPT_BACKED |
| Completion audit | TreatmentStatus for every BGC across every strain | SCHEMA_BACKED |
| Project bundle manifest | All files, sizes, SHA-256 checksums | CODE_BACKED |

---

## Part C — Treatment status vocabulary

Every BGC in every strain must carry one of these treatment status values:

| Status | Meaning |
|---|---|
| `full Mode B` | Full prose-first §1–§20 corrective-protocol Mode B report produced |
| `candidate card` | Abbreviated candidate card produced (MEDIUM priority) |
| `minimum candidate card` | Minimum-field interpreted card produced for LOW/DEPRIORITIZED or evidence-thin BGCs; must include locator, class/hypothesis, boundary, KCB/null, one interpretive sentence, and next action |
| `deferred` | Not analyzed this session; reason and completion path logged |
| `not applicable` | BGC is a known housekeeping cluster (e.g., ectoine, epsilon-PL); explicitly excluded from interpretation |

---

## Part D — Deferred ledger

Every deferred item must have:
- Item name and type
- Reason for deferral
- Exact inputs or conditions needed to complete
- Responsible tier (Mamey / Sapote)
- Target session or completion path

An item not logged in the deferred ledger is considered missing, not deferred.

---

*Sapote-Mamey Bundle v9.4 | Active controller: docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md | 2026-06-09*


---

## Citation-Compact Output Budget (proposed v9.7.136)

Citation-compact mode is the preferred low-token output profile for ChatGPT/Claude handbacks and reader-facing reports when the user wants dense evidence rather than repeated claim-safety prose.

The rule is:

1. emit one global BGC caveat per report/package;
2. do not repeat citation-compact paragraphs in every lead row or BGC card;
3. preserve claim-safety as structured fields:
   - `interpretation_scope`
   - `evidence_basis`
   - `citation_basis`
   - `uncertainty_flags`
   - `next_experiment`
4. write `Citation_Ledger.csv` and `Citation_Ledger.json`;
5. require citation basis for EXCEPTIONAL and HIGH leads, or an explicit `citation_needed` marker.

The template family lives in:

```text
templates/citation_compact/
```

The validation helpers live in:

```text
mamey/citation_compact.py
tests/test_citation_compact_v97136.py
```

This mode does not change scoring, lead ranking, cassette calls, KCB parsing, or RG-GMCI. It only changes how evidence, citations, and caveats are represented in outputs.



---

## Citation-Compact Provenance and Citation Status

Sapote-Mamey v9.7.140 uses citation-compact outputs to separate runtime evidence structure from literature verification.

- **antiSMASH 8.0** is recorded as method/database provenance for BGC detection and product/region calls: DOI `10.1093/nar/gkaf334`.
- **MIBiG 4.0** is recorded as reference-database provenance for curated BGC entries and KnownClusterBlast dereplication context: DOI `10.1093/nar/gkae1115`.
- **`PASS_STRUCTURE`** means the package structure, citation ledger, work-order files, compact reports, manifest tracking, and checksum tracking passed validation. It does **not** mean every literature claim has been manually verified.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a safe handoff for another ChatGPT/web-literature session. It is a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope. The older reader-facing scope field should not appear in current citation-compact outputs.

#### A2.7  Cross-strain GCF network (BiG-SCAPE) — A-series cohort deliverable

An exploratory / N-limited comparative deliverable produced after the per-strain runs, alongside the pangenome and normalization matrices: **`cross_strain_GCFs.tsv` + the browsable BiG-SCAPE HTML**. BiG-SCAPE clusters antiSMASH BGCs into gene cluster families by Pfam-domain content; the tsv lists, per cutoff, each family's spanned strains, dominant product, contains-MIBiG flag, and member `strain:node.region` locators — which join 1:1 onto the triage boards / Mode B cards. It is the whole-cluster-family complement to the pangenome's orthogroup sharing; cite them side by side, not interchangeably. BiG-SCAPE / Pfam are an external prerequisite (not vendored). Workflow + receipts: `docs/BIGSCAPE_GCF_WORKFLOW.md`. Framing is capacity / similarity, not identity or confirmed product.

#### A2.8  Known-vs-novel cross-strain GCF status (parallel MIBiG anchoring) — A-series cohort deliverable

`known_vs_novel_GCFs.tsv` = the base `cross_strain_GCFs.tsv` columns + `status` (KNOWN/NOVEL) + `n_members_known` + `mibig_matches`, produced by `bigscape_merge_anchors.py` unioning per-chat `bigscape_mibig_anchors.py` outputs against the no-MIBiG base. KNOWN = ≥1 family member anchors (shares a BiG-SCAPE family) to a characterised MIBiG reference; NOVEL = none — the cross-strain novelty candidates. Anchoring is domain-content similarity, not compound identity; NOVEL is candidate-novel, not confirmed. Exploratory / N-limited, like the pangenome and GCF-network layers. Workflow: `docs/BIGSCAPE_GCF_WORKFLOW.md` (parallel MIBiG anchoring across sessions).
