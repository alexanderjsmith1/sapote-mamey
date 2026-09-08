# Scanner Run Recipe — first worked example (staged; awaiting fasta)

**Item 4.** Runs the v0.5 scanner set on one real strain to produce its AB/AF capacity
profile — the first worked example for the thesis-atlas scoring bridge. Blocked only on
input: a proteome (`.faa`) or genome/antiSMASH output for one cohort strain (e.g. AS-XXX).

## Inputs needed (from the Developer or User)
- One strain proteome `AS-XXX.faa` (preferred) OR its antiSMASH `.gbk`/region output.

## Procedure
1. Place the proteome in `Wheelhouse/reports/inputs/`.
2. Build/scan with the engine:
   `python Wheelhouse/engine/pyhmmer_scanner_engine.py --proteome <faa> --registry Wheelhouse/scanners/scanner_registry_v0.5.json --hmm Wheelhouse/hmm/scanner_pfam.hmm`
   (requires `pyhmmer` + `pyfamsa`).
3. For each scanner: record gate fired (yes/no), supporting domains, cluster/region.
4. Emit an AB-axis and AF-axis capacity profile per the thesis-atlas
   `scoring/SCANNER_SCORING_BRIDGE.md` — confidence-weighted by each scanner's
   `test_status` (PASS full weight; TIGHTEN/REVIEW reduced; UNTESTED/NEW flagged).

## Claim-safety
Output is capacity prioritization, not activity prediction. A fired scanner = "capacity
consistent with class X"; never "produces X" or "active against Y". Bioactivity stays
extract-level.
