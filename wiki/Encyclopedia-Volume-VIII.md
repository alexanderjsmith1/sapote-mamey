# Volume VIII — Reference & Apparatus

> **Currency scope:** This volume retains its historical edition and review stamps. Only the checks listed in the [currency record](Encyclopedia-Currency.md) have been refreshed for the current candidate. Other constants, numerical claims, literature interpretations, and worked-run results have not been comprehensively revalidated. A newer bundle does not make those older observations current.

*Edition: bundle v9.7.33 / engine Mamey 1.9.41 · re-grounded to bundle v9.7.91 / engine Mamey 1.9.91 on 2026-06-20 (the three denominator_type values, all nine KCB BGCRecord fields, the bundle_support/registry_inventory_v1.9.4.json SSOT + the \_NON_REGISTRY parity set, and the \_RULE_FLAG / \_OWN_PRODUCTS_ONLY standing-rule map all re-verified against the running engine; §VII.9 relocated to Volume VII and §VIII.7 brought inside this volume) · 2026-06-16*
*Chapters VIII.1–VIII.7. The back-of-book apparatus: glossary, KCB denominator reference, registry/catalog
parity, the standing-rules registry, version-history known-traps, the literature spine, and the module index.*

------------------------------------------------------------------------

## §VIII.1 · Glossary

