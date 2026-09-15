#!/usr/bin/env python3
"""Validate a frozen GToTree execution packet before launch or postflight.

v9.7.432 (TREES_432 tree round) adds two typed post-run gates that any GToTree/IQ-TREE
launcher (``run_planned_tree.py``, a native GToTree v2 ``-T IQTREE`` run, ``build_tree.sh``)
must pass before a tree may be called built:

  * ``iqtree_completion(prefix_or_dir)`` — a build is COMPLETE only when ``<prefix>.contree``
    exists and is non-empty, ``<prefix>.treefile`` carries numeric support labels, and
    ``<prefix>.log`` contains "Total wall-clock time". A bare ``.treefile`` is INTERRUPTED.
  * ``tip_retention(...)`` — GToTree's "too few SCG hits" filter can drop a genome and still
    exit 0. Every staged genome is declared intent; a dropped QUERY is a hard failure
    (``QUERY_TIP_DROPPED``) with the genome named and its SCG-hit line quoted.

Both return typed dicts; nothing here raises on the happy path and nothing silently passes.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re
import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import logging as _logging  # noqa: E402
import sys as _sys_for_log  # noqa: E402
_LOG = _logging.getLogger(__name__)
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path

# GToTree output spellings: v1.8 writes Aligned_SCGs.faa, v2.0 writes aligned-SCGs.faa.
ALIGNMENT_NAMES = ("aligned-SCGs.faa", "Aligned_SCGs.faa", "Aligned_SCGs_mod_names.faa")
V2_IQTREE_SUBDIR = os.path.join("run-files", "iqtree-out")
V2_REMOVED_GENOMES = os.path.join("run-files", "removed-genomes.tsv")
V2_GENOME_SUMMARY = "genomes-summary-info.tsv"
V2_SCG_HIT_COUNTS = "SCG-hit-counts.tsv"
V2_NO_REMOVAL_LINE = "No genomes were removed due to having too few SCG hits"
WALL_CLOCK_MARKER = "Total wall-clock time"
# ")95:" / ")95/99:" / ")0.98:" — a numeric label directly after a close-paren = support present.
_SUPPORT_RE = re.compile(r"\)\s*[0-9]+(?:\.[0-9]+)?(?:/[0-9]+(?:\.[0-9]+)?)?\s*:")
_ACCEPTED_GTOTREE_VERSIONS = re.compile(r"(?:^|\D)(?:1\.8\.19|2\.0\.\d+)(?:\D|$)")


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def validate(packet, root, postflight=False):
    root=Path(root).resolve()
    for key in ("run_id","gtotree","hmm","panel","working_directory","output_directory","max_concurrent_jobs"):
        if key not in packet: raise ValueError("PACKET_FIELD_MISSING: "+key)
    gt=packet["gtotree"]; hmm=packet["hmm"]
    # v9.7.432: the installed and documented GToTree is v2.0.0; 1.8.19 stays accepted for the
    # standalone tree. Anything else (e.g. the conda env's 1.8.16) is still refused.
    if not _ACCEPTED_GTOTREE_VERSIONS.search(str(gt.get("version",""))):
        raise ValueError("GTOTREE_VERSION: production packet requires 1.8.19 or 2.0.x")
    for label,item in (("GTOTREE",gt),("HMM",hmm)):
        path=Path(item.get("path","")).resolve()
        if not path.is_file() or digest(path)!=item.get("sha256"):
            raise ValueError(label+"_IDENTITY")
    work=Path(packet["working_directory"]).resolve(); out=Path(packet["output_directory"]).resolve()
    if work==root or out==root or work==out or root not in work.parents or root not in out.parents:
        raise ValueError("RUN_DIRECTORY_ISOLATION")
    jobs=int(packet["max_concurrent_jobs"])
    if jobs < 1 or jobs > 4: raise ValueError("CONCURRENCY_CAP")
    panel=packet["panel"]
    if not panel or len({r.get("tip") for r in panel}) != len(panel): raise ValueError("PANEL_IDENTITY")
    seen=set()
    for row in panel:
        p=Path(row.get("genome_path","")).resolve()
        if not p.is_file() or digest(p)!=row.get("sha256"): raise ValueError("GENOME_IDENTITY: "+str(row.get("tip")))
        if row.get("sha256") in seen: raise ValueError("DUPLICATE_GENOME_CONTENT")
        seen.add(row["sha256"])
    if postflight:
        receipt=packet.get("postflight",{})
        retained=set(receipt.get("retained_tips",[])); expected={r["tip"] for r in panel}
        if retained != expected: raise ValueError("SILENT_TIP_LOSS")
        if not receipt.get("alignment_path") or not Path(receipt["alignment_path"]).is_file():
            raise ValueError("ALIGNMENT_MISSING")
    return {"status":"GTOTREE_EXECUTION_GATE_PASS", "panel_size":len(panel),
            "postflight":bool(postflight), "ceiling":"Execution identity/QC only; no biological conclusion."}


# ----------------------------------------------------------------------------------------------
# Card TREES_432_build_completion_gate_requires_contree
# ----------------------------------------------------------------------------------------------
def _iqtree_prefix(prefix_or_dir):
    """Accept an IQ-TREE prefix (``.../iqtree``), a GToTree v2 output dir (``<out>/`` ->
    ``<out>/run-files/iqtree-out/iqtree``), or a dir that directly holds ``iqtree.*``."""
    p = Path(prefix_or_dir)
    if p.is_dir():
        v2 = p / V2_IQTREE_SUBDIR / "iqtree"
        if (p / V2_IQTREE_SUBDIR).is_dir():
            return v2
        return p / "iqtree"
    return p


def support_node_count(tree_text):
    return len(_SUPPORT_RE.findall(tree_text))


def iqtree_completion(prefix_or_dir):
    """Typed completion status for one IQ-TREE run. Never raises for a missing/partial run.

    Returns ``{"status": "COMPLETE" | "INTERRUPTED" | "MISSING", "prefix", "reasons": [...],
    "support_nodes", "last_log_line", "treefile", "contree", "log"}``.
    COMPLETE requires ALL of: non-empty .contree, numeric support labels on .treefile,
    "Total wall-clock time" in .log. Anything else is INTERRUPTED (or MISSING when there is
    no .treefile at all).
    """
    prefix = _iqtree_prefix(prefix_or_dir)
    treefile = Path(str(prefix) + ".treefile")
    contree = Path(str(prefix) + ".contree")
    log = Path(str(prefix) + ".log")
    reasons, support_nodes, last_line = [], 0, ""
    if not treefile.is_file() or treefile.stat().st_size == 0:
        reasons.append(f"TREEFILE_MISSING: {treefile}")
    else:
        support_nodes = support_node_count(treefile.read_text(encoding="utf-8", errors="replace"))
        if support_nodes == 0:
            reasons.append(f"TREEFILE_NO_SUPPORT: {treefile.name} has no numeric internal-node labels "
                           "(ML topology written before the bootstrap finished)")
    if not contree.is_file() or contree.stat().st_size == 0:
        reasons.append(f"CONTREE_MISSING: {contree} absent or empty (bootstrap did not finish)")
    if not log.is_file():
        reasons.append(f"LOG_MISSING: {log}")
    else:
        lines = [ln.rstrip("\n") for ln in log.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
        last_line = lines[-1] if lines else ""
        if not any(WALL_CLOCK_MARKER in ln for ln in lines):
            reasons.append(f"LOG_NO_WALLCLOCK: '{WALL_CLOCK_MARKER}' not in {log.name}; last line: {last_line!r}")
    if not reasons:
        status = "COMPLETE"
    elif any(r.startswith("TREEFILE_MISSING") for r in reasons):
        status = "MISSING"
    else:
        status = "INTERRUPTED"
    return {"status": status, "prefix": str(prefix), "reasons": reasons, "support_nodes": support_nodes,
            "last_log_line": last_line, "treefile": str(treefile), "contree": str(contree), "log": str(log)}


# ----------------------------------------------------------------------------------------------
# Card TREES_432_query_tip_dropped_by_scg_filter_without_failure
# ----------------------------------------------------------------------------------------------
def tip_from_genome_path(path):
    """GToTree tip label = FASTA basename minus one extension (``genomes/QUERY-1.fna`` -> ``QUERY-1``;
    ``x.fna.gz`` -> ``x``)."""
    name = os.path.basename(str(path).strip())
    for ext in (".gz",):
        if name.endswith(ext):
            name = name[: -len(ext)]
    stem, _dot, _ext = name.rpartition(".")
    return stem or name


def read_genome_list(path):
    with open(path, encoding="utf-8") as fh:
        return [ln.rstrip("\n") for ln in fh if ln.strip()]


def find_alignment(out_dir):
    for name in ALIGNMENT_NAMES:
        cand = Path(out_dir) / name
        if cand.is_file():
            return str(cand)
    return None


def gtotree_retained_tips(out_dir):
    """Tips that actually reached the alignment (works for v1.8 and v2.0 spellings). The
    alignment headers are the authoritative retained set; the log is only a cross-check."""
    aln = find_alignment(out_dir)
    if not aln:
        return None
    tips = []
    with open(aln, encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            if ln.startswith(">"):
                tips.append(ln[1:].strip().split()[0])
    return tips


def gtotree_removal_reasons(out_dir):
    """{tip: reason} from GToTree v2's run-files/removed-genomes.tsv and genomes-summary-info.tsv.
    Empty dict when neither exists (v1.8 output)."""
    out = Path(out_dir)
    reasons = {}
    for rel in (V2_REMOVED_GENOMES, V2_GENOME_SUMMARY):
        f = out / rel
        if not f.is_file():
            continue
        with f.open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                tip = (row.get("genome_id") or "").strip()
                if not tip:
                    continue
                if rel == V2_GENOME_SUMMARY and (row.get("in_final_tree") or "").strip().lower() != "no":
                    continue
                reason = (row.get("reason_removed") or "").strip()
                stage = (row.get("stage_removed") or "").strip()
                reasons.setdefault(tip, (reason + (f" (stage {stage})" if stage else "")) or "removed (reason not stated)")
    return reasons


def scg_hit_line(out_dir, tip):
    """The genome's own row from SCG-hit-counts.tsv as ``{'unique': n, 'total': n, 'multi_copy': n,
    'markers': n}`` plus the raw line, or None when the file/row is absent."""
    f = Path(out_dir) / V2_SCG_HIT_COUNTS
    if not f.is_file():
        return None
    with f.open(encoding="utf-8", errors="replace") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for ln in fh:
            cells = ln.rstrip("\n").split("\t")
            if cells and cells[0] == tip:
                counts = []
                for c in cells[1:]:
                    try:
                        counts.append(int(c))
                    except ValueError:
                        continue  # blank or non-numeric SCG cell; not a hit count
                return {"markers": len(header) - 1, "total": sum(counts),
                        "unique": sum(1 for c in counts if c == 1),
                        "multi_copy": sum(1 for c in counts if c > 1),
                        "absent": sum(1 for c in counts if c == 0),
                        "raw": ln.rstrip("\n")[:200]}
    return None


def runlog_removal_claim(out_dir):
    """What gtotree-runlog.txt says about the SCG-hit filter: 'none', 'removed', or 'unknown'."""
    f = Path(out_dir) / "gtotree-runlog.txt"
    if not f.is_file():
        return "unknown"
    text = f.read_text(encoding="utf-8", errors="replace")
    if V2_NO_REMOVAL_LINE in text:
        return "none"
    if re.search(r"genome\(s\) removed", text):
        return "removed"
    return "unknown"


def declared_query_tips(genome_list_tips, tree_spec=None, query_tips=None):
    """Which expected tips are QUERIES. Explicit ``query_tips`` wins; then TREE_SPEC.json keys
    ``queries`` / ``query_tips`` / ``query_genomes`` (list of tip labels or genome paths); when
    nothing declares roles, every tip is treated as a query — the conservative reading of
    'every staged genome is declared intent'."""
    if query_tips:
        return {tip_from_genome_path(t) for t in query_tips}
    if tree_spec:
        for key in ("queries", "query_tips", "query_genomes"):
            vals = tree_spec.get(key)
            if isinstance(vals, list) and vals:
                return {tip_from_genome_path(v) for v in vals}
    return set(genome_list_tips)


def tip_retention(expected_tips, retained_tips, query_tips, out_dir=None, allow_reference_drop=False):
    """Typed audit of expected vs retained tips.

    ``status``: ``TIPS_RETAINED`` (nothing dropped), ``QUERY_TIP_DROPPED`` (hard; a declared query
    is absent), ``REFERENCE_TIP_DROPPED`` (hard unless ``allow_reference_drop``; then
    ``REFERENCE_TIP_DROPPED_ALLOWED``), ``ALIGNMENT_MISSING`` (retained_tips is None).
    ``dropped``: one row per missing tip with role, GToTree's stated reason, and its SCG-hit line.
    ``unexpected``: tips in the alignment that were not in the genome list (labelling drift).
    """
    expected = list(dict.fromkeys(expected_tips))
    if retained_tips is None:
        return {"status": "ALIGNMENT_MISSING", "dropped": [], "unexpected": [], "expected": expected,
                "retained": [], "runlog_claim": runlog_removal_claim(out_dir) if out_dir else "unknown"}
    retained = set(retained_tips)
    reasons = gtotree_removal_reasons(out_dir) if out_dir else {}
    dropped = []
    for tip in expected:
        if tip in retained:
            continue
        row = {"tip": tip, "role": "query" if tip in query_tips else "reference",
               "reason": reasons.get(tip, "absent from alignment; GToTree gave no reason"),
               "scg_hits": scg_hit_line(out_dir, tip) if out_dir else None}
        dropped.append(row)
    unexpected = sorted(retained - set(expected))
    if any(d["role"] == "query" for d in dropped):
        status = "QUERY_TIP_DROPPED"
    elif dropped:
        status = "REFERENCE_TIP_DROPPED_ALLOWED" if allow_reference_drop else "REFERENCE_TIP_DROPPED"
    else:
        status = "TIPS_RETAINED"
    return {"status": status, "dropped": dropped, "unexpected": unexpected, "expected": expected,
            "retained": sorted(retained), "runlog_claim": runlog_removal_claim(out_dir) if out_dir else "unknown"}


def format_dropped(result):
    lines = []
    for d in result.get("dropped", []):
        hits = d.get("scg_hits") or {}
        hit_txt = (f"; SCG hits: {hits['unique']} single-copy / {hits['multi_copy']} multi-copy / "
                   f"{hits['absent']} absent of {hits['markers']} markers") if hits else ""
        lines.append(f"  {d['role'].upper()} DROPPED: {d['tip']} — {d['reason']}{hit_txt}")
    for u in result.get("unexpected", []):
        lines.append(f"  UNEXPECTED TIP in alignment (not in genome list): {u}")
    return lines


def write_dropped_by_qc(path, result):
    """DROPPED_BY_QC.tsv — one row per dropped genome so the figure caption can say so."""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["tip", "role", "reason", "scg_unique", "scg_multi_copy", "scg_absent", "scg_markers"])
        for d in result.get("dropped", []):
            h = d.get("scg_hits") or {}
            w.writerow([d["tip"], d["role"], d["reason"], h.get("unique", ""), h.get("multi_copy", ""),
                        h.get("absent", ""), h.get("markers", "")])
    return path


def audit_gtotree_output(out_dir, genome_list, tree_spec_path=None, query_tips=None, allow_reference_drop=False):
    """Convenience: genome list + optional TREE_SPEC.json -> tip_retention() on a GToTree out dir."""
    expected = [tip_from_genome_path(p) for p in read_genome_list(genome_list)]
    spec = None
    if tree_spec_path and Path(tree_spec_path).is_file():
        spec = json.loads(Path(tree_spec_path).read_text(encoding="utf-8"))
    queries = declared_query_tips(expected, spec, query_tips)
    return tip_retention(expected, gtotree_retained_tips(out_dir), queries, out_dir, allow_reference_drop)


def main(argv=None):
    _logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys_for_log.stdout)
    p=argparse.ArgumentParser(description="GToTree execution packet gate + post-run completion / tip-retention gates.")
    p.add_argument("packet", nargs="?", help="frozen execution packet JSON (packet mode)")
    p.add_argument("--root", help="run root for packet mode")
    p.add_argument("--postflight",action="store_true")
    p.add_argument("--check-completion", metavar="PREFIX_OR_DIR",
                   help="typed IQ-TREE completion status (.contree + support + wall-clock); accepts an IQ-TREE prefix or a GToTree v2 output dir")
    p.add_argument("--check-tips", metavar="GTOTREE_OUT_DIR", help="tip-retention audit of a GToTree output dir")
    p.add_argument("--genome-list", help="genome list used for the run (with --check-tips)")
    p.add_argument("--tree-spec", help="TREE_SPEC.json declaring query roles (optional, with --check-tips)")
    p.add_argument("--query-tips", help="comma-separated query tip labels (overrides TREE_SPEC)")
    p.add_argument("--allow-reference-drop", action="store_true")
    p.add_argument("--dropped-tsv", help="write DROPPED_BY_QC.tsv here when tips were dropped")
    a=p.parse_args(argv)
    rc = 0
    if a.check_completion:
        res = iqtree_completion(a.check_completion)
        _LOG.info(json.dumps(res, indent=2))
        if res["status"] != "COMPLETE":
            rc = 1
    if a.check_tips:
        if not a.genome_list:
            p.error("--check-tips requires --genome-list")
        qt = [t for t in (a.query_tips or "").split(",") if t.strip()] or None
        res = audit_gtotree_output(a.check_tips, a.genome_list, a.tree_spec, qt, a.allow_reference_drop)
        _LOG.info(json.dumps(res, indent=2))
        if a.dropped_tsv and res["dropped"]:
            write_dropped_by_qc(a.dropped_tsv, res)
        if res["status"] not in ("TIPS_RETAINED", "REFERENCE_TIP_DROPPED_ALLOWED"):
            rc = 1
    if a.packet:
        if not a.root:
            p.error("packet mode requires --root")
        _LOG.info(json.dumps(validate(json.loads(Path(a.packet).read_text()),a.root,a.postflight),indent=2))
    elif not (a.check_completion or a.check_tips):
        p.error("give a packet (with --root), --check-completion, or --check-tips")
    return rc
if __name__=="__main__":raise SystemExit(main())
