# Compound Detection & Isolation Bench Guide — Format Exemplar

**Sapote-Mamey Bundle v9.7.96 | Layer C Reference Format**  
**[EXAMPLE: all strain IDs, compound names, and values below are illustrative. Replace with real data from Mamey package.]**  
Source reference: Multi-Strain Bench Guides v2, Actinomycetes Project, May 2026.

---

## Cover / Strain Registry Block (multi-strain guide)

```
Compound Detection & Isolation Bench Guides
[Collection name] · [N] strains · [Date] · [Any taxonomy corrections noted here]

| Strain | Taxonomy | Host | Location | Assembly | BGCs (corr.) | MIBiG highlights |
|---|---|---|---|---|---|---|
| [StrainID] | [Genus sp.] | [Host] | [Location] | [Tier (X%)] | ~[N] | [Top hits: compound N% · compound N%] |
```

Taxonomy correction notes go here if genus was updated from v1 to v2.

---

## Per-Strain Bench Guide Format

### [StrainID] — [Taxonomy] · [Host] · [Location]
**Assembly:** [Good/Moderate/Poor/Very poor] ([X]% interior)  
**Corrected BGCs:** ~[N] corrected ([N] raw)  
[Any correction note, e.g., "Corrected from Pseudonocardia sp. (v1)"]

**Strain overview** (2–3 sentences): genus, genome size, screen result, biosynthetic highlights, any genus-specific precedents (e.g., "Saccharopolyspora biosynthetic precedents include erythromycin, spinosyn").

---

### Sub-section 1: Known / Reference BGCs (positive expression controls)

These BGCs have ≥60% MIBiG similarity and should produce under standard conditions. Use them as metabolic activity markers before investing in novel BGC isolation.

| | [Compound A] · [N%] | [Compound B] · [N%] | [Compound C] · [N%] | [Compound D] · [N%] |
|---|---|---|---|---|
| **BGC / MIBiG%** | BGC-NN · N% | BGC-NN · N% | BGC-NN · N% | BGC-NN · N% |
| **Compound class** | [class] | [class] | [class] | [class] |
| **Est. MW (Da)** | [~N Da (estimate)] | [N–N Da range] | [exact if known] | [N Da] |
| **UV / Vis** | [λ nm] | [no chromophore] | [triple band: 304+318+334] | [N nm] |
| **Colour / CAS** | [colony colour or CAS+/–] | [colourless; no CAS] | [yellow pigment in crude] | [earthy odour — GC-MS] |
| **Extraction** | [media, days, °C; solvent; SPE] | [media, days; solvent; note if polar extraction required] | [media, days; solvent; note polyene = n-BuOH] | [Headspace SPME; GC-MS] |
| **LC-MS mode** | ESI+ [M+H]+ m/z [N]; [key neutral loss] | ESI+/– [MW range]; [diagnostic ion] | ESI– preferred; triple UV band diagnostic | GC-MS; m/z [N] base; RI match required |
| **Key assay** | [MRSA MIC / Candida MIC / enzymatic] | [target + IC50 range] | [Candida MIC + C. auris] | [Olfactory detection; GC-MS confirm] |
| **Induction hint** | [standard / OSMAC step] | [note if bldA T4 — 21-day fermentation + phosphate depletion] | [high aeration; extended] | [constitutive; no special conditions] |
| **Safety** | [standard handling] | [⚠ potent mitochondrial toxin — fume hood always] | [moderate cytotox; gloves] | [very low toxicity; GRAS] |

**Completeness rules for this table:**
- MW flagged as "(estimate)" unless from an isolated compound of ≥70% MIBiG similarity.
- UV field = exact λ if known class; "no chromophore — rely on MS" otherwise.
- Colour/CAS: colony colour if pigmented; "CAS assay" if siderophore; "none" if colourless.
- Safety: "⚠ potent mitochondrial toxin — fume hood" for antimycin/ETC inhibitors; "⚠ DNA-alkylating — fume hood" for enediyne/PBD; standard handling note for unknowns.
- If bldA T4: note explicitly in Induction hint row; add "(T4 — 21-day fermentation + phosphate depletion required)" to the cell.
- ENE/IDC/cytotoxic class: Safety row must include ⚠ and specific handling instruction.

---

### Sub-section 2: Novel / Highest-Priority BGC Candidates

