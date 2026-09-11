# antiSMASH profile (comparability field)

`antismash_profile` records the antiSMASH `--hmmdetection-strictness` used for a run, because
strictness changes which marginal clusters are detected — so corrected-BGC counts are only
comparable **within** one profile.

- Values: `strict` | `relaxed` | `loose` | `unknown`.
- Supplied at run time: `mamey_run.py run ... --antismash-profile relaxed`.
- Recorded in `manifest.json` and `commit_receipt.json` per strain.
- Default is `unknown` (it is NOT auto-detected — the standard region JSON does not carry it).

## Guard
Before any cross-strain / cross-habitat comparative or ecological claim, run:

    python tools/check_antismash_profile.py <packages_root>

It exits non-zero if strains were run under different profiles, or if any is `unknown`. This
protects the comparative claims the corrected-BGC counts feed. (The Run_Manifest *sheet* column is
a deliberate schema-v1.1 change, staged separately so the frozen 25-sheet schema is not mutated ad hoc.)
