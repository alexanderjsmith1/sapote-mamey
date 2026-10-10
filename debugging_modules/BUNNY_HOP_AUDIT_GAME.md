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

1. Identify the exact source tree or archive tier, version and source hashes. Read current user instructions, privacy/profile boundaries and generated-file ownership.
2. Create or reuse one indexed Markdown audit record. Link prior evidence in place and check source hashes before carrying a finding forward. No package-wide copy or source cleanup is implied.
3. Declare the eligible file pool, exclusions and review objective. A Python-only sample cannot establish documentation or whole-bundle coverage.

### Rolling for files

This example lists a local source tree without extracting an archive, executing project imports or copying source files. Substitute the exact accessible tree. It samples up to six files, including when the pool is smaller. Record the seed, sorted eligible roster, sampled paths and file hashes in the audit evidence; the same seed only reproduces a sample when the roster and Python sampling behavior are unchanged.

```python
from pathlib import Path
import hashlib, random
root = Path("/absolute/path/to/exact/CODE-tree")
seed = 20261004
candidates = sorted(p.relative_to(root).as_posix()
                    for prefix in ("mamey", "tools")
                    for p in (root / prefix).rglob("*.py")
                    if "__pycache__" not in p.parts and "_vendor" not in p.parts)
sample = random.Random(seed).sample(candidates, min(6, len(candidates)))
print("seed", seed, "eligible", len(candidates))
for rel in sample:
    print(rel, hashlib.sha256((root / rel).read_bytes()).hexdigest())
```

Audit all selected files, or declare the first fixed number before drawing. Record every reroll and its reason. Picking the interesting files or discarding an inconvenient draw creates a targeted sample; label it accordingly. Dependency hops are valuable targeted review and should be recorded separately from the random draw. No sampled result establishes an unbiased whole-tree verdict or a prevalence estimate.

---

## The Audit Format

For each file:

### 1. Read the file
Read the relevant source in place, including callers, error branches, writes and consumers. Record the exact functions or line ranges inspected. A first/last-page skim is partial review; do not label the entire file reviewed until the remaining source has been assessed. Reading an import is not proof that a branch executes.

### 2. Write a brief description
One short paragraph: what the file IS, what it does, approximate line count, key design features.

### 3. Inspector reports supported reasons to CHANGE or REMOVE the file
These can be:
- Correctness concerns (could produce wrong output)
- Design concerns (fragile, unmaintainable, inconsistent with pipeline conventions)
- Redundancy concerns (this file could be deleted or merged)
- Safety concerns (public-tier leakage risk, claim-safety violation, etc.)

Inspector reports only evidence-supported reasons, including zero when appropriate. The heading describes the historical game format, not a findings quota.

### 4. Defender examines the strongest supported case to KEEP the file as-is
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

## Patterns to investigate

Treat these as questions, not proof that a design is good or defective:

- Follow shared logic to its actual callers; an import, regex hit or duplicate name alone does not establish execution or dead code.
- Check refusal and partial-result paths. A zero exit or graceful fallback may omit required evidence; record missingness and the consumer's acceptance rule.
- Assess hardcoded thresholds against the named profile and version. A historical calibration statement does not validate every current use.
- Check output overwrite, source/output aliasing and multi-file consistency. Temporary-file replacement can protect one file without making a whole output set transactional. Recommend atomic writes when the failure scenario warrants them.
- Verify generated-file ownership, provenance and dependency availability before proposing deletion, a rewrite or an install. Preserve source evidence; recommendations do not authorize removal.
- Select meaningful verification for the changed behavior. Record commands, test selection, environment, exit status, passes/failures/skips and unavailable dependencies. The default test partition skips explicitly marked slow/network tests, and test fixtures replace the operator's registry environment; tests do not validate the real cohort by default.

---

## Notes for the Auditing Chat

- Adopt the audit role requested by the user; the game does not assign a model identity or authorize additional agents.
- **Claim-safe language always.** Even in audit notes: "BGC" not "compound," "biosynthetic capacity" not "produces."
- If you find a BGC referenced in a file, preserve the full strain / node-or-contig / region / BGC alias identity. Hold an unresolved join rather than guessing it.
- **Never make a public-tier claim based on auditing the PRIVATE code tier.** If you audit `make_public_tier.sh`, describe what it does — don't infer what the public tier contains.
- Assess disclosure against the current user-selected privacy profile and actual source metadata. A strain prefix alone does not establish private or public status; hold uncertain public export without blocking unrelated review.
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
*Originated: June 2026 analysis session.*
