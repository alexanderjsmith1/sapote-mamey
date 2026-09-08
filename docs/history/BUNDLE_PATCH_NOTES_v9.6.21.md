# BUNDLE PATCH NOTES — Sapote–Mamey v9.6.21

> **Status (this build):** ALL items below are applied to **all four tiers**
> (MERGED-PRIVATE-scaffold, CODE, CODE-analysis-free, SID-public) and to the
> root-level validator copy. Items 6 (root copy) and 7 (ijson dedup), previously
> "hand-apply / left as-is," are now **done**. The `test_master.xlsx` swap was
> applied to every tier that ships it (MERGED, CODE, SID-public; analysis-free has
> none). See the **Verification** appendix at the end for the gold-mode run on real
> strains.


Changes applied in this pass, each verified in a Python 3.12 container. Use this to
apply the same edits to your working bundle by hand, or drop in the patched files
directly. Everything below was confirmed to compile and run; the master-generation
pipeline and schema validator both pass after the changes.

Applies to: the **MERGED-PRIVATE-scaffold** tier (the canonical/full tier). Where a
change also affects the other three tiers (CODE, CODE-analysis-free, SID-public), it's
called out under **Other tiers**.

---

## 1. Validator no longer crashes as a bare script  ★ (your main ask)

**File:** `mamey/workbook_schema_check.py` (≈ line 113)

**Problem:** the module did a package-relative import:

```python
from .master_workbook import CANONICAL_V1_HEADERS as _BUILDER_HEADERS
```

This works under `python -m mamey.workbook_schema_check`, but the file's own docstring
documents bare-script usage (`python workbook_schema_check.py <wb.xlsx>`), and as a bare
script the relative import throws `ImportError: attempted relative import with no known
parent package`. `master_workbook.py` itself uses intra-package relative imports
(`mamey.models`, `mamey.assembly`, …), so it must be imported **as** `mamey.master_workbook`,
not as a standalone module.

**Fix:** try the package-relative import first; on failure, locate the directory that
contains the `mamey/` package, put it on `sys.path`, and import via the package path so
the inner relative imports resolve. Replace the single import line with:

```python
try:
    from .master_workbook import CANONICAL_V1_HEADERS as _BUILDER_HEADERS
except ImportError:
    import os as _os
    _here = _os.path.dirname(_os.path.abspath(__file__))
    # mamey/ copy run as a script: pkg root is the parent of this file's dir.
    # root-level copy run as a script: pkg root is this file's dir.
    for _root in (_os.path.dirname(_here), _here):
        if _os.path.exists(_os.path.join(_root, "mamey", "master_workbook.py")):
            if _root not in sys.path:
                sys.path.insert(0, _root)
            break
    from mamey.master_workbook import CANONICAL_V1_HEADERS as _BUILDER_HEADERS
```

(`sys` is already imported at the top of the file.)

**Verified — all three invocation modes return `status: PASS`:**
- `python3 mamey/workbook_schema_check.py <wb.xlsx>`  ← used to crash
- `python3 -m mamey.workbook_schema_check <wb.xlsx>`
- bare script invoked from an unrelated working directory

**Other tiers:** apply the identical edit to each tier's `mamey/workbook_schema_check.py`.
The branch that probes `_here` (rather than its parent) is what makes the same code also
work for a **root-level** copy of the validator — see item 6.

---

## 2. `requirements.txt` — declare matplotlib + numpy; retire reportlab

**File:** `requirements.txt`

- **Added `matplotlib>=3.7,<4.0`** and **`numpy>=1.24`**. matplotlib is imported by 11
  figure tools and numpy directly by 2; both were undeclared, so any figure run died
  with `ModuleNotFoundError`. Imports are hard (no fallback), so these belong in the
  install set whenever figures are produced.
- **Commented out `reportlab`** with a note. It was declared but is **not imported
  anywhere** in the codebase (the PDF path uses pandoc + xelatex via `md_to_pdf.sh`).
  Left as a comment so it's reversible — re-enable if you reintroduce reportlab output.
- Kept `openpyxl` and `ijson` as core; kept the optional `biopython` note.

## 3. `pyproject.toml` — figures/all extras; reportlab out of core

**File:** `pyproject.toml`

- Removed `reportlab` from `[project].dependencies` (unused — see above).
- Added optional-dependency extras:
  - `figures = ["matplotlib>=3.7,<4.0", "numpy>=1.24"]`
  - `all = ["matplotlib…", "numpy…", "biopython>=1.83,<2.0"]`
- Kept existing `bio` and `json` extras.

Now `pip install '.[figures]'`, `'.[bio]'`, or `'.[all]'` all resolve. TOML verified to
parse.

> **Decision needed from you:** reportlab is currently removed from the install set
> because nothing imports it. If that's wrong (e.g. a planned/out-of-tree consumer),
> un-comment it in `requirements.txt` and re-add it to `pyproject.toml` core deps.

---

## 4. Regenerated `test_master.xlsx` — current coded schema, de-identified  ★

**File:** `examples/test_data/test_master.xlsx`

**Was:** the legacy **descriptive** schema (15 sheets: Dashboard / Strain_Registry /
BGC_Master / SYN1_*) carrying real unpublished strain data — your Tier-0 Gate-B blocker.
It would also (correctly) **fail** the current validator, since the validator checks the
coded A1–H3 contract.

**Now:** regenerated through the canonical writer (`mamey run --master …` →
`master_workbook.update_master_workbook`) on two synthetic placeholder strains:

| strain | taxonomy | source |
|---|---|---|
| `DEMO_A` | `Streptomyces sp. (placeholder)` | `placeholder-habitat` |
| `DEMO_B` | `Amycolatopsis sp. (placeholder)` | `placeholder-habitat` |

