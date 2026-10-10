# Mode B exemplar reader guide — v9.7.447 source check

The reference collection below is historical calibration. For new current50_v2 authoring, use the explicit `current50_v2` contract and `FINISHED_FULL50_CURRENT50_V2` profile: §1–§50 exactly once in order, literature with relevance in §48–§49, and the data evidence table last in §50. A current50_v2 structural pass does not invoke all full48 finished-profile publication gates; it does not establish product, activity, linkage, scientific acceptance or release.

`phosphonate_reference_full48_no_blastp_exemplar.md` remains a **full48 format reference**, not a current50_v2 finished card. The seven other supplied class cards are legacy sketches. Historical “verify-modeb OK”, “FULL” and “zero findings” statements below describe their old scope and are not fresh validation. A lexical heading census finds gaps in their §1–§30 coverage; do not copy their omission pattern or import their locus-specific conclusions. The README's old “no live BLASTp run” statements for RiPP and siderophore also conflict with the supplied cards' §4/§28 claims of operator-supplied offline-ingested BLASTp. Resolve original evidence and provenance before using either channel as calibration.

Keep `strain / full node-or-contig / region / BGC alias` on each new card. Source identity, complete per-gene denominators, citation substance, cross-stream disposition and interpretation require their own review. Similarity does not establish identity; an Interior boundary label does not prove every pathway component is present or active. These files have not been scientifically re-certified by this documentation audit.

---

## Preserved historical collection README

# Mode B exemplars — current full48 reference plus legacy class calibration

The current typed-terminal format exemplar is `phosphonate_reference_full48_no_blastp_exemplar.md`: a
real reference-locus card with all §1–§48 sections, an exact 23-CDS roster, all-stream disposition, and
an honest typed no-BLASTP source limitation. It teaches structure, identity, denominator preservation,
and unavailable-evidence closure only; its genes, pathway call, comparators, experiments, conclusions,
and §20 action list must never transfer to another locus. It is not positive substantive calibration
for §§20, 39, 40, 42, or 48.

The older class cards below remain useful `LEGACY_CLASS_CALIBRATION` examples. They were authored for
the §1–§30 era and are not complete current-contract exemplars until individually upgraded.

## Current expanded reference exemplar

| Role | Exemplar file | Status |
|---|---|---|
| Full48 typed-terminal format / no independent BLASTP | `phosphonate_reference_full48_no_blastp_exemplar.md` | CURRENT_TYPED_TERMINAL_FORMAT_EXEMPLAR — 48/48 sections; 23/23 CDS; zero structure/depth findings; not positive calibration for §§20/39/40/42/48; no distribution stamp |

## Legacy class-calibration slot status

| Class | Exemplar file | Status |
|---|---|---|
| NRPS | `nrps_exemplar.md` | ✅ landed v9.7.260 — *S. amethystogenes* BGC002·region002 (NRPS; KCB tetronasin held similarity-only, class-divergent); verify-modeb OK |
| T1PKS | `t1pks_exemplar.md` | ✅ landed v9.7.260 — *S. avermitilis* BGC004·BA000030.4·region004 (filipin; OVER-MERGED, per-protocluster; PKS 96% CONFIRM); verify-modeb OK 0 warn |
| T2PKS | `t2pks_exemplar.md` | ✅ landed v9.7.260 — *S. amethystogenes* BGC029·region029 (fogacin; KS core CONFIRM; GerE→LuxR REFINE); verify-modeb OK |
| T3PKS | `t3pks_exemplar.md` | ⬜ awaiting the Developer or User |
| hybrid NRPS-PKS | `nrps_pks_hybrid_exemplar.md` | ✅ landed v9.7.260 — *S. spectabilis* BGC004·region004 (lagmysin; multi-system, fills hybrid+lasso; NRPS 100% + PKS-KS CONFIRM); verify-modeb OK |
| RiPP | `ripp_exemplar.md` | ✅ replaced v9.7.264 — **public class-III lanthipeptide** (catenulipeptin-anchored, KCB BGC0000501.3), *S. amethystogenes* subsp. *fukuiense* BGC008 · JBHTEE010000001.1 · region008. FULL §1–§30 incl. §21/§22/§23/§24, 0 lint ERRORs. Honest §4 (no live BLASTp run; offline-ingest path documented in §16). Retired the AS-derived mycofactocin card. |
| terpene | `terpene_exemplar.md` | ✅ landed v9.7.260 — public source: *S. avermitilis* BGC001·BA000030.4·region001 (avermitilol synthase, BLASTp 100% CONFIRM); verify-modeb OK |
| siderophore | `siderophore_exemplar.md` | ✅ replaced v9.7.264 — **public NI-siderophore** (desferrioxamine B/E-anchored, KCB BGC0000940.5), *S. avermitilis* MA-4680 BGC042 · BA000030.4 · region042. FULL §1–§30 incl. §23/§24, 0 lint ERRORs. Honest §4 (no live BLASTp run). Retired the AS-derived card. |
| saccharide / oligosaccharide | `saccharide_exemplar.md` | ⬜ awaiting the Developer or User |
| other / mixed | `other_exemplar.md` | ⬜ awaiting the Developer or User |

