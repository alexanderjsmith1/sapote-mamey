<!-- CANONICAL GLOSSARY -->
> **CANONICAL.** This is the single Sapote-Mamey source for reader-facing term definitions. Scoped addenda may define only their own local codes: `troubleshooting/CELL_STATUS_CODE_GLOSSARY.md` covers workbook cell-status codes. The historical `user_guides/comprehensive_glossary.md` and `user_guides/sapote_mamey_wheel_glossary.md` are retained drift sources, not parallel authorities.

# Sapote-Mamey Bundle — Glossary

This glossary covers abbreviations, codes, and terms used across Mamey output,
Sapote judgment reports, workbooks, evidence interfaces, and release tooling.
It is written for readers without a genomics or natural-products background.

Definitions are intended to remain stable across releases. A numeric threshold,
formula, registry count, command list, or schema field is a **versioned
implementation detail**: the named code, registry, or schema is authoritative
for the installed bundle. Historical numbers below explain older outputs; they
must not be copied into a current report without checking the current source.

Two reading notes before you start:

- **Claim-safe by design.** Throughout the bundle, biosynthetic predictions are written as *capacity* ("consistent with," "candidate," "predicted"), never as production claims. A cluster that *looks like* a vancomycin-class glycopeptide pathway is described as having "biosynthetic capacity consistent with a glycopeptide," not as "producing vancomycin." The glossary keeps that framing.
- **Similarity is not identity.** Wherever a known compound name appears next to a cluster (usually via a KCB hit), it marks the *nearest known class*, written with a leading "~" in reports (e.g. "~napyradiomycin"). It means "resembles," not "is."

---

## Core concepts

*The sixteen load-bearing terms the rest of this glossary leans on. Each is given a full structured entry; the enumerations that follow (BGC classes, status codes, resistance families, and so on) stay in scan-friendly tables. If you read only one section, read this one — every figure, caption, and lead ranking in the bundle is built from these concepts. Field order is consistent across entries: definition first, then what it operates on, outputs, the claim ceiling, related terms, where it surfaces, and version notes.*

---

### 1. BGC — biosynthetic gene cluster

- **Full name:** Biosynthetic gene cluster.
- **Aliases:** cluster; antiSMASH region call. `BGC###` is a source-scoped display alias, not the primary identity.
- **Category:** Base unit of analysis.
- **Definition:** An antiSMASH-called genomic region containing genes consistent with specialised-metabolite biosynthetic capacity. Assembly fragmentation can split one biological pathway across several region calls, so a BGC call is an analysis unit, not proof of one complete physical pathway.
- **Operates on:** antiSMASH region calls on the assembled genome.
- **Key fields:** strain, full `node_id`/`contig`, `antismash_region`/`region_number`, source-scoped `bgc_id`, `products`, and `edge_status`.
- **Claim ceiling:** A BGC is a *capacity* statement — it shows what enzymes are encoded, not what compound is made. The presence of a cluster never establishes production.
- **Evidence tier:** Structural (what is encoded).
- **Related terms:** Edge status, corrected count, architecture confidence, products.
- **Where you'll see it:** everywhere — `*_2_inventory.csv`, every board, every Mode B card.
- **Guards:** every individual reference must display `strain / full node-or-contig / region / BGC alias`, in that order. If any component is unavailable, fail closed instead of guessing or falling back to the alias.
- **Caveats:** a fragmented assembly splits one biological cluster across several BGC calls — this is what the rescue layer exists to detect.
- **Plain English:** "A region call containing genes that may form part or all of one chemical-making pathway; its full genomic address always travels with it."

---

### 2. KCB — KnownClusterBlast

- **Full name:** KnownClusterBlast sweep.
- **Aliases:** KCB hit; known-cluster match.
- **Category:** Scan (similarity).
- **Definition:** Scores each BGC against the MIBiG database of characterised clusters; a high cumulative score means the cluster resembles a known producer cluster.
- **Operates on:** antiSMASH KnownClusterBlast output vs MIBiG.
- **Key fields:** `kcb_top`, `kcb_cumulative`, KCB protein-hit count.
- **Claim ceiling:** **Similarity, not identity.** A KCB hit marks the *nearest known class*, written with a leading "~" (e.g. "~napyradiomycin") — it means *resembles*, never *is*. KCB never licenses a compound-identity or production claim.
- **Evidence tier:** Similarity signal; any downstream weight is versioned scoring policy.
- **Related terms:** MIBiG, RG-GMCI, ~ (tilde), claim ceiling, KCB-dark.
- **Where you'll see it:** triage board KCB columns; Mode B §KCB; every "~name" in a report.
- **Guards:** the genome self-hit bug (a genome hitting its own deposited cluster) was fixed in v9.7.22 (`kcb_top` correctness).
- **Caveats:** some genuinely bioactive clusters are *KCB-dark* (no database match) — marker-aware scoring exists so these aren't buried.
- **Plain English:** "How much this cluster looks like something already in the books — a resemblance score, not an ID."

---

### 3. Corrected BGC count

- **Full name:** Corrected (truncation-weighted) BGC count.
- **Aliases:** corrected count; defensible BGC inventory.
- **Category:** Key metric.
- **Definition:** The defensible cluster-inventory figure that discounts truncated clusters so a fragmented assembly is not credited with inflated capacity.
- **Operates on:** the `edge_status` of every BGC in the assembly.
- **Key fields / current engine formula:** **Interior × 1.0 + Edge × 0.5 + Full-contig × 0.25**, rounded to two decimals by `mamey/assembly.py::corrected_bgc_count`. This is a versioned engine rule, not a biological constant.
- **Claim ceiling:** a count, not a claim — but it is the *only* BGC-count figure permitted in comparative statements; raw counts are not used for cross-strain comparison.
- **Evidence tier:** computed (deterministic rule).
- **Related terms:** Edge status, interior %, assembly tier, RG-GMCI.
- **Where you'll see it:** `*_2_inventory.csv`; strain-summary tables; every cohort figure's strain ordering.
- **Guards:** Edge/Full-contig weights are fixed; do not re-derive the formula in downstream tools.
- **Caveats:** the rescue layer may later show two Edge fragments are one cluster — the corrected count is a *pre-rescue* defensible floor, not a final biological count.
- **Plain English:** "Count whole clusters as 1, half-clusters as ½, contig-spanning fragments as ¼ — so a shattered genome can't claim more chemistry than it has."

---

### 4. Edge status

- **Full name:** Edge / Interior / Full-contig truncation label.
- **Aliases:** boundary status.
- **Category:** Structural label (drives the corrected count).
- **Definition:** A simple three-way record of whether a BGC is truncated by a contig boundary.
- **Operates on:** the position of the BGC relative to its contig ends.
- **Key values:** **Interior** (fully inside a contig, weight 1.0); **Edge** (runs off one end, weight 0.5); **Full-contig** (spans the whole contig, likely cut at both ends, weight 0.25).
- **Claim ceiling:** Edge and Full-contig clusters are restricted to architecture-class claims; only Interior clusters support fuller capacity statements.
- **Evidence tier:** structural (observed from coordinates).
- **Related terms:** corrected count, architecture confidence (A–E), terminus-truncation rescue, assembly tier.
- **Where you'll see it:** inventory; triage board; the banner on every Edge/FC Mode B card.
- **Guards:** an Edge region whose boundary sits *at* the contig terminus is the trigger for terminus-truncation rescue (v9.7.100).
- **Caveats:** Edge status is simpler than the A–E architecture grade and answers only "is it truncated" — the two are reported side by side and should not be conflated.
- **Plain English:** "Is this cluster whole, cut off at one end, or the whole little contig — which tells us how much to trust it."

---

### 5. Architecture confidence (A–E) and the three confidence axes

- **Full name:** Architecture confidence grade; architecture capacity; class confidence; claim confidence.
- **Aliases:** `Arch`; A–E code.
- **Category:** Confidence framework.
- **Definition:** The A–E grade scores the **structural completeness** of a locus (A = interior & coherent; C = edge but coherent; D = full-contig; E = weak annotation). It is one of *four* distinct "confidence-like" measures that must not be conflated.
- **Operates on:** BGC position + annotation quality.
- **Key fields:** `Arch` (A–E structural grade); `Arch_Capacity` (the claim-safe class *name*, not a confidence); `Class_Conf` (confidence in that class call, HIGH/MOD/LOW); `claim_confidence` (overall lead-claim confidence).
- **Claim ceiling:** each axis caps a *different* claim; a clean structure (Arch=A) does not raise the class-call confidence (Class_Conf) or the lead confidence.
- **Evidence tier:** mixed (structural + judgment).
- **Related terms:** edge status, claim ceiling, Mode B, WL tier.
- **Where you'll see it:** `*_4_triage_board.csv`, reported side by side.
- **Guards:** "Arch=A, Class_Conf=LOW" is **coherent, not contradictory** — a structurally clean locus whose product class is still uncertain.
- **Caveats:** through v9.7.27 `Class_Conf` was mislabelled `Arch_Conf` (read as architecture-grade confidence, which it is not); renamed v9.7.28.
- **Plain English:** "Four different 'how sure are we' numbers that answer four different questions — don't mash them into one."

---

### 6. BGC-inventory assembly tier and fragmentation tier

