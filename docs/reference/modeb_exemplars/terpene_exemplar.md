# Mode B — BGC001 (BA000030.4 · region001) — *Streptomyces avermitilis* MA-4680

**Class exemplar: terpene.** Public type strain (GCA_000009765.2). Interpretation is claim-safe: biosynthetic *capacity* only; KCB/BLASTp are *similarity, not identity*; the region is cited as BGC001 · BA000030.4 · region001 throughout.

## §1 Identity and node/region
BGC001 sits on contig BA000030.4 (the *S. avermitilis* MA-4680 chromosome), antiSMASH region001, spanning ~21.0 kb. It is an **Interior** BGC — bounded on both flanks by non-cluster sequence on a finished chromosome, so no contig-edge truncation caveat applies. The region is a single-product terpene locus; its KnownClusterBlast top anchor is MIBiG `BGC0000683.3` (avermitilol), the characterized *S. avermitilis* sesquiterpenoid alcohol cluster, so this locus is the strain's own well-studied terpene system rather than a distant homolog. Cited hereafter as BGC001 · BA000030.4 · region001.

## §2 Why this BGC was selected
Selected as the **terpene class exemplar** for the public reference set: it is Interior (no boundary ambiguity), it carries a single dominant biosynthetic core gene whose independent BLASTp channel returns an unambiguous characterized match, and its KCB anchor is a MIBiG entry a reader can pull and check. It is a deliberately *clean* teaching case — one catalytic core plus honestly co-captured neighbours — chosen to show the reconciliation workflow rather than to showcase a difficult call.

## §3 Boundary and assembly status
Assembly tier **GOOD** (complete, finished chromosome; interior fraction well above threshold), boundary **Interior**. Because the locus is Interior on finished sequence, gene inventory and boundaries are taken as complete: there is no truncated-terminal-module caveat and no edge/full-contig confidence downgrade. The only completeness caveat is the ordinary one — antiSMASH region borders are heuristic, so the two or three genes at each flank are context, not guaranteed cluster members (addressed per gene in §4).

## §4 Gene-by-gene interpretation

**Evidence grid (store-backed facts + reconciled independent homology).** Domain calls are antiSMASH Pfam; the BLASTp column is an independent online run against nr (operator-supplied), reconciled against the domain call as CONFIRM / REFINE / OVERTURN. No per-gene observation is stated that is not in a real result.

| Locus | aa | antiSMASH domains | BLASTp top hit (nr) | %id | Reconciliation |
|---|---|---|---|---|---|
| **ctg1_83 ●** | 335 | Terpene_syn_C_2 | avermitilol synthase [*S. avermitilis*] (also PDB 9Y6I chain A) | 100.0 | **CONFIRM** — the class-defining call and its independent match agree exactly; the top hit is a solved-structure sesquiterpene synthase. |
| ctg1_77 | 145 | Polyketide_cyc | (polyketide cyclase / SnoaL-like) | — | CONFIRM (domain-level) — a cyclase-fold accessory; not the terpene core. |
| ctg1_79 | 496 | HATPase_c; HisKA | sensor histidine kinase [*Streptomyces mirabilis*] | 96.4 | **CONFIRM (as a kinase) → co-captured, not terpene-core.** The BLASTp call agrees it is a two-component sensor kinase — regulatory context swept into the region border, not part of the terpene chemistry. |
| ctg1_80 | 244 | Response_reg; Trans_reg_C | (DNA-binding response regulator) | — | Partner of ctg1_79 — the response-regulator half of a two-component system; regulatory, not biosynthetic. |
| ctg1_81 | 490 | DUF2079 | DUF2079 domain-containing protein [*Streptomyces* sp.] | 97.6 | CONFIRM (as an uncharacterized membrane protein) — function unknown; carried as co-located, not interpreted into the product. |
| ctg1_82 | 140 | Ribonuc_L-PSP | (RidA/YjgF-family deaminase) | — | Housekeeping-type accessory; not cluster-specific. |
| ctg1_85 | 186 | DDE_Tnp_1 | (transposase, DDE domain) | — | Mobile-element remnant at the flank — a boundary artefact, explicitly not a biosynthetic member. |

Prose walkthrough. The biosynthetic identity of this region rests on a single catalytic core, **ctg1_83** (●): its antiSMASH Terpene_syn_C_2 call and its BLASTp top hit — *avermitilol synthase*, at 100 % identity to a solved-structure sesquiterpene synthase — are in exact agreement, which is the strongest form of the three-channel reconciliation (intrinsic domain signature and extrinsic homology both point to the same characterized enzyme). Everything else in the region is either regulatory (the ctg1_79/ctg1_80 two-component pair, a sensor histidine kinase and its response regulator, confirmed as such by BLASTp) or non-core accessory/mobile sequence (ctg1_81 DUF2079, ctg1_82 deaminase, ctg1_85 transposase remnant). The honest reading is therefore a **single-enzyme terpene locus** with co-captured regulatory and flanking genes — a common pattern where antiSMASH's region border sweeps in adjacent two-component and mobile-element genes. The reconciliation adds no OVERTURN here: the class call is confirmed and the neighbours are correctly identified as context, which is exactly what a clean terpene exemplar should show.

