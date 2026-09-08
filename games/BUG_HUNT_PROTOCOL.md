# Bug Hunt Protocol — Sapote–Mamey

**Companion to:** Bunny Hop (per-file adversarial audit)
**Scope:** Codebase-wide systematic bug sweep

---

## What is Bug Hunt?

A pattern-driven sweep of the entire codebase looking for concrete, reproducible bugs.
Unlike the Bunny Hop (which audits files one at a time through Inspector/Defender
dialogue), Bug Hunt works across the whole tree using grep sweeps, diff analysis,
dead-code detection, and targeted reads of high-risk functions.

**The output is a prioritized patch card with verified fixes.**

| | Bunny Hop | Bug Hunt |
|---|---|---|
| Unit | One file at a time | Whole codebase |
| Method | Adversarial (Inspector vs Defender) | Pattern sweep + targeted reads |
| Finds | Design issues, claim-safety gaps, completeness | Crash bugs, data loss, dead code, leaks |
| Output | Per-file verdicts + patch card | Categorized bug list + verified fixes |

---

## How to Run a Session

### Setup

1. Upload the bundle zip + offline dependency wheels (pytest, biopython, ijson, pluggy, iniconfig)
2. Extract the CODE tier
3. Install dependencies and run `pytest` — the suite must be green before you start
4. Record the baseline: test count, pass/skip/fail/xfail

### Phase 1 — Automated Sweeps (~15 min)

Run every grep pattern in the **Pattern Library** below. For each hit, classify as:

- **BUG** — will crash, lose data, or produce wrong output under reachable conditions
- **LEAK** — file-handle, resource, or evidence leak; won't crash but degrades
- **SMELL** — style issue, inconsistency, or maintenance hazard; no runtime effect
- **FALSE POSITIVE** — pattern matched but the code is correct

Record hit counts per pattern. Don't fix anything yet — just inventory.

### Phase 2 — Targeted Reads (~30 min)

1. **Largest functions** — any function >200 lines
2. **New/changed files** — diff against the previous version
3. **Wiring check** — verify every new module is actually imported and called
4. **Operator precedence** — any `if A and B if C else D` pattern

### Phase 3 — Fix and Verify (~30 min)

For each BUG and high-priority LEAK:
1. Read the exact lines
2. Implement the fix
3. Run `pytest` after each fix — must stay green
4. **Never batch fixes without testing between them**

### Phase 4 — Report

Write the Bug Hunt report using the output format below.

---

## Pattern Library

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

### AS-ID Leak Check

```bash
# LP1: Real AS- strain IDs in non-test code
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
**Baseline:** NNNN passed, NN skipped, N xfailed
**Post-fix:** NNNN passed, NN skipped, N xfailed

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
**Verified:** pytest count after fix

## Patch Card

| ID | Severity | File | Fix | Effort | Verified |
|----|----------|------|-----|--------|----------|

## What This Cut Fixed Well
[Credit for bugs already fixed]

## Positive Exemplars
[Unusually well-written code]
```

---

## Quick-Start Checklist

```
[ ] Upload bundle + deps
[ ] Extract CODE tier
[ ] Install deps, run pytest, record baseline
[ ] Phase 1: Run all Pattern Library sweeps
[ ] Phase 2: Read largest functions + new/changed files + wiring check
[ ] Phase 3: Fix P0/P1 bugs, pytest after each
[ ] Phase 4: Write report + patch card
```

---

*Bug Hunt Protocol v1.0 — Sapote–Mamey*
**
