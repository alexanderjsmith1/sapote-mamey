# Sapote Workflow Contract — the mandatory set format

**Version:** v9.7.319
**Executable form:** `tools/sapote_workflow.py` (the driver/gate)
**Analogue:** this is to Sapote what `mamey run` (fixed phase order) + `mamey validate`
(hard seal gate) are to Mamey. Mamey enforces its set format in engine code; Sapote's set
format was, until now, prose spread across `FULL_RUN_PROFILE.md` §A, the execution slice,
and the deliverable contract, with a fleet of individually-callable gates and **no single
ordered driver**. This contract names the canonical ordered steps; the driver enforces them.

---

## Why a contract, not just a checklist

Sapote already ships every *gate* it needs (`mamey validate`, `verify-modeb`,
`verify-guide`, `compile-report --strict`, `check_deliverable_suite.py`,
`sapote_judgment_receipt.py`, `session_checklist.py`). What was missing is the property
Mamey gets for free from being code: **order enforcement** — a downstream step must not be
reported done while a mandatory upstream step is incomplete. The driver supplies exactly
that: it reads the *real* package artifacts, marks each step PASS / PENDING / BLOCKED / N/A
with a receipt, blocks any step whose mandatory predecessor is not PASS, writes a ledger,
and (`--strict`) exits non-zero if any mandatory step is incomplete.

The step list below is derived from `FULL_RUN_PROFILE.md` Section A (the 13-item delivery
order) collapsed onto the artifacts and gates that actually exist in a sealed package.

---

## The set format (canonical step order)

| Step | Stage | Req | Verified by | Real artifact / gate |
|---|---|:--:|---|---|
| **W0** | Sealed Mamey package | M | `mamey validate <pkg>` | `manifest.json` + `gate_validation.json` (`MAMEY_COMPLETE`) + `checksums_sha256.txt` |
| **W1** | First-pass scans + triage board | M | file present | `<ID>_4_triage_board.csv` (+ `source_scans` in manifest / `tools/build_first_pass_scans.py`) |
| **W2** | Lead boards / DAPR (AB + AF) | M | files present | `<ID>_4c_AB_lead_board.csv`, `<ID>_4c_AF_lead_board.csv` (`tools/lead_board.py`, `apply_dapr_boards.py`) |
| **W3** | Mode B §1–§30 templates emitted | M | dir populated | `mode_b_templates/*BGC*.md` via `mamey emit-modeb-template --batch` |
| **W4** | Mode B cards authored **and** verified | M | register + gate | `<ID>_judgment_register.json` COMPLETE entries; each card passes `mamey verify-modeb`; persisted by `ingest-receipts` |
| **W5** | BGC Guide(s) authored + verified | cond | `verify-guide` | `<BGC>_Guide.md` with no residual `<!-- LAY: -->` slots (`mamey guide` → `verify-guide`) |
| **W6** | Narrative set (lay guide / ecology / ferm) | M | files present | Layperson Guide + Ecological Synthesis + Fermentation Card (`DELIVERABLE_CONTRACT` A2) |
| **W7** | Compiled report (readiness gate) | M | strict compile | `<ID>_compiled_report.md`, zero open slots (`mamey compile-report --strict`) |
| **W8** | 13-item deliverable suite contract | M | suite gate | filled `DELIVERABLE_MANIFEST_<ID>.md` → `tools/check_deliverable_suite.py` rc=0 |
| **W9** | Judgment receipt | M | receipt gate | manifest no longer carries `JUDGMENT_PENDING` (`tools/sapote_judgment_receipt.py`) |
| **W10** | Session close + exactly-8 next-paths | M | behavioral | `tools/session_checklist.py` + exactly 8 numbered next-paths |

**Req:** M = mandatory (blocks downstream and fails `--strict`); cond = conditional
(fires when the predicate holds — e.g. W5 only when a Guide is requested — and never blocks).

### Conditional-section note (inside W4)
W4's per-card structure is the canonical **§1–§30 Mode B contract**
(`modeb_corrective_full30_v1`): §1–§20 + §28 + §30 always required; §21–§27/§29 fire on
predicate (RiPP, MATURATION_GAP, novel/no-MIBiG, isolation-worthy, fermentation-selected,
antimicrobial-candidate, >3 HIGH-tier BGCs). The driver does not re-adjudicate section
predicates — `verify-modeb` owns that. W4 PASS means the register shows COMPLETE cards; the
depth/structure of each card is confirmed by `verify-modeb`, which W4's receipt points to.

---

## Order-enforcement semantics

- A **mandatory** step is `BLOCKED` when its declared predecessor is not `PASS`.
- A **conditional** step that is not applicable is `N/A` and does **not** block its successors.
- `--strict` exits `1` if any mandatory step is not `PASS`; the ledger's "next mandatory
  step" line names the single next action and the exact command to run.
- The driver never *runs* authoring for you and never invents artifacts — it only reads what
  is on disk and shells out to the real gates. Fail-closed: a missing artifact is PENDING,
  never silently PASS.

---

## How to run

```bash
# status ledger (writes <ID>_SAPOTE_WORKFLOW_LEDGER.md into the package)
python tools/sapote_workflow.py --package runs_<date>/<ID>/package

# with a separate deliverables dir, JSON, and hard gate for CI / release:
python tools/sapote_workflow.py --package <pkg> --deliverables <dir> --strict --json
```

The ledger is the Sapote-tier analogue of the Mamey seal: a per-strain, receipt-backed
record of exactly where the judgment layer stands and what the next mandatory action is.

---

## Relationship to existing docs (nothing is superseded)

- `FULL_RUN_PROFILE.md` §A — the prose source of the delivery order. This contract is its
  enforced form; the profile still governs per-BGC Mode B card structure and batching.
- `docs/CHATGPT_EXECUTION_SLICE_v97147.md` — the default execution controller; §0 authority
  order still wins on any conflict. The driver implements, it does not override.
- `docs/DELIVERABLE_CONTRACT.md` — Part A/B item definitions that W6/W8 check against.
- `tools/session_checklist.py` — W10's close artifact (data-loss advisory + menu).
