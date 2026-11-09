# Whole-genome chitin reference evaluation

`tools/chitin_reference_eval.py` reads the chitin-domain counts a finished package already holds and compares the strain against a table of reference genomes that you supply. It prints a receipt that names the strain's chitin-domain profile and how good its closest reference is. It is for people who already have a validated package (see [First run](reader/01_FIRST_RUN.md)).

## Rules

- The intended unit is the strain's whole genome, never a single BGC. Whole-genome scope is a claim that needs a bound source and a coverage review. The receipt's `source_scope_state` says how the counts were bound: `PACKAGE_MANIFEST_SCAN_RECORD_COVERAGE_UNREVIEWED` for `--package` (read from the manifest's scan record, coverage not checked), or `UNRESOLVED_SCOPE_COUNTS_NOT_SOURCE_BOUND` for `--cgad-json` (a supplied object with no bound scan). `zero_count_interpretation` repeats this for zero counts: with an unresolved scope, a zero is not tested absence.
- It is separate from triage, scoring and Mode B. The tool has no triage or score option and must not feed either one.
- The result is encoded domain capacity only. It is not enzyme activity, expression, chitin use, an antifungal phenotype, ecological adaptation, novelty or a cause for any BGC. Every receipt carries this sentence in its `claim_ceiling` field. Show it with any table, report or figure caption built from a receipt.

## What you need

1. A package. The chitin and glycan scan runs in every gold-mode pipeline. It counts five families: `GH18`, `GH19`, `AA10_LPMO`, `CBM_CHITIN` and `GlcNAc`. The counts are in the package's `manifest.json` at `source_scans.chitinase.counts`. No package? Pass `--cgad-json <file>` instead. The file holds a `counts` object with those five keys.
2. A reference registry: a tab-separated file you write. The tool never reads or copies the reference sequences. It identifies a reference only by the path and SHA-256 you declare.

The registry needs the columns `reference_id`, `taxon` (or `genus`), `source_path` and `source_sha256`. It may also have `ani_pct`, `aligned_fragment_fraction` and `chitin_domains_total`. ANI is average nucleotide identity, a genome-to-genome similarity percent. You compute it outside this tool, for example with `fastANI` (see [LLM_COMPANION_TOOL_PROTOCOL.md](LLM_COMPANION_TOOL_PROTOCOL.md)). Then paste the values in.

```text
reference_id	taxon	source_path	source_sha256	ani_pct	aligned_fragment_fraction
REF_1	Streptomyces	/refs/ref1.fna	<sha256>	96.1	0.80
REF_2	Streptomyces	/refs/ref2.fna	<sha256>	88.0	0.70
REF_3	Streptomyces	/refs/ref3.fna	<sha256>
```

A row with no `ani_pct` is typed `NOT_SCORED`. It is never dropped and never read as zero similarity. Taxon matching is exact and case-sensitive. Use `--taxon` to set the strain's taxon, and `--genus-alias` (repeatable) to add another name to match.

## Run it

```bash
python3 tools/chitin_reference_eval.py \
  --package ./runs/EXAMPLE/package --registry my_reference_registry.tsv
```

With no package:

```bash
python3 tools/chitin_reference_eval.py \
  --cgad-json cgad_counts.json --registry my_reference_registry.tsv \
  --strain-id EXAMPLE --taxon Streptomyces
```

`--format tsv` prints one TSV row instead of JSON. `--out-json` and `--out-tsv` also write files. Each must be a new path: an existing file, the two flags naming the same path, or a path that is an input (the `--cgad-json` file, the package's `manifest.json` or the package folder, or the registry) is refused with exit 1 before anything is read or written.

What you should see: a JSON receipt on stdout and exit code 0. Read these fields:

- `profile.architecture_state` and `profile.missing_families`;
- `reference_quality` and `top_reference`;
- `reference_panel`, one row per registry row, each with a `row_state`.

Trimmed example:

```text
"profile": {"counts": {"GH18": 3, "GH19": 0, "AA10_LPMO": 2, "CBM_CHITIN": 4, "GlcNAc": 5},
            "domains_total": 9, "architecture_state": "MULTI_ARM_CHITIN_CAPACITY", ...},
"reference_quality": "SPECIES_LEVEL_SIMILARITY_CANDIDATE_NOT_TAXONOMIC_CONFIRMATION",
"top_reference": {"reference_id": "REF_1", "ani_pct": 96.1, ...}
```

A refusal (bad input, unreadable package, malformed registry) goes to stderr with a non-zero exit. Nothing mixes into stdout. The receipt is printed before the optional files are written. If an output error follows, stdout can be full while a file is missing. Check the exit code and every file you asked for.

## Architecture states

`domains_total` adds the four core families. `GlcNAc` is context and is not in the total. "Endo" means `GH18` or `GH19`.

| State | Condition |
|---|---|
| `MULTI_ARM_CHITIN_CAPACITY` | endo, `CBM_CHITIN` and `AA10_LPMO` all present |
| `PARTIAL_COORDINATED_CHITIN_CAPACITY` | endo and one of `CBM_CHITIN` or `AA10_LPMO` |
| `CHITINASE_FAMILY_CAPACITY_WITHOUT_SUPPORTING_ARMS` | endo, and neither `CBM_CHITIN` nor `AA10_LPMO` |
| `NON_ENDOCHITINASE_CHITIN_CONTEXT` | no endo, core total above 2 |
| `MINIMAL_MEASURED_CHITIN_DOMAIN_CAPACITY` | no endo, core total 2 or less (above 0, or `GlcNAc` alone) |
| `ABSENT_NO_MEASURED_CHITIN_DOMAINS` | core total 0 and `GlcNAc` 0, with all five keys supplied |
| `CHITIN_SCAN_INCOMPLETE_NOT_ABSENCE` | no family count is positive and at least one of the five keys is missing |

A missing key counts as zero in the arithmetic but is listed in `missing_families`. With positive counts, a capacity state can appear together with missing families, so read both fields. "Absent" is not proof of absence unless the scan covered the whole genome.

## Reference-quality states

The tool takes the registry row with the highest `ani_pct`, so that row is `top_reference`.

| State | Condition |
|---|---|
| `NO_TAXON_MATCHED_REFERENCE_PANEL` | no registry row matches the taxon or its aliases |
| `TAXON_MATCHED_PANEL_BUT_NO_ANI_AT_MIN_FRACTION` | a panel exists but no row has `ani_pct` |
| `SPECIES_LEVEL_SIMILARITY_CANDIDATE_NOT_TAXONOMIC_CONFIRMATION` | top ANI 95 or above, aligned fraction 0.5 or above |
| `HIGHER_SIMILARITY_NONSPECIES_REFERENCE_CONTEXT` | top ANI 90 or above, aligned fraction 0.5 or above |
| `DISTANT_AVAILABLE_TAXON_MATCHED_REFERENCE_CONTEXT` | panel scored, below both |

A high ANI hit is a candidate. It is never a taxonomic confirmation on its own.

Row states are `RETURNED_ABOVE_MIN_ALIGNED_FRACTION` (aligned fraction 0.2 or above), `NO_OUTPUT_AT_MIN_ALIGNED_FRACTION` and `NOT_SCORED`.

## Known limits

- Package mode reads the manifest as it is, and `source_scope_state` never says the scope was verified. It does not check the seal, the scan coverage, or that the genome is complete. Confirm those before you read an "absent" or "measured" label.
- The tool refuses boolean, negative and non-whole-number counts. Whole-number floats and numeric strings are accepted. Unknown family keys are ignored.
- The tool does not check ANI or fraction values for range. Reject out-of-range values before you build the registry.
- Row state uses an aligned fraction of 0.2. The quality tiers use 0.5. `top_reference` is the highest ANI regardless of fraction. A high-ANI row below 0.5 can keep another qualifying row from setting a high tier. `DISTANT_...` can mean a low or missing fraction, not a distant genome. Keep the full panel and read the reason.
- The tool does not check source paths or hashes. Missing identity fields become `NR`. `verify_reference_hash(path, declared_sha256)` in `mamey/chitin_reference_eval.py` is a separate checker you can call. It returns `None` when it cannot check. The evaluator does not call it.
- The receipt does not hash its own inputs, code or output. Record those hashes yourself.
- The tool draws no report. It prints data only. It does not run `fastANI` or touch the network.

If a report that uses this receipt also mentions a BGC, write that BGC as `strain / full node-or-contig / region / BGC alias`. A chitin state assigns no cause to that BGC. The bioactivity example files in [the metadata contract](BIOACTIVITY_METADATA_CONTRACT.md) are shape fixtures, not measurements.