These BGCs have <50% MIBiG similarity and are the primary discovery targets.

| BGC# | Size (kb) | Product type | MIBiG% | Closest reference | Priority |
|---|---|---|---|---|---|
| BGC-NN | N kb | [class] | N% | [compound name] | HIGH |
| BGC-NN | N kb | [class] | N% | [compound name] | MED |
| BGC-NN | N kb | [class] | N% | [compound name] | LOW |

**Priority assignment:**
- HIGH: Interior/Arch A or B + AB ≥ 50 or AF ≥ 40 + any CCTT trigger, OR Interior/Arch A + AB ≥ 65.
- MED: Edge/Arch C + CCTT trigger, OR Interior/Arch A + AB 40–49 without CCTT.
- LOW: Full-contig/Arch D, or no CCTT + AB < 40.

**Per-HIGH-BGC extraction/detection paragraph:**

> **BGC-NN** ([class description]): MIBiG% [N%] vs [closest reference compound] — [1 sentence on structural relationship]. Extraction: [medium, temp, days; solvent; SPE note]. Detection: [UV λ or MS handle; MW range; isotope pattern if halogenated]. Special note: [any caveat — edge truncation / TTA T4 gating with specific protocol / ENE [E-signal] note / §34 trap / pH-lability for spirotetronate / polar extraction for nucleoside].

Examples of special notes:
- TTA T4: "BGC is bldA-gated (TTA_tier T4) — standard 7-day ISP2 is insufficient; use R5 medium, phosphate depletion at day 7, 21-day total fermentation."
- Spirotetronate: "Tetronate ring is acid-labile (pH <4.5) — run pH 4.0 vs pH 7.0 parallel fractions before bioassay to confirm class."
- ENE: "T43-ENE fires — ene_KS vs hglE-KS disambiguation required by HMMER before any wet-lab; [E-signal] note applies if confirmed enediyne."
- §34 KCB mismatch: "KCB [score] reflects [N] MIBiG hits dominated by T2PKS references despite T1PKS annotation — t2ks/t2clf domain disambiguation required before compound-class assignment."
- New class: "ranthipeptide class — KCB=0 reflects class absence from MIBiG 4.0, not compound-class absence; polar extraction + MALDI-TOF + HRMS for unusual amino acid residues."
- Edge truncation: "BGC is Edge-truncated — class signal only; do not invest in full isolation until long-read sequencing resolves boundary."

---

### Sub-section 3: Fermentation Strategy

One paragraph per strain. Template:

> **[Genus] sp. · [medium] · [°C] · [rpm].** [Screen result and what it means — e.g., "Candida−, MRSA− — production requires elicitation beyond standard ISP2."]. [Known BGC positive controls and expected output — e.g., "Kyamicin (100% MIBiG) should produce constitutively — use earthy geosmin smell as metabolic activity marker."].
>
> OSMAC sequence (when screen-negative): (1) ISP2 standard; (2) low-phosphate medium; (3) low-nitrogen medium; (4) [genus-specific C source — inositol for IolR-active *Saccharothrix*, GlcNAc for DasR-active strains, mannitol/glycerol for most Streptomyces]; (5) co-culture with *Bacillus subtilis* spores.
>
> Priority extraction targets: [BGC-NN] ([class]): [solvent] at [pH]; [UV/MS handle]. [BGC-NN] ([class]): [solvent]; [handle]. [Long-read note if POOR/VERY_POOR: "Long-read sequencing strongly recommended before committing isolation resources to the [N] fragmented PKS clusters."] Dereplication priority: subtract [known compound(s)] before reporting novel hits.

---

## Example — AS-XXX (Saccharopolyspora sp., illustrative)

> **AS-XXX** | Saccharopolyspora sp. | Bombus sp. (bumblebee) · New Jersey  
> Assembly: GOOD (82% interior) | Corrected BGCs: ~30 corrected (33 raw)

### Sub-section 1: Known / Reference BGCs

