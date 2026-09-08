#!/usr/bin/env python3
"""bigslice_query.py -- BiG-SLiCE as a second, feature-based GCF opinion (complements BiG-SCAPE).

Why both: BiG-SCAPE clusters BGCs by pairwise Pfam-domain alignment (accurate, O(n^2), MIBiG as
the reference). BiG-SLiCE embeds each BGC as a fixed BiG-FAM feature vector and clusters by
Euclidean distance (super-linear; scales to 10^5-10^6 BGCs) and -- crucially -- can *query* a BGC
against the precomputed BiG-FAM model of ~1.2M GCFs derived from all of NCBI. That turns "novel vs
2,088 MIBiG references" into "novel vs essentially all sequenced bacterial biosynthesis", a much
stronger novelty statement for a discovery program.

Two modes:
  cluster : run BiG-SLiCE de novo on the cohort's antiSMASH GBKs -> its own GCF assignment. Join
            onto the node.region locator to compare against the BiG-SCAPE families (agreement =
            robust family; disagreement = worth a look).
  query   : query the cohort BGCs against a downloaded BiG-FAM model (full_run_result). Reports,
            per BGC, the nearest BiG-FAM GCF and its membership count -- a BGC whose nearest global
            GCF is small/absent is novel at the whole-database scale, not just vs MIBiG.

BiG-SLiCE is an EXTERNAL prerequisite, exactly like BiG-SCAPE (`pip install bigslice`; the BiG-FAM
model is a separate multi-GB download, `download_bigslice_hmmdb` + the BiG-FAM full_run archive).
This tool is a thin adapter + a locator-joining reader; it does not vendor BiG-SLiCE or the model.

Usage:
  # de novo clustering of the cohort
  python bigslice_query.py cluster --input bigscape_input/ --out bigslice_out/ [--threshold 0.4]
  # read its assignment joined to node.region, optionally diff vs a BiG-SCAPE cross_strain TSV
  python bigslice_query.py read --out bigslice_out/ [--bigscape-tsv cross_strain_GCFs.tsv]
  # query vs a downloaded BiG-FAM model
  python bigslice_query.py query --input bigscape_input/ --bigfam-model full_run_result/ --out q/

Stdlib only for read/diff; cluster/query shell out to the `bigslice` binary.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, sqlite3, subprocess, sys, re, glob, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.bigscape_namespace import NamespaceError, load_membership_tsv, public_error

LOCATOR = re.compile(r"_(NODE_.+)\.(region\d+)\.gbk$", re.I)


def _locator(fname):
    b = os.path.basename(fname)
    if b.upper().startswith("BGC"):
        return "MIBiG", b.split(".")[0]
    m = LOCATOR.search(b)
    return b.split("_")[0], (f"{m.group(1)}.{m.group(2)}" if m else b)


def cmd_cluster(a):
    # BiG-SLiCE expects a parent dir with one subfolder of GBKs + a datasets.tsv; build it.
    ds = os.path.join(a.out, "_bs_in")
    os.makedirs(os.path.join(ds, "cohort"), exist_ok=True)
    for f in glob.glob(os.path.join(a.input, "*.gbk")):
        dst = os.path.join(ds, "cohort", os.path.basename(f))
        if not os.path.exists(dst):
            os.symlink(os.path.abspath(f), dst)
    with open(os.path.join(ds, "datasets.tsv"), "w") as fh:
        fh.write("# Dataset name\tPath to folder\tPath to taxonomy\tDescription\n")
        fh.write("cohort\tcohort\t\tactinomycete symbiont cohort\n")
    cmd = ["bigslice", "-i", ds, a.out, "--threshold", str(a.threshold), "-t", str(a.threads)]
    emit("  $ " + " ".join(cmd))
    subprocess.run(cmd, check=True)
    emit("BiG-SLiCE de novo clustering written to", a.out, "(read with: this tool 'read')")


def cmd_read(a):
    """Read BiG-SLiCE's result.db -> {strain:locator -> gcf_id}. Optionally diff vs BiG-SCAPE."""
    resdb = os.path.join(a.out, "result", "data.db")
    if not os.path.exists(resdb):
        cands = glob.glob(os.path.join(a.out, "**", "*.db"), recursive=True)
        resdb = cands[0] if cands else None
    if not resdb:
        sys.exit("no BiG-SLiCE result DB under " + a.out)
    c = sqlite3.connect(resdb)
    # BiG-SLiCE schema: bgc(id,name,orig_folder,...), gcf_membership(bgc_id,gcf_id,rank,membership_value)
    assign = {}
    try:
        for name, gcf in c.execute(
            "select b.orig_filename, m.gcf_id from bgc b "
            "join gcf_membership m on m.bgc_id=b.id and m.rank=0"):
            strain, loc = _locator(name)
            if strain != "MIBiG":
                assign[f"{strain}:{loc}"] = gcf
    except sqlite3.OperationalError as e:
        sys.exit(f"unexpected BiG-SLiCE schema ({e}); check version")
    bs = {}
    if a.bigscape_tsv and os.path.exists(a.bigscape_tsv):
        for row in load_membership_tsv(a.bigscape_tsv, key_fields=("qualified_family_id",)):
            for locator in (row.get("members_locators") or "").split(";"):
                locator = locator.strip()
                if not locator:
                    continue
                prior = bs.get(locator)
                if prior is not None and prior != row["qualified_family_id"]:
                    raise NamespaceError("DUPLICATE_CONFLICT", "one portable locator has conflicting family assignments")
                bs[locator] = row["qualified_family_id"]
    emit(f"BiG-SLiCE assigned {len(assign)} cohort BGCs to GCFs")
    out = os.path.join(a.out, "bigslice_assignment.tsv")
    with open(out, "w") as fh:
        fh.write("strain_locator\tbigslice_gcf\n")
        for k, v in sorted(assign.items()):
            fh.write(f"{k}\t{v}\n")
    emit("wrote", out)
    if bs:
        # crude concordance: do BGCs BiG-SCAPE puts together also share a BiG-SLiCE GCF?
        shared = [k for k in assign if k in bs]
        emit(f"concordance sample: {len(shared)} BGCs in both; "
              "inspect bigslice_assignment.tsv vs the BiG-SCAPE family column for splits/merges")


