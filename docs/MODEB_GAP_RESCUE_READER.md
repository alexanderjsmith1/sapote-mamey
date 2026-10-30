# Read saved gap-rescue evidence in a Mode B card

Use existing gap-rescue results to fill the evidence scaffold in a `current50_v2`
card. You need the matching package, focal BGC and saved rescue run. 

Run from the bundle directory, selecting the package's local BGC alias:

```bash
python mamey_run.py emit-modeb-template --package runs/EXAMPLE/package --bgc BGC001 \
  --contract current50_v2 --gap-rescue-dir inputs/EXAMPLE-rescue \
  --out reviews/EXAMPLE-mode-b.md
```

`current50_v2` selects the profile that reads this evidence. Keep the card's full
**strain / full node-or-contig / region / BGC alias** from the source record.

## Check the saved inputs

The selected run needs `gap_rescue_receipt.json`, `gap_rescue.tsv` and
`gap_rescue_split_genes.tsv`. `gap_rescue_proteins.faa` can be in that run or its
parent. The reader uses a direct receipt first; otherwise it searches one child
level and requires exactly one matching focal identity.

An optional sibling `<run-folder>_ADJUDICATION.tsv` supplies reviewed gene rulings.
Add `--rescue-verdicts-tsv` when you have the separate pair-review table. That
table uses `strain`, `core identity`, `partner contig`, `partner region`,
`verdict`, `rule` and `source`. Review complete partner identities and the meaning
of each ruling: the reader does not enforce all those fields or a verdict vocabulary.

Gene support and pair rulings remain separate. A supported gene does not clear
an unresolved pair. A supplied source that is missing gives `RESCUE_EVIDENCE_HOLD`.

## Read the scaffold

Section 26 contains saved rescue tables; section 19 receives interpretation inputs.
Read the denominators for reference genes, annotated biosynthetic genes, search
matches, effective gene support and pair rulings separately. Split candidates
involving the focal locus are distinguished from candidates elsewhere.

`BOUND` describes the reader's identity/count/location/length/metric checks and
current file hashes. The reader hashes normalized saved protein strings; it does
not independently check the amino-acid alphabet or canonical assembly translations.
Split-piece geometry and sequences need their own source review. Keep the original
source receipts with these newly calculated hashes.

Write the interpretation from the reviewed evidence, then verify the saved card:

```bash
python mamey_run.py verify-modeb reviews/EXAMPLE-mode-b.md \
  --package runs/EXAMPLE/package --bgc BGC001 --contract current50_v2
```

The template is an authoring scaffold. Candidate links leave the contigs as
separate sequences. For interpretation that includes supported external
neighborhoods, use [expanded locus scope](MODEB_EXPANDED_LOCUS.md).

## Recover from a hold

A malformed examined receipt can hold discovery even for another locus; select
the exact reviewed leaf folder when appropriate. Missing `reference` or
`split_gene_check` fields can fail rendering after loading reported `BOUND`.
Keep the diagnostic and earlier output, obtain a corrected source receipt and
retry to a fresh destination. Do not fill scientific fields by inference.
Review local paths in receipts before sharing them.

<a id="reader-discovery-and-provenance-limits"></a>