**Verified:** 25-sheet coded schema (A1_Dashboard … H3_Schema_Version); validator
returns `status: PASS`, `column_errors: 0`, `strain_count: 2`; a scan for `SID####` /
`AS-###` identifier tokens returns **none**. The fixture now matches exactly what the
pipeline emits today.

> This aligns with your Gate-B "Option A" disposition (remove real data + add a
> placeholder). Confirm the placeholder content is what you want shipped, then this item
> can be checked off the blocker list. Reminder from earlier in our work: the old
> `test_master.xlsx` also still appears in the **SID-public** tier — replace it there too.

---

## 5. Narrowed a bare `except:`  (minor, safe)

**File:** `tools/export_figure_ready.py` (≈ line 37, the inner `num()` helper)

```python
# before
try: return float(x)
except: return None
# after
try: return float(x)
except (TypeError, ValueError): return None
```

Bare `except:` swallowed `KeyboardInterrupt`/`SystemExit`; the narrowed form catches only
the conversion errors actually expected here. Behavior otherwise unchanged.

---

## 6. Reconcile the duplicate root-level validator  (do-by-hand note)

There are **two** copies of the validator: `mamey/workbook_schema_check.py` (canonical)
and a convenience copy at the **bundle root**, next to the tier zips. They are currently
byte-identical. The item-1 fix is written to work for **both** locations (the loop probes
both `_here` and its parent), so:

- **Done this build:** the root-level copy was replaced with the patched `mamey/`
  version. The item-1 fix probes both `_here` and its parent, so the same code works
  whether the validator runs from `mamey/` or from the bundle root.

---

## 7. ijson import consolidated (APPLIED)

**File:** `mamey/antismash_evidence.py`

There were two `try/except` import blocks, both setting `_HAVE_IJSON`. They were **not**
fully redundant: the first bound `_ijson` (used by `_iter_records`, the
`MAMEY_STREAM_JSON` opt-in path) and the second bound bare `ijson` (used at the
`_stream_kcb_riq` bounded-mode call, `ijson.parse(raw)`). Deleting either block would have
left one of those names unbound.

**Fix:** consolidated to a single import block near the top of the module that binds **both**
names and degrades safely when ijson is absent:

```python
try:
    import ijson
    _ijson = ijson
    _HAVE_IJSON = True
except Exception:
    ijson = None
    _ijson = None
    _HAVE_IJSON = False
```

The second block was replaced with a one-line pointer comment. Both call sites already
guard on `_HAVE_IJSON`, so `ijson = None` / `_ijson = None` in the failure path is safe.
Verified: module compiles and imports; with ijson absent (this container) `_HAVE_IJSON` is
`False` and both names are `None` (correct graceful-degradation state).

---

## Files changed in this pass

```
mamey/workbook_schema_check.py        # item 1  (validator dual-mode import)
mamey/antismash_evidence.py           # item 7  (ijson import consolidated)
requirements.txt                      # item 2
pyproject.toml                        # item 3
examples/test_data/test_master.xlsx   # item 4  (regenerated, de-identified)
tools/export_figure_ready.py          # item 5
workbook_schema_check.py (root copy)  # item 6  (replaced with patched version)
PREREQUISITES.md                      # new — install/runtime guide
BUNDLE_PATCH_NOTES_v9.6.21.md         # new — this file
```

## Apply-to-all-tiers checklist — ALL DONE this build

- [x] item 1 → each tier's `mamey/workbook_schema_check.py` (4 tiers)
- [x] item 1 → root-level `workbook_schema_check.py` — item 6
- [x] items 2–3 → `requirements.txt` + `pyproject.toml` in each tier
- [x] item 4 → `test_master.xlsx` in MERGED, CODE, SID-public (analysis-free has none)
- [x] item 5 → `tools/export_figure_ready.py` in each tier
- [x] item 7 → ijson dedup in each tier's `mamey/antismash_evidence.py`
- [x] `PREREQUISITES.md` added to each tier root

---

## Verification — gold mode on real strains (this build)

Ran the patched engine end-to-end on two real antiSMASH 8 genomes, chained into one master:

| strain | regions | raw / corrected BGCs | assembly | status | time |
|---|---|---|---|---|---|
| AS-XXX | 51 | 51 / 27.0 | POOR | MAMEY_COMPLETE | ~24 s |
| AS-XXX | 64 | 64 / 23.5 | VERY_POOR | MAMEY_COMPLETE | ~18 s |

- Combined master validated: `status: PASS`, 25 sheets, 2 strains, 0 column errors,
  0 consistency errors. Dashboard: 2 strains, 115 total BGC records (51 + 64).
- Evidence-conservation paths fired: TIGRFAM diagnostics merged (AS-XXX: 2, AS-XXX: 6),
  GBK Pfam tier-1 hits (AS-XXX: 20, AS-XXX: 38).
- Gold-mode receipt: every BGC assigned to the full-Mode-B depth floor
  (`full_mode_b: 64/64` for AS-XXX), `gold_completeness: JUDGMENT_PENDING` — extraction
  complete, manifest handoff ready for the Sapote (Mamey v1.2) judgment layer to write the
  Mode B cards.
- Handoff `manifest.json` produced with the full key set (top_bgc_targets,
  split_pathway_candidates, resistance_gene_summary, wet_lab_priorities,
  metabolomics_targets, cross_strain_context, hallucination_traps_triggered, …).

Conclusion: extraction, master generation, multi-strain chaining, schema validation
(bare-script + module) and the Sapote handoff all function on v1.9.12 after the patches.
