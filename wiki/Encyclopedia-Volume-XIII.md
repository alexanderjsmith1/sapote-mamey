# Volume XIII — Compound-class annotation and the cassette catalog (v9.7.86)

> **Currency scope:** This volume retains its historical edition and review stamps. Only the checks listed in the [currency record](Encyclopedia-Currency.md) have been refreshed for the current candidate. Other constants, numerical claims, literature interpretations, and worked-run results have not been comprehensively revalidated. A newer bundle does not make those older observations current.

*This volume is generated from the scanner and the enriched registry via `tools/gen_user_catalog.py`; the canonical machine-readable form is `docs/USER_CATALOG.generated.md`. Cassette counts are capacity/signal, not product or activity; absence of a family is not a negative call.*

## §XIII.1 · The compound-class annotation layer

v9.7.86 adds a deterministic layer (`compound_class.py`) that records the chemotype a BGC's own evidence is consistent with. It reads antiSMASH's own `t2pks.product_classes` prediction as the primary, machinery-based signal, falling back to the resolved MIBiG product line; it never reads the raw KCB anchor blob, preserving the P-7 contamination fix. Each BGC carries `chemotype`, `pharmacology`, `evidence_source`, `class_evidence`, a `confidence` grade (HIGH/MODERATE/LOW), and a `cytotoxic_flag`. Most chemotypes are **annotation-only** (recorded, no score impact); three well-anchored families carry a scored consequence: polyene-macrolide → AF (antifungal), ionophore → AB (antibacterial), and anthracycline → its own cytotoxic/antitumor category (flagged and routed, not folded into the clean antibacterial board). Arylpolyene and spore pigments, and fungal mycotoxins / primary metabolites, are explicitly excluded.

## §XIII.2 · The fifteen cassette families

### release_macrocyclization <span class="small">(MMC-001 — Release and macrocyclization cassette)</span>

**Detects:** `thioesterase, \bte\b, cyclase, macrocycl, esterase, reductase release`

Detects chain-release and macrocyclization machinery in modular assembly lines: thioesterase (TE) and 'TE' tokens, cyclase, macrocyclization, esterase, and reductase-release wording. These domains determine how a linear NRPS/PKS chain is offloaded — by hydrolysis, macrolactone/macrolactam cyclization, or reductive release — and so shape final-product topology rather than its chemical class.

*Positive:* Read as architecture context: supports release/macrocyclization logic when co-located with NRPS/PKS modules, and can hint that a product is cyclic when a TE-cyclase sits at the chain terminus.

*Negative:* Absence is uninformative. Release/TE wording is near-ubiquitous in modular pathways, so a low or zero count under source-derived scope is not evidence against macrocyclization — it usually reflects annotation gaps.

*Claim-safety:* Tier-3 context only: a release/TE token never defines a product class or proves cyclization. Treat as architecture support for an NRPS/PKS lead; confirm topology by LC-MS/MS and curated domain calls.

### glycosylation <span class="small">(MMC-002 — Glycosylation cassette)</span>

**Detects:** `glycosyltransferase, glycosyl, sugar, deoxysugar, gt\b`

Detects sugar-tailoring machinery — glycosyltransferase, glycosyl, sugar, deoxysugar, and 'GT' tokens — that attach (deoxy)sugars to a core scaffold. Glycosylation is common across glycopeptides, macrolides, and aminoglycoside-adjacent metabolites and often modulates solubility, target binding, and bioactivity.

*Positive:* Supports a glycosylated-product hypothesis and flags sugar-decoration capacity when a glycosyltransferase sits in a PKS/NRPS/RiPP context.

*Negative:* Absence does not rule out glycosylation; GT annotations are easily missed. A positive call does not specify which sugar, how many, or the linkage.

*Claim-safety:* Tier-3 context with the saccharide standing-downgrade in force: glycosyltransferase tokens are widespread and low-specificity. Do not infer a glycoside or a sugar identity without deeper annotation and LC-MS/MS.

### halogenation <span class="small">(MMC-003 — Halogenation cassette)</span>

**Detects:** `(?<!de)halogenase, fluorinase, chlorinase, brominase`

