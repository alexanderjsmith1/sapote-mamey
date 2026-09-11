# ChatGPT Execution Slice — v9.7.147
**Status:** default ChatGPT/Sapote execution controller.  
**Replaces default use of:** `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md`.  
**Engine line:** Mamey 1.9.100.  
**Applies to:** sealed `MAMEY_COMPLETE` / `MAMEY_COMPLETE_WITH_ISSUES` packages and interactive Mode B handbacks.

This document is intentionally not a summary kernel. It is the full-depth ChatGPT execution contract needed to prevent abbreviated delivery, hidden edge-BGC suppression, and buried code-backed outputs.

---

## 0 — Authority order

1. `docs/DELIVERABLE_CONTRACT.md` — what must be handed back.
2. `docs/MODE_B_20_SECTION_CANONICAL_TITLES.md` and `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md` — §1–§20 section titles and structure. **These documents define section names only. §28 and §30 are required for every card; §21–§30 conditional sections are defined in §9 of this slice. The execution slice supersedes any "§1–§20 only" reading of those documents.**
3. `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md` — minimum reasoning depth for §5, §9, §11, §12, and §19.
4. `docs/TRIGGER_ROUTING.md` — workflow, quality-gate, and conflict-routing table.
5. `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` — parent controller for concepts not restated here.

`docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` is retained only for legacy integrations. Do not load it as the active controller for new ChatGPT sessions. If a legacy prompt asks for the slim kernel, load this execution slice after it and let this document override any abbreviated behavior.

---

## 1 — Non-negotiable operating rules

- Do not ask for scope confirmation once a sealed package or explicit Mode B target is present.
- Do not offer abbreviated alternatives to required deliverables.
- Do not pause between Mode B batches unless the session is at a hard execution limit; emit the current batch, state exactly what remains, and provide the next continuation path.
- Do not silently omit a BGC. Every detected BGC must be visible in the triage board and in the treatment ledger.
- Treat edge/full-contig status as assembly metadata, not an automatic reason for lower scientific visibility.
- Use claim-safe language: biosynthetic capacity and evidence-supported class hypotheses only; no production, structure, or bioactivity attribution without metabolomics/fractionation/genetic proof.
- End every substantive ChatGPT handback with exactly 8 distinct plain-text numbered next paths.

---

## 2 — Intake handshake

For every package:

```text
SAPOTE/CHATGPT EXECUTION SLICE LOADED
Package: [strain_id] · [MAMEY_COMPLETE/MAMEY_COMPLETE_WITH_ISSUES]
Bundle/engine/build: [bundle] / [engine] / [build_stamp]
Assembly: [tier] · [contigs] contigs · [interior_pct]% interior
BGCs: [raw] raw · [corrected] corrected
Controller: docs/CHATGPT_EXECUTION_SLICE_v97147.md
```

Abort only if the package is invalid or the user asked for extraction in a no-exec environment. Otherwise continue into the handback and judgment workflow.

---

## 3 — Mandatory post-`MAMEY_COMPLETE` handback block

When `MAMEY_COMPLETE` or `MAMEY_COMPLETE_WITH_ISSUES` is detected, the next ChatGPT response must include this block before narrative judgment:

```text
CODE-BACKED OUTPUTS PRESENTED
[ ] OPEN_ME_FIRST.html — link/path or NOT FOUND
[ ] manifest.json — link/path or NOT FOUND
[ ] [StrainID]_8_strain_brief.pdf — link/path or NOT FOUND
[ ] _8a…_8m_fig_*.png — list every figure found; include companion *_data.csv files
[ ] gold_figures/ — list all F01-F15 PNG + sidecar CSVs, or state SKIPPED/NOT_FOUND
[ ] cohort_figures_gold/ — list all cross-strain heatmaps if N>1 run, or NOT_APPLICABLE
[ ] locus_maps/ — list every SVG/PNG found, or state none found
[ ] [StrainID]_5_workbook.xlsx — link/path or NOT FOUND
[ ] checksums_sha256.txt — link/path or NOT FOUND
[ ] issue_log.md — link/path or NOT FOUND
```

**RC1 — NO_FIGURES_RENDERED.md detection (v9.7.148):**
If `NO_FIGURES_RENDERED.md` is present in the package, run `python -m mamey render-figures --package <pkg>` BEFORE presenting the handback. Do not present the handback without attempting figure rendering first. This file is written when `--brief none` or `--chatgpt-safe` was used; the re-render recovers the strain brief PDF and 8a/8b figures.

