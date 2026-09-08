# Mode B — BGC029 (JBHTEE010000001.1 · region029) — *Streptosporangium amethystogenes* subsp. *fukuiense*

**Class exemplar: t2pks (type II / aromatic PKS).** Public type strain (GCA_042665875.1). Claim-safe throughout: biosynthetic *capacity* only; KCB/BLASTp are *similarity, not identity*; cited as BGC029 · JBHTEE010000001.1 · region029.

## §1 Identity and node/region
BGC029 sits on contig JBHTEE010000001.1, antiSMASH region029, spanning ~44.2 kb. It is **Interior** (both flanks non-cluster). antiSMASH labels it **HR-T2PKS; PKS; fatty_acid; other; saccharide**, and the KnownClusterBlast top anchor is MIBiG `BGC0002021.3` (fogacin/fogacin B/fogacin C, score 1827) — a characterized aromatic-polyketide (angucyclinone-type) cluster. The "HR-T2PKS" label marks a highly-reducing type II PKS variant. Cited hereafter as BGC029 · JBHTEE010000001.1 · region029.

## §2 Why this BGC was selected
Selected as the **type II / aromatic PKS exemplar**: it carries the minimal-PKS ketosynthase core characteristic of the class, its KCB anchor is a defined MIBiG aromatic-polyketide entry (fogacin), and it offers a clean teaching REFINE — a co-captured regulator whose antiSMASH Pfam label (GerE) is resolved by BLASTp to a LuxR-type transcriptional regulator. It shows the confirmed aromatic-PKS core alongside honestly-labelled regulatory/peptidase context.

## §3 Boundary and assembly status
Assembly tier **GOOD**, boundary **Interior** — no contig-edge truncation caveat; gene inventory taken as complete. The region carries several labels (HR-T2PKS plus fatty_acid/other/saccharide), so as with any multi-label region the possibility of co-located accessory systems is kept open (§10); the type II PKS signal is the dominant and interpretable one and drives the class call.

## §4 Gene-by-gene interpretation

**Evidence grid.** Domain calls are antiSMASH Pfam; the BLASTp column is an independent operator-supplied online run against nr, reconciled as CONFIRM / REFINE / OVERTURN. No observation is stated that is not in a real result.

| Locus | aa | antiSMASH domains | BLASTp top hit (nr) | %id | Reconciliation |
|---|---|---|---|---|---|
| **ctg1_3726 ●** | 759 | Ketoacyl-synt_C; PKS_KS; ketoacyl-synt | beta-ketoacyl synthase N-terminal-like domain-containing protein [*Streptosporangium* sp.] | 97.1 | **CONFIRM** — the class-defining minimal-PKS ketosynthase; domain call and homology channel agree. |
| ctg1_3739 | 920 | AAA_16; GerE | LuxR C-terminal-related transcriptional regulator [*Streptosporangium* sp.] | 95.9 | **REFINE** — antiSMASH reads AAA_16 + GerE (a DNA-binding motif); BLASTp resolves the whole protein as a **LuxR-family transcriptional regulator** (the GerE domain is the LuxR C-terminal HTH). Regulatory, not biosynthetic-core; the REFINE sharpens "GerE motif" into "LuxR-type regulator." |
| ctg1_3742 | 774 | Peptidase_M64 | M64 family metallopeptidase [*Streptosporangium* sp.] | 91.6 | **CONFIRM (as a peptidase) → co-captured.** A metallopeptidase; confirmed as such, but not part of the aromatic-PKS chemistry — carried as co-located context. |

