# DELIVERABLE — Metabolomics Readiness (MR)

> **Filing.** `docs/modules/DELIVERABLE_MetabolomicsReadiness.md`.
> **Extends / references:** `DELIVERABLE_WetLabMatrix.md` (dereplication priority = Action score 4), `KNOWLEDGE_DiagnosticDomainCombos.md` (class call drives the defaults), Workbook Schema v1.0 (`Metabolomics_Readiness` sheet). **Do not restate the WL action scores — point to them.**
> **Precedence.** Parent monolith wins. This module owns the class→analytics default table and the polar-compound caveat.
> **Status:** `SCHEMA_BACKED` — `tools/build_metabolomics_readiness.py` emits `<strain>_Metabolomics_Readiness.csv` + the `Metabolomics_Readiness` sheet from the class→analytics table. (Sapote may still map by hand when no package is present.)
> **One-line purpose.** Prepare each lead for LC-MS / HRMS / UV / fractionation by giving the analyst expected MW range, ionization, UV handle, polarity, extraction route, and dereplication target — broad-class only, claim-safe.

---

## 1. When it is offered (Deliverable Offer Protocol)

Auto-build for every Full-Run Profile; the `Metabolomics_Readiness` workbook sheet is part of the Excel deliverable. Offer as a next-path whenever leads have a class call but no analytics plan. **Incomplete delivery** = naming a lead's class without its detection/extraction handle, or giving exact masses/formulas (forbidden — §37.4).

---

## 2. Inputs required

| Field | Feeds | Skip-not-fake |
|---|---|---|
| BGC class call (from `KNOWLEDGE_DiagnosticDomainCombos.md` + `manifest.json → products`) | row selection in the defaults table | no class → row marked `class unresolved`, no fabricated MW |
| Architecture grade (kernel M3) | confidence on the prediction | — |
| KCB top / RiQ (`_4_triage_board.csv`) | dereplication target + HRMS priority | — |
| Predicted polarity / heterocycle hints (Cys-loading, nucleoside, siderophore) | the **polar-compound caveat** | flag, don't assert structure |

---

## 3. Pipeline

`PROMPT_BACKED`: map each lead's class to the §3a defaults, then adjust for strain-specific evidence (e.g. DHB siderophore → CAS assay + iron-limited culture). To promote to `SCHEMA_BACKED`: `tools/build_metabolomics_readiness.py --package-dir <pkg>` emits the sheet.

---

## 3a. Class-level analytics defaults (PORTABLE COPY; authority: monolith §37.3)

| Class | MW range | Ionization | UV/Vis | Extraction |
|---|---|---|---|---|
| NAPAA | ~400–900 Da | positive likely | weak/moderate | EtOAc/BuOH, C18 |
| Lanthipeptide/RiPP | ~800–3,500 Da | positive likely | variable | SPE/C18, MeOH/water |
| Polyene PKS | ~700–1,300+ Da | pos/neg variable | strong polyene UV 300–400 nm | organic, UV-guided |
| NRPS peptide | ~500–2,500 Da | positive likely | variable | EtOAc/BuOH/C18 |
| Siderophore NRPS | ~500–1,500 Da | pos/neg; metal complexes | variable | **iron-limited culture, CAS assay** |
| Terpene/carotenoid | ~300–800 Da | APCI/positive | visible if carotenoid | nonpolar organic |
| Ectoine | ~142 Da | polar positive | weak | aqueous/polar |
| Peptidyl nucleoside | ~490–600 Da | positive; zwitterionic | **UV 262 nm** | **aqueous/polar; SAX pH 7.0; NOT C18-primary** |
| 14-membered macrolide | 500–900 Da | positive | weak ~280 nm | EtOAc/BuOH, C18 |
| 16-membered macrolide | 600–1,200 Da | positive | weak ~280 nm | EtOAc/BuOH, C18 |
| Large macrolide (≥24) | 800–1,500 Da | positive | variable | EtOAc/BuOH, C18 |
| Polyene macrolide | 700–1,300+ Da | pos/neg | strong UV 300–400 nm | EtOAc, C18, UV-guided |
| Linear polyketide | 400–1,200 Da | pos/neg | variable | EtOAc/BuOH broad |
| trans-AT polyketide | 500–1,500 Da | positive likely | variable | EtOAc/BuOH, GNPS networking |
| Aromatic PKS (anthracycline/tetracycline) | 400–900 Da | pos/neg | strong visible (often coloured) | EtOAc, C18, DAD-guided |
| Phosphonate | small, polar | neg often; **31P-NMR primary** | weak | **aqueous; ion-exchange; 31P-NMR before HRMS** |
| Enediyne | variable | handle as cytotoxic | UV variable | **SEC/UV-DAD; cytotoxicity readout** |

Last three rows extend §37.3 with classes the SID-XXX run surfaced.

**Polar-compound caveat (load-bearing).** Standard C18 reversed-phase **underrepresents or loses** polar/zwitterionic products — peptidyl nucleosides, siderophores, charged NRP fragments, **phosphonates**. When a lead predicts a polar product, explicitly flag that C18 crude extraction is insufficient and recommend aqueous/ion-exchange primary fractionation **before** HRMS dereplication.

---

## 3b. Per-BGC fields (the sheet)

`BGC # · Product class · Arch · Expected MW range · Ionization · UV/Vis · Polarity · Extraction recommendation · Dereplication target · HRMS priority · Bioassay pairing · Caveat`

---

## 4. Outputs & contract surface

`Metabolomics_Readiness` workbook sheet (Schema v1.0) + a top-targets block in the Deep Dive Synopsis + analytics lines on the Fermentation Card.

---

## 5. Acceptance checklist

- [ ] Every lead has MW range, ionization, UV, polarity, extraction, dereplication target.
- [ ] **No exact masses / formulas / structures** unless a named reference cluster with strong evidence supports it (§37.4) — broad ranges only.
- [ ] Polar/zwitterionic leads carry the C18-insufficient caveat.
- [ ] Bioassay pairing held at extract level.
- [ ] Contig-ID locators; affiliation = ; exactly 8 unique next-paths.

---

## 6. Knowledge inventory

| Piece | Owner |
|---|---|
| Class→analytics defaults | this module (portable copy of monolith §37.3) |
| Class call | `KNOWLEDGE_DiagnosticDomainCombos.md` |
| Dereplication priority | `DELIVERABLE_WetLabMatrix.md` (Action score 4) |
| Sheet schema | Workbook Schema v1.0 |

---

## 7. Worked next-paths closer (SID-XXX)

> Metabolomics readiness: BGC047 enediyne → SEC/UV-DAD + cytotoxicity (standard-SOP handling); BGC063 phosphonate → 31P-NMR primary, aqueous/IEX, C18-insufficient flag; BGC019/072 catecholate siderophore → iron-limited culture + CAS assay; BGC025/074 aromatic PKS → DAD-guided, coloured-band watch. Next paths:
> 1. Build the `Metabolomics_Readiness` sheet for all 12 leads.
> 2. Pair the 31P-NMR screen with GNPS LC-MS/MS as the strain's two decisive runs.
> 3. Flag every polar lead (phosphonate, siderophore) for IEX-first fractionation.
> 4. Cross-link each row to its Wet-Lab dereplication priority.
> 5. Promote to SCHEMA_BACKED with a sheet-writer tool.