**JUDGMENT PENDING banner (v9.7.148):**
After presenting code-backed outputs, emit this block before the deliverable menu:
```
═══════════════════════════════════════════════════════════════
⏳ EXTRACTION COMPLETE — SAPOTE JUDGMENT PENDING
   [N] BGCs extracted · 0 given Mode B interpretation
   Trigger full analysis: Run full Sapote analysis on [StrainID]
═══════════════════════════════════════════════════════════════
```
The session is not complete at MAMEY_COMPLETE. A package without Sapote judgment is a skeleton, not an analysis.

Then state that the prompt-backed set is ready. Offer or auto-produce, as the user preference and `DELIVERABLE_CONTRACT.md` require:

- Layperson-Ranked BGC Guide
- Technical Full-Analysis Report
- Compound Detection and Isolation Bench Guide
- Fermentation Card
- Wet-Lab Decision Matrix
- Metabolomics Readiness
- Ecological Synthesis
- Reviewer Attack Simulation
- Assembly QC / Contig Rescue / LMPKS Rescue when triggered
- Literature-Search Handoff list

A handback that merely says the run is done, without surfacing the strain brief, figures, locus maps, and prompt-backed set, is incomplete.

---

## 4 — Triage board and BGC visibility

### 4.1 Sort order

Sort all BGCs by `Corrected_rank` when present; otherwise by the active priority axis (`AB_auto`, `AF_auto`, or user-requested ranking). Do not sort Interior first and Edge/FC later. The `EdgeStatus` column provides assembly context; the rank provides scientific priority.

### 4.2 POOR/VERY_POOR assembly banner

If assembly tier is `POOR` or `VERY_POOR`, put this banner above the triage board:

> POOR-tier assembly — edge/full-contig status is primarily an assembly artefact. Rank by score and interpretability, not by boundary status. Boundary caveats appear in §3 and §19; they do not justify burying the BGC.

### 4.3 Every BGC visible

For POOR/VERY_POOR assemblies, every deliverable must show all detected BGCs:

- Triage board: all BGCs sorted by rank, edge/full-contig labeled but not buried.
- Mode B session: every BGC gets at least a minimum candidate card.
- Layperson guide: disclose the total count and catalog all remaining regions after the top leads.
- Fermentation card: include every bioactivity-relevant class, not only top-ranked interior BGCs.

Minimum candidate card fields:

```text
strain / full node-or-contig / regionXXX / BGC alias · class/product hypothesis · boundary status · KCB top hit or NONE · one interpretive sentence · next action
```

Single-gene or uninterpretable fragments may receive a minimum candidate card, but only with an explicit reason why full interpretation is not possible.

---

## 5 — Wet-lab and DAPR scoring boundary

Edge/full-contig truncation is interpreted differently by assembly tier:

| Assembly tier | Edge/FC score effect | Reason |
|---|---:|---|
| GOOD/MODERATE | −2 when truncation materially limits interpretation | Boundary likely reflects a real missing locus edge |
| POOR/VERY_POOR | 0 | Boundary is usually an assembly artefact; do not suppress the chemistry picture |

Never apply a POOR/VERY_POOR assembly-wide penalty to Interior BGCs, and never use edge/full-contig status to hide a high-scoring lead.

---

## 6 — Mode B structure

Full Mode B uses exactly the current §1–§20 section titles from `docs/MODE_B_20_SECTION_CANONICAL_TITLES.md`:

1. Identity and node/region
2. Why this BGC was selected
3. Boundary and assembly status
4. Gene-by-gene interpretation
5. Core biosynthetic logic
6. Tailoring and maturation logic
7. Transport, resistance, and regulation
8. Comparator/KCB interpretation
9. Alternative hypotheses
10. Fragmentation and co-capture risks
11. Product-family interpretation
12. Bee/microbe ecological interpretation
13. Antibacterial/antifungal relevance
14. What cannot be claimed
15. Missing evidence
16. BLASTP/HMMER next steps
17. LC-MS / fermentation implications
18. Figure/locus-map notes
19. Final Mode B judgement
20. Next actions

Rules:

- Full Mode B is prose-first. Tables are companions, not substitutes.
- Edge/FC BGCs may receive Full Mode B when the visible architecture is interpretable, the score/trigger warrants it, or the user selects them.
- The boundary caveat belongs in §3 and §19. Do not turn it into an all-sections depth reduction.
- Missing evidence does not remove a section. Keep the section and state the gap plus next action.

---

## 7 — Edge/FC equal-depth floor

Every edge/full-contig BGC with interpretable domain content must receive equal structural attention to an interior BGC at the same scientific priority. Minimum required for every edge/FC BGC:

