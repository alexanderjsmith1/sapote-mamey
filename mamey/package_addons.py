"""package_addons.py — post-package emitters wired into `mamey run` (patches P01 + P02).

Canonical home for two package addons so the engine and the standalone tools share one implementation
(SSOT). Both operate on a *written* package dir:

  emit_rescue_4b(package_dir, clusterblast_dir)  -> Diagnostic Rescue 4B files (CSV/MD/JSON + tiling)
  write_analysis_forward(package_dir)            -> <strain>_ANALYSIS_FORWARD.md (+ .json)
  add_d4_sheet(workbook_path, leads)             -> D4_Diagnostic_Rescues sheet

Claim ceiling is preserved by diagnostic_rescue itself; these only render its output.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import glob
import json
import os

from . import diagnostic_rescue as DR
from .xlsx_determinism import canonicalize_xlsx
from .xlsx_determinism import save_workbook_safely as _save_wb_safely

COMPILATION_ORDER = ["Layperson's Guide", "Synopsis", "Chapter", "KCB",
                     "Mode B (BGC# order)", "Fermentation Card"]

# N-01: the priority worklist must rank by LEAD TIER (what is actually a promising lead), not by the raw
# triage Rank, which is a score-based routing prior for the judgment layer. A standing-rule/fragment downgrade
# caps the tier without zeroing the raw score, so without this a demoted Inventory fragment can sort above a
# real High/Medium lead. Sort key: tier first (Exceptional→High→Medium→Inventory), tie-break by triage Rank.
_LEAD_TIER_ORDER = {"Exceptional": 0, "High": 1, "Medium": 2, "Low": 3, "Inventory": 4}  # AQUARIUS_01: 'Low' ranks above Inventory


def _lead_tier_rank(row):
    tier = (row.get("Lead_tier_auto") or "").strip()
    try:
        rnk = int(row.get("Corrected_rank") or row.get("Rank") or 10**6)
    except (TypeError, ValueError):
        rnk = 10**6
    return (_LEAD_TIER_ORDER.get(tier, 99), rnk)



# ----------------------------------------------------------------------------- helpers
def _first(pkg, suffix):
    hits = glob.glob(os.path.join(pkg, suffix))
    return hits[0] if hits else None


def _manifest(pkg):
    return _loadj(os.path.join(pkg, "manifest.json"))


def _node_map(man):
    return {b["bgc_id"]: (b.get("contig") or "") for b in man.get("bgcs", [])}


def _cctt(man):
    return (man.get("source_scans", {}).get("cctt", {}) or {}).get("per_bgc", {}) or {}


def _kcb(pkg):
    rj = _first(pkg, "*_records.json")
    if not rj:
        return {}
    return {r["bgc_id"]: r.get("kcb_top") for r in _loadj(rj).get("records", [])}


# ----------------------------------------------------------------------------- 4B rescue
def emit_rescue_4b(package_dir, clusterblast_dir=None, enable_concordance=True):
    """Build Diagnostic Rescue leads and write the four 4B files. Returns the leads list."""
    man = _manifest(package_dir)
    strain = man.get("strain_id", "STRAIN")
    rg = _first(package_dir, "*_4A_RGGMCI_full.json")
    if not rg:
        return []
    rggmci = _loadj(rg)
    nodes = _node_map(man)
    tiling_fn = None
    if clusterblast_dir and os.path.isdir(clusterblast_dir):
        tiling_fn = DR.make_tiling_fn(clusterblast_dir, lambda bid: nodes.get(bid, ""))
    fmap = DR.load_family_map() if enable_concordance else None
    leads = DR.build_leads(rggmci, _cctt(man), deep_tiling_fn=tiling_fn,
                           kcb_per_bgc=_kcb(package_dir), family_map=fmap)
    _write_4b(package_dir, strain, leads, deep=bool(tiling_fn))
    return leads


def _write_4b(pkg, strain, leads, deep):
    p = os.path.join(pkg, strain)
    cols = ["pair", "rescue_tier", "kcb_concordance", "core_bgc", "core_node", "core_triggers",
            "core_kcb_family", "arm_bgc", "arm_node", "arm_roles", "arm_kcb_family", "shared_scaffold",
            "reference_genes_covered", "reference_gene_overlap", "overlap_fraction", "tiling_verdict",
            "rggmci_confidence", "rggmci_gate", "promoted_over_rggmci", "claim_ceiling", "safe_claim"]
    # v9.7.374: every write in this function goes to a .tmp sibling then os.replace()s into place,
    # so a process killed mid-write (SIGKILL/OOM/power loss) -- including on a re-run of `mamey run`
    # over a package_dir that already carries valid prior 4B files -- cannot truncate a previously
    # valid deliverable to zero/partial bytes.
    _csv_path = f"{p}_4B_Diagnostic_Rescue_Leads.csv"
    _csv_tmp = _csv_path + ".tmp"
    with open(_csv_tmp, "w", newline="", encoding="utf-8") as f:
        w = _SafeDictWriter(f, fieldnames=cols)
        w.writeheader()
        for l in leads:
            w.writerow({c: l.get(c) for c in cols})
    os.replace(_csv_tmp, _csv_path)
    _json_path = f"{p}_4B_Diagnostic_Rescue_Leads.json"
    _json_tmp = _json_path + ".tmp"
    with open(_json_tmp, "w", encoding="utf-8") as f:
        json.dump({"strain": strain, "tiling_basis": "clusterblast_deep" if deep else "rggmci_summary",
                   "claim_ceiling": DR.CLAIM_CEILING, "leads": leads}, f, indent=2)
    os.replace(_json_tmp, _json_path)
    tcols = ["pair", "shared_scaffold", "ref_source", "reference_genes_covered",
             "reference_gene_overlap", "overlap_fraction", "tiling_verdict"]
    _tiling_path = f"{p}_4B_Diagnostic_Rescue_Tiling.csv"
    _tiling_tmp = _tiling_path + ".tmp"
    with open(_tiling_tmp, "w", newline="", encoding="utf-8") as f:
        w = _SafeDictWriter(f, fieldnames=tcols)
        w.writeheader()
        for l in leads:
            w.writerow({c: l.get(c) for c in tcols})
    os.replace(_tiling_tmp, _tiling_path)
    _md_path = f"{p}_4B_Diagnostic_Rescue_Leads.md"
    _md_tmp = _md_path + ".tmp"
    with open(_md_tmp, "w", encoding="utf-8") as f:
        f.write(f"# Diagnostic Rescue Leads — {strain}\n\n")
        f.write(f"> **Claim ceiling (all rows):** {DR.CLAIM_CEILING}\n\n")
        if not leads:
            f.write("_No diagnostic-rescue candidates._\n")
            os.replace(_md_tmp, _md_path)
            return
        f.write("| Tier | Concordance | Pair | Core | Arm | Scaffold | Genes | Overlap |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for l in leads:
            f.write(f"| {l['rescue_tier']} | {l.get('kcb_concordance','')} | {l['pair']} | "
                    f"{l['core_bgc']} ({l['core_triggers']}) | {l['arm_bgc']} ({l['arm_roles']}) | "
                    f"{l['shared_scaffold'] or '—'} | "
                    f"{l['reference_genes_covered'] if l['reference_genes_covered'] is not None else '—'} | "
                    f"{l['reference_gene_overlap'] if l['reference_gene_overlap'] is not None else '—'} |\n")
    os.replace(_md_tmp, _md_path)


# ----------------------------------------------------------------------------- analysis-forward (P01)
def write_analysis_forward(package_dir, top=12):
    """Write the START-HERE judgment directive (+ machine-readable JSON). Returns the .md path."""
    man = _manifest(package_dir)
    strain = man.get("strain_id", "STRAIN")
    n_raw = (man.get("bgc_counts") or {}).get("raw", 0)
    judged = bool(man.get("top_bgc_targets")) or bool(man.get("wet_lab_priorities"))

    tb = _first(package_dir, "*_4_triage_board.csv")
    triage = list(csv.DictReader(open(tb, encoding="utf-8"))) if tb else []
    rj = _first(package_dir, "*_4B_Diagnostic_Rescue_Leads.json")
    leads = _loadj(rj)["leads"] if rj else []
    high = [l for l in leads if l["rescue_tier"] == "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"]
    # P01-richer: MODERATE leads are lexicon-unknown / saccharide-arm pairs worth a human look
    moderate = [l for l in leads if l["rescue_tier"] == "DIAGNOSTIC_RESCUE_MODERATE"]
    rescue_bgcs = {b for l in high for b in (l["core_bgc"], l["arm_bgc"])}

    md = os.path.join(package_dir, f"{strain}_ANALYSIS_FORWARD.md")
    status = "COMPLETE" if judged else "PENDING"
    # v9.7.374: write to a .tmp sibling then os.replace() into place -- this is the START-HERE
    # judgment directive a re-run of `mamey run` would otherwise be able to truncate mid-write.
    _md_tmp = md + ".tmp"
    with open(_md_tmp, "w", encoding="utf-8") as f:
        f.write(f"# \u25b6 Analysis-forward \u2014 {strain}\n\n")
        f.write(f"> **This package is DETERMINISTIC EXTRACTION (Mamey).** "
                f"Full Sapote judgment (\u00a71\u2013\u00a78 Mode B) is **{status}**.\n\n")
        if not judged:
            f.write(f"**{n_raw} BGCs extracted \u00b7 0 / {n_raw} given full Mode B judgment.** "
                    "Manifest `top_bgc_targets`/`wet_lab_priorities` are empty because judgment has not run.\n\n")
            f.write(f"## \u25b6 Start full judgment\n\nTrigger:  **`Run full Sapote analysis on {strain}`**\n\n")
            f.write("Compilation order: " + " \u2192 ".join(COMPILATION_ORDER) + "\n\n")
            if high:
                f.write("## \u2605 Judge these first \u2014 Diagnostic Rescue HIGH (concordant splits)\n\n")
                for l in high:
                    f.write(f"- **{l['pair']}** \u2014 {l['core_bgc']} ({l['core_triggers']}) + "
                            f"{l['arm_bgc']} ({l['arm_roles']}) on {l['shared_scaffold']} "
                            f"[{l.get('kcb_concordance','')}]. Judge both fragments together.\n")
                f.write("\n")
            if moderate:
                _cap = 8
                f.write(f"## \u26a0 Worth a look \u2014 {len(moderate)} MODERATE rescue leads (lexicon-unknown / "
                        "saccharide-arm)\n\nGeometry passes but class concordance is unconfirmed \u2014 a human "
                        "should eyeball these; some may be real splits whose families aren't yet curated.\n\n")
                f.write(f"Starting subset (top {min(_cap, len(moderate))} of {len(moderate)}; "
                        f"full list in `{strain}_Diagnostic_Rescue_Leads.md`):\n\n")
                for l in moderate[:_cap]:
                    f.write(f"- {l['pair']} \u2014 {l.get('core_bgc','')} + {l.get('arm_bgc','')} "
                            f"on {l.get('shared_scaffold','')}\n")
                if len(moderate) > _cap:
                    f.write(f"- \u2026 and {len(moderate) - _cap} more (see the detail file)\n")
                f.write("\n")
            f.write(f"\n")
            _ranked = sorted(triage, key=_lead_tier_rank)  # N-01: lead-tier order, not raw triage rank
            f.write(f"## Priority worklist \u2014 top {top} by lead tier\n\n")
            f.write("| # | BGC | node/contig | products | tier | capacity | \u2605 |\n"
                    "|---|---|---|---|---|---|---|\n")
            for i, row in enumerate(_ranked[:top], 1):
                bid = row.get("BGC_ID", "")
                star = "\u2605" if bid in rescue_bgcs else ""
                f.write(f"| {i} | {bid} | {row.get('Node_ID','')} | "
                        f"{(row.get('Products','') or '')[:34]} | {row.get('Lead_tier_auto','')} | "
                        f"{row.get('Arch_Capacity','')} | {star} |\n")
            f.write(f"\n## Progress tracker\n\n- [ ] Layperson's Guide  - [ ] Synopsis  - [ ] Chapter  "
                    f"- [ ] KCB  - [ ] Mode B: 0/{n_raw}  - [ ] Fermentation Card\n\n")
            f.write("> Claim ceiling: capacity-based, claim-safe; KCB = similarity not identity; "
                    "rescue leads are reconstruction hypotheses, not contig joins.\n")
            # C2: wire report_mode.render_board -- terse board for Sapote session input.
            # Makes report_mode.py load-bearing: the judgment layer gets a compact fact-anchored
            # scaffold it can paste directly into a Sapote session. (v9.7.58)
            try:
                from .report_mode import render_board as _render_board
                _recs = []
                _verts = []
                for row in _ranked[:50]:
                    _recs.append({
                        "bgc_id": row.get("BGC_ID", ""),
                        "user_label": row.get("User_Label", ""),
                        "contig": row.get("Contig", "") or row.get("Node_ID", ""),
                        "architecture_capacity": row.get("Arch_Capacity", ""),
                        "architecture_confidence": row.get("Class_Conf", ""),
                        "edge_status": row.get("Boundary", ""),
                        "antismash_region": row.get("antiSMASH_Region", ""),
                        "products": [p.strip() for p in (row.get("Products", "") or "").split(";") if p.strip()],
                        "kcb_top": row.get("KCB_top", ""),
                    })
                    try:
                        _ks = float(row.get("KCB_score", 0) or 0)
                    except (ValueError, TypeError):
                        _ks = 0
                    _band = ("very high (>100k)" if _ks > 100000 else
                             "high (>50k)" if _ks > 50000 else
                             "moderate (>5k)" if _ks > 5000 else
                             "low (<5k)" if _ks > 0 else "no KCB hit")
                    _verts.append({
                        "bgc_id": row.get("BGC_ID", ""),
                        "lead_tier": row.get("Lead_tier_auto", ""),
                        "claim_confidence": row.get("Arch", ""),
                        "kcb_similarity_band": _band,
                        "standing_rule_flag": row.get("Standing_rule", ""),
                        "primary_metabolism_flag": bool(row.get("Primary_metab_flag", "")),
                        "misanchor_flag": row.get("Misanchor_Flag", ""),
                    })
                f.write("\n## Terse board (Sapote session input)\n\n```\n")
                f.write(_render_board(_recs, _verts, mode="terse"))
                f.write("```\n")
            except Exception as _e:
                f.write(f"\n<!-- report_mode.render_board unavailable: {_e} -->\n")
        else:
            f.write("Judgment fields populated; Mode B appears complete.\n")
    os.replace(_md_tmp, md)

    # machine-readable sidecar for the session-log compiler (P05)
    _sidecar_path = os.path.join(package_dir, f"{strain}_analysis_forward.json")
    _sidecar_tmp = _sidecar_path + ".tmp"
    with open(_sidecar_tmp, "w", encoding="utf-8") as f:
        json.dump({"strain": strain, "judgment_status": status, "n_bgcs": n_raw,
                   "mode_b_complete": 0, "trigger": f"Run full Sapote analysis on {strain}",
                   "compilation_order": COMPILATION_ORDER,
                   "judge_first_high": [l["pair"] for l in high],
                   "moderate_review_count": len(moderate),
                   "priority_worklist": [
                       {"rank": i, "triage_rank": r.get("Rank"), "bgc": r.get("BGC_ID"),
                        "node": r.get("Node_ID"), "products": r.get("Products"),
                        "lead_tier": r.get("Lead_tier_auto"), "capacity": r.get("Arch_Capacity"),
                        "is_rescue_bgc": r.get("BGC_ID") in rescue_bgcs}
                       for i, r in enumerate(sorted(triage, key=_lead_tier_rank)[:top], 1)]}, f, indent=2)
    os.replace(_sidecar_tmp, _sidecar_path)
    return md


# ----------------------------------------------------------------------------- D4 workbook sheet (P02)
def add_d4_sheet(workbook_path, leads):
    """Add/replace the D4_Diagnostic_Rescues sheet on an existing per-strain workbook."""
    try:
        import openpyxl
    except Exception:
        return False
    if not os.path.exists(workbook_path):
        return False
    wb = openpyxl.load_workbook(workbook_path)
    if "D4_Diagnostic_Rescues" in wb.sheetnames:
        del wb["D4_Diagnostic_Rescues"]
    ws = wb.create_sheet("D4_Diagnostic_Rescues")
    cols = ["pair", "rescue_tier", "kcb_concordance", "core_bgc", "core_node", "core_triggers",
            "core_kcb_family", "arm_bgc", "arm_node", "arm_roles", "arm_kcb_family", "shared_scaffold",
            "reference_genes_covered", "reference_gene_overlap", "tiling_verdict", "safe_claim"]
    ws.append(cols)
    for l in leads:
        ws.append([l.get(c) for c in cols])
    # v9.7.374 fix: was a bare _save_wb_safely(wb, workbook_path) -- an in-place re-save of the just-written
    # <strain>_5_workbook.xlsx (workbook.py's own writer, moments earlier, correctly uses the
    # tmp+os.replace pattern -- see master_workbook.py's identical established convention). An
    # interrupted write here (kill, OOM, disk full) leaves the workbook a truncated/corrupt zip;
    # since this call happens BEFORE write_manifest() computes checksums, a corrupted workbook
    # would get hash-pinned into checksums_sha256.txt as "valid" on the next run, shipping an
    # unreadable 5_workbook.xlsx in a package that still reports checksum_integrity PASS.
    _tmp = str(workbook_path) + ".tmp"
    _save_wb_safely(wb, _tmp)
    canonicalize_xlsx(_tmp)
    os.replace(_tmp, str(workbook_path))
    return True


# ===== merged from package_addons_html.py (HTML open-me-first emitter) =====
#!/usr/bin/env python3
"""
package_addons_html.py — generate OPEN_ME_FIRST.html for every completed Mamey package.

