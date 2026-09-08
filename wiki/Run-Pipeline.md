# The run pipeline — what happens inside `mamey_run.py run`

**Motto: deterministic extraction, judgment deferred.** Tier 1 (Mamey, Python) extracts and
organizes evidence; Tiers 2/3 (Sapote, LLM protocols shipped as Markdown) judge it. Nothing in this
pipeline makes a structural or bioactivity claim — outputs are class-level hypotheses routed for
later judgment.

Entry point is `mamey_run.py` (not an installed `python -m mamey` copy — the runner forces the local
package onto `sys.path` to avoid version-shadowing). `cli.py::run_one_strain()` orchestrates six
deterministic stages; data flows as typed objects from `models.py` (`RunContext` →
`AssemblyMetrics` + `list[BGCRecord]` → `SourceScanBundle` → `list[TriageRecord]`, bundled in a
`MameyRun`).

## The six stages

1. **Intake / parse** (`parsers.py`, `antismash_evidence.py`) — the antiSMASH output ZIP is parsed;
   each region becomes one `BGCRecord` with a stable `bgc_id` locked at parse time (the node-naming
   rule: every claim traces to a stable BGC node id). KnownClusterBlast / RiPP / Pfam / TIGRFAM
   evidence status is read. JSON handling defaults to `--json-evidence bounded` (streamed via the
   vendored ijson, wall-clock capped) with TXT-only fallback; `full` mode refuses files > 20 MB.
2. **Ten source-derived scans** (`source_scans.py`) — class triggers (CCTT), chitinase context
   (CGAD), resistance tiers, TFBS, RiPP maturation (UMED), bldA/TTA codon usage, cassettes, and
   more, producing a `SourceScanBundle`. `rggmci.py` adds RG-GMCI: multi-contig split-pathway
   linkage (two-proof rule — a HIGH-confidence merge claim needs two independent lines of
   evidence). Scan marker definitions increasingly come from a central registry
   (`registry_detector.py` / `registry_schema.py`) instead of hardcoded patterns.
3. **Scoring / triage** (`scoring.py::triage_bgcs`) — auto-floor AB/AF/novelty **routing priors**
   (explicitly NOT final scores), CCTT diagnostic bonuses, standing-rule downgrades from
   `mamey/data/rules_registry.json` (e.g. SACCHARIDE → Inventory tier, with false-positive-guard
   contexts), RG-GMCI bonuses, and mis-anchor / mobile-element / primary-metabolism guards that
   prevent false high-confidence calls.
4. **Workbooks** (`workbook.py`, `master_workbook.py`) — the per-strain `_5_workbook.xlsx`, plus
   accumulation into a persistent cross-strain `--master` workbook (Strain_Registry, BGC_Master,
   class matrix, DAPR boards).
5. **Package + manifest** (`packaging.py`) — the numbered outputs (`_1_intake.json`,
   `_2_inventory.csv`, `_3_*`, `_4_triage_board.csv`, `_5_*.xlsx`), `manifest.json` (the
   authoritative handoff to the judgment kernel), checksums, and the sealed ZIP whose name embeds
   both versions: `{strain}_SapoteMamey_v{BUNDLE}_engine{ENGINE}_Complete_Package.zip`.
6. **Validate** (`validate.py::validate_package`) — file presence plus **gates** (e.g. RGGMCI_GATE:
   HIGH-confidence pairs must be listed; DEPTH_FLOOR for gold mode) → `gate_validation.json` with
   PASS / PASS_WITH_ISSUES / MAMEY_COMPLETE.

Post-seal subcommands (`render-figures`, `cohort-figures`, `mode-b`, `domain-level`,
`ingest-receipts`) consume an already-sealed package and never fail the core run.

## Run modes

`gold` is the only analysis mode (every BGC gets full Mode B depth). `standard` is
deprecated/retired and aliased to `gold`; `smoke` was removed entirely at v9.7.161.

## Why so many `*_gate` / `*_guard` tests

Scoring behavior is data-driven (rules registry, marker registry, gate registry TSVs). Every scan
or scorer change is expected to have a paired `tests/test_*_gate.py` / `test_*_guard.py` asserting
the invariant — the gates are the contract, the tests are the proof it held.

*Claim-safety: triage priors route attention; they are not conclusions. Judgment is deferred to the
Sapote tiers, and even those emit class-level hypotheses only.*
