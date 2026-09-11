# Mode B — BGC004 (BA000030.4 · region004) — *Streptomyces avermitilis* MA-4680

**Class exemplar: t1pks (modular type I PKS).** Public type strain (GCA_000009765.2). Claim-safe throughout: biosynthetic *capacity* only; KCB/BLASTp are *similarity, not identity*; cited as BGC004 · BA000030.4 · region004. **This region is OVER-MERGED — antiSMASH resolved ≥2 protoclusters (chemical_hybrid). It is analysed per protocluster below; no single region-level product claim is made.**

## §1 Identity and node/region
BGC004 lies on contig BA000030.4 (the finished *S. avermitilis* MA-4680 chromosome), antiSMASH region004, spanning ~108.2 kb — a large multi-modular locus. It is **Interior** (both flanks are non-cluster sequence on a complete chromosome). The KnownClusterBlast top anchor is MIBiG `BGC0000059.5` (filipin), the characterized polyene-macrolide PKS, at a very high score (101801), so at least one protocluster here corresponds to the strain's own well-studied filipin-type system. Because the region is over-merged, "BGC004" names an antiSMASH border enclosing more than one biosynthetic system; per-protocluster reads follow in §5/§9/§10. Cited hereafter as BGC004 · BA000030.4 · region004.

## §2 Why this BGC was selected
Selected as the **modular type I PKS exemplar**: it carries the largest catalytic-core genes in the reference set (three multi-domain PKS subunits up to ~6,160 aa), its KCB anchor is a canonical MIBiG polyene cluster, and — usefully for a teaching card — it is *over-merged*, so it also exemplifies how to handle an antiSMASH region that encloses more than one system without collapsing it into a single product. It shows both the clean case (PKS subunits confirmed by independent homology) and the disciplined case (refusing a region-level product claim).

## §3 Boundary and assembly status
Assembly tier **GOOD** (finished chromosome; high interior fraction), boundary **Interior** — no contig-edge truncation caveat. The dominant completeness caveat here is *not* fragmentation but **over-merge**: antiSMASH flagged ≥2 protoclusters of chemical_hybrid kind, which is its own "≥2 BGCs in this region" signal. Region-level aggregate scores and the single KCB anchor are therefore composites over multiple systems and must be split before any product-family statement (§5, §11). Gene inventory itself is taken as complete (Interior, finished sequence).

## §4 Gene-by-gene interpretation

**Evidence grid.** Domain calls are antiSMASH Pfam; the BLASTp column is an independent operator-supplied online run against nr, reconciled as CONFIRM / REFINE / OVERTURN. No observation is stated that is not in a real result.

| Locus | aa | antiSMASH domains | BLASTp top hit (nr) | %id | Reconciliation |
|---|---|---|---|---|---|
| **ctg1_458 ●** | 3352 | ACP; Acyl_transf_1; Docking; KAsynt_C_assoc; KR | type I polyketide synthase [*Streptomyces* sp.] | 89.9 | **CONFIRM** — the modular-PKS call and the homology channel agree; a multi-module KS-AT-KR-ACP subunit. |
| **ctg1_459 ●** | 6160 | ACP; Acyl_transf_1; Docking; KAsynt_C_assoc; KR | type I polyketide synthase [*S. avermitilis*] | 96.5 | **CONFIRM** — the largest subunit; top hit is *S. avermitilis*' own PKS, confirming both class and source. |
| **ctg1_460 ●** | 1836 | Acyl_transf_1; Docking; KAsynt_C_assoc; KR | SDR family NAD(P)-dependent oxidoreductase | 96.0 | **REFINE** — antiSMASH reads it as a PKS module; the BLASTp top hit resolves to an SDR-family oxidoreductase, i.e. the ketoreductase (KR) domain dominates the best match. The gene is still PKS-associated, but the independent channel refines the emphasis from "full module" to "KR/SDR-dominant." |

Prose walkthrough. The catalytic identity of this locus rests on the modular type I PKS subunits ctg1_458, ctg1_459 and ctg1_460 (all ●). The two largest (ctg1_458, ctg1_459) are confirmed by independent BLASTp as type I polyketide synthases — ctg1_459's top hit is *S. avermitilis*' own PKS at 96.5 %, agreeing on both class and source. ctg1_460 is the instructive one: antiSMASH annotates the full PKS-module domain string, but the BLASTp top hit lands on an SDR-family NAD(P)-dependent oxidoreductase — the KR (ketoreductase) domain is an SDR fold, and here it dominates the best global match. That is a **REFINE, not an OVERTURN**: the gene remains PKS-associated (it carries Acyl_transf and KAsynt domains too), but the homology channel usefully flags that its strongest similarity is to the reductive tailoring chemistry rather than to a full extension module. Because the region is over-merged, these subunits are not assumed to belong to one assembly line; the per-protocluster split (§5) governs which modules act together. The KR-order and module grammar that BLASTp cannot resolve are the HMM channel's job (§16), not asserted here.

