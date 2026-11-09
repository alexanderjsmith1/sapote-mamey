# DELIVERABLE: Metabolomics Readiness

**What this is.** A table that gives each BGC (biosynthetic gene cluster) a broad class-level plan for LC-MS, HRMS, UV and fractionation. One tool writes it. You review it by hand.

**Purpose.** Before an analyst runs an extract, give the expected mass range, ionization mode, UV handle, polarity, extraction route and dereplication target for each locus. Broad class only. No exact masses, formulas or structures.

The current task and [assistant governance](../ASSISTANT_GOVERNANCE.md) decide what you may do. The tool's source owns the values. The engine does not run the tool. Terms are in the [glossary](../GLOSSARY.md).

## Run it

You need a package from `python mamey_run.py run ...` (see the [first-run guide](../reader/01_FIRST_RUN.md)).

```bash
python tools/build_metabolomics_readiness.py --package-dir runs/EXAMPLE/package --out-dir out/EXAMPLE
```

It reads `manifest.json` in the package. The last lines it prints look like `EXAMPLE: N BGCs -> M class-mapped, K carry polar-compound caveat`, followed by the two paths.

Success is two files in the output folder:

- `<strain>_Metabolomics_Readiness.csv`
- `<strain>_Metabolomics_Readiness.xlsx`, with one sheet named `Metabolomics_Readiness`

Both outputs must be new: if either file already exists in `--out-dir`, the tool stops with `OUTPUT_REFUSED` before writing anything, so an older spreadsheet can never sit beside a new CSV. If the spreadsheet step fails, the tool prints `(xlsx skipped: ...)` where the path should be, and the exit code is still 0; the CSV is then the only output of this run. The tool does not touch the master workbook. A package with no BGCs gives a header-only CSV.

## Columns

`locator`, `strain`, `full_contig`, `region`, `identity_state`, `bgc_id`, `class`, `MW_range`, `ionization`, `UV_handle`, `polarity`, `extraction_route`, `dereplication_target`, `claim_ceiling`.

`strain`, `full_contig` and `region` are copied from one manifest record (`strain_id`, the BGC's `contig` or `node_id`, and `antismash_region` or a zero-padded `region_number`). A missing part is left blank and `identity_state` reads `IDENTITY_HOLD: missing ...`; otherwise it reads `COMPLETE`. `locator` is a display label only.

A locus whose class the tool cannot map gets `class-default: unavailable` in `MW_range` and blanks elsewhere. Nothing is invented.

## Where the class values come from

The values are in the `CLASS_DEFAULTS` table at the top of `tools/build_metabolomics_readiness.py`. Read that table for the current ranges. It maps these classes: NRPS, PKS, trans-AT PKS, RiPP, lanthipeptide, terpene, siderophore, glycopeptide, saccharide, beta-lactone, arylpolyene, nucleoside, phosphonate and enediyne.

The tool picks the class by scanning the product text and the closest-hit text, in a fixed order. A closest-hit label can therefore set the class. This is not an independent class call. If the class is unsupported or conflicts with the domain evidence, hold it.

The ranges are broad class priors. They are not measured properties and not an approved experimental plan for a locus. A person with chemistry training should review them.

## Polar-compound caveat

Standard C18 reversed-phase extraction can lose polar or zwitterionic products, such as nucleosides, siderophores, charged peptides and phosphonates. Rows carrying `CAVEAT` in `polarity` need this flag. For those, recommend an aqueous or ion-exchange first fractionation before HRMS dereplication.

## Review checklist

- [ ] Every row has a mass range, ionization, UV handle, polarity, extraction route and dereplication target, or says it is unavailable.
- [ ] No exact mass, formula or structure appears unless a named reference cluster with strong evidence supports it.
- [ ] Polar rows carry the C18 caveat.
- [ ] Bioassay pairing stays at extract level.
- [ ] Every locus is written as `strain / full contig / region / BGC alias`, from the `strain`, `full_contig`, `region` and `bgc_id` columns; rows with `IDENTITY_HOLD` are held.
- [ ] Open holds are listed.

## Example row shape

| locator | class | MW_range | polarity |
|---|---|---|---|
| `BGC001 (<full contig> · region001)` | `phosphonate` | from `CLASS_DEFAULTS` | polar with `CAVEAT` |

See also the [wet-lab matrix](DELIVERABLE_WetLabMatrix.md) for dereplication priority.
