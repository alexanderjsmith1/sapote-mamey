# Fermentation Card — Format Exemplar + Regulator→Induction Lookup

**Sapote-Mamey Bundle v9.7.96 | Layer C fermentation-planning deliverable**
**[EXAMPLE: all strain IDs, BGC numbers, and values below are illustrative. Replace with real data from the Mamey scan output (TFBS counts, RiQ, bldA tiers).]**
Source reference: AS-XXX / AS-XXX Fermentation Cards, Actinomycetes Project, May 2026.

---

## Purpose

The Fermentation Card is the one-page deliverable that turns the pipeline's TFBS
regulator hits into a concrete wet-lab fermentation plan. It answers the bench
scientist's question: *"I have this strain — what media do I grow it on to switch
the interesting BGCs ON, and how do I detect what comes out?"*

The pipeline already computes the inputs: `scan_tfbs()` produces per-BGC regulator
hits, RiQ comes from the antiSMASH evidence, and bldA/TTA tiers come from
`scan_blda_tta()`. The card's job is the **translation layer** — regulator → induction
condition — plus ranking, dereplication verdicts, and class-specific extraction.

---

## Regulator → induction condition lookup (the translation layer)

This is the table that converts a TFBS hit into a fermentation instruction. It
extends monolith §10 with the copper/oxidative/NAD/SARP regulators used in the
reference cards. Score thresholds are actinomycete-validated; confirm applicability
for other groups.

| Regulator | TFBS family (source_scans) | Signal sensed | Induction condition | Typical protocol |
|---|---|---|---|---|
| **DmdR1** | DmdR_iron_box_like | Fe(II) repression | Iron starvation | Chelex-ISP2 + EDTA 200 µM + deferoxamine 50 µM; 28°C 14d |
| **FuR** | FuR_like | Ferric uptake | Iron starvation | Chelex-treated media; CAS assay readout |
| **Zur** | Zur_like | Zinc uptake | Zinc limitation | Low-Zn minimal media or TPEN 1–10 µM |
| **DasR** | DasR_like_palindrome | GlcNAc/chitin | GlcNAc induction | GlcNAc 10 mM in minimal media; 10d liquid; 28°C |
| **CopR** | *(add — see below)* | Copper | Cu-limitation | Minimal + CuSO₄ 0.1 µM (vs 10 µM standard); 14d |
| **OsdR** | OsdR (regulator scan) | Developmental/hypoxia | Solid sporulation ONLY | ISP2 agar 14–21d full sporulation; NEVER liquid |
| **BldD** | BldD_like | Developmental master | Solid media, stationary | ISP2 agar 14–21d; scrape + MeOH extract |
| **SARP** | SARP_BTAD_like | Pathway activator | P-limitation | Low-phosphate minimal (KH₂PO₄ 0.05 g/L); 14d |
| **AfsQ1** | *(add — see below)* | N/P stress | N/P limitation | Minimal (NH₄Cl 0.5 g/L, KH₂PO₄ 0.05 g/L); 14d |
| **CatR** | *(add — see below)* | Peroxide stress | H₂O₂ oxidative | H₂O₂ 0.1 mM pulse, then remove; 14d |
| **HypR** | *(add — see below)* | Peroxide stress | H₂O₂ oxidative (higher) | H₂O₂ 0.5 mM; or MMC 0.1 µg/mL 2h pulse |
| **LexA** | LexA_SOS_like | DNA damage / SOS | DNA-damage / anaerobic | MMC 0.1 µg/mL pulse OR sealed N₂/CO₂ 95:5 |
| **ANR / FNR** | ANR_FNR_like | Oxygen tension | Anaerobic | Sealed flask N₂/CO₂ 95:5; pre-reduced media; 14d |
| **NrtR** | *(add — see below)* | NAD⁺ pool | NAD-limitation | Niacin-restricted minimal media; 14d |
| **IolR** | IolR_like | Inositol | Inositol induction | Inositol-supplemented minimal media |
| **PhoP** | PhoP_box_like | Phosphate | P-limitation | Low-phosphate minimal media |
| **GBL/AdpA** | GBL_AdpA_like | Quorum/γ-butyrolactone | Stationary + conditioned medium | ISP2 14d + 10% conditioned medium |

**Regulators not yet in `TFBS_MOTIFS` (Release 2 motif additions):** CopR (copper-responsive),
AfsQ1 (the AfsQ1/AfsQ2 N/P two-component target — currently only the protein is in
REGULATOR_PATTERNS, not a DNA motif), CatR and HypR (peroxide regulators), NrtR
(NAD-responsive). Until calibrated motifs are added, these are reported from the
protein-level regulator scan (REGULATOR_PATTERNS / antiSMASH annotation) rather than
the upstream-motif scan, and the card should mark them `(protein-level call)`.

---

## Card format (matches AS-XXX / AS-XXX)

