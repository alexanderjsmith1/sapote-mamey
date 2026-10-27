# DELIVERABLE — Metabolomics Readiness (MR)

> **Filing.** `docs/modules/DELIVERABLE_MetabolomicsReadiness.md`.
> **Extends / references:** `DELIVERABLE_WetLabMatrix.md` (dereplication priority = Action score 4), `KNOWLEDGE_DiagnosticDomainCombos.md` (class call drives the defaults), Workbook Schema v1.0 (`Metabolomics_Readiness` sheet). **Do not restate the WL action scores — point to them.**
> **Precedence.** The current user task and [assistant governance](../ASSISTANT_GOVERNANCE.md) govern actions. The current writer owns emitted defaults; this module retains separate historical/proposed analytics guidance, with independent scientific review required.
> **Status:** `SCHEMA_BACKED` — `tools/build_metabolomics_readiness.py` emits `<strain>_Metabolomics_Readiness.csv` + the `Metabolomics_Readiness` sheet from the class→analytics table. (Sapote may still map by hand when no package is present).
> **One-line purpose.** Prepare each lead for LC-MS / HRMS / UV / fractionation by giving the analyst expected MW range, ionization, UV handle, polarity, extraction route, and dereplication target — broad-class only, claim-safe.

---

## 1. When it is offered (Deliverable Offer Protocol)

The writer is not run by the engine. It is an optional step for a selected Full-Run Profile. Offer as a next-path whenever leads have a class call but no analytics plan. **Incomplete delivery** = naming a lead's class without its detection/extraction handle, or giving exact masses/formulas (forbidden — §37.4).

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

`PROMPT_BACKED`: map each lead's class to the §3a defaults, then adjust for strain-specific evidence (e.g. DHB siderophore → CAS assay + iron-limited culture). The writer already exists. Invoke `python tools/build_metabolomics_readiness.py --package-dir <pkg> --out-dir <dir>` for a CSV and a separate XLSX; it does not modify the master workbook. XLSX errors are caught and reported as skipped, so verify both requested files rather than treating exit zero as complete delivery.

---

## 3a. Historical/proposed class-level analytics defaults

The retained table is not a byte-for-byte or scientific calibration of the current writer's `CLASS_DEFAULTS`. Read the actual source and emitted rows for the selected helper; these broad class priors are not measured properties or an approved experimental plan for a focal locus. The current `base_class()` scans product plus comparator wording in a fixed precedence order, so a comparator label can determine the selected default. That selection is not independent class adjudication. Preserve unsupported or conflicting class assignments as holds; no scientific default is changed by this documentation clarification.

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
| Aromatic PKS (anthracycline/tetracycline) | 400–900 Da | pos/neg | strong visible (often colored) | EtOAc, C18, DAD-guided |
| Phosphonate | small, polar | neg often; **31P-NMR primary** | weak | **aqueous; ion-exchange; 31P-NMR before HRMS** |
| Enediyne | variable | handle as cytotoxic | UV variable | **SEC/UV-DAD; cytotoxicity readout** |

The last three rows extend the original table.

**Polar-compound caveat (load-bearing).** Standard C18 reversed-phase **underrepresents or loses** polar/zwitterionic products — peptidyl nucleosides, siderophores, charged NRP fragments, **phosphonates**. When a lead predicts a polar product, explicitly flag that C18 crude extraction is insufficient and recommend aqueous/ion-exchange primary fractionation **before** HRMS dereplication.

---

## 3b. Per-BGC fields (the sheet)

Current emitted columns: `locator`, `bgc_id`, `class`, `MW_range`, `ionization`, `UV_handle`, `polarity`, `extraction_route`, `dereplication_target`, `claim_ceiling`. Architecture, HRMS priority and bioassay pairing in the older proposed schema are not current writer columns.

---

## 4. Outputs & contract surface

`Metabolomics_Readiness` sheet in the writer's separate XLSX + a top-targets block in the Deep Dive Synopsis + analytics lines on the Fermentation Card.

---

## 5. Acceptance checklist

- [ ] Every lead has MW range, ionization, UV, polarity, extraction, dereplication target.
- [ ] **No exact masses / formulas / structures** unless a named reference cluster with strong evidence supports it (§37.4) — broad ranges only.
- [ ] Polar/zwitterionic leads carry the C18-insufficient caveat.
- [ ] Bioassay pairing held at extract level.
- [ ] Contig-ID locators are bound to source records; affiliation is supplied rather than invented; handback states the result and holds without a fixed next-action count.

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

> Metabolomics readiness: SID-XXX / <contig> / region<NNN> / BGC047 enediyne → SEC/UV-DAD + cytotoxicity (standard-SOP handling). SID-XXX / <contig> / region<NNN> / BGC063 phosphonate → 31P-NMR primary, aqueous/IEX, C18-insufficient flag. SID-XXX / <contig> / region<NNN> / BGC019 and BGC072 catecholate siderophore → iron-limited culture + CAS assay. SID-XXX / <contig> / region<NNN> / BGC025 and BGC074 aromatic PKS → DAD-guided, colored-band watch. Next paths:
> 1. Build the `Metabolomics_Readiness` sheet for all 12 leads.
> 2. Pair the 31P-NMR screen with GNPS LC-MS/MS as the strain's two decisive runs.
> 3. Flag every polar lead (phosphonate, siderophore) for IEX-first fractionation.
> 4. Cross-link each row to its Wet-Lab dereplication priority.
> 5. Inspect the existing writer’s CSV and separate XLSX against the requested output contract.
