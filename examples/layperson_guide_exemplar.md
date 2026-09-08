# Layperson-Ranked BGC Guide — Format Exemplar

This file shows the required format for the Layperson-Ranked BGC Guide deliverable.  
Source: 16-Strain Cohort BGC Guide — **[EXAMPLE: all values, habitat names, and strain data are illustrative placeholders, not real project data]**

---

## Cover / Header Block (global guide)

```
Layperson-Ranked BGC Guide
[Collection name] | [Project name]
antiSMASH [version] | MIBiG [version] | Fragmentation-corrected BGC counts | [Date]
[Habitat breakdown: e.g., 1 Mushroom · 20 Hymenoptera · 5 Bryophyte · 1 Lichen]
[Quality note: e.g., Verified Literature Deep Dive applied throughout. All citations directly verified.]
```

Assembly quality thresholds table:

| Tier | Interior % | Interpretation |
|---|---|---|
| Good | ≥70% | Raw ≈ corrected; BGC claims reliable |
| Moderate | 45–69% | Minor correction; most interior BGCs reliable |
| Poor | 20–44% | Corrected count only; edge/full BGCs unreliable |
| Very poor | <20% | Raw count unreliable; interior BGCs only defensible |

Corrected BGC formula: **Interior + 0.5×Edge + 0.25×Full-contig**

---

## Global Ranked Top Targets Table (multi-strain guides)

| Rank | Strain | Habitat | Assembly | Key BGC(s) | Why it ranks here | Next experiment |
|---|---|---|---|---|---|---|
| #1 | [StrainID] | [Habitat] | Good (82%) | BGC-08 [class] | [2–3 sentence reason] | [specific action] |
| #2 | ... | | | | | |

---

## Per-Strain Section Format

### [StrainID] — [Habitat]

**Strain header block:**

| Field | Value |
|---|---|
| Genome | [X.XX Mb] |
| Contigs | [N] |
| Raw BGCs | [N] |
| Corrected BGCs | [N] |
| Interior % | [X.X%] |
| Assembly | [Good/Moderate/Poor/Very poor] |
| Bioassay | [MRSA+/Candida+/Not specified/etc.] |

**Narrative** (2–3 sentences explaining why this strain is interesting in plain language):

> [Example narrative — illustrative only: Best clean-chemistry strain in the cohort. BGC-08 is a transAT-PKS hybrid fused to a lassopeptide — a rare and complex architecture with antibacterial precedent. BGC-24 carries an NRPS-T1PKS scaffold with antifungal potential. Assembly is reliable (82% interior).]

**Top 5 BGC table:**

| BGC | Class | Size | Novelty | Layperson headline |
|---|---|---|---|---|
| BGC-08 | transAT-PKS + RiPP hybrid | 99 kb | Known (90%) | [Example] Large hybrid assembly-line BGC; antibacterial precedent; clear LC-MS detection handle |
| BGC-11 | NRPS/T1PKS complex | 129 kb | Novel | [Example] Largest BGC in strain; complex hybrid architecture; high novelty |
| BGC-24 | NRPS + T1PKS | 49 kb | Possibly known (66%) | [Example] Antifungal scaffold candidate; lipid-biosynthesis inhibitor class precedent |
| BGC-21 | T2PKS + thioamide | 69 kb | Novel | [Example] Divergent aromatic polyketide; genuinely novel scaffold |
| BGC-05 | NAPAA | 39 kb | Known (100%) | epsilon-Poly-L-lysine; antibacterial polycation — **[NAPAA: housekeeping; excluded from AB/AF priority tracks; bench-detectable as QC marker]** |

**Assembly/claim caveat** (1–3 sentences, mandatory):

> [Example: BGC-08 (90% MIBiG similarity) likely encodes a compound in a known class — structural novelty possible. BGC-11 and BGC-21 are genuinely novel. Assembly is reliable (82% interior).]

**Immediate next action** (1–3 sentences, specific):

> [Example: C18 LC-MS on EtOAc extract, days 4 and 7; GNPS molecular networking; bioassay-guided fractionation for BGC-08 (antibacterial) and BGC-24 (antifungal) leads.]

---

## Cross-Habitat Statistics Table (multi-strain guides)

*[EXAMPLE — n=4 per group, 16-strain cohort, illustrative values only]*

| Metric | Habitat-A (n=4) | Habitat-B (n=4) | Habitat-C (n=4) | Habitat-D (n=4) |
|---|---|---|---|---|
| Total corrected BGCs | 84 | 96 | 76 | 108 |
| Mean corrected BGCs/strain (all) | 21.0 | 24.0 | 19.0 | 27.0 |
| % novel (<50% MIBiG) | 50% | 78% | 80% | 84% |
| Good assemblies (≥70% int.) | 1 | 2 | 1 | 2 |
| Very poor assemblies | 1 | 1 | 1 | 0 |

---

## Citation Library Section

Follows per-strain sections. For each referenced compound class:
- Discovery citation (PMID, DOI, experimental evidence type)
- MOA citation
- BGC citation
- Any 2024+ heterologous expression or structural update

Format: PNAS-style (Author Year Title Journal Vol:Pages DOI | PMID | Evidence type)

---

## Claim-safety footer (mandatory)

> This document is a genome-mining guide and workflow deliverable. Compound identities are genome-mining hypotheses unless confirmed by LC-MS/MS isolation. Always use language such as "candidate", "predicted", or "may encode" in manuscripts unless metabolomics or isolation data confirm the compound. BGC names follow antiSMASH [version] / MIBiG [version] annotations. Corrected BGC counts must be used for all cross-strain quantitative comparisons.

