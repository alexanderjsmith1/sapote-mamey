# Cohort protein comparison contract for Mode B

## Purpose

`python mamey_run.py cohort-proteins` creates a portable, within-project protein-comparison channel. It answers a question that external BLASTp and whole-region BiG-SCAPE do not answer directly: for a selected gene in one exact BGC, which proteins in the measured AS, SID, type/reference, or other configured cohorts are closest, and do several of those proteins recur together in the same comparator BGC neighborhood?

This channel is intended primarily for Mode B §45, but its evidence can be routed into other sections when the section names the exact genes and preserves the claim ceiling.

## Identity and denominator rules

1. Protein SHA-256 is the primary molecular identity.
2. An occurrence is identified by `strain / full node-or-contig / region / BGC alias`, locus tag, and protein SHA-256.
3. Identical proteins in overlapping antiSMASH regions remain visible occurrences but do not become independent strain observations.
4. Every comparison states the measured cohort denominator as distinct strains, exact BGC loci, protein occurrences, and distinct protein sequences.
5. Self-exclusion applies only inside the cohort whose label exactly equals `--query-cohort`, using the focal strain string. The supplied label is not validated as a cohort-membership assertion; a misspelling or duplicate inclusion in another cohort can leave self matches. Check the actual cohort labels and selected strains before calling results non-self. Reported cohort denominators are whole-catalog counts before self-exclusion, not candidate counts after exclusion.
6. Missing package protein FASTAs, unresolved aliases, and incomplete exact-locus identities are typed quarantine states, not biological absences.

## Commands

Build a reusable database from any named package roots:

```bash
python mamey_run.py cohort-proteins build \
  --cohort AS=/path/to/as/runs \
  --cohort SID=/path/to/sid/runs \
  --cohort TYPE=/path/to/type/runs \
  --out project_evidence/cohort_proteins.sqlite
```

Legacy packages that predate `*_proteins.faa` can enter through an exact-locus GBK register instead of being treated as absent:

```bash
python mamey_run.py cohort-proteins build \
  --cohort AS=/path/to/current/as/runs \
  --gbk-register /path/to/governed_sid_region_gbks.tsv \
  --out project_evidence/cohort_proteins.sqlite
```

The tab-separated register requires `cohort`, `strain`, `full_node_or_contig`, `region`, `bgc_alias`, and `gbk_path`; `gbk_sha256` is optional but recommended. The adapter never derives a strain or alias from the filename. It requires the optional `bio` extra to parse GenBank translations and quarantines missing files, SHA mismatches, parse failures, incomplete identities, and CDSs without locus tags.

Compare the automatically selected core, resistance-routing, and transporter genes of one exact BGC:

```bash
python mamey_run.py cohort-proteins compare \
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

Ranking uses local alignment score, then query coverage, identity, and deterministic exact-locus/gene tie breakers. For aligned candidates the table provides identical-residue count, alignment-column denominator including gaps, BLOSUM-positive count, identity, positives, query coverage, subject coverage, protein SHA-256 values and comparator source-package paths. The prefilter restricts subject length to approximately 0.55–1.80 times query length, drops zero shared 4-mer candidates and aligns only the retained set. A missing row is not an exhaustive no-homology result. Ranking is within that screened set.

The states are navigation labels, not biological verdicts:

- `STRONG_WHOLE_PROTEIN_FAMILY_NAVIGATION`: at least 60% identity and 80% bilateral coverage;
- `MODERATE_WHOLE_PROTEIN_FAMILY_NAVIGATION`: at least 40% identity and 70% bilateral coverage;
- `WEAK_CLOSEST_AVAILABLE`: the highest-ranked measured candidate does not meet the moderate threshold.

Weak aligned rows are retained for within-screen navigation. Inspect `alignment_skipped` before describing any row as measured: a pair with either sequence longer than `MAMEY_MAX_ALIGN_AA` (default 10,000) is not aligned and receives placeholder zero metrics plus a skip reason; the current navigation state still reads `WEAK_CLOSEST_AVAILABLE`. Those placeholders are unavailable alignment evidence, not measured zero identity or a tested weak match. If explicit `--genes` entries lack sequences, the loader skips them; compare requested and resolved query lists and retain omissions as holds.

## Outputs, mutation and recovery

Build writes the selected SQLite path and its sibling `.receipt.json`, with database
hash, occurrence/cohort counts and quarantine summary. Missing packages or failed
bindings can still yield `PASS_WITH_TYPED_QUARANTINE`, including an empty catalog;
zero exit does not establish complete cohort coverage. Inspect quarantine and input
counts. Package catalog ingestion currently builds an alias-to-row dictionary,
so conflicting duplicate inventory aliases are not independently quarantined;
require the supplied inventory's alias uniqueness before using its joins.

An existing catalog is refused unless `--replace` is selected. Replacement swaps
the database before writing its receipt; it is not a crash-atomic database/receipt
pair. Preserve the old catalog and receipt for a separately authorized rebuild.
After interruption, verify that the receipt's database hash matches current bytes.

Compare opens the database read-only/immutable, so use a closed, checkpointed
snapshot; the handler does not check WAL/journal sidecars. It creates `--outdir`
with `exist_ok=True` and overwrites same-stem TSV/Markdown/receipt files. Use a fresh
output folder to retain earlier evidence; the label “additive” does not provide an
existing-output guard. Outputs are `__COHORT_PROTEIN_MATCHES.tsv`,
`__COHORT_NEIGHBORHOOD_SUMMARY.tsv`, `__MODEB_SECTION45_PAYLOAD.md` and
`__COHORT_PROTEIN_COMPARISON_RECEIPT.json` beneath an exact-locus-derived stem.

The comparison receipt binds output hashes but does not bind the input database or
focal package files. Retain an external run record binding those inputs, parameters,
actual query roster and matching build receipt; the comparison's `PASS` alone is
not sufficient for reproducible input identity. A version-aware input-binding and
skip-state repair remains owning-code work.

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
