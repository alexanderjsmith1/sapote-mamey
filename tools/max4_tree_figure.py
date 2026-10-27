#!/usr/bin/env python3
"""Build the tip table for a max-4-reference genome tree and render it through tools/render_max4_tree.R.

Two subcommands. Neither infers a tree; both read a finished IQ-TREE tree (.treefile or .contree).

metadata  Writes the figure metadata table the renderer reads. Rows come from any of:
            --table TSV       an existing table (tip, role, label_concise, source_display, geography_display, ...);
            --ncbi-json JSON  {accession: {organism, strain, fromtype, isolation_source, host, geo_loc_name}};
            --ncbi-jsonl F    NCBI Datasets genome summary lines (accession, organism, assembly_info.biosample, type_material);
            --queries TSV     isolate rows (tip, label_concise, source_display, geography_display; optional genus, host_group).
          Reference labels from NCBI records are the deposited organism, the strain when the name lacks it, " [Type]" only when
          NCBI Assembly says "assembly from type material", and the accession in brackets. Source and country are copied as
          deposited. Empty, "missing" and "not applicable" values stay empty; no placeholder is written.
          Edits are explicit inputs, each logged in <out>_changes.tsv:
            --overrides TSV   tip, field, value, reason (owner rulings; always applied);
            --fill-blank TSV  accession, field, value, evidence (fills a cell only when it is empty or "not deposited");
            --strip-query-brackets, --strip-text TEXT (tip-label notes such as " [outgroup]");
            --restore TSV (tip, full) then --shorten N (a long source is cut at a word with "..."; <out>_shortened.tsv keeps
            the full text for the caption).
          --tree keeps rows for the tree's tips and refuses a tip without a row. --max-refs-per-query N refuses more than N
          references per isolate (needs an anchor column naming each reference's isolate). Tips with neither a deposited source
          nor a country are listed in the receipt by full label, so the caption can name them.

render    Runs tools/render_max4_tree.R with options from --spec JSON ({"options": {"width": 9.6, "root": "TIP", ...}}; keys are
          the MAX4_* names with or without the prefix, any case) and --set KEY=VALUE. --groups, --genus-dots (colors from
          mamey/data/genus_palette.json, --palette-set, --genus-color GENUS=RRGGBB) and --query-groups switch on the color
          options. After drawing it reads the smallest text size back from the PDF (8 pt floor) and writes <stem>_receipt.json
          with every option and the SHA-256 of each input and output. --dry-run writes the receipt without drawing.
"""
from __future__ import annotations

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.logging_setup import get_logger as _get_logger  # noqa: E402

_OUT = _get_logger(__name__)
TOOL = "max4_tree_figure"
RENDERER = ROOT / "tools" / "render_max4_tree.R"
PALETTE = ROOT / "mamey" / "data" / "genus_palette.json"
REQUIRED = ["tip", "role", "label_concise", "source_display", "geography_display"]
ROLES = {"QUERY", "REFERENCE", "OUTGROUP"}
NULL = {"", "none", "missing", "not recorded", "not applicable", "na", "n/a", "unknown", "not collected", "not provided",
        "not known"}
FILLABLE = {"", "not deposited"}
TYPE_TEXT = "assembly from type material"
EDITABLE = {"label_concise", "source_display", "geography_display", "role", "genus", "host_group", "source_group", "geo_group"}
OPTIONS = {
    "WIDTH", "HMAX", "H", "ROWIN", "RESERVE", "PAD", "DPI", "MIN_BRANCH", "LEFT_PAD", "LEFT_PT", "SCALE_X", "CLIP_OFF",
    "LAB", "SMALL", "HEAD", "WRAP", "WRAP_GEO", "LINEHEIGHT", "SP_ROMAN", "DROP_TIPS", "META_EXTRA", "ROOT", "DROP_ROOT",
    "BREAK_TIP", "SUPPORT_MIN", "SUPPORT_HJUST", "SUPPORT_BG", "SUPPORT_DODGE", "NO_META", "STRIPS", "GENUS_DOTS",
    "GENUS_ROWS", "QUERY_GROUPS", "QUERY_GROUP_TITLE", "LEGEND_BOX", "LEGEND_KEY_PT",
}
TEXT_KEYS = {"LAB": 8.0, "SMALL": 8.0, "HEAD": 8.5}
MIN_PT = 8.0


