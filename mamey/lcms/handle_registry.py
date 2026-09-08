"""LC-MS Chemical Handle Registry v2.

The registry translates directed-study gene evidence and group context into
bench-facing LC-HRMS/DAD guidance while preserving identity safety.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import io
import json
import os


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated LC-MS handle deliverable on disk (matches mamey/packaging.py's helper)."""
    path = Path(path)
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding, newline="") as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, str(path))

@dataclass(frozen=True)
class LCMSHandle:
    handle_key: str
    expected_chemistry_class: str
    polarity: str
    positive_mode_adducts: str
    negative_mode_adducts: str
    uv_dad_handle: str
    extraction_warning: str
    stability_warning: str
    dereplication_warning: str
    fractionation_hint: str
    identity_safety_statement: str

DEFAULT_HANDLES = {
    "polyene_macrolide_like": LCMSHandle(
        handle_key="polyene_macrolide_like",
        expected_chemistry_class="polyene/macrolide-like modular PKS fragment",
        polarity="positive and negative mode",
        positive_mode_adducts="[M+H]+, [M+Na]+, [M+NH4]+ if ionizes",
        negative_mode_adducts="[M-H]- if acidic/polyhydroxylated",
        uv_dad_handle="check for polyene/macrolide-like chromophores; do not require exact comparator match",
        extraction_warning="avoid assuming standard C18 captures all active chemistry; compare resin/fraction methods",
        stability_warning="protect from light/oxidation for polyene-like candidates",
        dereplication_warning="desertomycin/nystatin-like signals are comparator context, not product identity",
        fractionation_hint="track active fractions by bioassay plus broad LC-HRMS/DAD windows",
        identity_safety_statement="candidate signal only; confirm by MS/MS, NMR, standard, genetics, or purification",
    ),
    "conglobatin_macrodiolide_like": LCMSHandle(
        handle_key="conglobatin_macrodiolide_like",
        expected_chemistry_class="conglobatin/macrodiolide-like T1PKS fragment",
        polarity="positive mode primary; negative mode secondary",
        positive_mode_adducts="[M+H]+, [M+Na]+",
        negative_mode_adducts="[M-H]- if observable",
        uv_dad_handle="weak/simple UV possible; do not rely on strong chromophore",
        extraction_warning="medium-polarity resin fractions may be informative",
        stability_warning="avoid prolonged heat and repeated dry-down until activity is mapped",
        dereplication_warning="conglobatin comparator support is not conglobatin identity",
        fractionation_hint="prioritize activity-correlated LC features across neighboring T1PKS-like fragments",
        identity_safety_statement="macrodiolide-like comparator context only until chemistry confirms",
    ),
    "streptophenazine_background": LCMSHandle(
        handle_key="streptophenazine_background",
        expected_chemistry_class="streptophenazine background/control branch",
        polarity="positive and negative mode",
        positive_mode_adducts="[M+H]+, [M+Na]+",
        negative_mode_adducts="[M-H]-",
        uv_dad_handle="phenazine-like UV/visible behavior expected",
        extraction_warning="use purified material as control branch if available",
        stability_warning="handle as known purified/control chemistry",
        dereplication_warning="do not rank as primary antifungal unless activity remaps here",
        fractionation_hint="compare purified streptophenazine activity against active extract/fractions",
        identity_safety_statement="known/background branch, not primary antifungal hypothesis unless activity proves it",
    ),
    "generic_pks_context": LCMSHandle(
        handle_key="generic_pks_context",
        expected_chemistry_class="generic PKS/NRPS biosynthetic fragment",
        polarity="positive and negative mode",
        positive_mode_adducts="[M+H]+, [M+Na]+",
        negative_mode_adducts="[M-H]-",
        uv_dad_handle="no diagnostic UV assigned; collect full DAD trace",
        extraction_warning="use orthogonal extraction/fractionation if activity does not track expected fractions",
        stability_warning="unknown stability; avoid harsh conditions",
        dereplication_warning="no named-product claim from BGC context alone",
        fractionation_hint="bioassay-guided fractionation plus untargeted LC-HRMS",
        identity_safety_statement="bioinformatic candidate only",
    ),
}

