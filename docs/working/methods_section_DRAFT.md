# Methods — Sapote–Mamey pipeline (DRAFT, against engine 1.9.96 / bundle v9.7.96)

> Working draft for the methods paper (target: *NAR Genomics & Bioinformatics* / *Bioinformatics*). Claude's natural voice; the Developer or User does the final formality pass. **Citation placeholders are marked `[CITE: …]` — verify metadata before use; none are invented DOIs.** Affiliation throughout: 

---

## 2. Materials and Methods

### 2.1 Overview and design rationale

Sapote–Mamey is a two-layer genome-mining pipeline that separates **deterministic measurement** from **interpretive judgment**, by design. The lower layer, **Mamey**, is a pure-Python engine that parses antiSMASH output `[CITE: antiSMASH 8.0.4, Blin et al.]` and emits a fixed inventory of biosynthetic gene clusters (BGCs) with their measured features; given identical input it produces byte-identical output, a property enforced by the test suite (see 2.7). The upper layer, **Sapote**, is a language-model judgment layer that reads only Mamey's structured evidence and applies a fixed set of claim-safety and interpretation rules. The separation is deliberate: every number in a Sapote verdict traces to a named field Mamey computed, so the interpretive layer can be audited against, and can never silently invent, the underlying measurement.

The pipeline was built to compare the biosynthetic *capacity* of actinomycetes isolated from pollinator (bee and wasp) microbiomes against bryophyte- and attine-ant-associated strains, and is deliberately conservative about what a genome alone can claim.

### 2.2 Claim-safety doctrine

A standing constraint governs every output: claims are **class-level and capacity-based**, never compound-identity or production claims. The pipeline reports that a locus carries "biosynthetic capacity consistent with" a chemotype, never that a strain "produces" a compound. Known-cluster-BLAST (KCB) hits are treated as **similarity signals, not identity** — a high KCB score against a characterized cluster indicates relatedness, not that the same product is made. Bioactivity is treated as **extract-level** (default axes: MRSA and *Candida*); activity is never pinned to a specific BGC absent fractionation, and absence of recorded activity is never reported as a negative phenotype, because the underlying bioassay data are non-standardized. Strains are contrasted by the **presence or absence of a biosynthetic mechanism**, not by phenotype.

### 2.3 The Mamey extraction engine

Mamey ingests an antiSMASH run and constructs a per-BGC record carrying, for each cluster, its product class prediction, boundary status, assembly context, and the results of a fixed scan battery.

**Boundary status and the corrected count.** Each BGC is classified by its position on the assembly: **Interior** (flanked by sufficient sequence on both sides; trusted), **Edge** (within a configurable flank of a contig end; possibly truncated), or **Full-contig** (the BGC spans the contig, so completeness is unknowable). Fragmentation inflates raw BGC counts, so the pipeline reports a **corrected BGC count** that down-weights uncertain clusters:

> corrected count = N(Interior) + ½·N(Edge) + ¼·N(Full-contig)

As of engine 1.9.85 (bundle v9.7.84), boundary status lowers *confidence* (an architecture grade) but no longer deducts from a BGC's activity score; the edge/full-contig score penalty was removed for lack of a measurement basis, and truncation is carried as a grade rather than a score change. The corrected-count weights above are separate and unchanged.

**Assembly tiers.** Strains are binned by interior-BGC fraction into GOOD (≥70%), MODERATE (≥45%), POOR (≥20%), and VERY_POOR (<20%), set authoritatively in `mamey/assembly.py`. Tier qualifies every downstream count and comparison.

**The scan battery.** Each BGC passes through a fixed set of deterministic scans, including: regulatory/resistance context scans; a bldA/TTA codon scan and a transcription-factor-binding-site (TFBS) scan, both of which are marked NOT_APPLICABLE automatically on non-actinomycetes (keyed on organism actino-status, so a GC-poor non-actinomycete cannot produce a spurious bldA tier); and a battery of class-compatibility triggers (the CCTT families) that flag diagnostic gene/motif content. A gene-adjacency rescue (RG-GMCI) recovers split or under-called clusters using fixed graph constants (gap/span/hub-degree). All scan thresholds are constants in the engine, not per-run tunables.

### 2.4 Compound-class annotation