- **Full name:** BGC-inventory assembly tier; assembly fragmentation tier.
- **Aliases:** `assembly_tier`; `fragmentation_tier`.
- **Category:** Genome-level QC.
- **Definition:** Two separate descriptors. `assembly_tier` summarizes BGC-boundary recovery from the interior-BGC percentage. `fragmentation_tier` summarizes sequence contiguity from contig count and N50. Neither is a compound-confidence grade.
- **Operates on:** interior-BGC percentage for `assembly_tier`; contig count and N50 for `fragmentation_tier`.
- **Key thresholds:** `assembly_tier`: GOOD ≥70% interior, MODERATE ≥45%, POOR ≥20%, VERY_POOR <20%, or UNKNOWN. `fragmentation_tier`: CLOSED, CONTIGUOUS, DRAFT, FRAGMENTED, HIGHLY_FRAGMENTED, or UNKNOWN under the ordered bands in `mamey/assembly.py`.
- **Claim ceiling:** fragmented or unknown contiguity requires BGC counts to be described as floors and weakens physical-completeness claims. It never licenses compound identity, production, or activity.
- **Evidence tier:** computed (deterministic thresholds).
- **Related terms:** corrected count, interior %, N50, edge status, assembly caveat.
- **Where you'll see it:** strain summary; the assembly banner on every package.
- **Guards:** do not infer sequence contiguity from `assembly_tier`; use `fragmentation_tier`. Genome-size or contamination warnings are separate advisory checks and do not alter extraction.
- **Caveats:** `assembly_tier` is an unfortunately broad historical field name. A genome can have a favorable interior-BGC percentage while still being highly fragmented by contig/N50 criteria.
- **Plain English:** "One label asks how many cluster calls avoid contig edges; the other asks how continuous the assembled genome is."

---

### 7. RG-GMCI and the rescue layer

- **Full name:** Reference-Guided Genome Mining Candidate Inference.
- **Aliases:** RGGMCI; "the rescue layer."
- **Category:** Scan / reconstruction (mandatory pre-triage for fragmented assemblies).
- **Definition:** Homology-guided linkage proposing that two BGC fragments on different contigs are one split pathway, when they map to the same reference producer cluster in ClusterBlast/KnownClusterBlast output.
- **Operates on:** antiSMASH ClusterBlast + KnownClusterBlast tables; per-BGC geometry.
- **Key fields (v9.7.100):** `rggmci_score`, `rggmci_confidence` (HIGH/MODERATE/LOW); `db_kind` (knownclusterblast vs clusterblast vs excluded subclusterblast); `rescue_evidence_base` (BOTH_KCB_AND_CB / CLUSTERBLAST_ONLY / KNOWNCLUSTERBLAST_ONLY); `functional_rescue_class` (COMPLEMENTARY / BOTH_CORE / ACCESSORY_ONLY); `subject_tiling_verdict` (COMPLEMENTARY_SPLIT / OVERLAPPING_PARALOG / …); `terminus_truncation_rescue`.
- **Claim ceiling:** **candidate inference — does not join contigs at the nucleotide level.** The bonus is routing priority, not claim confidence.
- **Evidence tier:** routing/prioritisation signal (capacity-level).
- **Related terms:** FLBR, EFLS, KCB, db_kind, terminus-truncation rescue, functional rescue class.
- **Where you'll see it:** `*_4A_RGGMCI_ranked_pairs.csv`; the workflow arrow (Parse → Scans → **RG-GMCI** → Boards); the "RG-GMCI context" line in Mode B.
- **Guards:** promiscuous-hub down-weighting (a fragment linking to >4 partners is demoted); distant-reference penalty.
- **Caveats:** a small severed-arm contig can belong to only one cluster, so where it pairs with several Edge regions the evidence base + functional class disambiguate; physical confirmation needs long-read / gap-PCR. **Reworked v9.7.100** to use the full ClusterBlast evidence rather than KnownClusterBlast alone.
- **Plain English:** "Two broken pieces on different contigs probably came from the same cluster because they both resemble the same known cluster — a lead to chase, not a proven join."

---

### 8. CCTT / T43 class-trigger framework

- **Full name:** Compound-Class Trigger Table.
- **Aliases:** T43-* triggers; cryptic-class triggers.
- **Category:** Diagnostic scan (feeds marker-aware scoring).
- **Definition:** A table of per-BGC gene/motif signals that flag specific biosynthetic classes — HAL (halogenase), LAN (lanthipeptide), TET (tetronate), PHO (phosphonate), NUC (nucleoside), ENE (enediyne), and others — independent of any KCB match.
- **Operates on:** per-BGC domain/gene annotations.
- **Key fields:** `cctt.counts` (hit count); `cctt.trigger_bgc_counts` (BGC-carrying count); the `T43-*` trigger IDs.
- **Claim ceiling:** a trigger is a *signal*, not a product call; it raises routing priority (and can floor a KCB-dark cluster), never compound identity.
- **Evidence tier:** diagnostic routing evidence; any downstream weight is versioned scoring policy.
- **Related terms:** diagnostic floor, marker-aware scoring, CGAD, [E-signal].
- **Where you'll see it:** the CCTT block in Mode B; marker columns on the board.
- **Guards:** report hits **and** BGC spread — "T43-PHO 8 hits / 1 BGC" is one dedicated phosphonate locus, not a phosphonate-rich strain.
- **Caveats:** through v9.7.27 only the hit count was shown ("T43-PHO ×8"), which misread as strain-level abundance.
- **Plain English:** "Gene-level tripwires for specific chemistry — so a cluster gets credit for what its genes show even when no database matches it."

---

### 9. Marker registry

- **Full name:** Diagnostic-marker registry.
- **Aliases:** marker bank; MMK IDs.
- **Category:** Scoring infrastructure.
- **Definition:** The curated set of per-BGC diagnostic markers (resistance folds, CCTT triggers, regulatory motifs) that marker-aware scoring reads, each with a stable ID so a score is traceable to the exact signal that produced it.
- **Operates on:** per-BGC scan outputs.
- **Key fields:** marker ID, marker class, the evidence-axis weight it carries.
- **Claim ceiling:** a marker is evidence *for routing*; its presence is capacity-level and traceable, never a production claim.
- **Evidence tier:** diagnostic (capacity-level).
- **Related terms:** CCTT, diagnostic floor, real-anchor rule, evidence traceability.
- **Where you'll see it:** the evidence-traceability block; marker columns on the board.
- **Guards:** **real-anchor rule** — every marker keyword is audited against the strings antiSMASH *actually emits* (e.g. "nucleoside"), not textbook compound names (e.g. "nikkomycin").
- **Caveats:** a marker firing is presence, not function — "presence ≠ function" applies.
- **Plain English:** "A fixed, ID'd list of gene-level clues the scorer is allowed to use, each one traceable back to what triggered it."

---

### 10. Mamey triage tier / routing prior

- **Full name:** Mamey triage tier (Exceptional / High / Medium / Low / Inventory).
- **Aliases:** routing tier; lead tier. A downstream Wet-Lab score is a separate judgment-layer metric.
- **Category:** Prioritisation.
- **Definition:** The engine's effort-allocation bucket derived from the largest of the antibacterial, antifungal, and novelty routing priors, followed by diagnostic floors and fail-safe downgrades.
- **Operates on:** AB, AF, novelty, corroborated diagnostics, class policy, and scoring guards.
- **Key thresholds:** current `mamey/scoring.py::triage_bgcs` uses Exceptional ≥85, High ≥70, and Medium ≥50. Below 50, the governed class policy selects Low or Inventory. These numbers are versioned implementation details.
- **Claim ceiling:** **tier is about where to spend effort, never how confident a claim is** — raising a lead's tier never raises its claim ceiling.
- **Evidence tier:** composite routing score.
- **Related terms:** AB/AF/novelty routing priors, diagnostic floor, standing-rule downgrade, evidence axes.
- **Where you'll see it:** the triage board's `tier`/lead-tier field and downstream lead lists.
- **Guards:** a corroborated class-defining diagnostic can floor Low/Inventory to Medium; class-specific machinery and standing-rule guards may apply other bounded adjustments.
- **Caveats:** precision, not recall — the tiers decide attention, not truth.
- **Plain English:** "Which regions the engine routes toward attention first — a to-do prior, not a measured activity or truth score."

---

### 11. Diagnostic bonus & diagnostic floor

- **Full name:** Marker-aware diagnostic bonus; diagnostic floor.
- **Aliases:** the floor; KCB-dark protection.
- **Category:** Scoring rule.
- **Definition:** Marker-aware scoring reads per-BGC diagnostics so that genuinely bioactive but *KCB-dark* clusters (no database match) are not buried by a KCB-only score; the **floor** guarantees a Tier-1 diagnostic cluster cannot sit below MEDIUM tier.
- **Operates on:** CCTT/resistance diagnostics + chitin context (CGAD).
- **Key fields:** `AF_DIAGNOSTIC_TRIGGERS` (the antifungal markers that fire the floor); the floored tier.
- **Claim ceiling:** the floor changes *routing*, not claim strength — a floored cluster is "worth screening," not "confirmed active."
- **Evidence tier:** diagnostic routing rule.
- **Related terms:** CCTT/T43-NUC, CGAD, KCB-dark, WL tier.
- **Where you'll see it:** the score-rationale line where a cluster was floored.
- **Guards:** the canonical worked case is a KCB-dark nucleoside cluster *with* chitin context (CGAD-positive) → antifungal bonus + floor to MEDIUM (the nikkomycin/polyoxin-style case a KCB-only scorer misses).
- **Caveats:** the floor sets a *minimum*; it does not promote to HIGH.
- **Plain English:** "A safety net so a real but unknown cluster isn't dumped just because the database has never seen it."

---

### 12. Standing-rule downgrade (permanent exclusions)

