#!/usr/bin/env python3
"""emit_modeb_template_full50.py — emit a §1–§50 Mode B template.

WHY THIS EXISTS
`mamey emit-modeb-template` emits the 48-section profile (§1–§48) and has no profile
selector. `docs/MODEB_50_SECTION_CONTRACT_CANDIDATE.md` states plainly:

    "This document change alone does not migrate emitters, gates or parsers."

So the 50-section contract has no emitter. This tool supplies one WITHOUT re-implementing
any engine logic: it shells to the real `emit-modeb-template` (so the BLASTp-completeness
HARD gate, the package binding, the observed gene table and §1–§47 all come from the
engine), then applies the migration the contract itself declares:

    "Migrate the former §48 synthesis into §19 without loss and the former §4 matrix
     into §50 without duplication."

Migration applied (deterministic, contract-declared — nothing invented):
  §1–§47   verbatim from the engine template.
  §4       keeps its interpretive blocks; its gene MATRIX moves to §50 (no duplication).
  §19      receives the former §48 synthesis body, labelled as a migrated block.
  §48      NEW — biosynthetic gene/domain/machinery citations (contract requirement §48).
  §49      NEW — genus secondary-metabolite / broader-context citations (§49).
  §50      NEW — the migrated complete gene matrix, under the contract's own §50 table rules.

Section headings for §48–§50 are derived from the contract's numbered requirements, which
carry no separate titles. The verbatim requirement text is emitted under each heading as the
authoring scope, so the contract's own words are the authority.

FAIL-CLOSED: refuses if the bundled Markdown contract's SHA-256 does not match
`source_document.sha256` in the frozen JSON. A pinned selection config is only meaningful
while those bytes are unchanged.

Claim-safety: a section heading is a scope statement. Emitting it supplies no evidence and
establishes no biological conclusion. Judgment deferred.

Usage:
  python3 tools/emit_modeb_template_full50.py --package <pkg> --bgc <BGC_ID> --out card.md
      [--bundle <bundle root>] [--python <interpreter>] [--receipt receipt.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CONTRACT_JSON = Path("mamey/data/mode_b/modeb_full50_contract.json")
SECTION_RE = re.compile(r"^## §(\d+)\b(.*)$")

# Short labels for the three new sections. The contract supplies requirements, not titles;
# these labels are stable and the verbatim requirement is emitted beneath each heading.
NEW_TITLES = {
    48: "Biosynthetic gene / domain / machinery citations",
    49: "Genus metabolite & broader biological-context citations",
    50: "Complete displayed-gene evidence table",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_contract(bundle: Path) -> dict:
    """Load the frozen 50-row contract and verify the Markdown it pins is unchanged."""
    jpath = bundle / CONTRACT_JSON
    if not jpath.is_file():
        raise SystemExit(f"FULL50_CONTRACT_MISSING: {jpath}")
    data = json.loads(jpath.read_text(encoding="utf-8"))
    if int(data.get("section_count", 0)) != 50:
        raise SystemExit(f"FULL50_CONTRACT_SHAPE: section_count={data.get('section_count')!r}, expected 50")
    src = data.get("source_document") or {}
    md = bundle / src.get("path", "")
    if not md.is_file():
        raise SystemExit(f"FULL50_SOURCE_MISSING: {md}")
    actual = _sha256(md)
    if actual != src.get("sha256"):
        raise SystemExit(
            "FULL50_CONTRACT_HASH_MISMATCH: "
            f"{md} is {actual}, contract pins {src.get('sha256')}. "
            "Consumer configs pin this document by hash; resolve the identity before emitting."
        )
    rows = {int(s["section_number"]): s["requirement"] for s in data["sections"]}
    if sorted(rows) != list(range(1, 51)):
        raise SystemExit("FULL50_CONTRACT_NUMBERING: sections are not exactly 1..50")
    return {"requirements": rows, "contract_sha256": actual, "json_path": str(jpath)}


def emit_engine_template(bundle: Path, python: str, package: Path, bgc: str) -> str:
    """Shell to the REAL engine emitter. Its BLASTp HARD gate is not bypassed."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "engine_template.md"
        proc = subprocess.run(
            [python, "mamey_run.py", "emit-modeb-template",
             "--package", str(package), "--bgc", bgc, "--out", str(out)],
            cwd=bundle, capture_output=True, text=True, timeout=1800,
        )
        if proc.returncode != 0 or not out.is_file():
            msg = (proc.stdout or "") + (proc.stderr or "")
            raise SystemExit(
                "ENGINE_TEMPLATE_REFUSED (not overridden here — fix the cause, do not waive "
                f"silently):\n{msg.strip()}"
            )
        return out.read_text(encoding="utf-8")


