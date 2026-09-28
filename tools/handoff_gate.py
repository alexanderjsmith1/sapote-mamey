#!/usr/bin/env python3
"""handoff_gate.py — one fail-closed check before work is handed to a person, a reviewer or another assistant.

Built because the misses that reach an owner are rarely scientific: a link that does not open, a patch queue that
names a hash its diff no longer has, a figure no index points to, a BGC written without its alias, claim wording
drawn on a figure. Each check below either runs a checker the bundle already ships or adds the missing one. It prints
one PASS/FAIL table and writes a JSON receipt; exit 0 only when every check passes.

Modes
  patches <patch folder> --compose <compose script> [--replay] [--excluded-ok CARD ...]
      - every `step`/`copy` line of the compose script names a file that exists (placeholders $Q = the patch folder;
        --var NAME=PATH for others);
      - in the queue (00_QUEUE_*.md), a paragraph that names a diff and exactly one short sha256 names that diff's
        current hash;
      - every line of a card's HASHES.txt that names an existing .diff/.patch/.py/.zip matches it;
      - every card folder holding a .diff/.patch (outside old/) is in the compose order or named in --excluded-ok;
      - tools/patch_packet_preflight.py finds no bloat or unsafe payload in any card;
      - --replay: the compose script prints "ALL APPLIED; .orig/.rej files: 0".
  deliverable <folder> [--index FILE.md ...] [--figure-dir DIR ...]
      - tools/check_md_links.py passes on every .md (outside old/);
      - every file an index links exists; every .png under --figure-dir is linked by an index;
      - BGC identities written "strain / node / regionNNN" carry the fourth component (the BGC alias);
      - no figure script (*.py in the folder) draws wording that mamey.figure_policy bans from figures.
  reply <file.md> [--root DIR]
      - every local link resolves from the project root (default: the current directory) and is a file;
      - spaces are %20 and parentheses %28 %29 (clients cut links at raw ones).

Receipt: HANDOFF_GATE_RECEIPT.json in the checked folder (reply mode: <file>.handoff_gate.json); --receipt overrides.

CLI:
  python tools/handoff_gate.py patches <patch folder> --compose <compose.sh> --replay
  python tools/handoff_gate.py deliverable <run folder> --index INDEX.md --figure-dir figures
  python tools/handoff_gate.py reply <draft.md> --root <project root>
"""
from __future__ import annotations

import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import hashlib
import json
import re
import subprocess
import urllib.parse
from datetime import datetime
from pathlib import Path

try:
    from mamey.figure_policy import FIGURE_BANNED_TEXT, class_level_hedge
    from mamey.path_safety import assert_output_outside_bundle
except ImportError:  # bare-script run: bundle root is one level up
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from mamey.figure_policy import FIGURE_BANNED_TEXT, class_level_hedge
    from mamey.path_safety import assert_output_outside_bundle

TOOLS = Path(__file__).resolve().parent
# our cards use CARD.md as the front door, so the preflight's PATCH_CARD/IMPLEMENTATION findings are not gate failures
BLOAT_CODES = {"FORBIDDEN_DIRECTORY_CLASS", "FILE_TOO_LARGE", "PACKET_TOO_LARGE", "FORBIDDEN_PATCH_PAYLOAD_PATH",
               "UNAPPLICABLE_BINARY_DIFF_MARKER", "COPIED_RELEASE_BASELINE"}
DRAW_CALLS = ("suptitle", "set_title", "ax.text", "fig.text", "label=", "set_xlabel", "set_ylabel", "annotate")
SHORT_IDENTITY = re.compile(r"\b[\w.-]+ / (?:\S+ = )?\S+ / region\d{3}(?! / )")