C1 (B-list item): a collaborator-facing HTML entry point that summarises the package
contents in plain language, shows the top leads, and links to the key files — so
someone receiving a completed output package doesn't need to know the file numbering
scheme to find what they need.
"""
import os
import json
import csv
from .manifest_schema import read_manifest_field
from pathlib import Path


def _loadj(p):   # B1: context-managed json load (no leaked handle); +utf-8 (B2)
    with open(p, encoding="utf-8") as _f:
        return json.load(_f)



_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       max-width: 860px; margin: 40px auto; padding: 0 24px; color: #1a1a1a; }
h1 { color: #2c5f2e; border-bottom: 3px solid #2c5f2e; padding-bottom: 8px; }
h2 { color: #3a3a3a; margin-top: 32px; }
.badge { display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.85em;
         font-weight:600; margin-left:8px; }
.pass { background:#d4edda; color:#155724; }
.warn { background:#fff3cd; color:#856404; }
.fail { background:#f8d7da; color:#721c24; }
table { border-collapse:collapse; width:100%; margin:16px 0; }
th { background:#2c5f2e; color:white; padding:8px 12px; text-align:left; font-size:0.9em; }
td { padding:7px 12px; border-bottom:1px solid #e0e0e0; font-size:0.9em; }
tr:nth-child(even) { background:#f8f8f8; }
.file-list { list-style:none; padding:0; }
.file-list li { padding:4px 0; }
.file-list li a { color:#2c5f2e; text-decoration:none; }
.file-list li a:hover { text-decoration:underline; }
.note { background:#f0f7f0; border-left:4px solid #2c5f2e; padding:12px 16px;
        border-radius:0 4px 4px 0; margin:16px 0; font-size:0.95em; }
.pending { background:#fff8e1; border-left:4px solid #f9a825; padding:12px 16px;
           border-radius:0 4px 4px 0; margin:16px 0; }
footer { margin-top:48px; padding-top:16px; border-top:1px solid #ddd;
         font-size:0.8em; color:#666; }
"""