Detects halogenating enzymes — halogenase (excluding dehalogenase), fluorinase, chlorinase, brominase — that install Cl/Br/F (and rarely I) onto natural-product scaffolds. Halogenation frequently raises structural novelty and can be important for potency, making it a useful prioritization signal.

*Positive:* Elevates search priority for halogenated metabolites; a flavin-dependent halogenase in a PKS/NRPS/RiPP context is a credible organohalogen cue.

*Negative:* Absence is not evidence of an unhalogenated product under source-derived scope. A positive call does not fix the halogen, position, or subclass (FADH2-dependent vs SAM-dependent fluorinase).

*Claim-safety:* Tier-2 class-supporting: signals capacity for halogenation, not a specific halogenated product. Confirm by curated halogenase HMM/BLAST and by halogen isotope pattern in MS before any organohalogen claim.

### phosphonate <span class="small">(MMC-004 — Phosphonate cassette)</span>

**Detects:** `phosphonate, pep mutase, phosphoenolpyruvate mutase, foma, fomb`

Detects C-P-bond (phosphonate) biosynthesis and self-protection: phosphonate wording plus the committed first-step enzyme PEP mutase (PepM) / phosphoenolpyruvate mutase, and FomA/FomB-type resistance markers. Phosphonates (e.g., fosfomycin-, rhizocticin-class) are antibacterial/antifungal antimetabolites of high interest.

*Positive:* High-value antibacterial/antimetabolite hypothesis when PepM-like biosynthesis and FomA/FomB-like self-resistance are concordant in the same neighbourhood; KCB similarity to rhizocticin/fosfomycin is corroborating, not identity.

*Negative:* Absence in a source-derived scan is not a true null unless the full proteome was in scope; PepM can sit off the antiSMASH region. A bare 'phosphonate' token without PepM may reflect transport/utilization, not biosynthesis.

*Claim-safety:* Tier-1 diagnostic but gated on committed enzymes: require PepM (+ aepY / phosphonopyruvate decarboxylase) confirmation before any phosphonate class claim. The regex already vetoes C-P lyase / phn transporter / utilization false-positives; confirm by HMM/BLAST, ³¹P-NMR, and fractionation.

### nucleoside <span class="small">(MMC-005 — Nucleoside cassette)</span>

**Detects:** `nucleoside, nikkomycin, polyoxin, nikj, nikd`

Detects peptidyl-nucleoside antifungal biosynthesis — nikkomycin/polyoxin wording and the diagnostic nikJ/nikD enzymes — for metabolites that inhibit fungal chitin synthase. Narrowed in v9.7.21 to drop the bare 'nucleoside' token, which over-called antifungal capacity on generic nucleoside primary metabolism.

*Positive:* Strong Candida/antifungal-track cue when Nik/Pol-like committed markers (nikJ/nikD) are confirmed alongside peptide-nucleoside assembly logic.

*Negative:* Absence is not an antifungal-negative call (no strain is called antifungal-negative; bioactivity is extract-level). A generic nucleoside hit without nikJ/nikD is not a peptidyl-nucleoside lead.

*Claim-safety:* Tier-1 diagnostic restricted to the peptidyl-nucleoside class: a true call needs the diagnostic Nik/Pol enzymes, not nucleotide-metabolism wording. Confirm by HMM/BLAST and antifungal fractionation.

### aminoglycoside_aminocyclitol <span class="small">(MMC-006 — Aminoglycoside/aminocyclitol cassette)</span>

**Detects:** `aminoglycoside, aminocyclitol, dois, btrc`

Detects aminocyclitol/aminoglycoside biosynthesis and self-protection: aminoglycoside, aminocyclitol, and the committed enzymes DOIS (2-deoxy-scyllo-inosose synthase) and BtrC. This class (e.g., 2-deoxystreptamine aminoglycosides) is antibacterial and clinically significant.

*Positive:* Antibacterial-track cue when DOIS/BtrC-like committed steps are confirmed within an aminoglycoside neighbourhood.

*Negative:* Absence is uninformative under partial scope. An 'aminoglycoside' wording hit can reflect a resistance/modifying gene (APH/AAC) rather than biosynthesis, so the bare token is not a producer call.

