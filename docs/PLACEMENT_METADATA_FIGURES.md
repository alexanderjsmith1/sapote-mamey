# Placement metadata figures

The native placement report can write its tables and diagnostic tree without metadata strips. Supplying report metadata requests the strip workflow; a requested but incomplete strip returns a nonzero status while preserving the tables and any partial attempt for inspection. There is no cross-file transaction or automatic biological interpretation.

`report`, `all`, and autopilot `run-16s` share repeatable `--owner-table`, `--owner-table-original`, `--resolved`, `--reviewed`, and `--query-override` inputs. Each occurrence is one complete TSV path, including paths with spaces. `--query-prefix` retains the legacy owner-ID join for compatible tables; the native query/reference roles come from the exact admitted placement names. `--rscript` selects one executable, not a shell command. No renderer is invoked when report metadata is absent.

On `build-ref` and `all`, `--reference-metadata` remains the single reference-build identity table, with `tip`, `taxon`, and `role` columns. Autopilot forwards that scalar separately. On `report` only, the older repeatable `--reference-metadata` spelling remains an alias for `--resolved`. Use `--resolved` for report tables on every front door. An explicitly empty path refuses; an omitted option remains optional.

For example, using already admitted inputs and separately prepared metadata:

```sh
python tools/phylo_place.py report --refpkg refpkg --jplace placement/epa_result.jplace \
  --outdir fresh_report --owner-table 'metadata/query owners.tsv' \
  --resolved metadata/resolved_sources.tsv --reviewed metadata/reviewed_sources.tsv
```

A requested strip requires an owner table and labelmap. Required table headers are validated before the front door starts its work. Exact native-tip joins and source-version conflicts are validated once those native identities are available; this cannot pre-admit an unknown future reference set. Existing output panels and report-attempt receipts refuse instead of being reused as current results. A failure after the attempt begins retains partial files; use a fresh destination for a new attempt.

## Type-material evidence

An accession namespace or a legacy `type_display=Type` is not evidence of strain type status. Unknown references remain unmarked; the internal `reference_nontype` color class means other/unknown reference, not a verified negative type assertion. The nearest-type table cells are blank when the admitted panel has no reviewed type references. Nearest-reference-any distances remain separate.

An affirmative reviewed row must contain `accession`, `tip`, `source_accession`, `taxon`, `strain`, `role`, `type_strain_of`, `type_evidence`, `review_state`, `source_url`, and `strain_identity_basis`. `source_accession` is the exact versioned source-sequence accession. `tip` is the exact native reference tip. `role` is `type_reference`; `review_state` is `REVIEWED`. `type_evidence` and the strain basis contain the source-reviewed evidence, with its URL. A named type target is required even where the deposited organism is a genus-level designation. Optional `assembly_accession` is distinct and cannot substitute for the source sequence accession.

The program checks the joins, explicit evidence fields, available native strain anchors, conflicting reviews, and requested resolver identity refusals. It does not verify biological truth by reading a caller's assertion. A reviewed genome type-material ledger or public genome roster is not automatically a reviewed 16S/native-tip map. Those source joins must be prepared and reviewed separately. Missing affirmative proof or a conflict is a HOLD, not an inferred type role. Raw deposited labels remain in provenance; unsupported inserted type labels require explicit anchors before they can be displayed.

Portable `placement_display.py --reference-role-table` uses the same affirmative admission. A bare legacy role column does not recreate a type marker. Versioned accessions remain intact; the type join does not collapse accession versions.

## Current-attempt artifacts

The native report writes an exclusive `<group>_REPORT_ATTEMPT.json`. Its diagnostic figure descriptor comes from the current renderer return; its strip descriptors come from the current builder and both completed child calls. Inspect this receipt rather than collecting arbitrary PNG files from the run directory.

The strip builder writes `BUILD_RECEIPT.json`, `METADATA_PROVENANCE.tsv`, `OMITTED_TIPS.tsv`, `TYPE_EVIDENCE.json`, `TYPE_EVIDENCE.tsv`, and figure context beside the copied metric source tree. Each variant renders independently beneath `color_strips/<group>/renders/<variant>/<group>/`, with its own inputs, log, runtime session, audit, validation, image files and `RENDER_RECEIPT.json`. A later variant does not append to or overwrite the earlier variant's receipt closure. The selected Rscript content is captured before and after execution, and the six effective thread-environment values are recorded.

`RENDERED` means both current children produced the required artifacts and their saved retained-tip geometry and metadata passed the reader. `RENDERED_WITH_OMISSIONS` additionally records the exact input/kept/query/omitted denominators and reasons. Omitted tips are not measured zeroes. `NOT_REQUESTED` is a successful optional-absence state; `HOLD_*` is incomplete. Identical image bytes can be admitted from two independent fresh children; a changed hash alone is not proof of a new render.

Numerical length QA, type-role admission and visual quality are separate. The figure package does not establish species identity, biological activity, or confidence in a clade from a placement weight. Retain the source-bound length receipt and inspect the actual rendered pages before publication.
