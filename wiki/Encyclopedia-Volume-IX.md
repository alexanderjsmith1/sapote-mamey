# Volume IX — Non-Actinomycete Genomes (Cross-Kingdom: Fungi · Cyanobacteria · Algae)

> **Currency scope:** This volume retains its historical edition and review stamps. Only the checks listed in the [currency record](Encyclopedia-Currency.md) have been refreshed for the current candidate. Other constants, numerical claims, literature interpretations, and worked-run results have not been comprehensively revalidated. A newer bundle does not make those older observations current.

*Edition: bundle v9.7.33 / engine Mamey 1.9.41 · re-grounded and restructured to bundle v9.7.91 / engine Mamey 1.9.91 on 2026-06-20*
*What happens when a pipeline built end-to-end for actinomycete bacteria is pointed at organisms outside that target kingdom — what transfers, what goes blind, what inverts, and how the engine gates its actinomycete-specific machinery. Organised in three parts: **A — Fungi** (ascomycetes, basidiomycetes), **B — Cyanobacteria**, **C — Algae**. Worked fungal genomes: the black yeasts* Capronia epimyces *CBS 606.96 (*GCF_000585565*) and* Cladophialophora yegresii *CBS 114405 (*GCF_000585515*) — both PUBLIC references, named directly.*

------------------------------------------------------------------------

## §IX.0 · Scope — non-actinomycete cross-kingdom sources

Sapote–Mamey targets one group: **actinomycete bacteria**. This volume collects runs on organisms *outside* that target — the famous non-actinomycete natural-product sources: **fungi** and **algae** (eukaryotes) and **cyanobacteria** (a distinct, prolific-NP bacterial phylum). "Non-bacterial" is a loose shorthand — cyanobacteria are bacteria — so the precise organising principle is *non-actinomycete cross-kingdom sources*. Routine non-actinomycete *bacteria* from the bee/insect cohort (rhizobia, firmicutes, proteobacterial endosymbionts — e.g. *Mesorhizobium*, *Melissococcus*) are not collected here; they are handled by the `cohort_resolver` NON-ACTINOMYCETE guard at intake (→ §II.1). <span class="tag t-concept">\[concept\]</span>

**The thread across all three parts:** the engine's *deterministic, organism-agnostic* layer (ingest, BGC inventory, boundary status, the corrected-count formula, assembly tiering, KCB/MIBiG anchoring, packaging) transfers across kingdoms unchanged, while the *actinomycete-calibrated interpretation* layer (the CCTT bacterial trigger families, the bldA/TTA developmental scan, bacterial TFBS motifs, the CGAD chitinase-as-antifungal coupling, the DAPR AB/AF scoring) goes silent — or, in one case, inverts. The claim-safety ceiling for a non-actinomycete result is therefore **higher** than for an actinomycete: the inventory is trustworthy, the actino-calibrated scores are not, and this volume is explicit about which is which. <span class="tag t-concept">\[concept\]</span>

------------------------------------------------------------------------

## Part A — Fungi

*Worked: two Chaetothyriales black yeasts (ascomycetes). Basidiomycetes: placeholder for future runs (§IX.7).*

### A · Ascomycetes

## §IX.1 · First cross-kingdom run — Capronia epimyces (ascomycete)

Sapote–Mamey was designed for one kingdom: **actinomycete bacteria**. Every assumption in the judgment layer —
the CCTT trigger families, the bldA/TTA developmental scan, the chitinase-as-antifungal coupling — encodes
*bacterial* natural-product biology. Volume IX documents what happened the first time that machinery was pointed
at a **fungus**, and it is included for two reasons: it is an honest record of where the bacterial assumptions
help, go quiet, or mislead; and it is the design basis for the fungal-support work (§IX.6). <span class="tag t-concept">\[concept\]</span>

The worked genome is *Capronia epimyces* CBS 606.96, a **black yeast** (order Chaetothyriales), downloaded from a
public database under accession **GCF_000585565** and already processed by **antiSMASH in fungal mode** (its output
records `taxon: fungi`). Because the genome is a public reference, it is named directly here — Volume IX needs no
PRIVATE worked-examples key (contrast §I.7). **\[observed\]**

