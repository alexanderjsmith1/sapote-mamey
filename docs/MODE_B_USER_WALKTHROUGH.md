# Write and check one Mode B card

**Mode B** is a written interpretation of one biosynthetic gene cluster (one
locus). A **card** is that write-up as one Markdown file. A **package** is the
folder that `run` produces for one strain. The tools build a card template and
check your writing. You write the sections.

You need a package that passed `validate`. If you do not have one, start with
the [first-run recipe](reader/01_FIRST_RUN.md). Keep the original ZIP.
The examples use `EXAMPLE`. For other terms, see the [glossary](GLOSSARY.md).

## Make a working copy

Work on a copy of the package, so the original stays untouched. Keep it outside
the bundle. The [BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md) uses the same
folder, so hits you ingest there reach your cards. Skip this if you already
made it:

```bash
mkdir -p $HOME/mamey-work/EXAMPLE
cp -R runs/EXAMPLE/package $HOME/mamey-work/EXAMPLE/package
```

Every command below uses `$HOME/mamey-work/EXAMPLE/package`. If a BLASTp load is pending, do it
first; `emit-modeb-template` refuses otherwise.

## 1. Pick the profile

A **profile** is the section layout a card must follow.

- **full48** is the default. It has 48 sections, with the gene-evidence table
  in section 4.
- **current50_v2** has 50 sections, with the evidence table last, in section 50.
  Use it when your task asks for GECCO results (a gene-cluster predictor), rescued
  contigs or literature sections. Add `--contract current50_v2` to both
  `emit-modeb-template` and `verify-modeb`.

The [profile guide](MODEB_PROFILE_MATRIX.md) lists every difference.

## 2. Pick the locus

Run this from the bundle root:

```bash
python mamey_run.py mode-b --package $HOME/mamey-work/EXAMPLE/package \
  --top-n 3 --outdir $HOME/mamey-work/EXAMPLE
```

`--top-n 3` covers ranks 1 through 3. The default is 10.

The last four lines are (the build line prints first; the count is your real lead count):

```text
  Mode B top-3 cards: $HOME/mamey-work/EXAMPLE/EXAMPLE_Mode_B_Top_Leads.md
  Mode B CSV: $HOME/mamey-work/EXAMPLE/EXAMPLE_Mode_B_Top_Leads.csv
  Mode B coverage receipt: $HOME/mamey-work/EXAMPLE/Mode_B_Coverage_Receipt.json
  Leads covered: 3
```

Exit code 0 means the files were written. Exit code 1 means the package is
unusable, for example no `manifest.json` or no single triage board; the reason
prints on stderr. `--strict-all` matters only when `--top-n` is at least the
number of clusters in the inventory. Then exit code 2 means fewer cards were
emitted than the inventory has clusters. With a smaller `--top-n`, such as 3,
it still exits 0. This command writes a table of leads and short scaffolds. It
does not write a finished card.

The per-gene lead table is a separate file that `run` already wrote into the
package: `$HOME/mamey-work/EXAMPLE/package/EXAMPLE_gene_by_gene_top_leads.csv`. It has one
row per gene in each of the top 10 clusters. Open it, or the
`EXAMPLE_Mode_B_Top_Leads.csv` file above, and choose one cluster.

Then open `$HOME/mamey-work/EXAMPLE/package/EXAMPLE_2_inventory.csv`. Find the chosen row by
its `BGC_ID` column. Copy its complete identity:

**strain / full node-or-contig / region / BGC alias**

Take the contig from the `Contig` column. Do not rebuild the identity from a
shortened label. If fields conflict, resolve that before writing.

## 3. Emit the template

```bash
python mamey_run.py emit-modeb-template --package $HOME/mamey-work/EXAMPLE/package \
  --bgc 'BGC_ID_FROM_INVENTORY' --out $HOME/mamey-work/EXAMPLE/template.md
```

Replace `BGC_ID_FROM_INVENTORY` with the `BGC_ID` value you chose.

| Exit code | Meaning |
|---|---|
| 0 | Template written. The command prints `template -> $HOME/mamey-work/EXAMPLE/template.md`. Without `--out` it prints the template. |
| 1 | The package folder or a required file is missing, the package fails a version check, a batch cannot start, or the `--out` file already exists or its folder does not. An existing `--out` file is left unchanged. |
| 2 | Wrong arguments. You need exactly one of `--bgc` or `--batch`. |
| 3 | The BLASTp gate blocked emission, or a `--batch` run with `--scope leads` or `--fail-on-empty` produced no template. Any other empty batch exits 0 with `emitted: 0`. |

Check that the template header names the inventory's full `Contig` value. If it
does not, replace it before you ingest the card. Otherwise ingest reports a
locus mismatch.

**BLASTp gate.** Emission refuses (exit 3, `BLASTP GATE — BLOCKED`) when BLASTp
results sit on disk but are not ingested. Ingest them first; see the
[BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md) and the
[authoring preflight](MODE_B_AUTHORING_PREFLIGHT.md). `--blastp-waiver 'REASON'`
overrides the block and logs the reason. Use it only on purpose.

**Optional inputs.** Pass these only when you have them for this task:

