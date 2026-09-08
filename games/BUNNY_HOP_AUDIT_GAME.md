# The Bunny Hop Audit Game
### A Protocol for Random File Auditing of the Sapote–Mamey Pipeline

---

## What This Is

The Bunny Hop Audit Game is a structured, random-sampling audit of the Sapote–Mamey pipeline codebase. The goal is to surface latent issues, validate design decisions, and build a patch card — without cherry-picking files or only auditing the ones you already know are clean.

**Why random sampling?** It catches problems you weren't looking for. Planned audits tend to focus on known pain points. Random audits surface forgotten scripts, design drift, and quiet inconsistencies that would otherwise stay buried.

**Why adversarial?** The Inspector vs. Defender format forces honest engagement with both the case for removing or changing something AND the case for keeping it. It prevents lazy "KEEP" rubberstamping and lazy "REMOVE" overcorrection.

---

## How to Play

### Setup

1. Load the Sapote–Mamey CODE bundle (the `CODE-YYYYMMDD.zip` tier, not analysis-free or public).
2. Start a fresh audit markdown file (e.g., `PIPELINE_AUDIT_SESSION_v2.md`).
3. This intro goes at the top of that file.
4. Start a new findings list — do NOT continue a previous session's list. Starting fresh lets you randomly re-examine a file that was audited before, which is fine and sometimes valuable (designs change across versions).

### Rolling for Files

Each round, use Python to sample randomly from the candidate pool:

```python
import zipfile, random
from io import BytesIO

outer_zip = '/mnt/user-data/uploads/Sapote_Mamey_vX_Y_Z.zip'
with zipfile.ZipFile(outer_zip, 'r') as z:
    code_zip_name = [n for n in z.namelist() if 'CODE-' in n and 'analysis-free' not in n][0]
    inner_z = zipfile.ZipFile(BytesIO(z.read(code_zip_name)), 'r')
    all_files = inner_z.namelist()

candidates = [f for f in all_files
              if (f.startswith('mamey/') or f.startswith('tools/'))
              and f.endswith('.py')
              and '__pycache__' not in f
              and '_vendor' not in f
              and f not in ('mamey/__init__.py', 'tools/__init__.py')]

sample = random.sample(candidates, 6)   # roll 6, pick 2–3 to audit this round
for i, f in enumerate(sample, 1):
    print(f"{i}. {f}")
```

**Picking:** Take the first 2–3 from the sample, or pick the ones that look most interesting. Either is fine — the randomness is in the roll, not the pick.

**Re-rolls are allowed.** If the sample is all tiny utility files, re-roll. If a file comes up that was audited in a previous session (of this or any other chat), audit it anyway — it might look different now, or catch something that was missed.

**The Bunny Hop move:** At any point, instead of rolling randomly, you can "hop" to a file that the current file references or depends on. If `workbook.py` imports from `mamey/models.py`, hop to `models.py` next. This lets you follow design threads without losing the random-sampling discipline.

---

## The Audit Format

For each file:

### 1. Read the file
Extract and read the full source. For files over ~200 lines, read the first 130–150 lines and the final 30 lines; then request more if needed.

### 2. Write a brief description
One short paragraph: what the file IS, what it does, approximate line count, key design features.

### 3. Inspector gives 3 reasons to CHANGE or REMOVE the file
These can be:
- Correctness concerns (could produce wrong output)
- Design concerns (fragile, unmaintainable, inconsistent with pipeline conventions)
- Redundancy concerns (this file could be deleted or merged)
- Safety concerns (public-tier leakage risk, claim-safety violation, etc.)

Inspector must give exactly **3 reasons**. Not 2, not 4.

### 4. Defender gives ≥1 reason to KEEP the file as-is
Defender argues the strongest case for the current design. Defender must engage honestly with the Inspector's points, not just restate "it works."

If the Defender's argument is strong, the Inspector can concede on some points.

### 5. Write Consensus
Consensus is one of:
- ✅ **KEEP AS-IS** — No changes needed.
- ✅ **KEEP + [ACTION]** — Keep the design; add a small specific improvement.
- 🟡 **PENDING** — Needs verification before consensus (e.g., "does this function actually get called?").
- 🔴 **CHANGE** — Design needs a real fix; describe it concisely.
- 🔴 **REMOVE** — File should be removed; explain why.