*Claim-safety:* Tier-1 diagnostic anchored on DOIS: the committed 2-deoxy-scyllo-inosose synthase step is the diagnostic, not the class name. Separate biosynthesis from resistance genes; confirm by HMM/BLAST and fractionation.

### tetronate_spirotetronate <span class="small">(MMC-007 — Tetronate/spirotetronate cassette)</span>

**Detects:** `tetronate, spirotetronate, fkbh, (?<!acyl)glyceryl`

Detects tetronate/spirotetronate polyketide building-block machinery: tetronate, spirotetronate, the glyceryl-transferase FkbH, and glyceryl (excluding acyl-glyceryl) tokens. Spirotetronates (e.g., chlorothricin-, kijanimicin-class) are architecturally complex polyketides of high novelty interest.

*Positive:* High-value polyketide-tailoring cue when FkbH and an ACP-glyceryl context sit within a modular PKS, consistent with tetronate unit installation.

*Negative:* Absence does not exclude a tetronate; FkbH context can be split across contigs. FkbH alone is shared with other glyceryl-using pathways and does not by itself prove a spiro-fused product.

*Claim-safety:* Tier-1 diagnostic but topology-gated: calling 'spiro' needs the Diels-Alderase/cyclization context, not just FkbH. Confirm by curated domain analysis and LC-MS/MS.

### thioamide_ycao <span class="small">(MMC-008 — Thioamide/YcaO cassette)</span>

**Detects:** `thioamide, ycaO`

Detects YcaO-dependent backbone thioamidation — thioamide and YcaO tokens — a rare amide-to-thioamide modification seen in thioamitide RiPPs and some thiopeptides. It is a strong novelty signal because true thioamidation is uncommon.

*Positive:* High-novelty cue, especially in NRPS/RiPP contexts, when a YcaO is paired with a TfuA partner and a precursor consistent with thioamide installation.

*Negative:* Absence is uninformative under source-derived scope. A YcaO hit alone is ambiguous: YcaO also performs azoline cyclodehydration in TOMMs, so a bare YcaO token is not a thioamide call.

*Claim-safety:* Tier-1 diagnostic but mechanism-ambiguous: distinguish thioamidating YcaO (needs TfuA / thioamide context) from TOMM cyclodehydratase YcaO before claiming thioamidation. Confirm by HMM/BLAST and MS mass-shift.

### lanthipeptide <span class="small">(MMC-009 — Lanthipeptide cassette)</span>

**Detects:** `lanthipeptide, lanm, lanc, lant, lanp`

Detects lanthipeptide RiPP biosynthesis and maturation: lanthipeptide wording and the Lan enzymes (LanM, LanC, LanT, LanP). These install (methyl)lanthionine thioether crosslinks (class I LanB/LanC; class II LanM) and handle export/proteolytic maturation, yielding ribosomal antibacterial peptides.

*Positive:* Supports lanthipeptide lead status when a precursor peptide and class-defining synthetase plus maturation logic are visible; a UMED maturation-gap is corroborating.

*Negative:* Absence is not antibacterial-negative (bioactivity is extract-level). Transporter/cyclase tokens (LanT/LanC-like) also appear in unrelated contexts, so they do not alone establish a lanthipeptide.

*Claim-safety:* Tier-2 class-supporting: require precursor + class-defining synthetase (LanB/LanC or LanM) to call the class. The UMED maturation-gap is a corroborating, not defining, signal; confirm by HMM/BLAST and LC-MS/MS.

### lassopeptide <span class="small">(MMC-010 — Lasso peptide cassette)</span>

**Detects:** `lassopeptide, lasso peptide`

Detects lasso-peptide RiPPs — lassopeptide / 'lasso peptide' wording — lariat-knot peptides matured by a cysteine-protease (B) and an ATP-dependent macrolactam synthetase (C), often with an RRE. Their threaded topology confers protease/thermal stability and varied bioactivity.

*Positive:* High-confidence RiPP cue when the lasso maturation constellation (B1/B2 + C, ± RRE) and a precursor are present together.

