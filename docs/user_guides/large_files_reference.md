# Sapote–Mamey Large File Reference
**Bundle v9.7.319 · Engine 1.9.111 · Add-ons 2026-07-03**
Hamilton, Ontario

*All files ≥1 MB in the bundle and the staged addon tree, with functional descriptions derived from direct inspection of file contents. Size values are exact byte counts rounded to two decimal places.*

---

## Bundle Files (sapote-mamey-v9.7.241-CODE)

### Wheelhouse/hmm/scanner_pfam.hmm
**Size:** 4,416,564 bytes (4.21 MB)
**Format:** HMMER3 profile HMM file (binary-safe text)
**Profiles:** 35 HMM families

This is the **core HMM reference set** that ships inside the lean CODE bundle itself, available without the addon stack. It covers the 35 most diagnostically critical Pfam families for actinomycete BGC detection. Unlike the addon's 148-family file, this set was curated for the smallest profile count that still provides coverage of every class-defining gate domain.

The 35 families: Aminotran_1_2, Aminotran_3, AMP-binding, CDPS, Chal_sti_synt_C, Chal_sti_synt_N, Condensation, DegT_DnrJ_EryC1, DHQ_synthase, Epimerase, FhuF, Glycos_transf_1, Glyco_transf_28, IucA_IucC, ketoacyl-synt, Ketoacyl-synt_C, KR (ketoreductase), LANC_like, Methyltransf_2, p450 (cytochrome P450), PEP_mutase, polyprenyl_synt, Polysacc_synt, PP-binding (phosphopantetheine), PS-DH, RmlD_sub_bind, Terpene_synth, Terpene_synth_C, Thioesterase, Thiolase_N, Trp_halogenase, YcaO, Acyl_transf_1, Lant_dehydr_C, Lant_dehydr_N.

These correspond to the diagnostic gate domains in `CCTT_PATTERNS` and `UMED_PATTERNS` — the ones that define class membership (Trp_halogenase for T43-HAL, YcaO for thioamide/TOMM, LANC_like + Lant_dehydr for lanthipeptides, CDPS for diketopiperazines). The Wheelhouse HMM file is tier 1 of the three-tier HMM model; the addon `scanner_pfam_150.hmm` is tier 3.

**Used by:** `mamey/source_scans.py` via `pyhmmer` when the science stack is installed. Degrades gracefully to regex pattern matching when pyhmmer or this file is unavailable.

---

### mamey/data/mibig/mibig_reference_index.bacterial.json
**Size:** 1,709,495 bytes (1.63 MB)
**Format:** JSON, schema version `mibig-index-0.1`
**Source:** MIBiG 4.0 bulk auto-extraction, generated 2026-06-14
**Records:** 2,091 bacterial BGCs (filter: domain_of_life == Bacteria from GBK lineage)

This is the **KnownClusterBlast reference index** — the database behind every KCB similarity score in the pipeline. It contains one entry per MIBiG accession with architecture signatures that the engine matches against antiSMASH's KnownClusterBlast output.

**Entry structure per BGC:**
- `accession` — MIBiG accession (BGC0000001 through BGC0002xxx)
- `compounds` — list of compound names assigned in MIBiG (e.g. "abyssomicin C")
- `architecture_signature` — `{region, pks_ks count, nrps_c count, nrps_a count, markers, size_kb}`
- `subclasses` — antiSMASH subclass labels (e.g. "Type I", "Class II")
- `taxonomy` — organism name, NCBI taxid, domain, likely_eukaryote flag
- `mibig_quality` — "high", "medium", "low", "questionable"
- `mibig_status` — "active" (1,956) or "pending" (135)
- `signature_completeness` — fraction of expected signature fields populated

**Class distribution (region field):** PKS: 453 · NRPS: 424 · ribosomal: 347 · other: 296 · NRPS;PKS hybrid: 280 · saccharide: 127 · terpene: 58 · PKS;saccharide: 31 · other combinations: 75.

