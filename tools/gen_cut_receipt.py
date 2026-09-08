#!/usr/bin/env python3
"""gen_cut_receipt.py — generate a cut receipt's file-delta from a machine checksum-diff. Generic.

Fixes the recurring hand-counted-receipt error (a receipt claimed "11 modified" when the real delta
was 47). Diffs two SOURCE_CHECKSUMS_SHA256.txt files (previous sealed tree vs this candidate) and emits
an immutable, reproducible delta: modified / new / removed, with the file lists. No human counting.

  gen_cut_receipt.py <old_checksums.txt> <new_checksums.txt> [--md]

Checksum line format: "<sha256>  ./<relpath>" (sha2, two spaces, path). Exit 0 always (reporting tool).
"""
from __future__ import annotations
import sys

def load(path):
    d = {}
    for ln in open(path):
        ln = ln.rstrip("\n")
        if not ln.strip():
            continue
        parts = ln.split(None, 1)
        if len(parts) != 2:
            continue
        sha, rel = parts[0], parts[1].strip()
        d[rel] = sha
    return d

def diff(old, new):
    old_k, new_k = set(old), set(new)
    added = sorted(new_k - old_k)
    removed = sorted(old_k - new_k)
    modified = sorted(k for k in (old_k & new_k) if old[k] != new[k])
    return added, removed, modified

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    md = "--md" in sys.argv
    if len(args) != 2:
        sys.exit("usage: gen_cut_receipt.py <old_checksums.txt> <new_checksums.txt> [--md]")
    old, new = load(args[0]), load(args[1])
    added, removed, modified = diff(old, new)

    if md:
        sys.stdout.write(("## Cut receipt — file delta (machine-generated from checksum diff)\n") + "\n")
        sys.stdout.write((f"- previous entries: **{len(old)}**  ·  this cut entries: **{len(new)}**") + "\n")
        sys.stdout.write((f"- **{len(modified)} modified / {len(added)} new / {len(removed)} removed**\n") + "\n")
        for label, items in (("New", added), ("Removed", removed), ("Modified", modified)):
            if items:
                sys.stdout.write((f"### {label} ({len(items)})") + "\n")
                for i in items:
                    sys.stdout.write((f"- `{i}`") + "\n")
                sys.stdout.write("\n")
    else:
        sys.stdout.write((f"prev_entries\t{len(old)}") + "\n")
        sys.stdout.write((f"this_entries\t{len(new)}") + "\n")
        sys.stdout.write((f"modified\t{len(modified)}") + "\n")
        sys.stdout.write((f"new\t{len(added)}") + "\n")
        sys.stdout.write((f"removed\t{len(removed)}") + "\n")
        for i in added:    sys.stdout.write((f"NEW\t{i}") + "\n")
        for i in removed:  sys.stdout.write((f"REMOVED\t{i}") + "\n")
        for i in modified: sys.stdout.write((f"MODIFIED\t{i}") + "\n")

if __name__ == "__main__":
    main()
