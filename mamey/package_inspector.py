"""package_inspector.py — B4/B6/B7 CLI subcommands for exploring packages without re-running.

Implements:
  inspect  <zip>             B4: preview what Mamey sees in an antiSMASH ZIP before running
  explain  <package_dir>     B6: human-readable summary of an existing result package
  list-bgcs <package_dir>    B7: quick BGC inventory extraction, table or JSON

All three operate read-only and never invoke the extraction engine.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import csv
import json
import sys
import warnings
from .manifest_schema import read_manifest_field
import zipfile
from pathlib import Path


def _inspect_strain_guess(path: Path) -> str:
    """Return a ChatGPT-safe strain guess from an uploaded antiSMASH ZIP name."""
    import re as _re
    stem = Path(path).stem
    for suffix in ("_genomic", "_antismash", "_results"):
        stem = _re.sub(_re.escape(suffix) + r"$", "", stem, flags=_re.I)
    stem = _re.sub(r"\s*\(\d+\)\s*$", "", stem)
    stem = _re.sub(r"(?i)(?:[ _-]+(?:loose|copy|new))+\s*$", "", stem)
    stem = stem.replace(" ", "_")
    stem = _re.sub(r"[^A-Za-z0-9_.-]+", "_", stem)
    stem = _re.sub(r"_+", "_", stem).strip("_")
    return stem or Path(path).stem


def classify_antismash_zip(names: list[str]) -> dict[str, object]:
    """Classify common antiSMASH ZIP shapes for ChatGPT-safe intake guidance.

    This is intentionally conservative and read-only. It does not decide whether
    extraction will succeed; it explains the input shape that `inspect` sees.
    """
    import re as _re
    from .parsers import is_macos_cruft

    # v9.7.152: strip macOS AppleDouble/__MACOSX shadows before counting, so a
    # macOS-zipped antiSMASH folder is not double-counted (._*.gbk shadows end in
    # .gbk and contain 'region'). See AUDIT_AS-XXX_macosx_appledouble.
    names = [n for n in names if not is_macos_cruft(n)]

    gbk_regions = [n for n in names if n.endswith(".gbk") and "region" in n.lower()]
    gbk_other = [n for n in names if n.endswith(".gbk") and "region" not in n.lower()]
    json_files = [n for n in names if n.endswith(".json")]
    has_index = any(n.endswith("index.html") or n.endswith("index.htm") for n in names)
    has_regions_js = any(n.endswith("regions.js") for n in names)
    has_knownclusterblast = any("knownclusterblast" in n.lower() for n in names)
    has_clusterblast = any("clusterblast" in n.lower() for n in names)
    accession_like = False
    accession = ""
    for n in gbk_other + gbk_regions + json_files:
        base = Path(n).name
        m = _re.search(r"\b([A-Z]{1,3}_?\d{5,9}\.\d+)\b", base)
        if m:
            accession_like = True
            accession = m.group(1)
            break

    if len(gbk_regions) == 1 and has_index and has_regions_js and json_files and has_clusterblast:
        shape = "single_region_antismash_accession"
        summary = "raw antiSMASH single-region accession run"
    elif len(gbk_regions) > 1:
        shape = "multi_region_antismash_run"
        summary = "raw antiSMASH multi-region run"
    elif gbk_regions:
        shape = "minimal_antismash_region_run"
        summary = "raw antiSMASH region run"
    else:
        shape = "not_antismash_region_zip"
        summary = "not a parseable antiSMASH region ZIP"

    return {
        "shape": shape,
        "summary": summary,
        "region_gbk_count": len(gbk_regions),
        "other_gbk_count": len(gbk_other),
        "json_count": len(json_files),
        "has_index_html": has_index,
        "has_regions_js": has_regions_js,
        "has_clusterblast": has_clusterblast,
        "has_knownclusterblast": has_knownclusterblast,
        "accession_like": accession_like,
        "accession": accession,
    }


# ---------------------------------------------------------------------------
# B4: inspect — preview an antiSMASH ZIP
# ---------------------------------------------------------------------------

def inspect_command(args) -> int:
    """Preview what Mamey sees in an antiSMASH ZIP before running.

    Reports: antiSMASH version, number of GBK region files, presence of JSON
    evidence, presence of knownclusterblast TXT files, contig count estimate,
    and a recommended run command.
    """
    zip_path = Path(args.zip).resolve()
    if not zip_path.exists():
        emit(f"ERROR: file not found: {zip_path}", file=sys.stderr)
        return 1
    if not zipfile.is_zipfile(zip_path):
        # v9.7.407 ratchet paydown: one emission for one message. Byte-identical on stderr
        # (same two lines, same stream, same order) -- only the call-site count changes.
        emit(f"ERROR: not a valid ZIP file: {zip_path}\n"
              "  If this is a raw genome assembly (.fna/.fa/.fasta), run antiSMASH on it first.",
              file=sys.stderr)
        return 1

    with zipfile.ZipFile(zip_path) as zf:
        from .ziputil import regular_file_names
        names = regular_file_names(zf)

    # v9.7.152: strip macOS AppleDouble/__MACOSX shadows before any counting so
    # region GBK / KCB TXT / batch-estimate all reflect real files only.
    from .parsers import is_macos_cruft
    names = [n for n in names if not is_macos_cruft(n)]

    # Categorise contents
    gbk_regions = [n for n in names if n.endswith(".gbk") and "region" in n.lower()]
    gbk_other   = [n for n in names if n.endswith(".gbk") and "region" not in n.lower()]
    json_files  = [n for n in names if n.endswith(".json")]
    cb_txt      = [n for n in names if "clusterblast" in n and n.endswith(".txt")]
    html_files  = [n for n in names if n.endswith(".html") or n.endswith(".htm")]
    input_shape = classify_antismash_zip(names)

    # Detect antiSMASH version from the structured comment without asking
    # ``ZipFile.read`` to materialise the entire region member.  ``inspect`` is
    # the public preflight command, so it must apply the parser-owned GBK size
    # policy before touching attacker-controlled compressed bytes too.
    as_version = None
    refused_members: set[str] = set()
    if gbk_regions:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                member = gbk_regions[0]
                from .parsers import _gbk_size_guard
                refusal = _gbk_size_guard(zf.getinfo(member))
                if refusal:
                    refused_members.add(member)
                    warnings.warn(
                        f"GBK_SIZE_GUARD_REFUSED: {member}: {refusal}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                else:
                    with zf.open(member) as raw:
                        txt = raw.read(8192).decode("utf-8", errors="ignore")
                    import re
                    m = re.search(r"antiSMASH\s+([\d.]+)", txt)
                    if m:
                        as_version = m.group(1)
        except Exception:
            pass
    # v9.7.235 (H-002 / F-005): if the narrow GBK structured-comment probe misses (some antiSMASH 8
    # variants place the version elsewhere), fall back to the SAME extractor `run` uses, so inspect's
    # preflight can't contradict the run receipt ("not detected" vs "8.0.4").
    if not as_version:
        try:
            from .parsers import extract_antismash_version as _eav
            as_version = _eav(zip_path, refused_members=refused_members) or None
        except Exception:
            pass

    # Detect if this looks like a bare assembly (no GBK regions)
    if not gbk_regions:
        emit(f"\n⚠  {zip_path.name} — does NOT look like an antiSMASH output ZIP", f"   Found {len(names)} files but no GBK region files.", "   This may be a raw NCBI/genome download. Run antiSMASH first:", "   https://antismash.secondarymetabolites.org", sep="\n")
        return 1

    emit(f"\nMamey inspect — {zip_path.name}", f"{'─'*50}", f"  antiSMASH version : {as_version or 'not detected'}", f"  GBK region files  : {len(gbk_regions)}  ← Mamey will parse one BGC per file", f"  GBK other files   : {len(gbk_other)}", f"  JSON evidence     : {'YES (' + str(len(json_files)) + ' file(s))' if json_files else 'NO — KCB/RiQ will fall back to TXT'}", f"  KCB TXT files     : {len(cb_txt)}  ({'available' if cb_txt else 'absent — KCB may be blank'})", f"  HTML/viz files    : {len(html_files)}", f"  Total ZIP entries : {len(names)}", f"  Input shape       : {input_shape['summary']}", sep="\n")
    if input_shape.get("accession_like"):
        emit(f"  Public accession  : {input_shape.get('accession')}")

    if input_shape.get("shape") == "single_region_antismash_accession":
        emit("\n  Single-region accession note:", "    This looks like a raw antiSMASH run on one public GenBank/INSDC sequence, not a full genome and not a sealed Mamey package.", "    It is still a valid Mamey intake target if inspect passes.", "    Assembly completeness warnings such as VERY_POOR / 0% interior BGCs can be expected for this input shape.", "    Treat this as reference/control evidence unless the user says it is a discovery strain.", sep="\n")

    # Derive a ChatGPT-safe suggested strain name from the ZIP filename.
    strain_guess = _inspect_strain_guess(zip_path)

    emit(f"\n  Capped-session run command (gold is the only analysis mode):", f"    python -m mamey run \\", f"        --strain {strain_guess} \\", f"        --input-zip \"{zip_path.name}\" \\", f"        --taxonomy \"<Genus species>\" \\", f"        --source \"<isolation source>\" \\", f"        --mode gold \\", f"        --release <PUBLIC|PRIVATE> \\", f"        --capped-session \\", f"        --json-evidence off \\", f"        --brief none", f"    Then validate: python -m mamey validate <outdir>/{strain_guess}/package", sep="\n")

    if not json_files:
        emit(f"\n  ⚠  No JSON evidence found. The run command above already uses --json-evidence off.")
    if len(gbk_regions) > 40:
        import math
        batches = math.ceil(len(gbk_regions) / 20)
        emit(f"\n  ⚠  {len(gbk_regions)} BGCs is a large strain (~{batches} judgment batches).", f"     Run gold directly (command above); sequence Mode B authoring across ~{batches} batches after the package validates.", sep="\n")

    return 0


# ---------------------------------------------------------------------------
# B6: explain — human-readable summary of an existing package
# ---------------------------------------------------------------------------

def explain_command(args) -> int:
    """Print a plain-language summary of an existing Mamey result package.

    Reads manifest_short.json (fast path) or manifest.json (fallback).
    Never re-runs extraction.
    """
    pkg = Path(args.package_dir).resolve()
    if not pkg.is_dir():
        emit(f"ERROR: not a directory: {pkg}", file=sys.stderr)
        return 1

    # Load manifest_short (preferred) or fall back to manifest.json
    ms_path  = pkg / "manifest_short.json"
    man_path = pkg / "manifest.json"
    ms:  dict = {}
    man: dict = {}

    if ms_path.exists():
        try:
            ms = json.loads(ms_path.read_text(encoding="utf-8"))
        except Exception as e:
            emit(f"[WARN] could not read manifest_short.json: {e}", file=sys.stderr)
    if man_path.exists():
        try:
            man = json.loads(man_path.read_text(encoding="utf-8"))
        except Exception as e:
            emit(f"[WARN] could not read manifest.json: {e}", file=sys.stderr)

    if not ms and not man:
        emit(f"ERROR: no manifest.json or manifest_short.json found in {pkg}", file=sys.stderr)
        return 1

    strain_id  = ms.get("strain_id") or man.get("strain_id") or pkg.parent.name
    mamey_ver  = ms.get("mamey_version") or man.get("version") or "?"
    status     = ms.get("status") or "unknown"
    asm_tier   = read_manifest_field("assembly_tier", manifest=man, manifest_short=ms, default="unknown")
    raw_bgcs   = read_manifest_field("raw_bgcs", manifest=man, manifest_short=ms, default="?")
    corrected  = read_manifest_field("corrected_bgcs", manifest=man, manifest_short=ms, default="?")
    int_pct    = read_manifest_field("interior_pct", manifest=man, manifest_short=ms)
    tax        = man.get("taxonomy") or "not verified"
    source     = man.get("source") or "not supplied"
    # E2E-01 (v9.7.338): the sealed manifest records the run mode at top-level `mode` ("gold"),
    # not under a `context.analysis_mode` key (which no writer emits) — so `explain` always printed
    # "Mode : ?". Resolve from the real manifest field, keeping the legacy keys as fallbacks.
    mode       = ((man.get("context") or {}).get("analysis_mode")
                  or man.get("mode") or ms.get("mode")
                  or (man.get("run_context") or {}).get("mode") or "?")

    top_ab = ms.get("top_3_ab") or []
    top_af = ms.get("top_3_af") or []

    # Read issues from issue_log.md
    issues = []
    issue_log = next(pkg.glob("issue_log.md"), None)
    if issue_log and issue_log.exists():
        txt = issue_log.read_text(encoding="utf-8", errors="ignore")
        issues = [line.lstrip("- ").strip() for line in txt.splitlines()
                  if line.strip().startswith("-") and "No blocking" not in line]

    emit(f"\nMamey explain — {strain_id}", f"{'─'*55}", f"  Status        : {status}", f"  Taxonomy      : {tax}", f"  Source        : {source}", f"  Mode          : {mode}   Mamey v{mamey_ver}", f"  Assembly tier : {asm_tier}" + (f"  ({int_pct}% interior)" if int_pct is not None else ""), f"  Raw BGCs      : {raw_bgcs}", f"  Corrected BGCs: {corrected}", sep="\n")

    if top_ab:
        emit(f"\n  Top antibacterial leads:")
        for i, lead in enumerate(top_ab, 1):
            emit(f"    {i}. {lead.get('bgc_id','?')} · {lead.get('contig','?')}  AB={lead.get('ab_score','?')}")
    if top_af:
        emit(f"\n  Top antifungal leads:")
        for i, lead in enumerate(top_af, 1):
            emit(f"    {i}. {lead.get('bgc_id','?')} · {lead.get('contig','?')}  AF={lead.get('af_score','?')}")

    if issues:
        emit(f"\n  Issues ({len(issues)}):")
        for issue in issues[:5]:
            emit(f"    · {issue[:100]}")
        if len(issues) > 5:
            emit(f"    · … and {len(issues)-5} more (see issue_log.md)")

    # Key files present
    key_files = {
        "OPEN_ME_FIRST.html": "collaborator entry point",
        "manifest_short.json": "machine-readable summary",
        "manifest.json": "full handoff object",
    }
    present = [f"{f} ({desc})" for f, desc in key_files.items() if (pkg / f).exists()]
    missing = [f for f in key_files if not (pkg / f).exists()]
    if present:
        emit(f"\n  Key files: {', '.join(present)}")
    if missing:
        emit(f"  Missing  : {', '.join(missing)}")

    emit(f"\n  To start judgment: upload manifest.json to Claude and type:", f"    \"Run full Sapote analysis on {strain_id}\"", sep="\n")

    return 0


# ---------------------------------------------------------------------------
# B7: list-bgcs — quick BGC inventory extraction
# ---------------------------------------------------------------------------

def _cohort_locator(r) -> str:
    """Canonical cohort join key: {full contig} {regionNNN} (engine-1.9.110-scoped). Matches the
    precompute architecture tables' Assembly_Locator exactly so tally<->architecture join on it."""
    from .crosswalk import region_label
    contig = str(r.get("Contig", "") or "").strip()
    reg = str(r.get("antiSMASH_Region", "") or r.get("Region", "") or "").strip()
    if reg and not reg.startswith("region"):
        try:
            reg = region_label(int(float(reg)))
        except Exception:
            pass
    return f"{contig} {reg}".strip()


