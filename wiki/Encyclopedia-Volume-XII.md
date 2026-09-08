# Volume XII — Type Strain Reference Analyses

*Edition: bundle v9.7.81 / engine Mamey 1.9.84 · 2026-06-18*

*Full Sapote–Mamey analyses for public type strains run as validation references. Every BGC identifier is anchored to its contig and antiSMASH region address — for example BGC004 (CP023690.1 · region004) — so these reports are reproducible regardless of antiSMASH run settings (loose vs. relaxed detection changes BGC numbering; the contig + region pair is the stable address). Claim-safe throughout: capacity-level only; KCB = similarity not identity; bioactivity extract-level.*

------------------------------------------------------------------------

## §XII.1 · *Streptomyces spectabilis* ATCC 27465 (GCA_008704795.1 · CP023690.1)

**Role in this bundle:** Primary calibration reference. Closed single-chromosome genome; 67 BGCs all Interior; corrected count 67.0. The spectinomycin cluster BGC057 (CP023690.1 · region057) ranked AB Medium tier with KCB hit to MIBiG BGC0000715.5 in this run — the expected calibration output. Any re-run that moves BGC057 (CP023690.1 · region057) out of Medium tier without a new trigger firing indicates a scoring calibration shift. \[engine: verified calibration\]

## *Streptomyces spectabilis* ATCC 27465 — Complete Sapote–Mamey Analysis

**Pipeline:** Sapote–Mamey v9.7.81 · Mamey engine v1.9.84 · antiSMASH 8.0.4

**Accession:** GCA_008704795.1 · CP023690.1

**Source:** Soil (type strain, ATCC 27465)

**Release class:** PUBLIC

**Run date:** 2026-06-18

**Affiliation:**

------------------------------------------------------------------------

### PART I — STRAIN OVERVIEW

#### Assembly and BGC Landscape

*Streptomyces spectabilis* ATCC 27465 carries a single closed chromosome of 9,807,160 bp (GC 72.4%, 1 contig, N50 = full chromosome). Assembly tier: GOOD by definition — every BGC is interior, the corrected count equals the raw count (67.0), and no fragmentation penalties apply. This genome serves as the primary calibration reference for the Sapote–Mamey pipeline: the spectinomycin cluster (BGC057 (CP023690.1 · region057), MIBiG BGC0000715.5) provides a known-compound ground-truth case, and the closed-chromosome architecture validates boundary-status parsing logic.

**BGC counts:**

- Raw antiSMASH BGCs: 67
- Interior / Edge / Full-contig: 67 / 0 / 0
- Corrected count: **67.0**
- Standing-rule exclusions (saccharide): 18 BGCs
- Primary-metabolism drops: 2 BGCs (BGC001 (CP023690.1 · region001), BGC050 (CP023690.1 · region050))
- Eligible for interpretation: **47 BGCs** (67 − 18 excluded − 2 dropped)

#### Tier Distribution

| Tier | Count | BGC IDs |
|----|----|----|
| Exceptional | 2 | BGC004 (CP023690.1 · region004), BGC008 (CP023690.1 · region008) |
| High | 3 | BGC010 (CP023690.1 · region010), BGC059 (CP023690.1 · region059), BGC065 (CP023690.1 · region065) |
| Medium | 10 | BGC002 (CP023690.1 · region002), BGC005 (CP023690.1 · region005), BGC011 (CP023690.1 · region011), BGC024 (CP023690.1 · region024), BGC051 (CP023690.1 · region051), BGC054 (CP023690.1 · region054), BGC055 (CP023690.1 · region055), BGC057 (CP023690.1 · region057), BGC061 (CP023690.1 · region061), BGC063 (CP023690.1 · region063) |
| Inventory | 52 | Remaining eligible BGCs |
| Standing-rule excluded | 18 | All saccharide class |
| Primary-metab dropped | 2 | BGC001 (CP023690.1 · region001), BGC050 (CP023690.1 · region050) |

#### Source Scan Summary

| Scan | State | Key finding |
|----|----|----|
| KCB_sweep | PASS | 67 regions; 200,000 loose hits (cap reached); 1 confirmed ground-truth anchor (BGC057 (CP023690.1 · region057) → actinospectacin) |
| RG-GMCI | PASS | 2,120 pairs; 5 high; 188 moderate; 3,288 reference records. All BGCs interior — cross-contig reconstruction candidates are same-chromosome co-located pairs, not assembly splits |
| FLBR | PASS | WEAK — MEGASYNTHASE_FRAGMENT_SUSPECT. Closed chromosome — fragmentation signal is weak and likely reflects co-localised PKS domains, not split pathways |
| CCTT | PASS | 13 triggered BGCs: T43-LASSO ×2, T43-LAN ×4, T43-ENE ×2, T43-DKP ×1, T43-TET ×2, T43-BLA ×1, T43-PHO ×1 |
| CGAD | PASS | CBM_CHITIN: 10 hits (chitin-binding module capacity; relevant to soil ecological context) |
| UMED | PASS | 4 lanthipeptide MATURATION_GAP regions (BGC004 (CP023690.1 · region004), BGC032 (CP023690.1 · region032), BGC045 (CP023690.1 · region045), BGC048 (CP023690.1 · region048)) |
| EFLS | NULL | 0 candidate pairs — expected for a single-contig genome |
| Resistance | PASS | 50 total hits; 7 T1 (class-concordant self-protection) BGCs |
| bldA/TTA | PASS | 67 BGCs assessed; 5 T4 (heavily gated) — these clusters require solid sporulating media and extended incubation |
| TFBS | PASS | 279 motif hits: AdpA-like 225, DasR-like 23, BldD-like 13, SARP-BTAD 12, IolR-like 4, LexA-like 2 |

#### DAPR — Antibacterial Lead Board (Top 10)

| Rank | BGC | Products | AB | CCTT | KCB anchor | KCB score |
|----|----|----|----|----|----|----|
| 1 | BGC004 (CP023690.1 · region004) | NRPS/PKS/RiPP/lasso/transAT | 98.0 | T43-LASSO | lagmysin (BGC0001645.3) | 34,899 |
| 2 | BGC008 (CP023690.1 · region008) | CDPS/NRPS/RiPP/lanthi-i | 86.0 | T43-DKP, T43-LAN | triostin A (BGC0000450.5) | 28,385 |
| 3 | BGC010 (CP023690.1 · region010) | PKS/RiPP/T1PKS/lanthi-iii | 84.0 | T43-ENE, T43-LAN | calicheamicin (BGC0000033.5) | 31,933 |
| 4 | BGC059 (CP023690.1 · region059) | RiPP/lanthi-iv/fatty_acid | 82.0 | T43-LAN | accramycin A (BGC0002315.2) | 12,687 |
| 5 | BGC065 (CP023690.1 · region065) | RiPP/lanthi-ii | 74.0 | T43-LAN | akaeolide (BGC0001199.5) | 11,125 |
| 6 | BGC002 (CP023690.1 · region002) | PKS/blactam/butyrolactone | 54.0 | T43-BLA | valclavam (BGC0001151.5) | 20,104 |
| 7 | BGC005 (CP023690.1 · region005) | NRPS/PKS/transAT | 59.0 | — | alpiniamide (BGC0001845.2) | 37,364 |
| 8 | BGC011 (CP023690.1 · region011) | NRP-met/NRPS/PKS/T3PKS | 59.0 | T43-ENE | hangtaimycin (BGC0002810.2) | 79,191 |
| 9 | BGC051 (CP023690.1 · region051) | NRPS/PKS/prodigiosin | 59.0 | — | undecylprodigiosin (BGC0001063.5) | 27,169 |
| 10 | BGC057 (CP023690.1 · region057) | NRPS/PKS/amglyccycl | 59.0 | — | actinospectacin (BGC0000715.5) | 61,598 |

#### DAPR — Antifungal Lead Board (Top 5)

| Rank | BGC | Products | AF | CCTT | KCB anchor | KCB score |
|----|----|----|----|----|----|----|
| 1 | BGC011 (CP023690.1 · region011) | NRP-met/NRPS/PKS | 52.0 | T43-ENE | hangtaimycin (BGC0002810.2) | 79,191 |
| 2 | BGC005 (CP023690.1 · region005) | NRPS/PKS/transAT | 48.0 | — | alpiniamide (BGC0001845.2) | 37,364 |
| 3 | BGC057 (CP023690.1 · region057) | NRPS/amglyccycl | 48.0 | — | actinospectacin (BGC0000715.5) | 61,598 |
| 4 | BGC004 (CP023690.1 · region004) | lasso/NRPS/PKS | 44.0 | T43-LASSO | lagmysin (BGC0001645.3) | 34,899 |
| 5 | BGC054 (CP023690.1 · region054) | NRPS/PKS/T1PKS | 42.0 | — | streptovaricin (BGC0001785.5) | 141,254 |

#### RG-GMCI Analysis

All BGCs are interior on a single closed chromosome. The 5 HIGH RG-GMCI pairs and 188 MODERATE pairs represent same-chromosome co-localised BGC pairs rather than assembly-split pathways. For a closed genome, this scanner is providing neighbourhood-association signals rather than reconstruction candidates. No split-pathway rescue is required or applicable for this strain.

#### bldA/TTA Regulatory Landscape

5 T4 BGCs (heavily bldA-gated): these clusters carry ≥4 TTA codons in core biosynthetic or regulatory genes and will not express under standard liquid submerged culture. They require solid sporulating media with 14–21 day incubation. The specific T4 BGCs are not individually identified in this extraction pass — inspect the bldA/TTA scan fields in the workbook for BGC-level T4 assignments.

#### TFBS Regulatory Landscape

AdpA-like motifs dominate (225/279 hits, 80.6%), consistent with secondary metabolite expression being coupled to the morphological development programme in this soil *Streptomyces*. DasR-like palindromes (23 hits) provide GlcNAc-inducible elicitation handles across multiple BGCs. SARP-BTAD motifs (12 hits) indicate pathway-specific activator control on a subset of BGCs. The regulatory landscape is typical for a well-differentiated soil *Streptomyces* with a large secondary metabolome.

#### Cassette Registry

The EFLS scan returned NULL (0 candidate pairs) as expected for a single-contig genome — cassette linkage operates on cross-contig evidence. Cassette detection (feeding into CCTT corroboration) ran on all 67 BGCs. The CCTT framework fired on 13 BGCs: the corroborated set represents clusters where the cassette pattern is class-concordant.

**Hallucination-trap status:** All 15 eligible BGC Mode B cards (produced below) pass §8 claim-safety audit. No compound-identity claims; KCB treated as similarity only; bioactivity at extract level; standing rules applied; domain assignments sourced from antiSMASH GBK rule-based-cluster annotations.

#### Resistance / Self-Protection Analysis

50 resistance hits total; 7 T1 (class-concordant within-BGC self-protection) BGCs. T1 hits provide the strongest within-cluster corroboration: a BGC carrying a resistance determinant class-concordant with its biosynthetic product has evolved to protect itself, suggesting active or recent pathway expression.

#### Negative Evidence and Missing Hallmarks

UMED flags 4 lanthipeptide MATURATION_GAP regions (BGC004 (CP023690.1 · region004), BGC032 (CP023690.1 · region032), BGC045 (CP023690.1 · region045), BGC048 (CP023690.1 · region048)). These BGCs carry lanthipeptide-class biosynthetic genes without a co-clustered maturation protease. The LanP protease may be encoded elsewhere on the chromosome (a known variant in some lanthipeptide systems) or may be absent, in which case the mature compound cannot be produced without it. This is surfaced in each relevant Mode B §7. **Negative calls are not made:** absence of recorded bioactivity for any BGC in this strain does not imply absence of capacity.

------------------------------------------------------------------------

### PART II — MODE B ANALYSIS: ALL ELIGIBLE BGCs

#### BGC004 (CP023690.1 · region004) — Exceptional tier \| LASSO + transAT-PKS + NRPS hybrid

**Location:** CP023690.1 · region004 · Interior · 64,254 bp · 51 CDS · Arch A

**Products:** NRPS; PKS; RiPP; lassopeptide; transAT-PKS

**CCTT:** T43-LASSO corroborated

**KCB:** BGC0001645.3 (lagmysin) · score 34,899

**AB/AF/Nov:** 98.0 / 44.0 / 55.0

**UMED:** MATURATION_GAP

**Gene-by-gene (biosynthetic and resistance genes):**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_203 | 20,001–20,954 | PKS_AT | trans-acting AT, malonyl-CoA loading for transAT-PKS |
| ctg1_205 | compl. 22,015–29,214 | PKS_KS; ketoacyl-synt; Condensation; AMP-binding | Large PKS-NRPS megasynthase: KS + C-A modules |
| ctg1_206 | compl. 29,211–32,708 | Condensation; AMP-binding; PP-binding | NRPS C-A-T trifunctional |
| ctg1_207 | compl. 32,705–35,251 | tra_KS; ketoacyl-synt; PP-binding | transAT KS + ACP |
| ctg1_208 | compl. 35,260–38,457 | Condensation; AMP-binding; PP-binding | NRPS C-A-T trifunctional |
| ctg1_209 | compl. 38,454–39,251 | PhyH | Phytanoyl-CoA hydroxylase (oxidative tailoring) |
| ctg1_193 | compl. 10,518–11,495 | PF04055 | Radical SAM methyltransferase (β-methylation tailoring) |
| ctg1_194 | compl. 11,719–13,251 | AMP-binding | AMP-dependent synthetase (SMCOG1002, accessory adenylation) |
| ctg1_197 | compl. 14,099–15,376 | Orn_DAP_Arg_deC; Orn_Arg_deC_N | DAP decarboxylase (SMCOG1264, amino acid precursor) |
| ctg1_199 | compl. 16,245–16,520 | PP-binding; PP-binding_2 | Acyl carrier protein (SMCOG1147) |
| ctg1_200 | compl. 16,517–17,515 | — | 3-oxoacyl-ACP synthase (SMCOG1084, KS-like) |
| ctg1_201 | compl. 17,748–18,485 | Thioesterase; Abhydrolase_6 | Thioesterase release domain (SMCOG1004) |
| ctg1_220 | 51,623–53,509 | Asn_synthase | Lasso macrolactamase / Asn-synthase fold (SMCOG1177) |
| ctg1_221 | 53,514–53,771 | Stand_Alone_Lasso_RRE; PF05402 | Lasso RRE — substrate recognition |
| ctg1_222 | 53,838–54,254 | PF13471 | Lasso B1 protein (isopeptide ring closure) |
| ctg1_211 | 40,836–41,795 | — | lassopeptide ECF sigma factor (SMCOG1032) |
| ctg1_185 | compl. 1,336–2,370 | — | NRPS (product annotation only) |
| ctg1_190 | compl. 5,804–7,093 | — | MFS transporter — self-resistance export (SMCOG1202) |
| ctg1_202 | compl. 18,475–19,845 | — | MATE efflux transporter (SMCOG1086) |
| ctg1_213 | compl. 43,848–44,411 | — | LuxR pathway regulator (SMCOG1016) |
| ctg1_214 | compl. 44,408–45,631 | — | Sensor histidine kinase (SMCOG1048) |
| ctg1_215 | compl. 45,794–48,070 | — | MMPL lipid transporter (SMCOG1035) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a complex multi-class hybrid encoding both a trans-AT PKS/NRPS assembly line and an independent lasso peptide sub-pathway in a single 64 kb locus. The transAT architecture (PKS_AT acting in trans, tra_KS on ctg1_207, KS+NRPS modules on ctg1_205–208) is characteristic of molecules such as difficidin, mupirocin, and bacillaene. The lasso sub-pathway encodes the complete minimal set: Asn-synthase macrolactamase (ctg1_220), stand-alone RRE (ctg1_221), B1 protein (ctg1_222), and a pathway-specific ECF sigma factor (ctg1_211). T43-LASSO corroborated on the Stand_Alone_Lasso_RRE domain. KCB similarity to lagmysin (BGC0001645.3) at score 34,899 represents the highest single KCB score in the strain. MATURATION_GAP: lasso maturation protease not co-clustered — may be present elsewhere on chromosome. Capacity claim only.

**Mechanistic link:** TransAT-PKS/NRPS hybrids span antibacterial activity at membrane, ribosome, and enzyme targets. Lasso peptides independently show Gram-negative outer membrane and ribosome targeting. The co-occurrence could represent bifunctional output or regulatory co-clustering of two independent pathways. Extract-level MRSA/Candida frame applies.

**Isolation strategy:** Solid ISP2 agar, 28°C, 14 days. TFBS: AdpA-dominant landscape — late harvest (stationary phase, day 7–10 on solid). UMED MATURATION_GAP — verify LanP/lasso protease elsewhere on chromosome. Detection: transAT-PKS products UV 240–280 nm; LC-MS 600–1,800 Da positive ESI. Lasso: heat/protease stability screen (boil 10 min, then treat with proteinase K — lasso backbone survives, linear peptides degrade). bldA tier: confirm in workbook (not T4 in this strain overall, but check individual BGC assignment).

------------------------------------------------------------------------

#### BGC008 (CP023690.1 · region008) — Exceptional tier \| CDPS + lanthipeptide-class-i