| | Migrastatin-like · 90% | Kyamicin · 100% | HSAF-class · 66% | Geosmin · 100% |
|---|---|---|---|---|
| BGC / MIBiG% | BGC-08 · 90% | BGC-14 · 100% | BGC-24 · 66% | terpene BGC · 100% |
| Compound class | T1PKS macrolide (actin inhibitor) | Lanthipeptide RiPP antibacterial | NRPS/T1PKS/terpene PTM (antifungal) | Sesquiterpene earthy odorant |
| Est. MW (Da) | ~495 Da (migrastatin exact) | ~2,200 Da (lanthipeptide range) | 500–600 Da (HSAF: 531) | 182.26 Da (exact) |
| UV / Vis | 240–260 nm (conjugated diene) | 210–230 nm (amide backbone) | 305 nm strong; 270 nm shoulder | No chromophore — GC-MS only |
| Colour / CAS | Colourless→pale yellow in solution | Colourless; ninhydrin: purple | Colourless→pale yellow; no CAS | Earthy odour detectable at 5 ppt |
| Extraction | ISP2, 10–14 d, 28°C; EtOAc pH 6; C18 semi-prep | ISP2, 7 d; boiling H2O (polar); Sep-Pak C18 SPE | ISP2, 7–10 d; EtOAc pH 6–7; C18 semi-prep | Headspace SPME; GC-MS; Kovats RI = 1723 |
| LC-MS mode | ESI+ [M+H]+ m/z 496; [M+Na]+ 518; macrolide ring-opening MS/MS | ESI+ multiply charged [M+2H]2+ [M+3H]3+; −18 Da dehydrations | ESI+ [M+H]+ ~532; HRMS tetramate carbonyl; neutral loss 114 Da | GC-MS preferred; m/z 112 (base); m/z 182 (M+); RI match required |
| Key assay | Cell migration (wound scratch HeLa); actin polymerisation; cytotox HeLa IC50 | MRSA MIC screen; Gram-pos. spectrum; VRE MIC | Candida MIC (ceramide synthase target) · C. auris; HeLa selectivity | Olfactory detection; positive = metabolic activity confirmed |
| Induction hint | Good assembly → reliable; 10–14 d fermentation; standard ISP2 | Standard fermentation; 100% MIBiG — should produce constitutively | Possible candidate for screen-negative → OSMAC required | High cell density OD >4; constitutive; detect early in growth |
| Safety | Cytostatic expected | Low cytotox expected | Unknown — treat as cytotoxic until tested | Very low toxicity; GRAS odorant |

### Sub-section 2: Novel Candidates

| BGC# | Size (kb) | Product type | MIBiG% | Closest ref. | Priority |
|---|---|---|---|---|---|
| BGC-11 | 128.9 | NRPS/T1PKS/T3PKS/HR-T2PKS | 15% | Skyllamycin D/E | HIGH |
| BGC-21 | 68.9 | Thioamide-NRP/NRPS/HR-T2PKS | 30% | Colibrimycin | HIGH |
| BGC-13 | 54.0 | T1PKS | 33% | Butyrolactol A | MED |
| BGC-20 | 51.0 | NRP-metallophore/NRPS | 10% | Cinnapeptin | MED |

> **BGC-11** (largest BGC in entire dataset, 128.9 kb; rare HR-T2PKS machinery; 4 BGC classes combined): Extract with EtOAc (pH 5); run C18 HPLC; UV 430 nm trace (aromatic PKS chromophore expected); HRMS full scan; GNPS molecular networking. 15% MIBiG = high novelty.
>
> **BGC-21** (thioamide-NRP; second HR-T2PKS-containing cluster; rare thioamide moiety): Extract with EtOAc; C18 semi-prep; check for thioamide UV fingerprint (~320 nm). 30% MIBiG = likely structurally distinct from colibrimycin.

### Sub-section 3: Fermentation Strategy

> **Saccharopolyspora sp. · ISP2 or oatmeal broth, 28°C, 200 rpm.** Screen-negative (Candida−, MRSA−) — elicitation required beyond standard ISP2. Kyamicin (100% MIBiG) should produce constitutively — use earthy geosmin smell as metabolic activity marker; if absent, culture is not growing productively. OSMAC protocol: (1) ISP2 standard; (2) low-phosphate; (3) low-nitrogen; (4) 2% glycerol as sole C source; (5) co-culture with *Bacillus subtilis* spores. BGC-11 (128.9 kb, HR-T2PKS hybrid): target EtOAc fraction at UV 430 nm — aromatic PKS chromophore expected. BGC-21 (thioamide-NRP): look for UV ~320 nm band in polar fraction. Long-read sequencing not needed — assembly already good (82%). Dereplication priority: subtract erythromycin/spinosyn (genus precedents) and geosmin before reporting novel hits.

