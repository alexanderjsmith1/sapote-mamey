# Cohort protein comparison contract for Mode B

## Purpose

`mamey cohort-proteins` creates a portable, within-project protein-comparison channel. It answers a question that external BLASTp and whole-region BiG-SCAPE do not answer directly: for a selected gene in one exact BGC, which proteins in the measured AS, SID, type/reference, or other configured cohorts are closest, and do several of those proteins recur together in the same comparator BGC neighborhood?

This channel is intended primarily for Mode B §45, but its evidence can be routed into other sections when the section names the exact genes and preserves the claim ceiling.

## Identity and denominator rules

1. Protein SHA-256 is the primary molecular identity.
2. An occurrence is identified by `strain / full node-or-contig / region / BGC alias`, locus tag, and protein SHA-256.
3. Identical proteins in overlapping antiSMASH regions remain visible occurrences but do not become independent strain observations.
4. Every comparison states the measured cohort denominator as distinct strains, exact BGC loci, protein occurrences, and distinct protein sequences.
5. The focal strain is excluded from its own cohort comparison when `--query-cohort` is supplied. This prevents the focal protein or overlapping calls from winning as a false non-self comparison.
6. Missing package protein FASTAs, unresolved aliases, and incomplete exact-locus identities are typed quarantine states, not biological absences.

## Commands

Build a reusable database from any named package roots:

```bash
mamey cohort-proteins build \
  --cohort AS=/path/to/as/runs \
  --cohort SID=/path/to/sid/runs \
  --cohort TYPE=/path/to/type/runs \
  --out project_evidence/cohort_proteins.sqlite
```

Legacy packages that predate `*_proteins.faa` can enter through an exact-locus GBK register instead of being treated as absent:

```bash
mamey cohort-proteins build \
  --cohort AS=/path/to/current/as/runs \
  --gbk-register /path/to/governed_sid_region_gbks.tsv \
  --out project_evidence/cohort_proteins.sqlite
```

The tab-separated register requires `cohort`, `strain`, `full_node_or_contig`, `region`, `bgc_alias`, and `gbk_path`; `gbk_sha256` is optional but recommended. The adapter never derives a strain or alias from the filename. It requires the optional `bio` extra to parse GenBank translations and quarantines missing files, SHA mismatches, parse failures, incomplete identities, and CDSs without locus tags.

Compare the automatically selected core, resistance-routing, and transporter genes of one exact BGC:

```bash
mamey cohort-proteins compare \
  --database project_evidence/cohort_proteins.sqlite \
  --package runs/STRAIN/package \
  --bgc "$SECONDARY_ALIAS_RESOLVED_INSIDE_PACKAGE" \
  --query-cohort AS \
  --outdir project_outputs/STRAIN/full_node/region/BGC041/cohort_proteins
```

`--bgc` is only a lookup key inside a single bound package. Every output row and heading emits the complete exact-locus display. Use `--genes gene1,gene2,...` to override automatic core/resistance/transport selection.

## Ranking and report states

The current portable implementation uses a disclosed two-stage method:

1. length-gated 4-mer prefilter, retaining the top 40 candidates per query gene and cohort;
2. local BLOSUM62 alignment with gap-open -11 and gap-extension -1.

Ranking uses local alignment score, then query coverage, identity, and deterministic exact-locus/gene tie breakers. The result table always provides identical-residue count, alignment-column denominator including gaps, BLOSUM-positive count, identity, positives, query coverage, subject coverage, protein SHA-256 values, and exact source paths.

The states are navigation labels, not biological verdicts:

- `STRONG_WHOLE_PROTEIN_FAMILY_NAVIGATION`: at least 60% identity and 80% bilateral coverage;
- `MODERATE_WHOLE_PROTEIN_FAMILY_NAVIGATION`: at least 40% identity and 70% bilateral coverage;
- `WEAK_CLOSEST_AVAILABLE`: the highest-ranked measured candidate does not meet the moderate threshold.

Weak rows are retained so a card can say “closest measured protein” rather than the misleading “nothing found.” They must be described as weak.

## Neighborhood extension

After per-protein ranking, matches are grouped by complete comparator locus. Multi-gene co-occurrence and order are reported separately from individual similarity. This allows the author to distinguish:

- one shared enzyme family;
- two or more component genes in the same comparator BGC;
- order-concordant, reverse-order, mixed-order, or order-unmeasured neighborhoods;
- recurrence of only one component of an apparently composite focal region.

Co-occurrence is not operon proof, physical joining, orthology, or complete pathway identity.

## Mode B routing

The same measured channel can improve these sections:

| Mode B section | Appropriate use |
|---|---|
| §§5–7 | Name the exact core/tailoring genes and show which machinery is cohort-conserved, component-specific, or weakly represented. |
| §8 | With a separately bound nucleotide channel, test boundary continuation, near-identical duplicated segments, and possible assembly splits. |
| §25 | Compare exact transporter proteins and ask whether they recur beside similar core machinery. |
| §27 | Compare exact resistance-like candidates, then require biosynthetic-class concordance and same-locus core context before any producer-protection hypothesis. |
| §38 | Replace unsupported “unique” language with measured within-cohort recurrence. This does not establish global novelty. |
| §41 | Report distinct-strain and exact-locus prevalence separately from repeated region observations. |
| §44 | Detect exact protein duplicates and near-duplicate ordered neighborhoods for dereplication. |
| §45 | Primary output: ranked AS/SID/internal-cohort gene comparisons with count-first metrics and neighborhood agreement/mismatch. |
| §46 | Add TYPE/reference cohorts using the same database contract; do not substitute a whole-genome name for gene-level evidence. |
| §47 | Select nonredundant comparator proteins/loci for phylogenies, synteny review, and targeted experiments. |

## BLASTN / nucleotide extension

Protein comparison should remain primary for functional-family navigation because coding sequences can diverge while proteins remain recognizably homologous. A separate, never-merged nucleotide channel is valuable for:

- near-identical strain-to-strain transfer or duplication;
- distinguishing alleles from broader protein-family matches;
- testing region boundaries and flanking synteny;
- detecting frameshifts, premature stops, or gene-model differences;
- selecting conserved or discriminating primer targets.

The nucleotide channel must bind exact CDS or region sequences and report its own aligned-base counts, identity, coverage, strand, and source SHA. It must not overwrite or be labeled as protein BLASTp evidence.

## Claim ceiling

Within-project similarity is not identity or orthology. Neighborhood recurrence is not pathway identity. Capacity is not production. A transporter or resistance-family match is not producer protection without gene-specific biochemical evidence and compound-class concordance. The database denominator is the measured package set, not nature.