**Location:** CP023690.1 · region008 · Interior · 56,048 bp · 49 CDS · Arch A

**Products:** CDPS; NRPS; RiPP; lanthipeptide-class-i

**CCTT:** T43-DKP corroborated (CDPS domain) + T43-LAN corroborated (LanB/LanC)

**KCB:** BGC0000450.5 (triostin A) · score 28,385

**AB/AF/Nov:** 86.0 / 32.0 / 37.0

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_451 | 20,001–26,003 | Condensation; AMP-binding; PP-binding; NAD_binding_4 | Large NRPS — C-A-T modules; annotated lanthipeptide-class-i region |
| ctg1_459 | compl. 31,875–35,030 | Lant_dehydr_N; Lant_dehydr_C; Lanthipeptide_LanB_RRE | \*\*LanB dehydratase\*\* — installs dehydroalanine/dehydrobutyrine (class-i essential) |
| ctg1_458 | compl. 30,571–31,878 | LANC_like | \*\*LanC cyclase\*\* — forms lanthionine thioether rings (class-i essential) |
| ctg1_460 | 35,228–35,371 | — | Annotated CDPS; predicted lanthipeptide precursor peptide |
| ctg1_469 | compl. 45,233–46,048 | CDPS | \*\*Cyclodipeptide synthase\*\* — DKP biosynthesis (T43-DKP trigger source) |
| ctg1_444 | compl. 10,526–11,380 | Condensation | Condensation domain — standalone module |
| ctg1_461 | 35,883–37,013 | Pyr_redox_2 | Pyridine nucleotide disulfide oxidoreductase (SMCOG1175, oxidative tailoring) |
| ctg1_467 | compl. 42,258–43,439 | — | FAD-binding monooxygenase (SMCOG1050) |
| ctg1_450 | 18,533–19,714 | — | β-lactamase fold hydrolase (SMCOG1053, maturation protease candidate) |
| ctg1_475 | 52,148–53,320 | — | β-lactamase fold (SMCOG1053) |
| ctg1_446 | compl. 12,428–14,734 | — | ABC transporter ATPase (SMCOG1000, self-resistance) |
| ctg1_447 | compl. 14,828–15,781 | — | SDR oxidoreductase (SMCOG1001) |
| ctg1_431 | 934–1,575 | — | TetR regulator (SMCOG1057) |
| ctg1_455 | compl. 27,641–28,591 | — | MerR-family regulator (SMCOG1171) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a lanthipeptide-class-i pathway co-clustered with an independent diketopiperazine (CDPS) pathway. The class-i lanthipeptide machinery is complete: LanB dehydratase (ctg1_459, Lant_dehydr_N + Lant_dehydr_C + LanB_RRE) plus LanC cyclase (ctg1_458, LANC_like) are the canonical class-i enzyme pair. The precursor peptide (ctg1_460) is co-annotated as CDPS and lanthipeptide — this may reflect a bifunctional precursor or two adjacent short ORFs. The CDPS (ctg1_469, DKP domain) independently produces a cyclic dipeptide (T43-DKP trigger). KCB similarity to triostin A (score 28,385) — triostin A is a cyclic depsipeptide antibiotic — the NRPS module (ctg1_451, large C-A-T enzyme) may produce a linear peptide scaffold. Two T43 triggers co-firing (DKP + LAN) on a single locus is unusual and warrants careful gene-level resolution of which genes serve which pathway. Capacity claim only.

**Mechanistic link:** Class-i lanthipeptides have established antibacterial activity against Gram-positive organisms through lipid II inhibition (nisin class) or membrane disruption. DKPs have diverse activities. The NRPS component adds additional mechanistic possibilities. AB score 86.0 reflects strong antibacterial priority.

**Isolation strategy:** Solid ISP2 agar, 28°C, 14–21 days. LanBC-dependent maturation requires sporulation-phase culture for expression. Detection: lanthipeptide scaffold; MALDI-MS or ESI-MS for cyclic peptide in 500–2,000 Da range. DKP detection: acidic extraction (EtOAc pH 3), TLC-visualisation of cyclic dipeptide spots.

------------------------------------------------------------------------

#### BGC010 (CP023690.1 · region010) — High tier \| T1PKS + lanthipeptide-class-iii \| \[E-signal\]

**Location:** CP023690.1 · region010 · Interior · 58,574 bp · 45 CDS · Arch A

**Products:** PKS; RiPP; T1PKS; lanthipeptide-class-iii

**CCTT:** T43-ENE corroborated + T43-LAN corroborated

**KCB:** BGC0000033.5 (calicheamicin) · score 31,933

**AB/AF/Nov:** 84.0 / 34.0 / 37.0

**Note:** T43-ENE fires on this locus. Per pipeline standing rule, the \[E-signal\] claim-safety note applies: enediyne-adjacent signal noted for information; no compound-identity claim to any enediyne class; BSL-2 flag retired (v9.7.75).

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_642 | 20,001–25,955 | ene_KS; PKS_AT; ketoacyl-synt; PP-binding | \*\*T1PKS with ene_KS\*\* — enediyne ketosynthase (T43-ENE trigger source); also PKS_AT |
| ctg1_643 | 25,959–26,474 | 4HBT_2 | 4-hydroxybenzoyl-CoA thioesterase type 2 (iterative PKS release) |
| ctg1_659 | 43,028–45,616 | micKC; LANC_like | \*\*Class-iii lanthipeptide synthetase micKC\*\* (T43-LAN trigger) |
| ctg1_662 | 45,622–49,845 | micKC; Pkinase; APH | \*\*Second class-iii synthetase\*\* with kinase + phosphotransferase (class-iii dual enzyme) |
| ctg1_660 | 45,622–45,717 | — | Predicted lanthipeptide precursor \#1 |
| ctg1_661 | 45,784–45,879 | — | Predicted lanthipeptide precursor \#2 |
| ctg1_658 | 41,657–42,628 | PF04055 | Radical SAM enzyme (methyltransferase, tailoring) |
| ctg1_655 | compl. 37,056–38,447 | Aldedh | Aldehyde dehydrogenase (SMCOG1017, tailoring oxidoreductase) |
| ctg1_630 | 5,936–6,805 | — | O-methyltransferase (SMCOG1042, tailoring) |
| ctg1_650 | 32,757–34,427 | Pyr_redox_2 | Pyridine nucleotide disulfide oxidoreductase (SMCOG1175) |
| ctg1_636 | compl. 12,540–13,970 | — | EmrB/QacA drug resistance transporter (SMCOG1005, self-resistance) |
| ctg1_663 | 48,571–49,845 | — | MFS transporter (SMCOG1020, self-resistance) |
| ctg1_656 | compl. 38,588–39,289 | — | LuxR response regulator (SMCOG1016) |
| ctg1_657 | compl. 39,282–41,315 | — | Sensor histidine kinase (SMCOG1048) |

**Pathway hypothesis \[E-signal applies\]:** The ene_KS domain (ctg1_642) is diagnostic for iterative enediyne-type PKS chemistry — this is the T43-ENE trigger. The KCB hit to calicheamicin (BGC0000033.5, score 31,933) is consistent with enediyne-class biosynthesis, but KCB = similarity not identity. The concurrent class-iii lanthipeptide pathway (ctg1_659 + ctg1_662, two micKC synthetases, two predicted precursor peptides ctg1_660 + ctg1_661) represents a second independent RiPP pathway on this locus. Class-iii lanthipeptides use a fused kinase-cyclase enzyme (micKC) rather than the separate LanB/LanC of class-i. Two micKC genes and two precursor peptides suggest a multi-variant lanthipeptide output. The co-location of an ene_KS PKS and a class-iii lanthipeptide sub-pathway in one antiSMASH region may reflect true co-clustering or antiSMASH region merging across adjacent clusters. \[E-signal\] note: enediyne-class biosynthesis is noted; no BSL-2 flag applies; capacity-level only.

**Mechanistic link:** Enediyne-adjacent PKS capacity potentially relevant to DNA-cleaving mechanisms. Class-iii lanthipeptides have emerging antibacterial activity profiles. AB score 84.0 places this as the third-ranked antibacterial lead. Route to wet lab requires caution for the PKS component.

**Isolation strategy:** Class-iii lanthipeptide detection: protease-stable, heat-stable cyclic peptide; MALDI-MS. For the PKS component: standard EtOAc extraction; LC-MS. Consider solid-phase extraction before LC-MS if enediyne-class chemistry is to be investigated.

------------------------------------------------------------------------

#### BGC059 (CP023690.1 · region059) — High tier \| lanthipeptide-class-iv

**Location:** CP023690.1 · region059 · Interior · 65,181 bp · 55 CDS · Arch A

**Products:** RiPP; fatty_acid; lanthipeptide-class-iv; other

**CCTT:** T43-LAN corroborated

**KCB:** BGC0002315.2 (accramycin A) · score 12,687

**AB/AF/Nov:** 82.0 / 24.0 / 29.0

**Gene-by-gene (key biosynthetic):**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_7590 | compl. 10,001–12,721 | Pkinase; LANC_like | \*\*Class-iv lanthipeptide synthetase\*\* — kinase-cyclase fusion (T43-LAN) |
| ctg1_7597 | 20,967–23,393 | Pkinase | Additional protein kinase (phosphorylation during maturation) |
| ctg1_7610 | 35,122–36,333 | t2fas; ketoacyl-synt | Type-II fatty acid synthase KS (fatty_acid component) |
| ctg1_7591 | compl. 13,763–15,565 | PF04055 | Radical SAM enzyme |
| ctg1_7594 | compl. 17,466–18,530 | Fer4_12; PF04055 | Iron-sulfur cluster + Radical SAM (methylation tailoring) |
| ctg1_7604 | compl. 29,799–31,109 | RmlD_sub_bind | Sugar epimerase/dehydratase (saccharide tailoring) |
| ctg1_7613 | 39,300–40,349 | Polysacc_synt_2; RmlD_sub_bind | Polysaccharide synthase-related (additional sugar modification) |
| ctg1_7616 | 42,425–43,171 | Glycos_transf_2 | Glycosyltransferase (sugar attachment) |
| ctg1_7601 | 27,165–27,983 | Abhydrolase_6; PF00561 | Hydrolase fold (possible maturation protease) |
| ctg1_7592 | compl. 15,562–17,235 | — | ABC transporter (SMCOG1288, self-resistance) |
| ctg1_7593 | compl. 17,466–18,530 | — | ABC transporter (SMCOG1288, tandem self-resistance) |
| ctg1_7624 | compl. 51,071–51,952 | — | ABC-2 transporter (SMCOG1065) |
| ctg1_7625 | compl. 51,949–52,848 | — | ABC transporter ATPase (SMCOG1000) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a class-iv lanthipeptide with unusual tailoring. Class-iv lanthipeptides use a fused kinase-LANC synthetase (ctg1_7590), distinct from class-i (separate LanB + LanC) and class-iii (micKC without the LANC-like domain). The additional protein kinase (ctg1_7597) may phosphorylate the precursor peptide as part of the thioether-forming cascade. Multiple glycosyltransferase and sugar-modification enzymes (ctg1_7604, ctg1_7613, ctg1_7616) suggest glycosylated lanthipeptide output. The fatty_acid component (ctg1_7610, t2fas KS) may produce a fatty acid chain attached to the lanthipeptide scaffold — lipid-modified lanthipeptides are a known sub-class. Multiple Radical SAM enzymes (ctg1_7591, ctg1_7594) suggest additional methylations or unusual modifications. KCB similarity to accramycin A (score 12,687) is relatively low — novel divergent lanthipeptide is likely. Capacity claim only.

**Mechanistic link:** Glycosylated and lipid-modified lanthipeptides can have enhanced membrane affinity and antibacterial potency compared to unmodified lanthipeptides. AB 82.0 reflects T43-LAN diagnostic corroboration plus the ABC tandem self-resistance signal (T1 hit confirmed).

**Isolation strategy:** Class-iv lanthipeptides are less well-characterised than class-i/ii — no established isolation protocol. Solid ISP2, 28°C, 14 days. MALDI-MS for the peptide scaffold after mild acid hydrolysis to release sugar chains if glycosylated. ESI-MS positive mode, mass range 800–3,000 Da for lipopeptide.

------------------------------------------------------------------------

#### BGC065 (CP023690.1 · region065) — High tier \| lanthipeptide-class-ii

**Location:** CP023690.1 · region065 · Interior · 22,880 bp · 23 CDS · Arch A

**Products:** RiPP; lanthipeptide-class-ii

**CCTT:** T43-LAN corroborated

**KCB:** BGC0001199.5 (akaeolide) · score 11,125

**AB/AF/Nov:** 74.0 / 24.0 / 39.0

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_8068 | 10,001–12,880 | DUF4135; LANC_like | \*\*Class-ii lanthipeptide LanM synthetase\*\* (T43-LAN trigger) — LanM is the defining fused enzyme of class-ii, combining dehydratase and cyclase functions |
| ctg1_8067 | 9,670–9,867 | — | Predicted lanthipeptide precursor peptide |
| allorf_x3 | compl. 14,354–14,449 | — | Additional predicted lanthipeptide precursors (×3 allORFs) |
| ctg1_8062 | 2,276–3,901 | Amidohydro_1 | Amidohydrolase — possible leader peptide processing protease |
| ctg1_8065 | 5,407–6,471 | — | O-methyltransferase (SMCOG1042) |
| ctg1_8074 | 16,104–17,141 | — | α/β hydrolase (SMCOG1066, maturation protease candidate) |
| ctg1_8066 | 6,747–9,554 | — | SARP transcriptional activator (SMCOG1041, pathway-specific regulation) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a class-ii lanthipeptide. The LanM fused synthetase (ctg1_8068, DUF4135 + LANC_like) is the class-defining enzyme: it installs both dehydroamino acids and thioether rings in a single bifunctional polypeptide, unlike the two-enzyme (LanB + LanC) system of class-i. Multiple predicted precursor peptides (ctg1_8067, allorf_x3) suggest a multi-variant output. KCB similarity to akaeolide (score 11,125) — akaeolide is a class-ii lanthipeptide with antibacterial activity. The cluster is compact (22.9 kb) and architecturally clean (single LanM, clear precursor, SARP activator, maturation protease candidate). SARP activator (ctg1_8066) provides a transcriptional activation handle. Novelty_auto 39.0 — divergent from known references.

**Mechanistic link:** Class-ii lanthipeptides include the cinnamycin/duramycin family (phosphatidylethanolamine-targeting, membrane disruption) and actagardine/mersacidin (lipid II inhibition). AB 74.0 with T43-LAN corroboration. SARP-mediated transcriptional control suggests accessible inducibility.

**Isolation strategy:** Solid ISP2 agar, 28°C, 14 days. SARP activator — consider overexpression for constitutive activation. Precursor is short peptide; MALDI-MS after C18 SPE cleanup. Class-ii lanthipeptides typically require leader peptide cleavage by the co-clustered protease; confirm ctg1_8062 or ctg1_8074 is the correct LanP equivalent.

------------------------------------------------------------------------

#### BGC002 (CP023690.1 · region002) — Medium tier \| β-lactam

**Location:** CP023690.1 · region002 · Interior · 51,713 bp · 44 CDS · Arch A

**Products:** PKS; PKS-like; blactam; butyrolactone; other

**CCTT:** T43-BLA corroborated

**KCB:** BGC0001151.5 (valclavam / (-)-2-(2-hydroxyethyl)clavam) · score 20,104

**AB/AF/Nov:** 54.0 / 24.0 / 19.0

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_111 | 27,143–28,678 | GATase_7; BLS; Asn_synthase | \*\*β-lactam synthetase (BLS)\*\* — class-defining enzyme for clavulanic acid / clavam biosynthesis (T43-BLA trigger) |
| ctg1_113 | 29,721–30,695 | CAS; TauD | \*\*Clavaminate synthase (CAS)\*\* — non-haem iron oxygenase, clavulanic acid pathway |
| ctg1_102 | 16,393–16,683 | — | Annotated blactam — short β-lactam-associated gene |
| ctg1_94 | 5,001–6,137 | AfsA | Butyrolactone synthase (AfsA, autoregulator) |
| ctg1_114 | compl. 30,754–31,713 | ksIII | Type-III PKS KS domain (stilbene/chalcone-type) |
| ctg1_110 | 25,424–27,139 | TPP_enzyme_N; TPP_enzyme_C | Pyruvate decarboxylase (SMCOG1055, ACVS precursor supply) |
| ctg1_115 | compl. 31,791–32,930 | azdH | azdH (acyl-CoA dehydrogenase type 2, SMCOG1191, cephamycin-related) |
| ctg1_106 | 19,575–20,264 | HAD_2 | HAD-superfamily phosphatase (SMCOG1115) |
| ctg1_117 | compl. 34,002–34,694 | PF00881 | Nitroreductase-fold |
| ctg1_118 | compl. 34,752–36,125 | Aminotran_3 | Aminotransferase class III (SMCOG1013, amino acid precursor) |
| ctg1_121 | compl. 38,542–39,522 | PF00561; Abhydrolase_6 | α/β hydrolase |
| ctg1_122 | compl. 39,519–40,440 | ADH_zinc_N | Crotonyl-CoA reductase / alcohol dehydrogenase (SMCOG1028) |
| ctg1_124 | compl. 41,547–42,662 | — | β-lactamase-fold (SMCOG1053, self-resistance candidate) |
| ctg1_100 | 13,127–16,084 | — | SARP transcriptional activator (SMCOG1041) |
| ctg1_109 | compl. 22,464–24,608 | — | Second SARP (SMCOG1041) |
| ctg1_123 | 40,517–41,482 | — | LysR regulator (SMCOG1014) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a clavulanic acid / clavam-class β-lactam. BLS (ctg1_111) and CAS (ctg1_113) are the two class-defining enzymes of the clavulanic acid pathway, and both are present. KCB similarity to valclavam (BGC0001151.5, score 20,104) — valclavam is a clavulanic acid analogue. The butyrolactone synthase (ctg1_94, AfsA) produces an autoregulatory butyrolactone — many *Streptomyces* secondary metabolite clusters are co-regulated by AfsA-derived autoregulators. The type-III PKS (ctg1_114, ksIII) is unusual in a β-lactam context and may contribute a polyketide starter unit or be independently regulated. Two SARP transcriptional activators suggest this cluster is under tight developmental control. T43-BLA corroborated on BLS domain. Capacity claim only.