- §1: identity and contig/region citation.
- §3: boundary and truncation statement.
- §4: gene table or gene-by-gene interpretation for all visible CDS.
- §5: core biosynthetic logic from the visible evidence.
- §11: product-family interpretation with truncation caveat.
- §19: claim ceiling, including what the boundary prevents.
- §20: next actions, including long-read sequencing or RG-GMCI reconstruction when applicable.

Do not create a separate lesser report type called “Partial Mode B” as the default for edge/FC BGCs.

---

## 8 — Interpretive floor before §19

Before writing §19, run the `INTERPRETIVE_FLOOR_CHECK` from `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md`:

- §5 must connect domain architecture to structural consequences.
- §9 must weigh alternatives against evidence.
- §11 must connect tailoring complement to scaffold complexity.
- §12 must reason through mechanism and tag ecological confidence.
- §19 must be an argument: evidence summary, alternative rejection, claim ceiling, confidence tags.

If any floor fails, expand the earlier section before writing §19.

---

## 9 — Optional/conditional §21–§30 extensions

§28 and §30 are required for every completed Mode B card. Other sections fire when data are available or class context warrants them.

| Section | Required when | Content |
|---|---|---|
| §21 — Precursor mass ladder | Any RiPP BGC | Predicted monoisotopic masses across modification states |
| §22 — RiPP database search | Any RiPP BGC | RODEO/antiSMASH precursor DB results; not BLASTP |
| §23 — Heterologous expression | `MATURATION_GAP` present or novel compound class | Host, construct boundary, co-expression needs |
| §24 — Scaffold novelty score | Novel compound / no MIBiG hit | COCONUT/NP Atlas/DNP comparison when available |
| §25 — Genome neighbourhood | Any isolation-worthy BGC | Flanking genes, mobility, synteny |
| §26 — OSMAC protocol | Any fermentation-selected BGC | Bench-ready induction/extraction plan |
| §27 — Self-resistance assessment | Any antimicrobial candidate | Genome-wide immunity/export assessment |
| §28 — Evidence provenance ledger | All cards | Claim-by-claim source tracing: observed/computed/inferred/assumed |
| §29 — Cross-cluster interactions | Strain has >3 high-priority BGCs | Regulatory/metabolic crosstalk hypotheses |
| §30 — Experimental decision tree | All cards | Open questions → experiments → programme consequences |

Do not invent external search results. If a database/literature search was not run, mark the extension as a work order, not a finding.

---

## 10 — Trigger routing hooks

The execution slice must recognize and obey these trigger constants from `docs/TRIGGER_ROUTING.md`:

- `CHATGPT_EXECUTION_SLICE_LOADED`
- `MAMEY_COMPLETE_HANDOFF_REQUIRED`
- `ANALYSIS_COMPLETE_DELIVERABLE_OFFER`
- `LOCUS_MAP_PRESENTATION_REQUIRED`
- `POOR_TIER_EDGE_EQUALITY`
- `INTERPRETIVE_FLOOR_CHECK`
- `FULL_MODEB_REQUEST_DETECTED`
- `OFFLINE_EVIDENCE_ALLOWED`
- `WISE_PKS_QUEUE_DETECTED`

Conflict guard: `OFFLINE_EVIDENCE_ALLOWED` suppresses `WISE_PKS_QUEUE_DETECTED` auto-trigger when BLASTP is unavailable rather than pending.

---

## 11 — Final output gate

Before handback, verify:

- [ ] Code-backed outputs were surfaced or explicitly marked not found.
- [ ] Prompt-backed deliverables were auto-produced or explicitly offered first in next paths.
- [ ] Triage board includes every BGC and is not Interior-first sorted.
- [ ] POOR/VERY_POOR edge/FC penalty is not applied.
- [ ] Every BGC has a treatment status and no silent omissions.
- [ ] Full Mode B cards use exact §1–§20 titles.
- [ ] §28 and §30 appear for every completed Mode B card, or a recorded reason explains why not.
- [ ] Final response ends with exactly 8 distinct numbered next paths.

---

---

## 12 — Mode B §16 completion → automatic BLASTP emission (v9.7.148)

After completing §16 (BLASTP priority queue) for any BGC:

1. Run: `python -m mamey modeb-blastp --package <pkg_dir> --bgc <BGC_ID>`
2. Present the output files immediately alongside the §16 text.
   State: "BLASTP files for BGC___ are in modeb_blastp/<BGC_ID>/ — batch N covers proteins X, Y, Z."
3. If the command is unavailable (no-exec session), emit the FASTA manually from the panel manifest and state which file was produced.
4. Include the companion README.txt with every batch.

This step is **not optional**. Completing §16 as prose without producing FASTA files is incomplete. The session should produce files a user can submit directly.

