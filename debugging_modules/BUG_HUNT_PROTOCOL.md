# Bug Hunt Protocol — Sapote–Mamey

**Companion to:** Bunny Hop (per-file adversarial audit)
**Scope:** Codebase-wide systematic bug sweep

---

## What is Bug Hunt?

A pattern-driven sweep of the entire codebase looking for concrete, reproducible bugs.
Unlike the Bunny Hop (which audits files one at a time through Inspector/Defender
dialogue), Bug Hunt works across the whole tree using grep sweeps, diff analysis,
dead-code detection, and targeted reads of high-risk functions.

**The output is a prioritized patch card with supported findings, proposed fixes and explicitly scoped verification.** A finding is not a verified fix until the candidate and relevant checks exist.

| | Bunny Hop | Bug Hunt |
|---|---|---|
| Unit | One file at a time | Whole codebase |
| Method | Adversarial (Inspector vs Defender) | Pattern sweep + targeted reads |
| Finds | Design issues, claim-safety gaps, completeness | Crash bugs, data loss, dead code, leaks |
| Output | Per-file verdicts + patch card | Categorized bug list + verified fixes |

---

## How to Run a Session

### Setup

1. Record exact baseline tree/tier, bundle and engine versions, selected scope, source file hashes and current user authorization. Reuse source evidence in place; isolate only files being modified. Read generated-file owners and the selected privacy profile.
2. Inspect dependencies and [test guidance](../tests/README.md). Installing wheels or running network/heavy jobs is a separate action, not a prerequisite for reading code.
3. Where a test baseline is needed and authorized, record the exact command, environment, selected test paths/markers and results. Existing failures do not prevent read-only auditing: identify them and distinguish pre-existing from candidate regressions.
4. Default pytest skips explicitly marked slow/network tests. `--run-slow --run-network` includes those partitions but is not by itself permission to use network or run costly jobs. `pyproject.toml` collects `tests`, `tools` and `deliverable_tools`; a narrower command proves a narrower scope. `tests/conftest.py` overrides `MAMEY_OFFICIAL_DATA` and `MAMEY_DATA_ROOT` with fixtures, so a test pass is not validation of the operator's real registry. External-reference absence may cause skips.

### Phase 1 — Automated Sweeps (bounded by the session scope)

Run every grep pattern in the **Pattern Library** below. For each hit, classify as:

- **BUG** — will crash, lose data, or produce wrong output under reachable conditions
- **LEAK** — file-handle, resource, or evidence leak; won't crash but degrades
- **SMELL** — style issue, inconsistency, or maintenance hazard; no runtime effect
- **FALSE POSITIVE** — pattern matched but the code is correct

Record hit counts per pattern. Don't fix anything yet — just inventory.

### Phase 2 — Targeted Reads (bounded by the session scope)

1. **Largest functions** — any function >200 lines
2. **New/changed files** — diff against the previous version
3. **Wiring check** — verify every new module is actually imported and called
4. **Operator precedence** — any `if A and B if C else D` pattern

### Phase 3 — Propose, fix and verify

For each supported high-priority finding, read the reachable caller and consumer, describe a concrete trigger and impact, and prepare a minimal candidate correction if authorized. Preserve the original source. Run meaningful checks for the changed behavior and required repository gates; coherent fixes may be checked together when the result remains attributable. Record unrun checks and failures. Do not invent findings to fill a panel, run a whole suite after every prose edit, or claim a regression-free release from a narrow test count.

### Phase 4 — Report

Write the Bug Hunt report using the output format below.

---

## Pattern Library

These historical grep recipes are triage aids. Prefer `rg` for current searches; record the actual query, paths and exclusions. They can miss multiline forms, aliases, dynamic imports, methods and nested definitions, and can match comments or harmless uses. S4 only searches `mamey`; D1 inspects three named modules; D2 only matches column-zero `def` lines. None is an exhaustive AST/call-graph analysis. Follow each hit to source and consumer before classifying it. A missing match is not proof of absence.

The privacy query below locates candidate identifiers only. A strain prefix and the historical numeric exclusions do not establish public/private status; assess the current user-selected profile and source metadata. The sweep does not prove public-tier contents.

### Data Safety

```bash
# S1: Bare json.dump into open() — file-handle leak + non-atomic write
grep -rn "json\.dump(.*open(" mamey/ tools/ --include="*.py" | grep -v __pycache__ | grep -v "with "

# S2: Bare json.load from open() — file-handle leak
grep -rn "json\.load(.*open(" mamey/ tools/ --include="*.py" | grep -v __pycache__ | grep -v "with "

# S3: Bare .open().write() — file-handle leak
grep -rn "\.open(.*\.write(" mamey/ tools/ --include="*.py" | grep -v __pycache__ | grep -v "with "

# S4: write_text() without encoding= (platform-dependent encoding)
grep -rn "write_text(" mamey/ --include="*.py" | grep -v __pycache__ | grep -v "encoding="
```