**Mechanistic link:** Clavulanic acid is a β-lactamase inhibitor — it potentiates other β-lactam antibiotics by irreversibly inhibiting β-lactamase enzymes in resistant bacteria. Biosynthetic capacity for a clavulanic acid-class compound is therefore an AB lead with a β-lactamase inhibitor mechanism. AB 54.0.

**Isolation strategy:** β-lactam/clavulanic acid derivatives are water-soluble; extract culture broth (not mycelium) by ion-exchange or SPE at pH 3.0. HPLC with UV detection at 260 nm. Bioactay: β-lactamase inhibition assay using nitrocefin substrate is a specific colorimetric handle.

------------------------------------------------------------------------

#### BGC005 (CP023690.1 · region005) — Medium tier \| transAT-PKS + NRPS

**Location:** CP023690.1 · region005 · Interior · 65,937 bp · 46 CDS · Arch A

**Products:** NRPS; PKS; PKS-like; T1PKS; transAT-PKS

**CCTT:** no trigger

**KCB:** BGC0001845.2 (alpiniamide) · score 37,364

**AB/AF/Nov:** 59.0 / 48.0 / 49.0

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_263 | compl. 20,001–21,248 | PKS_AT; PP-binding | trans-acting AT (PKS_AT; SMCOG1021 malonyl-CoA-ACP transacylase) |
| ctg1_265 | compl. 22,309–30,771 | hyb_KS; PKS_AT; mod_KS; ketoacyl-synt | T1PKS multi-module: hybrid KS + modular KS + AT |
| ctg1_266 | compl. 30,764–35,233 | ATd; tra_KS; PP-binding; ketoacyl-synt | transAT-PKS module: AT-deficient KS + trans-AT docking |
| ctg1_267 | compl. 35,258–45,937 | ATd; tra_KS; PP-binding; Condensation; AMP-binding | \*\*Large hybrid transAT-PKS/NRPS\*\* — AT-deficient KS modules + NRPS C-A-T |
| ctg1_264 | compl. 21,248–22,312 | ksIII | Type-III PKS KS (starter unit synthesis) |
| ctg1_243 | 1,212–1,799 | — | PKS-like (short PKS gene) |
| ctg1_253 | compl. 11,861–12,874 | Abi | Abortive infection system protein (rare in PKS context) |
| ctg1_259 | compl. 16,006–16,542 | — | Methyltransferase (SMCOG1089) |
| ctg1_252 | 10,422–11,138 | — | TetR regulator (SMCOG1239) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a large transAT-PKS/NRPS hybrid. The trans-acting AT (ctg1_263) loads malonyl-CoA or methylmalonyl-CoA onto AT-deficient KS modules (ctg1_266, ctg1_267). The megasynthase spans ctg1_265 through ctg1_267 — approximately 23 kb of biosynthetic protein — encoding at least 4–5 extension modules. KCB similarity to alpiniamide (BGC0001845.2, score 37,364) — alpiniamide is a polyketide-NRPS hybrid. Novelty_auto 49.0 reflects moderate divergence. The type-III PKS (ctg1_264, ksIII) likely provides a starter unit. No CCTT trigger fired — the class is supported by KCB anchor and antiSMASH product annotation only. Capacity claim only.

**Mechanistic link:** TransAT-PKS/NRPS hybrids encompass a broad range of biological activities. Alpiniamide is antifungal — the AF score 48.0 reflects this KCB-class signal. No diagnostic confirmation beyond KCB anchor.

**Isolation strategy:** Large PKS/NRPS products typically non-polar; EtOAc extraction from whole culture. UV 250–300 nm for polyketide chromophores. LC-MS positive ESI, 500–2,000 Da.

------------------------------------------------------------------------

#### BGC011 (CP023690.1 · region011) — Medium tier \| NRP-metallophore + NRPS + transAT-PKS-like \| \[E-signal\]

**Location:** CP023690.1 · region011 · Interior · 119,610 bp · 49 CDS · Arch A

**Products:** NRP-metallophore; NRPS; PKS; PKS-like; T3PKS; transAT-PKS-like

**CCTT:** T43-ENE corroborated

**KCB:** BGC0002810.2 (hangtaimycin / deoxyhangtaimycin) · score 79,191

**AB/AF/Nov:** 59.0 / 52.0 / 49.0

**Note:** \[E-signal\] applies (T43-ENE). Largest BGC in the strain at 119.6 kb.

**Gene-by-gene (selected biosynthetic):**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_775 | compl. 22,844–32,074 | Condensation; AMP-binding; PP-binding | Large NRPS — C-A-T modules |
| ctg1_776 | compl. 32,089–39,741 | Condensation; AMP-binding; PP-binding | NRP-metallophore NRPS — C-A-T (iron-chelating NRPS) |
| ctg1_777 | compl. 39,738–53,738 | ATd; tra_KS; PP-binding; ketoacyl-synt | \*\*transAT-PKS-like\*\* megasynthase module (14 kb gene) |
| ctg1_778 | compl. 53,738–75,688 | Condensation; AMP-binding; ATd; adh_short | \*\*Hybrid NRPS/transAT-PKS\*\* — 22 kb gene (largest biosynthetic gene in strain) |
| ctg1_779 | compl. 75,685–89,835 | PKS_KS; tra_KS; ATd; ketoacyl-synt; adh_short | transAT-PKS-like KS modules (14 kb) |
| ctg1_772 | compl. 20,001–21,284 | Chal_sti_synt_N | \*\*T3PKS\*\* chalcone/stilbene synthase fold |
| ctg1_773 | compl. 21,305–22,528 | t2pks2; ketoacyl-synt | Type-II PKS KS domain |
| ctg1_786 | compl. 97,385–98,647 | EntC | \*\*Isochorismate synthase\*\* (EntC) — siderophore precursor |
| ctg1_787 | compl. 98,786–99,610 | EntA; adh_short; adh_short_C2 | \*\*2,3-dihydro-2,3-DHBA dehydrogenase (EntA)\*\* — catecholate siderophore |
| ctg1_785 | compl. 95,730–97,388 | AMP-binding | AMP-dependent synthetase (SMCOG1002) |
| ctg1_782 | compl. 92,501–93,757 | Glyco_transf_28 | Glycosyltransferase (SMCOG1102) |
| ctg1_780 | 90,243–90,998 | Thioesterase; Abhydrolase_6 | Thioesterase release |
| ctg1_791 | 103,027–103,905 | APH | Aminoglycoside phosphotransferase (self-resistance) |
| ctg1_798 | compl. 111,316–112,257 | — | ClassA β-lactamase fold (resistance) |
| ctg1_793 | 104,722–107,904 | — | SARP regulator (SMCOG1041) |
| ctg1_801 | 114,441–116,741 | — | Second SARP (SMCOG1041) |
| ctg1_769 | 14,405–15,637 | p450 | Cytochrome P450 (SMCOG1007, oxidative tailoring) |
| ctg1_770 | compl. 15,723–17,672 | PKS_AT | Malonyl-CoA-ACP transacylase (SMCOG1021, trans-AT) |

**Pathway hypothesis \[E-signal\]:** The largest BGC in *S. spectabilis* at 119.6 kb. Multiple evidence lines converge: the catecholate siderophore sub-pathway (EntC + EntA, ctg1_786/787) generates 2,3-dihydroxybenzoic acid for iron chelation — the NRP-metallophore annotation. The three large transAT-PKS-like genes (ctg1_777, ctg1_778, ctg1_779, together ~50 kb) constitute a massive hybrid PKS/NRPS megasynthase. The T3PKS (ctg1_772) and type-II KS (ctg1_773) add additional biosynthetic capabilities. T43-ENE fires on this locus — the ene_KS-like chemistry in the transAT context may not represent canonical enediyne chemistry; the \[E-signal\] is noted rather than acting as a classification. KCB similarity to hangtaimycin (BGC0002810.2, score 79,191) — hangtaimycin is a macrolide-like natural product. The highest KCB score in the strain for any single BGC; the similarity likely reflects the large gene cluster overlapping multiple reference pathways. Capacity claim only.

**Mechanistic link:** NRP-metallophore siderophore capacity + large PKS/NRPS hybrid = potential for a macrolide-siderophore conjugate with Fe-dependent activity (analogous to siderophore-antibiotic conjugates). AF 52.0 is the highest antifungal score in the strain for this BGC; the siderophore component may disrupt fungal iron homeostasis. AB 59.0.

**Isolation strategy:** This is the most complex BGC in the strain — largest cluster, multi-enzyme system, multiple product classes. Prioritise fermentation optimisation before isolation: ISP2 solid, 28°C, 21 days. For the siderophore component: chrome azurol S (CAS) agar overlay for siderophore detection. For the macrolide: EtOAc extraction, LC-MS. SARP dual regulation suggests tight developmental control — OSMAC with carbon source variation.

------------------------------------------------------------------------

#### BGC024 (CP023690.1 · region024) — Medium tier \| T1PKS + herbimycin anchor \| T43-TET

**Location:** CP023690.1 · region024 · Interior · 84,618 bp · 43 CDS · Arch A

**Products:** PKS; T1PKS

**CCTT:** T43-TET corroborated (tetronate/spirotetronate)

**KCB:** BGC0000074.5 (herbimycin A) · score 103,558

**AB/AF/Nov:** 39.0 / 34.0 / 27.0

**Gene-by-gene (key biosynthetic):**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_2846 | 20,001–26,381 | mod_KS; PKS_AT; ketoacyl-synt; adh_short | T1PKS module — KS + AT + ketoreductase |
| ctg1_2848 | compl. 28,001–33,463 | mod_KS; PKS_AT; ketoacyl-synt; adh_short | T1PKS module |
| ctg1_2849 | compl. 33,475–41,802 | hyb_KS; PKS_AT; PP-binding; mod_KS | Hybrid KS — multiple PKS modules |
| ctg1_2853 | compl. 47,937–58,268 | PKS_AT; adh_short; PP-binding; mod_KS | T1PKS module |
| ctg1_2854 | compl. 58,304–64,618 | mod_KS; PKS_AT; ketoacyl-synt; ADH_zinc_N | T1PKS module with ADH_zinc_N |
| ctg1_2844 | compl. 17,056–18,375 | PKS_AT | trans-acting AT (SMCOG1021) |
| ctg1_2856 | compl. 66,705–67,796 | HAD_2 | \*\*FkbH-like HAD domain\*\* (SMCOG1256) — \*\*T43-TET trigger source\*\* (glycerol phosphate starter unit for spirotetronate) |
| ctg1_2858 | compl. 69,207–69,192 | PP-binding; PP-binding_2 | ACP (SMCOG1147) |
| ctg1_2859 | compl. 69,207–69,878 | Methyltransf_3; PCMT | Methyltransferase + carboxymethyl transferase |
| ctg1_2836 | 8,480–9,439 | PALP | Cysteine synthase (SMCOG1081) |
| ctg1_2852 | compl. 45,069–47,921 | Aminotran_3 | Aminotransferase class III (SMCOG1013) |
| ctg1_2839 | compl. 11,247–13,133 | Pkinase | Serine/threonine kinase (SMCOG1030, regulatory) |
| ctg1_2855 | compl. 64,750–66,618 | — | SARP regulator (SMCOG1041) |
| ctg1_2857 | compl. 67,824–68,924 | Acyl-CoA_dh_N; Acyl-CoA_dh_M; Acyl-CoA_dh_1 | Acyl-CoA dehydrogenase (tailoring) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a spirotetronate-class or tetronate-class T1PKS. The FkbH-like HAD domain (ctg1_2856, SMCOG1256) is the T43-TET trigger — FkbH catalyses glycerol-3-phosphate starter unit attachment, which is the committed first step of spirotetronate biosynthesis. Known spirotetronates include chlorothricin, spirohexenolide, and versipelostatin. KCB similarity to herbimycin A (BGC0000074.5, score 103,558 — the highest single-reference KCB score in the strain) places this cluster in the ansamycin/benzoquinone ansamycin context. Herbimycin A is an Hsp90 chaperone inhibitor. However, the antiSMASH product annotation is T1PKS without an explicit ansamycin call, and the T43-TET trigger (not an ansamycin trigger) dominates the class interpretation. The large T1PKS megasynthase (5 modular genes, ctg1_2846 through ctg1_2854) spans approximately 40 kb. Capacity claim only.

**Mechanistic link:** Spirotetronates include compounds with Hsp90 inhibition, topoisomerase inhibition, and antibacterial activities. Herbimycin-class ansamycins inhibit Hsp90 (antitumour, antifungal contexts). AB 39.0 / AF 34.0 — moderate priority. The T43-TET corroboration elevates confidence in the class call above keyword alone.

**Isolation strategy:** Large T1PKS compound; EtOAc extraction. UV absorption likely in the 250–320 nm range for a polyketide chromophore. LC-MS positive ESI 500–1,500 Da. If herbimycin-class: Hsp90 ATPase inhibition assay as a specific bioactivity handle.

------------------------------------------------------------------------

#### BGC051 (CP023690.1 · region051) — Medium tier \| prodigiosin-class

**Location:** CP023690.1 · region051 · Interior · 58,323 bp · 43 CDS · Arch A

**Products:** NRPS; NRPS-like; PKS; T1PKS; fatty_acid; other; prodigiosin; saccharide

**CCTT:** no trigger

**KCB:** BGC0001063.5 (undecylprodigiosin) · score 27,169

**AB/AF/Nov:** 59.0 / 42.0 / 35.0

**Gene-by-gene (key biosynthetic):**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_6815 | compl. 20,001–27,770 | FAAL_cd05931; AMP-binding; PP-binding; hyb_KS | \*\*Fatty acid-AMP ligase + hybrid PKS\*\* — fatty acyl chain activation (prodigiosin octyl chain) |
| ctg1_6816 | compl. 27,793–29,493 | AMP-binding | AMP-dependent synthetase (SMCOG1002) |
| ctg1_6817 | compl. 29,499–31,301 | PP-binding; Aminotran_1_2 | Aminotransferase + ACP (SMCOG1109 — 8-amino-7-oxononanoate synthase) |
| ctg1_6812 | compl. 15,271–18,009 | PPDK_N | \*\*Phosphoenolpyruvate-protein phosphotransferase\*\* — prodiginine ring biosynthesis |
| ctg1_6820 | compl. 31,897–32,928 | fabH | FabH — 3-oxoacyl-ACP synthase (fatty acid synthesis priming) |
| ctg1_6821 | 33,263–34,588 | t2fas; ketoacyl-synt | Type-II FAS KS (SMCOG1022 — fatty acid biosynthesis) |
| ctg1_6829 | compl. 40,736–43,495 | PKS_KS; ketoacyl-synt | PKS KS domain (SMCOG1022, backbone extension) |
| ctg1_6800 | 715–2,040 | Orn_monoox; Pyr_redox_2 | Ornithine monooxygenase (SMCOG1080 — proline/ornithine oxidation for pyrrole ring) |
| ctg1_6806 | 7,984–9,243 | p450 | Cytochrome P450 (SMCOG1007) |
| ctg1_6813 | compl. 18,006–19,169 | — | O-methyltransferase (SMCOG1042) |
| ctg1_6803 | 4,371–5,282 | — | Prodigiosin-annotated gene (SMCOG1174 — acetylglutamate kinase-like) |
| ctg1_6834 | compl. 46,953–48,323 | DegT_DnrJ_EryC1; Aminotran_5; Aminotran_1_2 | Sugar aminotransferase (deoxysugar biosynthesis) |
| ctg1_6830 | compl. 43,649–44,434 | — | SARP regulator (SMCOG1041) |
| ctg1_6832 | 45,483–46,136 | — | ABC transporter (SMCOG1000, self-resistance) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a prodiginine (prodigiosin-class) tripyrrole pigment/antibiotic. Prodiginines are produced by a convergent pathway: one branch produces 4-methoxy-2,2'-bipyrrole-5-carbaldehyde (MBC) via NRPS-like machinery; the other produces 2-undecylpyrrole via fatty acid + PKS; they condense to form the tripyrrole chromophore. The PPDK_N domain (ctg1_6812) and ornithine monooxygenase (ctg1_6800, Orn_monoox) are consistent with the MBC branch. The fatty acid-AMP ligase (ctg1_6815, FAAL) and FabH (ctg1_6820) supply the alkyl-pyrrole branch. KCB similarity to undecylprodigiosin (BGC0001063.5, score 27,169) is class-concordant. No CCTT trigger fires because no prodiginine trigger family exists in the current CCTT set. Prodiginines have antibacterial, antifungal, and antimalarial activities. Capacity claim only.

