#!/usr/bin/env python3
"""mamey_pipeline.py — single-entry Lab Office pipeline (the "working program" cohesion piece).

One command turns a sealed Mamey package into a single, reproducible REPORT that chains the stages and pins every
input. This is the answer to "we have a working engine but not a working *program*": the engine (Tier-1) runs; this
wraps it + validate + explain + figures into one strain -> report path, each stage manifest-guarded.

Stages (skips any whose inputs are absent — nothing fabricated):
  1. LOCATE  — verify the sealed package dir; sha256-manifest its contents (input_manifest.py).
  2. VALIDATE — run `mamey validate <package>` via the engine; capture PASS/FAIL.
  3. EXPLAIN  — run `mamey explain <package>`; capture the human summary.
  4. FIGURES  — render any Figure Studio *.json under --figures (lab_office_render.py) to SVG+PNG.
  5. REPORT   — write REPORT_<strain>.md linking package + validation + explain + figures + the manifest.

Usage:
  python Tools/mamey_pipeline.py --strain <STRAIN> \
      --package "<sealed tree>/runs/<STRAIN>/package" \
      --engine  "<sealed tree>" \
      [--figures "<dir of figure .json>"] --out "<report dir>"

Portable: uses the sealed tree's mamey_run.py + the local Tools (input_manifest, lab_office_render). No network.
Claim-safety travels through explain/figures unchanged (class-level hypotheses, judgment deferred).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, hashlib, os, subprocess, sys, datetime, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = os.path.join(ROOT, "Tools", "bin", "python3")
if not os.path.exists(PY):  # not installed at Tools/ (e.g. under test) -> use the running interpreter
    PY = sys.executable
INPUT_MANIFEST = os.path.join(HERE, "input_manifest.py")
LAB_OFFICE = os.path.join(HERE, "lab_office_render.py")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def sha256(p, buf=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(buf), b""):
            h.update(c)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strain", required=True)
    ap.add_argument("--package", required=True, help="sealed package dir (…/runs/<strain>/package)")
    ap.add_argument("--engine", required=True, help="sealed Sapote-Mamey tree (has mamey_run.py)")
    ap.add_argument("--figures", help="dir of Figure Studio .json to render (optional)")
    ap.add_argument("--lit-refs", help="optional path to a strain-keyed literature query tool "
                    "(e.g. lit_refs_for_strain.py); called as `<tool> <strain>`, stdout appended to the report")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    stages, log = {}, []
    engine_abs = os.path.abspath(args.engine)
    entry = os.path.join(engine_abs, "mamey_run.py")  # absolute so cwd=engine doesn't double the path
    package_abs = os.path.abspath(args.package)
    args.package = package_abs

    # 1 LOCATE + manifest
    if not os.path.isdir(args.package):
        emit(f"ERROR: package dir not found: {args.package}", file=sys.stderr); return 1
    pkg_files = sorted(glob.glob(os.path.join(args.package, "**", "*"), recursive=True))
    pkg_files = [p for p in pkg_files if os.path.isfile(p)]
    man = os.path.join(args.out, f"{args.strain}_PACKAGE_MANIFEST.tsv")
    with open(man, "w", encoding="utf-8") as fh:
        fh.write("file\tsha256\tsize\n")
        for p in pkg_files:
            fh.write(f"{os.path.relpath(p, args.package)}\t{sha256(p)}\t{os.path.getsize(p)}\n")
    stages["locate"] = f"{len(pkg_files)} package files pinned"
    log.append(f"1 LOCATE: {len(pkg_files)} files -> {os.path.basename(man)}")

    # 2 VALIDATE
    r = run([PY, entry, "validate", args.package], cwd=engine_abs)
    vtxt = (r.stdout + r.stderr)
    # v9.7.374 fix: the old third condition ("PASS" in the stringified last-40-lines) was a bare
    # substring search over the WHOLE tail window, satisfied by ANY unrelated sub-field the real
    # validate_package() JSON emits as its own independent "PASS" (file_presence, pks_ks_scan,
    # exclusion_gate, citation_compact_gate, checksum_integrity, or a nested WORKBOOK_CONTENT
    # block) -- completely independent of the actual overall `"status"` field. Reproduced live: a
    # realistic result with overall status="FAIL" (rggmci_gate failed) but several unrelated
    # PASS sub-fields in the tail was reported as vstatus="PASS". `mamey validate`'s own exit code
    # (mamey/cli.py::validate_command) is already the authoritative PASS/FAIL signal -- rc=0 iff
    # status.startswith("PASS") or status=="MAMEY_COMPLETE" (and --workbook-strict, never passed
    # here, is the only other way to force rc=1) -- so derive vstatus from it directly instead of
    # re-parsing free-text output.
    vstatus = "PASS" if r.returncode == 0 else "FAIL"
    open(os.path.join(args.out, f"{args.strain}_validate.txt"), "w", encoding="utf-8").write(vtxt)
    stages["validate"] = f"rc={r.returncode} ({vstatus})"
    log.append(f"2 VALIDATE: rc={r.returncode} -> {args.strain}_validate.txt")

    # 3 EXPLAIN
    r = run([PY, entry, "explain", args.package], cwd=engine_abs)
    etxt = (r.stdout + r.stderr).strip()
    open(os.path.join(args.out, f"{args.strain}_explain.txt"), "w", encoding="utf-8").write(etxt)
    stages["explain"] = f"rc={r.returncode}, {len(etxt)} chars"
    log.append(f"3 EXPLAIN: rc={r.returncode} -> {args.strain}_explain.txt")

    # 3.5 LITERATURE (optional, opt-in) — pull strain-keyed refs for the report feed
    lit_block = ""
    if args.lit_refs and os.path.exists(args.lit_refs):
        rl = run([PY, args.lit_refs, args.strain])
        if rl.returncode == 0 and rl.stdout.strip():
            lit_block = rl.stdout.strip()
        stages["literature"] = "appended" if lit_block else f"rc={rl.returncode} (no block)"
        log.append(f"3.5 LITERATURE: {stages.get('literature')}")

    # 4 FIGURES
    fig_note = "skipped (no --figures)"
    if args.figures and os.path.isdir(args.figures):
        r = run([PY, LAB_OFFICE, "--dir", args.figures])
        fig_note = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else "ran"
    stages["figures"] = fig_note
    log.append(f"4 FIGURES: {fig_note}")

    # 5 REPORT
    now = datetime.date.today().isoformat()
    rep = os.path.join(args.out, f"REPORT_{args.strain}.md")
    explain_head = "\n".join(etxt.splitlines()[:30])
    with open(rep, "w", encoding="utf-8") as fh:
        fh.write(f"# Sapote-Mamey pipeline report — {args.strain}\n\n**Date:** {now} · **engine:** "
                 f"`{os.path.basename(args.engine)}` · **package:** `{args.package}`\n\n")
        fh.write("## Pipeline stages\n")
        for k in ["locate", "validate", "explain", "figures"]:
            fh.write(f"- **{k}** — {stages.get(k,'—')}\n")
        fh.write(f"\n## Package (sha256-pinned)\n- `{os.path.basename(man)}` — {len(pkg_files)} files\n")
        fh.write(f"\n## Validate\n- `{args.strain}_validate.txt` — {stages['validate']}\n")
        fh.write(f"\n## Explain (human summary)\n\n```\n{explain_head}\n```\n")
        if lit_block:
            fh.write(f"\n## Literature (strain-keyed refs)\n\n{lit_block}\n")
        fh.write(f"\n## Figures\n- {fig_note}\n")
        fh.write("\n---\n_One-command pipeline (`mamey_pipeline.py`). Engine deferred judgment; this only chains + "
                 "reports. Class-level hypotheses, judgment deferred; no bioactivity/structure claims._\n")
    emit('[mamey_pipeline] ' + ' | '.join(log), f'[mamey_pipeline] REPORT -> {rep}', sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
