# Sapote–Mamey Quick Guide
**Version:** v9.7.401 / engine Mamey 1.9.143

---

## What this is

**Mamey** runs deterministic extraction: parsing, inventory, scans, scoring, workbook. It never writes speculative claims.  
**Sapote** is the LLM judgment layer: Mode B deep dives, ecological synthesis, figure interpretation.

Run Mamey first. Do Sapote only after you have a sealed package.

> **Mamey-first gate (v9.7.146+):** If you ask Claude or ChatGPT for Mode B without a sealed Mamey package, it will refuse and redirect you to run the engine first. The package provides correct boundary computation, WL/AB/AF scores, CCTT triggers, and cluster-level KCB that cannot be reproduced from raw antiSMASH output.

---

## 0. Install

Unzip the bundle, install the engine, then install the add-on wheels.

```bash
unzip sapote-mamey-v9.7.394-CODE-20260831v97394a.zip
cd sapote-mamey-v9.7.394-CODE-20260831v97394a
pip install -e .                      # installs the mamey command + core deps
```

On a managed system Python: add `--break-system-packages`. On Miniconda: plain `pip install -e .` works.

**Add-on wheels** (offline install — no network needed):

```bash
# drop the distributed .whl and .tar.gz files into a wheels/ folder, then:
pip install --no-index --find-links ./wheels biopython ijson pytest pluggy iniconfig
```

| Wheel | What it enables |
|---|---|
| `biopython-1.87-cp312-*.whl` | Robust GBK parsing (optional — shim works for standard antiSMASH output) |
| `ijson-3.5.0.tar.gz` | Fast JSON streaming C backend (optional — pure-Python copy ships in bundle) |
| `pytest-9.0.3-py3-none-any.whl` | Test suite — required for release cuts |
| `pluggy-1.6.0.tar.gz` · `iniconfig-2.3.0.tar.gz` | pytest dependencies |

For figures, also: `pip install matplotlib numpy`

**Biopython filename:** must use dots in version and platform tags (`1.87`, not `1_87`). If your file transfer swapped them, rename the file before installing.

**Verify:**

```bash
mamey doctor                          # dependency + permission check
python3 tools/sync_version.py --check # → engine 1.9.143, bundle 9.7.401
```

→ Full dependency reference: `docs/PREREQUISITES.md`

---

## 1. Run one strain

```bash
python mamey_run.py run \
  --strain AS-XXX \
  --input-zip AS-XXX_antismash.zip \
  --taxonomy "Streptomyces sp." \
  --source "Apis mellifera, Ontario" \
  --mode gold \
  --brief standard \
  --outdir runs/
```

Validate immediately after:

```bash
python mamey_run.py validate runs/AS-XXX/package
```

Status vocabulary: `MAMEY_COMPLETE` · `MAMEY_COMPLETE_WITH_ISSUES` · `VALIDATION_FAIL`. Do not use a VALIDATION_FAIL package.

---

## 2. Mamey-first for a cohort

Run every strain through Mamey before doing any Mode B interpretation. One strain at a time is fine.

```
run strain → validate → bank → update master workbook → next strain
```

Use the master workbook and special review buckets to choose Mode B targets. Do not spend judgment time on low-priority strains before the cross-strain pattern is visible.

---

## 3. Bank and build the master workbook

```bash
python tools/mamey_intake.py --packages runs/ --banked-dir cohort/ --workbook project_master.xlsx
```

Every run with `--master` appends the strain without deleting prior strains. Always check `WORKBOOK_STATUS` in the run output.

---

## 4. Post-MAMEY_COMPLETE handback

After every run the analysis chat automatically presents code-backed outputs before offering any prompt-backed deliverables:

- Strain brief PDF (`*_8_strain_brief.pdf`)
- All figures (`*_8a–_8m_fig_*.png` plus companion `_data.csv` files)
- Locus maps (`locus_maps/`)
- Workbook (`*_5_workbook.xlsx`)
- Checksums and issue log

If any of these are absent, say so — do not silently omit them.

---

## 5. The Deliverable Menu

After `MAMEY_COMPLETE`, the analysis chat presents the **Sapote–Mamey Diner Menu**. Full menu: `docs/DELIVERABLE_MENU_v97146.md`.