The headline result is that **the pipeline did not crash**: ingest, BGC counting, the corrected-count formula,
assembly tiering, KCB/MIBiG anchoring, and packaging all ran and produced sensible fungal output. The
deterministic engine extracted **25 BGCs**, corrected **24.5**, assembly **GOOD** (96% Interior). That a
bacteria-built engine read a fungal genome cleanly is the first finding: the **structural layer is
taxon-agnostic**. The interpretation layer is where the kingdom assumptions surface — and that is the rest of this
volume. **\[observed/computed\]**

## §IX.2 · What transferred and what did not

The clean way to read the pilot is by layer. The structural/geometric layer carries across kingdoms because it
asks questions ("how big is this region, how much of its contig does it span, how many regions are there") that do
not depend on the organism being a bacterium. The interpretation layer does not, because it asks "what *class* of
bacterial chemistry is this" — a question with bacterial assumptions built in. **\[inferred\]**

| Layer | Component | Cross-kingdom behavior on the fungus |
|----|----|----|
| **Structural (transfers)** | BGC parse / count | 25 BGCs parsed cleanly **\[observed\]** |
|  | Corrected-count formula (Interior + ½·Edge + ¼·Full-contig) | 24.5 — biology-neutral arithmetic, worked exactly **\[computed\]** |
|  | Assembly tiering | GOOD (96% Interior) — a genome-quality read, kingdom-independent **\[computed\]** |
|  | KCB / MIBiG anchoring | Resolved **real fungal references** (1,3,6,8-tetrahydroxynaphthalene → DHN-melanin; aspterric acid; notoamide; cryptosporioptide) — similarity works across kingdoms **\[observed\]** |
|  | Packaging / checksums | Sealed package emitted normally **\[observed\]** |
| **Interpretation (does not transfer)** | CCTT T43 triggers | Fired on **1 of 25** BGCs (T43-PHO only) — the bacterial signatures (lanthipeptide, lasso, thiopeptide…) are not how fungi build chemistry; the detectors are effectively **blind to fungal biosynthesis** **\[observed\]** |
|  | Lead tiers | **2 Medium / 23 Inventory** — almost everything under-called, because the diagnostic layer stayed silent **\[computed\]** |
|  | bldA/TTA scan | 521 rows — **meaningless**: bldA/TTA is an actinomycete developmental system; fungi have no bldA **\[observed → science\]** |
|  | TFBS (bacterial regulator motifs) | 310 rows — **meaningless**: fungal gene control is different **\[observed → science\]** |
|  | CGAD chitinase | 18 rows — **inverts** (the claim-safety hazard, → §IX.3) **\[observed → science\]** |

The root cause is one unread label: antiSMASH wrote `taxon: fungi` into its output, but the engine kept only the
user-supplied `--taxonomy` string and never read the kingdom flag, so it applied bacterial rules without ever
knowing — or asking — whether the organism was bacterial. Every interpretation-layer failure below traces to that
single unread field (→ the foundation patch P-F1, §IX.6). **\[observed: parsers.py / cli.py have no taxon branch\]**

## §IX.3 · The chitinase inversion — the claim-safety hazard

One interpretation failure is not a quiet miss but an **active inversion**, and it is the single most important
claim-safety point for fungal runs. <span class="tag t-science">\[science\]</span>

In a *bacterial* genome, the deterministic CGAD scan reads chitin-active machinery (GH18/GH19 chitinases, AA10
LPMOs, chitin-binding modules) as an **antifungal mechanism** — chitin is the fungal cell wall, so a *bacterium*
carrying chitinases is plausibly arming against fungi (→ §IV.5). **For a fungus, chitin is its own cell wall.**
The same GH18 genes are then **housekeeping** — hyphal growth, septation, cell-wall remodeling, autolysis — not
antifungal weapons. The bacterial interpretation therefore reads exactly backwards: what the bacterial frame
scores as "antifungal capacity" is, in a fungus, the organism's own structural cell-wall biology. *Capronia*'s
genome carries 4 chitinase / 14 chitin-related genes genome-wide; left uncorrected, a fungal report could imply
antifungal weaponry from self cell-wall genes. **\[observed genome counts; inferred interpretation\]**

This is grounded in the fungal cell-biology literature: fungi carry high numbers of GH18 chitinases, and the
structural scaffold of the fungal cell is chitin and β-(1,3)-glucan, with the chitinases serving cell-wall and
autolysis roles (Hartl, Zach & Seidl-Seiboth 2012, *Appl Microbiol Biotechnol* 93:533–543, DOI
10.1007/s00253-011-3723-3, open access). That account of fungal chitinases as cell-wall machinery is the direct
basis for treating *Capronia*'s chitinases as self cell-wall biology, not antifungal capacity. <span class="tag t-science">\[science\]</span>