class InputError(ValueError):
    """A refused input."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bound(paths) -> list:
    return [{"path": str(Path(p).resolve()), "sha256": sha256(Path(p))} for p in paths if p]


def clean(value) -> str:
    text = " ".join(str(value or "").split())
    return "" if text.lower() in NULL or text.lower().startswith("missing") else text


def read_tsv(path: Path, required) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            raise InputError(f"{path}: missing columns {missing}")
        return [dict(r) for r in reader]


def write_tsv(path: Path, fields, rows) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=list(fields), delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def tree_tips(path: Path) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    tips = re.findall(r"[(,]\s*([^(),:;\s]+)(?=\s*[:,)])", text)
    if not tips:
        raise InputError(f"{path}: no tip labels found")
    return tips


# ----------------------------------------------------------------------------------------------- NCBI records

def record_from_json(accession: str, rec: dict) -> dict:
    return {"accession": accession, "organism": rec.get("organism", ""), "strain": rec.get("strain", ""),
            "fromtype": rec.get("fromtype", ""), "isolation_source": rec.get("isolation_source", ""),
            "host": rec.get("host", ""), "geo_loc_name": rec.get("geo_loc_name", "")}


def record_from_datasets(line: dict) -> dict:
    org = line.get("organism") or {}
    bios = (line.get("assembly_info") or {}).get("biosample") or {}
    attrs = {a.get("name"): a.get("value") for a in bios.get("attributes", []) if isinstance(a, dict)}
    return {"accession": line.get("accession", ""), "organism": org.get("organism_name", ""),
            "strain": (org.get("infraspecific_names") or {}).get("strain", ""),
            "fromtype": (line.get("type_material") or {}).get("type_display_text", ""),
            "isolation_source": attrs.get("isolation_source", ""), "host": attrs.get("host", ""),
            "geo_loc_name": attrs.get("geo_loc_name", "")}


def reference_row(rec: dict, args) -> dict:
    acc, org, strain = rec["accession"], " ".join(rec["organism"].split()), " ".join(str(rec["strain"] or "").split())
    if not acc or not org:
        raise InputError(f"NCBI record without accession or organism: {rec}")
    name = org if (not strain or strain in org) else f"{org} {strain}"
    if (rec.get("fromtype") or "").strip() == TYPE_TEXT:
        name += " [Type]"
    src = clean(rec.get("isolation_source"))
    if not src and args.source_from_host and clean(rec.get("host")):
        src = "host: " + clean(rec.get("host"))
    geo = clean(rec.get("geo_loc_name"))
    if args.country_part:
        geo = geo.split(":")[0].strip()
    role = "OUTGROUP" if acc in args.outgroup else "REFERENCE"
    return {"tip": acc, "role": role, "label_concise": f"{name} ({acc})", "source_display": src, "geography_display": geo,
            "type_material": (rec.get("fromtype") or "").strip()}


# ----------------------------------------------------------------------------------------------- metadata

def build_metadata(args) -> dict:
    rows, fields, log = [], list(REQUIRED), []
    def add_fields(keys):
        for k in keys:
            if k not in fields:
                fields.append(k)
    if args.queries:
        q = read_tsv(args.queries, ["tip", "label_concise", "source_display", "geography_display"])
        for r in q:
            r.setdefault("role", "QUERY")
            r["role"] = r["role"] or "QUERY"
        add_fields(k for r in q for k in r)
        rows += q
    if args.table:
        t = read_tsv(args.table, REQUIRED)
        add_fields(k for r in t for k in r)
        rows += t
    recs = []
    if args.ncbi_json:
        data = json.loads(Path(args.ncbi_json).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise InputError("--ncbi-json must map accession to a record")
        recs += [record_from_json(a, r) for a, r in data.items()]
    if args.ncbi_jsonl:
        for line in Path(args.ncbi_jsonl).read_text(encoding="utf-8").splitlines():
            if line.strip():
                recs.append(record_from_datasets(json.loads(line)))
    if recs:
        add_fields(["type_material"])
        rows += [reference_row(r, args) for r in recs]
    if not rows:
        raise InputError("no rows: give --table, --queries, --ncbi-json or --ncbi-jsonl")
    for r in rows:
        for k in fields:
            r.setdefault(k, "")
        if r["role"] not in ROLES:
            raise InputError(f"{r['tip']}: role {r['role']!r} is not one of {sorted(ROLES)}")
    seen = set()
    for r in rows:
        if not r["tip"] or r["tip"] in seen:
            raise InputError(f"empty or duplicate tip {r['tip']!r}")
        seen.add(r["tip"])
    if args.tree:
        tips = tree_tips(args.tree)
        missing = [t for t in tips if t not in seen]
        if missing:
            raise InputError(f"{len(missing)} tree tips have no row, e.g. {missing[:5]}")
        dropped = [r["tip"] for r in rows if r["tip"] not in set(tips)]
        for t in dropped:
            log.append(("not_in_tree", t, "", "", "", "row dropped: tip not in the tree"))
        order = {t: i for i, t in enumerate(tips)}
        rows = sorted((r for r in rows if r["tip"] in order), key=lambda r: order[r["tip"]])
    by_tip = {r["tip"]: r for r in rows}

    if args.restore:
        for x in read_tsv(args.restore, ["tip", "full"]):
            r = by_tip.get(x["tip"])
            if r and r["source_display"] != x["full"]:
                log.append(("restored", r["tip"], "source_display", r["source_display"], x["full"], "full text of an earlier cut"))
                r["source_display"] = x["full"]
    for r in rows:
        lab = r["label_concise"]
        if args.strip_query_brackets and r["role"] == "QUERY":
            lab = re.sub(r"\s*\[[^\]]*\]\s*$", "", lab)
        for text in args.strip_text:
            lab = lab.replace(text, "")
        lab = " ".join(lab.split())
        if lab != r["label_concise"]:
            log.append(("label", r["tip"], "label_concise", r["label_concise"], lab, "tip-label note removed"))
            r["label_concise"] = lab
    if args.overrides:
        for x in read_tsv(args.overrides, ["tip", "field", "value", "reason"]):
            if x["field"] not in EDITABLE:
                raise InputError(f"--overrides: field {x['field']!r} is not editable")
            if not x["reason"].strip():
                raise InputError(f"--overrides: {x['tip']} {x['field']} has no reason")
            r = by_tip.get(x["tip"])
            if r is None:
                if args.tree:
                    continue
                raise InputError(f"--overrides: no row for tip {x['tip']!r}")
            if x["field"] not in fields:
                fields.append(x["field"])
            log.append(("override", r["tip"], x["field"], r.get(x["field"], ""), x["value"], x["reason"]))
            r[x["field"]] = x["value"]
    if args.fill_blank:
        for x in read_tsv(args.fill_blank, ["accession", "field", "value", "evidence"]):
            if x["field"] not in {"source_display", "geography_display"}:
                raise InputError(f"--fill-blank: field {x['field']!r} must be source_display or geography_display")
            hits = [r for r in rows if r["tip"] == x["accession"] or f"({x['accession']})" in r["label_concise"]]
            for r in hits:
                if r[x["field"]].strip().lower() in FILLABLE:
                    log.append(("filled", r["tip"], x["field"], r[x["field"]], x["value"], x["evidence"]))
                    r[x["field"]] = x["value"]
                else:
                    log.append(("kept_deposited", r["tip"], x["field"], r[x["field"]], r[x["field"]], "deposited value kept"))
    shortened = []
    if args.shorten:
        for r in rows:
            full = r["source_display"]
            if len(full) > args.shorten and not full.endswith(("…", "...")):
                cut = full[:args.shorten].rsplit(" ", 1)[0].rstrip(" ,;") + "..."
                shortened.append({"tip": r["tip"], "shown": cut, "full": full})
                log.append(("shortened", r["tip"], "source_display", full, cut, "long source; give the full text in the caption"))
                r["source_display"] = cut

    type_unverified = []
    for r in rows:
        if "[Type]" in r["label_concise"]:
            if "type_material" in r and r.get("type_material", "").strip():
                if r["type_material"].strip() != TYPE_TEXT:
                    raise InputError(f"{r['tip']}: [Type] on the label but NCBI type_material is {r['type_material']!r}")
            else:
                type_unverified.append(r["tip"])
    queries = [r for r in rows if r["role"] == "QUERY"]
    refs = [r for r in rows if r["role"] == "REFERENCE"]
    per_query = {}
    if "anchor" in fields:
        for r in refs:
            per_query.setdefault(r.get("anchor", "") or "(no anchor)", []).append(r["tip"])
    if args.max_refs_per_query:
        if "anchor" not in fields:
            raise InputError("--max-refs-per-query needs an anchor column naming each reference's isolate")
        over = {k: len(v) for k, v in per_query.items() if len(v) > args.max_refs_per_query}
        if over:
            raise InputError(f"more than {args.max_refs_per_query} references for {over}")
    no_meta = [r["label_concise"] for r in rows if not r["source_display"].strip() and not r["geography_display"].strip()]
    return {"rows": rows, "fields": fields, "log": log, "shortened": shortened, "type_unverified": type_unverified,
            "summary": {"tips": len(rows), "queries": len(queries), "references": len(refs),
                        "outgroups": sum(r["role"] == "OUTGROUP" for r in rows),
                        "references_per_query": {k: len(v) for k, v in per_query.items()},
                        "no_deposited_source_or_country": no_meta,
                        "no_source": sum(not r["source_display"].strip() for r in rows),
                        "no_country": sum(not r["geography_display"].strip() for r in rows)}}


def cmd_metadata(args) -> int:
    out = Path(args.out)
    stem = out.with_suffix("")
    products = [out, Path(f"{stem}_changes.tsv"), Path(f"{stem}_shortened.tsv"), Path(f"{stem}_receipt.json")]
    if any(p.exists() for p in products):
        raise InputError(f"refusing to overwrite {out} or its sidecars")
    res = build_metadata(args)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_tsv(out, res["fields"], res["rows"])
    with products[1].open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeWriter(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["kind", "tip", "field", "before", "after", "reason"])
        writer.writerows(res["log"])
    written = [out, products[1]]
    if res["shortened"]:
        write_tsv(products[2], ["tip", "shown", "full"], res["shortened"])
        written.append(products[2])
    inputs = [args.table, args.queries, args.ncbi_json, args.ncbi_jsonl, args.tree, args.overrides, args.fill_blank,
              args.restore, Path(__file__)]
    receipt = {"tool": TOOL, "step": "metadata", "inputs": bound(inputs), "outputs": bound(written),
               "settings": {"strip_query_brackets": args.strip_query_brackets, "strip_text": args.strip_text,
                            "shorten": args.shorten, "outgroup": args.outgroup, "country_part": args.country_part,
                            "source_from_host": args.source_from_host, "max_refs_per_query": args.max_refs_per_query},
               "summary": res["summary"], "type_label_without_ncbi_field": res["type_unverified"]}
    products[3].write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    s = res["summary"]
    _OUT.info(f"{out}: {s['tips']} tips ({s['queries']} isolates, {s['references']} references, {s['outgroups']} outgroup); "
              f"{len(res['log'])} logged changes; {s['no_source']} without source, {s['no_country']} without country")
    for name in s["no_deposited_source_or_country"]:
        _OUT.info(f"  no deposited source or country (name it in the caption): {name}")
    if res["type_unverified"]:
        _OUT.info(f"  [Type] labels with no type_material column to check: {len(res['type_unverified'])}")
    return 0


# ----------------------------------------------------------------------------------------------- render

def option_key(key: str) -> str:
    k = key.strip().upper().replace("-", "_")
    k = k[5:] if k.startswith("MAX4_") else k
    if k not in OPTIONS:
        raise InputError(f"unknown renderer option {key!r}")
    return "MAX4_" + k


def collect_options(args) -> dict:
    opts = {}
    if args.spec:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        items = spec.get("options", spec) if isinstance(spec, dict) else None
        if not isinstance(items, dict):
            raise InputError("--spec must be a JSON object, optionally with an options object")
        for k, v in items.items():
            opts[option_key(k)] = "1" if v is True else "" if v is False else str(v)
    for item in args.set:
        if "=" not in item:
            raise InputError(f"--set {item!r}: expected KEY=VALUE")
        k, v = item.split("=", 1)
        opts[option_key(k)] = v
    for short, default in TEXT_KEYS.items():
        key = "MAX4_" + short
        value = float(opts.get(key, default))
        if value < MIN_PT:
            raise InputError(f"{key}={value:g}: text below {MIN_PT:g} pt is refused")
    return opts


def genus_palette(metadata: Path, args, out: Path) -> tuple[Path, list]:
    rows = read_tsv(metadata, ["genus"])
    config = json.loads(PALETTE.read_text(encoding="utf-8"))
    colours = dict(config["default"])
    colours.update(config["sets"].get(args.palette_set or "", {}))
    for item in args.genus_colour:
        genus, _, colour = item.partition("=")
        colours[genus.strip()] = colour.strip() if colour.startswith("#") else "#" + colour.strip()
    present = sorted({r["genus"] for r in rows if r["genus"].strip()})
    fallback = [g for g in present if g not in colours]
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeWriter(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["genus", "colour"])
        writer.writerows((g, colours.get(g, config["fallback"])) for g in present)
    return out, fallback


def cmd_render(args) -> int:
    stem = Path(args.out)
    receipt_path = Path(f"{stem}_receipt.json")
    outputs = [Path(f"{stem}.pdf"), Path(f"{stem}.png"), Path(f"{stem}.svg")]
    if any(p.exists() for p in outputs + [receipt_path]):
        raise InputError(f"refusing to overwrite {stem}.* or its receipt")
    opts = collect_options(args)
    stem.parent.mkdir(parents=True, exist_ok=True)
    extra_inputs, fallback = [], []
    if args.groups:
        opts["MAX4_STRIPS"] = str(Path(args.groups).resolve())
    if args.genus_dots:
        pal, fallback = genus_palette(Path(args.metadata), args, Path(f"{stem}_genus_palette.tsv"))
        opts["MAX4_GENUS_DOTS"] = str(pal.resolve())
        extra_inputs += [PALETTE, pal]
    if args.query_groups:
        opts["MAX4_QUERY_GROUPS"] = str(Path(args.query_groups).resolve())
    for key in ("MAX4_STRIPS", "MAX4_QUERY_GROUPS"):
        if key in opts:
            extra_inputs.append(Path(opts[key]))
    command = [args.rscript or shutil.which("Rscript") or "Rscript", str(RENDERER), str(Path(args.tree).resolve()),
               str(Path(args.metadata).resolve()), str(stem.resolve())] + (["prune"] if args.prune else [])
    receipt = {"tool": TOOL, "step": "render", "renderer": str(RENDERER.relative_to(ROOT)), "options": opts,
               "command": command, "genus_fallback_colour": fallback,
               "inputs": bound([args.tree, args.metadata, args.spec, RENDERER, Path(__file__)] + extra_inputs)}
    if args.dry_run:
        receipt["status"] = "DRY_RUN"
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        _OUT.info(f"dry run: {receipt_path}")
        return 0
    if not shutil.which(command[0]) and not Path(command[0]).exists():
        raise InputError("Rscript is required to draw the tree")
    env = dict(os.environ)
    env.update(opts)
    env.setdefault("OMP_NUM_THREADS", "2")
    run = subprocess.run(command, env=env, capture_output=True, text=True)
    receipt["renderer_stdout"] = run.stdout.splitlines()
    if run.returncode != 0:
        receipt["status"] = "RENDER_FAILED"
        receipt["renderer_stderr"] = run.stderr.splitlines()[-20:]
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        raise InputError(f"renderer failed (exit {run.returncode}); see {receipt_path}")
    made = [p for p in outputs if p.exists()]
    width = float(opts.get("MAX4_WIDTH", "9.8"))
    from tools._min_text_check import check as _min_text
    text = _min_text(str(outputs[0]), MIN_PT, width)
    receipt.update({"outputs": bound(made), "min_text": text,
                    "status": "PASS" if text["status"] == "PASS" else "MIN_TEXT_FAIL"})
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for line in receipt["renderer_stdout"]:
        _OUT.info(line)
    _OUT.info(f"{stem}: {len(made)} files; smallest text {text['smallest_pt']} pt; receipt {receipt_path}")
    if fallback:
        _OUT.info(f"  genera drawn in the fallback colour: {', '.join(fallback)}")
    return 0 if receipt["status"] == "PASS" else 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("metadata", help="build the tip table")
    m.add_argument("--out", required=True, help="output TSV")
    m.add_argument("--table", type=Path)
    m.add_argument("--queries", type=Path)
    m.add_argument("--ncbi-json", type=Path)
    m.add_argument("--ncbi-jsonl", type=Path)
    m.add_argument("--tree", type=Path, help="keep only this tree's tips (refuses a tip without a row)")
    m.add_argument("--outgroup", action="append", default=[], help="accession drawn as the outgroup (repeatable)")
    m.add_argument("--country-part", action="store_true", help="keep geo_loc_name before ':' (country only)")
    m.add_argument("--source-from-host", action="store_true", help="when isolation_source is empty, show 'host: <host>'")
    m.add_argument("--strip-query-brackets", action="store_true", help="drop a trailing [..] note from isolate labels")
    m.add_argument("--strip-text", action="append", default=[], help="text removed from every label, e.g. ' [outgroup]'")
    m.add_argument("--overrides", type=Path)
    m.add_argument("--fill-blank", type=Path)
    m.add_argument("--restore", type=Path)
    m.add_argument("--shorten", type=int, default=0, help="cut sources longer than N characters (0 = off)")
    m.add_argument("--max-refs-per-query", type=int, default=0, help="refuse more than N references per isolate (0 = report)")
    r = sub.add_parser("render", help="draw the tree through tools/render_max4_tree.R")
    r.add_argument("--tree", required=True, type=Path)
    r.add_argument("--metadata", required=True, type=Path)
    r.add_argument("--out", required=True, help="output stem, without suffix")
    r.add_argument("--spec", type=Path, help="JSON options")
    r.add_argument("--set", action="append", default=[], help="KEY=VALUE renderer option (repeatable; wins over --spec)")
    r.add_argument("--prune", action="store_true", help="keep only the tips in the metadata table")
    r.add_argument("--groups", type=Path, help="colour strips table (kind, group, colour[, value_as_deposited])")
    r.add_argument("--genus-dots", action="store_true", help="genus-colored tip dots from the bundle genus palette")
    r.add_argument("--palette-set", choices=["moss", "attine"])
    r.add_argument("--genus-color", dest="genus_colour", action="append", default=[], metavar="GENUS=RRGGBB", help="color for one genus (repeatable)")
    r.add_argument("--genus-colour", dest="genus_colour", action="append", default=[], help=argparse.SUPPRESS)  # earlier spelling, same option
    r.add_argument("--query-groups", type=Path, help="isolate label colours by host_group (group, colour)")
    r.add_argument("--rscript", help="Rscript executable (default: on PATH)")
    r.add_argument("--dry-run", action="store_true", help="write the receipt and command without drawing")
    args = parser.parse_args(argv)
    try:
        return cmd_metadata(args) if args.command == "metadata" else cmd_render(args)
    except (InputError, OSError, json.JSONDecodeError, KeyError) as exc:
        _OUT.error(str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