**SIGXFSZ note:** if a protein is >2,500 aa (e.g. ctg94_18 at 3,049 aa), note it in the README and advise the user to try the full sequence first; if NCBI rejects it, split at domain boundaries into ~1,000 aa parts.

---

## 13 — Compiled analysis report — complete deliverable specification (v9.7.148)

After completing all Mode B cards and the ecological synthesis, produce the compiled analysis report. This is the **master deliverable** — the single document a PI or collaborator can open and read without knowing the pipeline. It contains everything.

**Pre-condition:** Mode B cards must be complete for all top-N leads. State which cards are pending if producing mid-session.

**The report is not a Mode B summary. It is not 7 pages.** It contains all of the following sections in order, with no section omitted:

---

### Required sections (all mandatory, in this order)

**1. Cover block**
Strain ID, genus/species, host, location, assembly tier, corrected BGC count, bundle version, date, PRIVATE tag. Pull from manifest deterministically.

**2. Executive summary** (1 page)
What the strain is, what the assembly quality means for confidence, the top 3–5 leads by name and class, the single most important experimental action. Claim-safe throughout. 5–10 sentences.

**3. Layperson guide** (1–2 pages)
Plain English — no jargon. Written for a PI who does not know antiSMASH. Cover: what the strain is, where it came from, what it appears to make, why those compounds might matter ecologically and medically, and what you would do next in the lab. This section must stand alone — a reader who reads only this section must understand the significance of the work.

**4. Assembly and strain summary**
Table: taxonomy, host, location, assembly tier, raw/corrected BGC count, N50, contigs, CCTT triggers, standing-rule exclusions applied, RGGMCI HIGH pairs. Assembly tier caveats for edge/full-contig BGCs.

**5. Triage board** (all BGCs, ranked by AB score)
Markdown table — every BGC, no omissions. Columns: BGC ID, Node/Region (with full node citation per §15), Class, Boundary, AB, AF, Novelty, KCB top hit, Downgrade flags, Priority.

**6. Figures** (every available figure, embedded or referenced)
- Strain brief figures (`_8a` landscape, `_8b` composition)
- Gold figures (`gold_figures/` — F01 per-BGC domain heatmap, etc.)
- Locus maps for all top-priority BGCs
- Any DAPR, RGGMCI, or cross-strain figures available
For each figure: embed the image if possible; otherwise state path + one-sentence caption.

**7. Cross-strain and ecological synthesis** (1–2 pages)
What this strain contributes to the cohort. Habitat-specific patterns, conserved classes, unique biosynthetic capacity. Cross-strain comparison if cohort data is available. Claim-safe throughout — mechanism not phenotype, capacity not activity.

**8. Priority lead deep-dives** (one section per top 3–5 BGC)
For each: BGC ID + node (per §15), compound class, biosynthetic logic summary (3–5 sentences), ecological interpretation, predicted activity axis, self-resistance mechanism, top BLASTP hits, next experimental action (§30 Q1 of the Mode B card). This is NOT a copy of the Mode B card — it is a synthesised narrative for each lead.

**9. Complete Mode B cards** (all completed cards, full §1–§20 + §28 + §30)
Every completed Mode B card, included in full. Not summarised. Not abbreviated. If a card runs long, include it in full. Uncarded BGCs get a minimum candidate card (class, KCB, next action, one sentence).

**10. BLASTP evidence summary**
Table: BGC, protein, %ID, organism, annotation, finding. All BLASTP results that changed a class call or confirmed a hypothesis.

**11. Fermentation and wet-lab guidance**
For each top-priority BGC: recommended media, additives, timepoints, extraction method, detection approach (LC-MS mass window, UV, bioassay). Formatted as a table + brief notes per BGC.

**12. Wet-lab decision matrix**
Per-BGC action: PRIORITY ISO / HIGH SEQ / MEDIUM ACT / LOW / EXCL. Dereplicate flag. One-line rationale.

**13. Outstanding work and next actions**
Numbered list: immediate (no uploads, no wet lab), bioinformatic, wet lab. Ordered by speed/impact.

**14. Methods and claim-safety note**
Pipeline version, antiSMASH version, claim-safe language statement, KCB = similarity disclaimer, and typed bioactivity metadata state. PNAS-format citations for antiSMASH and MIBiG.

---

### Build order (required — do not skip steps)

**Step 1 — Generate derivable figures from available CSVs.**
Before assembling the report, generate the figures that can be produced from the already-extracted data. These do not require a gold-mode run:
- `fig_bgc_ranking` — horizontal bar chart, top 15 BGCs by region length, coloured by boundary (Interior/Edge/FC)
- `fig_class_composition` — bar chart of compound class counts (non-excluded BGCs only)
- `fig_assembly_tier` — stacked bar of assembly completeness (Interior/Edge/FC fractions)

