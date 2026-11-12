# BLASTp → novelty workflow — five unmixed channels and one honest rank

Review how the BLASTp workflow separates evidence channels and ranking.  
This page is for researchers interpreting protein comparisons.

*Source of truth: `docs/BLASTP_NOVELTY_WORKFLOW.md`. Post-seal, advisory doctrine:
the ranking doctrine is advisory. Actual ingestion and search commands can author package overlays
and refresh post-seal checksums; consult [the command write contracts](../docs/ONLINE_BLASTP_PROTOCOL.md)
and work on a package copy when original bytes must remain fixed.*

## The claim ceiling (read before quoting any number)

The workflow records comparisons and supports **class-level capacity hypotheses**.
Similarity is not identity; a per-gene hit does not identify a product. High nr
identity establishes a close sequence under the declared search, not a characterized
compound. Scoped nr divergence does not establish taxonomic or chemical novelty.

## Keep homology channels and questions separate

| channel | database | the ONE question it answers |
|---|---|---|
| **nr** | NCBI nr (remote, paced RID crawl) | sequence similarity within the declared database, query, and result scope; not a taxonomic assignment |
| **KnownClusterBlast / MIBiG** | antiSMASH known-cluster results (in the bound package) | resemblance to a characterized reference family, under its recorded comparison scope |
| **ClusterBlast** | antiSMASH cluster comparison results (in the bound package) | similarity to deposited genome clusters; this is not the characterized MIBiG reference channel |
| **Swiss-Prot** | local curated BLAST DB | curated per-gene function sanity — a reviewed, named homolog (corroborating channel, sparse for BGC genes) |
| **ClusteredNR** | NCBI nr_cluster_seq (remote; shared NCBI search budget) | deep representative channel where nr is saturated — **ClusteredNR is NOT nr**; its numbers are never merged with nr's |

Keep each channel’s results and provenance separate; do not relabel hits across channels. Output
columns depend on the producer: the online CSV uses `channel`, `source_channel` and
`pct_positive`, while the SQLite hits store uses `subject_db`, `channel` and `pct_positives`.
Both report `pct_identity` separately from positives. Preserve missing values as missing. Verify
and retain the actual source/database binding: the manual nr-overlay guard checks
source-label text and does not independently establish the database.

## Grading the family anchor (capacity, not identity)

The thresholds below are this retained workflow's ranking heuristic, not universal biological
boundaries or proof that the current reader computed them. Bind the selected algorithm/version,
reference channel, denominator and coverage receipt before quoting an anchor grade.
These labels are not the `kcb_frontpage` parser's tiers: that reader uses similarity
and matching-gene thresholds (STRONG at ≥40/≥8, MODERATE at ≥25/≥5). Do not copy
a label between the two grading systems.

- **STRONG** — ≥4 genes hit one reference family, ≥25% of the admitted BGC gene-roster count, ≥55% median id.
- **PARTIAL** — ≥2 anchor genes, below the STRONG bar.
- **promiscuous-only** — hits only to genes recurring across unrelated clusters (scaffold/tailoring):
  gated OUT of "anchored" — these hits alone do not meet this heuristic's family-anchor rule.
- **NO_MIBiG** — use only for the declared, completed and admitted reference search with no qualifying anchor. Unavailable/unrun/unbound results remain distinct; absence of a stored hit is not itself a verified no-match.

Print the honest form `Ng @ X% → <family>`. Never print `= <compound>`.

## The lead signal: anchor × nr-distance

The retained advisory ranking combines a family anchor with nr divergence under the declared
search scope. These signals can prioritize review; they do not establish taxonomic, chemical or
pathway novelty. Two mandatory honesty rules:

1. **Denominator honesty** — always carry the gene count behind the median; an nr median over <~5
   genes is *soft* and must say so.
2. **Over-merge caveat** — a fused antiSMASH region (COMPOSITE_SEPARABLE) confounds both axes;
   verify the split before trusting either number.

**Candidate split interpretation:** retain both complete locus identities and review the recorded
channel, reference, geometry and contradictory evidence separately. Computational support can
prioritize a candidate relationship; it does not establish physical adjacency, a single complete
pathway or the exclusion of paralogy. Do not collapse loci or subtract a candidate rescue from a
biological BGC count.

## Remote-channel discipline (nr + ClusteredNR share one NCBI budget)

Use the selected current online runner's pacing, retry and ledger behavior, under explicit network
and sequence-submission authorization. Do not copy a historical observed open-RID count as a
guaranteed current NCBI service limit. nr and ClusteredNR remain distinct result channels even when
the runner coordinates their network budget. A failed submit or temporarily empty response is not
a tested biological no-hit. Preserve the request/status/error receipt and use the current
[online protocol](../docs/ONLINE_BLASTP_PROTOCOL.md) for recovery.

## Where it feeds

- **Phylogeny overlay** — per-strain novelty load painted onto tree tips (keyed to exact leaf
  labels, under the tree sign-off gate).
- **Mode B admission** — reconcile freshness and coverage against the selected card contract,
  independently binding the roster and query/result receipts. The text lint alone does not verify
  those bindings. Carry OBSERVATION / INFERENCE / ALTERNATIVE / FALSIFIER structure and retain
  typed holds for unresolved evidence; see [Mode B](Mode-B.md) for the promotion boundary.
- **Exclusions carry through** — use the selected cohort pack and actual
  `mamey/exclusions.py` accessors: hard exclusions, raw-assembly voids and audit-only
  QC holds are different states. The shipped generic default is empty; the accessor
  does not diagnose contamination or automatically identify chimeras. Pin the
  actual exclusion source and apply the reader's required scope.

## Related pages

[Mode B](Mode-B.md) puts protein comparisons into a locus-level evidence review.
