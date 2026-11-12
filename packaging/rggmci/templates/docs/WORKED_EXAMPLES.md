# Worked examples on public reference genomes

Four historical pair examples from public antiSMASH results (NCBI WGS assemblies), one for each common
software verdict. Exact source archives matched to later saved reruns comprise three Actinomadura archives recording `loose`
and one Saccharopolyspora archive recording `relaxed` in their antiSMASH JSON HMM-detection metadata.
Some records lack that field. These reruns are not a uniform-profile comparison and do not establish the
original historical runs' settings. Pairing requires different contigs and region-feature `/contig_edge="True"`, or a fallback
`Edge`/`Full-contig` status when region-feature flags are missing or conflicting. An explicit `False` excludes
a region; flags on other feature types do not substitute. Missing source members and unreadable ZIPs also
use the fallback. An interior-region exclusion is a software selection rule: it does not establish that the
biological region is whole or rule out missing neighboring sequence or a separate locus. Same-contig pairs
are listed apart as related loci, never as rescues. Every region is named as `organism strain / submitter's contig name = accession / antiSMASH region / alias`.
The submitter's contig name comes from each record's DEFINITION line. The alias (`BGC014`) is rggmci's reading
order and is not stable between runs, so look regions up by accession and region.

To check any pair yourself, open the two region files in the antiSMASH ZIP, `<accession>.<region>.gbk`. Read their
genes and domains, then the pair's supporting references in `best_sources`.

These results come from an earlier rggmci release. Scores and confidences on these genomes may differ in the current release; rerun the genome and compare by accession and region before quoting a number.

## 1. Complementary reference tiling: HIGH candidate

*Saccharopolyspora erythraea* D (AVCN00000000.1, 384 contigs)
- `Saccharopolyspora erythraea D / scaffold00041 = AVCN01000041.1 / region001 / BGC014`: NRPS-like; T1PKS, at a contig end.
- `Saccharopolyspora erythraea D / scaffold00075 = AVCN01000075.1 / region001 / BGC022`: T1PKS, reported `Full-contig` (at least 95% contig coverage).

Result: score 28, `HIGH_RG_GMCI_RESCUE`, `COMPLEMENTARY_SPLIT`, 5 strong references, 2 with good geometry (both
MIBiG). The MIBiG entries among the best sources are BGC0000136 (rifamycin) and BGC0001759 (rifamorpholine).

What it means:
- The two fragments hit different genes of the same reference clusters, and those genes sit side by side in the
  references. That fits one pathway cut by the assembly. Two separate pathways that share reference genes could
  give the same pattern.
- Each region's own KnownClusterBlast list points the same way. The contig-end fragment's top hits are ansamycin-type
  clusters (microansamycin, naphthomycin); the `Full-contig`-labeled fragment's include rifamorpholine and rifamycin.
- A hypothesis at the class level: the two fragments may be parts of one ansamycin-type type I PKS pathway. It
  does not name a compound, and it does not show the contigs are adjacent.

In the same genome, `Saccharopolyspora erythraea D / scaffold00014 = AVCN01000014.1 / region001 / BGC006` (T1PKS, contig end, top KnownClusterBlast
hit erythromycin) is HIGH with both fragments above. Those pairs cite other MIBiG clusters (kanglemycin; efomycin,
selvamicin) and the gene check reads them as a `MIXED_SUBJECT_SIGNAL`. A group of HIGH pairs can hold more than one
pathway: read each pair's references and the genes, not only the group.

## 2. Overlapping reference tiling: demoted to LOW

*Actinomadura montaniterrae* CYP1-1B (WBMR00000000.1, 492 contigs)
- `Actinomadura montaniterrae CYP1-1B / Scaffold2 = WBMR01000002.1 / region002 / BGC003`: NRPS; T2PKS; oligosaccharide, at a contig end.
- `Actinomadura montaniterrae CYP1-1B / Scaffold62 = WBMR01000062.1 / region001 / BGC017`: T2PKS, reported `Full-contig` (at least 95% contig coverage).

