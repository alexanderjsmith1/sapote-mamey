# Sapote–Mamey — External Validation Record

> **Historical observations; current acceptance held.** The table/narrative below records v9.6.x-era reports, not an independent current-cut validation receipt. Their software labels, ecological/chemical interpretations, original input files, full locus identities and run claims need their original source and run receipts before reuse. Missing/partial accession fields and bare BGC aliases are identity holds; do not infer missing contigs/regions or transfer findings to a current package. These reported runs cannot certify .447 whole-suite accuracy, current standalone behavior, biological production/activity or manuscript adoption.
>
> `resources/validation_runs.csv` is a historical plotting input, not a complete authoritative experiment ledger: it lacks per-row input/cut/receipt hashes and includes later rows absent from this six-run table. Two later rows have unreconciled retention values relative to raw/corrected pairs (51/50.5 with 31; 67/67 with 22). Preserve them as observations pending definition/receipt recovery; do not silently recalculate or present a regenerated figure as reconciled validation. See [resource limits](../resources/README.md) and [older validation records](../validation/README.md).

*Blind/external validation of the public **CODE tier** (data-free, no banks) on **public NCBI genomes** —
a mix of type strains and other public isolate assemblies, independent of the symbiont discovery cohort. Updated as runs accrue. All statements are class-level and
KCB-anchored (similarity, not identity); bioactivity metadata is optional strain-level context; these are public
type-strain genomes, so no ecological/symbiont claims attach to them.*

## Why this exists
The discovery cohort is unpublished symbiont strains. A reviewer (or a future user) needs to see the pipeline
work on **public, independent genomes it was not tuned on**. Each run below is the public CODE bundle, run
end-to-end with **no banks present**, on a fresh public NCBI genome. The record is committed so the evidence ships
with the code.

## Runs (public NCBI genomes)

| Strain | NCBI accession | Niche | Engine | Raw | Corrected | Assembly | Retention | Raw→Corr pct |
|---|---|---|---|---|---|---|---|---|
| *Actinomadura rugatobispora* | type | type strain | v9.6.11 | 75 | 75.0 | GOOD | 100% | 99th → 99th |
| ***Actinomadura macrotermitis* RB68** | ASM960437v1 | **termite symbiont** | v9.6.11 | 60 | 59.5 | GOOD | 99% | 58th → 98th |
| *Micromonospora humida* | GCA — JAFEUC… | type strain | v9.6.2 | 60 | 51.25 | GOOD | 85% | 58th → 94th |
| *Micromonospora* sp. WMMA1998 | — | marine | v9.6.11 | 42 | 42.0 | GOOD | 100% | 31st → 83rd |
| *Streptomyces griseoluteus* JCM 4765 | GCA_014656035.1 / BNBQ01… | soil | v9.6.2 | 44 | 39.25 | GOOD | 89% | 34th → 81st |
| MAR4-lineage marine *Streptomyces* | GCF_048656465.1 / NZ_JBMDLF… | marine | v9.6.2 | 41 | 37.25 | GOOD | 91% | 29th → 80th |

*All `MAMEY_COMPLETE`, end-to-end, data-free CODE bundle — **six consecutive clean external runs** spanning soil,
marine, type-strain, and now a **termite-symbiont** genome, across *Streptomyces*, *Micromonospora*, and
*Actinomadura* — diverse genomes the pipeline was not tuned on. (A private VERY_POOR attine symbiont, ≈37%
retention, is plotted de-identified as the fragmented contrast point.)*

**Figure.** `figures/validation_panel_corrected_vs_raw.png` (data: `resources/validation_runs.csv`, regenerate with
`tools/build_validation_panel.py`). Raw vs corrected BGC-count percentile against the 96-strain panel; the y=x line
is the only non-data element. The six public genomes sit **on or above** the line (high retention holds or floats
their rank: 80th–99th corrected); the fragmented symbiont sits **below** (it loses percentile on correction).
The corrected count, not the raw count, is the honest measure of resolved biosynthetic potential.

## What these runs validate

1. **The CODE artifact runs standalone.** The public, data-free bundle goes end-to-end with no `cohort/` banks
   present — a passing release test for the artifact that would actually be deposited, not just the working tree. (The
   external set is a mix: *A. rugatobispora* and *M. humida* are type strains; RB68, MAR4, and *Micromonospora* sp. WMMA1998 are
   other public isolate genomes — the point is breadth of independent public data, not type-strain status per se.)

2. **The corrected-count logic tracks assembly quality, not raw abundance.** S. griseoluteus sits *below* the
   median on raw count (34th pct) but high retention (89%) floats it to the 81st pct corrected — the inverse of a
   fragmented assembly, where a high raw count collapses on correction. Against a private VERY_POOR symbiont
   assembly (≈37% retention), the same logic cleanly separates the two regimes: high-retention public genomes
   resolve to the 80th–99th corrected percentile; the fragmented symbiont drops below its raw rank. The corrected
   count = Interior + ½·Edge + ¼·Full-contig is doing real discriminating work.

