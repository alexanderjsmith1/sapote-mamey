# Mode B — BGC004 (CP023690.1 · region004) — *Streptomyces spectabilis* ATCC 27465

**Class exemplar: nrps_pks_hybrid + lassopeptide.** Public type strain (GCA_008704795.1). Claim-safe throughout: biosynthetic *capacity* only; KCB/BLASTp are *similarity, not identity*; cited as BGC004 · CP023690.1 · region004. **This is a multi-class region (NRPS; PKS; transAT-PKS; RiPP; lassopeptide) — analysed per system below; no single region-level product claim is made.** It serves as the exemplar for both the hybrid-assembly-line slot and the lasso-peptide RiPP slot.

## §1 Identity and node/region
BGC004 sits on contig CP023690.1 (a finished *S. spectabilis* ATCC 27465 chromosome), antiSMASH region004, spanning ~64.3 kb. It is **Interior** (both flanks non-cluster). antiSMASH labels it with a stack of classes — **NRPS; PKS; RiPP; lassopeptide; transAT-PKS** — and the KnownClusterBlast top anchor is MIBiG `BGC0001645.3` (lagmysin, score 1476), a characterized **lasso peptide** cluster. The multi-class labelling means "BGC004" is an antiSMASH border enclosing at least two biosynthetic logics: a *trans*-AT NRPS-PKS hybrid assembly line and a lasso-peptide RiPP system. Cited hereafter as BGC004 · CP023690.1 · region004.

## §2 Why this BGC was selected
Selected to fill **two** exemplar slots at once — nrps_pks_hybrid and lassopeptide — because it genuinely co-encodes both a *trans*-AT NRPS-PKS hybrid and a lasso-peptide RiPP, anchored to the characterized lagmysin cluster by KCB. It is the reference case for a **multi-system region**: it teaches per-system decomposition and the refusal of a single fused product, while giving confirmed NRPS and PKS core genes plus a defined RiPP comparator.

## §3 Boundary and assembly status
Assembly tier **GOOD** (finished chromosome), boundary **Interior** — no contig-edge truncation caveat; gene inventory taken as complete. The dominant completeness caveat is **multi-system co-location**: five class labels under one region border is antiSMASH's signal that more than one biosynthetic system is present. Region-level aggregate scores and the single KCB anchor are composites and must be split before any product statement (§5, §11). This is handled per system throughout.

## §4 Gene-by-gene interpretation

**Evidence grid.** Domain calls are antiSMASH Pfam; the BLASTp column is an independent operator-supplied online run against nr, reconciled as CONFIRM / REFINE / OVERTURN. No observation is stated that is not in a real result.

