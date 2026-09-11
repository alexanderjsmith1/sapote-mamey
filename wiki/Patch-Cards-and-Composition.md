# Patch Cards and Composition — how a lane hands work to the cut

`CUT_PROTOCOL.md` covers what happens **at** the cut: the version bump, the tiers, the disclosure
block. This page covers what happens **before** it — how a lane packages a change so the composer
can fold it safely. That step had no written rules, and the gap produced real defects.

Every rule below is here because it was **measured breaking something**, not because it sounds tidy.

---

## The one rule that matters: ship a diff, not a copy of the file

A patch card can hand the composer either a **unified diff** or a **whole-file copy** (a "file
drop"). They are not equivalent.

| | unified diff | file drop |
|---|---|---|
| States which lines change | yes | no |
| Detects that the base moved | **yes** — `--fuzz=0` refuses | **no** — it overwrites |
| Composer can review intent | yes | only by diffing it themselves |

A file drop is written against the tree the author had. If the bundle gained content in a cut the
author never saw, copying their file over it **reverts that content with no conflict, no reject and
no message.** The fold looks clean and the change is gone.

**Generate the diff, don't hand-write it:**

```bash
diff -u a/tools/your_file.py b/tools/your_file.py > 001_your_change.patch
```

Then prove it applies to the sealed tree you are targeting:

```bash
patch -p1 -V none --fuzz=0 --batch --dry-run < 001_your_change.patch
```

`--fuzz=0` is the point. It refuses rather than guessing when the surrounding lines have moved —
which is exactly the signal a file drop cannot give you.

### `diffbuild/` is fine, and is not a payload

Keeping the before/after images you built the diff from — conventionally `diffbuild/a/…` and
`diffbuild/b/…` — is good practice: it shows your work. They are **scaffolding, not payload**. The
composer folds your `.patch`; nothing under `diffbuild/` is copied into the tree.

*(An audit tool briefly read those images as file drops and reported three innocent cards as
reverting sealed content. The cards were correct; the tool was wrong. If you write tooling over the
queue, exclude `diffbuild/`.)*

---

## What a card folder should contain

```
YOURLANE_412_short_description/
  PATCH_CARD.md                 <- required: what, why, how verified, claim ceiling
  001_short_description.patch   <- the change
  diffbuild/                    <- optional: the a/ and b/ images you diffed
```

**`PATCH_CARD.md` is not optional.** It is the only place the composer learns what the change is for
and what you checked. A card arrived in `.412` with a diff and a test but no card, and it was one
half of a collision that could not be adjudicated without knowing its intent.

A card states, briefly:
- the **base** it was authored against (the sealed bundle name and engine version),
- the **defect** and how it was reproduced,
- the **fix**,
- **verification** — apply/reverse at zero fuzz, tests run, fail-before/pass-after,
- the **claim ceiling** (see [Claim-Safety](Claim-Safety.md)).

---

## Three traps, each observed in a real queue

### 1. Two cards editing the same test file

If your card adds tests to a file another card also touches, **and both ship the file as a drop**,
whichever the composer copies second wins and the other's tests vanish silently.

Seen in `.412`: two sibling cards each dropped the same test file. The sealed file had 12 tests, one
card had 12+2, the other 12+1, neither was a superset — so **either apply order lost coverage**, and
the 15-test union existed in neither file. The diffs themselves were path-disjoint and perfectly
safe; only the test drops collided.

**Do:** ship test changes as a diff too. Two diffs against one file conflict **loudly**, which is
what you want. If you know a sibling card touches the same file, coordinate and ship one merged file.

### 2. Build artifacts in the payload

`.gitignore` excludes `__pycache__/`, so `.pyc` files never belong in a card. Four `.pyc` (carrying
Python 3.14 bytecode) and several `.DS_Store` reached one `.412` queue. A whole-directory file drop
would have copied them into the bundle.

```bash
find . -name '*.pyc' -o -name '__pycache__' -o -name '.DS_Store'   # before you hand off
```

### 3. Spending ratchet headroom without noticing

`repo_health.py --strict` ratchets `print_calls`, `silent_swallow` and `injected_print`. These are
meant to move **downward**. A new tool that adds an `except Exception: pass` or a handful of `print()`
pushes them up, and `STRICT_HEALTH_WAIVER.json` stops covering a metric **the moment its count drifts
above the signed `observed`**.

In `.412` a new figure tool took `silent_swallow` from 148 to 149 — exactly the signed ceiling. It
passed, but the next `except: pass` added anywhere in the tree would expire the waiver and hand a
future lane a hard stop it did not create.

**Do:** run the strict gate before handing off, and if your card moves a ratchet upward, say so in
the card and justify it.

```bash
python tools/repo_health.py --strict
```

---

## Before you hand off — the short checklist

1. `patch -p1 --fuzz=0 --dry-run` against the **sealed** base: clean.
2. Reverse dry-run: clean (your patch is undoable).
3. Your tests pass on the patched tree, **and fail on the unpatched one** — a test that passes both
   ways is not testing your fix.
4. No `.pyc` / `__pycache__` / `.DS_Store` in the folder.
5. `repo_health.py --strict` — note any ratchet you moved.
6. `PATCH_CARD.md` present, naming base, defect, fix, verification, claim ceiling.

---

## Related

- [Versioning](Versioning.md) — the three version streams and why they are synced at cut time
- [Claim-Safety](Claim-Safety.md) — the ceiling every card's output statement must respect
- [Common Mistakes](Common-Mistakes.md) — analysis-side counterparts to the traps above
- `CUT_PROTOCOL.md` (bundle root) — what happens once cards are folded

*Composition and engineering only; nothing here changes a scientific claim. Class-level hypotheses,
judgment deferred.*
