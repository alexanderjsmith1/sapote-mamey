"""reference_panel_ledger.py — characterize the detection panel by separating OBSERVED from COMPUTED.

The reviewer's "are you blinded?" concern is answered by provenance, not blinding: every engine signal is a
deterministic function of what antiSMASH supplied. This tool emits, per BGC, two clearly separated blocks —

  OBSERVED  (antiSMASH supplies): region product type, KnownClusterBlast anchor, edge status, locus size,
            CDS count, the annotation class (are CDS named, gene-symbol-only, or locus-tag-only?), and the
            backbone module counts (PKS_KS / Condensation / AMP-binding) read from aSDomain features.
  COMPUTED  (engine triggers): which T43 markers fired, the architecture class-capacity call + confidence.

Run it over the reference panel to characterize detection, then over unknown genomes to see what is detected
and on what supplied evidence. Usage:

    python3 tools/reference_panel_ledger.py <dir-of-zips> <out.csv>

Both paths are required. The tool exits 1 and writes nothing when no rows are produced.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import csv
from pathlib import Path
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mamey import parsers, class_architecture as A
from mamey.source_scans import run_source_scans
from mamey.crosswalk import contig_key


def _annotation_class(cin):
    """How much did antiSMASH give us to work with on this BGC's CDS?"""
    named = sum(1 for c in cin if c.product and c.product.lower() not in ("none", "hypothetical protein"))
    total = len(cin) or 1
    frac = named / total
    # gene-symbol-only: short alnum products (e.g. LooR1, GtfA, mldA) rather than descriptive names
    short = sum(1 for c in cin if c.product and 0 < len(c.product) <= 7 and " " not in c.product)
    if frac < 0.15:
        return "locus-tag-only"
    if short >= 0.4 * total:
        return "gene-symbol-heavy"
    return "descriptive"


def ledger_for_zip(zip_path):
    bgcs = parsers.parse_bgcs_from_zip(zip_path)
    if not bgcs:
        return []
    cds = parsers.extract_cds_features(zip_path)
    contigs = parsers.extract_contig_sequences(zip_path)
    doms = parsers.extract_domain_features(zip_path)
    ss = run_source_scans(bgcs, cds, contigs, doms)
    per = ss.cctt.get("per_bgc", {})
    vetoed = ss.cctt.get("related_family_vetoes", {})
    rows = []
    for b in bgcs:
        cin = [c for c in cds if contig_key(c.contig) == contig_key(b.contig)
               and not (c.end < b.start or c.start > b.end)]
        ks, c, a, _ = A._module_counts(b, doms)
        arch = A.derive_architecture(b, cds, doms)
        mk = [str(m) for m in per.get(b.bgc_id, [])]
        vmk = [d["marker"] for d in vetoed.get(b.bgc_id, [])]
        rows.append({
            # --- OBSERVED: what antiSMASH supplied ---
            "bgc_id": b.bgc_id,
            "contig": b.contig,
            "region": b.antismash_region or f"region{b.region_number:03d}",
            "obs_kcb_mibig_accession": getattr(b, "closest_mibig_accession", "") or "UNRESOLVED",
            "obs_kcb_protein_hits": "" if b.kcb_protein_hits is None else b.kcb_protein_hits,
            "obs_region_type": "; ".join(b.products),
            "obs_kcb_anchor": getattr(b, "closest_candidate_kcb_product", "") or "UNRESOLVED",
            "obs_edge_status": b.edge_status,
            "obs_size_kb": round((b.end - b.start) / 1000, 1),
            "obs_cds_count": len(cin),
            "obs_annotation_class": _annotation_class(cin),
            "obs_pks_ks": ks,
            "obs_nrps_c": c,
            "obs_nrps_a": a,
            # --- COMPUTED: what the engine triggered ---
            "cmp_t43_markers": "; ".join(mk) or "none",
            "cmp_t43_vetoed": "; ".join(vmk) or "",
            "cmp_architecture_capacity": arch.capacity,
            "cmp_architecture_confidence": arch.confidence,
        })
    return rows


USAGE = ("usage: python tools/reference_panel_ledger.py SRC_DIR OUT_CSV\n"
         "  Characterize reference BGCs: OBSERVED (antiSMASH) vs COMPUTED (engine T43 markers).\n"
         "  SRC_DIR: directory of antiSMASH/MIBiG .zip outputs. Required; there is no default.\n"
         "  OUT_CSV: output path to write. Required; there is no default.\n"
         "  Exit 0: rows written. Exit 1: no rows produced (nothing written). Exit 2: bad arguments.")


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    if any(a in ("-h", "--help") for a in args):
        emit(USAGE)
        return 0
    if len(args) != 2:
        sys.stderr.write("reference_panel_ledger: SRC_DIR and OUT_CSV are both required\n" + USAGE + "\n")
        return 2
    src, out = args
    if not os.path.isdir(src):
        sys.stderr.write(f"reference_panel_ledger: SRC_DIR is not a directory: {src}\n")
        return 2
    zips = sorted(f for f in os.listdir(src) if f.endswith(".zip"))
    all_rows = []
    for zf in zips:
        try:
            rows = ledger_for_zip(os.path.join(src, zf))
            for r in rows:
                r["source_file"] = zf
                # the four-part identity, from the engine's own contig, region and alias (one bound source)
                r["identity"] = f"{Path(zf).stem} / {r['contig']} / {r['region']} / {r['bgc_id']}"
            all_rows.extend(rows)
        except Exception as exc:  # noqa: BLE001
            emit(f"  skip {zf}: {exc}")
    if not all_rows:
        sys.stderr.write(f"NO_ROWS: no BGC rows from {len(zips)} zip(s) in {src}; nothing written\n")
        return 1
    cols = ["source_file", "identity", "bgc_id", "contig", "region", "obs_region_type", "obs_kcb_anchor",
            "obs_kcb_mibig_accession", "obs_kcb_protein_hits", "obs_edge_status",
            "obs_size_kb", "obs_cds_count", "obs_annotation_class", "obs_pks_ks", "obs_nrps_c", "obs_nrps_a",
            "cmp_t43_markers", "cmp_t43_vetoed", "cmp_architecture_capacity", "cmp_architecture_confidence"]
    with open(out, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in all_rows:
            w.writerow({k: r.get(k, "") for k in cols})
    emit(f"wrote {len(all_rows)} BGC rows from {len(zips)} zips -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
