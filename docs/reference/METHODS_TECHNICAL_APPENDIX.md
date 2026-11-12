# Methods technical appendix

**Version of record:** Mamey engine v1.9.181 · bundle v9.7.465  
**Scope:** the parameters and limits to report when you describe what the software did. It documents software behavior and claim limits. It is not evidence that a study used every module.
**Terms:** module acronyms (RG-GMCI, FLBR, EFLS, CCTT, CGAD, UMED, TFBS, RiQ, KCB) are defined in the [glossary](../GLOSSARY.md). For a copyable list of what to report, use the [methods reporting checklist](../METHODS_REPORTING_CHECKLIST.md). The [source map](../development/METHODS_IMPLEMENTATION_SOURCE_MAP.md) shows which module to cite for each topic.

## Release-sensitive parameter register

| Component | Parameter or governed resource | Documented value/state | Reporting requirement |
|---|---|---|---|
| antiSMASH admission | default tested major versions | 5-8 | Record version, strictness, schema status, and any override. Out-of-range/unreadable versions trigger a warning; this check alone does not refuse an otherwise recognized input. |
| GenBank read safety | uncompressed member size / compression ratio | 100,000,000 bytes / 200-fold | `MAMEY_GBK_MAX_BYTES` and `MAMEY_GBK_MAX_RATIO` are read at call time. These are member guards, not total archive or process-RAM limits. Report overrides and rejected members. |
| JSON evidence | default policy | `run --json-evidence` defaults to `bounded`; `--capped-session` forces the main walker `off` | The separate record pass still reads eligible, readable JSON for KCB percent; inspect its status for absent, held or unreadable input. Do not translate timeout or fallback into zero evidence. |
| RG-GMCI routing | HIGH / MODERATE score floors | 14 / 9 | Preserve score, component evidence, demotions, and deterministic state. |
| RG-GMCI geometry | overlap / locus gap / subject span | 0.20 / 30 / 400 | Report release and any changed constants. |
| RG-GMCI guards | hub degree / terminus margin / small partner | 4 / 500 bp / 25 kb | Report hub and terminus-complexity outcomes. |
| RG-GMCI export budgets | references per BGC / evidence rows / ranked pairs | 40 / 5,000 / 1,000 | References are limited during collection; exported HIGH evidence rows and HIGH ranked pairs are retained beyond the display budgets. Report total, exported, and omitted counts. |
| source-derived scans | UMED coupling / TFBS upstream window | 5 kb / 300 bp | Record registry/pattern version and sequence availability. |
| triage routing | tier cutoffs | 85 / 70 / 50 | Scores are routing priors, not biological probabilities. |
| scoring | diagnostic / RG-GMCI HIGH / MODERATE bonuses | 25 / 8 / 4 | Preserve standing rules, guards, and raw scores. |
| novelty | KCB reduction boundary | A non-UNKNOWN KCB state and recorded rank-1 percent (`kcb_similarity_pct`) at least 70 | A missing percent or UNKNOWN state does not trigger the reduction. A cumulative score without percent does not reduce novelty. Missing KCB evidence must not increase certainty. |
| novelty | RiQ credit boundary | similarity below 0.5 | Record RiQ source and binding state. |

All values above are release-specific. `tools/sync_version.py` owns the version-of-record line, and regression tests require it to match `pyproject.toml` and `mamey.__version__`.

## Module records and claim limits

### Input, inventory, and exact identity

Admission inspects archive members, rejects unsafe/non-regular members as evidence sources, and records schema uncertainty. Coordinate recovery and assembly metrics depend on the files present. Corrected BGC counts are heuristic. Every individual BGC must be displayed as `strain / full node-or-contig / region / BGC alias`. That is a requirement, and each route checks it differently. The direct card writer (`mamey.judgment_store.record_mode_b`) raises an identity hold before writing, unless its caller has already checked identity. `GCF_Tags.csv` still writes a row with a missing component, marks it `IDENTITY_HOLD` in `identity_status` and leaves the cell blank. Check the route you used.

### KnownClusterBlast, MIBiG, and RiQ