---

---

## Alternate format — Deep Single-Strain Bench Guide (Path B)

The matrix format above is for multi-strain guides. When a single strain warrants
a full bench workup (a top antibacterial or antifungal lead), use this deeper
per-strain structure instead. Source reference: Extended BGC Guide Path B,
Actinomycetes Project, May 2026. Nine numbered sections per strain:

```
### Bench Guide #[N] — [StrainID] | [priority BGC(s)]   [Assembly tier (X% interior)] | Bioassay: [result]
[One-line strain headline — what makes it bench-ready and what the priority compound class is.]

Priority BGC: [BGC-NN (class) + BGC-NN (class)]   Class: [...]   Size: [N kb]   [Known N% / Novel]

bldA/TTA tier analysis:
  [Tier 1–4 per priority BGC, with the consequence: e.g. "Tier 2 (1–2 TTA codons)
  — solid medium preferred"; if T4: "21-day fermentation + phosphate depletion
  required, R5 medium".]

Section 2 — Culture conditions:
  | BGC target | Conditions |
  | BGC-NN ([class]) | [medium]; [°C]; [days]; [rpm]; [volume]; [inoculum] |
  [one row per priority BGC + any positive-control/siderophore BGC to separate out]

Section 3 — Extraction protocol:
  | Step | Protocol |
  | Step 1 — [mycelium/broth] ([BGC]) | [centrifuge; solvent ×N; partition pH; evaporate] |
  [CAS plate assay row if a siderophore BGC must be dereplicated out]

Section 4 — Chromatography:
  | Target | Column | Gradient | Expected fraction | Detection |
  | BGC-NN [class] | C18 RP | [H2O/ACN gradient, time] | [% ACN window] | [UV λ; ESI± m/z] |

Section 5 — Detection & dereplication:
  [GNPS molecular networking targets; reference standards to compare against;
  cross-strain shared-family comparison if applicable; which fractions to subtract
  as housekeeping/known.]

Immediate next experiment: 1) [first concrete step]  2) [second]  3) [third]
  [A numbered 2–4 step sequence the bench scientist runs first — concrete, ordered.]

MOA confirmation assay: [the specific mechanism-of-action assay — e.g. "Boyden
  chamber cell-migration assay vs migrastatin-sensitive line"; "CsrA EMSA"; "MRSA
  broth microdilution MIC (USA300)"; "Candida spheroplast lysis for sphingolipid
  disruption"; "in vitro 50S translation inhibition".]

Assembly/claim caveat: [what cannot be claimed; full-contig/edge BGCs to treat as
  class-signal-only; housekeeping clusters to subtract; naming reconciliation note;
  "do not claim novel compound until LC-MS/MS distinguishes from [known]".]

Key references: [Author Journal Year (PMID) — what it covers]; ... — Verified-bucket only.
```

### Required elements that distinguish Path B from the matrix format

- **bldA/TTA tier analysis is its own section** — and must state the *consequence*
  (medium choice, fermentation length), not just the tier number.
- **MOA confirmation assay is a named field** — the specific assay tied to the
  predicted mechanism, not a generic "test for activity".
- **Immediate next experiment is a numbered ordered sequence** — what the bench
  scientist does first, second, third. This is the single most-used part of the
  guide; make it concrete.
- **Key references cite only Bert-Mode Verified-bucket entries** (see
  `docs/BERT_MODE_PROTOCOL.md` and `examples/citation_library_exemplar.md`).
- **Separate discovery targets from housekeeping** — siderophores (CAS assay),
  pigments (flaviolin/geosmin), and ε-PL are dereplicated out, never counted as
  bioactivity leads.

### When to use which format

| Situation | Format |
|---|---|
| Whole collection, comparison across strains | Multi-strain matrix (top of this file) |
| One strain getting a full experimental workup | Deep single-strain (Path B, above) |
| Top AB or AF lead from DAPR | Deep single-strain, always |

---

*Bench Guide Exemplar | Sapote-Mamey v9.7.96 | 2026-06-09  
*[EXAMPLE FILE — all strain data and compound values are illustrative placeholders unless explicitly marked otherwise.]*