| # | What you get | Say |
|---|---|---|
| 1 | Triage Board — all BGCs ranked | "Triage board" |
| 2 | Lead Sheet — top 3–5 leads, one paragraph each | "Lead sheet" |
| 3 | Layperson Guide — plain-English, for PI / lab meeting | "Layperson guide" |
| 4 | Locus Maps — SVG gene-arrow diagrams | "Locus maps for BGC___" |
| 5 | BLASTP Batches — ready-to-submit FASTA + README | "BLASTP batches for BGC___" |
| 6 | Mode B Deep Dive — full §1–§30 for one BGC | "Full Mode B for BGC___ (NODE___)" |
| 7 | Full Strain Plate — everything for one strain | "Full plate for [strain]" |
| S1 | Fermentation Card | "Fermentation card" |
| S2 | Wet Lab Decision Matrix | "Wet lab matrix" |
| S3 | Metabolomics Readiness | "Metabolomics readiness" |

You can combine: *"#2 and S1 for the top three leads"* · *"Mode B for BGC028 (NODE_32) plus a fermentation card"*

---

## 6. Mode B cards — what to expect

The finished card is **§1–§48** (`FINISHED_FULL48_CURRENT_EVIDENCE`, gate-enforced since v9.7.369); **§1–§20** is the always-required core subset and **§1–§30** is the legacy candidate/calibration profile. Two sections are required for every completed card:

- **§28 Evidence provenance ledger** — every factual claim traced to its source file, engine version, and evidence tier (observed/computed/inferred/assumed). Makes cards surgically updatable.
- **§30 Experimental decision tree** — five open questions, each with: the resolution experiment, what the result would change in the card, and the downstream programme consequence.

**Interpretive floor (v9.7.146+):** §5 must connect domain architecture to structural consequences. §9 must weigh alternatives with evidence. §12 must name the ecological mechanism. §19 must argue the verdict, not restate §11. See `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md`.

**Edge/FC BGC equality (v9.7.147+):** All detected BGCs appear in the triage board sorted by score. In POOR/VERY_POOR assemblies edge/FC BGCs receive full Mode B depth — the boundary caveat belongs in §3 and §19 only.

---

## 7. Special review buckets

Some BGC rows must be reviewed even when not top-ranked:

- **Nucleoside priority** — always review for antifungal relevance (nikkomycin/polyoxin-like).
- **Polyene/PTM/HSAF flags** — review for antifungal relevance; arylpolyene alone is not antifungal polyene evidence.
- **`other` product rows** — antiSMASH `other` is not junk; it means gene-level review is needed.
- **RG-GMCI HIGH pairs** — possible split-pathway reconstructions; hypotheses, not confirmed contig joins.

---

## 8. Claim-safety reminders

- "biosynthetic capacity consistent with X" — never "produces X"
- KCB hits are similarity signals, not product identity
- Bioactivity is extract-level; never pin to a specific BGC without fractionation
- NAPAA excluded from comparative claims (ubiquitous, ecologically non-informative)
- hglE-KS is habitat-non-specific — do not use for habitat specificity claims
- Cite BGCs as `BGC028 (NODE_32_length_60747_cov_53 · region001)` at first mention

---

## 9. Citation provenance

### Citation-Compact Provenance and Citation Status

- **antiSMASH 8.0** method provenance: DOI `10.1093/nar/gkaf334`
- **MIBiG 4.0** reference database: DOI `10.1093/nar/gkae1115`
- `PASS_STRUCTURE` means package integrity passed — not that literature claims are verified
- `citation_needed` means a literature-search pass is still required
- `Literature_Search_WorkOrder.md/json` is a safe handoff for a separate web-search session
- `operator_supplied` — provenance row came from runtime evidence already in the package
- `interpretation_scope` — reader-facing scope field used in current compact lead tables

---

## 10. Post-seal deliverable subcommands

These run **against an already-sealed package** (or a directory of them). Every one is post-seal and
non-blocking — it reads facts the engine already computed and **never touches AB/AF/tiers, scans,
gates, or a published tier**. They are capacity-level, judgment-deferred deliverables (sign-off gated);
`domain-reference` / `realistic-count` / `novelty-shortlist` / `signoff` are advisory helpers.

