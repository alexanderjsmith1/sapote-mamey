# antiSMASH strictness: provenance and comparability

`antismash_profile` records the selected detection strictness for a run. Current CLI choices are `auto`, `strict`, `relaxed`, `loose` and `unknown`; default is `auto`. Auto reads evidence from the archive, retaining `unknown` when unreadable. The field is recorded in manifest/commit metadata. It is a provenance field, not a complete biological comparability certificate.

The reader searches the largest three JSON members for strictness/recorded command-line evidence and has a supported loose-only structural fallback; absence of that fallback cannot distinguish strict from relaxed. Keep `strictness_evidence`, archive hash and warnings. Metadata reads are independent of the main `--json-evidence` setting: `off` does not prevent all JSON inspection.

An explicitly supplied strictness disagreeing with readable archive evidence produces `PROFILE_MISMATCH` but continues under the supplied value. Do not report that as an automatic refusal or correction. The run records the disagreement in the manifest `issues` list, and the pooling checker below refuses that package. Preserve the disagreement and reconcile it before pooling; a manifest field alone does not prove the archive ran that setting.

## Check selected packages

From the bundle root, during an authorized inspection:

```bash
python tools/check_antismash_profile.py /path/to/selected/packages
```

The guard recursively reads `manifest.json`, not source archives. Empty discovery, mixed labels, unknown/unreadable fields, repeated strain identities, a recorded `PROFILE_MISMATCH` issue and any label other than `strict`, `relaxed` or `loose` (for example `auto` or an arbitrary override) fail by default. `--warn-only` returns 0 despite those findings and marks the message as advisory; that exit is not acceptance. Use a selected package root: unrelated manifests or duplicate identities in its tree can contaminate the check.

A uniform admitted label still reflects the manifest, not the archive. Inspect the actual values, archive settings and input versions in addition to exit status. Passing known strictness is necessary for this project's pooled count interpretation but does not verify uniform software versions, parameters, input completeness, taxonomy or scientific acceptance.

See [input consumption and limits](ANTISMASH_INPUTS_CONSUMED.md) and [the intake workflow](SOPs/SOP-01_Intake_RawAntiSMASH_vs_MameyPackage.md).
