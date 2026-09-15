# Type Strain walkthroughs: nine detailed offline examples

This candidate walkthrough uses one representative from each of seven genera, with two additional
Streptomyces. Inputs were supplied as public-genome antiSMASH ZIPs. Their supplied identities were
bound to archived records; no independent online taxonomic verification or BLASTp search was done.
Input hashes and the exact archived header evidence are retained in the run receipts.

## What ran

Each input followed inspect → gold extraction → validate → explain → list-bgcs. Extraction used
bounded JSON, standard brief, locus maps on, and PRIVATE output tagging. All 45 command stages
returned exit 0. That is computational completion, not a declaration that the PDFs are ready to
publish or that interpretation is finished. No online search, tree construction, family clustering
or full Mode B authoring was performed.

The earlier broad panel ran all 18 archives. Its execution mean was 41.7815 seconds, range
31.626–58.299 seconds, but ten attempts received a placeholder `.` taxonomy from the intake script.
Those are retained as metadata failures; they are not clean biological walkthrough results. The
corrected panel below uses description-bound names. Do not pool the two panels into one clean benchmark.

## Performance and outputs

Nine corrected runs: mean **40.93 s**, median **39.18 s**, range **33.88–49.56 s**. Per-child peak RSS ranged **1.90–2.41 GB** (decimal).

Measurements were sequential on the available macOS arm64 host, with Python 3.12.14 and ten
logical CPUs reported by the host. No thread-count scaling experiment was performed. Each input
was measured once; caches and background activity were not controlled. These are descriptive
walkthrough measurements, not hardware-independent performance guarantees.

| Input | Regions | Run seconds | Peak GB | Extracted package MB | Evidence |
|---|---:|---:|---:|---:|---|
| Actinomadura citrea JCM 3295 (TS01) | 68 | 36.65 | 2.33 | 128.5 | MAIN_JSON_WALKER_TRUNCATED |
| Nocardia thailandica NBRC 100428 (TS05) | 51 | 41.65 | 2.18 | 117.4 | MAIN_JSON_WALKER_TRUNCATED |
| Pseudonocardia sp. DSM 110487 (TS10) | 52 | 45.46 | 1.90 | 113.5 | MAIN_JSON_WALKER_TRUNCATED |
| Saccharopolyspora erythraea NRRL2338 (TS11) | 57 | 36.20 | 2.15 | 133.5 | MAIN_JSON_WALKER_TRUNCATED |
| Saccharothrix espanaensis DSM 44229 (TS12) | 58 | 39.07 | 2.12 | 152.2 | MAIN_JSON_WALKER_TRUNCATED |
| Streptomyces clavuligerus ATCC 27064 (TS13) | 60 | 39.18 | 2.41 | 139.4 | MAIN_JSON_WALKER_TRUNCATED |
| Streptomyces fradiae ATCC 10745 (TS16) | 52 | 33.88 | 2.10 | 128.7 | MAIN_JSON_WALKER_TRUNCATED |
| Streptomyces spectabilis ATCC 27465 (TS17) | 67 | 46.70 | 2.37 | 175.0 | MAIN_JSON_WALKER_TRUNCATED |
| Streptosporangium pseudovulgare JCM 3115 (TS18) | 56 | 49.56 | 2.21 | 124.0 | MAIN_JSON_WALKER_TRUNCATED |

The pipeline's phase total and the external command wall time cover different spans, notably
post-seal rendering. Report them separately. Earlier macOS timing files mislabeled raw bytes as
KB; the candidate normalizes that field to KiB. These panel peak-memory values come independently
from the child-process receipt, not from interpreting the old mislabeled field.

## Per-strain result review

The row selected below is the first row of the recorded triage table, not a newly endorsed lead.
Each was cross-checked against the inventory and an actual source region GBK in its input ZIP.
AB/AF values are prioritization scores, not percentages or assay measurements.

### Actinomadura citrea JCM 3295 — TS01

Input: `Actinomadura_citrea_Strain_JCM_3295.zip`. SHA-256: `b5126ef8aadb785393bcc225b1b1545d7ff1ba36e9dbfd171ff0f011357af5c1`.

The run yielded **68 region records** (48 interior, 12 edge, 8 full-contig). Its weighted count is 56.0; the assembly record reports 74 contigs and N50 326159 bp. These are distinct measurements.

