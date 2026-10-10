# Existing gap-rescue inputs for current50_v2

The optional `--gap-rescue-dir` points to an existing run folder or its strain parent.
The reader selects one receipt by the complete strain / contig / region / BGC identity,
then pre-fills §26 and provides deterministic interpretation inputs in §19. It runs
no alignment, online search, assembly join or scoring change. Other profiles retain
their current section behavior.

```bash
python mamey_run.py emit-modeb-template --package <selected-existing-package> --bgc <BGC> \
  --contract current50_v2 --gap-rescue-dir <existing-run-or-strain-parent> \
  --rescue-verdicts-tsv <current-pair-review.tsv> --out <template.md>
```

Required saved files are `gap_rescue_receipt.json`, `gap_rescue.tsv`,
`gap_rescue_split_genes.tsv` in the selected run folder, plus `gap_rescue_proteins.faa`
in that folder or its parent. The optional sibling `<run-folder>_ADJUDICATION.tsv` overrides
partner rulings by reference-gene name plus candidate locus. Search status and
original partner ruling remain visible beside the effective adjudicated ruling.

The optional pair-review TSV uses the existing slide-source schema: `strain`,
`core identity`, `partner contig`, `partner region`, `verdict`, `rule`, `source`.
Exact focal identity selects rows. Matching rows must have a strain, partner contig and nonblank verdict; a supplied partner-region value is checked for agreement of its first two identity components. The reader does not enforce a complete four-part partner identity, a pair-verdict vocabulary, or nonblank `rule`/`source` values. Review those fields against the governed pair evidence before interpreting the rendered table. No exact focal row in a supplied table means no matched ruling, not rejection or acceptance. Gene-level SUPPORTED matches do not override pair-level UNRESOLVED or rejected rulings. A missing explicitly supplied source
produces RESCUE_EVIDENCE_HOLD, never zero rescue or a measured negative.

The reader reconciles receipt/table status counts and unique reference-gene rows. For ordinary matched gene rows, it checks a nonempty saved FASTA string, the declared length and finite identity/coverage percentages in [0,100], then hashes the normalized saved string (remove whitespace, uppercase, remove terminal stop symbols). It does not validate the amino-acid alphabet or independently bind those strings to canonical-assembly translations. Unmatched rows do not receive a protein hash. The hash is a saved-string binding, not proof of a valid protein or gene assignment.

Split rows are checked for required location/call columns and the allowed split-call vocabulary; a receipt `split_genes` field, when present, is compared by row count. Their piece sequences, geometry, metrics and complete identities are not independently reconciled by this reader. External ordinary-match locations are required to be nonblank and differ from the focal identity, but are not validated as complete canonical four-part identities. Preserve and review `strain / full node-or-contig / region / BGC alias` for each interpreted external locus. Source files also receive byte SHA-256 receipts; those receipts do not extend the validation scope.

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

## Reader discovery and provenance limits

`mamey/modeb_gap_rescue.py` uses the direct leaf receipt when present; otherwise it examines one level
of child receipts and requires exactly one matching core identity. This is not arbitrary recursive
workspace discovery. A malformed examined receipt can produce HOLD even when it is for another locus;
select the exact leaf when that is the governed source. Tables/receipt are read from the selected leaf;
only the saved protein FASTA has the documented parent fallback. The conventional adjudication file
is in the leaf’s parent unless an explicit gene-adjudication path is selected.

BOUND means internal identity/count/location/length/metric consistency and current byte receipts.
The reader does not compare these bytes against a previously sealed source-hash register, reopen raw
alignment/job outputs or prove canonical assembly translation. An internally consistent edited run can
receive new hashes; retain the original governed source receipt separately. An absent pair-review table
is not a rejected pair ruling, and gene-level support never supplies the missing independent pair or
physical-continuity evidence. A reader HOLD is visible scaffolding, not a measured negative or successful finished-card admission. Most reader exceptions become a HOLD result, but BOUND is not a guarantee that rendering can finish: `reference` and `split_gene_check` are read later by the renderer without being required during loading. An otherwise internally reconciled receipt missing either field can fail template generation rather than emit the usual rescue HOLD text. Preserve the saved source, captured diagnostic and any existing output; obtain a corrected, source-bound receipt from its owner and choose a fresh candidate output before retrying. Do not fill missing scientific fields by inference or treat an older template as the new invocation's output. Printed/emitted source receipts include resolved local paths; they are not an
automatically sanitized distribution artifact. No source package/run copy is required for inspection.