class Gate:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.rows.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})

    def report(self, receipt: Path) -> int:
        assert_output_outside_bundle(receipt.parent, __file__)
        w = max(len(r["check"]) for r in self.rows)
        ok = all(r["result"] == "PASS" for r in self.rows)
        lines = [f"{r['result']:4}  {r['check']:<{w}}  {r['detail']}" for r in self.rows]
        emit(*lines, f"HANDOFF GATE: {'PASS' if ok else 'FAIL'}", sep="\n")
        receipt.write_text(json.dumps({"tool": "handoff_gate", "when": datetime.now().isoformat(timespec="seconds"),
                                       "result": "PASS" if ok else "FAIL", "checks": self.rows}, indent=2) + "\n")
        return 0 if ok else 1


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def patches(a) -> int:
    g, folder = Gate(), Path(a.folder).resolve()
    script = Path(a.compose).resolve()
    comp = script.read_text()
    subs = {"Q": str(folder), **dict(v.split("=", 1) for v in (a.var or []))}
    for name, value in re.findall(r'^([A-Z]+)="([^"$]+)"', comp, re.M):
        subs.setdefault(name, value)

    def expand(path: str) -> Path:
        return Path(re.sub(r"\$(\w+)", lambda m: subs.get(m.group(1), m.group(0)), path))

    steps = [(m.group(1), expand(m.group(2))) for m in re.finditer(r'^(?:step|copy) "([^"]+)"\s+"([^"]+)"', comp, re.M)]
    missing = [label for label, p in steps if not p.exists()]
    g.check("compose steps point to existing files", bool(steps) and not missing,
            f"{len(steps)} steps" + (f"; missing: {missing}" if missing else ""))
    qlines = "\n".join(p.read_text() for p in folder.glob("00_QUEUE_*.md") if ".bak" not in p.name).splitlines()
    drift, compared, covered = [], 0, set()
    for _, p in steps:
        if p.exists() and p.suffix in (".diff", ".patch"):
            h = _sha(p)
            # a hash counts only on the diff's own line, or the next line when the diff's line names none
            for i in (i for i, line in enumerate(qlines) if p.name in line):
                named = re.findall(r"sha256 `([0-9a-f]{8})", qlines[i])
                if not named and i + 1 < len(qlines) and not re.search(r"`[^`]+\.(?:diff|patch)`", qlines[i + 1]):
                    named = re.findall(r"sha256 `([0-9a-f]{8})", qlines[i + 1])
                if len(named) == 1:
                    compared += 1
                    covered.add(p.resolve())
                    if named[0] != h[:8]:
                        drift.append(f"{p.parent.name}/{p.name}: queue names {named[0]}, file is {h[:8]}")
    # A full handoff digest can cover a diff whose queue entry carries no short digest.
    handoff_lines = "\n".join(p.read_text() for p in folder.glob("CODEX_REVIEW_HANDOFF_*.md")).splitlines()
    for _, p in steps:
        if p.is_file() and p.suffix in (".diff", ".patch") and p.resolve() not in covered:
            named = [h for line in handoff_lines if p.name in line
                     for h in re.findall(r"`([0-9a-f]{64})`", line)]
            if len(named) == 1:
                covered.add(p.resolve())
                compared += 1
                if named[0] != _sha(p):
                    drift.append(f"{p.name}: handoff digest does not match")
            else:
                drift.append(f"{p.name}: missing or ambiguous queue/handoff digest")
    g.check("queue sha matches each diff", not drift, "; ".join(drift) or f"{compared} diffs compared, all current")
    stale = []
    for hf in folder.glob("*/HASHES.txt"):
        for line in hf.read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
                target = (hf.parent / parts[1]).resolve()
                if target.suffix in (".diff", ".patch", ".py", ".zip") and (not target.is_file() or _sha(target) != parts[0]):
                    stale.append(f"{hf.parent.name}/{parts[1].lstrip('./')}")
    g.check("HASHES.txt lines match their files", not stale, ", ".join(stale) or "ok")
    composed = {p.resolve() for _, p in steps if p.exists()}
    cards = sorted(d for d in folder.iterdir() if d.is_dir() and d.name != "old")
    orphans = [str(p.relative_to(folder)) for d in cards
               if d.name not in set(a.excluded_ok or [])
               for p in sorted(d.rglob("*"))
               if p.is_file() and p.suffix in (".diff", ".patch")
               and "old" not in p.relative_to(d).parts and p.resolve() not in composed]
    g.check("every card with a diff is composed or excluded", not orphans, ", ".join(orphans) or "ok")
    bad = []
    for d in cards:
        r = subprocess.run([_sys.executable, str(TOOLS / "patch_packet_preflight.py"), str(d)], capture_output=True, text=True)
        try:
            found = [f for f in json.loads(r.stdout)["findings"] if f["code"] in BLOAT_CODES]
        except (ValueError, KeyError):
            found = [{"code": "PREFLIGHT_UNREADABLE", "relative_path": r.stderr.strip()[-80:]}]
        if found:
            bad.append(f"{d.name}: " + ", ".join(f"{f['code']} {f['relative_path']}" for f in found[:3]))
    g.check("no bloat or unsafe payload (patch_packet_preflight)", not bad, "; ".join(bad) or "ok")
    if a.replay:
        r = subprocess.run(["bash", str(script)], capture_output=True, text=True)
        tail = (r.stdout.strip().splitlines() or [""])[-1]
        g.check("compose replays cleanly", r.returncode == 0 and "ALL APPLIED; .orig/.rej files: 0" in r.stdout,
                f"exit {r.returncode}; " + tail[:120])
    return g.report(Path(a.receipt) if a.receipt else folder / "HANDOFF_GATE_RECEIPT.json")