---

## Format notes for new users

- The strain header block is a table, not prose.
- The narrative is 2–3 sentences maximum; no jargon; no abbreviations without definition.
- The BGC table has up to 5 rows showing the most notable BGCs. NAPAA (housekeeping) BGCs may appear in the table but must be explicitly labelled [NAPAA] and are excluded from the AB/AF priority tracks — they are not discovery leads.
- The layperson headline must be one plain sentence a non-specialist can understand. **Name the compound class.** "Large PKS cluster" is not acceptable. "Spirotetronate-class polyketide antibiotic with anti-MRSA precedent" is correct.
- The claim caveat must mention assembly quality and MIBiG similarity for any "known" compound.
- The next action must be specific: not "run LC-MS" but "C18 LC-MS; watch migrastatin-like m/z (MW ~495); GNPS networking."
- For very poor assemblies, the caveat must say "Long-read sequencing urgently recommended" and note which BGCs are defensible.
- Novelty % = antiSMASH knownclusterblast highest MIBiG cluster similarity. If not available from the Mamey package, estimate from KCB cumulative score context and note as "(estimated)".

---

## Worked Example — Per-Strain Card (illustrative; matches reference output quality)

*[EXAMPLE: AS-XXX illustrative card based on Saccharopolyspora sp. reference implementation]*

---

### AS-XXX — Hymenoptera

| Genome | Contigs | Raw BGCs | Corrected | Interior % | Assembly | Bioassay |
|---|---|---|---|---|---|---|
| 7.16 Mb | 57 | 33 | 30 | 81.8% | Good | Not specified |

Best clean-chemistry strain in the Hymenoptera set. BGC-08 is a migrastatin/iso-migrastatin-like transAT-PKS hybrid fused to a lassopeptide — a rare and complex architecture encoding an anti-invasion candidate with a clear LC-MS detection path. BGC-11 is a giant novel NRPS/PKS/HR-T2PKS (129 kb). BGC-24 carries an HSAF/10-epi-HSAF antifungal scaffold. Assembly is reliable (82% interior).

| BGC | Class | Size | Novelty | Layperson headline |
|---|---|---|---|---|
| BGC-08 | transAT-PKS + lassopeptide | 99 kb | Known (90%) | Migrastatin/iso-migrastatin-like hybrid; anti-cancer/invasion precedent; clear LC-MS target |
| BGC-11 | NRPS/T1PKS/HR-T2PKS | 129 kb | Novel | Giant complex hybrid; largest BGC in strain; rare T2PKS architecture |
| BGC-24 | NRPS + T1PKS | 49 kb | Possibly known (66%) | HSAF/10-epi-HSAF antifungal scaffold; sphingolipid biosynthesis inhibitor precedent |
| BGC-21 | thioamide-NRP + NRPS + HR-T2PKS | 69 kb | Novel | Rare colibrimycin-like T2PKS; 30% MIBiG — genuinely divergent |
| BGC-05 | NAPAA | 39 kb | Known (100%) | epsilon-Poly-L-Lysine — housekeeping polycation; bench-detectable positive control [NAPAA: excluded from AB/AF discovery tracks] |

**Assembly/claim caveat:** BGC-08 (90% MIBiG) likely encodes a migrastatin analogue — structural novelty possible but class is known. BGC-11 and BGC-21 are genuinely novel. Assembly is reliable; all major BGCs are interior.

**Immediate next action:** C18 LC-MS on EtOAc extract; watch migrastatin-like m/z (MW ~495 for migrastatin); GNPS molecular networking; CAS assay for BGC-21 siderophore context.

---

## Citation Library Format

Each compound class cited in the guide needs a verified bibliography entry. Format per entry:

```
[Compound class name]
Strains in dataset: [StrainID BGC# (N% MIBiG, edge status)]

[1–2 sentence class summary: structure, MOA, BGC highlights]

[Discovery]
Author(s) (Year). Title. Journal Vol(Issue):Pages. DOI: https://doi.org/... | PMID: XXXXXXXX | PMCID: PMCXXXXXXXX | Evidence: [Experimental / Review / Structural] — [one sentence summary of evidence]

[Mode of action]
Author(s) (Year). Title. Journal. DOI | PMID | Evidence: [...]

[BGC identification]
Author(s) (Year). Title. Journal. DOI | PMID | Evidence: [...]

[Most recent update (2020+) if available]
Author(s) (Year). Title. Journal. DOI | PMID | Evidence: [...]
```

**Rules:**
- Every PMID and DOI must be verified against PubMed or DOI.org before inclusion.
- Evidence type is mandatory: "Experimental", "Review", or "Structural" (cryo-EM, X-ray, NMR).
- BGCs in the dataset linked to each compound class must be listed at the top of the entry.
- Minimum: Discovery + MOA + BGC. Maximum: 4 entries per compound class unless clinical data exist.

---

## PNAS-Style Reference List

Copy-pasteable formatted citations. Format:

> Author(s) (Year) Title. *Journal* Vol(Issue):Pages. https://doi.org/[DOI]

One entry per line. All authors listed. Italicise journal name. Include DOI as full URL. No PMIDs in this list (PMIDs only in the citation library section above).

---

*Sapote-Mamey Bundle v9.7.96 | Format exemplar — 16-strain placeholder cohort, illustrative values only | 2026-06-09*
