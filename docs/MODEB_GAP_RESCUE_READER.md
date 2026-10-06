# Existing gap-rescue inputs for current50_v2

The optional `--gap-rescue-dir` points to an existing run folder or its strain parent.
The reader selects one receipt by the complete strain / contig / region / BGC identity,
then pre-fills §26 and provides deterministic interpretation inputs in §19. It runs
no alignment, online search, assembly join or scoring change. Other profiles retain
their current section behavior.

```bash
python mamey_run.py emit-modeb-template --package <copy> --bgc <BGC> \
  --contract current50_v2 --gap-rescue-dir <existing-run-or-strain-parent> \
  --rescue-verdicts-tsv <current-pair-review.tsv> --out <template.md>
```

Required saved files are `gap_rescue_receipt.json`, `gap_rescue.tsv`,
`gap_rescue_split_genes.tsv`, and `gap_rescue_proteins.faa` (in the run folder
or its parent). The optional sibling `<run-folder>_ADJUDICATION.tsv` overrides
partner rulings by reference-gene name plus candidate locus. Search status and
original partner ruling remain visible beside the effective adjudicated ruling.

The optional pair-review TSV uses the existing slide-source schema: `strain`,
`core identity`, `partner contig`, `partner region`, `verdict`, `rule`, `source`.
Exact focal identity selects rows. Gene-level SUPPORTED matches do not override
pair-level UNRESOLVED or rejected rulings. A missing explicitly supplied source
produces RESCUE_EVIDENCE_HOLD, never zero rescue or a measured negative.

The reader reconciles receipt/table counts and unique reference rows, validates
matched protein lengths against the saved FASTA, and records normalized AA
SHA-256 (remove whitespace, uppercase, remove terminal stop symbols). These hashes
bind saved query sequences; independent canonical-assembly translation matching
is a separate scientific review. Source files also receive byte SHA-256 receipts.

Denominators distinguish all reference genes, reference-annotated biosynthetic
genes, external search matches, effective gene support and pair-level rulings.
CLEAR split candidates involving the focal identity are separated from CLEAR
splits found elsewhere in the genome. Split tables retain weaker and rejected
calls. Homology, gene support, pair support, physical continuity and product
characterization remain separate evidence states. Shared KCB/reference evidence
does not count as independent confirmation. The reader makes no claim of a
complete pathway, exact product, production or antibacterial/antifungal activity.

This output is an authoring scaffold. Authors integrate the reviewed result into
the boundary, biosynthetic, accessory, final-judgement, GECCO, RG-GMCI and §50
gene evidence sections before verifying the saved authored card. A template is
not a finished card. The approved current50_v2 requirements and headings are
unchanged. Run the existing `verify-modeb --contract current50_v2` after authoring.