The engineering consequence: the CGAD-as-antifungal coupling must be switched **off** for fungi — the channel
relabelled "cell-wall chitin metabolism (self) — not an antifungal signal" and contributing zero antifungal score
(→ P-F3, the priority claim-safety fix, §IX.6). Note this is distinct from the T43-NUC coupling (nikkomycin /
polyoxin are chitin-synthase *inhibitors* — a genuine antifungal mechanism that may stay); the inversion is
specific to CGAD reading self chitinases as a weapon. **\[inferred\]**

## §IX.4 · Gene-by-gene recovery (the Sapote hand-pass)

Because the bacterial trigger layer under-called 23 of 25 BGCs, the genome's real chemistry was recovered by a
**manual gene-level Sapote pass** — reading the antiSMASH region GBKs directly to recover what the bacterial
triggers missed. Three clusters illustrate the pattern; all claim-safe (capacity not production; KCB = similarity;
domain evidence \[observed\] from the region GBK, class calls \[inferred\]). <span class="tag t-science">\[science/inferred\]</span>

**BGC003 — DHN-melanin, the black-yeast flagship.** `NW_006912904.1 | region003 | Interior | 66.6 kb`, Arch A.
The core gene carries the canonical **non-reducing iterative fungal PKS** domain string
SAT → itr_KS → AT → PT → ACP → TE \[observed\]: a starter-unit acyl transferase primes the chain, the iterative
KS/AT/ACP extend it, and the product-template domain folds the aromatic ring. The `itr_KS` (iterative) tag is the
fungal-vs-bacterial tell — fungal PKSs reuse one module iteratively, unlike bacterial modular assembly lines. KCB
anchors the region to **1,3,6,8-tetrahydroxynaphthalene** (T4HN, cumulative 1,821), the committed precursor of
**DHN-melanin**, and the region carries **scytalone dehydratase (×2)** and naphthol reductases — the diagnostic
DHN tailoring set (T4HN → scytalone → 1,3,8-THN → vermelone → 1,8-DHN → melanin). DHN-melanin is the **defining
pigment of black yeasts** and a documented stress/virulence factor in Chaetothyriales — so the genome's most
characteristic chemistry sits in a cluster the bacterial CCTT layer did **not** flag (it fell to Inventory). The
gene-level verdict: capacity **consistent with DHN-melanin**; the engine's Inventory tier is a false under-call
driven by the bacterial-trigger gap, not by the evidence. **\[observed domains; inferred class\]**

**BGC011 — fungal sesquiterpene (TRI5-class).** `NW_006912905.1 | region002 | Interior | 31.2 kb`. Carries
**trichodiene synthase (TRI5)**, a type-I terpene cyclase, with two cytochrome-P450 tailoring enzymes \[observed\];
KCB resolves toward the fungal sesquiterpenoid aspterric acid (2,575). The TRI5 core + P450 oxidative tailoring is
the standard fungal sesquiterpene layout. Capacity **consistent with a P450-tailored fungal sesquiterpene** —
again invisible to the bacterial triggers (there is no CCTT terpene-cyclase family). **\[observed; inferred\]**

**BGC023 — phosphonate (the one trigger that transferred).** `NW_006912912.1 | region001 | Interior | 61.0 kb`.
Covered in §IX.5 — the single CCTT firing, and a correct one.

| BGC | node \| region \| boundary | Capacity (claim-safe) | Engine tier | Gene-level verdict |
|----|----|----|----|----|
| BGC003 | NW_006912904.1 \| r003 \| Interior | DHN-melanin (NR-PKS → T4HN + scytalone dehydratase) | Inventory | **Flagship** — under-called |
| BGC023 | NW_006912912.1 \| r001 \| Interior | Phosphonate (PEP-mutase) | Medium | Real; the only correct CCTT firing |
| BGC011 | NW_006912905.1 \| r002 \| Interior | Fungal sesquiterpene (TRI5 + P450) | Inventory | Real — under-called |

The pattern is consistent: the genome's genuine fungal chemistry is **present and readable at the gene level**,
but the bacterial CCTT layer recognizes almost none of it, so the automated tiers under-call. The gene-by-gene
Sapote pass is what recovers it — and the judgment layer's claim-safety discipline (capacity, similarity,
node-tagged BGCs) holds identically across kingdoms even when the trigger layer does not. **\[inferred\]**