- `--cohort-dir`: other packages, to fill the prevalence section.
- `--reference-dir`: reference packages, to fill the genus comparison.
- `--strain-metadata`: a TSV of genus, host and exclusions, used as deposited.
- `--bigscape-regions-dir`: region GBK files, bound by exact strain, contig and region.
- `--gap-rescue-dir` and the `--rescue-*` options: see the [gap-rescue guide](MODEB_GAP_RESCUE_READER.md).

For many cards at once, use `--batch` with `--scope` and `--top-n`. Templates
go to `<package>/mode_b_templates/`, with an `_INDEX.md`.

## 4. Write the card

Copy the template to `$HOME/mamey-work/EXAMPLE/authored-card.md` and keep its section
titles exactly. Under each title, state the finding, its source, your inference
and any alternative that would change it. Use the full gene roster. Keep nr,
ClusteredNR and Swiss-Prot matches separate. Replace every prompt with
evidence-based text, or with the profile's required statement that a result is
missing or not applicable. Keep the section-accountability rows and all 14
supporting-stream entries.

Do not edit line 1 of a current50_v2 template. It is an HTML comment that
starts `<!-- MODE B |` and carries the identity and contract.

To see which evidence you have for each BGC before writing, run the optional
[availability inventory](MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md). For what each
section must contain, see the [current50 contract](MODEB_CURRENT50_V2_CONTRACT.md)
and the [historical interpretive rubric](MODEB_INTERPRETIVE_FLOOR_v97146.md).
That rubric's structure examples go past class level, so do not copy them. The
[full48 format example](reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md)
shows layout. Read its [documented limits](reference/modeb_exemplars/README.md)
before you reuse its evidence treatment. Tie compound identity and measured
activity to sources that establish them.

## 5. Verify the saved card

**Draft check.** `--no-strict-depth` turns thin-content findings into
warnings, but it does not excuse empty sections. An untouched template still
exits 1 with `EMPTY_OPTIONAL_SECTION` errors, for example for sections 31, 37,
39, 42 and 45. For a draft to pass, every optional section (31 to 48) that has a
heading needs body text. Write the section, or delete its heading while you
have not authored it. Expect FAIL until then:

```bash
python mamey_run.py verify-modeb $HOME/mamey-work/EXAMPLE/authored-card.md \
  --package $HOME/mamey-work/EXAMPLE/package --bgc 'BGC_ID_FROM_INVENTORY' \
  --no-strict-depth --report-json $HOME/mamey-work/EXAMPLE/verification-01.json
```

**Finished check (full48).** When the card is done, add this line as its own
plain line directly under the title. Do not put it in a code block or a comment;
the checker ignores those.

```text
**Document state:** FINISHED_FULL48_CURRENT_EVIDENCE
```

The line turns on the strict publication checks. A fresh template will fail
them, so leave the line out while you draft. For current50_v2, the emitted
line 1 already declares the profile, so you add nothing.

What you should see on success:

```text
[verify-modeb] authored-card.md: OK — §1–§48 structure + depth (2 warning(s))
        WARN: <CODE>: <message>
```

On failure the line reads `FAIL — N error(s)`, followed by one `ERROR:` line per
finding.

| Exit code | Meaning |
|---|---|
| 0 | No blocking findings. Read the warnings anyway. |
| 1 | At least one error, or the card file was not found. |
| 2 | The `--report-json` file could not be written. |

Notes:

- Use the same profile, package and BGC you used for emission.
- Without `--package`, the roster check cannot bind, and a finished full48 card
  fails with `BLASTP_MATRIX_ROSTER_UNBOUND`.
- `--summary-only` prints counts by finding code instead of every message.
- `--report-json` replaces an existing file, so give each retry a new name.
- The `--semantic-*`, `--substantive-quality-v2`, `--selection-process-v9`,
  `--figure-spec-v10`, `--inventory-reconciliation-v8` and
  `--reconciliation-specificity-v11` options are extra opt-in gates. Skip them
  unless your task asks for them. Each one requires the finished-card line.
- For an [expanded locus](MODEB_EXPANDED_LOCUS.md), add `--contract current50_v2
  --require-expanded-locus`. Add repeated `--rescue-tsv` files only for the
  sources chosen for that task; the [gap-rescue guide](MODEB_GAP_RESCUE_READER.md)
  explains them.

## 6. Save and review

Keep these together in `$HOME/mamey-work/EXAMPLE/`:

- `authored-card.md` and `template.md`;
- `verification-01.json` and the exact command you ran;
- the source files the card cites, with their hashes.

Record a hash with:

```bash
shasum -a 256 path/to/source-file
```

The report does not record input hashes or options, so save them yourself.
Re-verify after any change to the text or its sources. Have a person check the
interpretation against those sources.

To record the card in the package, follow
[from package to a recorded Mode B card](INGEST_AND_PRINCIPLES_WHITEPAPER.md#from-package-to-a-recorded-mode-b-card).
Run `verify-modeb` first, because ingest does not repeat the depth and
literature checks. Ingest refuses a card whose declared contract conflicts. Keep
earlier versions and the verification report.