- **Full name:** Standing biological constraints.
- **Aliases:** permanent exclusions; DOWNGRADE rules.
- **Category:** Interpretation guard.
- **Definition:** Permanent rules learned across many strains that override case-by-case interpretation to stop recurring over-claims.
- **Operates on:** comparative/cross-habitat claim generation.
- **Key members:** **saccharide** (pure-saccharide clusters omitted from comparative counts); **hglE-KS-PREV-001** (prevalent, habitat-non-specific across many strains/genera/habitats — habitat claims retired, novelty stands); **multi-siderophore** (iron-economy observation, not a per-strain distinction). (**NAPAA** is registry-neutral — listed, not interpreted; neither downgraded nor lead-blocking.)
- **Claim ceiling:** these terms may appear in inventories but **never** in comparative or habitat-specific claims.
- **Evidence tier:** standing rule (overrides local scoring).
- **Related terms:** claim ceiling, CCSM, [E-signal].
- **Where you'll see it:** the exclusions note on cohort/comparative figures.
- **Guards:** new strains do not reopen a retired hypothesis without explicit re-grounding.
- **Caveats:** exclusion from *comparison* is not a claim of biological unimportance — only that the signal is not ecologically discriminating.
- **Plain English:** "A short list of clusters we've learned are everywhere, so we stop reading meaning into them when comparing strains."

---

### 13. Claim-safety vocabulary

