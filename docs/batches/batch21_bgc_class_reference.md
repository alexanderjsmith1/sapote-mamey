# BGC Class Reference
**What each biosynthetic class looks like and what to watch for in Mode B**

**v9.7.149a** | Source: `docs/GLOSSARY.md`, `docs/DAPR_CLASS_FRAMEWORK.md`, `docs/GUIDE/06_Concepts_QandA.md` | Last updated: 2026-06-29

---

## How to use this reference

Find your BGC class. Read what the core genes look like, what KCB anchors are typical, what ecology signals to expect, and what Mode B mistakes are most common for this class. This is a working reference, not a textbook — it covers what actually comes up in Mamey output, not the full biochemistry.

---

## 1. Type I PKS (T1PKS) — modular polyketides

**What it is:** A multimodular assembly line where each module elongates the growing chain by one two-carbon unit. Each module contains one or more of: KS (ketosynthase), AT (acyltransferase), DH (dehydratase), ER (enoylreductase), KR (ketoreductase), ACP (acyl carrier protein).

**Core gene signatures:**
- Multiple KS domains (one per module, PF00109 family)
- AT domains (PF02801) — selects the extender unit (malonyl vs methylmalonyl)
- DH domains (PF00106) — dehydration; DH-rich modules → double bonds in product
- ER domains — rare; each ER produces a fully saturated carbon

**Trans-AT PKS:** A subclass where the AT is encoded by a standalone gene that acts in trans on all modules. Associated with complex products (lydicamycin, difficidin, bacillaene). KCB anchors from MIBiG often show "trans-AT" in the pathway description.

**Typical KCB anchors:**
- Polyenes: natamycin, nystatin, candicidin, amphotericin
- Trans-AT products: lydicamycin, difficidin, bacillaene, soraphen
- Macrolides: erythromycin, tylosin, rapamycin

**Ecology signals to check:**
- DH-rich modules (≥6 DH/KS ratio) → likely polyene (antifungal track)
- PAS-LuxR regulator flanking the cluster → polyene marker
- ER at unusual position → structural novelty signal; name the consequence in Mode B

**Mode B pitfalls:**
- Naming domains without connecting to structural consequence (floor violation; see batch16)
- Calling arylpolyene a polyene antifungal — check for `arylpolyene` in antiSMASH products label
- Missing the trans-AT signature — if the AT is a standalone gene, note it explicitly

---

## 2. Type II PKS (T2PKS) — aromatic polyketides

**What it is:** An iterative enzyme system that builds an aromatic ring scaffold. The minimal PKS is a heterodimer (KSα/KSβ) plus an ACP. A cyclase and a ketoreductase fold and aromatise the nascent chain.

**Core gene signatures:**
- KSα (chain-length factor, CLF): determines chain length
- KSβ (minimal PKS partner)
- ACP (discrete acyl-carrier protein)
- Ketoreductase + aromatase + cyclase genes

**Typical KCB anchors:**
- Antibacterial: tetracyclines, formicamycin/fasamycin, oxytetracycline
- Antitumour/cytotoxic: anthracyclines (doxorubicin-class), aureolic acids (mithramycin)
- Angucyclines: urdamycin, gilvocarcin, landomycin

**Ecology signals:**
- TetR-family regulator flanking → strong antibacterial routing signal
- Short (~20 gene) cluster with high KCB → likely known class

**Mode B pitfalls:**
- Conflating antibacterial T2PKS (formicamycin) with cytotoxic T2PKS (anthracyclines) — check the KCB anchor
- Anthracyclines and aureolic acids route OUT of the AB track to cytotoxicity; catch this in §13

---

## 3. NRPS — non-ribosomal peptides

**What it is:** A multimodular enzyme that assembles a peptide chain one amino acid at a time. Each module contains: C (condensation), A (adenylation, selects amino acid), T (thiolation/PCP, carries chain). Optional: E (epimerisation → D-amino acid).

