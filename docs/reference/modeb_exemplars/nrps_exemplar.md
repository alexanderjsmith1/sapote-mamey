# Mode B — BGC002 (JBHTEE010000001.1 · region002) — *Streptosporangium amethystogenes* subsp. *fukuiense*

**Class exemplar: nrps.** Public type strain (GCA_042665875.1). Claim-safe throughout: biosynthetic *capacity* only; KCB/BLASTp are *similarity, not identity*; cited as BGC002 · JBHTEE010000001.1 · region002. This card is also the exemplar for the case where **the KCB comparator name and the region's domain content diverge** — handled explicitly in §8/§9.

## §1 Identity and node/region
BGC002 sits on contig JBHTEE010000001.1, antiSMASH region002, spanning ~62.4 kb. It is **Interior** (both flanks non-cluster). antiSMASH labels the region **NRPS; terpene**, and the KnownClusterBlast top anchor is MIBiG `BGC0000163.5` (tetronasin, score 1141). Note immediately that tetronasin is a *polyether polyketide ionophore*, not an NRPS — so the region's dominant domain content (NRPS modules) and its nearest KCB name point at different chemistries. That divergence is the interpretive crux of this card and is treated as a similarity signal, not a product identity. Cited hereafter as BGC002 · JBHTEE010000001.1 · region002.

## §2 Why this BGC was selected
Selected as the **NRPS exemplar** — it carries confirmed non-ribosomal peptide synthetase modules — and, deliberately, as the exemplar for **comparator/product divergence**: its top KCB anchor (tetronasin) is a different biosynthetic class than its resolved domains (NRPS). It teaches the discipline of authoring from the reconciled domain content rather than the KCB headline, and of holding a mismatched comparator as backbone similarity only.

## §3 Boundary and assembly status
Assembly tier **GOOD**, boundary **Interior** — no contig-edge truncation caveat; gene inventory taken as complete. The region carries mixed labels (NRPS; terpene), so as with any multi-label region the possibility of ≥2 co-located systems is kept open (§10); the antiSMASH call did not flag a hard over-merge here, but the mixed products warrant the same caution before any single-product statement.

## §4 Gene-by-gene interpretation

**Evidence grid.** Domain calls are antiSMASH Pfam; the BLASTp column is an independent operator-supplied online run against nr, reconciled as CONFIRM / REFINE / OVERTURN. No observation is stated that is not in a real result.

| Locus | aa | antiSMASH domains | BLASTp top hit (nr) | %id | Reconciliation |
|---|---|---|---|---|---|
| **ctg1_139 ●** | 1868 | AMP-binding; AMP-binding_C; C2_LCL; Condensation | non-ribosomal peptide synthetase / MFS transporter [*Streptosporangium* sp.] | 95.2 | **CONFIRM** — a canonical NRPS module (C-A-PCP grammar); the homology channel agrees it is an NRPS. |
| **ctg1_142 ●** | 497 | AMP-binding; AMP-binding_C; NRPS-A_a3 | class I adenylate-forming enzyme family protein | 100.0 | **REFINE** — antiSMASH reads it as an NRPS adenylation (A) domain; the BLASTp top hit resolves to the broader "class I adenylate-forming enzyme" family. The adenylation chemistry is confirmed, but the independent channel refines it from "NRPS-module A-domain" toward a possibly **standalone adenylating enzyme** (e.g. an acyl/aryl-CoA ligase-like protein), which is not necessarily part of a peptide assembly line. |

Prose walkthrough. The NRPS identity of this region rests on ctg1_139 (●), a full multi-domain module (Condensation–Adenylation–thiolation grammar) whose BLASTp top hit independently confirms it as a non-ribosomal peptide synthetase. ctg1_142 is the instructive gene: antiSMASH annotates a standalone A-domain (AMP-binding, NRPS-A), but the BLASTp top hit at 100 % identity is to the broader *class I adenylate-forming enzyme* family — a superfamily that includes NRPS A-domains **and** standalone acyl-/aryl-CoA ligases. This is a **REFINE, not an OVERTURN**: adenylation chemistry is real either way, but the homology channel cautions that this gene may be a freestanding adenylating enzyme rather than a committed NRPS module. That distinction matters for the product read — a standalone ligase does not extend a peptide chain — and is exactly the kind of nuance the independent channel adds over the Pfam label. The C/A/PCP module order and whether ctg1_142 is chain-integrated are HMM-channel questions (§16).

## §5 Core biosynthetic logic
Non-ribosomal peptide assembly: the confirmed module (ctg1_139) performs condensation of an activated amino-acid monomer (selected and adenylated by its A-domain, tethered by its PCP) onto a growing peptidyl chain — the canonical C-A-PCP logic. Because the region is mixed-label (NRPS; terpene) and ctg1_142's chain-integration is uncertain, no single linear peptide product is inferred; the core logic is stated at the level of "encodes NRPS peptide-bond-forming capacity," with monomer identity and chain length left to module-grammar analysis.

