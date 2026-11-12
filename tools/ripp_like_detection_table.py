#!/usr/bin/env python3
"""RiPP-like protoclusters by detection domain, with full BGC identities, for one or more genomes.

For each genome give its antiSMASH ZIP and the package inventory (<ID>_2_inventory.csv, columns Contig,
antiSMASH_Region, BGC_ID) that was built from the same ZIP:
  ripp_like_detection_table.py --genome ID ZIP INVENTORY [--genome ...] --outdir DIR --stem NAME
Each RiPP-like protocluster gets its identity, strain / contig / region / BGC alias, from the inventory row
with the same contig and region. A protocluster with no single matching row gets identity_status
IDENTITY_HOLD and a blank alias; nothing is guessed.

Outputs (no overwrite): <stem>_protoclusters.tsv (one row per protocluster), <stem>_domain_summary.tsv
(protoclusters per trigger-domain combination, with how many sit in regions called RiPP-like alone and on a
contig edge) and <stem>_receipt.json (input SHA-256, per-genome record-pass receipts, row counts).
A detection domain names the antiSMASH rule that fired; it is not a product, structure or activity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

try:
    from mamey.ripp_like_detection import domain_summary, extract_ripp_like_triggers
except ImportError:  # run from tools/ without the package on the path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from mamey.ripp_like_detection import domain_summary, extract_ripp_like_triggers
from mamey.csv_safety import SafeDictWriter  # noqa: E402  (formula-injection guard for TSV output)

COLS = ["identity", "identity_status", "strain", "contig", "region", "bgc_alias", "protocluster_number",
        "protocluster_location", "contig_edge", "region_products", "region_is_ripp_like_only",
        "trigger_domains", "trigger_locus_tags", "trigger_lengths_aa", "status", "source"]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_inventory(path: Path) -> dict[tuple[str, str], list[str]]:
    with open(path, newline="") as fh:
        rd = csv.DictReader(fh)
        need = {"Contig", "antiSMASH_Region", "BGC_ID"}
        if not rd.fieldnames or not need <= set(rd.fieldnames):
            sys.exit(f"{path}: needs columns {sorted(need)}")
        idx: dict[tuple[str, str], list[str]] = {}
        for r in rd:
            idx.setdefault((r["Contig"].strip(), r["antiSMASH_Region"].strip()), []).append(r["BGC_ID"].strip())
    return idx


def genome_rows(strain: str, zip_path: Path, inventory: Path):
    rows, receipt = extract_ripp_like_triggers(zip_path)
    bad = [f for f in receipt.get("files", []) if f.get("status") != "READ_COMPLETE"] + receipt.get("archive_errors", [])
    if bad:
        sys.exit(f"{zip_path}: record pass incomplete ({bad[0]}); nothing written")
    idx = load_inventory(inventory)
    out = []
    for r in rows:
        hits = idx.get((r["record_id"], r["region"]), [])
        alias = hits[0] if len(hits) == 1 and hits[0] else ""
        out.append({**r, "strain": strain, "contig": r["record_id"], "bgc_alias": alias,
                    "identity_status": "BOUND" if alias else "IDENTITY_HOLD",
                    "identity": f"{strain} / {r['record_id']} / {r['region']} / {alias}" if alias else ""})
    return out, receipt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--genome", nargs=3, action="append", required=True, metavar=("ID", "ZIP", "INVENTORY"))
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--stem", required=True)
    a = ap.parse_args(argv)
    ids = [g[0] for g in a.genome]
    if len(set(ids)) != len(ids) or any(not i.strip() for i in ids):
        sys.exit("each --genome needs a distinct, non-blank ID")
    a.outdir.mkdir(parents=True, exist_ok=True)
    outs = [a.outdir / f"{a.stem}{s}" for s in ("_protoclusters.tsv", "_domain_summary.tsv", "_receipt.json")]
    ins = {Path(p).resolve() for g in a.genome for p in g[1:]}
    for p in outs:
        if p.exists() or p.resolve() in ins:
            sys.exit(f"refusing to overwrite {p}")
    all_rows, rec = [], {"tool": "tools/ripp_like_detection_table.py", "genomes": []}
    for strain, z, inv in a.genome:
        z, inv = Path(z), Path(inv)
        rows, receipt = genome_rows(strain, z, inv)
        all_rows += rows
        rec["genomes"].append({"id": strain, "zip": str(z), "zip_sha256": sha(z), "inventory": str(inv),
                               "inventory_sha256": sha(inv), "protoclusters": len(rows),
                               "identity_holds": sum(r["identity_status"] != "BOUND" for r in rows),
                               "record_pass": receipt})
    with open(outs[0], "w", newline="") as fh:
        w = SafeDictWriter(fh, fieldnames=COLS, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader(); w.writerows(all_rows)
    summ = domain_summary(all_rows)
    with open(outs[1], "w", newline="") as fh:
        w = SafeDictWriter(fh, fieldnames=list(summ[0]) if summ else ["trigger_domains", "protoclusters"],
                           delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(summ)
    rec.update(protoclusters=len(all_rows), identity_holds=sum(r["identity_status"] != "BOUND" for r in all_rows),
               unresolved=sum(r["status"] != "TRIGGER_FOUND" for r in all_rows),
               outputs={p.name: sha(p) for p in outs[:2]},
               scope="A detection domain names the antiSMASH rule that fired; it is not a product, structure or activity.")
    outs[2].write_text(json.dumps(rec, indent=1) + "\n")
    sys.stdout.write(f"{len(all_rows)} RiPP-like protoclusters; {rec['identity_holds']} identity holds; {rec['unresolved']} unresolved\n")
    for s in summ:
        sys.stdout.write(f"{s['protoclusters']}\t{s['trigger_domains']}\n")
    return all_rows, summ


if __name__ == "__main__":
    main()