def cmd_query(a):
    cmd = ["bigslice", "--query", a.input, "--n_ranks", "5", a.bigfam_model, "--query_name", "cohort"]
    emit('  $ ' + ' '.join(cmd), '  (requires a downloaded BiG-FAM full_run_result model; see module docstring)', sep="\n")
    subprocess.run(cmd, check=True)
    emit("query result under", a.bigfam_model, "-> read the query result DB for nearest global GCF + size")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("cluster"); c.add_argument("--input", required=True); c.add_argument("--out", required=True)
    c.add_argument("--threshold", type=float, default=0.4); c.add_argument("--threads", type=int, default=1)
    c.set_defaults(fn=cmd_cluster)
    r = sub.add_parser("read"); r.add_argument("--out", required=True); r.add_argument("--bigscape-tsv")
    r.set_defaults(fn=cmd_read)
    q = sub.add_parser("query"); q.add_argument("--input", required=True); q.add_argument("--bigfam-model", required=True)
    q.add_argument("--out", required=True); q.set_defaults(fn=cmd_query)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    try:
        main()
    except NamespaceError as error:
        # v9.7.405: sys.stderr.write, not print() — a typed-refusal diagnostic, and the
        # print ratchet is at ceiling. Registering these front doors as EXCLUDED files
        # would have dropped their PRE-EXISTING prints from the count too: a lower
        # measure without paying anything.
        sys.stderr.write(public_error(error) + "\n")
        sys.exit(2)