First recorded triage row: **TS01 / BMRD01000003.1 / region002 / BGC014**. Products: `RiPP; lanthipeptide-class-ii`; boundary `Interior`; architecture `A`; class confidence `LOW`; AB `74.0`, AF `24.0`. Source: `BMRD01000003.1.region002.gbk`. This binding was verified; compound identity was not.

Pipeline: `MAMEY_COMPLETE_WITH_ISSUES`; validator: `MAMEY_COMPLETE`; interpretation: `JUDGMENT_PENDING`. Evidence advisories: MAIN_JSON_WALKER_TRUNCATED. Check the selected row's underlying gene/domain and boundary evidence before choosing an interpretation. Empty or unavailable channels are not negative biology.

All 5 command stages returned zero. The package contains 686 files, approximately 128.5 MB; its sealed ZIP is 39.4 MB. Entry-page local links and ZIP integrity checked successfully. The remaining recorded issues are: MULTIBATCH: raw BGC count > 25 — judgment will need ~4 LLM batches (~20 BGCs each). Use the batch plan to sequence them. RG-GMCI HIGH pairs: 16 (include split-cluster review in each batch). OVER_MERGE_CANDIDATES: 7 region(s) carry >=2 protoclusters or neighbouring/interleaved/chemical_hybrid kind — antiSMASH's own 'region = >=2 BGCs' signal. See TS01_predicted_polymers.csv.

### Nocardia thailandica NBRC 100428 — TS05

Input: `Nocardia thailandica NBRC 100428 NZ_BAGK00000000.1.zip`. SHA-256: `5dc239cb7ac454bc15c450759c7bdf51ff4898bf8fc49c2ea41ec395367eda18`.

The run yielded **51 region records** (10 interior, 26 edge, 15 full-contig). Its weighted count is 26.75; the assembly record reports 312 contigs and N50 47211 bp. These are distinct measurements.

First recorded triage row: **TS05 / NZ_BAGK01000184.1 / region001 / BGC026**. Products: `NRPS; PKS; T1PKS; saccharide`; boundary `Edge`; architecture `C`; class confidence `MODERATE`; AB `59.0`, AF `42.0`. Source: `NZ_BAGK01000184.1.region001.gbk`. This binding was verified; compound identity was not.

Pipeline: `MAMEY_COMPLETE_WITH_ISSUES`; validator: `MAMEY_COMPLETE`; interpretation: `JUDGMENT_PENDING`. Evidence advisories: MAIN_JSON_WALKER_TRUNCATED. Check the selected row's underlying gene/domain and boundary evidence before choosing an interpretation. Empty or unavailable channels are not negative biology.

All 5 command stages returned zero. The package contains 554 files, approximately 117.4 MB; its sealed ZIP is 31.9 MB. Entry-page local links and ZIP integrity checked successfully. The remaining recorded issues are: MULTIBATCH: raw BGC count > 25 — judgment will need ~3 LLM batches (~20 BGCs each). Use the batch plan to sequence them. RG-GMCI HIGH pairs: 10 (include split-cluster review in each batch). VERY_POOR assembly (19.6% interior BGCs). Most leads are edge/FC fragments; RG-GMCI must be used before lead ranking. OVER_MERGE_CANDIDATES: 6 region(s) carry >=2 protoclusters or neighbouring/interleaved/chemical_hybrid kind — antiSMASH's own 'region = >=2 BGCs' signal. See TS05_predicted_polymers.csv.

### Pseudonocardia sp. DSM 110487 — TS10

Input: `Pseudonocardia sp. DSM 110487 CP080521.1.zip`. SHA-256: `f1e9e83c1744b8cb56bfa1693c295567a3d2c04463dec8e240a7b9f2f3e857d0`.

The run yielded **52 region records** (52 interior, 0 edge, 0 full-contig). Its weighted count is 52.0; the assembly record reports 1 contigs and N50 10132709 bp. These are distinct measurements.

First recorded triage row: **TS10 / CP080521.1 / region029 / BGC029**. Products: `RiPP; lassopeptide`; boundary `Interior`; architecture `A`; class confidence `LOW`; AB `68.0`, AF `20.0`. Source: `CP080521.1.region029.gbk`. This binding was verified; compound identity was not.

Pipeline: `MAMEY_COMPLETE_WITH_ISSUES`; validator: `MAMEY_COMPLETE`; interpretation: `JUDGMENT_PENDING`. Evidence advisories: MAIN_JSON_WALKER_TRUNCATED. Check the selected row's underlying gene/domain and boundary evidence before choosing an interpretation. Empty or unavailable channels are not negative biology.

