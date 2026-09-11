# The Sapote–Mamey Encyclopedia

> Read the [currency record](Encyclopedia-Currency.md) for checked settings and the limits of this historical reference.

The deep reference behind the [User Manual](User-Manual.md). Converted from the bundle's
`docs/GUIDE/03_Technical_Manual_Encyclopedia.html`; one page per volume.

| Volume | Title | Size |
|---|---|---|
| I | [Volume I — Foundations & Concepts](Encyclopedia-Volume-I.md) | 26 KB |
| II | [Volume II — The Mamey Engine (deterministic extraction)](Encyclopedia-Volume-II.md) | 31 KB |
| III | [Volume III — The Sapote Layer (judgment)](Encyclopedia-Volume-III.md) | 28 KB |
| IV | [Volume IV — Detection & Trigger Frameworks](Encyclopedia-Volume-IV.md) | 47 KB |
| V | [Volume V — Scoring, Ranking & DAPR](Encyclopedia-Volume-V.md) | 21 KB |
| VI | [Volume VI — Deliverables & Outputs](Encyclopedia-Volume-VI.md) | 35 KB |
| VII | [Volume VII — Operations, Release & Provenance](Encyclopedia-Volume-VII.md) | 21 KB |
| VIII | [Volume VIII — Reference & Apparatus](Encyclopedia-Volume-VIII.md) | 31 KB |
| IX | [Volume IX — Non-Actinomycete Genomes (Cross-Kingdom: Fungi · Cyanobacteria · Algae)](Encyclopedia-Volume-IX.md) | 28 KB |
| X | [Volume X — A Complete Genome: *Streptomyces spectabilis* ATCC 27465](Encyclopedia-Volume-X.md) | 20 KB |
| XI | [Volume XI — Both Layers Together: *Streptomyces* sp. M56](Encyclopedia-Volume-XI.md) | 14 KB |
| XII | [Volume XII — Type Strain Reference Analyses](Encyclopedia-Volume-XII.md) | 119 KB |
| XIII | [Volume XIII — Compound-class annotation and the cassette catalog (v9.7.86)](Encyclopedia-Volume-XIII.md) | 22 KB |

---

<div id="idx" class="section vol">

# The Sapote–Mamey Encyclopedia — Master Index

*A reference work for the Sapote–Mamey natural-product genome-mining pipeline.*
*Grounded against bundle v9.7.34 / engine Mamey 1.9.42; §IV.4 (RG-GMCI), §II.1 (cohort resolution), and §VI.4–VI.8
(lead boards, Mode B verdict layer, cross-strain merge) current to bundle v9.7.428 / engine Mamey 1.9.163,
Hamilton, Ontario, Canada · 2026-06-19*