Prose walkthrough. The aromatic-PKS identity of this region rests on **ctg1_3726** (●), whose PKS_KS / Ketoacyl-synt domains and independent BLASTp hit (beta-ketoacyl synthase, 97 %) agree exactly — this is the minimal-PKS ketosynthase that defines a type II system. The two other sampled genes are regulatory/accessory context. ctg1_3739 is the instructive REFINE: antiSMASH annotates an AAA_16 ATPase domain plus a GerE motif, but the BLASTp top hit resolves the protein as a **LuxR C-terminal-related transcriptional regulator** — GerE is in fact the C-terminal HTH of the LuxR family, so the homology channel usefully collapses the two Pfam fragments into a single, more informative call: a LuxR-type pathway regulator, not a biosynthetic enzyme. ctg1_3742 is confirmed as an M64 metallopeptidase and treated as co-captured context, not aromatic-PKS chemistry. The minimal-PKS partner genes (the KSβ/chain-length factor and ACP that complete the type II triad) and the cyclase/aromatase set that fold the poly-β-keto chain are the region's remaining core; they were not in this 3-gene sample and are the natural next BLASTp targets (§16).

## §5 Core biosynthetic logic
Type II (iterative aromatic) PKS logic: a minimal PKS — ketosynthase-α (the confirmed ctg1_3726), a chain-length-factor (KSβ), and a discrete ACP — iteratively condenses malonyl units into a poly-β-ketone chain, which dedicated cyclases and aromatases then regiospecifically fold and aromatise into a fused-ring aromatic polyketide (angucyclinone/anthracyclinone-type for the fogacin family). The "HR" (highly-reducing) label indicates additional ketoreduction beyond a canonical aromatic backbone. Chain length and cyclisation pattern determine the ring system and are set by the minimal-PKS + cyclase complement, not by the KS alone.

## §6 Tailoring and maturation logic
Aromatic polyketides of this class are typically tailored by oxygenases, ketoreductases, and glycosyltransferases that install the characteristic oxygenation and (for many angucyclines) sugar decoration. The "saccharide" co-label is consistent with a glycosylated aromatic product, though glycosyltransferase attribution is held pending the per-gene partition. Tailoring is stated at the class level (oxidative + reductive processing, possible glycosylation), not as specific product-committing gene calls, since the sampled genes here are the KS core plus regulatory/peptidase context.

## §7 Transport, resistance, and regulation
Regulation is local and now sharpened: ctg1_3739 is a **LuxR-family transcriptional regulator** (BLASTp REFINE), plausibly a pathway-specific activator/repressor of the locus. Resistance routing is **T3_TRANSPORTER_ONLY_ROUTING** — transporter-based, not a source-derived target-modification determinant; read as efflux context. Aromatic-polyketide loci commonly co-encode resistance/efflux for their (often DNA-intercalating or membrane-active) products; here only the transporter routing is flagged, and no target-modification immunity gene is asserted.

## §8 Comparator/KCB interpretation
KnownClusterBlast returns MIBiG `BGC0002021.3` (fogacin/fogacin B/C) at score 1827 — a characterized aromatic-polyketide cluster. Because the region's confirmed KS core and its KCB anchor are the same biosynthetic class (aromatic PKS), the comparator is a *consistent* similarity anchor (unlike the deliberately-divergent NRPS exemplar). It is still held as **similarity, not identity**: fogacin is the nearest characterized neighbour, supporting capacity for a fogacin-*like* aromatic polyketide, not a demonstration that fogacin is produced. The per-gene BLASTp genus (*Streptosporangium*) is internally consistent.

## §9 Alternative hypotheses
The class is well-supported (minimal-PKS ketosynthase confirmed). The open questions are the ring system and decoration. First, the naming: 'fogacin' is a **KCB comparator by similarity, not an identity claim** — it is the nearest characterised aromatic-polyketide neighbour, and the per-gene BLASTp genus (*Streptosporangium*) is consistent with it, but neither demonstrates the compound. Held that way, the leading hypothesis is a fogacin-*like* angucyclinone-type aromatic polyketide, but the "HR" and "saccharide" labels leave room for a more-reduced and/or glycosylated variant. Because "fogacin" is a **KCB comparator by similarity, not an identity claim**, the product is held as capacity for a fogacin-like aromatic polyketide, not fogacin itself. No plausible alternative makes this a non-PKS locus.