## §6 Tailoring and maturation logic
Tailoring is not enumerated as product-committing here: the mixed NRPS/terpene labelling means tailoring enzymes cannot be confidently assigned to a single assembly line without the per-system gene partition. Any oxidative/methyl tailoring present in the region is held at "present, system-assignment pending." The REFINE on ctg1_142 (possible standalone adenylating enzyme) is itself a caution against assuming every adenylation gene feeds the peptide product.

## §7 Transport, resistance, and regulation
Resistance routing is **T3_TRANSPORTER_ONLY_ROUTING** — i.e. the resistance signal is transporter-based, not a source-derived target-modification determinant; read as export/efflux context rather than a dedicated resistance mechanism. An MFS-transporter signature co-occurs with ctg1_139's hit, consistent with product export. Regulatory genes, if present, are treated as context and not attributed to a specific system given the mixed labels.

## §8 Comparator/KCB interpretation
KnownClusterBlast returns MIBiG `BGC0000163.5` (**tetronasin**) as the top anchor — but tetronasin is a *polyether polyketide ionophore*, a different biosynthetic class from the region's resolved NRPS content. This is a **comparator/product divergence**: the KCB score reflects shared backbone-fragment similarity (KCB compares cluster gene content, and polyether and NRPS clusters can share tailoring/transport genes), **not** that this region makes tetronasin. The comparator is therefore held as a similarity anchor only, and the product read is driven by the reconciled domain content (NRPS), not by the KCB headline. This is precisely the BGC046/selvamicin failure mode the linter guards against — the comparator name must not be promoted to product identity.

## §9 Alternative hypotheses
Given the divergence, the hypotheses are: (a) a genuine NRPS system whose nearest MIBiG neighbour happens to be a polyether cluster sharing accessory genes; (b) a hybrid NRPS-containing system with a polyketide/polyether component that pulls the tetronasin anchor; (c) two co-located systems (NRPS + terpene) that antiSMASH merged under one region label. Because "tetronasin" is a **comparator by similarity, not an identity claim**, and its class does not even match the resolved domains, the product is held as capacity for an NRPS-derived peptide, explicitly **not** as tetronasin. No hypothesis supports naming tetronasin as the product.

## §10 Fragmentation and co-capture risks
Fragmentation risk nil (Interior). The relevant risks are (i) mixed-label co-capture — NRPS and terpene genes under one region border may be separate systems, handled by not asserting a single product — and (ii) the ctg1_142 REFINE, i.e. mistaking a standalone adenylating enzyme for a chain-integrated NRPS module, handled by flagging it explicitly. Both are reasons the card stops at "NRPS capacity" rather than a named peptide.

## §11 Product-family interpretation
Product family: **non-ribosomal peptide** (capacity), monomer composition and length undetermined. Tetronasin (polyether) is **not** the product and is not named as such. The **terpene co-label** reflects a genuinely co-located second system — a terpene synthase/cyclase acting on a prenyl-diphosphate precursor (GPP/FPP/GGPP) — which, if real, is a separate product analysed on its own card, not folded into the NRPS read. No titre or condition-dependence is claimed.

## §12 Bee/microbe ecological interpretation
Public reference type strain, not a host-associated isolate — no bee/wasp/bryophyte ecological role is claimed. Generically, actinomycete NRPS products span siderophores, antibiotics, and signalling peptides; that breadth is a class-level statement (`assumed`), not a claim about a realised role here.

## §13 Antibacterial/antifungal relevance
No extract-level bioactivity data accompanies this public genome, so no antibacterial/antifungal phenotype is asserted. NRPS products *can* be antibacterial, but that is class-level potential, not a measured activity for this strain or this locus; extract assay would be needed to attach any activity.

## §14 What cannot be claimed
Cannot claim: that tetronasin is produced (the comparator class does not even match the domains); a single named peptide product (module grammar undetermined); that ctg1_142 is a committed NRPS module (it may be a standalone adenylating enzyme); any bioactivity or ecological role; any titre.

## §15 Missing evidence
Missing: HMM module grammar to order the C-A-PCP modules and decide ctg1_142's chain-integration; per-gene BLASTp across the full region to test the NRPS-vs-mixed-system question; LC-MS to detect any peptide product. These convert "NRPS capacity, comparator-divergent" into a defined system.