All 5 command stages returned zero. The package contains 569 files, approximately 113.5 MB; its sealed ZIP is 34.6 MB. Entry-page local links and ZIP integrity checked successfully. The remaining recorded issues are: MULTIBATCH: raw BGC count > 25 — judgment will need ~3 LLM batches (~20 BGCs each). Use the batch plan to sequence them. RG-GMCI HIGH pairs: 1 (include split-cluster review in each batch). OVER_MERGE_CANDIDATES: 2 region(s) carry >=2 protoclusters or neighbouring/interleaved/chemical_hybrid kind — antiSMASH's own 'region = >=2 BGCs' signal. See TS10_predicted_polymers.csv.

### Saccharopolyspora erythraea NRRL2338 — TS11

Input: `Saccharopolyspora_erythraea_NRRL_2338.zip`. SHA-256: `ac0b4836d21ab649630c2035ce437a8c9db397645992877286ec8552f68e499b`.

The run yielded **57 region records** (57 interior, 0 edge, 0 full-contig). Its weighted count is 57.0; the assembly record reports 1 contigs and N50 8212805 bp. These are distinct measurements.

First recorded triage row: **TS11 / AM420293.1 / region035 / BGC035**. Products: `RiPP; lanthipeptide-class-iii`; boundary `Interior`; architecture `A`; class confidence `LOW`; AB `74.0`, AF `24.0`. Source: `AM420293.1.region035.gbk`. This binding was verified; compound identity was not.

Pipeline: `MAMEY_COMPLETE_WITH_ISSUES`; validator: `MAMEY_COMPLETE`; interpretation: `JUDGMENT_PENDING`. Evidence advisories: MAIN_JSON_WALKER_TRUNCATED. Check the selected row's underlying gene/domain and boundary evidence before choosing an interpretation. Empty or unavailable channels are not negative biology.

All 5 command stages returned zero. The package contains 614 files, approximately 133.5 MB; its sealed ZIP is 37.2 MB. Entry-page local links and ZIP integrity checked successfully. The remaining recorded issues are: MULTIBATCH: raw BGC count > 25 — judgment will need ~3 LLM batches (~20 BGCs each). Use the batch plan to sequence them. RG-GMCI HIGH pairs: 13 (include split-cluster review in each batch). OVER_MERGE_CANDIDATES: 14 region(s) carry >=2 protoclusters or neighbouring/interleaved/chemical_hybrid kind — antiSMASH's own 'region = >=2 BGCs' signal. See TS11_predicted_polymers.csv.

### Saccharothrix espanaensis DSM 44229 — TS12

Input: `Saccharothrix_espanaensis_DSM_44229_Strain_type_strain__DSM_44229_GCA_000328705.1_ASM32870v1_genomic.zip`. SHA-256: `840c908e792ef6cd98f6da55a3e88831466ddf71579c247298ea5b2db0476140`.

The run yielded **58 region records** (58 interior, 0 edge, 0 full-contig). Its weighted count is 58.0; the assembly record reports 1 contigs and N50 9360653 bp. These are distinct measurements.

First recorded triage row: **TS12 / HE804045.1 / region023 / BGC023**. Products: `HR-T2PKS; NRPS; PKS; fatty_acid; halogenated; other; thioamide-NRP`; boundary `Interior`; architecture `A`; class confidence `HIGH`; AB `100`, AF `32.0`. Source: `HE804045.1.region023.gbk`. This binding was verified; compound identity was not.

Pipeline: `MAMEY_COMPLETE_WITH_ISSUES`; validator: `MAMEY_COMPLETE`; interpretation: `JUDGMENT_PENDING`. Evidence advisories: MAIN_JSON_WALKER_TRUNCATED. Check the selected row's underlying gene/domain and boundary evidence before choosing an interpretation. Empty or unavailable channels are not negative biology.

All 5 command stages returned zero. The package contains 617 files, approximately 152.2 MB; its sealed ZIP is 40.8 MB. Entry-page local links and ZIP integrity checked successfully. The remaining recorded issues are: MULTIBATCH: raw BGC count > 25 — judgment will need ~3 LLM batches (~20 BGCs each). Use the batch plan to sequence them. RG-GMCI HIGH pairs: 7 (include split-cluster review in each batch). OVER_MERGE_CANDIDATES: 9 region(s) carry >=2 protoclusters or neighbouring/interleaved/chemical_hybrid kind — antiSMASH's own 'region = >=2 BGCs' signal. See TS12_predicted_polymers.csv.

### Streptomyces clavuligerus ATCC 27064 — TS13

