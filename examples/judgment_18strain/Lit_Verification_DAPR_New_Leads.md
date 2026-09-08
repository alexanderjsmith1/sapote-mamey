# Literature Verification — DAPR New-Lead Activity Associations

**Actinomycetes Project** · Sapote judgment layer
Purpose: citation-back the class→activity associations newly added to the DAPR boards (judgment pack §1–§2) before they harden into the bundle. Feeds `G1_Literature_Index`.

> **Scope of what is verified.** Each entry verifies what the **named reference compound / class** does in the published literature. It does **not** assert that our BGC produces that compound — our calls remain KnownClusterBlast nearest-cluster, class-level hypotheses. The verification confirms the *if-this-class-then-this-activity* link the framework relies on.

## Verification table

| Lead (our locator) | Class / nearest cluster | Verified activity + mechanism | Producer (type) | Tier | Key references |
|---|---|---|---|---|---|
| SID-XXX BGC050; SID-XXX BGC047; SID-XXX BGC049 | PTM tetramate macrolactam / **HSAF (dihydromaltophilin)** | **Antifungal.** Inhibits filamentous fungi via sphingolipid-biosynthesis interference; in *Candida albicans* acts through β-tubulin binding → ROS-mediated apoptosis. Distinct mode of action from azoles/polyenes. | *Lysobacter enzymogenes* (also PTMs across diverse actinobacteria incl. *Streptomyces*) | **VERIFIED** | Yu et al. 2021 *Appl Environ Microbiol* 87:e03105-20; Du-lab biosynthesis studies (PMC6017996); Lou et al. PTM/HSAF mechanism |
| SID-XXX BGC002 (+ SID-XXX BGC040, SID-XXX BGC041) | β-lactam / **carbapenem MM4550** (olivanic acid family) | **Antibacterial + β-lactamase-inhibitory (dual).** Carbapenem β-lactam; C8-sulfonated olivanic-acid-type; cell-wall target. | *Streptomyces olivaceus* / *S. argenteolus* ATCC 11009 | **VERIFIED** | Hood, Box & Verrall 1979 *J Antibiot* 32:295-304; MM4550 cluster in *S. argenteolus* (PubMed 24420617, 2014); co-occurrence study, *mSphere* 2025 |
| SID-XXX BGC006 | clavam / **clavulanic acid** | **β-lactamase inhibitor** (weak intrinsic antibacterial); clinically paired with β-lactams. | *Streptomyces clavuligerus* | **VERIFIED** | Reading & Cole 1977 *Antimicrob Agents Chemother*; Pérez-Llarena et al. 1997 *J Bacteriol* 179:2053 (ccaR) |
| SID-XXX BGC043; SID-XXX BGC030 | lipopeptide / **A54145** | **Antibacterial (Gram-positive).** Calcium-dependent 10-membered cyclic lipodepsipeptide; daptomycin relative; membrane-active. | *Streptomyces fradiae* NRRL 18160 | **VERIFIED** | Boeck & Wetzel 1990 *J Antibiot*; Miao et al. 2006 *Microbiology* (BGC); Baltz 2021 *J Ind Microbiol Biotechnol* 48:kuab020 (review) |
| SID-XXX BGC044 | glycopeptide / **teicoplanin** | **Antibacterial, anti-MRSA.** Vancomycin-family glycopeptide; inhibits cell-wall biosynthesis by binding D-Ala-D-Ala / lipid II; VanS-type self-resistance (Tei3). | *Actinoplanes teichomyceticus* ATCC 31121 | **VERIFIED** | Parenti et al. 1978 *J Antibiot* 31:276-283; Somma et al. 1984 *Antimicrob Agents Chemother* 26:917; Yushchuk et al. 2022 *Int J Mol Sci* 23:15713 |

## Polyene & antifungal-class verification (antifungal board §2)