| Locus | aa | antiSMASH domains | BLASTp top hit (nr) | %id | Reconciliation |
|---|---|---|---|---|---|
| **ctg1_205 ●** | 2399 | AMP-binding; AMP-binding_C; C2_DCL; Condensation | non-ribosomal peptide synthetase [*Streptomyces* sp.] | 100.0 | **CONFIRM** — a full NRPS module (C-A-PCP grammar); domain call and homology channel agree exactly. |
| ctg1_194 | 510 | AMP-binding; AMP-binding_C; NRPS-A_a3 | class I adenylate-forming enzyme family protein | 100.0 | **REFINE** — antiSMASH reads an NRPS A-domain; BLASTp resolves the broader adenylate-forming superfamily, so this may be a **standalone adenylating enzyme** rather than a chain-integrated module (same pattern as the NRPS exemplar's ctg1_142). |
| **ctg1_207 ●** | 848 | KAsynt_C_assoc; Ketoacyl-synt_C; PCP; PKSI-KS | beta-ketoacyl synthase N-terminal-like domain-containing protein [*Streptomyces* sp.] | 93.3 | **CONFIRM** — a PKS ketosynthase carrying a PCP, i.e. the **hybrid PKS module** that interfaces with the NRPS machinery; class and homology agree. |

Prose walkthrough. The hybrid assembly-line identity rests on two confirmed cores: **ctg1_205** (●), a full NRPS module (Condensation-Adenylation-thiolation) confirmed at 100 % as a non-ribosomal peptide synthetase, and **ctg1_207** (●), a PKS ketosynthase that also carries a PCP (peptidyl-carrier) domain — the hallmark of an NRPS-PKS **hybrid** module, confirmed by BLASTp as a beta-ketoacyl synthase. Together they evidence a *trans*-AT NRPS-PKS hybrid logic (the transAT-PKS label means the acyltransferase acts in *trans* rather than being embedded in each module). ctg1_194 is the REFINE, identical in pattern to the NRPS exemplar: antiSMASH annotates an NRPS A-domain, but the BLASTp top hit is the broader class I adenylate-forming superfamily, so it may be a standalone adenylating enzyme rather than a committed module. Separately, the region's **lassopeptide/RiPP** system — the basis of the lagmysin KCB anchor — is not represented in this 3-gene sample: a lasso-peptide system is defined by a short precursor peptide plus a lasso cyclase (an asparagine-synthetase-like B protein and a transglutaminase-like B1/B2), which are small genes not captured here and are the natural next targets (§16). The honest reading is therefore **at least two co-located systems** — a hybrid NRPS-PKS assembly line (ctg1_205/207) and a lasso-peptide RiPP (lagmysin-anchored) — not one fused product.

## §5 Core biosynthetic logic
Per system. **System A (hybrid NRPS-PKS, *trans*-AT):** the NRPS module (ctg1_205) selects/condenses an amino-acid monomer while the hybrid PKS module (ctg1_207, KS+PCP) performs a polyketide extension, with a *trans*-acting acyltransferase loading extender units — an interleaved peptide/polyketide assembly line. **System B (lasso-peptide RiPP):** a ribosomally-synthesised precursor peptide is matured by a lasso cyclase into the threaded lariat-knot topology diagnostic of lasso peptides. These are **separate logics** and are not chained into one product; the multi-class label is decomposed rather than collapsed. Monomer identity, module order, and the lasso core sequence are left to per-system analysis.

## §6 Tailoring and maturation logic
System A tailoring (oxidative/reductive processing on the hybrid chain) and System B maturation (lasso threading + any post-cyclisation tailoring) are distinct and are held at "present per system, assignment pending" because the multi-system co-location prevents confident attribution of a given tailoring gene to a specific system without the full per-gene partition. The ctg1_194 REFINE is a reminder that not every adenylation gene in the border feeds the hybrid line.

## §7 Transport, resistance, and regulation
Resistance routing is **T3_TRANSPORTER_ONLY_ROUTING** — transporter-based export context, not a source-derived target-modification determinant. Regulatory and transport genes are not assigned to System A vs System B here given the co-location. Lasso peptides frequently carry a dedicated ABC transporter/isopeptidase for maturation and export; where present these would belong to System B, but are not attributed without the partition.

## §8 Comparator/KCB interpretation
KnownClusterBlast returns MIBiG `BGC0001645.3` (**lagmysin**, a lasso peptide) at score 1476. This anchor is a **similarity comparator, not an identity claim**, and it belongs to **System B** (the RiPP), not the hybrid assembly line — a clear illustration that in a multi-system region a single KCB hit tags only one of the systems. It is held as **similarity, not identity**: the region encodes lasso-peptide capacity most similar to lagmysin, not a demonstration that lagmysin is produced. The hybrid NRPS-PKS system (System A) has no MIBiG anchor in this sample and is read from domain content alone. The per-gene BLASTp genus (*Streptomyces*) is consistent with the lagmysin producer lineage.

## §9 Alternative hypotheses
The multi-class content admits: (a) two genuinely independent co-located systems (a hybrid NRPS-PKS and a lasso RiPP) that antiSMASH merged under one region; (b) a single hybrid megasystem incorporating a RiPP element (rarer). The distinct enzymatic logics (assembly-line thiotemplate vs ribosomal-precursor lasso maturation) favour (a). Because "lagmysin" is a **KCB comparator by similarity, not an identity claim** — and it tags only System B — the products are held as capacity: a hybrid NRPS-PKS product (System A) and a lagmysin-*like* lasso peptide (System B), neither named as a finished compound. No hypothesis supports a single fused product.

## §10 Fragmentation and co-capture risks
Fragmentation risk nil (Interior, finished chromosome). The dominant risk is **treating the multi-system region as one product**, which would fabricate a fused pathway; handled by per-system decomposition. Secondary risks: the ctg1_194 REFINE (standalone adenylating enzyme mistaken for a module) and mis-assignment of shared transport/regulatory genes to the wrong system — both handled by explicit flagging and by withholding cross-system attribution.

## §11 Product-family interpretation
Two product families, held as capacity: **(A)** a hybrid non-ribosomal-peptide/polyketide from the NRPS-PKS *trans*-AT system, composition undetermined; and **(B)** a **lasso peptide** (lagmysin-like), the ribosomal lariat-knot RiPP anchored by KCB. No single region-level compound is named; no titre or condition-dependence is claimed.

## §12 Bee/microbe ecological interpretation
Public reference type strain, not a host-associated isolate — no bee/wasp/bryophyte ecological role is claimed. Generically, lasso peptides can be protease-resistant antibacterials/receptor antagonists and hybrid NRPS-PKS products span many activities; these are class-level statements (`assumed`), not claims about a realised role here.

## §13 Antibacterial/antifungal relevance
Lasso peptides are frequently **antibacterial** (and notably protease/heat-stable due to their threaded topology), and hybrid NRPS-PKS products can be antibacterial or antifungal — but no extract-level bioactivity data accompanies this public genome, so any relevance is stated at the class level and as capacity per system, not as a measured phenotype for this strain or region. Extract assay would be required to attach an activity to either system.

## §14 What cannot be claimed
Cannot claim: a single region-level product (multi-system); that lagmysin is *produced* (only encoded lasso-peptide capacity most similar to it); that the lagmysin KCB says anything about the hybrid System A; that ctg1_194 is a committed NRPS module (possible standalone ligase); any bioactivity phenotype without extract data; any titre or condition-dependence.

## §15 Missing evidence
Missing: identification of the **lasso-peptide precursor + cyclase** genes (the small RiPP core that defines System B) to move beyond the KCB anchor; module grammar for the hybrid line (System A) to order NRPS/PKS modules and decide ctg1_194's integration; LC-MS for both a lasso peptide and a hybrid product. These convert "two-system capacity" into two defined products.

## §16 BLASTP/HMMER next steps
Two per-system steps. First, for **System B (lasso)**, target the small genes the 3-gene core sample missed: BLASTp/HMM the candidate **precursor peptide** (a short ORF) and the **lasso cyclase** (an asparagine-synthetase-like B protein plus a transglutaminase-like maturase) — HMM is essential here because short RiPP precursors often have no BLASTp hit, and the HMM channel is what rescues leader/core peptides. Second, for **System A (hybrid)**, HMM-adjudicate the module grammar across ctg1_205/207 (and resolve ctg1_194's module-vs-standalone status), extract the Stachelhaus specificity code from ctg1_205's adenylation domain to predict the peptide monomer selected by the hybrid line, and run whole-region per-gene BLASTp to draw the boundary between System A and System B empirically. No OVERTURN is pending on the two confirmed cores.

## §17 LC-MS / fermentation implications
Two detection strategies, because two products may co-occur. For the **lasso peptide**: target a compact, protease/heat-stable peptide mass; a diagnostic test is resistance to carboxypeptidase or thermal denaturation (the threaded lariat topology resists both), so an extract that retains a peptide mass after protease/heat treatment is strong evidence of a lasso. For the **hybrid NRPS-PKS product**: untargeted LC-MS/MS with mixed peptide/polyketide fragmentation. Screen across media and elicitation conditions for both, since either system may be silent under standard growth. Confirm any lasso candidate against a lagmysin reference or by exact mass before attaching the comparator name; keep the two products distinct in the analysis.

## §18 Figure/locus-map notes
A locus map should render **two separated system blocks** — System A (NRPS-PKS hybrid) and System B (lasso RiPP) — not one continuous cluster, this being the key visual for a multi-system region. Mark ctg1_205 (NRPS 100 %) and ctg1_207 (hybrid PKS-KS+PCP 93 %) as System A cores (●), flag ctg1_194 as a REFINE, and reserve a labelled placeholder in System B for the lasso precursor + cyclase (to be added once identified). The lagmysin KCB anchor should be drawn on System B only, annotated "similarity, tags RiPP system only."

## §19 Final Mode B judgement
BGC004 is a **source-derived, Interior, multi-system region** co-encoding a *trans*-AT NRPS-PKS hybrid assembly line (confirmed cores ctg1_205, ctg1_207) and a lasso-peptide RiPP (KCB-anchored to lagmysin). It supports capacity for two distinct products — a hybrid non-ribosomal-peptide/polyketide and a lagmysin-like lasso peptide — neither named as a finished compound and not fused into one. Confidence in the hybrid *class* call is high; the lasso system is evidenced by KCB and label pending its precursor/cyclase identification; product identities are held as capacity.

## §20 Next actions
Priority: identify the lasso precursor + cyclase (System B) via HMM/short-ORF search, and HMM-adjudicate the hybrid module grammar plus ctg1_194 (System A). Then whole-region per-gene BLASTp to draw the System-A/System-B boundary. Secondary: dual LC-MS screen (protease/heat-stable lasso + untargeted hybrid) across conditions, confirming any lasso candidate against a lagmysin reference. Do not author a single region-level product.

## §21 Precursor mass ladder
The lasso-peptide precursor for System B is **not among the genes sampled here** (the 3-gene core sample covered the hybrid NRPS-PKS System A), so no precursor sequence is stated — inventing one would be the fabrication the gate exists to prevent. The method, once the short precursor ORF is identified (§16): take the ripped core sequence after leader cleavage, compute the linear mass, then apply the lasso macrolactam mass change (a Gly/Asp/Glu side-chain-to-N-terminus isopeptide bond formed by the cyclase, a condensation with loss of water, ≈ −18 Da) and predict the threaded-lariat monoisotopic mass. The diagnostic observable is a compact peptide mass that survives protease/heat challenge (the threaded topology resists both). LC-MS targeting therefore compares the predicted macrolactam mass against protease/heat-treated extract; the lagmysin reference mass is the comparator anchor, held as similarity only, not asserted as the product mass.

## §22 RiPP database search
Once the precursor ORF is identified, search it against RiPP-specific resources (the lasso-peptide records in MIBiG, and lasso/RiPP-aware tools such as antiSMASH's RiPP module and RiPPMiner-style predictors) to place the core in the known lasso family and to test novelty. The KCB anchor already points at lagmysin (`BGC0001645.3`), so the expectation is a lagmysin-adjacent lasso; a database search on the actual precursor either confirms that placement or flags a novel core — either outcome is authored from the search result, not from the KCB headline. Until the precursor is in hand, the RiPP search is scoped as a pending step, and the lasso identity rests on the class label plus the (similarity-only) lagmysin comparator.

## §24 Scaffold novelty score
Novelty is scored **per system**, as elsewhere in this card. **System B (lasso RiPP):** LOW–MEDIUM — a class-consistent MIBiG comparator (lagmysin, `BGC0001645.3`) anchors the lasso, so its scaffold is known-like pending precursor confirmation (§21/§22). **System A (hybrid NRPS-PKS):** MEDIUM — it carries no MIBiG anchor in this analysis (the lagmysin KCB tags only System B, §8), so the hybrid product's scaffold has no class-matched comparator here and cannot be scored LOW. No single region-level novelty score is given; the multi-system border makes an aggregate score meaningless.

## §27 Self-resistance assessment
Resistance is transporter-routed (T3_TRANSPORTER_ONLY_ROUTING), not a source-derived target-modification determinant. Lasso-peptide systems commonly carry a dedicated isopeptidase/ABC exporter for maturation and self-handling; if present these belong to System B, but none is asserted here without the per-system partition. No target-based immunity gene is claimed.

## §28 Evidence provenance ledger
- Region identity, boundary, multi-class labels, KCB anchor, TTA/resistance routing: **store-backed** (Mamey inventory + KCB; `BGC0001645.3` lagmysin #1, score 1476; labels NRPS; PKS; RiPP; lassopeptide; transAT-PKS).
- Domain calls (AMP-binding, Condensation, PKSI-KS, PCP, NRPS-A): **store-backed** (antiSMASH Pfam).
- Per-gene top hits (NRPS 100 %; class I adenylate-forming enzyme 100 %; beta-ketoacyl synthase 93.3 %): **operator-supplied** independent BLASTp (nr), reconciled in §4.
- The lagmysin comparator is explicitly scoped to System B (the RiPP) and held as similarity, never a product. No reconstructed or fabricated observation is present.

## §30 Experimental decision tree
1. Resolve System B: HMM/short-ORF search for the lasso precursor + cyclase → confirms the RiPP beyond the KCB anchor.
2. Resolve System A: HMM module grammar on ctg1_205/207 + ctg1_194 status → hybrid assembly-line model.
3. Draw the boundary: whole-region per-gene BLASTp → partition System A from System B.
4. Detect both: protease/heat-stable peptide screen (lasso) + untargeted LC-MS/MS (hybrid) across conditions → confirm the lasso against a lagmysin reference before naming; keep products distinct.