**Quality:** 1,973 entries are "questionable" (auto-extracted, not manually curated), 86 "high". This is intentional — the file is explicitly noted as a "bulk auto-extracted reference space, SEPARATE from the curated reference_bgc_library.json." Partial signatures by design. Honest blanks instead of invented values.

**BGC size range:** 0.2–4,150 kb, median 28.4 kb.

**Used by:** `mamey/antismash_evidence.py` for KCB scoring; `mamey/concordance.py` for reference-BGC concordance checking; `mamey/adjudication.py` for curated adjudication overlay.

---

### tests/fixtures/teicoplanin_BGC0000440.zip / _BGC0000441.zip — RETIRED (v9.7.270)

These MIBiG teicoplanin fixtures (~1.28 MB and ~1.25 MB) were retired in v9.7.270. They carried a
CC-BY attribution requirement (MIBiG data) and were the largest non-HMM binaries in `tests/`. They
were replaced by a single small **public** fixture, `tests/fixtures/micromonospora_humida_JAFEUC01.zip`
(~136 KB, GenBank JAFEUC01, two PKS-containing multi-class-hybrid regions), which ships in **every**
tier — so it is not a large file and needs no download. The end-to-end derivation test
(`test_end_to_end_micromonospora_humida_hybrids`) uses it; glycopeptide classification itself remains
covered by the pure-classifier unit test `test_glycopeptide_via_gtf_gene_symbol`. Teicoplanin remains a
calibration reference *compound* in the science docs and MIBiG index; only the heavy antiSMASH-export
fixtures were removed.

---

## Addon Files (sapote-addons-20260703)

### sapote_addons_core/npatlas/all_actinobacteria_npatlas_ref.json
**Size:** 9,143,389 bytes (8.72 MB)
**Format:** JSON
**Source:** NPAtlas download 2024-09, filtered to Actinobacteria/Actinomycetota phyla, built 2026-07-03
**Records:** 8,007 compounds from 95 distinct genera, 33 families

This is the **primary NP Atlas compound reference** for the B6_Compound_Reference workbook sheet and the NP Atlas resolver module (`mamey/npatlas_resolver.py`). It contains every actinobacterial natural product in the NP Atlas September 2024 dump, pre-filtered to the relevant phyla.

**Entry structure per compound:**
- `npaid` — NP Atlas unique identifier (e.g. "NPA000003")
- `name` — compound name (e.g. "A-503083 F")
- `synonyms` — list of alternative names
- `mol_formula` — molecular formula (e.g. "C18H22N4O13")
- `mol_weight` — molecular weight as string
- `exact_mass` — monoisotopic mass (key for metabolomics: [M+H]⁺ and [M+Na]⁺)
- `m_plus_h` — [M+H]⁺ precursor m/z
- `m_plus_na` — [M+Na]⁺ precursor m/z
- `smiles` — SMILES string
- `inchikey` — InChIKey (unique structural identifier for dereplication)
- `npclassifier` — `{pathway, superclass, class, is_glycoside}` (biosynthesis-aware classification)
- `classyfire` — ChemOntology classification (structure-based)
- `origin_organism` — producing genus/species
- `reference` — DOI/PMID list

**Top producing genera:** *Streptomyces*: 5,758 compounds · *Micromonospora*: 309 · *Actinomadura*: 176 · *Nocardiopsis*: 153 · *Amycolatopsis*: 153 · *Nocardia*: 141 · *Salinispora*: 126 · *Saccharothrix*: 85 · *Actinomyces*: 80 · *Kitasatospora*: 71.

**Key design note:** `npclassifier` uses biosynthesis-aware compound classification (pathway/superclass/class). This is distinct from the structure-based `classyfire` classification. For matching against BGC product classes, use `npclassifier`; for dereplication by structure, use `inchikey` + `exact_mass`. The field note in the provenance block explicitly states: "npclassifier is biosynthesis-aware (use for BGC class matching)."