## §IX.5 · The one trigger that transferred — phosphonate / PEP-mutase

Of 25 fungal BGCs, exactly **one** CCTT trigger fired: **T43-PHO** on BGC023, and it fired **correctly**. The
region carries **PEP-mutase** (phosphoenolpyruvate phosphomutase, annotated as both a domain and a CDS product)
plus a phosphonate hydrolase and a 2-hydroxyacid dehydrogenase \[observed\]. PEP-mutase is the **committed,
irreversible first step of phosphonate (C–P-bond) biosynthesis** — the same diagnostic enzyme in both kingdoms.
Capacity **consistent with a phosphonate natural product**; fungal phosphonate biosynthesis is comparatively rare,
so this is a noteworthy cluster. **\[observed; inferred\]**

The cross-kingdom lesson is sharp and useful for the patch design: **kingdom-neutral triggers — those keyed on a
universal committed enzyme — survive the bacterial→fungal jump; kingdom-specific ones do not.** T43-PHO keys on
PEP-mutase, an enzyme that means the same thing in bacteria and fungi, so it transferred. T43-LAN, T43-LASSO,
T43-THA and the rest key on bacterial RiPP/peptide machinery fungi do not use, so they stayed silent. This is the
principle behind adding a *fungal* trigger subset (§IX.6, P-F4) rather than trying to retrofit the bacterial ones:
the fix is new kingdom-specific detectors, plus recognition that the committed-enzyme triggers are already
portable. **\[inferred\]**

## §IX.5b · Second ascomycete — Cladophialophora yegresii (the black-yeast pattern, reproduced)

A second Chaetothyriales black yeast, *Cladophialophora yegresii* CBS 114405 (**GCF_000585515**, PUBLIC), was run through the v9.7.91 engine to test whether the *Capronia* pattern reproduces on an independent fungal genome. It does. Genome **27.9 Mbp across 8 contigs**; the deterministic engine extracted **13 BGCs, all Interior** (13 / 0 / 0), corrected **13.0**, **100% Interior → GOOD**. The structural layer again carried across cleanly, and the intake correctly ignored the `__MACOSX` resource-fork files in the zip (parsing the 13 real region GBKs, not the doubled file count). **\[observed/computed\]**

The product spread is characteristically fungal — terpene-rich (6 terpene + 2 terpene-precursor), with NRPS/NRPS-like (×7), PKS/T1PKS/T3PKS (×6), and one NRP-metallophore — and the KCB anchors resolve to **real fungal references** (similarity, not identity, → §I.3). Notable regions, each node-tagged: <span class="tag t-science">\[observed anchors; inferred class\]</span>

| BGC | node \| region \| boundary | antiSMASH class | KCB anchor (similarity) | Capacity (claim-safe) |
|----|----|----|----|----|
| BGC006 | NW_006913047.1 \| region003 \| Interior | PKS / T1PKS | 1,3,6,8-tetrahydroxynaphthalene (T4HN) | **consistent with DHN-melanin** — the black-yeast flagship, the same chemistry as *Capronia* BGC003 |
| BGC002 | NW_006913045.1 \| region002 \| Interior | terpene | squalestatin S1 | consistent with a squalestatin-class meroterpenoid |
| BGC003 | NW_006913046.1 \| region001 \| Interior | PKS / T1PKS | neosartorin | consistent with an NR-PKS aromatic polyketide |
| BGC007 | NW_006913047.1 \| region004 \| Interior | terpene | clavaric acid | consistent with a triterpenoid |
| BGC010 | NW_006913049.1 \| region002 \| Interior | NRP-metallophore / NRPS | — | consistent with a fungal siderophore (NRPS-type) |

The headline is the cross-genome confirmation: **both** black yeasts KCB-anchor T4HN (the committed DHN-melanin precursor) on an interior PKS region — *Capronia* at BGC003, *Cladophialophora* at BGC006 \| NW_006913047.1 \| region003 — so the genome's most characteristic chemistry (the defining black-yeast pigment) is present and readable at the inventory level in both. As with *Capronia*, the bacterial CCTT layer recognises almost none of this fungal chemistry, so the automated lead tiers under-call; the inventory and KCB anchors, which are organism-agnostic, are what carry the signal. **\[observed; inferred\]**