Input: `Streptomyces_clavuligerus_ATCC_27064.zip`. SHA-256: `175247cb63031293837ecdf9f9864327dc39c8a2f33036b13644b05f4ac55092`.

The run yielded **60 region records** (58 interior, 2 edge, 0 full-contig). Its weighted count is 59.0; the assembly record reports 2 contigs and N50 6748591 bp. These are distinct measurements.

First recorded triage row: **TS13 / CP027858.1 / region002 / BGC002**. Products: `NRPS; NRPS-like; PKS; T1PKS; saccharide; terpene`; boundary `Interior`; architecture `A`; class confidence `MODERATE`; AB `59.0`, AF `74.0`. Source: `CP027858.1.region002.gbk`. This binding was verified; compound identity was not.

Pipeline: `MAMEY_COMPLETE_WITH_ISSUES`; validator: `MAMEY_COMPLETE`; interpretation: `JUDGMENT_PENDING`. Evidence advisories: MAIN_JSON_WALKER_TRUNCATED. Check the selected row's underlying gene/domain and boundary evidence before choosing an interpretation. Empty or unavailable channels are not negative biology.

All 5 command stages returned zero. The package contains 633 files, approximately 139.4 MB; its sealed ZIP is 40.7 MB. Entry-page local links and ZIP integrity checked successfully. The remaining recorded issues are: MULTIBATCH: raw BGC count > 25 — judgment will need ~3 LLM batches (~20 BGCs each). Use the batch plan to sequence them. RG-GMCI HIGH pairs: 13 (include split-cluster review in each batch). OVER_MERGE_CANDIDATES: 16 region(s) carry >=2 protoclusters or neighbouring/interleaved/chemical_hybrid kind — antiSMASH's own 'region = >=2 BGCs' signal. See TS13_predicted_polymers.csv.

### Streptomyces fradiae ATCC 10745 — TS16

Input: `Streptomyces_fradiae_ATCC_10745_GCA_008704425.1_ASM870442v1_genomic.zip`. SHA-256: `db260cdba68c8f927d1d31c1eb910309f0d735242ed0fe709ca7e62b344831e5`.

The run yielded **52 region records** (50 interior, 2 edge, 0 full-contig). Its weighted count is 51.0; the assembly record reports 1 contigs and N50 6725579 bp. These are distinct measurements.

First recorded triage row: **TS16 / CP023696.1 / region010 / BGC010**. Products: `RiPP; lanthipeptide-class-i`; boundary `Interior`; architecture `A`; class confidence `LOW`; AB `74.0`, AF `24.0`. Source: `CP023696.1.region010.gbk`. This binding was verified; compound identity was not.

Pipeline: `MAMEY_COMPLETE_WITH_ISSUES`; validator: `MAMEY_COMPLETE`; interpretation: `JUDGMENT_PENDING`. Evidence advisories: MAIN_JSON_WALKER_TRUNCATED. Check the selected row's underlying gene/domain and boundary evidence before choosing an interpretation. Empty or unavailable channels are not negative biology.

All 5 command stages returned zero. The package contains 575 files, approximately 128.7 MB; its sealed ZIP is 32.8 MB. Entry-page local links and ZIP integrity checked successfully. The remaining recorded issues are: MULTIBATCH: raw BGC count > 25 — judgment will need ~3 LLM batches (~20 BGCs each). Use the batch plan to sequence them. RG-GMCI HIGH pairs: 5 (include split-cluster review in each batch). OVER_MERGE_CANDIDATES: 7 region(s) carry >=2 protoclusters or neighbouring/interleaved/chemical_hybrid kind — antiSMASH's own 'region = >=2 BGCs' signal. See TS16_predicted_polymers.csv.

### Streptomyces spectabilis ATCC 27465 — TS17

Input: `Streptomyces_spectabilis_Strain_ATCC_27465_GCA_008704795.1_ASM870479v1_genomic.zip`. SHA-256: `78f877835bc8203b8a2c275f73604ae78ad0af1cb2a1b069d9c52941699f64da`.

The run yielded **67 region records** (67 interior, 0 edge, 0 full-contig). Its weighted count is 67.0; the assembly record reports 1 contigs and N50 9807160 bp. These are distinct measurements.

First recorded triage row: **TS17 / CP023690.1 / region004 / BGC004**. Products: `NRPS; PKS; RiPP; lassopeptide; transAT-PKS`; boundary `Interior`; architecture `A`; class confidence `MODERATE`; AB `98.0`, AF `44.0`. Source: `CP023690.1.region004.gbk`. This binding was verified; compound identity was not.

