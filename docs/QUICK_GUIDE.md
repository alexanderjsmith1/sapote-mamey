<!-- SAPOTE_DOC_STATE: HISTORICAL_SUPERSEDED -->
<!-- SAPOTE_SUPERSEDED_BY: ../CURRENT_DOCS_INDEX.md | GUIDE/02_Quick_Guide.md -->

> **Historical / superseded reference.** This shipped page preserves its dated content for
> traceability; it is not the current operator guide. Use the
> [Current Docs Index](../CURRENT_DOCS_INDEX.md) and the
> [canonical current Quick Guide](GUIDE/02_Quick_Guide.md) for current instructions.

# Sapote–Mamey Quick Guide

*Sapote–Mamey v9.7.382 · engine 1.9.135 · 2026-08-27*

---
## What this is
**Mamey** is the extraction engine: it parses antiSMASH output, builds the BGC inventory, runs the scans, computes scores, and produces the triage board and workbook. It never writes speculative claims.
**Sapote** is the judgment layer — the LLM side of the pipeline (Claude, in this session). It reads Mamey's deterministic outputs and writes the Mode B deep-dive cards, ecological synthesis, and figure interpretation.
The contract between them is simple: Mamey supplies facts; Sapote interprets them; neither crosses into the other's lane.

---
## The workflow
```
antiSMASH output → Mamey run → validate → review triage board → Mode B cards → deliverables
```
Run Mamey on every strain before doing any Mode B interpretation. One strain at a time is fine. Use the triage board and master workbook to choose where to invest Sapote time.

---
## What to look for in the triage board
The triage board (`*_4_triage_board.csv`) is the primary decision surface. These columns drive Mode B selection:

| Column | What it means | Act when |
|--------|--------------|----------|
| `Corrected_rank` | Priority rank (Interior + ½·Edge + ¼·Full-contig) | Primary sort for Mode B selection |
| `Lead_tier_auto` | Exceptional / High / Medium / Low / Inventory | High/Exceptional → judge first; Medium → check context; Low → specialized-class capacity read; Inventory → allow-listed/unresolved context. Routing only, not activity. |
| `CCTT_triggers` | Class-defining domain markers | Any T43-* trigger is class-definitive |
| `KCB_top` | Top KnownClusterBlast similarity anchor | Similarity, not identity; blank = no anchor |
| `Novelty_auto` | 0–100; ≥30 = novel pool | High novelty + blank KCB = characterize from domains |
| `Misanchor_Flag` | KCB anchor class conflicts with architecture | Do not cite this anchor as a class call |
| `Two_Pathway_Flag` | Second biosynthetic engine in this window | Describe both engines in §1 and §3 |
| `Boundary` | Interior / Edge / Full-contig | Edge/FC → boundary caveats in card |
| `Arch` | A–E architecture confidence | D/E → write at that confidence, not A |
| `bldA_tier` | T1–T4 activation dependence | T3/T4 → address in §7 fermentation |
| `Standing_rule` | Downgrade/drop class (saccharide, NAPAA, ectoine…) | Standing rules are not optional |
| `Primary_metab_flag` | Primary metabolic gene | DROP — do not write a Mode B card |

---
## Special review buckets
Some BGCs must be reviewed even when not top-ranked:
- **Nucleoside priority** — always review for antifungal relevance (nikkomycin/polyoxin-like logic).
- **Polyene/PTM/HSAF flags** — review for antifungal relevance; arylpolyene alone is not antifungal polyene macrolide evidence.
- **`other` product rows** — antiSMASH `other` is not junk; it means gene-level review is needed.
- **RG-GMCI HIGH pairs** — possible split-pathway reconstructions. Review all HIGH pairs before authoring any Mode B for either member. The combined locus may rank higher than either fragment alone.
- **`Two_Pathway_Flag`** — a non-empty cell means the BGC window carries two mechanistically distinct biosynthetic engines. The antiSMASH class label covers only one of them. Describe both in §1 and §3 of the Mode B card.
- **`Misanchor_Flag`** — the KCB anchor class is discordant with the antiSMASH architecture. The anchor is not a class call; treat the BGC as architecturally dark for KCB purposes.

