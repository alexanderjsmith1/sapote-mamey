# Optional class evidence and genome-side exports

The following commands read a package and write a fresh external directory, defaulting to `<package.parent>/post_seal/<command>/`. Supply a new `--out` for another run. They refuse outputs that resolve inside the package, including symlinks. Package manifests and integrity files remain unchanged. Stable source files and no concurrent writers are required.

The destination itself must not exist, even if it is empty. The publication helper creates missing parents and a hidden staging directory beside the destination, snapshots all package file hashes, checks the package again, then renames the staged directory into place. A caught failure removes its staging directory; newly created parents can remain. A process interruption can leave a hidden staging directory. Retain the log and inspect its source/output hashes as unaccepted partial evidence before retrying at a fresh destination; do not infer success from an output folder alone or modify the original package to clear a refusal. Package symlinks are refused by the snapshot. The shared publication check does not validate scientific conclusions or provide a universal output checksum manifest.

## GECCO

Request **GECCO crosscheck** for a class-level second opinion on the reviewed package/source pair. This command launches the external GECCO executable; it is not a planning-only reader. From the selected bundle root, substitute the actual paths and a fresh output directory:

```bash
python mamey_run.py gecco-crosscheck \
  --package "/absolute/reviewed_run/package" \
  --zip "/absolute/source/original_antismash.zip" \
  --out "/absolute/new_outputs/gecco_crosscheck" \
  --threshold 0.8 --jobs 1
```

Use the package directory itself. `--zip` is required by the CLI and must match the manifest's recorded `input_zip_sha256`. The adapter finds `gecco` on PATH, requires a successful `--version` probe whose output includes a `0.11.x` version, and rejects other versions. A finite threshold in `[0,1]` and a positive integer job count are required. The version probe has a 15-second timeout; the analysis subprocess has no adapter timeout. Select the resource scope before launching the workflow; a version probe alone does not establish usable model/dependency assets.