```bash
# --- CROSS-STRAIN LEDGERS ---
python mamey_run.py cohort-leads    --runs-dir <runs_dir> [--out COHORT_PRIORITY_LEADS.csv]  # union of Exceptional+High leads → one ranked CSV
python mamey_run.py cohort-assemble --runs-dir <runs_dir> [--out COHORT_MASTER.csv] [--xlsx]  # many sealed packages → one master table

# --- EVIDENCE / FALSE-POSITIVE LAYER ---
python mamey_run.py comparator-coverage <package> [--cohort-runs-dir <runs_dir>]  # two-denominator MIBiG comparator coverage

# --- ANTIFUNGAL + INTERPRETIVE DELIVERABLES ---
python mamey_run.py af-dossier   <root> [--out DIR] [--activity-table CSV] [--depth N]  # AF leads x optional measured Candida activity
python mamey_run.py good-guesses <root> [--out DIR] [--pdf] [--docx] [--depth N]       # claim-safe interpretive priors (solid/rare/remarkable/notable/interesting)

# --- DOCUMENT + FIGURE EXPORT ---
python mamey_run.py modeb-export <card.md|mode_b/> [--outdir DIR] [--format docx|pdf|both]  # authored Mode B card → .docx + .pdf
python -m mamey.kcb_locusmap --zip <zip> --contig <NODE> --out-dir <dir> \
    --strain-id <ID> --bgc-id BGC### [--products "..."] [--top-n 6]                         # offline KCB comparative locus map (PNG/SVG + data.csv)

# --- COUNT / NOVELTY / REFERENCE (advisory) ---
python mamey_run.py domain-reference  --package <pkg> [--out FILE]           # bundled Mode-B domain-reference dictionary
python mamey_run.py realistic-count   --package <pkg> [--out FILE]           # honest corrected BGC-count denominator
python mamey_run.py novelty-shortlist --package <pkg> [--top 30] [--out FILE]  # composite multi-signal novelty shortlist

# --- ANALYSIS QC + MODE-B INTERPRETATION GATES ---
python mamey_run.py signoff [tree.treefile ...] [--minutes N]                        # "would a master's student sign off?" tree QC (advisory, exit 0)
python mamey_run.py verify-modeb --package <pkg> --bgc BGC### --interp [--interp-strict]  # add WARN-only INTERP_* judgment checks to verify-modeb
```

Claim-safety holds throughout: these surface capacity-level hypotheses and priors with their resolving
experiment, never a structural or bioactivity claim. `good-guesses` tags each notable BGC
solid / rare / remarkable / notable / interesting **and** names the experiment that would resolve it.

---

## Useful commands — natural language that works

Sapote–Mamey runs through Claude or ChatGPT, which means you talk to it in plain English. The pipeline is designed to understand intent, not just syntax. The phrases below are examples that reliably trigger the right behaviour — but you don't need to copy them exactly. The words in brackets are the parts you change.

One important note before the list: the pipeline runs **Mamey first, then Sapote**. Always have a sealed Mamey package before asking for any interpretation. If you ask for a Mode B card without a package, the analysis chat will tell you to run Mamey first — that's intentional.

---

### Getting started with a package

> **"Can you work from this to get me the full deliverables?"**

This is the single most useful phrase. Upload your antiSMASH ZIP or a sealed Mamey package alongside it and the chat will run the engine, present all outputs, and offer everything the pipeline can produce. It works because it signals intent (full deliverables) without constraining the path — the pipeline figures out where you are in the workflow and picks up from there.

> **"Run Mamey on [strain].zip and give me the full plate."**  
> **"Run full Sapote analysis on [strain]."**  
> **"Load the Mamey package and start judgment."**

### The three evidence channels (for lead BGCs)

Once you have a package, these phrases drive the reconciled Mode B evidence workflow. The pipeline
runs them in the right order on its own when you ask for a lead card, but you can also call them
directly:

> **"Read the KCB front page for [strain]."**  
> — the named database leads, each with its corroboration tier (STRONG / COINCIDENTAL / LARGE_GENERIC). Run this first; it is the cheapest strong signal.

> **"BLASTp every gene in [BGC] and reconcile against antiSMASH."**  
> — independent per-gene homology, with CONFIRM / REFINE / OVERTURN per gene, plus the cluster coherence and function/novelty reads. Fail-closed: if NCBI is down it says so and invents nothing.

> **"Plan a BLASTp round for [strain]."**  
> — the phased campaign: full per-gene BLASTp for the top BGCs plus one representative per remaining cluster. Shows the plan and time estimate; say "run it" to submit.

