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

## The four shipped tiers — which ZIP, and when

Filename pattern: `sapote-mamey-v9.7.22-<TIER>-patched-<build>.zip` (suffix is the build tag;
alphabetical = chronological — pick the latest). Plus the patch kit
`sapote-mamey-DO-FIRST-kit-v9.7.22.zip`.

| Tier ZIP | Contains | Use when | Public? |
|---|---|---|---|
| `…-CODE-patched-…` | full engine + tools + docs + tests | you want to run the pipeline or read the code | **public** (0 AS-###) |
| `…-CODE-analysis-free-patched-…` | CODE minus bundled analysis outputs | a lean code-only handoff / smaller upload | **public** (0 AS-###) |
| `…-SID-public-patched-…` | code + **SID** strain material, AS-### scrubbed to `AS-XXX` | sharing strain context without exposing unpublished AS strains | **public** (leak-audited) |
| `…-MERGED-PRIVATE-scaffold-patched-…` | merged set **including unpublished AS strains** | internal work only | **PRIVATE — never publish** |
| `sapote-mamey-DO-FIRST-kit-…` | this session's new/changed files only | apply *over* a full tier, then run tests there | patch layer (not standalone) |

Rule of thumb: publish from **CODE** (or CODE-analysis-free); share strain context from
**SID-public**; keep **MERGED-PRIVATE** off any public surface (it carries AS-### in data).
File size is not a quality signal — the private scaffold is largest because it holds strain data.
