# Set strain access and track assay records

Use a privacy profile to assign access tiers and an evidence registry to track
materials and assays. You need your strain IDs, access decisions and source
records for each material or assay you enter.

## Privacy profiles

Copy the [profile example](../examples/privacy/strain_privacy_profile.example.json)
and replace its generic names with your strain IDs and tiers. Tiers with
`"public_export": true` map to `PUBLIC`; other tiers map to `PRIVATE`.
The default tier must be non-public, and an unlisted strain stays non-public.

From the program folder, use your run label, input path and profile:

```bash
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip   --privacy-profile privacy/strain_privacy_profile.json
```

`--privacy-profile` selects the file containing those access decisions. A public
release flag cannot override a private tier; the run records
`public_override_refused_by_profile` and can still finish. Check the actual
assignment and release fields in the output. `--release PRIVATE` can make the
choice more restrictive.

## Heterogeneous evidence registry

Copy the [registry example](../examples/privacy/strain_evidence_registry.example.tsv).
A material row identifies an extract or fraction, `parent_material_id` links it
to its source material, and an assay row names the panel and target tested on that
material. Record the actual level: `crude_extract`, `flash_fraction` or `hplc_fraction`.

A fraction needs a non-root parent. An assay must reference material from the same
strain and record its real `replicate_state`. `RESULTS_BOUND` records a source link;
inspect that source to establish the result and replicate meaning.

Validate the two files:

```bash
python tools/validate_portfolio_registry.py   --privacy-profile privacy/strain_privacy_profile.json   --evidence-registry evidence/strain_evidence_registry.tsv
```

The check covers required fields, unique IDs, state vocabularies, parent links,
profile tiers and material/strain agreement. It rejects cycles and cross-strain
parents. It does not open each `source_locator` or validate the vocabulary of
`replicate_state`; check those before using a recorded assay result.

`--project-registry` is a different format and cannot be paired with
`--privacy-profile` in the same extraction. Use the [project catalog guide](PROJECT_CATALOG.md)
for that route.

## Export boundary

The profile controls the package's access label. Public release still needs the
release checks and a decision to publish. The registry keeps access, material
lineage and assay records separate; it does not import measurements into a genome run.