def _bgc_score(r, col):
    try:
        return float(r.get(col) or 0)
    except (ValueError, TypeError):
        return 0.0


def _bgc_json_row(r) -> dict:
    """Map one triage-board row to the canonical list-bgcs --json record.

    Single source of truth for the --json schema, so the tally fallback in
    tools/build_cohort_precompute.py cannot drift from `mamey list-bgcs --json`.
    """
    return {
        "bgc_id":      r.get("BGC_ID", ""),
        "contig":      r.get("Contig", ""),
        "node_id":     r.get("Node_ID", ""),
        # v9.7.224 (Part B / QA join-key fix): canonical cohort join key = {full contig} {region},
        # engine-1.9.110-scoped. Matches the precompute architecture tables' Assembly_Locator
        # exactly (full contig with .cov, region label, NO bgc_id parenthetical) — distinct from the
        # boss-facing crosswalk.assembly_locator() label, which truncates to node_id. This is the
        # machine join key so tally<->architecture join at read time (was 0 matches on node_id).
        "assembly_locator": _cohort_locator(r),
        "products":    r.get("Products", ""),
        "boundary":    r.get("Boundary", ""),
        "ab_score":    _bgc_score(r, "AB_auto"),
        "af_score":    _bgc_score(r, "AF_auto"),
        "novelty_auto": _bgc_score(r, "Novelty_auto"),
        "cctt_triggers": r.get("CCTT_triggers", ""),
        "lead_tier":   r.get("Lead_tier_auto", ""),
        "kcb_top":     r.get("KCB_top", ""),
        "depth_floor": r.get("Depth_floor", ""),
        "standing_rule": r.get("Standing_rule", ""),
        "primary_metab": r.get("Primary_metab_flag", ""),
    }