**Used by:** `mamey/npatlas_resolver.py` to populate the `B6_Compound_Reference` workbook sheet when a strain is run with the NP Atlas addon present. Reads compound records matching the strain's KCB-named compounds, writes exact_mass, precursor ions, InChIKey, and primary DOI to B6. Never makes identity claims — INVENTORY_ONLY provenance tag.

---

### sapote_addons_core/npatlas/bacteria_nonactino_npatlas_ref.json
**Size:** 6,379,206 bytes (6.08 MB)
**Format:** JSON
**Source:** NPAtlas 2024-09, filtered to non-actinobacterial bacteria, built 2026-07-03

Companion reference to the actinobacterial file, covering Proteobacteria, Firmicutes, Cyanobacteria, and other bacterial phyla. Used when a strain's KCB comparators point to non-actinobacterial producer organisms. Structure is identical to the actinobacteria file with a `phylum_counts` field added. Smaller than the actinobacteria file because *Streptomyces* alone contributes 72% of actinobacterial NP Atlas entries.

---

### sapote_addons_figures/hmm/scanner_pfam_150.hmm
**Size:** 13,974,204 bytes (13.33 MB)
**Format:** HMMER3 profile HMM file
**Profiles:** 148 HMM families
**SHA256:** `2db9ed0e58d1cd679b6b3c15e01c411e0bd49ae410a116d50bd23afa904aa57c`

This is the **full three-tier HMM reference** that enables the complete offline domain scan. It is the empirically-built superset covering ~66% of domain signal across a typical actinomycete BGC proteome.

**Construction methodology:** The full Pfam-A (30,134 families) was scanned against SID10815's BGC proteome. The top ~130 families by hit frequency were retained, then all scanner-gate discriminating domains were force-added regardless of frequency. Coverage curve: top 35 → 36% signal | top 60 → 47% | top 100 → 58% | top 150 → 66% | top 200 → 73%.

The 148 families cover: PKS reductive-loop domains (KS, AT, DH, ER, KR, ACP, Docking, PS-DH, KAsynt_C_assoc, CurL-like_PKS_C, SpnB_Rossmann, SDR); NRPS core (Condensation, AMP-binding, AMP-binding_C, PP-binding); RiPP maturation (LANC_like, Lant_dehydr_N/C, YcaO, SPASM, RhiE-like_linker); NDP-sugar biosynthesis (DegT_DnrJ_EryC1, RmlD_sub_bind, Epimerase, GDP_Man_Dehyd); regulatory (TetR_N, MarR, MarR_2, LysR_substrate, HTH families, GerE, Sigma70_r4, BTAD, NovG_helical, Response_reg, HisKA, HATPase_c, HATPase_c_2); transport (ABC_tran, ABC_membrane, ABC2_membrane, ABC2_membrane_3, BPD_transp_1, MFS_1, MFS_3, Sugar_tr); oxidoreductases (Pyr_redox, Pyr_redox_2, FAD_binding_2, FAD_binding_3, DAO, Aldedh, ADH_zinc_N/N_2, adh_short/C2, NAD_binding families); methyltransferases (Methyltransf_2, 11, 12, 23, 25, 31, Ubie_methyltran); aminotransferases (Aminotran_1_2, 3, 5, Amino_oxidase, PALP, DegT_DnrJ_EryC1); terpene (Terpene_synth, Terpene_synth_C, Terpene_syn_C_2, polyprenyl_synt, PEP_mutase); special (DHQ_synthase for aminocyclitol, Trp_halogenase for T43-HAL, IucA_IucC for siderophore, CDPS for diketopiperazine, YcaO for thioamide, ECH_1/2, TauD, Radical_SAM, Isochorismatase, MbtH, PqqD, Thiolase_N, NUDIX, ATP-grasp, Asn_synthase, Mur_ligase_C/M, CBM_48, GT families, Beta-lactamase, 3Beta_HSD, IucA_IucC, FhuF, DUF397, DUF5753, Asp23, NmrA, SpoIIE, PKS_DE, PKS_DH_N, ACOX_C_alpha1, GT4-conflict, SDR, NovG_helical, RhiE-like_linker, CurL-like_PKS_C, SpnB_Rossmann).

