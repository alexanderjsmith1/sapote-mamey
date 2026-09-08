# Literature Verification — Routed-Out Classes (DAPR §2.5)

**Actinomycetes Project** · Sapote judgment layer
Purpose: citation-back the **routed-out** decisions — the classes deliberately *not* scored as antibacterial/antifungal leads — so the exclusions are as evidenced as the leads (`Lit_Verification_DAPR_New_Leads`). Feeds `G1_Literature_Index`.

> These BGCs are real, but their primary biology is cytotoxic (route to cytotoxicity, not MRSA/Candida leads) or ecological iron-acquisition (do not overcall as direct antibiotics). Scoring them as activity leads would overstate the cohort's antibacterial/antifungal yield.

## Cytotoxic-adjacent (route to cytotoxicity first)

| Class / our hits | Compound | Verified primary activity + mechanism | Routed-out rationale | Key references |
|---|---|---|---|---|
| Anthracycline — SID-XXX BGC035, SID-XXX BGC038 | **cosmomycin D** | Antitumor; DNA intercalation / DNA-damage; cardiotoxic class (doxorubicin family). Has antibacterial activity (MIC 0.01 µg/mL vs *S. aureus*) but is a DNA-damaging cytotoxic. | DNA-damaging antitumor — not a developable antibacterial; cardiotoxicity | Furlan et al. 2004 *J Antibiot* 57:647; Caetano et al. 2022 (cosP self-resistance) |
| Angucycline-diazo — widespread (SID-XXX, SID-XXX, SID-XXX, SID-XXX, SID-XXX, SID-XXX, SID-XXX, SID-XXX, SID-XXX, SID-XXX) | **kinamycin** | Antitumor; diazo/paraquinone → radical-mediated DNA damage (iron/H₂O₂/hydroxyl-radical dependent). | Radical DNA-damage cytotoxic; route to cytotoxicity | O'Hara et al. 2007 (kinamycin F mechanism); isolated from *S. murayamaensis* |
| Indolocarbazole — SID-XXX BGC049, SID-XXX BGC026, SID-XXX BGC047, SID-XXX BGC039, SID-XXX BGC042 | **rebeccamycin / K-252 (staurosporine)** | Antitumor; rebeccamycin = DNA topoisomerase I inhibitor, staurosporine/K-252 = protein-kinase inhibitor. | Topoisomerase / kinase antitumor; cytotoxic | Sánchez et al. 2006 (PubMed 16491358); indolocarbazole reviews |
| Hsp90 ansamycin — SID-XXX BGC050, SID-XXX BGC048 | **herbimycin / geldanamycin** | Antitumor; benzoquinone-ansamycin Hsp90 ATPase inhibitor → client-protein degradation; hepatotoxic. | Anticancer Hsp90 inhibitor; cytotoxic/hepatotoxic | Whitesell et al. 1994; Uehara et al. 1985 |
| Enediyne — SID-XXX BGC072/BGC033 | **kedarcidin** | DNA-cleaving chromoprotein enediyne; highly cytotoxic. | DNA-cleaving cytotoxic | enediyne literature (Hofstead, Leet) |
| Aminoquinone — SID-XXX BGC065 | **streptonigrin** | Antitumor; redox-active DNA damage. | Redox DNA-damage cytotoxic | streptonigrin literature |

## Ecological / siderophore (iron-withholding, not a direct antibiotic)

| Our hits | Compound | Verified role | Routed-out rationale | Key references |
|---|---|---|---|---|
| SID-XXX, SID-XXX, SID-XXX, SID-XXX, SID-XXX | **coelichelin** | Trishydroxamate ferric-iron chelator; siderophore for iron acquisition in *S. coelicolor*/*ambofaciens*; mediates microbial interactions. | Iron acquisition/competition is ecological/indirect — not a direct antibiotic | Lautru et al. 2005; Barona-Gómez et al. 2006; Patel et al. 2010 |
| SID-XXX BGC042, SID-XXX, SID-XXX | **desferrioxamine** | Trishydroxamate siderophore (also a pharmaceutical iron-chelator); ferric-iron uptake. | Iron-withholding, ecological | Barona-Gómez 2004; *des* cluster studies |
| SID-XXX BGC019, SID-XXX | **mirubactin** | NRPS siderophore (iron acquisition). | Ecological iron acquisition | mirubactin literature |

## Outcome
All routed-out classes are **VERIFIED** as cytotoxic-adjacent or ecological — the §2.5 exclusions hold. This protects the DAPR yield from being inflated by DNA-damaging antitumor agents or iron-acquisition systems. The boards in §1–§2 stand on the verified-active classes only.

*Claim-safety carried: nearest-cluster (KCB) similarity anchors, not identifications; bioactivity is the extract-level project default.*