## §IX.5c · Taxonomy gating at v9.7.91 — the per-BGC bldA defect, surfaced

The pilot's root cause (§IX.2 — an unread kingdom flag) has been *partly* addressed since, and these two runs show exactly how far. The engine now resolves an `actino_status` for each organism (`cohort_resolver.actino_status`): a genus in the `NON_ACTINO_GENERA` denylist → `non_actinomycete`; a genus in `ACTINO_GENERA` → `actinomycete`; anything else → `unknown`. The bldA/TTA scan reads that status and, on a confirmed non-actinomycete, reports `NOT_APPLICABLE` rather than a tier (v9.7.86 P-9 / v9.7.87 P-11). <span class="tag t-engine">\[engine\]</span>

**The gap these fungi expose.** The denylist is curated, not derived. It now lists many fungal genera and kingdom tokens (`fungi`, `eukaryota`, …, added in P-9/P-11), but **not** *Cladophialophora*, *Capronia*, or *Mesorhizobium*. Run with their real species names, all three resolve to `unknown` — which is a *review* tag, not `non_actinomycete` — so the actinomycete-specific machinery runs anyway. The concrete damage is visible in the inventory: *Cladophialophora*'s per-BGC `TTA_tier` reads **`T4` on all 13 fungal BGCs**, and the `bldA_TTA` scan reports `PASS` — the engine computing a *Streptomyces* developmental-regulation signal on a fungus that has no bldA system at all. **\[observed in `2_inventory.csv` / `3_scan_states.json`\]**

**The intended path works — when the kingdom is declared.** Re-running *Cladophialophora* with `--taxonomy "Fungi sp."` (hitting the P-11 kingdom token) produced an **organism-agnostic invariance check**: the inventory was byte-identical (13 BGCs, identical boundaries — taxonomy does not touch extraction), while `bldA_TTA` flipped `PASS → NOT_APPLICABLE` and the `*** NON-ACTINOMYCETE` intake flag fired. That cleanly separates the two layers: declaring the kingdom correctly gates the actino-specific interpretation without perturbing a single deterministic number. **\[observed — validated re-run\]**

Two residual defects worth a patch: (1) the denylist misses these genera, so a species-name run still mis-applies the actino scans; and (2) `unknown` was **not** surfaced in the fungi's `issue_log` (zero mentions) even though the v9.7.81 code comment says callers should surface it loudly. The list is unreliable in *both* directions: the same twelve-strain sweep marked a genuine actinomycete, *Saccharothrix espanaensis* (a well-known *Pseudonocardiaceae* producer), as `unknown` because its genus is absent from the *allow*list — so the genus-list approach can both run actino scans on a fungus and fail to recognise a real actinomycete. Note this is not a *resource* problem — a Mamey run is ≤1 minute, so the wasted actino scans cost nothing — it is a *data-interpretation* problem: the spurious `T4` tiers and bldA rows sit in the inventory waiting to mislead an analyst. The durable fix is the one §IX.6 already names (P-F1): read the kingdom from the antiSMASH GBK source-organism lineage — which records `taxon: fungi` directly — instead of matching against a hand-maintained genus list. Until then, the operator rule is simple: **for any non-actinomycete run, declare a kingdom token in `--taxonomy`** so the actino-specific scans gate to `NOT_APPLICABLE`. <span class="tag t-spec">\[spec/inferred\]</span>

## §IX.5d · Inferring kingdom from KCB consensus — a user-facing cross-check

If a hand-maintained genus list is unreliable, is there a signal already in the run that points at an organism's taxonomy? There is — in the **KnownClusterBlast anchors** — and a twelve-strain cross-kingdom sweep (the runs of this volume plus reference actinomycetes and non-actinomycete bacteria) shows both its power and its limits. The principle: a BGC that KCB-matches a characterised MIBiG cluster inherits a hint of that reference's *producer*, and across many BGCs those hints can form a **consensus**. The discipline is the same as everywhere else — a single hit is similarity, not identity (→ §I.3), so the assessment must rest on agreement across many BGCs, never one. <span class="tag t-concept">\[concept\]</span>

