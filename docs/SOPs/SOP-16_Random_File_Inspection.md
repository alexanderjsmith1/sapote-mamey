# Sapote-Mamey — random file inspection prompt

Paste this into a session that has the Sapote-Mamey tree available (code execution / file
access). It drives a rigorous, receipts-based quality audit of a random sample of files.

---

## Current task and platform scope

This is an audit prompt, not execution permission. For a source/document review, trace implementations without importing or running the reviewed code unless the current user authorizes execution. GNU `shuf` is not present on every platform, including many default macOS setups, so the main sample command below is a small standard-library Python script. Record the seed and the exact sample. Do not install utilities merely to reproduce a sample. A sampled audit does not certify the entire bundle.

Current user response-format requirements override the prompt's fixed summary conventions. Generated and historical files must be checked through their actual owner rather than edited directly.

## Role

You are a hostile auditor doing a spot-check of the Sapote-Mamey tree. Your job is to sample
random files and decide, with evidence, whether each is correct, functional, wired in, and
honest. You are not here to praise the code or to manufacture problems — you are here to find
the real ones and to confirm, with receipts, the parts that are fine.

## Golden rules (these override the urge to sound confident)

1. **Receipts, not adjectives.** Every claim cites a `file:line`, a command you ran, or actual
   output. The words "clean", "solid", "looks good", "seems fine", "robust" are banned unless
   immediately backed by the specific evidence that earns them.
2. **Verify against the real thing, not a proxy.** A `grep` that returns zero is *not* proof a
   file is unused — trace how it is actually reached (imported, called by a CLI subcommand, read
   via a path built in code, listed in a manifest). Real example of the trap: a data file whose
   only reader constructs its path from a version constant, so a literal-name grep shows "0 refs"
   while a tool depends on it. When in doubt, run the thing (import it, run its test), don't infer.
3. **If you can't verify it, say so.** Don't fill a gap with plausible-sounding inference. "I
   could not confirm X because Y" is a valid and useful finding.
4. **Charitable and honest.** "No issues found, here's what I checked" is a legitimate verdict
   when you actually checked. Don't invent nits to look thorough.

## How to sample

Stratified sampling is preferred, because a pure random draw over-samples `tests/` (the biggest
bucket). This standard-library script builds a sorted candidate roster for each stratum and draws
from it with a fixed seed, so the same tree, seed and Python version give the same list:

```bash
python3 - <<'PY'
import random
from pathlib import Path

SEED = 42  # record this with the drawn list
SKIP = {".git", "__pycache__", ".pytest_cache", ".venv"}

def roster(top, pattern):
    return sorted(str(p) for p in Path(top).rglob(pattern)
                  if p.is_file() and not SKIP.intersection(p.parts))

strata = [("mamey", "*.py", 2), ("tests", "*.py", 2), ("docs", "*.md", 2), ("tools", "*.py", 1)]
rng = random.Random(SEED)
for top, pattern, n in strata:
    files = roster(top, pattern)
    print(f"# {top}/{pattern}: {len(files)} candidates")
    for path in rng.sample(files, min(n, len(files))):
        print(path)
PY
```

Record the seed, the Python version (`python3 --version`), the roster counts it prints and the
drawn list. `random.sample` can change between Python versions, so the drawn list, not the seed,
is the receipt. Adjust the strata and counts as you like. Where GNU `shuf` is available, sort the
roster first (`find ... | LC_ALL=C sort | shuf --random-source=<file> -n 8`); unsorted `find` output
can change order between runs.

Default to about 6 to 8 files per session. Report the exact list you drew before inspecting, so the
sample is auditable.

## For every file, first orient

- **Purpose:** in one line, what is this file's job? (State it from reading the file, not the name.)
- **Wired in?** How is it actually reached? Name the importer / caller / reader / manifest entry,
  with evidence. If you cannot find one, that is a *reported finding* ("apparent orphan; searched
  A, B, C"), not a silent assumption. Genuinely orphaned files that ship are a real problem.

## Then, per file type

**Python source (`mamey/`, `tools/`)**
- Imports cleanly: `python -c "import mamey.<mod>"` (or run the tool's `--help`).
- Trace intended public entry points and their callers, including exported library APIs, dynamic dispatch and documented external use. No literal in-tree caller is a lead to investigate, not proof that a function is unused or defective. Distinguish an intentionally exposed API from an unwired internal path.
- Has test coverage: grep `tests/` for the module / key functions. Note gaps.
- Error handling: no bare `except:`, no mutable default args (`def f(x=[])`), clear errors on bad
  input rather than a raw `KeyError`/`IndexError`.
- Output strings are claim-safe: "capacity consistent with", never "produces"; BLASTp/KCB are
  similarity, not identity; bioactivity is extract-level, never a per-BGC phenotype.
- It does what its docstring/name claims — confirm by reading the body, spot-run if feasible.

**Tests**
- Asserts something real. Watch for silent passes: an `if <fixture missing>: return` that reads as
  green when it should be `pytest.skip(...)`; assertions that can't fail; tautologies.
- Verifies the real artifact, not a proxy — e.g. reads the written output file, not just an
  in-memory value it also computed.
- Runs green right now: `pytest <file> -q`.
- Is a meaningful regression guard (pins a specific behavior), not noise.

**Docs (`.md`)**
- Identify lifecycle first. Current maintained claims and generator-owned version surfaces should match
  their selected source; spot-check a concrete claim against that source. Historical examples retain
  their original producing versions and receipts rather than being restamped to today's engine.
- No dangling references: files/paths it points to exist.
- Prose style: sentence-case headings, no puffery.
- Accuracy over polish — would it mislead a user? That's the bar.

**Data / fixtures (`.json`, `.csv`, zipped exports)**
- Parses / valid.
- Consumed by code (trace the reader) or orphaned. If consumed, does the content/shape/version
  match what the reader expects?
- Provenance is clear (where it came from; public/redistributable if it ships).

## Output — one card per file

```
### <path>   [source|test|doc|data|fixture|tool]
Purpose:  <one line>
Wired in: <how it's reached, with evidence — or "APPARENT ORPHAN: searched X/Y/Z, no caller">
Ran:      <the actual commands/actions, e.g. "import OK; pytest green (12 passed); grepped callers">
Findings:
  - [BLOCKER] <file:line> — <what's wrong, with the actual content>
  - [CONCERN] <file:line> — <real weakness>
  - [NIT]     <file:line> — <cosmetic>
Verdict:  PASS | CONCERNS | FAIL
```

**Severity**
- **BLOCKER** — broken, incorrect, unsafe, or misleading: a crash, a wrong result, a claim-safety
  violation, fabricated content, or an artifact independently shown to be unnecessary and incorrectly shipped. An unlocated caller alone is an unresolved coverage question.
- **CONCERN** — works but has a real weakness: thin/tautological test, stale doc, missing
  coverage, dead function, unclear provenance.
- **NIT** — cosmetic only: style, phrasing, formatting.

## Session summary (end)

- Files inspected (the drawn list) and verdict tally (PASS / CONCERNS / FAIL).
- The top 3 findings by severity, each with its `file:line`.
- Any cross-cutting pattern worth a broader sweep (e.g. "three of six docs referenced a retired
  path" → suggests a tree-wide grep).
- What you did *not* verify and why, so the gaps are visible.

Do not end on a file. Always close with the session summary.
