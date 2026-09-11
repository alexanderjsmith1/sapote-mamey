# Sapote–Mamey deliverables

Default analysis, deep-dive, and report deliverables, each shipped in **three formats** — markdown (`.md`),
PDF (`.pdf`), and Word (`.docx`). Regenerate everything from the banked cohort with:

```bash
bash tools/build_all_deliverables.sh [cohort_dir] [workbook.xlsx]
```

This re-runs the report generators (Mode B deep dives, thesis vignettes, GCF tags, size profile) and compiles
every markdown to PDF (`tools/md_to_pdf.sh`, xelatex) and Word (`tools/md_to_docx.sh`, pandoc).

## analyses/
- **Saccharide_Omitted_Analysis** — per-strain class leaders + the saccharide-adjusted 33% novelty correction.
- **BGC_size_by_type_analysis** — fragmentation-robust size-by-type metric (count inflates +0.39, size deflates −0.55; the two bracket the truth).
- **Sapote_CrossStrain_Synthesis** — the verified 8-section ecological synthesis (hglE 17/59, T2PKS 90%, etc.).

## deep_dives/
- **ModeB_DeepDives_Full** — gene-by-gene §1–§8 for all 35 verdicts (27 CONFIRM / 3 DOWNGRADE / 5 DROP); DROPs show the gene-level basis for rejection.
- **ModeB_DeepDives_ClassA** — the six Class-A priority leads.
- **Thesis_Vignettes_ClassA** — each lead's dive paired with its size-context percentile + cause-effect map, as worked chapter sections.

## reports/
- **Sapote_Mamey_Session_Progress** — consolidated progress write-up.
- **Thesis_Figures_Index** — figure catalogue.
- **SAPOTE_MAMEY_RELEASES** — the three release tiers (CODE / SID / MERGED) and their data/privacy boundaries.
- **GCF_Expansion_PunchCard** — research brief for expanding the GCF thesaurus from the orphan list.

## incoming_figures/
Drop-in for figure markdowns produced in other chats. Place a `*.md` (with its referenced PNG/SVG alongside)
here; `build_all_deliverables.sh` will compile it to PDF + Word with the rest, and it can be folded into the
matching analysis report. See `incoming_figures/README.md`.

All deliverables are class-level and KCB-anchored (similarity, not identification); bioactivity metadata is optional strain-level context and omission is `NOT_SUPPLIED`. Verified free of private AS-prefixed identifiers.

## Requesting deliverables
Use `DELIVERABLE_INSTRUCTION_TEMPLATE.md` — a self-contained spec (goal, banked inputs, deterministic tool
command, output + encoding conventions, claim-safety guards, acceptance checklist, hand-back). Worked, validated
examples are in `DLV_EXAMPLES.md`. Track requests in `HIVE_Board.csv` (Board_ID ↔ Deliv_ID ↔ Status ↔
Output_Location; `Private=Yes` rows never enter a public CODE/SID release). The template's standard
confidence-tier palette and locus-label format apply across all figures/atlases/tables.

## Generic prompt library
`GENERIC_PROMPT_LIBRARY.md` — nine reusable parameterized prompts (G1–G9: BGC atlas, cross-cohort panel, strain
one-pager, single-BGC Mode B, cross-strain table, priority-leads figure, layperson guide, manuscript paragraph,
pangenome) with GLOBAL GUARDS and a **readiness audit** mapping each to its driving tool (7 ready, G2 gap + G6
partial pending a `--subset` flag — DLV-008). Paste GLOBAL GUARDS once per session, then any G-block.
