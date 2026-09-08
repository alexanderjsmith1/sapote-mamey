# Volume III — The Sapote Layer (judgment)

*Edition: bundle v9.7.33 / engine Mamey 1.9.41 · re-grounded to bundle v9.7.91 / engine Mamey 1.9.91 on 2026-06-20 (the AB/AF/novelty scoring model, the diagnostic bonus, the neutralized edge penalty, the RG-GMCI rescue, the lead-tier thresholds, the guard composition order, and the Mode B scaffold headings verified against the running engine) · §IV.4 (RG-GMCI rescue layer) re-grounded to bundle v9.7.100 / engine Mamey 1.9.98 on 2026-06-21 (db_kind CB/KCB separation, rescue_evidence_base, functional_rescue_class, terminus-truncation rescue) · 2026-06-15*
*Chapters III.1–III.7. Grounded in the running engine of this edition. Read Volumes I–II first (→ Master Index).*

------------------------------------------------------------------------

## §III.1 · The judgment contract

Sapote is the layer that does what a fixed rule cannot: it weighs competing signals, decides what a cluster's
evidence *means*, writes the per-BGC analysis, and ranks leads. That is interpretive work, and interpretive
work by an LLM is not deterministic — so Sapote operates under a **contract** that constrains what the judgment
is allowed to assert. The contract is the whole reason an LLM can be trusted in a discovery pipeline: it does
not ask the model to be infallible, it fences the model so its mistakes cannot become confident false claims. <span class="tag t-concept">\[concept\]</span>

The contract has four terms, each enforced somewhere concrete (the chapters that follow):

1.  **Build on the deterministic floor, never around it.** Sapote reads Mamey's extraction (counts, boundaries,
    scans, evidence channels) as fact and may interpret it, but may not silently overwrite it. The deterministic
    facts are pre-slotted into the analysis scaffold (→ §III.2) so the judgment writes *around* fixed numbers it
    cannot quietly change.
2.  **Capacity, similarity, extract-level** — the three claim-safety rules of §I.3 are binding on every sentence:
    biosynthetic capacity not production, KCB similarity not identity, bioactivity at the extract not the cluster.
3.  **Credit only what is corroborated.** A class-capacity claim, a bioactivity bonus, or a tier floor is granted
    only when the supporting signal survives the guards (→ §III.6) — uncorroborated triggers are recorded but
    carry no credit.
4.  **Audit the judgment against the facts.** The hallucination-trap and completeness gates (→ §III.7) check the
    judgment's claims back against the deterministic extraction before anything ships.

Where Mamey is the floor of fact, Sapote is disciplined inference standing on it — and the contract is what
keeps the inference from floating free.

## §III.2 · Mode B §1–§8 anatomy

**Mode B** is the full, gene-by-gene per-BGC dossier — the deliverable a reader opens to understand one cluster in
depth. It is produced by **two coupled artifacts**, and keeping them distinct is the whole point of the two-layer
contract: the engine emits a deterministic **§1–§8 scaffold** with facts pre-slotted (`report_mode.py`,
`render_full_scaffold`), and the judgment layer (the Sapote prompt) writes the **§1–§8 narrative report** that
fills prose into a fact-anchored skeleton. By default the board is **terse** — `render_terse` gives one compact,
fact-anchored line per BGC (always the contig, never a bare id; the KCB *band*, never a bare number); full Mode B
is generated only for the BGCs that earn it, which is safe because the boundary audit (§II.7) runs on the
structured record, not the prose — rigor does not depend on prose volume. <span class="tag t-engine">\[engine — `report_mode.py`\]</span>

**The engine scaffold headings (`report_mode.py:26` `MODE_B_SECTIONS`)** — what Python pre-slots facts under:
<span class="tag t-engine">\[engine\]</span>

1.  **Identity & location** — id, contig, region (no bare BGC id).
2.  **Architecture & class capacity** — `architecture_capacity` + arch confidence.
3.  **Boundary / truncation caveats** — `edge_status`.
4.  **KCB / MIBiG similarity (similarity, not identity)** — the band + top hit.
5.  **Source-derived scans** — cassettes, resistance, regulators.
6.  **Non-isolation / bioactivity context** — extract-level framing.
7.  **Lead tier & claim calibration** — lead tier + claim confidence.
8.  **Standing-rule / mis-anchor flags** — downgrade / primary-metab / mis-anchor flags.