**Core gene signatures:**
- A domains (PF00501) — substrate specificity determined by the Stachelhaus code (10 residues in the binding pocket)
- C domains (PF00668) — peptide bond formation
- T/PCP domains (PF00550) — tethers the chain
- TE domain (PF00975) — chain release; location and type affect product shape (lactonisation vs hydrolysis)

**Typical KCB anchors:**
- Antibacterial: vancomycin, daptomycin, A54145, glycinocin, surugamide, gramicidin
- Antifungal: iturin, bacillomycin, syringomycin (lipid tail NRPS)
- Siderophores: coelichelin, enterobactin, pyoverdine

**Ecology signals:**
- Lipid-starter unit + acidic residues + Ca-binding motif → membrane-targeting lipopeptide (antibacterial)
- No lipid start + hydroxamate/catecholate → siderophore; route to ecological/iron track
- Ornithine A-domain → HSAF/PTM family (antifungal, route to tetramate bucket)

**Mode B pitfalls:**
- Missing the Stachelhaus code analysis for substrate prediction — report the predicted substrate per A-domain
- Routing siderophores to the antibacterial track — check for NIS synthetase or hydroxamate markers
- Not noting the TE domain type — linear TE (hydrolysis) vs cyclising TE produces radically different scaffold shapes

---

## 4. Hybrid PKS/NRPS

**What it is:** A cluster where PKS and NRPS modules work on the same assembly line. The chain switches between polyketide elongation and peptide assembly in one biosynthetic pathway.

**Core signatures:** Mixed KS/AT/DH/KR/ACP (PKS) and C/A/T (NRPS) domains in contiguous ORFs.

**Key subtype — PTM (polycyclic tetramate macrolactams):**
- Ornithine A-domain (activates ornithine, unusual)
- Hybrid PKS-NRPS with a tetramic acid-forming TE
- CCTT trigger: T43-PTM
- Products: HSAF, dihydromaltophilin, ikarugamycin, frontalamide, alteramide
- Activity: broad-spectrum antifungal (sphingolipid target)

**Typical KCB anchors:** HSAF, lydicamycin, epothilone, bleomycin-class

**Mode B pitfalls:**
- HSAF from *Lysobacter* is the reference; flag that it's not bee-specific when citing Yu2007
- Bleomycin-class: route to cytotoxicity (glycopeptide-iron complex, DNA strand break)

---

## 5. RiPP — ribosomally synthesised and post-translationally modified peptides

**What it is:** A short peptide (precursor) encoded in the genome, then extensively modified by dedicated enzymes. Structural diversity comes from the modifications, not from NRPS module selection.

**Key subclasses:**

| Class | Marker gene | Signature | Examples |
|-------|------------|-----------|---------|
| Lanthipeptide class I | LanB + LanC | Lan-Dha bridges; MBL-fold LanC | Nisin, subtilin |
| Lanthipeptide class II | LanM | Same bridges; LanM bifunctional enzyme | Mersacidin, nukacin |
| Lanthipeptide class III | LanKC | Similar bridges; LanKC | Class III variously bioactive |
| Lasso peptide | LasB + LasC | Threaded ring | Streptomonomicin |
| Thiopeptide | YcaO | Azole rings; pyridine core | Thiostrepton, nosiheptide |
| Sactipeptide | Radical SAM | Cα-thioether bridges | Subtilosin A |
| Ranthipeptide | Radical SAM | Non-α-carbon thioether bridges | Novel / cryptic class |

**CCTT triggers:** T43-LAP (lasso), T43-LAN (lanthipeptide), T43-THI (thiopeptide)

**Mode B pitfalls:**
- Confusing lanthipeptide class I / II / III — they have different enzyme complements and different KCB anchors; look at the modifying enzyme genes (LanB + LanC vs LanM vs LanKC)
- Ranthipeptides are often KCB-dark — radical SAM is the marker; state "novel class candidate" rather than inferring a compound name
- Thiopeptides route to the antibacterial track; lanthipeptides may be antifungal, antibacterial, or both depending on class

---

## 6. Terpene

