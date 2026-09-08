"""Portable handoff bundler (v9.7.199).

A sealed Mamey package is a complete portable analysis substrate for another chat: explain,
list-bgcs, resume, emit-modeb-template, guide skeletons, cross-strain, and ingest all run on
the sealed package with no raw antiSMASH ZIP. The ONE gap is the online BLASTp channel
(blastp-online, which authors Mode B §4/§8/§27/§28) — it needs per-CDS amino-acid sequences,
which a sealed package does not carry but the antiSMASH region GBKs do.

`build_handoff` packs the sealed package plus the region GBKs (all, or just the top-N leads')
into ONE zip, so a receiving chat can do the FULL workflow including online BLASTp — without
re-uploading the 20-120 MB raw antiSMASH ZIP. For colli: package (16 MB) + all 70 region GBKs
(2.8 MB) vs the 120 MB raw ZIP.

Deterministic and offline (stdlib only). Fail-soft: a missing input ZIP yields a package-only
handoff with an explicit note, never a crash.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
import csv, glob, zipfile
from pathlib import Path

from .packaging import _package_files_fail_closed, _zip_compression


def _crosswalk_path(package_dir: Path) -> Path | None:
    m = sorted(package_dir.glob("*_2b_bgc_crosswalk.csv"))
    return m[0] if m else None


def _triage_path(package_dir: Path) -> Path | None:
    m = sorted(package_dir.glob("*_4_triage_board.csv"))
    return m[0] if m else None


def _bgc_to_source_gbk(package_dir: Path) -> dict[str, str]:
    """bgc_id -> source_gbk basename, from the crosswalk (authoritative BGC->region GBK map)."""
    cw = _crosswalk_path(package_dir)
    out: dict[str, str] = {}
    if not cw:
        return out
    with cw.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            src = (row.get("source_gbk") or "").strip()
            bid = (row.get("bgc_id") or "").strip()
            if bid and src:
                out[bid] = Path(src).name
    return out


def _top_n_bgcs(package_dir: Path, n: int) -> list[str]:
    """Top-N BGC_IDs by triage Corrected_rank (ascending; rank 1 first), falling back to raw
    Rank only when Corrected_rank is absent (e.g. an older package)."""
    tb = _triage_path(package_dir)
    if not tb:
        return []
    rows = []
    with tb.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            bid = (row.get("BGC_ID") or "").strip()
            # v9.7.371 fix: was Rank-first. Rank is the raw score-sorted position over ALL BGCs
            # including standing-rule-excluded/primary-metabolism rows; Corrected_rank is the
            # sequential rank over rows that survived exclusion (excluded rows get
            # corrected_rank=None -> ""). Every other consumer of these two columns in this
            # codebase checks Corrected_rank first (blastp_autoharness.py, compile_report.py,
            # locus_map.py, modeb_template_emitter.py, package_addons.py, report_card.py,
            # strain_modeb.py, session_resume.py, widget_deliverable.py) -- this file alone had
            # it backwards, so an excluded/downgraded BGC with a high raw Rank could win the sort
            # and ship as a "top-N lead" region GBK while a genuine top lead was omitted.
            rank = row.get("Corrected_rank") or row.get("Rank") or ""
            try:
                rk = float(rank)
            except (TypeError, ValueError):
                rk = float("inf")
            if bid:
                rows.append((rk, bid))
    rows.sort(key=lambda t: t[0])
    return [bid for _, bid in rows[:n]]


def build_handoff(package_dir: str | Path, input_zip: str | Path | None,
                  out_zip: str | Path, top_n: int | None = None) -> dict:
    """Pack a sealed package + its region GBKs into one portable handoff zip.

    top_n=None  -> ALL region GBKs from input_zip (robust default).
    top_n=N     -> only the top-N triage-ranked leads' region GBKs (leaner handoff).
    input_zip=None -> package-only handoff (triage/skeletons work; online BLASTp will not).
    Returns a summary dict.
    """
    package_dir = Path(package_dir)
    out_zip = Path(out_zip)
    if not package_dir.is_dir():
        raise ValueError(f"not a package directory: {package_dir}")
    package_files = _package_files_fail_closed(package_dir)

    wanted_basenames: set[str] | None = None  # None => all region GBKs
    selected_bgcs: list[str] = []
    if top_n is not None and input_zip is not None:
        selected_bgcs = _top_n_bgcs(package_dir, top_n)
        xmap = _bgc_to_source_gbk(package_dir)
        wanted_basenames = {xmap[b] for b in selected_bgcs if b in xmap}
        if not wanted_basenames:  # mapping failed -> fall back to all, don't silently ship none
            wanted_basenames = None

    region_gbks: list[tuple[str, bytes]] = []
    note = None
    if input_zip is not None:
        input_zip = Path(input_zip)
        if not input_zip.exists():
            note = f"input_zip not found ({input_zip}); shipping package-only handoff (no online BLASTp)."
        else:
            with zipfile.ZipFile(input_zip) as z:
                for info in z.infolist():
                    name = Path(info.filename).name
                    if ".region" in name and name.endswith(".gbk"):
                        if wanted_basenames is None or name in wanted_basenames:
                            region_gbks.append((name, z.read(info.filename)))
    else:
        note = "no input_zip supplied; package-only handoff (triage/skeletons OK, online BLASTp will not run)."

    # v9.7.374 fix: the previous sequence deleted any pre-existing out_zip BEFORE writing the new
    # one, then wrote zipfile.ZipFile's central directory only at close() time. A crash/kill mid-write
    # left NEITHER the old handoff.zip (already unlinked) NOR a valid new one (no central directory
    # yet) -- worse than an ordinary overwrite, which at least fails closed on the old content. Build
    # into a tmp sibling and only replace the real target after the archive is fully written and closed.
    tmp_out_zip = out_zip.with_name(out_zip.name + ".tmp")
    if tmp_out_zip.exists():
        tmp_out_zip.unlink()
    with zipfile.ZipFile(tmp_out_zip, "w", _zip_compression()) as z:
        for p in package_files:
            z.write(p, Path("package") / p.relative_to(package_dir))
        for name, data in region_gbks:
            z.writestr(f"region_gbks/{name}", data)
        readme = (
            "SAPOTE-MAMEY PORTABLE HANDOFF\n"
            "=============================\n"
            "package/       - sealed Mamey package (explain, list-bgcs, resume, emit-modeb-template,\n"
            "                 guide skeletons, cross-strain, ingest all run on this directly).\n"
            "region_gbks/   - antiSMASH region GBKs so `mamey blastp-online` can author Mode B\n"
            "                 §4/§8/§27/§28 without the raw antiSMASH ZIP.\n\n"
            f"region GBKs included: {len(region_gbks)}"
            + (f" (top-{top_n} leads: {', '.join(selected_bgcs)})" if (top_n and selected_bgcs and wanted_basenames is not None) else " (all regions)")
            + "\n"
            + (f"NOTE: {note}\n" if note else "")
        )
        z.writestr("HANDOFF_README.txt", readme)
    tmp_out_zip.replace(out_zip)

    return {"out_zip": str(out_zip), "region_gbks": len(region_gbks),
            "top_n": top_n, "selected_bgcs": selected_bgcs, "note": note,
            "bytes": out_zip.stat().st_size}


def handoff_command(args) -> int:
    """`mamey handoff --package <pkg> [--input-zip <raw.zip>] [--top-n N] --out <handoff.zip>`."""
    top_n = getattr(args, "top_n", None)
    # v9.7.409 (AUDIT_cli_edgecases): build_handoff raises ValueError ("not a package directory")
    # on a nonexistent/invalid package; it used to reach the terminal as a raw traceback. Catch it
    # at the command boundary and refuse cleanly (one-line ERROR, rc 1), like the sibling readers.
    try:
        res = build_handoff(args.package, getattr(args, "input_zip", None), args.out, top_n=top_n)
    except ValueError as exc:
        import sys
        emit(f"ERROR: {exc}", file=sys.stderr)
        return 1
    mb = res["bytes"] / 1048576
    emit(f"handoff -> {res['out_zip']} ({mb:.1f} MB)", f"  region GBKs: {res['region_gbks']}" + (f"  (top-{top_n}: {', '.join(res['selected_bgcs'])})" if top_n and res['selected_bgcs'] else '  (all regions)'), sep="\n")
    if res["note"]:
        emit(f"  NOTE: {res['note']}")
    return 0