def bgc_json_list_from_board(board_path, axis="rank", top_n=None, include_dropped=False) -> list:
    """Build the `list-bgcs --json` record list from a sealed package's triage board.

    Pure function of the board CSV path — no globbing, no engine re-run. Mirrors the
    default `mamey list-bgcs --json` semantics (dropped rows excluded, rank order).
    Reused by tools/build_cohort_precompute.py so BGC_FULL_TALLY fills from the sealed
    package alone (closes the v9.7.277 known gap for that table).
    """
    with open(board_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not include_dropped:
        rows = [r for r in rows if not r.get("Primary_metab_flag") and not r.get("Standing_rule")]
    if axis == "ab":
        rows = sorted(rows, key=lambda r: _bgc_score(r, "AB_auto"), reverse=True)
    elif axis == "af":
        rows = sorted(rows, key=lambda r: _bgc_score(r, "AF_auto"), reverse=True)
    if top_n:
        rows = rows[:top_n]
    return [_bgc_json_row(r) for r in rows]


def list_bgcs_command(args) -> int:
    """Print a quick BGC inventory from a sealed package.

    Reads the triage board CSV and prints a table (default) or JSON (--json).
    Supports --top N to limit output and --axis ab|af to sort by a specific axis.
    Never re-runs extraction.
    """
    pkg = Path(args.package_dir).resolve()
    if not pkg.is_dir():
        emit(f"ERROR: not a directory: {pkg}", file=sys.stderr)
        return 1

    # Find triage board
    boards = sorted(pkg.glob("*_4_triage_board.csv"))
    if not boards:
        emit(f"ERROR: no *_4_triage_board.csv found in {pkg}", "  Run 'mamey validate <package_dir>' to check package integrity.", sep="\n", file=sys.stderr)
        return 1

    with open(boards[0], newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Filter and sort
    axis    = getattr(args, "axis", "rank")
    top_n   = getattr(args, "top_n", None)
    as_json = getattr(args, "json", False)
    exclude_dropped = not getattr(args, "include_dropped", False)

    if exclude_dropped:
        rows = [r for r in rows if not r.get("Primary_metab_flag") and not r.get("Standing_rule")]

    def _score(r, col):
        try: return float(r.get(col) or 0)
        except (ValueError, TypeError): return 0.0

    if axis == "ab":
        rows = sorted(rows, key=lambda r: _score(r, "AB_auto"), reverse=True)
    elif axis == "af":
        rows = sorted(rows, key=lambda r: _score(r, "AF_auto"), reverse=True)
    # else: keep triage board order (rank)

    if top_n:
        rows = rows[:top_n]

    if as_json:
        # Emit compact JSON array (schema via the shared _bgc_json_row mapper)
        out = [_bgc_json_row(r) for r in rows]
        emit(json.dumps(out, indent=2))
        return 0

    # Table output
    strain_id = boards[0].name.split("_4_triage_board")[0]
    emit(f'\nMamey list-bgcs — {strain_id}  ({len(rows)} BGC(s)' + (f', sorted by {axis}' if axis != 'rank' else '') + ')', f"{'─' * 90}", sep="\n")
    FMT = "{:<10} {:<18} {:<30} {:<9} {:<6} {:<6} {:<14}"
    emit(FMT.format("BGC_ID", "Contig/Node", "Products", "Boundary", "AB", "AF", "Lead_tier"), FMT.format("──────", "──────────", "──────────────────────────────", "────────", "──", "──", "──────────"), sep="\n")
    for r in rows:
        products = r.get("Products", "")[:28] + ("…" if len(r.get("Products","")) > 28 else "")
        emit(FMT.format(
            r.get("BGC_ID", "")[:10],
            (r.get("Node_ID") or r.get("Contig", ""))[:17],
            products,
            r.get("Boundary", "")[:9],
            f"{_score(r, 'AB_auto'):.0f}",
            f"{_score(r, 'AF_auto'):.0f}",
            r.get("Lead_tier_auto", "")[:14],
        ))

    emit(f"\n  Tip: --axis ab|af sorts by score  |  --json for machine-readable output  |  --top N to limit")
    return 0