*Negative:* Absence is uninformative under partial scope. A label hit confirms class wording but not the threaded knot or the bioactivity, which still require structural confirmation.

*Claim-safety:* Tier-1 diagnostic at the class level only: the antiSMASH lasso label is reliable for class, but topology and activity remain capacity until shown by MS/NMR. Treat as a lasso-peptide capacity call.

### tomm_azole_ripp <span class="small">(MMC-011 — TOMM/azole RiPP cassette)</span>

**Detects:** `azole, tomm, cyclodehydratase, dehydrogenase, ripp`

Detects azol(in)e-containing RiPPs / thiazole-oxazole-modified microcins (TOMMs): azole, TOMM, cyclodehydratase, dehydrogenase, and RiPP tokens. A YcaO cyclodehydratase plus a flavin dehydrogenase install thiazole/oxazole heterocycles onto a ribosomal precursor (e.g., microcins, thiopeptides, cyanobactins). Crosswalk note: this is the TOMM/azole cassette (MMC-011) and is distinct from the indolocarbazole T43 trigger.

*Positive:* MRSA/antibacterial-track cue when a precursor, a YcaO/cyclodehydratase, and oxidation (dehydrogenase) logic are concordant, consistent with azole-heterocycle installation.

*Negative:* Absence is not antibacterial-negative. 'Dehydrogenase' and 'RiPP' are broad tokens, so a hit without the YcaO cyclodehydratase and a precursor is not a TOMM call.

*Claim-safety:* Tier-1 diagnostic but token-broad: require the YcaO cyclodehydratase + precursor to call a TOMM, and keep it separate from indolocarbazole (T43-IDC). Confirm by HMM/BLAST and LC-MS/MS heterocycle mass shifts.

### polyene_ptm_hsaf <span class="small">(MMC-012 — Polyene/PTM/HSAF cassette)</span>

**Detects:** `polyene, hsaf, maltophilin, tetramate, pks-nrps`

Detects polycyclic tetramate macrolactam (PTM) / HSAF-type antifungals: polyene, HSAF, maltophilin, tetramate, and PKS-NRPS tokens. These hybrid iterative PKS-NRPS systems build tetramate-containing macrolactams with broad antifungal activity, a recurrent mechanism in insect-associated actinomycetes.

*Positive:* Strong Candida/antifungal-track cue when a hybrid PKS-NRPS architecture with iterative module and tetramate-forming logic is confirmed.

*Negative:* Absence is not an antifungal-negative call (bioactivity is extract-level). 'Polyene' and 'tetramate' are broad tokens that also hit unrelated PKS contexts, so they are not alone a PTM/HSAF call.

*Claim-safety:* Tier-1 diagnostic gated on architecture: the diagnostic is the PTM hybrid PKS-NRPS, not the keyword. Confirm the hybrid architecture by domain analysis and antifungal fractionation before any HSAF/PTM class claim.

### siderophore_metallophore <span class="small">(MMC-013 — Siderophore/metallophore cassette)</span>

**Detects:** `siderophore, metallophore, nrp-metallophore, iron, ferric`

Detects iron/metal-acquisition metabolites — siderophore, metallophore, NRP-metallophore, iron, ferric tokens — covering NRPS and NRPS-independent siderophore systems that chelate Fe (and other metals) for nutrient uptake.

*Positive:* Supports siderophore/metallophore ecology and points to CAS / metal-limitation assays as the natural test; useful for ecological context.

*Negative:* Absence is uninformative; uptake genes are easily missed. 'Iron/ferric' tokens also hit uptake and regulatory genes unrelated to a biosynthetic siderophore.

*Claim-safety:* Tier-2 class-supporting and deliberately low-weight: siderophore capacity is widespread across actinomycetes and ecologically low-discrimination, so down-weight it in comparative and novelty claims. Confirm by HMM/BLAST and CAS assay.

### transporter_resistance <span class="small">(MMC-014 — Transporter/resistance cassette)</span>

**Detects:** `transporter, efflux, exporter, resistance, immunity`

Detects export/efflux/self-resistance/immunity wording near BGCs — transporter, efflux, exporter, resistance, immunity. These tokens are near-universal genomic background and are tracked for inventory completeness only.