- **Full name:** Claim-safety vocabulary (the bundle's central discipline).
- **Aliases:** capacity language; the claim ceiling.
- **Category:** Interpretation discipline.
- **Definition:** The fixed vocabulary governing how confident any statement may be: capacity not production, similarity not identity, missingness not absence.
- **Operates on:** every report sentence.
- **Key terms:** **Biosynthetic capacity** ("consistent with," never "produces"); **claim ceiling** (the max confidence a given evidence level allows); **~ (tilde)** ("resembles, is not"); **missingness vs absence** ("not found in this assembly" ≠ "gene absent"); **bioactivity metadata** (typed strain-level context, `NOT_SUPPLIED` when absent, never pinned to a BGC without governed linkage); **`[EG]`/`[VL]`** (evidence-grounded vs literature-verified).
- **Claim ceiling:** this *is* the claim-ceiling machinery.
- **Evidence tier:** governs all tiers.
- **Related terms:** KCB, architecture confidence, standing-rule downgrade, evidence traceability.
- **Where you'll see it:** every Mode B verdict; every caption.
- **Guards:** no strain is ever called activity-*negative* (absence of recorded activity means nothing — bioassay data is non-standardised).
- **Caveats:** the discipline is mandatory, not stylistic — a production/identity phrasing is a defect, not a wording preference.
- **Plain English:** "The house rules for how boldly anything may be stated — always 'could,' never 'does'."

---

### 14. Mode B

- **Full name:** Mode B — full per-BGC interpretation protocol.
- **Aliases:** Mode B card; expanded owner-review card.
- **Category:** Sapote judgment protocol.
- **Definition:** The current expanded per-BGC authoring protocol uses the canonical §1–§48 template. It begins with exact-locus identity and a gene-first evidence read, then carries architecture, channel-separated homology, tailoring, resistance, class, ecology, caveats, provenance, unresolved questions, and the final claim-safe verdict.
- **Operates on:** a sealed Mamey package's per-BGC evidence.
- **Key fields:** exact-locus identity, `document_state`, typed `evidence_state` holds, complete canonical gene roster, channel-separated BLASTp matrix when the finished profile is claimed, §28 provenance, §30 decision tree, and the final verdict.
- **Claim ceiling:** Mode B applies — not relaxes — the claim ceiling; a CONFIRM verdict is "judged a genuine cluster," not "produces compound X."
- **Evidence tier:** authored judgment; any downstream numeric weight is a versioned builder rule.
- **Related terms:** evidence axes, lead classes, DAPR, FULL ANALYSIS MODE.
- **Where you'll see it:** authored card Markdown, the judgment store/register, Mode B receipts, and compiled reports.
- **Guards:** run `modeb-availability` before prose. Keep nr, ClusteredNR, and local Swiss-Prot separate; bind every gene by the canonical roster and protein sequence identity. Edge/Full-contig status changes caveats, not authoring depth.
- **Caveats:** a generated scaffold, a mechanically valid card, and an ingested receipt are different states. None is scientific acceptance, release approval, or publication approval.
- **Plain English:** "The deep per-cluster write-up that turns raw scan output into a judged, caveated lead."

---

### 15. Evidence axes & legacy lead classes (A / B / C)

- **Full name:** Evidence axes; lead classes A/B/C.
- **Aliases:** the scoring backbone.
- **Category:** Prioritisation framework.
- **Definition:** A judgment-layer overlay that keeps independent lines of evidence legible instead of collapsing them into one biological claim. Historical cohort builders combined selected axes into A/B/C labels; that overlay is distinct from the current Mamey triage tier.
- **Operates on:** architecture/completeness, KCB similarity, novelty, diagnostics, regulation, authored judgment, and other explicitly bound evidence.
- **Key policy:** fixed weights, membership rules, and cohort totals are versioned builder outputs. Recompute them from the controlling builder and bound cohort; do not treat an old count or formula as a universal definition.
- **Key classes:** A/B/C are retained legacy routing labels where a downstream workflow still emits them. The emitting artifact must identify its rule and denominator.
- **Claim ceiling:** **raising a lead's class never raises its claim confidence** — class is about effort (precision), claim ceilings still cap assertions.
- **Evidence tier:** composite routing.
- **Related terms:** WL tier, Mode B, SARP, DAPR.
- **Where you'll see it:** selected legacy/cohort lead tables and historical figure documentation.
- **Guards:** never infer a current cohort count from this glossary; never translate a stronger lead class into a stronger product claim.
- **Caveats:** the axes can disagree without contradiction — they measure different things.
- **Plain English:** "Keep the different reasons for pursuing a region visible; if a workflow combines them, record exactly which rule and cohort it used."

---

### 16. Compound-class annotation

- **Full name:** Compound-class annotation layer.
- **Aliases:** chemotype layer.
- **Category:** Interpretation layer.
- **Definition:** Maps each BGC to a claim-safe chemotype/compound class so a cluster can be discussed by *class* without naming a product. The available classes and reference set are versioned data, not part of the term's definition.
- **Operates on:** KCB hits + class diagnostics + product annotations.
- **Key fields:** chemotype label; the MIBiG references supporting it.
- **Claim ceiling:** class-level only — "biosynthetic capacity consistent with a [class]," never a compound name.
- **Evidence tier:** capacity (class call).
- **Related terms:** KCB, CCTT, claim-safety vocabulary, `Arch_Capacity`.
- **Where you'll see it:** the product-class column; compound-class matrices in cohort work.
- **Guards:** cohort-local class matrices are computed *within* a cohort and must be recomputed after any merge — never concatenated.
- **Caveats:** a chemotype is a resemblance class, inheriting KCB's similarity-not-identity ceiling.
- **Plain English:** "Tag each cluster with the *kind* of molecule it could make, without ever claiming the specific molecule."

---

## Enumerations & code tables

*The sections below are scan-friendly lookup tables — codes, classes, and status values you match against output. The concepts behind them live in **Core concepts** above.*

## BGC classes (antiSMASH product annotations)

A **BGC** (biosynthetic gene cluster) is a contiguous run of genes that together build one natural product. antiSMASH labels each detected cluster with a predicted product class; these are the labels you will see.

| Term | Full name | What it means in plain English |
|---|---|---|
| T1PKS | Type I polyketide synthase | A large assembly-line enzyme that builds polyketide natural products (e.g. erythromycin, rapamycin). Often antibacterial or antifungal. |
| T2PKS | Type II polyketide synthase | An iterative enzyme system making aromatic polyketides (e.g. tetracyclines, anthracyclines, angucyclines). Usually has a strong UV chromophore. |
| T3PKS | Type III polyketide synthase | Simpler single-enzyme PKS; makes flavonoids and some phenolic compounds. |
| transAT-PKS | trans-acyltransferase PKS | A Type I PKS variant where the acyltransferase acts in *trans* (as a standalone enzyme). Frequently fragments across contigs; a common source of split pathways. |
| PKS-NRPS hybrid | Hybrid assembly line | A single megasynthase combining polyketide and peptide modules; builds mixed peptide-polyketide scaffolds. |
| hglE-KS | Heterocyst-glycolipid KS-like | A KS domain related to cyanobacterial glycolipid synthesis; used as a marker for certain reducing polyketide assemblies. (See *hglE-KS-PREV-001* under standing constraints — prevalent and habitat-non-specific.) |
| NRPS | Non-ribosomal peptide synthetase | Assembly-line enzyme building peptide natural products without the ribosome (e.g. vancomycin, daptomycin). |
| NRPS-like | NRPS-related | Has NRPS domains but doesn't follow the standard modular architecture; often makes small aryl-acid or diketo compounds. |
| RiPP | Ribosomally synthesised and post-translationally modified peptide | A peptide made by the ribosome, then chemically modified. Includes lanthipeptides, thiopeptides, sactipeptides. |
| Lanthipeptide (class I–IV) | Lanthipeptide | A RiPP with thioether (lanthionine) bridges. Class III made by LanKC multifunctional synthetase. Often antimicrobial. |
| Thiopeptide | Thiazolyl peptide | A heavily modified RiPP with a central pyridine/dehydro-ring; potent Gram-positive antibacterials (e.g. thiostrepton). |
| LAP | Linear azol(in)e-containing peptide | A RiPP class with heterocyclised cysteine/serine residues; includes the microcin/plantazolicin family. |
| Lassopeptide | Lasso peptide | A RiPP threaded into a knot-like lasso fold; protease- and heat-stable, often receptor antagonists. |
| Sactipeptide | Sulfur-to-alpha-carbon peptide | A RiPP with sactionine (Cα–S) bridges installed by a radical-SAM enzyme. |
| RaS-RiPP / ranthipeptide | Radical-SAM RiPP | A RiPP modified by a radical-SAM maturase; structurally novel, often KCB-dark. |
| NI-siderophore | NRPS-independent siderophore | An iron-scavenging molecule made without an NRPS assembly line. |
| NRP-metallophore | Non-ribosomal peptide metallophore | A metal-chelating NRP; often dual-function (iron-scavenging + bioactive warhead). |
| Betalactone | β-Lactone | A four-membered ring lactone; electrophilic warhead that inhibits serine hydrolases and proteases. Rare, high bioactivity potential. |
| Spirotetronate | Spirotetronate | A polyketide with a spiro-linked tetronic-acid ring; large clusters, often potent antibacterials (e.g. abyssomicin, kijanimicin). |
| Enediyne | Enediyne (9-/10-membered) | An extremely potent DNA-cleaving warhead class (e.g. calicheamicin). cytotoxicity caveats apply (handling per standard lab SOPs); see *T43-ENE / [E-signal]*. |
| Ansamycin / ansa-PKS | Ansamycin | A polyketide with a macrocyclic *ansa* bridge across an aromatic core (e.g. rifamycin). |
| Glycopeptide | Glycopeptide NRPS | A cross-linked, glycosylated heptapeptide class (e.g. vancomycin, kistamicin). Often carries *VanHAX* self-resistance. |
| Aminoglycoside / amglyccycl | Aminoglycoside / aminocyclitol | Sugar-based antibacterials (e.g. streptomycin, kanamycin); may carry *APH/AAC* self-resistance. |
| Nucleoside | Nucleoside antibiotic | A modified-nucleoside scaffold; includes chitin-synthase-inhibiting antifungals (e.g. nikkomycin/polyoxin class). Frequently KCB-dark. |
| Azoxy / guanidinotide | Azoxy / guanidino natural products | Specialised nitrogen-rich warhead classes flagged for novelty. |
| Terpene | Terpene/terpenoid | Built from isoprene units; includes antibiotics, pigments, and volatile compounds. |
| Saccharide | Sugar/glycoside | Carbohydrate-modifying cluster; often appended to a polyketide or peptide aglycone. (See *saccharide-gating* under standing constraints.) |
| Butyrolactone | γ-Butyrolactone | Autoregulatory signalling molecule (quorum sensing) in Streptomyces. Routes to ecology, not drug discovery. |
| Ectoine | Ectoine | Compatible solute for osmotic stress; not a drug-discovery target. |
| Indole | Indole-derived | Clusters making indole-containing metabolites (some pigments, some bioactive). |
| Phosphonate | Phosphonate | C–P-bonded compounds (e.g. fosfomycin class); may carry fosfomycin self-resistance. |
| Redox-cofactor | Redox cofactor | Biosynthesis of cofactor-like small molecules; usually primary-metabolism-adjacent. |
| Melanin | Melanin | Pigment biosynthesis. |
| Fatty acid | Fatty acid | Lipid/fatty acid biosynthesis cluster. |
| NAPAA | Non-alpha poly-amino acids | e.g. poly-gamma-glutamate; structural/protective rather than bioactive. Registry-neutral (listed, not interpreted; neither downgraded nor lead-blocking). |
| Halogenated | Halogenated compound | Cluster predicted to make a chlorinated or brominated product (halogenase present). |

---

## Scan names and abbreviations

Mamey runs a fixed battery of deterministic detection modules ("scans") over the antiSMASH output. Each BGC carries a record of which scans fired.

| Abbreviation | Full name | What it checks |
|---|---|---|
| KCB | KnownClusterBlast sweep | Scores each BGC against the MIBiG database of known clusters; high scores = known-class candidate. |
| RG-GMCI / RGGMCI | Reference-Guided Genome Mining Candidate Inference | Homology-guided linkage of fragmented BGC regions that map to the same reference producer cluster in ClusterBlast/KnownClusterBlast output; candidate inference, not a physical contig joiner; mandatory pre-triage step for fragmented (multi-contig) assemblies. |
| FLBR | Fragment-Linkage BGC Recovery | Census of fragmented megasynthase (PKS/NRPS) sets across contigs — flags LMPKS_FRAGMENT_SET; identifies the candidate fragments that EFLS/RG-GMCI then link (a detection step that feeds recovery, not the linkage itself). The README labels the same scan the "fragmented-megasynthase census". |
| EFLS | Edge-Flank Linkage Scan | Identifies split-pathway candidates at contig edges. Works with FLBR (which finds the fragments) and RG-GMCI (which infers the producer) to propose that two contig-edge pieces are one pathway. |
| CCTT | Compound-Class Trigger Table | Flags specific biosynthetic signals: HAL (halogenase), LAN (lanthipeptide), TET (tetronate/spirotetronate), PHO (phosphonate), NUC (nucleoside), and others. A CCTT trigger is the per-BGC signal the marker-aware scorer reads. |
| CGAD | Chitinase Genome Architecture Detection | Detects chitin-degrading enzyme families (GH18, GH19, AA10_LPMO, CBM_CHITIN, GlcNAc). Used as the chitin-context gate for nucleoside antifungal calls. |
| UMED | Unclustered Maturation Enzyme Detection | For each RiPP/lanthipeptide BGC, checks whether a required maturation enzyme (e.g. LanP/LanT, FlaP-AplP, M16 protease) is encoded in-cluster; if absent, flags a maturation-gap and scans genome-wide for the *unclustered* candidate enzyme. Hard claim ceiling: candidate / specificity-unverified / presence != function; fragmented (Very-Poor) assemblies report "not found in assembly" as missingness, not absence. |
| FLBR/EFLS/RG-GMCI trio | Fragment recovery chain | Read together: FLBR *finds* fragmented megasynthase sets, EFLS *locates* the edge pieces, RG-GMCI *infers* the shared reference producer. None physically rejoins contigs; all three produce candidate inferences. |
| bldA/TTA | bldA codon scan | Counts TTA codons in BGC ORFs; T4 BGCs depend on bldA for expression — affects fermentation strategy. |
| TFBS | Transcription Factor Binding Site scan | Counts regulatory motifs (GBL/AdpA, DasR, BldD, PhoP, SARP) near BGCs; guides induction strategies. (See *Regulatory elements* below.) |
| CCSM | Cross-Cohort Strain Module | Cross-strain comparison module: compares a strain's BGC/marker profile against the rest of the cohort. |
| DAPR | Dual Antibacterial/Antifungal Prioritization Ranking | Sapote protocol for ranking top 3 antibacterial and top 3 antifungal BGC leads. |
| LMPKS | Linear Megasynthase PKS | A split mega-PKS consistent with a linear polyether ionophore; detected by FLBR. |

**CCTT counts: hits vs. BGCs.** A CCTT trigger is reported two ways, and they answer different questions. The *hit* count (`cctt.counts`, shown as "N hits") is the number of gene/motif matches for that trigger across the genome; the *BGC-carrying* count (`cctt.trigger_bgc_counts`, shown as "M BGC(s)") is how many distinct clusters carry it. One BGC can hold several hits, so the two diverge — "T43-PHO 8 hits / 1 BGC" is a single dedicated phosphonate locus, not a phosphonate-rich strain, whereas the same 8 hits spread across 8 BGCs would be. The PHO_CLUSTER flag now reports both and words its interpretation from the BGC spread. (Through v9.7.27 only the hit count was shown, as "T43-PHO x8", which read as a strain-level abundance.)


---

## Regulatory elements & TFBS

The TFBS scan counts binding-site motifs for the regulators below near each BGC. They do not change *what* a cluster makes; they hint at *how to switch it on* in the lab (induction strategy) and, in the SARP case, feed the lead-class logic.

| Regulator | What it is | Why it matters here |
|---|---|---|
| SARP | Streptomyces Antibiotic Regulatory Protein | A pathway-specific *activator*. A SARP sitting in/near a BGC is positive evidence the cluster is a real, regulated antibiotic pathway — it is one of the five evidence axes and the second axis (with Mode B) that defines a Class-A lead. Read per-BGC, not genome-wide. |
| DasR | GlcNAc-responsive global repressor | Links nutrient sensing (N-acetylglucosamine, a chitin breakdown product) to antibiotic onset. A DasR site is a weak positive (a fractional point) in the score. |
| AdpA / GBL | A-factor / γ-butyrolactone cascade | The quorum-sensing developmental switch; GBL/AdpA control timing of secondary metabolism. |
| BldD | Master developmental repressor | Gatekeeps the switch from growth to sporulation/secondary metabolism. |
| PhoP | Phosphate-response regulator | Couples phosphate limitation to antibiotic production; relevant to media design. |

---

## Architecture confidence codes

→ *Concept and the four-axis framework: **Core concepts #5**. The lookup grids are below.*

The A–E structural grade, assigned by Mamey to every BGC from its position in the assembly:

| Code | Name | Meaning |
|---|---|---|
| A | Interior, coherent | BGC sits fully inside a contig with annotated product. Highest confidence. |
| B | Interior, ambiguous | Interior but product annotation weak or mixed. |
| C | Edge, coherent | BGC truncated at contig edge; product annotation coherent for the visible portion. Partial claims only. |
| D | Full-contig | BGC spans the entire contig — likely truncated at both ends. Architecture-class level only. |
| E | Weak/ambiguous | Poor annotation; inventory-level interpretation only. |

The four side-by-side confidence fields in `*_4_triage_board.csv` (do not conflate — they answer different questions and can disagree without contradiction):

| Column / field | What it measures | Values |
|---|---|---|
| `Arch` (architecture_confidence) | Structural completeness of the locus — the A–E grade above. | A–E |
| `Arch_Capacity` (architecture_capacity) | The claim-safe class-capacity call — a class *name*, not a confidence. | e.g. "lanthipeptide-class capacity" |
| `Class_Conf` (architecture_class_confidence) | Confidence in that class call. | HIGH / MODERATE / LOW |
| `claim_confidence` (B1) | Overall lead-claim confidence from scoring — the whole lead, not just the class. | HIGH / MODERATE / LOW |

*History: through v9.7.27 `Class_Conf` was labelled `Arch_Conf`, which read as architecture-grade confidence (which it is not); renamed in v9.7.28.*

The triage board's region-structure fields are also distinct: `Composite_region` is a structural flag that fires only when `Single_protocluster_count >= 3`; it is not the general over-merge verdict. `Overmerge_state` is the E5 verdict (`OVERMERGE_SUSPECT`, `COHERENT_CHEMICAL_HYBRID`, or `NOT_VERIFIABLE`). A consumer that needs the number of antiSMASH protoclusters resolved in the region, including a two-protocluster merge, must read `Protocluster_count`. These are structural descriptors only and do not establish product identity, novelty, or activity.


---

## Edge status (used in the corrected count)

→ *Concept and claim ceiling: **Core concepts #4**.*

The truncation label that drives the corrected count:

| Status | Meaning | Weight in corrected count |
|---|---|---|
| Interior | Fully inside a contig | 1.0 (full) |
| Edge | Runs off one end of a contig | 0.5 (half) |
| Full-contig | Spans the whole contig (likely cut at both ends) | 0.25 (quarter) |

---

## Evidence axes & legacy lead classes (A / B / C)

→ *Concept and the precision-not-confidence caveat: **Core concepts #15**.*

Evidence axes remain separate because they answer different questions. A
downstream builder may combine selected axes, but its versioned rule and
denominator must travel with the output.

| Axis | Question it answers |
|---|---|
| Structure / completeness | Is the visible locus coherent and physically complete enough for the proposed class? |
| Similarity | Does the locus resemble a characterized reference cluster? |
| Novelty / reference darkness | How weakly is the locus represented in the bound reference channels? |
| Diagnostic machinery | Do class-compatible genes, domains, or resistance signals corroborate the class? |
| Regulation / expression planning | Are pathway-linked regulatory signals present? This is not expression evidence. |
| Authored judgment | What claim-safe synthesis did the current Mode B review reach from the bound evidence? |

| Class | Definition | Plain English |
|---|---|---|
| Class-A / B / C | Legacy judgment-layer labels emitted by selected cohort builders. | Read the emitting artifact's rule, version, and denominator; there is no version-free membership count. |

---

## Marker-aware scoring & the diagnostic floor

→ *Concept and the KCB-dark rationale: **Core concepts #11**.*

| Term | Meaning |
|---|---|
| T43-NUC | A nucleoside diagnostic trigger. On a KCB-dark nucleoside cluster *with chitin context* (CGAD-positive), it adds an antifungal bonus and floors the cluster to at least Medium — the nikkomycin/polyoxin-style antifungal case a KCB-only scorer would miss. |
| Diagnostic floor | A Tier-1 diagnostic cannot leave a BGC below Medium tier, regardless of KCB. "Floors" = sets a minimum the score cannot drop beneath. |
| AF_DIAGNOSTIC_TRIGGERS | The set of antifungal-diagnostic markers that fire the floor. |
| Real-anchor rule | Audit every keyword against the strings antiSMASH *actually emits* (e.g. "nucleoside", "SGR PTMs"), not textbook compound names (e.g. "nikkomycin"). |

---

## Mamey triage tiers

→ *Concept and the effort-not-confidence caveat: **Core concepts #10**. Code remains the threshold authority.*

Mamey assigns every BGC a routing tier from its AB, AF, and novelty priors,
then applies corroborated floors and fail-safe downgrades.

| Tier | Criteria | Treatment |
|---|---|---|
| Exceptional | Current best routing prior ≥85 | Highest engine routing prior; still capacity-level and subject to guards |
| High | Current best routing prior ≥70 | High routing priority |
| Medium | Current best routing prior ≥50, or an applicable diagnostic/machinery floor | Review priority; a floor does not raise claim confidence |
| Low | Below 50 with a resolved specialised class outside the governed Inventory policy | Keep visible at lower routing priority |
| Inventory | Below 50 and unresolved or covered by the governed Inventory policy | Retain in the complete inventory; do not equate with biological unimportance |

The thresholds above describe the current engine and must be checked against
`mamey/scoring.py::triage_bgcs` when used outside this bundle.

---

## Resistance gene families

| Term | What it is | Self-protection significance |
|---|---|---|
| Beta_lactamase_fold | β-Lactamase-fold protein adjacent to biosynthetic genes | T1 diagnostic: strong evidence the BGC makes an antibacterial compound the producer must resist |
| APH/AAC | Aminoglycoside phosphotransferase / acetyltransferase | T1/T2: self-protection or routing; also common housekeeping |
| Erm_methylase | Erythromycin ribosome methylase | T1 diagnostic: typically paired with macrolide biosynthesis |
| VanHAX_like | Vancomycin resistance cluster | T1 diagnostic: paired with glycopeptide biosynthesis |
| Fosfomycin | Fosfomycin resistance | T1 diagnostic |
| Self_resistance_general | General self-resistance annotation | T2: supportive but non-specific |

**Resistance tiers:**

- **T1** — diagnostic self-protection co-located with biosynthetic genes
- **T2** — resistance-like but not directly diagnostic
- **T3** — transporter-only routing (efflux without biosynthetic coupling)
- **NULL** — no source-derived resistance detected

**Proximity rule:** a resistance marker only counts toward a lead if it sits *near* the BGC. A genome-wide β-lactamase elsewhere on the chromosome is not self-protection evidence for a distant cluster.

---

## BGC-inventory and fragmentation tiers

→ *Concept and claim-ceiling role: **Core concepts #6**. Keep the two fields separate.*

`assembly_tier` is derived only from the proportion of BGC calls that are Interior:

| `assembly_tier` | Interior-BGC percentage | Meaning |
|---|---|---|
| GOOD | ≥70% | Most called regions avoid contig boundaries |
| MODERATE | ≥45% | Mixed boundary recovery |
| POOR | ≥20% | Many called regions meet contig boundaries |
| VERY_POOR | <20% | Most called regions meet contig boundaries |
| UNKNOWN | unavailable denominator | Boundary-recovery tier cannot be computed |

`fragmentation_tier` is a separate ordered contig/N50 classification. The first
band satisfying both limits wins:

| `fragmentation_tier` | Current ordered band |
|---|---|
| CLOSED | ≤2 contigs and N50 ≥1,000,000 bp |
| CONTIGUOUS | ≤20 contigs and N50 ≥500,000 bp |
| DRAFT | ≤100 contigs and N50 ≥100,000 bp |
| FRAGMENTED | ≤1,000 contigs and N50 ≥10,000 bp |
| HIGHLY_FRAGMENTED | valid contig count but no earlier band matches |
| UNKNOWN | contig count unavailable or invalid |

Fragmented, highly fragmented, or unknown contiguity requires an explicit
caveat: BGC counts are floors, not measurements. Neither tier establishes a
compound, production, activity, or publication claim.

---

## Key metrics

| Term | Meaning |
|---|---|
| KCB cumulative score | Sum of KnownClusterBlast protein hit scores vs MIBiG; higher = closer match to a known cluster |
| KCB protein hits | Number of proteins with significant KCB hits; more hits = more complete match |
| MIBiG | Minimum Information about a Biosynthetic Gene cluster database; reference collection of known BGCs |
| Corrected BGC count | Interior + 0.5 × Edge + 0.25 × Full-contig; the defensible BGC inventory figure |
| Interior % | Fraction of BGCs fully inside contigs (not truncated at edges) |
| N50 | Contig length at which 50% of the assembly is in contigs this size or larger; proxy for assembly contiguity |
| RGGMCI | Reference-Guided Genome Mining Candidate Inference; the mandatory pre-triage, homology-guided linkage of fragmented BGC regions to a shared reference producer cluster (ClusterBlast/KnownClusterBlast) |
| Mode B | Expanded §1–§48 per-BGC interpretation protocol: exact-locus identity, canonical gene roster, channel-separated evidence, architecture, tailoring, resistance, product class, provenance, caveats, decisions, and claim-safe verdict |
| DAPR | Dual Antibacterial/Antifungal Prioritization Ranking — the two parallel top-3 lead tracks |
| Hallucination trap | A check applied to every BGC to catch over-interpretation of generic or ambiguous domain annotations |
| Wet-Lab / WL score | A downstream experimental-priority metric emitted by selected judgment tools. It is separate from the Mamey triage tier and must identify its own versioned inputs and rule. |

---

## Claim-safety vocabulary

→ *The discipline in full: **Core concepts #13**. The complete term list is below.*

The bundle's central discipline. These terms govern how confident any statement is allowed to be.

| Term | Meaning |
|---|---|
| Biosynthetic capacity | The permitted way to describe what a cluster *could* make. "Biosynthetic capacity consistent with a glycopeptide" — never "produces vancomycin." |
| Claim ceiling | The maximum confidence a statement may reach for a given evidence level. Fragmented assemblies, KCB-dark clusters, and edge clusters all lower the ceiling. |
| `[EG]` / `[VL]` | Evidence-tag on a verdict. `[EG]` = *evidence-grounded* but not literature-verified (provisional); `[VL]` = *verified against literature*. A project identifier or privacy tier never upgrades the tag. |
| Architecture Confidence | The A–E grade (above), reported alongside every claim so a reader sees the structural basis. |
| Evidence Traceability | A block linking each claim back to the specific scan/hit that supports it. |
| ~ (tilde) | "Resembles, is not." Prefixes any known-compound name attached by KCB (e.g. "~kijanimicin"). Similarity, not identity. |
| Bioactivity metadata | Optional typed strain-level context; omission is `NOT_SUPPLIED`, and any observation is never attributed to a BGC without governed linkage. |
| Missingness vs absence | "Not found in this assembly" (a fragmented genome may simply not contain the region) is reported as *missingness*, never as proof a gene is *absent*. |

---

## Evidence, identity, portability, and authority vocabulary

These terms describe how the portable application finds and binds external
evidence, how Mode B reports readiness, and how release tooling separates a
candidate from an authorized release.

| Term | Meaning |
|---|---|
| Exact-locus identity | The mandatory display and join identity for one BGC: `strain / full node-or-contig / region / BGC alias`. The alias is last and source-scoped. Missing components cause a hold; they are never guessed. |
| Source object | An external evidence file or dataset represented by its source role, logical locator, SHA-256, byte count, and binding/admission state. A path, filename, timestamp, or duplicate copy is not source authority by itself. |
| Logical locator | A portable reference such as `evidence://root-id/path` that resolves through runtime configuration. Machine-specific absolute paths may be supplied at runtime but do not enter portable or public reports. |
| Discovery catalog | A bounded inventory of candidate collections. `DISCOVERED_NOT_ADMITTED` means exactly that: discovery proposes material for review and does not authorize consumption. |
| Admission / collection decision | The explicit disposition `CONSUME`, `REJECT_WITH_REASON`, or `SUPERSEDED_WITH_RECEIPT` for a hash-bound collection. Admission permits a workflow to read named bytes; it is not scientific acceptance. |
| Exact-locus evidence states | `EXACT_LOCUS` is bound to strain, full node/contig, and region; `ALIAS_BOUND` lacks an independent full locator; `STRAIN_ONLY` is context only; `UNBOUND` cannot yet join; `ABSENT` means no matching artifact in the configured scope. `UNBOUND` and `ABSENT` are workflow states, not biological negatives. |
| Evidence-readiness states | `READY_BOUND` may be integrated; `AVAILABLE_UNINGESTED` must be ingested first; `NEAR_READY_ACTIVE_RUN` remains blocked while a run completes; `PRACTICALLY_ATTAINABLE` should be obtained before content QA; `STRUCTURALLY_UNAVAILABLE` and `NOT_APPLICABLE` require a typed reason. |
| Gene-first / sequence-first review | Build the canonical gene roster before prose and preserve its order. Bind a protein result by the exact locus plus protein SHA-256; a locus tag or similar name alone does not prove sequence identity. Every canonical gene remains in the denominator, including boundary/context genes. |
| Channel-separated BLASTp | NCBI nr, NCBI ClusteredNR, and local Swiss-Prot are separate evidence channels with separate named-match, alignment-metric, state, and coverage fields. Missing or unbound evidence in one channel is never filled from another. ClusteredNR is not nr; percent positives is not percent identity; similarity is not functional proof. |
| `document_state` / `evidence_state` | Two orthogonal Mode B axes. `document_state` says where the card is in the authoring/review ladder; `evidence_state` records bound, unbound, quarantined, unavailable, or not-applicable evidence. A mechanically validated state is not maintainer acceptance or publication approval. |
| Privacy profile | User-owned policy mapping exact strain IDs to named access tiers. Unassigned strains inherit a required non-public default. Only a tier explicitly marked `public_export: true` maps to package `PUBLIC`; all others map to `PRIVATE`. Privacy policy is not scientific evidence or publication approval. |
| Package `PUBLIC` / `PRIVATE` | A binary export label used by package consumers. It is derived fail-closed from the active privacy policy and does not replace staged-tree leak audits, governance decisions, or publication authorization. |
| Release/archive transaction states | **Source tree**, **staged tier tree**, **archive candidate**, and **verified archive** are distinct objects. A clean source does not prove the stage; a clean stage does not prove the ZIP; a matching ZIP or local gate does not promote a candidate. `PUBLIC_RELEASE` is a separately authorized promotion state; a CODE or `NOT_FOR_PUBLIC_RELEASE` candidate is not one. |
| Portable / offline core | The application, small reference assets, vendored fallbacks, and local wheel paths are designed to run without network access. Optional commands whose names or help explicitly say online may contact their named service and must retain provenance; their absence is an evidence gap, not a failed core extraction. |
| Sealed package | A package that passed the deterministic extraction and package-integrity gates for its recorded engine and inputs. `MAMEY_COMPLETE` means that extraction handoff is complete; it does not mean Sapote judgment, biological validation, acceptance, release, or publication is complete. |
| Post-seal tool | An additive consumer of an already sealed package, such as Mode B, domain-level, receipt ingestion, comparison, cohort, or figure tooling. "Post-seal" and "non-blocking" mean the core extraction does not depend on it; they do not guarantee the added output is complete, correct, accepted, or release-ready. |
| Mechanical gate / authority ceiling | A validator may establish schema, hash, identity, or completeness facts only. It cannot grant scientific acceptance, owner acceptance, integration, release, or publication authority unless a separate governing decision explicitly does so. |

Contract sources: `PORTABLE_EVIDENCE_WORKSPACE.md`,
`MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md`,
`MODE_B_SUPPORT_CARD_CONTRACT.md`,
`MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md`,
`PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md`, and the release tools under `tools/`.

---

## Standing biological constraints

Permanent rules, learned across many strains, that override case-by-case interpretation. They exist to stop recurring over-claims.

| Constraint | Rule |
|---|---|
| NAPAA | NAPAA (poly-amino-acid class) | Registry-neutral: listed but not interpreted, neither downgraded nor lead-blocking (rules registry `status: neutral`). Common and frequently adjacent to genuine BGCs, so it carries no comparative weight on its own. The Nosema/glucocerebrosidase hypothesis is retired. |
| hglE-KS-PREV-001 | The hglE-KS glycolipid domain is prevalent and habitat-non-specific (confirmed across many strains, multiple genera, all three habitats). Habitat-specific claims are retired; its structural novelty (zero KCB) still stands. |
| Saccharide-gating null | Pure-saccharide clusters (carbohydrate machinery with no specialist warhead) are omitted from comparative counts; the polysaccharide-gating signal was confirmed null in the bryophyte and attine sets. |
| Multi-siderophore flag | Carrying several siderophore systems recurs across many strains; treated as an iron-economy observation, not a per-strain distinction. |
| T43-ENE / [E-signal] | A genuine enediyne (`ene_KS`) carries an [E-signal] claim-safety note — cytotoxic/DNA-damaging class; cytotoxicity/self-protection review, handling per standard lab SOPs (no selective BSL-2 gate — selective biosafety flags give false reassurance). Confirm a genuine `ene_KS` call vs an `hglE-KS` cross-reaction at the gene level first. (Defers to encyclopedia Vol VIII glossary.) |

---

## Validation vocabulary

Terms used in the external-validation record (runs on public reference genomes that test whether the pipeline behaves).

| Term | Meaning |
|---|---|
| Type strain | The designated reference isolate for a species, with a public, well-characterised genome. Used as a known-answer test. |
| Positive control | A genome whose chemistry is known in advance (e.g. MAR4 marine *Streptomyces* and its halogenated meroterpenoids); the run should recover that signature. |
| Negative control | A genome expected *not* to light up (e.g. *Deinococcus radiodurans*); guards against false positives. |
| Blinded prospective validation | Running the pipeline on a genome before checking the literature answer, so the call can't be tuned to fit. |
| Corrected-vs-raw percentile | The validation figure's axis: a strain's BGC-count rank before and after the correction. High-retention genomes rise; fragmented ones fall. The point is that the *corrected* count tracks quality, not raw abundance. |

---

## Ecological habitats & host systems

The cohort spans three symbiotic niches; these words appear in strain descriptions and chapter titles.

| Term | Meaning |
|---|---|
| Attine / fungus-garden | Fungus-growing ants and the actinomycetes associated with their gardens (e.g. *Pseudonocardia*, *Amycolatopsis*); a classic defensive-symbiosis source of antifungals. |
| Bryophyte / lichen | Mosses, liverworts, and lichens and their associated actinomycetes; one of the three habitat sets. |
| Hymenoptera / bee | Bees and wasps and their symbionts (e.g. *Streptomyces philanthi*, the beewolf symbiont); the third habitat set. |
| Fungus-growing termite | An independent insect-fungiculture system (e.g. *Macrotermes*); a natural cross-system comparator to the attine ants. *Actinomadura macrotermitis* RB68 is the bundle's public termite-symbiont validation genome. |
| Actinomycete | The bacterial group (Actinomycetota) that dominates this project; prolific producers of natural products. Genera here include *Streptomyces*, *Amycolatopsis*, *Pseudonocardia*, *Saccharothrix*, *Micromonospora*, *Nocardia*, *Actinomadura*, *Sciscionella*. |

---

## Release tiers & gates

How the bundle is staged for distribution. Tier construction, package privacy,
and promotion to a public release are separate controls.

| Tier | Contents | Purpose |
|---|---|---|
| CODE | Data-free: engine, tools, docs, templates. No banks, no internal working docs. | The GitHub-push artifact. |
| CODE-analysis-free | A lean CODE variant with selected analysis outputs removed. | Smaller code/tool handoff. |
| SID-public | CODE + the public SID cohort banks (the SID strains carry public GenBank/GCA genomes). | The supplementary data archive. |
| MERGED-PRIVATE | Everything, including `private/` and real AS identifiers. | The private scaffold; never published. |
| PUBLIC-RELEASE | A separately authorized public promotion cut. | Publication/distribution only after the active governance and archive gates pass. |

| Gate | Meaning |
|---|---|
| Technical release gates | Schema, tests, identity, checksum, membership, derivation, and content-audit checks. Passing them creates technical evidence only. |
| Governance gate | A separately active, signed, non-invalidated decision required for `PUBLIC_RELEASE`; candidate tiers remain candidates without it. |
| Leak/content audit | The staged public tree is checked for disallowed cohort identifiers, private paths/content, forbidden payloads, and other configured leaks. The archive still requires its own identity/integrity verification. |

---

## Failure / status codes

| Code | Meaning |
|---|---|
| `INPUT_MISSING` | Required input file not present |
| `MAMEY_FAILED` | Deterministic scan failed; reason required |
| `UNSUPPORTED_ACCESSION_MODE` | Accession-only run requested; must supply antiSMASH ZIP |
| `ANTISMASH_PARSE_FAILED` | antiSMASH output could not be parsed |
| `WORKBOOK_SCHEMA_CONFLICT` | Workbook columns do not match required schema |
| `PACKAGE_QA_FAILED` | Package manifest, checksums, or required files missing |
| `RECOVERY_NEEDED` | Partial output exists; exact recovery inputs listed |
| `DEFERRED` | Item intentionally deferred; reason and completion path required |
| `MAMEY_COMPLETE` | Package passed all deterministic extraction/handoff gates for its recorded inputs; Sapote judgment, acceptance, release, and publication remain separate |

---

## Plain-language terms (overloaded everyday words)

The bundle reuses a lot of ordinary English words as technical terms. This
section is for readers who hit a familiar word being used in an unfamiliar way.
It is not an exhaustive glossary of the abbreviations above — only the common
words that carry a special meaning here.

### Names

| Name | What it means here |
|---|---|
| Mamey | The deterministic engine: the Python layer that parses antiSMASH output and extracts the BGC inventory. It does no biological interpretation. |
| Sapote | The judgment layer: interprets Mamey's output and writes the claim-safe reports. Mamey + Sapote together = the bundle. |
| Bert / Davey / Eden | Retired internal mode names. Now "Verified Literature Deep Dive," "Rapid Literature Deep Dive," and the summary-table workflow. Kept here only because the old names may still appear in some files. |

### Overloaded common words

| Word | Everyday meaning | What it means in Sapote–Mamey |
|---|---|---|
| Gate | a fence opening | A bounded validation checkpoint. Its name and receipt must say what it checked; passing one gate does not imply scientific, acceptance, integration, release, or publication authority. |
| Cassette | a tape | A reusable biosynthetic logic pattern in the registry, used for marker-aware scoring. |
| Marker | a pen / signpost | A literature-backed diagnostic signature that flags a specific biosynthetic capability. |
| Arm | a limb | A glycosylation arm: sugar-tailoring genes sitting outside the core BGC boundary. Reported as evidence, not proof of physical linkage. |
| Scan | to look over | One detection-module pass (CCTT, CGAD, EFLS, etc.). Each BGC carries "scan states." |
| Sweep | to clean | A scoring pass across a whole reference database. The KCB sweep scores every BGC against MIBiG. |
| Triage | ER prioritizing | Ranking BGCs by promise. The "triage board" is the ranked output. |
| Board | a plank | A results table: Lead Board, Hive Board, Triage Board. |
| Lead | to guide / the metal | A prioritized BGC candidate worth pursuing. Raising lead priority never raises claim confidence. |
| Kernel | a seed | The Slim Judgment Kernel: the condensed instruction core that drives Sapote's behavior. |
| Monolith | a stone slab | The single large parent-controller document. It wins over everything except the deliverable contract. |
| Manifest | a cargo list | Two senses: the `manifest.json` handoff object Mamey emits, and the release manifest listing shipped files. |
| Ledger | an account book | The append-only audit log of findings. |
| Freeze | to turn to ice | A locked baseline that must not drift: schema freeze, frozen release candidate, freeze-triage. |
| Constellation | stars | An evidence constellation: a set of co-occurring signals reported together instead of as one over-claim. |
| Edge | a border | A contig edge: where a BGC is cut off at the end of a contig, so it may be truncated or incomplete. |
| Flank | a side | The region beside a contig edge; EFLS looks here for the other half of a split pathway. |
| Warhead | a missile tip | The reactive chemical group that gives a compound its bioactivity (e.g. a β-lactone electrophile). |
| Rescue | a save | A candidate inference that relates fragments split across contigs. FLBR finds fragments and RG-GMCI/related tools propose linkage; they do not reassemble or physically join the contigs. |
| Census | a population count | FLBR's tally of fragmented megasynthase sets across contigs. |
| Banked / Bank | money in a bank | The stored cross-session cohort state (`cohort/`) that the master workbook is built from. |
| Handoff | a relay pass | The structured transfer of data from Mamey to Sapote (and between the execution and judgment layers). |
| Trap | a snare | A hallucination trap: a deliberate check on every BGC to catch over-interpretation of generic domains. |
| Card | a playing card | A structured per-item write-up: a Mode B card per BGC, or an A5 fermentation card. |
| Corrected | fixed | The assembly-quality-adjusted BGC count (vs. the raw antiSMASH region count). |
| Tier | a level | A named band whose meaning depends on the field: evidence tier, Mamey routing tier, privacy tier, or release tier. Never compare two "tiers" until their namespace is clear. |
| Atlas | a map book | The interactive BGC Atlas HTML tool. |
| Hub | a center | The master Hub workbook that integrates every workstream. |
| Register | a record book | A structured ledger such as a missingness, judgment, or output register. A missingness row records a workflow observation, not proof of biological absence. |
| Contract | a legal agreement | The deliverable contract: the spec defining which outputs a run must produce. It outranks the monolith. |
| Anchor | a ship's weight | A publicly reproducible reference point (KCB anchor, calibration anchor) that grounds a threshold. |
| Floor | the ground | A minimum a score cannot drop below. A Tier-1 diagnostic "floors" a BGC's priority score. |
| Ceiling | the roof | A maximum a claim cannot exceed. The claim ceiling caps how confident a statement is allowed to be. |
| Band | a stripe / group | A prevalence bracket (e.g. core / common / rare) used to judge whether a class is informative for comparison. |
| Proximity | nearness | The proximity rule: a resistance marker only counts toward a lead if it sits near the BGC. |
| Snapshot | a quick photo | The Project Memory Snapshot: a captured cross-session state of a strain's analysis. |
| Split | to divide | A split pathway: one biosynthetic pathway whose genes are spread across two or more contigs (Split-A / Split-B). |
| Routed out | sent away | A class deliberately excluded from a track (e.g. cytotoxic-adjacent classes routed out of the antibacterial lead track). |
| Verdict | a court ruling | A Mode B verdict: the confirm/drop call on whether a candidate is genuine. |
| Profile | a silhouette | A scan profile: the assembled per-BGC summary of all scan results. |
| Pack | a bundle | A judgment pack or prompt pack: a grouped set of inputs or instructions handed off as one unit. |
| Guard | a sentry | An audit-finding guard (G1–G6): an automated check that fails the build if a known defect reappears. |
| Trigger | a switch | A CCTT trigger: a specific biosynthetic signal (halogenase, lanthipeptide, etc.) that fires a flag. |
| Axis | a graph line | One independent evidence question, such as structure, similarity, novelty, diagnostics, regulation, or authored judgment. A versioned builder may combine selected axes, but the combination is not a biological truth score. |
| Class | a school group | Either a biosynthetic/compound class or a legacy A/B/C lead overlay, depending on context. Neither is the Mamey routing tier, and neither raises the claim ceiling. |
| Dark | absence of light | KCB-dark: a cluster with no KnownClusterBlast match — unknown, possibly novel, easy to under-rank. |
| Tilde (~) | approximately | "Resembles, is not" — the similarity marker before any known-compound name. |

---

## Versioned implementation notes

This appendix helps readers interpret historical outputs. It does not create a
second definition or freeze counts and formulas across releases. Check the
named current code, registry, or schema before using an implementation detail.

*Historical v9.7.85 scoring fix: keyword credit changed to score a BGC's own
product classes rather than class tokens in its KCB anchor's genome-description
text. This note explains old output and is not a current-version label.*

| Term | Full name | What it means in plain English |
|---|---|---|
| Marker registry | Governed evidence library (`mamey/mamey_markers.py`) | The versioned detection-marker set spanning domain-class, CCTT, regulator, TFBS, maturation, resistance, transporter, chitin/glycan, and fragment-rescue libraries. Each marker has a stable ID, evidence tier, and claim ceiling. Query the current registry for its count; do not copy an older fixed total. |
| CCTT / T43 | Class-trigger framework | The versioned T43 trigger set in `mamey/source_scans.py::CCTT_PATTERNS`. When a class-defining trigger is corroborated on a compatible locus it may drive the current diagnostic bonus and Medium floor; tailoring-only/promiscuous triggers do not receive that floor by themselves. Query the current registry for families and weights. |
| Standing-rule downgrade | Permanent-exclusion cap | A rule that downgrades or excludes a non-informative class from comparative claims: saccharide and hglE-KS/hexacosalactone (habitat-non-specific). Scores are preserved for audit; the class is simply set aside from cross-strain comparison. (NAPAA is *not* in this set — it is registry-neutral.) |
| RiQ | Reference-information quotient | A region-mapped novelty signal from the `bounded`/`full` JSON evidence: low RiQ (< 0.5) means the region is distant from its closest MIBiG reference → a small novelty increment. Exempt from the evidence record cap. |
| RG-GMCI | Reference-guided multi-contig inference | Homology-guided shared-reference linkage across contigs — proposes two fragments on different contigs are one split pathway when they share MIBiG references. **Does not join contigs at the nucleotide level.** Its bonus (HIGH +8 / MODERATE +4) is routing priority, not claim confidence; promiscuous-hub and distant-reference pairs are down-weighted. |
| Edge penalty | (removed v9.7.84) | A score deduction for BGCs on a contig edge, **removed in v9.7.84**. It had no measurement basis (edge BGCs show no truncation signature in their base score) and was burying overlooked edge fragments at the tier threshold. Truncation is now carried as a confidence grade (architecture C/D), not a score deduction. The corrected-count weight (Interior 1.0 / Edge 0.5 / Full-contig 0.25) is separate and unchanged. |
| Judgment store / register | Mode B persistence layer | The per-package store (`<strain>_judgment_register.json` + `judgment/*_mode_b.md`) that holds Sapote's Mode B cards durably. Without it, a Mode B card lives only in chat and is lost when the session ends. |
| Mode B receipt | `mode_b_receipt.json` | The JSON a Sapote session emits at the end of a Mode B batch (`{strain_id, session_id, cards:[{bgc_id, mode_b_md, …}]}`). `mamey ingest-receipts` consumes it to persist the cards into the judgment store and reconcile the workbook's E1 sheet. Fail-closed (unknown BGC skipped, never invented) and idempotent. |
| `doctor` / `inspect` / `explain` / `list-bgcs` | Read-only package commands (v9.7.83) | `doctor` pre-flight-checks the environment; `inspect`/`explain` summarize a sealed package; `list-bgcs` prints the BGC inventory (with `--json`). None re-run extraction. |

### RG-GMCI rescue layer (added v9.7.100 / engine 1.9.98)

*The v9.7.100 cut reworked how RG-GMCI uses ClusterBlast evidence and added a physical (coordinate-based) rescue path. These five terms are the new fields you will see on the 4A ranked-pairs output and in Mode B cards. All remain candidate inference — none joins contigs at the nucleotide level.*

| Term | Full name | What it means in plain English |
|---|---|---|
| db_kind / CB–KCB separation | ClusterBlast database-of-origin tag | Each shared-reference hit is now tagged by which antiSMASH file it came from: **knownclusterblast** (a characterized MIBiG cluster — tells you the likely product class), **clusterblast** (a cross-genome GenBank neighbour — tells you two fragments co-occur in real genomes), or **subclusterblast** (sub-operon hits — *excluded* from rescue geometry). Earlier code blind-merged all three because the word "clusterblast" is a substring of all of them; separating them is what surfaces clusterblast-only rescues a KCB-only path would miss. |
| rescue_evidence_base | Which databases corroborate a pair | Per rescued pair, records whether the linkage is supported by **BOTH_KCB_AND_CB** (strongest), **CLUSTERBLAST_ONLY** (real genome neighbours but no characterized match — the common case for novel clusters), or **KNOWNCLUSTERBLAST_ONLY** (characterized-cluster identity without cross-genome corroboration). Observational; it does not by itself change the score. |
| functional_rescue_class | Gene-role complementarity of the two fragments | Compares the biosynthetic gene roles (core / tailoring / transport / regulatory) on each fragment using **core-fraction asymmetry**: **COMPLEMENTARY** (one fragment carries the core, the other the accessory genes — what a real split looks like), **BOTH_CORE** (both carry a near-complete core → paralogous clusters, *not* a split), or **ACCESSORY_ONLY** (two accessory fragments; weak). A cross-check on the subject-tiling verdict, not a standalone call. |
| subject-tiling verdict | Disjoint-vs-shared reference subject genes | Reads which genes of a shared reference cluster each fragment hits: **COMPLEMENTARY_SPLIT** (disjoint subject genes = two halves of one cluster), **OVERLAPPING_PARALOG** (shared subject genes = independent paralogous clusters), or MIXED/INSUFFICIENT. Gated to avoid calling every low-signal pair a split. |
| Terminus-truncation rescue / TERMINUS_TRUNCATION_SPLIT | Coordinate-confirmed split at a contig break | The simplest, most certain rescue: an **Edge** region whose boundary sits *at* the contig terminus is a cluster sliced by the assembly break. When paired with a small (≤25 kb) complete-contig "severed arm" or a shared *specific* biosynthetic class, it is flagged TERMINUS_TRUNCATION_SPLIT and **overrides** an OVERLAPPING_PARALOG verdict that rests on a gene class which is legitimately multi-copy *within one* cluster (e.g. the bottromycin RRE/methyltransferase). The paralog call is preserved for genuine paralogs. Produces candidates, not confirmed joins — a small contig can be the severed arm of only one cluster, so where it pairs with several Edge regions the evidence base + functional class disambiguate; physical confirmation still needs long-read / gap-PCR. |

---

*Maintenance note: this glossary is the reader-facing canonical source for term
definitions. When a new scan, code, or overloaded term enters the bundle, add
or revise the definition here and point other documents here. Keep counts,
formulas, and status enumerations tied to their code/schema source and keep
claim-safe framing in every definition.*

*Maintenance note: version-sync marker for the installed engine 1.9.152.*

---

### Historical additions from v9.7.141–v9.7.147

| Term | Full name | What it means in plain English |
|---|---|---|
| Ranthipeptide | Radical SAM RiPP subclass | A ribosomally synthesised and post-translationally modified peptide (RiPP) associated with radical-SAM maturation, a recognition element, and a precursor peptide. Additional tailoring can diversify the predicted scaffold. A specific locus still requires the complete exact-locus identity and gene-level evidence; class membership alone is not product identity. |
| §28 — Evidence provenance ledger | Mode B card section 28 within the current §1–§48 profile | A per-claim table recording the factual claim, evidence tier, source file or field, engine version, confidence, and update trigger. It supports surgical revision but does not itself validate the claim. |
| §30 — Experimental decision tree | Mode B card section 30 within the current §1–§48 profile | A structured set of unresolved questions, resolution experiments, expected card changes, and downstream consequences. It turns a card into a research plan without implying that any experiment has been performed. |
| ChatGPT Execution Slice | `docs/CHATGPT_EXECUTION_SLICE_v97147.md` | The default ChatGPT/Sapote execution controller as of v9.7.147. Replaces `SAPOTE_SLIM_JUDGMENT_KERNEL.md` in all default load paths. Contains full-depth, non-abbreviated rules: no scope-negotiation, no abbreviated Mode B, edge/FC equality enforced, §28/§30 required, post-MAMEY_COMPLETE handback mandatory. |
| POOR-tier edge equality | Edge/FC equal-visibility rule (v9.7.147) | In POOR or VERY_POOR assemblies (< 45% interior BGCs), the interior/edge/full-contig distinction is primarily an assembly artefact, not a scientific signal. All BGCs appear in the triage board sorted by corrected_rank (score), not Interior-first. Edge/FC BGCs receive full Mode B depth; boundary status appears as a caveat in §3 and §19 only, not as a reason for abbreviated treatment. The Wet Lab Matrix edge/FC −2 penalty is also suppressed for POOR/VERY_POOR assemblies. |
| Mamey-first gate | Workflow enforcement rule (v9.7.146) | A rule in CLAUDE_START_HERE.md and the ChatGPT Execution Slice: Mode B, DAPR, triage, or any Sapote interpretation is refused without a sealed Mamey package. The package provides correct boundary computation (flanking-buffer analysis, not just the raw contig_edge flag), WL/AB/AF scores, CCTT triggers, and cluster-level KCB that cannot be reproduced from raw antiSMASH output. Offline analysis (explicitly requested) is permitted with an explicit flag on every fact that would change with a Mamey run. |
| Deliverable Menu | `docs/DELIVERABLE_MENU_v97146.md` | A diner-menu-format document listing all deliverables the pipeline can produce, grouped by audience (quick orders, full meals, sides, specials). Each item has a plain-language description and a trigger phrase. Presented at MAMEY_COMPLETE. Replaces the technical deliverable list in SESSION_START_MANIFEST as the user-facing entry point. |
| verify_checksums | Package integrity function (v9.7.145c) | A function in `mamey/validate.py` that recomputes SHA256 for every line in `checksums_sha256.txt` and returns a list of errors. Mutable post-seal files (`run_phase_receipts.jsonl`, `package_status.json`) are excluded from the check because they are appended after checksum generation by design. Now wired into `validate_package()` — a corrupted non-mutable file causes `status: FAIL`. |
| PATCH-PACKAGING-SEAL | Checksum ordering fix (v9.7.146) | The fix to `mamey/packaging.py` that corrects the root cause of recurring checksum failures: `write_manifest()` now excludes mutable post-seal files from the checksum set *before* hashing, so `checksums_sha256.txt` is always self-consistent at the moment of writing. Prior to v9.7.146, receipts appended after the checksum was computed caused mutable-file mismatch on every `sha256sum -c` run. |
| Interpretive floor | Per-section minimum depth (v9.7.146) | The minimum reasoning requirement for Mode B sections §5, §9, §11, §12, and §19, defined in `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md`. §5 must connect domain architecture to structural consequences. §9 must weigh alternatives with evidence. §11 must connect tailoring complement to scaffold complexity. §12 must name the ecological mechanism with a literature anchor. §19 must argue the verdict, not restate §11. |
| ENGINE_LINEAGE.md | Engine version governance document (v9.7.145) | `docs/ENGINE_LINEAGE.md` records every engine version bump with: old/new engine, first bundle carrying the new engine, reason for bump, whether scoring semantics changed, and tests run. `sync_version.py --check` exits non-zero if the current engine version has no entry here. Motivated by the undocumented 1.9.99→1.9.100 bump at v9.7.142. |
| TRIGGER_ROUTING.md | Canonical trigger routing table (v9.7.145) | `docs/TRIGGER_ROUTING.md` is the single authoritative table for what happens when any named trigger fires (workflow triggers, quality-gate triggers, biology-escalation triggers, routing conflict guards). Previously the routing was scattered across multiple prompt documents. All future trigger definitions go here first. |

*Historical note: the rows above entered during the named version window.
Their current definitions and gates remain controlled by the present code and
schema, not by the historical introduction label.*
