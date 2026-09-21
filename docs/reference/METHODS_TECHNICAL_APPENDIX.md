# Methods technical appendix

**Version of record:** Mamey engine v1.9.167 · bundle v9.7.435  
**Scope:** implementation-oriented reporting reference. This appendix documents software behavior and claim ceilings; it is not evidence that a study used every module.

## Release-sensitive parameter register

| Component | Parameter or governed resource | Documented value/state | Reporting requirement |
|---|---|---|---|
| antiSMASH admission | tested major versions | 5-8 | Record version, strictness, schema status, and any override. |
| ZIP safety | GenBank member size / compression ratio | 100,000,000 bytes / 200-fold | Report environment overrides and rejected members. |
| JSON evidence | default policy | bounded, wall-clock-capped parsing with visible fallback | Do not translate a timeout or fallback into zero evidence. |
| RG-GMCI routing | HIGH / MODERATE score floors | 14 / 9 | Preserve score, component evidence, demotions, and deterministic state. |
| RG-GMCI geometry | overlap / locus gap / subject span | 0.20 / 30 / 400 | Report release and any changed constants. |
| RG-GMCI guards | hub degree / terminus margin / small partner | 4 / 500 bp / 25 kb | Report hub and terminus-complexity outcomes. |
| RG-GMCI bounds | reference / pair / evidence-row caps | 40 / 5,000 / 1,000 | A capped scan is incomplete, not negative. |
| source-derived scans | UMED coupling / TFBS upstream window | 5 kb / 300 bp | Record registry/pattern version and sequence availability. |
| triage routing | tier cutoffs | 85 / 70 / 50 | Scores are routing priors, not biological probabilities. |
| scoring | diagnostic / RG-GMCI HIGH / MODERATE bonuses | 25 / 8 / 4 | Preserve standing rules, guards, and raw scores. |
| novelty | KCB reduction boundary | reference score above 10,000 | Missing KCB evidence must not increase certainty. |
| novelty | RiQ credit boundary | similarity below 0.5 | Record RiQ source and binding state. |

All values above are release-specific. `tools/sync_version.py` owns the version-of-record line, and regression tests require it to match `pyproject.toml` and `mamey.__version__`.

## Module records and claim ceilings

### Input, inventory, and exact identity

Admission inspects archive members, rejects unsafe/non-regular members as evidence sources, and records schema uncertainty. Coordinate recovery and assembly metrics depend on the files present. Corrected BGC counts are heuristic. Every individual BGC must be displayed as `strain / full node-or-contig / region / BGC alias`; incomplete identities fail closed.

### KnownClusterBlast, MIBiG, and RiQ

Parsers normalize source-specific evidence while retaining provenance and source precedence. Reference compound names and similarity measures support class-level hypotheses only. Distinguish `NO_VERIFIED_SEARCH`, `SEARCH_FAILED`, `QUERY_UNBOUND`, `ZERO_ADMITTED_ROWS`, and `VERIFIED_NO_HIT`; they are not interchangeable.

### RG-GMCI, FLBR, and EFLS

These modules nominate fragmentation or split-pathway candidates. RG-GMCI enumerates pairs sharing reference clusters and evaluates subject tiling, product compatibility, contig termini, and hub promiscuity. It has no LLM call and does not modify HIGH/MODERATE/LOW states after deterministic scoring. FLBR and EFLS are separate evidence channels and must be named explicitly. None proves that two contigs are physically adjacent.

### Marker, capacity, and routing scans

CCTT uses versioned patterns, class compatibility, and vetoes. CGAD, UMED, resistance, bldA/TTA, and TFBS depend on annotation or sequence context and may be not applicable or degraded. Triage scores are deterministic expert policy. Marker presence is not function; annotation absence in a partial archive is not biological absence.

### Mode B

Deterministic availability inventories, templates, and gates precede Sapote/human/LLM-authored interpretation. Evidence must remain channel-specific and exact-locus-bound. Gene roles, missing components, core/accessory divisions, ecology, and experiments are authored hypotheses with a recorded reviewer disposition. A structurally complete template is not a finished scientific analysis.

### Cohort, phylogeny, and figures

Cohort comparisons require compatible versions/profiles, declared units and denominators, duplicate controls, and governed metadata. Phylogeny and ANI/AAI require hash-bound panels and external-tool receipts. Figures require source-data and methods/caption sidecars plus visual QA. Attractive rendering does not validate a claim.

### Sealing and validation

Manifests, reciprocal checksums, privacy profiles, and seal gates establish reproducibility and policy state. They do not establish biological truth. Hermetic fixtures validate software behavior; biological validation requires independent, task-specific controls.

## Failure-state vocabulary

Use explicit states such as `NOT_RUN`, `NOT_APPLICABLE`, `UNAVAILABLE`, `QUERY_UNBOUND`, `SCHEMA_UNRECOGNIZED`, `DEGRADED`, `PARTIAL`, `CAPPED`, `FAILED`, `HELD`, and `VERIFIED_NO_HIT`. Report the triggering evidence and recovery condition. Never replace these states with `0`, `absent`, or `negative` unless a complete, verified observation supports that statement.

## Study manifest minimum

Freeze the bundle, engine, build or commit; input and reference hashes; antiSMASH version/strictness; registry and database versions; non-default limits; scoring policy; Mode B profile; model/prompt/controller for authored output; cohort roster and exclusions; external tool builds; seeds/threads; figure profile; privacy tier; commands; receipts; and reviewer dispositions.

