# Make a quick per-BGC overview

`report-card` writes a Markdown overview of each biosynthetic gene cluster (BGC) in a package. It reads the package CSVs and leaves slots for your own interpretation. It is not a Mode B card. For a full card, follow the [card walkthrough](MODE_B_USER_WALKTHROUGH.md).

You need a package that passed `validate`. If you do not have one, start with the [first-run recipe](reader/01_FIRST_RUN.md). Terms are in the [glossary](GLOSSARY.md).

## 1. Generate the overview

Run this from the bundle root, with the same `python` you used for `doctor`:

```text
python mamey_run.py report-card --package runs/EXAMPLE/package --bgc BGC001 --out reviews/EXAMPLE-BGC001-card.md
```

- `--bgc` takes the `BGC_ID` value from the package's triage board (case does not matter). Leave it out to get every row.
- Leave out `--out` to print the Markdown to the screen. Parent folders of `--out` are created. An existing file is overwritten, so use a new name.

What you should see with `--out`:

```text
[report-card] EXAMPLE: 1 card(s) (1 with predicted polymer) -> reviews/EXAMPLE-BGC001-card.md
```

With a single `--bgc`, the card count must be 1. The command also exits 0 with `0 card(s)` when the alias is not found, so read that number. The count of cards with a predicted polymer can be lower than the card count. That is normal for clusters that are not NRPS or PKS.

If the rescue-evidence source cannot be read, the file opens with `RESCUE_PROVIDER_UNAVAILABLE`. That means the rescue evidence is unresolved, not that there is none.

## 2. Read the layers

Each card has four layers. The headings in the file are:

| Heading | What it holds |
|---|---|
| `L0 · Headline` | Predicted class, three heuristic badges and a suggested action. |
| `L1 · Predicted molecule` | Package-predicted backbone and SMILES, a calculated mass, and the boundary. |
| `L2 · Evidence (auto)` | Per-module substrate calls, the engine's capacity read, the KnownClusterBlast comparator and the over-merge flag. It ends with an `AUTHOR L2` comment for you to fill. |
| `L3 · Provenance & claim ceiling` | What the package supports and what it does not. It ends with an `AUTHOR L3` comment. |

Success means the file was written. It does not mean the author slots are filled or the content is checked.

## 3. Check where the modules came from

The L2 module line ends with a tag that says how modules were matched to this BGC.

- `gene-table region assignment`: modules were joined by the BGC's own genes, from the package file `<strain>_gene_by_gene_all_bgcs.csv`. This is the normal case. Two regions on one contig get their own modules.
- `some module mapping unresolved`: some modules could not be tied to a contig. Rows left out are not negative evidence.
- `single-region contig fallback`: the package has no gene table, so modules were joined by contig. This works only when the contig holds one region and its name contains `NODE_<N>`.
- `module mapping unresolved`: the package has no gene table and the contig holds several regions, or the contig name has no `NODE_<N>`. The card then lists no modules. That is not a biological no-call.

Check the module list against the region's gene roster before you rely on it.

## 4. Read the input rows

The command reads the package's `<strain>_4_triage_board.csv`, `<strain>_predicted_polymers.csv` and `<strain>_nrps_prediction.csv`. The strain name comes from the triage board file name, or from the package folder name if that file is absent. The engine version is the package's `manifest.json` `workflow_version`. If the manifest is absent, unreadable or invalid, or has no `workflow_version`, the card shows the version of the engine running the command instead, with the reason in brackets, for example `(running engine; package manifest.json absent)`. That is not necessarily the engine that built the package. Check the package's own run records before you cite a version.

The polymer is matched by contig and region number. If two rows share that key, the longest polymer is kept.

The command writes no hash or receipt. Record the package path, the input hashes and the output hash yourself (`shasum -a 256 <file>`).

## 5. Author within the evidence

- The novelty, activity and tractability badges are routing hints. They do not show chemical novelty, product identity, phenotype or feasibility.
- The report card reads `KCB_score`, a cumulative score, not a percent similarity. Record the score, reference and database release as reported; check the separate similarity percent and its state when available. A low score does not establish why a match is weak, that a cluster is new, or that the database lacks a relative. A KCB match is not cluster identity.
- Bioactivity priors describe a strain's extract, not one BGC.
- The mass comes from the supplied SMILES by RDKit (a chemistry library). If the region has no SMILES, the card says `Predicted mass: no SMILES for this region.` If the SMILES contains wildcards, cannot be parsed, or RDKit is missing, the card says `Predicted mass: pending —` and the reason. The mass describes that candidate structure. It does not show that the molecule was detected.
- Keep the full identity **strain / full node-or-contig / region / BGC alias** in anything you write from this card. The command does not check it for you.

## 6. Continue

Save the automatic file and keep your edited copy as a separate file. For a full card, choose a profile in the [profile guide](MODEB_PROFILE_MATRIX.md). `verify-modeb` offers `full48` (default) and `current50_v2`. For page layout, see the [region page layout](PER_BGC_PAGE_LAYOUT_SPEC.md).