Data source: `_4_triage_board.csv` (already in the package). Use matplotlib. Data-only PNG + companion `_data.csv` per figure.

If gold figures exist (`gold_figures/` in the package): include them. If `gold_figures/GOLD_FIGURES_REQUIRE_GOLD_MODE.md` is present: note that domain heatmaps require a gold-mode re-run and include the note inline.

**Step 2 — Generate domain-strip locus maps for top-priority BGCs.**
For each top-3 lead: produce a gene-arrow locus map from the GBK data (already parsed into `_gene_context.jsonl` or `cds_table.csv`). If locus maps already exist in the package (`locus_maps/` or `gold_figures/`): use them. If not: generate from the CDS table using the locus map renderer.

The megacluster reconstruction figure (if produced earlier in the session) is included here. Any BLASTP-informed architecture figures belong in this section.

**Step 3 — Resolve any wrong or pending cards.**
If any Mode B card has been reclassified or flagged as invalid (e.g. BGC044 ranthipeptide → mycofactocin), the revised card must be complete before assembly. Do not include an invalidated card in the compiled report; include a placeholder noting the revision is pending.

**Step 4 — Assemble in this exact section order:**
```
Cover page
→ Executive summary
→ Layperson guide
→ Assembly and strain summary
→ Triage board (all BGCs)
→ Figures (Steps 1 + 2 outputs, with captions)
→ Cross-strain and ecological synthesis
→ Priority lead deep-dives (top 3–5)
→ [Section break] Complete Mode B cards (all, §1–§20 + §28 + §30)
→ BLASTP evidence summary table
→ Fermentation and wet-lab guidance
→ Wet-lab decision matrix
→ Outstanding work and next actions
→ Methods and claim-safety note
```

Each section break gets a full-page divider in the PDF (horizontal rule + section title, centred).

**Step 5 — Gate delivery on `mamey compile-report --strict`.**

Before presenting the compiled report as a deliverable, run:
```bash
python -m mamey compile-report <pkg> --strict
```
If it exits non-zero, the open SAPOTE narrative slots are printed — fill them first. To write pre-authored narrative sections into the package:
```bash
python -m mamey write-narrative <pkg> --section executive_summary --file exec.md
python -m mamey write-narrative <pkg> --section layperson_guide   --file lay.md
python -m mamey write-narrative <pkg> --section ecological_synthesis --file ecol.md
python -m mamey write-narrative <pkg> --section priority_deep_dives  --file deepdives.md
```
Each write runs the claim-safety linter. Refused with exit 3 if linter flags; use `--force` only after review. **A report with unfilled SAPOTE slots is not a deliverable.**

### Format and rendering requirements

**Table of contents must be auto-generated, not hand-written.** Never write a TOC with estimated page numbers — they will be wrong. The TOC in the AS-XXX v9.7.148c report was 53 pages off by the final section (Outstanding Work: said page 60, actually page 113). Figures claimed to start on page 17; they started on page 26.

Use pandoc's automatic TOC generation via the YAML front-matter:
```yaml
---
title: "AS-XXX Analysis Report"
toc: true
toc-depth: 1
---
```

With `toc: true`, pandoc inserts `	ableofcontents` at the start of the LaTeX document. LaTeX computes correct page numbers after two-pass compilation. Do NOT write a manually formatted `Table of Contents` block in the Markdown body — it will produce a second, wrong TOC alongside the automatic one.

If the compiled report is produced as pure Markdown without LaTeX rendering, omit the TOC entirely rather than writing a hand-estimated one. A missing TOC is better than a wrong one.

**Section breaks must not produce blank pages.** Every section divider in the Markdown source must be a single `---` horizontal rule followed immediately by the section heading on the next line. Do NOT use:
- A LaTeX `\clearpage` or `
ewpage` command in the Markdown
- Two consecutive `---` rules
- A `---` rule followed by a blank line before the heading
- A dedicated full-page section title page (a page containing only "Section 3 — Chapter" with nothing else)

The correct pattern is:
```markdown
[last line of section 2 content]

---

# 3. Chapter — BGC Landscape

[first line of section 3 content]
```

The wrong pattern (produces blank page + header-only page):
```markdown
[last line of section 2 content]

---

# Section 3

---

# 3. Chapter — BGC Landscape
```