> **"Adjudicate [gene] — does the domain signature back BLASTp or antiSMASH?"**  
> — the offline HMM tie-breaker for a disagreement, plus module architecture and short-gene rescue.

A useful thing to know: a lead card wants all three channels *reconciled*, not just listed. The
honest answer for a well-conserved cluster with no characterised product match is "conserved genes,
unknown product" — which is a better lead than a weak compound name.


These are the formal trigger phrases. "Full plate" (menu item #7) means everything for one strain. "Start judgment" means begin Mode B after the package is loaded.

---

### Getting specific deliverables

> **"Triage board for [strain]."**  
> **"What are the top leads?"** / **"What's the best guess?"**  
> **"Write me the layperson guide."** / **"Explain it to my PI."**  
> **"Full Mode B for BGC028 (NODE_32 · region001)."**  
> **"Locus maps for the top three leads."**  
> **"BLASTP batches for BGC050."**

You can combine items in one request:

> **"Mode B for BGC028 plus a fermentation card and a wet lab matrix."**  
> **"Top leads, layperson guide, and BLASTP batches for the polyene cluster."**

---

### Continuing or updating an analysis

> **"Can you work from this to get me the full deliverables?"** *(with a prior handoff package uploaded)*

The same phrase works for continuing. If you upload the handoff package from a previous session, the chat reads the established context — what's been done, what's pending, what the established findings are — and picks up without re-deriving anything.

> **"Continue from where we left off on [strain]. Next priority is [BGC]."**  
> **"I have the Mamey package from the testing chat. What are the next steps?"**  
> **"Here's the BLASTP result for batch 10. Integrate it into the BGC050 card."**

---

### Requesting figures specifically

> **"Give me the domain heatmap for [strain]."** *(requires gold mode)*  
> **"Run render-figures on this package."**  
> **"I need the fermentation figures."**  
> **"Produce the figure set for the cohort."** *(2+ gold packages)*

If figures were skipped (`--brief none` or a capped run), say:

> **"Figures weren't produced — can you render them now?"**

The chat will run `mamey render-figures` and present the outputs.

---

### Asking about specific science

> **"What class is BGC044?"**  
> **"Is the polyene cluster split across contigs?"**  
> **"What proteins from BGC050 should I BLASTP first?"**  
> **"What does the halogenase on BGC044 do?"**

These work because the pipeline holds the triage context and mode B cards in memory for the session. You can ask follow-up questions without re-stating the strain or BGC.

---

### Triggering §21–§30 extensions

> **"Add the mass ladder for this RiPP BGC."** *(triggers §21)*  
> **"Write the experimental decision tree for BGC028."** *(triggers §30)*  
> **"I need the heterologous expression strategy."** *(triggers §23 when MATURATION_GAP is present)*  
> **"Give me the OSMAC protocol for [BGC]."** *(triggers §26)*  
> **"What are the five most important open questions about this cluster?"** *(triggers §30)*

---

### Getting a compiled report

> **"Write me the analysis report for [strain]."**  
> **"Compile everything into a single document."**  
> **"I need something I can share with my PI."**

The compiled Markdown report (`<strain>_Analysis_Report_<date>.md`) covers: executive summary, strain metadata, top leads, full triage board, Mode B cards, figures, BLASTP action list, fermentation guidance, and a candidate appendix for remaining BGCs.

---

### Workflow control

> **"Run in gold mode this time."** *(enables deep_data.json, gene-by-gene, automatic figures)*  
> **"Skip figures for now — just give me the triage."** *(brief=none)*  
> **"This is private data — mark it PRIVATE throughout."**  
> **"Flag this as an AS-series strain."** *(triggers PI-clearance guard)*

---

### The pattern that works

The pipeline is designed to understand what you need even when the phrasing is loose. A few principles that make requests work well:

**Name the BGC with its node.** "BGC028 (NODE_32 · region001)" is unambiguous; "the polyene cluster" depends on prior context. Both work in an ongoing session; the node citation works everywhere.

**State what you have.** "I have the Mamey package" or "I only have the antiSMASH ZIP" tells the chat which step to start from.

**Say what you want to do with the output.** "Something I can share with my PI" → layperson guide. "Something I can bring to lab meeting" → same. "Something for the bench" → fermentation card + wet lab matrix.

**You don't need to know the menu item number.** "Full plate," "everything," "complete analysis" all map to #7. The chat resolves the intent.