## §16 BLASTP/HMMER next steps
Two steps. Also resolve **A-domain substrate specificity**: extract the Stachelhaus specificity-conferring code from ctg1_139's adenylation domain (and ctg1_142's, if module-integrated) to predict the selected amino-acid monomer — the code, not the KCB anchor, is what constrains the peptide's composition. First, **HMM-adjudicate ctg1_142**: the BLASTp REFINE (adenylation superfamily) versus the antiSMASH NRPS-A call is exactly a case the HMM module-grammar channel should break — does ctg1_142 sit in a C-A-PCP module context (NRPS-integrated) or stand alone (a ligase)? Second, run per-gene BLASTp across the region's core genes to test whether the NRPS and terpene labels are one hybrid system or two co-located systems, and to see whether the shared genes driving the tetronasin KCB are accessory/transport rather than backbone — which would confirm the comparator divergence rather than a true polyether product.

## §17 LC-MS / fermentation implications
For detection, target a **non-ribosomal peptide**, not a polyether: the comparator divergence means a tetronasin-guided search would likely mislead. Use an untargeted LC-MS/MS approach with peptide-oriented fragmentation, and only after a candidate is seen attempt monomer inference from module grammar. Because expression may be silent under standard conditions, screen across media and elicitation conditions rather than a single culture, and pair with an antibacterial bioassay only as a non-specific activity indicator. Do not pre-commit the mass search to the tetronasin reference, since the KCB class does not match the resolved domains.

## §18 Figure/locus-map notes
A locus map should mark ctg1_139 as the confirmed NRPS core (●, labelled NRPS / MFS-transporter 95 %) and render ctg1_142 with a **REFINE flag** (antiSMASH: NRPS-A; BLASTp: adenylate-forming superfamily) so a reader sees the module-vs-standalone question. The KCB tetronasin anchor should be annotated as "similarity only — class divergent," not drawn as the product, to reinforce the comparator-divergence teaching point.

## §19 Final Mode B judgement
BGC002 is a **source-derived, Interior NRPS region** with a confirmed non-ribosomal peptide synthetase module (ctg1_139) and a REFINE on a second adenylation gene (ctg1_142) that may be a standalone ligase. Its top KCB anchor (tetronasin, a polyether) is class-divergent from the resolved domains and is held as backbone similarity only — the product is NRPS-derived *capacity*, explicitly not tetronasin. Confidence in the NRPS *class* call is high; product identity is undetermined pending module grammar and chemical detection.

## §20 Next actions
Priority: HMM-adjudicate ctg1_142 (module-integrated vs standalone) and run whole-region per-gene BLASTp to resolve the NRPS-vs-mixed-system question and confirm the tetronasin comparator is accessory-driven similarity. Secondary: untargeted peptide-oriented LC-MS/MS across conditions; do not search on the tetronasin mass. Keep the comparator labelled similarity-only throughout.

## §24 Scaffold novelty score
Novelty is **MEDIUM / uncertain**, and this is the honest nuance of a comparator-divergent region: the store carries a KCB anchor (tetronasin), so the region is not "no-MIBiG", but that anchor is a **polyether polyketide** — a different class from the resolved NRPS domains (§8). The NRPS product therefore has **no class-matched MIBiG comparator**, so its scaffold novelty cannot be scored LOW on the strength of the tetronasin hit. Scored MED to reflect that the nearest MIBiG neighbour does not share the product's biosynthetic class; a class-matched search is needed before calling the peptide known or novel.

## §27 Self-resistance assessment
Resistance is transporter-routed (T3_TRANSPORTER_ONLY_ROUTING), not a source-derived target-modification determinant — read as efflux/export context, not a dedicated self-resistance mechanism. No target-based immunity gene is asserted for this locus.

## §28 Evidence provenance ledger
- Region identity, boundary, mixed products, KCB anchor, TTA/resistance routing: **store-backed** (Mamey inventory + KCB; `BGC0000163.5` tetronasin #1, score 1141; products NRPS; terpene).
- Domain calls (AMP-binding, Condensation, NRPS-A): **store-backed** (antiSMASH Pfam).
- Per-gene top hits (NRPS/MFS 95.2 %; class I adenylate-forming enzyme 100 %): **operator-supplied** independent BLASTp (nr), reconciled in §4.
- No reconstructed or fabricated observation is present; the tetronasin comparator is explicitly labelled similarity-only, never a product.

## §30 Experimental decision tree
1. Adjudicate ctg1_142 (HMM module grammar): NRPS-integrated or standalone ligase? → sets whether it feeds the peptide.
2. Partition NRPS vs terpene labels (whole-region BLASTp): one hybrid or two systems? → sets product count.
3. Detect: untargeted peptide-oriented LC-MS/MS across conditions → confirm any peptide independent of the (class-divergent) tetronasin anchor.
4. Only if a polyether signature emerges independently, revisit the tetronasin comparator — otherwise keep it similarity-only.