```
[StrainID] — [Taxonomy]
[Host/source] · [bioactivity flags] · antiSMASH [ver] · [date]

PRIORITY BGC TARGETS (ranked by isolation priority)
| BGC | ★ rating | Compound class | bldA | Dereplication (RiQ) | Key TFBS → induction |
| [N] | ★★★★★ | [class] | T[1-4] | [VERIFY-FIRST/POSSIBLY NOVEL/POTENTIALLY NOVEL/STRUCT. VARIANT/CLOSE] RiQ=[x] | [Regulator(score) → condition] |

INDUCTION CONDITIONS — Ranked by BGC coverage
| Condition | Protocol | Targets (BGCs) | Screen |
| [1. Iron starvation] | [protocol] | [BGC list with regulator scores] | [readout assay] |
[one row per induction condition that fires; order by how many BGCs it covers]

EXTRACTION METHODS BY COMPOUND CLASS
| Compound type | Broth extraction | Mycelium | Diagnostic screen |
[one row per compound class present]

DEREPLICATION VERDICTS
| BGC | Verdict | RiQ | Action |
[CLOSE (RiQ≥0.95): CAS/HRMS only, do not isolate · VERIFY-FIRST: HRMS vs reference first ·
 STRUCT. VARIANT (RiQ 0.73–0.85): isolate after priority unknowns · POSSIBLY NOVEL (0.50–0.73):
 standard isolation + full Mode B · POTENTIALLY NOVEL (<0.50): highest discovery priority]

STANDARD CULTURE CONDITIONS
| Parameter | Standard | Notes |  [temp/rich media/induction media/durations]

SOLID MEDIA REQUIRED: [BGCs with OsdR/BldD — never expressed in liquid]
bldA T4 BGCs: [list, or "NONE — all T1–T2"]  [T4 = bldA-gated; needs 21d + phosphate depletion]

[footer: All assignments bioinformatic predictions — confirm by LC-HRMS and bioassay]
```

---

## Ranking rules (★ rating)

The star rating combines novelty (RiQ, lower = more novel = higher priority),
bioactivity potential (AB/AF auto-score, CCTT triggers), and tractability (assembly
tier, bldA tier):

- **★★★★★** — top isolation priority: Interior/Arch A + (AB ≥ 55 or AF ≥ 45 or CCTT trigger) + RiQ ≤ 0.75
- **★★★★** — Interior/Arch A–B + moderate AB/AF + RiQ ≤ 0.80, or any POTENTIALLY NOVEL (RiQ < 0.50)
- **★★★** — Interior/Arch B + CCTT or STRUCT. VARIANT worth confirming
- **★★** — standard isolation candidate; Interior with a clear class but no exceptional signal
- **—** (no stars) — CLOSE/dereplicate-only (RiQ ≥ 0.95) or housekeeping (siderophore by CAS only)

`★UPGRADED` tag: a BGC promoted above its base rating because of a specific extra
signal (extra tailoring genes confirmed, a diagnostic CCTT trigger, a pigment marker)
— always state the reason inline.

---

## Worked example (illustrative — format reference only)

### AS-XXX — *Streptosporangium* sp.
Bumblebee-associated · MRSA-active · Candida-active · antiSMASH 8.0.4

```
PRIORITY BGC TARGETS
| BGC | ★ | Compound class | bldA | Dereplication | Key TFBS → induction |
| 7  | ★★★★★ | Enduracididine NRPS (lipid II inhibitor) | T1 | VERIFY-FIRST RiQ=0.730 | AfsQ1 → N/P limitation |
| 20 | ★★★★  | YcaO-TOMM (MOST NOVEL)                  | T1 | POTENTIALLY NOVEL RiQ=0.257 | CatR → H₂O₂ 0.1 mM |
| 25 | ★★★★  | NAPAA/RiPP hybrid (poly-Lys+laccase)    | T1 | POSSIBLY NOVEL RiQ=0.663 | FuR×6 → Fe-limitation |
| 4  | ★★    | TOMM RiPP (dual cyclodehydratase)       | T1 | POSSIBLY NOVEL RiQ=0.501 | OsdR=25.8 → SOLID SPORULATION ONLY |
| 2  | —     | Coelichelin siderophore                 | T1 | CLOSE RiQ=0.981 | FuR → Fe-lim (CAS assay only) |

SOLID MEDIA REQUIRED: BGCs 4, 8 (bldA T1 but OsdR/BldD gated) — OsdR=25.8 on BGC 4 = never expressed in liquid
bldA T4 BGCs: NONE — all T1–T2 (≤2 TTA codons)
```

---

## Required claim-safety footer (mandatory)

Every Fermentation Card ends with:

> All assignments are bioinformatic predictions from genome mining. Compound-class,
> regulator, and induction predictions require confirmation by LC-HRMS and bioassay.
> RiQ-based novelty and TFBS-based induction are planning aids, not production proof.

---

*Fermentation Card Exemplar | Sapote-Mamey v9.7.96 | 2026-06-09
*[EXAMPLE FILE — all strain data illustrative unless explicitly marked.]*
