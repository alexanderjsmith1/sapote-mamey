# Round 2: a public-strain walkthrough across the 80 MB boundary

This walkthrough uses v9.7.428 with the Round 1 instruction and 80 MB candidate patches. No new release was cut. Run receipts and input hashes accompany the review package. Tests used the existing Python 3.12.14 audit environment; no fresh dependency installation, online homology search, or publication was performed.

## Choose inputs for a reason

Round 1 exercised a complete Streptomyces fradiae chromosome. Round 2 uses two fragmented Nocardia assemblies and a recovery path. Identity was checked against GenBank DEFINITION/ACCESSION fields inside the supplied archives. The directory name alone was not treated as verification of type status. Both archives report antiSMASH 8.0.4. Isolation habitat was not supplied for these runs.

| Input archive | Uncompressed main JSON | Reason selected |
|---|---:|---|
| `Nocardia thailandica NBRC 100428 NZ_BAGK00000000.1.zip` | 77,703,211 bytes | Below 80 MB; a different genus and fragmented assembly |
| `Nocardia_brevicatena_NBRC-12119_NZ_BAFU00000000.zip` | 80,592,682 bytes | Just above 80 MB; demonstrate a hold and bounded rerun |

All 18 archives were inventoried, not all run. Each contains one JSON file; 14 exceed 80,000,000 bytes. Compressed ZIP size is not the quantity checked by the full-mode guard.

## Run the example

From the candidate bundle root, activate the prepared Python 3.12+ environment. Replace `path/to/Type_Strains` with your local folder. Quote paths containing spaces. Inspect before execution:

```bash
python mamey_run.py inspect "path/to/Type_Strains/Nocardia thailandica NBRC 100428 NZ_BAGK00000000.1.zip"
python mamey_run.py run --strain NT_NBRC100428 \
  --input-zip "path/to/Type_Strains/Nocardia thailandica NBRC 100428 NZ_BAGK00000000.1.zip" \
  --taxonomy 'Nocardia thailandica' --source 'not supplied' \
  --mode gold --json-evidence full --brief none --locus-maps off \
  --release PRIVATE --outdir analysis/round2/thailandica_full
python mamey_run.py validate analysis/round2/thailandica_full/NT_NBRC100428/package
```

For the second input, inspect its ZIP and run with strain `NB_NBRC12119`, taxonomy `Nocardia brevicatena`, the matching ZIP, and a distinct `analysis/round2/brevicatena_full` output root. Keep other settings the same. The full-mode size hold is an expected result of this candidate's cap.

Retain that attempt. Repeat the second run with `--json-evidence bounded` and a new output root, `analysis/round2/brevicatena_bounded`. Do not add `--capped-session`: it overrides bounded to off.

```bash
python mamey_run.py validate analysis/round2/brevicatena_bounded/NB_NBRC12119/package
python mamey_run.py explain analysis/round2/brevicatena_bounded/NB_NBRC12119/package
python mamey_run.py list-bgcs analysis/round2/brevicatena_bounded/NB_NBRC12119/package
```

These command shapes were exercised locally; exact absolute paths and arguments are in the execution receipts. The output labels are local selectors, not accession numbers. PRIVATE is the selected artifact tag, not an assertion about source genome availability.

## Read the outcomes

| Run | Seconds | Peak RAM, decimal GB | Main JSON outcome |
|---|---:|---:|---|
| thailandica_full | 43.102 | 4.11 | `UNKNOWN` |
| brevicatena_full | 28.290 | 1.70 | `PARSE_HELD` |
| brevicatena_bounded | 29.825 | 1.43 | `TRUNCATED` |

All three direct runs and all three explicit validators returned exit 0. Explain and list-bgcs also returned exit 0 for the bounded package. All pipeline manifests still say `MAMEY_COMPLETE_WITH_ISSUES`. A validator's completion does not erase those issues or complete Sapote judgment.

The thailandica full parse was admitted, but visibility remains `REPORTED_NOT_COMPLETENESS_VALIDATED`; UNKNOWN is not an exhaustive parse certificate. The brevicatena full run reports `MAIN_JSON_PARSE_HELD`. Its bounded rerun reports `MAIN_JSON_WALKER_TRUNCATED`. Recovery made some main-JSON evidence available within the bounded policy; it did not establish complete evidence.

## Read the biology conservatively

Thailandica produced 51 region records: 10 interior, 26 edge and 15 full-contig. Its assembly manifest reports 312 contigs and N50 47,211 bp. Brevicatena produced 55 region records: 20 interior, 23 edge and 12 full-contig; 248 contigs and N50 102,039 bp. Both are classified FRAGMENTED by the assembly-contiguity fields. The separate boundary-derived labels VERY_POOR and POOR are not the same measurement.

The corrected counts (26.75 and 34.5) are pipeline-derived values, not observed numbers of distinct products. Fragmentation and over-merge candidates both require review. A whole-region count cannot be equated with the number of independent pathways or compounds.

A source-bound label returned by list-bgcs is `NB_NBRC12119 / NZ_BAFU01000246.1 / region001 / BGC054`. Use the entire identity when discussing that record. A listed PKS class is annotation evidence, not identification of a produced compound.

## What remains unfinished

Briefs and locus maps were explicitly deferred. No Mode B card, external protein search, assay interpretation, comparative tree or master-workbook update was completed. Generated figures were not visually reviewed in Round 2, and biological conclusions were not independently validated. This exercise checks workflow usability and recorded evidence states; it is not a benchmark across machines or a scientific acceptance test.

Before deeper interpretation, select the records of interest, inspect boundary and linkage evidence, and decide which missing channels matter to the question. Keep hashes, command receipts, manifests, issue logs and sealed result ZIPs together.
