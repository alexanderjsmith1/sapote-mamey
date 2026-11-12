# Reading rggmci output

## The input it needs

Use a saved antiSMASH result ZIP with region GenBank files (`<contig>.region<NNN>.gbk`) and usable cluster-level reference records from `clusterblast/` (CB), `knownclusterblast/` (KCB), or both. RG-GMCI keeps these channels separate: cross-genome CB and characterized-reference KCB can each support a candidate pair. KCB-only evidence is not automatically unscorable. SubClusterBlast records are retained as a separate marker channel and do not supply pairing geometry.

To get these records in a new antiSMASH run, turn on KnownClusterBlast and ClusterBlast: `--cb-knownclusters --cb-general` on the command line, or the matching options on the web server, where ClusterBlast is off by default.

When neither CB nor KCB supplies usable records, there are no reference-supported pairs from this input. That is a missing/empty evidence state, not proof that no fragmented pathway exists. Read `reference_map_status`, `reference_parse_error_count` and the original channel files; a parsed map can still contain no eligible shared pair. This guide does not require resubmitting or regenerating antiSMASH output merely because one channel is absent.

## Pairs (`<genome>_pairs.tsv`, or `--pairs`)

One row per kept pair of regions: the top 1,000 by rank, plus every HIGH pair below them. `pairs_total` in the JSON
counts every scored pair. `pairs_exported` in the summary counts retained rows; their difference is
truncation, not evidence that omitted pairs were absent. The JSON also records that difference in
`rggmci_summary.ranked_pairs_not_exported`. A historical worked archive scored 1,360 and retained 1,000,
so 360 were not exported; no new run on that archive is claimed here. Every HIGH pair beyond the first
1,000 is retained, so 1,000 is not an absolute export ceiling.

