# Choose a Mode B example

For a new card, choose the [native profile](../../MODEB_PROFILE_MATRIX.md), then follow the [authoring walkthrough](../../MODE_B_USER_WALKTHROUGH.md). The default is `full48`; use `current50_v2` when the work order selects it. Current50 v2 keeps literature with relevance in §48–§49 and the data evidence table last at §50.

Use the [full48 reference](phosphonate_reference_full48_no_blastp_exemplar.md) to study ordered sections, the displayed gene denominator and typed unavailable-evidence handling. Use the seven class sketches below for examples of gene-to-prose reasoning. Their historical measurements and pass/FULL labels are retained source assertions, not fresh validation or a completion template for a new locus.

Before reusing a claim, trace its actual sources and receipts. The RiPP sketch's §15 conflicts with its §§4/16/28 about selected precursor/LanKC results; the siderophore introduction conflicts with its §§4/16/28 about whether a panel ran. These are unresolved source-state conflicts, not no-hit findings. Keep complete strain / full node-or-contig / region / BGC alias and independently review gene denominators, channel binding, citations and biological interpretation. Reuse writing structure rather than transferring these loci's genes, scores, mechanisms, activity claims or proposed experiments.
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

The retained proposal was to recalibrate class-specific writing depth against real examples. The shipped
legacy passive evaluator instead uses priority-based 12k/11k/10k floors plus density and enrichment checks,
with a separate reduced floor for qualifying boundary fragments. It does not select a class-specific floor.
A legacy FULL tier is separate from the selected full48/current50 verifier; use the current profile's
requirements and source review rather than treating these character counts as a scientific acceptance bar.


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

`tests/test_exemplars_are_clean_v97247.py` defines regression checks for these files. Its locus context is
derived from the card's declared/modal contig index or its own native tags, rather than an independent
package roster. It can miss foreign genes sharing that index; a pass does not authenticate the source
identity or biology. The separate full48 reference test also checks a hardcoded displayed roster and
ordinary structure/depth. No fresh test execution or independent evidence admission is established here.


## Profile status of these exemplars (v9.7.372, publication-quality repair Patch 9)

The seven class exemplars above are **legacy §1–§30 teaching sketches** (six-column, nr-only §4 grids, abbreviated §§5–7). They calibrate register and claim-safety for `MODEB_CANDIDATE_30` authoring; **do not treat them as gold-standard publication exemplars** — they do not meet the finished-card contract. The expanded reference exemplar is `phosphonate_reference_full48_no_blastp_exemplar.md` (Kitasatospora setae KM-6054T / NC_016109.1 / region016 / BGC016): all 48 sections in exact order, 23/23 genes, explicit typed handling of the absent independent-BLASTp channel. Its biology must never be transferred into other cards; reuse only its structure and register. A finished-card exemplar with a fully populated channel-separated matrix and cross-stream dispositions follows once a type-strain BLASTp panel exists (.373).
