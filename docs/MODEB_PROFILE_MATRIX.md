# Choose a Mode B card profile

A **profile** is the section layout a Mode B card must follow. Choose it before you write a card, then follow the [authoring walkthrough](MODE_B_USER_WALKTHROUGH.md). You need a package, one complete locus identity and the evidence for that card. Terms are in the [glossary](GLOSSARY.md).

The default is `full48`. Choose `current50_v2` when your task asks for GECCO results, rescued contigs or literature sections.

## The two profiles

| | `full48` (default) | `current50_v2` |
|---|---|---|
| Sections | 1 to 48, each once, in order | 1 to 50, each once, in order |
| Gene-evidence table | Section 4, "Gene-by-gene interpretation" | Section 50, "Data evidence table", last |
| GECCO (a gene-cluster predictor) | No dedicated section | Section 22 |
| Rescued contigs | No dedicated section | Section 26 |
| Literature | No dedicated section | Sections 48 and 49 |
| Finished-card token | `FINISHED_FULL48_CURRENT_EVIDENCE` | `FINISHED_FULL50_CURRENT50_V2` |
| Flag on `emit-modeb-template` and `verify-modeb` | none (default) | `--contract current50_v2` |

Use the same profile to emit and to verify. Each section needs interpretation specific to the locus, or a reasoned statement of why there is a gap. [Preflight](MODE_B_AUTHORING_PREFLIGHT.md) explains when a gap allows a draft and when it holds a finished card.

The full48 section list is in the machine file `mamey/data/mode_b/modeb_full30_corrective_contract.json`. The `full30` in that file name is old; the file defines 48 sections. The current50 file is `mamey/data/mode_b/modeb_current50_v2_contract.json`; see the [current50 guide](MODEB_CURRENT50_V2_CONTRACT.md). Older 8-, 10-, 20- and 30-section documents describe earlier formats. Do not use them.

For writing examples, see the [exemplar guide](reference/modeb_exemplars/README.md). Check your own locus, gene list and citations against it.

## Read the verification result

What `verify-modeb` prints depends on the result:

- On a pass it prints `OK`, the profile name and the number of warnings, then each warning. If the evidence section's coverage could not be checked, because no package core count was bound, the `OK` line says `coverage NOT verified`.
- On a failure it prints `FAIL` and the number of errors, then each error and each warning. It does not print the profile name.
- It never prints the arguments you gave it.

With `--report-json`, the JSON report also records `contract`, `contract_schema_version`, `profile` and `coverage_verified`. `coverage_verified` is `true` only when the package core count was bound, the coverage checks passed and the card passed. The finished-card token turns on the strict publication checks in full48. The later `--semantic-*` checks are opt-in. current50_v2 has its own checks.

Exit code 0 can still come with warnings. Read them.

The JSON report does not record the card, package or source hashes, the verifier version or the arguments. Save those beside it. An existing report file is replaced, so give each attempt a new name:

```text
python mamey_run.py verify-modeb reviews/EXAMPLE-mode-b.md --package runs/EXAMPLE/package --bgc BGC001 --report-json reviews/EXAMPLE-verify-1.json
```

Verify again after you edit the card or its sources.

Two flags weaken the check. `--no-strict-depth` turns depth failures into warnings. `--force` keeps claim-safety findings at warning level on a finished-profile card. Use them only on drafts. Do not use them on a card you will send out.

## After verification

Export the card with [`modeb-export`](MODEB_EXPORT_HOOK.md), or save the authored card with `ingest-receipts` ([walkthrough step 6](MODE_B_USER_WALKTHROUGH.md#6-save-and-review)). A person must read the text and check it against the evidence before the interpretation is accepted.