| column | meaning |
|---|---|
| `identity_a`, `identity_b` | complete canonical endpoint labels: logical strain / full physical contig / region / BGC alias; retain the source archive/result hashes and do not infer taxonomy from the logical label |
| `region_a`, `region_b`, `source_gbk_a`, `source_gbk_b` | exact region labels and source member locators for each endpoint |
| `bgc_a`, `bgc_b` | source-scoped region aliases, numbered in reading order; not stable cross-run join keys |
| `contig_a`, `contig_b` | the full contig names antiSMASH used; use them to find the regions |
| `products_a`, `products_b` | antiSMASH's product annotations for each region |
| `edge_a`, `edge_b` | `Full-contig`: the region covers 95% or more of its contig. `Edge`: it starts or ends within 5 kb of a contig end. `Interior`: neither. `Unknown`: contig length not available. On a circular contig the origin is not an end, so only `Full-contig` or `Interior` apply |
| `rggmci_score` | the pair score before the acceptance gates |
| `rggmci_confidence` | `HIGH_RG_GMCI_RESCUE`, `MODERATE_RG_GMCI_CANDIDATE` or `LOW_SHARED_REFERENCE_SIGNAL`, after the gates |
| `acceptance_gate` | which gate kept or demoted the pair, and why |
| `supporting_references` | reference clusters hit by both regions |
| `good_geometry_references` | references where the two regions' hits overlap or sit side by side |
| `both_at_contig_ends` | whether both regions are `Edge` or `Full-contig`. It comes from those labels, so `Edge` means within 5 kb of an end; it does not show that a gene runs off the end. A description, not a rating |
| `subject_tiling_verdict` | the gene-level check on shared references: `COMPLEMENTARY_SPLIT` (the regions hit different genes), `TERMINUS_TRUNCATION_SPLIT` (a fragment cut at a contig end), `OVERLAPPING_PARALOG` (they hit the same genes), `MIXED_SUBJECT_SIGNAL` (some of each), `INSUFFICIENT_SUBJECT_DATA` (too few reference genes hit, or too little geometry, to call either way; not a negative result) |
| `max_endpoint_hub_degree` | the larger number of HIGH partners either region had before the hub guard |
| `best_sources` | the five best supporting references, with where each region's hits sit on them and how many proteins each contributed |
| `depth_a`, `depth_b` | each contig's read depth, from the `_cov_` part of a SPAdes contig name; blank for other names |
| `depth_ratio`, `depth_flag` | the lower depth over the higher. `DEPTH_MISMATCH` below 0.67 (a plasmid, a repeat, or a second population), `DEPTH_CONSISTENT` otherwise, `DEPTH_UNAVAILABLE` without depths. A flag, never a demotion |
| `completion_tier` | whether reference-guided completion ran: `FULL`, `NO_ALIGNER`, `NO_MIBIG_PROTEINS`, `NO_WHOLE_GENOME_GENBANK` or `OFF` |
| `ref_completion_partner` | `yes` when one region's contig is an accepted partner for the other region's reference; `no`; `no_reference` when neither region had a reference. Blank unless `FULL` |
| `split_gene_links` | how many genes split across the two regions' contigs were called `CLEAR`; one broken gene counts once, however many references see it. Blank unless `FULL` |
| `residue_tiling` | for pairs the paralog gate demoted, which stretch of each shared MIBiG protein each region covers: `COMPLEMENTARY_RESIDUES`, `OVERLAPPING_RESIDUES`, `MIXED_RESIDUES`, `THIN_RESIDUES`, `NO_SHARED_MIBIG_REFERENCE`, `REGION_SOURCE_UNAVAILABLE` (a region's own GenBank file or its proteins could not be read, so nothing was placed) or `NOT_TESTED`. These fields are initialized when the residue layer is invoked. `NOT_TESTED` can accompany `DIAMOND_NOT_FOUND`, `DIAMOND_DB_NOT_FOUND` or `NO_PAIRS_IN_SCOPE` without an alignment search; read `residue_tiling_status` and `pairs_tested` (see below) |

### `acceptance_gate` verdicts

A pair can carry several, joined by `+`.

| verdict | meaning |
|---|---|
| `OK_shared_specific_product_class` | the regions share a specific product class (compared by antiSMASH family) |
| `OK_compatible_hybrid` | the classes differ but form a known hybrid (e.g. NRPS with PKS) |
| `OK_cocluster_exempt_complementary_shared_mibig` | two different specific classes that would otherwise fail, kept because the regions tile 2 to 6 MIBiG clusters together |
| `RESTORED_sugar_arm_glycosylated_partner` | a sugar-only fragment returned to HIGH next to a backbone partner whose region names a glycosyltransferase |
| `DEMOTED_HIGH_TO_MODERATE_no_specific_product_class_after_exclusions` | no specific class left once saccharide, other, NAPAA, aminopolycarboxylic-acid and the RiPP umbrella word are set aside |
| `DEMOTED_HIGH_TO_MODERATE_incompatible_product_classes` | classes that do not combine into one pathway |
| `DEMOTED_HIGH_TO_MODERATE_distinct_ripp_subclasses` | two different RiPP subclasses |
| `DEMOTED_HIGH_TO_MODERATE_fewer_than_2_good_geometry_references` | fewer than two references where the hits overlap or sit side by side |
| `DEMOTED_HIGH_TO_MODERATE_R1_both_drop_class` | both regions carry only saccharide, NAPAA, hglE-KS, PKS-like or other |
| `DEMOTED_HIGH_TO_MODERATE_R2_no_strong_references` | no reference with strong support |
| `DEMOTED_HIGH_TO_MODERATE_R3_noise_class_both_sides` | neither region carries a specialist class (only fatty_acid, saccharide, NAPAA, hglE-KS or other) |
| `ST-PARALOG_no_complementarity_proof` | the gene-level check finds both regions hit the same reference genes, which is a computational overlapping-reference signal compatible with duplicate or related loci, not proof of two copies; the pair drops to LOW |
| `DEMOTED_HUB_PROMISCUITY_degree_N_gt_4` | one region has more than four HIGH partners; all its HIGH pairs step down |
| `DEMOTED_TO_LOW_shared_reference_only_no_geometry_no_split_signal` | the regions share references but nothing places them side by side |

**Only contig-edge regions are paired.** rggmci pairs a region when antiSMASH flags it as touching a contig edge
(`/contig_edge="True"` on the region feature). When a file has no flag, or its region features disagree, the
`Edge`/`Full-contig` status above is used instead. An explicit region-feature `False` excludes the region,
even if its fallback status is `Edge`; only the region feature's flags count. A missing region member also
uses the fallback, and an unreadable ZIP returns the fallback set. This is a rule of the method, not a finding: a region inside a
contig can still lack pieces the assembly or antiSMASH did not show, and rggmci does not look for them. Two regions
that both reach a contig end may be fragments the assembly separated; rggmci does not claim a join.

## Related loci (`related_locus_pairs` in the JSON)

Pairs that involve an interior region, or two regions on one contig, are scored the same way and kept apart.
Their `rggmci_confidence` is set to `RELATED_LOCUS_NOT_A_RESCUE`. The original grade is in `shared_reference_grade`,
the interior side in `interior_side`, and the reason in `related_because` (`interior region`, `same contig`, or both). They can
point to a second copy of a cluster, a separate locus of one pathway, or a shared cassette.
They are never contig rescues and never feed the rescue list, candidate groups or the hub count.

## Candidate groups (`CANDIDATE_GROUPS.tsv`)

HIGH pairs on different contigs that share a region are gathered into one group, so a pathway that may
be spread over several fragments reads as one candidate. `n_at_contig_ends` counts the group's regions that
run to a contig end. Groups are listed with the most HIGH pairs first.

MODERATE pairs never join groups. Chained together, they link a genome's similar clusters into one large
network that describes no single pathway. `possible_moderate_links` lists the cross-contig MODERATE pairs
that touch a group, as places to look next.

## Summary (`SUMMARY.tsv`)

One row per genome: regions, `scored_pairs` (every scored pair), `pairs_exported` (the rows kept in the pair
table), HIGH, MODERATE, how many HIGH pairs cross contigs and how many of those
have both regions at contig ends, how many groups, and the size of the largest group. Three columns describe
reference-guided completion: `completion_tier`, the number of accepted partner contigs, and the number of `CLEAR`
split genes. Truncation is explicit in the console and is the difference between `scored_pairs` and
`pairs_exported` in this table. `high` and `moderate` count all scored pairs; they need not sum to the
retained count, which also includes LOW rows. Omitted rows cannot be recovered from this capped JSON or
pair table alone. An `error` column records a ZIP that could not be read; the
batch carries on past it.

## Reference-guided completion

Written with `--out-dir` as three tables per genome, and under `reference_completion` in the JSON. Every row starts
with the tier, the aligner, the region (`<genome> / <contig> / regionNNN / <alias>`), its reference, how the reference
was chosen (`knownclusterblast`, or `discovered` with its protein count, ties and size check) and the reference's
compound names. When the tier is not `FULL`, each table holds one row that names the tier.

The reference is the region's best-ranked KnownClusterBlast MIBiG hit that the database holds. A region with no such
hit is given the MIBiG cluster with the most region proteins at 35% identity or more over half the protein or more.
This needs at least two proteins, one of them with a biosynthetic role, in a cluster of 250 kb or less.

### Reference genes (`<genome>_reference_completion.tsv`)

One row per reference gene.

| column | meaning |
|---|---|
| `status` | `PRESENT_IN_CORE` (a match inside the region at 30% identity or more over half the reference protein, or 25% with e ≤ 1e-10), `MISSING_FOUND_CLEAR` (the best match elsewhere reaches 35% and beats the next candidate's score by 20% or more), `MISSING_FOUND_AMBIGUOUS`, `MISSING_NOT_FOUND` |
| `best_identity_pct`, `best_coverage_pct`, `best_locus`, `best_contig`, `best_region_identity` | the best match and where it sits; a match outside every region is labeled `(no antiSMASH region)` |
| `reciprocal_best` | whether this reference gene is that protein's own best match among the reference's genes |
| `partner_verdict` | for a find outside the region: `SUPPORTED` (another find of this reference sits within 10 kb), `SINGLE_GENE`, `HOUSEKEEPING_CONTEXT` (a lone find beside primary-metabolism genes; needs the Pfam scan) or `PARALOG_FAMILY` (the reciprocal search fails, or five or more other genome proteins match the same reference gene) |
| `reciprocal_best_mibig`, `reciprocal_best_identity`, `reciprocal_reference_identity`, `reciprocal_family_ratio` | the find's own best MIBiG cluster, and how its best score against the reference's compound family compares. Below 0.9 the best score against the selected reference's compound family is less than 90% of the best MIBiG score for that aligned stretch, and the verdict uses it as a paralog-family signal. Database coverage, shared domains and alignment scope limit that signal; it does not assign a compound family |
| `paralogs_in_genome`, `adjacent_finds`, `housekeeping_neighbours`, `neighbour_pfams` | the counts behind the verdict; `neighbour_pfams` lists only the housekeeping-marker domains found |

The reciprocal search uses the stretch of the genome protein that matched the reference and every MIBiG target, not
a top few. A conserved family can match many clusters almost equally.

### Split genes (`<genome>_split_genes.tsv`)

A reference gene in two pieces on different contigs. Each piece covers 40 residues or more of the gene and less than
80% of it. The pieces overlap by 20 residues or less and together cover half the gene or more. Each piece's open end
lies within 300 bp of a contig end.

| `split_call` | meaning |
|---|---|
| `CLEAR` | the pieces beat any whole-gene match elsewhere by 10 identity points or more |
| `WEAK` | they beat it by less |
| `RIVAL_STRONGER` | a whole gene elsewhere matches as well: likely paralog fragments |
| `MODULAR_UNRESOLVED` | the reference gene or a piece is an assembly-line protein (a KS or C domain, or two or more A domains), where module paralogy can fake two halves |
| `RECURRENT_COMMON_GENE` | the same two pieces also split against references of unrelated compound families, at least one belonging to a region that holds neither piece: a broken common gene, such as a regulator. `split_call_before_recurrence` keeps the call it replaced |

### Partner contigs (`<genome>_partner_contigs.tsv`)

One row per contig, other than the region's own, that carries a find or a split piece.

| column | meaning |
|---|---|
| `position_ok` | a find lies within 20 kb of a contig end, or the contig is under 40 kb |
| `depth_ratio`, `depth_ok` | the contig's read depth over the region's contig's; fails below 0.67, blank without depths (blank never fails) |
| `partner_verdicts` | the verdicts of its finds, and its split pieces |
| `support_ok` | two or more passing finds with one `SUPPORTED`, or a passing `CLEAR` split piece. A find passes when it is near a contig end and `SUPPORTED` or `SINGLE_GENE`; mobile-element genes (transposase, integrase, recombinase, insertion element) never count |
| `accepted`, `reason` | `accepted` needs support and a depth that does not fail. `reason` is `accepted`, `depth`, `support` or `no passing finds` |

### Residue tiling (pair fields beginning `residue_`)

`--reference-completion` off disables reference-guided completion only. An explicit `--diamond-db` can still invoke residue tiling. Inspect each layer's status separately.


For pairs the paralog gate demoted (`ST-PARALOG_no_complementarity_proof`), each region's proteins are aligned with
DIAMOND against the MIBiG clusters both regions share in KnownClusterBlast. Each side is placed on a cluster with
every residue used once. A cluster is complementary when each side places 300 residues or more and they share 10% or
less of the smaller side, and overlapping when they share more. It runs with `--diamond-db`, or by default when the
completion database has its DIAMOND index. With `--diamond-db`, `--residue-scope all` tests every pair. The detail fields describe the
cluster both sides match best. Against relatives near 50% identity, modular PKS often reads `MIXED_RESIDUES`: one
module cannot be told from another.

The JSON's `residue_tiling_status.state` is `RAN`, `DIAMOND_NOT_FOUND`, `DIAMOND_DB_NOT_FOUND` or
`NO_PAIRS_IN_SCOPE`. `pairs_tested` counts only the pairs that had a shared MIBiG cluster to place. A pair with
none reads `NO_SHARED_MIBIG_REFERENCE` and is not counted, so `RAN` with `pairs_tested` 0 can happen.
`regions_source_unavailable` lists regions whose proteins could not be read; their pairs read
`REGION_SOURCE_UNAVAILABLE` and are counted in `pairs_source_unavailable`. A pair outside `--residue-scope`
keeps `NOT_TESTED`.

| Field | Meaning |
|---|---|
| `residue_references_tested` | the shared MIBiG clusters tested for this pair |
| `residue_complementary_references`, `residue_overlapping_references` | how many of those clusters were complementary, and how many overlapping |
| `residue_top_reference`, `residue_top_class` | the cluster both sides match best, and its class |
| `residues_a`, `residues_b` | the cluster residues each side was placed on |
| `residue_identity_a`, `residue_identity_b` | each side's identity on that cluster |
| `residue_overlap` | the residues both sides were placed on, as a fraction of the smaller side |
| `residue_stretches_a`, `residue_stretches_b` | up to six of each side's longest placements, as `<reference protein>:<start>-<end>@<identity>` |

The detail fields are blank when no cluster was placed.

## BLASTp queries (`rggmci fasta`)

- `<genome>_blastp_NN.fasta`: one file per NCBI submission, at most 20 proteins and 85,000 residues.
  Header fields: genome, region alias, slot, role (`core`, `additional` or `edge`), gene, contig, region,
  coordinates, protein length and why it was chosen. Don't edit the headers; the layer reads them back.
- `blastp_manifest.json` and `blastp_manifest.tsv`: every query, its region and the pairs it serves, the
  selection settings, and the SHA-256 of the antiSMASH ZIP.
- `HOW_TO_BLASTP.md`: the steps on the NCBI site.

## BLASTp layer (`rggmci blastp-layer`)

- `blastp_proteins.tsv`, one row per query protein:
  - `blastp_status` is `HIT`, `NO_HITS` (XML2 lists the query with nothing), `NO_HITS_AFTER_EXCLUSION` or
    `NOT_IN_RESULTS` (not in any file given; could be not run or no hits).
  - The top hit's identity, query coverage, e-value, accession, title and organism.
  - `top_organisms` lists up to five, as named in the XML2.
- `blastp_pairs.tsv`, one row per pair:
  - The pair's `rggmci_confidence`, copied unchanged.
  - Per side, proteins sent, with hits, with no hits, not in the results, and the median top identity.
  - `organisms_with_homologs_of_both` and `shared_organisms` need the XML2 for both sides of the pair. Without it they read "needs XML2"; when the XML2 covers only one side they read "needs XML2 for side a" (or b) and give no count, because the other side's organisms are unknown, not absent.
- `blastp_layer.json`: all of the above, plus query headers in the results that matched nothing in the
  manifest (renamed headers are reported, never guessed).

## Gene context on pairs

When the ZIP's gene annotations allow it, each pair carries a description of the two fragments' genes. These fields
never change a score or a confidence. They are thresholds on antiSMASH's predicted gene roles, so check the genes
before reading anything into them. Without gene context for one side, `functional_rescue_class` and
`modular_continuation` read `UNKNOWN_NO_PROFILE` and the other fields are blank.

| Field | Meaning |
|---|---|
| `a_functional_roles`, `b_functional_roles` | the gene roles present in each fragment |
| `a_core_fraction`, `b_core_fraction` | `core / (core + tailoring + transport + regulatory)` from predicted role counts, excluding `other`. A zero denominator returns 0.0, a software fallback rather than evidence of accessory function; a missing profile returns `None` (blank in TSV), not zero |
| `functional_rescue_class` | `COMPLEMENTARY` (the core fractions differ by 0.20 or more and the lower is 0.30 or less), `BOTH_CORE` (both are 0.35 or more and within 0.20 of each other, a core-rich computational descriptor that does not establish paralogy or exclude a modular split), `ACCESSORY_ONLY` (both are 0.30 or less; this includes zero-denominator profiles and does not require tailoring genes) or `AMBIGUOUS` (none of these) |
| `modular_continuation` | `MODULAR_CONTINUATION` (both fragments carry assembly-line genes and there is at most one release gene between them), `MODULAR_TWO_RELEASES` (each side has its own release gene), `MODULAR_CONTINUATION_MULTI_RELEASE_ONE_SIDE`, or `NOT_MODULAR` (one side has no assembly-line gene) |
| `a_assembly_line_cds`, `b_assembly_line_cds`, `a_release_cds`, `b_release_cds` | the gene counts behind `modular_continuation` |

## Contig ends

| Field | Meaning |
|---|---|
| `terminus_sequence_state_a`, `terminus_sequence_state_b` | the sequence at the contig end each region touches: `COMPLEX_TERMINUS`, `LOW_COMPLEXITY_TERMINUS`, `HOMOPOLYMER_TERMINUS`, `AMBIGUOUS_TERMINUS` (holds N or another non-ACGT base), `TERMINUS_SEQUENCE_UNAVAILABLE`, or `NOT_APPLICABLE` when the region touches no contig end |
| `junction_evidence_state` | `SEQUENCE_COMPLEXITY_CLEAR` only when every truncated contig end was read and is complex; `SEQUENCE_COMPLEXITY_UNRESOLVED` when an end could not be read or is ambiguous; `LONG_READ_ONLY` when a truncated end is low-complexity or a homopolymer, so only long reads can settle the join; `NOT_APPLICABLE` when the pair has no truncated end |

## What a candidate is, and what it is not

- RG-GMCI surfaces fragments by biosynthetic logic seen through homology. Two or more regions matched
  adjacent or overlapping parts of the same reference clusters, so they may belong to one pathway.
- That is one line of evidence. The second is the genes themselves: do the domains on the fragments
  complement each other into one coherent assembly line, with loading, extension, tailoring and release
  each accounted for once? Do they point to the same compound family?
- A candidate is not a joined contig. It does not show that the fragments are physically adjacent, and it
  does not name a compound.
- To check one, open each region's GenBank file and read the genes and domains. A long-read assembly
  settles physical adjacency.