A deterministic annotation layer (`compound_class.py`) records the chemotype a BGC's own evidence is consistent with — read from antiSMASH's own product-class prediction and the resolved MIBiG product line `[CITE: MIBiG, Terlouw et al.]`, using own-evidence only and never the raw KCB anchor's genome-description text. Each annotation carries a confidence grade (HIGH/MODERATE/LOW) and a cytotoxicity flag. Most chemotypes are annotation-only (recorded, no score effect); a small number of well-anchored families (e.g. polyene-macrolide → antifungal, ionophore → antibacterial, anthracycline → its own cytotoxic category) carry a scored consequence.

### 2.5 The Sapote scoring and judgment layer

Sapote scores each BGC on three axes — **antibacterial (AB)**, **antifungal (AF)**, and **novelty** — each composed as a base floor plus class-keyword credit plus a gated diagnostic bonus, modulated by a guard stack (primary-metabolism suppression, mobile-element and mis-anchor suppression, standing-rule downgrades, and a RiPP-fragment floor) and the RG-GMCI rescue. A BGC's lead tier is the maximum across axes. Keyword credit scores a BGC's **own** product classes only — not class tokens appearing in a KCB anchor's genome-description text, which describe the reference organism rather than the cluster (a fix introduced at engine 1.9.86 to remove keyword contamination from the anchor blob).

Several classes are **permanently down-weighted** as uninformative for the discovery axis under the project's standing rules: saccharides; NAPAA (excluded from comparative claims as convergent and habitat-non-specific); and the hglE-KS glycolipid domain / hexacosalactone (habitat-non-specific — structural novelty stands, but no habitat-exclusivity claim). Enediyne KCB hits carry a neutral claim-safety signal and a detection/veto path but no per-cluster biosafety flag.

### 2.6 Privacy-preserving release architecture

Because the cohort includes unpublished strains, the pipeline ships in four tiers cut by a single deterministic script: a private MERGED scaffold that retains real strain identifiers, and three public tiers (CODE, CODE-analysis-free, SID-public) from which private identifiers are scrubbed. The cut is **fail-closed**: it refuses to ship a public tier if any unpublished strain identifier survives, verified by (i) a tokenize-aware redactor with a public-name carve-out for compound names that collide with the identifier syntax, (ii) a leak audit that greps the staged tree (including test files, against a synthetic-ID allowlist), and (iii) a tier-derivation parity check confirming each public tier is an exact redaction-view of the private source. A version-sync gate refuses any tree whose version restatements have drifted from the single source of truth.

### 2.7 Determinism, verification, and reproducibility

Determinism is a verified property, not an aspiration: the test suite (~1,400 tests) holds byte-identical output for fixed input, pins scan constants and scoring composition, and enforces the privacy and version-sync invariants above. Because scoring constants change between some engine versions, scores are comparable only within a scoring-boundary span; cross-strain comparison requires all strains to be scored under one engine version. The bundle records, per release, the engine and bundle versions and the build provenance, so any reported figure can be traced to the exact engine that produced it.

### 2.8 Strain cohort and application

[Cohort paragraph — to merge with the existing biological-results draft: the Hymenoptera/bryophyte cohort composition (bee/wasp/moss), isolation and sequencing methods, and the comparison design. Pull exact strain counts and genus/host/location from `Master_Strain_List_v3`; use only its taxonomy/host/location fields, not its bioassay columns, per the extract-level bioactivity doctrine. `[CITE: cohort isolation/sequencing methods]`]

---

### Notes for the formality pass (not for the manuscript)
- **Verify before citing:** antiSMASH version + authors, MIBiG citation, any prior natural-product-mining tool comparisons. No DOIs are asserted here.
- **Numbers to lock at submission:** exact test count, current engine version, assembly-tier cut values (quoted as 70/45/20 — confirm against `mamey/assembly.py` at submission, since these are the authoritative figures and the older 66/50/33 set is retired).
- **A reviewer will ask** what Sapote (the LLM layer) does that a rules engine couldn't — worth a sentence in the discussion on where judgment genuinely adds value (claim-safety arbitration, split-pathway adjudication) vs where it's deterministic.
- **Comparison table** against existing genome-mining tools (antiSMASH, DeepBGC, GECCO, BiG-SCAPE) would strengthen 2.1 — different scope (they detect/cluster; Sapote–Mamey adjudicates capacity claim-safely), but reviewers will expect the positioning.
