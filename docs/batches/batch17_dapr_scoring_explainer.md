# DAPR Scoring Explainer
**Antibacterial / antifungal dual-axis scoring in plain English**

**v9.7.149a** | Source: `docs/DAPR_CLASS_FRAMEWORK.md` | Last updated: 2026-06-29

---

## What DAPR is

DAPR (antibacterial / antifungal dual prioritization) is the scoring vocabulary Sapote uses to rank BGCs by bioactivity potential. It operates on two independent axes — AB (antibacterial) and AF (antifungal) — so a BGC that looks like a broad-spectrum compound can score high on both, while one that looks like a polyene (purely antifungal) scores high on AF only.

**Key principle:** All DAPR calls are class-level hypotheses. Extract-level bioactivity (MRSA + *Candida*) is the project default. DAPR never licenses a per-BGC activity claim or a compound-identity claim.

**Verification status:** The class→activity associations used on the 18-strain cohort are literature-verified — antibacterial (carbapenem MM4550, clavulanate, A54145, teicoplanin, formicamycin, surugamide, glycinocin), antifungal polyenes (filipin, candicidin, nystatin, linearmycin, mediomycin), and the HSAF/PTM tetramate class. See `examples/judgment_18strain/Lit_Verification_DAPR_New_Leads.md` for the citation set.

---

## The two axes

| Axis | What it scores | Default target |
|------|---------------|----------------|
| **AB** (antibacterial) | Biosynthetic capacity consistent with compounds active against bacteria | MRSA (*Staphylococcus aureus* ATCC 43300) |
| **AF** (antifungal) | Biosynthetic capacity consistent with compounds active against fungi | *Candida albicans* (extract-level default) |

Scores combine: KCB anchor, BGC class, self-resistance tier, boundary completeness (interior > edge > full-contig), and architecture confidence. Weights are defined in `resources/bioactivity_axes.json`.

---

## Antifungal buckets (highest confidence first)

| Bucket | Representative compounds | BGC/marker signature |
|--------|------------------------|---------------------|
| **Polyenes** | nystatin, amphotericin, natamycin, candicidin, filipin, rimocidin, linearmycin, mediomycin | Large modular T1PKS; DH-rich modules (polyene pattern); PAS-LuxR regulator. **Not arylpolyene** — that is a pigment, not an antifungal polyene. |
| **Peptidyl nucleosides** | nikkomycin, polyoxin, pacidamycin, mureidomycin | Chitin-synthase inhibition; nucleoside pathway genes; UV ~260 nm |
| **PTM tetramate macrolactams** | HSAF, dihydromaltophilin, ikarugamycin, frontalamide, alteramide | Hybrid PKS-NRPS with ornithine A-domain; sphingolipid biology target |
| **Bacillus lipopeptides** | iturin, bacillomycin, fengycin, plipastatin | Large NRPS, lipid tail — mostly *Bacillus*; atypical in *Streptomyces* |
| **Phenylpyrroles** | pyrrolnitrin | prnABCD genes; halogenated tryptophan precursor |
| **Phenazines** | phenazine-1-carboxylic acid, pyocyanin | phz core genes; redox mechanism; coloured product |
| **Polyether ionophores** | nigericin, monensin, lasalocid, salinomycin | cis-AT T1PKS + epoxidase — **cytotoxic caution** (route to cytotoxicity track) |
| **Macrolide (ATP-synthase)** | oligomycin | Large T1PKS — **cytotoxic caution** |

---

## Antibacterial buckets

| Bucket | Representative compounds | BGC/marker signature |
|--------|------------------------|---------------------|
| **Aminoglycosides** | streptomycin, neomycin, kanamycin, gentamicin, hygromycin | DOIS/aminotransferase/GT pathway; APH/AAC resistance genes |
| **Glycopeptides (anti-MRSA)** | vancomycin, teicoplanin, A40926 | NRPS core; halogenase; VanHAX self-resistance cluster |
| **β-lactams / carbapenems** | thienamycin, MM4550, cephamycin, clavulanate | CarB/CarC genes; β-lactam synthetase; PBP self-protection |
| **Lipopeptides (membrane)** | daptomycin, A54145, glycinocin | NRPS; acidic residues; lipid starter; Ca-dependent motif |
| **Lanthipeptides / thiopeptides** | nisin, mersacidin; thiostrepton, nosiheptide | LanB/C or LanM genes (lanthipeptide); YcaO/azole (RiPP thiopeptide) |
| **Aromatic T2PKS** | formicamycin, fasamycin, tetracyclines | T2PKS core + cyclases; TetR/efflux resistance |
| **Macrolides** | erythromycin, tylosin, pikromycin | Modular T1PKS + glycosyltransferase; Erm resistance |
| **Aminocoumarins** | novobiocin, clorobiocin | Gyrase target; aminocoumarin biosynthetic genes |
| **Phosphonates / moenomycin** | fosfomycin, platensimycin | PepM phosphonate genes; terpenoid-PKS hybrid; phosphoglycolipid |
| **Orthosomycins** | evernimicin, avilamycin | Glycosylated oligosaccharide scaffold |
| **Liponucleosides** | tunicamycin, muraymycin, caprazamycin | MraY logic; polar extraction; nucleoside-lipid conjugate |

---

## Routed OUT — do not score as AB/AF leads

These classes are routed away from the antibacterial/antifungal track. They get their own tracks or are excluded from comparative leads.

