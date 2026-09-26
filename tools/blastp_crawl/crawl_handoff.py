#!/usr/bin/env python3
"""Move a ClusteredNR gap crawl to another machine, and bring its results home.

  pack    Build a self-contained handoff folder and zip from the workspace's gap lanes: the runner,
          the lane script, the throughput plotter, the concurrency hook (wired for Claude Code with a
          lane cap), every selected query tree and ledger, a manifest of ledger checksums, and a
          START_HERE.md with the prompt for the assistant on the other machine.
  return  Run inside an unpacked handoff folder once every lane has stopped. Zips every lane folder
          (ledger, log, result CSVs, XML) for the trip home.
  merge   At home: merge a return zip into the workspace lanes. Dry run unless --execute. A lane
          whose home ledger changed since the handoff, or whose return lost a home `fetched` row,
          is held and not touched. Existing result files are never overwritten.

While a handoff is out, don't run the same lanes at home: both machines would submit the same
proteins. Set SAPOTE_WORKSPACE_ROOT to the folder that holds `Blastp RESULTS/` (pack, merge).

  python3 tools/blastp_crawl/crawl_handoff.py pack --out <dir outside the bundle>
  python3 tools/blastp_crawl/crawl_handoff.py return                  # inside the handoff folder
  python3 tools/blastp_crawl/crawl_handoff.py merge <BLASTP_RETURN_*.zip> [--execute]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
try:
    from mamey.csv_safety import SafeWriter
    from mamey.path_safety import assert_output_outside_bundle
except ImportError:  # bare script: the bundle root is two levels above this file
    sys.path.insert(0, str(HERE.parents[1]))
    from mamey.csv_safety import SafeWriter
    from mamey.path_safety import assert_output_outside_bundle

CODE_ROOT = HERE.parents[1]          # bundle root, or the handoff folder itself
LANE_PREFIX = "_STRAINGAP_SINGLE_CLNR_GAP_AS"
SKIP = {"fetched", "submitted", "submit_failed_parked", "unsure"}
MANIFEST = "HANDOFF_MANIFEST.tsv"
MANIFEST_COLS = ["lane", "queries_dir", "ledger_sha256_at_handoff", "ledger_rows", "runnable",
                 "fetched", "held_rids"]
CODE_FILES = [
    "tools/blastp_crawl/nr_rid_runner.py",
    "tools/blastp_crawl/run_lane.sh",
    "tools/blastp_crawl/crawl_handoff.py",
    "tools/blastp_monitoring/plot_crawl_proteins_24_96h.py",
    "tools/blastp_monitoring/blastp_health.py",
    "mamey/__init__.py",
    "mamey/csv_safety.py",
    "mamey/path_safety.py",
    "hooks/block_blastp_overconcurrency.sh",
    "hooks/blastp_launch_probe.py",
]


def workspace() -> Path:
    return Path(os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runners_live() -> bool:
    p = subprocess.run(["pgrep", "-f", "nr_rid_runner.py run"], capture_output=True, text=True)
    return bool(p.stdout.strip())


def lane_rows(ledger: Path) -> dict[str, dict]:
    if not ledger.exists():
        return {}
    with ledger.open(newline="") as fh:
        return {r["file"]: r for r in csv.DictReader(fh)}


def ledger_rows_from_bytes(data: bytes) -> dict[str, dict]:
    return {r["file"]: r for r in csv.DictReader(io.StringIO(data.decode("utf-8", "replace")))}


def survey(br: Path, wanted: set[str] | None):
    """One row per gap lane that still has work: runnable query files or held RIDs."""
    out = []
    for q in sorted(br.glob("_QUERIES_GAP_AS-*_K")):
        m = re.search(r"AS-(\d+)", q.name)
        if not m:
            continue
        strain = f"AS-{m.group(1)}"
        if wanted and strain not in wanted:
            continue
        lane = br / f"{LANE_PREFIX}{m.group(1)}"
        led = lane_rows(lane / "_ledger.csv")
        files = [p.relative_to(q).as_posix() for p in q.rglob("*.faa")]
        runnable = sum(1 for f in files if led.get(f, {}).get("status") not in SKIP)
        held = sum(1 for r in led.values() if r.get("status") == "submitted")
        if runnable or held:
            out.append(dict(strain=strain, q=q, lane=lane, led=led, runnable=runnable, held=held,
                            fetched=sum(1 for r in led.values() if r.get("status") == "fetched")))
    return out


START_HERE = """# BLASTp handoff: ClusteredNR gap crawl