**The judgment-layer report sections (Sapote kernel, `SAPOTE_SLIM_JUDGMENT_KERNEL.md`)** — the fuller narrative
the prose layer writes: §1 Overview table + Evidence Traceability · §2 **gene-by-gene domain analysis** (every CDS
± 3 kb, PFAM/TIGRFAM + bitscore, functional flag) · §3 module architecture (NRPS/PKS) or RiPP logic · §4
biosynthetic pathway hypothesis (≥120 words, cites domain IDs/bitscores) · §5 MIBiG/KCB comparison · §6
mechanistic link to bioactivity (≥60 words) · §7 **isolation strategy** (≥80 words; bldA tier, TFBS induction,
detection handle) · §8 **claim-safety audit**. The word-count floors force the prose layer to *show its reasoning*
rather than assert a class; §8 is the keystone — every report ends by auditing its own claims (→ §III.7). <span class="tag t-spec">\[spec\]</span>

> **Audit finding (engine ↔ prompt divergence).** The engine scaffold (`report_mode.py`) and the kernel report
> spec use **different §1–§8 heading schemes** — the engine's §2 is "Architecture & class capacity," the kernel's
> §2 is "gene-by-gene domain analysis," and so on. They are complementary in intent (skeleton vs. full narrative)
> but they are **not aligned heading-for-heading**, so a reader comparing a terse engine scaffold to a full Sapote
> report sees two different §1–§8 layouts. This is a documentation/contract divergence (analogous to the BSL-2
> drift, → §I.6 / patch F1), and a **reconciliation candidate** for the patch chat: pick one canonical §1–§8 scheme
> and have both the scaffold and the kernel name it. Flagged here rather than silently smoothed. <span class="tag t-finding">\[finding\]</span>

Two structural rules. **Batch order:** Interior BGCs and triggered BGCs (CCTT / §45 Tier-1 resistance / FLBR
anchor) are written in Batch 1; the remainder follow in subsequent batches — the highest-evidence clusters first.
**Split-pathway anchors:** when one pathway spans multiple contigs (→ §IV.4), the pathway unit and its secondary
fragments are noted in §1 and §5, WL is scored at the pathway-unit level, and the standalone Arch grade is still
reported. A compact one-line **terse** rendering exists for cohort-scale reading; it too always carries the contig
and the KCB *band* with the "(similarity, not identity)" tag inline — the discipline does not relax at smaller
sizes. <span class="tag t-engine">\[engine/spec\]</span>

## §III.3 · Scoring: the AB/AF/novelty model

Beneath the prose, every BGC is scored on three axes by a deterministic, transparent model — the numbers the
tiering and ranking are built on. The axes are **AB** (antibacterial potential), **AF** (antifungal potential),
and **novelty**. Each starts from a small base and accrues keyword-weighted credit from the cluster's product
text: <span class="tag t-engine">\[engine\]</span>

> base AB = 25 + AB-keyword score · base AF = 20 + AF-keyword score · novelty = 30 + novelty-keyword score

On top of the keyword bases, three forces move a score:

- **Diagnostic bonus (+25).** When a corroborated class-defining trigger fires, the relevant axis gets a fixed
  bonus — a nucleoside or HSAF/PTM trigger (T43-NUC, T43-PTM) lifts **AF**; a lanthipeptide/lasso/thioamide
  trigger (T43-LAN, T43-LASSO, T43-THA, …) lifts **AB**. This is how a gene-level diagnostic, not just keywords,
  reaches the score.