Pipeline: `MAMEY_COMPLETE_WITH_ISSUES`; validator: `MAMEY_COMPLETE`; interpretation: `JUDGMENT_PENDING`. Evidence advisories: MAIN_JSON_WALKER_TRUNCATED. Check the selected row's underlying gene/domain and boundary evidence before choosing an interpretation. Empty or unavailable channels are not negative biology.

All 5 command stages returned zero. The package contains 685 files, approximately 175.0 MB; its sealed ZIP is 47.8 MB. Entry-page local links and ZIP integrity checked successfully. The remaining recorded issues are: MULTIBATCH: raw BGC count > 25 — judgment will need ~4 LLM batches (~20 BGCs each). Use the batch plan to sequence them. RG-GMCI HIGH pairs: 5 (include split-cluster review in each batch). OVER_MERGE_CANDIDATES: 21 region(s) carry >=2 protoclusters or neighbouring/interleaved/chemical_hybrid kind — antiSMASH's own 'region = >=2 BGCs' signal. See TS17_predicted_polymers.csv.

### Streptosporangium pseudovulgare JCM 3115 — TS18

Input: `Streptosporangium_pseudovulgare_JCM-3115_NZ_BMQJ00000000.zip`. SHA-256: `ec632dafdb9106e448f9e2161dc8fb4feca0dd69072ca9108a4519e23f2bf05a`.

The run yielded **56 region records** (45 interior, 10 edge, 1 full-contig). Its weighted count is 50.25; the assembly record reports 73 contigs and N50 329744 bp. These are distinct measurements.

First recorded triage row: **TS18 / NZ_BMQJ01000002.1 / region002 / BGC009**. Products: `RiPP; lanthipeptide-class-iii`; boundary `Interior`; architecture `A`; class confidence `LOW`; AB `74.0`, AF `24.0`. Source: `NZ_BMQJ01000002.1.region002.gbk`. This binding was verified; compound identity was not.

Pipeline: `MAMEY_COMPLETE_WITH_ISSUES`; validator: `MAMEY_COMPLETE`; interpretation: `JUDGMENT_PENDING`. Evidence advisories: MAIN_JSON_WALKER_TRUNCATED. Check the selected row's underlying gene/domain and boundary evidence before choosing an interpretation. Empty or unavailable channels are not negative biology.

All 5 command stages returned zero. The package contains 606 files, approximately 124.0 MB; its sealed ZIP is 38.9 MB. Entry-page local links and ZIP integrity checked successfully. The remaining recorded issues are: MULTIBATCH: raw BGC count > 25 — judgment will need ~3 LLM batches (~20 BGCs each). Use the batch plan to sequence them. RG-GMCI HIGH pairs: 9 (include split-cluster review in each batch). OVER_MERGE_CANDIDATES: 7 region(s) carry >=2 protoclusters or neighbouring/interleaved/chemical_hybrid kind — antiSMASH's own 'region = >=2 BGCs' signal. See TS18_predicted_polymers.csv.

## Where the walkthrough breaks or needs judgment

- Metadata: the original `ORGANISM = .` intake issue demonstrates why successful parsing is not identity verification. Use the full archived description or record an unresolved identity.
- Evidence: bounded mode can finish with a truncated main JSON walker. Full mode can instead hold an over-cap file. Neither should be called exhaustive extraction.
- Presentation: the inspected Nocardia brief has first-page overflow, overlapping text and shortened identifiers. Package validation did not catch those visual defects. Layout repair remains necessary.
- Interpretation: rendered extraction briefs and ranking tables do not complete Mode B. No externally verified function, chemical identity or activity claim was produced here.
- Storage: figures and locus maps generate hundreds of files per package. Use the run inventory to choose what to retain or archive; do not silently duplicate every run into a review ZIP.

## Reproduce or continue

Use the [Master Walkthrough](MASTER_WALKTHROUGH.md) and its expanded offline-output settings.
The accompanying review kit includes run scripts and exact receipts, the candidate patches,
validation logs and inventories. Set paths and recreate a compatible environment on another
machine; do not copy a virtual environment. Individual Complete_Package ZIPs remain in the run
folders and are indexed by the review record. The software patch ZIP intentionally does not
duplicate those large biological outputs.

Keep state and transcript coverage using the [shared handoff policy](ASSISTANT_USER_GUIDE.md#next-paths-automatic-save-state-and-transcripts).
