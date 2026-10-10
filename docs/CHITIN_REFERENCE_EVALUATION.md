# Whole-genome chitin/GlcNAc reference-capacity evaluation

**Module:** `mamey/chitin_reference_eval.py` (library) + `tools/chitin_reference_eval.py`
(operator front door) + `tests/test_chitin_reference_eval_v97405.py`.

Formalises the per-strain whole-genome chitin reference evaluation workroom (Codex, *August 21
Codex/PER_STRAIN_CHITIN_REFERENCE_EVALUATION_2026-08-21/*) into the bundle. State names, the
architecture-profile logic, and the reference-quality tiers are carried over from that workroom's
own `working/*.py` scripts; the input surface is generalised from that workroom's 46-strain
hardcoded census to any sealed package's CGAD scan output paired with an operator-supplied
reference registry.

## Scope — read this before wiring anything to this module

Two decisions from the source workroom's decision ledger govern this module and are unchanged
here (`DECISION_AND_HOLD_LEDGER.tsv`, both `ACTIVE`, "superseded only by owner"):

- **CHD-001** — the strain is the biological unit of evaluation. A cohort table is navigation and
  context only, never the unit of conclusion.
- **CHD-002** — chitin analysis is **whole-genome** and **independent of Mode B / BGC completion**.
  Chitinase/CGAD capacity is a whole-genome trait, not a BGC call.

**Consequence for callers:** this module must never be routed through triage or scoring. It has
no `--triage`/`--score` mode and takes no `TriageRecord`/`BGCRecord` input on purpose. If a future
change would make it feed triage, that is a scope change requiring an owner ruling, not a patch.

## Claim ceiling

Every evaluation carries `claim_ceiling` (workroom `CHH-002`, `ACTIVE`):

> encoded domain capacity only — not enzyme activity, expression, chitin utilization, antifungal
> phenotype, ecological adaptation, novelty, or BGC causality

Any rendering of an evaluation (report, table, figure caption) must show this text. Genome
capacity is not activity, is not expression, is not a phenotype, and is not a BGC-causal claim.

## Inputs

### 1. CGAD scan output

The CGAD chitin/glycan scan already runs inside every gold-mode Mamey pipeline
(`mamey/source_scans.py` → `CHITINASE_PATTERNS` = `GH18`, `GH19`, `AA10_LPMO`, `CBM_CHITIN`,
`GlcNAc`) and its counts land in a sealed package's `manifest.json` at
`source_scans.chitinase.counts` — the same field `mamey/cli.py` itself reads to derive
`cgad_active` for the lead-tier gate. `tools/chitin_reference_eval.py --package <dir>` reads this
by default; `--cgad-json <path>` accepts any JSON file/object with a `counts` dict directly
(useful for a strain evaluated outside a full package, or for testing).

### 2. Reference registry (operator-supplied, never redistributed)

A TSV with (at minimum) `reference_id`, `taxon` (or `genus`), `source_path`, `source_sha256`, and
optionally `ani_pct`, `aligned_fragment_fraction`, `chitin_domains_total`. **This module never
reads, copies, or redistributes the reference sequence itself** — a reference is identified only
by its declared path and SHA-256. ANI/identity values are accepted as already-computed registry
columns (run by the operator, e.g. via `fastANI`, outside this module) rather than executed as a
subprocess here — that separation is deliberate, matching the "reference by path and hash, never
redistribute" instruction this module was built under. `mamey.chitin_reference_eval.
verify_reference_hash(path, declared_sha256)` is available for an operator to spot-check a
registry row's declared hash against the live file when the path resolves locally; it returns
`None` (never a false pass) when the path can't be checked.

A registry row with **no `ani_pct`** types `NOT_SCORED` — never dropped silently, never treated as
zero similarity.

## Output vocabulary (kept from the source workroom)

**Architecture-profile states** (per-strain capacity, from CGAD's 5-family counts; `GlcNAc` is
context and excluded from the reported `domains_total`, mirroring the workroom's GH16/GH3/NagB
context exclusion):

| State | Condition |
|---|---|
| `MULTI_ARM_CHITIN_CAPACITY` | GH18/19 (endo) **and** CBM_CHITIN **and** AA10_LPMO all present |
| `PARTIAL_COORDINATED_CHITIN_CAPACITY` | endo **and** one of CBM_CHITIN/AA10_LPMO |
| `CHITINASE_FAMILY_CAPACITY_WITHOUT_SUPPORTING_ARMS` | endo present, no CBM/LPMO support |
| `NON_ENDOCHITINASE_CHITIN_CONTEXT` | no endo, core total > 2 |
| `MINIMAL_MEASURED_CHITIN_DOMAIN_CAPACITY` | no endo, core total ≤ 2 (and > 0, or GlcNAc alone) |
| `ABSENT_NO_MEASURED_CHITIN_DOMAINS` | core total = 0 **and** GlcNAc = 0 |

**Reference-quality states** (per-strain, from its taxon-matched reference panel; thresholds
unchanged from the workroom's `reference_quality()`):

| State | Condition |
|---|---|
| `NO_TAXON_MATCHED_REFERENCE_PANEL` | registry has no row for this taxon (or its aliases) |
| `TAXON_MATCHED_PANEL_BUT_NO_ANI_AT_MIN_FRACTION` | panel exists, no row has `ani_pct` |
| `SPECIES_LEVEL_SIMILARITY_CANDIDATE_NOT_TAXONOMIC_CONFIRMATION` | top ANI ≥ 95%, aligned fraction ≥ 0.5 |
| `HIGHER_SIMILARITY_NONSPECIES_REFERENCE_CONTEXT` | top ANI ≥ 90%, aligned fraction ≥ 0.5 |
| `DISTANT_AVAILABLE_TAXON_MATCHED_REFERENCE_CONTEXT` | panel scored, below both thresholds |

Note the name: `SPECIES_LEVEL_SIMILARITY_CANDIDATE_NOT_TAXONOMIC_CONFIRMATION` — a high ANI hit is
a **candidate**, never asserted as a taxonomic confirmation on its own.

**Per-reference row states:** `RETURNED_ABOVE_MIN_ALIGNED_FRACTION`,
`NO_OUTPUT_AT_MIN_ALIGNED_FRACTION`, `NOT_SCORED`.

## Operator usage

```bash
# From a sealed package's manifest.json
python3 tools/chitin_reference_eval.py \
    --package ./runs/<strain>/package --registry my_reference_registry.tsv

# From a standalone CGAD counts JSON (e.g. testing, or a strain without a full package)
python3 tools/chitin_reference_eval.py \
    --cgad-json cgad_counts.json --registry my_reference_registry.tsv \
    --strain-id <id> --taxon <genus>

# TSV row instead of the JSON receipt; also write both to disk
python3 tools/chitin_reference_eval.py \
    --package ./runs/<strain>/package --registry my_reference_registry.tsv \
    --format tsv --out-json out.json --out-tsv out.tsv
```

`stdout` is the deliverable (JSON receipt by default, or a TSV row with `--format tsv`). A typed
refusal (bad input, unreadable package, malformed registry, missing CGAD scan) is written to
`stderr` and exits non-zero — the two streams are never mixed, but stdout is emitted before optional disk outputs are written. A later output error can leave stdout populated and partial disk outputs; successful stdout is not proof that all files were published.

## What this module deliberately does not do

- It does not run `fastANI` (or any subprocess) itself — ANI values are registry input, not
  computed here, so the bundle never needs network/DB access to produce an evaluation and never
  needs to redistribute reference genomes.
- It does not touch triage, scoring, or any `TriageRecord` — per CHD-002 above.
- It does not render a Markdown report — this cut ships the typed data and receipt only, matching
  the source workroom's own `"Rendering:" not run.` state; a rendering pass is a separate,
  additive piece of work.

## Provenance

Vocabulary, thresholds, and claim-ceiling text are carried over from the source workroom's
the Codex workroom script `build_per_strain_chitin_evaluations` (2026-08-21; `architecture()`, `reference_quality()`) rather
than reinvented. See that workroom's `PER_STRAIN_CHITIN_EVALUATION_INDEX__2026-08-21.md` and
`SAVE_STATE.md` for the original 46-strain / 81-reference evidence run this module generalises.

## Current validation and reference-selection limits

Package mode reads manifest fields but does not verify sealing, scan coverage, whole-genome completeness or source hashes (`tools/chitin_reference_eval.py:52–96,140–173`). An all-zero/empty count dictionary can yield `ABSENT_NO_MEASURED_CHITIN_DOMAINS` because missing known family keys become zero. Values are `int()`-coerced (including truncatable floats and booleans); unknown family keys are ignored. Admit a complete, source-bound scan independently before interpreting an “absent” or “measured” label (`mamey/chitin_reference_eval.py:161–203`). The five-family total is saved annotation capacity, not a protein/gene count or biochemical measurement.

Registry matching is exact and case-sensitive on taxon/genus or supplied aliases. No taxonomy resolver, duplicate-reference rejection, required source-path/hash validation or hash verification runs automatically. Missing reference identity/path/hash fields become `NR`; declared hashes simply pass through. `verify_reference_hash` is an optional separate file reader, returning `None` when uncheckable; its result is not called or included by the evaluator. Do not infer verified reference bytes from a reference-panel row. Retain the registry's own hash and the separately checked source hashes in the owner record (`:224–253,294–313`).

Optional numeric ANI/aligned-fraction values are parsed without finite/range checks. Reject nonfinite/out-of-range ANI/fractions upstream. Row state uses aligned fraction **0.2**, while the high-quality thresholds use **0.5**. Quality and `top_reference` select the **maximum ANI among all scored rows**, not the best row that passes 0.5. A highest-ANI row below the fraction cutoff can therefore prevent a high-quality state even where another row qualifies. `DISTANT_AVAILABLE_TAXON_MATCHED_REFERENCE_CONTEXT` can reflect inadequate/missing fraction rather than biologically distant ANI. Preserve the full panel and separate reason; these state names do not establish taxonomy (`:206–269,283–290`).

The emitted evaluation is typed data, not an independently hash-bound receipt: it does not hash the source counts/manifest, registry, code, parameters, outputs or itself. Optional JSON/TSV files are each written through atomic helpers after stdout; the pair is not one transaction and can replace existing destinations. Normal typed refusals return1; numeric parsing and output errors outside those catch classes can raise exceptions. Use unused external destinations, verify process status and every expected file, retain partial attempts, and record actual input/output/code hashes separately. Use the original decision and run receipts for historical workroom decisions and 46-strain/81-reference counts; keep current scientific adoption separately recorded.

This remains a strain/whole-genome context lane. If any separate report mentions a BGC, retain strain / full node-or-contig / region / BGC alias; no chitin state assigns causality to that locus. Typed bioactivity examples are shape fixtures, not measured evidence: see [the metadata validator boundary](BIOACTIVITY_METADATA_CONTRACT.md).