| Group (strains) | KCB anchor consensus | Taxonomic read |
|----|----|----|
| **Fungi** — *Capronia*, *Cladophialophora* | Named anchors overwhelmingly fungal: T4HN/DHN-melanin, notoamide, aspterric acid, squalestatin, neosartorin, metachelin, cryptosporioptide | **Fungal — confident** (well-represented in MIBiG) |
| **Actinomycetes** — *Nocardia*, *Actinomadura*, *S. drozdowiczii*, *Saccharothrix*, AJS327 | Named anchors overwhelmingly actinomycete: lipstatin, leinamycin, griseusin, coelichelin, kedarcidin, thiocoraline, nocathiacin, lankacidin, desertomycin, erythromycin, asukamycin, desferrioxamine | **Actinomycete — confident**; notably this correctly calls *Saccharothrix*, which the genus *allow*list missed (§IX.5c) |
| **Under-represented phyla** — *Trebouxia* (alga), *Gemmata* (Planctomycete), *Deinococcus* | Almost no named anchors — mostly generic `Type:` labels; a few phylum-specific hits (clipibicyclene/azabicyclene in the Planctomycete) | **Inconclusive** — KCB is blind where the phylum's chemistry is not in the reference set |
| **Crossover risk** — *Mesorhizobium*, *Melissococcus* | Mixed: a *Streptomyces*-product hit (kanamycin) *and* a proteobacterial acyl-homoserine-lactone signal in *Mesorhizobium*; a *Paenibacillus* product (fusaricidin) in *Melissococcus* | **Use consensus, not single hits** — exactly the failure mode of trusting one anchor |