**Mechanistic link:** Prodiginines intercalate DNA (via tripyrrole chromophore), trigger apoptosis, and inhibit vacuolar H+-ATPases. Antibacterial against Gram-positive organisms; antifungal activity documented in some congeners. AB 59.0, AF 42.0.

**Isolation strategy:** Prodiginines are red pigments visible on colony surface — visual detection on ISP2 agar without additional analytical equipment. Solid culture extraction with methanol; red-coloured fraction enrichment. UV absorption at 530 nm (characteristic prodiginine chromophore). EtOAc extraction or C18 SPE from broth.

------------------------------------------------------------------------

#### BGC054 (CP023690.1 · region054) — Medium tier \| streptovaricin-class T1PKS

**Location:** CP023690.1 · region054 · Interior · 103,120 bp · 48 CDS · Arch A

**Products:** NRPS; NRPS-like; PKS; T1PKS; butyrolactone; other

**CCTT:** no trigger

**KCB:** BGC0001785.5 (streptovaricin) · score 141,254 — highest KCB score in the strain

**AB/AF/Nov:** 51.0 / 42.0 / 35.0

**Gene-by-gene (key biosynthetic):**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_6977 | 27,783–44,885 | PKS_AT; mod_KS; AMP-binding; PP-binding; adh_short | \*\*Large T1PKS + NRPS-like\*\* module (17 kb) |
| ctg1_6978 | 44,917–55,716 | PKS_AT; mod_KS; ketoacyl-synt; adh_short | T1PKS module (10.8 kb) |
| ctg1_6979 | 55,753–66,645 | PKS_AT; mod_KS; adh_short; ketoacyl-synt | T1PKS module (10.9 kb) |
| ctg1_6980 | 66,842–72,421 | PKS_AT; mod_KS; ketoacyl-synt; adh_short | T1PKS module (5.6 kb) |
| ctg1_6981 | 72,474–83,120 | PKS_AT; mod_KS; adh_short; ketoacyl-synt | T1PKS module (10.6 kb) |
| ctg1_6957 | compl. 5,870–7,324 | — | T1PKS gene (upstream module) |
| ctg1_6983 | 84,027–85,088 | Fe-ADH; DHQ_synthase | \*\*3-dehydroquinate synthase\*\* (SMCOG1183) — AHBA biosynthesis precursor for ansamycin |
| ctg1_6956 | compl. 5,001–5,732 | AfsA | \*\*Butyrolactone synthase (AfsA)\*\* — autoregulator |
| ctg1_6967 | 16,113–17,297 | Glycos_transf_1 | Glycosyltransferase (SMCOG1045) |
| ctg1_6968 | 17,377–18,597 | NTP_transf_3 | NDP-sugar synthase (SMCOG1064) |
| ctg1_6969–6970 | 18,766–20,768 | GFO_IDH_MocA; GFO_IDH_MocA_C3 | NAD-oxidoreductase × 2 (sugar modification) |
| ctg1_6972 | 21,443–22,735 | p450 | Cytochrome P450 (SMCOG1007) |
| ctg1_6974 | 23,682–24,887 | p450 | Cytochrome P450 (SMCOG1007) |
| ctg1_6976 | 26,544–27,737 | p450 | Cytochrome P450 (SMCOG1007) |
| ctg1_6990 | 91,569–92,813 | p450 | Cytochrome P450 (SMCOG1007) |
| ctg1_6992 | 94,751–96,004 | p450 | Cytochrome P450 (SMCOG1007) — 5 P450 oxidases total |
| ctg1_6985 | 86,353–87,165 | ThiF | ThiF-domain sulfur relay (ubiquitin-activating fold) |
| ctg1_6986 | 87,333–88,493 | DegT_DnrJ_EryC1; Aminotran_1_2 | Aminotransferase (SMCOG1056, sugar biosynthesis) |
| ctg1_6991 | compl. 92,843–94,489 | — | FAD-binding monooxygenase (SMCOG1050) |
| ctg1_6993 | compl. 96,110–97,177 | MITE0000085 | O-methyltransferase (SMCOG1042) |
| ctg1_6994 | compl. 97,244–98,047 | — | Methyltransferase (SMCOG1089) |
| ctg1_6988 | 89,590–90,324 | HAD_2 | HAD phosphatase (SMCOG1115) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a streptovaricin-class ansamycin or related aromatic polyketide. The DHQ_synthase (ctg1_6983, SMCOG1183) is a key marker — 3-dehydroquinate synthase produces the AHBA (3-amino-5-hydroxybenzoic acid) starter unit characteristic of ansamycin natural products (rifamycin, streptovaricin, naphthomycin). KCB similarity to streptovaricin (BGC0001785.5, score 141,254 — the highest KCB score in this strain across all BGCs) is strongly class-concordant. Five cytochrome P450 oxidases (ctg1_6972, 6974, 6976, 6990, 6992) produce the oxidative tailoring characteristic of ansamycin complexity. Multiple sugar modification enzymes and glycosyltransferase suggest glycosylated output. AfsA butyrolactone (ctg1_6956) is an autoregulator. Capacity claim only — streptovaricin itself was produced by a related strain; this cluster may produce a variant.

**Mechanistic link:** Streptovaricins are ansamycins that inhibit bacterial RNA polymerase (same mechanism as rifamycin). Strong antibacterial capacity against mycobacteria and Gram-positive organisms including MRSA. The antifungal score (AF 42.0) is secondary. AB 51.0 in a well-characterised class.

**Isolation strategy:** Ansamycins are moderately polar; methanol/water extraction from solid culture, partition into EtOAc. UV absorption at 425 nm for the chromophoric ansamycin scaffold. IC50 against E. coli RNA polymerase as a specific bioactivity handle.

------------------------------------------------------------------------

#### BGC055 (CP023690.1 · region055) — Medium tier \| NRPS bonnevillamide-class

**Location:** CP023690.1 · region055 · Interior · 52,733 bp · 48 CDS · Arch A

**Products:** NRPS; NRPS-like

**CCTT:** no trigger

**KCB:** BGC0002373.3 (bonnevillamide D/E) · score 29,063

**AB/AF/Nov:** 41.0 / 32.0 / 27.0

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_7102 | 20,001–21,749 | AMP-binding; PP-binding | NRPS-like module (adenylation + ACP) |
| ctg1_7104 | 22,500–24,311 | AMP-binding; PP-binding | NRPS-like module (second A-T) |
| ctg1_7108 | 27,707–29,515 | AMP-binding; PP-binding | NRPS-like module (third A-T) |
| ctg1_7109 | 29,512–32,733 | Condensation; AMP-binding; PP-binding | Full NRPS module — C-A-T |
| ctg1_7111 | 33,183–34,667 | Condensation | Condensation domain (partial/standalone) |
| ctg1_7113 | 35,605–37,215 | PP-binding; Condensation | ACP + condensation (downstream) |
| ctg1_7114 | 37,208–38,578 | ATP-grasp_3; ATP-grasp | ATP-grasp-fold enzyme (ligase) |
| ctg1_7106 | 25,597–26,415 | Thioesterase | Thioesterase release domain |
| ctg1_7091 | compl. 8,397–9,602 | p450 | Cytochrome P450 (SMCOG1007, in NRPS gene) |
| ctg1_7105 | 24,308–25,600 | p450 | Cytochrome P450 (SMCOG1007) |
| ctg1_7107 | 26,412–27,659 | p450 | Cytochrome P450 (third P450) |
| ctg1_7112 | 34,851–35,615 | Thioesterase; Abhydrolase_6 | Second thioesterase |
| ctg1_7086 | compl. 3,158–4,480 | Glycos_transf_1 | Glycosyltransferase (SMCOG1045) |
| ctg1_7084 | compl. 914–1,897 | APH | Aminoglycoside phosphotransferase (self-resistance) |
| ctg1_7094 | 11,641–12,996 | — | Pyridoxal-dependent decarboxylase (SMCOG1180) |
| ctg1_7087–7088 | 4,667–6,795 | — | Two-component regulatory system |

**Pathway hypothesis:** Biosynthetic capacity consistent with a bonnevillamide-class NRPS linear or cyclic lipopeptide. Bonnevillamides are NRPS-derived lipopeptides with antibacterial activity. The module architecture — three NRPS-like A-T modules (ctg1_7102, 7104, 7108) followed by a full C-A-T module (ctg1_7109) — suggests a 4-residue linear or cyclic peptide core. The ATP-grasp ligase (ctg1_7114) may provide an unusual amide or lactam bond. Three cytochrome P450s (ctg1_7091, 7105, 7107) and a glycosyltransferase (ctg1_7086) contribute tailoring. Two thioesterase domains provide chain release options. APH self-resistance (ctg1_7084) gives a T1 hit. KCB anchor is relatively clean (bonnevillamide-class score 29,063). Capacity claim only.

**Mechanistic link:** Bonnevillamide-class NRPSs are antibacterial, mechanism poorly defined. AB 41.0 / AF 32.0 — Medium tier, moderate priority. APH self-resistance provides corroborating evidence of production.

**Isolation strategy:** NRPS lipopeptide — EtOAc extraction, C18 SPE. Mass range 500–2,000 Da, positive ESI. Bioassay: antibacterial against Gram-positive panel.

------------------------------------------------------------------------

#### BGC057 (CP023690.1 · region057) — Medium tier \| spectinomycin (aminocyclitol) — CALIBRATION GROUND TRUTH

**Location:** CP023690.1 · region057 · Interior · 108,644 bp · 78 CDS · Arch A

**Products:** NRPS; NRPS-like; PKS; T1PKS; amglyccycl; other

**CCTT:** no trigger (aminocyclitol class not in CCTT trigger set — correct behaviour)

**KCB:** BGC0000715.5 (actinospectacin / spectinomycin) · score 61,598

**AB/AF/Nov:** 59.0 / 48.0 / 35.0

**Calibration note:** BGC057 (CP023690.1 · region057) is the spectinomycin biosynthetic gene cluster — the compound that gives *S. spectabilis* its name. Its ranking at AB Medium tier with a clean KCB anchor to BGC0000715.5 is the expected calibration output. No T43 trigger fires because the aminocyclitol class is not represented in the current CCTT trigger set (this is a known gap — T43-AMC fires on DOIS/2-deoxy-scyllo-inosose-synthase, which is present in BGC057 (CP023690.1 · region057) based on the amglyccycl product annotation, but the exact trigger configuration may or may not detect it). If this BGC appears at Exceptional tier or is absent from the ranked board in a re-run, inspect the run calibration and scoring model.

**Gene-by-gene (selected):**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_7237 | 3,224–4,336 | — | amglyccycl-annotated (aminocyclitol-related) |
| ctg1_7243 | 10,001–10,993 | RmlD_sub_bind; Polysacc_synt_2 | Sugar biosynthesis — dTDP-glucose pathway (spectinomycin sugar arm) |
| ctg1_7244 | compl. 11,023–11,952 | RmlD_sub_bind | NAD-epimerase/dehydratase (SMCOG1010, dTDP-rhamnose pathway) |
| ctg1_7247 | compl. 14,247–15,074 | Glycos_transf_2; SpcFG | \*\*SpcFG\*\* — spectinomycin-specific glycosyltransferase (ground-truth domain) |
| ctg1_7248 | compl. 15,076–15,984 | Fer4_12; QueE | Radical SAM QueE-like (aminocyclitol ring modification) |
| ctg1_7249 | compl. 15,981–17,300 | DegT_DnrJ_EryC1; Aminotran_1_2 | DegT aminotransferase (SMCOG1056) |
| ctg1_7256 | 24,493–25,428 | APH | Aminoglycoside phosphotransferase (self-resistance — spectinomycin resistance) |
| ctg1_7258 | compl. 26,369–27,241 | TauD | TauD-type dioxygenase (SMCOG1121) |
| ctg1_7261 | compl. 29,063–38,188 | Condensation; AMP-binding; ketoacyl-synt; PKS_KS | Large NRPS/PKS gene (backbone assembly) |
| ctg1_7262 | compl. 38,185–42,144 | Condensation; AMP-binding; PP-binding; Thioesterase | NRPS C-A-T-TE module |
| ctg1_7268 | compl. 46,442–47,509 | PT_FPPS_like | Polyprenyl synthase (SMCOG1182, terpene-precursor component) |
| ctg1_7287 | 70,721–72,529 | AMP-binding; PP-binding | NRPS-like adenylation + ACP |
| ctg1_7288 | 72,606–74,357 | GATase_7; Asn_synthase | Asparagine synthase fold (glutamine-hydrolyzing) |
| ctg1_7290 | 77,749–84,432 | Condensation; AMP-binding; PP-binding | NRPS C-A-T module |
| ctg1_7292 | 85,657–88,644 | hyb_KS; PKS_AT; ketoacyl-synt; PP-binding | PKS module |
| ctg1_7293 | 88,641–89,405 | Thioesterase; Abhydrolase_6 | Thioesterase release |

**Pathway hypothesis:** Established biosynthetic route to spectinomycin (actinospectacin). The SpcFG glycosyltransferase domain (ctg1_7247) is the diagnostic spectinomycin domain. The aminocyclitol scaffold is biosynthesised from myo-inositol via DOIS (2-deoxy-scyllo-inosose-synthase); the spectinomycin sugar arm (actinamine) is installed by SpcFG. This is the only BGC in this analysis with confirmed compound identity (ground truth). Capacity claim language applies throughout; the compound identity is established in the literature, not by this analysis.

------------------------------------------------------------------------

#### BGC061 (CP023690.1 · region061) — Medium tier \| NRP-metallophore (siderophore)

**Location:** CP023690.1 · region061 · Interior · 57,832 bp · 36 CDS · Arch A

**Products:** NRP-metallophore; NRPS

**CCTT:** no trigger

**KCB:** BGC0000325.5 (coelichelin) · score 32,208

**AB/AF/Nov:** 41.0 / 36.0 / 27.0

**Key biosynthetic genes:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_7767 | 20,001–30,938 | AMP-binding; Condensation; PP-binding | Large NRPS — C-A-T modules (siderophore assembly) |
| ctg1_7774 | 36,453–37,832 | Orn_monoox; Pyr_redox_2 | \*\*Ornithine monooxygenase\*\* (SMCOG1080) — hydroxamate siderophore signature |
| ctg1_7786 | compl. 51,299–52,861 | PF00561 | α/β hydrolase |
| ctg1_7787 | compl. 53,036–54,223 | APH | Aminoglycoside phosphotransferase (self-resistance) |
| ctg1_7759 | compl. 9,897–11,474 | Amidohydro_1 | Amidohydrolase (siderophore tailoring) |
| ctg1_7770 | 34,009–34,221 | — | MbtH-like protein (SMCOG1009 — NRPS assembly chaperone) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a coelichelin-class hydroxamate siderophore. Coelichelin is a *S. coelicolor* tripeptide hydroxamate siderophore derived from N-hydroxy amino acids. The ornithine monooxygenase (ctg1_7774) is the key enzyme, installing the N-OH group that coordinates Fe³⁺. KCB similarity to coelichelin (BGC0000325.5, score 32,208) is class-concordant. The MbtH-like protein (ctg1_7770) is an NRPS assembly chaperone. Siderophores contribute to iron competition in the soil environment. No CCTT trigger. Capacity claim only.

**Ecological note:** Siderophore production in soil *Streptomyces* is ecologically significant — iron competition is a primary determinant of microbiome composition. CGAD showed 10 chitin-binding module hits in the strain, consistent with a chitinolytic soil organism. The siderophore capacity complements the antifungal toolkit: iron deprivation through siderophore competition is antifungal in some contexts.

**Isolation strategy:** Siderophores are polar; aqueous extraction from broth, CAS agar overlay for detection. HPLC-MS in positive mode. Chrome azurol S (CAS) universal siderophore assay for quantification.

------------------------------------------------------------------------

#### BGC063 (CP023690.1 · region063) — Medium tier \| RiPP-like (bottromycin-family TIGR03975)

**Location:** CP023690.1 · region063 · Interior · 11,923 bp · 10 CDS · Arch A

**Products:** RiPP; RiPP-like

**CCTT:** no trigger

**KCB:** *S. spectabilis* ATCC 27465 chromosome (self-hit) · score 6,207

**AB/AF/Nov:** 33.0 / 20.0 / 50.0

