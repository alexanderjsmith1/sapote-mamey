# Short ID Registry
**Project:** Sapote-Mamey Actinomycete Natural Product Discovery  
**Repository:** `sapote-mamey` (https://github.com/alexanderjsmith1/sapote-mamey)  
**Version:** 1.0 — 2026-06-08

---

## Naming rule

```
{PREFIX}_{species_epithet}_{strain_designator}
```

| Field | Rule |
|---|---|
| Prefix | `S_` for all benchmark *Streptomyces* strains; `SID` for project field isolates |
| Species epithet | Lowercase species name only (no subspecies, no authority) |
| Separator | Single underscore `_` |
| Strain designator | Collection code + catalog number. Dots → `_`. Hyphens → `_`. Spaces → removed. For GCA accessions: strip `.version` suffix and assembly name suffix entirely. |

**Rationale:** underscores are filesystem-safe and Python-identifier-safe; dots and hyphens are not. No special characters. GCA version suffixes are omitted because they change with genome updates and would break cross-version comparisons.

---

## SID field isolates

> *The reference-project field isolates (actinomycete collection) are **published in Chevrette et al. 2019**, with **genomes available as public NCBI data** — so their `SID####` identifiers may be listed openly here. (Earlier releases withheld them under a mistaken "unpublished" assumption; that has been corrected.) When you run this pipeline on your own collection, add your own strain IDs to this table using the naming convention above.*

---

## Benchmark strains (12 strains)

| Short ID | Full strain name | Key known chemistry | Collection | Dot/hyphen handling |
|---|---|---|---|---|
| `S_coelicolor_GCA008931305` | *Streptomyces coelicolor* A3(2) GCA_008931305.1 | Actinorhodin, CDA, prodigiosin, coelibactin | GCA accession | Strip `.1_ASM893130v1(4)` |
| `S_avermitilis_GCA000009765` | *Streptomyces avermitilis* MA-4680 GCA_000009765.2 | Avermectin, filipin | GCA accession | Strip `.2_ASM976v2` |
| `S_clavuligerus_ATCC27064` | *Streptomyces clavuligerus* ATCC 27064 | Clavulanic acid, cephamycin C | ATCC | No special chars |
| `S_collinus_CGMCC4_1623` | *Streptomyces collinus* CGMCC 4.1623 | Betalactone (BGC006) | CGMCC | Dot → `_` in `4.1623` |
| `S_fradiae_ATCC10745` | *Streptomyces fradiae* ATCC 10745 | Tylosin, neomycin (T43-AMC) | ATCC | No special chars |
| `S_gossypii_N2_109` | *Streptomyces gossypii* N2-109 | Unknown; RGGMCI case study | — | Hyphen → `_` |
| `S_drozdowiczii_JCM13580` | *Streptomyces drozdowiczii* JCM 13580 | Unknown; RGGMCI 3 fragments | JCM | No special chars |
| `S_laculatispora_Mut2` | *Streptomyces laculatispora* Mut2 | Unknown; RGGMCI negative control | — | `Mut2` kept as-is |
| `S_lanatus_JCM4588` | *Streptomyces lanatus* JCM 4588 | Betalactone (BGC028) | JCM | No special chars |
| `S_griseofuscus_DSM40191` | *Streptomyces griseofuscus* DSM 40191 | Unknown; 881 HIGH RGGMCI pairs | DSM | No special chars |
| `S_griseoluteus_JCM4765` | *Streptomyces griseoluteus* JCM 4765 | Lanthipeptide (BGC011, T43-LAN) | JCM | No special chars |

---

## Platform-specific notes

**When ChatGPT runs Mamey:** use the full strain identifier in `BGC_Master` Strain column (e.g., `Streptomyces_coelicolor_GCA_008931305.1_ASM893130v1(4)`). Claude converts to short ID automatically on merge.

**When Claude writes to workbook:** all sheets use the short ID as the strain key. Never use the full Mamey strain identifier inside the workbook.

**When publishing:** the short IDs appear in supplementary tables and the workbook deposited to Zenodo. The full strain names appear in the Methods section text.

---

## Disambiguation notes

`S_collinus_CGMCC4_1623` — the underscore in `4_1623` represents the catalog-number dot `4.1623`. This is NOT two separate fields; `CGMCC4_1623` is one atomic strain designator.

`S_laculatispora_Mut2` — `Mut2` is a strain designation from a mutagenesis series, not a collection catalog number. Kept as-is; no dots or hyphens to resolve.

`S_gossypii_N2_109` — `N2-109` is the strain designation; hyphen → underscore gives `N2_109`. The underscore is NOT a separator between `N2` and `109`; this is one atomic designator.

---

## Version history

| v | Date | Change |
|---|---|---|
| 1.0 | 2026-06-08 | Initial registry; 28 SID strains + 11 benchmark strains defined |
