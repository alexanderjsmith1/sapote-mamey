# Sapote–Mamey

**Claim-safe interpretive genome mining for actinomycete biosynthetic gene clusters (BGCs).**

*Current to bundle v9.7.401 · engine Mamey 1.9.143*

Sapote–Mamey turns antiSMASH output into auditable, claim-safe biosynthetic evidence packages and
interpretations. It is built in two layers, and the boundary between them is deliberate:

- **Mamey** — the executable BGC-analysis module. A deterministic Python engine that extracts and
  records source-derived measurements and evidence states: BGC inventory, boundary tiers, KCB
  triage, per-gene comparison evidence, and figures. Given the same admitted inputs and
  configuration it produces the same outputs, and defers biological judgment.
- **Sapote** — the governed post-extraction judgment workflow. It uses Mamey's sealed evidence
  packages to author gene-by-gene Mode B cards, ecological synthesis, and deliverables under hard
  claim-safety rules.

**Engine motto: deterministic extraction, judgment deferred.**

---

## Read in this order

| Start | Page | What it gives you |
|---|---|---|
| **1** | **[Quick Guide](Quick-Guide.md)** | Installation, the run command, key flags, the deliverable menu. Start here. |
| **2** | **[User Manual](User-Manual.md)** | The consolidated operating manual — install → running a strain → reading the output → configuration → engine internals. |
| **3** | **[Concepts Q&A](Concepts-Q-and-A.md)** | The "why does it work this way" companion, in plain language. |
| **4** | **[Encyclopedia](Encyclopedia.md)** | The deep reference — 13 volumes, engine internals through type-strain analyses. |
| — | **[Glossary](Glossary.md)** | The single canonical source for every term. The Manual and Encyclopedia point here rather than redefining. |
| — | **[Common Mistakes](Common-Mistakes.md)** | Wrong ZIP type, stale antiSMASH, missing dependencies. Read this first when something goes wrong. |

## Installing

| Page | Covers |
|---|---|
| **[Prerequisites](Prerequisites.md)** | Python-side dependencies, offline wheels, the bundle tiers. |
| **[External Tools & Databases](External-Tools-and-Databases.md)** | The external binaries and reference databases, with the version of record, run-defining parameters, and a version-matched citation for each — the reproducibility spine of the Methods. **These binaries are not shipped in the bundle**; that page has the conda recipes and the environment variables the drivers read. |

## Workflows

| Page | Covers |
|---|---|
| **[Phylogenetic Placement](Phylogenetic-Placement.md)** | Placing query sequences onto a fixed reference tree (MAFFT → RAxML-NG → EPA-ng → gappa), and how to read likelihood-weight ratios and pendant lengths. |

---

## Claim-safety — read this before interpreting any output

Every claim the pipeline makes is **capacity-level**. It reports "biosynthetic capacity consistent
with class X", never "produces compound Y".

- A KnownClusterBlast hit is **similarity, not identity**.
- Bioactivity metadata is optional **strain-level** context, never pinned to a single BGC without
  governed linkage.
- **Absence of recorded evidence is never read as biological absence.** Missing is not negative.
- Marker/16S phylogenetic placement indicates a **neighborhood, not a species assignment**.
- Expression is "unknown" without culture data.

Mamey is the factual floor; Sapote is the interpretive ceiling. The contract between them is what
keeps "what the data says" from blurring into "what we think it means".

---

## Licence

Code is MIT; documentation is CC-BY-4.0. See the repository `LICENSE` and `LICENSE-DOCS.txt`.