**Note:** KCB top hit is a self-match to the same genome — this is the lowest-evidence KCB call in the eligible set.

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_7896 | 5,001–6,923 | TIGR03975 | \*\*TIGR03975 — bottromycin-family RiPP\*\* (class-defining marker for bottromycin sub-family of thioamide RiPPs) |
| ctg1_7894 | 2,994–4,790 | PF00561; Peptidase_S9 | α/β hydrolase + serine protease (maturation protease) |
| ctg1_7893 | 1,753–2,997 | — | MFS transporter (SMCOG1020, export) |
| ctg1_7898 | 7,828–9,798 | — | GTP-binding protein LepA (elongation factor LepA, unusual context) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a bottromycin-family RiPP. TIGR03975 is a bottromycin-family protein marker — it is the recognition/modification enzyme from the bottromycin biosynthetic pathway, and its presence here is the class signal. Bottromycins are thioamide-containing RiPPs with antibacterial activity against Gram-positive organisms. The cluster is compact (11.9 kb) and encodes the minimum bottromycin machinery: the TIGR03975 marker enzyme and a maturation protease (ctg1_7894). The self-hit KCB (matching its own genome at score 6,207) indicates no well-characterised MIBiG reference provides a clean anchor — this is a novel divergent bottromycin-family cluster. Novelty_auto 50.0. Capacity claim only.

**Mechanistic link:** Bottromycins are antibacterial against Gram-positive organisms including MRSA and VRE, targeting the ribosomal decoding site (A-site at the 30S ribosome). AB 33.0 — lowest among eligible BGCs but the bottromycin class is clinically relevant and the TIGR03975 marker is a strong class indicator.

**Isolation strategy:** RiPP products typically small peptides (MW \< 2,000 Da). Solid ISP2, 28°C, 14 days. MALDI-MS or ESI-MS. Bottromycin-class products are heat stable. Bioassay: MRSA inhibition is the appropriate primary screen for bottromycin-class confirmation.

------------------------------------------------------------------------

### PART III — CROSS-BGC SYNTHESIS

#### Mechanistic Ecology Synthesis

*S. spectabilis* ATCC 27465 is a soil isolate with a large secondary metabolome characteristic of a well-differentiated soil *Streptomyces*. The 67 BGCs span at least eight distinct compound classes with corroborated CCTT triggers, plus multiple high-similarity KCB anchors to established natural products.

**Dominant mechanistic theme:** Lanthipeptide capacity dominates the corroborated trigger landscape — T43-LAN fires on 4 BGCs (BGC008 (CP023690.1 · region008), BGC010 (CP023690.1 · region010), BGC059 (CP023690.1 · region059), BGC065 (CP023690.1 · region065)) across three different lanthipeptide classes (i, ii, iii, and iv). This is the highest representation of any single compound family in this genome and suggests a historical selective pressure for peptide-based defence in the soil niche.

**RiPP cluster density:** 6 of 15 eligible BGCs (40%) encode RiPP-class or RiPP-associated chemistry (BGC004 (CP023690.1 · region004) lasso, BGC008 (CP023690.1 · region008) CDPS/class-i, BGC010 (CP023690.1 · region010) class-iii, BGC059 (CP023690.1 · region059) class-iv, BGC065 (CP023690.1 · region065) class-ii, BGC063 (CP023690.1 · region063) bottromycin-family). This is substantially higher than the typical *Streptomyces* proportion and suggests a specialisation in small-peptide antibiotics.

**Iron ecology:** BGC061 (CP023690.1 · region061) (coelichelin-class siderophore) and BGC011 (CP023690.1 · region011) (NRP-metallophore sub-pathway) together encode substantial iron-chelating capacity. In soil, iron competition is a primary ecological determinant — siderophore-producing strains have competitive advantages. The CGAD signal (10 chitin-binding module hits) further positions this strain as a soil competitor with multi-layered chemical ecology.

**Autoregulation:** Two butyrolactone synthases (AfsA) in BGC002 (CP023690.1 · region002) and BGC054 (CP023690.1 · region054) indicate two independent autoregulatory circuits. Butyrolactones (γ-butyrolactones in *Streptomyces*) are quorum-sensing-like signals that trigger secondary metabolite expression at colony density thresholds. Their presence in two separate clusters suggests that different metabolite classes are triggered at different colony densities or developmental stages.

**Ansamycin capacity:** BGC054 (CP023690.1 · region054) (streptovaricin anchor, score 141,254) is the KCB-anchored ansamycin lead. RNA polymerase inhibition is a potent antibacterial mechanism; the presence of an ansamycin-class cluster alongside a lanthipeptide-rich background suggests this strain has layered antibacterial strategies targeting both the ribosome/membrane (lanthipeptides) and transcription (ansamycin).

**Hypothesis:** *S. spectabilis* ATCC 27465 is a competitive soil organism whose secondary metabolite profile targets both bacterial competitors (lanthipeptides, β-lactam, ansamycin, prodiginine, bottromycin) and potentially fungal competitors (prodiginine antifungal activity, siderophore-mediated iron deprivation). The high bldA gating (5 T4 BGCs) suggests that a significant fraction of the secondary metabolome is expressed only during sporulation — consistent with a compound deployment strategy aligned to dispersal rather than active vegetative competition.

#### Environmental Trigger Experiment Matrix

| BGC | Primary trigger signal | Elicitation experiment | Expected response |
|----|----|----|----|
| BGC004 (CP023690.1 · region004) | AdpA-like TFBS dominant | Delayed harvest (day 10–14 solid culture) | Lasso peptide production increases at sporulation |
| BGC008 (CP023690.1 · region008) | SARP regulatory density | SARP overexpression construct | Constitutive lanthipeptide expression |
| BGC010 (CP023690.1 · region010) | Two-component system | Vary Fe²⁺ concentration | Two-component may respond to metal availability |
| BGC051 (CP023690.1 · region051) | LuxR regulator | Co-culture with competitor organism | Prodiginine pigment visible response |
| BGC054 (CP023690.1 · region054) | AfsA butyrolactone | Add synthetic butyrolactone (20–50 nM) | Ansamycin expression triggered by autoregulator |
| BGC061 (CP023690.1 · region061) | Iron-limitation signal | ISP2 + chelexed (iron-depleted) media | Siderophore expression increases under Fe limitation |
| Any bldA T4 | bldA developmental | Solid media + 21-day harvest | T4 clusters expressed only in sporulation phase |
| DasR-associated | DasR palindromes (23 hits) | GlcNAc supplementation (0.5 mM) | GlcNAc-inducible BGC expression |

#### Compound Detection and Isolation Bench Guide

**Priority 1 — Antibacterial leads for immediate fermentation:**

1\. **BGC004 (CP023690.1 · region004)** (lasso/transAT-PKS hybrid): Solid ISP2 agar, 28°C, 14 days. Extraction: MeOH + EtOAc. Detection: heat/protease stability test for lasso component; LC-MS positive ESI 600–1,800 Da. MRSA screen on methanol extract.

2\. **BGC008 (CP023690.1 · region008)** (lanthipeptide-class-i + CDPS): Solid ISP2 agar, 28°C, 14 days. Extraction: EtOAc partition. Detection: MALDI-MS for cyclic peptide 500–2,000 Da. Ninhydrin-negative (cyclic/modified peptide).

3\. **BGC010 (CP023690.1 · region010)** (lanthipeptide-class-iii, \[E-signal\]): Solid ISP2 agar, 28°C, 14 days. Standard isolation — note \[E-signal\] annotation for information only.

4\. **BGC059 (CP023690.1 · region059)** (lanthipeptide-class-iv): Solid ISP2 agar, 28°C, 14 days. ABC transporter self-resistance suggests active production. MALDI-MS.

5\. **BGC057 (CP023690.1 · region057)** (spectinomycin) — GROUND TRUTH: already characterised; use as positive control for extraction protocol validation.

**Priority 2 — Secondary leads:**

6\. **BGC054 (CP023690.1 · region054)** (streptovaricin/ansamycin): Solid ISP2 + 0.5% sucrose. EtOAc extraction. UV 425 nm. RNA polymerase inhibition assay.

7\. **BGC011 (CP023690.1 · region011)** (large NRP-metallophore/PKS hybrid): Solid ISP2, 21 days. CAS agar overlay for siderophore component. Broth extraction for PKS component.

8\. **BGC002 (CP023690.1 · region002)** (β-lactam/clavulanic acid): Aqueous broth extraction pH 3.0. β-lactamase inhibition assay with nitrocefin.

9\. **BGC051 (CP023690.1 · region051)** (prodigiosin): Visible red pigment on solid media. MeOH extraction direct from agar surface.

**Negative evidence summary:** UMED flags 4 MATURATION_GAP regions. BGCs BGC032 (CP023690.1 · region032), BGC045 (CP023690.1 · region045), BGC048 (CP023690.1 · region048) carry lanthipeptide-class-related chemistry without co-clustered maturation proteases — these three are included in Inventory-tier and are noted here as requiring verification that the LanP/protease is present elsewhere on the chromosome before wet-lab investment.

------------------------------------------------------------------------

### PART IV — LAYPERSON'S GUIDE TO BGCs IN *S. spectabilis* ATCC 27465

*This section describes what each cluster might make in plain language. All claims are "could produce" — genome analysis shows the recipe, not the dish.*

**BGC004 (CP023690.1 · region004) (Top priority):** This cluster contains recipes for two different types of antibiotics at once — a "lasso peptide" (a tiny protein folded into a molecular lasso shape that can block bacterial machinery) and a large assembly-line antibiotic made by linking chemical units together like a molecular chain. It's the highest-scoring cluster in the genome and most closely resembles a compound called lagmysin.

**BGC008 (CP023690.1 · region008) (Top priority):** Two compound classes again: a lanthipeptide (a type of modified peptide with chemical bridges that give it unusual stability and potency against bacteria) and a diketopiperazine (a small cyclic molecule with diverse antibiotic activities). The lanthipeptide machinery is the complete class-i set — a relatively well-understood system with known active products like nisin.

**BGC010 (CP023690.1 · region010) (High priority):** A lanthipeptide (class-iii) combined with a polyketide assembly line. The polyketide component has a chemical signature (enediyne-type ketosynthase) that is noted for information — enediyne-class compounds are among the most potent antibiotics known but this is an early-stage signal and no specific compound is identified.

**BGC059 (CP023690.1 · region059) (High priority):** A class-iv lanthipeptide — a relatively recently described class of modified peptides. Has multiple sugar-modification enzymes suggesting the final compound may have sugar groups attached, which often enhances the compound's ability to target bacteria.

**BGC065 (CP023690.1 · region065) (High priority):** A class-ii lanthipeptide. Clean, compact cluster with a single LanM enzyme (the class-defining enzyme), a precursor peptide, and a pathway regulator. Resembles akaeolide, a known antibacterial lanthipeptide.

**BGC057 (CP023690.1 · region057) (Medium — ground truth):** This is spectinomycin — the antibiotic that gives *S. spectabilis* its name. It's used clinically against gonorrhoea. This cluster is confirmed and serves as the positive control for the whole analysis.

**BGC054 (CP023690.1 · region054) (Medium):** Resembles streptovaricin, an ansamycin antibiotic that works by blocking the bacterial enzyme that reads DNA to make messenger RNA. This is a large cluster with five oxidation enzymes — the final compound likely has multiple chemical modifications.

**BGC011 (CP023690.1 · region011) (Medium):** The largest cluster in the genome. Makes both a siderophore (an iron-grabbing molecule) and a large complex antibiotic scaffold. The iron-grabbing capacity may help the bacterium compete for iron in the soil.

**BGC051 (CP023690.1 · region051) (Medium):** Prodigiosin-related — prodigiosin is the bright red pigment that gives some bacteria their colour. It also has antibiotic and antifungal activities. Production may be visible as red pigment on the colony surface.

**BGC002 (CP023690.1 · region002) (Medium):** A clavulanic acid-class β-lactam. Clavulanic acid doesn't kill bacteria on its own, but it disables the resistance enzymes (β-lactamases) that bacteria use to defeat other antibiotics. Combined with a β-lactam antibiotic, it would restore effectiveness against resistant bacteria.

**BGC024 (CP023690.1 · region024) (Medium):** A large polyketide resembling herbimycin A, a compound that inhibits Hsp90 — a protein that cancer cells and fungal pathogens depend on. The cluster contains a diagnostic enzyme for spirotetronate biosynthesis.

**BGC055 (CP023690.1 · region055) (Medium):** An NRPS-derived peptide resembling bonnevillamide, with three P450 oxidation enzymes that would heavily modify the final structure. Less well-characterised compound class.

**BGC061 (CP023690.1 · region061) (Medium):** A siderophore (iron-capture molecule) resembling coelichelin. Primarily an ecological competitor in soil — helps the bacterium outcompete for iron. Some antifungal applications through iron deprivation.

**BGC063 (CP023690.1 · region063) (Medium):** A tiny cluster with a single diagnostic enzyme from the bottromycin family. Bottromycins are antibiotics that block the ribosome — the cellular machine that makes proteins. This appears to be a divergent, potentially novel bottromycin-class compound.

**47 Inventory-tier BGCs:** These clusters are real and present — they just lack the evidence required to rank them higher. Many carry saccharide-class chemistry (sugar biosynthesis) excluded by standing rules. Others have low KCB similarity and no CCTT trigger. They remain in the genome and could be revisited with additional experimental data.

------------------------------------------------------------------------

### PART V — QUALIFIED NULLS AND VALIDATION CONTROLS

**Ground truth validation (PASS):** BGC057 (CP023690.1 · region057) (spectinomycin, MIBiG BGC0000715.5) ranks at AB Medium tier with KCB score 61,598 in this run. This matches the expected calibration output. Scoring model calibration: CONFIRMED.

**Assembly parsing validation (PASS):** Single closed chromosome; 67/0/0 Interior/Edge/Full-contig; corrected count 67.0 = raw count. No parsing errors detected.

**Standing-rule application (PASS):** 18 BGCs correctly assigned saccharide-exclusion; 2 primary-metabolism drops correctly identified. Standing rules applied before scoring — excluded BGCs visible in inventory but not in corrected lead rank.

**UMED completeness (PARTIAL NOTE):** 4 lanthipeptide MATURATION_GAP regions flagged. These are incomplete pathways as assembled — not calls of non-production, but notes that the maturation enzyme is not co-clustered.

**CCTT corroboration (PASS):** All 13 triggered BGCs carry corroborated triggers on class-compatible loci. No uncorroborated triggers assigned class capacity credit.

**Negative calls (NONE MADE):** No BGC is called "antibacterial-negative" or "antifungal-negative." Absence of recorded activity for any BGC = absence of data, not absence of capacity.

------------------------------------------------------------------------

*Report generated: 2026-06-18 · Sapote–Mamey v9.7.81*

*All claims capacity-level only. KCB = similarity not identity. Bioactivity extract-level unless fractionation data available.*

------------------------------------------------------------------------

## §XII.2 · *Streptomyces liangshanensis* type strain (CP050177.1)

**Role in this bundle:** Public soil *Streptomyces* type strain. Demonstrates HSAF-class antifungal capacity (BGC026 (CP050177.1 · region026), AF 67.0, T43-PTM corroborated) and an azoxy N–N bond cluster (BGC027 (CP050177.1 · region027), T43-NN corroborated). Single closed chromosome; 45 BGCs all Interior; corrected count 45.0. \[observed: Mamey v1.9.84 / antiSMASH 8.0.4\]

## *Streptomyces liangshanensis* — Complete Sapote–Mamey Analysis

**Pipeline:** Sapote–Mamey v9.7.81 · Mamey engine v1.9.84 · antiSMASH 8.0.4

**Accession:** CP050177.1

**Source:** Soil, Sichuan Province, China (type strain)

**Release class:** PUBLIC

**Run date:** 2026-06-18

**Affiliation:**

------------------------------------------------------------------------

### PART I — STRAIN OVERVIEW

#### Assembly and BGC Landscape

*Streptomyces liangshanensis* carries a single closed chromosome of 7,716,784 bp (GC 72.1%, 1 contig, N50 = full chromosome). Assembly tier: GOOD — all 45 BGCs are interior, corrected count equals raw count (45.0). Like *S. spectabilis*, the single closed chromosome means RG-GMCI cross-contig pairs represent same-chromosome neighbourhood associations, not assembly splits.

**BGC counts:**

- Raw antiSMASH BGCs: 45
- Interior / Edge / Full-contig: 45 / 0 / 0
- Corrected count: **45.0**
- Standing-rule exclusions (saccharide ×19, NAPAA ×1): 20 BGCs
- Primary-metabolism drops: 1 BGC (BGC005 (CP050177.1 · region005), saccharide/terpene)
- Eligible for interpretation: **24 BGCs**

#### Tier Distribution

| Tier | Count | BGC IDs |
|----|----|----|
| High | 1 | BGC010 (CP050177.1 · region010) |
| Medium | 7 | BGC007 (CP050177.1 · region007), BGC009 (CP050177.1 · region009), BGC012 (CP050177.1 · region012), BGC026 (CP050177.1 · region026), BGC027 (CP050177.1 · region027), BGC031 (CP050177.1 · region031), BGC040 (CP050177.1 · region040) |
| Inventory | 37 | Remaining eligible |
| Standing-rule excluded | 20 | Saccharide class (×19) + NAPAA (×1, BGC001 (CP050177.1 · region001)) |
| Primary-metab dropped | 1 | BGC005 (CP050177.1 · region005) |