## §5 Core biosynthetic logic
Per protocluster, not per region. The confirmed subunits (ctg1_458/459) encode canonical KS-AT-(KR)-ACP modular extension — decarboxylative Claisen condensation of malonyl/methylmalonyl extender units with programmed β-keto processing — the logic of a *cis*-AT type I polyketide assembly line. Because antiSMASH split this region into ≥2 protoclusters, the module set is **not** read as one continuous assembly line: each protocluster's subunits are grouped separately, and no single chain-length or product is inferred across the whole region. For the filipin-anchored protocluster, the logic is that of a polyene-macrolide PKS; the second protocluster's logic is treated as a distinct system pending its own core read.

## §6 Tailoring and maturation logic
Type I polyene PKS systems of this class typically recruit cytochrome P450 hydroxylases and, for filipin-type polyenes, post-PKS oxidative tailoring; ctg1_460's KR/SDR-dominant signature is part of the reductive processing rather than standalone tailoring. Specific tailoring genes are not enumerated as product-committing here because the over-merge means tailoring enzymes cannot be confidently assigned to a single protocluster without the per-protocluster gene partition. Any tailoring attribution is therefore held at "present in region, protocluster assignment pending."

## §7 Transport, resistance, and regulation
No source-derived resistance determinant is flagged (Resistance_tier: NULL_NO_SOURCE_DERIVED_RESISTANCE). Large modular-PKS loci commonly co-encode ABC transporters and pathway-specific regulators; where present these are read as export/regulatory context, not as product evidence. Because the region is over-merged, transporter/regulator genes are not assigned to a specific protocluster here. The absence of a dedicated resistance cassette is consistent with a polyene whose self-protection is membrane-sterol-composition-based rather than an encoded immunity gene, but this is stated as an observation, not a mechanism claim.

## §8 Comparator/KCB interpretation
KnownClusterBlast returns MIBiG `BGC0000059.5` (filipin) at a very high score (101801). Because filipin is a characterized *S. avermitilis/filipinensis*-lineage polyene, the comparator here is best read as strong backbone similarity to a known polyene-macrolide PKS, plausibly the strain's own filipin-type system. The high score reflects the over-merge as well (region-level KCB aggregates across protoclusters), so it is **not** taken as identity of the whole region to filipin — only that one protocluster is filipin-like. KCB remains a similarity channel; the per-gene BLASTp genus (*S. avermitilis*) is consistent with the comparator's producer lineage.

## §9 Alternative hypotheses
The class is not in doubt (modular type I PKS — confirmed on two subunits). The real alternatives concern the over-merge: (a) the region is a single large filipin-type assembly line that antiSMASH split at an internal boundary, versus (b) it is two independent PKS systems co-located on the chromosome. The chemical_hybrid protocluster call favours (b) or a genuinely hybrid arrangement. Because "filipin" is a **KCB comparator by similarity, not an identity claim**, the product is held as capacity for a filipin-*like* polyene from at least one protocluster, not as a demonstration that filipin is produced. Naming is supported by the source-genus match but not proven by it.

## §10 Fragmentation and co-capture risks
Fragmentation risk is nil (Interior, finished chromosome). The dominant risk is **over-merge**, already flagged: treating the region as one product would fabricate a fused assembly line that antiSMASH itself split. This is handled by analysing per protocluster and refusing a region-level product claim. Co-capture of regulatory/transport genes at the flanks is the secondary risk and is handled by not attributing them to a specific system.

## §11 Product-family interpretation
Product family: **polyene macrolide (filipin-like)** for the filipin-anchored protocluster, stated as capacity; the second protocluster is left as an unnamed modular-PKS product pending its own read. No single region-level compound is named — that would violate the over-merge discipline. No titre or condition-dependent production is claimed.

## §12 Bee/microbe ecological interpretation
This is a public reference type strain, not a host-associated isolate, so no bee/wasp/bryophyte ecological role is claimed. Generically, polyene macrolides are antifungal membrane-sterol binders; that is a class-level property (`assumed`), not a claim about a realised ecological function here.

## §13 Antibacterial/antifungal relevance
Polyene macrolides of the filipin class are characteristically **antifungal** (they bind ergosterol and permeabilise fungal membranes) — but no extract-level bioactivity data accompanies this public genome, so any relevance is stated at the class level and as capacity, not as a measured phenotype for this strain or this BGC. Extract-level assay would be required to attach an activity to the locus.

## §14 What cannot be claimed
Cannot claim: a single region-level product (over-merged); that filipin is *produced* (only encoded capacity for a filipin-like polyene in one protocluster); that ctg1_460 is a standalone oxidoreductase (it is PKS-associated, KR/SDR-dominant); any antifungal phenotype for this strain without extract data; any titre or condition-dependence.

## §15 Missing evidence
Missing: the per-protocluster gene partition needed to assign modules, tailoring, and transport to each system; LC-MS/bioassay confirmation of a polyene product; HMM module-grammar to order the KS-AT-DH-KR-ACP domains and count modules. These would convert "modular PKS capacity, ≥2 systems" into named per-protocluster products.

