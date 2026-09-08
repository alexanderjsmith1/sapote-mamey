#!/usr/bin/env python3
r"""fetch_mibig_reference.py — turn a MIBiG accession into a reference GBK from the PUBLIC repo.

The KCB front page hands you a MIBiG accession for every known-cluster hit (e.g. "BGC0000116.5 |
nystatin-like ..."), but the comparative chain could only obtain that reference from the private
anchored BiG-SCAPE DB (fetch_reference_cluster --acc) — MIBiG IDs are not NCBI nucleotide
accessions, so --ncbi cannot reach them either. Anyone without the DB was stuck. This closes that
gap: it pulls the reference GBK straight from MIBiG's public repository
(dl.secondarymetabolites.org), so a KCB hit becomes a comparison-ready reference with no DB.

MIBiG only ships per-release tarballs (no per-entry URL), so this downloads the release GBK
tarball ONCE into a cache and extracts the requested accession(s). Output GBKs are named
<label>.gbk — the same convention fetch_reference_cluster uses — so they drop straight into
cluster_gene_compare / cluster_relate / cluster_completeness / cluster_brief.

    fetch_mibig_reference.py --acc BGC0000116:nystatin_ref --acc BGC0000877:polyoxin --outdir refs/

CLAIM DISCIPLINE: a MIBiG reference is a COMPARISON ANCHOR, not a product assignment. Similarity
to it is capacity/architecture-level, never identity. This tool only fetches the reference; the
comparison tools decide what the similarity means.

stdlib only. Network: dl.secondarymetabolites.org (MIBiG). Deterministic given a fixed release.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, os, re, tarfile, argparse, urllib.request
from pathlib import Path

_REPO = "https://dl.secondarymetabolites.org/mibig"
_DEFAULT_CACHE = os.path.expanduser("~/.cache/mibig")
_ACC_RE = re.compile(r"(BGC\d{7})")


def canonical_acc(field):
    """Extract the canonical MIBiG accession from a KCB_top-style field.

    'BGC0000116.5 | nystatin-like ...' -> 'BGC0000116' (the trailing '.5' is a clusterblast
    rank, not a version; the MIBiG file is BGC0000116.gbk).
    """
    m = _ACC_RE.search(field or "")
    return m.group(1) if m else None


def _tarball_path(cache, version):
    return os.path.join(cache, f"mibig_gbk_{version}.tar.gz")


def ensure_tarball(cache, version, timeout=600, log=lambda s: None):
    """Return the cached tarball path, downloading it once if absent."""
    os.makedirs(cache, exist_ok=True)
    path = _tarball_path(cache, version)
    if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
        return path
    url = f"{_REPO}/mibig_gbk_{version}.tar.gz"
    log(f"downloading {url} (one-time cache → {path})")
    tmp = path + ".part"
    with urllib.request.urlopen(url, timeout=timeout) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    os.replace(tmp, path)
    return path


def _extract_from_tarball(tar_path, specs, version="4.0", outdir="refs", log=lambda s: None):
    """Extract requested accessions from a (already-present) tarball. No network.

    specs: list of 'ACCESSION:label'. Returns (written, missing).
    """
    os.makedirs(outdir, exist_ok=True)
    want, bad = {}, []
    for spec in specs:
        acc_field, label = (spec.split(":", 1) + [None])[:2] if ":" in spec else (spec, None)
        acc = canonical_acc(acc_field)
        if not acc:
            bad.append(spec)
            continue
        want[acc] = label or acc
    written, missing = [], list(bad)
    if not want:
        return written, missing
    member_prefix = f"mibig_gbk_{version}/"
    with tarfile.open(tar_path, "r:gz") as tf:
        names = set(tf.getnames())
        for acc, label in want.items():
            member = f"{member_prefix}{acc}.gbk"
            if member not in names:
                missing.append(acc)
                continue
            data = tf.extractfile(member).read()
            out = os.path.join(outdir, f"{label}.gbk")
            Path(out).write_bytes(data)
            written.append((acc, label, out))
            log(f"{acc} → {out} ({len(data)} bytes)")
    return written, missing


def extract_refs(specs, version="4.0", cache=_DEFAULT_CACHE, outdir="refs", log=lambda s: None):
    """specs: list of 'ACCESSION:label'. Downloads the release tarball once (cached), then extracts."""
    tar_path = ensure_tarball(cache, version, log=log)
    return _extract_from_tarball(tar_path, specs, version=version, outdir=outdir, log=log)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch MIBiG reference GBK(s) from the public repo (no anchored DB).")
    ap.add_argument("--acc", action="append", default=[], required=True, metavar="ACCESSION:label",
                    help="MIBiG accession (BGCxxxxxxx, trailing rank tolerated), repeatable")
    ap.add_argument("--version", default="4.0", help="MIBiG release (default 4.0)")
    ap.add_argument("--cache", default=_DEFAULT_CACHE, help=f"tarball cache dir (default {_DEFAULT_CACHE})")
    ap.add_argument("--outdir", default="refs")
    a = ap.parse_args(argv)

    def log(s):
        emit(f"[fetch_mibig_reference] {s}", file=sys.stderr)

    try:
        written, missing = extract_refs(a.acc, version=a.version, cache=a.cache,
                                        outdir=a.outdir, log=log)
    except Exception as e:
        emit(f"[fetch_mibig_reference] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    for acc, label, out in written:
        emit(out)
    if missing:
        emit(f"[fetch_mibig_reference] NOT FOUND in MIBiG {a.version}: {', '.join(missing)}",
              file=sys.stderr)
    log(f"{len(written)} reference GBK(s) ready for cluster_gene_compare / cluster_brief.")
    return 0 if written and not missing else (0 if written else 1)


if __name__ == "__main__":
    sys.exit(main())