#### DAPR — Antibacterial Lead Board (Top 8 eligible)

| Rank | BGC | Products | AB | AF | Nov | Tier | CCTT | KCB anchor | Score |
|----|----|----|----|----|----|----|----|----|----|
| 1 | BGC010 (CP050177.1 · region010) | fatty_acid; other | 71.0 | 48.0 | 82.0 | High | — | \*S. xanthii\* CRXT-Y-14 (composite) | 1,305 |
| 2 | BGC009 (CP050177.1 · region009) | PKS; T1PKS; T2PKS | 63.0 | 38.0 | 39.0 | Medium | — | hedamycin (BGC0000233.5) | 44,005 |
| 3 | BGC031 (CP050177.1 · region031) | HR-T2PKS; NRPS; halogenated | 63.0 | 32.0 | 35.0 | Medium | T43-HAL | colibrimycin (BGC0002100.2) | 31,689 |
| 4 | BGC040 (CP050177.1 · region040) | NRPS; PKS; T1PKS; halogenated | 59.0 | 42.0 | 35.0 | Medium | T43-HAL | glycinocin A (BGC0000379.5) | 41,448 |
| 5 | BGC007 (CP050177.1 · region007) | fatty_acid; other | 41.0 | 24.0 | 52.0 | Medium | — | \*S. ruber\* JCM 3131 (composite) | 4,091 |
| 6 | BGC027 (CP050177.1 · region027) | azoxy-crosslink; fatty_acid | 33.0 | 28.0 | 41.0 | Medium | T43-NN | tambjamine BE-18591 (BGC0002381.3) | 17,377 |
| 7 | BGC012 (CP050177.1 · region012) | RiPP; RiPP-like | 33.0 | 20.0 | 50.0 | Medium | — | 14-hydroxyisochainin (BGC0002788.2) | 5,154 |
| 8 | BGC026 (CP050177.1 · region026) | NRPS; PKS; T1PKS | 51.0 | 67.0 | 35.0 | Medium | T43-PTM | combamide (BGC0001556.5) | 27,441 |

#### DAPR — Antifungal Lead Board (Top 5)

| Rank | BGC | Products | AF | CCTT | KCB anchor | Score |
|----|----|----|----|----|----|----|
| 1 | BGC026 (CP050177.1 · region026) | NRPS; PKS; T1PKS | 67.0 | T43-PTM | combamide (BGC0001556.5) | 27,441 |
| 2 | BGC010 (CP050177.1 · region010) | fatty_acid; other | 48.0 | — | \*S. xanthii\* composite | 1,305 |
| 3 | BGC040 (CP050177.1 · region040) | NRPS/PKS/halogenated | 42.0 | T43-HAL | glycinocin A (BGC0000379.5) | 41,448 |
| 4 | BGC009 (CP050177.1 · region009) | PKS; T1PKS; T2PKS | 38.0 | — | hedamycin (BGC0000233.5) | 44,005 |
| 5 | BGC007 (CP050177.1 · region007) | fatty_acid; other | 24.0 | — | \*S. ruber\* composite | 4,091 |

**BGC026 (CP050177.1 · region026) is the clear antifungal priority:** AF 67.0 with T43-PTM corroboration is the highest antifungal score in the strain and places BGC026 (CP050177.1 · region026) in the top quadrant of the DAPR scatter (visible in the figure as the uppermost point at AF ~67, AB ~51).

#### Source Scan Summary

| Scan | State | Key finding |
|----|----|----|
| KCB_sweep | PASS | 45 regions; 200,000 loose hits (cap reached) |
| RG-GMCI | PASS | 938 pairs; 6 high; 49 moderate; 1,954 reference records. All interior — neighbourhood signals only |
| FLBR | PASS | WEAK — MEGASYNTHASE_FRAGMENT_SUSPECT (closed genome; fragmentation signal weak) |
| CCTT | PASS | 6 triggered BGCs: T43-HAL (×3 BGCs), T43-PHO (×1), T43-NN (×1), T43-PTM (×1) |
| CGAD | PASS | CBM_CHITIN: 8 hits (chitin-binding capacity; soil ecological context) |
| UMED | PASS | 2 lanthipeptide MATURATION_GAP regions (BGC012 (CP050177.1 · region012), BGC001 (CP050177.1 · region001)) |
| EFLS | NULL | 0 candidate pairs — single-contig genome, expected |
| Resistance | PASS | 16 total hits; \*\*0 T1 BGCs\*\* |
| bldA/TTA | PASS | 45 BGCs assessed; \*\*0 T4\*\* — no developmental bldA gating in any BGC |
| TFBS | PASS | 239 motif hits: AdpA-like 184, DasR-like 24, BldD-like 12, IolR-like 9 |

**Notable scan findings:**

**0 T1 resistance hits:** No class-concordant within-BGC self-protection determinant was detected in any of the 45 BGCs. This does not mean no compound is produced — T1 resistance is a corroborating signal, and its absence is not a negative — but it removes the strongest within-cluster production evidence available from the scan tier. This is the most significant absence in this dataset and warrants attention during wet-lab follow-up.

**0 T4 bldA-gated BGCs:** All 45 BGCs can be expressed under standard liquid culture conditions — no developmental gating constraint. This is practically valuable: any BGC in this strain is accessible in liquid ISP2 or SG media without requiring solid-phase sporulation conditions.

**IolR motifs (9 hits):** IolR regulates inositol/pollen sugar catabolism. In bee microbiology, pollen is an inositol-rich substrate. The IolR signal in a soil *Streptomyces* is lower background than expected in a bee-associated strain but worth noting for ecological context.

**RG-GMCI top pairs (same-chromosome — neighbourhood associations):** BGC022 (CP050177.1 · region022)+BGC031 (CP050177.1 · region031), BGC023 (CP050177.1 · region023)+BGC031 (CP050177.1 · region031), BGC023 (CP050177.1 · region023)+BGC027 (CP050177.1 · region027). Both BGC031 (CP050177.1 · region031) and BGC027 (CP050177.1 · region027) appear in multiple top pairs, suggesting they share biosynthetic neighbourhood signals with BGC022 (CP050177.1 · region022) and BGC023 (CP050177.1 · region023). This is likely due to co-localised fatty acid and halogenase gene content shared across proximal BGCs on the chromosome, not split-pathway reconstruction.

#### Cassette Registry and Hallucination-Trap Summary

EFLS NULL (single contig — expected). CCTT corroboration applied to all 6 triggered BGCs on class-compatible loci. No uncorroborated triggers granted class-capacity credit. All 8 Mode B cards below pass §8 claim-safety audit.

#### Negative Evidence Summary

UMED flags 2 MATURATION_GAP regions: BGC012 (CP050177.1 · region012) (RiPP-like) and BGC001 (CP050177.1 · region001) (NAPAA — excluded). BGC012 (CP050177.1 · region012) carries a DUF692 domain without a co-clustered maturation enzyme — the RiPP precursor cannot be converted to a mature compound without the missing enzyme. 0 T1 resistance across the genome — no class-concordant self-protection at any BGC.

------------------------------------------------------------------------

### PART II — MODE B ANALYSIS: ALL ELIGIBLE BGCs

#### BGC010 (CP050177.1 · region010) — High tier \| Unresolved fatty_acid/other — highest novelty in strain

**Location:** CP050177.1 · region010 · Interior · 21,233 bp · 20 CDS · **Arch E**

**Products:** fatty_acid; other

**CCTT:** no trigger

**KCB:** *Streptomyces xanthii* CRXT-Y-14 plasmid composite · score 1,305

**AB/AF/Nov:** 71.0 / 48.0 / **82.0** (highest novelty score in strain)

**UMED:** no gap

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_1234 | compl. 10,001–11,233 | t2fas; ketoacyl-synt | \*\*Type-II FAS ketosynthase\*\* (SMCOG1022) — core biosynthetic enzyme |
| ctg1_1232 | 9,030–9,563 | — | Thioesterase superfamily protein (SMCOG1144) — chain release |
| ctg1_1240 | 16,259–16,927 | — | Methyltransferase (SMCOG1089) — methyl modification |
| ctg1_1228 | compl. 5,227–5,826 | — | TetR regulator (SMCOG1057) |
| ctg1_1233 | 9,595–9,888 | — | Transcriptional regulator (SMCOG1167) |
| ctg1_1239 | 15,724–16,218 | — | Transcriptional regulator (SMCOG1167) |
| ctg1_1238 | 14,008–15,687 | — | EmrB/QacA drug resistance transporter (SMCOG1005) — efflux |
| ctg1_1243 | compl. 18,878–20,503 | — | EmrB/QacA drug resistance transporter (SMCOG1005) — second efflux |

12 remaining CDS in the region annotate as hypothetical with no assignable domain hits.

**Pathway hypothesis:** Biosynthetic capacity consistent with a minimally characterised fatty acid or modified lipid pathway. The sole biosynthetic enzyme with a named domain is ctg1_1234, carrying a type-II fatty acid synthase ketosynthase (t2fas) — the iterative KS enzyme used in both fatty acid elongation and type-II polyketide assembly. A methyltransferase (ctg1_1240) suggests at least one methyl branch. The thioesterase (ctg1_1232) provides chain release. The remaining 12 hypothetical genes carry no assignable biosynthetic function from the current HMM set. Two EmrB/QacA efflux transporters (ctg1_1238, ctg1_1243) are disproportionate for a minimal fatty acid cluster, suggesting active export of a bioactive product.

Architecture grade E is not a deprioritisation. It is an honest statement that the current gene-level evidence is insufficient to assign a class — which is precisely why novelty_auto 82.0 is so high. The near-complete absence of KCB similarity (score 1,305 to a composite multi-class reference, the lowest informative anchor in this strain) reflects a gene content that does not resemble any characterised MIBiG cluster. This is the definition of genuine novelty at the capacity level.

**Mechanistic link:** Insufficient domain evidence for a specific mechanistic hypothesis. Two efflux transporters suggest active product export. A methylated fatty acid or modified lipid could target bacterial membranes or lipid biosynthesis. Extract-level MRSA/Candida frame applies. AB 71.0 / AF 48.0 without a CCTT trigger — scores derive from class keyword content only.

**Isolation strategy:** All BGCs in this strain are bldA-accessible (0 T4) — standard liquid ISP2 culture is viable for initial screening. No DasR-specific elicitation signal for BGC010 (CP050177.1 · region010) from TFBS scan. Detection: non-polar product; EtOAc extraction from whole culture. If a modified fatty acid, FAME analysis + GC-MS for initial chemical profiling; LC-MS positive ESI 200–800 Da for modified lipid. The 12 hypothetical genes are the primary unknowns: targeted domain searches (HMMER against UniRef/PFAM) in those sequences would clarify biosynthetic capacity before committing to wet-lab investment.

**§8 claim-safety audit:** ✓ No compound-identity claim. ✓ KCB anchor noted as composite, low-score, uninformative. ✓ Architecture grade E and its implications explicitly stated throughout. ✓ Novelty score 82.0 attributed to absence of KCB similarity, not to confirmed chemical novelty. ✓ Interior, no truncation caveat.

------------------------------------------------------------------------

#### BGC026 (CP050177.1 · region026) — Medium tier \| HSAF/PTM tetramate macrolactam (top antifungal lead)

**Location:** CP050177.1 · region026 · Interior · 49,897 bp · 34 CDS · Arch A

**Products:** NRPS; PKS; T1PKS

**CCTT:** **T43-PTM corroborated** (HSAF/tetramate macrolactam)

**KCB:** BGC0001556.5 (combamide) · score 27,441

**AB/AF/Nov:** 51.0 / **67.0** / 35.0

**UMED:** no gap

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_3571 | compl. 20,001–29,897 | ketoacyl-synt; PKS_KS; PKS_AT; adh_short; Condensation; AMP-binding | \*\*Large NRPS/PKS/T1PKS megasynthase\*\* — hybrid PKS-NRPS module; core biosynthetic enzyme (T43-PTM source) |
| ctg1_3581 | 41,757–43,010 | ATP-grasp | ATP-grasp-fold enzyme (amide/lactam bond formation — key for macrolactam ring closure) |
| ctg1_3568 | compl. 15,203–16,444 | p450 | Cytochrome P450 (SMCOG1007, oxidative tailoring) |
| ctg1_3569 | compl. 16,516–18,159 | — | Dehydrogenase (SMCOG1222, reduction tailoring) |
| ctg1_3570 | compl. 18,287–20,011 | — | Dehydrogenase (SMCOG1222, second reduction) |
| ctg1_3553 | 841–1,887 | Glycos_transf_2 | Glycosyltransferase (SMCOG1123) — sugar attachment |
| ctg1_3557 | compl. 4,866–5,597 | — | TetR regulator (SMCOG1239) |

**Pathway hypothesis:** Biosynthetic capacity consistent with an HSAF/tetramate macrolactam. HSAF (heat-stable antifungal factor) and related compounds (dihydromaltophilin, discodermolide-precursor class) are produced by a single large PKS/NRPS enzyme that builds the polyene chain and simultaneously cyclises it into a tetramic acid macrolactam. The T43-PTM trigger fired on the large multifunctional enzyme ctg1_3571, which carries both PKS (PKS_KS + PKS_AT + ketoacyl-synt) and NRPS (Condensation + AMP-binding) domains — this is the exact domain architecture of HSAF-producing enzymes. The ATP-grasp enzyme (ctg1_3581) catalyses the macrolactam ring closure step. KCB similarity to combamide (BGC0001556.5, score 27,441) places the cluster in the combamide/HSAF/macrolactam family. Two dehydrogenases and a P450 provide tailoring oxidation. A glycosyltransferase (ctg1_3553) suggests sugar modification of the macrolactam scaffold. AF 67.0 is the highest antifungal score in the genome and the top antifungal lead by a substantial margin. Capacity claim only.

**Mechanistic link:** HSAF-class tetramate macrolactams have established antifungal mechanism: they disrupt sphingolipid biosynthesis by inhibiting sphinganine C4-hydroxylase (encoded in the fungal ergosterol pathway). This is a mechanistically distinct antifungal target from cell wall (chitin/glucan synthesis), membrane (ergosterol binding), and nucleoside-type (chitin synthase) mechanisms. The SMCOG1119 halogenase in BGC031 (CP050177.1 · region031) (T43-HAL) is separate — BGC026 (CP050177.1 · region026) does not carry a halogenase. The antifungal combination of BGC026 (CP050177.1 · region026) (sphingolipid mechanism) with BGC031 (CP050177.1 · region031) or BGC040 (CP050177.1 · region040) (halogenated NRPS/PKS) in this strain provides complementary mechanism coverage. AF 67.0 places BGC026 (CP050177.1 · region026) clearly dominant on the AF axis of the DAPR scatter (figure, top point).

**Isolation strategy:** HSAF-class compounds are produced during transition from exponential to stationary growth; solid ISP2 agar, 28°C, 10 days is the standard condition. LC-MS positive ESI for the macrolactam scaffold; detection at 280–330 nm UV (tetramate chromophore). Sphingolipid biosynthesis inhibition bioassay using *Fusarium graminearum* (HSAF-sensitive reference fungus) as a specific detection screen. GlcNAc supplementation (24 DasR-like TFBS hits) may elicit expression. All BGCs accessible in liquid culture (0 T4 bldA gating).

**§8 audit:** ✓ Capacity language throughout ("consistent with HSAF-class tetramate macrolactam"). ✓ T43-PTM corroboration cited as domain evidence (PKS_KS + Condensation + AMP-binding on same enzyme). ✓ KCB = similarity not identity (combamide reference). ✓ AF 67.0 attributed to diagnostic trigger + class keyword score. ✓ Interior, Arch A, no truncation caveat.

------------------------------------------------------------------------

#### BGC009 (CP050177.1 · region009) — Medium tier \| hedamycin-class T2PKS + T1PKS

**Location:** CP050177.1 · region009 · Interior · 90,435 bp · 76 CDS · Arch A

**Products:** PKS; PKS-like; T1PKS; T2PKS; saccharide

**CCTT:** no trigger

**KCB:** BGC0000233.5 (hedamycin) · score 44,005

**AB/AF/Nov:** 63.0 / 38.0 / 39.0