A 111-page report should not have 16 near-blank pages (8 blank + 8 header-only). If a section needs visual separation, a single horizontal rule before the heading is sufficient. LaTeX's `\part{}` and `\chapter{}` commands also create forced page breaks — avoid them unless explicitly needed.

**BGC IDs in every part of the compiled report must carry node and region (§15).** The 324 bare BGC ID instances found in the AS-XXX compiled report were all prose violations — exclusion lists, lead tier tables, cross-references, fermentation guidance. The §15 rule applies everywhere in the document, including:
- Exclusion tables: `BGC018 (NODE_16 · r001)` not `BGC018`
- Lead tier tables: `BGC028 (NODE_32 · r001)` not `BGC028`
- TOC entries: abbreviation acceptable (`BGC028 · NODE_32`) but bare ID alone is not
- Cover summary fields: include short node form — `BGC028 megacluster (NODE_32 · r001)`

Before rendering the PDF, run the pre-delivery scan from §15: search for bare `BGC\d{3}` patterns not followed by `NODE_` or `· r\d+` within the same clause. Fix every hit. In a compiled report this is non-trivial — budget time for it.

**Cover page — do not repeat in section bodies.** The cover page (section 1) contains the strain metadata table (strain ID, genus, host, assembly tier, top leads). Every section after the cover starts clean — do not repeat the strain/date/bundle header as body text. The running header (strain name · PRIVATE) is added by the LaTeX renderer automatically; do not put it in the Markdown body. If you include a mini-header at the top of each section (e.g. "AS-XXX Analysis Synopsis · Saccharopolyspora sp."), this will stack on top of the renderer's running header and produce overlapping text. Remove all per-section header repetitions — start each section directly with its heading (e.g. `# 1. Synopsis`) and content.

**Layperson guide claim-safety.** The layperson guide uses plain English — that is correct and intentional. However, plain English still has a claim ceiling. The specific violations to avoid:

- NEVER: "AS-XXX produces X" / "The compound is X" / "This bacterium makes Y antibiotic"
- ALWAYS: "AS-XXX has the genetic capacity to make something in the X class" / "The genes suggest this bacterium could produce a compound similar to X" / "We cannot say what compound is made without isolating it"

The layperson guide is allowed to say "produces" when describing a *class* of chemistry (e.g. "produces siderophore-type molecules that grab iron") — but NOT when naming a specific compound or making a product identity claim. The distinction:
- ✅ "produces siderophore-type iron-grabbing molecules" (class-level capacity)
- ✅ "has genes for making polyketide antibiotics, a class that includes erythromycin" (analogy to known, not identity claim)
- ❌ "produces totopotensamide" (compound identity)
- ❌ "the compound is a structurally distinct analogue of X" (identity claim dressed as analogy)
- ❌ "the compound is secreted into the growth medium" (implies compound identity is known)

**Popular mechanism names are footnotes, not headlines.** Compound-class mechanism analogies (e.g. "Trojan horse," "molecular sponge," "molecular scissors") are useful shorthand in live analysis conversations where they're grounded in gene-level evidence. They become overclaims when they appear as section titles, fermentation card names, or headlines in compiled reports. The compiled report must be more conservative than the analysis conversation that informed it.

Correct: "BGC003 (NODE_107 · region001) encodes biosynthetic capacity consistent with an albomycin-class siderophore-antibiotic conjugate." A footnote may add: "This compound class has been described informally as a 'Trojan horse' mechanism in the literature."

Incorrect as a headline: "FERM-002: Albomycin Trojan horse" — this makes the mechanism analogy the primary identifier for the compound, which it is not.

The same principle applies to any evocative label coined during a Mode B analysis session. If it originated in the conversation rather than in a published compound name, treat it as informal shorthand: use it in prose where the context makes clear it is a mechanistic description, not in titles, headers, fermentation card names, or TOC entries.

**"PI clearance required" must not appear anywhere.** The correct phrase is just **PRIVATE**. Check every footer, every header, every classification line in the Markdown source before rendering. The running footer is generated from the YAML front-matter — ensure the YAML uses "PRIVATE" not "PRIVATE — AS-series data · PI clearance required."

**Background must be white. Text must be black.** Do not use dark themes, dark backgrounds, or coloured backgrounds anywhere in the document.

**Do not use `wkhtmltopdf` directly.** Use `tools/md_to_pdf.sh` or produce clean Markdown and let the PDF skill handle rendering. `wkhtmltopdf` inherits dark-mode CSS from the system and produces illegible output.

**Produce the report as Markdown first** (`<strain>_Analysis_Report_<date>.md`), then render to PDF. The Markdown file is the canonical deliverable — the PDF is a presentation copy.

