# RiPPER native discovery: CLI and Methods

For maintainers of the optional RiPPER adapter. Skip this page unless you run RiPPER on a named strain. Core runs (`mamey_run.py`) never need it. For what the adapter is, read [RIPPER_OPTIONAL_ADAPTER.md](RIPPER_OPTIONAL_ADAPTER.md).

RiPPER searches near selected enzymes for short ribosomal peptide (RiPP) precursor candidates. A candidate is a lead, not a product. This page shows the commands. The setup is in [RIPPER_NATIVE_DISCOVERY.md](RIPPER_NATIVE_DISCOVERY.md). The run lifecycle is in [RIPPER_OPERATIONAL_LIFECYCLE.md](RIPPER_OPERATIONAL_LIFECYCLE.md).

Terms used here:
- Terminal: the JSON file that records how a run ended. No terminal means the run did not complete.
- Raw discovery: `RAW_DISCOVERY.json`, the candidate rows the run kept. It has no annotation and no coordinates.
- Control result: an extra receipt that older terminals need. New terminals do not.

Set absolute paths first. Use the Python from your admitted environment. Every output folder must be new and outside the bundle. The one exception is a reviewed native run with `--resume-preflight`: it reuses the run root that its own earlier preflight reserved, and only when that folder is pristine and its source, files, profile, root and review request still match (see [native discovery](RIPPER_NATIVE_DISCOVERY.md)). No other existing folder is accepted.

```sh
PYTHON=/absolute/path/to/python
ADAPTER=/absolute/path/to/bundle/tools/ripper_adapter.py
```

`python tools/ripper_adapter.py <subcommand> --help` lists the options of each subcommand.

## Prepare and run a new native discovery

Do these in order. Nothing launches until step 5.