| Lead (our locator) | Class / nearest cluster | Verified activity + mechanism | Producer (type) | Tier | Key references |
|---|---|---|---|---|---|
| SID-XXX BGC004 | **filipin** (pentaene polyene) | **Antifungal** (also a sterol probe). Ergosterol binding → membrane pores. Cluster regulator PteF (PAS-LuxR) co-controls filipin **and oligomycin** — matching SID-XXX carrying both. | *Streptomyces avermitilis* | **VERIFIED** | Vicente et al. (PteF, *S. avermitilis*); polyene mode of action, Merck/AEM reviews |
| SID-XXX BGC004; SID-XXX BGC003 | **candicidin / FR-008** (heptaene aromatic polyene) | **Antifungal.** PABA-starter aromatic polyene macrolide; ergosterol binding; ~205 kb / 21-gene cluster, PAS-LuxR regulator FscRI. | *Streptomyces griseus* IMRU 3570 / *Streptomyces* sp. FR-008 | **VERIFIED** | Gil & Campelo-Díez 2003 *Appl Microbiol Biotechnol* 60:633; FscRI regulation studies |
| SID-XXX BGC031+008+032 | **nystatin** (tetraene polyene) | **Antifungal**, esp. *Candida*. Binds ergosterol → transmembrane channels → K⁺ leakage → cell death; closely related to amphotericin B. | *Streptomyces noursei* ATCC 11455 | **VERIFIED** | Brautaset/Zotchev *nys* cluster; Brown & Hazen (discovery); polyene MoA reviews |
| SID-XXX BGC022; SID-XXX BGC030/042 | **linearmycin** (linear aminopolyol polyene) | **Antifungal + antibacterial.** Lytic membrane-targeting; active vs *S. aureus*, *C. albicans*, *Aspergillus*; lyses *Bacillus*. | *Streptomyces* sp. | **VERIFIED** | Sakuda et al. 1995/96 *Tetrahedron Lett* / *J Chem Soc Perkin Trans*; Stubbendieck & Straight 2017–18 |
| SID-XXX BGC038 | **mediomycin** (linear aminopolyol polyene) | **Antifungal + antibacterial** (linearmycin/ECO-02301/neotetrafibricin family). | *Streptomyces* spp. | **VERIFIED** | Caffrey et al. 2016; Zhang et al. 2017 (linear polyene reviews) |

Polyene mechanism (class-level): binding to ergosterol via the conjugated-double-bond face forms hydrophilic channels → ion leakage → fungal death; affinity for cholesterol explains mammalian toxicity. The PAS-LuxR cluster regulator (PimM/FscRI/PteF/NysRIV/AmphRIV) is conserved across polyene clusters — corroborating the framework's polyene marker clue. PTM/HSAF antifungal activity is further corroborated by ikarugamycin-type PTMs (e.g. *S. zhaozhouensis*) active against *Aspergillus*/*Candida* and MRSA.

## Cohort-specific notes
- **SID-XXX carbapenem + clavulanate co-occurrence is literature-supported.** Recent work documents *Streptomyces* isolates carrying both clavulanic-acid-like and MM4550-like carbapenem BGCs, with the carbapenem contributing both antimicrobial and β-lactamase-inhibitory activity and the clavam contributing inhibition — i.e., a natural antibiotic + inhibitor pairing (*mSphere* 2025). SID-XXX fits this documented pattern, which makes it independently interesting rather than a coincidental double hit.
- **A54145 is reported in only a handful of *Streptomyces*.** Bioinformatic surveys note the A54145 BGC in a small number of *Streptomyces*; finding two copies here (SID-XXX, SID-XXX) is consistent with that rarity and worth confirming on re-assembly.
- **HSAF self-resistance / physiology caveat.** Besides antifungal activity, HSAF has a documented iron-chelating / oxidative-stress-modulating role in its producer. This does not weaken the antifungal call but is worth noting when interpreting any co-located resistance/iron genes.

## Tier outcome
All new-lead associations — antibacterial (carbapenem MM4550, clavulanate, A54145, teicoplanin), the HSAF/PTM antifungal class, and the polyene board (filipin, candicidin, nystatin, linearmycin, mediomycin) — are **VERIFIED** against primary literature. No entries fell to Partial. The DAPR boards in the judgment pack §1–§2 are fully citation-backed and cleared to harden into the bundle.

## Claim-safety (carried)
Class-level hypotheses only; KCB nearest cluster is a similarity anchor, not an identification. Bioactivity is the extract-level project default (MRSA + Candida); per-BGC activity requires fractionation. References verify compound-class activity, not production by our strains.