Parsers normalize source-specific evidence while retaining provenance and source precedence. Reference compound names and similarity measures support class-level hypotheses only. Distinguish `NO_VERIFIED_SEARCH`, `SEARCH_FAILED`, `QUERY_UNBOUND`, `ZERO_ADMITTED_ROWS`, and `VERIFIED_NO_HIT`; they are not interchangeable. A recognized KnownClusterBlast no-hit report can produce `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED`; an unsupported empty, missing, unreadable or unbound file is not that recognized state. Neither is a verified no-hit.

### RG-GMCI, FLBR, and EFLS

These modules nominate fragmentation or split-pathway candidates. RG-GMCI enumerates pairs sharing reference clusters and evaluates subject tiling, product compatibility, contig termini, and hub promiscuity. It has no LLM call and does not modify HIGH/MODERATE/LOW states after deterministic scoring. FLBR and EFLS are separate evidence channels and must be named explicitly. None proves that two contigs are physically adjacent.

### Marker, capacity, and routing scans

CCTT uses versioned patterns, class compatibility, and vetoes. CGAD, UMED, resistance, bldA/TTA, and TFBS depend on annotation or sequence context and may be not applicable or degraded. Triage scores are deterministic expert policy. Marker presence is not function; annotation absence in a partial archive is not biological absence.

### Mode B

Deterministic availability inventories, templates, and gates come first. A person or an assistant then writes the interpretation. Evidence must remain channel-specific and exact-locus-bound. Gene roles, missing components, core/accessory divisions, ecology, and experiments are authored hypotheses with a recorded reviewer disposition. A structurally complete template is not a finished scientific analysis.

### Cohort, phylogeny, and figures

Cohort comparisons require compatible versions/profiles, declared units and denominators, duplicate controls, and governed metadata. Phylogeny and ANI/AAI require hash-bound panels and external-tool receipts. Figures require source-data and methods/caption sidecars plus visual QA. Attractive rendering does not validate a claim.

### Sealing and validation

Manifests, reciprocal checksums, privacy profiles, and seal gates check selected files and policy state. They do not by themselves show that a workflow can be reproduced: checksum exclusions and varying artifacts limit byte comparison (see below), and a validated replay is a separate test. They do not establish biological truth. Hermetic fixtures validate software behavior; biological validation requires independent, task-specific controls.

## Failure-state vocabulary

Use explicit states such as `NOT_RUN`, `NOT_APPLICABLE`, `UNAVAILABLE`, `QUERY_UNBOUND`, `SCHEMA_UNRECOGNIZED`, `DEGRADED`, `PARTIAL`, `CAPPED`, `FAILED`, `HELD`, and `VERIFIED_NO_HIT`. Report the triggering evidence and recovery condition. Never replace these states with `0`, `absent`, or `negative` unless a complete, verified observation supports that statement.

## Study manifest minimum

Freeze and report each item below. The [methods reporting checklist](../METHODS_REPORTING_CHECKLIST.md) covers the same ground as checkboxes.

- Bundle, engine, and build or commit.
- Input and reference hashes.
- antiSMASH version and strictness.
- Registry and database versions.
- Non-default limits and the scoring policy.
- Mode B profile, and the model, prompt and controller for any authored output.
- Cohort roster and exclusions.
- External tool builds, seeds and threads.
- Figure profile and privacy tier.
- Commands, receipts and reviewer dispositions.

## Reading export limits and reproducibility

The budgets are in the register above. `rggmci.py` keeps every row associated with a HIGH pair before it applies the 5,000-row budget, so the evidence export can exceed 5,000 rows. Its ranked-pair export keeps the first 1,000 ranked pairs plus HIGH pairs beyond that point. The separate `split_candidates` list is sliced to 1,000. An exported list is therefore not the full pair census. Preserve `pairs_total`, evidence-row totals, omitted-row counts, and the summary's export message. A reported candidate remains a hypothesis, including a HIGH candidate.

Analytical determinism is scoped to the named fields/artifacts and fixed inputs, policy, versions, and environment. It is not a guarantee that every package byte is invariant across invocations: `packaging.py` explicitly treats timing receipts as mutable, excludes selected post-seal images/PDFs from checksums, and notes PDF build timestamps. Record the checksum exclusions and the actual deterministic comparison scope. Refer to the [source map](../development/METHODS_IMPLEMENTATION_SOURCE_MAP.md) to locate owners; its existence gate does not validate these parameter values.
