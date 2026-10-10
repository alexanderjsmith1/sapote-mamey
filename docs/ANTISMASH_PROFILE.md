# antiSMASH strictness: provenance and comparability

`antismash_profile` records the selected detection strictness for a run. Current CLI choices are `auto`, `strict`, `relaxed`, `loose` and `unknown`; default is `auto` (`mamey/cli.py:6184–6188`). Auto reads evidence from the archive, retaining `unknown` when unreadable (`:1405–1420`). The field is recorded in manifest/commit metadata. It is a provenance field, not a complete biological comparability certificate.

The reader searches the largest three JSON members for strictness/recorded command-line evidence and has a supported loose-only structural fallback; absence of that fallback cannot distinguish strict from relaxed (`mamey/antismash_input.py:185–251`). Keep `strictness_evidence`, archive hash and warnings. Metadata reads are independent of the main `--json-evidence` setting: `off` does not prevent all JSON inspection.

An explicitly supplied strictness disagreeing with readable archive evidence produces `PROFILE_MISMATCH` but continues under the supplied value (`mamey/cli.py:1416–1420`). Do not report that as an automatic refusal or correction. Preserve the disagreement and reconcile it before pooling; a manifest field alone does not prove the archive ran that setting.

## Check selected packages

From the bundle root, during an authorized inspection:

```bash
python tools/check_antismash_profile.py /path/to/selected/packages
```

The guard recursively reads `manifest.json`, not source archives. Empty discovery, mixed labels, unknown/unreadable fields and repeated strain identities fail by default; `--warn-only` returns 0 despite those findings (`tools/check_antismash_profile.py:22–80`). Use a selected package root: unrelated manifests or duplicate identities in its tree can contaminate the check.

The checker does not restrict every nonblank label to the strict/relaxed/loose enum. A uniform arbitrary label can pass. Inspect the actual values, archive settings and input versions in addition to exit status. Passing known strictness is necessary for this project's pooled count interpretation but does not verify uniform software versions, parameters, input completeness, taxonomy or scientific acceptance.

See [input consumption and limits](ANTISMASH_INPUTS_CONSUMED.md) and [the intake workflow](SOPs/SOP-01_Intake_RawAntiSMASH_vs_MameyPackage.md). Record the selected reader/checker results against the actual input hashes.