This folder runs the ClusteredNR BLASTp gap crawl on another machine and sends the results home.
Made {made} by `tools/blastp_crawl/crawl_handoff.py pack`. {n_lanes} lanes, {n_runnable} proteins
left to run.

## Setup, once
1. Unzip anywhere. A path with spaces is fine.
2. Check `python3 --version` and `curl --version`. For plots only: `python3 -m pip install --user matplotlib`.
3. Open Claude Code in this folder. `.claude/settings.json` switches on the BLASTp concurrency hook
   with a cap of {max_lanes} lanes. Keep it.
4. Paste the prompt below.

## Prompt for the assistant
> You're running the ClusteredNR BLASTp gap crawl for the Sapote-Mamey project from a handoff
> folder. Read `START_HERE.md` and `HANDOFF_MANIFEST.tsv` first. Start lanes only when I ask, as
> background tasks, one at a time and a minute apart: `sleep 60 && ./run_lane.sh AS-<n>`. Don't
> change the runner's settings, and don't edit the runner, ledgers or query files by hand. For
> "plot blastp", run `./plot.sh`, look at the PNG, and show it to me. For lane numbers, run
> `./health.sh`. If lanes stall, tell me; I stop all lanes, then we restart one, wait for a fetched
> result, and add lanes one at a time. When I say we're done, confirm every lane has stopped, then
> run `./return.sh`.

## House rules
- **{max_lanes} lanes at most, started a minute apart.** A lane submits one protein every 5 minutes,
  so about 12 an hour.
- **A result counts when it is fetched.** A submission alone proves nothing.
- **On a stall, stop all lanes.** Restart one, wait for a fetched result, then add lanes back.
- **Held RIDs are normal.** ClusteredNR has returned results after 7 to 27 hours. A RID older than an
  hour stops blocking its lane and is checked every 15 minutes. After 36 hours it is marked `unsure`
  and never resubmitted automatically.
- **Split errors by type before blaming NCBI.** Mostly `poll ERROR curl rc=52` on every lane points
  at the network or at NCBI itself; the runner's hourly `RATE` line shows how loud each lane is.
- **No email address in any NCBI request.** The runner doesn't send one.
- **Don't run these lanes at home while this folder is out.**