## §10 Fragmentation and co-capture risks
Fragmentation risk nil (Interior). Co-capture is the relevant risk: the multi-label region (HR-T2PKS + fatty_acid/other/saccharide) may sweep in accessory or neighbouring genes, and as §4 shows it has captured a LuxR regulator and an M64 peptidase that are not aromatic-PKS core. These are flagged as regulatory/accessory so they cannot leak into the product read. No hard over-merge was flagged, but the mixed labels warrant the same caution before naming a single product.

## §11 Product-family interpretation
Product family: **aromatic polyketide** (fogacin-like angucyclinone-type), stated as capacity, possibly reduced ("HR") and/or glycosylated ("saccharide"). No specific fogacin congener is named as the product; no titre or condition-dependence is claimed.

## §12 Bee/microbe ecological interpretation
Public reference type strain, not a host-associated isolate — no bee/wasp/bryophyte ecological role is claimed. Generically, aromatic polyketides (angucyclines/anthracyclines) frequently have antibacterial or cytotoxic activity; that is a class-level property (`assumed`), not a claim about a realised role for this strain.

## §13 Antibacterial/antifungal relevance
Aromatic polyketides of the angucycline/anthracycline type are often **antibacterial and/or cytotoxic**, but no extract-level bioactivity data accompanies this public genome, so any relevance is stated at the class level and as capacity, not as a measured phenotype for this strain or this BGC. Extract assay would be required to attach an activity.

## §14 What cannot be claimed
Cannot claim: that fogacin is *produced* (only encoded capacity for a fogacin-like aromatic polyketide); that ctg1_3739 or ctg1_3742 participate in the biosynthetic chemistry (they are a regulator and a peptidase); a specific ring system or glycosylation pattern without the cyclase/tailoring partition; any bioactivity phenotype without extract data; any titre.

## §15 Missing evidence
Missing: BLASTp/HMM on the minimal-PKS partners (KSβ/CLF, ACP) and the cyclase/aromatase set to define the ring system; glycosyltransferase identification to test the "saccharide" label; LC-MS/UV to detect the aromatic product. These convert "aromatic-PKS capacity" into a defined ring system and decoration.

## §16 BLASTP/HMMER next steps
Two steps. First, run **per-gene BLASTp on the minimal-PKS partners** — the ketosynthase-β/chain-length factor and the discrete ACP that complete the type II triad with the confirmed ctg1_3726, plus the cyclase/aromatase genes — because the ring system is set by that complement, not by the KSα alone. Second, **HMM-adjudicate the tailoring/glycosyltransferase candidates** to test the "HR" and "saccharide" labels (is there genuine extra ketoreduction and a sugar-transfer gene?). No OVERTURN is pending on the KS core; the ctg1_3739 REFINE (GerE→LuxR) is already resolved and needs no further channel.

## §17 LC-MS / fermentation implications
For detection, target an **aromatic polyketide**: angucyclinone/anthracyclinone-type products have diagnostic UV-vis absorption (extended chromophores absorbing in the visible, often yellow/orange pigmented colonies) that is a fast first screen, followed by LC-MS with a fogacin-family mass window and, if the saccharide label holds, a search for glycosylated congeners (+hexose mass increments). Because aromatic-PKS expression can be condition-dependent, screen across media and growth phases, and pair with an antibacterial bioassay as a non-specific activity indicator. Confirm any candidate against a fogacin reference or by exact mass before attaching the comparator name.

## §18 Figure/locus-map notes
A locus map should mark ctg1_3726 as the aromatic-PKS core (●, labelled PKS_KS / beta-ketoacyl synthase 97 %), render ctg1_3739 with a **REFINE flag** (antiSMASH: AAA_16+GerE; BLASTp: LuxR-family regulator) to show the two-fragment→single-call resolution, and grey ctg1_3742 (M64 peptidase) as co-captured context. The minimal-PKS partners and cyclases should be highlighted as the next-analysis targets.