def split_sections(text: str) -> tuple[str, dict[int, list[str]], list[int], str]:
    """Split an emitted template into preamble, per-§ bodies, order, and trailing footer."""
    lines = text.splitlines(keepends=True)
    preamble: list[str] = []
    bodies: dict[int, list[str]] = {}
    order: list[int] = []
    cur: int | None = None
    for line in lines:
        m = SECTION_RE.match(line.rstrip("\n"))
        if m:
            cur = int(m.group(1))
            order.append(cur)
            bodies[cur] = [line]
            continue
        (bodies[cur] if cur is not None else preamble).append(line)
    footer = ""
    if order:
        last = bodies[order[-1]]
        # the engine's trailing italic note belongs to the document, not to §48
        for i, line in enumerate(last):
            if line.lstrip().startswith("*Template emitted by"):
                footer = "".join(last[i:])
                bodies[order[-1]] = last[:i]
                break
    return "".join(preamble), bodies, order, footer


def extract_matrix(body: list[str]) -> tuple[list[str], list[str]]:
    """Split §4 into (kept interpretive lines, the contiguous gene matrix).

    §4 carries SEVERAL tables (the observed gene matrix plus instructional channel and
    keyword tables). Only the gene matrix migrates. It is located by the engine's own
    "**Gene table**" label, falling back to the first table whose header names a locus
    column - never simply "the first table", which would move an instructional one.
    Returns (body, []) unchanged if no gene matrix is present.
    """
    def _is_sep(line: str) -> bool:
        return bool(re.match(r"^\s*\|[\s:|-]+\|\s*$", line))

    def _table_at(i: int) -> bool:
        return (i + 1 < len(body) and body[i].lstrip().startswith("|")
                and _is_sep(body[i + 1]))

    start = None
    # primary anchor: the engine's labelled gene table
    for i, line in enumerate(body):
        if line.lstrip().startswith("**Gene table**"):
            for j in range(i, min(i + 8, len(body))):
                if _table_at(j):
                    start = j
                    break
            break
    # fallback: first table whose header names a locus/gene column
    if start is None:
        for i in range(len(body) - 1):
            if _table_at(i) and re.search(r"locus[ _]?tag|\bgene\b", body[i], re.I):
                start = i
                break
    if start is None:
        return body, []
    end = start + 2
    while end < len(body) and body[end].lstrip().startswith("|"):
        end += 1
    return body[:start] + body[end:], body[start:end]