## Sending results home
Stop every lane, then run `./return.sh`. It writes `BLASTP_RETURN_<date>.zip` to the Desktop and
prints its sha256. At home: `crawl_handoff.py merge <zip>`, then again with `--execute`.
"""


def cmd_pack(a) -> int:
    ws = workspace()
    br = ws / "Blastp RESULTS"
    out_parent = Path(a.out).resolve()
    assert_output_outside_bundle(out_parent, __file__, kind="BLASTp handoff folder")
    if runners_live() and not a.allow_live:
        sys.exit("pack refused: a nr_rid_runner.py lane is running. Stop the lanes first, so the "
                 "ledgers don't change under the copy (or pass --allow-live).")
    wanted = {s.strip() for s in a.lanes.split(",")} if a.lanes else None
    lanes = survey(br, wanted)
    if not lanes:
        sys.exit("pack: no gap lane with work left" + (f" among {sorted(wanted)}" if wanted else ""))
    name = a.name or f"BLASTP_HANDOFF_{dt.date.today():%Y-%m-%d}"
    dest = out_parent / name
    if dest.exists() or dest.with_suffix(".zip").exists():
        sys.exit(f"pack refused: {dest} (or its .zip) already exists")
    (dest / "Blastp RESULTS").mkdir(parents=True)
    for rel in CODE_FILES:
        src = CODE_ROOT / rel
        if not src.exists():
            continue                     # e.g. blastp_health.py in an older bundle
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest / rel)
    rows = []
    for ln in lanes:
        shutil.copytree(ln["q"], dest / "Blastp RESULTS" / ln["q"].name)
        (dest / "Blastp RESULTS" / ln["lane"].name).mkdir()
        led_path = ln["lane"] / "_ledger.csv"
        digest = ""
        if led_path.exists():
            shutil.copy2(led_path, dest / "Blastp RESULTS" / ln["lane"].name / "_ledger.csv")
            digest = sha256(led_path.read_bytes())
        rows.append([ln["lane"].name, ln["q"].name, digest, len(ln["led"]), ln["runnable"],
                     ln["fetched"], ln["held"]])
    with (dest / MANIFEST).open("w", newline="") as fh:
        w = SafeWriter(fh, delimiter="\t")
        w.writerow(MANIFEST_COLS)
        w.writerows(rows)
    (dest / ".claude").mkdir()
    (dest / ".claude" / "settings.json").write_text(json.dumps({
        "env": {"SAPOTE_BLASTP_MAX_LANES": str(a.max_lanes)},
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",
                  "command": 'bash "$CLAUDE_PROJECT_DIR/hooks/block_blastp_overconcurrency.sh"'}]}]},
    }, indent=2) + "\n")
    wrappers = {
        "run_lane.sh": 'export SAPOTE_WORKSPACE_ROOT="$HERE"\nexec "$HERE/tools/blastp_crawl/run_lane.sh" "$@"\n',
        "plot.sh": ('mkdir -p "$HERE/plots"\nSAPOTE_WORKSPACE_ROOT="$HERE" SAPOTE_BLASTP_PLOT_DIR="$HERE/plots" '
                    'python3 "$HERE/tools/blastp_monitoring/plot_crawl_proteins_24_96h.py" --lanes "*GAP*" '
                    '--active-hours 48\necho "open: $HERE/plots/blastp_throughput_proteins_24_96h.png"\n'),
        "health.sh": 'SAPOTE_WORKSPACE_ROOT="$HERE" exec python3 "$HERE/tools/blastp_monitoring/blastp_health.py" "$@"\n',
        "return.sh": 'cd "$HERE" && exec python3 "$HERE/tools/blastp_crawl/crawl_handoff.py" return "$@"\n',
    }
    for fname, body in wrappers.items():
        p = dest / fname
        p.write_text('#!/bin/bash\nset -euo pipefail\nHERE="$(cd "$(dirname "$0")" && pwd)"\n' + body)
        p.chmod(0o755)
    for ln in lanes:                     # mark the home lanes, so nothing runs them twice
        ln["lane"].mkdir(parents=True, exist_ok=True)
        (ln["lane"] / "_HANDOFF_OUT.txt").write_text(
            f"handed off {dt.datetime.now():%Y-%m-%d %H:%M} in {name}\n"
            f"folder: {dest}\nmerge its return zip to clear this marker\n")
    n_runnable = sum(r[4] for r in rows)
    (dest / "START_HERE.md").write_text(START_HERE.format(
        made=dt.date.today().isoformat(), n_lanes=len(rows), n_runnable=n_runnable, max_lanes=a.max_lanes))
    zpath = dest.with_suffix(".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dest.rglob("*")):
            if p.is_file() and p.name != ".DS_Store":
                z.write(p, p.relative_to(out_parent).as_posix())
    print(f"packed {len(rows)} lanes, {n_runnable} runnable proteins")
    print(f"folder: {dest}")
    print(f"zip:    {zpath}  ({zpath.stat().st_size:,} B, sha256 {sha256(zpath.read_bytes())})")
    print("While it is out, don't run these lanes here.")
    return 0


def cmd_return(a) -> int:
    root = Path.cwd()
    if not (root / MANIFEST).exists():
        sys.exit(f"return: run this inside the unpacked handoff folder (no {MANIFEST} in {root})")
    if runners_live():
        sys.exit("return refused: lanes are still running; stop them first")
    out_dir = Path(a.out).expanduser() if a.out else Path.home() / "Desktop"
    out = out_dir / f"BLASTP_RETURN_{dt.datetime.now():%Y-%m-%d_%H%M}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(root / MANIFEST, MANIFEST)
        for p in sorted((root / "Blastp RESULTS").glob(f"{LANE_PREFIX}*/**/*")):
            if p.is_file() and p.name not in (".DS_Store", "_runner.pid"):
                z.write(p, p.relative_to(root).as_posix())
        for p in sorted((root / "plots").glob("*")) if (root / "plots").exists() else []:
            z.write(p, p.relative_to(root).as_posix())
    print(f"{out}  ({out.stat().st_size:,} B, sha256 {sha256(out.read_bytes())})")
    print("Send this zip home and merge it with crawl_handoff.py merge.")
    return 0


def cmd_merge(a) -> int:
    br = workspace() / "Blastp RESULTS"
    if a.execute:
        assert_output_outside_bundle(br, __file__, kind="BLASTp results")
    z = zipfile.ZipFile(a.zip)
    names = set(z.namelist())
    with z.open(MANIFEST) as fh:
        man = {r["lane"]: r for r in csv.DictReader(io.TextIOWrapper(fh, "utf-8"), delimiter="\t")}
    prefix = f"Blastp RESULTS/{LANE_PREFIX}"
    lanes = sorted({n.split("/")[1] for n in names if n.startswith(prefix)})
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"{'EXECUTE' if a.execute else 'DRY RUN'}: {Path(a.zip).name} ({len(lanes)} lanes)")
    held = 0
    for lane in lanes:
        home = br / lane
        zled = f"Blastp RESULTS/{lane}/_ledger.csv"
        if zled not in names:
            print(f"  {lane}: no ledger in the zip; skipped")
            continue
        new_b = z.read(zled)
        home_led = home / "_ledger.csv"
        home_b = home_led.read_bytes() if home_led.exists() else b""
        if lane not in man:
            print(f"  {lane}: HELD, not in the handoff manifest"); held += 1; continue
        if (sha256(home_b) if home_b else "") != man[lane]["ledger_sha256_at_handoff"]:
            print(f"  {lane}: HELD, the home ledger changed after the handoff"); held += 1; continue
        old, new = (ledger_rows_from_bytes(home_b) if home_b else {}), ledger_rows_from_bytes(new_b)
        lost = [f for f, r in old.items()
                if r.get("status") == "fetched" and new.get(f, {}).get("status") != "fetched"]
        if lost:
            print(f"  {lane}: HELD, {len(lost)} home fetched rows are not fetched in the return"); held += 1; continue
        copied = same = conflict = 0
        for n in sorted(names):
            if not n.startswith(f"Blastp RESULTS/{lane}/") or n.endswith("/"):
                continue
            rel = n[len(f"Blastp RESULTS/{lane}/"):]
            if rel in ("_ledger.csv", "_run.log", "_runner.pid", "_HANDOFF_OUT.txt"):
                continue
            target = home / rel
            data = z.read(n)
            if target.exists():
                if target.read_bytes() == data:
                    same += 1
                else:
                    conflict += 1
                    print(f"    conflict, kept the home copy: {rel}")
                continue
            copied += 1
            if a.execute:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        gained = (sum(1 for r in new.values() if r.get("status") == "fetched")
                  - sum(1 for r in old.values() if r.get("status") == "fetched"))
        print(f"  {lane}: +{gained} fetched · files new {copied}, identical {same}, conflicts {conflict}")
        if a.execute:
            home.mkdir(parents=True, exist_ok=True)
            if home_b:
                shutil.copy2(home_led, home / f"_ledger.csv.bak_premerge_{stamp}")
            home_led.write_bytes(new_b)
            (home / "_HANDOFF_OUT.txt").unlink(missing_ok=True)
            zlog = f"Blastp RESULTS/{lane}/_run.log"
            if zlog in names:
                with (home / "_run.log").open("ab") as fh:
                    fh.write(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] ==== merged from {Path(a.zip).name} ====\n".encode())
                    fh.write(z.read(zlog))
    print(f"{held} lane(s) held." + ("" if a.execute else " Nothing written; re-run with --execute."))
    return 1 if held else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack", help="build a handoff folder and zip")
    p.add_argument("--out", required=True, help="parent folder for the handoff (outside the bundle)")
    p.add_argument("--lanes", default="", help="comma list of strains, e.g. AS-1,AS-2 (default: every lane with work)")
    p.add_argument("--max-lanes", type=int, default=4, help="concurrency hook cap on the other machine (default 4)")
    p.add_argument("--name", default="", help="folder name (default BLASTP_HANDOFF_<date>)")
    p.add_argument("--allow-live", action="store_true", help="pack even while a lane is running")
    r = sub.add_parser("return", help="zip the lane folders for the trip home (run inside the handoff)")
    r.add_argument("--out", default="", help="folder for the zip (default ~/Desktop)")
    m = sub.add_parser("merge", help="merge a return zip into the workspace")
    m.add_argument("zip")
    m.add_argument("--execute", action="store_true")
    a = ap.parse_args()
    return {"pack": cmd_pack, "return": cmd_return, "merge": cmd_merge}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
