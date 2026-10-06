# Sapote-Mamey Package Profiles

Different ZIP files serve different purposes. File size alone is not a quality signal.

| Package profile | Purpose | Typical contents | antiSMASH / strain outputs? | GitHub suitable? |
|---|---|---|---|---|
| Source repo | Public codebase | Python package, docs, tests, templates, prompts | No | Yes |
| ChatGPT standalone bundle | Runnable handoff for chat-based execution | Source repo plus launch docs and lightweight examples | Usually no | Release asset only |
| Lite bundle | Minimal runnable package | Core code/docs with fewer extras | No | Maybe release asset |
| Strain output package | One analyzed strain | PDFs, workbook, CSV ledgers, figures, extracted protein FASTA, manifests | Derived outputs yes | No, unless demo/synthetic |
| Full archival package | Complete private reproducibility package | Source outputs plus generated reports and possibly large antiSMASH-derived files | Yes | No |

## GitHub rule

Do not commit real strain FASTA files, antiSMASH ZIPs, generated PDFs/workbooks, or large private output archives. Use small synthetic fixtures for tests.

## Large antiSMASH JSON note

antiSMASH outputs can be very large because full JSON files may contain sequence, features, domains, clusterblast evidence, and region metadata. Mamey source packages should not bundle those outputs.

## Which release ZIP exists now

Releases cut the **CODE tier only** (`CUT_PROTOCOL.md`, "Releases cut the CODE tier only", since v9.7.444):
`sapote-mamey-v<version>-CODE-<build>.zip`, with its own leak audit, derivation check and checksums. Use it to
run the pipeline or read the code. The release owner alone seals and publishes a cut.

**Disclosure should not be decided by a strain ID prefix.** Whether a strain's material may leave the project
follows its exact assignment profile and the live release gates (`docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md`,
whose default is non-public). Be aware that the CLI's `--privacy-profile` is optional. Without it, `mamey run`
still applies a legacy derivation from the ID shape: `AS-` → PUBLIC, and `AJS-`/`PENDING`/unrecognized →
PRIVATE (`mamey/cli.py`, `--release` help). That tag is a run label, not a disclosure decision. Select the exact
profile whenever disclosure matters.

### Historical: the multi-tier set (retired)
Until v9.7.444, releases also cut CODE-analysis-free, SID/cohort-public, MERGED-PRIVATE and public tiers, plus a
DO-FIRST patch kit. That tooling stays in the bundle, disabled: the tier branches refuse to run unless
`SAPOTE_ENABLE_DISABLED_TIERS=1` is set. Do not use those tiers for sharing. The old "share strain context from
SID-public" rule is withdrawn.