def write_open_me_first(package_dir: str | Path) -> Path:
    """Generate OPEN_ME_FIRST.html in package_dir. Returns the path written."""
    root = Path(package_dir)

    def _read_optional_metadata(path: Path) -> dict:
        """Return absent optional metadata as empty, but fail on present invalid metadata."""
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path.name} is unreadable: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} must contain a JSON object")
        return value

    manifest = _read_optional_metadata(root / "manifest.json")
    ms = _read_optional_metadata(root / "manifest_short.json")

    strain_id   = manifest.get("strain_id") or ms.get("strain_id") or root.name
    taxonomy    = manifest.get("taxonomy") or "not verified"
    source      = manifest.get("source") or "not supplied"
    # v9.7.371 fix: same defect already found and fixed in package_inspector.py::explain_command
    # (E2E-01, v9.7.338) -- the sealed manifest records the run mode at top-level "mode" ("gold"),
    # not under a "context.analysis_mode" key that no writer emits, and manifest_short.json never
    # sets a "mode" key either. Every OPEN_ME_FIRST.html ever generated showed "Mode: unknown"
    # regardless of whether the run was gold/smoke. Mirrors the fixed package_inspector.py version.
    mode        = ((manifest.get("context") or {}).get("analysis_mode")
                   or manifest.get("mode") or ms.get("mode")
                   or (manifest.get("run_context") or {}).get("mode") or "unknown")
    status      = ms.get("status") or "unknown"
    raw_bgcs    = read_manifest_field("raw_bgcs", manifest=manifest, manifest_short=ms, default="?")
    corrected   = read_manifest_field("corrected_bgcs", manifest=manifest, manifest_short=ms, default="?")
    asm_tier    = read_manifest_field("assembly_tier", manifest=manifest, manifest_short=ms, default="unknown")
    mamey_ver   = ms.get("mamey_version") or manifest.get("version") or "?"

    # Status badge
    status_upper = str(status).upper()
    if "COMPLETE" in status_upper or "PASS" in status_upper:
        badge_cls, badge_txt = "pass", "✅ EXTRACTION COMPLETE"
    elif "FAIL" in status_upper:
        badge_cls, badge_txt = "fail", "❌ VALIDATION FAILED"
    else:
        badge_cls, badge_txt = "warn", "⚠ UNKNOWN"

    # Top leads from manifest_short
    top_ab = ms.get("top_3_ab") or []
    top_af = ms.get("top_3_af") or []

    def _lead_rows(leads, score_key):
        if not leads:
            return '<tr><td colspan="3">No lead data (run judgment layer)</td></tr>'
        rows = ""
        for i, lead in enumerate(leads, 1):
            bgc = lead.get("bgc_id","?")
            contig = lead.get("contig","?")
            score = lead.get(score_key, lead.get("ab_score", lead.get("af_score","?")))
            rows += f"<tr><td>{i}</td><td><code>{bgc}</code> · {contig}</td><td>{score}</td></tr>"
        return rows

    # Key files
    def _find_files(patterns):
        found = []
        for pat in patterns:
            matches = sorted(root.glob(pat))
            found.extend(matches[:1])
        return found

    key_files = []
    for pat, label in [
        (f"{strain_id}_ANALYSIS_FORWARD.md", "Analysis Forward — ranked leads to judge first"),
        (f"{strain_id}_4_triage_board.csv", "Triage Board — all BGCs ranked"),
        (f"{strain_id}_4c_AB_lead_board.csv", "Antibacterial Lead Board"),
        (f"{strain_id}_4c_AF_lead_board.csv", "Antifungal Lead Board"),
        (f"{strain_id}_5_workbook.xlsx", "Per-Strain Workbook (Excel)"),
        ("manifest_short.json", "Manifest Short — machine-readable summary"),
        ("gate_validation.json", "Validation Gate"),
        ("issue_log.md", "Issue Log"),
        ("START_HERE.md", "Start Here (Markdown version)"),
    ]:
        p = root / pat
        if p.exists():
            key_files.append((p.name, label))

    file_items = "\n".join(
        f'''        <li><a href="{name}">{name}</a> — {label}</li>'''
        for name, label in key_files
    )

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mamey Package — {strain_id}</title>
  <style>{_CSS}</style>
