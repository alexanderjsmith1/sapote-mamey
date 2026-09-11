#!/usr/bin/env python3
"""Describe nearest-neighbor concordance across explicitly selected density rungs.

Usage: ladder_test.py FOLDER PANEL_STEM PATTERN
Each PANEL_STEM_<integer>x directory must contain exactly one .nwk or .treefile.
Distances are patristic. Tied nearest neighbors contribute their marked fraction.
The baseline (marked-1)/(total-1) is a descriptive label-count reference, not a
statistical test. No ratio threshold establishes biological association or its
absence. Monophyly is conditional on the input root, which this tool does not validate.
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys

EXIT_REFUSED = 2


def sister_null(marked, total):
    if not 2 <= marked < total:
        raise ValueError("Need at least two marked tips and at least one unmarked tip")
    return (marked - 1) / (total - 1)


def analyse(nwk, pattern, tie_rel_tol=1e-9, tie_abs_tol=1e-12):
    from Bio import Phylo

    if not pattern or not pattern.strip():
        raise ValueError("Empty marking pattern")
    if any(not math.isfinite(x) or x < 0 for x in (tie_rel_tol, tie_abs_tol)):
        raise ValueError("Tie tolerances must be finite and nonnegative")
    tree = Phylo.read(nwk, "newick")
    tips = tree.get_terminals()
    names = [t.name for t in tips]
    if any(not name or not name.strip() for name in names) or len(names) != len(set(names)):
        raise ValueError("Tip names must be nonempty and unique")
    for clade in tree.find_clades():
        length = clade.branch_length
        if clade is tree.root and length is None:
            continue
        if length is None or not math.isfinite(length) or length < 0:
            raise ValueError("Every non-root edge needs a finite nonnegative branch length")
    marked = [t for t in tips if pattern.casefold() in t.name.casefold()]
    expected = sister_null(len(marked), len(tips))
    markset = set(marked)
    fractions, tie_count, all_neighbors = [], 0, 0
    for tip in marked:
        distances = [(other, tree.distance(tip, other)) for other in tips if other is not tip]
        if any(not math.isfinite(d) or d < 0 for _, d in distances):
            raise ValueError("Invalid patristic distance")
        minimum = min(d for _, d in distances)
        nearest = [other for other, distance in distances
                   if math.isclose(distance, minimum, rel_tol=tie_rel_tol, abs_tol=tie_abs_tol)]
        fractions.append(sum(other in markset for other in nearest) / len(nearest))
        tie_count += len(nearest) > 1
        all_neighbors += len(nearest) == len(tips) - 1
    observed = math.fsum(fractions) / len(marked)
    ancestor = tree.common_ancestor(marked)
    inside = ancestor.get_terminals()
    intruders = [t.name for t in inside if t not in markset]
    return {"n": len(marked), "total": len(tips), "mono": not intruders,
            "intruders": len(intruders), "clade_size": len(inside),
            "mrca_is_root": ancestor is tree.root,
            "vacuous": len(inside) == len(tips),
            "sister_obs": observed, "sister_exp": expected,
            "sister_ratio": observed / expected, "tie_frac": tie_count / len(marked),
            "tie_rel_tol": tie_rel_tol, "tie_abs_tol": tie_abs_tol,
            "status": "UNINFORMATIVE" if all_neighbors == len(marked) else "DESCRIPTIVE",
            "marked_names": sorted(t.name for t in marked), "names": sorted(intruders),
            "interpretation": "Descriptive only; input root unverified; biological association undetermined"}


def find_rungs(folder, stem):
    root = Path(folder)
    if not root.is_dir() or not stem:
        raise ValueError("A valid folder and nonempty panel stem are required")
    pattern = re.compile(re.escape(stem) + r"_(\d+)x")
    rungs = []
    seen = set()
    for directory in root.iterdir():
        match = pattern.fullmatch(directory.name)
        if not directory.is_dir() or not match:
            continue
        number = int(match[1])
        if number in seen:
            raise ValueError("Duplicate numeric density rung")
        seen.add(number)
        files = sorted(p for p in directory.iterdir()
                       if p.is_file() and p.suffix in {".nwk", ".treefile"})
        if len(files) != 1:
            raise ValueError(f"Rung {directory.name} needs exactly one tree; found {len(files)}")
        rungs.append((number, directory.name, str(files[0])))
    if len(rungs) < 2:
        raise ValueError("A density ladder needs at least two explicit rungs")
    return [(name, path) for _, name, path in sorted(rungs)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("folder")
    parser.add_argument("panel_stem")
    parser.add_argument("pattern")
    args = parser.parse_args(argv)
    try:
        rows = [(name, analyse(path, args.pattern))
                for name, path in find_rungs(args.folder, args.panel_stem)]
        membership = {tuple(result["marked_names"]) for _, result in rows}
        if len(membership) != 1:
            raise ValueError("Marked tip identities differ across rungs")
    except (OSError, ValueError, ImportError) as exc:
        sys.stderr.write(f"REFUSED: {exc}\n")
        return EXIT_REFUSED
    sys.stdout.write(json.dumps({"panels": rows, "interpretation": "UNDETERMINED: descriptive ratios do not establish biological association or its absence"},
                               indent=2, allow_nan=False) + "\n")
    # Emit the descriptive measurements, but refuse an informative ladder verdict
    # when every candidate neighbor is tied at any rung.
    return EXIT_REFUSED if any(r["status"] == "UNINFORMATIVE" for _, r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