| Class | Route | Why |
|-------|-------|-----|
| **Indolocarbazoles** (staurosporine, rebeccamycin, K-252) | → cytotoxicity track | Non-selective kinase inhibition; not antibacterial/antifungal at non-toxic concentrations |
| **Enediynes** (kedarcidin, calicheamicin) | → [E-signal] + cytotoxicity | DNA-damaging; BSL-2 relevant; not a clean antibiotic |
| **Aureolic acids** (mithramycin, chromomycin) | → cytotoxicity | Antitumour / DNA-binding |
| **Anthracyclines** (cosmomycin, doxorubicin-class) | → cytotoxicity | Non-selective DNA intercalation |
| **Ansamycins** (geldanamycin, herbimycin) | → cytotoxicity | Hsp90 inhibition; not antibacterial/antifungal |
| **Angucycline-diazo** (kinamycin) | → cytotoxicity | Reactive diazo; DNA strand break |
| **Aminoquinone** (streptonigrin) | → cytotoxicity | Non-selective oxidative mechanism |
| **Siderophores** (coelichelin, desferrioxamine, enterobactin) | → ecological / iron track | Iron-withholding; not direct antibiotic; acknowledge ecological role |
| **arylpolyene** (flexirubin pigments) | → exclude from antifungal | Oxidative-stress defense; not an antifungal polyene despite the name |

**Important on arylpolyene:** antiSMASH flags both real polyenes and arylpolyene pigments as "polyene." Check for `arylpolyene` in the antiSMASH class label and DH-poor module count. Real polyenes are DH-rich (each DH domain generates one double bond in the polyene chromophore); arylpolyenes are phenolic pigments with completely different biosynthesis.

---

## How DAPR interacts with self-resistance tier

Self-resistance genes (resistance cassettes in or near the BGC) are a strong secondary signal. Sapote uses a three-tier self-resistance scale:

| Tier | Meaning | Effect on DAPR score |
|------|---------|---------------------|
| **T1** | Source-derived self-resistance — resistance gene in the BGC itself, same contig | +bonus (strong signal of active antibiotic production in the native host) |
| **T2** | Genomic resistance — resistance gene on a different contig, same genome | +smaller bonus |
| **T3** | Transporter-only — efflux or ABC transporter without a mechanism-specific resistance gene | no bonus (transporters are ubiquitous) |

A BGC with a VanHAX self-resistance cluster (glycopeptide producer) scores much higher AB than an identical PKS without resistance genes, because the resistance gene indicates the producer evolved alongside the antibiotic.

---

## DAPR output in the workbook

DAPR boards appear in the workbook as sheets C1 and C2 (applied by `apply_dapr_boards.py` after Sapote judgment):

- **C1 — Antibacterial priority board:** ranked BGCs by AB score; confidence tier; reasoning trail
- **C2 — Antifungal priority board:** ranked BGCs by AF score; confidence tier; reasoning trail

The render layer (`render_dapr_boards.py`) produces a markdown/CSV summary for the deliverable.

---

## In Mode B: how to use DAPR

When writing §13 (Antibacterial/antifungal relevance) in full Mode B:

1. Identify which bucket the BGC's KCB anchor maps to (use the tables above)
2. State the bucket and mechanism explicitly: "Biosynthetic capacity consistent with polyene-class antifungals; ergosterol-membrane disruption mechanism"
3. Note the self-resistance tier if relevant: "T1 self-resistance (ABC transporter + P-glycoprotein efflux, co-located)"
4. Apply the routing rules: if the KCB anchor or product class falls in the Routed OUT list, redirect: "Routes to cytotoxicity track per DAPR standing rules; excluded from AB/AF lead ranking"
5. Never claim per-BGC activity — "Extract-level bioactivity assumed (MRSA + *Candida* default); fractionation required for compound-level assignment"

---

## Common DAPR mistakes

**Scoring arylpolyene as antifungal polyene:** check the antiSMASH class label. "Arylpolyene" in the products field is a pigment; don't score it on the AF polyene track.

**Scoring siderophores on the antibacterial track:** desferrioxamine, coelichelin, and related iron-chelators are ecological (iron-withholding competition), not direct antibiotics. Route to the ecological track and acknowledge iron-competition mechanism.

**Double-counting the cytotoxic bucket as both AB and AF:** enediynes and anthracyclines are cytotoxic at sub-antibiotic concentrations. Don't route them through both AB and AF — route them OUT.

**Missing the PTM / HSAF route:** HSAF (heat-stable antifungal factor from *Lysobacter enzymogenes*) and related tetramate macrolactams appear as PKS-NRPS hybrids. The marker is the ornithine A-domain + T43-PTM CCTT trigger. Don't file these as generic NRPS — they belong on the AF tetramate bucket.

---

## See also

- **Authoritative source:** `docs/DAPR_CLASS_FRAMEWORK.md`
- **Verified literature backing:** `examples/judgment_18strain/Lit_Verification_DAPR_New_Leads.md`
- **CCTT trigger for tetramate (HSAF):** MMK-CCTT-012 in `bundle_support/registry_inventory_v1.9.4.json`
- **CCTT trigger for polyene:** MMK-CCTT-016 in `bundle_support/registry_inventory_v1.9.4.json`
- **DAPR tools:** `render_dapr_boards.py`, `apply_dapr_boards.py`, `build_dapr_rescue_sheets.py`
- **Bioactivity axes map:** `resources/bioactivity_axes.json`