3. **The v9.6.2 diagnostic-floor fix generalizes (not overfit to the discovery cohort).** On *M. humida*, a
   `T43-NUC` nucleoside trigger fired on **BGC034**, whose KCB anchor is a bare chromosome hit — KCB-dark, the
   exact failure mode that had buried the discovery-cohort nucleoside at Inventory. The TIER_1 diagnostic floor
   surfaced it to **Medium / AF 46** on this unrelated genome, confirming the fix catches the next KCB-dark
   antifungal rather than a single tuned case. *(S. griseoluteus carried no nucleoside locus, so it does not
   exercise this path — noted for honesty: not every run tests every fix.)*

4. **A standing cross-cohort finding is independently corroborated.** `hglE-KS` appears in the top *M. humida*
   lead (BGC021, a bottromycin/lasso/hglE-KS megalocus) — a Micromonospora type strain, neither symbiont nor the
   habitats where the signal was first seen — consistent with `hglE-KS-PREV-001` being genus- and
   habitat-non-specific (its structural-novelty status stands; no habitat-exclusive claim).

5. **The pipeline recovers a characterized lineage's known chemistry (positive control).** On the MAR4
   marine *Streptomyces* (`GCF_048656465.1`), the run surfaced **6 halogenase + 9 terpene-containing loci** — the
   halogenated-meroterpenoid fingerprint (napyradiomycin/marinone-type) that *defines* the MAR4 lineage — with a
   halogenated PKS/T1PKS as the top **High** lead (BGC023), plus a 2-deoxystreptamine+terpene hybrid and marine
   NRP-metallophore/siderophore loci. Pointing at the right chemistry on a genome whose answer is independently
   known is the strongest external check yet: not just "ran clean," but "found what's actually there."

6. **The diagnostic floor gets a second, independent confirmation — on a symbiont genome — and surfaces a
   cross-system ecological parallel.** *Actinomadura macrotermitis* RB68 (`ASM960437v1`) is a public symbiont of
   *Macrotermes* **fungus-growing termites** — an insect-fungiculture system that evolved independently of the
   attine-ant fungus gardens at the centre of this project. It ran `MAMEY_COMPLETE` at GOOD / ~99% interior, 98th
   corrected percentile. Its **BGC044** is a KCB-dark **nucleoside** lead (nearest anchor a bare chromosome hit)
   that the marker-aware floor surfaced to **Medium / AF 55.3** — the *exact* KCB-dark-nucleoside-antifungal case
   the v9.6.x work was built for, now firing on a second, unrelated, public genome (the first external
   confirmation was *M. humida* BGC034). That is the independent re-confirmation the floor needed.

   The ecological reading, kept claim-safe: a nucleoside chitin-synthase-inhibitor-class antifungal (the
   nikkomycin/polyoxin route) in a **termite** fungus-garden symbiont parallels the same class in the **attine
   ant** symbiont cohort — convergent recruitment of one chemical-defence class against garden fungal antagonists
   across two independent fungicultures. This is a **hypothesis from one genome**, not an established pattern; it
   motivates pulling more *Macrotermes*-symbiont actinomycetes to test whether the signal is systematic. Strict
   caveats: class-level and KCB-anchored (similarity, not identity); the nucleoside core needs **gene-level
   confirmation (e.g. *nikJ*/*truD*)** before it can be called nikkomycin-*type*; **no polyene or azoxy** was
   detected, so the parallel is specifically the chitin-synthase-inhibitor class, not antifungal capacity in
   general. RB68 also carries an enediyne signal (`T43-ENE`) → **BSL-2 consult before any bulk fermentation**, and
   a genuine `ene_KS` call must be distinguished from an `hglE-KS` cross-reaction at the gene level first. Because
   RB68 is **public**, it can anchor the ant↔termite antifungal-convergence comparison in a manuscript or the
   public release **without the privacy constraints** that apply to the unpublished attine cohort — a citable,
   reproducible positive control for that narrative. (`hglE-KS` ×4 here further corroborates `hglE-KS-PREV-001`.)

## Reading the leads (claim-safe)
Type strains are "solid, not spectacular" external anchors: *M. humida* is a prolific producer (2 Exceptional / 3
High), *S. griseoluteus* more even (23 Medium / 21 Inventory, T2PKS aromatics consistent with its known
chemistry); the MAR4 strain headlines on halogenated meroterpenoids (1 High / 19 Medium / 21 Inventory), its
lineage signature. Leads are class-level hypotheses; KCB anchors are similarity; activity is the extract-level default.

## Admitting additional validation evidence

A one-row plotting append is insufficient to establish a new validated run. First bind the evaluated software/cut, task, source accessions/versions, input and artifact hashes, exact locus identities where discussed, expected outcome provenance, observed result, all skips/holds and the complete run receipt. Keep inputs in place with locators/hashes rather than copying packages into the code bundle. External execution and adoption need the current user's authorized scope.

Only after reconciliation should the selected plotting metadata and reader-facing account be updated consistently. `tools/build_validation_panel.py:35–84` reads the CSV and uses stored retention values in labels; it does not reconstruct input provenance or verify scientific claims. Preserve the original historical values and identify a separately admitted replacement if one is needed. Private de-identification is not itself a disclosure authorization or proof that remaining metadata is safe.

Retain the historical narrative and unresolved values for source traceability. Record any new run, figure, corrected CSV or scientific adoption separately, with its evidence and scope.
