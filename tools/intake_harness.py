#!/usr/bin/env python3
"""intake_harness.py — multi-strain intake for Sapote-Mamey with performance metrics.

Drives a batch of genome zips through the engine + the class-aware Diagnostic Rescue layer, captures
per-strain wall-time and peak RSS, and appends to a persistent cross-batch registry. Built to grow a
diagnostic-rescue validation set across many small batches.

INPUT TYPES (auto-detected per zip):
  - antiSMASH 8 output (region*.gbk present)  -> staged, run, rescued, metered
  - raw assembly (.fna/.fasta only)           -> recorded NEEDS_ANTISMASH, not run (needs antiSMASH first)

USAGE:
  python tools/intake_harness.py --inputs <dir|zip...> --outdir runs/ \
      --registry out/intake_registry.csv --metrics out/intake_metrics.csv \
      --batch-report out/intake_batchN_report.md [--source "..."] [--mode gold] [--bench]

Peak memory uses psutil (subprocess RSS incl. children); falls back to resource.ru_maxrss if absent.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# P1-4 (v9.7.382): bind THIS harness's own repo root BEFORE any `mamey` import so a hostile
# PYTHONPATH or a different mamey tree on sys.path cannot version-shadow the engine (the exact
# failure mamey_run.py exists to prevent). tools/ first (for _wbio), then the repo root FIRST.
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
from _wbio import atomic_open

# Release policy is owned by mamey.cohort_figures.is_private() — the single source of
# truth updated for the 2026-07-06 PI public-cohort decision (AS- is public; only AJS-/
# PENDING- remain private). Import it so this guard cannot drift from the engine again.
# (Fixes stale-regex bug: the old guard blanket-refused PUBLIC for all AS-#### names,
# contradicting is_private() which returns False for AS-.)
try:
    from mamey.cohort_figures import is_private as _is_private
except Exception:  # pragma: no cover - fallback mirrors the canonical policy exactly
    def _is_private(sid):
        return str(sid).startswith(("AJS-", "PENDING-"))
import zipfile
from mamey.diagnostic_rescue import CORE_TRIGGERS  # noqa: E402

try:
    import psutil
    _HAVE_PSUTIL = True
except Exception:
    import resource
    _HAVE_PSUTIL = False

_SUFFIX = re.compile(r"(_loose|_copy)?(_GC[AF]_[0-9.]+)?(_ASM[0-9A-Za-z]+)?(_genomic)?(_1)?$")
BENCH_FIXTURE = os.path.join(ROOT, "examples", "test_data", "smoke_antismash_small.zip")


def clean_name(fname: str) -> str:
    base = re.sub(r"\.zip$", "", os.path.basename(fname))
    base = _SUFFIX.sub("", base)
    base = re.sub(r"_+", "_", base).strip("_")
    return base[:60]


def assembly_tag(fname: str) -> str | None:
    """Pull a stable assembly discriminator (GCA/GCF/ASM accession) from the original filename."""
    m = re.search(r"(GC[AF]_\d+(?:\.\d+)?|ASM\d+[A-Za-z0-9]*)", os.path.basename(fname))
    return m.group(1) if m else None


def assign_unique_names(zips):
    """clean_name strips assembly boilerplate, so multiple assemblies of one species collapse to the same
    base (e.g. four Melissospora_conviva_ASM#### -> 'Mconviva'), which would overwrite packages and collide
    registry keys. Disambiguate any colliding base with its assembly tag so distinct genomes stay distinct."""
    from collections import Counter
    bases = {zp: clean_name(zp) for zp in zips}
    counts = Counter(bases.values())
    out = {}
    for i, (zp, b) in enumerate(bases.items()):
        if counts[b] > 1:
            tag = assembly_tag(zp) or f"v{i+1}"
            out[zp] = f"{b}_{tag}"[:60]
        else:
            out[zp] = b
    return out


def run_monitored(cmd, **kw):
    """Run cmd; return (returncode, wall_s, peak_mb, combined_output)."""
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kw)
    peak = 0
    if _HAVE_PSUTIL:
        try:
            pp = psutil.Process(p.pid)
            while p.poll() is None:
                try:
                    rss = pp.memory_info().rss
                    for c in pp.children(recursive=True):
                        try:
                            rss += c.memory_info().rss
                        except psutil.Error:
                            pass
                    peak = max(peak, rss)
                except psutil.Error:
                    break
                time.sleep(0.03)
        except psutil.Error:
            pass
        out = p.stdout.read() if p.stdout else ""
        p.wait()
        peak_mb = peak / 1e6
    else:
        out = p.stdout.read() if p.stdout else ""
        p.wait()
        peak_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0
    return p.returncode, round(time.perf_counter() - t0, 3), round(peak_mb, 1), out


def _safe_extract_zip(z, dest):
    """Back-compat shim; canonical guard lives in mamey.ziputil (v9.7.367).

    BC2-398: this file already imports unconditionally from `mamey` (no try/except fallback,
    unlike tools/sapote_md_preflight.py's degraded-environment pattern), so there was no reason
    for it to carry its own independent zip-slip guard — the same asymmetric-duplicate shape this
    round's audit has repeatedly found and consolidated elsewhere. mamey/raw_antismash_triage.py
    already delegates to the canonical guard the same way; this file previously did not.
    `mamey.ziputil.safe_extract_all` uses `Path.resolve()` (filesystem-aware, follows symlinks in
    the destination path) rather than this file's prior `os.path.abspath()` (purely lexical) —
    both correctly reject the same `../`-traversal and absolute-path zip-member shapes tested
    below; the canonical version is the one path forward, not two to keep in sync.
    """
    from mamey.ziputil import safe_extract_all
    safe_extract_all(z, dest)

def detect_and_stage(zip_path, stage_root, name):
    """Return (kind, input_zip_or_none, clusterblast_dir_or_none, organism)."""
    d = os.path.join(stage_root, name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        _safe_extract_zip(z, d)
    shutil.rmtree(os.path.join(d, "__MACOSX"), ignore_errors=True)
    region_gbks = glob.glob(os.path.join(d, "**", "*region*.gbk"), recursive=True)
    if not region_gbks:
        return "NEEDS_ANTISMASH", None, None, None
    gdir = os.path.dirname(region_gbks[0])
    organism = None
    try:
        for line in open(region_gbks[0], encoding="utf-8", errors="replace"):
            if "ORGANISM" in line:
                organism = line.split("ORGANISM", 1)[1].strip()
                break
    except Exception:
        pass
    input_zip = os.path.join(stage_root, name + ".input.zip")
    with zipfile.ZipFile(input_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(gdir):
            for fn in files:
                if "__MACOSX" in root or fn.startswith("._"):
                    continue
                fp = os.path.join(root, fn)
                z.write(fp, os.path.relpath(fp, gdir))
    cb = os.path.join(gdir, "clusterblast")
    if not os.path.isdir(cb):
        hits = glob.glob(os.path.join(gdir, "**", "*_c1.txt"), recursive=True)
        cb = os.path.dirname(hits[0]) if hits else None
    return "ANTISMASH", input_zip, cb, organism


def parse_run_summary(log):
    def grab(key, cast):
        m = re.search(rf'"{key}":\s*"?([0-9A-Za-z_.]+)"?', log)
        return cast(m.group(1)) if m else None
    return {
        "raw_bgcs": grab("raw_bgcs", int),
        "corrected_bgcs": grab("corrected_bgcs", float),
        "assembly_tier": grab("assembly_tier", str),
    }


def rescue_summary(pkg, strain):
    p = os.path.join(pkg, f"{strain}_4B_Diagnostic_Rescue_Leads.json")
    if not os.path.exists(p):
        return {"rescue_leads": 0, "rescue_HIGH": 0, "rescue_MODERATE": 0, "IDC_split_HIGH": 0}
    leads = _read_json(p)["leads"]
    hi = [l for l in leads if l["rescue_tier"] == "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"]
    return {
        "rescue_leads": len(leads),
        "rescue_HIGH": len(hi),
        "rescue_MODERATE": sum(1 for l in leads if l["rescue_tier"] == "DIAGNOSTIC_RESCUE_MODERATE"),
        "IDC_split_HIGH": sum(1 for l in hi if "T43-IDC" in (l.get("core_triggers") or "")),
    }


def cores_present(pkg):
    man = _read_json(os.path.join(pkg, "manifest.json"))
    cctt = man.get("source_scans", {}).get("cctt", {}).get("per_bgc", {})
    found = {t for hits in cctt.values() for t in CORE_TRIGGERS if any(t in str(h) for h in (hits or []))}
    return ";".join(sorted(t.split("-")[1].split("_")[0] for t in found))


def append_rows(path, rows, header_order=None):
    if not rows:
        return
    existing = []
    if os.path.exists(path):
        existing = list(csv.DictReader(open(path)))
    all_rows = existing + rows
    # v9.7.116: deterministic column order. `list({set comprehension})` gave non-deterministic order
    # (set iteration), so two runs could rewrite the checkpoint CSV with different column orders —
    # the silent column-misalignment failure mode. sorted() pins it.
    cols = header_order or sorted({k for r in all_rows for k in r})
    # v9.7.116: atomic read-rewrite. This is a checkpoint CSV (read existing, append, rewrite the
    # whole file); a killed write would lose the ENTIRE accumulated checkpoint, not just new rows.
    with atomic_open(path, newline="") as f:
        w = _SafeDictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(all_rows)


def load_taxonomy_map(path):
    """Load and validate a --taxonomy-map JSON file. Returns {} for path=None.

    Fails closed (SystemExit) on anything other than a flat JSON object of
    string -> string pairs, so a malformed map can't silently pass through
    and produce confusing per-strain taxonomy at run time.
    """
    if not path:
        return {}
    with open(path) as fh:
        taxonomy_map = json.load(fh)
    if not isinstance(taxonomy_map, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in taxonomy_map.items()):
        raise SystemExit(f"--taxonomy-map must be a JSON object of {{strain: taxonomy}} "
                          f"string pairs; got {path}")
    return taxonomy_map


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True, help="dir of zips and/or individual zips")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--batch-report", default=None)
    ap.add_argument("--batch-label", default="batch")
    ap.add_argument("--source", default="public reference genome")
    ap.add_argument("--taxonomy-map", default=None,
                     help="Optional path to a JSON file of {strain_name: taxonomy_string} "
                          "overrides. When a strain name (as assigned by assign_unique_names) "
                          "matches a key, that taxonomy is used for both --taxonomy and the "
                          "registry 'organism' column instead of the GBK-derived value (which "
                          "for many draft/SPAdes assemblies is a placeholder like '.' or empty, "
                          "since the assembly's own GBK ORGANISM line was never populated). "
                          "Genus/host known only from institutional record — not the GBK — is "
                          "exactly the case this is for. Unmapped strains fall back to the prior "
                          "auto-derived behavior unchanged.")
    ap.add_argument("--release", default="PUBLIC", choices=["PUBLIC", "PRIVATE"],
                    help="release tag for these strains; PRIVATE for unpublished AS/AJS strains (hard guard)")
    ap.add_argument("--mode", default="gold",
                    choices=["standard", "gold"],
                    help="Engine mode passed through to mamey run. gold is the default/only analysis "
                         "mode; 'standard' is a deprecated alias (v9.7.92+). smoke was removed at v9.7.161.")
    ap.add_argument("--bench", action="store_true", dest="bench",
                    help="run the bundled fixture in gold mode for a machine-normalization datapoint")
    ap.add_argument("--resume", action="store_true",
                    help="skip strains already present in the registry (timeout-safe re-runs)")
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    stage_root = os.path.join(a.outdir, "_stage")
    os.makedirs(stage_root, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=ROOT)

    zips = []
    for item in a.inputs:
        if os.path.isdir(item):
            zips += sorted(glob.glob(os.path.join(item, "*.zip")))
        elif item.endswith(".zip"):
            zips.append(item)

    taxonomy_map = load_taxonomy_map(a.taxonomy_map)

    smoke = None
    if getattr(a, 'bench', False) and os.path.exists(BENCH_FIXTURE):
        rc, wall, mem, _ = run_monitored(
            [sys.executable, "-m", "mamey", "run", "--input-zip", BENCH_FIXTURE, "--strain", "MX_BENCH",
             "--taxonomy", "Streptomyces sp.", "--source", "bench", "--mode", "gold",
             "--brief", "none", "--outdir", os.path.join(a.outdir, "_bench")], env=env)
        smoke = {"wall_s": wall, "peak_mb": mem, "rc": rc}

    _REG_HDR = ["strain", "organism", "release", "assembly_tier", "raw_bgcs", "diagnostic_cores_present",
                "rescue_leads", "rescue_HIGH", "rescue_MODERATE", "IDC_split_HIGH"]
    _MET_HDR = ["strain", "batch", "status", "engine_wall_s", "engine_peak_mb", "rescue_wall_s", "n_regions"]

    done = set()
    if a.resume and os.path.exists(a.registry):
        done = {r["strain"] for r in csv.DictReader(open(a.registry))}

    def _checkpoint(reg_row, met_row):
        # append immediately so a timeout never loses completed strains
        append_rows(a.registry, [reg_row], _REG_HDR)
        append_rows(a.metrics, [met_row], _MET_HDR)

    reg_rows, met_rows = [], []
    emit(f"[intake] {len(zips)} input(s) | mem-monitor={'psutil' if _HAVE_PSUTIL else 'ru_maxrss'}"
          f"{' | resume' if a.resume else ''}")
    name_for = assign_unique_names(zips)
    for zp in zips:
        name = name_for[zp]
        if a.release == "PUBLIC" and _is_private(name):
            raise SystemExit(f"Refusing PUBLIC intake for private-looking strain {name}; rerun with --release PRIVATE")
        if name in done:
            emit(f"  - {name:40} SKIP (already in registry)")
            continue
        kind, izip, cb, org = detect_and_stage(zp, stage_root, name)
        if name in taxonomy_map:
            org = taxonomy_map[name]
        if kind == "NEEDS_ANTISMASH":
            emit(f"  - {name:40} NEEDS_ANTISMASH (raw assembly; run antiSMASH 8 first)")
            reg_rows.append({"strain": name, "organism": org or "?", "release": a.release,
                             "assembly_tier": "NEEDS_ANTISMASH", "raw_bgcs": "", "diagnostic_cores_present": "",
                             "rescue_leads": "", "rescue_HIGH": "", "rescue_MODERATE": "", "IDC_split_HIGH": ""})
            met_rows.append({"strain": name, "batch": a.batch_label, "status": "NEEDS_ANTISMASH",
                             "engine_wall_s": "", "engine_peak_mb": "", "rescue_wall_s": "", "n_regions": ""})
            _checkpoint(reg_rows[-1], met_rows[-1])
            continue

        rc, wall, mem, log = run_monitored(
            [sys.executable, "-m", "mamey", "run", "--input-zip", izip, "--strain", name,
             "--taxonomy", org or "sp.", "--source", a.source, "--mode", a.mode,
             "--json-evidence", "bounded", "--brief", "none", "--outdir", a.outdir], env=env)
        pkg = os.path.join(a.outdir, name, "package")
        if rc != 0 or not os.path.isdir(pkg):
            emit(f"  - {name:40} RUN_FAILED (rc={rc})")
            met_rows.append({"strain": name, "batch": a.batch_label, "status": "RUN_FAILED",
                             "engine_wall_s": wall, "engine_peak_mb": mem, "rescue_wall_s": "", "n_regions": ""})
            append_rows(a.metrics, [met_rows[-1]], _MET_HDR)
            continue

        # The engine now emits the 4B Diagnostic Rescue files itself (concordance-gated) during the run,
        # so no separate rescue subprocess is needed — read its summary straight from the package.
        rwall = ""
        summ = parse_run_summary(log)
        resc = rescue_summary(pkg, name)
        reg_rows.append({"strain": name, "organism": org or "?", "release": a.release,
                         "assembly_tier": summ["assembly_tier"], "raw_bgcs": summ["raw_bgcs"],
                         "diagnostic_cores_present": cores_present(pkg), **resc})
        met_rows.append({"strain": name, "batch": a.batch_label, "status": "OK",
                         "engine_wall_s": wall, "engine_peak_mb": mem, "rescue_wall_s": rwall,
                         "n_regions": summ["raw_bgcs"]})
        _checkpoint(reg_rows[-1], met_rows[-1])
        emit(f"  - {name:40} {summ['assembly_tier']:13} raw={summ['raw_bgcs']:>3} "
              f"HIGH={resc['rescue_HIGH']} IDC={resc['IDC_split_HIGH']} | {wall}s {mem}MB")

    if a.batch_report:
        _write_report(a.batch_report, a.batch_label, reg_rows, met_rows, smoke)
    emit(f"[intake] registry -> {a.registry} | metrics -> {a.metrics}")


def _write_report(path, label, reg, met, smoke):
    ok = [m for m in met if m["status"] == "OK"]
    walls = [m["engine_wall_s"] for m in ok]
    mems = [m["engine_peak_mb"] for m in ok]
    with atomic_open(path, "w") as f:  # v9.7.116: atomic

        try:
            from mamey import __version__ as _ev
        except Exception:
            _ev = "?"
        f.write(f"# Intake — {label}\n\nMamey v{_ev}\n\n")
        f.write("## Performance\n\n")
        f.write("| Reference (user) | This run |\n|---|---|\n")
        # AUDIT_371: smoke's rc was captured but never checked here, so a failed
        # subprocess (e.g. --mode smoke, retired at v9.7.161 -> argparse rejects it near-
        # instantly, rc=2) rendered as an implausibly fast "successful" benchmark number
        # instead of a visible failure. Surface rc != 0 explicitly; numbers are only shown
        # for a genuine rc == 0 run. Does not change what --smoke-bench actually runs (that
        # --mode smoke is retired is a separate, tool-owner design question).
        if smoke and smoke.get("rc", 0) == 0:
            f.write(f"| smoke 2.887 s | smoke {smoke['wall_s']} s / {smoke['peak_mb']} MB |\n")
        elif smoke:
            f.write(f"| smoke 2.887 s | FAILED (rc={smoke.get('rc')}) — not a valid benchmark "
                    f"datapoint |\n")
        else:
            f.write("| smoke 2.887 s | (not benchmarked this batch) |\n")
        f.write("| pilot 44 s, 502 MB peak | "
                + (f"std median {sorted(walls)[len(walls)//2]} s, max {max(mems)} MB peak |\n" if ok else "— |\n"))
        f.write("\n| Strain | status | engine wall (s) | peak (MB) | rescue (s) | regions |\n|---|---|---|---|---|---|\n")
        for m in met:
            f.write(f"| {m['strain']} | {m['status']} | {m.get('engine_wall_s','')} | "
                    f"{m.get('engine_peak_mb','')} | {m.get('rescue_wall_s','')} | {m.get('n_regions','')} |\n")
        f.write("\n## Registry rows added\n\n| Strain | Organism | Assembly | raw | cores | HIGH | IDC-split |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in reg:
            f.write(f"| {r['strain']} | *{r['organism']}* | {r['assembly_tier']} | {r['raw_bgcs']} | "
                    f"{r['diagnostic_cores_present']} | {r.get('rescue_HIGH','')} | {r.get('IDC_split_HIGH','')} |\n")
        f.write("\n_Claim ceiling on every rescue lead: clusterblast-scaffolded reconstruction hypothesis, "
                "not a contig join or product-identity claim._\n")


if __name__ == "__main__":
    main()