## §5 Core biosynthetic logic
A class I terpene synthase (ctg1_83) with the canonical Terpene_syn_C fold. Mechanistically this family cyclises a prenyl-diphosphate substrate (for a sesquiterpene alcohol product, farnesyl diphosphate) via metal-dependent ionisation and carbocation cyclisation, with the terminal hydroxyl introduced by water capture of the final cation. The single-synthase architecture means the region encodes the cyclisation step; upstream isoprenoid supply (FPP) is provided by primary metabolism, not by genes in this region.

## §6 Tailoring and maturation logic
No dedicated tailoring enzymes (oxidoreductases, methyltransferases, glycosyltransferases) are resolved within the region borders beyond the synthase itself — consistent with a simple sesquiterpene-alcohol product that requires only cyclisation and hydroxylation performed by the synthase. Absence of tailoring genes is stated as an observation, not proof: any peripheral tailoring would sit outside the heuristic border and is not claimed here.

## §7 Transport, resistance, and regulation
Regulation is local and explicit: the ctg1_79 / ctg1_80 two-component system (sensor histidine kinase + response regulator) is co-located and plausibly modulates expression, though co-location is not proof of dedicated cluster regulation. No source-derived resistance determinant is flagged (Resistance_tier: NULL_NO_SOURCE_DERIVED_RESISTANCE), and no dedicated exporter is resolved within the region — expected for a small volatile/semi-volatile terpenoid that does not require a dedicated efflux/resistance cassette.

## §8 Comparator/KCB interpretation
KnownClusterBlast returns MIBiG `BGC0000683.3` (avermitilol) as the top anchor (score 691). Because this is *S. avermitilis*' own characterized cluster, the comparator is best read as **identity of source, not merely similarity** — but the *product* claim still travels as capacity: the genome encodes the avermitilol synthase, which is consistent with capacity for an avermitilol-like sesquiterpenoid, not a demonstration that the compound is made under any given condition. KCB is a similarity channel; here it happens to point back at the strain's own reference entry.

## §9 Alternative hypotheses
The single-synthase architecture leaves little ambiguity about class (it is a terpene locus). The open question is *which* sesquiterpenoid. The name 'avermitilol' here is a **comparator by similarity, not an identity claim** — KCB reports backbone similarity and the BLASTp hit reports enzyme homology; neither demonstrates the compound. That said, the comparator is unusually well-supported: the per-gene BLASTp genus (*S. avermitilis*) matches the producer of the avermitilol reference, so the similarity anchor and the source genus agree — the failure mode where a KCB name comes from a different-genus producer does not apply here. Even so, a class I synthase can be promiscuous and the realised product depends on substrate and conditions, so the leading hypothesis is an avermitilol-*like* sesquiterpene alcohol from this cyclase fold, held as capacity. No plausible alternative makes this a non-terpene locus.

## §10 Fragmentation and co-capture risks
Fragmentation risk is nil (Interior, finished chromosome). Co-capture risk is the relevant one and is real: as §4 shows, the region border has swept in a two-component regulatory pair and a transposase remnant. These are flagged as non-core so they cannot leak into a product or ecological claim. This is the exemplar's teaching point — Interior does not mean every gene in the border is biosynthetic.

## §11 Product-family interpretation
Product family: **sesquiterpenoid alcohol** (avermitilol-like), stated as capacity. The region encodes the cyclase for such a product; the specific stereochemistry/decoration is not claimed beyond what the synthase homology supports. No yield, titre, or condition-dependent production is claimed.

## §12 Bee/microbe ecological interpretation
Source-independent framing: this is a public reference type strain, not a bee/wasp/bryophyte isolate, so no host-associated ecological claim is made. Generically, actinomycete sesquiterpenoids can contribute to chemical signalling and antimicrobial/defensive repertoires; that is a class-level statement (`assumed`), not a claim about a realised ecological role here.

## §13 Antibacterial/antifungal relevance
No extract-level bioactivity data accompanies this public genome, so no antibacterial/antifungal phenotype is asserted for this BGC. Terpene synthases of this family are not, in general, the primary drivers of antibacterial extract activity; any relevance would be at the extract level and is not evidenced here.

## §14 What cannot be claimed
Cannot claim: that avermitilol is *produced* (only that the capacity is encoded); that any neighbouring regulatory or mobile-element gene participates in biosynthesis; any bioactivity or ecological role; any titre or condition-dependence. The 100 % BLASTp identity establishes the enzyme's identity, not the compound's production.