*Version & patch state — see the [Patch Notes](#patch-notes) at the end of this document.*

------------------------------------------------------------------------

## What this is

The Operating Manual tells you *how to run* Sapote–Mamey. This Encyclopedia tells you *what every part is, why
it exists, and how it relates to the rest* — the conceptual foundations, the scientific domain, the engine
internals, the judgment doctrine, the deliverables, the operations, and the reference apparatus, as one
cross-referenced whole. It is written to be read in pieces and consulted by entry, not read front to back.

It is built **volume by volume, chapter by chapter**. Each volume is a standalone file; chapters are numbered
within their volume (e.g. **§I.3** = Volume I, Chapter 3). This index is the spine: it holds the full map, the
editorial conventions, and the build status.

## How to read it

- **Foundations first.** Volume I is the worldview — the two-layer contract and the claim-safety doctrine that
  govern everything else. Read it before the technical volumes or they will read as arbitrary.
- **Then by need.** Volumes II–VIII are reference; jump to the entry you need. Cross-references are written as
  "→ §IV.2".
- **Claim-safety is load-bearing, not decorative.** Wherever the text describes what a strain *has*, it means
  biosynthetic capacity, never production. This is doctrine (→ §I.3), applied throughout.

## Editorial conventions

1.  **Numbering.** `§<Volume>.<Chapter>` for chapters; `§<Volume>.<Chapter>.<n>` for sub-sections.
2.  **Evidence tags.** Where it matters, a claim about engine behavior is tagged: <span class="tag t-engine">\[engine\]</span> = verified
    against the running code/artifacts of this edition; <span class="tag t-concept">\[concept\]</span> = conceptual framing or rationale;
    <span class="tag t-science">\[science\]</span> = a claim about the biology/chemistry, held to the literature. This mirrors the project's own
    observed/computed/inferred/assumed discipline.
3.  **Claim-safe language.** Capacity-level only; KCB = similarity not identity; bioactivity is extract-level;
    every BGC is named with its node/contig. (→ §I.3)
4.  **Release discipline.** No unpublished strain identifier (AS/AJS/PENDING) appears in this work except as
    an anonymized example. Named genomes / NCBI accessions may appear. (→ §I.7, §VII.4)
5.  **Currency.** Each volume stamps the edition (bundle/engine) it was written against. When the engine moves,
    a volume is revised, not silently left stale.
6.  **Affiliation.** Always

------------------------------------------------------------------------

## The volumes

### Volume I — Foundations & Concepts · **\[BUILT\]**

The worldview. What the pipeline is, the two-layer contract, the claim-safety doctrine, the scientific domain,
the unit of work and the corrected count, the standing exclusions, and the public/private embargo.
Chapters I.1–I.7.

### Volume II — The Mamey Engine (deterministic extraction) · **\[BUILT\]**

Ingest and the schema gate; the ten First-Pass Scans; evidence channels; boundary status and assembly tiers;
the FLBR megasynthase census; the output package and its validation. Chapters II.1–II.8.

### Volume III — The Sapote Layer (judgment) · **\[BUILT\]**

The judgment contract; Mode B §1–§8 anatomy; the scoring and triage model; the lead-tier ladder
(Exceptional / High / Medium / Inventory); architecture confidence A–E; the hallucination-trap audit.
Chapters III.1–III.7.

### Volume IV — Detection & Trigger Frameworks · **\[BUILT\]**

The CCTT T43 trigger framework and its eighteen families (AMC, BLA, BLT, DKP, ENE, GPA, HAL, IDC, LAN, LASSO, NN, NUC, PYE,
PHO, PTM, TET, THA, XHAL — with TOMM/LMPKS/SILENT noted as related non-trigger signals); KnownClusterBlast and
ClusterBlast; RG-GMCI cross-contig integration; CGAD, UMED, EFLS;
the resistance screen and its HGT guard; bldA/TTA tiering; TFBS. Chapters IV.1–IV.10.

### Volume V — Scoring, Ranking & DAPR · **\[BUILT\]**

The AB/AF/novelty model; diagnostic floors and corroboration; the primary-metabolism and mis-anchor guards;
the standing-rule downgrades in scoring; DAPR dual antibacterial/antifungal prioritization; the rationale
renderer. Chapters V.1–V.7.

### Volume VI — Deliverables & Outputs · **\[BUILT\]**

The deliverable contract; the strain brief and the extraction-complete/judgment-pending banner; the figure
system and its data-only CSV discipline; Mode B reports; DAPR tables; the layperson's guide; the synopsis and
chapter; the fermentation/bench card; the cross-comparative synthesis. Chapters VI.1–VI.9.

### Volume VII — Operations, Release & Provenance · **\[BUILT\]**

Running the pipeline; modes (smoke/standard/gold) and evidence levels (off/bounded/full); the four release
tiers; the release-and-leak hard guard; cutting and per-tier verification; checksums and provenance; the
standardized chat-handoff format. Chapters VII.1–VII.9.

### Volume VIII — Reference & Apparatus · **\[BUILT\]**

The science glossary; the marker catalog and the registry-as-SSOT model; the standing-rules registry; the
known traps; the version history; literature and citation conventions. Chapters VIII.1–VIII.6.

### Volume IX — Non-Actinomycete Genomes (Cross-Kingdom: Fungi · Cyanobacteria · Algae) · **\[BUILT\]**

The first fungal antiSMASH run through a bacteria-built pipeline (public worked genome *Capronia epimyces*,
GCF_000585565): what transferred (the structural layer), what went blind (the bacterial CCTT triggers), what
inverted (the CGAD chitinase claim-safety hazard), the gene-by-gene Sapote recovery, the one trigger that
transferred (phosphonate/PEP-mutase), and the fungal-support patch roadmap (P-F1–P-F6). Chapters IX.1–IX.6.

------------------------------------------------------------------------

## Build status

| Vol | Title | Chapters | Status |
|----|----|----|----|
| I | Foundations & Concepts | 7 | **BUILT** (this edition) |
| II | The Mamey Engine | 8 | **BUILT** (this edition) |
| III | The Sapote Layer | 7 | **BUILT** (this edition) |
| IV | Detection & Trigger Frameworks | 10 | **BUILT** (this edition) |
| V | Scoring, Ranking & DAPR | 7 | **BUILT** (this edition) |
| VI | Deliverables & Outputs | 9 | **BUILT** (this edition) |
| VII | Operations, Release & Provenance | 8 | **BUILT** (this edition) |
| VIII | Reference & Apparatus | 6 | **BUILT** (this edition) |
| IX | Non-actinomycete cross-kingdom genomes (fungi · cyanobacteria · algae) | 6 | **BUILT** (this edition) |
| XII | Type Strain Reference Analyses (*S. spectabilis*, *S. liangshanensis*) | 2 | **BUILT** (v9.7.81) |

Volumes are added one per pass. Each is grounded in the running engine of its edition, not written from memory;
where a chapter states engine behavior it is checked against the code or a real run before it ships.

</div>

<div id="vol1" class="section vol">

# The Sapote–Mamey Encyclopedia