GECCO is optional and off by default. Install it separately if desired; the bundle and doctor do not install it. This adapter targets the 0.11 CLI/table format and probes the actual executable version. It runs `gecco run` with `--cds-feature CDS --locus-tag locus_tag --force-tsv` using the whole-genome GBK inside the exact package-bound source ZIP. If more than one whole-genome GBK exists, choose `--genome-member`. The default threshold is 0.8; an explicit threshold is recorded. [Upstream CLI](https://github.com/zellerlab/GECCO/blob/v0.11.0/gecco/cli/commands/run.py) and [table model](https://github.com/zellerlab/GECCO/blob/master/gecco/model.py) describe the external interface.

The published directory contains `<strain>_7_gecco_vs_antismash.csv`, `<strain>_7_gecco_only_clusters.csv`, `<strain>_7_gecco_gene_probabilities.csv`, the selected `genome.gbk`, `raw/` external outputs, `gecco.log`, `support.json`, `receipt.json` and requested copied gap-gene tables. Overlap rows are `OVERLAP_OBSERVED` or `NO_OVERLAP_OBSERVED`; a GECCO-only cluster means no overlap with the manifest's selected region roster, not proof that no other predictor has called it. JSON lists in CSV cells remain serialized lists.

The receipt records exact source/version/threshold/job/argv and hashes published files other than itself. Hash the receipt separately and reconcile region/CDS/cluster and copied-join counts before handoff. Recorded argv contains the temporary staging paths used during execution; those paths move at publication, so it is provenance rather than a directly reusable replay command. `bound_support` consumers verify the package snapshot and `support.json` hash; they do not recheck every raw output or independently validate GECCO biology.

CLI exit 0 means publication completed; caught input/filesystem/subprocess/ZIP failures return 2. On a native run failure, captured stdout/stderr are not written to `gecco.log` because that write happens only after successful subprocess return; staging cleanup can remove other partial outputs. Preserve terminal invocation/exit evidence, report unavailable native diagnostic streams explicitly and use the shared fresh-destination recovery guidance. Do not treat a missing failure log as evidence the external run succeeded. A `NODE_n_length_L` match ignores rewritten coverage suffixes but refuses normalized-contig ambiguity. The adapter checks returned CDS IDs and coordinates against the source before publication. Candidate selection considers `.gbk`/`.gb` members and excludes names matching `.regionNNN.gbk`; `--genome-member` must name an exact eligible archive member when selection is ambiguous. Source records require unique full and normalized contig IDs plus globally unique, nonempty CDS locus tags and in-bounds coordinates. Each package region must have a contig and span within that genome.

GECCO's required `genome.genes.tsv` must contain exactly the full source CDS tag roster with matching contig and 1-based inclusive coordinates; a filtered subset causes refusal, even if the external program exits successfully. `genome.clusters.tsv` must have unique nonblank cluster IDs, admitted contigs and in-bounds 1-based inclusive coordinates. Invalid present probabilities are refused; blank/NA probabilities remain unknown. The output gene CSV uses 1-based inclusive coordinates, while GECCO-only cluster CSV uses zero-based half-open intervals. Do not join these columns without recording the conversion. A low probability is not evidence against a cluster; an overlap is a second opinion, not proof.

Repeat `--gap-genes "/absolute/source/gap_genes.tsv"` for optional copied joins. A `.tsv` suffix selects tab parsing; other suffixes use commas. At least one of `locus_tag`, `query_gene` or `protein_id` is required. If several are present, their nonempty values must agree for every row. Preexisting `gecco_mean_p`, `gecco_join_state` or `gecco_binding_scope` columns are refused. Supplied strain fields must exactly match, and supplied contig fields must agree after the adapter's normalization.

Coordinate columns must come in complete pairs. `start/end` and `start_1based/end_inclusive` mean 1-based inclusive; `start_0based/end_exclusive` mean zero-based half-open. Supplied coordinates are checked against a matched source CDS. Without them, a joined row is explicitly `SOURCE_LOCUS_TAG_ONLY`; it is not a coordinate-validated join. Unknown tags remain `NO_SOURCE_LOCUS_TAG_MATCH`/`UNMATCHED`, even when supplied coordinates are syntactically valid. Copied outputs are `<input-stem>_gecco<input-suffix>`; inputs producing the same output name are refused. Inspect `gecco_join_state` and `gecco_binding_scope`, not just the presence of a probability. Original tables are not modified.

## Genome-side metabolomics bridge

Request **genome-side metabolomics export** to prepare class-hypothesis and region-GBK files for a separately reviewed MS workflow. Run from the selected bundle root in its compatible environment, with Biopython available for GenBank declaration checks:

```bash
python mamey_run.py export-metabolomics \
  --package "/absolute/reviewed_run/package" \
  --source-zip "/absolute/source/original_antismash.zip" \
  --out "/absolute/new_outputs/metabolomics_export"
```

Replace these template paths; the destination must be fresh. Add `--gecco-dir "/absolute/reviewed_gecco_crosscheck"` only for a matching recorded sidecar. `--package` takes the package directory itself, not a CompletePackage ZIP or a run root. Its JSON-object manifest must include a valid strain ID and unique full-locus BGC records with integer zero-based start/end and region number.

The original antiSMASH ZIP is required evidence even though `--source-zip` is optional syntactically. Without it, the resolver uses only the manifest's declared `input_zip` locator; there is no workspace search. `input_zip_sha256` must be a valid recorded SHA-256 and the selected archive must match it. A relocated archive can be supplied explicitly without rewriting the accepted manifest. Each BGC must bind exactly one `.regionNNN.gbk` member with matching contig/region, span, original coordinates, region feature and unique in-bounds CDS declarations. Missing members or declarations cause refusal rather than a target-only partial export. These checks bind the supplied declaration; they do not independently establish the truth of the original extraction or validate the whole package.

New extraction runs populate `manifest.json`'s `metabolomics_targets` from observed domain counts. The exporter recomputes the same fields for older packages without altering them. PKS, NRPS, RiPP and supported terpene markers map to broad NPClassifier pathway vocabulary in `mamey/data/bgc_class_to_npclassifier.json`; this is a versioned hypothesis table, not a structure classification or CANOPUS result. Other or product-only evidence stays `unmapped`. Hybrid regions retain independent hypotheses. Every entry carries the full strain / contig / region / BGC identity and the ceiling: **capacity; an expected class to look for, not a predicted compound**.

Measured median identity uses distinct per-gene MIBiG evidence for the bound best accession. Unknown measurements and the corresponding 74% close-match flag stay null; cumulative KCB score is never reinterpreted as identity. A supplied GECCO sidecar must match the original package snapshot and its recorded support hash.

Outputs are `<strain>_metabolomics_targets.tsv`, `metabolomics_targets.json`, `nplinker/antismash/<strain>_<BGC>.gbk`, `nplinker/source_pointers.json`, `nplinker/strain_mappings.json`, `podp_record_template.json`, `README.md` and `receipt.json`. JSON lists/dictionaries in the target TSV are serialized JSON cells. Source pointers bind each original region member's bytes and declaration; the receipt binds the package snapshot, original archive and mapping policy, but does not hash every final output or itself. Retain an external output/receipt hash inventory and compare target/pointer/GBK counts with the requested manifest roster. A successful zero-target export can result from an empty manifest BGC list; it is not evidence that the genome has no BGCs.

The CLI returns 0 after a published export and 2 for caught input/filesystem/ZIP refusals; other exceptions can propagate. The success message explicitly leaves MS sample mapping for the operator. `OPERATOR_COMPLETION_REQUIRED`, null MS metadata and an empty sample-name list are incomplete templates, not evidence of a validated NPLinker/PoDP integration. The templates are explicitly marked incomplete and do not claim validation against external submission schemas. NPLinker, PRISM, GNPS/MASST, SIRIUS/CANOPUS, DeepBGC and BiG-SLiCE are registered optional companions. Web services are labelled manual/offline-unprobed; local detection cannot establish service availability. No MS data are invented, uploaded or associated by this command.

## Explicit non-KS second-proof policy

Request **non-KS second-proof review** with the explicitly selected `nonks_position_v1` policy, bound package, scorecard and a fresh external output directory:

```bash
python mamey_run.py two-proof-rescue \
  --package "/absolute/reviewed_run/package" \
  --policy nonks_position_v1 \
  --scorecard "/absolute/source/bound_scorecard.tsv" \
  --out "/absolute/new_outputs/nonks_second_proof"
```

Replace all template paths. The input is the package directory with its manifest and exactly one top-level `*_4A_RGGMCI_ranked_pairs.csv`; a package ZIP/run root is not normalized by this adapter. Zero or multiple matching pair files are refused. Existing package `_4D` rows are recomputed from `_4A` and the manifest's `source_scans.pks_ks_scan`; no new KS scan or reference-position analysis runs here. Without `--policy`, the default remains `ks_clade_v2`. `--scorecard` is optional syntactically, so selecting the alternative without it can publish unresolved advisory rows rather than establish the position proof.

The normal package run and `--policy ks_clade_v2` preserve the established default KS rule. The named alternative recomputes advisory `_4D` outputs externally and records its policy in every row and receipt. It grants an alternative second proof only for a positively observed non-KS core class, a complementary **HIGH** RG-GMCI linkage, and a scorecard **CONSISTENT** reading with a named relative. A relative of any assembly level can supply this reading. **APART_CLOSE** or **CONFLICT** vetoes an eligible non-KS pair; APART_WEAK, absent/read-unresolved position and unresolved class evidence leave the independent proof unresolved. The adapter keeps the KS protocol when domain counts or the BGC's KS count are positive, and also conservatively when its product labels contain `pks`, `polyketide` or `transat`; that label-based branch is not a new observed KS-domain result. Non-KS eligibility requires a recognized positive core-domain count on either member and different manifest contigs, with no KS-present state on either member. Supplied domain entries are checked for contig, overlapping coordinates and basic schema, but the count dictionary is not reconciled with those entries. Preserve the producing domain evidence and counts as a separate source-admission requirement. Per-gene KnownClusterBlast remains supporting evidence, never a second proof.

The scorecard TSV must carry `strain`, exact `identity_a` and `identity_b`, `layers_verdict`, and `relative`. Identities must match this manifest's four-part loci. Matching-strain duplicate or conflicting pair bindings are refused. Rows whose `strain` is not exactly the manifest strain are skipped before identity checks; a mixed or case-mismatched scorecard can therefore provide no usable position rows without a dedicated coverage refusal. `layers_verdict` is not a validated enum: an unrecognized spelling is retained but does not clear a position proof. Compare expected and consumed pair identities and verdict vocabulary before interpreting the result. A nonblank `relative` is a declared identifier, not independent confirmation of that genome, assembly quality or its positioning result. No distance threshold is changed or reimplemented: the existing scorecard owns its position reading. Verdicts are class-level candidates for human adjudication, never a merge, production or activity claim. This implementation does not establish benchmark validity for an unmeasured non-KS population.

The output directory contains `<strain>_4D_two_proof_rescue.csv` and `receipt.json`. Review `rule_policy`, full `identity_a`/`identity_b`, `verdict`, `second_proof_channel`, `independent_proof_state`, `position_verdict` and `position_reference` together. KS-only links not associated with ranked BGC pairs can carry blank BGC/full-identity fields; keep them unresolved and do not invent a locus assignment. The receipt binds a package snapshot and pair/scorecard hashes, but does not hash the final CSV or itself. Its `ks_scan_state=AVAILABLE` means the stored scan object is truthy, not that every required scan or locus was validated. Retain an external output/source hash inventory and requested/observed pair counts. The CLI returns 0 after publication and 2 for caught value/filesystem refusals; zero pairs or unresolved proofs can still be successful publication.

**Current complementarity handoff limit:** the underlying join admits either an explicit `COMPLEMENTARY` class or a guarded disjoint-reference fallback. It then omits the fallback counters from the projected row. The alternative policy checks complementarity again on that projected row, so a fallback-only HIGH candidate with a valid position can retain its prior verdict while reporting independent position proof `PRESENT`. Preserve the original `_4A` counters and review both fields; do not manually promote the candidate or treat `PRESENT` alone as `TWO_PROOF_RESCUE`. A source-owner correction and scoped regression validation are required to make that handoff consistent.

Keep the package, pair CSV, scorecard and stored domain/KS scans stable throughout the run. Pair/manifest/scorecard reads precede the publication snapshot, and external scorecard hashing occurs after its read; the receipt alone does not establish that concurrent replacements were excluded. Use the shared fresh-directory publication/recovery guidance above and preserve prior accepted evidence.

## Package argument syntax

These command prefixes identify the package argument; the complete examples above supply the remaining inputs and external output destination. Replace every placeholder before execution.

- `gecco-crosscheck --package <package>`
- `export-metabolomics --package <package>`
- `two-proof-rescue --package <package>`