## What a new exemplar must be

- A **real, verified** §1–§48 card that passes the current structure/depth gate and grades **FULL** at the current
  floor — real domain·BLASTp substance, no padding. (The verified AS-XXX BGC007 card, 36k chars / 3.0
  mentions-per-1k, is the reference shape for a large modular class.)
- Redacted to the tier it will ship in (AS IDs → `AS-XXX` for public tiers; the release redactor handles
  this, but exemplars committed to the repo should already be redaction-clean).
- One per class is enough — its purpose is to show the depth bar and the aSDomain/BLASTp evidence density,
  not to be a template to copy verbatim.

## Calibration hook

Once a class's exemplar lands, the depth gate's floor for that class can be **recalibrated against real
data** instead of the current provisional single-anchor numbers — in particular whether small classes
(RiPP, terpene) warrant a class-specific floor below the flat 10–12k, since a genuinely complete small-BGC
card may carry less absolute length while still being domain-dense. Until then the flat floor + density
rule applies to every class.


---

## v9.7.247 — the phantom-locus repair (F1)

Both exemplars carried, in §4, two paragraphs of authoring boilerplate templated in from
`modeb_template_emitter`:

- *"per-gene BLASTp overturned two of ten on BGC006 (β-lactamase→esterase, phenol-hydroxylase→ferritin)"*
- *"the offline, deterministic channel that settled BGC006 **ctg12_71**"*

`ctg12_71` belongs to *Amycolatopsis* sp. NPDC004378 (`Wheelhouse/validations/BGC006_online_blastp.csv`).
It exists on neither exemplar's strain. Both files therefore failed v9.7.246's own release-blocking
`PHANTOM_LOCUS` lint — **the gate refused the cards that define the bar.**

The paragraphs were **deleted, not reworded**, per the v9.7.246 changelog: there is no BLASTp result to
reword. Deletion cost 1,643 ch (ripp) and 1,639 ch (siderophore); **both remain FULL with zero THIN_\*
findings**, and ripp's `PAD_SIGNAL` disappeared with them — the boilerplate was itself padding.

`tests/test_exemplars_are_clean_v97247.py` now lints these files in CI. An exemplar that defines the bar
must clear it.


## Profile status of these exemplars (v9.7.372, publication-quality repair Patch 9)

The seven class exemplars above are **legacy §1–§30 teaching sketches** (six-column, nr-only §4 grids, abbreviated §§5–7). They calibrate register and claim-safety for `MODEB_CANDIDATE_30` authoring; **do not treat them as gold-standard publication exemplars** — they do not meet the finished-card contract. The expanded reference exemplar is `phosphonate_reference_full48_no_blastp_exemplar.md` (Kitasatospora setae KM-6054T / NC_016109.1 / region016 / BGC016): all 48 sections in exact order, 23/23 genes, explicit typed handling of the absent independent-BLASTp channel. Its biology must never be transferred into other cards; reuse only its structure and register. A finished-card exemplar with a fully populated channel-separated matrix and cross-stream dispositions follows once a type-strain BLASTp panel exists (.373).