## §15 Missing evidence
Missing: LC-MS/GC-MS confirmation of the sesquiterpenoid product; expression data (whether the two-component system activates the locus); substrate assay of the synthase. These are the experiments that would move the card from encoded-capacity to demonstrated-product.

## §16 BLASTP/HMMER next steps
The core is settled (three-channel agreement on ctg1_83: Pfam Terpene_syn_C_2, BLASTp 100 % to avermitilol synthase, and the solved PDB structure 9Y6I of that enzyme). Next steps are therefore confirmatory rather than exploratory. First, HMM-adjudicate the flanking Polyketide_cyc gene (ctg1_77) to decide whether it is a genuine cyclase accessory or border noise swept in by the region heuristic. Second, run per-gene BLASTp on the two-component pair (ctg1_79/ctg1_80) only if regulatory attribution matters for a follow-up expression study — it is not needed for the product call. No OVERTURN is pending anywhere in the region, so no re-adjudication of the catalytic core is required; the homology channel and the domain channel already agree.

## §17 LC-MS / fermentation implications
For detection, target a volatile-to-semi-volatile sesquiterpene alcohol. GC-MS of an organic extract or a headspace sampling is the first-line method for a small terpenoid; LC-MS with a sesquiterpenoid mass window is the complementary approach, using the avermitilol reference mass (C15 sesquiterpene alcohol) as the search anchor. Because a co-located two-component system (ctg1_79/ctg1_80) may gate expression, do not assume constitutive production: screen across several media and growth phases rather than a single condition, since a negative result under one condition would be uninformative. If a candidate mass is seen, confirm against an avermitilol standard or by exact mass and fragmentation before attaching the comparator name to the observed compound.

## §18 Figure/locus-map notes
A locus map should mark ctg1_83 as the single catalytic core (●) and label it with both channels (Terpene_syn_C_2 / avermitilol synthase, 100 %), render ctg1_79/ctg1_80 as a linked two-component regulatory pair with a connector, and grey out ctg1_85 (transposase remnant) as a border artefact. The visual goal is to reinforce the single-core reading — one filled marker, everything else rendered as context — so a reader does not mistake the co-captured regulatory or mobile genes for biosynthetic members.

## §19 Final Mode B judgement
BGC001 is a **source-derived, Interior terpene BGC** with a single class I sesquiterpene-synthase core (ctg1_83) whose independent homology channel confirms it as an avermitilol synthase at 100 % identity. Biosynthetic capacity is consistent with an avermitilol-like sesquiterpenoid; the remaining region genes are regulatory or accessory and are excluded from the product interpretation. Confidence in the *class* call is high; the *product* remains a capacity statement pending chemical confirmation.

## §20 Next actions
Priority action: GC-MS (or LC-MS) on an organic extract across several conditions, targeting the avermitilol sesquiterpenoid mass, then confirm any candidate against a reference standard before naming it. Secondary: optional HMM adjudication of the flanking Polyketide_cyc gene (ctg1_77) to settle whether it is a genuine accessory. No re-analysis of the catalytic core is required — the three-channel agreement on ctg1_83 is already the strongest available evidence for the class call, so effort should go to the chemical confirmation step, which is the only thing that converts encoded capacity into a demonstrated product.

## §24 Scaffold novelty score
Novelty is **LOW**: the core terpene synthase (ctg1_83) matches avermitilol synthase at 100% by both KCB and independent BLASTp, so the scaffold is a characterized terpenoid backbone with a direct MIBiG/named comparator, not a novel class. Stated as a novelty read on the backbone, not a product or titre claim; downstream tailoring, if any, is not scored here because it is not the class-defining core.

## §27 Self-resistance assessment
No source-derived self-resistance determinant is present (NULL_NO_SOURCE_DERIVED_RESISTANCE). Consistent with a non-toxic terpenoid that does not require a dedicated resistance/immunity cassette; absence is reported as an observation, not proof of non-toxicity.

## §28 Evidence provenance ledger
- Region identity, boundary, KCB anchor, TTA/resistance tiers: **store-backed** (Mamey inventory + KCB, `BGC0000683.3` avermitilol #1, score 691).
- Domain calls (Terpene_syn_C_2, HisKA, etc.): **store-backed** (antiSMASH Pfam).
- Per-gene top hits (avermitilol synthase 100 %; sensor histidine kinase 96.4 %; DUF2079 97.6 %): **operator-supplied** independent BLASTp (nr), reconciled in §4.
- No reconstructed or fabricated observation is present. Every §4 row traces to a real BLASTp result or an antiSMASH call.

## §30 Experimental decision tree
1. Detect the sesquiterpenoid (GC-MS/LC-MS on extract). → If detected, proceed; if not, vary condition (the two-component system may gate expression) and retry.
2. Confirm identity vs the avermitilol reference standard. → If matched, the capacity → product link is closed for this condition.
3. (Optional) express ctg1_83 heterologously with FPP to confirm the synthase product independent of native regulation.