</head>
<body>

<h1>📦 Mamey Package: {strain_id}
  <span class="badge {badge_cls}">{badge_txt}</span>
</h1>

<div class="note">
  <strong>What this is:</strong> A <em>deterministic extraction</em> package produced by Mamey v{mamey_ver}.
  It contains the inventory, scans, scores, and evidence for every biosynthetic gene cluster
  antiSMASH detected in this genome. It is <strong>not</strong> a finished analysis —
  the interpretive step (Mode B judgment, ecological synthesis, bench guidance) is the separate
  <strong>Sapote judgment layer</strong>, triggered by uploading this package to a Claude session.
</div>

<div class="pending">
  ⏳ <strong>Judgment pending.</strong> To start: upload <code>manifest.json</code> (or the Complete_Package.zip)
  to your Claude session and type: <em>"Run full Sapote analysis on {strain_id}"</em>
</div>

<h2>At a glance</h2>
<table>
  <tr><th>Field</th><th>Value</th></tr>
  <tr><td>Strain ID</td><td><strong>{strain_id}</strong></td></tr>
  <tr><td>Taxonomy</td><td>{taxonomy}</td></tr>
  <tr><td>Source</td><td>{source}</td></tr>
  <tr><td>Mode</td><td>{mode}</td></tr>
  <tr><td>Raw BGCs</td><td>{raw_bgcs}</td></tr>
  <tr><td>Corrected BGCs</td><td>{corrected}</td></tr>
  <tr><td>Assembly tier</td><td>{asm_tier}</td></tr>
  <tr><td>Mamey version</td><td>v{mamey_ver}</td></tr>
  <tr><td>Extraction status</td><td>{status}</td></tr>