- **Rescue bonus.** A region supported by an RG-GMCI cross-contig rescue (→ §II.3) gains a bonus — a fragment plausibly part of a real pathway is surfaced for review. (Before v9.7.84 the rescue also reduced the now-removed fragmentation penalty.) <span class="tag t-engine">reworked v9.7.100</span> The rescue layer now reads the *full* ClusterBlast evidence, not KnownClusterBlast alone. Each shared-reference hit is tagged by database of origin (`db_kind`: knownclusterblast = characterized MIBiG cluster; clusterblast = cross-genome GenBank neighbour; subclusterblast = sub-operon, excluded from geometry), and each pair records a `rescue_evidence_base` (BOTH_KCB_AND_CB / CLUSTERBLAST_ONLY / KNOWNCLUSTERBLAST_ONLY) so a novel cluster with real genome neighbours but no characterized match is no longer invisible to a KCB-only path. A `functional_rescue_class` cross-checks gene-role complementarity by core-fraction asymmetry (one fragment core-bearing + one accessory-dominated = COMPLEMENTARY split; both core-rich = BOTH_CORE paralog, not a split). A **terminus-truncation rescue** (`TERMINUS_TRUNCATION_SPLIT`) flags the physical case — an Edge region whose boundary sits at the contig terminus, paired with a small (≤25 kb) complete "severed-arm" contig — and *overrides* an OVERLAPPING_PARALOG verdict that rests on a gene class legitimately multi-copy within one cluster (e.g. the bottromycin RRE/methyltransferase). All remain candidate inference, not nucleotide-level contig joining; a small severed-arm contig can belong to only one cluster, so where it pairs with several Edge regions the evidence base and functional class disambiguate, and physical confirmation still needs long-read / gap-PCR. See Glossary "RG-GMCI rescue layer".
- **Fragmentation penalty.** <span class="tag t-engine">removed v9.7.84</span> Boundary status no longer deducts from the score — Edge/FC BGCs showed no truncation signature in their base score, and the penalty was burying overlooked edge fragments at the tier threshold. Truncation is now a confidence grade (architecture C/D), not a score deduction. *Historical:* a penalty scaled by truncation pulled the axes down (more on AB/AF than novelty), reduced by any rescue. Axes are clamped to 0–100.

**The exact arithmetic (`scoring.py`).** For the reader who wants to reproduce a score by hand: <span class="tag t-engine">\[engine\]</span>

| Step | Rule |
|----|----|
| Bases | `AB = 25 + Σ AB_KEYWORDS` · `AF = 20 + Σ AF_KEYWORDS` · `novelty = 30 + Σ NOVELTY_KEYWORDS` |
| Diagnostic bonus | `+25` (`DIAGNOSTIC_BONUS`) to AB and/or AF when a *corroborated* AB/AF trigger fires |
| Novelty corrections | KCB cumulative `> 10000` → `−15` (strong known similarity = less novel); KCB `None` (dark) → `+5`; RiQ `< 0.5` → `+10` |
| Edge penalty <span class="tag t-engine">removed v9.7.84</span> | `edge_penalty` returns **0** for all boundary statuses (v9.7.84, engine 1.9.85). *Historical (≤1.9.84):* Interior 0 · Edge 10 · Full-contig 18. Truncation now affects confidence grade, not score. |
| RG-GMCI rescue | `rescue_bonus` = **8** (HIGH) / **4** (MODERATE) / 0 — added to every axis **and** subtracted from the penalty (`effective_penalty = max(0, penalty − 8|4)`); a primary-flagged region gets no rescue |
| Final | `ab = clamp₀…₁₀₀(base_ab + rescue − effective_penalty × 0.35)` · `af` same · `nov = clamp(novelty + rescue − effective_penalty × 0.2)` |

