# The run pipeline — what happens inside `mamey_run.py run`

Understand the stages of the run command.  
This page is for operators and readers interpreting run outputs.

**Motto: deterministic extraction, judgment deferred.** Tier 1 (Mamey, Python) extracts and
organizes evidence; Sapote, the judgment workflow, interprets it. Nothing in this
pipeline establishes a measured product structure or bioactivity. It emits
source-derived records and structural/capacity heuristics for later review.

Entry point is `mamey_run.py` (not an installed `python -m mamey` copy — the runner forces the local
package onto `sys.path` to avoid version-shadowing). `cli.py::run_one_strain()` coordinates the following six-part overview, not an exhaustive phase-receipt list; data flows as typed objects from `models.py` (`RunContext` →
`AssemblyMetrics` + `list[BGCRecord]` → `SourceScanBundle` → `list[TriageRecord]`, bundled in a
`MameyRun`).

## The six stages

1. **Intake / parse** (`parsers.py`, `antismash_evidence.py`) — the antiSMASH output ZIP is parsed;
   admitted parsed records yield `BGCRecord` objects with local aliases. Preview
   counts do not establish that every source region was admitted or scored. A claim about an individual
   locus also needs its bound `strain / full node-or-contig / region / BGC alias` identity; the alias
   alone is not a physical identity. KnownClusterBlast / RiPP / Pfam / TIGRFAM
   evidence states are recorded. `run --json-evidence` defaults to `bounded`;
   `--capped-session` forces the main walker to `off`. The CLI applies a bounded-parser
   budget, not a whole-run time guarantee; fallback/record work can occur outside it.
   On a bounded-parser timeout or unavailable ijson, the main walker falls back to off.
   KnownClusterBlast TXT files can be read when available, and a separate record pass
   can still read JSON for the KCB percent and TIGRFAM hits. Inspect their statuses;
   off does not necessarily make the result TXT-only. `full` mode refuses JSON files over 80,000,000 bytes (`FULL_MAX_JSON_BYTES`).
   [JSON evidence modes](../docs/reader/04_RECOVERY_AND_LIMITS.md#json-evidence-modes) has the details.
2. **Source-derived annotation and context scans** (`source_scans.py`) — class triggers (CCTT), chitinase context
   (CGAD), resistance tiers, TFBS, RiPP maturation (UMED), bldA/TTA codon usage, cassettes, and
   more, producing a `SourceScanBundle`. `rggmci.py` adds RG-GMCI: homology-guided candidate links between
   fragments on different contigs. A link is not a contig join; HIGH is a computational category,
   not proof of physical linkage. Pattern and registry roles are producer-specific; inspect the selected scan
   and marker source rather than assuming one universal detection implementation.
3. **Scoring / triage** (`scoring.py::triage_bgcs`) — computes numeric AB/AF/novelty
   **routing scores (priors)** from eligible evidence. It applies diagnostic bonuses,
   standing-rule handling from `mamey/data/rules_registry.json` with a class-dependent
   bottom tier (Low or Inventory), RG-GMCI bonuses,
   and mis-anchor / mobile-element / primary-metabolism guards that limit selected
   credit and flag interpretation risks. A guard is not proof that false positives
   were eliminated.
4. **Workbooks** (`workbook.py`, `master_workbook.py`) — the per-strain `_5_workbook.xlsx`, plus
   accumulation into a persistent cross-strain `--master` workbook (Strain_Registry, BGC_Master,
   class matrix, DAPR boards).
5. **Package + manifest** (`packaging.py`) — the numbered outputs (`_1_intake.json`,
   `_2_inventory.csv`, `_3_*`, `_4_triage_board.csv`, `_5_*.xlsx`), `manifest.json` (the
   authoritative handoff to the judgment kernel), checksums, and the sealed ZIP whose name embeds
   both versions and the antiSMASH detection profile:
   `{strain}_SapoteMamey_v{BUNDLE}_engine{ENGINE}_{profile}_Complete_Package.zip`.
   The profile token is `strict`, `relaxed`, `loose` or `unknown`; use the emitted filename
   and manifest rather than reconstructing it.
6. **Validate** (`validate.py::validate_package`) — file presence plus **gates** (e.g. RGGMCI_GATE:
   HIGH-confidence pairs must be listed; DEPTH_FLOOR for gold mode) → `gate_validation.json`. The
   [status values](../docs/reader/04_RECOVERY_AND_LIMITS.md#status-values) table lists what each result means.

Post-seal subcommands (`render-figures`, `cohort-figures`, `mode-b`, `domain-level`,
`ingest-receipts`) consume an already-sealed package after extraction. A post-seal command can fail or skip its
own requested output even though it does not rerun the core analysis. Authoring commands such as
`mode-b`, `render-figures` and `domain-level` can write package artifacts and refresh post-seal
integrity checksums; `validate` normally writes a mutable `package_status.json` receipt. Preserve
original package bytes on a separate working copy when required and inspect each command result.

## Run modes

`gold` is the only analysis mode; it assigns the gold evidence/depth requirements. It does not
author a finished Mode B card for every region. `standard` is a deprecated alias of `gold`;
`smoke` was removed entirely at v9.7.161. Review actual phase receipts and selected outputs
separately from the mode label; see [artifact scope](../docs/PER_MODE_ARTIFACT_SET.md).

## Why so many `*_gate` / `*_guard` tests

Scoring behavior is data-driven (rules registry, marker registry, gate registry TSVs). Every scan
or scorer change is expected to have a paired `tests/test_*_gate.py` / `test_*_guard.py` asserting
the invariant — the named checks and their tested scope matter. A passing test supports its
exercised cases, not every input or scientific claim.

*Claim-safety: triage priors route attention; they are not conclusions. Judgment is deferred to the
Sapote tiers, and even those emit class-level hypotheses only.*
