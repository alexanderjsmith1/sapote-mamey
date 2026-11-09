# RG-GMCI complementary-rescue atlas

`tools/rggmci_rescue_atlas.py` is an additive, post-seal review tool. RG-GMCI (reference-guided linkage of fragmented regions that share a reference cluster) and MIBiG are defined in [the glossary](GLOSSARY.md). It asks whether two
complete loci match distinct proteins in the same MIBiG comparator and whether those proteins
form coherent reference segments. It does not change the deterministic RG-GMCI result.

## Inputs

The tool does not make the pair, locus or hit tables. They come from your RG-GMCI review and per-strain MIBiG hit searches, and you pass their paths.

- a pair table (TSV) with these columns: `strain`, `identity_a`, `identity_b`,
  `rggmci_confidence` (tiers A and B need the value `HIGH_RG_GMCI_RESCUE`) and
  `subject_tiling_verdict`. `rggmci_score`, `terminus_override_note` and `pair` are
  carried through when present. `tools/definitive_bgc_ranker.py` writes `identity_a`
  and `identity_b` into its pair rows;
- a locus table keyed by `complete_identity`, with `boundary` (`Interior` or a
  contig-end value) and `current_antismash_products`;
- one or more `MIBIG_HITS_EXACT_IDENTITY.tsv` files, one per target folder, written by
  `tools/clear_match_finder.py` ([Clear match finder](CLEAR_MATCH_FINDER.md)). Columns
  read: `complete_identity`, `mibig_accession`, `mibig_product`, `subject_gene`,
  `query_gene`, `reference_rank`, `pct_identity`, `pct_coverage_interpretation`; and
- a locally supplied MIBiG GenBank tar archive for the reference-protein order and denominator.

Every locus must use `strain / full node-or-contig / region / BGC alias`. The check is on the
text only: an identity with fewer than four parts, an empty part, a region that is not
`regionNNN` or an alias that is not `BGCNNN` stops the build. Each pair identity must also appear
in the locus table. The tool does not compare the strain or node against a package, so a
shortened or generic node name passes if it is used the same way in every table. Bind each
identity to its package inventory yourself. No network access is used.

## Run

```bash
python tools/rggmci_rescue_atlas.py \
  --pairs pairs.tsv \
  --loci loci.tsv \
  --hits-root review/per_strain \
  --mibig references/mibig_gbk.tar.gz \
  --out review/rggmci_rescue_atlas
```

The tool writes these files into `--out`:

- `RGGMCI_RESCUE_CANDIDATES.tsv`: the complete candidate ranking;
- `RGGMCI_PAIR_REFERENCE_EVIDENCE.tsv`: the full pair-by-reference evidence;
- `RGGMCI_STRICT_RESCUES.tsv`: the strict A and B review subset;
- `RGGMCI_RESCUE_ATLAS.md`: a Markdown front door;
- `RGGMCI_RESCUE_ATLAS_RECEIPT.json`: a receipt with counts and the claim ceiling.

Comparator names remain comparator
labels. Physical joining, exact product identity, pathway completeness, expression, production,
activity, novelty, and scientific acceptance remain unresolved without independent evidence.

## Evidence tiers

- **A** requires high RG-GMCI support, at least three distinct comparator proteins from each locus,
  ten combined proteins, no shared subjects, broad reference coverage, ordered tiling, boundary
  support, and no generic modular caution.
- **B** accepts a smaller but still disjoint, ordered, high-ranked and boundary-supported signal.
- **C** retains plausible complementary pairs for biological review.
- **D** holds every other pair: shared-reference signals that lack breadth, specificity or
  disjointness, and pairs with no MIBiG reference recorded for both loci
  (`reference_tiling_topology` = `NO_SHARED_EXACT_REFERENCE`). A pair with no shared reference
  only means the supplied hit tables did not record one. It is not evidence that none exists.

The numeric score orders evidence within these gates. It is a prioritization score, not a posterior
probability or biological truth value.

A value that was not measured is blank, not zero. `reference_roster_state` says whether the
reference roster loaded (`LOADED`, `REFERENCE_ROSTER_NOT_LOADED` or `NO_SHARED_REFERENCE`), and
`unmeasured_fields` lists the blank gate inputs. When the roster did not load,
`reference_total_proteins` and `reference_protein_coverage` are blank. A pair with no shared
reference has blank medians, coverage, disjointness and ranks. The calculation uses the same
values as before for a blank field (0 for coverage, identity and disjointness, 999 for rank), so
tiers and scores are unchanged. A pair with blank coverage cannot reach tier A or B.

## Receipt scope, reference versions, and recovery

The tool prints its receipt JSON to stdout. `"status": "PASS"` and exit 0 mean the atlas tables were written, including an empty or all-D candidate set. The receipt records counts and claim ceiling but no input/archive/output hashes, software version, or per-query receipt admission. Keep an external run record that hashes the pair/locus tables, every discovered hit table, exact MIBiG archive, renderer/source version, and outputs. Use a tightly scoped `--hits-root`: discovery recursively reads every matching `MIBIG_HITS_EXACT_IDENTITY.tsv` underneath it. An identity string alone does not prove the protein/query/run receipt is current.

The code strips accession version suffixes when joining hits and archive names. The archive denominator is the number of regex-extracted `/protein_id` entries, not a separately validated complete reference-CDS roster. Verify archive version, unique subject identifiers, reference coverage and denominator before interpreting the score/tier. Duplicate archive accession stems overwrite the prior roster; hit rows may include repeated alignments. Resolve reference-version mismatches before interpreting a score.

Existing output directories are accepted and fixed files are overwritten without staged all-or-nothing publication. A failed write can leave a partial new atlas beside an old receipt. Choose a fresh output directory; preserve prior artifacts, resolve the failure, and check all expected files against the new run record before sharing. No new source evidence or scientific acceptance is generated by this tool.