Two lessons land. First, **where a clade is well-represented in MIBiG, KCB consensus is a strong, independent taxonomic signal** — strong enough to correct the genus list (it places *Saccharothrix* with the actinomycetes the allowlist could not). Second, it **degrades honestly**: for an alga or a Planctomycete it returns generic types and simply cannot call the taxonomy, rather than calling it wrongly. And the crossover cases are the concrete form of the standing caution — *Streptomyces*/*Bacillus* BGC overlap, or HSAF being made by both *Lysobacter* (a gammaproteobacterium) and actinomycetes — so a confident read needs several BGCs agreeing, never a lone hit. **\[observed across 12 runs; inferred\]**

The practical framing: this is a **user-facing analytical cross-check** (a Sapote-layer judgment), not a Mamey requirement — the deterministic run completes identically regardless, and the check would consume the existing KCB output rather than changing it. Its best use is as a *second source* alongside the GBK-lineage kingdom read (P-F1): when the declared taxonomy, the GBK lineage, and the KCB consensus agree, a taxonomic assessment is well-supported; when they disagree — a declared *Streptomyces* whose anchors are all fungal, say — that disagreement is exactly the mislabel the cross-check exists to catch. <span class="tag t-spec">\[spec/inferred\]</span>

### B · Basidiomycetes

*Placeholder — no basidiomycete genome has been run through the pipeline yet. The expectation from first principles: the same organism-agnostic transfer (inventory, boundary, corrected count, KCB) with the same actino-interpretation silence, plus basidiomycete-specific chemistry (e.g. terpenoid-rich repertoires, sesquiterpene synthases) that the bacterial CCTT layer will not recognise. Real worked examples to be added when runs are deposited (Zenodo).* <span class="tag t-spec">\[spec\]</span>

## §IX.6 · The fungal-support patch roadmap

The pilot produced a six-item patch spec to make fungal runs trustworthy. Since then, parts have partly shipped — the bldA/TTA gate now reports `NOT_APPLICABLE` on a recognised non-actinomycete (P-F2, via `actino_status`; P-9/P-11), though the durable taxon-from-GBK foundation (P-F1) and the genus-recognition gap of §IX.5c remain open. It is recorded here as the volume's
forward pointer; the work itself belongs to a dedicated fungal patch effort, **gated so every change leaves
bacterial runs byte-identical** (re-run a public actinomycete, diff manifest + triage board). <span class="tag t-spec">\[spec\]</span>

| Patch | What | Priority |
|----|----|----|
| **P-F1** | Read the antiSMASH `taxon` flag; set a run-level `kingdom ∈ {bacteria, fungi}` (default bacteria, fail-safe), record it in the manifest, thread it into the scan pack and brief; accept a `--kingdom` override | **Foundation — first** |
| **P-F3** | Fix the CGAD chitinase inversion: for `kingdom == fungi`, do not route CGAD into the antifungal reading; relabel "cell-wall chitin metabolism (self)"; zero antifungal contribution | **Priority — claim-safety** |
| **P-F2** | Gate the actinomycete-only scans (bldA/TTA, bacterial TFBS) behind `kingdom == bacteria`; for fungi emit the sheet with an "N/A — actinomycete-specific" stamp so package shape is constant | Correctness |
| **P-F4** | Add a fungal CCTT subset (active when `kingdom == fungi`): T43F-DHN (scytalone dehydratase + THN reductase), T43F-DMATS (indole prenyltransferase), T43F-ISO (isocyanide synthase), T43F-TRI (trichodiene synthase), T43F-AFLA (versicolorin/norsolorinic-acid), T43F-SID (fungal siderophore NRPS) | Coverage — the under-calling fix |
| **P-F5** | Behind the kingdom switch, add fungal-appropriate AB/AF weights and a fungal diagnostic subset; keep all claim-safety invariants identical | Coverage |
| **P-F6** | Brief & deliverables stamp the kingdom and the applicability caveats ("FUNGAL RUN — actinomycete-specific scans not applicable; CGAD reported as self cell-wall, not antifungal") | Honesty |

Suggested order: **P-F1 → P-F3 → P-F2 → P-F4 → P-F5 → P-F6**. What explicitly **needs no change** (taxon-agnostic,
verified by the pilot): ingest & schema gate, BGC parsing, the corrected-count formula, assembly tiering, KCB/MIBiG
anchoring, RG-GMCI reconstruction geometry, packaging/checksums, and the claim-safety language scaffolding. The
pilot's value is precisely this map: a clear catalogue of what to keep, what to gate, and what to invert before any
fungal report goes out — which is exactly what a first cross-kingdom run is for. <span class="tag t-spec">\[spec/inferred\]</span>

------------------------------------------------------------------------

## Part B — Cyanobacteria

*Placeholder — no cyanobacterial genome has been run yet.* Cyanobacteria are **bacteria** (a distinct Gram-negative, oxygenic-phototroph phylum), not eukaryotes, and are collected in this volume only because they sit outside the actinomycete target while being one of the most prolific non-actinomycete natural-product phyla (microcystins, cyanobactins, and a large RiPP/NRPS/PKS repertoire). The expectation: the organism-agnostic layer transfers as for fungi; some triggers keyed on universal committed enzymes (the phosphonate / PEP-mutase logic of §IX.5) may transfer, while the bldA/TTA and actinomycete-specific scans should gate to `NOT_APPLICABLE` once the cyanobacterial taxonomy is recognised — though, per §IX.5c, that recognition currently depends on the genus being in the denylist or a kingdom token being declared. Real worked examples to be added when runs are deposited (Zenodo). <span class="tag t-spec">\[spec\]</span>

------------------------------------------------------------------------

## Part C — Algae

**Worked genome — *Trebouxia* sp. (green alga, lichen photobiont; GCA_000818905, PUBLIC).** The first algal genome through the pipeline — a eukaryotic phototroph, the algal partner in the lichen symbiosis. Genome **61.7 Mbp across 848 contigs** (a fragmented large draft); the deterministic engine extracted **15 BGCs**, 14 / 1 / 0, corrected **14.5**, **93% Interior → GOOD**. The structural layer transferred exactly as for the fungi. **\[observed/computed\]**

The product spread is modest and characteristically non-bacterial — other ×8, fatty_acid ×7, terpene ×5, plus one **halogenated** region (algae are notable halogenated-metabolite producers) and a single saccharide / PKS. The decisive finding is in the KCB channel: **not one BGC resolved a named MIBiG reference** — every anchor fell to a generic `Type:` label. Algal natural-product chemistry is so under-represented in the reference databases that KnownClusterBlast is effectively **blind** to it. This is the cleanest statement of the cross-kingdom claim-safety ceiling: the inventory is real, but with no named anchors and no algal-calibrated detectors, the interpretation layer has nothing characterised to anchor against, and any claim beyond capacity would be unsupported. **\[observed; inferred\]**

*More algal genomes (red algae, microalgae) to be added when deposited (Zenodo).* <span class="tag t-spec">\[spec\]</span>

------------------------------------------------------------------------

*End of Volume IX. Parts B and C are scaffolded for the cross-kingdom runs to come; Part A (Fungi) carries the two worked ascomycete genomes and the v9.7.91 taxonomy-gating finding. The organising lesson is constant across all three: the deterministic inventory transfers, the actinomycete-calibrated interpretation does not, and the package is explicit about which is which.*

</div>

<div id="vol-x" class="section vol">
