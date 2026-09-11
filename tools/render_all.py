#!/usr/bin/env python3
"""Render a built GToTree/IQ-TREE tree with publication-ready tip labels.

Two steps the existing tools do separately, chained so a tree goes from raw
newick to a figure in one call:

  1. tools/relabel_and_render.py maps comparator tips from their genome FASTA
     headers to 'Genus species Strain'. It deliberately leaves AS-#### query
     tips alone.
  2. AS tips are then labelled 'Genus AS-#### (host)' from the SSOT, which is
     what Alex asked for and what the raw GToTree labels never carry. A strain
     with no taxonomy in the SSOT is left bare AND reported -- that silence is
     exactly how AS-XXX reached a rendered figure unlabelled.

Usage:
    render_all.py <treefile> <genomes_dir> <out.png> "Title1||Title2" [outgroup_substr]
"""
import sys, os, re, csv, subprocess

if __name__ == "__main__":
    ROOT = os.environ.get("MAMEY_DATA_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SSOT = f"{ROOT}/strain_data/_ANTISMASH_CANONICAL/STRAIN_METADATA_CONSOLIDATED.tsv"
    PY = sys.executable
    RELABEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relabel_and_render.py")
    RENDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_clean_tree.py")

    treefile, gdir, outpng, title = sys.argv[1:5]
    og_hint = sys.argv[5] if len(sys.argv) > 5 else "OUTGROUP"

    # step 1 -- comparator tips from FASTA headers (also renders, which we redo below)
    r = subprocess.run([PY, RELABEL, treefile, gdir, outpng, title, og_hint],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-800:], r.stderr[-800:], sep="\n")
    print(r.stdout.strip())

    rel_tf = treefile.replace(".treefile", "_relabeled.treefile")

    # step 2 -- AS tips get genus + host
    tax, host = {}, {}
    with open(SSOT) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            s = (row.get("strain") or "").strip()
            if not s:
                continue
            tax[s] = (row.get("taxonomy") or "").strip()
            host[s] = (row.get("host_common") or row.get("source") or "").strip()  # governed host first

    nwk = open(rel_tf).read()
    # Clean comparator tip junk relabel copies from messy filenames: doubled SID + contig suffix,
    # assembler contig tokens, a genus typo. .c\d+ (digits) keeps _OUTGROUP tags intact.
    nwk = re.sub(r'(SID\d+)_SID\d+(\.c\d+)?', r'\1', nwk)
    nwk = re.sub(r'(SID\d+)_tig\d+', r'\1', nwk)
    nwk = re.sub(r'_supercont[\d.]+', '', nwk)
    nwk = nwk.replace('Streptoymces', 'Streptomyces')
    missing, done = [], {}
    for lf in sorted(set(re.findall(r"[(,]([^(),:]+):", nwk))):   # sorted: stable missing-list + substitution order
        m = re.fullmatch(r"(AS-\d+)", lf)
        if not m:
            continue
        sid = m.group(1)
        genus = (tax.get(sid, "").split() or [""])[0]
        if not genus:
            missing.append(sid)
            continue
        # NEVER put parentheses, commas, colons or semicolons in a newick label -- they are
        # structural characters. A first pass wrote 'Genus_AS-XXX_(attine-ant)' and the '('
        # opened a new clade: the host became a tip and the real label slid onto an internal
        # branch. The figure still rendered and still looked plausible, which is the danger.
        h = re.sub(r"[^A-Za-z0-9.\-]+", "-", host.get(sid, "").strip()).strip("-")
        if h.lower() in ("", "unknown", "na", "none"):
            h = ""
        done[lf] = f"{genus}_{sid}" + (f"_{h}" if h else "")

    for old in sorted(done, key=len, reverse=True):
        nwk = re.sub(r"(?<=[(,])" + re.escape(old) + r"(?=:)", done[old], nwk)

    # Relabelling must not change the tree. Any structural character smuggled into a label
    # alters the topology silently, and the figure still renders -- so compare tip counts
    # before and after rather than trusting the substitution.
    before = len(re.findall(r"[(,]([^(),:]+):", open(rel_tf).read()))
    after = len(re.findall(r"[(,]([^(),:]+):", nwk))
    if before != after:
        print(f'  !! ABORT: relabelling changed the tree -- {before} tips before, {after} after.', '     A label almost certainly contains a newick structural character: ( ) , : ;', sep="\n")
        sys.exit(1)

    out_tf = rel_tf.replace("_relabeled.treefile", "_labeled.treefile")
    open(out_tf, "w").write(nwk)
    print(f"AS tips labelled: {len(done)}")
    if missing:
        print(f"  !! NO TAXONOMY IN SSOT, left bare: {', '.join(sorted(missing))}")

    og = next((lf for lf in re.findall(r"[(,]([^(),:]+):", nwk)
               if og_hint.upper() in lf.upper()), "")
    r = subprocess.run([PY, RENDER, out_tf, outpng, title, og], capture_output=True, text=True)
    print(r.stdout[-300:] or r.stderr[-400:])
    sys.exit(r.returncode)
