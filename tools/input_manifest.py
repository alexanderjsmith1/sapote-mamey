#!/usr/bin/env python3
"""input_manifest.py — the "no wrong / no half files" guard (portable, stdlib only).

Every analysis that consumes a set of input files should run this to emit, beside its output:
  <label>_INPUT_MANIFEST.tsv   one row per input actually consumed: key, path, sha256, size, channel
  <label>_COVERAGE_REPORT.md   consumed vs the AUTHORITATIVE denominator -> explicit GAP list

Why: "grabbed the wrong file / stale cut / only half the cohort" must be *detectable*, not silent. The
manifest pins every input by sha256 + its NODE.rNNN / strain key; the coverage report states the denominator
up front and lists every gap. See memory workflow-hardening-and-lab-office.

Usage:
  # manifest + coverage for a set of genome files, keyed by strain, vs an authoritative strain list
  python Tools/input_manifest.py --label ANI_pseudonocardiaceae --out <dir> \
      --inputs <dir-or-glob-or-files...> --key-mode strain \
      --denominator <file: one expected key per line>   # optional; omit to skip coverage

  # key modes: strain (AS-\\d+ / SID\\d+), noderegion (NODE..regionNNN), basename (filename stem)
Exit: 0 if (no denominator) or (coverage complete); 3 if any expected key is missing (a real gap).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, hashlib, os, re, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open

STRAIN_RE = re.compile(r"(AS-\d+|AJS-\d+|SID\d+|PENDING-\w+)", re.I)
NODEREG_RE = re.compile(r"(NODE_\d+_length_\d+_cov_\d+(?:\.\d+)?\.?region\d+|NODE_\d+.*?region\d+)", re.I)


def sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


def key_of(path, mode):
    base = os.path.basename(path)
    if mode == "strain":
        m = STRAIN_RE.search(base)
        return m.group(1) if m else base.rsplit(".", 1)[0]
    if mode == "noderegion":
        m = NODEREG_RE.search(base)
        return m.group(1) if m else base.rsplit(".", 1)[0]
    return base.rsplit(".", 1)[0]  # basename


def expand_inputs(items):
    out = []
    for it in items:
        if os.path.isdir(it):
            for root, _, files in os.walk(it):
                for f in files:
                    out.append(os.path.join(root, f))
        elif any(c in it for c in "*?["):
            out.extend(glob.glob(it))
        elif os.path.isfile(it):
            out.append(it)
        else:
            emit(f"WARN: input not found: {it}", file=sys.stderr)
    return sorted(set(out))


def load_denominator(path):
    keys = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # accept a bare key or the first column of a csv/tsv
        keys.append(re.split(r"[,\t]", s)[0].strip())
    return keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--key-mode", default="strain", choices=["strain", "noderegion", "basename"])
    ap.add_argument("--channel", default="", help="source channel tag written into every row")
    ap.add_argument("--denominator", help="file of expected keys (one per line / first csv col)")
    ap.add_argument("--denominator-name", default="authoritative set")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    paths = expand_inputs(args.inputs)
    rows = []
    for p in paths:
        rows.append((key_of(p, args.key_mode), p, sha256(p), os.path.getsize(p)))
    # manifest
    man = os.path.join(args.out, f"{args.label}_INPUT_MANIFEST.tsv")
    # v9.7.374 fix: was a bare open(man, "w") -- ironic given this tool's own stated purpose
    # ("grabbed the wrong file / stale cut / only half the cohort must be detectable, not
    # silent"): a killed process mid-write left a truncated manifest that is itself exactly the
    # kind of undetectable half-file this tool exists to catch. atomic_open (tools/_wbio.py) is
    # the established drop-in for this multi-write-loop shape.
    with atomic_open(man) as fh:
        fh.write("key\tpath\tsha256\tsize_bytes\tchannel\n")
        for k, p, h, s in rows:
            fh.write(f"{k}\t{p}\t{h}\t{s}\t{args.channel}\n")
    consumed = sorted({r[0] for r in rows})
    dup = len(rows) - len({r[1] for r in rows})

    # coverage
    exit_code = 0
    cov = os.path.join(args.out, f"{args.label}_COVERAGE_REPORT.md")
    now = datetime.date.today().isoformat()
    with atomic_open(cov) as fh:  # v9.7.374 fix: same non-atomic-write class as the manifest above
        fh.write(f"# Coverage report — {args.label}\n\n**Date:** {now} · **key-mode:** {args.key_mode}\n\n")
        fh.write(f"- **Inputs consumed:** {len(rows)} files → {len(consumed)} unique keys\n")
        fh.write(f"- **Manifest (sha256-pinned):** `{os.path.basename(man)}`\n")
        if args.denominator:
            expected = load_denominator(args.denominator)
            exp_set, con_set = set(expected), set(consumed)
            missing = sorted(exp_set - con_set)
            extra = sorted(con_set - exp_set)
            pct = 100.0 * len(con_set & exp_set) / len(exp_set) if exp_set else 0.0
            fh.write(f"- **Authoritative denominator ({args.denominator_name}):** {len(exp_set)} expected keys\n")
            fh.write(f"- **Coverage:** {len(con_set & exp_set)} / {len(exp_set)} = **{pct:.1f}%**\n\n")
            if missing:
                exit_code = 3
                fh.write(f"## ⚠ GAP — {len(missing)} expected key(s) NOT consumed (investigate before trusting results)\n")
                for k in missing:
                    fh.write(f"- {k}\n")
                fh.write("\n")
            else:
                fh.write("## ✅ No gap — every expected key was consumed\n\n")
            if extra:
                fh.write(f"## Extra — {len(extra)} consumed key(s) NOT in the denominator (verify these belong)\n")
                for k in extra:
                    fh.write(f"- {k}\n")
                fh.write("\n")
        else:
            fh.write("- **Coverage:** (no denominator supplied — manifest only; supply --denominator to gap-check)\n\n")
        if dup:
            fh.write(f"## Note — {dup} duplicate path(s) collapsed\n\n")
        fh.write("_Claim-safety: coverage ≠ correctness; a complete manifest proves inputs were seen, not that "
                 "the analysis is right. Denominators are class-level counts. See workflow-hardening-and-lab-office._\n")
    emit(f"[input_manifest] {args.label}: {len(rows)} files / {len(consumed)} keys -> {man}", f"[input_manifest] coverage -> {cov} (exit {exit_code})", sep="\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