### Exception Handling

```bash
# E1: except ... : pass (silent swallow)
grep -rn "except.*:" mamey/ tools/ --include="*.py" | grep -v __pycache__ | grep "pass$" | grep -v "# "

# E2: Bare except: (catches SystemExit, KeyboardInterrupt)
grep -rn "except:$" mamey/ tools/ --include="*.py" | grep -v __pycache__
```

### Claim Safety

```bash
# C1: Raw kcb_top without safe rendering
grep -rn "kcb_top" mamey/ tools/ --include="*.py" | grep -v __pycache__ | \
  grep -v "closest_candidate\|safe_kcb\|test_\|#\|_safe\|render_safe\|display"

# C2: Product-identity language ("produces", "synthesizes")
grep -rn "produces\|synthesizes\|generates\|makes" mamey/ tools/ docs/ --include="*.py" --include="*.md" | \
  grep -v __pycache__ | grep -v "#\|test_\|changelog\|README"
```

### Logic Bugs

```bash
# L1: Operator precedence — ternary inside boolean
grep -rn "and.*if.*else" mamey/ tools/ --include="*.py" | grep -v __pycache__ | grep -v "#\|lambda"

# L2: Mutable default arguments
grep -rn "def .*=\[\]\|def .*={}" mamey/ tools/ --include="*.py" | grep -v __pycache__ | grep -v "field("
```

### Dead Code and Wiring

```bash
# D1: New modules not imported anywhere
for mod in mamey/architecture_first.py mamey/nominal_length.py mamey/mode_b_quality_gate.py; do
  base=$(basename "$mod" .py)
  echo "=== $base ==="
  grep -rn "import.*$base\|from.*$base" mamey/ tools/ --include="*.py" | \
    grep -v __pycache__ | grep -v "$base.py"
done

# D2: Duplicate function definitions
python3 -c "
import re, collections
from pathlib import Path
for py in sorted(Path('mamey').rglob('*.py')):
    if '__pycache__' in str(py): continue
    funcs = re.findall(r'^def (\w+)\(', py.read_text(), re.MULTILINE)
    dups = [f for f, c in collections.Counter(funcs).items() if c > 1]
    if dups: print(f'  {py}: DUPLICATE defs: {dups}')
"
```

### Historical identifier search — disclosure triage

```bash
# LP1: Candidate AS identifiers; classify under the selected privacy profile
grep -rn "AS-[0-9]\{3\}" mamey/ tools/ --include="*.py" | grep -v __pycache__ | \
  grep -v "test_\|fixture\|example\|AS-9[0-1][0-9]\|AS-XXX"
```

---

## Severity Scale

| Level | Meaning | Fix when |
|-------|---------|----------|
| **P0** | Crashes on reachable path, or loses/corrupts data | This session — block the cut |
| **P1** | File-handle leak, evidence loss, or claim-safety violation in core | This session or next cut |
| **P2** | Same issues in tools layer, dead code in production, missing encoding | Next cut |
| **P3** | Style, redundant code, documentation drift | Sweep when convenient |

---

## Output Format

```markdown
# Bug Hunt Report — Sapote–Mamey v9.7.NNN

**Session date:** YYYY-MM-DD
**Source:** exact path/tier, versions and file SHA-256 values
**Scope:** reviewed paths, exclusions, selected privacy profile
**Baseline:** exact command/environment; pass/fail/skip/xfail; absent dependencies
**Candidate:** current indexed patch path and hash
**Post-fix:** exact commands and results; unrun gates and remaining holds

## Sweep Results

| Pattern | Hits | BUG | LEAK | SMELL | FP |
|---------|------|-----|------|-------|----|
| S1 | N | N | N | — | N |
| ...

## Bugs Found

### B1 (severity) — short title
**File:** path:line
**Impact:** what happens
**Fix:** what was changed
**Verified:** relevant check command and outcome, evidence path/hash, limits; or NOT RUN

## Patch Card

| ID | Severity | File | Fix | Effort | Verified |
|----|----------|------|-----|--------|----------|

## What This Cut Fixed Well
[Credit for bugs already fixed]

## Positive Exemplars
[Unusually well-written code]
```

---

## Completion record

Report reviewed versus unreviewed scope, supported findings and solutions, exact candidate files, meaningful checks, unresolved holds and the next bounded action. A sweep result is not release approval, scientific acceptance or permission to send the report to another chat.

*Bug Hunt Protocol — current operational boundaries reconciled against the v9.7.447 source.*
