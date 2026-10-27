# What would make this work ready for review?

Retired in v9.7.458 and kept as a record. Settings and commands may be out of date. Current guide: [Mode B walkthrough](../../MODE_B_USER_WALKTHROUGH.md).

For a Mode B card, start with the [card walkthrough](../../MODE_B_USER_WALKTHROUGH.md): select the profile, prepare evidence, author, verify, save and review. Readiness comes from the evidence and checks required by that work order. A grade, test count or COMPLETE label cannot replace them.

For other work, use the relevant maintained route:

- **A cohort comparison:** [cohort provenance and rescoring guidance](COHORT_RESCORING_PLAN.md) explains the version/input checks and limits. Its embedded engine-1.9.96 plan is historical; do not use it to select a current engine or authorize reruns.
- **A Methods section:** the [Methods reporting checklist](../../METHODS_REPORTING_CHECKLIST.md) identifies the versions, observation units, source bindings and study-specific details to report for modules actually used. A Methods draft does not supply Results or verified citations.
- **A software/release review:** [contributor guidance](../../../CONTRIBUTING.md) and the [cut protocol](../../../CUT_PROTOCOL.md) define their respective checks. Engineering results remain separate from scientific acceptance and release authority.

Use the selected route to name the actual remaining gap and one bounded next action. For example, a card with unverified gene coverage needs its exact package/roster binding checked before its finished status can be assessed; adding unrelated tests would not resolve that gap.

## Historical rationale retained from 20 June 2026

This page originally recorded a v9.7.96 → v9.7.97 readiness discussion. The details below preserve its useful design history, not current counts, verified present-day completion or instructions to perform the proposed actions. No historical letter grade carries forward.

| Area | What the dated record contributed |
|---|---|
| Test strategy | It reported 1,132 test functions in 190 files, correcting a loose “~1,400” estimate. The motivating failure was an orphaned `sync_version` gate: the lesson was to test gate registration and wiring, rather than add tests to reach a count. It proposed roughly 40–80 targeted tests for input parsing/comparative outputs, rather than 600 filler tests. |
| Coverage priorities | The dated record named `cohort_figures_d/g`, `cohort_figure_captions` and `package_addons_html` as four zero-test presentation modules. It described `antismash_evidence` as 1,069 lines with four test files and `cross_strain_figures` / `master_figure_atlas` as having one test file each. These are historical audit targets, not a current coverage census. |
| Gate wiring | It recorded `tools/gate_registry.tsv` and `tests/test_gate_wiring_invariant.py`, 14 classified gates, a synthetic unregistered-gate failure and a wiring-removal check involving six `sync_version` references. It reported 15/15 touched checks green. These results were not rerun; treat them as history. |
| Release orchestration | It described `tools/release.sh`, a single build-prep call to `log_release.py`, four-tier cuts and a post-build `check_tier_parity.py` gate. Use the current cut protocol above for today's supported tier and owner process. |
| Reference correction | It identified the historical placeholder `ISID-XXX` and NCBI taxId 2601673, with a proposed online source recovery and an xfail tripwire in `tests/test_mibig_no_redaction_corruption.py`. Recovery and test-marker removal require evidence and owner review; this page does not establish that the issue remains open or is resolved. |
| Comparability | It proposed a scoring-boundary guard and a homogeneous engine-1.9.96 rescore. The linked cohort guidance now describes an existing version gate and its limits, so “build a guard next” is no longer a current task. Equal engine labels alone do not establish input/profile comparability. |
| Documentation | It proposed a staleness flagger plus one re-grounded encyclopedia volume as a template, mentioning retired enediyne-BSL2, BRYO-HGT-001 and 66-50-33 wording as historical search targets. A lexical flagger helps locate prose; source review is still needed to decide a correction. |
| Scientific readiness | It distinguished a Methods draft from a paper with study Results and verified citation metadata. Tooling cannot supply missing observations or scientific acceptance. The historical cohort rerun proposal does not establish today's study requirements or authorize compute. |

Return to the current route for the deliverable you are preparing; preserve any unresolved scientific or source gap with the exact claim it affects.