---
## When KCB is uninformative
On all-novel strains (most BGCs novelty ≥30, `KCB_top` blank or score < 500), KCB is too noisy to lean on. These axes work without a reference database:
- **`Two_Pathway_Flag`** — pure domain architecture. The most reliable first-pass signal for hidden pathway capacity on dark BGCs.
- **RG-GMCI HIGH pairs** — shared ClusterBlast geometry (not KnownClusterBlast). A `CLUSTERBLAST_ONLY` pair can rescue a split pathway with no MIBiG anchor at all.
- **CCTT triggers** — class-definitive domain markers that survive fragmentation. A T43-LASSO on a Full-contig BGC is still a lasso even with a 0% KCB score.

See the Detection Without KCB reference for the full treatment.

---
## Claim-safety rules
These apply to every sentence in every Mode B card and every deliverable:
- "biosynthetic capacity consistent with X" — not "produces X"
- KCB hits are similarity signals, not product identity
- Bioactivity metadata is optional strain-level context; omission is `NOT_SUPPLIED` and observations are never pinned to a BGC without governed linkage
- NAPAA excluded from comparative claims
- hglE-KS is habitat-non-specific; do not use for habitat specificity claims
- A `Misanchor_Flag` means the KCB anchor is discordant — do not cite it as a class call
- A `Two_Pathway_Flag` signals two engines, not evidence of a hybrid compound

---
## Mode B card durability
A Mode B card that lives only in a session window is lost when the session ends. Commit cards via the receipt path — this fires the card-time gates (claim-safety, locator reconciliation, quality floor) and reconciles the workbook index. Do not call a Mode B batch done until the receipts are ingested.

---
## Hostile audit
To get an adversarial review of a Mode B card or any document:
> "Audit this card" / "tear apart this BGC analysis" / "what would a reviewer say" / "is this publishable"

The auditor finds fabricated specificity, claim-safety failures, standing rule violations, KCB misuse, boundary failures, and lead-tier disagreements. Output is severity-ranked (BLOCKER / MAJOR / MINOR / STYLE) with quoted offending text and concrete corrections. Works on documentation as well as cards.

---
## Reference
- **Scoring constants and thresholds** — see the Quick Reference section of the Encyclopedia
- **Detection Without KCB** — two-pathway detection and fragment rescue for novel strains
- **Deliverable contract** — the 13-item full-run deliverable set
- **Mode B writing guide** — the full §1–§30 authoring reference (`FULL_MODEB_30_SECTION_CONTRACT_v97150.md`; §1–§20 mandatory core + §28, §30 mandatory + §21–§27, §29 conditional)
- **Fermentation and isolation** — detection handles, mechanism confirmation assays, extraction strategy
- **Cross-strain cohort / GCF families** — BiG-SCAPE across a cohort, families read back to the `strain:node.region` locator space; see `BIGSCAPE_GCF_WORKFLOW.md`, `BIGSCAPE_MAMEY_INTEGRATION.md`, and `SOPs/SOP-17_CrossStrain_GCF_Cohort.md`

---
## For users with Python/terminal access
The commands below are the direct Mamey invocations. If you are working through Claude, Claude runs these on your behalf — you do not need to run them yourself.

**Run a strain:**
```bash
python3 -m mamey run \
  --input-zip <antiSMASH_output.zip> \
  --strain <ID> \
  --taxonomy "<Genus species>" \
  --source "<provenance>" \
  --release PRIVATE \
  --mode gold \
  --json-evidence bounded \
  --outdir runs/
```

**Validate:**
```bash
python3 -m mamey validate runs/<strain>/package
```

**Seal (runs all QC gates, emits DEBUG_RECEIPT.md):**
```bash
python3 -m mamey seal-package runs/<strain>/package --out receipts/
```

**Bank and build the master workbook:**
```bash
python tools/mamey_intake.py --packages runs/ --banked-dir cohort/ --workbook project_master.xlsx
```

**Commit Mode B cards durably:**
```bash
python3 -m mamey ingest-receipts \
  --package runs/<strain>/package \
  --receipt mode_b_receipt.json \
  --master project_master.xlsx
```

**WORKBOOK_STATUS** is printed at the end of every run. A missing workbook without a recovery command is an incomplete delivery.