Result: score 35, high enough for HIGH, with 19 strong references and 16 with good geometry. It still ends
`LOW_SHARED_REFERENCE_SIGNAL`, with gate `ST-PARALOG_no_complementarity_proof` and gene check `OVERLAPPING_PARALOG`.

Why: on the shared references the two regions hit the same reference genes (87 shared, 0 references where they are
complementary). This overlapping-reference signal is compatible with duplicate or related loci, but it does
not establish two copies or exclude a fragmented modular pathway. Separate gene, assembly and locus evidence
is needed to distinguish those explanations. A shared gene or two does not trigger this: the check allows up to 2 shared genes, when they are at most 15%
of all genes hit and each side still hits 2 genes of its own.

## 3. A promiscuous fragment: HIGH demoted to MODERATE by the hub guard

*Actinomadura harenae* NEAU-Ht49 (RFFG00000000.1, 274 contigs)
- `Actinomadura harenae NEAU-Ht49 / Scaffold69 = RFFG01000069.1 / region001 / BGC027`: NRPS, reported `Full-contig` (at least 95% contig coverage).
- `Actinomadura harenae NEAU-Ht49 / Scaffold112 = RFFG01000112.1 / region001 / BGC035`: NRPS; T3PKS, reported `Full-contig` (at least 95% contig coverage).

Result: score 35, 21 strong references and 22 with good geometry (13 of them MIBiG), but
`MODERATE_RG_GMCI_CANDIDATE` with `DEMOTED_HUB_PROMISCUITY_degree_5_gt_4`.

Why: one of the two regions reached HIGH with five partners. rggmci treats a region with more than four HIGH
partners as a hub. The limit of four is a setting of the method, not a measured property of genomes. A hub's pairs step down from HIGH to MODERATE. The pair
stays in the table as a place to look; `max_endpoint_hub_degree` gives the degree. Only contig-edge partners count
toward the degree.

## 4. Too little geometry: MODERATE

*Actinomadura bangladeshensis* DSM 45347 (SMJW00000000.1, 566 contigs)
- `Actinomadura bangladeshensis DSM 45347 / NODE_143_length_21100_cov_32.5167 = SMJW01000143.1 / region001 / BGC019`: terpene, reported `Full-contig` (at least 95% contig coverage).
- `Actinomadura bangladeshensis DSM 45347 / NODE_218_length_13334_cov_23.9278 = SMJW01000218.1 / region001 / BGC022`: lanthipeptide-class-iv, reported `Full-contig` (at least 95% contig coverage).

Result: score 32 and a `COMPLEMENTARY_SPLIT` gene check, but only 1 reference with good geometry (none from
MIBiG), so `DEMOTED_HIGH_TO_MODERATE_fewer_than_2_good_geometry_references`.

Why: HIGH needs at least two references where the fragments' hits overlap or sit side by side. One reference can be
chance. The two product classes differ as well, so the pair would need more support than this.

## Historical report on 40 genomes

The earlier report stated the following totals and settings. They were not revalidated here and are
not the four-archive source-profile census above.

rggmci on 40 public genomes (5 per genus across 8 genera, antiSMASH relaxed): 1,329 regions, of which 272 touch a
contig edge. 75 HIGH pairs, all across contigs, in 10 draft assemblies of 49 to 566 contigs. The other 30 genomes
have no HIGH pair, and 27 of them have no contig-edge region at all. One of the other three shows why two regions on
one contig are not paired: Saccharothrix variisporea DSM 43911 / Ga0197496_11 = RBXR01000001.1 / region001 / BGC001
and Saccharothrix variisporea DSM 43911 / Ga0197496_11 = RBXR01000001.1 / region032 / BGC032 sit at the two ends of
one 9.4 Mb contig and share type I PKS references. They are a related locus, not a rescue.
