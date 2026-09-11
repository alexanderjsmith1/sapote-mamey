# Spec — Cohesive Per-BGC Report (L0–L3) + Comparison Matrix

> **Naming / disambiguation (read first).** This file was renamed from `PER_BGC_REPORT_SPEC.md` to
> `PER_BGC_REPORT_CARD_SPEC.md` to remove a near-collision with the **existing, normative**
> `docs/PER_BGC_PAGE_LAYOUT_SPEC.md`. They are **two different documents with two different concerns**,
> not a rename of each other:
> - `docs/PER_BGC_PAGE_LAYOUT_SPEC.md` (existing, shipped, normative; referenced by
>   `DELIVERABLE_CONTRACT.md` §A2.5) governs **page rendering** — co-locating a BGC's locus map,
>   class line, and §1–§20 **Mode B** card on one page-unit. Its numbered "§1–§20" are *Mode B sections*
>   (§1 Architecture … §6 Bioactivity … §8 Wet-lab); **it has no build-order §6 / §6.1.**
> - **This** file governs the **content structure** of the per-BGC analysis — the L0–L3 report card. Its
>   §6 is the build order; §6.1 is the `mamey report-card` command that `report_card.py` implements.
> - **They are complementary:** when an L0–L3 card is compiled into a deliverable it must **respect the
>   page-layout co-location mandate** (A2.5) — layout governs *where* it renders, this spec governs *what*
>   it contains. Any citation of "§6.1" for `report-card` means **this** file, not the layout spec.
> - **Tree status:** this is a **new session artifact, not yet committed to the bundle tree** (0 refs).
>   `report_card.py` is correctly a next-cut feature built on the Patch-G CSVs from .196/.197.


**Status:** design spec (v0). **Purpose:** a single per-BGC artifact with progressive disclosure, so the same page serves a PI and a reviewer, and analyses stop "dropping off" into thin partial deliverables. **Does not replace** the layperson guide / Mode B / bench guide — it's the cohesive top layer that *binds* them and degrades gracefully (an un-authored BGC still gets L0–L1 from the engine; L2–L3 deepen as authored). Claim discipline is mandatory at every layer: capacity-level, KCB/BLASTp = similarity not identity, bioactivity extract-level, node·region on first mention, provenance tags.

## 1 · The four layers

| Layer | Audience | Contains | Mostly from |
|---|---|---|---|
| **L0 Headline** | PI / collaborator / layperson | one plain-language predicted-product line; 3 badges (Novelty, Predicted activity, Tractability); one action | engine (auto) |
| **L1 Molecule** | anyone | products/class; predicted polymer; predicted SMILES → formula + monoisotopic mass + [M+H]+ (or "pending"); features (D-residues, N-methyl, linear/cyclic); partial-assembly caveat | engine (auto) |
| **L2 Evidence** | bench scientist / reviewer | per-module substrate/extender calls (confidence); domain grammar; comparators (KCB, ClusterBlast, per-gene BLASTp) as **similarity**; over-merge flag | engine + authored |
| **L3 Provenance** | reviewer | store-backed vs reconstructed vs not-established; method/versions; **claim ceiling** | engine + authored |

**Progressive disclosure:** L0+L1 render for every BGC from the package with no authoring. L2 comparators and L3 judgement deepen as a BGC is worked. An un-worked BGC is honestly an L0–L1 card, not a fake "full" one — which is exactly the "analyses drop off" problem this fixes.

## 2 · Field → source map (implementable today from a v9.7.196 package)

| Field | Source file · column |
|---|---|
| locator (node·region), products, boundary, AB/AF/novelty, lead tier, KCB anchor+score | `{S}_4_triage_board.csv` |
| predicted polymer, SMILES, over_merge_flag, n_protoclusters, candidate_kind | `{S}_predicted_polymers.csv` (Patch G) |
| per-module substrate/extender + confidence, domain_class | `{S}_nrps_prediction.csv` (Patch G) |
| formula, monoisotopic mass, [M+H]+ | RDKit on the wildcard-free SMILES (add `rdkit` dep; skip when `[*]` present) |
| domain grammar (C/A/PCP/KS counts) | `domain_level/ordered_domain_architectures_by_bgc.csv` / aSDomain features |
| per-gene BLASTp reconciliation | live channel (`blastp-online`, once Patch B is fixed) → evidence store |
| ecology / capacity narrative (L2/L3 prose) | authored (Sapote) |

**Gap this exposes:** predicted mass needs RDKit (not currently a dep) and needs the SMILES wildcard-free; `X` positions block it → resolve `X` from the Stachelhaus best-calls already in `nrps_prediction.csv` before computing. Fragmented (Edge/Full-contig) clusters yield **partial** polymers → the mass is a fragment; L1 must say so (see the AS-XXX/AS-XXX cards).

