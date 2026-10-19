# RiPPER adapter: supported actions

Use `python tools/ripper_adapter.py --help` to list commands. Choose a compatible
Python environment and absolute input paths. Every output directory must be new
and outside the bundle source tree; existing inputs and results are retained.


For a new local runtime, follow [explicit runtime preparation](RIPPER_NATIVE_DISCOVERY.md#prepare-an-explicit-local-runtime-before-native-preflight).
Select compatible existing Python, Perl/modules, BLAST and reviewed Prodigal-short
files before preflight; keep new provisioning separate from byte binding. The
recorded native run used mixed system/private files, not a portable self-contained
installer. Python SQLite snapshot support, execution-time psutil capability,
config whitespace restrictions and exact executable budgets are part of setup.

| Need | Supported command and required evidence | Result |
|---|---|---|
| Prepare inputs | `plan` or `local-plan --semantic-validation` with the query roster, GenBank, query FASTA, config and source profile | Input plan; no upstream execution |
| Bind an adapted source | `adapted-profile` with exact original source, cumulative patch, adapted source and source-owner receipt | Distinct hash-bound profile; does not silently accept changed source bytes |
| Check a native setup | `lifecycle` with a native spec, explicit `--file ROLE=PATH` bindings and adapted profile | Preflight plus concrete review request; default launches nothing |
| Run native discovery | `lifecycle --execute-native --native-admission …`; add `--resume-preflight` only for its matching pristine preflight | Supervised native discovery with execution and terminal receipts |
| Inspect a completed native result | `native-result --terminal … --raw … --out …`; legacy publication also needs explicit `--control-result …` | Hash-bound raw-result summary; preserves raw status and missing annotation/coordinate evidence |
| Import a separately annotated table | `import` with matching complete receipt, query coverage, raw TSV, columns, config, log and selected output profile/channel | Declared imported-table evidence; not BGC attribution |
| Evaluate native reconstructed coordinates | `native-coordinates` with a native reconstruction packet, explicit 18-role artifact roster and legacy control receipt if needed | Native-qualified row/window/score/translation assessments; instrumented producer and BGC evidence remain separate |
| Evaluate declared coordinates | `bind-coordinates` with the supported evidence schema, local input plan, original GenBank, query FASTA and bound mapping | Coordinate/sequence consistency assessments, including mismatch or ambiguity |

A native discovery run has completed on one fabricated 6000-nt record and 150-aa
bait: exit 0, 78 raw candidates, `SUCCESS_UNBOUND`. This is a functioning opt-in
entry point. That recorded run's single-run authorization is consumed; inspecting
it does not launch a retry. A new run needs its own current, matching admission.
See [CLI examples and Methods wording](RIPPER_CLI_METHODS.md).

Use the recorded state to choose the next action:

- `HOLD`, `FAILED`, `INTERRUPTED`, `AMBIGUOUS` or unrun evidence: retain the
  state and logs; do not attach stale raw rows or turn a null count into zero.
- `SUCCESS_UNBOUND`: raw candidates were retained. Inspect exact terminal/raw
  bindings; retain `HMM=NOT_RUN_SEPARATE_STAGE` and unverified BGC membership.
- `NO_HIT` versus `NO_RETAINED_CANDIDATES`: preserve the distinction between
  no tailoring-enzyme hit and a tailoring-enzyme match with no retained rows.
  Neither establishes biological absence.
- Missing or ambiguous peptide coordinates: obtain the original record, window,
  source-stage and row identity evidence. A sequence match alone does not identify
  a producer row or establish BGC membership. Preserve alternate locations.
- HMM annotation not run: retain the raw result. Obtain independently bound HMM
  model/index, annotation-stage and postprocessing evidence before importing an
  annotated table; an empty discovery summary is not such a table.
- File/profile mismatch: select matching historical inputs or bind a new source
  or run without relabelling or overwriting prior evidence.
- Missing Biopython: select a compatible installed environment for strict
  GenBank validation. Text-only planning remains available and explicitly held.

Small JSON/text inputs use a 5 MiB cap. Executable and model roles have separate
explicit streaming budgets; the text cap does not imply that a larger installed
BLAST or Prodigal binary is missing. Receipts are content-bound declarations, not
authenticated identities. Supported discovery does not itself produce HMM calls,
precursor validation, coordinate-producer attestation or canonical BGC evidence.