1. Set up the runtime. Follow [RIPPER_NATIVE_DISCOVERY.md](RIPPER_NATIVE_DISCOVERY.md#prepare-an-explicit-local-runtime-before-native-preflight).
2. Bind the adapted source. This hashes four files and checks that base plus patch gives the adapted source exactly:

   ```sh
   "$PYTHON" -B "$ADAPTER" adapted-profile \
     --owner-receipt "$OWNER_RECEIPT" --base-source "$ORIGINAL_SOURCE" \
     --source-patch "$CUMULATIVE_PATCH" --adapted-source "$ADAPTED_SOURCE" \
     --out "$FRESH_PROFILE_DIR"
   ```

   It writes `ADAPTED_SOURCE_PROFILE.json` in the output folder.
3. Write the lifecycle spec. The layout and an example are in [RIPPER_OPERATIONAL_LIFECYCLE.md](RIPPER_OPERATIONAL_LIFECYCLE.md#lifecycle-spec-and-invocation). Use mode `adapted_local05`.
4. Run preflight. This launches nothing:

   ```sh
   "$PYTHON" -B "$ADAPTER" lifecycle \
     --spec "$SPEC" --adapted-profile "$FRESH_PROFILE_DIR/ADAPTED_SOURCE_PROFILE.json" \
     --run-root "$FRESH_RUN_ROOT" \
     --file "archived_base=$ORIGINAL_SOURCE" \
     --file "source_patch=$CUMULATIVE_PATCH" \
     --file "upstream_source=$ADAPTED_SOURCE" \
     --file "adaptation_receipt=$OWNER_RECEIPT" \
     --file "source_closure=$SOURCE_HANDOFF" \
     --file "source_discovery_contract=$DISCOVERY_CONTRACT"
   ```

   Repeat `--file ROLE=PATH` for every other role: inputs, executables, Perl modules, runtime receipt. The full list is in [RIPPER_NATIVE_DISCOVERY.md](RIPPER_NATIVE_DISCOVERY.md#source-runtime-and-input-admission). A missing role gives status `HOLD` and names what is missing.
   Success looks like a `NATIVE_REVIEW_REQUEST.json` in the run root. It is the exact request a reviewer approves.
5. Review the request, write the admission file ([format](RIPPER_NATIVE_DISCOVERY.md#review-and-admission)), and rerun step 4 with `--execute-native --native-admission "$ADMISSION" --resume-preflight`. Use the same spec, profile, files and run root. `--resume-preflight` is for a preflight that already reserved the run root.

An admission covers one run. Do not reuse it for a retry.

Exit codes: `0` for a finished command, `2` for a refusal, failure, `AMBIGUOUS`, or `HOLD` or `UNAVAILABLE` on an execute run, `130` for an interrupt.

## Inspect a finished native result

You need the output folder of an earlier `lifecycle --execute-native` run. Its canonical terminal depends on the route: `EXECUTION_TERMINAL.json` when the run resumed a reserved preflight (`--resume-preflight`), or `TERMINAL.json` when it ran directly on a fresh root. `RAW_DISCOVERY.json` is written only when native discovery produced raw output. Open the folder and read the terminal's status before you assume raw output exists. The examples below use the resumed route; replace the terminal name for a direct run.

```sh
"$PYTHON" -B "$ADAPTER" native-result \
  --terminal "$RUN_ROOT/EXECUTION_TERMINAL.json" \
  --raw "$RUN_ROOT/RAW_DISCOVERY.json" \
  --out "$FRESH_INSPECTION_OUT"
```

Add `--control-result "$CONTROL_RESULT"` only for a terminal written by older code. The command reads only the files you name. It checks that terminal and raw agree. It does not prove who ran the process, so keep the original receipts.

Success: exit 0 and a `NATIVE_RESULT.json`. A synthetic test record gives output like this:

```json
{
  "terminal_status": "SUCCESS_UNBOUND",
  "raw_candidate_count": 78,
  "lexical_channel_counts": {"main": 3, "distant": 75},
  "hmm_annotation": "NOT_RUN_SEPARATE_STAGE",
  "coordinate_status": "ABSENT_PRODUCER_MAPPING",
  "candidate_membership": "UNVERIFIED",
  "canonical_import": "NOT_ADMITTED",
  "biological_absence_inferred": false
}
```

The counts belong to that test record. Yours will differ. The `main` and `distant` labels come from the source's serial numbers. Distant rows are not HMM-supported predictions. Distinct IDs that share a sequence stay distinct rows.

To inspect a failed, interrupted or held run, leave out `--raw`. The output keeps the terminal state with a null candidate count, and the exit code is 2. A raw file next to an unadmitted terminal is refused. For an admitted run, these are refused: missing raw bytes, mismatched hashes or counts, changed qualifiers. The raw table must have exactly nine columns.

## Read the status

[RIPPER_NATIVE_DISCOVERY.md](RIPPER_NATIVE_DISCOVERY.md#statuses) has the one status table. Two rules apply everywhere.
- `SUCCESS_UNBOUND` means raw candidates exist in the declared scope. It does not mean annotated, placed on the genome, or validated.
- A `NO_HIT` or `NO_RETAINED_CANDIDATES` result is never evidence that the strain lacks RiPPs.

Nine-column raw output does not meet the eleven-column annotated import. The `import` subcommand needs a separately annotated table with its own receipt. Do not turn raw native JSON into an operator receipt to get around this.

## Evaluate native coordinate reconstruction

Use `native-coordinates` after a native run that kept candidates. It checks whether each candidate's sequence matches a window of the source GenBank record. It consumes a `ripper-native-coordinate-reconstruction/1` packet plus the files the packet names, each given as `--file ROLE=PATH`.

No bundled tool writes the packet; you author it as a JSON file. It must carry `schema`, `candidate_count` (equal to the run's candidate count), `rows` (one per candidate), `source_stage`, and a `bindings` object with one entry for each of the 18 roles below, each giving `path`, `bytes` and `sha256`. It also carries fixed qualifier fields that state what the run is and is not: `status` is `EXACT_RETAINED_ARTIFACT_RECONSTRUCTION_ONLY`, `candidate_membership` is `UNVERIFIED`, `hmm_annotation` is `NOT_RUN`, `biology` is `UNASSESSED`, `instrumented_producer_sidecar` is `false`, and the origin fields are `mapping_origin` `derived_from_retained_native_artifacts`, `native_evidence_kind` `local_adapter_observed_native`, `upstream_execution` `EXECUTED_NATIVE_LOCAL_ADAPTER_OBSERVED`, `original_raw_coordinate_provenance` `ABSENT_PRODUCER_MAPPING` and `producer_authentication` `CONTENT_BINDINGS_ONLY_NOT_AUTHENTICATED_PRODUCER`. The command refuses a packet with any other value, so it cannot be used to promote a claim.

```sh
"$PYTHON" -B "$ADAPTER" native-coordinates \
  --packet "$COORD_PACKET" --out "$FRESH_COORD_OUT" \
  --file "raw=$RUN_ROOT/RAW_DISCOVERY.json" \
  --file "terminal=$RUN_ROOT/EXECUTION_TERMINAL.json" \
  --file "faa=$FAA" --file "score=$SCORE" ...
```

Repeat `--file` for all 18 roles, with no extras: `raw`, `terminal`, `faa`, `score`, `window`, `genbank`, `query`, `stage`, `provenance`, `source`, `config`, `reconstruction`, `profile`, `queries`, `sqlite`, `exported_genbank`, `prodigal_stage_started`, `lifecycle_launch`. The command compares this list to the packet and follows no other path. Add `--control-result` for an older terminal.

Success is exit 0 and a `NATIVE_COORDINATE_BINDING.json`. The command joins each candidate to its FASTA record, one Prodigal score row and the source window. It checks accession versions, interval convention, strand, the selected enzyme coding sequence and the translation. A candidate that fits gets `RECONSTRUCTED_SEQUENCE_COORDINATES_UNATTESTED`. That says the interval was rebuilt from kept files. It does not say the run produced coordinates. BGC membership stays `UNVERIFIED`, HMM annotation stays `NOT_RUN_SEPARATE_STAGE`, and canonical import stays not admitted.

These are refused: wrong source or window, version aliases, one-base offsets, reversed strands, non-integer geometry, changed hashes, duplicate candidate identities, ambiguous score joins, and any promoted producer, HMM or BGC claim. Nontriplet intervals are refused, not trimmed.

## Methods wording

Report what your own receipts say. Do not copy versions from another run. Fill the blanks from the run's `runtime_receipt`, `EXECUTION_TERMINAL.json` and the adapter's own output.

> The optional RiPPER adapter (bundle version `<from the run receipt>`) supervised one native run of a locally adapted RiPPER source (source SHA-256 `<hash>`, profile `<adapted_profile_id>`) on `<input description>`. The run used Python `<version>`, Biopython `<version>`, Perl `<version>`, BioPerl `<version>`, BLAST+ `<version>` and a modified Prodigal `<version, source commit>`. File hashes are retained in the run receipts. Limits were `<wall seconds>` s, `<RSS>` of sampled process-tree memory, `<disk>` of run output and one compute thread. Sampling is not an operating-system quota. The process exited `<code>` and produced `<n>` raw candidates (`<status>`). HMM annotation was not run. BGC membership was not verified. The run shows execution and output compatibility only. It does not measure sensitivity or show that a candidate is a precursor.

Keep the terminal, raw JSON, SQLite file, FASTA, stage outputs and before/after dependency receipts for reproducibility.