## 3 · Badge rules (deterministic, from engine fields)

- **Novelty** = f(KCB strength, novelty score): `HIGH` if KCB NONE/weak (`KCB_score` low **and** no named-compound anchor) or novelty ≥ ~60; `LOW` if a strong KCB to a named compound (`KCB_score` high, e.g. nystatin 31637); `MODERATE` between (known family, moderate score). *This is the novelty spine — the organizing axis.*
- **Predicted activity** = f(AB/AF, KCB compound class), phrased "capacity consistent with": `HIGH antifungal` when AF high + polyene/known-antifungal KCB (AS-XXX); `moderate antibacterial` at mid AB; always extract-level, never per-BGC phenotype.
- **Tractability** = f(boundary, over_merge_flag, assembled-completeness): `HIGH` = Interior + not over-merged + polymer assembled; downgrade for Edge/Full-contig (truncated), over-merge (split first), or `X`-heavy/empty polymer. Feeds "what to do first" (split / finish / assay).

Thresholds are first-pass; calibrate against the cohort once the report runs strain-wide.

## 4 · Comparison matrix — which tool answers which question (grounded in the verified current state)

Two distinct questions; the pipeline is currently strong on the first, weak on the second (which is the discovery target).

| Tool | Question it answers | Axis | In-bundle status (verified) |
|---|---|---|---|
| **KnownClusterBlast (MIBiG)** | is it a *known* compound? | KNOWN | ✅ strong (91 refs) |
| **antiSMASH `cluster_compare` / RiQ** | second, quantitative known-cluster score | KNOWN | ⚠️ ingested (bounded-mode stream), **not surfaced** → wire as KCB cross-check |
| **NP Atlas (structure)** | is the *predicted structure* near a known NP? | KNOWN | ⚠️ present but **name-keyed only**; no RDKit/Tanimoto → add SMILES→Tanimoto (rdkit now available) |
| **BiG-SCAPE vs MIBiG** | which known family / GCF | KNOWN | ❌ external — integrate |
| **antiSMASH ClusterBlast (all-GenBank)** | similar to *uncharacterised* clusters in other genomes | NOVEL | ⚠️ ingested but used **only for RGGMCI** (57 refs, mostly `rggmci.py`) → surface as a novelty axis: "N hits to prediction-only clusters, 0 to MIBiG = conserved-but-cryptic" |
| **per-gene BLASTp → nr** | closest relatives + are they characterised? | NOVEL | ✅ works (this session: giant NRPS → uncharacterised *Nocardia*); systematize once Patch B fixed |
| **BiG-FAM / BiG-SLICE** | how novel vs *all sequenced* bacteria (GCF membership) | NOVEL | ❌ external — **highest-value integration**; quantifies novelty against the whole universe, not the MIBiG sliver |
| **ARTS** | is it likely bioactive *and* novel (resistance-guided) | NOVEL+activity | ❌ external — integrate; strong prioritiser |
| **BiG-SCAPE on cohort + refs** | cohort-conserved-but-MIBiG-absent families | NOVEL (cohort) | ❌ external — integrate for the cohort view |

**The join key across everything is the predicted structure (polymer/SMILES).** It connects: metabolomics (predicted mass → target LC-MS features → GNPS networking → link BGC to a detected mass), known chemistry (SMILES → Tanimoto vs NP Atlas), and the L0 headline. Build the comparison layer and L0–L3 populates itself.

## 5 · Holistic prioritisation (the report's spine)

One ranked surface fusing three axes the report already surfaces as badges:
`priority = novelty (KCB-dark / BiG-FAM-rare) × predicted activity (ARTS / AB-AF / KCB class) × tractability (boundary / over-merge / detectable mass)`.
The current triage board is KCB+heuristic; adding BiG-FAM novelty and ARTS resistance turns it into a discovery-prioritisation engine, and the Patch-G over-merge flag already feeds tractability.

## 6 · Build order (proposed)
1. **Now (no new deps but rdkit):** an engine command `mamey report-card --package … [--bgc …]` that renders L0–L1 for every BGC from the triage board + Patch-G CSVs, with RDKit mass on wildcard-free SMILES and the partial-assembly caveat on Edge/Full-contig. Resolve `X` from `nrps_prediction.csv` Stachelhaus best-calls before the SMILES mass step.
2. **Next cut:** surface `cluster_compare`/RiQ (KCB cross-check) and ClusterBlast-as-novelty from data already in the ZIP; add NP Atlas SMILES→Tanimoto.
3. **Integration projects:** BiG-FAM query, ARTS, cohort BiG-SCAPE, GNPS mass linkage — external, network/DB setup, sequenced by value (BiG-FAM first).

*Prototype demonstrating L0–L3 on real data across five strains: `L0_L3_CARD_PROTOTYPE.md`.*