Consensus must include a **specific, actionable improvement** if anything was found (not just "could be improved").

---

## Claim-Safety Conventions for Audit Language

The audit is about the pipeline code, not the science. But the same epistemic standards apply:

- **Observed:** "The function calls subprocess.run()" — directly seen in the source.
- **Computed:** "This file is 334 lines." — counted deterministically.
- **Inferred:** "This design was chosen to prevent the v9.7.86 drift incident." — based on the docstring or commit context.
- **Assumed:** "This is probably never called at runtime." — not yet verified; flag it.

Don't make a CHANGE recommendation based on an assumed problem. Verify first (grep, test run, read the caller), or flag as 🟡 PENDING.

---

## What to Track

Keep a running summary at the bottom of the session file:

```
## Summary — SESSION vN (Files 1–N)
1. ✅ `mamey/figure_policy.py` — KEEP as-is; add audit log.
2. ✅ `mamey/registry_schema.py` — KEEP as-is; verify stable-ID validation.
3. 🔴 `tools/some_script.py` — CHANGE: description of the fix needed.
...
```

And a **Patch Card** section at the bottom — all actionable improvements with estimated effort:

```
## Patch Card
| File | Action | Effort |
|------|--------|--------|
| mamey/domain_figures.py | Add atomic PNG writes | XS |
| tools/render_dapr_boards.py | Create DAPR_STANDING_CONSTRAINTS.md | S |
| mamey/compound_class.py | Add exclusion-list docstring comments | XS |
```

Effort scale: XS (5 min), S (15–30 min), M (1–2 hrs), L (half-day), XL (multi-day).

---

## Meta-Patterns to Watch For

Previous sessions have identified recurring design patterns across the pipeline. When you see these, they're usually intentional — don't flag them as issues unless there's a specific violation:

1. **Single source of truth** — Logic is imported, not duplicated. (e.g., `verify_tier_derivation.py` imports live redaction logic; was previously broken when it had an inlined copy.)
2. **Fail-closed logic** — Incomplete state → explicit non-zero exit, never silent pass.
3. **Intentional brittleness** — Hardcoded positions, hardcoded lists, hardcoded registries are BY DESIGN. They're auditable. Don't reflexively externalize them.
4. **Frozen/immutable design** — Frozen dataclasses, frozensets, frozen tuples prevent accidental mutation.
5. **Evidence-based constraints** — Hardcoded exclusions and thresholds are calibrated against the 32-ref MIBiG set. They're not arbitrary.
6. **Policy at code time** — Policy enforced in code (not config), intentional (not laziness).
7. **Atomic writes** — `.tmp` + `os.rename()` is the standard pattern for output integrity. Flag any output writer that doesn't use it.
8. **Graceful degradation** — Report what you can; don't crash on partial failure.
9. **Regression anchors** — Parity tests, positional pairing, backward-compatibility layers are intentional constraints, not tech debt.

---

## Notes for the Auditing Chat

- You are Claude (Sapote judgment layer), auditing Mamey (the deterministic Python extraction engine).
- **Claim-safe language always.** Even in audit notes: "BGC" not "compound," "biosynthetic capacity" not "produces."
- If you find a BGC referenced in a file, always note the node or contig alongside it.
- **Never make a public-tier claim based on auditing the PRIVATE code tier.** If you audit `make_public_tier.sh`, describe what it does — don't infer what the public tier contains.
- If you encounter a file that appears to reference unpublished strain data (AS-series IDs), flag it with 🔴 LEAK RISK before proceeding.
- Inspector and Defender are both you. Play both roles honestly. Don't let Defender capitulate easily; don't let Inspector be contrarian for its own sake.

---

## Starting the Session

Once you have this intro in your markdown, begin:

```
## Game 1 — [optional theme, e.g., "Core Extraction Layer"]

[Roll for files]
[Pick 2–3]
[Audit each]
[Write consensus]
[Update summary]
```

Good luck. Keep rolling until you have a solid patch card or run out of time.

---
*Bunny Hop Audit Game — Protocol v1.0 | Sapote–Mamey Pipeline*
*Originated: June 2026 analysis session (Alexander J. Smith / )*
