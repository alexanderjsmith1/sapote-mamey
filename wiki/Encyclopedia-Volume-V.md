# Volume V — Scoring, Ranking & DAPR

*Edition: bundle v9.7.33 / engine Mamey 1.9.41 · re-grounded to bundle v9.7.91 / engine Mamey 1.9.91 on 2026-06-20 (the AB/AF/novelty keyword tables — 18/17/11 terms — the diagnostic subsets, the guard composition order, the TIER1_FLOOR_EXCLUDED_PREFIXES, and the shipped PC-12 cargo-aware concordance gate verified against the running engine) · 2026-06-16*
*Chapters V.1–V.7. The scoring volume. Read Volume III (the Sapote layer) and Volume IV (detection) first.*

This volume documents how the engine turns extracted evidence into a ranked triage board: the three axes and the
tier ladder (V.1), the diagnostic layer that rescues gene-only leads (V.2), the corroboration gate (V.3), the
guard stack and **the order in which guards compose** (V.4 — the chapter the \#28 finding proved was missing),
architecture confidence and why it is decoupled from the tier (V.5), the rationale renderer that makes a score
auditable (V.6), and DAPR (V.7). Numbers are quoted from `mamey/scoring.py` at this edition; treat them as the
calibration of *this* engine, not universal constants.

------------------------------------------------------------------------

## §V.1 · The three axes and the lead-tier ladder

Every BGC is scored on **three independent axes**, each a base plus a keyword sum: <span class="tag t-engine">\[engine\]</span> (`scoring.py:257`)

- **Antibacterial (AB)** = `25 + Σ AB_KEYWORDS` — 18 weighted terms, e.g. carbapenem 18; phosphonate 15;
  hr-t2pks, transat-pks, thioamide, thiopeptide, thiazolylpeptide 14.
- **Antifungal (AF)** = `20 + Σ AF_KEYWORDS` — 17 terms, e.g. hsaf, nystatin, nikkomycin, polyoxin 20; polyene,
  candicidin, nucleoside 18.
- **Novelty** = `30 + Σ NOVELTY_KEYWORDS` — 11 terms, e.g. transat-pks, enediyne, azoxy 18; thioamide, phosphonate
  15; ranthipeptide, hglE 12.

The full weight tables (`scoring.py`), for reference and for tuning (→ Configuration Reference, §VII.7): <span class="tag t-engine">\[engine\]</span>

| `AB_KEYWORDS` (18) |  |  | `AF_KEYWORDS` (17) |  |  | `NOVELTY_KEYWORDS` (11) |  |
|----|----|----|----|----|----|----|----|
| carbapenem | 18 |  | hsaf / nystatin / nikkomycin / polyoxin | 20 |  | transat-pks / enediyne / azoxy | 18 |
| phosphonate | 15 |  | polyene / candicidin / nucleoside | 18 |  | thioamide / phosphonate | 15 |
| hr-t2pks / transat-pks / thioamide / thiopeptide / thiazolylpeptide / aminoglycoside | 14 |  | tetramate | 16 |  | ranthipeptide / hglE | 12 |
| nrps / t2pks / lanthipeptide | 12 |  | sgr ptm | 14 |  | ripp | 10 |
| t1pks / lassopeptide / phenazine | 10 |  | chitin / ptm | 12 |  | nrps / t1pks / t2pks | 8 |
| saccharide / halogenated / ripp / azole | 8 |  | t1pks / transat-pks | 10–12 |  |  |  |
|  |  |  | nrps | 8 |  |  |  |
|  |  |  | terpene | 6 |  |  |  |
|  |  |  | siderophore / metallophore | 4 |  |  |  |

Two design points are visible in the weights. The **novelty** table is short and weighted toward structurally
unusual chemistry (trans-AT, enediyne, azoxy, hglE) — novelty is meant to flag the *unusual*, not the merely
present. And `saccharide` carries a low AB weight (8) precisely because it over-calls; the standing-rule guard
(§VIII.4) then removes a saccharide-only region from the corrected rank entirely, so a low weight plus a guard,
not a single mechanism, keeps sugar noise down (the worked guard-trace in §V.6 shows this on a real region).

After the diagnostic layer (V.2) and the guards (V.3–V.4) adjust the bases, two further novelty corrections apply:
a high known-cluster signal **subtracts** novelty (`kcb_cumulative > 10000 → novelty − 15`), while a *missing* KCB
denominator (a truly KCB-dark region) **adds** a small novelty increment (`+5`), and a low RiQ (`< 0.5`) adds
`+10`. Fragmentation is **no longer penalised** on the score (v9.7.84): the edge penalty was removed because Edge/FC BGCs show no truncation signature in their base score, and the penalty was burying overlooked edge fragments at the tier threshold. Truncation is now carried as a confidence grade (C/D), not a deduction. RG-GMCI rescue (→ §IV.4) still adds its bonus (HIGH +8 / MODERATE +4); with no penalty there is nothing left to reduce. *Historical (≤1.9.84):* ab/af lost 0.35× and novelty 0.2× the effective edge penalty, which RG-GMCI reduced by
the same amount, so a reconstructed split pathway is not double-charged for being fragmented. Each axis is then
clamped to `[0, 100]`. <span class="tag t-engine">\[engine\]</span> (`scoring.py:327–351`)

The **lead tier** reads from the strongest axis: `best = max(AB, AF, novelty)`, then <span class="tag t-engine">\[engine\]</span> (`scoring.py:455`)

| Tier | Condition | Reading |
|----|----|----|
| **Exceptional** | best ≥ 85 | rare — across mixed VERY_POOR→GOOD cohorts it often does not fire at all |
| **High** | best ≥ 70 | a strong, confidently-scored lead |
| **Medium** | best ≥ 50 | a real lead worth a dossier |
| **Inventory** | best \< 50 | catalogued, not prioritised |

Because the tier is `max()` of three axes, a strain can reach High on novelty alone (a structurally unusual but
non-bioactive-scoring locus) or on a single bioactivity axis. The tier is a *promise of interest*, not a claim of
activity — the claim-safety doctrine (→ §I.3) is enforced by the guards below, not by the number.

## §V.2 · The diagnostic layer — rescuing the gene-only lead

A KCB-dark, gene-only cluster can still carry a *definitive class diagnostic* — the nikkomycin/BGC008 case is the
canonical one: labelled only "nucleoside; other", KCB-dark, but a `T43-NUC` trigger plus the NikJ TIGRFAM make it
a real antifungal. The diagnostic layer ensures such evidence reaches the tier gate instead of being computed and
dropped. <span class="tag t-engine">\[engine\]</span>

- **Diagnostic bonus.** A corroborated diagnostic trigger adds `DIAGNOSTIC_BONUS = 25` to its axis. The
  antifungal diagnostics are **`{T43-NUC, T43-PTM}`**; the antibacterial diagnostics are the **six**
  **`{T43-LAN, T43-LASSO, T43-THA, T43-PHO, T43-AMC, T43-BLA}`** (PHO/AMC/BLA wired v9.7.20/.21, each firing only
  on its *own* biosynthetic diagnostic, so a fired one is a real class hit, not a similarity-only anchor).
  <span class="tag t-engine">\[engine\]</span> (`AF_DIAGNOSTIC_TRIGGERS` / `AB_DIAGNOSTIC_TRIGGERS`, `scoring.py:34–46`).
- **The Tier-1 floor.** A definitive class marker (a corroborated CCTT diagnostic, or a T1 self-resistance hit)
  **floats the tier to at least Medium**, so a gene-only class lead is never buried below a text-rich but
  class-empty region. One deliberate exclusion: a *lone* tailoring-enzyme marker — halogenase (`T43-HAL`) or
  exotic-halogenase (`T43-XHAL`) — is a modification, not a class call, and does **not** floor on its own
  (`TIER1_FLOOR_EXCLUDED_PREFIXES`, `scoring.py:53`); a class-defining marker that co-occurs still does.
- **The RiPP-fragment cap.** The opposite case: a truncated RiPP-family fragment (\<8 kb, no precursor captured)
  is **capped at Inventory** so an incomplete RiPP cannot float above a complete cluster on the strength of a
  partial signal. The floor lifts the real gene-only lead; the cap holds down the fragment. <span class="tag t-engine">\[engine\]</span>

**Worked score computation (real v9.7.33 run — a lanthipeptide lead in the Bumblebee *Streptomyces*).** A clean
Interior RiPP lead, BGC label `RiPP; RiPP-like; lanthipeptide-class-iii`, Architecture grade A, KCB cumulative
8,260. The axes compute as: <span class="tag t-engine">\[engine: real run; strain in the PRIVATE worked-examples key\]</span>

| Axis | Computation | Value |
|----|----|----|
| **AB** | base 25 + AB keywords (lanthipeptide 12 + ripp 8 = 20) = **45**; corroborated **T43-LAN** is an AB diagnostic → **+25** `DIAGNOSTIC_BONUS`; Interior → edge penalty 0 | **70.0** |
| **AF** | base 20 + AF keywords (none match) = 20; no AF diagnostic | **20.0** |
| **Novelty** | base 30 + novelty keywords (ripp 10) = 40; KCB 8,260 \< 10,000 → no −15; not KCB-dark → no +5 | **40.0** |

`best = max(70, 20, 40) = 70` → tier **High** (≥ 70). The example shows the diagnostic layer doing exactly its
job: the lanthipeptide keyword weight alone (base 45) would land the lead at Inventory, but the corroborated
T43-LAN diagnostic lifts AB by 25 to reach High — a gene-class signal reaching lead tier on its own merits, the
+25 to a single axis being the unmistakable fingerprint of `DIAGNOSTIC_BONUS` (AF and novelty sit at their
keyword-only values). Had the lanthipeptide trigger fired on a class-incompatible locus, the corroboration gate
(§V.3) would have withheld that +25 and the lead would stay at Inventory.

## §V.3 · The corroboration gate

The diagnostic bonus and the Tier-1 floor are powerful, so they are fenced by a single gate: a trigger earns its
credit only if it is **corroborated** — if it fired on a class-*compatible* locus. A class-defining trigger that
fires on a class-incompatible region (a phosphonate trigger on a type-III PKS) is **uncorroborated**: recorded in
the rationale for the judgment layer to see, but granted **no diagnostic bonus, no floor, and no class-capacity
credit**. Only corroborated triggers build the capacity claim. <span class="tag t-engine">\[engine\]</span>

Two points the \#28 finding made load-bearing (→ §V.4):

1.  **Corroboration is the real protection, not the regex.** Even a tightened trigger such as `T43-PHO` (with its
    catabolic-phn / C–P-lyase / transporter exclusions) still over-fires on a few non-phosphonate regions; what
    keeps those out of the capacity claim is this gate, not the pattern. A reader should treat a *fired* trigger as
    a candidate and a *corroborated* trigger as evidence.
2.  **An uncorroborated trigger must be stripped of *both* of its roles.** A diagnostic trigger does two things —
    it grants an axis bonus (V.2) *and* it sets the `tier1_diag` exemption that the guards in V.4 respect. If a
    trigger is uncorroborated, both must be withheld. Withholding only the bonus while leaving the exemption intact
    is precisely the gap behind the \#28 non-composition bug.

## §V.4 · The guard stack and its composition order

Claim-safety is enforced by a stack of **guards** that strip or withhold credit when a signal has not earned it.
Several can apply to one BGC, so **the order in which they read each other is part of the contract** — and is the
single most error-prone thing in the scorer. The order, as the engine runs it: <span class="tag t-engine">\[engine\]</span> (`scoring.py:274–360`)

1.  **Bases + diagnostic bonus** are computed (V.1–V.2).
2.  **The corroboration gate** resolves which triggers are corroborated, producing `corrob_triggers`, and from it
    the exemption flag **`tier1_diag = bool(corrob_triggers) or rt_tier.startswith("T1")`** (`scoring.py:278`).
3.  **Three suppression guards then fire, each gated on `not tier1_diag`** — i.e. each is *exempted* by a
    corroborated class signal:
    - **Primary-metabolism / pigment guard** — a region whose own core genes are housekeeping/pigment markers and
    whose product class is only weak/over-call labels (`WEAK_OVERCALL_CLASSES`) has AB/AF floored to 25/20
    (de-ranks a topoisomerase mis-labelled "NRPS-like", a carotenoid mis-read as antifungal).
    - **Mobile-element / HGT demotion (#28)** — `mobile_flag = mobile_dominant and not tier1_diag`; an ICE-dominated
    region not independently class-typed has AB/AF floored (→ §IV.8).
    - **Mis-anchor guard** — a KCB anchor lacking its committed class diagnostic (aminoglycoside-no-DOIS,
    polyene-with-too-few-PKS-KS) has the anchor-derived axis credit floored.
4.  **The enediyne guard** runs *independently of `tier1_diag`*: a spurious/PREV-001 enediyne anchor loses its +18
    novelty; a genuine enediyne keeps an `[E-signal]` claim-safety note (no BSL-2 flag, → §I.6).
5.  **Novelty corrections, penalty, RG-GMCI rescue, clamp, `max()`, tier** (V.1).
6.  **The Tier-1 floor** floats a corroborated class lead to ≥ Medium (V.2); **standing-rule downgrades** (saccharide
    / NAPAA / hglE) drop the row from corrected lead rank.

**The composition hazard (the \#28 follow-up).** Because all three step-3 guards consult `tier1_diag`, and
`tier1_diag` is true whenever *any* trigger sits in `corrob_triggers`, a trigger that the corroboration gate
*should* have marked uncorroborated but didn't will exempt a region from all three guards. This is exactly the
canonical-ICE failure: `NZ_CP029601.1` BGC032 is mobile-dominant, but its `T43-LAN` trigger was never marked
uncorroborated (the ICE has no lanthipeptide cyclase/precursor), so `tier1_diag = True`, `mobile_flag = False`, and
the impostor keeps rank-1. **The contract V.4 must enforce:** the corroboration gate must mark a class trigger
uncorroborated when its region is mobile-dominant **and** the class's defining enzyme is absent — closing the loop
so an uncorroborated trigger cannot both fail to earn its bonus and still grant the exemption. **The class-trigger
half of this shipped in v9.7.35** (#28, option 1: `architecture_class_confidence == LOW` as the enzyme-absent
proxy); on BGC032 the impostor drops rank 1→3. But `tier1_diag` has a **second source** — `rt_tier.startswith("T1")`
(self-resistance) — that \#28 does not touch, and on the same real BGC032 a `T1_DIAGNOSTIC_SELF_PROTECTION`
(`APH_AAC`) tier still holds `tier1_diag = True`, so the region is rank-demoted but **not** mobile-flagged.

**The resistance-axis fix (PC-12) uses a signal the engine already computes.** *(Shipped in v9.7.37.)* The
resistance tier carries
`class_concordant_groups` (`source_scans.py:888`): a T1 self-protection tier is `HIGH_CLASS_CONCORDANT` when the
resistance group matches the cluster's product class, and `MODERATE_CLASS_UNVERIFIED` when concordance is not
established. BGC032's `APH_AAC` (aminoglycoside resistance) against a *lanthipeptide* product is the latter —
**concordance empty**. So the engine already *knows* the resistance does not match the cluster; it just did not act
on that when setting `tier1_diag`. PC-12: on a mobile-dominant region, a T1 self-protection tier counts toward
`tier1_diag` **only if `class_concordant_groups` is non-empty** — a non-concordant resistance inside ICE machinery
is horizontally-acquired *cargo*, not self-protection. This floors BGC032 (concordance empty → cargo → the mobile
demotion fires; real-data check: AB 57→25, dropped from the ranked leads) while genuine self-resistant clusters
(non-empty concordance) keep their tier-1 status. Crucially this reads concordance in the **safe direction** — a
resistance/class *mismatch* downgrades; it never trusts a label *match* as positive evidence.

> **The root cause behind \#28, PC-11/PC-12, and the T43-PHO / over-call findings is one thing: label-vs-domain.**
> Many signals can fire on the *product-class label* (a keyword/token) rather than on *parsed domain evidence*. The
> durable fix is to gate on signals the engine derives from parsed domains/context, which it already has on both
> axes: **`architecture_class_confidence`** (class axis, domain-derived — \#28) and **`class_concordant_groups`**
> (resistance axis, concordance — PC-12). A tempting shortcut — domain-gating against `cassette_families` — was
> built as a scaffold and **rejected**: `cassette_families` is itself label-contaminated (the `lanthipeptide`
> cassette pattern matches the product-label token, not a LanC/LanM cyclase), so gating against it would have
> re-corroborated BGC032 and **silently undone \#28**. The lesson generalizes: *a label cannot be disciplined by
> another label.* Reliable corroboration must trace to parsed domain evidence. <span class="tag t-finding">\[finding — PC-12; class-axis fix
> shipped v9.7.35, resistance-axis fix shipped v9.7.37 (verified in scoring.py against NZ_CP029601.1 BGC032)\]</span>

## §V.5 · Architecture confidence, decoupled from the tier

The engine carries two architecture fields, easy to conflate (→ §III.5): **`architecture_confidence`** (the A–E
grade — *how much of the locus is present*, structural completeness, parse-time, `models.py:71`) and
**`architecture_class_confidence`** (HIGH/MODERATE/LOW — *how sure is the class-capacity call*, the "Class_Conf"
board column, `models.py:74`). **Neither feeds the tier.** The tier is `max(AB, AF, novelty)` and nothing else; a
HIGH-confidence, well-bounded locus can still land at Inventory if its keyword/diagnostic score is low. Both fields
are *display* signals that let a reader weight a lead — a High lead on an A-grade complete locus reads differently
from a High lead floored up from a D-grade fragment — but they do not move the rank. <span class="tag t-engine">\[engine\]</span> (`scoring.py:455`)

This decoupling is the central open scoring question. A candidate **architecture floor** — keyed on
`architecture_class_confidence == HIGH` to lift confidently-typed but low-scoring loci from Inventory toward Medium
— is a natural follow-on (a prototype recovered confidently-graded aromatic-T2PKS and β-lactone loci with no
regression), and it sits alongside a known **keyword-coverage gap**: a class with no axis keywords (β-lactone is
absent from `AB_KEYWORDS`/`AF_KEYWORDS`) scores zero on bioactivity even when its chemistry is real. Both are real
engine behaviours this volume records as the design frontier, not yet shipped guards. <span class="tag t-engine">\[engine: current behaviour;
the arch-floor is a prototype, not in the release\]</span>

## §V.6 · The rationale renderer — the legible trace

A score a reader cannot audit is a number to be distrusted, so every scored BGC carries a **rationale string** that
names each adjustment that fired: the edge status and architecture grade; the KCB/RiQ values; RG-GMCI notes; the
diagnostic floor or RiPP-fragment cap; the AF-diagnostic; **`CCTT-UNCORROBORATED`** when a trigger fired on a
class-incompatible locus; the primary-metab/pigment flag; the standing-rule downgrade; the mis-anchor flag; the
mobile-element demotion; and the `[E-signal]` note. This is built engine code, not a Sapote-prompt convenience —
**`render_rationale()`** is a standalone, independently-tested function (`scoring.py`, `render_rationale()`, with
`tests/test_render_rationale.py`), extracted as the v9.7.32 refactor so the trace can be unit-tested in isolation.
<span class="tag t-engine">\[engine: built\]</span> It is how a reader confirms *why* a cluster scored as it did — and, for the guards of V.4, the
place a missing demotion (the \#28 case) becomes visible: a mobile-dominant region whose rationale shows no
`MOBILE-ELEMENT DEMOTION` line is the tell.

**Worked guard-trace (real v9.7.33 run — the Attine *Pseudonocardia*).** A Saccharide region (Edge, KCB anchor to
a *Nocardia* T1PKS/trans-AT cluster, KCB 5,436) scores AB 48.9 / AF 33.9 / novelty 50.8 on raw keywords — enough
to rank. Its board row carries **`Standing_rule = saccharide-exclusion`**, and the rationale therefore reads
`…; STANDING-RULE DOWNGRADE (saccharide-exclusion): excluded from corrected lead rank`. The effect: the region is
**dropped from the corrected rank** despite a respectable raw score (and the KCB anchor is itself cross-class — a
saccharide label against a T1PKS/trans-AT subject — so even the anchor argues against reading it as a real
polyketide lead). The trace is the audit: a reader sees the raw score, sees the standing-rule line, and sees the
region absent from the corrected rank — every step legible, no silent demotion. <span class="tag t-engine">\[engine: real run; strain in the
PRIVATE worked-examples key\]</span>

## §V.7 · DAPR — dual antibacterial/antifungal priority ranking

**DAPR** (deliverable spec B) is the ranked triage a bench scientist reads to choose targets. It reads the triage
board's AB/AF axes, boundary, architecture, KCB, CCTT triggers, location, and the manifest's mobile-element flag,
and emits **Track A** (antibacterial, ranked by AB), **Track B** (antifungal, ranked by AF), a **dual-threat**
list (top-quartile on both), and — crucially — an **excluded list**: BGCs carrying a standing-rule, primary-
metabolism, or mobile-element flag are named under "flagged, not ranked," **never** in the ranked body, so a
demoted region cannot reappear at the top of a hand-built table. Every DAPR table is claim-safe by contract: the
KCB column is labelled **similarity** (not identity), and a **mandatory footer** states bioactivity is
extract-level and that absence of recorded activity is never a negative call — strains are contrasted by
mechanism, never by phenotype (→ §I.3). <span class="tag t-spec">\[spec\]</span> — DAPR's columns are in the canonical master schema and
<span class="tag t-spec">\[spec\]</span> — As of v9.7.91 the per-strain package *does* emit the core of this: `4c_AB_lead_board.csv` (Track A, AB-ranked) and `4c_AF_lead_board.csv` (Track B, AF-ranked), each carrying a `Downgrade` column (the standing-rule / primary-metab / mobile flag — the "excluded, not ranked" signal) and a `Corrected_rank` (the v9.7.45 dedicated lead boards). What remains master-level / <span class="tag t-spec">\[spec\]</span> is the *combined* DAPR deliverable — the cross-track dual-threat list and the exact mandatory-footer wording — so a later edition can promote the per-strain AB/AF boards to <span class="tag t-engine">\[engine\]</span> while keeping the combined cross-track view as the spec'd master artifact.

A standing caveat tied to V.4, **now resolved**: the \#28 corroboration↔mobile fix (class-axis, v9.7.35) and PC-12 (resistance-axis, v9.7.37) both shipped, so the mobile-element flag the DAPR excluded-list relies on is now populated correctly on the canonical class-trigger-bearing ICE (BGC032: AB 57→25, mobile-flagged, dropped from the ranked leads). A hand-built DAPR on an *older* run (engine ≤1.9.84, missing one or both fixes) should still apply the mobile-dominance test directly; on a v9.7.91 run the flag can be trusted.

------------------------------------------------------------------------

*End of Volume V. Remaining planned: Volume VII — Operations, Release & Provenance; Volume VIII — Reference &
Apparatus. With V drafted, the eight-volume set is built except for the operations and apparatus references.*

</div>

<div id="vol6" class="section vol">
