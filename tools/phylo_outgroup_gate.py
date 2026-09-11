                      
"""Evaluate outgroup and ingroup pairwise alignment identity with explicit missingness."""
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))                                        
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from _console import emit                                               

BOUNDARY_PTS = 1.0


def load(path):
    """Read a nonempty rectangular alignment without silently replacing records."""
    records, key = {}, None
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                fields = line[1:].split()
                if not fields or fields[0] in records:
                    raise ValueError("blank or duplicate FASTA identifier")
                key = fields[0]
                records[key] = []
            elif key is None:
                raise ValueError("sequence before first FASTA identifier")
            else:
                if any(c.upper() not in "ACGTRYSWKMBDHVN-.?" for c in line):
                    raise ValueError("unsupported alignment symbol")
                records[key].append(line.upper())
    result = {k: "".join(v) for k, v in records.items()}
    lengths = {len(v) for v in result.values()}
    if not result or len(lengths) != 1 or 0 in lengths:
        raise ValueError("alignment must have nonempty sequences of equal length")
    return result


def ident(x, y):
    """Identity over shared unambiguous A/C/G/T columns; None when none exist."""
    if len(x) != len(y):
        raise ValueError("unequal alignment lengths")
    pairs = [(a, b) for a, b in zip(x.upper(), y.upper())
             if a in "ACGT" and b in "ACGT"]
    return ((100.0 * sum(a == b for a, b in pairs) / len(pairs), len(pairs))
            if pairs else (None, 0))


def check(aln, min_cols=500, sample=0, seed=12345):
    """A distance-screen heuristic, never proof of rooting or taxonomic placement."""
    if min_cols < 1 or sample < 0:
        return 3, "cannot evaluate: min_cols must be positive and sample nonnegative"
    try:
        alignment = load(aln)
    except (OSError, ValueError) as error:
        return 3, f"cannot evaluate: {error}"
    ogs = [k for k in alignment if "outgroup" in k.lower()]
    ing = sorted(k for k in alignment if k not in ogs)
    if len(ogs) != 1 or len(ing) < 3:
        return 3, (f"cannot evaluate: {len(ogs)} outgroup tip(s), {len(ing)} ingroup tip(s) "
                   "(need exactly 1 and >=3)")
    og = ogs[0]
    def comparable(a, b):
        pct, columns = ident(alignment[a], alignment[b])
        return (pct, columns, b) if pct is not None and columns >= min_cols else None
    outside = [comparable(og, k) for k in ing]
    if any(row is None for row in outside):
        return 3, "cannot evaluate: insufficient outgroup overlap with one or more ingroup tips"
    nearest = max(outside)
    best = []
    rng = random.Random(seed)
    sampled = bool(sample and len(ing) - 1 > sample)
    for a in ing:
        others = [k for k in ing if k != a]
        if sampled:
            others = rng.sample(others, sample)
        comparisons = [comparable(a, b) for b in others]
        if any(row is None for row in comparisons):
            return 3, f"cannot evaluate: insufficient ingroup overlap for {a}"
        best.append(max(comparisons) + (a,))
    worst = min(best)
    margin = nearest[0] - worst[0]
    head = (f"outgroup {og}\n"
            f"  nearest ingroup {nearest[2]}: {nearest[0]:.3f}% over {nearest[1]} nt\n"
            f"  most isolated ingroup {worst[3]}: {worst[0]:.3f}% over {worst[1]} nt\n"
            f"  margin {margin:+.3f} percentage points")
    if sampled:
        return 3, head + "\n  INDETERMINATE: sampled comparisons; rerun with sample=0."
    if margin <= 0:
        return 0, head + "\n  SCREEN_PASS: no distance-screen inversion; rooting is not validated."
    if margin < BOUNDARY_PTS:
        return 3, head + "\n  INDETERMINATE: boundary inversion requires review."
    return 2, head + "\n  SCREEN_FAIL: distance-screen inversion; review alignment and outgroup selection."


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("alignments", nargs="+")
    args = parser.parse_args()
    worst, reports = 0, []
    for path in args.alignments:
        rc, message = check(path)
        reports.append(f"{path}\n  {message}")
        worst = max(worst, rc)
    emit("\n\n".join(reports))
    return worst


if __name__ == "__main__":
    sys.exit(main())