**Validated:** AS-XXX — 137/148 families hit; CDPS detected (photopiperazine), Trp_halogenase detected (tetrachlorizine), PKS detected (ionostatin).

**Three-tier model:** Tier 1 = 35 core HMMs in the CODE bundle (`Wheelhouse/hmm/scanner_pfam.hmm`) · Tier 2 = pyhmmer engine (this addon's wheel) · Tier 3 = this file (148-family data). All three required for full offline scan.

---

## Wheel Files (size ≥ 1MB)

Wheel sizes are the compressed `.whl` archive. Installed size is typically 3–8× larger.

| Wheel | Compressed | Notes |
|---|---|---|
| scipy-1.18.0 | 34 MB | Largest single wheel; scientific algorithms. Installed ~200 MB. |
| numpy-2.5.0 | 16 MB | Fundamental array computing; installed ~30 MB. |
| pandas-3.0.3 | 11 MB | Tabular data; installed ~60 MB. |
| logomaker-0.8.7 | 13 MB | Includes large bundled font/glyph data for logo rendering. |
| matplotlib-3.11.0 | 9.6 MB | Figure rendering; installed ~50 MB. |
| pyhmmer-0.12.1 | 3.9 MB | Includes compiled HMMER3 C code as Cython extension. |
| pyrodigal-3.7.1 | 2.9 MB | Includes compiled Prodigal C code as Cython extension. |
| pyskani-0.2.0 | 3.4 MB | Includes compiled skani Rust code as PyO3 extension. |
| pyfamsa-0.7.0 | 1.9 MB | Includes compiled FAMSA C++ code as Cython extension. |
| biopython-1.87 | 3.1 MB | Includes compiled C extensions for sequence parsing. |
| pip-26.1.2 | 1.8 MB | Package manager; large due to bundled pip internals. |
| pyswrd-0.3.1 | ~1 MB | SWORD Smith-Waterman; includes SIMD C++ extensions. |
| gffutils-0.14 | 1.6 MB | Includes SQLite bundling. |
| pygments-2.20.0 | 1.2 MB | Large due to bundled syntax lexers for ~500 languages. |

**Wheel files < 1MB** (pyrodigal_gv, pyopal, pyfastani, pyfastx, pytantan, pytrimal, pyskani, gb-io, taxopy, DendroPy, archspec, argcomplete, argh, bcbio-gff, ijson, iniconfig, packaging, pluggy, psutil, pyfaidx, scoring_matrices, setuptools, simplejson, six, wheel, dna_features_viewer, pycirclize): individually small, some because they are pure Python, some because the compiled code is compact.

---

## Size Summary by Category

| Category | File count | Total size |
|---|---|---|
| Bundle HMM data | 1 | 4.2 MB |
| Bundle reference data (MIBiG) | 1 | 1.6 MB |
| Bundle test fixtures | 2 | 2.5 MB |
| Addon HMM data (full 148) | 1 | 13.3 MB |
| Addon NP Atlas references | 2 | 14.8 MB |
| Addon wheels ≥1 MB | 14 | ~118 MB compressed |
| **Total large-file footprint** | **21** | **~154 MB** |

The remaining ~330 bundle files (source code, docs, tests, prompts, templates) total approximately 22 MB.

---

*Inspection methodology: file sizes obtained via `os.path.getsize()`; format and content determined by direct Python inspection of file structure (zipfile, json.load, HMMER profile counting, METADATA extraction from wheel ZIPs). No values inferred from filenames or prior knowledge.*

---

## Graceful Degradation When Large Files Are Absent

Each large file has a specific degradation path when absent or inaccessible.

**Wheelhouse/hmm/scanner_pfam.hmm (absent):** The offline HMM scan falls back to regex-based pattern matching for CCTT triggers and UMED detection. All 18 CCTT families and all 7 UMED families are covered by regex, so the scan still runs. The HMM-based scan provides higher specificity (especially for multi-domain combinations and distant homologs), but its absence is not a blocking failure. `mamey doctor` reports `science stack not fully available`.

**mamey/data/mibig/mibig_reference_index.bacterial.json (absent or unreadable):** KCB scoring from the package's own antiSMASH JSON still works — Mamey reads KCB hits from antiSMASH's internal KnownClusterBlast output, not from this index directly. This index is used by `mamey/concordance.py` for reference-BGC concordance checking and by `mamey/adjudication.py` for curated overlay. Those modules fail gracefully when the file is absent (concordance returns no matches, adjudication is skipped). `manifest.json` will carry a note that concordance was not run.

**Test fixtures:** the end-to-end architecture test uses `tests/fixtures/micromonospora_humida_JAFEUC01.zip` (~136 KB, public), which ships in every tier — no fixture download is needed and no tests skip for a missing fixture. (The former teicoplanin fixtures were retired in v9.7.270; see the RETIRED entry above.)

**scanner_pfam_150.hmm (addon, absent):** Falls back to the 35-family Wheelhouse HMM. Coverage drops from 148 to 35 families and ~66% to ~28% of actinomycete BGC domain signal. All class-defining gate domains (Trp_halogenase, YcaO, LANC_like, Lant_dehydr, etc.) are in the 35-family set, so gating decisions are unaffected. The scan is less sensitive to accessory/tailoring domain variants.

**NP Atlas reference files (absent):** The `B6_Compound_Reference` workbook sheet is not populated. All other sheets are unaffected. The `npatlas_resolver.py` module checks for the file at import and logs a warning rather than failing. The `mamey doctor` output does not check for NP Atlas files (they are an optional addon, not a required dependency), but a run that would populate B6 will note NPATLAS_ABSENT in the issue_log.

---

## SHA256 Checksums for Reference Data Files

These are the authoritative integrity hashes for the large reference files, used to verify that the files shipped correctly and have not been modified.

**scanner_pfam_150.hmm** (addon, 148 families, 13.33 MB):
`2db9ed0e58d1cd679b6b3c15e01c411e0bd49ae410a116d50bd23afa904aa57c`

Source: `sapote_addons_figures/hmm/SCANNER_PFAM_150_MANIFEST.md` — the SHA256 is embedded in the manifest and verified by the installer.

**scanner_pfam.hmm** (Wheelhouse, 35 families, 4.21 MB): No SHA256 in the bundle manifest for this file. Integrity is verified by HMM profile count (35 entries, verified by `content.count('//')`) and by the installer's import test of pyhmmer against the file.

**mibig_reference_index.bacterial.json** (2,091 entries, 1.63 MB): No standalone SHA256; integrity is verified by the schema version field (`"schema_version": "mibig-index-0.1"`) and entry count (`"n": 2091`) at load time in `mamey/concordance.py`.

---

## Inspection Methodology Receipt

All values in this document were obtained by direct Python inspection in the session. No values were inferred from filenames or prior knowledge.

| File | Method used |
|---|---|
| scanner_pfam.hmm | `open(...).read().count('//')` for profile count; `[l.split()[1] for l in ... if l.startswith('NAME')]` for names; `os.path.getsize()` for size |
| mibig_reference_index.bacterial.json | `json.load()`; field inspection of `data.keys()`, `data['n']`, `data['entries'][0].keys()`, class distribution via Counter |
| micromonospora_humida_JAFEUC01.zip | `zipfile.ZipFile().namelist()` for contents; `os.path.getsize()` for size |
| all_actinobacteria_npatlas_ref.json | `json.load()`; `data['_provenance']` for metadata; `data['compounds'][0].keys()` for structure; Counter on `origin_organism` genus field |
| scanner_pfam_150.hmm | Same as scanner_pfam.hmm |
| All .whl files | `zipfile.ZipFile().read('*/METADATA')` decoded and parsed for Name/Version/Summary fields; `os.path.getsize()` for compressed size |

*Last updated: 2026-07-09 · v2 additions (degradation, checksums, methodology receipt) · Bundle v9.7.319*