*Positive:* Supportive context at most: a class-matched resistance gene beside a cognate BGC can corroborate a self-protection hypothesis, but only with class-specific concordance.

*Negative:* Absence means nothing — transport/resistance wording is everywhere. Presence equally proves nothing about activity or self-protection on its own.

*Claim-safety:* Tier-5 overinterpretation risk, inventory-only: never let this cassette drive a lead or support a self-resistance claim without class-specific, BGC-cognate evidence confirmed by curated HMM/BLAST.

### chitin_glycan_ecology <span class="small">(MMC-015 — Chitin/glycan ecology cassette)</span>

**Detects:** `chitinase, gh18, gh19, aa10, lpmo, glcnac, dasr`

Detects chitinolysis and GlcNAc-responsive regulation — chitinase, GH18, GH19, AA10/LPMO, GlcNAc, DasR — markers for chitin utilization and antifungal/insect-ecology hypotheses. Relevant to fungal-cell-wall degradation and to host-associated (e.g., bee/Hymenoptera) defensive ecology.

*Positive:* Supports antifungal/ecology hypotheses when assessed at whole-proteome scope, since these genes usually sit outside BGCs; DasR/GlcNAc context links the response to chitin sensing.

*Negative:* Absence under BGC-local-only scope is not a true null — chitinases are typically genome-dispersed, so scope must be confirmed before reading a zero.

*Claim-safety:* Tier-2 class-supporting and scope-sensitive: GH18/GH19/AA10 family calls are annotation first-pass and need HMMER/BLAST; any chitin-ecology inference requires confirmed whole-genome scope, not BGC-local counts.

## §XIII.3 · The twelve workbook scans

- **KCB_sweep** — Known-cluster-blast similarity sweep -\> RiQ novelty. KCB is a similarity signal, not a product identification.
- **RG_GMCI** — Reference-genome-guided multi-cluster integration: detects split-cluster pairs across contig breaks.
- **FLBR** — Fragment-linked biosynthetic rescue / LMPKS fragment set.
- **CCTT** — T43 diagnostic class triggers (18 families) feeding AB/AF/novelty.
- **CGAD** — Chitinase / glycan-active-domain ecology scan.
- **UMED** — RiPP maturation-machinery scan (proteases / transporters / maturation gaps).
- **EFLS** — Evidence-from-linkage scan: candidate co-localized pairs.
- **resistance** — Self-protection / resistance-tier scan.
- **bldA_TTA** — bldA-dependent TTA-codon developmental-control scan. NOT_APPLICABLE outside actinomycetes.
- **TFBS** — Transcription-factor binding-site motif scan (upstream region).
- **regulators** — Regulator-family census (cluster-situated + global regulators).
- **transporters** — Transporter-family census (ABC / MFS / efflux).

<div id="patch-notes" class="section vol" style="padding:40px 54px 110px;border-top:3px solid var(--rule);max-width:1180px;margin:0 auto">

# Patch Notes

*Chronological patch state for this edition, moved here from the front matter. Per-section currency is marked inline with (v9.7.X) tags throughout the volumes; this log records what has shipped and where the engine now stands.*