def get_handle(key: str) -> LCMSHandle:
    return DEFAULT_HANDLES.get(key, DEFAULT_HANDLES["generic_pks_context"])

def infer_handle_key(row: dict) -> str:
    text = " ".join(str(row.get(k, "")) for k in [
        "set_id", "node", "mibig_context", "antiSMASH_domains", "modeb_function",
        "allowed_figure_label", "source_role"
    ]).lower()
    if "streptophenazine" in text or "bgc011" in text or "node_11" in text:
        return "streptophenazine_background"
    if "conglobatin" in text or "macrodiolide" in text or "node_456" in text or "node_58" in text:
        return "conglobatin_macrodiolide_like"
    if "nystatin" in text or "polyene" in text or "desertomycin" in text or "macrolide" in text or "cal_domain" in text:
        return "polyene_macrolide_like"
    if "pks" in text or "ks" in text or "at" in text:
        return "generic_pks_context"
    return "generic_pks_context"

def write_lcms_handles(gene_evidence_csv: Path, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_out: list[dict] = []
    with gene_evidence_csv.open(newline="") as handle:
        for row in csv.DictReader(handle):
            # Emit handles for evidence-supported core genes and background/control rows.
            role_text = (row.get("source_role", "") + " " + row.get("modeb_function", "")).lower()
            if row.get("evidence_tier") not in {"A", "B", "C"} and "background" not in row.get("set_id", "").lower():
                continue
            if not any(token in role_text for token in ["pks", "nrps", "biosynthetic", "megasynthase", "ketoreductase", "thioesterase"]) and "background" not in row.get("set_id", "").lower():
                continue
            key = infer_handle_key(row)
            handle_obj = get_handle(key)
            rows_out.append({
                "set_id": row.get("set_id", ""),
                "node": row.get("node", ""),
                "locus_tag": row.get("locus_tag", ""),
                "evidence_tier": row.get("evidence_tier", ""),
                **asdict(handle_obj),
            })

    csv_path = out_dir / "LCMS_Chemical_Handle.csv"
    fieldnames = [
        "set_id", "node", "locus_tag", "evidence_tier", "handle_key",
        "expected_chemistry_class", "polarity", "positive_mode_adducts",
        "negative_mode_adducts", "uv_dad_handle", "extraction_warning",
        "stability_warning", "dereplication_warning", "fractionation_hint",
        "identity_safety_statement",
    ]
    _csv_buf = io.StringIO()
    writer = _SafeDictWriter(_csv_buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows_out)
    _atomic_write_text(csv_path, _csv_buf.getvalue())

    md_path = out_dir / "LCMS_Chemical_Handle.md"
    lines = ["# LC-MS Chemical Handle Registry v2", "", "Comparator context is not product identity.", ""]
    for row in rows_out:
        lines.append(f"## {row['set_id']} · {row['node']} · {row['locus_tag']}")
        lines.append(f"- **Class:** {row['expected_chemistry_class']}")
        lines.append(f"- **Polarity:** {row['polarity']}")
        lines.append(f"- **UV/DAD:** {row['uv_dad_handle']}")
        lines.append(f"- **Extraction warning:** {row['extraction_warning']}")
        lines.append(f"- **Identity safety:** {row['identity_safety_statement']}")
        lines.append("")
    _atomic_write_text(md_path, "\n".join(lines))

    receipt = {
        "gene_evidence_csv": str(gene_evidence_csv),
        "handle_count": len(rows_out),
        "outputs": {
            "lcms_csv": str(csv_path),
            "lcms_md": str(md_path),
        }
    }
    receipt_path = out_dir / "LCMS_HANDLE_RECEIPT.json"
    _atomic_write_text(receipt_path, json.dumps(receipt, indent=2))
    return {**receipt["outputs"], "receipt": str(receipt_path)}