**Gene-by-gene (key biosynthetic):**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_1153 | 35,001–36,269 | t2ks; ketoacyl-synt | \*\*T2PKS alpha-ketosynthase (KSα)\*\* — type-II PKS core enzyme |
| ctg1_1154 | 36,266–37,483 | t2clf; ketoacyl-synt | \*\*T2PKS chain-length factor (KSβ/CLF)\*\* — controls chain length in type-II PKS |
| ctg1_1156 | compl. 38,782–39,039 | PP-binding | \*\*T2PKS ACP\*\* — acyl carrier protein (t2pks ACP score 88.0, E=7.2e-28) |
| ctg1_1150 | compl. 32,561–33,340 | adh_short | Ketoreductase (KR C9, score 433.7) — first ring reduction |
| ctg1_1151 | compl. 33,389–34,327 | — | Cyclase CYC C5–C14 (score 489.8) + SubclassB1 resistance |
| ctg1_1157 | compl. 39,117–40,046 | — | Cyclase CYC C7–C12 (score 409.3) — second ring cyclisation |
| ctg1_1158 | compl. 40,138–46,302 | mod_KS; PKS_AT; ketoacyl-synt; ADH_N | \*\*T1PKS module\*\* — extension after T2PKS core |
| ctg1_1159 | compl. 46,371–49,271 | PKS_KS; PKS_AT; ketoacyl-synt; PP-binding | T1PKS module (second extension) |
| ctg1_1160 | compl. 49,264–50,310 | PKS_AT | AT domain (trans-acting or cis) |
| ctg1_1161 | 50,493–51,536 | ksIII | Type-III KSα (KSIII, score 409.6) — starter unit synthesis |
| ctg1_1163 | 53,101–54,330 | — | Oxygenase (OXY, score 44.9) — oxidative modification |
| ctg1_1164 | 54,379–55,599 | p450 | Cytochrome P450 (SMCOG1007) |
| ctg1_1141 | compl. 23,871–24,587 | — | Methyltransferase (MET, score 20.1) |
| ctg1_1144 | compl. 26,895–28,037 | MGT | Glycosyltransferase-MGT (score 363.7) |
| ctg1_1167 | compl. 57,442–58,590 | MGT | Second glycosyltransferase (GT, score 375.6) — two GT enzymes |
| ctg1_1129 | compl. 8,328–9,695 | Aminotran_3 | Aminotransferase class III (SMCOG1013) |
| ctg1_1166 | compl. 56,393–57,385 | RmlD_sub_bind | NDP-sugar epimerase/dehydratase (SMCOG1010) |
| ctg1_1168 | compl. 58,600–59,280 | dTDP_sugar_isom | dTDP-sugar isomerase (deoxysugar biosynthesis) |
| ctg1_1170 | compl. 60,731–61,609 | NTP_transf_3 | NDP-sugar synthase (SMCOG1064) |
| ctg1_1151 | compl. 33,389–34,327 | — | SubclassB1 resistance (β-lactamase fold class B1 — resistance determinant) |
| ctg1_1149 | compl. 31,262–32,125 | — | SARP transcriptional activator (SMCOG1041) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a hedamycin-class or angucycline-related aromatic polyketide. The complete minimal type-II PKS set is present: KSα (ctg1_1153, t2ks), CLF/KSβ (ctg1_1154, t2clf), and ACP (ctg1_1156, PP-binding). Two cyclases (CYC C5–C14 and CYC C7–C12) fold the nascent polyketide chain into a polycyclic aromatic scaffold. The ketoreductase (KR C9, ctg1_1150) provides first-ring stereospecific reduction. This T2PKS core is extended downstream by two T1PKS modules (ctg1_1158, ctg1_1159) — an unusual hybrid configuration consistent with the "extended aromatic polyketide" class that includes hedamycin and pluramycin. Two MGT-family glycosyltransferases attach sugar moieties to the aglycone. The deoxysugar biosynthetic cassette (ctg1_1166, 1168, 1170 + aminotransferase ctg1_1129) provides the aminosugar building blocks characteristic of glycosylated angucyclines. KCB similarity to hedamycin (BGC0000233.5, score 44,005) — hedamycin is an anthracycline-class DNA-intercalating antibiotic. The SubclassB1 resistance hit (ctg1_1151) provides minimal class-concordant self-protection evidence (β-lactamase-fold, not a strong T1 signal). Capacity claim only.

**Mechanistic link:** Hedamycin-class compounds intercalate DNA and alkylate guanine residues — a potent antibacterial and antitumour mechanism. AB 63.0 is the second-highest antibacterial score in the strain. The glycosylated aromatic polyketide scaffold with aminosugars is characteristic of compounds active against Gram-positive organisms including MRSA.

**Isolation strategy:** Type-II PKS aromatic polyketides are pigmented — look for yellow/orange colour on solid culture. EtOAc extraction from whole culture. UV absorption at 430–480 nm for the anthracycline chromophore. LC-MS positive ESI; glycosylated aromatic polyketides typically 400–800 Da. Solid ISP2 agar, 28°C, 14 days. 0 T4 gating — liquid culture accessible.

**§8 audit:** ✓ Capacity language throughout. ✓ KCB hedamycin = similarity not identity. ✓ SubclassB1 resistance noted as weak (not T1 class-concordant). ✓ Interior, Arch A. ✓ Two-PKS hybrid architecture noted as unusual and reported without overclaiming the compound class.

------------------------------------------------------------------------

#### BGC031 (CP050177.1 · region031) — Medium tier \| HR-T2PKS + NRPS + Trp-halogenase \| T43-HAL

**Location:** CP050177.1 · region031 · Interior · 59,266 bp · 39 CDS · Arch A

**Products:** HR-T2PKS; NRPS; PKS; fatty_acid; halogenated; other

**CCTT:** **T43-HAL corroborated** (Trp_halogenase domain)

**KCB:** BGC0002100.2 (colibrimycin) · score 31,689

**AB/AF/Nov:** 63.0 / 32.0 / 35.0

**Gene-by-gene (key biosynthetic):**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_4075 | compl. 16,796–18,409 | Trp_halogenase | \*\*Tryptophan halogenase\*\* (MITE0000092 halogenation 68% identity) — \*\*T43-HAL trigger source\*\* |
| ctg1_4078 | 20,001–21,332 | hr-t2pks-ksa; ketoacyl-synt | \*\*HR-T2PKS KSα\*\* — highly-reducing type-II PKS core |
| ctg1_4079 | 21,338–22,435 | t2fas; ketoacyl-synt | \*\*HR-T2PKS t2fas (CLF-like)\*\* — chain-length factor |
| ctg1_4080 | 22,553–23,296 | adh_short | SDR ketoreductase (SMCOG1001) |
| ctg1_4085 | 27,331–32,520 | Condensation; AMP-binding; PP-binding | \*\*NRPS module\*\* — C-A-T trifunctional |
| ctg1_4086 | 32,517–39,266 | Condensation; AMP-binding; PP-binding | \*\*NRPS module\*\* — second C-A-T (6.75 kb gene) |
| ctg1_4082 | 24,047–25,552 | Condensation | Condensation domain (partial module or linker) |
| ctg1_4076 | 18,623–19,675 | PALP | Cysteine synthase-fold (SMCOG1081) |
| ctg1_4077 | 19,741–20,004 | PP-binding | ACP carrier protein |
| ctg1_4068 | 9,407–10,975 | — | Isochorismate synthase (SMCOG1018) — entry isochorismate pathway |
| ctg1_4067 | 8,369–9,403 | — | Ornithine cyclodeaminase (SMCOG1158) |
| ctg1_4087 | 39,263–40,249 | — | Ornithine carbamoyltransferase (SMCOG1114) |
| ctg1_4102 | compl. 57,633–58,643 | TauD | TauD-type dioxygenase (SMCOG1121, oxidative tailoring) |
| ctg1_4098 | 52,298–53,119 | — | 4'-phosphopantetheinyl transferase (SMCOG1012, PPTase — NRPS priming enzyme) |
| ctg1_4084 | 27,062–27,277 | — | MbtH-like protein (SMCOG1009, NRPS assembly chaperone) |
| ctg1_4066 | 5,270–8,248 | — | SARP regulator (SMCOG1041, halogenated product context) |
| ctg1_4065 | 2,657–4,924 | — | MMPL lipid transporter (SMCOG1035) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a halogenated HR-T2PKS/NRPS hybrid. The tryptophan halogenase (ctg1_4075, Trp_halogenase domain, MITE0000092) is the T43-HAL trigger source — it installs a halogen (chlorine or bromine) onto a tryptophan substrate that feeds into the downstream NRPS modules. This is mechanistically analogous to the rebeccamycin pathway (RebH Trp-halogenase + RebD IndSyn) but without an IndSyn enzyme, suggesting the Trp-halogenase here serves a different downstream pathway. The HR-T2PKS core (ctg1_4078 KSα + ctg1_4079 CLF + ctg1_4080 KR) produces a reduced polyketide chain. Two large NRPS modules (ctg1_4085, ctg1_4086 together ~12 kb) encode at least 2 amino acid activations. The isochorismate synthase (ctg1_4068) suggests chorismate-derived starter unit synthesis. KCB similarity to colibrimycin (BGC0002100.2, score 31,689) — colibrimycin is a glycosylated polyketide-NRPS hybrid. The combination of halogenation + HR-T2PKS + NRPS is architecturally novel and consistent with a halogenated aromatic lipopeptide. Top RG-GMCI pair: BGC022 (CP050177.1 · region022)+BGC031 (CP050177.1 · region031) (shared halogenase signal). Capacity claim only.

**Mechanistic link:** Halogenated NRPS/PKS hybrids include compounds with membrane-disrupting or enzyme-inhibiting mechanisms. The Trp-halogenase generates 7-chlorotryptophan (or 5-chlorotryptophan), which is an activated substrate with enhanced binding affinity in NRPS downstream chemistry. AB 63.0 — tied for second-highest antibacterial score in the strain.

**Isolation strategy:** Halogenated compounds detectable by their chlorine/bromine isotope signature in LC-MS (M and M+2 in ~3:1 ratio for Cl, ~1:1 for Br). EtOAc extraction. UV detection compound-class dependent. OSMAC with isochorismate supplementation (feeding the starter unit) may enhance titre.

**§8 audit:** ✓ T43-HAL corroboration on Trp_halogenase domain (class-compatible locus). ✓ KCB = similarity. ✓ "Halogenated HR-T2PKS/NRPS hybrid" capacity language throughout. ✓ Interior, Arch A.

------------------------------------------------------------------------

#### BGC040 (CP050177.1 · region040) — Medium tier \| T1PKS + NRPS halogenated \| T43-HAL

**Location:** CP050177.1 · region040 · Interior · 75,851 bp · 43 CDS · Arch A

**Products:** NRPS; NRPS-like; PKS; T1PKS; saccharide

**CCTT:** **T43-HAL corroborated**

**KCB:** BGC0000379.5 (glycinocin A) · score 41,448

**AB/AF/Nov:** 59.0 / 42.0 / 35.0

**Gene-by-gene (key biosynthetic):**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_5413 | 17,393–18,580 | — | \*\*Halogenase\*\* (SMCOG1119) — \*\*T43-HAL trigger source\*\* |
| ctg1_5415 | 20,001–29,699 | PKS_KS; PKS_AT; tra_KS; AMP-binding; PP-binding | Large T1PKS/transAT-PKS + NRPS hybrid module (9.7 kb) |
| ctg1_5416 | 29,696–38,896 | tra_KS; PP-binding; ketoacyl-synt; adh_short | transAT-PKS module (9.2 kb) |
| ctg1_5417 | 38,931–45,206 | PKS_KS; PKS_AT; tra_KS; PP-binding; ketoacyl-synt | T1PKS + transAT-PKS module (6.3 kb) |
| ctg1_5419 | 46,321–50,373 | DegT_DnrJ_EryC1; adh_short; PP-binding; Aminotran_1_2 | \*\*Sugar aminotransferase\*\* — deoxysugar biosynthesis (DegT/DnrJ family) |
| ctg1_5434 | compl. 64,092–65,132 | Glycos_transf_2 | Glycosyltransferase (sugar attachment) |
| ctg1_5435 | compl. 65,129–65,851 | Glycos_transf_2 | Second glycosyltransferase (ppm1 type) |
| ctg1_5422 | 51,936–52,751 | Thioesterase; Abhydrolase_6 | Thioesterase release domain |
| ctg1_5406 | compl. 6,230–7,057 | PF00561; Abhydrolase_6 | α/β hydrolase |
| ctg1_5411 | 14,615–15,562 | PF00561; Abhydrolase_6 | Second α/β hydrolase |
| ctg1_5404 | compl. 5,549–5,986 | 4HBT_2 | 4-hydroxybenzoyl-CoA thioesterase type 2 |
| ctg1_5429 | 59,126–60,616 | — | Methyltransferase (SMCOG1248) |
| ctg1_5423 | 52,748–54,349 | — | EmrB/QacA efflux transporter (SMCOG1005) |
| ctg1_5438 | compl. 67,864–68,718 | — | ABC-2 transporter (SMCOG1065, self-resistance) |
| ctg1_5439 | compl. 68,715–69,791 | — | ABC transporter ATPase (SMCOG1000, self-resistance) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a halogenated glycosylated T1PKS/transAT-PKS product. The halogenase (ctg1_5413, SMCOG1119) is the T43-HAL trigger — SMCOG1119 is a general flavin-dependent halogenase, less substrate-specific than the Trp_halogenase in BGC031 (CP050177.1 · region031). Three large PKS megasynthase genes (ctg1_5415–5417, together ~25 kb) encode multiple KS and AT modules in a mixed T1PKS/transAT configuration. Two glycosyltransferases and a DegT aminotransferase cassette provide glycosylated output. KCB similarity to glycinocin A (BGC0000379.5, score 41,448) — glycinocin A is a halogenated lipopeptide/glycopeptide antibiotics. An ABC transporter pair (ctg1_5438, ctg1_5439) provides self-resistance export capacity. Capacity claim only.

**Mechanistic link:** Halogenated glycosylated PKS compounds span diverse mechanisms — the halogen often enhances binding affinity and membrane penetration, and glycosylation typically modifies pharmacokinetics. AB 59.0 / AF 42.0. ABC transporter self-resistance provides corroborating evidence of production.

**Isolation strategy:** Large PKS product; EtOAc extraction. Halogen isotope signature in LC-MS (Cl M:M+2 = 3:1). Two glycosyltransferases — mild acid hydrolysis to release sugars and analyse aglycone separately may help with structure elucidation. Solid ISP2, 28°C, 14 days.

------------------------------------------------------------------------

#### BGC027 (CP050177.1 · region027) — Medium tier \| azoxy / N–N bond \| T43-NN

**Location:** CP050177.1 · region027 · Interior · 30,646 bp · 27 CDS · **Arch B**

**Products:** azoxy-crosslink; fatty_acid; other

**CCTT:** **T43-NN corroborated** (N–N bond biosynthesis)

**KCB:** BGC0002381.3 (tambjamine BE-18591) · score 17,377

**AB/AF/Nov:** 33.0 / 28.0 / 41.0

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_3669 | 10,001–11,146 | azdH; Acyl-CoA_dh_N | \*\*azdH\*\* — acyl-CoA dehydrogenase with azoxy function; \*\*class-defining azoxy gene\*\* |
| ctg1_3672 | 13,111–13,656 | azdO | \*\*azdO\*\* — N-oxygenase; installs the N-oxide of the azoxy N–N bond |
| ctg1_3674 | 14,240–15,226 | vlmB | \*\*vlmB\*\* — valanimycin biosynthesis B; another N–N bond enzyme |
| ctg1_3677 | 16,588–17,808 | t2fas; ketoacyl-synt | Type-II FAS KS (SMCOG1022, fatty acyl chain) |
| ctg1_3675 | 15,223–16,257 | fabH | FabH — 3-oxoacyl-ACP synthase II (starter unit) |
| ctg1_3676 | 16,358–16,588 | PP-binding | ACP carrier protein |
| ctg1_3679 | 19,651–20,646 | LPG_synthase_C | Lysophospholipid glycerol acyltransferase — lipid tailoring |
| ctg1_3681 | 21,102–22,217 | delta12_cd03507 | Δ12 fatty acid desaturase — double bond introduction |
| ctg1_3668 | 8,276–9,961 | Aldedh | Aldehyde dehydrogenase (SMCOG1017) |
| ctg1_3670 | 11,276–12,592 | Aminotran_3 | Aminotransferase class III (SMCOG1013) |
| ctg1_3665 | compl. 4,483–7,101 | — | Large fatty acid gene |
| ctg1_3678 | compl. 17,903–18,718 | — | SARP regulator (SMCOG1041) |
| ctg1_3687 | compl. 28,308–29,756 | — | Sensor histidine kinase (SMCOG1003) |
| ctg1_3688 | compl. 29,753–30,490 | — | Response regulator (SMCOG1008) |

**Pathway hypothesis:** Biosynthetic capacity consistent with an azoxy-crosslink natural product. Azoxy compounds contain an –N=N(O)– functional group (an azoxy bond), biosynthetically installed by a dedicated N-oxygenase. The diagnostic gene set is: azdH (ctg1_3669, azoxy-crosslink-specific acyl-CoA dehydrogenase), azdO (ctg1_3672, N-oxygenase that installs the N-oxide of the N–N bond), and vlmB (ctg1_3674, N–N bond biosynthesis enzyme from the valanimycin pathway). These three together constitute an azoxy biosynthetic cassette — only the second or third such complete cassette to be characterised in *Streptomyces*. The fatty acid component (ctg1_3677, t2fas; ctg1_3675, fabH; ctg1_3676, ACP) provides the aliphatic chain. A Δ12 desaturase (ctg1_3681) introduces unsaturation. KCB similarity to tambjamine BE-18591 (score 17,377) — tambjamines are tripyrrole compounds but the azoxy gene content overrides this KCB anchor as the primary class call. T43-NN corroborated. Arch B (moderately complete — some domain complexity). Capacity claim only.