> **Patch-state note (engine is ahead of this edition's base grounding).** Most sections are grounded against
> **v9.7.34**; the engine has since advanced to **v9.7.91 / Mamey 1.9.91** (suite 1404 passed, 91 skipped). Shipped
> since the base: **\#28** (corroboration↔mobile, class-trigger axis) in **v9.7.35**; the **BSL-2 doctrine reframe**,
> the root **`SHA256SUMS.txt`**, and the **§I.6** scope fix in **v9.7.36**; **PC-12** (resistance axis — the T1
> self-protection tier gated on `class_concordant_groups`) **shipped in v9.7.37** — no longer in progress; the
> **RG-GMCI v2** arc — adjacency guard (**v9.7.38**), locus-number proxy + identity axis (**v9.7.39**),
> phantom-coordinate fix (**v9.7.40**), and the `gg ≥ 2` + product-class HIGH gates (**v9.7.74**); the **RG-GMCI
> hub-degree guard + co-cluster exemption + Bug A/B keying fixes** (**v9.7.42**) and the **`_blast_hits` locus-tag
> fix** (**v9.7.43**) — both in §IV.4; and the **B-series** shake-down patches: the **accession→SID/cohort resolver**
> (**v9.7.44**, §II.1), **dedicated AB/AF lead-board files** (**v9.7.45**, §VI.4), the **gene-by-gene Mode B verdict
> layer wired into gold-mode runs** (**v9.7.46**, §VI.5), the **verified cross-strain merge** (exercised v9.7.46,
> §VI.8), and **run↔bank cohort-label consistency** (**v9.7.74**, §II.1/§VI.8). **§IV.4, §II.1, §VI.4–VI.8** and the
> PC-12 sections (§V.4, §III.6, §IV.8, §VIII.4) have been re-based to this state; the remaining volumes still carry
> their v9.7.34 grounding and inline version tags, and await a full re-grounding pass. **v9.7.76–v9.7.84 (engine → 1.9.85):** the most consequential change is the **removal of the edge/full-contig scoring penalty in v9.7.84** — the scoring-mechanics passages in this edition (§IX scoring, the edge-penalty table rows, the fragmentation-penalty definition) have been *corrected in place* to reflect this, and scores are no longer comparable across the 1.9.84→1.9.85 boundary (re-score cohorts before comparison). Also shipped: the Mode B receipt persistence path (`ingest-receipts`, v9.7.84, →§VI.8), per-trigger CCTT workbook columns and the B3 KCB pivot (v9.7.84), and the read-only inspector commands (`doctor/inspect/explain/list-bgcs`, v9.7.83). The 189 double-nested span artifacts noted in QC have been cleared. **Honest scope note:** apart from the in-place scoring corrections, the volumes have NOT been re-verified against the v9.7.85 engine line-by-line — a full per-volume re-grounding pass remains a separate, tracked task. Treat any volume's inline `(v9.7.X)` tag as the authority for when that specific passage was last grounded.

**v9.7.85–v9.7.91 (engine → 1.9.91) — no scoring boundary since v9.7.84.** Everything in this span is output/packaging or test/tooling; AB/AF/novelty scoring, corrected-BGC counts, and tier gates are unchanged, so scores remain comparable across v9.7.84→v9.7.91 (the last scoring boundary was the edge/full-contig penalty removal at 1.9.84→1.9.85). **v9.7.92–v9.7.95 (engine → 1.9.95) — still no scoring boundary.** This span is figure-system and packaging only: `--mode standard` retired (aliases to gold), a uniform `gene_by_gene_all_bgcs` gold export, and the `cohort-figures` command with F/G/D series (`--series {F,G,D,all}`, 41 figures) plus regenerable base captions and a regulator/gene glossary. AB/AF/novelty scoring, corrected-BGC counts, and tier gates are unchanged, so scores remain comparable across v9.7.84→v9.7.95. Edition tag **v9.7.95 / v9.7.394 / engine 1.9.141**; per-volume re-grounding of the technical volumes against 1.9.95 remains a tracked task (inline (v9.7.X) tags are authoritative per passage). Shipped: the **manual-BLASTP worklist fix** (v9.7.91) — `candidate_blastp_rows` scored only `locus_tag + product`, but antiSMASH leaves `product` empty and puts function in `sec_met_domain`/`gene_functions`, so the worklist shipped empty on real strains; now non-empty (AS-XXX 0→110 rows, *S. spectabilis* type strain 0→147); new `kcb_closest_gene` / `kcb_bitscore` / `user_blastp_label` columns, conservative (rule-based-clusters‑confirmed gene names only). **Locus maps** now carry a per-arrow ctgN_M assembly locus label (horizontal when sparse, rotated 90° when dense; LS-2 6.0pt), and the **LS-2 font scan** was extended to `locus_map.py` (previously uncovered). A `verify_tier_derivation.py` tier-parity tool was added. Test suite 1393→1404 (+11 property tests). **Honest scope note:** the technical volumes below still carry their inline (v9.7.X) grounding tags and have not been re-verified line-by-line against 1.9.91 — a per-volume re-grounding pass remains a tracked task.

</div>
