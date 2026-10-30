# Write and check one Mode B card

Turn one locus's evidence into a saved interpretation with a verification report.
You need a validated working package, its gene evidence and the sources used to
write the card. Keep the original package ZIP. The examples use `EXAMPLE`.

## Choose the locus and profile

Use the default **full48** profile unless your task calls for **current50_v2**.
Full48 has 48 sections and its gene-evidence table in section 4. Current50 v2 has
50 sections, with the evidence table last in section 50. For that profile, add
`--contract current50_v2` to both emission and verification. See the
[profile guide](MODEB_PROFILE_MATRIX.md) for the exact differences.

If you need a lead to start with, run this from the program folder:

```bash
python mamey_run.py mode-b --package runs/EXAMPLE/package \
  --top-n 1 --outdir reviews/EXAMPLE
```

`--top-n 1` prepares one lead; a value of 3 prepares ranks 1 through 3.
`--outdir` puts the writing inputs in your review folder. This command can also
refresh package checksums, which is why you should use a working package.

Read the lead table, then copy the selected row's complete identity from the
package inventory: **strain / full node-or-contig / region / BGC alias**.
Use that inventory identity rather than reconstructing it from a shortened
summary label. Resolve conflicting fields before writing about that locus.

## Emit the template

Replace `<alias>` with the selected inventory row's `BGC_ID`:

```bash
python mamey_run.py emit-modeb-template --package runs/EXAMPLE/package \
  --bgc '<alias>' --out reviews/EXAMPLE/template.md
```

The alias selects a row within this package; keep all four identity fields in
the card and your source notes. The emitted titles define the sections to write.
If emission reports saved but un-ingested BLASTp, follow
[preflight](MODE_B_AUTHORING_PREFLIGHT.md) to resolve that state first.

Add `--cohort-dir`, `--reference-dir`, `--strain-metadata` or
`--bigscape-regions-dir` only when you have those inputs for this task. Record the selected profile's missing-evidence state and reason. For batch `modeb-round`, the separate
`--from-precompute` route currently stops with
`COHORT_PREFILL_SOURCE_BINDING_UNAVAILABLE`; ordinary `--cohort-dir` is a different input.

## Write the card

Save your writing as `reviews/EXAMPLE/authored-card.md`, keeping the template.
Under each exact emitted title, explain the finding, its source, the inference
and any alternative that changes your interpretation. Use the full gene roster
and distinguish nr, ClusteredNR and Swiss-Prot matches.

Replace every prompt with evidence-based text or the selected profile's required
explanation of a missing or inapplicable result. Keep the section-accountability
rows and all 14 supporting-stream entries. Reconcile earlier content when revising
an existing card. The [writing contract](MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md)
and [interpretive guide](MODEB_INTERPRETIVE_FLOOR_v97146.md) explain these requirements.

The [full48 format example](reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md)
can help with layout; read its [documented limits](reference/modeb_exemplars/README.md)
before reusing its treatment of evidence. Keep compound identity and measured
activity tied to sources that actually establish them.

## Verify the saved writing

For a finished full48 check, include this declaration in the authored file:

```text
**Document state:** FINISHED_FULL48_CURRENT_EVIDENCE
```

That declaration activates the full48 publication checks. For current50 v2,
keep its emitted identity/contract/profile header as the first line instead.
Then check the actual saved card:

```bash
python mamey_run.py verify-modeb reviews/EXAMPLE/authored-card.md \
  --package runs/EXAMPLE/package --bgc '<alias>' \
  --report-json reviews/EXAMPLE/verification-01.json
```

`--report-json` saves the findings beside the card. Read warnings, coverage and
errors as well as the exit code. Use a new receipt filename on retry because
an existing one is replaced. Keep full findings visible while fixing problems.
Use the same profile, package and alias that you used for emission.

For an explicitly requested [expanded locus](MODEB_EXPANDED_LOCUS.md), add
`--require-expanded-locus` to current50 v2 verification. Add repeated `--rescue-tsv`
inputs only for the sources selected for that expanded-locus task; the
[gap-rescue guide](MODEB_GAP_RESCUE_READER.md) explains their role.

## Save and review

Keep the authored card, template, source paths/hashes, selected contract, exact
verification command and JSON report together. The report does not record all
input hashes or options, so save those alongside it. Reverify after changing
the text or sources, and have the interpretation checked against those sources.

If the task also calls for saving the card into a package, follow
[ingest-receipts](INGEST_AND_PRINCIPLES_WHITEPAPER.md#from-package-to-a-recorded-mode-b-card)
with a writable package. Ingest checks the card's declared contract, structure
and evidence table; verify the authored card first because ingest does not repeat
the depth and literature checks. A conflicting contract is refused. Keep earlier
versions and the verification report after saving the new card.

<a id="1-choose-the-profile"></a>
<a id="2-prepare-the-evidence-and-review-folder"></a>
<a id="3-emit-and-author-the-selected-template"></a>
<a id="4-verify-the-authored-file"></a>
<a id="5-save-the-card-and-its-review-evidence"></a>
<a id="6-review-the-evidence-and-decide-what-is-ready"></a>