def deliverable(a) -> int:
    g, folder = Gate(), Path(a.folder).resolve()
    mds = [p for p in folder.rglob("*.md") if "old" not in p.relative_to(folder).parts]
    if mds:
        r = subprocess.run([_sys.executable, str(TOOLS / "check_md_links.py"), *map(str, mds)], capture_output=True, text=True)
        g.check("markdown links resolve (check_md_links)", r.returncode == 0,
                f"{len(mds)} files" + ("" if r.returncode == 0 else "; " + " | ".join(r.stdout.strip().splitlines()[-3:])[:300]))
    linked, missing = set(), []
    for idx in a.index or []:
        ip = folder / idx
        for t in re.findall(r"\]\(([^)]+\.(?:png|html|pdf|svg|tsv))\)", ip.read_text()):
            p = (ip.parent / urllib.parse.unquote(t)).resolve()
            linked.add(p)
            if not p.exists():
                missing.append(t)
    if a.index:
        g.check("every file an index links exists", not missing, f"{len(linked)} linked" + (f"; missing {missing[:5]}" if missing else ""))
    if a.figure_dir:
        figs = [p.resolve() for d in a.figure_dir for p in (folder / d).rglob("*.png")]
        unlinked = [str(p.relative_to(folder)) for p in figs if p not in linked]
        g.check("every figure is linked by an index", not unlinked, f"{len(unlinked)} unlinked" + (f": {unlinked[:3]}" if unlinked else ""))
    short = [f"{p.name}: {m.group(0)[:70]}" for p in mds + list(folder.glob("*.tsv"))
             for m in SHORT_IDENTITY.finditer(p.read_text(errors="replace"))]
    g.check("BGC identities carry the alias (strain / node / region / BGC)", not short,
            f"{len(short)} short" + (f", e.g. {short[0]}" if short else ""))
    claims = []
    for p in folder.glob("*.py"):
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if any(c in line for c in DRAW_CALLS):
                text = " ".join(re.findall(r"[\"']([^\"']+)[\"']", line))
                hits = [m.group(0) for m in FIGURE_BANNED_TEXT.finditer(text)] + (["class-level"] if class_level_hedge(text) else [])
                if hits:
                    claims.append(f"{p.name}:{i} {hits}")
    g.check("no claim wording drawn on figures (figure_policy)", not claims, "; ".join(claims[:4]) or "ok")
    return g.report(Path(a.receipt) if a.receipt else folder / "HANDOFF_GATE_RECEIPT.json")


def reply(a) -> int:
    g, f = Gate(), Path(a.file).resolve()
    root = Path(a.root).resolve() if a.root else Path.cwd()
    text = f.read_text()
    hrefs = re.findall(r"\]\(([^)\s]+(?:\([^)\s]*\)[^)\s]*)?)\)", text)
    bad = []
    for t in hrefs:
        if re.match(r"^(https?|mailto):", t) or t.startswith("#"):
            continue
        path = urllib.parse.unquote(re.sub(r":\d+$", "", t))
        target = (root / path).resolve()
        if not target.is_file() or root not in target.parents:
            bad.append(t)
    g.check("reply links open files under the project root", not bad, "; ".join(bad[:5]) or f"{len(hrefs)} links")
    raw = [t for t in re.findall(r"\]\(([^)]*)\)", text) if " " in t]
    g.check("reply links encode spaces", not raw, "; ".join(raw[:3]) or "ok")
    parens = [t for t in hrefs if "(" in t or ")" in t]
    g.check("reply links encode parentheses as %28 %29", not parens, "; ".join(parens[:3]) or "ok")
    return g.report(Path(a.receipt) if a.receipt else f.with_suffix(".handoff_gate.json"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("patches")
    p.add_argument("folder"); p.add_argument("--compose", required=True); p.add_argument("--replay", action="store_true")
    p.add_argument("--excluded-ok", nargs="*"); p.add_argument("--var", action="append", help="NAME=PATH for $NAME in the script")
    d = sub.add_parser("deliverable")
    d.add_argument("folder"); d.add_argument("--index", action="append"); d.add_argument("--figure-dir", action="append")
    r = sub.add_parser("reply")
    r.add_argument("file"); r.add_argument("--root")
    for s in (p, d, r):
        s.add_argument("--receipt")
    a = ap.parse_args(argv)
    return {"patches": patches, "deliverable": deliverable, "reply": reply}[a.mode](a)


if __name__ == "__main__":
    raise SystemExit(main())