## §19 Final Mode B judgement
BGC029 is a **source-derived, Interior type II (aromatic) PKS region** with a confirmed minimal-PKS ketosynthase core (ctg1_3726) and a class-consistent KCB anchor (fogacin). Biosynthetic capacity is consistent with a fogacin-like aromatic polyketide, possibly reduced and/or glycosylated; co-captured genes (a LuxR regulator, an M64 peptidase) are excluded from the product read. Confidence in the *class* call is high; the specific ring system and product identity are held as capacity pending the minimal-PKS/cyclase partition and chemical confirmation.

## §20 Next actions
Priority: per-gene BLASTp on the minimal-PKS partners (KSβ/CLF, ACP) and cyclase/aromatase genes to define the ring system, plus glycosyltransferase check for the saccharide label. Secondary: UV/LC-MS screen for a pigmented aromatic polyketide across conditions, confirming any candidate against a fogacin reference before naming. The KS core and the regulator call are settled.

## §23 Heterologous expression
Because the aromatic-PKS product is not confirmed at the chemical level and the tailoring/cyclase complement is only partly sampled, heterologous expression is the decisive test. Refactor the minimal-PKS cassette (the confirmed ketosynthase ctg1_3726 with its KSβ/chain-length factor and discrete ACP) plus the cyclase/aromatase set into a characterised *Streptomyces* host (e.g. *S. coelicolor* or *S. albus*) under a strong promoter, and screen the host extract for a new pigmented aromatic polyketide absent from the empty-vector control. A positive result confirms the ring system independent of native (LuxR-regulated) expression; a negative result points to missing tailoring genes or a silent cluster. Include and exclude the LuxR regulator (ctg1_3739) to test whether native regulation gates the locus. This step converts encoded aromatic-PKS capacity into a demonstrated product without waiting on native induction.

## §24 Scaffold novelty score
Novelty is **LOW–MEDIUM**: the region has a class-consistent MIBiG comparator (fogacin, `BGC0002021.3`) and a confirmed aromatic-PKS ketosynthase core, so the backbone reads as a known-like angucyclinone-type aromatic polyketide rather than a novel class. The residual novelty (the MED half) is in the decoration: the "HR" (extra reduction) and "saccharide" labels leave the specific ring reduction and glycosylation pattern unscored until the cyclase/glycosyltransferase complement is resolved (§16). Stated as a backbone novelty read, not a product claim.

## §27 Self-resistance assessment
Resistance is transporter-routed (T3_TRANSPORTER_ONLY_ROUTING), not a source-derived target-modification determinant — read as efflux/export context. For a potentially DNA-active aromatic polyketide, a target-based immunity gene may exist but is **not** asserted here without evidence; only the transporter routing is flagged.

## §28 Evidence provenance ledger
- Region identity, boundary, HR-T2PKS/saccharide labels, KCB anchor, TTA/resistance routing: **store-backed** (Mamey inventory + KCB; `BGC0002021.3` fogacin #1, score 1827).
- Domain calls (PKS_KS, Ketoacyl-synt, AAA_16, GerE, Peptidase_M64): **store-backed** (antiSMASH Pfam).
- Per-gene top hits (beta-ketoacyl synthase 97.1 %; LuxR-family regulator 95.9 %; M64 metallopeptidase 91.6 %): **operator-supplied** independent BLASTp (nr), reconciled in §4.
- No reconstructed or fabricated observation is present; every §4 row traces to a real BLASTp result or an antiSMASH call.

## §30 Experimental decision tree
1. Define the aromatic core: BLASTp/HMM the minimal-PKS partners + cyclases → ring system (angucyclinone vs other).
2. Test decoration: glycosyltransferase present? → glycosylated vs aglycone product; extra ketoreduction for the "HR" label?
3. Detect: UV/LC-MS for a pigmented aromatic polyketide across conditions → confirm against a fogacin reference before naming.
4. If antibacterial/cytotoxic follow-up is wanted, run extract-level bioassay — the genome does not license a phenotype claim on its own.