## §16 BLASTP/HMMER next steps
Two concrete steps. First, **HMM-adjudicate the module grammar**: BLASTp confirms class and source but cannot order the domains or count modules, so run `hmm-adjudicate` on ctg1_458/459/460 to resolve KS→AT→DH→KR→ACP order and module number — this is what turns "type I PKS subunits" into an assembly-line model. Second, run per-gene BLASTp across the *whole* region's core genes (not just the three sampled here) to establish the protocluster boundary empirically: genes whose top hits cluster to the filipin producer versus a different producer partition the over-merged region into its two systems. Only ctg1_460's REFINE needs follow-up beyond that; no OVERTURN is pending on the confirmed subunits.

## §17 LC-MS / fermentation implications
For detection, target a **polyene macrolide** — filipin-type polyenes have a diagnostic UV signature (a characteristic conjugated-polyene absorption in the ~320–360 nm region with fine structure) that is a fast first screen, followed by LC-MS with the filipin reference mass window. Because polyene expression is often condition-dependent, screen across media and growth phases rather than a single condition, and pair the UV screen with an antifungal bioassay (polyenes give a clear zone against a sterol-containing fungal indicator). Any candidate must be confirmed against a filipin standard or by exact mass before the comparator name is attached to the observed compound; the over-merge means a second, non-polyene product may co-occur and should not be conflated.

## §18 Figure/locus-map notes
A locus map should render the ≥2 protoclusters as **separate blocks with a visible split**, not one continuous cluster — this is the single most important visual for an over-merged region. Mark ctg1_458/459/460 as catalytic cores (●) within their protocluster, label ctg1_459 with both channels (type I PKS / *S. avermitilis* PKS 96 %), and annotate ctg1_460 as KR/SDR-dominant. Regulatory and transport genes should be greyed as unassigned context so a reader does not attribute them to a specific system.

## §19 Final Mode B judgement
BGC004 is a **source-derived, Interior, over-merged modular type I PKS region** enclosing ≥2 protoclusters. Its core PKS subunits are confirmed by independent homology (one to *S. avermitilis*' own PKS), and at least one protocluster is filipin-like by KCB similarity — supporting capacity for a filipin-type polyene macrolide. No single region-level product is claimed; the region is read per protocluster. Confidence in the *class* call is high; product identity is held as capacity pending the protocluster partition and chemical confirmation.

## §20 Next actions
Priority: partition the over-merged region into its protoclusters by whole-region per-gene BLASTp, then HMM-adjudicate module grammar on the confirmed subunits to build the assembly-line model. Secondary: UV/LC-MS + antifungal bioassay screen for a filipin-type polyene across several conditions, confirming any candidate against a standard before naming. Do not author a single region-level product; keep the two systems distinct until the partition is in.

## §24 Scaffold novelty score
Novelty is **LOW**: the region has a strong characterized MIBiG comparator (filipin, `BGC0000059.5`) at a high KCB score, and the per-gene BLASTp cores hit named type I PKS proteins — one the strain's own PKS — so the scaffold reads as a known-like polyene-macrolide PKS, not a novel class. Stated as a novelty read, not a product claim. Because the region is over-merged, only the filipin-anchored protocluster is scored here; the second protocluster is left unscored pending its partition (§5), and could carry independent novelty.

## §27 Self-resistance assessment
No source-derived self-resistance determinant is present (NULL_NO_SOURCE_DERIVED_RESISTANCE). For polyenes, self-protection is typically via membrane sterol composition rather than an encoded immunity gene, so absence of a resistance cassette is consistent with the class — reported as an observation, not a mechanism claim.

## §28 Evidence provenance ledger
- Region identity, boundary, over-merge flag, KCB anchor, TTA/resistance tiers: **store-backed** (Mamey inventory + KCB; `BGC0000059.5` filipin #1, score 101801; chemical_hybrid ≥2 protoclusters).
- Domain calls (Acyl_transf_1, KAsynt_C_assoc, KR, ACP): **store-backed** (antiSMASH Pfam).
- Per-gene top hits (type I PKS 89.9 % / 96.5 %; SDR oxidoreductase 96.0 %): **operator-supplied** independent BLASTp (nr), reconciled in §4.
- No reconstructed or fabricated observation is present; every §4 row traces to a real BLASTp result or an antiSMASH call.

## §30 Experimental decision tree
1. Partition the region: whole-region per-gene BLASTp → do top-hit producers split into two systems? If yes, treat as two products; if no, revisit the over-merge call.
2. Build the assembly line: HMM module grammar on the confirmed subunits → order and count modules per protocluster.
3. Detect: UV polyene screen + LC-MS + antifungal bioassay across conditions → confirm any candidate against a filipin standard before naming.
4. If a non-polyene product co-occurs (second protocluster), analyse it as its own card.