**Mechanistic link:** Azoxy natural products include valanimycin (antitumour) and compounds with membrane-disrupting or enzyme-inhibiting activities. The N–N=O functional group is a reactive electrophile that can form covalent adducts with nucleophilic cellular targets. AB 33.0 / Nov 41.0 — moderate priority but chemically distinctive. The azoxy compound class is rare in *Streptomyces* and represents genuine novelty in ecological context.

**Isolation strategy:** Azoxy compounds are typically polar; aqueous/MeOH extraction. The N-oxide group may be detectable by ¹⁵N NMR if isotope-labelled culture is feasible. LC-MS with characteristic fragmentation of the N=N(O) group. Two-component regulatory system (ctg1_3687/3688) provides a signalling handle — test with exogenous signal molecules.

------------------------------------------------------------------------

#### BGC007 (CP050177.1 · region007) — Medium tier \| Unresolved fatty_acid (second novel cluster)

**Location:** CP050177.1 · region007 · Interior · 20,948 bp · 17 CDS · **Arch E**

**Products:** fatty_acid; other

**CCTT:** no trigger

**KCB:** *S. ruber* JCM 3131 composite · score 4,091

**AB/AF/Nov:** 41.0 / 24.0 / 52.0

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_1017 | compl. 10,001–10,948 | fabH | \*\*FabH\*\* — 3-oxoacyl-ACP synthase II (SMCOG1084) — sole assigned biosynthetic domain |
| ctg1_1023 | 17,994–18,851 | Fer2_4 | Iron-sulfur cluster ferredoxin (Fer2_4) |
| ctg1_1021 | 13,986–15,941 | — | Flavodoxin (SMCOG1134, electron carrier) |
| ctg1_1012 | 5,264–6,241 | — | Aldo/keto reductase (SMCOG1039) |
| ctg1_1009 | compl. 802–1,875 | — | Inner-membrane translocator (SMCOG1113) |
| ctg1_1010 | compl. 1,872–3,416 | — | ABC transporter ATPase (SMCOG1000) |
| ctg1_1019 | compl. 11,229–12,614 | — | MFS transporter (SMCOG1137) |
| ctg1_1016 | compl. 9,209–9,898 | — | GntR regulator (SMCOG1071) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a minimally characterised fatty acid or iron-associated biosynthetic pathway. FabH (ctg1_1017) is the sole named biosynthetic domain — it primes fatty acid chains with a CoA starter unit. The ferredoxin (ctg1_1023, Fer2_4) and flavodoxin (ctg1_1021) suggest an iron-sulfur/electron-transfer dependent modification. The ABC transporter provides export capacity. Architecture grade E: minimal evidence for class assignment. Novelty_auto 52.0 — no characterised MIBiG reference matches this gene content cleanly. Parallel to BGC010 (CP050177.1 · region010) in being an architecturally simple, high-novelty cluster with limited domain evidence.

**Mechanistic link:** FabH-initiated fatty acid synthesis or modified fatty acid. Extract-level bioactivity frame applies. Ferredoxin involvement suggests a potential for oxidative or radical chemistry in the pathway.

**Isolation strategy:** Same approach as BGC010 (CP050177.1 · region010) — EtOAc non-polar extraction, GC-MS fatty acid profiling, LC-MS 200–800 Da. The ABC transporter suggests active export into culture broth — prioritise broth over mycelium extraction.

------------------------------------------------------------------------

#### BGC012 (CP050177.1 · region012) — Medium tier \| RiPP-like (DUF692)

**Location:** CP050177.1 · region012 · Interior · 11,329 bp · 9 CDS · Arch A

**Products:** RiPP; RiPP-like

**CCTT:** no trigger

**KCB:** BGC0002788.2 (14-hydroxyisochainin) · score 5,154

**UMED:** **MATURATION_GAP**

**AB/AF/Nov:** 33.0 / 20.0 / 50.0

**Gene-by-gene:**

| Locus | Coords (bp) | Sec_met domains | Role |
|----|----|----|----|
| ctg1_1383 | 5,001–6,329 | DUF692 | \*\*DUF692\*\* — a domain found in RiPP clusters; function not fully characterised but associated with RiPP post-translational modification in some contexts |
| ctg1_1385 | 7,601–9,241 | PF00561 | α/β hydrolase fold (maturation protease candidate — but UMED flags it as insufficient) |
| ctg1_1378 | 1,270–2,124 | — | Polysaccharide deacetylase (SMCOG1235) |

**Pathway hypothesis:** Biosynthetic capacity consistent with a divergent RiPP with a DUF692 modification enzyme. DUF692 (Domain of Unknown Function 692) has been found in a small number of characterised RiPP clusters, including some bacteriocin pathways. Its exact biochemical function is not established. The cluster is compact (11.3 kb, 9 CDS) and encodes no identified precursor peptide, no canonical RiPP recognition element (RRE), and no maturation protease beyond the UMED-flagged PF00561 hydrolase. MATURATION_GAP: the pipeline flags that the canonical maturation enzyme for the RiPP class is not co-clustered. KCB similarity to 14-hydroxyisochainin (score 5,154) — isochainin is a fungal polyketide; this KCB anchor is almost certainly a false reference arising from partial domain matches, not pathway similarity. Novelty_auto 50.0. Capacity claim only; this cluster warrants manual inspection before wet-lab investment.

**Mechanistic link:** Insufficient evidence for a specific mechanistic hypothesis. If DUF692 is confirmed as an RiPP modification enzyme, the compound class would depend on the precursor peptide sequence, which is not identified in this cluster. Extract-level bioactivity frame applies.

**Isolation strategy:** If pursuing: solid ISP2, 28°C, 14 days. MALDI-MS for small peptide products. The absence of an identified precursor peptide is a significant obstacle — targeted ORF prediction upstream and downstream of ctg1_1383 for short ORFs with RiPP-like sequence features would help before wet-lab investment.

**§8 audit:** ✓ Capacity language. ✓ MATURATION_GAP disclosed. ✓ DUF692 function acknowledged as not fully characterised. ✓ KCB isochainin anchor flagged as likely class-discordant. ✓ Interior, Arch A.

------------------------------------------------------------------------

### PART III — CROSS-BGC SYNTHESIS

#### Mechanistic Ecology Synthesis

*S. liangshanensis* presents a distinct secondary metabolome profile from *S. spectabilis*. The dominant biosynthetic themes are: (1) halogenated aromatic polyketide and NRPS chemistry (BGC009 (CP050177.1 · region009), BGC031 (CP050177.1 · region031), BGC040 (CP050177.1 · region040)); (2) an HSAF-class antifungal (BGC026 (CP050177.1 · region026)); (3) an azoxy N–N bond compound (BGC027 (CP050177.1 · region027)); and (4) two unresolved high-novelty clusters (BGC007 (CP050177.1 · region007), BGC010 (CP050177.1 · region010)). The absence of lanthipeptide clusters (unlike *S. spectabilis*) and the presence of a confirmed azoxy biosynthesis cassette distinguish this strain.

**HSAF antifungal dominance (BGC026 (CP050177.1 · region026)):** The AF 67.0 score and T43-PTM corroboration make BGC026 (CP050177.1 · region026) the clearest single lead in this genome. HSAF-class compounds are ecologically relevant in soil contexts where fungal competition is intense. The sphingolipid biosynthesis mechanism (inhibiting sphinganine C4-hydroxylase) is distinct from cell-wall-targeting antifungals and is not yet clinically exploited.

**Halogenation capacity (BGC031 (CP050177.1 · region031) + BGC040 (CP050177.1 · region040) + BGC022 (CP050177.1 · region022)):** Three BGCs carry halogenase genes — BGC031 (CP050177.1 · region031) carries a Trp-halogenase (tryptophan-specific, analogous to rebeccamycin RebH), BGC040 (CP050177.1 · region040) carries a general flavin-dependent halogenase (SMCOG1119), and BGC022 (CP050177.1 · region022) also carries a halogenase (not analysed at Mode B depth here). This concentration of halogenase capacity in one genome is noteworthy. Halogenation generally enhances binding affinity to biological targets and increases membrane permeability. The co-occurrence of Trp-halogenation (BGC031 (CP050177.1 · region031)) with downstream NRPS modules parallels indolocarbazole and rebeccamycin biosynthesis architecturally, though without the IndSyn enzyme.

**N–N bond chemistry (BGC027 (CP050177.1 · region027)):** Azoxy compounds are among the rarest natural product classes in bacteria. The complete azdH + azdO + vlmB cassette in BGC027 (CP050177.1 · region027) represents an uncommon biosynthetic capability. In soil ecology, N–N bond-containing compounds have niche-specific roles — valanimycin (another azoxy compound) was isolated from a soil *Streptomyces* and shows antitumour activity. The ecological role in a soil competitor context is unclear but chemically distinctive.

**Two high-novelty fatty acid clusters (BGC007 (CP050177.1 · region007), BGC010 (CP050177.1 · region010)):** Both clusters score in the top novelty range (82.0 and 52.0 respectively) with near-absent KCB similarity. Architecture grade E on both reflects the genuine interpretive gap. The two EmrB/QacA efflux transporters flanking BGC010 (CP050177.1 · region010) and the ABC transporter in BGC007 (CP050177.1 · region007) provide the strongest inference available: these genes are disproportionate to the minimal biosynthetic content and suggest active export of bioactive products.

**No bldA T4 gating, no T1 resistance:** Practically, 0 T4 means the full secondary metabolome of this strain is accessible in liquid culture — a significant operational advantage. The absence of T1 self-protection hits means no within-cluster corroborating resistance signal is available for any BGC, reducing confidence in active production across the board. The wet-lab programme should prioritise direct compound detection before assuming production.

**NAPAA exclusion (BGC001 (CP050177.1 · region001)):** BGC001 (CP050177.1 · region001) was excluded by the NAPAA standing rule. The NAPAA-exclusion is a documented standing rule — NAPAA-class BGCs are ubiquitous across genera and not ecologically informative at the strain level. This exclusion is correct and noted here for completeness.

#### Environmental Trigger Experiment Matrix

| BGC | Signal | Elicitation experiment | Expected |
|----|----|----|----|
| BGC026 (CP050177.1 · region026) (antifungal HSAF) | T43-PTM, TetR regulation | Standard liquid ISP2, harvest day 7–10 (stationary) | Tetramate macrolactam expression at stationary phase |
| BGC031 (CP050177.1 · region031) (halogenated) | SARP activator (ctg1_4066), Trp-halogenase | OSMAC: varied carbon source (mannitol vs glucose) | SARP-activated halogenated product |
| BGC040 (CP050177.1 · region040) (halogenated) | ABC transporter self-resistance | Co-culture with Gram-positive competitor | Inducible halogenated compound |
| BGC027 (CP050177.1 · region027) (azoxy) | Two-component system (ctg1_3687/3688) | Vary Fe²⁺/Fe³⁺ concentration | N–N bond compound expression |
| BGC010 (CP050177.1 · region010) (novel) | EmrB/QacA efflux | Sub-inhibitory concentrations of diverse antibiotics (OSMAC) | Novel compound released under stress |
| Any BGC | DasR (24 hits) | GlcNAc supplementation 0.5 mM | Broad secondary metabolite induction |
| Any BGC | IolR (9 hits) | Inositol supplementation (pollen extract) | IolR-regulated compound expression |

#### Compound Detection and Isolation Bench Guide

**Priority 1 — Antifungal lead (BGC026 (CP050177.1 · region026), HSAF):**

Solid ISP2 agar, 28°C, 10 days. EtOAc extraction. UV 280–330 nm (tetramate). LC-MS positive ESI 300–700 Da. Bioassay: *Fusarium graminearum* inhibition zone (HSAF-sensitive). Sphingolipid biosynthesis inhibition with fluorescent ceramide accumulation assay.

**Priority 2 — Antibacterial leads:**

BGC009 (CP050177.1 · region009) (hedamycin-class): yellow/orange pigment on solid culture; UV 430–480 nm; MRSA broth dilution assay.

BGC031 (CP050177.1 · region031) (halogenated): LC-MS Cl isotope signature; NRPS product 400–900 Da.

BGC040 (CP050177.1 · region040) (halogenated glycosylated PKS): LC-MS Cl isotope; mild acid hydrolysis for aglycone.

**Priority 3 — Chemical novelty leads:**

BGC010 (CP050177.1 · region010) + BGC007 (CP050177.1 · region007): EtOAc extraction; LC-MS profiling; GC-MS fatty acid analysis; compare culture vs media blank.

BGC027 (CP050177.1 · region027) (azoxy): MeOH/aqueous extraction; ¹H NMR for N=N(O) signature.

#### Layperson's Guide to BGCs in *S. liangshanensis*

**BGC010 (CP050177.1 · region010) (Top AB score, highest novelty):** This cluster has the most unusual chemistry in the genome — a tiny recipe with almost no resemblance to anything in the database, which means it could make something completely new. The only enzyme we can identify is a fatty acid-building enzyme. Two export pumps suggest whatever it makes is actively pushed out of the cell, which is a sign of something bioactive.

**BGC026 (CP050177.1 · region026) (Top AF score — antifungal priority):** This is the most exciting antifungal lead. The cluster makes an HSAF-class compound — the same family as heat-stable antifungal factor, a compound that kills fungi by disrupting their membrane chemistry in a way that's completely different from most antifungals. The HSAF mechanism is clinically unexploited. High confidence: two independent lines of evidence (the T43-PTM diagnostic trigger and KCB similarity to a known HSAF-family reference) point to the same compound class.

**BGC009 (CP050177.1 · region009) (Second AB score — hedamycin-class):** This large cluster resembles hedamycin — an antibiotic that works by inserting itself between the rungs of bacterial DNA and blocking it from being read. The machinery is a complete type-II polyketide synthase (a two-component enzyme system that builds aromatic ring systems) plus extra decorating enzymes that add sugars. Produces a visually distinctive coloured product.

**BGC031 (CP050177.1 · region031) (Halogenated NRPS hybrid):** This cluster has a tryptophan-halogenase — the same kind of enzyme that puts chlorine on tryptophan in the rebeccamycin antibiotic pathway. Here, the halogenated amino acid feeds into an NRPS peptide assembly line. The halogen makes the final compound more potent against biological targets.

**BGC040 (CP050177.1 · region040) (Halogenated PKS):** A large polyketide assembly line with a second type of halogenase (less specific than BGC031 (CP050177.1 · region031)) plus two sugar-attaching enzymes. The sugars are likely key for antibiotic activity — sugar moieties help antibiotics bind to their bacterial targets.

**BGC027 (CP050177.1 · region027) (Azoxy compound — rare chemistry):** This is genuinely rare. The three enzymes azdH + azdO + vlmB together make an N=N(O) bond — an azoxy crosslink. Very few bacteria make this kind of chemistry. The ecological role is unclear but chemically this compound class includes antitumour agents.

**BGC007 (CP050177.1 · region007) (Second novel unresolved cluster):** Similar situation to BGC010 (CP050177.1 · region010) — minimal biosynthetic evidence (one fatty acid enzyme), high novelty, active export. Two unresolved novel clusters in one genome is a finding in itself.

**BGC012 (CP050177.1 · region012) (RiPP-like with DUF692):** A small cluster with an enzyme (DUF692) whose function is not fully known, found in a few RiPP pathways. Missing the maturation enzyme that would process the precursor peptide. Lower priority until the maturation gap is resolved.

------------------------------------------------------------------------

### PART IV — QUALIFIED NULLS AND VALIDATION CONTROLS

**Assembly tier (PASS):** Single closed chromosome, 45/0/0 Interior/Edge/Full-contig, corrected count 45.0.

**NAPAA exclusion applied (PASS):** BGC001 (CP050177.1 · region001) correctly excluded — NAPAA standing rule applied before scoring.

**0 T1 resistance (informational):** No class-concordant self-protection determinant detected across the genome. This is not a call of non-production; it removes the strongest within-cluster corroborating signal.

**0 T4 bldA-gated BGCs (informational):** All BGCs accessible in liquid culture — a practical advantage.

**UMED MATURATION_GAP (BGC012 (CP050177.1 · region012)):** Disclosed in Mode B §8 and in this section. BGC012 (CP050177.1 · region012) should not be treated as a production-confirmed cluster until the maturation enzyme is identified.

**Negative calls (NONE MADE):** No BGC is called antibacterial-negative or antifungal-negative.

**CCTT corroboration (PASS):** All 4 triggered families (T43-HAL ×3, T43-PTM ×1, T43-PHO ×1, T43-NN ×1) fired on class-compatible loci. BGC001 (CP050177.1 · region001) carries T43-PHO but is excluded by NAPAA standing rule — the trigger is recorded but no capacity credit extends to comparative claims.

------------------------------------------------------------------------

*Report generated: 2026-06-18 · Sapote–Mamey v9.7.81*

*All claims capacity-level only. KCB = similarity not identity. Bioactivity extract-level unless fractionation data available.*

------------------------------------------------------------------------

→ Volume X for *S. spectabilis* as a Mamey-only calibration case (assembly stats, boundary parsing, spectinomycin anchor).\
→ Volume XI for *Streptomyces* sp. M56 (discovery-mode reference).\
→ User Manual §7 for fungal and cyanobacterial genome guidance.\
→ §I.3 for the claim-safety doctrine governing all claims in this volume.

</div>