**What it is:** Built from isoprene units (C5) via terpene synthases. Sesquiterpenes (C15), diterpenes (C20), and sesterterpenes (C25) are most common in actinomycetes. Often combined with NRPS/PKS tailoring.

**Core gene signatures:**
- Terpene cyclase (PF01397 or PF03936) — distinctive fold
- Prenyl transferase — assembles the isoprenoid backbone
- P450 or oxygenase — tailoring

**Typical KCB anchors:** platensimycin, merochlorin, pentalenolactone, naphterpene, terrabactins

**Ecology signals:** Some terpenes are signalling molecules; others are antifungal or antibacterial. Platensimycin is a FabF inhibitor (antibacterial). Check DAPR bucket carefully.

**Mode B pitfalls:**
- Terpene claims are often low-confidence without close KCB anchors — flag Grade C/D more often here
- Platensimycin is in the phosphonate/FabF bucket (antibacterial); don't route to general antifungal

---

## 7. Enediyne

**What it is:** An extremely potent DNA-cleaving compound containing a 1,5-diyn-3-ene core (enediyne warhead). Two structural types: 9-membered ring (chromoprotein-associated; e.g. neocarzinostatin, kedarcidin) and 10-membered ring (uncomplexed; e.g. calicheamicin, dynemicin).

**Core gene signatures:**
- PKS with an iterative KS domain (ITES, distinct from modular T1PKS KS)
- Gene cassette for warhead biosynthesis (often ~35 genes)
- CCTT trigger: T43-ENE (enediyne KS motif)

**Claim handling — mandatory:**
- Tag with `[E-signal]` in Sapote output
- Route to cytotoxicity track, not antibacterial/antifungal
- Note BSL-2 relevance before any bulk fermentation planning
- Do not overclaim compound identity from KCB alone — enediyne BGCs diverge substantially

**Mode B pitfall:**
- The T43-ENE trigger fires on the iterative KS motif. Some hglE-KS clusters (glycolipid, not enediyne) fire a weaker signal. Check for the full enediyne cassette before routing to the enediyne track.

---

## 8. Phosphonate

**What it is:** Contains a C–P (carbon-phosphorus) bond. Rare and often highly bioactive. PepM (phosphoenolpyruvate mutase) is the hallmark enzyme that forms the C–P bond.

**Core gene signatures:**
- PepM (PF02222) — the defining marker
- Hydroxyethylphosphonate dioxygenase
- Often combined with NRPS or PKS tailoring

**Typical KCB anchors:** fosfomycin, phosphinothricin, phosphonothrixin

**Mode B:** CCTT trigger may fire (T43-PHO). Phosphonate compounds are often antibacterial (fosfomycin: MurA inhibitor). Check KCB anchor for routing.

---

## 9. Common class-specific pitfalls summary

| Class | Most common Mode B error |
|-------|-------------------------|
| T1PKS polyene | Calling arylpolyene a polyene antifungal |
| T2PKS | Not separating antibacterial vs cytotoxic anchors |
| NRPS | Routing siderophores to AB track |
| Hybrid PKS/NRPS | Not flagging HSAF scope (not bee-specific) |
| RiPP lanthipeptide | Mixing up class I/II/III modifying enzymes |
| RiPP thiopeptide | Missing the pyridine-core/azole ring markers |
| Terpene | Over-claiming compound identity from weak KCB |
| Enediyne | Not routing to cytotoxicity; missing the BSL-2 note |
| Phosphonate | Missing PepM as the diagnostic gene |

---

## See also

- **DAPR buckets (activity routing):** `batch17_dapr_scoring_explainer.md`
- **Claim-safety language:** `batch20_claim_safety_field_manual.md`
- **CCTT trigger registry:** `bundle_support/registry_inventory_v1.9.4.json`
- **Glossary (PKS/NRPS domains):** `docs/GUIDE/06_Concepts_QandA.md` Bank 78–84
- **DAPR class framework:** `docs/DAPR_CLASS_FRAMEWORK.md`
