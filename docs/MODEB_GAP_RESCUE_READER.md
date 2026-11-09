# Read saved gap-rescue evidence in a Mode B card

Use saved gap-rescue results to fill the evidence scaffold in a `current50_v2`
card. A **gap-rescue run** searches each antiSMASH region's missing reference genes elsewhere in the
assembly. Make one with `python mamey_run.py gap-rescue --strain EXAMPLE --input-zip inputs/EXAMPLE.zip --out <folder outside the bundle>`.
It is heavy, runs one genome at a time, and needs DIAMOND on your `PATH` plus MIBiG reference files.
Run `gap-rescue --help` for the rest. It writes one folder per region and a `SUMMARY.tsv` into `--out`.

You also need the matching package and the focal BGC. Terms are in the [glossary](GLOSSARY.md).

Run from the bundle directory, selecting the package's local BGC alias:

```bash
python mamey_run.py emit-modeb-template --package runs/EXAMPLE/package --bgc BGC001 \
  --contract current50_v2 --gap-rescue-dir inputs/EXAMPLE-rescue \
  --out reviews/EXAMPLE-mode-b.md
```

`--out` must name a file that does not exist yet. If the path already exists, the command exits 1,
prints `The file was not changed`, and leaves the existing file as it was. Choose a new name for each
emission.

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
an unresolved pair.

If a required source is missing or unreadable, the reader records a hold in the template instead of failing. Sections 19 and
26 of the emitted file begin with `RESCUE_EVIDENCE_HOLD:` and the reason. Search the file for that
word. It means no rescue count was established. It does not mean there is no rescue.

## Read the scaffold

Section 26 contains saved rescue tables; section 19 receives interpretation inputs.
Read the denominators for reference genes, annotated biosynthetic genes, search
matches, effective gene support and pair rulings separately. Split candidates
involving the focal locus are distinguished from candidates elsewhere.

In sections 19 and 26, the reader reports one of two states. `BOUND` means the identity, count,
location, length and metric checks passed and the current file hashes were recorded. A typical
section 19 line reads: "N of M reference genes in the focal region; K supported external
reference-gene assignment(s); ...". `RESCUE_EVIDENCE_HOLD` is the other state.

The reader hashes normalized saved protein strings. It does
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
Keep the diagnostic, the earlier output and the rescue folder as they are. Do not edit a saved
receipt or evidence file in place. To get a corrected receipt, run `gap-rescue` again into a new
`--out` folder. If a file can only be repaired by hand, copy the rescue folder to a new folder first,
record the original file's SHA-256, what you changed and why, and point `--gap-rescue-dir` at the copy.
Then run `emit-modeb-template` again into a new `--out` file. Check that sections 19 and 26 no longer start with `RESCUE_EVIDENCE_HOLD:`. Do not
fill scientific fields by inference.
Review local paths in receipts before sharing them.