Two numbers carry design intent. The **penalty multiplier differs by axis** — `0.35` on AB/AF, `0.2` on novelty —
so truncation costs a bioactivity claim more than a novelty observation (a fragment can still be structurally
novel even when its activity can't be judged). And the **RG-GMCI rescue acts twice** — it lifts the axis *and*
shrinks the penalty — because a fragment with independent cross-contig support is being treated, correctly, as
part of a real pathway rather than a stub. A Full-contig region thus loses `18 × 0.35 = 6.3` from AB/AF and only
`18 × 0.2 = 3.6` from novelty, before any rescue.

The model is deliberately legible: a reader can see exactly why a cluster scored as it did — base keywords, which
diagnostic fired, whether a rescue applied — because a score whose derivation is opaque cannot be trusted or
corrected. The guards of §III.6 act on these same bases (flooring AB/AF for demoted regions) before the tier is
read.

## §III.4 · Triage and the lead-tier ladder

Triage turns the three axis scores into one **lead tier** — the headline that tells a reader how much attention a
cluster earns. The tier is read from the **best single axis**, `best = max(AB, AF, novelty)`, against fixed
thresholds: <span class="tag t-engine">\[engine\]</span>

> **Exceptional** ≥ 85 · **High** ≥ 70 · **Medium** ≥ 50 · **Inventory** \< 50

Using the best axis (not a sum) means a cluster strong on one axis — a potent antifungal that is unremarkable
antibacterially — reaches its deserved tier rather than being averaged into mediocrity. Two floors and one cap
then correct for known failure modes: <span class="tag t-engine">\[engine\]</span>

- **Tier-1 diagnostic floor.** A definitive class marker — a corroborated CCTT T43 trigger or a T1
  self-protection tier — floors the cluster to at least **Medium**, so a gene-only, KCB-dark lead with a weak
  text score still reaches lead tier instead of being buried. (Recorded as DIAG-FLOOR in the rationale.)
- **RiPP-fragment floor → cap.** A RiPP-family region truncated below the size threshold with no precursor
  captured is **capped at Inventory** — a fragment that cannot be evaluated as a product is not allowed to float
  above genuine leads. (RIPP-FRAGMENT-FLOOR.)
- **Guard demotions** (→ §III.6) strip AB/AF credit before tiering and drop the row from the **corrected lead
  rank** — the sequential rank computed only over rows not downgraded by a standing rule, primary-metabolism,
  or mobile-element flag.

The result is a ranked triage board where the tier and the corrected rank together encode both raw strength and
claim-safe eligibility.

**Worked example (real v9.7.33 runs — tier distribution across the three habitat strains).** The board's tier
mix tells an honest story about each strain at a glance: <span class="tag t-engine">\[engine: real runs; strains in the PRIVATE
worked-examples key\]</span>

| Strain | Raw BGCs | Tier distribution | Reading |
|----|----|----|----|
| Bumblebee *Streptomyces* | 68 | several **High** RiPP lanthipeptide leads (AB 70–76) + a long Inventory tail | corroborated T43-LAN diagnostics push real RiPP leads to High (→ §V worked example) |
| Attine *Pseudonocardia* | 50 | 49 Inventory / 1 Medium | one T43-THA-driven RiPP lead; five Promiscuous T43-HAL firings correctly stay Inventory (→ §IV worked example) |
| Bryophyte *Pseudonocardia* | 41 | 39 Inventory / 2 Medium | no CCTT diagnostics; the two Medium rows are Saccharide-topped raw scores that the standing-rule guard keeps out of the corrected rank |

The distribution is not a quality verdict on the organism — it reflects what survives the claim-safe machinery.
A strain with a corroborated class diagnostic (the bumblebee strain's lanthipeptides) surfaces High leads; a
strain whose top raw scorers are Saccharides or lone halogenases (the two *Pseudonocardia*) correctly shows a
near-flat board, because the guards keep unearned signal out of the lead rank. The board is read together with
the corrected count and assembly tier (→ §II.5), never alone.

**The Wet-Lab Decision Score (WL) — the bench counterpart to the lead tier.** Where the lead tier answers "how
strong is the capacity signal," **WL** (`§33`, judgment layer) answers a different question — "should this cluster
go to the bench, and how soon" — by scoring *actionability*, not just strength. It sums independent criteria and
maps to a decision band: <span class="tag t-engine">\[engine/spec — `SAPOTE_SLIM_JUDGMENT_KERNEL.md`\]</span>

| Adds |  | Subtracts |  |
|----|----|----|----|
| Interior BGC | +3 | Edge / Full-contig truncation | −2 |
| Arch A / B / C(pathway unit) | +3 / +2 / +1 | Tiny unanchored fragment | −3 |
| No KCB + strong diagnostic domains (Arch A) | +4 | Likely housekeeping | −3 |
| Strong KCB \>5000 with divergent tailoring | +3 |  |  |
| RiQ \<0.50 with coherent domains | +3 |  |  |
| TFBS clear induction condition · T3/T4 bldA | +2 · +2 |  |  |
| Specific mechanistic link to tested activity | +2 |  |  |
| Distinctive detection handle | +2 |  |  |
| Concordant Tier 1/2 resistance gene | +1 |  |  |

Decision bands: **≥10 Immediate · 7–9 Strong · 4–6 Conditional · 1–3 Inventory · ≤0 Deprioritized.** Two
deliberate design choices show the actionability framing. A region with **no KCB but strong diagnostic domains**
scores the single largest bonus (+4): an *un-anchored* but well-formed cluster is the most interesting thing to
take to the bench, the opposite of what a similarity-only ranking would surface. And the **Arch C penalty is not
applied to a split-pathway anchor** (→ §IV.4) — a pathway fragmented across contigs is scored at the pathway-unit
level so the assembly artifact does not bury a real lead. WL and lead tier are reported together: a cluster can be
Inventory on capacity strength yet Conditional-to-Strong on WL because it carries a clean detection handle and an
induction condition — which is exactly the cluster a bench program wants to know about. <span class="tag t-engine">\[engine/spec\]</span>

## §III.5 · Architecture confidence A–E

Distinct from the lead tier (how *promising*) is the **architecture confidence grade**, A through E — how
*structurally complete* the locus is. It is assigned deterministically at parse time from the cluster's boundary
status, its product class, its length, and its KCB signal, and it answers a different question than the score:
not "is this an interesting cluster?" but "how much of the cluster do we actually have?" <span class="tag t-engine">\[engine\]</span>

The grade runs from **A** (a structurally complete, well-bounded locus whose architecture can be read with
confidence) down to **E** (a highly fragmentary or ambiguous locus where the architecture call rests on little).
The two-level rule matters here: when fragments are integrated into one pathway unit (via RG-GMCI/EFLS), an
*anchor* fragment retains its own standalone architecture grade, while the *assembled pathway-unit* label is
graded more cautiously — the integration is a hypothesis, and the grade says so. Carrying A–E alongside the lead
tier lets a reader weigh a High-tier lead on a B-grade complete locus very differently from a High-tier lead
floored up from a D-grade fragment, even when the headline tier is identical.

**A–E is a parallel *display* signal, decoupled from the tier — it does not feed tiering.** The tier is read
solely from `best = max(ab, af, novelty)` (→ §V.1); the A–E grade is assigned at parse time and never enters the
tier computation. A HIGH-confidence, well-bounded locus can still land at Inventory if its keyword/diagnostic
score is low (observed: aromatic T2PKS and β-lactone loci graded confidently yet scoring Inventory). The grade
informs a reader's *weighting* of a lead, not the lead's rank. <span class="tag t-engine">\[engine\]</span> (parse-time grade, `models.py:71`;
tier at `scoring.py:455`).

Two distinct fields are easy to conflate and should be named separately: **`architecture_confidence`** (the A–E
grade — *how much of the locus do we have*, structural completeness, `models.py:71`) and
**`architecture_class_confidence`** (HIGH/MODERATE/LOW — *how sure are we of the class-capacity call*, the
"Class_Conf" board column, `models.py:74`). They answer different questions; only the former is the A–E grade.
The class-capacity call and its class-confidence travel alongside the grade so that marker-invisible classes still
show their capacity, but neither feeds the tier. <span class="tag t-engine">\[engine\]</span>

## §III.6 · The guards: how claim-safety is enforced in scoring

The claim-safety doctrine of §I.3 is not honored by good intentions; it is enforced by a set of **guards** that
withhold or strip credit when a signal does not earn it. Each guard fires only under specific, conservative
conditions and is recorded in the rationale so no demotion is silent. The guards, all consistent in discipline
(a corroborated real-class signal exempts the region — the "CCTT-veto" pattern): <span class="tag t-engine">\[engine\]</span>

- **CCTT corroboration.** A class-defining trigger that fires on a class-*incompatible* locus (e.g. a
  phosphonate trigger on a type-III PKS) is **uncorroborated**: it is recorded for the judgment layer to see, but
  grants no diagnostic bonus, no floor, and no class-capacity credit. Only corroborated triggers build the
  capacity claim.
- **Primary-metabolism / pigment guard.** A region whose own core genes are housekeeping/pigment markers, whose
  product class is only weak/over-call labels, and that has no Tier-1 diagnostic, has its AB/AF credit stripped to
  the floor — a topoisomerase mis-labeled "NRPS-like" or a carotenoid mis-read as antifungal does not rank as
  bioactivity.
- **Mis-anchor guard.** A KCB product-name anchor that lacks the class diagnostic it implies (an aminoglycoside
  anchor with no DOIS, a polyene anchor with too few PKS KS domains) has its anchor-derived axis credit
  suppressed — similarity to a name is not capacity for its product.
- **Mobile-element demotion (#28).** A region dominated by mobile/ICE machinery (gene-level integrase,
  recombinase, conjugation, rep) and not independently class-typed has its AB/AF credit floored and is dropped
  from corrected rank — an integrative element mis-typed as a biosynthetic class is not a discovery lead (→ §II.3,
  the HGT guard; the demotion mirrors the primary-metab guard). **Real-data caveat (this edition):** the demotion
  is logic-complete and fixture-verified and its *specificity* holds (no genuine lead lost), but its *positive
  path does not yet fire on the canonical ICE.* On `NZ_CP029601.1`, a mobile-dominant ICE (BGC032) carrying a
  `T43-LAN` trigger is **not** demoted, because that trigger — which the corroboration guard never marked
  uncorroborated (the ICE has no lanthipeptide cyclase/precursor) — satisfies the CCTT-veto. The two guards below
  do not yet **compose**: an uncorroborated trigger the corroboration guard missed becomes the veto that shields
  the impostor (→ §IV.8; logged as the \#28 follow-up). <span class="tag t-engine">\[engine: verified against NZ_CP029601.1\]</span>
- **Standing-rule downgrade.** The permanent exclusions of §I.6 (saccharide, NAPAA, hglE-KS-PREV-001) are removed
  from the corrected lead rank; for hglE the structural-novelty observation is explicitly preserved while the
  ecological claim is barred.

These guards are read sequentially and the order matters; the corroboration guard runs *first* and sets the
`tier1_diag` exemption that the primary-metab, mobile-element, and mis-anchor guards all consult — which is why a
corroboration miss propagates into the others (the composition contract is specified in → §V.4).

**The exact composition order (`scoring.py`).** The sequence is fixed, and reading it top-to-bottom is the only
way to predict a score, because each step's exemption flows into the next: <span class="tag t-engine">\[engine\]</span>

1.  **Bases** — `AB = 25 + kw`, `AF = 20 + kw`, `novelty = 30 + kw` (§III.3).
2.  **Corroboration guard** — resolve `_uncorr`; `corrob_triggers = triggers − _uncorr`. *(This is the augmentation
    point for the \#28 fix,* *shipped v9.7.35* *(option 1, `architecture_class_confidence == LOW`): marking a
    mobile-dominant, class-enzyme-absent gated trigger uncorroborated here makes the cascade below compose correctly
    for the class-trigger path — → §V.4.)*
3.  **Diagnostic bonus** — `+25` to AB and/or AF for corroborated AB/AF triggers.
4.  **`tier1_diag`** — `bool(corrob_triggers) or rt_tier.startswith("T1")`. This single boolean gates the next three.
5.  **Three suppression guards, each gated on `not tier1_diag`** — primary-metab floor (AB→25, AF→20); mobile-element
    \#28 floor (AB→25, AF→20); mis-anchor suppression (anchor-derived axis floored). A corroborated class signal
    (`tier1_diag = True`) exempts all three — the CCTT-veto.
6.  **Enediyne guard** — runs *independently* of `tier1_diag`: strips the spurious enediyne novelty credit and
    attaches the `[E-signal]` note (a PREV-001/hglE artifact must not keep the +18, even when a trigger fired).
7.  **Novelty corrections** — KCB `>10000` −15 / `None` +5; RiQ `<0.5` +10.
8.  **Penalty + RG-GMCI rescue → clamp → `best = max(ab, af, nov)` → tier** (Exceptional ≥85 / High ≥70 /
    Medium ≥50 / Inventory).
9.  **Tier-1 floor** — a corroborated diagnostic floats the tier up to ≥ Medium (DIAG-FLOOR), *except* the
    floor-excluded promiscuous prefixes `T43-HAL_` / `T43-XHAL_` (§V.2); a sub-threshold RiPP fragment is instead
    **capped** at Inventory (RIPP-FRAGMENT-FLOOR).
10. **Standing-rule downgrade** — saccharide / NAPAA / hglE-KS-PREV-001 dropped from the corrected lead rank (hglE
    keeps its structural-novelty observation).

The single most important fact in this sequence is step 4 → step 5: because the three suppression guards all gate
on `not tier1_diag`, **a trigger that the corroboration guard (step 2) fails to mark uncorroborated shields the
region from all three** — which is precisely the \#28 composition gap (an ICE's spuriously-corroborated `T43-LAN`
keeps `tier1_diag = True` and the mobile demotion never fires). The \#28 fix (v9.7.35) closes this for the
**class-trigger branch** of `tier1_diag`.

> **Audit finding — `tier1_diag` has *two* sources, and \#28 closes only one (PC-11, open).** Step 4 is
> `tier1_diag = bool(corrob_triggers) **or** rt_tier.startswith("T1")`. The \#28 fix acts on the first disjunct
> (the corroborated-trigger branch); it does **not** touch the second (the **T1 self-resistance** branch). On real
> data (WAC 01438, `NZ_CP029601.1`, BGC032) this means \#28 is only **partial**: the impostor dropped from rank 1→3
> (the \#28 goal — it no longer leads), but it is *not* fully demoted — `mobile_element_flag` stays empty — because
> the region also carries a `T1_DIAGNOSTIC_SELF_PROTECTION` tier (`APH_AAC` aminoglycoside resistance) that
> independently sets `tier1_diag = True` on the resistance path. `APH_AAC` resistance sitting inside full ICE
> machinery is *cargo, not self-protection* \[observed: T1 tier + ICE families; inferred: cargo\]. The fix (PC-12)
> does **not** mirror \#28's proxy or add a new layer — it uses the resistance tier's existing
> `class_concordant_groups` (`source_scans.py:888`): on a mobile-dominant region a T1 tier counts only if the
> resistance is class-concordant, and BGC032's `APH_AAC`-vs-lanthipeptide concordance is empty → cargo → floors. So
> the earlier framing — "the fix lives entirely in step 2, the rest of the cascade is already correct" — was
> **incomplete**: a real strain exposed a second, independent shield. The unifying root (label-vs-domain) and the
> full PC-12 treatment are developed in **§V.4**. <span class="tag t-finding">\[finding — shipped in v9.7.37\]</span>

Each guard is exempted by a genuine corroborated class signal, so the guards de-rank false positives without
touching real clusters — the entire point of fencing the judgment rather than blunting it.

## §III.7 · The hallucination-trap audit and the completeness gate

The last term of the contract (§III.1) is that the judgment is audited against the facts before it ships. Two
mechanisms do this. <span class="tag t-concept">\[concept/engine\]</span>

The **hallucination-trap audit** is the judgment layer's structured self-check: every claim the prose makes is
required to trace back to a deterministic fact in the scaffold — a count, a boundary, a scan result, a KCB band —
and a claim that cannot be traced is a trap to be caught and removed, not smoothed over. It is the operational
form of the project's observed/computed/inferred/assumed discipline: the audit asks, of each statement, *which
channel backs this?* and rejects statements that answer "none." This is a Sapote prompt-layer construct, not
engine Python, but it is checked against the engine's emitted facts.

The **completeness gate** is fail-closed and deterministic: it verifies that the denominator of the analysis —
how many of the strain's BGCs were actually carried through — reconciles against the antiSMASH source, so the
judgment layer cannot silently analyze a subset and present it as the whole. It works with the engine's recorded
**denominator type** for each KCB call (whether a similarity figure is computed against significant
KnownClusterBlast hits, the best subject cluster, or is unresolved), so a similarity band is never reported
against an unstated or wrong denominator. Fail-closed means the absence of a clean reconciliation is a failure,
not a pass — the safe default when completeness cannot be proven is to refuse, not to assume.

Together the two gates close the loop the contract opens: Sapote may interpret freely, but every interpretation
is pulled back to the deterministic floor and made to show its evidence before it reaches a reader.

------------------------------------------------------------------------

*End of Volume III. Next: Volume IV — Detection & Trigger Frameworks (the CCTT T43 framework and its fifteen
families in depth, KnownClusterBlast, RG-GMCI, CGAD, UMED, EFLS, the resistance screen and its HGT guard,
bldA/TTA, TFBS). Grounded in the running engine of its edition before it ships.*

</div>

<div id="vol4" class="section vol">