| Term | Meaning |
|----|----|
| **BGC** | biosynthetic gene cluster — a genomic locus encoding one secondary-metabolite pathway |
| **antiSMASH** | the upstream tool that detects BGC regions; Mamey parses its output, never re-detects |
| **KCB / KnownClusterBlast** | similarity of a region to *characterized* MIBiG reference clusters — the anchor; similarity, **not** identity |
| **ClusterBlast** | similarity of a region to *other* antiSMASH regions; scaffolds RG-GMCI + a fallback denominator (§IV.1) |
| **MIBiG** | the curated repository of experimentally characterized BGCs; the KCB reference set |
| **CCTT / T43** | the class-corroborating trigger framework — 15 gene-signature families (§IV.3) |
| **corroboration gate** | a trigger earns credit only if it fired on a class-compatible locus; else **uncorroborated** (§V.3) |
| **diagnostic bonus** | `+25` to an axis when a corroborated diagnostic trigger fires (§V.2) |
| **RG-GMCI** | reference-guided gapped multi-contig integration — the cross-contig reconstruction adjudicator (§IV.4) |
| **FLBR / LMPKS** | fragmented large/modular-biosynthesis rescue — the megasynthase KS census (§II.6) |
| **EFLS** | cross-contig linkage by shared evidence (cassettes/CCTT/FLBR), complementing RG-GMCI (§II.3) |
| **CGAD** | chitinase / glycan-active-domain scan — chitin-active machinery, antifungal-relevant (§IV.5) |
| **UMED** | maturation/tailoring-enzyme detection — completeness evidence for a pathway (§IV.6) |
| **boundary status** | `Interior` \| `Edge` \| `Full-contig` — where a region sits on its contig (§II.2) |
| **corrected count** | `Interior + ½·Edge + ¼·Full-contig` — fragmentation-discounted BGC count (§II.5) |
| **assembly tier** | GOOD / MODERATE / POOR / VERY_POOR by interior fraction (≥70/45/20) (§II.5) |
| **lead tier** | Exceptional / High / Medium / Inventory by `max(AB,AF,novelty)` (≥85/70/50) (§V.1) |
| **architecture_confidence** | A–E structural-completeness grade; **decoupled from the tier** (§V.5) |
| **architecture_class_confidence** | HIGH/MODERATE/LOW confidence in the *class-capacity call* (distinct field) (§V.5) |
| **RiQ** | rarity/isolation quotient (0–1) per region; a low RiQ adds novelty (§II.2, §V.1) |
| **WL** | Wet-Lab Decision Score (judgment layer, §33) — an actionability score ("take to the bench?") summing Interior/Arch/KCB/RiQ/induction/handle criteria to a band (≥10 Immediate … ≤0 Deprioritized); reported alongside the lead tier (→ §III.4) |
| **mis-anchor** | a KCB anchor lacking its committed class diagnostic; anchor credit suppressed (§V.4) |
| **standing rule** | a permanent class downgrade (saccharide / NAPAA / hglE-KS-PREV-001) (§VIII.4) |
| **mobile-element demotion (#28)** | floors AB/AF for an ICE-dominated, non-class-typed region (§IV.8, §V.4) |
| **`[E-signal]`** | the neutral enediyne claim-safety note that replaced the BSL-2 flag in v9.7.28 (§I.6) |
| **DAPR** | dual antibacterial/antifungal priority ranking — the bench-facing target table (§V.7) — <span class="tag t-spec">`[spec]`</span> |
| **Mode B** | the per-BGC dossier the judgment layer produces (§1–§8) (Vol III) |
| **parse_confidence** | LOW/MEDIUM/HIGH honesty field on the KCB parse (§II.4) |
| **PEP-mutase (PpM/ppm)** | phosphoenolpyruvate mutase — the committed phosphonate-biosynthesis diagnostic (§IV.3, T43-PHO) |

The table above is the quick index. The entries below are the fuller, worked-example forms, grouped by where each
term sits in the pipeline flow. Examples use only public material (WAC and SID strains, named genomes, MIBiG
references): no unpublished identifier appears in a definition.

### Inputs and upstream evidence

**BGC (biosynthetic gene cluster)**: a contiguous genomic locus encoding the enzymes for one secondary-metabolite
pathway. *Example:* a 187 kb region carrying NRPS/PKS modules, tailoring enzymes, a regulator and a transporter,
detected by antiSMASH as one glycopeptide-class region, is one BGC. Mamey's unit of analysis is the BGC, and every
BGC is carried with its contig and region (`BGC044 | contig_3 | region044`), never as a bare id.

**antiSMASH**: the upstream detection tool that finds BGC regions and writes GBK/JSON/TXT output. *The boundary
this encyclopedia never crosses:* Mamey **parses** antiSMASH output and never re-detects a cluster. If antiSMASH did
not call a region, Mamey has no BGC there: the engine's job begins at antiSMASH's output, not at the genome.

**MIBiG**: the curated repository of experimentally characterized BGCs, each tied to a known product. It is the
reference set KnownClusterBlast compares against. *Why it matters:* a KCB hit means "this region resembles a MIBiG
entry," and the strength of that statement is bounded by what MIBiG actually contains, which is a fraction of
biosynthetic space.

**KCB / KnownClusterBlast**: the similarity of a region to *characterized* MIBiG clusters: the anchor a region is
read against. *The cardinal rule:* KCB is **similarity, not identity**. *Example:* a region with a strong KCB hit
to the balhimycin cluster has biosynthetic capacity consistent with a glycopeptide, it is **not** "a balhimycin
producer," and the engine renders the hit as a band ("(similarity, not identity)"), never as a bare percentage that
invites an identification.

**ClusterBlast**: the similarity of a region to *other antiSMASH regions* (not the characterized MIBiG set). It
scaffolds RG-GMCI's cross-contig reconstruction and supplies a fallback denominator when KCB is dark (§IV.1).
*Distinction worth keeping:* KCB compares to *characterized* clusters, ClusterBlast to *any* clusters, so a strong
ClusterBlast hit with no KCB hit means "resembles something, but nothing characterized."

**parse_confidence**: an honesty field on the *parse* itself, LOW / MEDIUM / HIGH (§II.4). *Example:* a region that
resolves a KCB anchor with a clean denominator is `HIGH`; a region with KCB dark or unresolved defaults to `LOW`.
It says how well the evidence was *read*, distinct from how complete the structure is (`architecture_confidence`)
or how promising the lead is (lead tier).

### Detection and corroboration

**CCTT / T43**: the class-corroborating trigger framework, eighteen gene-signature families (§IV.3). A trigger is a
gene/motif signature that *corroborates* a class-capacity claim. *Example:* the T43-LAN trigger fires on
lanthipeptide signatures; a corroborated T43-LAN raises confidence that a lanthipeptide-labelled region truly has
lanthipeptide capacity.

**corroboration gate**: the rule that a trigger earns credit only if it fired on a class-compatible locus, otherwise
it is marked **uncorroborated** (§V.3). *The canonical worked case:* on WAC 01438, BGC032's T43-LAN fired on a
mobile element with no LanC/LanM cyclase, so the trigger should be marked uncorroborated, the discipline that
keeps a label from corroborating itself (→ §V.4, label-vs-domain).

**diagnostic bonus**: `+25` added to an axis when a corroborated *diagnostic* trigger fires (§V.2). *Example:* a
corroborated T43-THA (thioamide) on an antibacterial-class region adds 25 to the AB axis, because the thioamide
signature is a strong, class-specific signal, not a generic keyword.

**mis-anchor**: a KCB anchor that lacks the class diagnostic it commits to, so the anchor-derived credit is
suppressed (§V.4). *Example:* a region anchored to an enediyne reference but carrying no genuine ene_KS signal is a
mis-anchor: the anchor *claims* a class the region's own domains do not support, so the engine declines the
anchor's credit rather than inheriting a false class.

**CGAD / UMED / EFLS / RG-GMCI / FLBR**: the source-derived and cross-contig scans (§IV.5–§IV.7, §IV.4, §II.6).
*One-line each with its job:* CGAD reads chitin-active machinery (antifungal/ecological context); UMED reads
maturation/tailoring enzymes (is the pathway *whole*); EFLS links contig fragments by shared evidence; RG-GMCI
rescues fragments against a reference; FLBR censuses megasynthase ketosynthases for a split PKS/NRPS.

**mobile-element demotion (#28)**: the guard that floors AB/AF for a region dominated by ICE/transposon machinery
and not independently class-typed (§IV.8, §V.4). *Example:* WAC 01438 BGC032 is mobile-dominant (five mobility
families) with a false lanthipeptide signal, and the demotion's job is to keep that integrative element from
ranking as a discovery lead. The class-axis half shipped in v9.7.35; the resistance-axis half (PC-12) shipped in
v9.7.37.

**PEP-mutase (PpM/ppm)**: phosphoenolpyruvate mutase, the committed first step of phosphonate biosynthesis and the
diagnostic behind T43-PHO (§IV.3). *Why it is load-bearing:* the C–P bond is rare and the PEP-mutase gene is its
strongest single marker, so a confirmed `ppm` turns a phosphonate *label* into a corroborated phosphonate
*capacity*, and recommends ³¹P-NMR follow-up.

### Geometry, counting, and confidence

**boundary status**: where a region sits on its contig, `Interior` / `Edge` / `Full-contig` (§II.2). *Example:* a
region with both flanks ≥5 kb from the contig ends is `Interior` (trusted); a region within 5 kb of an end is
`Edge` (possibly truncated); a region spanning ≥95% of its contig is `Full-contig` (the contig *is* the region,
so completeness is unknowable). Boundary status drives both the corrected count and the edge penalty.

**corrected count**: the fragmentation-discounted BGC count, `Interior + ½·Edge + ¼·Full-contig` (§II.5).
*Example:* a strain with 17 Interior, 31 Edge, 20 Full-contig regions has a *raw* count of 68 but a *corrected*
count of 17 + 15.5 + 5 = 37.5, the honest figure that does not let a shattered assembly inflate the headline.

**assembly tier**: GOOD / MODERATE / POOR / VERY_POOR by interior fraction (≥70 / 45 / 20) (§II.5). *Example:* a
draft genome where only 24% of regions are Interior is `VERY_POOR`, and every lead from it carries truncation
caveats, because most of its clusters sit at contig ends.

**RiQ (rarity / isolation quotient)**: a 0–1 score per region where a *low* value flags rarity and adds novelty
(§V.1). *Example:* a region that is isolated in similarity space (few near neighbours, KCB-dark) earns a low RiQ
and a novelty bump, the engine's way of rewarding "this looks unlike characterized things."

**architecture_confidence (A–E)**: the structural-completeness grade, **decoupled from the lead tier** (§V.5).
*Example:* a complete, well-resolved NRPS megacluster grades `A`; a truncated fragment grades toward `E`. A
high-promise lead can still be structurally incomplete, which is why this is a separate field from the tier.

**architecture_class_confidence (HIGH / MODERATE / LOW)**: confidence specifically in the *class-capacity call*,
distinct from structural completeness (§V.5). *Example:* BGC032's `LOW` means the engine does not believe the
lanthipeptide class call (no cyclase), and \#28 reads exactly this field as its enzyme-absent proxy.

### Scoring, ranking, and deliverables

**lead tier**: Exceptional / High / Medium / Inventory by `max(AB, AF, novelty)` (≥85 / 70 / 50) (§V.1). *Example:*
a region scoring AB 70 lands `High`; the tier is the single headline promise, summarising the three axes into one
actionable band.

**WL (Wet-Lab Decision Score)**: an actionability score that answers "take this to the bench?" by summing
Interior / architecture / KCB / RiQ / induction / detection-handle criteria into a band (≥10 Immediate … ≤0
Deprioritized) (§III.4). *Distinction from the lead tier:* the lead tier asks *how promising is the chemistry*, WL
asks *how ready is this for a wet-lab campaign* (a promising lead on a shattered contig with no detection handle
may tier High yet score low on WL).

**standing rule**: a permanent class downgrade applied regardless of score, saccharide / NAPAA / hglE-KS-PREV-001
(§VIII.4). *Example:* a saccharide region is dropped from the corrected lead rank even if its keywords score well,
because the class is excluded by standing policy (the downgrade is a `saccharide-exclusion` flag, not a deletion).

**`[E-signal]`**: the neutral enediyne claim-safety note that replaced the per-cluster BSL-2 flag in v9.7.28
(§I.6). *Example:* a genuine enediyne ene_KS signal attaches an `[E-signal]` note routing the lead to
cytotoxicity/self-protection review, with handling under standard non-selective lab SOPs, rather than a selective
biosafety flag that would falsely imply the unflagged clusters are "safe."

**Mode B**: the per-BGC dossier the judgment layer produces, the full §1–§48 treatment a reader opens to understand
one cluster in depth (Vol III). *Example:* a Mode B report walks identity → architecture → boundary → KCB → scans →
bioactivity → lead tier → claim-safety audit for a single region, ending by auditing its own claims.

**DAPR (dual antibacterial/antifungal priority ranking)**: the bench-facing target table that ranks leads on both
axes at once (§V.7) <span class="tag t-spec">`[spec]`</span>. *Example:* a DAPR row carries a strain's region with its AB and AF scores side by
side, so a reader scanning for antifungal leads and a reader scanning for antibacterial leads read the same table
from two directions.

## §VIII.2 · The KCB / denominator apparatus

A similarity band is meaningless without its denominator, so every KCB call records *against what* it was scored.
`denominator_type` takes one of three values: <span class="tag t-engine">\[engine\]</span>

| `denominator_type` | Meaning |
|----|----|
| `knownclusterblast significant hits` | scored against the region's KnownClusterBlast (MIBiG) significant hits — the headline KCB |
| `clusterblast best subject cluster` | fallback when no KnownClusterBlast hit exists — scored against the best ClusterBlast subject (§IV.1) |
| `UNRESOLVED` | KCB-dark; no denominator resolved (raises novelty +5, → §V.1) |

The full KCB resolution chain on each `BGCRecord` (each defaulting to `UNRESOLVED` so an unfilled field is never a
silent blank): `closest_mibig_accession`, `closest_candidate_kcb_product`, `closest_product_provenance`,
`source_kcb_file`, `source_kcb_locator`, `kcb_hit_rank`, `kcb_cumulative`, `kcb_protein_hits`, `denominator_type`.
A high `kcb_cumulative` resting on very few proteins (`kcb_protein_hits` ≤ 3) is a truncation artifact on
fragmented assemblies and must not be read as a strong hit (→ §IV.1). The cumulative-over-10,000 case subtracts
novelty (a well-known cluster is less novel), `> 10000 → novelty − 15` (§V.1). <span class="tag t-engine">\[engine\]</span>

**Reading a KCB call, field by field.** What the resolution chain records for a region with a genuine MIBiG hit:
<span class="tag t-engine">\[engine\]</span>

1.  `denominator_type = knownclusterblast significant hits`: the region scored against the characterised MIBiG set, the headline case.
2.  `closest_mibig_accession` + `closest_candidate_kcb_product`: the specific reference and its product, e.g. a glycopeptide reference. This is the *anchor*, and it is reported as a band with "(similarity)", never as an identification.
3.  `kcb_hit_rank = 1` with `kcb_protein_hits` well above 3: a top-rank hit resting on many shared proteins, so the similarity is structural, not a truncation artifact.
4.  `kcb_cumulative` moderate (not \>10000): a real but not over-familiar hit, so no novelty subtraction. A cumulative \>10000 would mark a very well-known cluster and subtract 15 from novelty.
5.  `closest_product_provenance` + `source_kcb_file` + `source_kcb_locator`: the evidence trail, the exact file and locator the call came from, so a reader can trace the anchor to its source.

The three denominator types are three epistemic states, not three formats: <span class="tag t-engine">\[engine\]</span>

1.  **`knownclusterblast significant hits` (resolved against MIBiG):** "this resembles a *characterised* cluster." The strongest statement KCB makes, and still only similarity.
2.  **`clusterblast best subject cluster` (fallback):** "no characterised match, but it resembles *some* antiSMASH region." A weaker anchor used only when KCB is empty, so the band must be read with that caveat.
3.  **`UNRESOLVED` (KCB-dark):** "resembles nothing the references contain." The engine does not treat this as failure, it treats it as *signal*: a KCB-dark region earns a novelty +5, because looking unlike known things is exactly what a discovery program is mining for. The denominator field is therefore not bookkeeping, it is the difference between "weak hit," "fallback hit," and "promising unknown," all of which a bare similarity percentage would flatten into one number.

## §VIII.3 · The marker catalog and registry-parity discipline

Marker detection has a **single source of truth** so a class signature can never drift between two definitions.
<span class="tag t-engine">\[engine\]</span>

| Artifact | Role |
|----|----|
| `bundle_support/registry_inventory_v1.9.4.json` | the runtime SSOT — the registry-backed detector reads marker values from here |
| `docs/MARKER_CATALOG.generated.json` | the regenerated human-readable catalog (must not be stale) |
| `tools/gen_marker_catalog.py` | regenerates the catalog from the registry + source |
| `tests/test_b2_registry_parity.py` | asserts the registry-backed detector reproduces the hardcoded literals bit-for-bit |

**The discipline:** editing a marker means changing the literal **and** the registry value **and** regenerating
the catalog — a marker added in one place and forgotten in another fails parity. A *new source-scan pattern dict*
that is not registry-backed (e.g. `MOBILE_ELEMENT_PATTERNS` from \#28) must be added to the parity test's
`_NON_REGISTRY` exemption set, alongside `VETO_CONTEXT_PATTERNS` and `PRIMARY_METABOLISM_PATTERNS`
(`test_b2_registry_parity.py:42`); the registry-backed set is the curated library-to-global map only. <span class="tag t-engine">\[engine\]</span>

## §VIII.4 · The standing-rules registry

Standing rules are permanent, institution-level downgrades — lessons encoded so they are not relearned per cohort.
The engine flag map (`scoring.py:152` `_RULE_FLAG`; `standing_rule_for`): <span class="tag t-engine">\[engine\]</span>

| Rule | Flag | Behavior | Subtlety |
|----|----|----|----|
| **Saccharide** | `saccharide-exclusion` | a region whose *own* product classes are exclusively saccharide is excluded from corrected lead rank | **committed-class guard:** a real NRPS/PKS that merely glycosylates keeps lead status (`_OWN_PRODUCTS_ONLY = {SACCHARIDE}`) — not a blanket sugar veto |
| **NAPAA** | `NAPAA-exclusion` | ε-poly-L-lysine-class; excluded from comparative/ecological claims | this edition marks NAPAA **neutral** (non-blocking) — the retired Nosema hypothesis is not repeated |
| **hglE-KS-PREV-001** | `hglE-KS-PREV-001` | prevalent glycolipid domain; habitat-non-specific (8 strains/7 genera/3 habitats) | marked **noted** (non-blocking); **structural novelty preserved**, only the ecological claim barred |
| **enediyne** | `[E-signal]` | a genuine enediyne keeps an `[E-signal]` claim-safety note | **no BSL-2 lab-safety flag** (removed v9.7.28 R-B; selective flags give false reassurance) (§I.6) |

The standing rules read the full product+MIBiG+KCB text, but the committed-class guard still protects a real lead
that merely *mentions* an excluded term. A standing rule excludes a region from the *corrected lead rank*; it does
not erase the observation (hglE's structural novelty is explicitly retained). <span class="tag t-engine">\[engine\]</span>

**The committed-class guard, worked.** The subtlety that keeps the saccharide rule from over-firing is worth seeing
concretely. Two regions can both carry the word "saccharide" and be treated oppositely: <span class="tag t-engine">\[engine\]</span>

1.  A region whose product classes are **exclusively** saccharide (a bare sugar cluster) is excluded from corrected lead rank with a `saccharide-exclusion` flag: its own products are `{SACCHARIDE}` and nothing else, so it is what the rule is for.
2.  A real **NRPS/PKS** cluster that happens to **glycosylate** its product carries "saccharide" in its text but its *own committed classes* include a megasynthase, so `_OWN_PRODUCTS_ONLY = {SACCHARIDE}` is false and the lead keeps its status. A glycosylated polyketide is a genuine lead that merely *mentions* sugar, not a sugar cluster.

The guard is the difference between *excluding a class* and *excluding a keyword*: the rule fires on what a region
*is* (its committed product set), not on whether an excluded term *appears* anywhere in its text. The same logic
protects the other rules: a real cluster that mentions an enediyne reference in its KCB text is not flagged
`[E-signal]` unless it carries a genuine ene_KS signal of its own.

**How a standing rule surfaces downstream.** A downgrade is never silent: the flag travels with the region into the
deliverables, so a reader sees both the exclusion and its reason. In DAPR (→ §VI.4) a saccharide-excluded region
appears in the **excluded list** with `saccharide-exclusion` as its stated reason, never in the ranked tracks; in
the figure data CSV it carries a `suppressed_saccharide_only` column so the suppression is auditable row by row (→
§VI.3); in Mode B its §34 trap card and §8 claim both name the downgrade. The standing rule is an institution-level
memory, the saccharide / NAPAA / hglE lessons encoded once so they are not relitigated per cohort, and the audit
trail is what lets a reader trust that the lessons were applied rather than assumed (the registry is read as the
single source of truth, → §VIII.3).

## §VIII.5 · Version history and known traps

The audit loop (§VII.6) leaves a trail of corrected mistakes; the most instructive become *known traps* — failure
modes a future editor or engineer must not re-introduce. <span class="tag t-engine">\[engine\]</span>

| Trap | The mistake | The guard |
|----|----|----|
| **Registry reassignment** | editing a marker literal only; the runtime reads the registry, so the edit has no effect | edit literal **+** registry value **+** regen catalog (§VIII.3) |
| **New pattern dict parity** | adding a non-registry pattern dict; parity test fails | add it to `_NON_REGISTRY` |
| **CCTT pipe-join** | an internal `\|` in a CCTT token; the registry pipe-join/split truncates it | use consecutive negative lookaheads, never an internal `\|` |
| **Public-tier scrub fixtures** | a test fixture with a literal `AS-NNN`; the scrub mangles it / the audit flags it | build fixtures by concatenation (`"AS-"+"123"`) or add to the scan exemption |
| **Per-tier assumption** | assuming a fix propagated to all tiers | run pytest **in each cut tier**; never assume (§VII.4) |
| **Line-number drift** | `str_replace` shifts line numbers; a later `sed -n` edits the wrong line | re-view before editing by line number |
| **Label-as-domain-evidence** | corroborating a class/resistance signal against a *label-derived* field (`cassette_families`, a product-class token) instead of parsed domain evidence — a label "confirming" itself | trace corroboration to a parsed-domain signal: `architecture_class_confidence` (class) / `class_concordant_groups` (resistance); never gate a label against another label |

**Worked known-trap — the T43-PHO precision arc** (the cleanest example of the audit loop correcting a
mis-grounded signal): the phosphonate trigger began over-firing (~84% of its hits uncorroborated); a carboxy-
phosphonate + PEP_mutase refinement and then a catabolic-`phn`/C–P-lyase/transporter exclusion (v9.7.31)
tightened the regex across three releases — yet a verified run *still* fires it on a few non-phosphonate regions,
so the real protection was always the **corroboration gate** (§V.3), not the regex. The lesson the trap encodes: a
tightened pattern reduces noise but does not replace corroboration; never document a trigger as "now
class-specific" on the strength of its regex alone. <span class="tag t-engine">\[engine\]</span>

**Worked known-trap — the cassette-contamination near-miss (PC-12 scaffold, rejected).** The label-vs-domain
principle has a sharp, recent illustration. A root-cause fix for the corroboration↔mobile composition gap (#28 /
PC-11) was scaffolded as a new `CCTT_DOMAIN_COMPAT` map that would domain-gate a class trigger against the region's
`cassette_families`. It looked principled — gate on domain evidence, only on a mobile background — but verification
killed it: `cassette_families` is itself **label-contaminated**. The `lanthipeptide` cassette pattern matches the
product-label token `lanthipeptide` (not only a LanC/LanM cyclase), so the canonical impostor BGC032 — which has
*no* in-region cyclase (the real `LanC` sits \>1.7 Mb away) — still carries a `lanthipeptide` cassette family via
loose flank coupling. Gating against it would have read that as domain corroboration and **silently undone \#28**.
The corrected fix used signals the engine already derives from parsed domains/context (`architecture_class_confidence`
on the class axis; `class_concordant_groups` on the resistance axis) and floored BGC032 cleanly. The trap encodes
the general rule and the reason the audit loop exists: *a label cannot be disciplined by another label* — and a
scaffold, however sound in direction, is not trusted until its inputs are verified against a real run. <span class="tag t-engine">\[engine\]</span>

## §VIII.6 · The literature apparatus *(<span class="tag t-science">`[science]`</span> spine — Pass-1 candidates; DOIs pending Pass-2 verification)*

The encyclopedia's <span class="tag t-science">`[science]`</span> claims rest on a literature spine. The table below is the **Pass-1 candidate list**
(from the Sapote–Mamey literature work order); each row's references are author-year candidates pending the
**Verified Literature Deep Dive** (Pass 2), where metadata (authors, DOI/PMID/PMCID) is verified and quantitative
fields pulled from full text. **DOIs are deliberately not listed here** — they are populated only after
verification, never from memory. <span class="tag t-cand">\[science: candidate, unverified\]</span>

| Theme | Grounds (encyclopedia §) | Pass-1 candidate references | DOI/PMID |
|----|----|----|----|
| A1 actinomycete SM genome mining | §I.1, §I.4 | Nett/Ikeda/Moore 2009; Rutledge & Challis 2015; Scherlach & Hertweck 2021 | Pass-2 |
| A2 BGC definitions / MIBiG | §VIII.2, §IV.1 | Medema et al. 2015 (MIBiG); Kautsar et al. 2020; Zdouc et al. 2025 (MIBiG 4.0) | Pass-2 |
| A3 antiSMASH / KCB | §II.1, §IV.1 | Medema et al. 2011; Blin et al. 2023 (antiSMASH 7); Blin et al. 2025 (8.0) | Pass-2 |
| A4 insect defensive symbiosis | §I.4 | — | Pass-2 |
| A5 selvamicin / polyene anchor | §I.4, §IV.5 | Van Arnam et al. 2016 (selvamicin); polyene/amphotericin reviews | Pass-2 |
| A7 bee ecology / pollinator health | §I.4 | Grubbs et al. 2021; Diarra et al. 2024 *(hedge: bee defensive mutualism less settled than attine/beewolf)* | Pass-2 |
| B8 assembly quality / fragmentation | §II.5 | BiosyntheticSPAdes 2019; antiSMASH boundary papers *(the corrected-count weights remain an internal heuristic, not a literature equation)* | Pass-2 |
| B9 modular PKS/NRPS splitting | §II.6, §IV.4 | Smith & Tsai 2015; ClusterCAD 2.0 2023; trans-AT reviews | Pass-2 |
| B10 similarity vs identity | §I.3, §IV.1 | Blin et al. 2019; Caesar et al. 2021; Bauman et al. 2021 | Pass-2 |
| B11 resistance-gene-guided mining | §IV.8 | Panter et al. 2018; ARTS; Dong et al. 2023 (RGDB) | Pass-2 |
| B12 mobile elements / ICEs | §IV.8, §V.4 (#28) | Choufa et al. 2022 (AICE); Choufa et al. 2024 | Pass-2 |
| B13 phosphonate biosynthesis vs catabolism | §IV.3 (T43-PHO) | Metcalf & van der Donk 2009; Peck & van der Donk 2013 | Pass-2 |
| B14 chitinases / CGAD | §IV.5 | GH18/GH19 + AA10 LPMO reviews; nikkomycin/polyoxin primary papers | Pass-2 |
| B15 bldA / TTA | §IV.9 | Leskiw et al. 1991; Chater & Chandra 2008 | Pass-2 |
| B16 RiPP maturation / UMED | §IV.6 | Yang & van der Donk 2013; Repka et al. 2017 | Pass-2 |
| B17 claim-safety / reproducibility | §I.2, §I.3 | Wilkinson et al. 2016 (FAIR); Caesar et al. 2021 | Pass-2 |

When Pass 2 verifies a row, its citation moves into the relevant chapter with a real DOI/PMID and the tag is
upgraded from <span class="tag t-cand">`[science: candidate]`</span> to <span class="tag t-science">`[science]`</span>. No citation graduates on memory alone.

------------------------------------------------------------------------

## §VIII.7 · Module index — `docs/modules/` <span class="tag t-engine">\[engine\]</span>

The `docs/modules/` directory contains reference modules for specific deliverable types and
knowledge layers. Each module specifies inputs, outputs, claim ceilings, and integration notes.
They are the deep reference behind the User Manual sections on deliverable types (→ §VI).

### Deliverable modules

- [`DELIVERABLE_AssemblyQC.md`](../docs/modules/DELIVERABLE_AssemblyQC.md) — AssemblyQC
- [`DELIVERABLE_ContigRescueReconstruction.md`](../docs/modules/DELIVERABLE_ContigRescueReconstruction.md) — ContigRescueReconstruction
- [`DELIVERABLE_EcologicalSynthesis.md`](../docs/modules/DELIVERABLE_EcologicalSynthesis.md) — EcologicalSynthesis
- [`DELIVERABLE_FamilySeeds.md`](../docs/modules/DELIVERABLE_FamilySeeds.md) — FamilySeeds
- [`DELIVERABLE_FigureSuggestion.md`](../docs/modules/DELIVERABLE_FigureSuggestion.md) — FigureSuggestion
- [`DELIVERABLE_LMPKSRescue.md`](../docs/modules/DELIVERABLE_LMPKSRescue.md) — LMPKSRescue
- [`DELIVERABLE_MetabolomicsReadiness.md`](../docs/modules/DELIVERABLE_MetabolomicsReadiness.md) — MetabolomicsReadiness
- [`DELIVERABLE_ReviewerAttack.md`](../docs/modules/DELIVERABLE_ReviewerAttack.md) — ReviewerAttack
- [`DELIVERABLE_SubsetPanel.md`](../docs/modules/DELIVERABLE_SubsetPanel.md) — SubsetPanel
- [`DELIVERABLE_WetLabMatrix.md`](../docs/modules/DELIVERABLE_WetLabMatrix.md) — WetLabMatrix

### Knowledge modules

- [`KNOWLEDGE_ConstellationReporting.md`](../docs/modules/KNOWLEDGE_ConstellationReporting.md) — ConstellationReporting
- [`KNOWLEDGE_DiagnosticDomainCombos.md`](../docs/modules/KNOWLEDGE_DiagnosticDomainCombos.md) — DiagnosticDomainCombos
- [`KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md`](../docs/modules/KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md) — Evidence Axes and Lead Class Logic
- [`KNOWLEDGE_JudgmentChecks.md`](../docs/modules/KNOWLEDGE_JudgmentChecks.md) — JudgmentChecks
- [`KNOWLEDGE_LeadTiers.md`](../docs/modules/KNOWLEDGE_LeadTiers.md) — LeadTiers

### Other modules

- [`MODE_B_WRITE.md`](../docs/modules/MODE_B_WRITE.md) — MODE B WRITE
- [`SAPOTE_LEAD_DETAIL_MODULE.md`](../docs/modules/SAPOTE_LEAD_DETAIL_MODULE.md) — SAPOTE LEAD DETAIL MODULE

------------------------------------------------------------------------

*End of Volume VIII — and of the eight-volume working draft. The set now spans Foundations (I), the Mamey engine
(II), the Sapote layer (III), Detection (IV), Scoring & DAPR (V), Deliverables (VI), Operations & Release (VII),
and this Reference apparatus (VIII). Each chapter is grounded in the running engine of its edition; the <span class="tag t-science">`[science]`</span>
spine awaits Pass-2 verification before its citations are final.*

</div>

<div id="vol9" class="section vol">