def build(bundle: Path, python: str, package: Path, bgc: str) -> tuple[str, dict]:
    contract = load_contract(bundle)
    reqs = contract["requirements"]
    engine_text = emit_engine_template(bundle, python, package, bgc)
    preamble, bodies, order, footer = split_sections(engine_text)

    if not order:
        raise SystemExit("ENGINE_TEMPLATE_UNPARSEABLE: no '## §N' headings found")
    if order != sorted(order) or len(set(order)) != len(order):
        raise SystemExit(f"ENGINE_TEMPLATE_ORDER: sections not unique and ascending: {order}")

    actions: list[str] = []

    # --- former §4 matrix -> §50 (without duplication) -----------------------------
    matrix: list[str] = []
    if 4 in bodies:
        kept, matrix = extract_matrix(bodies[4])
        if matrix:
            bodies[4] = kept + [
                "\n**Gene matrix migrated to §50** (contract: *\"the former §4 matrix into §50 "
                "without duplication\"*). §4 retains interpretation; the full roster is §50.\n",
            ]
            actions.append(f"moved §4 gene matrix ({len(matrix)} lines) to §50")
        else:
            actions.append("§4 carried no contiguous matrix; nothing migrated")

    # --- former §48 synthesis -> §19 (without loss) ---------------------------------
    former48 = bodies.pop(48, None)
    if former48 is not None:
        order = [n for n in order if n != 48]
        if 19 not in bodies:
            raise SystemExit("MIGRATION_TARGET_MISSING: §19 absent, cannot migrate the former §48")
        carried = "".join(former48[1:]).strip("\n")
        bodies[19] = bodies[19] + [
            "\n#### Migrated former §48 — cross-cohort synthesis & claim ceiling\n",
            "<!-- Migrated per MODEB_50_SECTION_CONTRACT_CANDIDATE.md: \"Migrate the former §48 "
            "synthesis into §19 without loss\". Author here; do not re-create a §48 synthesis "
            "section. Legacy 48-section cards keep their own §48 and are read as legacy. -->\n",
            (carried + "\n") if carried else "",
        ]
        actions.append("migrated former §48 synthesis into §19")

    # --- new §48, §49, §50 -----------------------------------------------------------
    for n in (48, 49, 50):
        block = [f"## §{n} {NEW_TITLES[n]}\n", "\n",
                 f"<!-- CONTRACT §{n} (verbatim from modeb_full50_contract.json): {reqs[n]} -->\n"]
        if n == 50 and matrix:
            block += ["\n**Complete displayed-gene evidence table** (migrated from §4; one row per "
                      "exact-region and boundary-context gene). `qcov NR` means not reported, never "
                      "zero. ClusteredNR is not full nr. Missing or unbound evidence carries a typed "
                      "state and is not biological absence.\n", "\n"] + matrix
        elif n == 50:
            block += ["\n<!-- HOLD: no contiguous gene matrix was present in the engine template's "
                      "§4. Supply the displayed-gene roster and state the typed hold; do not invent "
                      "rows. -->\n"]
        else:
            block += ["\n<!-- Author: one entry per citation — identifiable citation, direct "
                      "DOI/PMID/publisher link, what the source supports, relevance to THIS locus, "
                      "transfer limits, and abstract-only vs full-text. Primary sources for "
                      "mechanistic claims; label reviews as synthesis. No quota, no invented "
                      "references, no generic filler. -->\n"]
        bodies[n] = block
        order.append(n)
        actions.append(f"emitted new §{n}")

    order = sorted(set(order))
    if order != list(range(1, 51)):
        missing = sorted(set(range(1, 51)) - set(order))
        extra = sorted(set(order) - set(range(1, 51)))
        raise SystemExit(f"FULL50_SHAPE_FAILED: missing={missing} unexpected={extra}")

    out = preamble + "".join("".join(bodies[n]) for n in order)
    if footer:
        out += ("\n" if not out.endswith("\n") else "") + footer.replace(
            "§1–§48", "§1–§50").replace("§1-§48", "§1-§50")

    receipt = {
        "profile": "MODEB_FULL50_MIGRATED",
        "section_count": len(order),
        "sections": order,
        "contract_json": contract["json_path"],
        "contract_markdown_sha256": contract["contract_sha256"],
        "engine_template_sha256": hashlib.sha256(engine_text.encode("utf-8")).hexdigest(),
        "emitted_sha256": hashlib.sha256(out.encode("utf-8")).hexdigest(),
        "migration_actions": actions,
        "package": str(package),
        "bgc": bgc,
        "claim_ceiling": (
            "A section heading is a scope statement. Emission supplies no evidence and "
            "establishes no biological conclusion. Judgment deferred."
        ),
    }
    return out, receipt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Emit a §1–§50 Mode B template (migrated from the engine's §1–§48).")
    ap.add_argument("--package", required=True, type=Path)
    ap.add_argument("--bgc", required=True)
    ap.add_argument("--out", type=Path, help="write the template here (default: stdout)")
    ap.add_argument("--bundle", type=Path, default=Path(__file__).resolve().parents[1],
                    help="bundle root containing mamey_run.py (default: parent of tools/)")
    ap.add_argument("--python", default=sys.executable,
                    help="interpreter for the engine call (needs Python >= 3.12)")
    ap.add_argument("--receipt", type=Path, help="write the emission receipt JSON here")
    args = ap.parse_args(argv)

    if not (args.bundle / "mamey_run.py").is_file():
        raise SystemExit(f"BUNDLE_ROOT_INVALID: no mamey_run.py under {args.bundle}")

    text, receipt = build(args.bundle, args.python, args.package, args.bgc)
    notes = []
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        notes.append(f"full50 template -> {args.out}  ({receipt['section_count']} sections)")
    else:
        sys.stdout.write(text)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        notes.append(f"receipt -> {args.receipt}")
    if notes:
        print("\n".join(notes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