</table>

<h2>Top antibacterial leads</h2>
<table>
  <tr><th>#</th><th>BGC · Contig</th><th>AB score</th></tr>
  {_lead_rows(top_ab, "ab_score")}
</table>

<h2>Top antifungal leads</h2>
<table>
  <tr><th>#</th><th>BGC · Contig</th><th>AF score</th></tr>
  {_lead_rows(top_af, "af_score")}
</table>

<h2>Key files — open these first</h2>
<ul class="file-list">
{file_items}
</ul>

<h2>How to read the results</h2>
<ul>
  <li><strong>Triage Board</strong> — all BGCs ranked by lead tier and antibacterial/antifungal score.
      Downgraded rows (standing-rule exclusions) are marked in the <code>Standing_rule</code> column.</li>
  <li><strong>Analysis Forward</strong> — the ordered list of BGCs the judgment layer should address first,
      with rescue recommendations.</li>
  <li><strong>Workbook (Excel)</strong> — multi-sheet summary with per-BGC rows, scan results,
      and provenance. Open <code>*_5_workbook.xlsx</code>.</li>
  <li><strong>Lead Boards</strong> — single-axis pre-sorted views: one for antibacterial, one for antifungal.
      The quickest way to identify the top chemistry.</li>
  <li><strong>Issue Log</strong> — any non-blocking issues recorded during extraction (accession labels,
      missing optional files, etc.). A populated issue log does not mean the package failed.</li>
</ul>

<div class="note">
  <strong>Claim safety reminder:</strong> all scores and class calls in this package represent
  <em>biosynthetic capacity consistent with</em> a class — not product identity. KCB hits are
  similarity signals, not proof. Bioactivity metadata is optional strain-level context and never
  supplies an assay target by default; no BGC is called antibacterial- or antifungal-negative on scores alone.
</div>

<footer>
  Sapote–Mamey v{mamey_ver} ·
  Generated by Mamey extraction engine · Judgment (Mode B, ecology, bench cards) requires the Sapote layer.
</footer>
</body>
</html>"""

    out_path = root / "OPEN_ME_FIRST.html"
    # Atomic write (.tmp + rename) — pipeline output-integrity standard. A killed process must not
    # leave a half-written collaborator-facing HTML that the post-seal enrichment check sees as present.
    tmp_path = root / "OPEN_ME_FIRST.html.tmp"
    tmp_path.write_text(html_out, encoding="utf-8")
    os.replace(tmp_path, out_path)
    return out_path