**Target length:** as long as it needs to be. For a 13-BGC strain with 10 Mode B cards, expect 40–80 pages. Do not abbreviate to fit a page target.

**File naming:**
- Markdown: `<strain>_Analysis_Report_<date>.md`
- PDF: `<strain>_Analysis_Report_<date>.pdf`

Both files are required deliverables. Present both.

---

## 14 — Mycofactocin disambiguation rule (v9.7.148 PATCH-MYCO-DISAMBIGUATION)

When TIGRFAM evidence includes the co-occurrence of:
- TIGR03967 (MftC radical SAM) AND
- TIGR03996 (MftD FMN-dependent oxidoreductase) AND
- TIGR03997 (MftE HMHP hydrolase)

**Call the class as mycofactocin**, regardless of whether TIGR04085 (SPASM domain) is also present.

Mycofactocin pathways carry SPASM-domain radical SAM enzymes. The presence of TIGR04085 does not make the locus ranthipeptide if MftD+MftE are co-clustered. The MftD+MftE co-occurrence is definitive for mycofactocin.

**Downstream implications:**
- Mycofactocin is a redox cofactor RiPP, not an antibiotic
- Exclude from antibacterial/antifungal comparative leads
- Lead tier: Inventory / cofactor class
- Ecological interpretation: cofactor biosynthesis, not defensive chemistry
- Do not apply ranthipeptide-specific interpretations (thioether crosslinks, QueE ring contraction, halogenated ranthipeptide scaffold)

This rule was triggered by BGC044 (NODE_73) in AS-XXX, where the prior ranthipeptide interpretation was invalidated by the Mamey v9.7.146 TIGRFAM scan.


---

## 15 — BGC node/contig citation — hard enforcement rule (v9.7.148a)

**Every BGC reference in every deliverable must carry its node and region.** This is an absolute requirement, not a style preference. It applies to all output: Mode B cards, triage boards, layperson guides, analysis reports, fermentation cards, ecological synthesis, RGGMCI discussions, exclusion lists, and prose cross-references.

### The required citation format

**First mention in any section:**
```
BGC007 (NODE_1_length_406707_cov_83 · region001)
```
or, for the triage table abbreviated form:
```
BGC007 | NODE_1 · r001
```

**Subsequent mentions within the same section:** the full node may be abbreviated to `NODE_1` (drop the length/cov suffix) but the region must be retained:
```
BGC007 (NODE_1 · r001)
```

**Cross-references between sections** (e.g. "BGC007 and BGC027 form a pair"): use the abbreviated form — `BGC007 (NODE_1 · r001)` — not the bare ID.

**Exclusion lists** (e.g. "NAPAA (BGC023)"): append the node — `NAPAA (BGC023 · NODE_4 · r001)`.

**Locus map file references** (e.g. "BGC007_locus_map.svg"): this is a filename, not a BGC citation — no node required in the filename itself, but the surrounding sentence must carry the node: "Locus map for BGC007 (NODE_1 · r001): BGC007_locus_map.svg."

### Where the node data comes from

The Mamey package contains the full BGC→node map in three places:
- `_4_triage_board.csv` — columns `node_id`, `contig`, `antismash_region`, `assembly_locator`
- `_1_intake.json` — `bgc_records[].node_id`, `.antismash_region`
- `bgc_data.json` — `bgcs[].node_id`, `.region`

The `assembly_locator` field in the triage board contains the canonical human-readable string (e.g. `NODE_1_length_406707_cov_83.896633 region001 (BGC007)`). Use it verbatim at first mention; abbreviate only for subsequent references within the same section.

**If the triage board is not loaded**: the Mode B card header already carries the node (`## BGC007 · NODE_1_length_406707 · region001`). Read it from there.

### Mechanical check before presenting any deliverable

Before presenting any document, scan for bare `BGC\d+` patterns — that is, `BGC007` not followed within the same clause by `NODE_` or `contig` or `· r\d+`. Every hit is a violation. Fix it before presenting.

The following patterns are NEVER acceptable:
```
BGC007 is one of the top leads          ← bare
NAPAA (BGC023)                          ← bare
BGC007 and BGC027 form a siderophore pair  ← bare
RiPP BGCs (003/019/022)                 ← bare (also: do not use numeric shorthand without the BGC prefix)
```

The following are ALWAYS required:
```
BGC007 (NODE_1 · r001) is one of the top leads
NAPAA (BGC023 · NODE_4 · r001)
BGC007 (NODE_1 · r001) and BGC027 (NODE_6 · r001) form a siderophore pair
RiPP BGCs: BGC003 (NODE_15 · r001), BGC019 (NODE_3 · r001), BGC022 (NODE_4 · r002)
```

