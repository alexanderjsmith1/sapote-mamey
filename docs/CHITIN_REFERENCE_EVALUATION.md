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
Tools/bin/python3 tools/chitin_reference_eval.py \
    --package ./runs/<strain>/package --registry my_reference_registry.tsv

# From a standalone CGAD counts JSON (e.g. testing, or a strain without a full package)
Tools/bin/python3 tools/chitin_reference_eval.py \
    --cgad-json cgad_counts.json --registry my_reference_registry.tsv \
    --strain-id <id> --taxon <genus>

# TSV row instead of the JSON receipt; also write both to disk
Tools/bin/python3 tools/chitin_reference_eval.py \
    --package ./runs/<strain>/package --registry my_reference_registry.tsv \
    --format tsv --out-json out.json --out-tsv out.tsv
```

`stdout` is the deliverable (JSON receipt by default, or a TSV row with `--format tsv`). A typed
refusal (bad input, unreadable package, malformed registry, missing CGAD scan) is written to
`stderr` and exits non-zero — the two streams are never mixed, so a caller can always trust that
anything on `stdout` is a real receipt.

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