This rule exists because BGC IDs are Mamey-internal bookkeeping. A collaborator reading the report, a reviewer examining the evidence, or a user returning to the report months later cannot locate `BGC007` in the assembly or antiSMASH HTML without the node and region. The node citation is the locus identifier; the BGC number is a convenience alias.


---

## 16 — Multi-strain batch workflow (v9.7.148e)

**When you have multiple antiSMASH ZIPs, do not run `mamey run` on each strain one at a time by hand.** Use the intake harness, which chains them, appends to a shared master workbook, writes a batch report, and handles timeouts gracefully.

### Step 1 — Install the engine (once per session)

```bash
pip install -e . --break-system-packages
```

No network required. Works offline from the bundle.

### Step 2 — Run all strains in one batch

```bash
python tools/intake_harness.py   --inputs strain_A.zip strain_B.zip strain_C.zip strain_D.zip   --outdir runs_YYYYMMDD   --registry runs_YYYYMMDD/intake_registry.csv   --metrics runs_YYYYMMDD/intake_metrics.csv   --batch-report runs_YYYYMMDD/batch_report.md   --release PRIVATE   --mode gold
```

Use `--mode gold` — it is the default and only analysis mode (smoke was removed v9.7.161; standard is a deprecated alias). For a capped ChatGPT session add `--capped-session`. Each strain's package lands at `runs_YYYYMMDD/<strain_id>/package/`.

### Step 3 — Validate each package

```bash
for pkg in runs_YYYYMMDD/*/package; do
    python -m mamey validate "$pkg"
done
```

### Step 4 — Run Mode B for each strain's top leads

```bash
python -m mamey mode-b --package runs_YYYYMMDD/<strain_id>/package --top-n 5 --outdir mode_b/<strain_id>/
```

Repeat for each strain. **Do not author Mode B cards from raw antiSMASH GBKs by hand** — that is what the engine run produces. Cards authored without a Mamey package are missing AB/AF scores, CCTT triggers, corrected BGC counts, KCB crosswalk, standing-rule exclusions, and RGGMCI pairs.

### Step 5 — Strain metadata is in the package, not the user

Do not ask the user for strain metadata (host, genus, location). All of it is in `<pkg>/_1_intake.json` (strain_id, display_name, release) and `<pkg>/manifest.json`. The triage board has the assembly tier, contig count, corrected BGC count. Read the package first.

### What "I have the manifests but not the full package outputs" means

If you have triage boards but not the gene-by-gene table, locus maps, or RGGMCI pairs, re-run in gold (the default) to get the full output:

```bash
python -m mamey run   --strain <ID> --display '<Genus species strain ID>'   --input-zip <antiSMASH.zip> --outdir runs_YYYYMMDD   --mode gold --release PRIVATE   --master runs_YYYYMMDD/Mamey_Master.xlsx
```

### §21–§30 are required

§21–§30 extensions (§28 evidence ledger, §30 experimental decision tree) are required for every completed Mode B card per this execution slice §9. The reference to "§1–§20 only" in `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md` is superseded by this slice. If that document says §21–§30 don't exist, this slice takes precedence (§0 authority order).

**After each completed Mode B card, persist it to the judgment register immediately:**

```bash
python -m mamey ingest-receipts --package <pkg> --card judgment/<strain>_<BGC_ID>_mode_b.md
```

This is the recommended per-card flow — one file, one command, no receipt JSON to assemble. It resolves the BGC ID and session ID automatically from the card's `<!-- MODE B: ... -->` header. **A card that exists only in chat is not in the register** and will not appear in `mamey resume` or `mamey compile-report` until ingested.

At the start of a new session, recover any cards that were written but never ingested:
```bash
python -m mamey ingest-receipts --package <pkg> --auto-detect
```

`--receipt <file.json>` remains available for batched end-of-session persistence workflows, but `--card` is the simpler default for ingesting as you go. The three flows (`--receipt`, `--auto-detect`, `--card`) are mutually exclusive.

After any ingest, `mamey resume` reflects the new state immediately:
```
**Judgment status:** IN_PROGRESS | **Last Sapote session:** S-2026-06-29-batch3
```
`judgment_status` is the register's rolled-up state across all BGCs (PENDING / IN_PROGRESS / COMPLETE).

---

*Sapote–Mamey v9.7.148a execution-slice update · patches: PATCH-COMPILED-OUTPUT Ph1/Ph2, PATCH-MODEB-BLASTP-AUTO, PATCH-AUTO-FIGURES, PATCH-MYCO-DISAMBIGUATION, PATCH-NODE-CITATION-ENFORCEMENT.*
